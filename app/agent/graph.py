"""
Module for agent and multi-agent creation and configuration.
"""

from datetime import date

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

from app.agent.agent_config import agent_config
from app.agent.tools import get_tools, load_chat_model
from app.config import settings
from app.schemas.core import Agent, GraphConfiguration, Hotel

URL = settings.interpreter_url


def make_agent(config: Agent):
    """Creates individual agents with specified model, tools, prompt, and name configuration"""
    return create_react_agent(
        model=load_chat_model(config["model"]),
        tools=get_tools(config["selected_tools"]),
        prompt=config["system_prompt"],
        name=config["name"],
    )


def create_subagents(hotels: list[Hotel] | str):
    """Creates subagents for SQL and Analysis tasks based on the provided hotels"""

    sql_config: Agent = {
        "model": agent_config.sql_agent_model,
        "system_prompt": agent_config.sql_agent_prompt.format(
            today=date.today(), hotels=hotels
        ),
        "selected_tools": agent_config.sql_agent_tools,
        "name": "sql_agent",
    }

    sql_agent = make_agent(sql_config)

    analysis_config: Agent = {
        "model": agent_config.analysis_agent_model,
        "system_prompt": agent_config.analysis_agent_prompt.format(
            today=date.today(), url=URL
        ),
        "selected_tools": agent_config.analysis_agent_tools,
        "name": "analysis_agent",
    }

    analysis_agent = make_agent(analysis_config)

    return [sql_agent, analysis_agent]


memory = MemorySaver()


def create_graph(config: GraphConfiguration):
    """Creates the overall graph with a supervisor and subagents based on the provided configuration"""
    application = config.get(
        "application",
        {"name": "Default App", "description": "No description provided"},
    )
    hotels = config.get("selected_hotels", [])

    subagents = create_subagents(hotels)

    supervisor = create_supervisor(
        agents=subagents,  # type: ignore
        model=load_chat_model(agent_config.supervisor_model),
        prompt=agent_config.supervisor_prompt.format(
            today=date.today(),
            hotels=hotels,
            url=URL,
            application=application["name"],
            description=application["description"],
        ),
        output_mode="last_message",
    )

    return supervisor.compile(checkpointer=memory)
