from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database.vector_database.vector_db import get_or_create_vector_store
from app.routers.api import api_router

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"\n🚀 Starting {settings.app_name} v{settings.app_version}")
    get_or_create_vector_store()
    print("✅ Application startup complete\n")

    yield
    print("\n🛑 Application shutdown complete")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
