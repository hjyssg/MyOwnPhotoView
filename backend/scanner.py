import os
import cv2
import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from backend.database import MediaItem, SessionLocal
import hashlib
from PIL import Image
import piexif
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.heic']
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi']
THUMBNAIL_DIR = Path("backend/cache/thumbnails")

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
            exif_dict = piexif.load(img.info.get("exif", b""))
            gps_tags = exif_dict.get("GPS")
            
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
    if 'screenshot' in filename or '截屏' in filename:
        return 'screenshot'
    
    try:
        if filepath.suffix.lower() in ['.jpg', '.jpeg', '.heic']:
            img = Image.open(filepath)
            exif_dict = piexif.load(img.info.get("exif", b""))
            if exif_dict.get("0th", {}).get(piexif.ImageIFD.Model):
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
            exif_dict = piexif.load(img.info.get("exif", b""))
            date_str = exif_dict.get("0th", {}).get(piexif.ImageIFD.DateTime)
            if date_str:
                return datetime.datetime.strptime(date_str.decode(), '%Y:%m:%d %H:%M:%S')
    except Exception:
        pass
    return datetime.datetime.fromtimestamp(filepath.stat().st_mtime)

def create_video_thumbnail(video_path: Path, thumbnail_path: Path):
    try:
        vid_cap = cv2.VideoCapture(str(video_path))
        if not vid_cap.isOpened():
            return

        success = False
        image = None
        success, image = vid_cap.read()

        if not success:
            vid_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            success, image = vid_cap.read()

        if not success:
            vid_cap.set(cv2.CAP_PROP_POS_MSEC, 100)
            success, image = vid_cap.read()

        if success and image is not None:
            cv2.imwrite(str(thumbnail_path), image)
        vid_cap.release()
    except Exception as e:
        print(f"Error creating thumbnail for {video_path}: {e}")

def get_video_duration(video_path: Path) -> int:
    try:
        vid_cap = cv2.VideoCapture(str(video_path))
        if not vid_cap.isOpened():
            return 0
        fps = vid_cap.get(cv2.CAP_PROP_FPS)
        frame_count = vid_cap.get(cv2.CAP_PROP_FRAME_COUNT)
        vid_cap.release()
        
        if fps > 0 and frame_count > 0:
            duration = int(frame_count / fps)
            return max(1, duration)
        return 0
    except Exception as e:
        return 0

def scan_directory(directory: str, db: Session):
    print(f"正在扫描目录: {directory}")
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = Path(root) / filename
            ext = filepath.suffix.lower()
            abs_filepath = str(filepath.resolve())
            unique_id = hashlib.md5(abs_filepath.encode()).hexdigest()

            db_item = db.query(MediaItem).filter(MediaItem.filepath == abs_filepath).first()
            
            if db_item:
                if db_item.media_type == 'video' and (db_item.duration == 0 or not (THUMBNAIL_DIR / f"{unique_id}.jpg").exists()):
                    db_item.duration = get_video_duration(filepath)
                    create_video_thumbnail(filepath, THUMBNAIL_DIR / f"{unique_id}.jpg")
                continue

            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                thumbnail_filename = f"{unique_id}.jpg"
                thumbnail_path = THUMBNAIL_DIR / thumbnail_filename
                if not thumbnail_path.exists():
                    try:
                        with Image.open(filepath) as img:
                            img.thumbnail((400, 400))
                            img.save(thumbnail_path, "JPEG")
                    except Exception: pass

                lat, lon = get_geo_info(filepath)
                source_type = determine_source_type(filepath, 'image')

                item = MediaItem(
                    id=unique_id,
                    filepath=abs_filepath,
                    media_type='image',
                    created_at=get_creation_time(filepath),
                    thumbnail_path=f"thumbnails/{thumbnail_filename}",
                    latitude=lat,
                    longitude=lon,
                    source_type=source_type
                )
                db.add(item)
                count += 1

            elif ext in SUPPORTED_VIDEO_EXTENSIONS:
                thumbnail_filename = f"{unique_id}.jpg"
                thumbnail_path = THUMBNAIL_DIR / thumbnail_filename
                if not thumbnail_path.exists():
                    create_video_thumbnail(filepath, thumbnail_path)

                item = MediaItem(
                    id=unique_id,
                    filepath=abs_filepath,
                    media_type='video',
                    created_at=get_creation_time(filepath),
                    duration=get_video_duration(filepath),
                    thumbnail_path=f"thumbnails/{thumbnail_filename}",
                    source_type='video'
                )
                db.add(item)
                count += 1
                
    db.commit()
    print(f"扫描完成，共添加 {count} 个文件")

def start_scan(directory: str):
    db = next(get_db())
    scan_directory(directory, db)
