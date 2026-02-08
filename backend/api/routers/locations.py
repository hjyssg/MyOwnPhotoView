from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db
from backend.services.location_service import (
    get_locations_payload,
    get_media_by_location_payload,
    normalize_location_key_for_match,
)

router = APIRouter()


@router.get('/api/locations')
def get_locations(db: Session = Depends(get_db)):
    return get_locations_payload(db)


@router.get('/api/media/by-location')
def get_media_by_location(key: str, db: Session = Depends(get_db)):
    target = normalize_location_key_for_match(key)
    if not target:
        raise HTTPException(status_code=400, detail='Missing location key')
    return get_media_by_location_payload(db, target)
