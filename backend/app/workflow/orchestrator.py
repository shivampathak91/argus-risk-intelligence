"""
ARGUS Platform — Antigravity Workflow Orchestrator
Executes the full multi-agent pipeline with parallel and sequential phases.
Uses asyncio for concurrency (ADK ParallelAgent + SequentialAgent pattern).
Broadcasts real-time progress via WebSocket.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)

from app.database.models import (
    Debate,
    Incident,
    IncidentType,
    Recommendation,
    Report,
    Upload,
    UploadType,
    Workflow,
    WorkflowStatus,
)
from app.database.session import get_db


# ── WebSocket Manager ─────────────────────────────────────────────────────────
# Imported lazily to avoid circular imports

def _broadcast(event_type: str, workflow_id: str, incident_id: str, data: dict):
    """Broadcast a WebSocket event to connected clients."""
    try:
        from app.main import ws_manager

        event = {
            "event_type": event_type,
            "workflow_id": workflow_id,
            "incident_id": incident_id,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        asyncio.create_task(ws_manager.broadcast(workflow_id, json.dumps(event)))
    except Exception:
        pass  # WebSocket errors never block the pipeline


def _update_agent_step(
    workflow_id: str,
    agent_name: str,
    status: str,
    output_summary: Optional[str] = None,
    error: Optional[str] = None,
    started_at: Optional[float] = None,
    completed_at: Optional[float] = None,
):
    """Update a single agent step in the workflow record."""
    logger.info(f"Updating agent step: {agent_name} -> {status} for workflow {workflow_id}")
    with get_db() as db:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow or not workflow.agent_steps:
            logger.warning(f"Workflow {workflow_id} not found or has no agent_steps")
            return

        steps = list(workflow.agent_steps)
        updated = False
        for step in steps:
            if step.get("agent") == agent_name:
                step["status"] = status
                if output_summary:
                    step["output_summary"] = output_summary[:500]
                if error:
                    step["error"] = str(error)[:500]
                if started_at:
                    step["started_at"] = datetime.fromtimestamp(started_at, tz=timezone.utc).isoformat()
                if completed_at and started_at:
                    step["completed_at"] = datetime.fromtimestamp(completed_at, tz=timezone.utc).isoformat()
                    step["duration_seconds"] = round(completed_at - started_at, 2)
                updated = True
                break

        if updated:
            # Use raw SQL update to bypass SQLAlchemy ORM JSON issues
            agent_steps_json = json.dumps(steps)
            db.execute(
                text("UPDATE workflows SET agent_steps = :agent_steps, updated_at = CURRENT_TIMESTAMP WHERE id = :workflow_id"),
                {"agent_steps": agent_steps_json, "workflow_id": workflow_id}
            )
            db.commit()
            logger.info(f"Successfully updated agent step {agent_name} to {status}")
        else:
            logger.warning(f"Agent {agent_name} not found in workflow steps")


async def _run_agent(
    agent_name: str,
    workflow_id: str,
    incident_id: str,
    fn,  # Callable that runs the agent (sync)
    *args,
    **kwargs,
) -> Optional[Any]:
    """
    Run a single agent in an executor (non-blocking).
    Updates workflow steps and broadcasts WebSocket events.
    """
    started_at = time.time()
    logger.info(f"[{workflow_id}] Starting {agent_name} agent for incident {incident_id}")
    _update_agent_step(workflow_id, agent_name, "running", started_at=started_at)
    _broadcast(
        "agent_started",
        workflow_id,
        incident_id,
        {"agent": agent_name, "started_at": datetime.fromtimestamp(started_at, tz=timezone.utc).isoformat()},
    )

    try:
        # Run synchronous agent code in threadpool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: fn(*args, **kwargs))
        completed_at = time.time()

        summary = _get_result_summary(agent_name, result)
        logger.info(f"[{workflow_id}] {agent_name} agent completed in {round(completed_at - started_at, 2)}s: {summary}")
        _update_agent_step(
            workflow_id, agent_name, "completed",
            output_summary=summary,
            started_at=started_at,
            completed_at=completed_at,
        )
        _broadcast(
            "agent_completed",
            workflow_id,
            incident_id,
            {
                "agent": agent_name,
                "duration_seconds": round(completed_at - started_at, 2),
                "summary": summary,
            },
        )
        return result

    except Exception as exc:
        completed_at = time.time()
        error_msg = str(exc)
        logger.error(f"[{workflow_id}] {agent_name} agent failed after {round(completed_at - started_at, 2)}s: {error_msg}")
        
        # Check if it's a quota/rate limit error - mark as skipped instead of failed
        if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            logger.warning(f"[{workflow_id}] {agent_name} skipped due to API quota limits")
            _update_agent_step(
                workflow_id, agent_name, "skipped",
                error="API quota exceeded - agent skipped",
                started_at=started_at,
                completed_at=completed_at,
            )
            _broadcast(
                "agent_skipped",
                workflow_id,
                incident_id,
                {"agent": agent_name, "error": "API quota exceeded"},
            )
            return None
        else:
            _update_agent_step(
                workflow_id, agent_name, "failed",
                error=error_msg,
                started_at=started_at,
                completed_at=completed_at,
            )
            _broadcast(
                "agent_failed",
                workflow_id,
                incident_id,
                {"agent": agent_name, "error": error_msg},
            )
            return None


def _get_result_summary(agent_name: str, result) -> str:
    """Extract a brief summary from agent result for step tracking."""
    if result is None:
        return "No output (agent may have been skipped)"

    try:
        if agent_name == "vision" and hasattr(result, "analysis_summary"):
            return result.analysis_summary[:200]
        elif agent_name == "ocr" and hasattr(result, "extraction_summary"):
            return result.extraction_summary[:200]
        elif agent_name == "knowledge" and hasattr(result, "knowledge_summary"):
            return result.knowledge_summary[:200]
        elif agent_name == "risk" and hasattr(result, "overall_risk_level"):
            return f"{result.overall_risk_level.upper()} risk (score: {result.risk_score:.1f}/100)"
        elif agent_name == "simulation" and hasattr(result, "simulation_summary"):
            return result.simulation_summary[:200]
        elif agent_name == "recommendation" and hasattr(result, "recommendation_summary"):
            return result.recommendation_summary[:200]
        elif agent_name == "report" and hasattr(result, "executive_summary"):
            return result.executive_summary[:200]
        elif agent_name == "commander" and hasattr(result, "mission_summary"):
            return result.mission_summary[:200]
        elif isinstance(result, dict):
            return str(result)[:200]
        else:
            return "Completed successfully"
    except Exception:
        return "Completed"


async def run_incident_pipeline(workflow_id: str, incident_id: str) -> None:
    """
    Main pipeline orchestrator.

    Execution Plan:
    ┌─────────────────────────────────────────────┐
    │         PHASE 1: PARALLEL INTAKE            │
    │  Vision Agent  │  OCR Agent  │  Knowledge   │
    └─────────────────────────────────────────────┘
                         │
    ┌─────────────────────────────────────────────┐
    │         PHASE 2: SEQUENTIAL ANALYSIS        │
    │  Risk Assessment → Simulation →             │
    │  Recommendation → Debate → Report           │
    └─────────────────────────────────────────────┘
                         │
    ┌─────────────────────────────────────────────┐
    │         PHASE 3: COMMANDER DECISION         │
    │  Commander synthesizes & debates conflicts  │
    └─────────────────────────────────────────────┘
    """
    pipeline_start = time.time()
    logger.info(f"[{workflow_id}] ===== STARTING INCIDENT PIPELINE =====")
    logger.info(f"[{workflow_id}] Incident ID: {incident_id}")
    
    # Track if pipeline actually ran agents
    agents_ran = False

    # ── Load incident ─────────────────────────────────────────────────────────
    logger.info(f"[{workflow_id}] Loading incident and workflow from database")
    with get_db() as db:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        uploads = db.query(Upload).filter(Upload.incident_id == incident_id).all()

        logger.info(f"[{workflow_id}] Workflow found: {workflow is not None}, Incident found: {incident is not None}, Uploads count: {len(uploads)}")

        if not workflow or not incident:
            logger.error(f"[{workflow_id}] Early return: workflow or incident not found")
            return

        # Mark running
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now(timezone.utc)

        incident_type = str(incident.incident_type)
        incident_title = incident.title
        incident_description = incident.description or ""
        location = incident.location_name
        lat = incident.latitude
        lng = incident.longitude

        # Categorize uploads
        image_uploads = [(u.file_path, u.id) for u in uploads if u.upload_type == UploadType.IMAGE]
        doc_uploads = [
            {"path": u.file_path, "upload_type": u.upload_type, "id": u.id}
            for u in uploads
            if u.upload_type in (UploadType.PDF, UploadType.CSV, UploadType.TXT)
        ]

    _broadcast("workflow_started", workflow_id, incident_id, {
        "incident_title": incident_title,
        "incident_type": incident_type,
        "image_count": len(image_uploads),
        "doc_count": len(doc_uploads),
    })

    class SkippedResult:
        def __init__(self, summary: str):
            self.summary = summary
            
        @property
        def analysis_summary(self): return self.summary
        @property
        def extraction_summary(self): return self.summary
        @property
        def knowledge_summary(self): return self.summary

    def run_vision_sync():
        if not image_uploads:
            return SkippedResult("No images to analyze")
        from app.agents.vision import VisionAgent
        agent = VisionAgent()
        image_paths = [p for p, _ in image_uploads]
        results = agent.analyze_multiple(image_paths, incident_context=incident_description)
        return agent.synthesize_multi_image_findings(results)

    def run_ocr_sync():
        if not doc_uploads:
            return SkippedResult("No documents to analyze")
        from app.agents.ocr import OCRAgent
        agent = OCRAgent()
        doc = doc_uploads[0]
        return agent.extract(doc["path"], doc["upload_type"], context=incident_description)

    def run_knowledge_sync():
        try:
            from app.agents.knowledge import KnowledgeAgent
            agent = KnowledgeAgent()
            return agent.analyze(
                incident_type=incident_type,
                incident_description=incident_description,
                key_findings=[],
                location=location,
            )
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                return SkippedResult("API quota exceeded - using fallback")
            raise

    # Run Phase 1 in parallel
    logger.info(f"[{workflow_id}] Starting Phase 1: Parallel intake")
    vision_data, ocr_data, knowledge_data = await asyncio.gather(
        _run_agent("vision", workflow_id, incident_id, run_vision_sync),
        _run_agent("ocr", workflow_id, incident_id, run_ocr_sync),
        _run_agent("knowledge", workflow_id, incident_id, run_knowledge_sync),
        return_exceptions=True,
    )
    logger.info(f"[{workflow_id}] Phase 1 gather complete")

    # Convert exceptions to None
    if isinstance(vision_data, Exception):
        logger.error(f"[{workflow_id}] Vision agent failed: {vision_data}")
        vision_data = None
    if isinstance(ocr_data, Exception):
        logger.error(f"[{workflow_id}] OCR agent failed: {ocr_data}")
        ocr_data = None
    if isinstance(knowledge_data, Exception):
        logger.error(f"[{workflow_id}] Knowledge agent failed: {knowledge_data}")
        knowledge_data = None

    def to_dict(data):
        if data is None or isinstance(data, SkippedResult):
            return {}
        return data.model_dump() if hasattr(data, "model_dump") else (data if isinstance(data, dict) else {})

    # Convert pydantic models to dicts
    vision_dict = to_dict(vision_data)
    ocr_dict = to_dict(ocr_data)
    knowledge_dict = to_dict(knowledge_data)

    _broadcast("phase_complete", workflow_id, incident_id, {"phase": "intake"})

    logger.info(f"[{workflow_id}] Phase 1 complete. Vision: {bool(vision_dict)}, OCR: {bool(ocr_dict)}, Knowledge: {bool(knowledge_dict)}")
    logger.info(f"[{workflow_id}] Starting Phase 2: Sequential analysis")

    try:
        # ── PHASE 2: Sequential analysis ──────────────────────────────────────────
        
        # Risk Assessment
        risk_data = None
        try:
            started = time.time()
            logger.info(f"[{workflow_id}] Starting risk assessment agent")
            _update_agent_step(workflow_id, "risk", "running", started_at=started)
            from app.agents.risk import RiskAssessmentAgent
            logger.info(f"[{workflow_id}] Initializing RiskAssessmentAgent...")
            risk_agent = RiskAssessmentAgent()
            logger.info(f"[{workflow_id}] Calling risk_agent.assess with incident_type={incident_type}, vision={bool(vision_dict)}, ocr={bool(ocr_dict)}, knowledge={bool(knowledge_dict)}")
            risk_result = risk_agent.assess(
                incident_type=incident_type,
                vision_results=vision_dict if vision_dict else None,
                ocr_results=ocr_dict if ocr_dict else None,
                knowledge_results=knowledge_dict if knowledge_dict else None,
                incident_description=incident_description,
                location=location,
            )
            risk_data = risk_result.model_dump()
            completed = time.time()
            logger.info(f"[{workflow_id}] Risk assessment completed in {round(completed - started, 2)}s: {risk_result.overall_risk_level} risk")
            _update_agent_step(workflow_id, "risk", "completed",
                              output_summary=_get_result_summary("risk", risk_result),
                              started_at=started, completed_at=completed)

            # Update incident risk level in DB
            with get_db() as db:
                incident_db = db.query(Incident).filter(Incident.id == incident_id).first()
                if incident_db:
                    incident_db.risk_level = risk_result.overall_risk_level
                    incident_db.confidence_score = risk_result.confidence_score
                    # Handle incident_type - strip prefix if present
                    new_type = str(risk_result.incident_type) if hasattr(risk_result, 'incident_type') else str(incident_type)
                    if new_type.startswith("IncidentType."):
                        new_type = new_type.replace("IncidentType.", "")
                    incident_db.incident_type = new_type

            _broadcast("agent_completed", workflow_id, incident_id, {
                "agent": "risk",
                "risk_level": risk_result.overall_risk_level,
                "risk_score": risk_result.risk_score,
            })
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{workflow_id}] Risk assessment failed with error: {error_msg}", exc_info=True)
            if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower() or "limit" in error_msg.lower():
                logger.warning(f"[{workflow_id}] Risk assessment skipped due to API quota")
                _update_agent_step(workflow_id, "risk", "skipped", error="API quota exceeded")
                if vision_dict:
                    risk_data = {"overall_risk_level": "medium", "confidence_score": 0.5, "incident_type": incident_type}
                    with get_db() as db:
                        incident_db = db.query(Incident).filter(Incident.id == incident_id).first()
                        if incident_db:
                            incident_db.risk_level = "medium"
                            incident_db.confidence_score = 0.5
            else:
                _update_agent_step(workflow_id, "risk", "failed", error=error_msg)
                # Set minimal risk_data to allow pipeline to continue
                risk_data = {"overall_risk_level": "medium", "confidence_score": 0.3, "incident_type": incident_type}

        # Simulation
        simulation_data = None
        if risk_data:
            try:
                started = time.time()
                logger.info(f"[{workflow_id}] Starting simulation agent")
                _update_agent_step(workflow_id, "simulation", "running", started_at=started)
                from app.agents.simulation import SimulationAgent
                sim_agent = SimulationAgent()
                sim_result = sim_agent.simulate(
                    incident_type=incident_type,
                    risk_assessment=risk_data,
                    knowledge_context=knowledge_dict if knowledge_dict else None,
                    ocr_data=ocr_dict if ocr_dict else None,
                )
                simulation_data = sim_result.model_dump()
                completed = time.time()
                logger.info(f"[{workflow_id}] Simulation completed in {round(completed - started, 2)}s: {len(sim_result.scenarios)} scenarios")
                _update_agent_step(workflow_id, "simulation", "completed",
                                  output_summary=_get_result_summary("simulation", sim_result),
                                  started_at=started, completed_at=completed)
                _broadcast("agent_completed", workflow_id, incident_id, {
                    "agent": "simulation",
                    "scenarios_count": len(sim_result.scenarios),
                })
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                    logger.warning(f"[{workflow_id}] Simulation skipped due to API quota")
                    _update_agent_step(workflow_id, "simulation", "skipped", error="API quota exceeded")
                    simulation_data = {"scenarios": [{"description": "Simulation skipped due to API quota"}]}
                else:
                    _update_agent_step(workflow_id, "simulation", "failed", error=error_msg)

        # Recommendation
        recommendation_data = None
        if risk_data:
            try:
                started = time.time()
                logger.info(f"[{workflow_id}] Starting recommendation agent")
                _update_agent_step(workflow_id, "recommendation", "running", started_at=started)
                from app.agents.recommendation import RecommendationAgent
                rec_agent = RecommendationAgent()
                rec_result = rec_agent.generate(
                    incident_type=incident_type,
                    risk_assessment=risk_data,
                    ocr_results=ocr_dict if ocr_dict else None,
                    vision_results=vision_dict if vision_dict else None,
                    knowledge_results=knowledge_dict if knowledge_dict else None,
                    simulation_results=simulation_data,
                    location=location,
                )
                recommendation_data = rec_result.model_dump()
                completed = time.time()
                logger.info(f"[{workflow_id}] Recommendation completed in {round(completed - started, 2)}s: {len(rec_result.recommendations)} recommendations")
                _update_agent_step(workflow_id, "recommendation", "completed",
                                  output_summary=_get_result_summary("recommendation", rec_result),
                                  started_at=started, completed_at=completed)

                # Persist recommendations to DB
                with get_db() as db:
                    for rec in rec_result.recommendations:
                        rec_dict = rec.model_dump() if hasattr(rec, "model_dump") else rec
                        db_rec = Recommendation(
                            incident_id=incident_id,
                            workflow_id=workflow_id,
                        priority=rec_dict.get("priority", 1),
                        action=rec_dict.get("action", ""),
                        rationale=rec_dict.get("rationale", ""),
                        evidence=rec_dict.get("evidence", []),
                        contributing_agents=rec_dict.get("contributing_agents", []),
                        confidence_score=rec_dict.get("confidence_score"),
                        historical_matches=rec_dict.get("historical_matches", []),
                        estimated_impact=rec_dict.get("estimated_impact"),
                        time_sensitivity=rec_dict.get("time_sensitivity"),
                    )
                    db.add(db_rec)

                _broadcast("agent_completed", workflow_id, incident_id, {
                    "agent": "recommendation",
                    "recommendations_count": len(rec_result.recommendations),
                })
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                    logger.warning(f"[{workflow_id}] Recommendation skipped due to API quota")
                    _update_agent_step(workflow_id, "recommendation", "skipped", error="API quota exceeded")
                    recommendation_data = {
                        "recommendations": [
                            {
                                "priority": 1,
                                "action": "Monitor incident closely",
                                "rationale": "Fallback recommendation due to API quota limits",
                                "confidence_score": 0.3,
                                "time_sensitivity": "immediate"
                            }
                        ]
                    }
                else:
                    _update_agent_step(workflow_id, "recommendation", "failed", error=error_msg)

        # ── PHASE 3: Commander decision & debate ──────────────────────────────────
        
        commander_data = None
        if risk_data and recommendation_data:
            try:
                started = time.time()
                logger.info(f"[{workflow_id}] Starting commander and debate agents")
                _update_agent_step(workflow_id, "debate", "running", started_at=started)
                _update_agent_step(workflow_id, "commander", "running", started_at=started)

                from app.agents.commander import CommanderAgent
                commander = CommanderAgent()
                commander_result = commander.command(
                    incident_type=incident_type,
                    risk_assessment=risk_data,
                    recommendations=recommendation_data,
                    knowledge_results=knowledge_dict if knowledge_dict else None,
                    simulation_results=simulation_data,
                    vision_results=vision_dict if vision_dict else None,
                    ocr_results=ocr_dict if ocr_dict else None,
                )
                commander_data = commander_result.model_dump()
                completed = time.time()

                logger.info(f"[{workflow_id}] Commander/debate completed in {round(completed - started, 2)}s: {len(commander_result.debate_results)} debates")
                _update_agent_step(workflow_id, "debate", "completed",
                                  output_summary=f"{len(commander_result.debate_results)} debates resolved",
                                  started_at=started, completed_at=completed)
                _update_agent_step(workflow_id, "commander", "completed",
                                  output_summary=commander_result.mission_summary[:200],
                                  started_at=started, completed_at=completed)

                # Persist debate results to DB
                with get_db() as db:
                    for debate in commander_result.debate_results:
                        debate_dict = debate.model_dump() if hasattr(debate, "model_dump") else debate
                        db_debate = Debate(
                            incident_id=incident_id,
                            workflow_id=workflow_id,
                            topic=debate_dict.get("topic", ""),
                            turns=[t.model_dump() if hasattr(t, "model_dump") else t
                                   for t in debate_dict.get("turns", [])],
                            final_decision=debate_dict.get("final_decision"),
                            decision_rationale=debate_dict.get("decision_rationale"),
                            decided_by="commander",
                            outcome_confidence=debate_dict.get("outcome_confidence"),
                        )
                        db.add(db_debate)

                _broadcast("debate_resolved", workflow_id, incident_id, {
                    "debates": len(commander_result.debate_results),
                    "final_risk_level": commander_result.final_risk_level,
                    "mission_summary": commander_result.mission_summary,
                })
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                    logger.warning(f"[{workflow_id}] Commander/debate skipped due to API quota")
                    _update_agent_step(workflow_id, "debate", "skipped", error="API quota exceeded")
                    _update_agent_step(workflow_id, "commander", "skipped", error="API quota exceeded")
                    commander_data = {
                        "mission_summary": "Commander analysis skipped due to API quota limits",
                        "debate_results": []
                    }
                else:
                    _update_agent_step(workflow_id, "debate", "failed", error=error_msg)
                    _update_agent_step(workflow_id, "commander", "failed", error=error_msg)

        # ── Report Generation ─────────────────────────────────────────────────────
        if risk_data and recommendation_data:
            try:
                started = time.time()
                logger.info(f"[{workflow_id}] Starting report generation agent")
                _update_agent_step(workflow_id, "report", "running", started_at=started)

                from app.agents.report import ReportAgent
                report_agent = ReportAgent()

                final_risk = commander_data.get("final_risk_level", risk_data.get("overall_risk_level")) if commander_data else risk_data.get("overall_risk_level")
                final_confidence = commander_data.get("final_confidence", risk_data.get("confidence_score")) if commander_data else risk_data.get("confidence_score")

                report_result = report_agent.generate(
                    incident_id=incident_id,
                    incident_title=incident_title,
                    incident_type=incident_type,
                    location=location,
                    risk_assessment=risk_data,
                    recommendations=recommendation_data,
                    knowledge_context=knowledge_dict if knowledge_dict else None,
                    simulation_results=simulation_data,
                    ocr_results=ocr_dict if ocr_dict else None,
                    vision_results=vision_dict if vision_dict else None,
                )

                # Build timeline from workflow steps
                with get_db() as db:
                    workflow_db = db.query(Workflow).filter(Workflow.id == workflow_id).first()
                    timeline = []
                    if workflow_db and workflow_db.agent_steps:
                        for step in workflow_db.agent_steps:
                            if step.get("started_at"):
                                timeline.append({
                                    "timestamp": step["started_at"],
                                    "event": f"{step['agent'].title()} Agent started",
                                })
                            if step.get("completed_at") and step.get("status") == "completed":
                                timeline.append({
                                    "timestamp": step["completed_at"],
                                    "event": f"{step['agent'].title()} Agent completed — {step.get('output_summary', '')[:100]}",
                                })

                    report_result.timeline = timeline

                    # Persist report to DB
                    db_report = Report(
                        incident_id=incident_id,
                        workflow_id=workflow_id,
                        title=report_result.title,
                        executive_summary=report_result.executive_summary,
                        risk_analysis=report_result.risk_analysis,
                        confidence_score=final_confidence,
                        risk_level=final_risk,
                        timeline=report_result.timeline,
                        data_sources=report_result.data_sources,
                        full_report_json=report_result.model_dump(),
                    )
                    db.add(db_report)

                completed = time.time()
                logger.info(f"[{workflow_id}] Report generation completed in {round(completed - started, 2)}s: {report_result.title}")
                _update_agent_step(workflow_id, "report", "completed",
                                  output_summary=report_result.executive_summary[:200],
                                  started_at=started, completed_at=completed)
                _broadcast("report_ready", workflow_id, incident_id, {
                    "title": report_result.title,
                    "risk_level": final_risk,
                })

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                    logger.warning(f"[{workflow_id}] Report generation skipped due to API quota")
                    _update_agent_step(workflow_id, "report", "skipped", error="API quota exceeded")
                else:
                    logger.error(f"[{workflow_id}] Report generation failed: {error_msg}")
                    _update_agent_step(workflow_id, "report", "failed", error=error_msg)

    except Exception as phase2_error:
        logger.error(f"[{workflow_id}] Phase 2 failed with exception: {phase2_error}")
        logger.error(f"[{workflow_id}] Phase 2 traceback: ", exc_info=True)
        # Mark workflow as failed if Phase 2 crashes
        with get_db() as db:
            workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if workflow:
                workflow.status = WorkflowStatus.FAILED
                workflow.error_message = f"Phase 2 execution failed: {str(phase2_error)}"

    # ── Finalize workflow ─────────────────────────────────────────────────────
    pipeline_end = time.time()
    with get_db() as db:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if workflow:
            # Check if all steps completed (allow some failures)
            steps = workflow.agent_steps or []
            failed_critical = any(
                s.get("status") == "failed" and s.get("agent") in ("risk", "commander")
                for s in steps
            )
            workflow.status = WorkflowStatus.FAILED if failed_critical else WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now(timezone.utc)
            workflow.total_duration_seconds = round(pipeline_end - pipeline_start, 2)

    logger.info(f"[{workflow_id}] Workflow completed in {round(pipeline_end - pipeline_start, 2)}s with status: {workflow.status if workflow else 'unknown'}")
    _broadcast("workflow_completed", workflow_id, incident_id, {
        "duration_seconds": round(pipeline_end - pipeline_start, 2),
        "status": "completed",
    })
