"""
ARGUS Platform — Search MCP Server
Provides web search capability to ADK agents via MCP protocol.
Uses DuckDuckGo as primary (no API key required) with Tavily fallback.
"""

from __future__ import annotations

import json
from typing import List, Dict, Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

from app.config import settings


app = Server("argus-search-mcp")


@app.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(
        tools=[
            Tool(
                name="web_search",
                description=(
                    "Search the web for current information about disaster events, "
                    "infrastructure incidents, emergency guidelines, or scientific data. "
                    "Use for real-time context when analyzing incidents."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query string",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 5)",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="search_disaster_data",
                description=(
                    "Specialized search for disaster databases, FEMA, USGS, NOAA, "
                    "and emergency management resources."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "disaster_type": {
                            "type": "string",
                            "description": "Type of disaster to search for",
                        },
                        "location": {
                            "type": "string",
                            "description": "Geographic location (optional)",
                        },
                        "year_range": {
                            "type": "string",
                            "description": "Year or range, e.g. '2020' or '2018-2023'",
                        },
                    },
                    "required": ["disaster_type"],
                },
            ),
        ]
    )


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    if name == "web_search":
        return await _duckduckgo_search(arguments["query"], arguments.get("max_results", 5))

    elif name == "search_disaster_data":
        disaster_type = arguments["disaster_type"]
        location = arguments.get("location", "")
        year_range = arguments.get("year_range", "")

        query_parts = [f"{disaster_type} disaster incident data"]
        if location:
            query_parts.append(location)
        if year_range:
            query_parts.append(year_range)
        query_parts.append("site:fema.gov OR site:usgs.gov OR site:noaa.gov OR site:ready.gov")

        query = " ".join(query_parts)
        return await _duckduckgo_search(query, 5)

    return CallToolResult(
        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
        isError=True,
    )


async def _duckduckgo_search(query: str, max_results: int) -> CallToolResult:
    """
    Search using DuckDuckGo Instant Answer API (no API key required).
    Falls back to Tavily if TAVILY_API_KEY is configured.
    """
    # Try Tavily first if configured
    if settings.TAVILY_API_KEY:
        try:
            return await _tavily_search(query, max_results)
        except Exception as e:
            import logging
            logging.warning(f"Tavily search failed: {e}. Falling back to DuckDuckGo.")
            pass  # Fall back to DuckDuckGo

    try:
        import httpx

        # DuckDuckGo HTML search (scraping-free approach via instant answers)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_redirect": "1",
                    "no_html": "1",
                    "skip_disambig": "1",
                },
                headers={"User-Agent": "ARGUS Risk Platform/1.0"},
            )
            data = response.json()

        results: List[Dict[str, Any]] = []

        # Abstract (if available)
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", "DuckDuckGo Summary"),
                "snippet": data["AbstractText"],
                "url": data.get("AbstractURL", ""),
                "source": data.get("AbstractSource", ""),
            })

        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append({
                    "title": topic.get("Text", "")[:100],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                    "source": "DuckDuckGo",
                })

        if not results:
            # If DDG instant answers gives nothing, return guidance
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Search performed for: '{query}'\n"
                         "No instant results found. "
                         "Configure TAVILY_API_KEY for full web search capability.\n"
                         "Proceeding with knowledge base data only.",
                )]
            )

        formatted = json.dumps(results[:max_results], indent=2)
        return CallToolResult(content=[TextContent(type="text", text=formatted)])

    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Search unavailable: {e}. Proceeding with internal knowledge base only.",
            )]
        )


async def _tavily_search(query: str, max_results: int) -> CallToolResult:
    """Search using Tavily API (requires TAVILY_API_KEY)."""
    import httpx

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.TAVILY_API_KEY,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            },
        )
        data = response.json()

    results = [
        {
            "title": r.get("title", ""),
            "snippet": r.get("content", "")[:500],
            "url": r.get("url", ""),
            "score": r.get("score", 0),
            "source": "Tavily",
        }
        for r in data.get("results", [])
    ]

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(results, indent=2))]
    )


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
