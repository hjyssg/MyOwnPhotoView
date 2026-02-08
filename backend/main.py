from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
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
import math
import shutil
import socket
import ipaddress
import io
import qrcode
try:
    from send2trash import send2trash
except Exception:
    send2trash = None

# Ensure required static directories exist so StaticFiles doesn't fail on startup
os.makedirs('backend/cache/thumbnails', exist_ok=True)
os.makedirs('backend/media', exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ],
    allow_origin_regex=r'^https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|192\.168\.\d+\.\d+)(:\d+)?$',
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.mount('/thumbnails', StaticFiles(directory='backend/cache/thumbnails'), name='thumbnails')
app.mount('/media', StaticFiles(directory='backend/media'), name='media')

SCAN_FOLDERS_CONFIG_PATH = 'backend/data/scan_folders.json'
APP_SETTINGS_CONFIG_PATH = 'backend/data/app_settings.json'


DEFAULT_APP_SETTINGS = {
    'auto_scan_on_startup': False,
    'scan_mode': 'incremental',  # incremental | force
}


class ScanFoldersPayload(BaseModel):
    folders: list[str]


class AppSettingsPayload(BaseModel):
    auto_scan_on_startup: bool
    scan_mode: str

scan_lock = threading.Lock()
scan_state = {
    'is_running': False,
    'directory': None,
    'current_folder': None,
    'current_file': None,
    'processed_files': 0,
    'total_files': 0,
    'current_folder_index': 0,
    'total_folders': 0,
    'stats': None,
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


def _normalize_scan_mode(value: str | None) -> str:
    mode = (value or '').strip().lower()
    return 'force' if mode == 'force' else 'incremental'


def _load_app_settings() -> dict:
    settings = dict(DEFAULT_APP_SETTINGS)
    if not os.path.exists(APP_SETTINGS_CONFIG_PATH):
        return settings

    try:
        with open(APP_SETTINGS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            settings['auto_scan_on_startup'] = bool(data.get('auto_scan_on_startup', settings['auto_scan_on_startup']))
            settings['scan_mode'] = _normalize_scan_mode(data.get('scan_mode'))
    except Exception:
        pass

    return settings


def _save_app_settings(settings: dict):
    os.makedirs(os.path.dirname(APP_SETTINGS_CONFIG_PATH), exist_ok=True)
    payload = {
        'auto_scan_on_startup': bool(settings.get('auto_scan_on_startup', False)),
        'scan_mode': _normalize_scan_mode(settings.get('scan_mode')),
    }
    with open(APP_SETTINGS_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _should_force_rescan(force_rescan: bool | None = None) -> bool:
    if force_rescan is not None:
        return bool(force_rescan)
    settings = _load_app_settings()
    return settings.get('scan_mode') == 'force'


def _get_folder_scan_stats(db: Session, folder: str) -> tuple[bool, int]:
    abs_folder = os.path.abspath(folder).rstrip('/\\')
    prefix = abs_folder + os.sep

    count = (
        db.query(func.count(MediaItem.id))
        .filter(
            or_(
                MediaItem.filepath == abs_folder,
                MediaItem.filepath.like(f'{prefix}%'),
            ),
            MediaItem.is_deleted == 0,
        )
        .scalar()
        or 0
    )
    return count > 0, int(count)


def _run_scan_job(directory: str, force_rescan: bool = False):
    _update_scan_state(
        is_running=True,
        directory=directory,
        current_folder=directory,
        current_file=None,
        processed_files=0,
        total_files=0,
        current_folder_index=1,
        total_folders=1,
        stats=None,
        started_at=_now_iso(),
        finished_at=None,
        message='running',
        error=None,
    )

    db = SessionLocal()
    try:
        def on_progress(payload: dict):
            _update_scan_state(
                current_folder=directory,
                **payload,
            )

        stats = scan_directory(
            directory,
            db,
            force_rescan=force_rescan,
            progress_callback=on_progress,
        )
        _update_scan_state(
            is_running=False,
            current_file=None,
            finished_at=_now_iso(),
            message='completed',
            stats=stats,
        )
    except Exception as e:
        _update_scan_state(
            is_running=False,
            current_file=None,
            finished_at=_now_iso(),
            message='failed',
            error=str(e),
        )
    finally:
        db.close()


def _run_scan_all_job(directories: list[str], force_rescan: bool = False):
    total = len(directories)
    _update_scan_state(
        is_running=True,
        directory=f'multi ({total})',
        current_folder=None,
        current_file=None,
        processed_files=0,
        total_files=0,
        current_folder_index=0,
        total_folders=total,
        stats=None,
        started_at=_now_iso(),
        finished_at=None,
        message='running',
        error=None,
    )

    db = SessionLocal()
    try:
        summary = {
            'added': 0,
            'updated': 0,
            'skipped': 0,
            'deleted': 0,
            'processed_files': 0,
            'total_files': 0,
        }

        for idx, directory in enumerate(directories, start=1):
            def on_progress(payload: dict, _directory=directory, _idx=idx):
                _update_scan_state(
                    current_folder=_directory,
                    current_folder_index=_idx,
                    total_folders=total,
                    **payload,
                )

            stats = scan_directory(
                directory,
                db,
                force_rescan=force_rescan,
                progress_callback=on_progress,
            )
            for key in summary.keys():
                summary[key] += int(stats.get(key, 0))

        _update_scan_state(
            is_running=False,
            current_file=None,
            finished_at=_now_iso(),
            message='completed',
            stats=summary,
        )
    except Exception as e:
        _update_scan_state(
            is_running=False,
            current_file=None,
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


def _percentile(sorted_values: list[int], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])

    rank = (len(sorted_values) - 1) * p
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return float(sorted_values[low])

    low_v = float(sorted_values[low])
    high_v = float(sorted_values[high])
    return low_v + (high_v - low_v) * (rank - low)


def _sample_items_by_range(items: list[dict], sample_count: int) -> list[dict]:
    if sample_count <= 0 or not items:
        return []
    if len(items) <= sample_count:
        return items

    total = len(items)
    sampled = []
    for i in range(sample_count):
        start = (i * total) // sample_count
        end = ((i + 1) * total) // sample_count
        pick_index = (start + max(start, end - 1)) // 2
        sampled.append(items[pick_index])
    return sampled


def _normalize_location_key_for_match(location_key: str | None) -> str:
    return (location_key or '').strip().lower()


def _query_mappable_media_items(db: Session) -> list[MediaItem]:
    return (
        db.query(MediaItem)
        .filter(MediaItem.latitude.isnot(None), MediaItem.longitude.isnot(None), MediaItem.is_deleted == 0)
        .order_by(MediaItem.created_at.desc())
        .all()
    )


def _is_under_any_scan_folder(filepath: str, folders: list[str]) -> bool:
    abs_path = os.path.abspath(filepath)
    for folder in folders:
        abs_folder = os.path.abspath(folder)
        try:
            common = os.path.commonpath([abs_path, abs_folder])
            if common == abs_folder:
                return True
        except Exception:
            continue
    return False


def _soft_delete_outside_scan_folders(db: Session, folders: list[str]) -> int:
    now = datetime.datetime.utcnow()
    changed = 0
    items = db.query(MediaItem).all()
    for item in items:
        if _is_under_any_scan_folder(item.filepath, folders):
            continue
        if int(item.is_deleted or 0) == 1:
            continue
        item.is_deleted = 1
        item.deleted_at = now
        changed += 1
    if changed > 0:
        db.commit()
    return changed


def _delete_thumbnail_file_by_relpath(relpath: str) -> bool:
    if not relpath:
        return False
    thumb_name = os.path.basename(relpath)
    thumb_path = os.path.join('backend', 'cache', 'thumbnails', thumb_name)
    if not os.path.isfile(thumb_path):
        return False
    try:
        os.remove(thumb_path)
        return True
    except Exception:
        return False


def _cleanup_thumbnail_if_unused(db: Session, relpath: str | None) -> bool:
    if not relpath:
        return False
    refs = (
        db.query(func.count(MediaItem.id))
        .filter(MediaItem.thumbnail_path == relpath, MediaItem.is_deleted == 0)
        .scalar()
        or 0
    )
    if int(refs) > 0:
        return False
    return _delete_thumbnail_file_by_relpath(relpath)


def _hard_delete_soft_deleted_items(db: Session) -> dict:
    items = db.query(MediaItem).filter(MediaItem.is_deleted == 1).all()
    if not items:
        return {'deleted_media_items': 0, 'deleted_thumbnails': 0}

    thumbnails = {item.thumbnail_path for item in items if item.thumbnail_path}
    deleted_media_items = len(items)
    for item in items:
        db.delete(item)
    db.commit()

    deleted_thumbnails = 0
    for relpath in thumbnails:
        refs = db.query(func.count(MediaItem.id)).filter(MediaItem.thumbnail_path == relpath).scalar() or 0
        if int(refs) == 0 and _delete_thumbnail_file_by_relpath(relpath):
            deleted_thumbnails += 1

    return {
        'deleted_media_items': deleted_media_items,
        'deleted_thumbnails': deleted_thumbnails,
    }


def _cleanup_unused_thumbnails(db: Session) -> dict:
    thumbnail_dir = os.path.join('backend', 'cache', 'thumbnails')
    if not os.path.isdir(thumbnail_dir):
        return {'deleted_thumbnails': 0, 'kept_thumbnails': 0}

    referenced_rows = db.query(MediaItem.thumbnail_path).filter(MediaItem.thumbnail_path.isnot(None)).all()
    referenced_names = {os.path.basename(row[0]) for row in referenced_rows if row and row[0]}

    deleted_thumbnails = 0
    kept_thumbnails = 0
    for name in os.listdir(thumbnail_dir):
        file_path = os.path.join(thumbnail_dir, name)
        if not os.path.isfile(file_path):
            continue
        if name in referenced_names:
            kept_thumbnails += 1
            continue
        try:
            os.remove(file_path)
            deleted_thumbnails += 1
        except Exception:
            kept_thumbnails += 1

    return {
        'deleted_thumbnails': deleted_thumbnails,
        'kept_thumbnails': kept_thumbnails,
    }


def _is_private_ipv4(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
        return isinstance(ip, ipaddress.IPv4Address) and (ip.is_private or ip.is_loopback)
    except Exception:
        return False


def _collect_local_ipv4_candidates() -> list[str]:
    candidates = set()

    try:
        host_name = socket.gethostname()
        _, _, addrs = socket.gethostbyname_ex(host_name)
        for ip in addrs:
            if _is_private_ipv4(ip):
                candidates.add(ip)
    except Exception:
        pass

    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, family=socket.AF_INET)
        for info in infos:
            ip = info[4][0]
            if _is_private_ipv4(ip):
                candidates.add(ip)
    except Exception:
        pass

    ordered = sorted(candidates)
    return ordered


def _build_access_url_candidates(request: Request) -> list[str]:
    urls = []
    seen = set()

    def push(url: str):
        if not url:
            return
        if url in seen:
            return
        seen.add(url)
        urls.append(url)

    frontend_port = os.getenv('FRONTEND_PORT', '3000').strip() or '3000'
    frontend_scheme = os.getenv('FRONTEND_SCHEME', 'http').strip() or 'http'
    frontend_host = os.getenv('FRONTEND_HOST', '').strip()
    if frontend_host:
        push(f'{frontend_scheme}://{frontend_host}:{frontend_port}')

    host = (request.url.hostname or '').strip()
    if host and host not in ('localhost', '127.0.0.1'):
        push(f'http://{host}:{frontend_port}')

    for ip in _collect_local_ipv4_candidates():
        if ip in ('127.0.0.1',):
            continue
        push(f'http://{ip}:{frontend_port}')

    push('http://localhost:3000')
    return urls


@app.get('/api/network/access')
def get_network_access_info(request: Request):
    candidates = _build_access_url_candidates(request)
    preferred = candidates[0] if candidates else 'http://localhost:3000'
    return {
        'preferred_url': preferred,
        'candidate_urls': candidates,
    }


@app.get('/api/network/qrcode')
def get_network_access_qrcode(request: Request, target: str | None = None):
    candidates = _build_access_url_candidates(request)
    fallback = candidates[0] if candidates else 'http://localhost:3000'
    content = (target or '').strip() or fallback

    qr_img = qrcode.make(content)
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type='image/png',
        headers={
            'Cache-Control': 'no-store',
        },
    )


@app.on_event('startup')
def on_startup():
    create_db_and_tables()

    folders = _load_scan_folders_config()
    db = SessionLocal()
    try:
        _soft_delete_outside_scan_folders(db, folders)
    finally:
        db.close()

    settings = _load_app_settings()
    if not settings.get('auto_scan_on_startup'):
        return

    existing = [p for p in folders if os.path.isdir(p)]
    if not existing:
        return

    with scan_lock:
        if scan_state['is_running']:
            return

    worker = threading.Thread(
        target=_run_scan_all_job,
        args=(existing, _should_force_rescan()),
        daemon=True,
    )
    worker.start()


@app.post('/api/scan')
def scan_media_endpoint(directory: str, force_rescan: bool | None = None):
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

    worker = threading.Thread(
        target=_run_scan_job,
        args=(requested_path, _should_force_rescan(force_rescan)),
        daemon=True,
    )
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
def save_scan_folders_endpoint(payload: ScanFoldersPayload, db: Session = Depends(get_db)):
    folders = _normalize_folder_paths(payload.folders)
    _save_scan_folders_config(folders)
    soft_deleted_count = _soft_delete_outside_scan_folders(db, folders)
    return {'folders': folders, 'soft_deleted_count': int(soft_deleted_count)}


@app.get('/api/settings')
def get_app_settings_endpoint():
    return _load_app_settings()


@app.put('/api/settings')
def save_app_settings_endpoint(payload: AppSettingsPayload):
    normalized = {
        'auto_scan_on_startup': payload.auto_scan_on_startup,
        'scan_mode': _normalize_scan_mode(payload.scan_mode),
    }
    _save_app_settings(normalized)
    return normalized


@app.post('/api/scan/all')
def scan_all_media_endpoint(force_rescan: bool | None = None):
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

    worker = threading.Thread(
        target=_run_scan_all_job,
        args=(existing, _should_force_rescan(force_rescan)),
        daemon=True,
    )
    worker.start()

    return {
        'status': 'started',
        'message': 'Scan-all started in background',
        'directories': existing,
    }


@app.post('/api/scan/reset')
def reset_scan_data_endpoint():
    with scan_lock:
        if scan_state['is_running']:
            raise HTTPException(status_code=409, detail='Scan is running, cannot reset now')

    db = SessionLocal()
    try:
        deleted = db.query(MediaItem).delete()
        db.commit()
    finally:
        db.close()

    thumbnail_dir = 'backend/cache/thumbnails'
    removed_thumbnails = 0
    if os.path.isdir(thumbnail_dir):
        for name in os.listdir(thumbnail_dir):
            file_path = os.path.join(thumbnail_dir, name)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    removed_thumbnails += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path, ignore_errors=True)
            except Exception:
                pass

    _update_scan_state(
        is_running=False,
        directory=None,
        current_folder=None,
        current_file=None,
        processed_files=0,
        total_files=0,
        current_folder_index=0,
        total_folders=0,
        stats=None,
        started_at=None,
        finished_at=_now_iso(),
        message='idle',
        error=None,
    )

    return {
        'status': 'ok',
        'deleted_media_items': int(deleted or 0),
        'deleted_thumbnails': removed_thumbnails,
    }


@app.post('/api/maintenance/purge-soft-deleted')
def purge_soft_deleted_endpoint():
    with scan_lock:
        if scan_state['is_running']:
            raise HTTPException(status_code=409, detail='Scan is running, cannot purge now')

    db = SessionLocal()
    try:
        result = _hard_delete_soft_deleted_items(db)
    finally:
        db.close()

    return {'status': 'ok', **result}


@app.post('/api/thumbnails/cleanup-unused')
def cleanup_unused_thumbnails_endpoint():
    with scan_lock:
        if scan_state['is_running']:
            raise HTTPException(status_code=409, detail='Scan is running, cannot cleanup now')

    db = SessionLocal()
    try:
        result = _cleanup_unused_thumbnails(db)
    finally:
        db.close()

    return {'status': 'ok', **result}


@app.get('/api/media')
def get_media_items(db: Session = Depends(get_db)):
    items = db.query(MediaItem).filter(MediaItem.is_deleted == 0).order_by(MediaItem.created_at.desc()).all()
    return [media_item_to_dict(item) for item in items]


@app.post('/api/media/{item_id}/trash')
def trash_media_item(item_id: str, db: Session = Depends(get_db)):
    if send2trash is None:
        raise HTTPException(status_code=500, detail='send2trash is not installed on server')

    item = db.query(MediaItem).filter(MediaItem.id == item_id).first()
    if not item or int(item.is_deleted or 0) == 1:
        raise HTTPException(status_code=404, detail='Media item not found')

    file_path = item.filepath
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')

    try:
        send2trash(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to move to recycle bin: {e}')

    now = datetime.datetime.utcnow()
    item.is_deleted = 1
    item.deleted_at = now
    db.commit()

    thumbnail_removed = False
    if item.media_type == 'video':
        thumbnail_removed = _cleanup_thumbnail_if_unused(db, item.thumbnail_path)

    return {
        'status': 'ok',
        'id': item.id,
        'trashed': True,
        'thumbnail_removed': bool(thumbnail_removed),
    }


@app.get('/api/media/by-date')
def get_media_by_date(date: str, db: Session = Depends(get_db)):
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid date format, expected YYYY-MM-DD')

    items = (
        db.query(MediaItem)
        .filter(func.date(MediaItem.created_at) == date, MediaItem.is_deleted == 0)
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
    query = query.filter(MediaItem.is_deleted == 0)
    if name == 'video':
        query = query.filter(MediaItem.media_type == 'video')
    elif name != 'all':
        query = query.filter(MediaItem.source_type == name)

    items = query.order_by(MediaItem.created_at.desc()).all()
    return [media_item_to_dict(item) for item in items]


@app.get('/api/locations')
def get_locations(db: Session = Depends(get_db)):
    items = _query_mappable_media_items(db)

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
    target = _normalize_location_key_for_match(key)
    if not target:
        raise HTTPException(status_code=400, detail='Missing location key')

    # 与 /api/locations 使用完全一致的数据口径（仅统计可上地图的媒体）。
    items = _query_mappable_media_items(db)
    filtered = []
    for item in items:
        _, location_key = normalize_location_name(item.location_name)
        if _normalize_location_key_for_match(location_key) == target:
            filtered.append(media_item_to_dict(item))
    return filtered


@app.get('/api/stats/busy-days')
def get_busy_days(
    order: str = 'asc',
    min_count: int | None = None,
    limit: int = 200,
    only_camera: bool = False,
    db: Session = Depends(get_db),
):
    normalized_order = 'desc' if (order or '').lower() == 'desc' else 'asc'
    safe_limit = max(1, min(int(limit), 2000))
    abs_floor = max(1, int(min_count)) if min_count is not None else 30

    grouped_query = db.query(
        func.date(MediaItem.created_at).label('date_key'),
        func.count(MediaItem.id).label('count'),
    ).filter(MediaItem.is_deleted == 0)
    if only_camera:
        grouped_query = grouped_query.filter(MediaItem.source_type == 'camera')

    day_rows = grouped_query.group_by(func.date(MediaItem.created_at)).all()
    day_counts = [int(row.count or 0) for row in day_rows]
    sorted_counts = sorted(day_counts)

    median = _percentile(sorted_counts, 0.5)
    q1 = _percentile(sorted_counts, 0.25)
    q3 = _percentile(sorted_counts, 0.75)
    iqr = max(0.0, q3 - q1)
    relative_threshold = max(float(abs_floor), median * 2.5)
    outlier_threshold = max(float(abs_floor), q3 + 1.5 * iqr)

    busy_rows = []
    for row in day_rows:
        count = int(row.count or 0)
        if count < abs_floor:
            continue
        if count >= relative_threshold or count >= outlier_threshold:
            busy_rows.append({'date_key': str(row.date_key), 'count': count})

    if not busy_rows:
        return {
            'items': [],
            'meta': {
                'order': normalized_order,
                'count': 0,
                'only_camera': only_camera,
                'thresholds': {
                    'abs_floor': abs_floor,
                    'median': round(median, 2),
                    'q1': round(q1, 2),
                    'q3': round(q3, 2),
                    'iqr': round(iqr, 2),
                    'relative': round(relative_threshold, 2),
                    'outlier': round(outlier_threshold, 2),
                },
            },
        }

    busy_date_set = {row['date_key'] for row in busy_rows}
    media_query = db.query(
        MediaItem.created_at,
        MediaItem.location_name,
        MediaItem.id,
        MediaItem.thumbnail_path,
        MediaItem.media_type,
    ).filter(func.date(MediaItem.created_at).in_(busy_date_set), MediaItem.is_deleted == 0)
    if only_camera:
        media_query = media_query.filter(MediaItem.source_type == 'camera')

    media_rows = media_query.order_by(MediaItem.created_at.desc()).all()
    location_counter_by_date = {}
    preview_candidates_by_date = {}
    for row in media_rows:
        date_key = row.created_at.date().isoformat()
        city, key = normalize_location_name(row.location_name)
        # 与 Timeline 行为保持一致：只用可归一化出的地点参与“主地点”评选。
        # 无定位信息的素材不应把当天主地点“挤掉”。
        if not city or not key:
            pass
        else:
            if date_key not in location_counter_by_date:
                location_counter_by_date[date_key] = {}

            bucket = location_counter_by_date[date_key]
            if key not in bucket:
                bucket[key] = {'location_key': key, 'location_city': city, 'count': 0}
            bucket[key]['count'] += 1

        preview_bucket = preview_candidates_by_date.setdefault(date_key, [])
        preview_bucket.append(
            {
                'id': row.id,
                'thumbnail_path': row.thumbnail_path,
                'media_type': row.media_type,
            }
        )

    items = []
    for row in busy_rows:
        date_key = row['date_key']
        date_locations = location_counter_by_date.get(date_key, {})
        if date_locations:
            top_location = sorted(
                date_locations.values(),
                key=lambda x: (-x['count'], x['location_city']),
            )[0]
        else:
            top_location = {'location_key': None, 'location_city': None, 'count': 0}

        count = row['count']
        score = max(
            (count / relative_threshold) if relative_threshold > 0 else 0,
            (count / outlier_threshold) if outlier_threshold > 0 else 0,
        )
        items.append(
            {
                'date_key': date_key,
                'year': int(date_key.split('-')[0]),
                'count': count,
                'top_location_key': top_location['location_key'],
                'top_location_city': top_location['location_city'],
                'top_location_count': top_location['count'],
                'preview_items': _sample_items_by_range(
                    preview_candidates_by_date.get(date_key, []),
                    5,
                ),
                'score': round(score, 3),
            }
        )

    items.sort(key=lambda x: x['date_key'], reverse=(normalized_order == 'desc'))
    items = items[:safe_limit]

    return {
        'items': items,
        'meta': {
            'order': normalized_order,
            'count': len(items),
            'only_camera': only_camera,
            'thresholds': {
                'abs_floor': abs_floor,
                'median': round(median, 2),
                'q1': round(q1, 2),
                'q3': round(q3, 2),
                'iqr': round(iqr, 2),
                'relative': round(relative_threshold, 2),
                'outlier': round(outlier_threshold, 2),
            },
        },
    }


@app.get('/api/media/image/{item_id}')
async def get_image(item_id: str, request: Request):
    db = SessionLocal()
    try:
        item = db.query(MediaItem).filter(MediaItem.id == item_id).first()
        if item and int(item.is_deleted or 0) == 1:
            item = None
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

    return FileResponse(
        path=file_path,
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
        if item and int(item.is_deleted or 0) == 1:
            item = None
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
