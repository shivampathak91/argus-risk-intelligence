"""
ARGUS Platform — SQLAlchemy ORM Models
All 8 database tables as specified in the AEGIS brief.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship


class Base(DeclarativeBase):
    """Shared base for all ORM models."""

    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ── Enumerations ──────────────────────────────────────────────────────────────

class UserRole(str, PyEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class IncidentType(str, PyEnum):
    BRIDGE_FAILURE = "bridge_failure"
    URBAN_FLOOD = "urban_flood"
    WILDFIRE = "wildfire"
    POWER_GRID_FAILURE = "power_grid_failure"
    EARTHQUAKE = "earthquake"
    LANDSLIDE = "landslide"
    UNKNOWN = "unknown"


class RiskLevel(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UploadType(str, PyEnum):
    IMAGE = "image"
    PDF = "pdf"
    CSV = "csv"
    TXT = "txt"


class AgentName(str, PyEnum):
    COMMANDER = "commander"
    VISION = "vision"
    OCR = "ocr"
    KNOWLEDGE = "knowledge"
    RISK = "risk"
    SIMULATION = "simulation"
    RECOMMENDATION = "recommendation"
    REPORT = "report"


# ── Models ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = Column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = Column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = Column(String(255))
    role: Mapped[str] = Column(Enum(UserRole), default=UserRole.ANALYST, nullable=False)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    last_login: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))

    # Relationships
    incidents: Mapped[list["Incident"]] = relationship("Incident", back_populates="created_by_user", lazy="select")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", lazy="select")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = Column(String(500), nullable=False)
    description: Mapped[Optional[str]] = Column(Text)
    incident_type: Mapped[str] = Column(Enum(IncidentType), default=IncidentType.UNKNOWN, nullable=False)
    risk_level: Mapped[Optional[str]] = Column(Enum(RiskLevel))
    confidence_score: Mapped[Optional[float]] = Column(Float)
    location_name: Mapped[Optional[str]] = Column(String(500))
    latitude: Mapped[Optional[float]] = Column(Float)
    longitude: Mapped[Optional[float]] = Column(Float)
    is_demo: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    created_by: Mapped[Optional[str]] = Column(String(36), ForeignKey("users.id"))

    # Relationships
    created_by_user: Mapped[Optional["User"]] = relationship("User", back_populates="incidents")
    uploads: Mapped[list["Upload"]] = relationship("Upload", back_populates="incident", lazy="select")
    workflows: Mapped[list["Workflow"]] = relationship("Workflow", back_populates="incident", lazy="select")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="incident", lazy="select")
    recommendations: Mapped[list["Recommendation"]] = relationship("Recommendation", back_populates="incident", lazy="select")
    debates: Mapped[list["Debate"]] = relationship("Debate", back_populates="incident", lazy="select")
    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="incident", lazy="select")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    name: Mapped[str] = Column(String(500), nullable=False)
    asset_type: Mapped[str] = Column(String(100), nullable=False)  # bridge, road, building, etc.
    status: Mapped[str] = Column(String(50), default="unknown")
    condition_score: Mapped[Optional[float]] = Column(Float)  # 0.0 (critical) to 1.0 (good)
    latitude: Mapped[Optional[float]] = Column(Float)
    longitude: Mapped[Optional[float]] = Column(Float)
    asset_metadata: Mapped[Optional[dict]] = Column(JSON)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="assets")


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    filename: Mapped[str] = Column(String(500), nullable=False)
    original_filename: Mapped[str] = Column(String(500), nullable=False)
    upload_type: Mapped[str] = Column(Enum(UploadType), nullable=False)
    file_path: Mapped[str] = Column(String(1000), nullable=False)
    file_size: Mapped[int] = Column(Integer, nullable=False)
    mime_type: Mapped[str] = Column(String(100), nullable=False)
    processed: Mapped[bool] = Column(Boolean, default=False)
    extraction_summary: Mapped[Optional[str]] = Column(Text)  # AI summary of extracted content

    incident: Mapped["Incident"] = relationship("Incident", back_populates="uploads")


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    status: Mapped[str] = Column(Enum(WorkflowStatus), default=WorkflowStatus.PENDING, nullable=False)
    started_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    agent_steps: Mapped[Optional[list]] = Column(JSON)  # List of {agent, status, started_at, completed_at, output}
    error_message: Mapped[Optional[str]] = Column(Text)
    total_duration_seconds: Mapped[Optional[float]] = Column(Float)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="workflows")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    workflow_id: Mapped[Optional[str]] = Column(String(36), ForeignKey("workflows.id"))
    title: Mapped[str] = Column(String(500), nullable=False)
    executive_summary: Mapped[Optional[str]] = Column(Text)
    risk_analysis: Mapped[Optional[str]] = Column(Text)
    confidence_score: Mapped[Optional[float]] = Column(Float)
    risk_level: Mapped[Optional[str]] = Column(Enum(RiskLevel))
    timeline: Mapped[Optional[list]] = Column(JSON)  # [{time, event}]
    data_sources: Mapped[Optional[list]] = Column(JSON)
    pdf_path: Mapped[Optional[str]] = Column(String(1000))
    full_report_json: Mapped[Optional[dict]] = Column(JSON)  # Complete structured report

    incident: Mapped["Incident"] = relationship("Incident", back_populates="reports")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    workflow_id: Mapped[Optional[str]] = Column(String(36), ForeignKey("workflows.id"))
    priority: Mapped[int] = Column(Integer, nullable=False)  # 1 = highest
    action: Mapped[str] = Column(Text, nullable=False)
    rationale: Mapped[str] = Column(Text, nullable=False)
    evidence: Mapped[Optional[list]] = Column(JSON)  # Supporting evidence items
    contributing_agents: Mapped[Optional[list]] = Column(JSON)
    confidence_score: Mapped[Optional[float]] = Column(Float)
    historical_matches: Mapped[Optional[list]] = Column(JSON)
    estimated_impact: Mapped[Optional[str]] = Column(Text)
    time_sensitivity: Mapped[Optional[str]] = Column(String(50))  # immediate, 24h, 1week, etc.

    incident: Mapped["Incident"] = relationship("Incident", back_populates="recommendations")


class Debate(Base):
    __tablename__ = "debates"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    workflow_id: Mapped[Optional[str]] = Column(String(36), ForeignKey("workflows.id"))
    topic: Mapped[str] = Column(Text, nullable=False)  # The decision being debated
    turns: Mapped[Optional[list]] = Column(JSON)  # [{agent, position, argument, confidence}]
    final_decision: Mapped[Optional[str]] = Column(Text)
    decision_rationale: Mapped[Optional[str]] = Column(Text)
    decided_by: Mapped[str] = Column(String(50), default="commander")
    outcome_confidence: Mapped[Optional[float]] = Column(Float)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="debates")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[str]] = Column(String(36), ForeignKey("users.id"))
    action: Mapped[str] = Column(String(100), nullable=False)
    resource_type: Mapped[Optional[str]] = Column(String(100))
    resource_id: Mapped[Optional[str]] = Column(String(36))
    details: Mapped[Optional[dict]] = Column(JSON)
    ip_address: Mapped[Optional[str]] = Column(String(45))
    user_agent: Mapped[Optional[str]] = Column(String(500))

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")


class KnowledgeBase(Base):
    """Historical incidents for the KnowledgeAgent to query."""
    __tablename__ = "knowledge_base"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_type: Mapped[str] = Column(Enum(IncidentType), nullable=False, index=True)
    title: Mapped[str] = Column(String(500), nullable=False)
    description: Mapped[str] = Column(Text, nullable=False)
    location: Mapped[Optional[str]] = Column(String(500))
    year: Mapped[Optional[int]] = Column(Integer)
    risk_level: Mapped[Optional[str]] = Column(Enum(RiskLevel))
    outcome: Mapped[Optional[str]] = Column(Text)
    lessons_learned: Mapped[Optional[str]] = Column(Text)
    casualties: Mapped[Optional[int]] = Column(Integer)
    economic_damage_usd: Mapped[Optional[float]] = Column(Float)
    keywords: Mapped[Optional[list]] = Column(JSON)  # For keyword matching
