"""
ARGUS Platform — SQLite MCP Server
Provides database query tools to ADK agents via MCP protocol.
Read-only access for knowledge retrieval; write access via DB session only.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

from app.config import settings


app = Server("argus-sqlite-mcp")

DB_PATH = str(settings.DATABASE_URL).replace("sqlite:///", "")


def _query_db(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute a SELECT query and return rows as dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    finally:
        conn.close()


@app.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(
        tools=[
            Tool(
                name="search_knowledge_base",
                description=(
                    "Search the historical incidents knowledge base for past events "
                    "similar to the current incident. Returns relevant historical data "
                    "including outcomes, lessons learned, and economic impact."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "incident_type": {
                            "type": "string",
                            "description": "Type of incident to match",
                            "enum": [
                                "bridge_failure", "urban_flood", "wildfire",
                                "power_grid_failure", "earthquake", "landslide", "unknown"
                            ],
                        },
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keywords to match in description and lessons learned",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 5)",
                            "default": 5,
                        },
                    },
                    "required": ["incident_type"],
                },
            ),
            Tool(
                name="get_incident_history",
                description="Retrieve all past incidents of a given type for trend analysis.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "incident_type": {"type": "string"},
                        "risk_level": {
                            "type": "string",
                            "description": "Filter by risk level",
                            "enum": ["low", "medium", "high", "critical"],
                        },
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["incident_type"],
                },
            ),
            Tool(
                name="get_recommendations_history",
                description=(
                    "Get past recommendations made for similar incidents. "
                    "Useful for recommendation consistency and historical comparison."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "incident_type": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["incident_type"],
                },
            ),
            Tool(
                name="get_knowledge_entry",
                description="Get a single knowledge base entry by its ID.",
                inputSchema={
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"],
                },
            ),
        ]
    )


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    try:
        if name == "search_knowledge_base":
            incident_type = arguments["incident_type"]
            keywords = arguments.get("keywords", [])
            limit = min(arguments.get("limit", 5), 20)

            # Base query filtered by incident type
            rows = _query_db(
                "SELECT * FROM knowledge_base WHERE incident_type = ? ORDER BY year DESC LIMIT ?",
                (incident_type, limit * 2),  # Fetch extra for keyword filtering
            )

            # Keyword-based relevance ranking
            if keywords:
                def relevance(row: dict) -> int:
                    text = f"{row.get('description', '')} {row.get('lessons_learned', '')} {row.get('title', '')}".lower()
                    return sum(1 for kw in keywords if kw.lower() in text)

                rows.sort(key=relevance, reverse=True)

            rows = rows[:limit]
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(rows, default=str, indent=2))]
            )

        elif name == "get_incident_history":
            incident_type = arguments["incident_type"]
            risk_level = arguments.get("risk_level")
            limit = min(arguments.get("limit", 10), 50)

            if risk_level:
                rows = _query_db(
                    "SELECT * FROM incidents WHERE incident_type = ? AND risk_level = ? ORDER BY created_at DESC LIMIT ?",
                    (incident_type, risk_level, limit),
                )
            else:
                rows = _query_db(
                    "SELECT id, title, incident_type, risk_level, confidence_score, location_name, created_at "
                    "FROM incidents WHERE incident_type = ? ORDER BY created_at DESC LIMIT ?",
                    (incident_type, limit),
                )

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(rows, default=str, indent=2))]
            )

        elif name == "get_recommendations_history":
            incident_type = arguments["incident_type"]
            limit = min(arguments.get("limit", 10), 50)

            rows = _query_db(
                """
                SELECT r.action, r.rationale, r.confidence_score, r.time_sensitivity,
                       i.incident_type, i.risk_level, i.title
                FROM recommendations r
                JOIN incidents i ON r.incident_id = i.id
                WHERE i.incident_type = ?
                ORDER BY r.confidence_score DESC
                LIMIT ?
                """,
                (incident_type, limit),
            )
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(rows, default=str, indent=2))]
            )

        elif name == "get_knowledge_entry":
            rows = _query_db(
                "SELECT * FROM knowledge_base WHERE id = ?",
                (arguments["id"],),
            )
            if not rows:
                return CallToolResult(
                    content=[TextContent(type="text", text="Entry not found")],
                    isError=True,
                )
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(rows[0], default=str, indent=2))]
            )

    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Database error: {e}")],
            isError=True,
        )

    return CallToolResult(
        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
        isError=True,
    )


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
