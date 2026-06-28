"""
ARGUS Platform — Workflow Routes
Trigger and monitor the multi-agent analysis pipeline.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.deps import AnalystUser, CurrentUser, DBSession
from app.database.models import Incident, Workflow, WorkflowStatus
from app.database.schemas import WorkflowResponse, WorkflowTrigger

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post("/run", response_model=WorkflowResponse, status_code=201)
def trigger_workflow(
    body: WorkflowTrigger,
    background_tasks: BackgroundTasks,
    db: DBSession,
    current_user: AnalystUser,
) -> Workflow:
    """
    Trigger the full multi-agent analysis pipeline for an incident.
    Returns the workflow record immediately; analysis runs in the background.
    """
    logger.info(f"Triggering workflow for incident {body.incident_id}")
    incident = db.query(Incident).filter(Incident.id == body.incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Check for an already-running workflow
    running = (
        db.query(Workflow)
        .filter(
            Workflow.incident_id == body.incident_id,
            Workflow.status == WorkflowStatus.RUNNING,
        )
        .first()
    )
    if running:
        raise HTTPException(
            status_code=409,
            detail=f"Workflow {running.id} is already running for this incident",
        )

    # Validate that there are uploads to process
    if not incident.uploads:
        raise HTTPException(
            status_code=400,
            detail="No files uploaded for this incident. Please upload at least one file first.",
        )

    # Create the workflow record with proper JSON serialization
    workflow = Workflow(
        incident_id=body.incident_id,
        status=WorkflowStatus.PENDING,
    )
    db.add(workflow)
    db.flush()
    workflow_id = workflow.id

    # Set agent_steps after flush to ensure proper JSON handling
    workflow.agent_steps = [
        {"agent": "vision", "status": "pending"},
        {"agent": "ocr", "status": "pending"},
        {"agent": "knowledge", "status": "pending"},
        {"agent": "risk", "status": "pending"},
        {"agent": "simulation", "status": "pending"},
        {"agent": "recommendation", "status": "pending"},
        {"agent": "debate", "status": "pending"},
        {"agent": "report", "status": "pending"},
        {"agent": "commander", "status": "pending"},
    ]
    db.commit()

    # Launch background pipeline
    logger.info(f"Adding background task for workflow {workflow_id}")
    background_tasks.add_task(_run_pipeline, workflow_id=workflow_id, incident_id=body.incident_id)
    logger.info(f"Background task added for workflow {workflow_id}")

    return workflow


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: str,
    db: DBSession,
    current_user: CurrentUser,
) -> Workflow:
    """Get the current status and step details of a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.get("/incident/{incident_id}", response_model=List[WorkflowResponse])
def list_workflows_for_incident(
    incident_id: str,
    db: DBSession,
    current_user: CurrentUser,
) -> List[Workflow]:
    """List all workflows for a given incident."""
    return (
        db.query(Workflow)
        .filter(Workflow.incident_id == incident_id)
        .order_by(Workflow.created_at.desc())
        .all()
    )


async def _run_pipeline(workflow_id: str, incident_id: str) -> None:
    """
    Background task: import and run the Antigravity orchestrator.
    Isolated to avoid import-time side effects.
    """
    logger.info(f"Starting pipeline for workflow {workflow_id}, incident {incident_id}")
    try:
        from app.workflow.orchestrator import run_incident_pipeline

        logger.info(f"Imported orchestrator, calling run_incident_pipeline")
        await run_incident_pipeline(workflow_id=workflow_id, incident_id=incident_id)
        logger.info(f"Pipeline completed for workflow {workflow_id}")
    except Exception as exc:
        logger.error(f"Pipeline failed for workflow {workflow_id}: {exc}", exc_info=True)
        # Update workflow to FAILED on unrecoverable error
        from app.database.session import get_db as _get_db

        with _get_db() as db:
            workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if workflow:
                workflow.status = WorkflowStatus.FAILED
                workflow.error_message = str(exc)
