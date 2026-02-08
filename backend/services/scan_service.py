import datetime
import os
import shutil
import threading

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.config import THUMBNAIL_DIR
from backend.database import MediaItem, SessionLocal
from backend.scanner import scan_directory
from backend.services.scan_state import now_iso, scan_lock, scan_state, update_scan_state


def run_scan_job(directory: str, force_rescan: bool = False):
    update_scan_state(
        is_running=True,
        directory=directory,
        current_folder=directory,
        current_file=None,
        processed_files=0,
        total_files=0,
        current_folder_index=1,
        total_folders=1,
        stats=None,
        started_at=now_iso(),
        finished_at=None,
        message='running',
        error=None,
    )

    db = SessionLocal()
    try:
        def on_progress(payload: dict):
            update_scan_state(current_folder=directory, **payload)

        stats = scan_directory(directory, db, force_rescan=force_rescan, progress_callback=on_progress)
        update_scan_state(
            is_running=False,
            current_file=None,
            finished_at=now_iso(),
            message='completed',
            stats=stats,
        )
    except Exception as e:
        update_scan_state(
            is_running=False,
            current_file=None,
            finished_at=now_iso(),
            message='failed',
            error=str(e),
        )
    finally:
        db.close()


def run_scan_all_job(directories: list[str], force_rescan: bool = False):
    total = len(directories)
    update_scan_state(
        is_running=True,
        directory=f'multi ({total})',
        current_folder=None,
        current_file=None,
        processed_files=0,
        total_files=0,
        current_folder_index=0,
        total_folders=total,
        stats=None,
        started_at=now_iso(),
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
                update_scan_state(
                    current_folder=_directory,
                    current_folder_index=_idx,
                    total_folders=total,
                    **payload,
                )

            stats = scan_directory(directory, db, force_rescan=force_rescan, progress_callback=on_progress)
            for key in summary.keys():
                summary[key] += int(stats.get(key, 0))

        update_scan_state(
            is_running=False,
            current_file=None,
            finished_at=now_iso(),
            message='completed',
            stats=summary,
        )
    except Exception as e:
        update_scan_state(
            is_running=False,
            current_file=None,
            finished_at=now_iso(),
            message='failed',
            error=str(e),
        )
    finally:
        db.close()


def can_start_scan() -> tuple[bool, dict | None]:
    with scan_lock:
        if scan_state['is_running']:
            return False, {
                'status': 'running',
                'message': 'A scan job is already running',
                'directory': scan_state['directory'],
            }
    return True, None


def start_scan_thread(directory: str, force_rescan: bool):
    worker = threading.Thread(target=run_scan_job, args=(directory, force_rescan), daemon=True)
    worker.start()


def start_scan_all_thread(directories: list[str], force_rescan: bool):
    worker = threading.Thread(target=run_scan_all_job, args=(directories, force_rescan), daemon=True)
    worker.start()


def is_under_any_scan_folder(filepath: str, folders: list[str]) -> bool:
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


def soft_delete_outside_scan_folders(db: Session, folders: list[str]) -> int:
    now = datetime.datetime.utcnow()
    changed = 0
    items = db.query(MediaItem).all()
    for item in items:
        if is_under_any_scan_folder(item.filepath, folders):
            continue
        if int(item.is_deleted or 0) == 1:
            continue
        item.is_deleted = 1
        item.deleted_at = now
        changed += 1
    if changed > 0:
        db.commit()
    return changed


def delete_thumbnail_file_by_relpath(relpath: str) -> bool:
    if not relpath:
        return False
    thumb_name = os.path.basename(relpath)
    thumb_path = os.path.join(THUMBNAIL_DIR, thumb_name)
    if not os.path.isfile(thumb_path):
        return False
    try:
        os.remove(thumb_path)
        return True
    except Exception:
        return False


def cleanup_thumbnail_if_unused(db: Session, relpath: str | None) -> bool:
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
    return delete_thumbnail_file_by_relpath(relpath)


def hard_delete_soft_deleted_items(db: Session) -> dict:
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
        if int(refs) == 0 and delete_thumbnail_file_by_relpath(relpath):
            deleted_thumbnails += 1

    return {'deleted_media_items': deleted_media_items, 'deleted_thumbnails': deleted_thumbnails}


def cleanup_unused_thumbnails(db: Session) -> dict:
    if not os.path.isdir(THUMBNAIL_DIR):
        return {'deleted_thumbnails': 0, 'kept_thumbnails': 0}

    referenced_rows = db.query(MediaItem.thumbnail_path).filter(MediaItem.thumbnail_path.isnot(None)).all()
    referenced_names = {os.path.basename(row[0]) for row in referenced_rows if row and row[0]}

    deleted_thumbnails = 0
    kept_thumbnails = 0
    for name in os.listdir(THUMBNAIL_DIR):
        file_path = os.path.join(THUMBNAIL_DIR, name)
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

    return {'deleted_thumbnails': deleted_thumbnails, 'kept_thumbnails': kept_thumbnails}


def reset_scan_state_to_idle():
    update_scan_state(
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
        finished_at=now_iso(),
        message='idle',
        error=None,
    )


def clear_thumbnail_cache_dir() -> int:
    removed_thumbnails = 0
    if os.path.isdir(THUMBNAIL_DIR):
        for name in os.listdir(THUMBNAIL_DIR):
            file_path = os.path.join(THUMBNAIL_DIR, name)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    removed_thumbnails += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path, ignore_errors=True)
            except Exception:
                pass
    return removed_thumbnails
