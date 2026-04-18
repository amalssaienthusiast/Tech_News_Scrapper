"""
Newsletter LangGraph Workflow

Orchestrates the complete newsletter generation pipeline using LangGraph.
"""

import asyncio
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from .state import NewsletterState, StorySelection, create_initial_state
from .editor import get_editor
from .writer import get_writer

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# NODE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

async def load_stories_node(state: NewsletterState) -> Dict[str, Any]:
    """Load analyzed stories from database."""
    logger.info(f"Loading stories for date: {state['target_date']}")
    
    try:
        from src.database import Database
        db = Database()
        
        # Get articles with intelligence data
        articles = db.get_all_articles()
        
        # Filter to today's articles or recent ones
        # Join with intelligence data
        enriched = []
        for article in articles[:100]:  # Limit for performance
            intel = db.get_intelligence(article.get('id', ''))
            if intel:
                article.update(intel)
            enriched.append(article)
        
        # Sort by criticality
        enriched.sort(key=lambda x: x.get('criticality', 0), reverse=True)
        
        logger.info(f"Loaded {len(enriched)} analyzed stories")
        
        return {
            "available_stories": enriched,
            "analyzed_count": len(enriched),
            "current_step": "stories_loaded"
        }
        
    except Exception as e:
        logger.error(f"Failed to load stories: {e}")
        return {
            "available_stories": [],
            "analyzed_count": 0,
            "error": str(e),
            "current_step": "load_failed"
        }


async def ai_editor_node(state: NewsletterState) -> Dict[str, Any]:
    """AI Editor selects top stories."""
    logger.info("AI Editor selecting top stories...")
    
    if not state["available_stories"]:
        return {
            "error": "No stories available for selection",
            "current_step": "editor_failed"
        }
    
    editor = get_editor()
    selection = await editor.select_stories(
        available_stories=state["available_stories"],
        max_top=4,
        max_shortlist=10,
        previous_newsletter=state.get("previous_newsletter")
    )
    
    # Convert selected IDs to StorySelection objects
    top_stories = []
    shortlist_stories = []
    
    for article in state["available_stories"]:
        article_id = article.get('id', '')
        
        if article_id in selection.selected_ids:
            top_stories.append(StorySelection(
                article_id=article_id,
                title=article.get('title', ''),
                url=article.get('url', ''),
                source=article.get('source', ''),
                criticality=article.get('criticality', 0),
                is_disruptive=article.get('disruptive', False),
                summary=article.get('ai_summary', ''),
                full_content=article.get('full_content', '')
            ))
        elif article_id in selection.shortlist_ids:
            shortlist_stories.append(article)
    
    # Sort top stories by their position in selection
    id_to_position = {id: i for i, id in enumerate(selection.selected_ids)}
    top_stories.sort(key=lambda x: id_to_position.get(x.article_id, 999))
    
    logger.info(f"Selected {len(top_stories)} top stories, {len(shortlist_stories)} for shortlist")
    
    return {
        "top_stories": top_stories,
        "shortlist_stories": shortlist_stories,
        "editor_reasoning": selection.reasoning,
        "current_step": "editor_complete"
    }


def human_review_node(state: NewsletterState) -> Dict[str, Any]:
    """
    Human-in-the-loop review checkpoint.
    
    In LangGraph Cloud, this would use interrupt().
    For local GUI, we set a flag for the workflow manager to handle.
    """
    logger.info("Awaiting human review of story selection...")
    
    # In GUI mode, this is handled externally
    # The workflow will pause here until human_approved is set
    
    return {
        "current_step": "awaiting_review",
        "review_attempts": state.get("review_attempts", 0) + 1
    }


async def write_sections_node(state: NewsletterState) -> Dict[str, Any]:
    """Write newsletter sections for each top story."""
    logger.info("Writing newsletter sections...")
    
    writer = get_writer()
    sections = []
    
    for story in state["top_stories"]:
        section = await writer.write_section(story)
        sections.append(section)
        story.section_text = section
    
    logger.info(f"Wrote {len(sections)} sections")
    
    return {
        "sections": sections,
        "top_stories": state["top_stories"],  # Updated with section_text
        "current_step": "sections_complete"
    }


async def write_supplementary_node(state: NewsletterState) -> Dict[str, Any]:
    """Write intro and shortlist sections."""
    logger.info("Writing supplementary content...")
    
    writer = get_writer()
    
    # Generate intro
    intro = await writer.write_intro(
        stories=state["top_stories"],
        newsletter_name=state["newsletter_name"]
    )
    
    # Generate shortlist
    shortlist = await writer.write_shortlist(state["shortlist_stories"])
    
    # Generate subject line
    subject, alternatives = await writer.generate_subject_line(state["top_stories"])
    
    return {
        "intro_text": intro,
        "shortlist_text": shortlist,
        "subject_line": subject,
        "subject_alternatives": alternatives,
        "current_step": "supplementary_complete"
    }


async def assemble_node(state: NewsletterState) -> Dict[str, Any]:
    """Assemble final newsletter."""
    logger.info("Assembling final newsletter...")
    
    writer = get_writer()
    
    final_markdown = writer.assemble_newsletter(
        newsletter_name=state["newsletter_name"],
        date=state["target_date"],
        subject=state["subject_line"],
        intro=state["intro_text"],
        sections=state["sections"],
        shortlist=state["shortlist_text"]
    )
    
    return {
        "final_markdown": final_markdown,
        "generated_at": datetime.now(UTC).isoformat(),
        "current_step": "assembled"
    }


async def export_node(state: NewsletterState) -> Dict[str, Any]:
    """Export newsletter to file."""
    logger.info("Exporting newsletter...")
    
    output_dir = Path("output/newsletters")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{state['target_date']}.md"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(state["final_markdown"])
    
    logger.info(f"Newsletter exported to: {filepath}")
    
    return {
        "export_path": str(filepath),
        "current_step": "exported"
    }


# ═══════════════════════════════════════════════════════════════════════════
# ROUTING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def route_after_load(state: NewsletterState) -> str:
    """Route after loading stories."""
    if state.get("error") or not state.get("available_stories"):
        return END
    return "ai_editor"


def route_after_review(state: NewsletterState) -> str:
    """Route after human review."""
    if state.get("human_approved"):
        return "write_sections"
    elif state.get("human_feedback"):
        # User provided feedback, go back to editor
        return "ai_editor"
    elif state.get("review_attempts", 0) >= 3:
        # Too many attempts, proceed anyway
        return "write_sections"
    else:
        # Still waiting
        return "human_review"


# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW BUILDER
# ═══════════════════════════════════════════════════════════════════════════

class NewsletterWorkflow:
    """
    Newsletter generation workflow manager.
    
    Provides both sync and async interfaces for newsletter generation.
    """
    
    def __init__(self, skip_human_review: bool = False):
        """
        Initialize workflow.
        
        Args:
            skip_human_review: Skip human approval (auto-approve)
        """
        self.skip_human_review = skip_human_review
        self._graph = self._build_graph()
        self._state: Optional[NewsletterState] = None
        self._approval_callback: Optional[Callable] = None
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        graph = StateGraph(NewsletterState)
        
        # Add nodes
        graph.add_node("load_stories", load_stories_node)
        graph.add_node("ai_editor", ai_editor_node)
        graph.add_node("human_review", human_review_node)
        graph.add_node("write_sections", write_sections_node)
        graph.add_node("write_supplementary", write_supplementary_node)
        graph.add_node("assemble", assemble_node)
        graph.add_node("export", export_node)
        
        # Add edges
        graph.add_edge(START, "load_stories")
        graph.add_conditional_edges("load_stories", route_after_load)
        graph.add_edge("ai_editor", "human_review")
        
        if self.skip_human_review:
            graph.add_edge("human_review", "write_sections")
        else:
            graph.add_conditional_edges("human_review", route_after_review)
        
        graph.add_edge("write_sections", "write_supplementary")
        graph.add_edge("write_supplementary", "assemble")
        graph.add_edge("assemble", "export")
        graph.add_edge("export", END)
        
        return graph
    
    def compile(self):
        """Compile the workflow graph."""
        return self._graph.compile(checkpointer=MemorySaver())
    
    async def generate(
        self,
        target_date: Optional[str] = None,
        newsletter_name: str = "Tech Intelligence Daily",
        on_review_needed: Optional[Callable] = None
    ) -> NewsletterState:
        """
        Generate newsletter.
        
        Args:
            target_date: Date for newsletter (default: today)
            newsletter_name: Name of newsletter
            on_review_needed: Callback when human review is needed
            
        Returns:
            Final state with generated newsletter
        """
        self._approval_callback = on_review_needed
        
        initial = create_initial_state(target_date, newsletter_name)
        
        compiled = self.compile()
        
        # Run with config
        config = {"configurable": {"thread_id": target_date or "latest"}}
        
        final_state = None
        async for state in compiled.astream(initial, config):
            self._state = state
            
            # Check if we need human review
            for node_name, node_state in state.items():
                if isinstance(node_state, dict):
                    if node_state.get("current_step") == "awaiting_review":
                        if on_review_needed:
                            # Callback to GUI for approval
                            approved = await self._wait_for_approval(node_state)
                            if approved:
                                node_state["human_approved"] = True
                    final_state = node_state
        
        return final_state
    
    async def _wait_for_approval(self, state: Dict) -> bool:
        """Wait for human approval (to be overridden by GUI)."""
        if self.skip_human_review:
            return True
        
        if self._approval_callback:
            return await self._approval_callback(state)
        
        # Default: auto-approve after delay
        logger.info("Auto-approving after 2 seconds (no callback set)")
        await asyncio.sleep(2)
        return True
    
    def approve_selection(self, approved: bool, feedback: Optional[str] = None):
        """Approve or reject story selection (called from GUI)."""
        if self._state:
            self._state["human_approved"] = approved
            self._state["human_feedback"] = feedback


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

async def generate_newsletter(
    target_date: Optional[str] = None,
    newsletter_name: str = "Tech Intelligence Daily",
    skip_review: bool = False
) -> NewsletterState:
    """
    Generate a newsletter for the specified date.
    
    Args:
        target_date: Date for newsletter
        newsletter_name: Newsletter name
        skip_review: Skip human review step
        
    Returns:
        Final newsletter state with markdown
    """
    workflow = NewsletterWorkflow(skip_human_review=skip_review)
    return await workflow.generate(target_date, newsletter_name)
