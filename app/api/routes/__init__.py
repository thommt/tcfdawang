from fastapi import APIRouter

from . import questions, fetch, sessions

api_router = APIRouter()
api_router.include_router(questions.router)
api_router.include_router(fetch.router, prefix="/questions")
api_router.include_router(sessions.sessions_router)
api_router.include_router(sessions.answer_group_router)
api_router.include_router(sessions.answers_router)

__all__ = ["api_router"]
