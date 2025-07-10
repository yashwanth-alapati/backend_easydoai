from langchain.tools import Tool
from pydantic import BaseModel, Field
from typing import Any, Dict
import asyncio
from services.calendar_lambda_service import CalendarLambdaService

# Initialize calendar Lambda service
calendar_lambda_service = CalendarLambdaService()


class GoogleCalendarMCPInput(BaseModel):
    tool: str = Field(
        description="The Google Calendar tool to call, e.g. 'create-event', 'list-calendars', etc."
    )
    args: Dict[str, Any] = Field(description="Arguments for the Google Calendar tool.")


def google_calendar_mcp_func(tool: str, args: Dict[str, Any]) -> Any:
    """
    Enhanced Google Calendar function that integrates with Lambda and OAuth
    Maps old MCP tool calls to new Lambda-based calendar service
    """

    async def run():
        try:
            # Extract user_id (should be auto-injected by agent)
            user_id = args.get("user_id")
            if not user_id:
                return {
                    "status": "error",
                    "message": "user_id is required for calendar operations",
                }

            # Map old tool names to new Lambda tool names
            tool_mapping = {
                "list-calendars": "list_calendars",
                "list-events": "list_events",
                "create-event": "create_event",
                "update-event": "update_event",
                "delete-event": "delete_event",
            }

            lambda_tool_name = tool_mapping.get(tool, tool)

            if tool == "list-calendars":
                result = await calendar_lambda_service.call_calendar_tool(
                    lambda_tool_name, user_id
                )

            elif tool == "list-events":
                result = await calendar_lambda_service.call_calendar_tool(
                    lambda_tool_name,
                    user_id,
                    calendar_id=args.get("calendarId", "primary"),
                    max_results=args.get("maxResults", 10),
                    time_min=args.get("timeMin"),
                    time_max=args.get("timeMax"),
                )

            elif tool == "create-event":
                # Map old argument names to new ones
                result = await calendar_lambda_service.call_calendar_tool(
                    lambda_tool_name,
                    user_id,
                    summary=args.get("summary"),
                    start_time=args.get("start"),
                    end_time=args.get("end"),
                    calendar_id=args.get("calendarId", "primary"),
                    description=args.get("description"),
                    location=args.get("location"),
                    attendees=[
                        attendee.get("email")
                        for attendee in args.get("attendees", [])
                        if attendee.get("email")
                    ],
                )

            elif tool == "update-event":
                result = await calendar_lambda_service.call_calendar_tool(
                    lambda_tool_name,
                    user_id,
                    event_id=args.get("eventId"),
                    calendar_id=args.get("calendarId", "primary"),
                    summary=args.get("summary"),
                    start_time=args.get("start"),
                    end_time=args.get("end"),
                    description=args.get("description"),
                    location=args.get("location"),
                )

            elif tool == "delete-event":
                result = await calendar_lambda_service.call_calendar_tool(
                    lambda_tool_name,
                    user_id,
                    event_id=args.get("eventId"),
                    calendar_id=args.get("calendarId", "primary"),
                )

            else:
                return {
                    "status": "error",
                    "message": (
                        f"Unknown calendar tool: {tool}. "
                        "Available: list-calendars, list-events, create-event, "
                        "update-event, delete-event"
                    ),
                }

            return result

        except Exception as e:
            return {"status": "error", "message": f"Calendar tool error: {str(e)}"}

    return asyncio.run(run())


# Updated tool descriptions for the new Lambda-based system
GOOGLE_CALENDAR_TOOLS = [
    {
        "name": "list-calendars",
        "description": "List all available calendars for the user.",
        "args": {},
    },
    {
        "name": "list-events",
        "description": "List events from a calendar.",
        "args": {
            "calendarId": "string (use 'primary' for main calendar, default: 'primary')",
            "maxResults": "integer (max events to return, default: 10)",
            "timeMin": "ISO datetime string (optional, start time filter)",
            "timeMax": "ISO datetime string (optional, end time filter)",
        },
    },
    {
        "name": "create-event",
        "description": "Create a new calendar event.",
        "args": {
            "calendarId": "string (use 'primary' for main calendar, default: 'primary')",
            "summary": "string (title of the event, required)",
            "description": "string (optional, event description)",
            "start": "ISO datetime string (event start time, required)",
            "end": "ISO datetime string (event end time, required)",
            "location": "string (optional, event location)",
            "attendees": "array of {email: string} (optional, attendee list)",
        },
    },
    {
        "name": "update-event",
        "description": "Update an existing calendar event.",
        "args": {
            "calendarId": "string (default: 'primary')",
            "eventId": "string (required, ID of event to update)",
            "summary": "string (optional, new title)",
            "description": "string (optional, new description)",
            "start": "ISO datetime string (optional, new start time)",
            "end": "ISO datetime string (optional, new end time)",
            "location": "string (optional, new location)",
        },
    },
    {
        "name": "delete-event",
        "description": "Delete a calendar event.",
        "args": {
            "calendarId": "string (default: 'primary')",
            "eventId": "string (required, ID of event to delete)",
        },
    },
]


def build_tools_prompt(tools):
    import json

    return "\n".join(
        f"- {tool['name']}: {tool['description']}\n  Arguments: {json.dumps(tool['args'], indent=2)}"
        for tool in tools
    )


GOOGLE_CALENDAR_SYSTEM_PROMPT = (
    "You have access to the following Google Calendar tools via Lambda MCP:\n"
    f"{build_tools_prompt(GOOGLE_CALENDAR_TOOLS)}\n"
    "These tools integrate with the user's Google Calendar. If authentication is required, "
    "the system will provide an authorization URL. Always include user_id in tool calls."
)


def get_tool() -> Tool:
    return Tool(
        name="google_calendar_mcp",
        description=GOOGLE_CALENDAR_SYSTEM_PROMPT,
        func=google_calendar_mcp_func,
        args_schema=GoogleCalendarMCPInput,
    )
