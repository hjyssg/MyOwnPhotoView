import os

SCAN_FOLDERS_CONFIG_PATH = 'backend/data/scan_folders.json'
APP_SETTINGS_CONFIG_PATH = 'backend/data/app_settings.json'

DEFAULT_APP_SETTINGS = {
    'auto_scan_on_startup': False,
    'scan_mode': 'incremental',
}

THUMBNAIL_DIR = os.path.join('backend', 'cache', 'thumbnails')
MEDIA_DIR = os.path.join('backend', 'media')
