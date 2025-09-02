from typing import Any
from pydantic import BaseModel, Field


class CodeRequest(BaseModel):
    code: str = Field(..., description="Python code to execute")
    database: str = Field(..., description="Database name for SQL execution")


class CodeToolResult(BaseModel):
    status: str = Field(..., description="Execution status: success, error, timeout")
    output: str = Field(default="", description="Standard output")
    errors: str = Field(default="", description="Error messages")
    images: list[str] = Field(default=[], description="URLs to generated images")
    objects: dict[str, Any] = Field(
        default={}, description="Created variables and objects"
    )
    execution_time: float = Field(default=0.0, description="Execution time in seconds")
