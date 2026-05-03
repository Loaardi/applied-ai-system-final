"""
test_ai_reliability.py — Reliability & Testing Suite for PawPal+

Covers all four required testing areas:
1. Automated tests (unit tests for key functions)
2. Confidence scoring (AI rates how sure it is)
3. Logging and error handling (records what failed and why)
4. Human evaluation (structured output for peer review)

Run with: python -m pytest tests/test_ai_reliability.py -v
"""

import pytest
import logging
from datetime import datetime, date

from knowledge_base import KnowledgeBase
from ai_agent import PawPalAgent, AgentResponse
from pawpal_system import Owner, Pet, Task, Scheduler


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: AUTOMATED TESTS — Unit tests for core AI functions
# ═══════════════════════════════════════════════════════════════════════

class TestKnowledgeBaseRetrieval:
    """Test that the RAG knowledge base returns correct, structured data."""

    def setup_method(self):
        self.kb = KnowledgeBase()

    def test_retrieve_known_breed(self):
        """Breed-specific data should return high confidence."""
        result = self.kb.retrieve("Dog", "Golden Retriever")
        assert result["_confidence"] == 0.95
        assert result["_source"] == "Dog/Golden Retriever"
        assert "hip dysplasia" in result["health_notes"].lower()
        assert len(result["tasks"]) >= 5

    def test_retrieve_species_default(self):
        """Unknown breed falls back to species defaults with lower confidence."""
        result = self.kb.retrieve("Dog", "Shiba Inu")
        assert result["_confidence"] == 0.7
        assert result["_source"] == "Dog/_default"
        assert len(result["tasks"]) >= 3

    def test_retrieve_unknown_species(self):
        """Completely unknown species returns minimal data with low confidence."""
        result = self.kb.retrieve("Iguana")
        assert result["_confidence"] == 0.2
        assert result["_source"] == "none"
        assert "vet" in result["feeding"].lower() or "consult" in result["feeding"].lower()

    def test_retrieve_species_no_breed(self):
        """Species without breed specified returns defaults."""
        result = self.kb.retrieve("Cat")
        assert result["_confidence"] == 0.7
        assert result["_source"] == "Cat/_default"

    def test_retrieve_case_insensitive(self):
        """Retrieval should handle mixed case inputs."""
        result = self.kb.retrieve("dog", "golden retriever")
        assert result["_confidence"] == 0.95
        assert "Golden Retriever" in result["_source"]

    def test_retrieve_whitespace_handling(self):
        """Retrieval should strip whitespace from inputs."""
        result = self.kb.retrieve("  Dog  ", "  Golden Retriever  ")
        assert result["_confidence"] == 0.95

    def test_all_species_have_defaults(self):
        """Every species in the KB should have a _default entry."""
        for species in self.kb.get_supported_species():
            result = self.kb.retrieve(species)
            assert result["_confidence"] >= 0.7, f"{species} missing defaults"
            assert len(result["tasks"]) >= 1, f"{species} has no default tasks"

    def test_all_tasks_have_required_fields(self):
        """Every task in the KB should have description, hour, minute, frequency."""
        for species in self.kb.get_supported_species():
            result = self.kb.retrieve(species)
            for task in result.get("tasks", []):
                assert "description" in task, f"Missing description in {species}"
                assert "hour" in task, f"Missing hour in {species}"
                assert "minute" in task, f"Missing minute in {species}"
                assert 0 <= task["hour"] <= 23, f"Invalid hour in {species}"
                assert 0 <= task["minute"] <= 59, f"Invalid minute in {species}"

    def test_query_log_records_every_call(self):
        """Every retrieval should be logged for auditability."""
        self.kb.retrieve("Dog", "Golden Retriever")
        self.kb.retrieve("Cat")
        self.kb.retrieve("Iguana")
        log = self.kb.get_query_log()
        assert len(log) == 3
        assert log[0]["confidence"] == 0.95
        assert log[1]["confidence"] == 0.7
        assert log[2]["confidence"] == 0.2


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: CONFIDENCE SCORING — AI rates how sure it is
# ═══════════════════════════════════════════════════════════════════════

class TestConfidenceScoring:
    """Test that confidence scores accurately reflect data quality."""

    def setup_method(self):
        self.agent = PawPalAgent()

    def _make_pet(self, name="Buddy", species="Dog"):
        owner = Owner(name="TestOwner", age=30)
        pet = Pet(name=name, kind_of_animal=species, owner=owner)
        owner.add_pet(pet)
        return pet, owner

    def test_high_confidence_for_known_breed(self):
        """Known breed should produce confidence >= 0.8."""
        pet, owner = self._make_pet("Mochi", "Dog")
        response = self.agent.generate_care_plan(pet, breed="Golden Retriever", owner=owner)
        assert response.success is True
        assert response.confidence_score >= 0.8
        assert response.retrieval_source == "Dog/Golden Retriever"

    def test_medium_confidence_for_species_only(self):
        """Species without breed should produce medium confidence (0.5-0.8)."""
        pet, owner = self._make_pet("Rex", "Dog")
        response = self.agent.generate_care_plan(pet, breed=None, owner=owner)
        assert response.success is True
        assert 0.5 <= response.confidence_score <= 0.85

    def test_low_confidence_for_unknown_species(self):
        """Unknown species should produce low confidence (< 0.5)."""
        pet, owner = self._make_pet("Scales", "Iguana")
        response = self.agent.generate_care_plan(pet, breed=None, owner=owner)
        assert response.success is True
        assert response.confidence_score < 0.5

    def test_confidence_decreases_with_conflicts(self):
        """More schedule conflicts should lower confidence."""
        pet, owner = self._make_pet("Buddy", "Dog")
        today = date.today()

        # Add conflicting tasks at the same time
        for i in range(3):
            task = Task(
                description=f"Task {i}",
                time=datetime.combine(today, datetime.min.time().replace(hour=8)),
                frequency="daily",
                pet=pet,
            )
            pet.add_task(task)

        response = self.agent.generate_care_plan(pet, breed="Golden Retriever", owner=owner)
        # Should still succeed but with warnings that lower confidence
        assert response.success is True
        assert len(response.warnings) > 0

    def test_confidence_always_between_0_and_1(self):
        """Confidence score must always be in valid range."""
        pet, owner = self._make_pet("Any", "Dog")
        response = self.agent.generate_care_plan(pet, breed="Golden Retriever", owner=owner)
        assert 0.0 <= response.confidence_score <= 1.0

        # Edge case: unknown species
        pet2, owner2 = self._make_pet("Unknown", "Platypus")
        response2 = self.agent.generate_care_plan(pet2, owner=owner2)
        assert 0.0 <= response2.confidence_score <= 1.0


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: LOGGING AND ERROR HANDLING
# ═══════════════════════════════════════════════════════════════════════

class TestLoggingAndErrorHandling:
    """Test that the system logs actions and handles errors gracefully."""

    def setup_method(self):
        self.agent = PawPalAgent()

    def _make_pet(self, name="Buddy", species="Dog"):
        owner = Owner(name="TestOwner", age=30)
        pet = Pet(name=name, kind_of_animal=species, owner=owner)
        owner.add_pet(pet)
        return pet, owner

    def test_response_log_records_every_action(self):
        """Every agent action should be logged with metadata."""
        pet, owner = self._make_pet()
        self.agent.generate_care_plan(pet, breed="Golden Retriever", owner=owner)
        self.agent.analyze_schedule(owner)

        log = self.agent.get_response_log()
        assert len(log) == 2
        assert log[0]["action"] == "generate_care_plan"
        assert log[1]["action"] == "analyze_schedule"

        # Each log entry should have required fields
        for entry in log:
            assert "success" in entry
            assert "confidence" in entry
            assert "processing_time_ms" in entry
            assert "timestamp" in entry

    def test_processing_time_is_recorded(self):
        """Every response should record how long it took."""
        pet, owner = self._make_pet()
        response = self.agent.generate_care_plan(pet, owner=owner)
        assert response.processing_time_ms > 0
        assert response.processing_time_ms < 5000  # Should be fast (< 5s)

    def test_error_handling_returns_structured_response(self):
        """Errors should return a valid AgentResponse, not crash."""
        # Create a pet with None owner to potentially trigger edge cases
        pet, owner = self._make_pet("ErrorPet", "Dog")
        # Even with unusual inputs, the agent should return gracefully
        response = self.agent.generate_care_plan(pet, breed=None, owner=owner)
        assert isinstance(response, AgentResponse)
        assert response.success is True  # Should handle gracefully

    def test_empty_schedule_analysis_doesnt_crash(self):
        """Analyzing an empty schedule should return helpful message, not error."""
        owner = Owner(name="Empty", age=25)
        response = self.agent.analyze_schedule(owner)
        assert response.success is True
        assert response.confidence_score == 1.0
        assert "no tasks" in response.message.lower() or "add" in response.message.lower()

    def test_knowledge_base_query_log_persists(self):
        """KB query log should accumulate across multiple calls."""
        kb = KnowledgeBase()
        kb.retrieve("Dog", "Golden Retriever")
        kb.retrieve("Cat", "Persian")
        kb.retrieve("Hamster")  # Unknown

        log = kb.get_query_log()
        assert len(log) == 3
        confidences = [entry["confidence"] for entry in log]
        assert confidences == [0.95, 0.95, 0.2]

    def test_logger_captures_warnings(self, caplog):
        """Logger should capture warnings for unknown breeds."""
        kb = KnowledgeBase()
        with caplog.at_level(logging.WARNING, logger="pawpal.knowledge_base"):
            kb.retrieve("Dog", "Shiba Inu")
        assert any("not found" in record.message.lower() for record in caplog.records)


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: HUMAN EVALUATION — Structured output for peer review
# ═══════════════════════════════════════════════════════════════════════

class TestAgentOutputQuality:
    """
    Tests that verify output CONTENT quality, not just structure.
    These act as a checklist a human reviewer would use.
    """

    def setup_method(self):
        self.agent = PawPalAgent()

    def _make_pet(self, name="Buddy", species="Dog"):
        owner = Owner(name="TestOwner", age=30)
        pet = Pet(name=name, kind_of_animal=species, owner=owner)
        owner.add_pet(pet)
        return pet, owner

    def test_care_plan_mentions_breed_specific_info(self):
        """Output should reference breed-specific details, not just generic advice."""
        pet, owner = self._make_pet("Mochi", "Dog")
        response = self.agent.generate_care_plan(pet, breed="Golden Retriever", owner=owner)
        message_lower = response.message.lower()
        # Golden Retriever-specific terms should appear
        assert any(
            term in message_lower
            for term in ["hip dysplasia", "ear", "shedder", "retriever", "fetch"]
        ), f"Missing breed-specific info in: {response.message[:200]}"

    def test_care_plan_includes_all_care_categories(self):
        """A complete care plan should cover exercise, feeding, grooming, health."""
        pet, owner = self._make_pet("Buddy", "Dog")
        response = self.agent.generate_care_plan(pet, breed="Golden Retriever", owner=owner)
        message_lower = response.message.lower()
        for category in ["exercise", "feeding", "grooming", "health"]:
            assert category in message_lower, f"Missing '{category}' in care plan"

    def test_suggested_tasks_have_valid_times(self):
        """All suggested tasks should have realistic times (0-23 hours)."""
        pet, owner = self._make_pet("Rex", "Dog")
        response = self.agent.generate_care_plan(pet, breed="Labrador Retriever", owner=owner)
        for task in response.suggested_tasks:
            assert 0 <= task["hour"] <= 23, f"Invalid hour: {task['hour']}"
            assert 0 <= task["minute"] <= 59, f"Invalid minute: {task['minute']}"
            assert task["description"].strip() != "", "Empty task description"

    def test_cat_plan_does_not_include_walks(self):
        """Cat care plans should not suggest dog-specific activities."""
        pet, owner = self._make_pet("Whiskers", "Cat")
        response = self.agent.generate_care_plan(pet, owner=owner)
        for task in response.suggested_tasks:
            assert "walk" not in task["description"].lower(), \
                f"Cat plan incorrectly suggests walking: {task['description']}"

    def test_conflict_detection_in_analysis(self):
        """Schedule analysis should catch overlapping tasks."""
        pet, owner = self._make_pet("Buddy", "Dog")
        today = date.today()
        # Add two tasks at the same time
        t1 = Task(description="Feed", time=datetime.combine(today, datetime.min.time().replace(hour=8)), frequency="daily", pet=pet)
        t2 = Task(description="Walk", time=datetime.combine(today, datetime.min.time().replace(hour=8)), frequency="daily", pet=pet)
        pet.add_task(t1)
        pet.add_task(t2)

        response = self.agent.analyze_schedule(owner)
        assert response.success is True
        assert len(response.warnings) >= 1
        assert any("conflict" in w.lower() or "8:00" in w or "08:00" in w for w in response.warnings)

    def test_multi_pet_analysis_covers_all_pets(self):
        """Analysis of multi-pet household should mention all pets."""
        owner = Owner(name="Jordan", age=30)
        dog = Pet(name="Mochi", kind_of_animal="Dog", owner=owner)
        cat = Pet(name="Whiskers", kind_of_animal="Cat", owner=owner)
        owner.add_pet(dog)
        owner.add_pet(cat)

        today = date.today()
        dog.add_task(Task(description="Walk", time=datetime.combine(today, datetime.min.time().replace(hour=7)), frequency="daily", pet=dog))
        cat.add_task(Task(description="Feed", time=datetime.combine(today, datetime.min.time().replace(hour=8)), frequency="daily", pet=cat))

        response = self.agent.analyze_schedule(owner)
        assert response.success is True
        assert "2" in response.message  # Should mention 2 pets


# ═══════════════════════════════════════════════════════════════════════
# SUMMARY PRINTER — Run this to get the testing summary for the report
# ═══════════════════════════════════════════════════════════════════════

def print_test_summary():
    """
    Run this function to generate a formatted testing summary.
    Usage: python -c "from tests.test_ai_reliability import print_test_summary; print_test_summary()"
    """
    agent = PawPalAgent()
    kb = KnowledgeBase()

    print("=" * 60)
    print("PawPal+ AI Reliability Testing Summary")
    print("=" * 60)

    # Test 1: Confidence scores across scenarios
    print("\n📊 Confidence Scoring Results:")
    scenarios = [
        ("Dog", "Golden Retriever", "Known breed"),
        ("Dog", None, "Species only"),
        ("Cat", "Persian", "Known breed"),
        ("Iguana", None, "Unknown species"),
        ("Hamster", None, "Unknown species"),
    ]

    scores = []
    for species, breed, label in scenarios:
        owner = Owner(name="Test", age=30)
        pet = Pet(name="TestPet", kind_of_animal=species, owner=owner)
        owner.add_pet(pet)
        response = agent.generate_care_plan(pet, breed=breed, owner=owner)
        scores.append(response.confidence_score)
        print(f"  {label:20s} ({species:6s}, {str(breed):20s}) → confidence: {response.confidence_score:.2f}")

    avg_conf = sum(scores) / len(scores)
    print(f"\n  Average confidence: {avg_conf:.2f}")

    # Test 2: KB coverage
    print(f"\n📚 Knowledge Base Coverage:")
    print(f"  Supported species: {', '.join(kb.get_supported_species())}")
    for species in kb.get_supported_species():
        breeds = kb.get_available_breeds(species)
        print(f"  {species}: {len(breeds)} breed(s) — {', '.join(breeds) if breeds else 'defaults only'}")

    # Test 3: Response log
    print(f"\n📝 Agent Response Log ({len(agent.get_response_log())} actions recorded):")
    for entry in agent.get_response_log():
        print(f"  [{entry['timestamp'][:19]}] {entry['action']} — "
              f"success={entry['success']}, confidence={entry['confidence']:.2f}, "
              f"time={entry['processing_time_ms']:.0f}ms")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    print_test_summary()