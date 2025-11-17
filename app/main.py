from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import os
from fastapi import FastAPI
from dotenv import load_dotenv

from app.api.routes import api_router
from app.db.base import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    load_dotenv()
    init_db()
    yield


app = FastAPI(title="TCF Learning Service", lifespan=lifespan)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Basic health endpoint."""
    return {"status": "ok"}


app.include_router(api_router)
