"""
ARGUS Platform — FastAPI Application Entry Point
Configures middleware, routes, WebSocket manager, and startup events.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.audit import AuditLogMiddleware
from app.database.session import init_db
from app.database.schemas import HealthResponse


# ── WebSocket Manager ─────────────────────────────────────────────────────────

class WebSocketManager:
    """Manages WebSocket connections for live agent timeline updates."""

    def __init__(self):
        # workflow_id -> Set of connected WebSocket clients
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, workflow_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if workflow_id not in self._connections:
            self._connections[workflow_id] = set()
        self._connections[workflow_id].add(websocket)

    def disconnect(self, workflow_id: str, websocket: WebSocket) -> None:
        if workflow_id in self._connections:
            self._connections[workflow_id].discard(websocket)
            if not self._connections[workflow_id]:
                del self._connections[workflow_id]

    async def broadcast(self, workflow_id: str, message: str) -> None:
        """Send a message to all clients subscribed to a workflow."""
        if workflow_id not in self._connections:
            return
        dead: Set[WebSocket] = set()
        for ws in list(self._connections[workflow_id]):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._connections[workflow_id].discard(ws)

    async def broadcast_all(self, message: str) -> None:
        """Broadcast to all connected clients."""
        for workflow_id in list(self._connections.keys()):
            await self.broadcast(workflow_id, message)


ws_manager = WebSocketManager()


# ── Application Lifecycle ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "ARGUS is an AI-powered Early Warning & Risk Intelligence Platform. "
        "It analyzes disaster and infrastructure incidents using multiple AI agents "
        "with explainable AI, simulation, and professional reporting."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.add_middleware(AuditLogMiddleware)

# ── Routes ────────────────────────────────────────────────────────────────────

from app.api.routes import auth, incidents, uploads, workflows, reports, demo

app.include_router(auth.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(workflows.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(demo.router, prefix="/api/v1")


# ── WebSocket Endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws/workflow/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    """
    WebSocket endpoint for real-time agent pipeline progress.
    Clients subscribe to a workflow_id and receive events as agents execute.
    
    Events:
    - workflow_started: Pipeline has begun
    - agent_started: An agent has started processing
    - agent_completed: An agent finished successfully
    - agent_failed: An agent encountered an error
    - debate_resolved: Commander resolved an agent conflict
    - phase_complete: A pipeline phase completed
    - report_ready: Report has been generated
    - workflow_completed: Full pipeline is done
    """
    await ws_manager.connect(workflow_id, websocket)
    try:
        # Send current workflow state on connect
        from app.database.session import get_db
        from app.database.models import Workflow

        with get_db() as db:
            wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if wf:
                await websocket.send_text(json.dumps({
                    "event_type": "connection_established",
                    "workflow_id": workflow_id,
                    "incident_id": wf.incident_id,
                    "data": {
                        "status": wf.status,
                        "agent_steps": wf.agent_steps,
                    },
                    "timestamp": wf.created_at.isoformat() if wf.created_at else None,
                }))

        # Keep connection alive until client disconnects
        while True:
            try:
                data = await websocket.receive_text()
                # Echo ping/pong for keep-alive
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(workflow_id, websocket)


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check() -> dict:
    """Check platform health and configuration status."""
    from app.database.session import engine

    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "database": db_status,
        "gemini_configured": bool(settings.GOOGLE_API_KEY),
    }


@app.get("/", tags=["System"])
def root():
    """ARGUS API root."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
    }
