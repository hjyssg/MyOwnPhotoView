import datetime
import logging
import mimetypes
import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.config import THUMBNAIL_DIR
from backend.core.dependencies import get_db
from backend.services.media_service import (
    get_active_media_dicts,
    get_media_item_or_none,
    trash_media_item_by_id,
)
from backend.scanner import get_video_duration
from backend.services.thumbnail_service import (
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
    create_video_thumbnail,
    generate_image_thumbnail,
    hash_file_sampled,
)

router = APIRouter()
logger = logging.getLogger(__name__)

THUMBNAIL_DIR_PATH = Path(THUMBNAIL_DIR)


def _load_media_snapshot(db: Session, item_id: str):
    try:
        item = get_media_item_or_none(db, item_id)
        if not item:
            return None
        return {'filepath': item.filepath, 'media_type': item.media_type}
    finally:
        # For file/stream responses, release DB connections before response body is sent.
        db.close()


@router.get('/api/media')
def get_media_items(db: Session = Depends(get_db)):
    return get_active_media_dicts(db)


@router.post('/api/media/{item_id}/trash')
def trash_media_item(item_id: str, db: Session = Depends(get_db)):
    try:
        return trash_media_item_by_id(db, item_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except FileNotFoundError as e:
        message = str(e)
        code = 404 if 'not found' in message.lower() else 500
        raise HTTPException(status_code=code, detail=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to move to recycle bin: {e}')


@router.get('/api/media/by-date')
def get_media_by_date(date: str, db: Session = Depends(get_db)):
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid date format, expected YYYY-MM-DD')

    from backend.database import MediaItem
    from backend.location_normalizer import media_item_to_dict

    items = (
        db.query(MediaItem)
        .filter(func.date(MediaItem.created_at) == date, MediaItem.is_deleted == 0)
        .order_by(MediaItem.created_at.desc())
        .all()
    )
    return [media_item_to_dict(item) for item in items]


@router.get('/api/media/by-album')
def get_media_by_album(name: str, db: Session = Depends(get_db)):
    allowed = {'camera', 'screenshot', 'video', 'web', 'all'}
    if name not in allowed:
        raise HTTPException(status_code=400, detail='Invalid album name')

    from backend.database import MediaItem
    from backend.location_normalizer import media_item_to_dict

    query = db.query(MediaItem).filter(MediaItem.is_deleted == 0)
    if name == 'video':
        query = query.filter(MediaItem.media_type == 'video')
    elif name != 'all':
        query = query.filter(MediaItem.source_type == name)

    items = query.order_by(MediaItem.created_at.desc()).all()
    return [media_item_to_dict(item) for item in items]


@router.get('/api/media/{item_id}/duration')
def get_media_duration(item_id: str, db: Session = Depends(get_db)):
    """Lazy duration fetch: returns cached duration or computes it on-demand for videos."""
    from backend.database import MediaItem

    item = db.query(MediaItem).filter(MediaItem.id == item_id, MediaItem.is_deleted == 0).first()
    if not item:
        raise HTTPException(status_code=404, detail='Media item not found')
    if item.media_type != 'video':
        return {'duration': None}

    # Return cached duration if available
    if item.duration is not None:
        return {'duration': item.duration}

    # Compute on-demand
    file_path = Path(item.filepath)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail='Video file not found')

    duration = get_video_duration(file_path)
    item.duration = duration
    db.commit()
    return {'duration': duration}


@router.get('/api/media/image/{item_id}')
async def get_image(item_id: str, request: Request, db: Session = Depends(get_db)):
    """
        获得原图
    """
    snapshot = _load_media_snapshot(db, item_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail='Media item not found')
    file_path = snapshot['filepath']

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = 'image/jpeg'

    file_size = os.path.getsize(file_path)
    file_mtime = int(os.path.getmtime(file_path))
    etag = f'W/"{file_mtime}-{file_size}"'

    if request.headers.get('if-none-match') == etag:
        return Response(status_code=304, headers={'ETag': etag, 'Cache-Control': 'public, max-age=86400'})

    return FileResponse(path=file_path, media_type=mime_type, headers={'ETag': etag, 'Cache-Control': 'public, max-age=86400'})


@router.get('/api/media/stream/{item_id}')
async def stream_video(item_id: str, request: Request, db: Session = Depends(get_db)):
    snapshot = _load_media_snapshot(db, item_id)
    if not snapshot or snapshot['media_type'] != 'video':
        raise HTTPException(status_code=404, detail='Video not found')
    video_path = snapshot['filepath']

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail='Video file not found')

    file_size = os.path.getsize(video_path)
    mime_type, _ = mimetypes.guess_type(video_path)
    if mime_type is None:
        mime_type = 'video/mp4'

    range_header = request.headers.get('Range')
    if range_header:
        range_match = re.search(r'bytes=(\d+)-(\d*)', range_header)
        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
        chunk_size = end - start + 1

        def generate():
            with open(video_path, 'rb') as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    read_size = min(65536, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    yield data
                    remaining -= len(data)

        return StreamingResponse(
            generate(),
            status_code=206,
            headers={
                'Content-Range': f'bytes {start}-{end}/{file_size}',
                'Accept-Ranges': 'bytes',
                'Content-Length': str(chunk_size),
            },
            media_type=mime_type,
        )

    return StreamingResponse(open(video_path, 'rb'), media_type=mime_type)


@router.get('/api/thumbnail')
async def get_thumbnail(
    filepath: str,
    thumbnail_path: str | None = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get thumbnail for a media file. Generates on-the-fly if not exists.
    
    Args:
        filepath: Path to the media file (required for generation)
        thumbnail_path: Existing thumbnail path for fast lookup (optional)
    """
    from backend.database import MediaItem

    # Fast path: if thumbnail_path is provided, try to find it directly
    if thumbnail_path:
        # thumbnail_path is like "thumbnails/abc123.jpg"
        direct_path = THUMBNAIL_DIR_PATH / Path(thumbnail_path).name
        if direct_path.exists():
            # Return thumbnail with caching
            file_size = os.path.getsize(direct_path)
            file_mtime = int(os.path.getmtime(direct_path))
            etag = f'W/"{file_mtime}-{file_size}"'

            if request and request.headers.get('if-none-match') == etag:
                return Response(status_code=304, headers={'ETag': etag, 'Cache-Control': 'public, max-age=86400'})

            return FileResponse(
                path=direct_path,
                media_type='image/jpeg',
                headers={'ETag': etag, 'Cache-Control': 'public, max-age=86400'}
            )
        # If thumbnail doesn't exist, fall through to generation flow

    # Find media item by filepath
    item = db.query(MediaItem).filter(MediaItem.filepath == filepath, MediaItem.is_deleted == 0).first()
    if not item:
        raise HTTPException(status_code=404, detail='Media item not found')

    file_path = Path(filepath)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail='File not found')

    # Determine thumbnail path based on content hash
    try:
        content_hash = hash_file_sampled(file_path)
    except Exception as e:
        logger.exception(
            'Failed to hash media file for thumbnail; fallback to stored hash. filepath=%s',
            filepath,
            exc_info=e,
        )
        content_hash = item.content_hash or 'fallback'

    thumbnail_filename = f'{content_hash}.jpg'
    thumbnail_full_path = THUMBNAIL_DIR_PATH / thumbnail_filename

    # Generate thumbnail if not exists
    if not thumbnail_full_path.exists():
        THUMBNAIL_DIR_PATH.mkdir(parents=True, exist_ok=True)
        ext = file_path.suffix.lower()

        try:
            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                generate_image_thumbnail(file_path, thumbnail_full_path)
            elif ext in SUPPORTED_VIDEO_EXTENSIONS:
                create_video_thumbnail(file_path, thumbnail_full_path)
            else:
                raise HTTPException(status_code=400, detail='Unsupported file type')
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(
                'Thumbnail generation raised exception. filepath=%s thumbnail_full_path=%s ext=%s',
                filepath,
                str(thumbnail_full_path),
                ext,
                exc_info=e,
            )
            raise HTTPException(status_code=500, detail='Failed to generate thumbnail')

    # Check again after generation attempt
    if not thumbnail_full_path.exists():
        logger.error(
            'Thumbnail generation finished but file missing. filepath=%s thumbnail_full_path=%s',
            filepath,
            str(thumbnail_full_path),
        )
        raise HTTPException(status_code=500, detail='Thumbnail generation failed')

    # Return thumbnail with caching
    file_size = os.path.getsize(thumbnail_full_path)
    file_mtime = int(os.path.getmtime(thumbnail_full_path))
    etag = f'W/"{file_mtime}-{file_size}"'

    if request and request.headers.get('if-none-match') == etag:
        return Response(status_code=304, headers={'ETag': etag, 'Cache-Control': 'public, max-age=86400'})

    return FileResponse(
        path=thumbnail_full_path,
        media_type='image/jpeg',
        headers={'ETag': etag, 'Cache-Control': 'public, max-age=86400'}
    )
