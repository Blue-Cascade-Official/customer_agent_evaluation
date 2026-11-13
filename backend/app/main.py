import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audio, elevenlabs_routes, knowledge, sessions, settings as settings_api
from app.config import get_settings
from app.db import init_db

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


settings = get_settings()
app = FastAPI(title="Internee AI Call Evaluation API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(elevenlabs_routes.router)
app.include_router(knowledge.router)
app.include_router(audio.router)
app.include_router(settings_api.router)


@app.get("/health")
def health():
    return {"status": "ok"}
