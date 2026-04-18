"""
Quantum Types Module.

This module defines the metaphysical data structures required for the 
Quantum Layer of the Tech News Scraper. It handles the definitions 
for Temporal States, Quantum Coherence, and Consciousness Levels.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Any
from datetime import datetime

class TemporalState(Enum):
    """The temporal position of a scraped artifact."""
    PAST = "past"       # Archived / Historical
    PRESENT = "present" # Real-time / Current
    FUTURE = "future"   # Predictive / Anticipated

class CoherenceStatus(Enum):
    """The quantum stability of the system."""
    STABLE = "stable"
    ENTANGLED = "entangled"
    COLLAPSING = "collapsing"
    SUPERPOSITION = "superposition"
    DECOHERENT = "decoherent"

class ConsciousnessLevel(Enum):
    """The level of semantic awareness applied to filtering."""
    LOW = "low"     # Robotic matching
    MEDIUM = "medium" # Semantic understanding
    HIGH = "high"    # Intuitive / "Psychic"

@dataclass
class QuantumArticle:
    """
    An article existing in a quantum state.
    
    Attributes:
        content: The actual text content.
        timeline: The temporal origin (PAST/PRESENT/FUTURE).
        probability: The likelihood of this news being true (0.0-1.0).
        reality_id: The identifier of the parallel reality source.
        entanglement_score: How strongly coupled it is to user intent.
        published_at: Publication timestamp (alias for timestamp for GUI compatibility).
    """
    id: str
    title: str
    content: str
    url: str
    timeline: TemporalState
    probability: float = 1.0
    reality_id: int = 1
    entanglement_score: float = 0.0
    timestamp: Optional[datetime] = None
    published_at: Optional[datetime] = None

@dataclass
class QuantumParadoxResult:
    """
    Result of a temporal feedback loop operation.
    Contains both the initial perception and the future-influenced result.
    """
    initial_observation: Any
    stabilized_reality: Any
    paradox_resolved: bool = True
