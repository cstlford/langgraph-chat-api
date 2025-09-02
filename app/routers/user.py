import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy.sql import text

from app.database.snowflake import get_database, get_snowflake_conn
from app.schemas.user import HotelResponse

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{organization_id}", response_model=HotelResponse)
async def get_user_context(organization_id: int):
    try:
        database = get_database(organization_id)
        with get_snowflake_conn() as conn:
            conn.execute(text(f"USE DATABASE {database};"))
            query = text("select ID, Name from DM_BI.VW_HOTEL")
            result = conn.execute(query)
            hotels = result.fetchall()
            return {
                "hotels": [{"id": row[0], "name": row[1]} for row in hotels],
                "database": database,
            }

    except Exception as e:
        logger.error("Failed to fetch user context: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch user context: {str(e)}"
        ) from e
