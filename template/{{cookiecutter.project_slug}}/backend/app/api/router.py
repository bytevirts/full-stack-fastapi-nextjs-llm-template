"""API router aggregation."""

from fastapi import APIRouter

from app.api.routes.v1 import v1_router

api_router = APIRouter()

# API v1 routes
api_router.include_router(v1_router, prefix="/v1")
