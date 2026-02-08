import os

from backend.api.routers.locations import router as locations_router
from backend.api.routers.media import router as media_router
from backend.api.routers.network import router as network_router
from backend.api.routers.scan import router as scan_router
from backend.api.routers.settings import router as settings_router
from backend.api.routers.stats import router as stats_router
from backend.core.app_factory import create_app
from backend.database import SessionLocal, create_db_and_tables
from backend.services.scan_service import can_start_scan, soft_delete_outside_scan_folders, start_scan_all_thread
from backend.services.settings_service import load_app_settings, load_scan_folders_config, should_force_rescan

app = create_app()
app.include_router(network_router)
app.include_router(settings_router)
app.include_router(scan_router)
app.include_router(media_router)
app.include_router(locations_router)
app.include_router(stats_router)


@app.on_event('startup')
def on_startup():
    create_db_and_tables()

    folders = load_scan_folders_config()
    db = SessionLocal()
    try:
        soft_delete_outside_scan_folders(db, folders)
    finally:
        db.close()

    settings = load_app_settings()
    if not settings.get('auto_scan_on_startup'):
        return

    existing = [p for p in folders if os.path.isdir(p)]
    if not existing:
        return

    can_start, _ = can_start_scan()
    if not can_start:
        return

    start_scan_all_thread(existing, should_force_rescan())


@app.get('/')
def read_root():
    return {'message': 'Welcome to Local Smart Gallery'}
