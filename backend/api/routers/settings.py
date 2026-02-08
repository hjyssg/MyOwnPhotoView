from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db
from backend.schemas.settings import AppSettingsPayload, ScanFoldersPayload
from backend.services.scan_service import soft_delete_outside_scan_folders
from backend.services.settings_service import (
    get_folder_scan_stats,
    load_app_settings,
    load_scan_folders_config,
    normalize_folder_paths,
    normalize_scan_mode,
    save_app_settings,
    save_scan_folders_config,
)

router = APIRouter()


@router.get('/api/scan/folders')
def get_scan_folders_endpoint(db: Session = Depends(get_db)):
    folders = load_scan_folders_config()
    items = []
    for folder in folders:
        has_scanned, scanned_count = get_folder_scan_stats(db, folder)
        items.append({'path': folder, 'has_scanned': has_scanned, 'scanned_count': scanned_count})
    return {'folders': folders, 'items': items}


@router.put('/api/scan/folders')
def save_scan_folders_endpoint(payload: ScanFoldersPayload, db: Session = Depends(get_db)):
    folders = normalize_folder_paths(payload.folders)
    save_scan_folders_config(folders)
    soft_deleted_count = soft_delete_outside_scan_folders(db, folders)
    return {'folders': folders, 'soft_deleted_count': int(soft_deleted_count)}


@router.get('/api/settings')
def get_app_settings_endpoint():
    return load_app_settings()


@router.put('/api/settings')
def save_app_settings_endpoint(payload: AppSettingsPayload):
    normalized = {
        'auto_scan_on_startup': payload.auto_scan_on_startup,
        'scan_mode': normalize_scan_mode(payload.scan_mode),
    }
    save_app_settings(normalized)
    return normalized
