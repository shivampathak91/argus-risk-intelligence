"""
ARGUS Platform — Incidents Routes
CRUD for incident management.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AnalystUser, CurrentUser, DBSession
from app.database.models import Incident, IncidentType
from app.database.schemas import (
    IncidentCreate,
    IncidentDetail,
    IncidentResponse,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    KnowledgeGraphResponse,
)


router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=List[IncidentResponse])
def list_incidents(
    db: DBSession,
    current_user: CurrentUser,
    incident_type: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    is_demo: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
) -> List[Incident]:
    """List all incidents with optional filtering."""
    query = db.query(Incident)
    if incident_type:
        query = query.filter(Incident.incident_type == incident_type)
    if risk_level:
        query = query.filter(Incident.risk_level == risk_level)
    if is_demo is not None:
        query = query.filter(Incident.is_demo == is_demo)

    return query.order_by(Incident.created_at.desc()).offset(offset).limit(limit).all()


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    body: IncidentCreate,
    db: DBSession,
    current_user: AnalystUser,
) -> Incident:
    """Create a new incident record."""
    incident = Incident(
        title=body.title,
        description=body.description,
        location_name=body.location_name,
        latitude=body.latitude,
        longitude=body.longitude,
        incident_type=str(body.incident_type) if hasattr(body, 'incident_type') and body.incident_type else IncidentType.UNKNOWN.value,
        created_by=current_user.id,
    )
    db.add(incident)
    db.flush()
    return incident


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident(
    incident_id: str,
    db: DBSession,
    current_user: CurrentUser,
) -> Incident:
    """Get full details of a single incident including all related data."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(
    incident_id: str,
    db: DBSession,
    current_user: AnalystUser,
) -> None:
    """Delete an incident and all its related data."""
    from app.database.models import Upload, Workflow, Report, Recommendation, Debate
    from pathlib import Path

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.is_demo:
        raise HTTPException(status_code=400, detail="Demo incidents cannot be deleted")

    # Delete uploads and files
    uploads = db.query(Upload).filter(Upload.incident_id == incident_id).all()
    for upload in uploads:
        file_path = Path(upload.file_path)
        if file_path.exists():
            file_path.unlink()
        db.delete(upload)

    # Delete debates
    db.query(Debate).filter(Debate.incident_id == incident_id).delete()

    # Delete recommendations
    db.query(Recommendation).filter(Recommendation.incident_id == incident_id).delete()

    # Delete reports
    db.query(Report).filter(Report.incident_id == incident_id).delete()

    # Delete workflows
    db.query(Workflow).filter(Workflow.incident_id == incident_id).delete()

    # Delete incident
    db.delete(incident)


@router.get("/{incident_id}/knowledge-graph", response_model=KnowledgeGraphResponse)
def get_knowledge_graph(
    incident_id: str,
    db: DBSession,
    current_user: CurrentUser,
) -> KnowledgeGraphResponse:
    """
    Build and return the knowledge graph for a given incident.
    Connects incident → uploads, recommendations, reports, debates,
    and historical knowledge base matches.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    nodes: List[KnowledgeGraphNode] = []
    edges: List[KnowledgeGraphEdge] = []

    # Root incident node
    nodes.append(KnowledgeGraphNode(
        id=f"incident-{incident.id}",
        label=incident.title,
        node_type="incident",
        properties={
            "risk_level": incident.risk_level,
            "incident_type": incident.incident_type,
            "confidence": incident.confidence_score,
        },
    ))

    # Upload nodes
    for upload in incident.uploads:
        node_id = f"upload-{upload.id}"
        nodes.append(KnowledgeGraphNode(
            id=node_id,
            label=upload.original_filename,
            node_type="upload",
            properties={"type": upload.upload_type, "processed": upload.processed},
        ))
        edges.append(KnowledgeGraphEdge(
            source=f"incident-{incident.id}",
            target=node_id,
            relationship="has_upload",
        ))

    # Recommendation nodes
    for rec in incident.recommendations:
        node_id = f"rec-{rec.id}"
        label = rec.action[:60] + "..." if len(rec.action) > 60 else rec.action
        nodes.append(KnowledgeGraphNode(
            id=node_id,
            label=label,
            node_type="recommendation",
            properties={
                "priority": rec.priority,
                "confidence": rec.confidence_score,
                "time_sensitivity": rec.time_sensitivity,
            },
        ))
        edges.append(KnowledgeGraphEdge(
            source=f"incident-{incident.id}",
            target=node_id,
            relationship="generated",
        ))

    # Report nodes
    for report in incident.reports:
        node_id = f"report-{report.id}"
        nodes.append(KnowledgeGraphNode(
            id=node_id,
            label=report.title,
            node_type="report",
            properties={"risk_level": report.risk_level, "confidence": report.confidence_score},
        ))
        edges.append(KnowledgeGraphEdge(
            source=f"incident-{incident.id}",
            target=node_id,
            relationship="produced",
        ))

    # Debate nodes
    for debate in incident.debates:
        node_id = f"debate-{debate.id}"
        label = debate.topic[:60] + "..." if len(debate.topic) > 60 else debate.topic
        nodes.append(KnowledgeGraphNode(
            id=node_id,
            label=label,
            node_type="debate",
            properties={"final_decision": debate.final_decision, "confidence": debate.outcome_confidence},
        ))
        edges.append(KnowledgeGraphEdge(
            source=f"incident-{incident.id}",
            target=node_id,
            relationship="debated",
        ))

    return KnowledgeGraphResponse(nodes=nodes, edges=edges)
