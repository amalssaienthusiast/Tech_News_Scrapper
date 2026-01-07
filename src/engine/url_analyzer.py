"""
URL Analyzer for deep knowledge extraction.

This module provides comprehensive URL analysis:
- Full content extraction with structure
- Entity extraction (companies, people, technologies)
- Key points summarization
- Related content discovery
- Knowledge graph building
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp
from bs4 import BeautifulSoup

# Local imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.core.types import Article, SourceTier, TechScore
from src.data_structures import TechKeywordMatcher
from src.engine.deep_scraper import ContentExtractor, DeepScraper

logger = logging.getLogger(__name__)


@dataclass
class EntityExtraction:
    """
    Extracted entities from content.
    
    Attributes:
        companies: Company/organization names
        people: Person names
        technologies: Technology/product names
        locations: Mentioned locations
        dates: Mentioned dates
    """
    companies: List[str] = field(default_factory=list)
    people: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)


@dataclass
class KeyPoint:
    """A key point extracted from the article."""
    text: str
    importance: float  # 0.0 to 1.0
    category: str  # "main", "supporting", "detail"


@dataclass
class URLAnalysisResult:
    """
    Comprehensive analysis result for a URL.
    
    Attributes:
        url: Analyzed URL
        article: Base article data
        entities: Extracted entities
        key_points: Summarized key points
        related_urls: Discovered related content
        tech_categories: Detected tech categories
        sentiment: Content sentiment (positive/neutral/negative)
        reading_time_min: Estimated reading time
        analysis_timestamp: When analysis was performed
    """
    url: str
    article: Article
    entities: EntityExtraction
    key_points: List[KeyPoint]
    related_urls: List[str]
    tech_categories: List[str]
    sentiment: str
    reading_time_min: int
    analysis_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.article.title,
            "summary": self.article.summary,
            "content_preview": self.article.content[:500] + "..." if len(self.article.content) > 500 else self.article.content,
            "tech_score": self.article.tech_score.score if self.article.tech_score else 0,
            "entities": {
                "companies": self.entities.companies,
                "people": self.entities.people,
                "technologies": self.entities.technologies,
            },
            "key_points": [{"text": kp.text, "importance": kp.importance} for kp in self.key_points],
            "related_urls": self.related_urls[:5],
            "tech_categories": self.tech_categories,
            "sentiment": self.sentiment,
            "reading_time_min": self.reading_time_min,
            "analyzed_at": self.analysis_timestamp.isoformat(),
        }


class EntityExtractor:
    """
    Extract named entities from text.
    
    Uses pattern matching and heuristics for entity extraction
    without requiring heavy NLP dependencies.
    """
    
    # Known tech companies for recognition
    KNOWN_COMPANIES: Set[str] = {
        "google", "microsoft", "apple", "amazon", "meta", "facebook",
        "nvidia", "intel", "amd", "openai", "anthropic", "tesla",
        "ibm", "oracle", "salesforce", "adobe", "netflix", "twitter",
        "x", "linkedin", "github", "gitlab", "atlassian", "zoom",
        "slack", "dropbox", "uber", "lyft", "airbnb", "stripe",
        "coinbase", "binance", "robinhood", "palantir", "snowflake",
        "databricks", "mongodb", "elastic", "cloudflare", "datadog",
        "twilio", "okta", "crowdstrike", "zscaler", "splunk",
    }
    
    # Known technologies/products
    KNOWN_TECHNOLOGIES: Set[str] = {
        "chatgpt", "gpt-4", "gpt-5", "claude", "gemini", "llama",
        "copilot", "midjourney", "dall-e", "stable diffusion",
        "kubernetes", "docker", "terraform", "ansible",
        "react", "vue", "angular", "next.js", "node.js",
        "python", "javascript", "typescript", "rust", "golang",
        "pytorch", "tensorflow", "keras", "scikit-learn",
        "aws", "azure", "gcp", "lambda", "s3", "ec2",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "kafka", "rabbitmq", "graphql", "rest api",
    }
    
    # Patterns for entity extraction
    COMPANY_PATTERNS = [
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Inc\.?|Corp\.?|LLC|Ltd\.?|Co\.?)\b',
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:announced|released|launched|unveiled)\b',
    ]
    
    PERSON_PATTERNS = [
        r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\s*,?\s*(?:CEO|CTO|CFO|COO|founder|co-founder|president|VP)\b',
        r'\b(?:CEO|CTO|CFO|founder)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b',
    ]
    
    def __init__(self):
        """Initialize entity extractor."""
        self._company_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.COMPANY_PATTERNS
        ]
        self._person_patterns = [
            re.compile(p) for p in self.PERSON_PATTERNS
        ]
    
    def extract(self, text: str) -> EntityExtraction:
        """
        Extract entities from text.
        
        Args:
            text: Text content to analyze
        
        Returns:
            EntityExtraction with found entities
        """
        text_lower = text.lower()
        
        # Extract companies
        companies = set()
        for company in self.KNOWN_COMPANIES:
            if company in text_lower:
                companies.add(company.title())
        
        for pattern in self._company_patterns:
            for match in pattern.finditer(text):
                companies.add(match.group(1))
        
        # Extract technologies
        technologies = set()
        for tech in self.KNOWN_TECHNOLOGIES:
            if tech.lower() in text_lower:
                technologies.add(tech)
        
        # Extract people
        people = set()
        for pattern in self._person_patterns:
            for match in pattern.finditer(text):
                people.add(match.group(1))
        
        return EntityExtraction(
            companies=list(companies)[:10],
            people=list(people)[:10],
            technologies=list(technologies)[:15],
        )


class KeyPointExtractor:
    """
    Extract key points from article content.
    
    Uses heuristics to identify important sentences
    that summarize the article's main ideas.
    """
    
    # Importance indicators
    IMPORTANCE_PHRASES = [
        "announced", "launched", "released", "unveiled",
        "breakthrough", "first", "new", "major", "significant",
        "billion", "million", "acquired", "raised", "funding",
        "partnership", "collaboration", "security", "vulnerability",
        "ai", "artificial intelligence", "machine learning",
    ]
    
    def extract(self, content: str, max_points: int = 5) -> List[KeyPoint]:
        """
        Extract key points from content.
        
        Args:
            content: Article content
            max_points: Maximum number of key points
        
        Returns:
            List of KeyPoint objects
        """
        # Split into sentences
        sentences = self._split_sentences(content)
        
        if not sentences:
            return []
        
        # Score each sentence
        scored = []
        for sentence in sentences:
            score = self._score_sentence(sentence)
            if score > 0.3 and 50 < len(sentence) < 300:
                scored.append((sentence, score))
        
        # Sort by score and select top
        scored.sort(key=lambda x: x[1], reverse=True)
        
        key_points = []
        for sentence, score in scored[:max_points]:
            category = "main" if score > 0.7 else "supporting" if score > 0.5 else "detail"
            key_points.append(KeyPoint(
                text=sentence.strip(),
                importance=score,
                category=category,
            ))
        
        return key_points
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _score_sentence(self, sentence: str) -> float:
        """Score a sentence for importance."""
        score = 0.0
        sentence_lower = sentence.lower()
        
        # Check for importance phrases
        for phrase in self.IMPORTANCE_PHRASES:
            if phrase in sentence_lower:
                score += 0.15
        
        # Bonus for quotes (often contain key information)
        if '"' in sentence or '"' in sentence:
            score += 0.2
        
        # Bonus for numbers (often contain key facts)
        if re.search(r'\$?\d+(?:\.\d+)?(?:\s*(?:billion|million|thousand|percent|%))?', sentence):
            score += 0.15
        
        # Position bonus (first sentences often important)
        # This would require knowing position, simplified here
        
        return min(1.0, score)


class SentimentAnalyzer:
    """
    Simple sentiment analysis for content.
    
    Uses keyword-based approach for lightweight sentiment detection.
    """
    
    POSITIVE_WORDS = {
        "success", "successful", "growth", "growing", "breakthrough",
        "innovation", "innovative", "leading", "leader", "best",
        "improved", "improvement", "profit", "profitable", "gain",
        "positive", "optimistic", "exciting", "amazing", "great",
    }
    
    NEGATIVE_WORDS = {
        "fail", "failure", "failed", "loss", "losses", "decline",
        "declining", "concern", "concerns", "worried", "problem",
        "problems", "issue", "issues", "risk", "risks", "threat",
        "vulnerability", "breach", "hack", "layoff", "layoffs",
        "bankruptcy", "crash", "crisis", "warning",
    }
    
    def analyze(self, text: str) -> str:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
        
        Returns:
            "positive", "negative", or "neutral"
        """
        text_lower = text.lower()
        words = set(text_lower.split())
        
        positive_count = len(words & self.POSITIVE_WORDS)
        negative_count = len(words & self.NEGATIVE_WORDS)
        
        if positive_count > negative_count * 1.5:
            return "positive"
        elif negative_count > positive_count * 1.5:
            return "negative"
        else:
            return "neutral"


class URLAnalyzer:
    """
    Comprehensive URL analysis engine.
    
    Provides deep knowledge extraction from any URL:
    - Full content extraction
    - Entity recognition
    - Key points summarization
    - Related content discovery
    - Sentiment analysis
    
    Example:
        analyzer = URLAnalyzer()
        result = await analyzer.analyze("https://example.com/article")
        
        print(f"Title: {result.article.title}")
        print(f"Key Points:")
        for point in result.key_points:
            print(f"  - {point.text}")
        print(f"Entities: {result.entities.companies}")
    """
    
    def __init__(self):
        """Initialize URL analyzer."""
        self._scraper = DeepScraper()
        self._entity_extractor = EntityExtractor()
        self._key_point_extractor = KeyPointExtractor()
        self._sentiment_analyzer = SentimentAnalyzer()
        self._keyword_matcher = TechKeywordMatcher()
    
    async def analyze(self, url: str) -> Optional[URLAnalysisResult]:
        """
        Perform comprehensive analysis of a URL.
        
        Args:
            url: URL to analyze
        
        Returns:
            URLAnalysisResult with full analysis, or None if failed
        """
        logger.info(f"Analyzing URL: {url}")
        
        # Fetch and process article
        article = await self._scraper.analyze_url_deep(url)
        
        if not article:
            logger.error(f"Failed to fetch article: {url}")
            return None
        
        # Extract entities
        entities = self._entity_extractor.extract(article.content)
        
        # Extract key points
        key_points = self._key_point_extractor.extract(article.content)
        
        # Analyze sentiment
        sentiment = self._sentiment_analyzer.analyze(article.content)
        
        # Calculate reading time (avg 200 words/min)
        word_count = len(article.content.split())
        reading_time = max(1, word_count // 200)
        
        # Get tech categories
        _, keywords = self._keyword_matcher.calculate_tech_score(article.content)
        categories = self._categorize_content(keywords)
        
        # Discover related URLs (from same page)
        related_urls = await self._discover_related(url)
        
        return URLAnalysisResult(
            url=url,
            article=article,
            entities=entities,
            key_points=key_points,
            related_urls=related_urls,
            tech_categories=categories,
            sentiment=sentiment,
            reading_time_min=reading_time,
        )
    
    def _categorize_content(self, keywords: List[str]) -> List[str]:
        """Categorize content based on keywords."""
        categories = set()
        
        keyword_to_category = {
            "ai": "AI/ML",
            "artificial intelligence": "AI/ML",
            "machine learning": "AI/ML",
            "deep learning": "AI/ML",
            "programming": "Software Development",
            "coding": "Software Development",
            "developer": "Software Development",
            "cybersecurity": "Security",
            "security": "Security",
            "hacking": "Security",
            "cloud": "Cloud Computing",
            "aws": "Cloud Computing",
            "azure": "Cloud Computing",
            "blockchain": "Blockchain/Web3",
            "cryptocurrency": "Blockchain/Web3",
            "startup": "Startups/Business",
            "funding": "Startups/Business",
        }
        
        for keyword in keywords:
            kw_lower = keyword.lower()
            if kw_lower in keyword_to_category:
                categories.add(keyword_to_category[kw_lower])
        
        return list(categories)[:5]
    
    async def _discover_related(self, url: str) -> List[str]:
        """Discover related content URLs."""
        # For now, return empty list
        # In full implementation, would analyze page for related links
        return []
    
    def format_analysis_report(self, result: URLAnalysisResult) -> str:
        """
        Format analysis result as readable report.
        
        Args:
            result: Analysis result to format
        
        Returns:
            Formatted string report
        """
        lines = [
            "=" * 60,
            f"📰 {result.article.title}",
            "=" * 60,
            f"🔗 {result.url}",
            f"📊 Tech Score: {result.article.tech_score.score:.2f}" if result.article.tech_score else "",
            f"⏱️ Reading Time: {result.reading_time_min} min",
            f"💭 Sentiment: {result.sentiment}",
            "",
            "📂 Categories: " + ", ".join(result.tech_categories) if result.tech_categories else "",
            "",
            "📌 Key Points:",
        ]
        
        for i, point in enumerate(result.key_points, 1):
            lines.append(f"  {i}. {point.text}")
        
        if result.entities.companies:
            lines.append("")
            lines.append("🏢 Companies: " + ", ".join(result.entities.companies[:5]))
        
        if result.entities.technologies:
            lines.append("🔧 Technologies: " + ", ".join(result.entities.technologies[:5]))
        
        if result.entities.people:
            lines.append("👤 People: " + ", ".join(result.entities.people[:5]))
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
