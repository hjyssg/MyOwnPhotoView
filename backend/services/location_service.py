from sqlalchemy.orm import Session

from backend.location_normalizer import media_item_to_dict, normalize_location_name
from backend.services.media_service import query_mappable_media_items


def normalize_location_key_for_match(location_key: str | None) -> str:
    return (location_key or '').strip().lower()


def get_locations_payload(db: Session) -> list[dict]:
    items = query_mappable_media_items(db)

    groups = {}
    for item in items:
        location_city, location_key = normalize_location_name(item.location_name)
        if not location_key:
            continue

        if location_key not in groups:
            groups[location_key] = {
                'location_key': location_key,
                'location_city': location_city,
                'count': 0,
                'sum_lat': 0.0,
                'sum_lon': 0.0,
                'cover_id': item.id,
            }

        groups[location_key]['count'] += 1
        groups[location_key]['sum_lat'] += float(item.latitude)
        groups[location_key]['sum_lon'] += float(item.longitude)

    result = []
    for _, g in groups.items():
        if g['count'] == 0:
            continue
        result.append(
            {
                'location_key': g['location_key'],
                'location_city': g['location_city'],
                'count': g['count'],
                'center_latitude': g['sum_lat'] / g['count'],
                'center_longitude': g['sum_lon'] / g['count'],
                'cover_id': g['cover_id'],
            }
        )

    result.sort(key=lambda x: x['count'], reverse=True)
    return result


def get_media_by_location_payload(db: Session, key: str) -> list[dict]:
    target = normalize_location_key_for_match(key)
    items = query_mappable_media_items(db)
    filtered = []
    for item in items:
        _, location_key = normalize_location_name(item.location_name)
        if normalize_location_key_for_match(location_key) == target:
            filtered.append(media_item_to_dict(item))
    return filtered
