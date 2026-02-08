from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db
from backend.services.stats_service import get_busy_days_payload

router = APIRouter()


@router.get('/api/stats/busy-days')
def get_busy_days(
    order: str = 'asc',
    min_count: int | None = None,
    limit: int = 200,
    only_camera: bool = False,
    db: Session = Depends(get_db),
):
    return get_busy_days_payload(
        db=db,
        order=order,
        min_count=min_count,
        limit=limit,
        only_camera=only_camera,
    )
