import os
import datetime
import hashlib
import subprocess
from pathlib import Path
from sqlalchemy.orm import Session
from backend.database import MediaItem, SessionLocal
from PIL import Image, ImageOps
import piexif
import reverse_geocoder as rg

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.heic']
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi']
THUMBNAIL_DIR = Path('backend/cache/thumbnails')


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


def get_geo_info(filepath: Path):
    lat = None
    lon = None
    try:
        if filepath.suffix.lower() in ['.jpg', '.jpeg', '.heic']:
            img = Image.open(filepath)
            exif_dict = piexif.load(img.info.get('exif', b''))
            gps_tags = exif_dict.get('GPS')

            if gps_tags:
                lat_dms = gps_tags.get(piexif.GPSIFD.GPSLatitude)
                lat_ref = gps_tags.get(piexif.GPSIFD.GPSLatitudeRef)
                lon_dms = gps_tags.get(piexif.GPSIFD.GPSLongitude)
                lon_ref = gps_tags.get(piexif.GPSIFD.GPSLongitudeRef)

                lat = get_decimal_from_dms(lat_dms, lat_ref)
                lon = get_decimal_from_dms(lon_dms, lon_ref)
    except Exception:
        pass
    return lat, lon


def determine_source_type(filepath: Path, media_type: str) -> str:
    if media_type == 'video':
        return 'video'

    filename = filepath.name.lower()
    if 'screenshot' in filename or '鎴睆' in filename:
        return 'screenshot'

    try:
        if filepath.suffix.lower() in ['.jpg', '.jpeg', '.heic']:
            img = Image.open(filepath)
            exif_dict = piexif.load(img.info.get('exif', b''))
            if exif_dict.get('0th', {}).get(piexif.ImageIFD.Model):
                return 'camera'
    except Exception:
        pass

    if filepath.suffix.lower() == '.png':
        return 'screenshot'

    return 'web'


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_creation_time(filepath: Path) -> datetime.datetime:
    try:
        if filepath.suffix.lower() in ['.jpg', '.jpeg', '.heic']:
            img = Image.open(filepath)
            exif_dict = piexif.load(img.info.get('exif', b''))
            date_str = exif_dict.get('0th', {}).get(piexif.ImageIFD.DateTime)
            if date_str:
                return datetime.datetime.strptime(date_str.decode(), '%Y:%m:%d %H:%M:%S')
    except Exception:
        pass
    return datetime.datetime.fromtimestamp(filepath.stat().st_mtime)


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
    command = [
        'ffmpeg',
        '-y',
        '-ss',
        '00:00:01',
        '-i',
        str(video_path),
        '-frames:v',
        '1',
        str(thumbnail_path),
    ]
    result = _run_command(command)
    if result is None:
        return
    if result.returncode != 0:
        # fallback to first frame for very short videos
        fallback_command = [
            'ffmpeg',
            '-y',
            '-ss',
            '00:00:00',
            '-i',
            str(video_path),
            '-frames:v',
            '1',
            str(thumbnail_path),
        ]
        _run_command(fallback_command)


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


def _remove_thumbnail_file(item: MediaItem):
    if not item.thumbnail_path:
        return
    thumb = THUMBNAIL_DIR / Path(item.thumbnail_path).name
    if thumb.exists():
        try:
            thumb.unlink()
        except Exception:
            pass


def scan_directory(directory: str, db: Session):
    directory = os.path.abspath(directory)
    print(f'Scanning directory: {directory}')
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

    existing_items = {
        item.filepath: item
        for item in db.query(MediaItem).all()
        if _is_under_directory(item.filepath, directory)
    }

    seen_paths = set()
    added_count = 0
    updated_count = 0
    skipped_count = 0

    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = Path(root) / filename
            ext = filepath.suffix.lower()
            if ext not in SUPPORTED_IMAGE_EXTENSIONS and ext not in SUPPORTED_VIDEO_EXTENSIONS:
                continue

            try:
                stat = filepath.stat()
                abs_filepath = str(filepath.resolve())
            except Exception:
                continue

            seen_paths.add(abs_filepath)
            unique_id = hashlib.md5(abs_filepath.encode()).hexdigest()
            thumbnail_filename = f'{unique_id}.jpg'
            thumbnail_path = THUMBNAIL_DIR / thumbnail_filename
            file_mtime = stat.st_mtime
            file_size = stat.st_size

            db_item = existing_items.get(abs_filepath)

            if db_item and db_item.mtime == file_mtime and db_item.size == file_size:
                if db_item.media_type == 'video':
                    if db_item.duration in [None, 0]:
                        db_item.duration = get_video_duration(filepath)
                        updated_count += 1
                    if not thumbnail_path.exists():
                        create_video_thumbnail(filepath, thumbnail_path)
                        updated_count += 1
                skipped_count += 1
                continue

            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                lat, lon = get_geo_info(filepath)
                loc_name = None
                if lat is not None and lon is not None:
                    try:
                        results = rg.search((lat, lon))
                        if results:
                            loc_name = f"{results[0]['admin1']} {results[0]['name']}"
                    except Exception:
                        pass

                try:
                    with Image.open(filepath) as img:
                        img = ImageOps.exif_transpose(img)
                        img.thumbnail((400, 400))
                        img.save(thumbnail_path, 'JPEG')
                except Exception:
                    pass

                source_type = determine_source_type(filepath, 'image')

                if db_item:
                    db_item.media_type = 'image'
                    db_item.created_at = get_creation_time(filepath)
                    db_item.duration = None
                    db_item.thumbnail_path = f'thumbnails/{thumbnail_filename}'
                    db_item.latitude = lat
                    db_item.longitude = lon
                    db_item.source_type = source_type
                    db_item.location_name = loc_name
                    db_item.mtime = file_mtime
                    db_item.size = file_size
                    updated_count += 1
                else:
                    item = MediaItem(
                        id=unique_id,
                        filepath=abs_filepath,
                        media_type='image',
                        created_at=get_creation_time(filepath),
                        thumbnail_path=f'thumbnails/{thumbnail_filename}',
                        latitude=lat,
                        longitude=lon,
                        source_type=source_type,
                        location_name=loc_name,
                        mtime=file_mtime,
                        size=file_size,
                    )
                    db.add(item)
                    added_count += 1

            elif ext in SUPPORTED_VIDEO_EXTENSIONS:
                create_video_thumbnail(filepath, thumbnail_path)
                duration = get_video_duration(filepath)

                if db_item:
                    db_item.media_type = 'video'
                    db_item.created_at = get_creation_time(filepath)
                    db_item.duration = duration
                    db_item.thumbnail_path = f'thumbnails/{thumbnail_filename}'
                    db_item.source_type = 'video'
                    db_item.location_name = None
                    db_item.latitude = None
                    db_item.longitude = None
                    db_item.mtime = file_mtime
                    db_item.size = file_size
                    updated_count += 1
                else:
                    item = MediaItem(
                        id=unique_id,
                        filepath=abs_filepath,
                        media_type='video',
                        created_at=get_creation_time(filepath),
                        duration=duration,
                        thumbnail_path=f'thumbnails/{thumbnail_filename}',
                        source_type='video',
                        mtime=file_mtime,
                        size=file_size,
                    )
                    db.add(item)
                    added_count += 1

    deleted_count = 0
    for existing_path, item in existing_items.items():
        if existing_path not in seen_paths:
            _remove_thumbnail_file(item)
            db.delete(item)
            deleted_count += 1

    db.commit()
    print(
        'Scan complete. '
        f'Added: {added_count}, Updated: {updated_count}, '
        f'Skipped: {skipped_count}, Deleted: {deleted_count}'
    )


def start_scan(directory: str):
    db = next(get_db())
    scan_directory(directory, db)
