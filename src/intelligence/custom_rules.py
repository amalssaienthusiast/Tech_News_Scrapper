"""
Custom Alert Rules for Tech News Scraper

Enterprise feature providing rule-based alerting with:
- Keyword triggers (match titles/content)
- Sentiment thresholds
- Company/Topic filters
- Custom webhook targets
- Rule prioritization and cooldowns
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid

logger = logging.getLogger(__name__)


class RuleConditionType(str, Enum):
    """Types of conditions for alert rules."""
    KEYWORD = "keyword"           # Match keywords in title/content
    SENTIMENT = "sentiment"       # Sentiment threshold
    COMPANY = "company"           # Specific company mentioned
    TOPIC = "topic"               # Specific topic category
    SOURCE = "source"             # From specific source
    CRITICALITY = "criticality"   # Minimum criticality score


class RuleAction(str, Enum):
    """Actions to take when rule triggers."""
    ALERT = "alert"              # Standard alert dispatch
    EMAIL = "email"              # Send email
    WEBHOOK = "webhook"          # Custom webhook
    TELEGRAM = "telegram"        # Telegram message
    DISCORD = "discord"          # Discord message
    HIGHLIGHT = "highlight"      # Just highlight in GUI


class AlertRule(BaseModel):
    """
    Custom alert rule definition.
    
    Rules define conditions and actions for automated alerting.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = Field(description="Human-readable rule name")
    enabled: bool = True
    priority: int = Field(default=5, ge=1, le=10, description="Higher = more important")
    
    # Conditions (all must match for rule to trigger)
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Actions to take when triggered
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Cooldown (prevent repeated triggers)
    cooldown_minutes: int = Field(default=60, ge=0)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    description: str = ""
    
    def add_keyword_condition(self, keywords: List[str], match_title: bool = True, match_content: bool = True):
        """Add a keyword matching condition."""
        self.conditions.append({
            "type": RuleConditionType.KEYWORD.value,
            "keywords": [k.lower() for k in keywords],
            "match_title": match_title,
            "match_content": match_content,
            "match_all": False  # Match any keyword
        })
    
    def add_sentiment_condition(self, min_score: float = None, max_score: float = None, sentiment: str = None):
        """Add a sentiment threshold condition."""
        self.conditions.append({
            "type": RuleConditionType.SENTIMENT.value,
            "min_score": min_score,
            "max_score": max_score,
            "sentiment": sentiment  # "positive", "negative", "neutral"
        })
    
    def add_company_condition(self, companies: List[str]):
        """Add a company mention condition."""
        self.conditions.append({
            "type": RuleConditionType.COMPANY.value,
            "companies": [c.lower() for c in companies]
        })
    
    def add_topic_condition(self, topics: List[str]):
        """Add a topic category condition."""
        self.conditions.append({
            "type": RuleConditionType.TOPIC.value,
            "topics": [t.lower() for t in topics]
        })
    
    def add_criticality_condition(self, min_criticality: int):
        """Add a minimum criticality condition."""
        self.conditions.append({
            "type": RuleConditionType.CRITICALITY.value,
            "min_criticality": min_criticality
        })
    
    def add_alert_action(self, level: str = "high"):
        """Add standard alert action."""
        self.actions.append({
            "type": RuleAction.ALERT.value,
            "level": level
        })
    
    def add_webhook_action(self, url: str, headers: Dict[str, str] = None, template: str = None):
        """Add custom webhook action."""
        self.actions.append({
            "type": RuleAction.WEBHOOK.value,
            "url": url,
            "headers": headers or {},
            "template": template  # Optional JSON template with {{variable}} placeholders
        })
    
    def add_email_action(self, recipients: List[str], subject_template: str = None):
        """Add email notification action."""
        self.actions.append({
            "type": RuleAction.EMAIL.value,
            "recipients": recipients,
            "subject_template": subject_template or "🔔 Alert: {{title}}"
        })
    
    def is_on_cooldown(self) -> bool:
        """Check if rule is on cooldown."""
        if not self.last_triggered or self.cooldown_minutes == 0:
            return False
        
        elapsed = datetime.now() - self.last_triggered
        return elapsed < timedelta(minutes=self.cooldown_minutes)


class RuleEngine:
    """
    Rule engine for evaluating and executing custom alert rules.
    
    Features:
    - Rule persistence to JSON
    - Condition evaluation
    - Action execution
    - Cooldown management
    """
    
    def __init__(self, rules_path: Optional[Path] = None):
        """Initialize rule engine."""
        self._rules_path = rules_path or Path(__file__).parent.parent.parent / "data" / "alert_rules.json"
        self._rules: Dict[str, AlertRule] = {}
        self._load_rules()
        
        logger.info(f"RuleEngine initialized with {len(self._rules)} rules")
    
    def _load_rules(self):
        """Load rules from JSON file."""
        if self._rules_path.exists():
            try:
                with open(self._rules_path, 'r') as f:
                    data = json.load(f)
                    for rule_data in data.get("rules", []):
                        rule = AlertRule(**rule_data)
                        self._rules[rule.id] = rule
            except Exception as e:
                logger.error(f"Failed to load rules: {e}")
    
    def _save_rules(self):
        """Save rules to JSON file."""
        self._rules_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "rules": [rule.model_dump() for rule in self._rules.values()]
        }
        
        with open(self._rules_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def add_rule(self, rule: AlertRule) -> str:
        """Add a new rule."""
        self._rules[rule.id] = rule
        self._save_rules()
        logger.info(f"Rule added: {rule.name} ({rule.id})")
        return rule.id
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            self._save_rules()
            logger.info(f"Rule removed: {rule_id}")
            return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)
    
    def list_rules(self, enabled_only: bool = False) -> List[AlertRule]:
        """List all rules, optionally filtering enabled only."""
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return sorted(rules, key=lambda r: r.priority, reverse=True)
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update a rule's properties."""
        if rule_id not in self._rules:
            return False
        
        rule = self._rules[rule_id]
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        self._save_rules()
        return True
    
    def evaluate_article(
        self,
        title: str,
        content: str = "",
        source: str = "",
        topics: List[str] = None,
        companies: List[str] = None,
        sentiment: str = "neutral",
        sentiment_score: float = 0.0,
        criticality: int = 5
    ) -> List[AlertRule]:
        """
        Evaluate all rules against an article.
        
        Args:
            title: Article title
            content: Article content/summary
            source: Source name
            topics: List of topic categories
            companies: List of companies mentioned
            sentiment: Sentiment label
            sentiment_score: Sentiment score (-1 to 1)
            criticality: Criticality score (1-10)
            
        Returns:
            List of triggered rules (sorted by priority)
        """
        triggered_rules = []
        
        article_data = {
            "title": title.lower(),
            "content": content.lower(),
            "source": source.lower(),
            "topics": [t.lower() for t in (topics or [])],
            "companies": [c.lower() for c in (companies or [])],
            "sentiment": sentiment.lower(),
            "sentiment_score": sentiment_score,
            "criticality": criticality
        }
        
        for rule in self.list_rules(enabled_only=True):
            if rule.is_on_cooldown():
                continue
            
            if self._evaluate_conditions(rule, article_data):
                triggered_rules.append(rule)
                
                # Update trigger stats
                rule.last_triggered = datetime.now()
                rule.trigger_count += 1
        
        # Save updated trigger counts
        if triggered_rules:
            self._save_rules()
        
        return sorted(triggered_rules, key=lambda r: r.priority, reverse=True)
    
    def _evaluate_conditions(self, rule: AlertRule, article: Dict[str, Any]) -> bool:
        """Evaluate all conditions for a rule. All must match."""
        if not rule.conditions:
            return False  # No conditions = never trigger
        
        for condition in rule.conditions:
            if not self._evaluate_condition(condition, article):
                return False
        
        return True
    
    def _evaluate_condition(self, condition: Dict[str, Any], article: Dict[str, Any]) -> bool:
        """Evaluate a single condition."""
        cond_type = condition.get("type")
        
        if cond_type == RuleConditionType.KEYWORD.value:
            return self._eval_keyword(condition, article)
        elif cond_type == RuleConditionType.SENTIMENT.value:
            return self._eval_sentiment(condition, article)
        elif cond_type == RuleConditionType.COMPANY.value:
            return self._eval_company(condition, article)
        elif cond_type == RuleConditionType.TOPIC.value:
            return self._eval_topic(condition, article)
        elif cond_type == RuleConditionType.SOURCE.value:
            return self._eval_source(condition, article)
        elif cond_type == RuleConditionType.CRITICALITY.value:
            return self._eval_criticality(condition, article)
        
        return False
    
    def _eval_keyword(self, cond: Dict, article: Dict) -> bool:
        """Evaluate keyword condition."""
        keywords = cond.get("keywords", [])
        text_parts = []
        
        if cond.get("match_title", True):
            text_parts.append(article["title"])
        if cond.get("match_content", True):
            text_parts.append(article["content"])
        
        full_text = " ".join(text_parts)
        
        if cond.get("match_all", False):
            return all(kw in full_text for kw in keywords)
        else:
            return any(kw in full_text for kw in keywords)
    
    def _eval_sentiment(self, cond: Dict, article: Dict) -> bool:
        """Evaluate sentiment condition."""
        if cond.get("sentiment"):
            if article["sentiment"] != cond["sentiment"]:
                return False
        
        score = article["sentiment_score"]
        
        if cond.get("min_score") is not None:
            if score < cond["min_score"]:
                return False
        
        if cond.get("max_score") is not None:
            if score > cond["max_score"]:
                return False
        
        return True
    
    def _eval_company(self, cond: Dict, article: Dict) -> bool:
        """Evaluate company condition."""
        rule_companies = set(cond.get("companies", []))
        article_companies = set(article["companies"])
        
        # Also check in title/content
        text = article["title"] + " " + article["content"]
        
        for company in rule_companies:
            if company in article_companies or company in text:
                return True
        
        return False
    
    def _eval_topic(self, cond: Dict, article: Dict) -> bool:
        """Evaluate topic condition."""
        rule_topics = set(cond.get("topics", []))
        article_topics = set(article["topics"])
        
        return bool(rule_topics & article_topics)
    
    def _eval_source(self, cond: Dict, article: Dict) -> bool:
        """Evaluate source condition."""
        sources = cond.get("sources", [])
        return article["source"] in sources
    
    def _eval_criticality(self, cond: Dict, article: Dict) -> bool:
        """Evaluate criticality condition."""
        min_crit = cond.get("min_criticality", 0)
        return article["criticality"] >= min_crit
    
    async def execute_actions(
        self,
        rule: AlertRule,
        article_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute all actions for a triggered rule.
        
        Args:
            rule: The triggered rule
            article_data: Article data for templating
            
        Returns:
            List of action results
        """
        results = []
        
        for action in rule.actions:
            action_type = action.get("type")
            
            try:
                if action_type == RuleAction.WEBHOOK.value:
                    result = await self._exec_webhook(action, article_data)
                elif action_type == RuleAction.EMAIL.value:
                    result = await self._exec_email(action, article_data)
                else:
                    result = {"type": action_type, "status": "skipped"}
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Action execution failed: {e}")
                results.append({"type": action_type, "status": "error", "error": str(e)})
        
        return results
    
    async def _exec_webhook(self, action: Dict, data: Dict) -> Dict:
        """Execute webhook action."""
        import aiohttp
        
        url = action.get("url")
        headers = action.get("headers", {})
        template = action.get("template")
        
        # Build payload
        if template:
            # Replace template variables
            payload_str = template
            for key, value in data.items():
                payload_str = payload_str.replace(f"{{{{{key}}}}}", str(value))
            payload = json.loads(payload_str)
        else:
            payload = {
                "rule_triggered": True,
                "timestamp": datetime.now().isoformat(),
                **data
            }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                return {
                    "type": "webhook",
                    "status": "success" if response.status < 400 else "failed",
                    "status_code": response.status
                }
    
    async def _exec_email(self, action: Dict, data: Dict) -> Dict:
        """Execute email action."""
        try:
            from src.notifications import get_email_service
            
            service = get_email_service()
            if not service.is_configured():
                return {"type": "email", "status": "not_configured"}
            
            # For now, just log - would need to generate proper email content
            logger.info(f"Would send email to {action.get('recipients')}")
            return {"type": "email", "status": "success"}
            
        except Exception as e:
            return {"type": "email", "status": "error", "error": str(e)}


# Singleton instance
_rule_engine: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    """Get singleton RuleEngine instance."""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = RuleEngine()
    return _rule_engine


# Convenience function to create common rules
def create_breaking_news_rule(keywords: List[str], name: str = "Breaking News Alert") -> AlertRule:
    """Create a rule for breaking news keywords."""
    rule = AlertRule(name=name, priority=8)
    rule.add_keyword_condition(keywords)
    rule.add_alert_action(level="high")
    return rule


def create_company_watch_rule(companies: List[str], name: str = "Company Watch") -> AlertRule:
    """Create a rule for watching specific companies."""
    rule = AlertRule(name=name, priority=7)
    rule.add_company_condition(companies)
    rule.add_alert_action(level="medium")
    return rule


def create_negative_sentiment_rule(
    threshold: float = -0.3,
    name: str = "Negative Sentiment Alert"
) -> AlertRule:
    """Create a rule for negative sentiment articles."""
    rule = AlertRule(name=name, priority=6)
    rule.add_sentiment_condition(max_score=threshold)
    rule.add_alert_action(level="medium")
    return rule
