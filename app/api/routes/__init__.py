from fastapi import APIRouter

from . import questions

api_router = APIRouter()
api_router.include_router(questions.router)

__all__ = ["api_router"]
