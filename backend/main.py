from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from backend.database import create_db_and_tables, SessionLocal, MediaItem
from backend.scanner import scan_directory
from backend.location_normalizer import media_item_to_dict, normalize_location_name
import os
import re
import mimetypes
import threading
import datetime
import json

# Ensure required static directories exist so StaticFiles doesn't fail on startup
os.makedirs('backend/cache/thumbnails', exist_ok=True)
os.makedirs('backend/media', exist_ok=True)

app = FastAPI()

app.mount('/thumbnails', StaticFiles(directory='backend/cache/thumbnails'), name='thumbnails')
app.mount('/media', StaticFiles(directory='backend/media'), name='media')

SCAN_FOLDERS_CONFIG_PATH = 'backend/data/scan_folders.json'


class ScanFoldersPayload(BaseModel):
    folders: list[str]

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


def _normalize_folder_paths(paths: list[str]) -> list[str]:
    normalized = []
    seen = set()
    for path in paths:
        raw = (path or '').strip()
        if not raw:
            continue
        abs_path = os.path.abspath(raw)
        key = abs_path.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(abs_path)
    return normalized


def _load_scan_folders_config() -> list[str]:
    if not os.path.exists(SCAN_FOLDERS_CONFIG_PATH):
        return []

    try:
        with open(SCAN_FOLDERS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        folders = data.get('folders', []) if isinstance(data, dict) else []
        if not isinstance(folders, list):
            return []
        return _normalize_folder_paths([str(v) for v in folders])
    except Exception:
        return []


def _save_scan_folders_config(folders: list[str]):
    os.makedirs(os.path.dirname(SCAN_FOLDERS_CONFIG_PATH), exist_ok=True)
    with open(SCAN_FOLDERS_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump({'folders': folders}, f, ensure_ascii=False, indent=2)


def _get_folder_scan_stats(db: Session, folder: str) -> tuple[bool, int]:
    abs_folder = os.path.abspath(folder).rstrip('/\\')
    prefix = abs_folder + os.sep

    count = (
        db.query(func.count(MediaItem.id))
        .filter(
            or_(
                MediaItem.filepath == abs_folder,
                MediaItem.filepath.like(f'{prefix}%'),
            )
        )
        .scalar()
        or 0
    )
    return count > 0, int(count)


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


def _run_scan_all_job(directories: list[str]):
    total = len(directories)
    _update_scan_state(
        is_running=True,
        directory=f'multi ({total})',
        started_at=_now_iso(),
        finished_at=None,
        message='running',
        error=None,
    )

    db = SessionLocal()
    try:
        for idx, directory in enumerate(directories, start=1):
            _update_scan_state(message=f'running {idx}/{total}: {directory}')
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


@app.get('/api/scan/folders')
def get_scan_folders_endpoint(db: Session = Depends(get_db)):
    folders = _load_scan_folders_config()
    items = []
    for folder in folders:
        has_scanned, scanned_count = _get_folder_scan_stats(db, folder)
        items.append(
            {
                'path': folder,
                'has_scanned': has_scanned,
                'scanned_count': scanned_count,
            }
        )
    return {'folders': folders, 'items': items}


@app.put('/api/scan/folders')
def save_scan_folders_endpoint(payload: ScanFoldersPayload):
    folders = _normalize_folder_paths(payload.folders)
    _save_scan_folders_config(folders)
    return {'folders': folders}


@app.post('/api/scan/all')
def scan_all_media_endpoint():
    folders = _load_scan_folders_config()
    existing = [p for p in folders if os.path.isdir(p)]

    if not existing:
        raise HTTPException(status_code=400, detail='No valid scan folders configured')

    with scan_lock:
        if scan_state['is_running']:
            return {
                'status': 'running',
                'message': 'A scan job is already running',
                'directory': scan_state['directory'],
            }

    worker = threading.Thread(target=_run_scan_all_job, args=(existing,), daemon=True)
    worker.start()

    return {
        'status': 'started',
        'message': 'Scan-all started in background',
        'directories': existing,
    }


@app.get('/api/media')
def get_media_items(db: Session = Depends(get_db)):
    items = db.query(MediaItem).order_by(MediaItem.created_at.desc()).all()
    return [media_item_to_dict(item) for item in items]


@app.get('/api/media/by-date')
def get_media_by_date(date: str, db: Session = Depends(get_db)):
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid date format, expected YYYY-MM-DD')

    items = (
        db.query(MediaItem)
        .filter(func.date(MediaItem.created_at) == date)
        .order_by(MediaItem.created_at.desc())
        .all()
    )
    return [media_item_to_dict(item) for item in items]


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

    items = query.order_by(MediaItem.created_at.desc()).all()
    return [media_item_to_dict(item) for item in items]


@app.get('/api/locations')
def get_locations(db: Session = Depends(get_db)):
    items = (
        db.query(MediaItem)
        .filter(MediaItem.latitude.isnot(None), MediaItem.longitude.isnot(None))
        .order_by(MediaItem.created_at.desc())
        .all()
    )

    groups = {}
    for item in items:
        location_city, location_key = normalize_location_name(item.location_name)
        if not location_key:
            continue

        if location_key not in groups:
            groups[location_key] = {
                'location_key': location_key,
                'location_city': location_city,
                'count': 0,
                'sum_lat': 0.0,
                'sum_lon': 0.0,
                'cover_id': item.id,
            }

        groups[location_key]['count'] += 1
        groups[location_key]['sum_lat'] += float(item.latitude)
        groups[location_key]['sum_lon'] += float(item.longitude)

    result = []
    for _, g in groups.items():
        if g['count'] == 0:
            continue
        result.append(
            {
                'location_key': g['location_key'],
                'location_city': g['location_city'],
                'count': g['count'],
                'center_latitude': g['sum_lat'] / g['count'],
                'center_longitude': g['sum_lon'] / g['count'],
                'cover_id': g['cover_id'],
            }
        )

    result.sort(key=lambda x: x['count'], reverse=True)
    return result


@app.get('/api/media/by-location')
def get_media_by_location(key: str, db: Session = Depends(get_db)):
    target = (key or '').strip().lower()
    if not target:
        raise HTTPException(status_code=400, detail='Missing location key')

    items = db.query(MediaItem).order_by(MediaItem.created_at.desc()).all()
    filtered = []
    for item in items:
        _, location_key = normalize_location_name(item.location_name)
        if (location_key or '').lower() == target:
            filtered.append(media_item_to_dict(item))
    return filtered


@app.get('/api/media/image/{item_id}')
async def get_image(item_id: str, request: Request):
    db = SessionLocal()
    try:
        item = db.query(MediaItem).filter(MediaItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail='Media item not found')
        file_path = item.filepath
    finally:
        db.close()

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = 'image/jpeg'

    file_size = os.path.getsize(file_path)
    file_mtime = int(os.path.getmtime(file_path))
    etag = f'W/"{file_mtime}-{file_size}"'

    if request.headers.get('if-none-match') == etag:
        return Response(
            status_code=304,
            headers={
                'ETag': etag,
                'Cache-Control': 'public, max-age=86400',
            },
        )

    return StreamingResponse(
        open(file_path, 'rb'),
        media_type=mime_type,
        headers={
            'ETag': etag,
            'Cache-Control': 'public, max-age=86400',
        },
    )


@app.get('/api/media/stream/{item_id}')
async def stream_video(item_id: str, request: Request):
    db = SessionLocal()
    try:
        item = db.query(MediaItem).filter(MediaItem.id == item_id).first()
        if not item or item.media_type != 'video':
            raise HTTPException(status_code=404, detail='Video not found')
        video_path = item.filepath
    finally:
        db.close()

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
