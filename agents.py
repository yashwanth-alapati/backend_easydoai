"""
LangGraph agent for orchestrating the easydo.ai chatbot.
"""

import logging
from typing import Dict, Any, List, Sequence, TypedDict
from langchain_anthropic import ChatAnthropic
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.messages import ToolMessage
from langgraph.graph import StateGraph, END
from tools import get_tools
from datetime import datetime, date
import json
import os

from dotenv import load_dotenv

# Add these imports for timezone correction
from dateutil import parser
import pytz

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
load_dotenv()
logger = logging.getLogger("easydoai.agent")
logger.setLevel(logging.INFO)


class AgentState(TypedDict):
    messages: Sequence[BaseMessage]
    next_action: str
    tool_results: List[Any]


class EasydoAgent:
    """Main agent using LangGraph for easydo.ai"""

    def __init__(self):
        logger.info("Initializing EasydoAgent")
        self.llm = ChatAnthropic(
            model="claude-3-opus-20240229",
            temperature=0.7,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        logger.info("Loaded Claude model for LLM.")
        self.tools = get_tools()
        logger.info(f"Loaded tools: {list(tool.name for tool in self.tools)}")
        self.tools_by_name = {tool.name: tool for tool in self.tools}
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        logger.info("Bound tools to LLM.")
        self.graph = self._build_graph()
        logger.info("LangGraph workflow built.")

    def _build_graph(self):
        logger.info("Building LangGraph workflow...")
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tools_node)
        workflow.add_node("final", self._final_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent", self._should_use_tools, {"tools": "tools", "final": "final"}
        )
        workflow.add_edge("tools", "agent")
        workflow.add_edge("final", END)
        logger.info("Workflow graph nodes and edges set.")
        return workflow.compile()

    def _agent_node(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Entering agent node.")
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            current_date = datetime.now().strftime("%B %d, %Y")
            system_message = SystemMessage(
                content=f"You are easydo.ai, an agentic productivity assistant. Today's date is {current_date}."
            )
            messages = [system_message] + list(messages)
            logger.info("Added system message to conversation.")
        logger.info(f"Messages to LLM: {[m.content for m in messages]}")
        response = self.llm_with_tools.invoke(messages)
        logger.info(f"LLM response: {getattr(response, 'content', str(response))}")
        has_tool_calls = hasattr(response, "tool_calls") and response.tool_calls
        if has_tool_calls:
            logger.info(
                f"LLM requested tool calls: {[tc['name'] for tc in response.tool_calls]}"
            )
        else:
            logger.info("LLM did not request any tool calls.")
        return {
            "messages": messages + [response],
            "next_action": "tools" if has_tool_calls else "final",
        }

    def _ensure_iso_with_tz(self, dt_str, tz_str):
        """Ensure datetime string has timezone info, else append from tz_str."""
        try:
            dt = parser.parse(dt_str)
            if not dt.tzinfo:
                tz = pytz.timezone(tz_str)
                dt = tz.localize(dt)
            return dt.isoformat()
        except Exception as e:
            logger.warning(
                f"Could not parse or localize datetime '{dt_str}' with tz '{tz_str}': {e}"
            )
            return dt_str  # fallback to original

    def _tools_node(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Entering tools node.")
        messages = state["messages"]
        last_message = messages[-1]
        tool_messages = []
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]
                logger.info(f"Processing tool call: {tool_name} with args: {tool_args}")
                # --- PATCH: Fix Google Calendar datetime strings if needed ---
                if (
                    tool_name == "google_calendar_mcp"
                    and tool_args.get("tool") == "create-event"
                ):
                    args = tool_args.get("args", {})
                    tz = args.get("timeZone", "America/New_York")
                    for key in ["start", "end"]:
                        val = args.get(key)
                        if (
                            isinstance(val, str)
                            and "T" in val
                            and ("Z" not in val and "+" not in val and "-" not in val)
                        ):
                            args[key] = self._ensure_iso_with_tz(val, tz)
                    tool_args["args"] = args
                # -----------------------------------------------------------
                if tool_name in self.tools_by_name:
                    tool = self.tools_by_name[tool_name]
                    try:
                        result = tool.func(**tool_args)
                        logger.info(
                            f"Tool '{tool_name}' executed successfully. Result: {result}"
                        )

                        def json_encoder(obj):
                            if isinstance(obj, (datetime, date)):
                                return obj.isoformat()
                            raise TypeError(
                                f"Object of type {type(obj)} is not JSON serializable"
                            )

                        tool_message = ToolMessage(
                            content=json.dumps(result, default=json_encoder),
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                        tool_messages.append(tool_message)
                    except Exception as e:
                        logger.error(f"Error executing tool '{tool_name}': {e}")
                        tool_message = ToolMessage(
                            content=json.dumps({"error": str(e)}),
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                        tool_messages.append(tool_message)
                else:
                    logger.error(f"Tool '{tool_name}' not found.")
                    tool_message = ToolMessage(
                        content=json.dumps({"error": "Tool not found"}),
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                    tool_messages.append(tool_message)
        else:
            logger.info("No tool calls to process in tools node.")
        return {"messages": messages + tool_messages, "tool_results": []}

    def _final_node(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Entering final node.")
        return state

    def _should_use_tools(self, state: AgentState) -> str:
        logger.info(
            f"Deciding next action based on state: {state.get('next_action', 'final')}"
        )
        return state.get("next_action", "final")

    async def process_message(
        self, user_input: str, conversation_history: List[BaseMessage] = None
    ) -> str:
        logger.info(f"Processing user message: {user_input}")
        if conversation_history is None:
            conversation_history = []
        messages = conversation_history + [HumanMessage(content=user_input)]
        logger.info(f"Initial state for graph: {messages}")
        initial_state = {"messages": messages, "tool_results": [], "next_action": ""}
        final_state = await self.graph.ainvoke(initial_state)
        logger.info(f"Final state after graph execution: {final_state}")
        for message in reversed(final_state["messages"]):
            if isinstance(message, AIMessage):
                logger.info(f"Final AI response: {message.content}")
                return message.content
        logger.warning("No AIMessage found in final state.")
        return "I'm sorry, I couldn't generate a response."
