"""
knowledge_base.py — RAG Knowledge Store for PawPal+

Stores breed-specific pet care data and retrieves it by species/breed.
This is the "Retrieval" part of Retrieval-Augmented Generation.
"""

import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("pawpal.knowledge_base")

# ── Pet care knowledge base ──────────────────────────────────────────
# Each entry contains structured care data for a specific breed/species.
# The AI agent retrieves this BEFORE generating recommendations.

PET_CARE_DATA: Dict[str, Dict] = {
    "Dog": {
        "_default": {
            "exercise": "30-60 minutes of daily exercise (walks, play)",
            "feeding": "2 meals per day, portion based on weight",
            "grooming": "Brush weekly, bathe monthly",
            "health_notes": "Annual vet checkup, keep vaccinations current",
            "enrichment": "Interactive toys, training sessions, socialization",
            "tasks": [
                {"description": "Morning walk", "hour": 7, "minute": 0, "frequency": "daily"},
                {"description": "Breakfast", "hour": 8, "minute": 0, "frequency": "daily"},
                {"description": "Dinner", "hour": 18, "minute": 0, "frequency": "daily"},
                {"description": "Evening walk", "hour": 17, "minute": 0, "frequency": "daily"},
            ],
        },
        "Golden Retriever": {
            "exercise": "1-2 hours daily; high-energy breed that loves fetch and swimming",
            "feeding": "2 meals/day, 2-3 cups each; prone to obesity so measure portions",
            "grooming": "Daily brushing (heavy shedder), check ears for moisture/infection",
            "health_notes": "Prone to hip dysplasia, ear infections, and cancer. Vet checkups every 6 months recommended",
            "enrichment": "Puzzle toys, retrieval games, obedience training (highly trainable)",
            "tasks": [
                {"description": "Morning walk", "hour": 7, "minute": 0, "frequency": "daily"},
                {"description": "Breakfast (measured portion)", "hour": 8, "minute": 0, "frequency": "daily"},
                {"description": "Midday enrichment", "hour": 12, "minute": 30, "frequency": "daily"},
                {"description": "Evening walk", "hour": 17, "minute": 0, "frequency": "daily"},
                {"description": "Dinner (measured portion)", "hour": 18, "minute": 0, "frequency": "daily"},
                {"description": "Brush coat", "hour": 20, "minute": 0, "frequency": "daily"},
                {"description": "Ear check", "hour": 20, "minute": 15, "frequency": "weekly"},
            ],
        },
        "Labrador Retriever": {
            "exercise": "1-2 hours daily; loves swimming and retrieving",
            "feeding": "2 meals/day, 2-3 cups each; very food-motivated, watch for overeating",
            "grooming": "Brush 2-3 times per week, more during shedding season",
            "health_notes": "Prone to hip/elbow dysplasia and obesity. Regular weight monitoring important",
            "enrichment": "Food puzzles, fetch, dock diving, nose work",
            "tasks": [
                {"description": "Morning walk", "hour": 7, "minute": 0, "frequency": "daily"},
                {"description": "Breakfast (measured)", "hour": 8, "minute": 0, "frequency": "daily"},
                {"description": "Midday activity", "hour": 12, "minute": 30, "frequency": "daily"},
                {"description": "Evening walk", "hour": 17, "minute": 0, "frequency": "daily"},
                {"description": "Dinner (measured)", "hour": 18, "minute": 0, "frequency": "daily"},
                {"description": "Brush coat", "hour": 20, "minute": 0, "frequency": "weekly"},
            ],
        },
        "Chihuahua": {
            "exercise": "20-30 minutes daily; short walks, indoor play",
            "feeding": "2 meals/day, 1/4 to 1/2 cup each; small stomachs, avoid overfeeding",
            "grooming": "Brush weekly (short coat) or daily (long coat), dental care critical",
            "health_notes": "Prone to dental disease, patellar luxation, hypoglycemia. Keep warm in cold weather",
            "enrichment": "Small puzzle toys, gentle training sessions, lap time",
            "tasks": [
                {"description": "Morning walk (short)", "hour": 8, "minute": 0, "frequency": "daily"},
                {"description": "Breakfast", "hour": 8, "minute": 30, "frequency": "daily"},
                {"description": "Dinner", "hour": 18, "minute": 0, "frequency": "daily"},
                {"description": "Dental chew", "hour": 19, "minute": 0, "frequency": "daily"},
                {"description": "Brush teeth", "hour": 20, "minute": 0, "frequency": "weekly"},
            ],
        },
    },
    "Cat": {
        "_default": {
            "exercise": "15-30 minutes of interactive play daily",
            "feeding": "2 meals per day, wet and/or dry food",
            "grooming": "Brush weekly, trim nails biweekly",
            "health_notes": "Annual vet checkup, dental care important",
            "enrichment": "Climbing structures, window perches, feather toys",
            "tasks": [
                {"description": "Breakfast", "hour": 7, "minute": 30, "frequency": "daily"},
                {"description": "Clean litter box", "hour": 8, "minute": 0, "frequency": "daily"},
                {"description": "Play session", "hour": 14, "minute": 0, "frequency": "daily"},
                {"description": "Dinner", "hour": 18, "minute": 0, "frequency": "daily"},
                {"description": "Evening play session", "hour": 21, "minute": 0, "frequency": "daily"},
            ],
        },
        "Persian": {
            "exercise": "15-20 minutes daily; calm breed, prefers gentle play",
            "feeding": "2 meals/day; may need flat-faced bowl design",
            "grooming": "Daily brushing required (long coat mats easily), face cleaning daily",
            "health_notes": "Prone to breathing issues (brachycephalic), kidney disease, eye discharge",
            "enrichment": "Gentle toys, window watching, quiet companionship",
            "tasks": [
                {"description": "Breakfast", "hour": 7, "minute": 30, "frequency": "daily"},
                {"description": "Clean litter box", "hour": 8, "minute": 0, "frequency": "daily"},
                {"description": "Brush coat (required daily)", "hour": 9, "minute": 0, "frequency": "daily"},
                {"description": "Clean face/eyes", "hour": 9, "minute": 15, "frequency": "daily"},
                {"description": "Gentle play", "hour": 14, "minute": 0, "frequency": "daily"},
                {"description": "Dinner", "hour": 18, "minute": 0, "frequency": "daily"},
            ],
        },
    },
    "Bird": {
        "_default": {
            "exercise": "Supervised out-of-cage time daily (1-2 hours)",
            "feeding": "Fresh food and water daily; species-appropriate seed/pellet mix",
            "grooming": "Provide bathing dish, nail trims as needed",
            "health_notes": "Avian vet checkup annually; watch for feather plucking (stress sign)",
            "enrichment": "Foraging toys, mirrors, music, talking/training",
            "tasks": [
                {"description": "Fresh water and food", "hour": 7, "minute": 0, "frequency": "daily"},
                {"description": "Out-of-cage time", "hour": 10, "minute": 0, "frequency": "daily"},
                {"description": "Cage spot-clean", "hour": 18, "minute": 0, "frequency": "daily"},
                {"description": "Full cage cleaning", "hour": 10, "minute": 0, "frequency": "weekly"},
            ],
        },
    },
    "Fish": {
        "_default": {
            "exercise": "Adequate tank size for swimming; species-appropriate tank mates",
            "feeding": "1-2 small feedings per day; remove uneaten food",
            "grooming": "Weekly partial water change (25%), filter maintenance monthly",
            "health_notes": "Monitor water temperature and pH; watch for white spots or lethargy",
            "enrichment": "Plants, hiding spots, varied diet",
            "tasks": [
                {"description": "Morning feeding", "hour": 8, "minute": 0, "frequency": "daily"},
                {"description": "Evening feeding", "hour": 18, "minute": 0, "frequency": "daily"},
                {"description": "Check water temperature", "hour": 9, "minute": 0, "frequency": "daily"},
                {"description": "Partial water change", "hour": 10, "minute": 0, "frequency": "weekly"},
                {"description": "Filter maintenance", "hour": 10, "minute": 0, "frequency": "monthly"},
            ],
        },
    },
    "Rabbit": {
        "_default": {
            "exercise": "3-4 hours of free-roam time daily; rabbits need space to hop",
            "feeding": "Unlimited hay, fresh greens daily, small amount of pellets",
            "grooming": "Brush weekly (more for long-haired breeds), nail trims monthly",
            "health_notes": "Vet checkup annually; prone to GI stasis if diet is wrong. Teeth grow continuously",
            "enrichment": "Tunnels, digging boxes, chew toys, social interaction",
            "tasks": [
                {"description": "Fresh hay and water", "hour": 7, "minute": 0, "frequency": "daily"},
                {"description": "Fresh greens", "hour": 12, "minute": 0, "frequency": "daily"},
                {"description": "Free-roam time", "hour": 16, "minute": 0, "frequency": "daily"},
                {"description": "Pellet feeding (small amount)", "hour": 18, "minute": 0, "frequency": "daily"},
                {"description": "Clean litter area", "hour": 8, "minute": 0, "frequency": "daily"},
                {"description": "Nail trim", "hour": 10, "minute": 0, "frequency": "monthly"},
            ],
        },
    },
}


class KnowledgeBase:
    """
    RAG Knowledge Store — retrieves breed-specific pet care data.
    
    The AI agent calls retrieve() BEFORE generating any recommendation.
    This grounds the AI's output in structured, vetted data rather than
    relying solely on the model's training data.
    """

    def __init__(self):
        self.data = PET_CARE_DATA
        self._query_log: List[Dict] = []
        logger.info("KnowledgeBase initialized with %d species", len(self.data))

    def retrieve(self, species: str, breed: Optional[str] = None) -> Dict:
        """
        Retrieve care data for a given species and optional breed.
        
        Returns breed-specific data if available, otherwise falls back
        to species-level defaults. Logs every query for auditability.
        
        Args:
            species: The animal type (e.g., "Dog", "Cat")
            breed: Optional specific breed (e.g., "Golden Retriever")
            
        Returns:
            Dict with keys: exercise, feeding, grooming, health_notes,
            enrichment, tasks, _source (what matched), _confidence (how specific)
        """
        query = {"species": species, "breed": breed}
        
        # Normalize inputs
        species_key = species.strip().title() if species else ""
        breed_key = breed.strip().title() if breed else None

        # Try to find matching data
        if species_key not in self.data:
            result = self._not_found(species_key, breed_key)
            self._log_query(query, result)
            return result

        species_data = self.data[species_key]

        # Try breed-specific first
        if breed_key and breed_key in species_data:
            result = {**species_data[breed_key]}
            result["_source"] = f"{species_key}/{breed_key}"
            result["_confidence"] = 0.95
            logger.info("Retrieved breed-specific data: %s/%s", species_key, breed_key)
            self._log_query(query, result)
            return result

        # Fall back to species default
        if "_default" in species_data:
            result = {**species_data["_default"]}
            result["_source"] = f"{species_key}/_default"
            result["_confidence"] = 0.7
            if breed_key:
                logger.warning(
                    "Breed '%s' not found for %s; using species defaults",
                    breed_key, species_key,
                )
            else:
                logger.info("Retrieved species defaults for %s", species_key)
            self._log_query(query, result)
            return result

        result = self._not_found(species_key, breed_key)
        self._log_query(query, result)
        return result

    def _not_found(self, species: str, breed: Optional[str]) -> Dict:
        """Return a minimal result when no data is found."""
        logger.warning("No data found for species='%s', breed='%s'", species, breed)
        return {
            "exercise": "Research specific needs for this animal",
            "feeding": "Consult a veterinarian for dietary guidance",
            "grooming": "Basic grooming as appropriate for the species",
            "health_notes": "Regular vet checkups recommended",
            "enrichment": "Provide species-appropriate stimulation",
            "tasks": [],
            "_source": "none",
            "_confidence": 0.2,
        }

    def _log_query(self, query: Dict, result: Dict):
        """Record every retrieval for auditability."""
        entry = {
            "query": query,
            "source": result.get("_source", "unknown"),
            "confidence": result.get("_confidence", 0.0),
        }
        self._query_log.append(entry)
        logger.debug("Query log entry: %s", entry)

    def get_query_log(self) -> List[Dict]:
        """Return the full query log for testing and auditing."""
        return list(self._query_log)

    def get_available_breeds(self, species: str) -> List[str]:
        """List all breeds with specific data for a species."""
        species_key = species.strip().title() if species else ""
        if species_key not in self.data:
            return []
        return [k for k in self.data[species_key] if k != "_default"]

    def get_supported_species(self) -> List[str]:
        """List all species in the knowledge base."""
        return list(self.data.keys())