from langchain.tools import Tool
from tavily import TavilyClient
import os
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class WebSearchInput(BaseModel):
    query: str = Field(description="The search query string")


def web_search_func(query: str) -> List[Dict[str, Any]]:
    """
    Search the web using Tavily API with both search and extract capabilities.
    First searches for results, then extracts full content from top 3 URLs.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return [{"error": "Tavily API key not configured"}]

    try:
        # Initialize Tavily client
        tavily_client = TavilyClient(api_key=api_key)

        # Perform initial search
        logger.info(f"🔍 Performing Tavily search for: {query}")
        search_response = tavily_client.search(
            query=query,
            search_depth="advanced",  # Get more comprehensive results
            max_results=5,  # Get top 5 search results
            include_answer=True,  # Include AI-generated answer
            include_images=False,  # Skip images to save context
            include_raw_content=False,  # We'll get raw content via extract
        )

        # Extract URLs from top 3 search results for detailed content
        urls_to_extract = []
        search_results = search_response.get("results", [])

        for result in search_results[:3]:  # Only top 3 to manage context
            if result.get("url"):
                urls_to_extract.append(result["url"])

        # Extract full content from top URLs
        extracted_content = []
        if urls_to_extract:
            logger.info(f"📄 Extracting content from {len(urls_to_extract)} URLs")

            for url in urls_to_extract:
                try:
                    extract_response = tavily_client.extract(url)

                    if extract_response.get("results"):
                        for extracted in extract_response["results"]:
                            raw_content = extracted.get("raw_content", "")

                            # Limit content to manage context (max 2000 chars per result)
                            if len(raw_content) > 2000:
                                raw_content = raw_content[:2000] + "..."

                            extracted_content.append(
                                {
                                    "url": url,
                                    "extracted_content": raw_content,
                                    "content_length": len(raw_content),
                                }
                            )

                except Exception as extract_error:
                    logger.warning(
                        f"Failed to extract content from {url}: {extract_error}"
                    )
                    # Continue with other URLs even if one fails
                    continue

        # Combine search results with extracted content
        enhanced_results = []

        # Add the AI-generated answer if available
        if search_response.get("answer"):
            enhanced_results.append(
                {
                    "type": "answer",
                    "title": "AI Generated Answer",
                    "content": search_response["answer"],
                    "url": "",
                    "score": 1.0,
                }
            )

        # Process search results and match with extracted content
        for i, result in enumerate(search_results):
            enhanced_result = {
                "type": "search_result",
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0),
                "favicon": result.get("favicon", ""),
            }

            # Add extracted content if available for this URL
            for extracted in extracted_content:
                if extracted["url"] == result.get("url"):
                    enhanced_result["extracted_content"] = extracted[
                        "extracted_content"
                    ]
                    enhanced_result["has_full_content"] = True
                    break
            else:
                enhanced_result["has_full_content"] = False

            enhanced_results.append(enhanced_result)

        # Add metadata about the search
        search_metadata = {
            "type": "metadata",
            "query": query,
            "total_results": len(search_results),
            "extracted_urls": len(extracted_content),
            "response_time": search_response.get("response_time", "unknown"),
            "search_depth": "advanced",
        }

        # Return results with metadata first, then answer, then enhanced results
        final_results = [search_metadata]
        final_results.extend(enhanced_results)

        logger.info(
            f"✅ Search completed: {len(enhanced_results)} results, {len(extracted_content)} with extracted content"
        )
        return final_results

    except Exception as e:
        logger.error(f"❌ Tavily search error: {e}")
        return [{"error": f"Search failed: {str(e)}"}]


def get_tool() -> Tool:
    return Tool(
        name="web_search",
        description=(
            "Search the web for current information using Tavily Search with content extraction. "
            "This tool performs an advanced web search and extracts full content from the top 3 results "
            "to provide comprehensive information about meetings, events, current affairs, or general knowledge. "
            "Returns both search results and extracted detailed content when available."
        ),
        func=web_search_func,
        args_schema=WebSearchInput,
    )
