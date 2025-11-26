from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
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

    id = Column(Integer, primary_key=True, index=True)
    filepath = Column(String, unique=True, index=True)
    media_type = Column(String, default='image')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    duration = Column(Integer, nullable=True)  # Duration in seconds for videos
    thumbnail_path = Column(String, nullable=True) # Path to the video thumbnail

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)