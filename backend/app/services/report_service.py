"""
ARGUS Platform — PDF Report Service
Generates professional PDF reports from structured report data.
Uses ReportLab for local PDF generation.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings


def generate_pdf_report(report) -> Path:
    """
    Generate a professional PDF report from a Report ORM model.
    
    Args:
        report: SQLAlchemy Report model instance
        
    Returns:
        Path to the generated PDF file
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm, mm
        from reportlab.platypus import (
            HRFlowable,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        raise RuntimeError("ReportLab not installed: pip install reportlab")

    # Ensure output directory exists
    reports_dir = settings.REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = reports_dir / f"ARGUS_Report_{report.id[:8]}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"

    # ── Define color palette ──────────────────────────────────────────────────
    DARK_NAVY = colors.HexColor("#0A1628")
    ACCENT_BLUE = colors.HexColor("#1E3A5F")
    DANGER_RED = colors.HexColor("#DC2626")
    WARNING_AMBER = colors.HexColor("#D97706")
    SUCCESS_GREEN = colors.HexColor("#059669")
    MEDIUM_BLUE = colors.HexColor("#3B82F6")
    LIGHT_GRAY = colors.HexColor("#F8FAFC")
    MID_GRAY = colors.HexColor("#64748B")
    WHITE = colors.white

    RISK_COLORS = {
        "critical": DANGER_RED,
        "high": colors.HexColor("#EA580C"),
        "medium": WARNING_AMBER,
        "low": SUCCESS_GREEN,
    }

    risk_color = RISK_COLORS.get(str(report.risk_level or "medium").lower(), MEDIUM_BLUE)

    # ── Styles ────────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "ArgusTitle",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=WHITE,
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    style_subtitle = ParagraphStyle(
        "ArgusSubtitle",
        fontName="Helvetica",
        fontSize=11,
        textColor=colors.HexColor("#94A3B8"),
        spaceAfter=2,
        alignment=TA_CENTER,
    )
    style_section_header = ParagraphStyle(
        "ArgusSection",
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=ACCENT_BLUE,
        spaceBefore=16,
        spaceAfter=6,
    )
    style_body = ParagraphStyle(
        "ArgusBody",
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=6,
        leading=14,
        alignment=TA_JUSTIFY,
    )
    style_caption = ParagraphStyle(
        "ArgusCaption",
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=MID_GRAY,
        spaceAfter=4,
    )
    style_risk_badge = ParagraphStyle(
        "ArgusRisk",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=WHITE,
        alignment=TA_CENTER,
    )

    # ── Document ──────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
        title=report.title or "ARGUS Risk Intelligence Report",
        author="ARGUS AI Platform",
        subject="Risk Intelligence Analysis",
    )

    story = []

    # ── Cover Header ──────────────────────────────────────────────────────────
    header_data = [
        [Paragraph("ARGUS", style_title)],
        [Paragraph("Autonomous Risk Intelligence &amp; Early Warning Platform", style_subtitle)],
        [Spacer(1, 4)],
        [Paragraph("RISK INTELLIGENCE REPORT", ParagraphStyle(
            "ArgusSubheader", fontName="Helvetica-Bold", fontSize=12,
            textColor=colors.HexColor("#38BDF8"), alignment=TA_CENTER
        ))],
    ]
    header_table = Table(header_data, colWidths=[17 * cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 12))

    # ── Incident Title + Risk Badge ───────────────────────────────────────────
    risk_level_text = str(report.risk_level or "UNKNOWN").upper()
    confidence_pct = f"{(report.confidence_score or 0) * 100:.0f}%"

    meta_data = [
        [
            Paragraph(report.title or "Untitled Report", ParagraphStyle(
                "ArgusIncidentTitle", fontName="Helvetica-Bold", fontSize=14,
                textColor=DARK_NAVY, spaceAfter=4,
            )),
            Paragraph(
                f"<b>RISK LEVEL</b><br/>{risk_level_text}",
                ParagraphStyle("RiskBadge", fontName="Helvetica-Bold", fontSize=14,
                               textColor=WHITE, alignment=TA_CENTER),
            ),
        ],
        [
            Paragraph(
                f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}<br/>"
                f"Confidence: {confidence_pct} | Platform: ARGUS v1.0",
                style_caption,
            ),
            Paragraph(
                f"AI Confidence: {confidence_pct}",
                ParagraphStyle("RiskConf", fontName="Helvetica", fontSize=10,
                               textColor=WHITE, alignment=TA_CENTER),
            ),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[12 * cm, 5 * cm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (1, 1), risk_color),
        ("BACKGROUND", (0, 0), (0, 1), LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 16))

    # ── Executive Summary ─────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", style_section_header))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE, spaceAfter=8))
    if report.executive_summary:
        for para in report.executive_summary.split("\n\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), style_body))
    else:
        story.append(Paragraph("Executive summary not available.", style_body))

    # ── Risk Analysis ─────────────────────────────────────────────────────────
    story.append(Paragraph("Risk Analysis", style_section_header))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=8))
    if report.risk_analysis:
        for para in report.risk_analysis.split("\n\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), style_body))

    # ── Recommendations ───────────────────────────────────────────────────────
    story.append(Paragraph("Recommendations", style_section_header))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=8))

    full_report = report.full_report_json or {}
    recommendations_text = full_report.get("recommendations_text", "")
    if recommendations_text:
        for para in recommendations_text.split("\n\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), style_body))

    # ── Timeline ──────────────────────────────────────────────────────────────
    if report.timeline:
        story.append(Paragraph("Analysis Timeline", style_section_header))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=8))

        timeline_data = [["Time", "Event"]]
        for entry in (report.timeline or [])[:20]:
            if isinstance(entry, dict):
                ts = entry.get("timestamp", "")
                event = entry.get("event", "")
                timeline_data.append([Paragraph(str(ts)[:19], style_caption), Paragraph(str(event)[:200], style_body)])

        if len(timeline_data) > 1:
            timeline_table = Table(timeline_data, colWidths=[4 * cm, 13 * cm])
            timeline_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(timeline_table)

    # ── Data Sources & Confidence ─────────────────────────────────────────────
    story.append(Spacer(1, 8))
    story.append(Paragraph("Data Sources & Methodology", style_section_header))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=8))

    if report.data_sources:
        for source in report.data_sources:
            story.append(Paragraph(f"• {source}", style_body))

    # Methodology note
    story.append(Paragraph(
        "This report was generated by the ARGUS multi-agent AI platform using "
        "Google Gemini AI for analysis across Vision, OCR, Knowledge, Risk Assessment, "
        "Simulation, Recommendation, and Commander agents operating in a structured pipeline.",
        style_body,
    ))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    footer_data = [[
        Paragraph(
            "ARGUS Risk Intelligence Platform | Confidential | For Official Use Only",
            ParagraphStyle("Footer", fontName="Helvetica-Oblique", fontSize=8,
                           textColor=MID_GRAY, alignment=TA_CENTER),
        )
    ]]
    footer_table = Table(footer_data, colWidths=[17 * cm])
    footer_table.setStyle(TableStyle([
        ("TOPBORDER", (0, 0), (-1, 0), 1, MID_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(footer_table)

    # ── Build PDF ─────────────────────────────────────────────────────────────
    doc.build(story)
    return pdf_path
