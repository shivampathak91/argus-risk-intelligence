"""
ARGUS Platform — Filesystem MCP Server
Provides file read/write/list tools to ADK agents via MCP protocol.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)

from app.config import settings


app = Server("argus-filesystem-mcp")

ALLOWED_BASE = settings.UPLOAD_DIR.resolve()


def _safe_path(relative_path: str) -> Path:
    """Resolve and validate that the path is within the uploads directory."""
    resolved = (ALLOWED_BASE / relative_path).resolve()
    if not str(resolved).startswith(str(ALLOWED_BASE)):
        raise ValueError(f"Access denied: path '{relative_path}' is outside uploads directory")
    return resolved


@app.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(
        tools=[
            Tool(
                name="read_file",
                description="Read the contents of an uploaded file by its relative path within the uploads directory.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from uploads root (e.g., 'txts/report.txt' or 'images/photo.jpg')",
                        }
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="list_files",
                description="List all files in a subdirectory of the uploads directory.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Subdirectory name: 'images', 'pdfs', 'csvs', 'txts', or 'reports'",
                            "enum": ["images", "pdfs", "csvs", "txts", "reports"],
                        }
                    },
                    "required": ["directory"],
                },
            ),
            Tool(
                name="write_file",
                description="Write text content to a file in the reports directory.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Filename to write (will be placed in uploads/reports/)",
                        },
                        "content": {
                            "type": "string",
                            "description": "Text content to write",
                        },
                    },
                    "required": ["filename", "content"],
                },
            ),
            Tool(
                name="get_file_info",
                description="Get metadata about a file (size, type, modification time).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path from uploads root"},
                    },
                    "required": ["path"],
                },
            ),
        ]
    )


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    if name == "read_file":
        path = _safe_path(arguments["path"])
        if not path.exists():
            return CallToolResult(
                content=[TextContent(type="text", text=f"ERROR: File not found: {arguments['path']}")],
                isError=True,
            )
        # Text files: read as UTF-8
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return CallToolResult(content=[TextContent(type="text", text=content)])
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"ERROR reading file: {e}")],
                isError=True,
            )

    elif name == "list_files":
        directory = arguments["directory"]
        dir_path = _safe_path(directory)
        if not dir_path.is_dir():
            return CallToolResult(
                content=[TextContent(type="text", text=f"Directory '{directory}' does not exist")],
            )
        files = [f.name for f in dir_path.iterdir() if f.is_file()]
        listing = "\n".join(sorted(files)) if files else "(empty)"
        return CallToolResult(content=[TextContent(type="text", text=listing)])

    elif name == "write_file":
        filename = arguments["filename"]
        content = arguments["content"]
        # Only allow writes to reports directory
        target = _safe_path(f"reports/{filename}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Successfully wrote {len(content)} chars to reports/{filename}")]
        )

    elif name == "get_file_info":
        path = _safe_path(arguments["path"])
        if not path.exists():
            return CallToolResult(
                content=[TextContent(type="text", text=f"ERROR: File not found: {arguments['path']}")],
                isError=True,
            )
        stat = path.stat()
        import datetime
        info = (
            f"Path: {arguments['path']}\n"
            f"Size: {stat.st_size} bytes\n"
            f"Modified: {datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()}\n"
            f"Extension: {path.suffix}\n"
        )
        return CallToolResult(content=[TextContent(type="text", text=info)])

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
