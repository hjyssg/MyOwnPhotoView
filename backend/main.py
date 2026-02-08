import os
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
import uvicorn
from backend.api.routers.locations import router as locations_router
from backend.api.routers.media import router as media_router
from backend.api.routers.network import router as network_router
from backend.api.routers.scan import router as scan_router
from backend.api.routers.settings import router as settings_router
from backend.api.routers.stats import router as stats_router
from backend.core.app_factory import create_app
from backend.core.config import APP_BUNDLE_ROOT
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

FRONTEND_BUILD_DIR = Path(APP_BUNDLE_ROOT) / 'frontend' / 'build'


def _frontend_index_exists() -> bool:
    return (FRONTEND_BUILD_DIR / 'index.html').exists()


def _safe_frontend_path(relative_path: str) -> Path | None:
    if not relative_path:
        return None
    candidate = (FRONTEND_BUILD_DIR / relative_path).resolve()
    root = FRONTEND_BUILD_DIR.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _serve_frontend_index():
    index_file = FRONTEND_BUILD_DIR / 'index.html'
    if index_file.exists():
        return FileResponse(index_file)
    return {'message': 'Welcome to Local Smart Gallery'}


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
    return _serve_frontend_index()


@app.get('/{full_path:path}')
def frontend_spa_fallback(full_path: str):
    if full_path.startswith(('api/', 'thumbnails/', 'media/')):
        raise HTTPException(status_code=404, detail='Not Found')

    file_path = _safe_frontend_path(full_path)
    if file_path and file_path.is_file():
        return FileResponse(file_path)

    if _frontend_index_exists():
        return FileResponse(FRONTEND_BUILD_DIR / 'index.html')

    raise HTTPException(status_code=404, detail='Not Found')


def main():
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '8000'))
    uvicorn.run(app, host=host, port=port)


if __name__ == '__main__':
    main()
