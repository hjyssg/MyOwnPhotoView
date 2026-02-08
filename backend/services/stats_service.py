from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import MediaItem
from backend.location_normalizer import normalize_location_name


def sample_items_by_range(items: list[dict], sample_count: int) -> list[dict]:
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


def get_busy_days_payload(
    db: Session,
    order: str = 'asc',
    min_count: int | None = None,
    limit: int = 200,
    only_camera: bool = False,
):
    normalized_order = 'desc' if (order or '').lower() == 'desc' else 'asc'
    safe_limit = max(1, min(int(limit), 2000))
    abs_floor = max(1, int(min_count)) if min_count is not None else 300

    grouped_query = db.query(
        func.date(MediaItem.created_at).label('date_key'),
        func.count(MediaItem.id).label('count'),
    ).filter(MediaItem.is_deleted == 0)
    if only_camera:
        grouped_query = grouped_query.filter(MediaItem.source_type == 'camera')

    day_rows = grouped_query.group_by(func.date(MediaItem.created_at)).all()

    busy_rows = []
    for row in day_rows:
        count = int(row.count or 0)
        if count >= abs_floor:
            busy_rows.append({'date_key': str(row.date_key), 'count': count})

    if not busy_rows:
        return {
            'items': [],
            'meta': {
                'order': normalized_order,
                'count': 0,
                'only_camera': only_camera,
                'min_count': abs_floor,
            },
        }

    busy_date_set = {row['date_key'] for row in busy_rows}
    media_query = db.query(
        MediaItem.created_at,
        MediaItem.location_name,
        MediaItem.id,
        MediaItem.filepath,
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
        if city and key:
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
                'filepath': row.filepath,
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
        score = (count / abs_floor) if abs_floor > 0 else 0
        items.append(
            {
                'date_key': date_key,
                'year': int(date_key.split('-')[0]),
                'count': count,
                'top_location_key': top_location['location_key'],
                'top_location_city': top_location['location_city'],
                'top_location_count': top_location['count'],
                'preview_items': sample_items_by_range(preview_candidates_by_date.get(date_key, []), 5),
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
            'min_count': abs_floor,
        },
    }
