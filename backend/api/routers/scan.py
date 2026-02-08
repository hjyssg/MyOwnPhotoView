import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db
from backend.database import MediaItem
from backend.services.scan_service import (
    can_start_scan,
    clear_thumbnail_cache_dir,
    cleanup_unused_thumbnails,
    hard_delete_soft_deleted_items,
    reset_scan_state_to_idle,
    start_scan_all_thread,
    start_scan_thread,
)
from backend.services.scan_state import get_scan_state_copy, scan_lock, scan_state
from backend.services.settings_service import load_scan_folders_config, should_force_rescan

router = APIRouter()


@router.post('/api/scan')
def scan_media_endpoint(directory: str, force_rescan: bool | None = None):
    requested_path = os.path.abspath(directory)
    if not os.path.isdir(requested_path):
        raise HTTPException(status_code=404, detail=f'Directory does not exist: {requested_path}')

    can_start, payload = can_start_scan()
    if not can_start:
        return payload

    start_scan_thread(requested_path, should_force_rescan(force_rescan))
    return {'status': 'started', 'message': 'Scan started in background', 'directory': requested_path}


@router.get('/api/scan/status')
def scan_status_endpoint():
    return get_scan_state_copy()


@router.post('/api/scan/all')
def scan_all_media_endpoint(force_rescan: bool | None = None):
    folders = load_scan_folders_config()
    existing = [p for p in folders if os.path.isdir(p)]
    if not existing:
        raise HTTPException(status_code=400, detail='No valid scan folders configured')

    can_start, payload = can_start_scan()
    if not can_start:
        return payload

    start_scan_all_thread(existing, should_force_rescan(force_rescan))
    return {'status': 'started', 'message': 'Scan-all started in background', 'directories': existing}


@router.post('/api/scan/reset')
def reset_scan_data_endpoint(db: Session = Depends(get_db)):
    with scan_lock:
        if scan_state['is_running']:
            raise HTTPException(status_code=409, detail='Scan is running, cannot reset now')

    deleted = db.query(MediaItem).delete()
    db.commit()
    removed_thumbnails = clear_thumbnail_cache_dir()
    reset_scan_state_to_idle()

    return {
        'status': 'ok',
        'deleted_media_items': int(deleted or 0),
        'deleted_thumbnails': removed_thumbnails,
    }


@router.post('/api/maintenance/purge-soft-deleted')
def purge_soft_deleted_endpoint(db: Session = Depends(get_db)):
    with scan_lock:
        if scan_state['is_running']:
            raise HTTPException(status_code=409, detail='Scan is running, cannot purge now')
    result = hard_delete_soft_deleted_items(db)
    return {'status': 'ok', **result}


@router.post('/api/thumbnails/cleanup-unused')
def cleanup_unused_thumbnails_endpoint(db: Session = Depends(get_db)):
    with scan_lock:
        if scan_state['is_running']:
            raise HTTPException(status_code=409, detail='Scan is running, cannot cleanup now')
    result = cleanup_unused_thumbnails(db)
    return {'status': 'ok', **result}
