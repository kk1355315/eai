from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.config import settings
from app.db import engine, init_db
from app.routers import advice, health, inventory, profile, recognitions, reference, user_events
from app.seed import seed_reference_data


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    with Session(engine) as session:
        seed_reference_data(session)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)
app.include_router(health.router)
app.include_router(reference.router)
app.include_router(profile.router)
app.include_router(recognitions.router)
app.include_router(inventory.router)
app.include_router(advice.router)
app.include_router(user_events.router)
