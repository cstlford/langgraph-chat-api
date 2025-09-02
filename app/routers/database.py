import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy.sql import text

from app.database.snowflake import get_snowflake_conn
from app.schemas.database import DatabaseRequest, DatabaseResponse

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


router = APIRouter()


@router.post("/query", response_model=DatabaseResponse)
async def query_table(request: DatabaseRequest):
    try:
        with get_snowflake_conn() as conn:
            conn.execute(text(f"USE DATABASE {request.database};"))
            result = conn.execute(text(request.sql))

        return [dict(row) for row in result.mappings().all()]

    except Exception as e:
        logger.error("Snowflake Error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e
