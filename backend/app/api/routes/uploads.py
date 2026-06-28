"""
ARGUS Platform — Upload Routes
Handles multi-type file uploads with validation.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status

from app.api.deps import AnalystUser, DBSession
from app.config import settings
from app.database.models import Incident, Upload, UploadType, Workflow, WorkflowStatus
from app.database.schemas import UploadResponse


router = APIRouter(prefix="/uploads", tags=["Uploads"])

MAX_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

MIME_TO_TYPE: dict[str, UploadType] = {
    "image/jpeg": UploadType.IMAGE,
    "image/png": UploadType.IMAGE,
    "image/webp": UploadType.IMAGE,
    "image/gif": UploadType.IMAGE,
    "application/pdf": UploadType.PDF,
    "text/plain": UploadType.TXT,
    "text/csv": UploadType.CSV,
    "application/csv": UploadType.CSV,
    "application/vnd.ms-excel": UploadType.CSV,
}

TYPE_TO_DIR: dict[UploadType, str] = {
    UploadType.IMAGE: "images",
    UploadType.PDF: "pdfs",
    UploadType.CSV: "csvs",
    UploadType.TXT: "txts",
}


@router.post("/{incident_id}", response_model=List[UploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_files(
    incident_id: str,
    background_tasks: BackgroundTasks,
    db: DBSession,
    current_user: AnalystUser,
    files: List[UploadFile] = File(...),
) -> List[Upload]:
    """
    Upload one or more files (images, PDFs, CSVs, TXTs) to an incident.
    Files are validated, stored on disk, and registered in the database.
    Automatically triggers the analysis workflow after successful upload.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results: List[Upload] = []

    for file in files:
        # Validate MIME type
        content_type = file.content_type or ""
        upload_type = MIME_TO_TYPE.get(content_type)
        if upload_type is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{content_type}' for '{file.filename}'. "
                       "Allowed: JPEG, PNG, WebP, GIF, PDF, TXT, CSV",
            )

        # Read and validate size
        content = await file.read()
        if len(content) > MAX_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File '{file.filename}' exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB",
            )
        if len(content) == 0:
            raise HTTPException(status_code=400, detail=f"File '{file.filename}' is empty")

        # Generate unique filename to prevent collisions
        file_hash = hashlib.sha256(content).hexdigest()[:12]
        ext = Path(file.filename or "file").suffix.lower()
        unique_filename = f"{uuid.uuid4().hex}_{file_hash}{ext}"

        # Save to appropriate subdirectory
        upload_dir = settings.UPLOAD_DIR / TYPE_TO_DIR[upload_type]
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / unique_filename

        with open(file_path, "wb") as f:
            f.write(content)

        # Register in database
        db_upload = Upload(
            incident_id=incident_id,
            filename=unique_filename,
            original_filename=file.filename or unique_filename,
            upload_type=upload_type,
            file_path=str(file_path),
            file_size=len(content),
            mime_type=content_type,
            processed=False,
        )
        db.add(db_upload)
        db.flush()
        results.append(db_upload)

    # Automatically trigger workflow after upload
    background_tasks.add_task(_trigger_workflow_after_upload, incident_id=incident_id)

    return results


async def _trigger_workflow_after_upload(incident_id: str) -> None:
    """
    Background task: trigger workflow after upload if no workflow is already running.
    Includes retry logic for SQLite database locks.
    """
    import asyncio
    import logging
    from app.database.session import get_db as _get_db

    max_retries = 3
    retry_delay = 0.5  # seconds

    for attempt in range(max_retries):
        try:
            with _get_db() as db:
                # Check for already-running workflow
                running = (
                    db.query(Workflow)
                    .filter(
                        Workflow.incident_id == incident_id,
                        Workflow.status == WorkflowStatus.RUNNING,
                    )
                    .first()
                )
                if running:
                    return  # Skip if workflow already running

                # Create workflow record with proper JSON serialization
                workflow = Workflow(
                    incident_id=incident_id,
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

            # Run pipeline
            from app.workflow.orchestrator import run_incident_pipeline
            await run_incident_pipeline(workflow_id=workflow_id, incident_id=incident_id)
            return  # Success, exit retry loop

        except Exception as exc:
            if "database is locked" in str(exc) and attempt < max_retries - 1:
                logging.warning(f"Database locked on attempt {attempt + 1}/{max_retries}, retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                # Log error but don't fail the upload
                logging.error(f"Failed to trigger workflow after upload: {exc}")
                return


@router.get("/{incident_id}", response_model=List[UploadResponse])
def list_uploads(
    incident_id: str,
    db: DBSession,
    current_user: AnalystUser,
) -> List[Upload]:
    """List all uploads for a given incident."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return db.query(Upload).filter(Upload.incident_id == incident_id).all()


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload(
    upload_id: str,
    db: DBSession,
    current_user: AnalystUser,
) -> None:
    """Delete an upload record and its file from disk."""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Remove file from disk if it exists
    file_path = Path(upload.file_path)
    if file_path.exists():
        file_path.unlink()

    db.delete(upload)
