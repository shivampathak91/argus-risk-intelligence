"""
ARGUS Platform — Knowledge Agent
Retrieves historical incident data from the knowledge base
and identifies patterns relevant to the current incident.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from groq import Groq
from pydantic import BaseModel

from app.config import settings
from app.database.models import IncidentType, KnowledgeBase
from app.database.session import get_db


# ── Output Schema ─────────────────────────────────────────────────────────────

class HistoricalMatch(BaseModel):
    incident_id: str
    title: str
    location: Optional[str]
    year: Optional[int]
    similarity_score: float  # 0.0 - 1.0
    similarity_reasons: List[str]
    outcome: Optional[str]
    lessons_learned: Optional[str]
    casualties: Optional[int]
    economic_damage_usd: Optional[float]


class KnowledgeAnalysisResult(BaseModel):
    historical_matches: List[HistoricalMatch]
    incident_type_confirmed: str
    risk_pattern: str           # Description of recurring patterns
    average_severity: str       # Historical average severity for this type
    typical_outcomes: List[str]
    key_risk_factors: List[str] # Factors that historically made things worse
    protective_factors: List[str]  # Factors that historically reduced risk
    comparable_events: int      # Number of comparable historical events found
    knowledge_confidence: float
    knowledge_summary: str


# ── Knowledge System Prompt ───────────────────────────────────────────────────

KNOWLEDGE_SYSTEM_PROMPT = """
You are the Knowledge Agent of the ARGUS Risk Intelligence Platform.

Your role is to analyze current incident data against historical records to:
1. Find the most relevant historical incidents
2. Identify recurring patterns and risk factors
3. Extract lessons learned from past events
4. Provide evidence-based context for risk assessment

You have access to a database of historical disasters and infrastructure incidents.
Your findings directly inform the Risk Assessment and Recommendation agents.

Always be specific about which historical events you're referencing.
Compute similarity scores based on shared characteristics.
"""


class KnowledgeAgent:
    """
    Retrieves and analyzes historical incident data.
    Matches current incidents to past events and extracts lessons learned.
    """

    def __init__(self):
        self.demo_mode = settings.DEMO_MODE
        if not self.demo_mode:
            if not settings.GROQ_API_KEY:
                raise RuntimeError("GROQ_API_KEY not configured")
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            self.primary_model = settings.GROQ_MODEL
            self.fallback_models = settings.GROQ_FALLBACK_MODELS

    def _fetch_historical_records(
        self,
        incident_type: str,
        keywords: List[str],
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        """Fetch relevant historical records from the knowledge base."""
        with get_db() as db:
            query = db.query(KnowledgeBase)

            # Filter by incident type if known
            if incident_type and incident_type != "unknown":
                try:
                    inc_type = IncidentType(incident_type)
                    query = query.filter(KnowledgeBase.incident_type == inc_type)
                except ValueError:
                    pass  # Unknown type — search all

            records = query.all()

            # Keyword ranking
            if keywords:
                def relevance(r: KnowledgeBase) -> int:
                    text = f"{r.title} {r.description} {r.lessons_learned or ''}".lower()
                    return sum(1 for kw in keywords if kw.lower() in text)
                records.sort(key=relevance, reverse=True)

            return [
                {
                    "id": r.id,
                    "incident_type": r.incident_type,
                    "title": r.title,
                    "description": r.description,
                    "location": r.location,
                    "year": r.year,
                    "risk_level": r.risk_level,
                    "outcome": r.outcome,
                    "lessons_learned": r.lessons_learned,
                    "casualties": r.casualties,
                    "economic_damage_usd": r.economic_damage_usd,
                    "keywords": r.keywords or [],
                }
                for r in records[:limit]
            ]

    def analyze(
        self,
        incident_type: str,
        incident_description: str,
        key_findings: List[str],
        location: Optional[str] = None,
        keywords: Optional[List[str]] = None,
    ) -> KnowledgeAnalysisResult:
        """
        Find historical matches and extract knowledge for the current incident.
        
        Args:
            incident_type: Type of incident (e.g., 'bridge_failure')
            incident_description: Description of the current incident
            key_findings: Key findings from OCR/Vision agents
            location: Geographic location if known
            keywords: Keywords from OCR analysis
            
        Returns:
            KnowledgeAnalysisResult with historical context and patterns
        """
        # Demo mode - return mock data
        if self.demo_mode:
            return KnowledgeAnalysisResult(
                historical_matches=[
                    HistoricalMatch(
                        incident_id="demo-001",
                        title=f"Similar {incident_type.replace('_', ' ').title()} Event",
                        location=location or "Unknown",
                        year=2023,
                        similarity_score=0.75,
                        similarity_reasons=["Similar incident type", "Comparable environmental conditions"],
                        outcome="Resolved with moderate intervention",
                        lessons_learned="Early detection and rapid response are critical",
                        casualties=0,
                        economic_damage_usd=50000.0,
                    )
                ],
                incident_type_confirmed=incident_type,
                risk_pattern="Historical data suggests moderate risk progression",
                average_severity="medium",
                typical_outcomes=["Partial damage", "Operational disruption", "Recovery within 2-4 weeks"],
                key_risk_factors=["Delayed response", "Infrastructure aging", "Environmental stressors"],
                protective_factors=["Early detection systems", "Regular maintenance", "Emergency protocols"],
                comparable_events=1,
                knowledge_confidence=0.6,
                knowledge_summary="Demo mode: Using simulated historical data for demonstration purposes.",
            )
        
        # Fetch relevant historical records
        all_keywords = list(keywords or []) + key_findings[:5]
        historical_records = self._fetch_historical_records(
            incident_type=incident_type,
            keywords=all_keywords,
        )

        if not historical_records:
            # No historical data — return minimal result
            return KnowledgeAnalysisResult(
                historical_matches=[],
                incident_type_confirmed=incident_type,
                risk_pattern="Insufficient historical data for pattern analysis",
                average_severity="unknown",
                typical_outcomes=[],
                key_risk_factors=[],
                protective_factors=[],
                comparable_events=0,
                knowledge_confidence=0.2,
                knowledge_summary="No comparable historical incidents found in the knowledge base.",
            )

        # AI-powered analysis of historical matches
        prompt = f"""
Analyze the CURRENT INCIDENT against these HISTORICAL RECORDS.

CURRENT INCIDENT:
Type: {incident_type}
Description: {incident_description}
Location: {location or 'Unknown'}
Key Findings: {json.dumps(key_findings[:10])}

HISTORICAL RECORDS ({len(historical_records)} records):
{json.dumps(historical_records, default=str, indent=2)}

Analyze and return JSON with this structure:
{{
  "historical_matches": [
    {{
      "incident_id": "id from record",
      "title": "incident title",
      "location": "location",
      "year": year_as_integer_or_null,
      "similarity_score": 0.0-1.0,
      "similarity_reasons": ["specific reasons why this is similar"],
      "outcome": "what happened",
      "lessons_learned": "what was learned",
      "casualties": number_or_null,
      "economic_damage_usd": number_or_null
    }}
  ],
  "incident_type_confirmed": "confirmed incident type",
  "risk_pattern": "description of recurring patterns across historical events",
  "average_severity": "low|medium|high|critical",
  "typical_outcomes": ["list of what typically happens with this incident type"],
  "key_risk_factors": ["factors that historically made outcomes worse"],
  "protective_factors": ["factors that historically reduced impact"],
  "comparable_events": number,
  "knowledge_confidence": 0.0-1.0,
  "knowledge_summary": "2-3 sentence summary of what history tells us about this type of incident"
}}

Rank historical matches by similarity score (highest first).
Be specific about what makes each historical event similar or different.
"""

        # Try primary model first, then fallbacks
        models_to_try = [self.primary_model] + self.fallback_models
        last_error = None

        for model_name in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": KNOWLEDGE_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=3000,
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
            # Ensure historical_matches are properly typed
            matches = []
            for m in data.get("historical_matches", []):
                try:
                    matches.append(HistoricalMatch(**m))
                except Exception:
                    pass
            data["historical_matches"] = matches
            return KnowledgeAnalysisResult(**data)
        except Exception as e:
            return KnowledgeAnalysisResult(
                historical_matches=[],
                incident_type_confirmed=incident_type,
                risk_pattern="Analysis failed — using raw historical data",
                average_severity="unknown",
                typical_outcomes=[r.get("outcome", "") for r in historical_records[:3] if r.get("outcome")],
                key_risk_factors=[],
                protective_factors=[],
                comparable_events=len(historical_records),
                knowledge_confidence=0.4,
                knowledge_summary=f"Found {len(historical_records)} related incidents. AI synthesis failed: {e}",
            )
