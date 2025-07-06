import asyncio
from typing import Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import Anthropic
from dotenv import load_dotenv
import sys

load_dotenv()  # Load environment variables from .env


class GmailMCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()

    async def connect_to_gmail_server(self):
        """Connect to the Gmail AutoAuth MCP server."""
        # Use npx to launch the Gmail MCP server
        server_params = StdioServerParameters(
            command="npx", args=["@gongrzhe/server-gmail-autoauth-mcp"], env=None
        )
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )
        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print(
            "\nConnected to Gmail MCP server with tools:", [tool.name for tool in tools]
        )

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available Gmail tools."""
        messages = [{"role": "user", "content": query}]
        response = await self.session.list_tools()
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )

        tool_results = []
        final_text = []

        for content in response.content:
            if content.type == "text":
                final_text.append(content.text)
            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input
                # Execute Gmail tool call
                result = await self.session.call_tool(tool_name, tool_args)
                tool_results.append({"call": tool_name, "result": result})
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                # Continue conversation with tool results
                if hasattr(content, "text") and content.text:
                    messages.append({"role": "assistant", "content": content.text})
                messages.append({"role": "user", "content": result.content})

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                )
                final_text.append(response.content[0].text)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop."""
        print("\nGmail MCP Client Started!")
        print("Type your Gmail queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == "quit":
                    break
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


async def main():
    client = GmailMCPClient()
    try:
        await client.connect_to_gmail_server()
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
