import boto3
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from services.google_oauth import oauth_service

"""
Gmail Lambda MCP Service - integrates Gmail MCP Lambda with OAuth flow
"""


# Load environment variables first
load_dotenv()


logger = logging.getLogger(__name__)


class GmailLambdaService:
    """Service to interact with Gmail MCP Lambda function"""

    def __init__(self):
        self.lambda_client = boto3.client("lambda", region_name="us-east-1")
        self.function_name = "LambdaMCPStack-GmailMCPLambdaD2EF2F90-M8OUb80rPJ9G"

    async def call_gmail_tool(
        self, tool_name: str, user_id: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Call Gmail MCP tool via Lambda
        Returns either:
        - Tool result if authenticated
        - Auth URL if not authenticated
        - Error if something went wrong
        """
        try:
            # Prepare Lambda payload
            payload = {
                "jsonrpc": "2.0",
                "id": "gmail_tool_call",
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
                    # Generate OAuth URL
                    auth_data = oauth_service.get_authorization_url("gmail", user_id)
                    return {
                        "status": "authentication_required",
                        "message": "Gmail access requires authentication. Please visit the authorization URL.",
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
            logger.error(f"Error calling Gmail Lambda: {e}")
            return {
                "status": "error",
                "message": f"Failed to call Gmail service: {str(e)}",
            }

    async def get_gmail_messages(
        self, user_id: str, query: str = "", max_results: int = 10
    ) -> Dict[str, Any]:
        """Get Gmail messages for a user"""
        return await self.call_gmail_tool(
            "get_gmail_messages", user_id=user_id, query=query, max_results=max_results
        )

    async def send_gmail_message(
        self, user_id: str, to: str, subject: str, body: str
    ) -> Dict[str, Any]:
        """Send Gmail message for a user"""
        return await self.call_gmail_tool(
            "send_gmail_message", user_id=user_id, to=to, subject=subject, body=body
        )

    async def list_available_tools(self) -> Dict[str, Any]:
        """List available Gmail tools from Lambda"""
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
            logger.error(f"Error listing Gmail tools: {e}")
            return {"status": "error", "message": f"Failed to list tools: {str(e)}"}


# Global service instance
gmail_lambda_service = GmailLambdaService()
