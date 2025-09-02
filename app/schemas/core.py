from typing import TypedDict, Literal
from datetime import datetime


class Message(TypedDict):
    role: Literal["user", "assistant"]
    text: str
    timestamp: datetime


class Application(TypedDict):
    name: str
    description: str


class Hotel(TypedDict):
    id: int
    name: str


class Agent(TypedDict):
    model: str
    system_prompt: str
    selected_tools: list[str]
    name: str


class GraphConfiguration(TypedDict):
    selected_hotels: list[Hotel]
    application: Application
