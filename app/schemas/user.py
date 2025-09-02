from pydantic import BaseModel

from app.schemas.core import Hotel


class HotelResponse(BaseModel):
    hotels: list[Hotel]
    database: str
