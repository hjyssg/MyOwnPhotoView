import json
import re
from functools import lru_cache
from pathlib import Path


ALIAS_PATH = Path('backend/data/location_alias_zh.json')
LOCATION_ZH_MAP_PATH = Path('backend/data/location_zh_map.json')


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


@lru_cache(maxsize=1)
def _load_location_zh_map() -> dict:
    try:
        if LOCATION_ZH_MAP_PATH.exists():
            data = json.loads(LOCATION_ZH_MAP_PATH.read_text(encoding='utf-8'))
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


def _normalize_lookup_key(value: str | None) -> str:
    if not value:
        return ''
    # 保留中文，英文与数字统一小写并去除常见分隔符/标点
    return re.sub(r"[^\w\u4e00-\u9fff]+", '', value.strip().lower())


@lru_cache(maxsize=1)
def _build_location_lookup() -> list[tuple[str, str]]:
    """
    基于 location_zh_map 构建 “归一化别名 -> 标准中文地名” 映射，
    返回按 key 长度降序的列表，便于做最长匹配避免短词误匹配。
    """
    raw_map = _load_location_zh_map()
    alias_to_city: dict[str, str] = {}

    for section in ('city', 'admin1', 'country'):
        section_data = raw_map.get(section, {})
        if not isinstance(section_data, dict):
            continue

        for en_name, zh_name in section_data.items():
            if not isinstance(en_name, str) or not isinstance(zh_name, str):
                continue

            canonical_city = _strip_cn_suffix(zh_name.strip())
            if not canonical_city:
                continue

            for candidate in {en_name, zh_name, canonical_city}:
                k = _normalize_lookup_key(candidate)
                if k:
                    alias_to_city[k] = canonical_city

    # 长 key 优先，减少 "us" 命中 "russia" 这类误匹配
    return sorted(alias_to_city.items(), key=lambda kv: len(kv[0]), reverse=True)


def normalize_location_name(location_name: str | None) -> tuple[str | None, str | None]:
    if not location_name:
        return None, None

    raw = location_name.strip()
    if not raw:
        return None, None

    # 1) 优先使用 location_zh_map 归一化（用于首页地点聚合）
    normalized_raw = _normalize_lookup_key(raw)
    for alias_key, canonical_city in _build_location_lookup():
        if not alias_key:
            continue
        # 拉丁短词容易误命中，仅允许较长 token 做子串匹配；中文至少 2 字
        is_chinese_key = re.search(r'[\u4e00-\u9fff]', alias_key) is not None
        min_len = 2 if is_chinese_key else 4
        if len(alias_key) < min_len:
            continue
        if alias_key in normalized_raw:
            return canonical_city, _to_location_key(canonical_city)

    lower_raw = raw.lower()
    alias_map = _load_alias_map()
    for city, aliases in alias_map.items():
        if city.lower() in lower_raw:
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
