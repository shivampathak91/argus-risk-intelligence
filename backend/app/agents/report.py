"""
ARGUS Platform — Report Agent
Generates structured professional reports from all agent outputs.
Produces both JSON and initiates PDF generation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from groq import Groq
from pydantic import BaseModel

from app.config import settings


# ── Output Schema ─────────────────────────────────────────────────────────────

class ReportData(BaseModel):
    title: str
    incident_type: str
    risk_level: str
    confidence_score: float
    executive_summary: str
    incident_overview: str
    methodology: str
    risk_analysis: str
    simulation_findings: str
    recommendations_text: str
    historical_context: str
    timeline: List[Dict[str, str]]    # [{timestamp, event}]
    data_sources: List[str]
    key_metrics: Dict[str, Any]
    limitations: str
    conclusion: str
    generated_at: str


# ── Report System Prompt ──────────────────────────────────────────────────────

REPORT_SYSTEM_PROMPT = """
You are the Report Agent of the ARGUS Risk Intelligence Platform.

Your role is to compile all agent findings into a professional, executive-grade 
risk intelligence report.

Report Standards:
- Write for a government or senior management audience
- Be specific and quantitative
- Cite evidence and confidence levels for every major claim
- Use professional language appropriate for emergency management
- Structure content logically: overview → analysis → findings → recommendations
- Highlight the most critical findings in the executive summary
- The report must be comprehensive enough to stand alone as a decision-making document

The report should feel like it was written by a senior risk analyst,
not an AI system.
"""


class ReportAgent:
    """
    Compiles all agent outputs into a professional risk intelligence report.
    """

    def __init__(self):
        self.demo_mode = settings.DEMO_MODE
        if not self.demo_mode:
            if not settings.GROQ_API_KEY:
                raise RuntimeError("GROQ_API_KEY not configured")
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            self.primary_model = settings.GROQ_MODEL
            self.fallback_models = settings.GROQ_FALLBACK_MODELS

    def generate(
        self,
        incident_id: str,
        incident_title: str,
        incident_type: str,
        location: Optional[str],
        risk_assessment: Dict[str, Any],
        recommendations: Dict[str, Any],
        knowledge_context: Optional[Dict[str, Any]] = None,
        simulation_results: Optional[Dict[str, Any]] = None,
        ocr_results: Optional[Dict[str, Any]] = None,
        vision_results: Optional[Dict[str, Any]] = None,
    ) -> ReportData:
        """
        Generate a comprehensive professional report.

        Returns:
            ReportData with all sections of the report
        """
        now = datetime.now(timezone.utc).isoformat()

        # Demo mode - return mock data
        if self.demo_mode:
            # Build basic data sources for demo
            demo_data_sources = ["ARGUS Multi-Agent Analysis System"]
            if vision_results:
                demo_data_sources.append("Visual damage analysis")
            if ocr_results:
                demo_data_sources.append("Document analysis")
            if knowledge_context:
                demo_data_sources.append("Historical knowledge base")
            if simulation_results:
                demo_data_sources.append("Scenario simulation")

            # Build basic key metrics for demo
            demo_key_metrics = {
                "risk_level": risk_assessment.get("overall_risk_level", "unknown"),
                "risk_score": risk_assessment.get("risk_score", 0),
                "confidence": risk_assessment.get("confidence_score", 0),
                "immediate_threats_count": len(risk_assessment.get("immediate_threats", [])),
                "recommendation_count": len(recommendations.get("recommendations", [])),
            }

            return ReportData(
                title=f"ARGUS Risk Intelligence Report: {incident_title}",
                incident_type=incident_type,
                risk_level=risk_assessment.get("overall_risk_level", "medium"),
                confidence_score=risk_assessment.get("confidence_score", 0.65),
                executive_summary=f"Demo mode: This incident has been assessed as {risk_assessment.get('overall_risk_level', 'medium')} risk. Immediate inspection and stabilization are recommended based on visual and historical analysis.",
                incident_overview=f"Analysis of {incident_title} conducted using ARGUS multi-agent system. Visual analysis detected structural concerns, historical patterns indicate potential progression without intervention.",
                methodology="ARGUS multi-agent analysis including Vision, OCR, Knowledge, Risk Assessment, Simulation, Recommendation, and Commander agents.",
                risk_analysis=f"Risk assessment indicates {risk_assessment.get('overall_risk_level', 'medium')} risk level with score of {risk_assessment.get('risk_score', 55)}/100. Key factors include structural damage indicators and historical failure patterns.",
                simulation_findings="Simulation scenarios indicate that immediate response significantly reduces risk trajectory, while delayed intervention increases probability of structural failure.",
                recommendations_text="Primary recommendation: Deploy emergency inspection team immediately. Secondary: Implement temporary supports within 24-48 hours.",
                historical_context="Historical data shows similar incidents with comparable risk factors. Past events indicate that early intervention significantly reduces adverse outcomes.",
                timeline=[{"timestamp": now, "event": "Report generated"}],
                data_sources=demo_data_sources,
                key_metrics=demo_key_metrics,
                limitations="Demo mode: This is a simulated report for demonstration purposes.",
                conclusion="Demo mode: Based on multi-agent analysis, immediate action is recommended to mitigate identified risks.",
                generated_at=now,
            )

        # Compile key metrics
        key_metrics = {
            "risk_level": risk_assessment.get("overall_risk_level", "unknown"),
            "risk_score": risk_assessment.get("risk_score", 0),
            "confidence": risk_assessment.get("confidence_score", 0),
            "immediate_threats_count": len(risk_assessment.get("immediate_threats", [])),
            "recommendation_count": len(recommendations.get("recommendations", [])),
        }

        if simulation_results:
            key_metrics["scenarios_analyzed"] = len(simulation_results.get("scenarios", []))
            key_metrics["worst_case"] = simulation_results.get("worst_case_scenario")

        if knowledge_results := knowledge_context:
            key_metrics["historical_matches"] = knowledge_results.get("comparable_events", 0)

        # Build data sources list
        data_sources = ["ARGUS Multi-Agent Analysis System"]
        if vision_results:
            data_sources.append("Visual damage analysis (Gemini Vision)")
        if ocr_results:
            data_sources.append(f"Document analysis ({ocr_results.get('document_type', 'Document')})")
        if knowledge_context:
            data_sources.append(f"Historical knowledge base ({key_metrics.get('historical_matches', 0)} comparable events)")
        if simulation_results:
            data_sources.append(f"Scenario simulation ({key_metrics.get('scenarios_analyzed', 0)} scenarios)")

        prompt = f"""
Generate a professional risk intelligence report for this incident.

INCIDENT: {incident_title}
TYPE: {incident_type}
LOCATION: {location or 'Unknown'}
ANALYSIS DATE: {now}

RISK ASSESSMENT:
Level: {risk_assessment.get('overall_risk_level', 'unknown').upper()}
Score: {risk_assessment.get('risk_score', 0):.1f}/100
Confidence: {risk_assessment.get('confidence_score', 0):.0%}
Immediate threats: {json.dumps(risk_assessment.get('immediate_threats', []))}
Secondary risks: {json.dumps(risk_assessment.get('secondary_risks', []))}
Key risk factors: {json.dumps([rf.get('factor', '') if isinstance(rf, dict) else str(rf) for rf in risk_assessment.get('risk_factors', [])][:5])}
Reasoning: {risk_assessment.get('assessment_reasoning', '')}

RECOMMENDATIONS:
Primary: {recommendations.get('primary_recommendation', '')}
Summary: {recommendations.get('recommendation_summary', '')}
Top 3 actions: {json.dumps([r.get('action', '') if isinstance(r, dict) else str(r) for r in recommendations.get('recommendations', [])[:3]])}

HISTORICAL CONTEXT:
{json.dumps({
    'pattern': knowledge_context.get('risk_pattern') if knowledge_context else None,
    'average_severity': knowledge_context.get('average_severity') if knowledge_context else None,
    'comparable_events': knowledge_context.get('comparable_events') if knowledge_context else 0,
    'typical_outcomes': knowledge_context.get('typical_outcomes', [])[:2] if knowledge_context else [],
}, indent=2)}

SIMULATION:
{json.dumps({
    'most_likely': simulation_results.get('most_likely_scenario') if simulation_results else None,
    'worst_case': simulation_results.get('worst_case_scenario') if simulation_results else None,
    'summary': simulation_results.get('simulation_summary') if simulation_results else None,
}, indent=2)}

Write a professional report as JSON:
{{
  "title": "ARGUS Risk Intelligence Report: {incident_title}",
  "incident_type": "{incident_type}",
  "risk_level": "{risk_assessment.get('overall_risk_level', 'unknown')}",
  "confidence_score": {risk_assessment.get('confidence_score', 0)},
  "executive_summary": "3-4 sentence high-level summary for senior decision makers. State risk level, key threats, and primary action required.",
  "incident_overview": "Comprehensive description of the incident, what was analyzed, and initial findings.",
  "methodology": "Brief description of the ARGUS multi-agent methodology used in this analysis.",
  "risk_analysis": "Detailed risk analysis section covering all identified risk factors with evidence citations.",
  "simulation_findings": "Summary of simulation scenarios and their predicted outcomes.",
  "recommendations_text": "Formatted recommendations section with evidence and priorities.",
  "historical_context": "How this incident compares to historical precedents and what history tells us.",
  "timeline": [
    {{"timestamp": "ISO timestamp or relative time", "event": "event description"}}
  ],
  "data_sources": {json.dumps(data_sources)},
  "key_metrics": {json.dumps(key_metrics)},
  "limitations": "Honest statement of data limitations and confidence constraints.",
  "conclusion": "Final conclusion and call to action.",
  "generated_at": "{now}"
}}

Write each section as a proper professional paragraph (not bullet points in JSON strings).
"""

        # Try primary model first, then fallbacks
        models_to_try = [self.primary_model] + self.fallback_models
        last_error = None

        for model_name in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=5000,
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
            return ReportData(**data)
        except Exception as e:
            # Minimal fallback report
            return ReportData(
                title=f"ARGUS Report: {incident_title}",
                incident_type=incident_type,
                risk_level=risk_assessment.get("overall_risk_level", "unknown"),
                confidence_score=risk_assessment.get("confidence_score", 0),
                executive_summary=(
                    f"This incident has been assessed as {risk_assessment.get('overall_risk_level', 'unknown').upper()} risk "
                    f"with a score of {risk_assessment.get('risk_score', 0):.1f}/100. "
                    f"{recommendations.get('primary_recommendation', 'Immediate assessment required.')}"
                ),
                incident_overview=f"Incident analysis for {incident_title} at {location or 'unknown location'}.",
                methodology="ARGUS multi-agent AI analysis pipeline.",
                risk_analysis=risk_assessment.get("assessment_reasoning", "Risk analysis unavailable."),
                simulation_findings=simulation_results.get("simulation_summary", "No simulation data.") if simulation_results else "No simulations run.",
                recommendations_text=recommendations.get("recommendation_summary", "No recommendations generated."),
                historical_context=knowledge_context.get("knowledge_summary", "No historical context.") if knowledge_context else "No historical data.",
                timeline=[],
                data_sources=data_sources,
                key_metrics=key_metrics,
                limitations=f"Report generation encountered an error: {e}. Data accuracy may be reduced.",
                conclusion=recommendations.get("primary_recommendation", "Immediate action required."),
                generated_at=now,
            )
