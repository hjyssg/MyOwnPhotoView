import os
import datetime
import hashlib
import subprocess
import re
import logging
from pathlib import Path
from functools import lru_cache
from typing import Callable

from sqlalchemy import or_
from sqlalchemy.orm import Session
from PIL import Image, ImageOps
from backend.core.config import APP_BUNDLE_ROOT, THUMBNAIL_DIR
from backend.database import MediaItem, SessionLocal
import json
import piexif
import reverse_geocoder as rg

try:
    import xxhash
except ImportError:  # pragma: no cover
    xxhash = None

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.heic']
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi']
THUMBNAIL_DIR = Path(THUMBNAIL_DIR)
COMMIT_EVERY = 300
logger = logging.getLogger(__name__)


def get_decimal_from_dms(dms, ref):
    if not dms or not ref:
        return None
    degrees = dms[0][0] / dms[0][1]
    minutes = dms[1][0] / dms[1][1] / 60.0
    seconds = dms[2][0] / dms[2][1] / 3600.0

    decimal = degrees + minutes + seconds
    if ref in [b'S', b'W', 'S', 'W']:
        decimal = -decimal
    return decimal


def _is_valid_coordinate(lat, lon):
    if lat is None or lon is None:
        return False
    if lat == 0 and lon == 0:
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180


CN_MAP_PATH = Path(APP_BUNDLE_ROOT) / 'backend' / 'data' / 'location_zh_map.json'


@lru_cache(maxsize=1)
def _load_cn_map():
    try:
        if CN_MAP_PATH.exists():
            return json.loads(CN_MAP_PATH.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {
        'country': {},
        'admin1': {},
        'city': {},
    }


@lru_cache(maxsize=10000)
def reverse_geocode_location(lat, lon):
    if not _is_valid_coordinate(lat, lon):
        return None

    try:
        result = rg.search([(lat, lon)], mode=1)
        if not result:
            return None

        place = result[0]
        cn_map = _load_cn_map()

        country = place.get('cc') or place.get('country') or ''
        admin1 = place.get('admin1', '')
        city = place.get('name', '')

        country_cn = cn_map.get('country', {}).get(country, country)
        admin1_cn = cn_map.get('admin1', {}).get(admin1, admin1)
        city_cn = cn_map.get('city', {}).get(city, city)

        parts = [p for p in [country_cn, admin1_cn, city_cn] if p]
        return ' '.join(parts) if parts else None
    except Exception:
        return None


def _run_command(command):
    try:
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
            encoding='utf-8',
            errors='ignore',
        )
    except FileNotFoundError:
        return None


def create_video_thumbnail(video_path: Path, thumbnail_path: Path):
    def _thumbnail_ready() -> bool:
        return thumbnail_path.exists() and thumbnail_path.stat().st_size > 0

    # 先按帧抓图：短视频优先第2帧，其次第1帧
    attempts = [
        [
            'ffmpeg',
            '-y',
            '-i',
            str(video_path),
            '-vf',
            'select=eq(n\\,1)',
            '-vframes',
            '1',
            str(thumbnail_path),
        ],
        [
            'ffmpeg',
            '-y',
            '-i',
            str(video_path),
            '-vf',
            'select=eq(n\\,0)',
            '-vframes',
            '1',
            str(thumbnail_path),
        ],
        [
            'ffmpeg',
            '-y',
            '-ss',
            '00:00:00',
            '-i',
            str(video_path),
            '-frames:v',
            '1',
            str(thumbnail_path),
        ],
    ]

    last_err = ''
    for command in attempts:
        result = _run_command(command)
        if result is None:
            last_err = 'ffmpeg not found'
            break

        if _thumbnail_ready():
            return

        if result.stderr:
            last_err = result.stderr.strip()

    logger.error(
        'Failed to generate video thumbnail. video_path=%s thumbnail_path=%s last_err=%s',
        str(video_path),
        str(thumbnail_path),
        (last_err[:500] if last_err else 'unknown error'),
    )


def get_video_duration(video_path: Path) -> int:
    command = [
        'ffprobe',
        '-v',
        'error',
        '-show_entries',
        'format=duration',
        '-of',
        'default=nokey=1:noprint_wrappers=1',
        str(video_path),
    ]
    result = _run_command(command)
    if result is None or result.returncode != 0:
        return 0
    try:
        duration = float(result.stdout.strip())
        return max(1, int(duration))
    except Exception:
        return 0


def _is_under_directory(path: str, directory: str) -> bool:
    try:
        common = os.path.commonpath([os.path.abspath(path), directory])
        return common == directory
    except Exception:
        return False


def _hash_file_content(filepath: Path) -> str:
    if xxhash is not None:
        hasher = xxhash.xxh64()
    else:
        hasher = hashlib.blake2b(digest_size=16)

    with filepath.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def _hash_file_sampled(filepath: Path) -> str:
    """Fast content fingerprint using sampled bytes (head/middle/tail).

    - Small files (<=3MB): hash full content to keep good uniqueness.
    - Large files: hash only sampled slices to avoid full-file I/O bottleneck.
    """
    sample_size = 64 * 1024
    small_file_threshold = 3 * 1024 * 1024

    if xxhash is not None:
        hasher = xxhash.xxh64()
    else:
        hasher = hashlib.blake2b(digest_size=16)

    try:
        file_size = filepath.stat().st_size
    except Exception:
        return _filename_fingerprint(filepath)

    hasher.update(str(file_size).encode('utf-8'))

    with filepath.open('rb') as f:
        if file_size <= small_file_threshold:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                hasher.update(chunk)
            return hasher.hexdigest()

        # head
        f.seek(0)
        hasher.update(f.read(sample_size))

        # middle
        middle_offset = max(0, (file_size // 2) - (sample_size // 2))
        f.seek(middle_offset)
        hasher.update(f.read(sample_size))

        # tail
        tail_offset = max(0, file_size - sample_size)
        f.seek(tail_offset)
        hasher.update(f.read(sample_size))

    return hasher.hexdigest()


def _filename_fingerprint(filepath: Path) -> str:
    return hashlib.md5(str(filepath.resolve()).encode()).hexdigest()


def _parse_creation_time_from_filename(filepath: Path) -> datetime.datetime | None:
    filename = filepath.stem
    patterns = [
        r'(?<!\d)(\d{4})[-_]?([01]\d)[-_]?([0-3]\d)[T_\- ]?([0-2]\d)[-_:]?([0-5]\d)[-_:]?([0-5]\d)(?!\d)',
        r'(?<!\d)(\d{4})[-_]?([01]\d)[-_]?([0-3]\d)(?!\d)',
    ]
    for p in patterns:
        match = re.search(p, filename)
        if not match:
            continue
        try:
            parts = [int(v) for v in match.groups()]
            if len(parts) == 3:
                y, m, d = parts
                return datetime.datetime(y, m, d)
            if len(parts) == 6:
                y, m, d, hh, mm, ss = parts
                return datetime.datetime(y, m, d, hh, mm, ss)
        except Exception:
            continue
    return None


def _fallback_creation_time(filepath: Path) -> datetime.datetime:
    from_filename = _parse_creation_time_from_filename(filepath)
    if from_filename is not None:
        return from_filename
    try:
        return datetime.datetime.fromtimestamp(filepath.stat().st_ctime)
    except Exception:
        return datetime.datetime.utcnow()


def _extract_exif_info(exif_bytes: bytes):
    if not exif_bytes:
        return None, None, None
    try:
        exif_dict = piexif.load(exif_bytes)
    except Exception:
        return None, None, None

    created_at = None
    date_str = exif_dict.get('0th', {}).get(piexif.ImageIFD.DateTime)
    if date_str:
        try:
            created_at = datetime.datetime.strptime(date_str.decode(), '%Y:%m:%d %H:%M:%S')
        except Exception:
            created_at = None

    lat = None
    lon = None
    gps_tags = exif_dict.get('GPS')
    if gps_tags:
        lat_dms = gps_tags.get(piexif.GPSIFD.GPSLatitude)
        lat_ref = gps_tags.get(piexif.GPSIFD.GPSLatitudeRef)
        lon_dms = gps_tags.get(piexif.GPSIFD.GPSLongitude)
        lon_ref = gps_tags.get(piexif.GPSIFD.GPSLongitudeRef)
        lat = get_decimal_from_dms(lat_dms, lat_ref)
        lon = get_decimal_from_dms(lon_dms, lon_ref)
        if not _is_valid_coordinate(lat, lon):
            lat, lon = None, None

    model = exif_dict.get('0th', {}).get(piexif.ImageIFD.Model)
    return created_at, (lat, lon), model


def _determine_source_type(filepath: Path, model_tag) -> str:
    filename = filepath.name.lower()
    if 'screenshot' in filename or '鎴睆' in filename:
        return 'screenshot'
    if filepath.suffix.lower() == '.png':
        return 'screenshot'
    if model_tag:
        return 'camera'
    return 'web'


def _process_image_file(filepath: Path, thumbnail_path: Path):
    exif_bytes = b''
    with Image.open(filepath) as img_raw:
        exif_bytes = img_raw.info.get('exif', b'')
        img = ImageOps.exif_transpose(img_raw)
        original_mode = img.mode

        if img.mode in ('RGBA', 'LA'):
            rgba = img.convert('RGBA')
            background = Image.new('RGB', rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.split()[-1])
            img = background
        elif img.mode == 'P':
            if 'transparency' in img.info:
                rgba = img.convert('RGBA')
                background = Image.new('RGB', rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.split()[-1])
                img = background
            else:
                img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        img.thumbnail((400, 400))
        img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)

        if original_mode != img.mode:
            logger.debug(
                'Thumbnail mode converted for JPEG save. filepath=%s mode_before=%s mode_after=%s',
                str(filepath),
                original_mode,
                img.mode,
            )

    exif_created_at, gps, model = _extract_exif_info(exif_bytes)
    lat, lon = gps if gps else (None, None)
    created_at = exif_created_at or _fallback_creation_time(filepath)
    loc_name = reverse_geocode_location(lat, lon)
    source_type = _determine_source_type(filepath, model)

    return {
        'created_at': created_at,
        'latitude': lat,
        'longitude': lon,
        'location_name': loc_name,
        'source_type': source_type,
    }


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _remove_thumbnail_file(item: MediaItem, db: Session):
    if not item.thumbnail_path:
        return

    reference_count = (
        db.query(MediaItem)
        .filter(
            MediaItem.thumbnail_path == item.thumbnail_path,
            MediaItem.filepath != item.filepath,
        )
        .count()
    )
    if reference_count > 0:
        return

    thumb = THUMBNAIL_DIR / Path(item.thumbnail_path).name
    if thumb.exists():
        try:
            thumb.unlink()
        except Exception:
            pass


def scan_directory(
    directory: str,
    db: Session,
    force_rescan: bool = False,
    progress_callback: Callable[[dict], None] | None = None,
):
    directory = os.path.abspath(directory)
    print(f'Scanning directory: {directory}')
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

    prefix = directory.rstrip('/\\') + os.sep
    existing_rows = (
        db.query(MediaItem)
        .filter(or_(MediaItem.filepath == directory, MediaItem.filepath.like(f'{prefix}%')))
        .all()
    )
    existing_items = {item.filepath: item for item in existing_rows if _is_under_directory(item.filepath, directory)}

    seen_paths = set()
    added_count = 0
    updated_count = 0
    skipped_count = 0
    dirty_ops = 0

    candidate_files = []
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = Path(root) / filename
            ext = filepath.suffix.lower()
            if ext in SUPPORTED_IMAGE_EXTENSIONS or ext in SUPPORTED_VIDEO_EXTENSIONS:
                candidate_files.append(filepath)

    total_files = len(candidate_files)
    if progress_callback:
        progress_callback(
            {
                'total_files': total_files,
                'processed_files': 0,
                'current_file': None,
                'message': f'running 0/{total_files}',
            }
        )

    for index, filepath in enumerate(candidate_files, start=1):
        ext = filepath.suffix.lower()

        if progress_callback:
            progress_callback(
                {
                    'processed_files': index - 1,
                    'total_files': total_files,
                    'current_file': str(filepath),
                    'message': f'running {index - 1}/{total_files}',
                }
            )

        try:
            stat = filepath.stat()
            abs_filepath = str(filepath.resolve())
        except Exception:
            continue

        seen_paths.add(abs_filepath)
        file_mtime = stat.st_mtime
        file_size = stat.st_size

        db_item = existing_items.get(abs_filepath)

        # Check if thumbnail exists (handle case where thumbnail was deleted but DB record remains)
        thumbnail_exists = True
        if db_item and db_item.thumbnail_path:
            thumb_full_path = THUMBNAIL_DIR / Path(db_item.thumbnail_path).name
            thumbnail_exists = thumb_full_path.exists()

        unchanged = (
            (not force_rescan)
            and db_item
            and int(db_item.is_deleted or 0) == 0
            and db_item.mtime == file_mtime
            and db_item.size == file_size
            and bool(db_item.content_hash)
            and thumbnail_exists
        )
        if unchanged:
            skipped_count += 1
            if progress_callback:
                progress_callback(
                    {
                        'processed_files': index,
                        'total_files': total_files,
                        'current_file': abs_filepath,
                        'message': f'running {index}/{total_files}',
                    }
                )
            continue

        try:
            content_hash = _hash_file_sampled(filepath)
        except Exception:
            content_hash = _filename_fingerprint(filepath)

        thumbnail_filename = f'{content_hash}.jpg'
        thumbnail_path = THUMBNAIL_DIR / thumbnail_filename

        if ext in SUPPORTED_IMAGE_EXTENSIONS:
            try:
                image_info = _process_image_file(filepath, thumbnail_path)
            except Exception:
                image_info = {
                    'created_at': _fallback_creation_time(filepath),
                    'latitude': None,
                    'longitude': None,
                    'location_name': None,
                    'source_type': 'web',
                }

            if db_item:
                db_item.media_type = 'image'
                db_item.created_at = image_info['created_at']
                db_item.duration = None
                db_item.thumbnail_path = f'thumbnails/{thumbnail_filename}'
                db_item.latitude = image_info['latitude']
                db_item.longitude = image_info['longitude']
                db_item.source_type = image_info['source_type']
                db_item.location_name = image_info['location_name']
                db_item.content_hash = content_hash
                db_item.is_deleted = 0
                db_item.deleted_at = None
                db_item.mtime = file_mtime
                db_item.size = file_size
                updated_count += 1
                dirty_ops += 1
            else:
                item = MediaItem(
                    id=_filename_fingerprint(filepath),
                    filepath=abs_filepath,
                    media_type='image',
                    created_at=image_info['created_at'],
                    thumbnail_path=f'thumbnails/{thumbnail_filename}',
                    latitude=image_info['latitude'],
                    longitude=image_info['longitude'],
                    source_type=image_info['source_type'],
                    location_name=image_info['location_name'],
                    content_hash=content_hash,
                    is_deleted=0,
                    deleted_at=None,
                    mtime=file_mtime,
                    size=file_size,
                )
                db.add(item)
                added_count += 1
                dirty_ops += 1

        elif ext in SUPPORTED_VIDEO_EXTENSIONS:
            if not thumbnail_path.exists() or force_rescan:
                create_video_thumbnail(filepath, thumbnail_path)
            duration = get_video_duration(filepath)

            if db_item:
                db_item.media_type = 'video'
                db_item.created_at = _fallback_creation_time(filepath)
                db_item.duration = duration
                db_item.thumbnail_path = f'thumbnails/{thumbnail_filename}'
                db_item.source_type = 'video'
                db_item.location_name = None
                db_item.latitude = None
                db_item.longitude = None
                db_item.content_hash = content_hash
                db_item.is_deleted = 0
                db_item.deleted_at = None
                db_item.mtime = file_mtime
                db_item.size = file_size
                updated_count += 1
                dirty_ops += 1
            else:
                item = MediaItem(
                    id=_filename_fingerprint(filepath),
                    filepath=abs_filepath,
                    media_type='video',
                    created_at=_fallback_creation_time(filepath),
                    duration=duration,
                    thumbnail_path=f'thumbnails/{thumbnail_filename}',
                    source_type='video',
                    content_hash=content_hash,
                    is_deleted=0,
                    deleted_at=None,
                    mtime=file_mtime,
                    size=file_size,
                )
                db.add(item)
                added_count += 1
                dirty_ops += 1

        if dirty_ops >= COMMIT_EVERY:
            db.commit()
            dirty_ops = 0

        if progress_callback:
            progress_callback(
                {
                    'processed_files': index,
                    'total_files': total_files,
                    'current_file': abs_filepath,
                    'message': f'running {index}/{total_files}',
                }
            )

    deleted_count = 0
    for existing_path, item in existing_items.items():
        if existing_path not in seen_paths:
            item.is_deleted = 1
            item.deleted_at = datetime.datetime.utcnow()
            deleted_count += 1
            dirty_ops += 1

    if dirty_ops > 0:
        db.commit()
    stats = {
        'added': added_count,
        'updated': updated_count,
        'skipped': skipped_count,
        'deleted': deleted_count,
        'processed_files': total_files,
        'total_files': total_files,
    }

    if progress_callback:
        progress_callback(
            {
                'processed_files': total_files,
                'total_files': total_files,
                'current_file': None,
                'message': f'completed {total_files}/{total_files}',
                'stats': stats,
            }
        )

    print(
        'Scan complete. '
        f'Added: {added_count}, Updated: {updated_count}, '
        f'Skipped: {skipped_count}, Deleted: {deleted_count}'
    )
    return stats


def start_scan(directory: str, force_rescan: bool = False):
    db = next(get_db())
    scan_directory(directory, db, force_rescan=force_rescan)
