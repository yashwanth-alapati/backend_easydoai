from langchain.tools import Tool
from pydantic import BaseModel, Field
from typing import Any, Dict
import asyncio
import json
from services.gmail_lambda_service import gmail_lambda_service

class GmailMCPInput(BaseModel):
    action: str = Field(
        description="Gmail action: 'get_messages', 'send_message', or 'list_tools'"
    )
    user_id: str = Field(description="User ID for Gmail access")
    # Optional parameters for different actions
    query: str = Field(default="", description="Search query for get_messages")
    max_results: int = Field(default=10, description="Max results for get_messages")
    to: str = Field(default="", description="Recipient email for send_message")
    subject: str = Field(default="", description="Email subject for send_message")
    body: str = Field(default="", description="Email body for send_message")

def gmail_mcp_func(action: str, user_id: str, **kwargs) -> Any:
    """
    Enhanced Gmail MCP function that integrates with Lambda and OAuth
    """
    async def run():
        try:
            if action == "get_messages":
                result = await gmail_lambda_service.get_gmail_messages(
                    user_id=user_id,
                    query=kwargs.get("query", ""),
                    max_results=kwargs.get("max_results", 10)
                )
            elif action == "send_message":
                if not all([kwargs.get("to"), kwargs.get("subject"), kwargs.get("body")]):
                    return {
                        'status': 'error',
                        'message': 'send_message requires: to, subject, and body'
                    }
                result = await gmail_lambda_service.send_gmail_message(
                    user_id=user_id,
                    to=kwargs["to"],
                    subject=kwargs["subject"],
                    body=kwargs["body"]
                )
            elif action == "list_tools":
                result = await gmail_lambda_service.list_available_tools()
            else:
                return {
                    'status': 'error',
                    'message': f"Unknown action: {action}. Use 'get_messages', 'send_message', or 'list_tools'"
                }
            
            return result
        
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Gmail tool error: {str(e)}"
            }
    
    return asyncio.run(run())

def get_tool() -> Tool:
    return Tool(
        name="gmail_mcp",
        description="Access Gmail via Lambda MCP server. Actions: get_messages (query, max_results), send_message (to, subject, body), list_tools. Always requires user_id.",
        func=gmail_mcp_func,
        args_schema=GmailMCPInput,
    )
