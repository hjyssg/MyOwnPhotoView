import sys
from pathlib import Path


def _is_frozen() -> bool:
    return bool(getattr(sys, 'frozen', False))


def _get_runtime_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _get_bundle_root(runtime_root: Path) -> Path:
    if _is_frozen() and hasattr(sys, '_MEIPASS'):
        return Path(getattr(sys, '_MEIPASS'))
    return runtime_root


APP_RUNTIME_ROOT = _get_runtime_root()
APP_BUNDLE_ROOT = _get_bundle_root(APP_RUNTIME_ROOT)

SCAN_FOLDERS_CONFIG_PATH = str(APP_RUNTIME_ROOT / 'backend' / 'data' / 'scan_folders.json')
APP_SETTINGS_CONFIG_PATH = str(APP_RUNTIME_ROOT / 'backend' / 'data' / 'app_settings.json')

DEFAULT_APP_SETTINGS = {
    'auto_scan_on_startup': False,
    'scan_mode': 'incremental',
}

THUMBNAIL_DIR = str(APP_RUNTIME_ROOT / 'backend' / 'cache' / 'thumbnails')
MEDIA_DIR = str(APP_RUNTIME_ROOT / 'backend' / 'media')
