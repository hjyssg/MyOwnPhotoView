import os
import logging
from uuid import uuid4

from fastapi import Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.core.config import MEDIA_DIR, THUMBNAIL_DIR


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    os.makedirs(THUMBNAIL_DIR, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)

    app = FastAPI()

    @app.exception_handler(Exception)
    async def internal_server_error_handler(request: Request, exc: Exception):
        request_id = uuid4().hex[:12]
        logger.exception(
            '[500] request_id=%s method=%s path=%s query=%s',
            request_id,
            request.method,
            request.url.path,
            request.url.query,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                'detail': 'Internal Server Error',
                'request_id': request_id,
            },
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
        allow_origin_regex=r'^https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|192\.168\.\d+\.\d+)(:\d+)?$',
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    app.mount('/thumbnails', StaticFiles(directory=THUMBNAIL_DIR), name='thumbnails')
    app.mount('/media', StaticFiles(directory=MEDIA_DIR), name='media')
    return app
