from pydantic import BaseModel, Field

from app.schemas.core import Application, Hotel, Message


class ChatRequest(BaseModel):
    message: Message
    selected_hotels: list[Hotel] = Field(..., alias="selectedHotels")
    organization_id: int = Field(..., alias="organizationId")
    thread_id: str | None = Field(..., alias="threadId")
    application: Application
    database: str | None
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": {
                    "text": "Hello, world!",
                    "role": "user",
                    "timestamp": "2023-01-01T00:00:00Z",
                },
                "selectedHotels": [],
                "organizationId": 38,
                "threadId": "123",
                "database": "DB_DEMO_SMP",
                "application": {"name": "My App", "description": "My App Description"},
            }
        }
    }


class NewThreadResponse(BaseModel):
    thread_id: str
