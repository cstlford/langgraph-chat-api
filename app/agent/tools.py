from typing import Any, Callable, Literal
import httpx

from langchain_tavily import TavilySearch
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain.tools.retriever import create_retriever_tool
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy.sql import text

from app.config import settings
from app.database.snowflake import get_snowflake_conn
from app.database.vector_database.vector_store import get_vectorstore


@tool
async def code_interpreter(code: str, config: RunnableConfig):
    """Execute Python code in a secure sandboxed environment.

    You have access to a preloaded Python environment with common data science, math, and visualization libraries, including:

    - pandas, numpy, scipy, scikit-learn, statsmodels
    - matplotlib, seaborn, plotly
    - sympy, networkx
    - requests, httpx, BeautifulSoup (bs4), lxml
    - Pillow (image processing), python-dateutil, pytz
    - openpyxl, xlsxwriter (Excel I/O)

    A helper function `execute_sql(sql: str) -> pd.DataFrame` is also available for querying Snowflake.
    Use it to run SELECT queries and receive results as a pandas DataFrame.
    """
    url = settings.interpreter_url
    database = config.get("configurable", {}).get("database", None)

    if database is None:
        raise ValueError("Database not found in config")

    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{url}/run", json={"code": code, "database": database}
        )
        resp.raise_for_status()

        return resp.json()


@tool
def schema_retriever(query: str, schema_filter: Literal["isp", "dm_bi"]) -> str:
    """Search the Snowflake database schema to find tables and columns for SQL query generation.

    Use this tool when you need to:
    - Find which tables contain specific data (occupancy, revenue, bookings, etc.)
    - Get column names and data types for SQL queries
    - Understand table relationships and structure
    - Find the right business metrics and dimensions

    Args:
        query: Describe what data you're looking for. If searching for derived metrics,
        search for the constituent parts.

        Examples:
            "future revenue and bookings for next quarter"
            "ADR calculation and rate analysis"
            "occupancy rates and room inventory"
            "hotel property names and locations"
            "capacity planning and room availability"
            "confirmed reservations and business on books"

        schema_filter: Which schema to search:
            - "dm_bi": Business Intelligence views for future bookings, inventory,
              hotel details. Use for questions about upcoming business, occupancy
              projections, and capacity analysis.
            - "isp": Historical operational data for past performance analysis,
              completed stays, and historical ADR calculations.

    Returns: Table structures with column names, data types, sample values, and
    usage guidance to help write accurate SQL queries for hotel business analysis.
    """
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 4, "filter": {"schema": schema_filter}}
    )

    retriever_tool = create_retriever_tool(
        retriever,
        "retrieve_snowflake_schema",
        "Search and return information about the Snowflake schema.",
    )

    results = retriever_tool.invoke({"query": query})

    return results


@tool
def sql_executor(sql: str, config: RunnableConfig):
    """Execute a SQL query against the Snowflake database."""
    database = config.get("configurable", {}).get("database", None)

    if database is None:
        raise ValueError("Database not found in config")
    with get_snowflake_conn() as conn:
        conn.execute(text(f"USE DATABASE {database};"))
        result = conn.execute(text(sql))

    return [dict(row) for row in result.mappings().all()]


web_search = TavilySearch(max_results=5, topic="general", search_depth="basic")


def get_tools(selected_tools: list[str]) -> list[Callable[..., Any]]:
    """Convert a list of tool names to actual tool functions."""
    tools = []

    for tool_name in selected_tools:
        match tool_name:
            case "code_interpreter":
                tools.append(code_interpreter)
            case "schema_retriever":
                tools.append(schema_retriever)
            case "sql_executor":
                tools.append(sql_executor)
            case "web_search":
                tools.append(web_search)
    return tools


def load_chat_model(model_provider: str) -> BaseChatModel:
    try:
        provider, model = model_provider.split("/", maxsplit=1)
        return init_chat_model(model, model_provider=provider)
    except ValueError:
        raise ValueError(
            f"Expected model_provider in format 'provider/model', got: '{model_provider}'"
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to initialize model '{model}' with provider '{provider}': {e}"
        )
