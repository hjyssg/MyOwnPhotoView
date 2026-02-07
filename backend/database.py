from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, BigInteger, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import datetime

DATABASE_URL = "sqlite:///./gallery.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(String, primary_key=True, index=True)
    filepath = Column(String, unique=True, index=True)
    media_type = Column(String, default='image')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    duration = Column(Integer, nullable=True)  # Duration in seconds for videos
    thumbnail_path = Column(String, nullable=True) # Path to the video thumbnail
    
    # Phase 2: Location and Intelligence
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    source_type = Column(String, default='unknown') # 'camera', 'web', 'screenshot', 'video'
    location_name = Column(String, nullable=True)
    mtime = Column(Float, nullable=False, default=0)
    size = Column(BigInteger, nullable=False, default=0)

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()

def _apply_lightweight_migrations():
    """Add newly introduced columns for existing SQLite databases."""
    with engine.begin() as connection:
        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(media_items)")).fetchall()
        }
        if "mtime" not in columns:
            connection.execute(
                text("ALTER TABLE media_items ADD COLUMN mtime FLOAT NOT NULL DEFAULT 0")
            )
        if "size" not in columns:
            connection.execute(
                text("ALTER TABLE media_items ADD COLUMN size BIGINT NOT NULL DEFAULT 0")
            )
