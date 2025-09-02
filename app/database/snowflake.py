from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import sqlalchemy.pool as pool
from app.config import db_settings
from app.schemas.error import DatabaseNotFoundError


def create_snowflake_engine():
    private_key_str = db_settings.snowflake_private_key
    snowflake_pass = db_settings.snowflake_pass or None

    p_key = serialization.load_pem_private_key(
        private_key_str.encode(),
        password=snowflake_pass.encode() if snowflake_pass else None,
        backend=default_backend(),
    )

    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return create_engine(
        URL(
            account=db_settings.account,
            user=db_settings.snowflake_user,
            warehouse=db_settings.warehouse,
        ),
        connect_args={"authenticator": "SNOWFLAKE_JWT", "private_key": pkb},
        poolclass=pool.QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )


engine = create_snowflake_engine()


def get_snowflake_conn():
    return engine.connect()


def get_database(organization_id: int) -> str:
    with get_snowflake_conn() as conn:
        conn.execute(text(f"USE DATABASE {db_settings.orchestrator_database};"))
        query = text(
            "SELECT DATAWAREHOUSE_DATABASE_NAME FROM META.TBL_ORGANIZATION_CONFIG WHERE organization_id = :org_id"
        )
        result = conn.execute(query, {"org_id": organization_id}).fetchone()
        if not result:
            raise DatabaseNotFoundError("Organization not found")
    return result[0]
