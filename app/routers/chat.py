import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from sse_starlette import EventSourceResponse

from app.agent.agent_config import agent_config
from app.agent.graph import create_graph
from app.database.snowflake import get_database
from app.schemas.chat import ChatRequest
from app.schemas.error import DatabaseNotFoundError

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/stream")
async def stream(request: Request, chat_request: ChatRequest):
    try:
        database = (
            get_database(chat_request.organization_id)
            if not chat_request.database
            else chat_request.database
        )
        thread_id = (
            chat_request.thread_id if chat_request.thread_id else str(uuid.uuid4())
        )

        graph = create_graph(
            {
                "application": chat_request.application,
                "selected_hotels": chat_request.selected_hotels,
            }
        )

        async def event_generator():
            try:
                async for chunk in graph.astream(
                    {"messages": [HumanMessage(content=chat_request.message["text"])]},
                    config=RunnableConfig(
                        configurable={
                            "thread_id": thread_id,
                            "database": database,
                        }
                    ),
                    stream_mode="updates",
                ):
                    if await request.is_disconnected():
                        logger.info("Client disconnected during stream")
                        return

                    event = None
                    data = None

                    supervisor_msgs = chunk.get("supervisor", {}).get("messages", [])

                    for msg in supervisor_msgs[-1:]:
                        if isinstance(msg, AIMessage):
                            event = "message"
                            data = msg.content
                        elif (
                            isinstance(msg, ToolMessage)
                            and msg.name in agent_config.route_config
                        ):
                            event = "route"
                            data = json.dumps(
                                {
                                    "destination": agent_config.route_config[msg.name][
                                        "name"
                                    ],
                                    "message": agent_config.route_config[msg.name][
                                        "message"
                                    ],
                                }
                            )

                    if event is not None:
                        yield {"event": event, "data": data}

                yield {
                    "event": "done",
                    "data": json.dumps({"threadId": thread_id, "database": database}),
                }

            except asyncio.CancelledError:
                logger.info("Stream generator cancelled")
                raise
            except ValueError as ve:
                logger.error("ValueError in stream: %s", str(ve), exc_info=True)
                yield {
                    "event": "error",
                    "data": "Invalid input provided. Please try again.",
                }
            except Exception as e:
                logger.error("Unexpected error in stream: %s", str(e), exc_info=True)
                yield {
                    "event": "error",
                    "data": "An unexpected error occurred. Please try again later.",
                }

        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
        )
    except DatabaseNotFoundError as e:
        logger.error(
            "Database not found with organization ID: %s; Error: %s",
            chat_request.organization_id,
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=404, detail="Database not found.") from e
    except ValueError as ve:
        logger.error("ValueError: %s", str(ve), exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid input provided.") from ve
    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        ) from e


@router.get("/new-thread")
async def create_new_thread():
    return {"thread_id": str(uuid.uuid4())}
