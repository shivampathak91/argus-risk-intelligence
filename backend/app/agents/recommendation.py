"""
ARGUS Platform — Recommendation Agent
Generates evidence-based, prioritized recommendations with
confidence scores and full explainability.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from groq import Groq
from pydantic import BaseModel

from app.config import settings


# ── Output Schema ─────────────────────────────────────────────────────────────

class Recommendation(BaseModel):
    priority: int                      # 1 = highest priority
    action: str
    rationale: str
    evidence: List[str]                # Specific evidence supporting this
    contributing_agents: List[str]     # Which agents informed this
    confidence_score: float            # 0.0 - 1.0
    historical_matches: List[Dict[str, Any]]  # Similar past events
    estimated_impact: str
    time_sensitivity: str              # immediate / 24h / 48h / 1week / 1month
    implementation_notes: Optional[str]
    cost_estimate: Optional[str]


class RecommendationResult(BaseModel):
    recommendations: List[Recommendation]
    primary_recommendation: str        # The single most important action
    overall_confidence: float
    evidence_basis: List[str]         # All evidence used across all recommendations
    agent_contributions: Dict[str, str]  # agent_name -> contribution summary
    recommendation_summary: str


# ── Recommendation System Prompt ──────────────────────────────────────────────

RECOMMENDATION_SYSTEM_PROMPT = """
You are the Recommendation Agent of the ARGUS Risk Intelligence Platform.

Your role is to generate actionable, evidence-based recommendations for disaster 
and infrastructure incident response.

Every recommendation MUST:
1. Be supported by specific evidence from the analysis
2. Explain WHY this action is recommended (rationale)
3. State WHICH agents provided the supporting evidence
4. Include a confidence score based on evidence quality
5. Reference historical precedents when available
6. Be prioritized by urgency and impact

Recommendation principles:
- Priority 1 = must act NOW (life safety, imminent collapse)
- Priority 2 = act within 24 hours (prevent escalation)  
- Priority 3 = act within 1 week (contain damage)
- Priority 4 = act within 1 month (recovery/prevention)

Never generate generic recommendations ("assess the situation").
Always be specific ("install temporary shoring under pier column 3 to prevent collapse").

Disagreement with Risk Agent: If evidence supports different risk levels, 
explicitly state your position and confidence.
"""


class RecommendationAgent:
    """
    Generates prioritized, evidence-backed recommendations.
    All recommendations are derived from actual agent outputs.
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
        incident_type: str,
        risk_assessment: Dict[str, Any],
        ocr_results: Optional[Dict[str, Any]] = None,
        vision_results: Optional[Dict[str, Any]] = None,
        knowledge_results: Optional[Dict[str, Any]] = None,
        simulation_results: Optional[Dict[str, Any]] = None,
        location: Optional[str] = None,
    ) -> RecommendationResult:
        """
        Generate prioritized recommendations from all agent outputs.
        
        Returns:
            RecommendationResult with ordered, evidenced recommendations
        """
        # Demo mode - return mock data
        if self.demo_mode:
            return RecommendationResult(
                recommendations=[
                    Recommendation(
                        priority=1,
                        action="Deploy emergency inspection team within 6 hours",
                        rationale="Immediate structural assessment required to prevent collapse",
                        evidence=["Visual analysis shows structural cracks", "Risk assessment indicates medium-high danger"],
                        contributing_agents=["vision", "risk"],
                        confidence_score=0.75,
                        historical_matches=[],
                        estimated_impact="Prevents potential structural failure",
                        time_sensitivity="immediate",
                        implementation_notes="Coordinate with local emergency services",
                        cost_estimate="Moderate - requires specialized personnel",
                    ),
                    Recommendation(
                        priority=2,
                        action="Implement temporary support structures",
                        rationale="Stabilize affected area while permanent repairs are planned",
                        evidence=["Simulation shows 45% damage increase without intervention"],
                        contributing_agents=["simulation"],
                        confidence_score=0.7,
                        historical_matches=[],
                        estimated_impact="Reduces collapse risk by 80%",
                        time_sensitivity="24-48 hours",
                        implementation_notes="Requires structural engineering consultation",
                        cost_estimate="High - materials and labor intensive",
                    ),
                ],
                primary_recommendation="Deploy emergency inspection team within 6 hours",
                overall_confidence=0.7,
                evidence_basis=["Visual evidence of damage", "Risk assessment findings", "Simulation projections"],
                agent_contributions={"vision": "Detected structural cracks", "risk": "Assessed medium-high danger level", "simulation": "Projected damage increase"},
                recommendation_summary="Demo mode: Immediate inspection and stabilization recommended based on simulated risk patterns",
            )
        
        # Assemble all evidence
        evidence_sections = []

        evidence_sections.append(
            f"RISK ASSESSMENT:\n"
            f"  Level: {risk_assessment.get('overall_risk_level', 'unknown').upper()}\n"
            f"  Score: {risk_assessment.get('risk_score', 0):.1f}/100\n"
            f"  Immediate threats: {json.dumps(risk_assessment.get('immediate_threats', []))}\n"
            f"  Secondary risks: {json.dumps(risk_assessment.get('secondary_risks', []))}\n"
            f"  Time to critical: {risk_assessment.get('time_to_critical', 'unknown')}\n"
            f"  Risk factors: {json.dumps([rf.get('factor', '') if isinstance(rf, dict) else str(rf) for rf in risk_assessment.get('risk_factors', [])])}"
        )

        if vision_results:
            evidence_sections.append(
                f"VISUAL EVIDENCE:\n"
                f"  Damage indicators: {json.dumps(vision_results.get('damage_indicators', []))}\n"
                f"  Severity: {vision_results.get('severity_estimate', 'unknown')}\n"
                f"  Summary: {vision_results.get('analysis_summary', '')}"
            )

        if ocr_results:
            evidence_sections.append(
                f"DOCUMENT EVIDENCE:\n"
                f"  Critical findings: {json.dumps(ocr_results.get('critical_findings', []))}\n"
                f"  Key measurements: {json.dumps(ocr_results.get('key_entities', {}).get('measurements', []))}\n"
                f"  Timeline: {json.dumps(ocr_results.get('timeline_events', [])[:5])}"
            )

        if knowledge_results:
            evidence_sections.append(
                f"HISTORICAL KNOWLEDGE:\n"
                f"  Pattern: {knowledge_results.get('risk_pattern', '')}\n"
                f"  Key risk factors: {json.dumps(knowledge_results.get('key_risk_factors', []))}\n"
                f"  Protective factors: {json.dumps(knowledge_results.get('protective_factors', []))}\n"
                f"  Historical matches: {len(knowledge_results.get('historical_matches', []))} events"
            )

        if simulation_results:
            evidence_sections.append(
                f"SIMULATION RESULTS:\n"
                f"  Worst case: {simulation_results.get('worst_case_scenario', 'unknown')}\n"
                f"  Most likely: {simulation_results.get('most_likely_scenario', 'unknown')}\n"
                f"  Key variables: {json.dumps(simulation_results.get('key_variables', []))}"
            )

        full_evidence = "\n\n".join(evidence_sections)

        prompt = f"""
Generate specific, actionable recommendations for this incident.

INCIDENT TYPE: {incident_type}
LOCATION: {location or 'Unknown'}

ALL EVIDENCE:
{full_evidence}

Return recommendations as JSON:
{{
  "recommendations": [
    {{
      "priority": 1,
      "action": "specific action to take (not generic)",
      "rationale": "why this action is recommended based on evidence",
      "evidence": ["specific evidence items that support this recommendation"],
      "contributing_agents": ["vision|ocr|knowledge|risk|simulation"],
      "confidence_score": 0.0-1.0,
      "historical_matches": [
        {{"title": "past incident", "year": 2020, "relevance": "why relevant"}}
      ],
      "estimated_impact": "what this action will achieve",
      "time_sensitivity": "immediate|24h|48h|1week|1month",
      "implementation_notes": "practical implementation guidance",
      "cost_estimate": "rough cost if applicable"
    }}
  ],
  "primary_recommendation": "single most critical action",
  "overall_confidence": 0.0-1.0,
  "evidence_basis": ["list of all key evidence items across all recommendations"],
  "agent_contributions": {{
    "vision": "what vision analysis contributed",
    "ocr": "what document analysis contributed",
    "knowledge": "what historical analysis contributed",
    "risk": "what risk assessment contributed"
  }},
  "recommendation_summary": "2-3 sentence executive summary of recommended actions"
}}

REQUIREMENTS:
- Generate 4-6 recommendations ordered by priority (1=most urgent)
- Each recommendation must cite specific evidence, not generic risk
- Include at least one immediate action if risk is HIGH or CRITICAL
- Include at least one prevention/recovery action (priority 4+)
- Reference specific historical incidents when supporting recommendations
"""

        # Try primary model first, then fallbacks
        models_to_try = [self.primary_model] + self.fallback_models
        last_error = None

        for model_name in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=4000,
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
            parsed_recs = []
            for r in data.get("recommendations", []):
                try:
                    parsed_recs.append(Recommendation(**r))
                except Exception:
                    pass
            data["recommendations"] = parsed_recs
            return RecommendationResult(**data)
        except Exception as e:
            return RecommendationResult(
                recommendations=[],
                primary_recommendation="Assessment generation failed",
                overall_confidence=0.3,
                evidence_basis=[],
                agent_contributions={},
                recommendation_summary=f"Recommendation generation failed: {e}",
            )
