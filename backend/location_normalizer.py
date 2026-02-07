import json
import re
from functools import lru_cache
from pathlib import Path


ALIAS_PATH = Path('backend/data/location_alias_zh.json')


@lru_cache(maxsize=1)
def _load_alias_map() -> dict:
    try:
        if ALIAS_PATH.exists():
            data = json.loads(ALIAS_PATH.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _strip_cn_suffix(name: str) -> str:
    if not name:
        return name
    suffixes = [
        '特别行政区',
        '自治州',
        '地区',
        '省',
        '市',
        '区',
        '县',
    ]
    for suffix in suffixes:
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)]
    return name


def _to_location_key(city: str | None) -> str | None:
    if not city:
        return None
    key = city.strip().lower()
    key = re.sub(r'[\s_\-]+', '', key)
    return key or None


def normalize_location_name(location_name: str | None) -> tuple[str | None, str | None]:
    if not location_name:
        return None, None

    raw = location_name.strip()
    if not raw:
        return None, None

    lower_raw = raw.lower()
    alias_map = _load_alias_map()
    for city, aliases in alias_map.items():
        if city in raw:
            return city, _to_location_key(city)
        for alias in aliases:
            if alias.lower() in lower_raw:
                return city, _to_location_key(city)

    chinese_parts = re.findall(r'[\u4e00-\u9fff]{2,}', raw)
    if chinese_parts:
        city = _strip_cn_suffix(chinese_parts[-1])
        return city, _to_location_key(city)

    parts = [p for p in re.split(r'[\s,|/\-]+', raw) if p]
    if not parts:
        return None, None

    city = parts[-1]
    city = re.sub(r'(?i)\b(city|shi|province|prefecture)\b', '', city).strip()
    if not city:
        city = parts[-1]
    city = city.title()
    return city, _to_location_key(city)


def media_item_to_dict(item) -> dict:
    location_city, location_key = normalize_location_name(item.location_name)
    return {
        'id': item.id,
        'filepath': item.filepath,
        'media_type': item.media_type,
        'created_at': item.created_at,
        'duration': item.duration,
        'thumbnail_path': item.thumbnail_path,
        'latitude': item.latitude,
        'longitude': item.longitude,
        'source_type': item.source_type,
        'location_name': item.location_name,
        'location_city': location_city,
        'location_key': location_key,
        'mtime': item.mtime,
        'size': item.size,
    }
