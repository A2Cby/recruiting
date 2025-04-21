from fastapi import APIRouter

from api.v1.endpoints import matching

api_router = APIRouter()

api_router.include_router(matching.router, prefix="/matching", tags=["Candidate Matching"])

# You can include other routers here as your API grows
# api_router.include_router(another_router, prefix="/other", tags=["Other Module"]) 