"""
ARGUS Platform — PDF MCP Server
Provides PDF text extraction tools to ADK agents via MCP protocol.
Uses PyMuPDF (fitz) for local, high-quality text extraction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

from app.config import settings


app = Server("argus-pdf-mcp")

ALLOWED_BASE = settings.UPLOAD_DIR.resolve()


def _safe_path(relative_path: str) -> Path:
    resolved = (ALLOWED_BASE / relative_path).resolve()
    if not str(resolved).startswith(str(ALLOWED_BASE)):
        raise ValueError("Path traversal detected")
    return resolved


@app.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(
        tools=[
            Tool(
                name="extract_pdf_text",
                description=(
                    "Extract all text content from a PDF file. "
                    "Returns the full text with page numbers and metadata."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from uploads root (e.g., 'pdfs/report.pdf')",
                        }
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="extract_pdf_pages",
                description="Extract text from specific page ranges of a PDF.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "start_page": {
                            "type": "integer",
                            "description": "First page number (1-indexed)",
                            "default": 1,
                        },
                        "end_page": {
                            "type": "integer",
                            "description": "Last page number (1-indexed, inclusive)",
                        },
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="get_pdf_metadata",
                description="Get metadata from a PDF file (title, author, page count, creation date).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="extract_pdf_tables",
                description=(
                    "Attempt to extract tabular data from a PDF. "
                    "Returns detected tables as structured text."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"],
                },
            ),
        ]
    )


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return CallToolResult(
            content=[TextContent(type="text", text="ERROR: PyMuPDF not installed. Run: pip install pymupdf")],
            isError=True,
        )

    try:
        if name == "extract_pdf_text":
            path = _safe_path(arguments["path"])
            if not path.exists():
                return CallToolResult(
                    content=[TextContent(type="text", text=f"ERROR: File not found: {arguments['path']}")],
                    isError=True,
                )

            doc = fitz.open(str(path))
            pages_text: List[str] = []
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                if text:
                    pages_text.append(f"--- Page {page_num} ---\n{text}")

            full_text = "\n\n".join(pages_text)
            doc.close()

            # Truncate if extremely long (>50k chars) to avoid token overload
            if len(full_text) > 50_000:
                full_text = full_text[:50_000] + "\n\n[... truncated for length ...]"

            return CallToolResult(content=[TextContent(type="text", text=full_text)])

        elif name == "extract_pdf_pages":
            path = _safe_path(arguments["path"])
            doc = fitz.open(str(path))
            start = max(0, arguments.get("start_page", 1) - 1)
            end = min(len(doc) - 1, arguments.get("end_page", len(doc)) - 1)

            pages_text = []
            for i in range(start, end + 1):
                text = doc[i].get_text("text").strip()
                pages_text.append(f"--- Page {i + 1} ---\n{text}")

            doc.close()
            return CallToolResult(content=[TextContent(type="text", text="\n\n".join(pages_text))])

        elif name == "get_pdf_metadata":
            path = _safe_path(arguments["path"])
            doc = fitz.open(str(path))
            meta = doc.metadata
            info = {
                "title": meta.get("title", ""),
                "author": meta.get("author", ""),
                "subject": meta.get("subject", ""),
                "creator": meta.get("creator", ""),
                "page_count": len(doc),
                "creation_date": meta.get("creationDate", ""),
                "file_size_bytes": path.stat().st_size,
            }
            doc.close()
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(info, indent=2))]
            )

        elif name == "extract_pdf_tables":
            path = _safe_path(arguments["path"])
            doc = fitz.open(str(path))
            all_tables = []

            for page_num, page in enumerate(doc, start=1):
                # Use PyMuPDF's find_tables if available (v1.23+)
                try:
                    tabs = page.find_tables()
                    for i, table in enumerate(tabs.tables):
                        rows = table.extract()
                        table_text = f"\n[Table {i+1} on Page {page_num}]\n"
                        for row in rows:
                            table_text += " | ".join(str(cell or "").strip() for cell in row) + "\n"
                        all_tables.append(table_text)
                except AttributeError:
                    # Older PyMuPDF — fall back to structured text
                    text = page.get_text("blocks")
                    pass

            doc.close()

            if not all_tables:
                return CallToolResult(
                    content=[TextContent(type="text", text="No tables detected in this PDF.")]
                )

            return CallToolResult(
                content=[TextContent(type="text", text="\n".join(all_tables))]
            )

    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"PDF processing error: {e}")],
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
