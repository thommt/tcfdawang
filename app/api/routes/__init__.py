from fastapi import APIRouter

from . import questions, fetch, sessions, tasks, paragraphs, sentences, flashcards, conversations

api_router = APIRouter()
api_router.include_router(questions.router)
api_router.include_router(fetch.router, prefix="/questions")
api_router.include_router(sessions.sessions_router)
api_router.include_router(sessions.answer_group_router)
api_router.include_router(sessions.answers_router)
api_router.include_router(tasks.router)
api_router.include_router(paragraphs.router)
api_router.include_router(sentences.router)
api_router.include_router(flashcards.router)
api_router.include_router(conversations.router)

__all__ = ["api_router"]
