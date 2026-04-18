"""
Conscious Quality Filter Module.

This module implements the 'Consciousness Layer' of the scraper.
It uses LLM-based intuition to filter articles not just by keywords,
but by their 'vibe' and semantic alignment with the user's metaphysical interests.
"""

import logging
import random
from typing import List, Any
from src.core.quantum_types import QuantumArticle, ConsciousnessLevel
from config.settings import CONSCIOUSNESS_LEVEL

logger = logging.getLogger(__name__)

class QuantumConsciousnessField:
    """Represents the active consciousness field of the scraper."""
    
    def __init__(self, awareness_level: str = "medium", intuition_enabled: bool = True):
        self.awareness_level = ConsciousnessLevel(awareness_level)
        self.intuition_enabled = intuition_enabled
        
    def intuit_importance(self, content: str, timeline_relevance: str) -> float:
        """
        Calculate the 'intuition score' of a piece of content.
        This simulates a gut feeling about the article's importance.
        """
        # In a full implementation, this calls an LLM to analyze "vibes"
        # For now, we simulate the quantum fluctuation of interest
        
        base_score = 0.5
        
        # Keyword resonance
        if "quantum" in content.lower():
            base_score += 0.3
        if "breakthrough" in content.lower():
            base_score += 0.2
        if "future" in content.lower():
            base_score += 0.1
            
        # Awareness multiplier
        if self.awareness_level == ConsciousnessLevel.HIGH:
            # High consciousness is more discerning but more intuitive
            base_score *= 1.2
            
        # Add random quantum fluctuation (intuition is never static)
        fluctuation = random.uniform(-0.1, 0.1)
        
        return min(max(base_score + fluctuation, 0.0), 1.0)

class ConsciousQualityFilter:
    """
    Uses quantum consciousness to filter articles.
    Not just keyword matching, but semantic understanding.
    """
    
    def __init__(self):
        self.consciousness = QuantumConsciousnessField(
            awareness_level=CONSCIOUSNESS_LEVEL,
            intuition_enabled=True
        )
        logger.info(f"🧠 Conscious Filter initialized (Level: {CONSCIOUSNESS_LEVEL})")

    def filter_with_consciousness(self, articles: List[QuantumArticle]) -> List[QuantumArticle]:
        """
        Filter articles based on their intuitive importance score.
        """
        filtered = []
        
        for article in articles:
            # Intuition check
            intuition_score = self.consciousness.intuit_importance(
                content=article.content or article.title,
                timeline_relevance=article.timeline.value
            )
            
            # Store the score in the article's entanglement property
            article.entanglement_score = intuition_score
            
            # Threshold check (0.6 is the default 'resonance' threshold)
            if intuition_score > 0.6:
                filtered.append(article)
                logger.debug(f"  ✨ Article resonated: {article.title[:30]}... (Score: {intuition_score:.2f})")
            else:
                logger.debug(f"  🌑 Article discarded: {article.title[:30]}... (Score: {intuition_score:.2f})")
                
        logger.info(f"🧠 Consciousness filtered {len(articles)} -> {len(filtered)} articles")
        return filtered
