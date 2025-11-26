from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from backend.database import create_db_and_tables, SessionLocal, MediaItem
from backend.scanner import scan_directory
import os
import re
import mimetypes

app = FastAPI()

app.mount("/thumbnails", StaticFiles(directory="backend/cache/thumbnails"), name="thumbnails")
app.mount("/media", StaticFiles(directory="backend/media"), name="media")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.post("/api/scan")
def scan_media_endpoint(directory: str, db: Session = Depends(get_db)):
    # Security Check: Ensure the path is within the allowed media directory
    safe_base_path = os.path.abspath("backend/media")
    requested_path = os.path.abspath(directory)

    if not requested_path.startswith(safe_base_path):
        raise HTTPException(status_code=400, detail="Error: You can only scan directories within the 'backend/media' folder.")

    if not os.path.isdir(requested_path):
        raise HTTPException(status_code=404, detail="Error: Directory not found.")

    scan_directory(requested_path, db)
    return {"message": f"Scan completed for directory: {directory}"}

@app.get("/api/media")
def get_media_items(db: Session = Depends(get_db)):
    return db.query(MediaItem).order_by(MediaItem.created_at.desc()).all()

@app.get("/api/media/stream/{item_id}")
async def stream_video(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(MediaItem).filter(MediaItem.id == item_id).first()
    if not item or item.media_type != 'video':
        raise HTTPException(status_code=404, detail="Video not found")

    video_path = item.filepath
    file_size = os.path.getsize(video_path)

    mime_type, _ = mimetypes.guess_type(video_path)
    if mime_type is None:
        mime_type = "video/mp4"
    range_header = request.headers.get('Range')

    if range_header:
        byte1, byte2 = 0, file_size - 1
        range_match = re.search(r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            byte1 = int(range_match.group(1))
            if range_match.group(2):
                byte2 = int(range_match.group(2))

        length = byte2 - byte1 + 1
        headers = {
            'Content-Range': f'bytes {byte1}-{byte2}/{file_size}',
            'Content-Length': str(length),
            'Accept-Ranges': 'bytes',
        }

        def file_iterator(path, offset, chunk_size):
            with open(path, 'rb') as f:
                f.seek(offset)
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    yield data

        return StreamingResponse(
            file_iterator(video_path, byte1, 65536),
            status_code=206,
            headers=headers,
            media_type=mime_type
        )
    else:
        def file_iterator(path, chunk_size):
            with open(path, 'rb') as f:
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    yield data

        headers = {
            'Content-Length': str(file_size),
            'Accept-Ranges': 'bytes',
        }
        return StreamingResponse(
            file_iterator(video_path, 65536),
            headers=headers,
            media_type=mime_type
        )

@app.get("/")
def read_root():
    return {"message": "Welcome to Local Smart Gallery"}
