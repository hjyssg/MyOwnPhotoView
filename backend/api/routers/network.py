from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.services.network_service import build_access_url_candidates, build_qrcode_png

router = APIRouter()


@router.get('/api/network/access')
def get_network_access_info(request: Request):
    candidates = build_access_url_candidates(request)
    preferred = candidates[0] if candidates else 'http://localhost:3000'
    return {'preferred_url': preferred, 'candidate_urls': candidates}


@router.get('/api/network/qrcode')
def get_network_access_qrcode(request: Request, target: str | None = None):
    candidates = build_access_url_candidates(request)
    fallback = candidates[0] if candidates else 'http://localhost:3000'
    content = (target or '').strip() or fallback
    buffer = build_qrcode_png(content)
    return StreamingResponse(
        buffer,
        media_type='image/png',
        headers={'Cache-Control': 'no-store'},
    )
