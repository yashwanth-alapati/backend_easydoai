from langchain.tools import Tool
from pydantic import BaseModel, Field
from typing import Any, Dict
import asyncio
from contextlib import AsyncExitStack  # <-- Add this import!
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class GmailMCPInput(BaseModel):
    tool: str = Field(description="The Gmail MCP tool to call, e.g. 'send_email', 'search_emails', etc.")
    args: Dict[str, Any] = Field(description="Arguments for the Gmail MCP tool.")

def gmail_mcp_func(tool: str, args: Dict[str, Any]) -> Any:
    async def run():
        async with AsyncExitStack() as stack:
            server_params = StdioServerParameters(
                command="npx",
                args=["@gongrzhe/server-gmail-autoauth-mcp"],
                env=None
            )
            stdio_transport = await stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport
            session = await stack.enter_async_context(ClientSession(stdio, write))
            await session.initialize()
            result = await session.call_tool(tool, args)
            # Convert result to plain dict or string
            if hasattr(result, "content"):
                # If result.content is a list of TextContent, join their text
                if isinstance(result.content, list):
                    return "\n".join(
                        getattr(item, "text", str(item)) for item in result.content
                    )
                # If it's a single TextContent
                return getattr(result.content, "text", str(result.content))
            return str(result)
    return asyncio.run(run())

def get_tool() -> Tool:
    return Tool(
        name="gmail_mcp",
        description="Call any Gmail MCP tool (send, search, label, etc). Args: tool (str), args (dict).",
        func=gmail_mcp_func,
        args_schema=GmailMCPInput
    )