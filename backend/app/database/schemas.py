"""
ARGUS Platform — Pydantic Schemas
Request/Response models for all API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Base ──────────────────────────────────────────────────────────────────────

class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, numbers, underscores, and hyphens")
        return v.lower()


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(TimestampMixin):
    id: str
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool


# ── Incidents ─────────────────────────────────────────────────────────────────

class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    incident_type: Optional[str] = "unknown"
    description: Optional[str] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class IncidentResponse(TimestampMixin):
    id: str
    title: str
    description: Optional[str]
    incident_type: str
    risk_level: Optional[str]
    confidence_score: Optional[float]
    location_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    is_demo: bool
    created_by: Optional[str]


class IncidentDetail(IncidentResponse):
    uploads: List["UploadResponse"] = []
    workflows: List["WorkflowResponse"] = []
    reports: List["ReportResponse"] = []
    recommendations: List["RecommendationResponse"] = []
    debates: List["DebateResponse"] = []


# ── Uploads ───────────────────────────────────────────────────────────────────

class UploadResponse(TimestampMixin):
    id: str
    incident_id: str
    filename: str
    original_filename: str
    upload_type: str
    file_size: int
    mime_type: str
    processed: bool
    extraction_summary: Optional[str]


# ── Workflows ─────────────────────────────────────────────────────────────────

class WorkflowTrigger(BaseModel):
    incident_id: str


class AgentStep(BaseModel):
    agent: str
    status: str  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    output_summary: Optional[str] = None
    error: Optional[str] = None


class WorkflowResponse(TimestampMixin):
    id: str
    incident_id: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    agent_steps: Optional[List[Dict[str, Any]]]
    error_message: Optional[str]
    total_duration_seconds: Optional[float]


# ── Reports ───────────────────────────────────────────────────────────────────

class ReportResponse(TimestampMixin):
    id: str
    incident_id: str
    workflow_id: Optional[str]
    title: str
    executive_summary: Optional[str]
    risk_analysis: Optional[str]
    confidence_score: Optional[float]
    risk_level: Optional[str]
    timeline: Optional[List[Dict[str, Any]]]
    data_sources: Optional[List[str]]
    pdf_path: Optional[str]


# ── Recommendations ───────────────────────────────────────────────────────────

class RecommendationResponse(TimestampMixin):
    id: str
    incident_id: str
    priority: int
    action: str
    rationale: str
    evidence: Optional[List[str]]
    contributing_agents: Optional[List[str]]
    confidence_score: Optional[float]
    historical_matches: Optional[List[Dict[str, Any]]]
    estimated_impact: Optional[str]
    time_sensitivity: Optional[str]


# ── Debates ───────────────────────────────────────────────────────────────────

class DebateTurn(BaseModel):
    agent: str
    position: str
    argument: str
    confidence: float
    evidence: Optional[List[str]] = None


class DebateResponse(TimestampMixin):
    id: str
    incident_id: str
    workflow_id: Optional[str]
    topic: str
    turns: Optional[List[Dict[str, Any]]]
    final_decision: Optional[str]
    decision_rationale: Optional[str]
    decided_by: str
    outcome_confidence: Optional[float]


# ── Demo Mode ─────────────────────────────────────────────────────────────────

class DemoScenario(BaseModel):
    id: str
    name: str
    description: str
    incident_type: str
    preview_image: Optional[str] = None


class DemoLaunch(BaseModel):
    scenario_id: str


# ── WebSocket Events ──────────────────────────────────────────────────────────

class WSEvent(BaseModel):
    """WebSocket message envelope for live agent timeline."""
    event_type: str  # agent_started, agent_completed, agent_failed, debate_turn, workflow_done
    workflow_id: str
    incident_id: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Knowledge Graph ───────────────────────────────────────────────────────────

class KnowledgeGraphNode(BaseModel):
    id: str
    label: str
    node_type: str  # incident, recommendation, report, asset, historical
    properties: Optional[Dict[str, Any]] = None


class KnowledgeGraphEdge(BaseModel):
    source: str
    target: str
    relationship: str  # caused_by, related_to, generated, addresses


class KnowledgeGraphResponse(BaseModel):
    nodes: List[KnowledgeGraphNode]
    edges: List[KnowledgeGraphEdge]


# ── Simulation ────────────────────────────────────────────────────────────────

class SimulationScenario(BaseModel):
    name: str
    description: str
    parameter_changes: Dict[str, Any]  # e.g., {"rainfall_mm": 300, "repair_delay_days": 30}


class SimulationRequest(BaseModel):
    incident_id: str
    scenarios: List[SimulationScenario]


class SimulationOutcome(BaseModel):
    scenario_name: str
    predicted_risk_level: str
    probability: float
    affected_population: Optional[int]
    infrastructure_impact: Optional[str]
    economic_impact_usd: Optional[float]
    recommended_actions: List[str]
    confidence: float
    reasoning: str


class SimulationResponse(BaseModel):
    incident_id: str
    base_risk_level: str
    outcomes: List[SimulationOutcome]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    gemini_configured: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
