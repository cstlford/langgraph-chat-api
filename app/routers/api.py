from fastapi import APIRouter

from app.routers.chat import router as chat_router
from app.routers.user import router as user_router
from app.routers.database import router as database_router

api_router = APIRouter(prefix="/api")

api_router.include_router(prefix="/chatbot", router=chat_router)
api_router.include_router(prefix="/user", router=user_router)
api_router.include_router(prefix="/db", router=database_router)
