from typing import Any
from pydantic import BaseModel, RootModel


class DatabaseRequest(BaseModel):
    sql: str
    database: str
    model_config = {
        "json_schema_extra": {
            "example": {"sql": "SELECT * FROM users", "database": "my_database"}
        }
    }


class DatabaseResponse(RootModel[list[dict[str, Any]]]):
    model_config = {"json_schema_extra": {"example": [{"id": 1, "name": "John Doe"}]}}
