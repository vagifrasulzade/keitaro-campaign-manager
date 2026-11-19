from fastapi import APIRouter

from app.api.v1 import campaigns, meta, streams

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(meta.router)
api_router.include_router(campaigns.router)
api_router.include_router(streams.router)
