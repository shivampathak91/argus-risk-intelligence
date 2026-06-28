"""
ARGUS Platform — OCR Agent
Extracts and structures content from PDFs, CSVs, and TXT files.
Uses PyMuPDF for PDFs and pandas for CSVs.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from groq import Groq
from pydantic import BaseModel

from app.config import settings
from app.database.models import UploadType


# ── Output Schema ─────────────────────────────────────────────────────────────

class OCRExtractionResult(BaseModel):
    raw_text: str
    document_type: str
    key_entities: Dict[str, List[str]]  # dates, measurements, locations, names, etc.
    critical_findings: List[str]
    numerical_data: Dict[str, Any]      # measurements, counts, statistics
    timeline_events: List[Dict[str, str]]  # [{date, event}]
    structural_sections: Dict[str, str]    # section_name -> content
    data_quality_score: float              # 0.0 - 1.0
    extraction_summary: str


# ── OCR System Prompt ─────────────────────────────────────────────────────────

OCR_SYSTEM_PROMPT = """
You are the OCR Agent of the ARGUS Risk Intelligence Platform.

Your role is to read and extract structured information from text documents, 
PDF reports, and CSV datasets about infrastructure incidents and disasters.

You MUST:
1. Identify document type (inspection report, situation report, dataset, etc.)
2. Extract all critical data points (measurements, dates, locations, readings)
3. Identify all named entities (people, organizations, locations, infrastructure items)
4. Extract timeline events in chronological order
5. Structure the document into logical sections
6. Highlight findings that indicate risk or urgency
7. Compute basic statistics for numerical data in CSVs

For CSV files: compute mean, min, max, standard deviation, trend direction, and identify anomalies.
For PDFs: extract by sections and identify the document's key message.
For TXT: extract facts, dates, measurements, and entities.

Return your analysis in the specified JSON format.
"""


class OCRAgent:
    """
    Extracts and structures content from PDFs, CSVs, and TXT files.
    Uses PyMuPDF for PDFs and AI-powered entity extraction.
    """

    def __init__(self):
        self.demo_mode = settings.DEMO_MODE
        if not self.demo_mode:
            if not settings.GROQ_API_KEY:
                raise RuntimeError("GROQ_API_KEY not configured")
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            self.primary_model = settings.GROQ_MODEL
            self.fallback_models = settings.GROQ_FALLBACK_MODELS

    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract full text from a PDF using PyMuPDF."""
        try:
            import fitz
        except ImportError:
            raise RuntimeError("PyMuPDF not installed: pip install pymupdf")

        doc = fitz.open(file_path)
        pages = []
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append(f"[Page {page_num}]\n{text}")
        doc.close()
        return "\n\n".join(pages)

    def _parse_csv(self, file_path: str) -> Dict[str, Any]:
        """Parse a CSV file and compute basic statistics."""
        try:
            import pandas as pd

            df = pd.read_csv(file_path)
            stats: Dict[str, Any] = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": df.columns.tolist(),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "missing_values": df.isnull().sum().to_dict(),
                "statistics": {},
                "sample_rows": df.head(5).to_dict(orient="records"),
                "anomalies": [],
            }

            # Compute statistics for numeric columns
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            for col in numeric_cols:
                col_stats = {
                    "mean": float(df[col].mean()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "std": float(df[col].std()),
                    "median": float(df[col].median()),
                }
                stats["statistics"][col] = col_stats

                # Basic anomaly detection: values > 3 standard deviations from mean
                mean = df[col].mean()
                std = df[col].std()
                if std > 0:
                    outliers = df[abs(df[col] - mean) > 3 * std]
                    if not outliers.empty:
                        stats["anomalies"].append({
                            "column": col,
                            "outlier_count": len(outliers),
                            "outlier_values": outliers[col].tolist()[:5],
                        })

            return stats
        except Exception as e:
            # Fallback: basic CSV reading without pandas
            rows = []
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(dict(row))
            return {
                "row_count": len(rows),
                "columns": list(rows[0].keys()) if rows else [],
                "sample_rows": rows[:5],
                "error": f"Full statistics unavailable: {e}",
            }

    def _read_text_file(self, file_path: str) -> str:
        """Read a text file."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return content[:50_000]  # Truncate to 50k chars

    def _ai_extract_entities(self, raw_text: str, doc_type: str, csv_stats: Optional[Dict] = None) -> OCRExtractionResult:
        """Use Gemini to extract structured information from document text."""
        prompt = f"""
Analyze this {doc_type} document for the ARGUS Risk Intelligence Platform.

DOCUMENT CONTENT:
{raw_text[:15000]}

{f"CSV STATISTICS: {json.dumps(csv_stats, default=str, indent=2)[:3000]}" if csv_stats else ""}

Extract and return JSON with this exact structure:
{{
  "raw_text": "first 500 chars of document",
  "document_type": "type of document",
  "key_entities": {{
    "dates": ["all dates mentioned"],
    "locations": ["all locations/addresses"],
    "measurements": ["all measurements with units"],
    "organizations": ["all org names"],
    "infrastructure_items": ["bridges, roads, buildings, power lines, etc."],
    "personnel": ["names and roles"],
    "risk_indicators": ["specific risk phrases"]
  }},
  "critical_findings": ["list of the most important findings from the document"],
  "numerical_data": {{
    "key_numbers": {{"label": value}},
    "statistics": {{"computed statistics if CSV"}}
  }},
  "timeline_events": [
    {{"date": "...", "event": "...description..."}}
  ],
  "structural_sections": {{
    "section_name": "brief content summary"
  }},
  "data_quality_score": 0.0-1.0,
  "extraction_summary": "2-3 sentence summary of the document's key information and risk implications"
}}

Be comprehensive. Extract ALL dates, measurements, and critical findings.
"""

        # Try primary model first, then fallbacks
        models_to_try = [self.primary_model] + self.fallback_models
        last_error = None

        for model_name in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": OCR_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                )
                # If successful, break out of the loop
                break
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                # If it's a quota/rate limit error, try next model
                if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg or "limit" in error_msg:
                    import logging
                    logging.warning(f"Groq model {model_name} hit quota limit, trying fallback model...")
                    continue
                else:
                    # For other errors, don't try fallbacks
                    raise
        else:
            # All models failed
            raise RuntimeError(f"All Groq models failed. Last error: {last_error}")

        raw = response.choices[0].message.content.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(raw)
            # Ensure raw_text is populated
            if not data.get("raw_text"):
                data["raw_text"] = raw_text[:500]
            return OCRExtractionResult(**data)
        except Exception as e:
            return OCRExtractionResult(
                raw_text=raw_text[:500],
                document_type=doc_type,
                key_entities={},
                critical_findings=["Extraction failed: " + str(e), raw[:300]],
                numerical_data={},
                timeline_events=[],
                structural_sections={},
                data_quality_score=0.3,
                extraction_summary=f"Document parsed but structured extraction failed: {e}",
            )

    def extract(
        self,
        file_path: str,
        upload_type: str,
        context: Optional[str] = None,
    ) -> OCRExtractionResult:
        """
        Extract structured content from any supported file type.

        Args:
            file_path: Absolute path to the file
            upload_type: One of 'pdf', 'csv', 'txt'
            context: Optional incident context to guide extraction
        """
        # Demo mode - return mock data
        if self.demo_mode:
            return OCRExtractionResult(
                raw_text="Demo mode: Simulated document content extraction...",
                document_type="inspection_report",
                key_entities={
                    "dates": ["2024-01-15", "2024-01-20"],
                    "locations": ["Main Street Bridge", "Downtown District"],
                    "measurements": ["crack width: 2.5cm", "deflection: 15mm"],
                    "organizations": ["Department of Transportation", "Structural Engineering Division"],
                    "infrastructure_items": ["bridge deck", "support beams", "expansion joints"],
                    "personnel": ["Inspector J. Smith", "Engineer M. Johnson"],
                    "risk_indicators": ["structural fatigue", "corrosion evidence", "load capacity reduction"]
                },
                critical_findings=[
                    "Multiple cracks detected in primary support structure",
                    "Corrosion affecting 40% of steel components",
                    "Load capacity reduced by 25% from design specifications"
                ],
                numerical_data={
                    "key_numbers": {"crack_count": 47, "corrosion_percentage": 40, "capacity_reduction": 25},
                    "statistics": {"avg_crack_width": "2.5cm", "max_deflection": "15mm"}
                },
                timeline_events=[
                    {"date": "2024-01-15", "event": "Initial inspection conducted"},
                    {"date": "2024-01-20", "event": "Detailed structural analysis completed"}
                ],
                structural_sections={
                    "executive_summary": "Critical structural issues identified requiring immediate attention",
                    "findings": "47 cracks detected, significant corrosion present",
                    "recommendations": "Immediate load restrictions and repair scheduling"
                },
                data_quality_score=0.85,
                extraction_summary="Demo mode: Simulated OCR extraction reveals significant structural concerns requiring immediate intervention."
            )

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        csv_stats = None

        if upload_type == UploadType.PDF or path.suffix.lower() == ".pdf":
            raw_text = self._extract_pdf_text(file_path)
            doc_type = "PDF inspection/situation report"
        elif upload_type == UploadType.CSV or path.suffix.lower() == ".csv":
            csv_stats = self._parse_csv(file_path)
            # Convert stats to text for AI analysis
            raw_text = (
                f"CSV Dataset: {csv_stats['row_count']} rows, {csv_stats['column_count']} columns\n"
                f"Columns: {', '.join(csv_stats.get('columns', []))}\n\n"
                f"Sample data:\n{json.dumps(csv_stats.get('sample_rows', []), indent=2)}\n\n"
                f"Statistics:\n{json.dumps(csv_stats.get('statistics', {}), indent=2)}"
            )
            doc_type = "CSV dataset"
        elif upload_type == UploadType.TXT or path.suffix.lower() == ".txt":
            raw_text = self._read_text_file(file_path)
            doc_type = "text report/document"
        else:
            raise ValueError(f"Unsupported file type for OCR: {upload_type}")

        if context:
            raw_text = f"[Incident Context: {context}]\n\n" + raw_text

        return self._ai_extract_entities(raw_text, doc_type, csv_stats)

    def extract_multiple(
        self,
        files: List[Dict[str, str]],
        context: Optional[str] = None,
    ) -> Dict[str, OCRExtractionResult]:
        """
        Extract content from multiple files.
        
        Args:
            files: List of {"path": ..., "upload_type": ...} dicts
            context: Optional incident context
            
        Returns:
            Dict keyed by file path
        """
        results = {}
        for file_info in files:
            path = file_info["path"]
            upload_type = file_info["upload_type"]
            try:
                results[path] = self.extract(path, upload_type, context)
            except Exception as e:
                results[path] = OCRExtractionResult(
                    raw_text="",
                    document_type="unknown",
                    key_entities={},
                    critical_findings=[f"Extraction failed: {e}"],
                    numerical_data={},
                    timeline_events=[],
                    structural_sections={},
                    data_quality_score=0.0,
                    extraction_summary=f"File could not be processed: {e}",
                )
        return results
