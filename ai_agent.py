"""
ai_agent.py — Agentic AI Assistant for PawPal+

Implements the agentic workflow:
1. Parse user request
2. Retrieve relevant knowledge (RAG)
3. Reason about pet needs + schedule constraints
4. Generate personalized recommendations with confidence scores
5. Validate output before returning

Includes: confidence scoring, structured logging, error handling, guardrails.
"""

import logging
import time
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from knowledge_base import KnowledgeBase
from pawpal_system import Owner, Pet, Task, Scheduler

# ── Logging setup ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("pawpal_agent.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("pawpal.agent")


@dataclass
class AgentResponse:
    """Structured response from the AI agent, with metadata for testing."""
    success: bool
    message: str
    suggested_tasks: List[Dict] = field(default_factory=list)
    confidence_score: float = 0.0
    reasoning: str = ""
    retrieval_source: str = ""
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    error: Optional[str] = None


class PawPalAgent:
    """
    Agentic AI assistant for PawPal+.
    
    The agent follows a plan-retrieve-generate-validate loop:
    1. PLAN:     Determine what the user needs
    2. RETRIEVE: Query the knowledge base for relevant data (RAG)
    3. GENERATE: Build a response grounded in retrieved data
    4. VALIDATE: Check the response for conflicts, completeness, and safety
    
    Every response includes a confidence score (0.0 - 1.0) so the user
    and tests can evaluate how reliable the output is.
    """

    def __init__(self):
        self.kb = KnowledgeBase()
        self._response_log: List[Dict] = []
        logger.info("PawPalAgent initialized")

    # ── Main entry point ─────────────────────────────────────────────

    def generate_care_plan(
        self, pet: Pet, breed: Optional[str] = None, owner: Optional[Owner] = None
    ) -> AgentResponse:
        """
        Generate a full daily care plan for a pet.
        
        This is the primary agentic workflow:
        1. Retrieve breed/species data from knowledge base
        2. Analyze existing schedule for conflicts
        3. Generate task recommendations with reasoning
        4. Validate and score confidence
        """
        start_time = time.time()
        logger.info("Generating care plan for %s (%s, breed=%s)", pet.name, pet.kind_of_animal, breed)

        try:
            # ── STEP 1: RETRIEVE ─────────────────────────────────
            care_data = self.kb.retrieve(species=pet.kind_of_animal, breed=breed)
            retrieval_confidence = care_data.get("_confidence", 0.0)
            retrieval_source = care_data.get("_source", "unknown")

            logger.info(
                "Retrieved data from '%s' (confidence=%.2f)",
                retrieval_source, retrieval_confidence,
            )

            # ── STEP 2: ANALYZE existing schedule ────────────────
            existing_tasks = pet.get_tasks()
            existing_times = {t.time.strftime("%H:%M") for t in existing_tasks}
            warnings = []

            if owner:
                scheduler = Scheduler(owner)
                conflict_msg = scheduler.check_for_conflicts()
                if conflict_msg:
                    warnings.append(conflict_msg)
                    logger.warning("Existing conflicts detected: %s", conflict_msg)

            # ── STEP 3: GENERATE recommendations ─────────────────
            suggested_tasks = []
            reasoning_parts = []

            reasoning_parts.append(
                f"Analyzed care needs for {pet.name} ({pet.kind_of_animal}"
                + (f", {breed}" if breed else "")
                + f"). Data source: {retrieval_source}."
            )

            # Generate tasks from knowledge base data
            kb_tasks = care_data.get("tasks", [])
            if kb_tasks:
                reasoning_parts.append(
                    f"Knowledge base recommends {len(kb_tasks)} care tasks."
                )
                for task_info in kb_tasks:
                    time_str = f"{task_info['hour']:02d}:{task_info['minute']:02d}"

                    # Check if this task time conflicts with existing tasks
                    is_duplicate = time_str in existing_times
                    if is_duplicate:
                        warnings.append(
                            f"Task at {time_str} conflicts with existing schedule; "
                            f"review '{task_info['description']}' manually."
                        )

                    suggested_tasks.append({
                        "description": task_info["description"],
                        "hour": task_info["hour"],
                        "minute": task_info["minute"],
                        "frequency": task_info.get("frequency", "daily"),
                        "pet_name": pet.name,
                        "has_conflict": is_duplicate,
                    })
            else:
                reasoning_parts.append(
                    "No specific tasks found in knowledge base; providing general guidance."
                )

            # Add care summary to reasoning
            for key in ["exercise", "feeding", "grooming", "health_notes", "enrichment"]:
                if key in care_data and care_data[key]:
                    reasoning_parts.append(f"  {key.replace('_', ' ').title()}: {care_data[key]}")

            # ── STEP 4: VALIDATE and score ───────────────────────
            confidence = self._calculate_confidence(
                retrieval_confidence=retrieval_confidence,
                num_tasks=len(suggested_tasks),
                num_warnings=len(warnings),
                has_breed_data=breed is not None and retrieval_source != "none",
            )

            # Build the user-facing message
            message = self._format_care_plan(
                pet=pet,
                breed=breed,
                care_data=care_data,
                suggested_tasks=suggested_tasks,
                warnings=warnings,
                confidence=confidence,
            )

            elapsed_ms = (time.time() - start_time) * 1000

            response = AgentResponse(
                success=True,
                message=message,
                suggested_tasks=suggested_tasks,
                confidence_score=confidence,
                reasoning="\n".join(reasoning_parts),
                retrieval_source=retrieval_source,
                warnings=warnings,
                processing_time_ms=elapsed_ms,
            )

            self._log_response("generate_care_plan", response)
            logger.info(
                "Care plan generated (confidence=%.2f, tasks=%d, warnings=%d, time=%.0fms)",
                confidence, len(suggested_tasks), len(warnings), elapsed_ms,
            )
            return response

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error("Error generating care plan: %s", str(e), exc_info=True)
            response = AgentResponse(
                success=False,
                message=f"Sorry, I encountered an error generating the care plan: {str(e)}",
                confidence_score=0.0,
                error=str(e),
                processing_time_ms=elapsed_ms,
            )
            self._log_response("generate_care_plan", response)
            return response

    def analyze_schedule(self, owner: Owner) -> AgentResponse:
        """
        Analyze an existing schedule for problems and improvements.
        
        Checks for: time conflicts, missing care categories, 
        unrealistic timing, and provides improvement suggestions.
        """
        start_time = time.time()
        logger.info("Analyzing schedule for owner '%s'", owner.name)

        try:
            scheduler = Scheduler(owner)
            all_tasks = scheduler.get_all_tasks(sort_by_time=True)
            warnings = []
            suggestions = []

            if not all_tasks:
                response = AgentResponse(
                    success=True,
                    message="No tasks in the schedule yet. Add some tasks or generate a care plan to get started!",
                    confidence_score=1.0,
                    reasoning="Empty schedule — nothing to analyze.",
                    processing_time_ms=(time.time() - start_time) * 1000,
                )
                self._log_response("analyze_schedule", response)
                return response

            # Check for conflicts
            conflicts = scheduler.get_same_time_conflicts()
            if conflicts:
                for t1, t2 in conflicts:
                    warnings.append(
                        f"⚠️ Conflict: '{t1.description}' and '{t2.description}' "
                        f"are both at {t1.time.strftime('%H:%M')}."
                    )

            # Check each pet has minimum care coverage
            for pet in owner.pets:
                pet_tasks = [t for t in all_tasks if t.pet and t.pet.name == pet.name]
                task_descs = " ".join(t.description.lower() for t in pet_tasks)

                care_data = self.kb.retrieve(species=pet.kind_of_animal)
                
                if "feed" not in task_descs and "breakfast" not in task_descs and "dinner" not in task_descs:
                    suggestions.append(f"🍽️ {pet.name} has no feeding tasks. {care_data.get('feeding', 'Add feeding schedule.')}")

                if pet.kind_of_animal == "Dog" and "walk" not in task_descs:
                    suggestions.append(f"🚶 {pet.name} (Dog) has no walk scheduled. {care_data.get('exercise', 'Add daily walks.')}")

                if pet.kind_of_animal == "Cat" and "litter" not in task_descs:
                    suggestions.append(f"🧹 {pet.name} (Cat) has no litter box task. Clean daily for hygiene.")

            # Check for very early/late tasks
            for task in all_tasks:
                hour = task.time.hour
                if hour < 5:
                    warnings.append(
                        f"🌙 '{task.description}' for {task.pet.name} is at {task.time.strftime('%H:%M')} — "
                        f"very early. Is this intentional?"
                    )

            # Build response
            parts = [f"📋 Schedule Analysis for {owner.name}\n"]
            parts.append(f"Total tasks: {len(all_tasks)} across {len(owner.pets)} pet(s)\n")

            if warnings:
                parts.append("**Issues Found:**")
                for w in warnings:
                    parts.append(f"  {w}")
                parts.append("")

            if suggestions:
                parts.append("**Suggestions:**")
                for s in suggestions:
                    parts.append(f"  {s}")
                parts.append("")

            if not warnings and not suggestions:
                parts.append("✅ Schedule looks good! No conflicts or gaps detected.")

            confidence = self._calculate_confidence(
                retrieval_confidence=0.8,
                num_tasks=len(all_tasks),
                num_warnings=len(warnings),
                has_breed_data=True,
            )

            elapsed_ms = (time.time() - start_time) * 1000
            response = AgentResponse(
                success=True,
                message="\n".join(parts),
                confidence_score=confidence,
                reasoning=f"Analyzed {len(all_tasks)} tasks, found {len(warnings)} issues and {len(suggestions)} suggestions.",
                warnings=warnings,
                processing_time_ms=elapsed_ms,
            )
            self._log_response("analyze_schedule", response)
            return response

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error("Error analyzing schedule: %s", str(e), exc_info=True)
            response = AgentResponse(
                success=False,
                message=f"Error analyzing schedule: {str(e)}",
                confidence_score=0.0,
                error=str(e),
                processing_time_ms=elapsed_ms,
            )
            self._log_response("analyze_schedule", response)
            return response

    # ── Confidence scoring ───────────────────────────────────────────

    def _calculate_confidence(
        self,
        retrieval_confidence: float,
        num_tasks: int,
        num_warnings: int,
        has_breed_data: bool,
    ) -> float:
        """
        Calculate a confidence score (0.0 - 1.0) for the agent's output.
        
        Factors:
        - retrieval_confidence: How specific the knowledge base match was
        - num_tasks: More tasks = more complete plan
        - num_warnings: Warnings reduce confidence
        - has_breed_data: Breed-specific data is more reliable
        
        This score is included in every response so tests can verify
        the agent knows when it's uncertain.
        """
        score = retrieval_confidence * 0.5  # 50% from data quality

        # Task completeness (up to 30%)
        if num_tasks >= 5:
            score += 0.30
        elif num_tasks >= 3:
            score += 0.20
        elif num_tasks >= 1:
            score += 0.10

        # Breed specificity bonus (10%)
        if has_breed_data:
            score += 0.10

        # Warning penalty (up to -20%)
        penalty = min(num_warnings * 0.05, 0.20)
        score -= penalty

        # Clamp to [0.0, 1.0]
        final = max(0.0, min(1.0, round(score, 2)))
        logger.debug(
            "Confidence: retrieval=%.2f, tasks=%d, warnings=%d, breed=%s -> %.2f",
            retrieval_confidence, num_tasks, num_warnings, has_breed_data, final,
        )
        return final

    # ── Output formatting ────────────────────────────────────────────

    def _format_care_plan(
        self,
        pet: Pet,
        breed: Optional[str],
        care_data: Dict,
        suggested_tasks: List[Dict],
        warnings: List[str],
        confidence: float,
    ) -> str:
        """Format the care plan as a readable message for the UI."""
        parts = []

        # Header
        breed_str = f" ({breed})" if breed else ""
        parts.append(f"🐾 Daily Care Plan for {pet.name}{breed_str}\n")

        # Care summary
        if care_data.get("_source") != "none":
            parts.append(f"Based on {care_data.get('_source', 'general')} care guidelines:\n")
            
            for key, emoji in [
                ("exercise", "🏃"),
                ("feeding", "🍽️"),
                ("grooming", "✂️"),
                ("health_notes", "🏥"),
                ("enrichment", "🧩"),
            ]:
                if key in care_data and care_data[key]:
                    parts.append(f"  {emoji} {key.replace('_', ' ').title()}: {care_data[key]}")
            parts.append("")

        # Suggested schedule
        if suggested_tasks:
            parts.append("**Recommended Schedule:**\n")
            for task in sorted(suggested_tasks, key=lambda t: (t["hour"], t["minute"])):
                time_str = f"{task['hour']:02d}:{task['minute']:02d}"
                conflict = " ⚠️ (conflicts with existing task)" if task.get("has_conflict") else ""
                parts.append(f"  {time_str} — {task['description']} [{task['frequency']}]{conflict}")
            parts.append("")

        # Warnings
        if warnings:
            parts.append("**Warnings:**")
            for w in warnings:
                parts.append(f"  ⚠️ {w}")
            parts.append("")

        # Confidence indicator
        if confidence >= 0.8:
            conf_label = "High"
        elif confidence >= 0.5:
            conf_label = "Medium"
        else:
            conf_label = "Low"
        parts.append(f"📊 Confidence: {conf_label} ({confidence:.0%})")

        return "\n".join(parts)

    # ── Logging and auditability ─────────────────────────────────────

    def _log_response(self, action: str, response: AgentResponse):
        """Log every agent response for testing and auditing."""
        entry = {
            "action": action,
            "success": response.success,
            "confidence": response.confidence_score,
            "num_tasks": len(response.suggested_tasks),
            "num_warnings": len(response.warnings),
            "processing_time_ms": response.processing_time_ms,
            "error": response.error,
            "timestamp": datetime.now().isoformat(),
        }
        self._response_log.append(entry)

    def get_response_log(self) -> List[Dict]:
        """Return the full response log for testing and auditing."""
        return list(self._response_log)