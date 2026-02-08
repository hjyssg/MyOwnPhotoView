import datetime
import os

from sqlalchemy.orm import Session

from backend.database import MediaItem
from backend.location_normalizer import media_item_to_dict
from backend.services.scan_service import cleanup_thumbnail_if_unused

try:
    from send2trash import send2trash
except Exception:  # pragma: no cover
    send2trash = None


def get_active_media_items(db: Session) -> list[MediaItem]:
    return db.query(MediaItem).filter(MediaItem.is_deleted == 0).order_by(MediaItem.created_at.desc()).all()


def get_active_media_dicts(db: Session) -> list[dict]:
    return [media_item_to_dict(item) for item in get_active_media_items(db)]


def get_media_item_or_none(db: Session, item_id: str) -> MediaItem | None:
    item = db.query(MediaItem).filter(MediaItem.id == item_id).first()
    if item and int(item.is_deleted or 0) == 1:
        return None
    return item


def trash_media_item_by_id(db: Session, item_id: str) -> dict:
    if send2trash is None:
        raise RuntimeError('send2trash is not installed on server')

    item = db.query(MediaItem).filter(MediaItem.id == item_id).first()
    if not item or int(item.is_deleted or 0) == 1:
        raise FileNotFoundError('Media item not found')

    file_path = item.filepath
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError('File not found')

    send2trash(file_path)

    now = datetime.datetime.utcnow()
    item.is_deleted = 1
    item.deleted_at = now
    db.commit()

    thumbnail_removed = False
    if item.media_type == 'video':
        thumbnail_removed = cleanup_thumbnail_if_unused(db, item.thumbnail_path)

    return {
        'status': 'ok',
        'id': item.id,
        'trashed': True,
        'thumbnail_removed': bool(thumbnail_removed),
    }


def query_mappable_media_items(db: Session) -> list[MediaItem]:
    return (
        db.query(MediaItem)
        .filter(MediaItem.latitude.isnot(None), MediaItem.longitude.isnot(None), MediaItem.is_deleted == 0)
        .order_by(MediaItem.created_at.desc())
        .all()
    )
