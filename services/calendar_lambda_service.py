import boto3
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from services.google_oauth import oauth_service

"""
Calendar Lambda MCP Service - integrates Calendar MCP Lambda with OAuth flow
"""

# Load environment variables first
load_dotenv()

logger = logging.getLogger(__name__)


class CalendarLambdaService:
    """Service to interact with Calendar MCP Lambda function"""

    def __init__(self):
        self.lambda_client = boto3.client("lambda", region_name="us-east-1")
        # ✅ Use hardcoded function name like Gmail (no dynamic discovery)
        self.function_name = "LambdaMCPStack-CalendarMCPLambdaC5011EA6-jnbDF1nmxPbQ"

    async def call_calendar_tool(
        self, tool_name: str, user_id: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Call Calendar MCP tool via Lambda
        Returns either:
        - Tool result if authenticated
        - Auth URL if not authenticated
        - Error if something went wrong
        """
        try:
            # Prepare Lambda payload
            payload = {
                "jsonrpc": "2.0",
                "id": "calendar_tool_call",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": {"user_id": user_id, **kwargs},
                },
            }

            # Call Lambda function
            response = self.lambda_client.invoke(
                FunctionName=self.function_name, Payload=json.dumps(payload)
            )

            # Parse response
            result = json.loads(response["Payload"].read())

            # Check if user needs authentication
            if "error" in result:
                error_message = result["error"].get("message", "")
                if "not authenticated" in error_message.lower():
                    # Generate OAuth URL for Calendar
                    auth_data = oauth_service.get_authorization_url("google_calendar", user_id)
                    return {
                        "status": "authentication_required",
                        "message": "Google Calendar access requires authentication. Please visit the authorization URL.",
                        "authorization_url": auth_data["authorization_url"],
                        "state": auth_data["state"],
                    }
                else:
                    return {"status": "error", "message": error_message}

            # Tool executed successfully
            if "result" in result:
                content = result["result"].get("content", [])
                if content and isinstance(content, list) and len(content) > 0:
                    text_content = content[0].get("text", "")
                    try:
                        parsed_content = json.loads(text_content)
                        return {"status": "success", "data": parsed_content}
                    except json.JSONDecodeError:
                        return {"status": "success", "data": text_content}

                return {"status": "success", "data": result["result"]}

            return {
                "status": "error",
                "message": "Unexpected response format from Lambda",
            }

        except Exception as e:
            logger.error(f"Error calling Calendar Lambda: {e}")
            return {
                "status": "error",
                "message": f"Failed to call Calendar service: {str(e)}",
            }

    async def list_calendars(self, user_id: str) -> Dict[str, Any]:
        """List all user's calendars"""
        return await self.call_calendar_tool("list_calendars", user_id=user_id)

    async def create_event(
        self,
        user_id: str,
        summary: str,
        start_time: str,
        end_time: str,
        calendar_id: str = "primary",
        description: str = None,
        location: str = None,
        attendees: list = None,
    ) -> Dict[str, Any]:
        """Create a new calendar event"""
        return await self.call_calendar_tool(
            "create_event",
            user_id=user_id,
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            calendar_id=calendar_id,
            description=description,
            location=location,
            attendees=attendees,
        )

    async def list_available_tools(self) -> Dict[str, Any]:
        """List available Calendar tools from Lambda"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": "list_tools",
                "method": "tools/list",
                "params": {},
            }

            response = self.lambda_client.invoke(
                FunctionName=self.function_name, Payload=json.dumps(payload)
            )

            result = json.loads(response["Payload"].read())

            if "result" in result:
                return {"status": "success", "tools": result["result"].get("tools", [])}

            return {"status": "error", "message": "Failed to list tools"}

        except Exception as e:
            logger.error(f"Error listing Calendar tools: {e}")
            return {"status": "error", "message": f"Failed to list tools: {str(e)}"}


# Global service instance
calendar_lambda_service = CalendarLambdaService()