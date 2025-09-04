from typing import Any, Callable
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
from app.database.vector_database.vector_db import get_or_create_vector_store


@tool
async def code_interpreter(code: str, config: RunnableConfig):
    """Execute Python code in a secure sandboxed environment.

    You have access to a preloaded Python environment with common data science, math, and visualization libraries:
    - pandas, numpy, matplotlib, seaborn

    <execute_sql function>
    A helper function `execute_sql(sql: str) -> pd.DataFrame` is available for querying Snowflake.
    Use it for SELECT queries and receive results as a pandas DataFrame.
    Always use dates in yyyymmdd format in your sql queries.
    </execute_sql function>

    Return format:
    {
        'status': 'success' | 'error' | 'timeout',
        'output': str,        # printed text
        'errors': str,        # stderr
        'images': [str],      # URLs for saved matplotlib/seaborn plots
        'objects': {...},     # captured variables (with previews)
        'files': [str],       # downloadable files (e.g., CSVs for DataFrames)
        'execution_time': float
    }

    Important:
    - To capture results, either print them (goes to 'output') OR assign them to a variable (goes to 'objects' and saves a CSV in 'files'), not both.
    Example:
        print(execute_sql("SELECT * FROM my_table"))   # appears only in 'output'
        df = execute_sql("SELECT * FROM my_table")     # appears in 'objects' + CSV in 'files'
    - Visualizations made with matplotlib/seaborn are saved automatically and appear in 'images'.
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

        response = resp.json()
        print(response)
        return response


@tool
def schema_retriever(query: str) -> str:
    """Search a vector database with snowflake database schema to find tables and columns for SQL query generation.

    Args:
        query: Describe what data you're looking for. If searching for derived metrics,
        search for the constituent parts.

        Examples:
            - "business on the books"

    Returns: Table structures with column names, data types, sample values, and
    usage guidance to help write accurate SQL queries for hotel business analysis.
    """
    vectorstore = get_or_create_vector_store()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    return create_retriever_tool(
        retriever,
        "",
        "",
    ).invoke({"query": query})


@tool
def sql_executor(sql: str, config: RunnableConfig):
    """Execute a SQL query against the Snowflake database. Always add a limit 10 clause when testing queries."""
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
    except ValueError as ve:
        raise ValueError(
            f"Expected model_provider in format 'provider/model', got: '{model_provider}'"
        ) from ve
    except Exception as e:
        raise RuntimeError(
            f"Failed to initialize model '{model}' with provider '{provider}': {e}"
        ) from e
