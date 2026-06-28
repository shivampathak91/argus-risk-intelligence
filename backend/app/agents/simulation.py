"""
ARGUS Platform — Simulation Agent
Runs "what-if" scenario simulations based on current incident data.
Generates predicted outcomes for different intervention/deterioration scenarios.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from groq import Groq
from pydantic import BaseModel

from app.config import settings


# ── Output Schema ─────────────────────────────────────────────────────────────

class SimulationOutcome(BaseModel):
    scenario_name: str
    scenario_description: str
    probability: float                    # 0.0 - 1.0
    predicted_risk_level: str             # low / medium / high / critical
    risk_score_change: float              # delta from baseline risk score
    affected_population: Optional[int]
    infrastructure_impact: str
    economic_impact_usd: Optional[float]
    recommended_actions: List[str]
    time_to_impact: Optional[str]
    confidence: float
    reasoning: str


class SimulationResult(BaseModel):
    incident_type: str
    baseline_risk_level: str
    baseline_risk_score: float
    scenarios: List[SimulationOutcome]
    most_likely_scenario: str
    worst_case_scenario: str
    best_case_scenario: str
    simulation_confidence: float
    key_variables: List[str]           # Variables that most affect outcome
    simulation_summary: str


# ── Simulation System Prompt ──────────────────────────────────────────────────

SIMULATION_SYSTEM_PROMPT = """
You are the Simulation Agent of the ARGUS Risk Intelligence Platform.

Your role is to run "what-if" scenario simulations for infrastructure and disaster incidents.
You generate probabilistic outcome predictions based on:
1. Current incident state (from risk assessment)
2. Historical precedents (from knowledge base)
3. Parameter changes in each scenario

Simulation Principles:
- Base probability estimates on historical data when available
- Model cascade effects (e.g., bridge failure → road closure → delayed emergency response)
- Consider economic, population, and infrastructure impacts together
- Be conservative in best-case scenarios; be realistic in worst-case
- Different inputs MUST produce different simulation outputs
- Support scenarios like: flood worsens, repair delayed, budget cut, resource shortage

Never return identical outcomes for different scenarios.
Always justify probability estimates with reasoning.
"""


class SimulationAgent:
    """
    Generates "what-if" scenario simulations using Gemini.
    Outputs are derived from actual incident data and historical patterns.
    """

    def __init__(self):
        self.demo_mode = settings.DEMO_MODE
        if not self.demo_mode:
            if not settings.GROQ_API_KEY:
                raise RuntimeError("GROQ_API_KEY not configured")
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            self.primary_model = settings.GROQ_MODEL
            self.fallback_models = settings.GROQ_FALLBACK_MODELS

    # Default scenario templates (parameters are filled with actual incident data)
    DEFAULT_SCENARIOS = [
        {
            "name": "No Intervention",
            "description": "Current deterioration continues without any remediation or response",
            "parameter_changes": {"intervention": False, "time_horizon_days": 30},
        },
        {
            "name": "Immediate Emergency Response",
            "description": "Full emergency response deployed within 6 hours",
            "parameter_changes": {"intervention": True, "response_time_hours": 6, "resources": "full"},
        },
        {
            "name": "Delayed Response (72 hours)",
            "description": "Response delayed by 72 hours due to resource constraints",
            "parameter_changes": {"intervention": True, "response_time_hours": 72, "delay_reason": "resource shortage"},
        },
        {
            "name": "Worsening Conditions",
            "description": "Environmental conditions deteriorate (extreme weather, aftershocks, continued flooding)",
            "parameter_changes": {"conditions_worsen": True, "severity_multiplier": 1.5},
        },
        {
            "name": "Budget-Constrained Response",
            "description": "Response limited to 40% of required resources due to budget constraints",
            "parameter_changes": {"budget_reduction": 0.6, "resources": "partial"},
        },
    ]

    def simulate(
        self,
        incident_type: str,
        risk_assessment: Dict[str, Any],
        knowledge_context: Optional[Dict[str, Any]] = None,
        ocr_data: Optional[Dict[str, Any]] = None,
        custom_scenarios: Optional[List[Dict[str, Any]]] = None,
    ) -> SimulationResult:
        """
        Run scenario simulations for the current incident.
        
        Args:
            incident_type: Type of incident
            risk_assessment: Output from RiskAssessmentAgent
            knowledge_context: Output from KnowledgeAgent (historical outcomes)
            ocr_data: Extracted numerical data from documents
            custom_scenarios: Optional user-defined scenarios (in addition to defaults)
        """
        # Demo mode - return mock data
        if self.demo_mode:
            return SimulationResult(
                incident_type=incident_type,
                baseline_risk_level=risk_assessment.get("overall_risk_level", "medium"),
                baseline_risk_score=risk_assessment.get("risk_score", 55.0),
                scenarios=[
                    SimulationOutcome(
                        scenario_name="No Intervention",
                        scenario_description="Current deterioration continues without any remediation",
                        probability=0.7,
                        predicted_risk_level="critical",
                        risk_score_change=25.0,
                        affected_population=0,
                        infrastructure_impact="severe",
                        economic_impact_usd=500000.0,
                        recommended_actions=["Deploy emergency team", "Implement load restrictions"],
                        time_to_impact="30 days",
                        confidence=0.7,
                        reasoning="Without intervention, deterioration accelerates based on historical patterns",
                    ),
                    SimulationOutcome(
                        scenario_name="Immediate Response",
                        scenario_description="Full emergency response deployed within 6 hours",
                        probability=0.8,
                        predicted_risk_level="low",
                        risk_score_change=-30.0,
                        affected_population=0,
                        infrastructure_impact="minimal",
                        economic_impact_usd=50000.0,
                        recommended_actions=["Continue monitoring", "Schedule repairs"],
                        time_to_impact="30 days",
                        confidence=0.8,
                        reasoning="Rapid response contains damage and prevents escalation",
                    ),
                ],
                most_likely_scenario="Immediate Response",
                worst_case_scenario="No Intervention",
                best_case_scenario="Immediate Response",
                simulation_confidence=0.65,
                key_variables=["response_time", "resource_availability", "environmental_conditions"],
                simulation_summary="Demo mode: Simulation indicates immediate response significantly reduces risk trajectory",
            )
        
        scenarios = self.DEFAULT_SCENARIOS.copy()
        if custom_scenarios:
            scenarios.extend(custom_scenarios)

        # Build simulation context
        context_parts = [
            f"INCIDENT TYPE: {incident_type}",
            f"CURRENT RISK: {risk_assessment.get('overall_risk_level', 'unknown').upper()} "
            f"(score: {risk_assessment.get('risk_score', 0):.1f}/100)",
            f"IMMEDIATE THREATS: {json.dumps(risk_assessment.get('immediate_threats', []))}",
            f"POPULATION AT RISK: {risk_assessment.get('population_at_risk', 'unknown')}",
            f"TIME TO CRITICAL: {risk_assessment.get('time_to_critical', 'unknown')}",
        ]

        if knowledge_context:
            context_parts.append(
                f"HISTORICAL PATTERN: {knowledge_context.get('risk_pattern', 'N/A')}\n"
                f"TYPICAL OUTCOMES: {json.dumps(knowledge_context.get('typical_outcomes', [])[:3])}\n"
                f"KEY RISK FACTORS: {json.dumps(knowledge_context.get('key_risk_factors', [])[:5])}"
            )

        if ocr_data:
            context_parts.append(
                f"NUMERICAL DATA: {json.dumps(ocr_data.get('numerical_data', {}), default=str)[:1000]}\n"
                f"CRITICAL FINDINGS: {json.dumps(ocr_data.get('critical_findings', [])[:5])}"
            )

        incident_context = "\n".join(context_parts)

        prompt = f"""
{incident_context}

SCENARIOS TO SIMULATE:
{json.dumps(scenarios, indent=2)}

Simulate each scenario and return results as JSON:
{{
  "incident_type": "{incident_type}",
  "baseline_risk_level": "current risk level",
  "baseline_risk_score": current_risk_score,
  "scenarios": [
    {{
      "scenario_name": "name of scenario",
      "scenario_description": "what this scenario entails",
      "probability": 0.0-1.0,
      "predicted_risk_level": "low|medium|high|critical",
      "risk_score_change": positive_or_negative_delta,
      "affected_population": number_or_null,
      "infrastructure_impact": "specific infrastructure consequences",
      "economic_impact_usd": estimated_dollar_amount_or_null,
      "recommended_actions": ["actions to take under this scenario"],
      "time_to_impact": "when consequences materialize",
      "confidence": 0.0-1.0,
      "reasoning": "explanation of why this outcome is predicted with this probability"
    }}
  ],
  "most_likely_scenario": "scenario name",
  "worst_case_scenario": "scenario name",
  "best_case_scenario": "scenario name",
  "simulation_confidence": 0.0-1.0,
  "key_variables": ["variables that most determine outcome"],
  "simulation_summary": "2-3 sentence overview of simulation findings"
}}

CRITICAL: Each scenario MUST have a different probability and different risk score change.
Base all estimates on the actual incident data provided above.
"""

        # Try primary model first, then fallbacks
        models_to_try = [self.primary_model] + self.fallback_models
        last_error = None

        for model_name in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": SIMULATION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
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
            parsed_scenarios = []
            for s in data.get("scenarios", []):
                try:
                    parsed_scenarios.append(SimulationOutcome(**s))
                except Exception:
                    pass
            data["scenarios"] = parsed_scenarios
            return SimulationResult(**data)
        except Exception as e:
            baseline = risk_assessment.get("overall_risk_level", "medium")
            baseline_score = risk_assessment.get("risk_score", 50.0)
            return SimulationResult(
                incident_type=incident_type,
                baseline_risk_level=baseline,
                baseline_risk_score=baseline_score,
                scenarios=[],
                most_likely_scenario="Unknown",
                worst_case_scenario="Unknown",
                best_case_scenario="Unknown",
                simulation_confidence=0.3,
                key_variables=[],
                simulation_summary=f"Simulation failed to parse: {e}",
            )
