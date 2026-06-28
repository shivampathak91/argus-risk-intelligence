"""
ARGUS Platform — Reports Routes
Retrieve AI-generated reports and export as PDF.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DBSession
from app.database.models import Report
from app.database.schemas import ReportResponse


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/incident/{incident_id}", response_model=List[ReportResponse])
def get_reports_for_incident(
    incident_id: str,
    db: DBSession,
    current_user: CurrentUser,
) -> List[Report]:
    """List all AI-generated reports for an incident."""
    return (
        db.query(Report)
        .filter(Report.incident_id == incident_id)
        .order_by(Report.created_at.desc())
        .all()
    )


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: str,
    db: DBSession,
    current_user: CurrentUser,
) -> Report:
    """Get the full details of a single report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{report_id}/pdf")
def download_report_pdf(
    report_id: str,
    db: DBSession,
    current_user: CurrentUser,
) -> FileResponse:
    """
    Download the generated PDF for a report.
    Generates on-demand if not yet created.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Generate PDF if not yet done
    if not report.pdf_path or not Path(report.pdf_path).exists():
        try:
            from app.services.report_service import generate_pdf_report
            pdf_path = generate_pdf_report(report)
            report.pdf_path = str(pdf_path)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"PDF generation failed: {exc}",
            )

    return FileResponse(
        path=report.pdf_path,
        media_type="application/pdf",
        filename=f"ARGUS_Report_{report.id[:8]}.pdf",
    )
