from langchain.tools import Tool
from langchain_community.tools.tavily_search import TavilySearchResults
import os
from pydantic import BaseModel, Field
from typing import List, Dict, Any


class WebSearchInput(BaseModel):
    query: str = Field(description="The search query string")


def web_search_func(query: str) -> List[Dict[str, Any]]:
    """
    Search the web using Tavily API.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return [{"error": "Tavily API key not configured"}]
    search_tool = TavilySearchResults(api_key=api_key)
    try:
        results = search_tool.run(query)
        return results
    except Exception as e:
        return [{"error": str(e)}]


def get_tool() -> Tool:
    return Tool(
        name="web_search",
        description="Search the web for current information about meetings, events, or general knowledge.",
        func=web_search_func,
        args_schema=WebSearchInput,
    )
