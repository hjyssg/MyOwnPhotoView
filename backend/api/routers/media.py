import datetime
import mimetypes
import os
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db
from backend.services.media_service import (
    get_active_media_dicts,
    get_media_item_or_none,
    trash_media_item_by_id,
)

router = APIRouter()


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


@router.get('/api/media/image/{item_id}')
async def get_image(item_id: str, request: Request, db: Session = Depends(get_db)):
    item = get_media_item_or_none(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail='Media item not found')
    file_path = item.filepath

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
    item = get_media_item_or_none(db, item_id)
    if not item or item.media_type != 'video':
        raise HTTPException(status_code=404, detail='Video not found')
    video_path = item.filepath

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
