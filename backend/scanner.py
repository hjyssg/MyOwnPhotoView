import os
import cv2
import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from backend.database import MediaItem, SessionLocal
import hashlib

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
    print(f"Scanning directory: {directory}")
    base_dir = Path(directory)
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = Path(root) / filename
            ext = filepath.suffix.lower()

            # Use a unique identifier for the filepath in the DB to avoid collisions
            unique_id = hashlib.md5(str(filepath).encode()).hexdigest()
            db_item = db.query(MediaItem).filter(MediaItem.id == unique_id).first()

            if db_item:
                continue

            web_path = f"/media/{filepath.relative_to(base_dir)}"

            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                item = MediaItem(
                    id=unique_id,
                    filepath=web_path,
                    media_type='image',
                    created_at=get_creation_time(filepath)
                )
                db.add(item)

            elif ext in SUPPORTED_VIDEO_EXTENSIONS:
                thumbnail_filename = f"{unique_id}.jpg"
                thumbnail_path = THUMBNAIL_DIR / thumbnail_filename
                create_video_thumbnail(filepath, thumbnail_path)

                item = MediaItem(
                    id=unique_id,
                    filepath=str(filepath), # Store the real path for streaming
                    media_type='video',
                    created_at=get_creation_time(filepath),
                    duration=get_video_duration(filepath),
                    thumbnail_path=f"/thumbnails/{thumbnail_filename}"
                )
                db.add(item)
    db.commit()

def start_scan(directory: str):
    db = next(get_db())
    scan_directory(directory, db)
