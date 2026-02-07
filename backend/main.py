from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import create_db_and_tables, SessionLocal, MediaItem
from backend.scanner import scan_directory
import os
import re
import mimetypes
import threading
import datetime

# Ensure required static directories exist so StaticFiles doesn't fail on startup
os.makedirs('backend/cache/thumbnails', exist_ok=True)
os.makedirs('backend/media', exist_ok=True)

app = FastAPI()

app.mount('/thumbnails', StaticFiles(directory='backend/cache/thumbnails'), name='thumbnails')
app.mount('/media', StaticFiles(directory='backend/media'), name='media')

scan_lock = threading.Lock()
scan_state = {
    'is_running': False,
    'directory': None,
    'started_at': None,
    'finished_at': None,
    'message': 'idle',
    'error': None,
}


def _now_iso():
    return datetime.datetime.utcnow().isoformat() + 'Z'


def _update_scan_state(**kwargs):
    with scan_lock:
        scan_state.update(kwargs)


def _run_scan_job(directory: str):
    _update_scan_state(
        is_running=True,
        directory=directory,
        started_at=_now_iso(),
        finished_at=None,
        message='running',
        error=None,
    )

    db = SessionLocal()
    try:
        scan_directory(directory, db)
        _update_scan_state(is_running=False, finished_at=_now_iso(), message='completed')
    except Exception as e:
        _update_scan_state(
            is_running=False,
            finished_at=_now_iso(),
            message='failed',
            error=str(e),
        )
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event('startup')
def on_startup():
    create_db_and_tables()


@app.post('/api/scan')
def scan_media_endpoint(directory: str):
    requested_path = os.path.abspath(directory)

    if not os.path.isdir(requested_path):
        raise HTTPException(status_code=404, detail=f'Directory does not exist: {requested_path}')

    with scan_lock:
        if scan_state['is_running']:
            return {
                'status': 'running',
                'message': 'A scan job is already running',
                'directory': scan_state['directory'],
            }

    worker = threading.Thread(target=_run_scan_job, args=(requested_path,), daemon=True)
    worker.start()

    return {
        'status': 'started',
        'message': 'Scan started in background',
        'directory': requested_path,
    }


@app.get('/api/scan/status')
def scan_status_endpoint():
    with scan_lock:
        return dict(scan_state)


@app.get('/api/media')
def get_media_items(db: Session = Depends(get_db)):
    return db.query(MediaItem).order_by(MediaItem.created_at.desc()).all()


@app.get('/api/media/by-date')
def get_media_by_date(date: str, db: Session = Depends(get_db)):
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid date format, expected YYYY-MM-DD')

    return (
        db.query(MediaItem)
        .filter(func.date(MediaItem.created_at) == date)
        .order_by(MediaItem.created_at.desc())
        .all()
    )


@app.get('/api/media/by-album')
def get_media_by_album(name: str, db: Session = Depends(get_db)):
    allowed = {'camera', 'screenshot', 'video', 'web', 'all'}
    if name not in allowed:
        raise HTTPException(status_code=400, detail='Invalid album name')

    query = db.query(MediaItem)
    if name == 'video':
        query = query.filter(MediaItem.media_type == 'video')
    elif name != 'all':
        query = query.filter(MediaItem.source_type == name)

    return query.order_by(MediaItem.created_at.desc()).all()


@app.get('/api/media/image/{item_id}')
async def get_image(item_id: str, db: Session = Depends(get_db)):
    item = db.query(MediaItem).filter(MediaItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail='Media item not found')

    file_path = item.filepath
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = 'image/jpeg'

    return StreamingResponse(open(file_path, 'rb'), media_type=mime_type)


@app.get('/api/media/stream/{item_id}')
async def stream_video(item_id: str, request: Request, db: Session = Depends(get_db)):
    item = db.query(MediaItem).filter(MediaItem.id == item_id).first()
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


@app.get('/')
def read_root():
    return {'message': 'Welcome to Local Smart Gallery'}
