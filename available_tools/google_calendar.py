from langchain.tools import Tool
from pydantic import BaseModel, Field
from typing import Any, Dict
import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json
import os

class GoogleCalendarMCPInput(BaseModel):
    tool: str = Field(description="The Google Calendar MCP tool to call, e.g. 'create-event', 'list-events', etc.")
    args: Dict[str, Any] = Field(description="Arguments for the Google Calendar MCP tool.")

def google_calendar_mcp_func(tool: str, args: Dict[str, Any]) -> Any:
    async def run():
        async with AsyncExitStack() as stack:
            script_dir = os.path.dirname(os.path.realpath(__file__))
            # Construct the absolute path to the credentials file
            credentials_path = os.path.abspath(os.path.join(script_dir, "..", "..", "google-calendar-mcp", "gcp-oauth.keys.json"))
            
            server_params = StdioServerParameters(
                command="npx",
                args=["@cocal/google-calendar-mcp"],
                # Pass the absolute path as an environment variable to the tool
                env={
                    "GOOGLE_OAUTH_CREDENTIALS": credentials_path
                }
            )
            stdio_transport = await stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport
            session = await stack.enter_async_context(ClientSession(stdio, write))
            await session.initialize()
            result = await session.call_tool(tool, args)
            # Convert result to plain dict or string
            if hasattr(result, "content"):
                if isinstance(result.content, list):
                    return "\n".join(
                        getattr(item, "text", str(item)) for item in result.content
                    )
                return getattr(result.content, "text", str(result.content))
            return str(result)
    return asyncio.run(run())

# ---- TOOL DEFINITIONS FOR PROMPT ----

GOOGLE_CALENDAR_MCP_TOOLS = [
    {
        "name": "list-calendars",
        "description": "List all available calendars.",
        "args": {}
    },
    {
        "name": "list-events",
        "description": "List events from one or more calendars.",
        "args": {
            "calendarId": "string or array of strings (use 'primary' for main calendar)",
            "timeMin": "ISO datetime string (optional)",
            "timeMax": "ISO datetime string (optional)"
        }
    },
    {
        "name": "search-events",
        "description": "Search for events in a calendar by text query.",
        "args": {
            "calendarId": "string (use 'primary' for main calendar)",
            "query": "string (free text search)",
            "timeMin": "ISO datetime string (optional)",
            "timeMax": "ISO datetime string (optional)"
        }
    },
    {
        "name": "list-colors",
        "description": "List available color IDs and their meanings for calendar events.",
        "args": {}
    },
    {
        "name": "create-event",
        "description": "Create a new calendar event.",
        "args": {
            "calendarId": "string (use 'primary' for main calendar)",
            "summary": "string (title of the event)",
            "description": "string (optional, notes for the event)",
            "start": "ISO datetime string **with timezone** (e.g., 2024-08-15T10:00:00Z or 2024-08-15T10:00:00-07:00). Do NOT omit the timezone.",
            "end": "ISO datetime string **with timezone** (e.g., 2024-08-15T11:00:00Z or 2024-08-15T11:00:00-07:00). Do NOT omit the timezone.",
            "timeZone": "string (IANA timezone, e.g., America/Los_Angeles)",
            "location": "string (optional)",
            "attendees": "array of {email: string} (optional)",
            "colorId": "string (optional, see list-colors)",
            "reminders": "object (optional, see below)",
            "recurrence": "array of strings (optional, RFC5545 format)"
        }
    },
    {
        "name": "update-event",
        "description": "Update an existing calendar event with recurring event modification scope support.",
        "args": {
            "calendarId": "string",
            "eventId": "string",
            "summary": "string (optional, new title)",
            "description": "string (optional, new description)",
            "start": "ISO datetime string (optional, new start time)",
            "end": "ISO datetime string (optional, new end time)",
            "timeZone": "string (IANA timezone, required if modifying start/end or for recurring events)",
            "location": "string (optional, new location)",
            "colorId": "string (optional, new color ID)",
            "attendees": "array of {email: string} (optional, replaces existing attendees)",
            "reminders": "object (optional, new reminder settings)",
            "recurrence": "array of strings (optional, new recurrence rules)",
            "modificationScope": "string (optional, 'single', 'all', or 'future')",
            "originalStartTime": "ISO datetime string (required if modificationScope is 'single')",
            "futureStartDate": "ISO datetime string (required if modificationScope is 'future')"
        }
    },
    {
        "name": "delete-event",
        "description": "Delete a calendar event.",
        "args": {
            "calendarId": "string",
            "eventId": "string"
        }
    },
    {
        "name": "get-freebusy",
        "description": "Retrieve free/busy information for one or more calendars within a time range.",
        "args": {
            "timeMin": "ISO datetime string (start of interval)",
            "timeMax": "ISO datetime string (end of interval)",
            "timeZone": "string (optional, IANA timezone)",
            "groupExpansionMax": "integer (optional, max group expansion)",
            "calendarExpansionMax": "integer (optional, max calendar expansion)",
            "items": "array of {id: string} (calendar or group identifiers)"
        }
    }
]

def build_tools_prompt(tools):
    return "\n".join(
        f"- {tool['name']}: {tool['description']}\n  Arguments: {json.dumps(tool['args'], indent=2)}"
        for tool in tools
    )

GOOGLE_CALENDAR_SYSTEM_PROMPT = (
    "You have access to the following Google Calendar MCP tools:\n"
    f"{build_tools_prompt(GOOGLE_CALENDAR_MCP_TOOLS)}\n"
    "When calling a tool, use the exact argument names and types as shown above."
)

def get_tool() -> Tool:
    return Tool(
        name="google_calendar_mcp",
        description=GOOGLE_CALENDAR_SYSTEM_PROMPT,
        func=google_calendar_mcp_func,
        args_schema=GoogleCalendarMCPInput
    )

# You can now use GOOGLE_CALENDAR_SYSTEM_PROMPT as your system prompt for the LLM.