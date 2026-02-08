import json
import os

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.core.config import APP_SETTINGS_CONFIG_PATH, DEFAULT_APP_SETTINGS, SCAN_FOLDERS_CONFIG_PATH
from backend.database import MediaItem


def normalize_folder_paths(paths: list[str]) -> list[str]:
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


def load_scan_folders_config() -> list[str]:
    if not os.path.exists(SCAN_FOLDERS_CONFIG_PATH):
        return []
    try:
        with open(SCAN_FOLDERS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        folders = data.get('folders', []) if isinstance(data, dict) else []
        if not isinstance(folders, list):
            return []
        return normalize_folder_paths([str(v) for v in folders])
    except Exception:
        return []


def save_scan_folders_config(folders: list[str]):
    os.makedirs(os.path.dirname(SCAN_FOLDERS_CONFIG_PATH), exist_ok=True)
    with open(SCAN_FOLDERS_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump({'folders': folders}, f, ensure_ascii=False, indent=2)


def normalize_scan_mode(value: str | None) -> str:
    mode = (value or '').strip().lower()
    return 'force' if mode == 'force' else 'incremental'


def load_app_settings() -> dict:
    settings = dict(DEFAULT_APP_SETTINGS)
    if not os.path.exists(APP_SETTINGS_CONFIG_PATH):
        return settings

    try:
        with open(APP_SETTINGS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            settings['auto_scan_on_startup'] = bool(data.get('auto_scan_on_startup', settings['auto_scan_on_startup']))
            settings['scan_mode'] = normalize_scan_mode(data.get('scan_mode'))
    except Exception:
        pass
    return settings


def save_app_settings(settings: dict):
    os.makedirs(os.path.dirname(APP_SETTINGS_CONFIG_PATH), exist_ok=True)
    payload = {
        'auto_scan_on_startup': bool(settings.get('auto_scan_on_startup', False)),
        'scan_mode': normalize_scan_mode(settings.get('scan_mode')),
    }
    with open(APP_SETTINGS_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def should_force_rescan(force_rescan: bool | None = None) -> bool:
    if force_rescan is not None:
        return bool(force_rescan)
    settings = load_app_settings()
    return settings.get('scan_mode') == 'force'


def get_folder_scan_stats(db: Session, folder: str) -> tuple[bool, int]:
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
