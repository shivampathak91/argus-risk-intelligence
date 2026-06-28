"""
ARGUS Platform — Vision Agent
Analyzes uploaded images using Gemini Vision to detect damage,
classify incidents, and extract visual evidence.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from pydantic import BaseModel

from app.config import settings


# ── Output Schema ─────────────────────────────────────────────────────────────

class VisionAnalysisResult(BaseModel):
    detected_objects: List[str]
    damage_indicators: List[str]
    incident_type_suggestion: str
    severity_estimate: str  # low / medium / high / critical
    confidence: float       # 0.0 - 1.0
    visual_evidence: List[str]
    location_clues: List[str]
    recommended_risk_factors: List[str]
    analysis_summary: str


# ── Agent ─────────────────────────────────────────────────────────────────────

VISION_SYSTEM_PROMPT = """
You are the Vision Agent of the ARGUS Risk Intelligence Platform.

Your role is to analyze images related to infrastructure incidents and natural disasters.

You MUST:
1. Identify ALL visible objects, structures, and environmental features
2. Detect ALL damage indicators (cracks, corrosion, flooding, fire damage, deformation, etc.)
3. Estimate the severity of visible damage honestly based on what you see
4. Extract any visible text, signs, measurements, or location clues
5. Identify infrastructure type (bridge, building, road, power line, etc.)
6. Note environmental conditions (flooding level, fire spread, structural stability)

You MUST NOT:
- Assume damage that is not visible
- Return generic responses
- Ignore minor details that could indicate risk

Your analysis directly feeds into the Risk Assessment and Recommendation agents.
Different images WILL produce different outputs. Be precise and specific.

Return your analysis in the requested JSON format.
"""

VISION_ANALYSIS_PROMPT = """
Analyze this image for the ARGUS Risk Intelligence Platform.

Provide a detailed JSON analysis with the following structure:
{
  "detected_objects": ["list of all visible objects and structures"],
  "damage_indicators": ["specific visible damage items with measurements/descriptions if possible"],
  "incident_type_suggestion": "most likely incident type",
  "severity_estimate": "low|medium|high|critical",
  "confidence": 0.0-1.0,
  "visual_evidence": ["specific visual evidence supporting your assessment"],
  "location_clues": ["any visible location indicators, signs, or geographical features"],
  "recommended_risk_factors": ["risk factors that other agents should investigate"],
  "analysis_summary": "comprehensive 2-3 sentence summary of what you see and its risk implications"
}

Be specific and quantitative where possible (e.g., "crack approximately 5cm wide", "floodwater depth estimated 1.2m based on vehicle submersion").
"""


class VisionAgent:
    """
    Analyzes uploaded images using Gemini Vision API.
    Returns structured damage assessment and visual evidence.
    """

    def __init__(self):
        self.demo_mode = settings.DEMO_MODE
        if not self.demo_mode:
            if not settings.GOOGLE_API_KEY:
                raise RuntimeError("GOOGLE_API_KEY is not configured. Vision analysis is unavailable.")
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.primary_model = settings.GEMINI_VISION_MODEL
            self.fallback_models = settings.GEMINI_FALLBACK_MODELS
            self.model = genai.GenerativeModel(
                model_name=self.primary_model,
                system_instruction=VISION_SYSTEM_PROMPT,
            )

    def _load_image(self, file_path: str) -> genai.types.BlobDict:
        """Load an image file and encode it for Gemini Vision."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {file_path}")

        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        mime_type = mime_map.get(path.suffix.lower(), "image/jpeg")

        with open(path, "rb") as f:
            image_data = f.read()

        return {"mime_type": mime_type, "data": image_data}

    def analyze(
        self,
        file_path: str,
        incident_context: Optional[str] = None,
    ) -> VisionAnalysisResult:
        """
        Analyze a single image.

        Args:
            file_path: Absolute path to the image file
            incident_context: Optional text describing the incident context

        Returns:
            VisionAnalysisResult with structured damage analysis
        """
        # Demo mode - return mock data
        if self.demo_mode:
            return VisionAnalysisResult(
                detected_objects=["bridge structure", "roadway", "support pillars", "river below"],
                damage_indicators=["visible cracks in support structure", "corrosion on steel beams", "deformation in main span"],
                incident_type_suggestion="bridge_failure",
                severity_estimate="high",
                confidence=0.75,
                visual_evidence=["structural deformation observed", "multiple crack patterns detected"],
                location_clues=["urban environment", "river crossing"],
                recommended_risk_factors=["structural fatigue", "environmental stress", "age-related deterioration"],
                analysis_summary="Demo mode: Simulated vision analysis indicates potential bridge structural issues requiring immediate inspection.",
            )

        image_data = self._load_image(file_path)

        prompt_parts = [VISION_ANALYSIS_PROMPT]
        if incident_context:
            prompt_parts.append(f"\nIncident Context: {incident_context}")
        prompt_parts.append("\nAnalyze the provided image now:")
        prompt_parts.append(image_data)

        # Try primary model first, then fallbacks
        models_to_try = [self.primary_model] + self.fallback_models
        last_error = None

        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=VISION_SYSTEM_PROMPT,
                )
                response = model.generate_content(
                    prompt_parts,
                    generation_config=genai.GenerationConfig(
                        temperature=0.2,  # Low temperature for factual analysis
                        max_output_tokens=2048,
                    ),
                )
                # If successful, break out of the loop
                break
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                # If it's a quota/rate limit error, try next model
                if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg or "resource exhausted" in error_msg:
                    import logging
                    logging.warning(f"Model {model_name} hit quota limit, trying fallback model...")
                    continue
                else:
                    # For other errors, don't try fallbacks
                    raise
        else:
            # All models failed
            raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")

        # Parse JSON from response
        raw_text = response.text.strip()
        # Extract JSON block if wrapped in markdown
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            # Attempt to extract JSON object from response
            import re
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                # Construct minimal result if JSON parsing fails
                data = {
                    "detected_objects": ["Unable to parse structured response"],
                    "damage_indicators": [],
                    "incident_type_suggestion": "unknown",
                    "severity_estimate": "unknown",
                    "confidence": 0.3,
                    "visual_evidence": [raw_text[:500]],
                    "location_clues": [],
                    "recommended_risk_factors": [],
                    "analysis_summary": raw_text[:500],
                }

        return VisionAnalysisResult(**data)

    def analyze_multiple(
        self,
        file_paths: List[str],
        incident_context: Optional[str] = None,
    ) -> Dict[str, VisionAnalysisResult]:
        """Analyze multiple images and return results keyed by file path."""
        results = {}
        for path in file_paths:
            try:
                results[path] = self.analyze(path, incident_context)
            except Exception as e:
                # Log failure but continue with other images
                results[path] = VisionAnalysisResult(
                    detected_objects=[],
                    damage_indicators=[],
                    incident_type_suggestion="unknown",
                    severity_estimate="unknown",
                    confidence=0.0,
                    visual_evidence=[],
                    location_clues=[],
                    recommended_risk_factors=[],
                    analysis_summary=f"Analysis failed: {e}",
                )
        return results

    def synthesize_multi_image_findings(
        self,
        individual_results: Dict[str, VisionAnalysisResult],
    ) -> Dict[str, Any]:
        """
        When multiple images are analyzed, synthesize findings into a unified assessment.
        Uses Gemini to reason across all image results.
        """
        if len(individual_results) == 1:
            result = list(individual_results.values())[0]
            return result.model_dump()

        # Build summary of all image analyses for synthesis
        summary_parts = ["You are synthesizing visual analysis from multiple images.\n"]
        for i, (path, result) in enumerate(individual_results.items(), start=1):
            summary_parts.append(
                f"Image {i} ({Path(path).name}):\n"
                f"  Damage: {', '.join(result.damage_indicators[:5])}\n"
                f"  Severity: {result.severity_estimate} (confidence: {result.confidence:.0%})\n"
                f"  Summary: {result.analysis_summary}\n"
            )

        synthesis_prompt = (
            "\n".join(summary_parts)
            + "\nSynthesize these findings into a single unified assessment JSON "
            "with the same structure as individual image analyses. "
            "The severity_estimate should reflect the worst observed condition."
        )

        response = self.model.generate_content(
            synthesis_prompt,
            generation_config=genai.GenerationConfig(temperature=0.2, max_output_tokens=1024),
        )

        raw = response.text.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(raw)
        except Exception:
            # Return the highest-severity individual result as fallback
            best = max(
                individual_results.values(),
                key=lambda r: {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(r.severity_estimate, 0),
            )
            return best.model_dump()
