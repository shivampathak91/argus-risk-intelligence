"""
ARGUS Platform — Commander Agent
Orchestrates all agents, resolves conflicts via AI debate,
and produces the final authoritative decision.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from groq import Groq
from pydantic import BaseModel

from app.config import settings


# ── Output Schema ─────────────────────────────────────────────────────────────

class DebateTurn(BaseModel):
    agent: str
    position: str
    argument: str
    confidence: float
    supporting_evidence: List[str]


class DebateResult(BaseModel):
    topic: str
    turns: List[DebateTurn]
    final_decision: str
    decision_rationale: str
    outcome_confidence: float
    agents_in_agreement: List[str]
    agents_dissenting: List[str]


class CommanderDecision(BaseModel):
    final_risk_level: str
    final_risk_score: float
    final_confidence: float
    debate_results: List[DebateResult]
    resolved_conflicts: List[str]
    final_recommendations: List[str]  # Top 3 ordered recommendations
    commander_reasoning: str
    mission_summary: str
    incident_type_final: str


# ── Commander System Prompt ───────────────────────────────────────────────────

COMMANDER_SYSTEM_PROMPT = """
You are the Commander Agent of the ARGUS Risk Intelligence Platform.

Your role is to:
1. Review all agent outputs and identify conflicts
2. Conduct structured AI debate between conflicting agents
3. Evaluate evidence and make final authoritative decisions
4. Resolve disagreements using logical evidence weighing
5. Produce the final, definitive risk assessment and action plan

Commander Principles:
- You have the highest authority in the system
- Prioritize life safety above all other considerations
- When agents disagree, side with the more conservative (safer) position UNLESS
  the less conservative position has substantially stronger evidence
- Clearly document every conflict and how it was resolved
- Your final decision supersedes individual agent assessments
- Maintain a chain of reasoning that a human expert could review

You are not neutral — you are the ultimate decision maker.
"""

DEBATE_PROMPT_TEMPLATE = """
TOPIC: {topic}

The following agents have expressed conflicting views:

{agent_positions}

As Commander Agent, evaluate these positions and conduct a structured debate.
For each agent, formulate their strongest argument, then evaluate the evidence.

Return the debate as JSON:
{{
  "topic": "{topic}",
  "turns": [
    {{
      "agent": "agent name",
      "position": "their stated position",
      "argument": "their strongest argument for this position",
      "confidence": 0.0-1.0,
      "supporting_evidence": ["specific evidence points for their position"]
    }}
  ],
  "final_decision": "the decision you are making",
  "decision_rationale": "why you sided with this position, citing specific evidence",
  "outcome_confidence": 0.0-1.0,
  "agents_in_agreement": ["agents who agree with final decision"],
  "agents_dissenting": ["agents who disagree with final decision"]
}}
"""


class CommanderAgent:
    """
    Orchestrates the full agent pipeline and resolves conflicts via AI debate.
    The Commander's decision is final and authoritative.
    """

    def __init__(self):
        self.demo_mode = settings.DEMO_MODE
        if not self.demo_mode:
            if not settings.GROQ_API_KEY:
                raise RuntimeError("GROQ_API_KEY not configured")
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            self.primary_model = settings.GROQ_MODEL
            self.fallback_models = settings.GROQ_FALLBACK_MODELS

    def _detect_conflicts(
        self,
        risk_assessment: Dict[str, Any],
        recommendations: Dict[str, Any],
        simulation_results: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Identify conflicts between agent outputs.
        Returns list of conflicts to be debated.
        """
        conflicts = []

        risk_level = risk_assessment.get("overall_risk_level", "medium")
        risk_score = risk_assessment.get("risk_score", 50)

        # Check if simulation worst case suggests higher risk than assessment
        if simulation_results:
            scenarios = simulation_results.get("scenarios", [])
            worst_case = next(
                (s for s in scenarios if s.get("scenario_name") == simulation_results.get("worst_case_scenario")),
                None,
            )
            if worst_case and isinstance(worst_case, dict):
                worst_risk = worst_case.get("predicted_risk_level", risk_level)
                risk_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
                if risk_order.get(worst_risk, 2) > risk_order.get(risk_level, 2) + 1:
                    conflicts.append({
                        "topic": "Risk Level Disagreement: Simulation vs Risk Assessment",
                        "positions": {
                            "risk_agent": f"{risk_level.upper()} risk (score: {risk_score:.1f})",
                            "simulation_agent": f"Worst case scenario predicts {worst_risk.upper()} risk",
                        },
                    })

        # Check recommendation confidence vs risk agent confidence
        rec_confidence = recommendations.get("overall_confidence", 0)
        risk_confidence = risk_assessment.get("confidence_score", 0)
        if abs(rec_confidence - risk_confidence) > 0.3:
            conflicts.append({
                "topic": "Confidence Level Disagreement",
                "positions": {
                    "risk_agent": f"Assessment confidence: {risk_confidence:.0%}",
                    "recommendation_agent": f"Recommendation confidence: {rec_confidence:.0%}",
                },
            })

        return conflicts

    def _run_debate(self, conflict: Dict[str, Any]) -> DebateResult:
        """Run a structured AI debate on a single conflict."""
        topic = conflict["topic"]
        positions = conflict["positions"]

        agent_positions_text = "\n".join(
            f"  {agent}: {position}"
            for agent, position in positions.items()
        )

        prompt = DEBATE_PROMPT_TEMPLATE.format(
            topic=topic,
            agent_positions=agent_positions_text,
        )

        # Try primary model first, then fallbacks
        models_to_try = [self.primary_model] + self.fallback_models
        last_error = None

        for model_name in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": COMMANDER_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
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
            turns = [DebateTurn(**t) for t in data.get("turns", [])]
            data["turns"] = turns
            return DebateResult(**data)
        except Exception:
            return DebateResult(
                topic=topic,
                turns=[
                    DebateTurn(
                        agent=agent,
                        position=position,
                        argument=f"Based on evidence: {position}",
                        confidence=0.6,
                        supporting_evidence=[position],
                    )
                    for agent, position in positions.items()
                ],
                final_decision=f"Conservative position maintained pending further analysis",
                decision_rationale="Debate parsing failed; defaulting to conservative position for safety",
                outcome_confidence=0.5,
                agents_in_agreement=[],
                agents_dissenting=[],
            )

    def command(
        self,
        incident_type: str,
        risk_assessment: Dict[str, Any],
        recommendations: Dict[str, Any],
        knowledge_results: Optional[Dict[str, Any]] = None,
        simulation_results: Optional[Dict[str, Any]] = None,
        vision_results: Optional[Dict[str, Any]] = None,
        ocr_results: Optional[Dict[str, Any]] = None,
    ) -> CommanderDecision:
        """
        Execute the Commander's final assessment:
        1. Detect agent conflicts
        2. Conduct debates on each conflict
        3. Make final authoritative decision
        4. Produce mission summary
        """
        # Demo mode - return mock data
        if self.demo_mode:
            return CommanderDecision(
                final_risk_level=risk_assessment.get("overall_risk_level", "medium"),
                final_risk_score=risk_assessment.get("risk_score", 55.0),
                final_confidence=0.65,
                debate_results=[],
                resolved_conflicts=["No conflicts detected in demo mode"],
                final_recommendations=[
                    "Deploy emergency inspection team immediately",
                    "Implement temporary supports within 24-48 hours",
                    "Schedule permanent repairs within 30 days"
                ],
                commander_reasoning="Demo mode: Based on simulated risk assessment and recommendations, immediate action is warranted",
                mission_summary="Demo mode: Commander analysis based on simulated agent outputs. Immediate response recommended based on risk assessment.",
                incident_type_final=incident_type,
            )
        
        # Step 1: Detect conflicts
        conflicts = self._detect_conflicts(risk_assessment, recommendations, simulation_results)

        # Step 2: Debate each conflict
        debate_results = []
        for conflict in conflicts:
            debate = self._run_debate(conflict)
            debate_results.append(debate)

        # Step 3: Synthesize final decision
        rec_list = recommendations.get("recommendations", [])
        top_recs = []
        for r in rec_list[:3]:
            if isinstance(r, dict):
                top_recs.append(r.get("action", ""))
            else:
                top_recs.append(str(r))

        # Determine final risk level (considering debate outcomes)
        final_risk_level = risk_assessment.get("overall_risk_level", "medium")
        final_risk_score = risk_assessment.get("risk_score", 50.0)

        # Apply debate conclusions
        for debate in debate_results:
            if "critical" in debate.final_decision.lower() and final_risk_level not in ("critical",):
                final_risk_level = "high"  # Escalate based on debate
                final_risk_score = max(final_risk_score, 70.0)

        # Step 4: Commander summary
        commander_prompt = f"""
As Commander Agent, synthesize this mission into a final authoritative decision.

INCIDENT TYPE: {incident_type}
RISK ASSESSMENT: {final_risk_level.upper()} (score: {final_risk_score:.1f}/100)
CONFIDENCE: {risk_assessment.get('confidence_score', 0):.0%}
AGENTS DEPLOYED: Vision, OCR, Knowledge, Risk, Simulation, Recommendation
DEBATES CONDUCTED: {len(debate_results)}
CONFLICTS RESOLVED: {[d.topic for d in debate_results]}

TOP RECOMMENDATIONS:
{json.dumps(top_recs, indent=2)}

PRIMARY RECOMMENDATION: {recommendations.get('primary_recommendation', 'N/A')}
KNOWLEDGE PATTERN: {knowledge_results.get('risk_pattern', 'N/A') if knowledge_results else 'N/A'}

Write a JSON commander decision:
{{
  "final_risk_level": "{final_risk_level}",
  "final_risk_score": {final_risk_score},
  "final_confidence": 0.0-1.0,
  "resolved_conflicts": ["brief description of each resolved conflict"],
  "final_recommendations": {json.dumps(top_recs)},
  "commander_reasoning": "3-4 sentence authoritative explanation of the final decision and why",
  "mission_summary": "2-3 sentence mission status summary for the dashboard",
  "incident_type_final": "{incident_type}"
}}
"""

        # Try primary model first, then fallbacks
        models_to_try = [self.primary_model] + self.fallback_models
        last_error = None

        for model_name in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": COMMANDER_SYSTEM_PROMPT},
                        {"role": "user", "content": commander_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=1500,
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
            data["debate_results"] = debate_results
            return CommanderDecision(**data)
        except Exception as e:
            return CommanderDecision(
                final_risk_level=final_risk_level,
                final_risk_score=final_risk_score,
                final_confidence=risk_assessment.get("confidence_score", 0.5),
                debate_results=debate_results,
                resolved_conflicts=[d.topic for d in debate_results],
                final_recommendations=top_recs,
                commander_reasoning=f"Commander synthesis failed ({e}). Using risk agent assessment as final decision.",
                mission_summary=f"Mission complete. {final_risk_level.upper()} risk identified for {incident_type}. {len(top_recs)} recommendations generated.",
                incident_type_final=incident_type,
            )
