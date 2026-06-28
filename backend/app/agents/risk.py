"""
ARGUS Platform — Risk Assessment Agent
Synthesizes all agent outputs to produce a comprehensive risk score
with confidence levels and supporting evidence.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from groq import Groq
from pydantic import BaseModel

from app.config import settings


# ── Output Schema ─────────────────────────────────────────────────────────────

class RiskFactor(BaseModel):
    factor: str
    severity: str         # low / medium / high / critical
    confidence: float
    evidence: List[str]
    agent_source: str


class RiskAssessmentResult(BaseModel):
    overall_risk_level: str           # low / medium / high / critical
    risk_score: float                 # 0.0 - 100.0
    confidence_score: float           # 0.0 - 1.0
    risk_factors: List[RiskFactor]
    immediate_threats: List[str]
    secondary_risks: List[str]
    population_at_risk: Optional[int]
    infrastructure_impact: str
    time_to_critical: Optional[str]   # e.g., "24-48 hours", "immediate"
    evidence_summary: List[str]
    contributing_agents: List[str]
    assessment_reasoning: str
    incident_type: str


# ── Risk System Prompt ────────────────────────────────────────────────────────

RISK_SYSTEM_PROMPT = """
You are the Risk Assessment Agent of the ARGUS Risk Intelligence Platform.

Your role is to synthesize all available evidence — visual analysis, document extraction,
and historical knowledge — to produce a comprehensive, quantified risk assessment.

Risk Levels:
- LOW: Monitoring sufficient, no immediate action required
- MEDIUM: Preventive action recommended within 7 days
- HIGH: Urgent action required within 24-48 hours  
- CRITICAL: Immediate emergency response required

You MUST:
1. Base every conclusion on specific evidence from the input data
2. Weight evidence by source reliability (visual > documented > inferred)
3. Identify both immediate and secondary cascade risks
4. Quantify uncertainty honestly
5. Explicitly state which agents provided which evidence
6. Produce different risk levels for genuinely different evidence
   (e.g., minor cracks = MEDIUM, structural failure = CRITICAL)

Never assign CRITICAL risk without specific evidence of imminent danger.
Never assign LOW risk when there are documented casualties or structural failures.
"""


class RiskAssessmentAgent:
    """
    Synthesizes Vision, OCR, and Knowledge outputs into a risk score.
    All risk levels are evidence-based, not hardcoded.
    """

    def __init__(self):
        self.demo_mode = settings.DEMO_MODE
        if not self.demo_mode:
            if not settings.GROQ_API_KEY:
                raise RuntimeError("GROQ_API_KEY not configured")
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            self.primary_model = settings.GROQ_MODEL
            self.fallback_models = settings.GROQ_FALLBACK_MODELS

    def assess(
        self,
        incident_type: str,
        vision_results: Optional[Dict[str, Any]] = None,
        ocr_results: Optional[Dict[str, Any]] = None,
        knowledge_results: Optional[Dict[str, Any]] = None,
        incident_description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> RiskAssessmentResult:
        """
        Perform comprehensive risk assessment from all agent outputs.
        
        Args:
            incident_type: Type of incident
            vision_results: Output from VisionAgent (or None if no images)
            ocr_results: Output from OCRAgent (or None if no documents)
            knowledge_results: Output from KnowledgeAgent
            incident_description: User-provided description
            location: Geographic location
            
        Returns:
            RiskAssessmentResult with scored, evidenced risk assessment
        """
        # Demo mode - return mock data
        if self.demo_mode:
            return RiskAssessmentResult(
                overall_risk_level="medium",
                risk_score=55.0,
                confidence_score=0.6,
                risk_factors=[
                    RiskFactor(
                        factor="Structural damage observed",
                        severity="medium",
                        confidence=0.7,
                        evidence=["Visual analysis detected cracks", "Historical data shows progression risk"],
                        agent_source="vision,knowledge"
                    )
                ],
                immediate_threats=["Potential structural collapse if left untreated"],
                secondary_risks=["Operational disruption", "Economic impact"],
                population_at_risk=0,
                infrastructure_impact="moderate",
                time_to_critical="7-14 days",
                evidence_summary=["Visual evidence of damage", "Historical pattern analysis"],
                contributing_agents=["vision", "knowledge"],
                assessment_reasoning="Demo mode: Risk assessment based on simulated data patterns",
                incident_type=incident_type
            )
        
        # Build evidence context
        evidence_sections = []

        if incident_description:
            evidence_sections.append(f"INCIDENT DESCRIPTION:\n{incident_description}")

        if vision_results:
            evidence_sections.append(
                f"VISUAL ANALYSIS:\n"
                f"  Damage indicators: {vision_results.get('damage_indicators', [])}\n"
                f"  Severity estimate: {vision_results.get('severity_estimate', 'unknown')}\n"
                f"  Confidence: {vision_results.get('confidence', 0):.0%}\n"
                f"  Key findings: {vision_results.get('visual_evidence', [])}\n"
                f"  Summary: {vision_results.get('analysis_summary', '')}"
            )

        if ocr_results:
            evidence_sections.append(
                f"DOCUMENT EXTRACTION:\n"
                f"  Critical findings: {ocr_results.get('critical_findings', [])}\n"
                f"  Key measurements: {ocr_results.get('key_entities', {}).get('measurements', [])}\n"
                f"  Risk indicators: {ocr_results.get('key_entities', {}).get('risk_indicators', [])}\n"
                f"  Timeline: {ocr_results.get('timeline_events', [])}\n"
                f"  Numerical data: {json.dumps(ocr_results.get('numerical_data', {}), default=str)[:500]}\n"
                f"  Summary: {ocr_results.get('extraction_summary', '')}"
            )

        if knowledge_results:
            evidence_sections.append(
                f"HISTORICAL KNOWLEDGE:\n"
                f"  Historical pattern: {knowledge_results.get('risk_pattern', '')}\n"
                f"  Average severity: {knowledge_results.get('average_severity', 'unknown')}\n"
                f"  Key risk factors: {knowledge_results.get('key_risk_factors', [])}\n"
                f"  Typical outcomes: {knowledge_results.get('typical_outcomes', [])}\n"
                f"  Historical matches: {len(knowledge_results.get('historical_matches', []))} comparable events"
            )

        evidence_context = "\n\n".join(evidence_sections)

        prompt = f"""
Assess risk for this incident using ALL provided evidence.

INCIDENT TYPE: {incident_type}
LOCATION: {location or 'Unknown'}

EVIDENCE:
{evidence_context}

Return a comprehensive risk assessment as JSON:
{{
  "overall_risk_level": "low|medium|high|critical",
  "risk_score": 0.0-100.0,
  "confidence_score": 0.0-1.0,
  "risk_factors": [
    {{
      "factor": "specific risk factor name",
      "severity": "low|medium|high|critical",
      "confidence": 0.0-1.0,
      "evidence": ["specific evidence items supporting this factor"],
      "agent_source": "vision|ocr|knowledge|combined"
    }}
  ],
  "immediate_threats": ["threats requiring action in hours"],
  "secondary_risks": ["cascade/downstream risks"],
  "population_at_risk": number_or_null,
  "infrastructure_impact": "description of infrastructure at risk",
  "time_to_critical": "time window if no action taken",
  "evidence_summary": ["key evidence items that drove this assessment"],
  "contributing_agents": ["list of which agents provided evidence"],
  "assessment_reasoning": "detailed explanation of why this risk level was chosen, citing specific evidence",
  "incident_type": "{incident_type}"
}}

CRITICAL RULES:
- Risk score 0-25 = LOW, 26-50 = MEDIUM, 51-75 = HIGH, 76-100 = CRITICAL
- Cite specific evidence for every risk factor
- Different evidence MUST produce different scores
- Do not assign CRITICAL without documented casualties, structural failure, or imminent collapse
"""

        # Try primary model first, then fallbacks
        models_to_try = [self.primary_model] + self.fallback_models
        last_error = None

        for model_name in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": RISK_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.15,
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
            # Parse risk factors
            risk_factors = []
            for rf in data.get("risk_factors", []):
                try:
                    risk_factors.append(RiskFactor(**rf))
                except Exception:
                    pass
            data["risk_factors"] = risk_factors
            data["incident_type"] = incident_type
            return RiskAssessmentResult(**data)
        except Exception as e:
            # Fallback: derive risk from available severity indicators
            severity_map = {"low": "low", "medium": "medium", "high": "high", "critical": "critical"}
            vision_sev = vision_results.get("severity_estimate", "medium") if vision_results else "medium"
            risk_level = severity_map.get(vision_sev, "medium")

            return RiskAssessmentResult(
                overall_risk_level=risk_level,
                risk_score={"low": 20, "medium": 45, "high": 70, "critical": 90}.get(risk_level, 45),
                confidence_score=0.4,
                risk_factors=[],
                immediate_threats=[],
                secondary_risks=[],
                population_at_risk=None,
                infrastructure_impact="Assessment parsing failed",
                time_to_critical=None,
                evidence_summary=[],
                contributing_agents=["vision", "ocr", "knowledge"],
                assessment_reasoning=f"AI assessment parsing failed: {e}. Risk level derived from vision severity.",
                incident_type=incident_type,
            )
