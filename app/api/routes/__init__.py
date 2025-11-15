from fastapi import APIRouter

from . import questions, fetch

api_router = APIRouter()
api_router.include_router(questions.router)
api_router.include_router(fetch.router, prefix="/questions")

__all__ = ["api_router"]
