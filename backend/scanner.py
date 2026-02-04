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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_creation_time(filepath: Path) -> datetime.datetime:
    """尝试从 EXIF 获取拍摄时间，否则回退到文件修改时间"""
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
        success, image = vid_cap.read()
        if success:
            cv2.imwrite(str(thumbnail_path), image)
        vid_cap.release()
    except Exception as e:
        print(f"Error creating thumbnail for {video_path}: {e}")


def get_video_duration(video_path: Path) -> int:
    try:
        vid_cap = cv2.VideoCapture(str(video_path))
        fps = vid_cap.get(cv2.CAP_PROP_FPS)
        frame_count = vid_cap.get(cv2.CAP_PROP_FRAME_COUNT)
        vid_cap.release()
        return int(frame_count / fps) if fps > 0 else 0
    except Exception as e:
        print(f"Error getting duration for {video_path}: {e}")
        return 0

def scan_directory(directory: str, db: Session):
    print(f"正在扫描目录: {directory}")
    base_dir = Path(directory)
    count = 0
    
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = Path(root) / filename
            ext = filepath.suffix.lower()

            # 使用绝对路径的字符串作为唯一标识
            abs_filepath = str(filepath.resolve())
            
            # 检查文件是否已存在（通过filepath）
            db_item = db.query(MediaItem).filter(MediaItem.filepath == abs_filepath).first()
            if db_item:
                continue

            # 为数据库ID使用MD5哈希
            unique_id = hashlib.md5(abs_filepath.encode()).hexdigest()

            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                # 处理 HEIC 或生成缩略图（如果需要）
                thumbnail_filename = f"{unique_id}.jpg"
                thumbnail_path = THUMBNAIL_DIR / thumbnail_filename
                
                # 如果是图片，我们也生成一个小缩略图以加快前端加载（可选）
                # 这里为了简单，如果已经有缩略图就不重复生成
                if not thumbnail_path.exists():
                    try:
                        with Image.open(filepath) as img:
                            img.thumbnail((400, 400))
                            img.save(thumbnail_path, "JPEG")
                    except Exception as e:
                        print(f"Error creating thumbnail for {filepath}: {e}")

                item = MediaItem(
                    id=unique_id,
                    filepath=abs_filepath,
                    media_type='image',
                    created_at=get_creation_time(filepath),
                    thumbnail_path=f"thumbnails/{thumbnail_filename}"
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
                    thumbnail_path=f"thumbnails/{thumbnail_filename}"
                )
                db.add(item)
                count += 1
                
    db.commit()
    print(f"扫描完成，共添加 {count} 个文件")

def start_scan(directory: str):
    db = next(get_db())
    scan_directory(directory, db)
