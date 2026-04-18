"""
GUI Enhancement Widgets - Storage mode selector, personalization controls, and article save/export.

Integrates the new storage architecture and personalization engine into the GUI.

Usage:
    from gui.enhancement_widgets import StorageModePanel, PersonalizationPanel, ArticleSaveButton
    
    storage_panel = StorageModePanel(parent, async_runner)
    personalization = PersonalizationPanel(parent, on_update_callback)
"""

import asyncio
import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Import theme
try:
    from gui import THEME, get_font
except ImportError:
    # Fallback theme for testing
    class FallbackTheme:
        bg = "#1a1b26"
        bg_dark = "#16161e"
        bg_highlight = "#292e42"
        bg_visual = "#33467c"
        fg = "#c0caf5"
        fg_dark = "#565f89"
        comment = "#565f89"
        cyan = "#7dcfff"
        green = "#9ece6a"
        orange = "#ff9e64"
        red = "#f7768e"
        purple = "#bb9af7"
        magenta = "#ff007c"
        black = "#15161e"
    THEME = FallbackTheme()
    def get_font(size="md", weight="normal", family=None):
        sizes = {"xs": 10, "sm": 11, "md": 12, "lg": 14, "xl": 18, "2xl": 24}
        return ("Segoe UI", sizes.get(size, 12), weight)

logger = logging.getLogger(__name__)


class StorageModePanel(tk.Frame):
    """
    Storage mode selector panel.
    
    Allows users to switch between EPHEMERAL, HYBRID, and PERSISTENT modes.
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        async_runner: Optional[Any] = None,
        on_mode_change: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent, bg=THEME.bg_highlight, padx=10, pady=8)
        
        self.async_runner = async_runner
        self.on_mode_change = on_mode_change
        
        self._current_mode = "hybrid"
        self._storage_manager = None
        
        self._build_ui()
        self._load_current_mode()
    
    def _build_ui(self) -> None:
        # Header
        header = tk.Frame(self, bg=THEME.bg_highlight)
        header.pack(fill=tk.X)
        
        tk.Label(
            header, text="💾", font=get_font("lg"),
            fg=THEME.cyan, bg=THEME.bg_highlight
        ).pack(side=tk.LEFT)
        
        tk.Label(
            header, text="Storage Mode", font=get_font("sm", "bold"),
            fg=THEME.fg, bg=THEME.bg_highlight
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # Mode buttons
        modes_frame = tk.Frame(self, bg=THEME.bg_highlight, pady=8)
        modes_frame.pack(fill=tk.X)
        
        self.mode_var = tk.StringVar(value="hybrid")
        
        modes = [
            ("ephemeral", "⚡ Live", THEME.orange, "Articles expire, no history"),
            ("hybrid", "🔄 Hybrid", THEME.cyan, "Live + AI cache (recommended)"),
            ("persistent", "💿 Persistent", THEME.purple, "Full database storage"),
        ]
        
        for mode_id, label, color, tooltip in modes:
            btn = tk.Radiobutton(
                modes_frame,
                text=label,
                variable=self.mode_var,
                value=mode_id,
                font=get_font("xs"),
                fg=color,
                bg=THEME.bg_highlight,
                selectcolor=THEME.bg_dark,
                activebackground=THEME.bg_highlight,
                activeforeground=color,
                command=self._on_mode_select,
                cursor="hand2",
            )
            btn.pack(side=tk.LEFT, padx=(0, 12))
        
        # Status label
        self.status_label = tk.Label(
            self, text="Mode: Loading...",
            font=get_font("xs"), fg=THEME.comment, bg=THEME.bg_highlight
        )
        self.status_label.pack(anchor=tk.W)
    
    def _load_current_mode(self) -> None:
        """Load current storage mode."""
        try:
            from src.db_storage.ephemeral_store import StorageMode
            from src.db_storage.unified_storage import _load_mode_from_config
            
            mode = _load_mode_from_config()
            if mode:
                self._current_mode = mode.value
                self.mode_var.set(mode.value)
            
            self._update_status(self._current_mode)
        except Exception as e:
            logger.warning(f"Could not load storage mode: {e}")
            self._update_status("hybrid")
    
    def _update_status(self, mode: str) -> None:
        """Update status label."""
        descriptions = {
            "ephemeral": "⚡ Articles auto-expire (2hr TTL)",
            "hybrid": "🔄 Live feed + cached AI summaries",
            "persistent": "💿 Full database storage",
        }
        self.status_label.config(text=descriptions.get(mode, f"Mode: {mode}"))
    
    def _on_mode_select(self) -> None:
        """Handle mode selection."""
        new_mode = self.mode_var.get()
        if new_mode == self._current_mode:
            return
        
        # Confirm mode change
        msg = f"Switch to {new_mode.upper()} mode?\n\n"
        if new_mode == "ephemeral":
            msg += "Articles will expire after 2 hours.\nNo persistent storage."
        elif new_mode == "persistent":
            msg += "All articles will be saved to database.\nRequires more storage."
        else:
            msg += "Articles in memory, AI summaries cached.\nBest of both worlds."
        
        if not messagebox.askyesno("Change Storage Mode", msg):
            self.mode_var.set(self._current_mode)
            return
        
        # Change mode
        self._change_mode(new_mode)
    
    def _change_mode(self, new_mode: str) -> None:
        """Change storage mode."""
        async def do_change():
            try:
                from src.db_storage import set_storage_mode, StorageMode
                
                mode_enum = StorageMode(new_mode)
                await set_storage_mode(mode_enum)
                
                self._current_mode = new_mode
                self._update_status(new_mode)
                
                if self.on_mode_change:
                    self.on_mode_change(new_mode)
                
                logger.info(f"Storage mode changed to {new_mode}")
                
            except Exception as e:
                logger.error(f"Failed to change mode: {e}")
                self.mode_var.set(self._current_mode)
        
        if self.async_runner:
            self.async_runner.run_async(do_change())
        else:
            asyncio.create_task(do_change())


class ArticleSaveExportPanel(tk.Frame):
    """
    Panel for saving and exporting articles.
    
    Shows saved article count and provides export functionality.
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        async_runner: Optional[Any] = None,
    ) -> None:
        super().__init__(parent, bg=THEME.bg_highlight, padx=10, pady=8)
        
        self.async_runner = async_runner
        self._saved_count = 0
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        # Header
        header = tk.Frame(self, bg=THEME.bg_highlight)
        header.pack(fill=tk.X)
        
        tk.Label(
            header, text="📥", font=get_font("lg"),
            fg=THEME.green, bg=THEME.bg_highlight
        ).pack(side=tk.LEFT)
        
        tk.Label(
            header, text="Saved Articles", font=get_font("sm", "bold"),
            fg=THEME.fg, bg=THEME.bg_highlight
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # Count
        self.count_label = tk.Label(
            self, text="0 articles saved",
            font=get_font("xs"), fg=THEME.comment, bg=THEME.bg_highlight
        )
        self.count_label.pack(anchor=tk.W, pady=(5, 8))
        
        # Buttons
        btn_frame = tk.Frame(self, bg=THEME.bg_highlight)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(
            btn_frame, text="📋 Export JSON",
            font=get_font("xs"), bg=THEME.bg_visual, fg=THEME.fg,
            padx=10, pady=4, relief=tk.FLAT, cursor="hand2",
            command=self._export_json
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        tk.Button(
            btn_frame, text="📄 Export MD",
            font=get_font("xs"), bg=THEME.bg_visual, fg=THEME.fg,
            padx=10, pady=4, relief=tk.FLAT, cursor="hand2",
            command=self._export_markdown
        ).pack(side=tk.LEFT)
    
    def update_count(self, count: int) -> None:
        """Update saved article count."""
        self._saved_count = count
        self.count_label.config(text=f"{count} article{'s' if count != 1 else ''} saved")
    
    def _export_json(self) -> None:
        """Export saved articles as JSON."""
        async def do_export():
            try:
                from src.db_storage import get_storage_manager
                storage = await get_storage_manager()
                saved = storage.export_articles()
                
                if not saved:
                    messagebox.showinfo("Export", "No saved articles to export.")
                    return
                
                # Ask for save location
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                    initialfile=f"tech_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                
                if filepath:
                    with open(filepath, "w") as f:
                        json.dump(saved, f, indent=2, default=str)
                    messagebox.showinfo("Export", f"Exported {len(saved)} articles to:\n{filepath}")
                    
            except Exception as e:
                logger.error(f"Export failed: {e}")
                messagebox.showerror("Export Error", str(e))
        
        if self.async_runner:
            self.async_runner.run_async(do_export())
        else:
            asyncio.create_task(do_export())
    
    def _export_markdown(self) -> None:
        """Export saved articles as Markdown newsletter."""
        async def do_export():
            try:
                from src.db_storage import get_storage_manager
                storage = await get_storage_manager()
                saved = storage.export_articles()
                
                if not saved:
                    messagebox.showinfo("Export", "No saved articles to export.")
                    return
                
                # Build markdown
                md_lines = [
                    f"# Tech News Digest",
                    f"*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
                    "",
                    f"**{len(saved)} Articles**",
                    "",
                    "---",
                    "",
                ]
                
                for i, article in enumerate(saved, 1):
                    md_lines.append(f"## {i}. {article.get('title', 'Untitled')}")
                    md_lines.append(f"**Source:** {article.get('source', 'Unknown')}")
                    md_lines.append(f"**URL:** {article.get('url', '')}")
                    
                    if article.get("ai_summary"):
                        md_lines.append("")
                        md_lines.append(f"> {article['ai_summary']}")
                    
                    md_lines.append("")
                    md_lines.append("---")
                    md_lines.append("")
                
                # Ask for save location
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".md",
                    filetypes=[("Markdown files", "*.md"), ("All files", "*.*")],
                    initialfile=f"tech_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                )
                
                if filepath:
                    with open(filepath, "w") as f:
                        f.write("\n".join(md_lines))
                    messagebox.showinfo("Export", f"Exported {len(saved)} articles to:\n{filepath}")
                    
            except Exception as e:
                logger.error(f"Export failed: {e}")
                messagebox.showerror("Export Error", str(e))
        
        if self.async_runner:
            self.async_runner.run_async(do_export())
        else:
            asyncio.create_task(do_export())


class PersonalizationScoreWidget(tk.Frame):
    """
    Shows personalization score for a single article.
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        score: float = 0.0,
        topics: Optional[List[str]] = None,
        companies: Optional[List[str]] = None,
    ) -> None:
        super().__init__(parent, bg=THEME.bg_highlight)
        
        self.score = score
        self.topics = topics or []
        self.companies = companies or []
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        # Score bar
        if self.score > 0:
            color = THEME.green if self.score >= 0.5 else THEME.cyan if self.score >= 0.25 else THEME.fg_dark
            
            bar_bg = tk.Frame(self, bg=THEME.bg_dark, height=4, width=60)
            bar_bg.pack(side=tk.LEFT, padx=(0, 5))
            bar_bg.pack_propagate(False)
            
            fill_width = int(60 * min(self.score, 1.0))
            bar_fill = tk.Frame(bar_bg, bg=color, height=4, width=fill_width)
            bar_fill.pack(side=tk.LEFT)
            
            # Score text
            tk.Label(
                self, text=f"{self.score:.0%}",
                font=get_font("xs"), fg=color, bg=THEME.bg_highlight
            ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Tags
        for topic in self.topics[:2]:
            tk.Label(
                self, text=f"#{topic}",
                font=get_font("xs"), fg=THEME.cyan, bg=THEME.bg_dark,
                padx=4, pady=1
            ).pack(side=tk.LEFT, padx=1)
        
        for company in self.companies[:2]:
            tk.Label(
                self, text=f"${company}",
                font=get_font("xs"), fg=THEME.green, bg=THEME.bg_dark,
                padx=4, pady=1
            ).pack(side=tk.LEFT, padx=1)


class SaveArticleButton(tk.Button):
    """
    Button to save/unsave an article.
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        article_id: str,
        is_saved: bool = False,
        on_save: Optional[Callable[[str, bool], None]] = None,
        **kwargs
    ) -> None:
        self.article_id = article_id
        self.is_saved = is_saved
        self.on_save = on_save
        
        super().__init__(
            parent,
            text="💾" if not is_saved else "✅",
            font=get_font("sm"),
            bg=THEME.bg_visual if not is_saved else THEME.green,
            fg=THEME.fg if not is_saved else THEME.black,
            padx=8, pady=2,
            relief=tk.FLAT,
            cursor="hand2",
            command=self._toggle_save,
            **kwargs
        )
    
    def _toggle_save(self) -> None:
        """Toggle save state."""
        self.is_saved = not self.is_saved
        
        if self.is_saved:
            self.config(text="✅", bg=THEME.green, fg=THEME.black)
        else:
            self.config(text="💾", bg=THEME.bg_visual, fg=THEME.fg)
        
        if self.on_save:
            self.on_save(self.article_id, self.is_saved)


class CacheStatsWidget(tk.Frame):
    """
    Shows Redis cache statistics.
    """
    
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg=THEME.bg_highlight, padx=10, pady=8)
        self._build_ui()
    
    def _build_ui(self) -> None:
        tk.Label(
            self, text="📊 Cache Stats", font=get_font("sm", "bold"),
            fg=THEME.purple, bg=THEME.bg_highlight
        ).pack(anchor=tk.W)
        
        self.stats_label = tk.Label(
            self, text="Loading...",
            font=get_font("xs"), fg=THEME.comment, bg=THEME.bg_highlight,
            justify=tk.LEFT
        )
        self.stats_label.pack(anchor=tk.W, pady=(5, 0))
    
    async def refresh(self) -> None:
        """Refresh cache stats."""
        try:
            from src.cache import get_redis_cache
            cache = await get_redis_cache()
            
            if cache.is_connected:
                stats = cache.stats
                text = (
                    f"Hits: {stats['cache_hits']} | Misses: {stats['cache_misses']}\n"
                    f"Published: {stats['articles_published']}"
                )
                self.stats_label.config(text=text, fg=THEME.fg)
            else:
                self.stats_label.config(text="Redis not connected", fg=THEME.red)
                
        except Exception as e:
            self.stats_label.config(text=f"Error: {e}", fg=THEME.red)


# Helper function to add save button to article cards
def add_save_button_to_card(
    card_frame: tk.Frame,
    article_id: str,
    async_runner: Optional[Any] = None,
) -> SaveArticleButton:
    """
    Add a save button to an article card.
    
    Args:
        card_frame: The card frame to add button to
        article_id: Article ID
        async_runner: Async runner for storage operations
    
    Returns:
        The created SaveArticleButton
    """
    def on_save(aid: str, saved: bool) -> None:
        async def do_save():
            try:
                from src.db_storage import get_storage_manager
                storage = await get_storage_manager()
                
                if saved:
                    storage.save_article(aid)
                    logger.info(f"Article {aid} saved")
                else:
                    storage.unsave_article(aid)
                    logger.info(f"Article {aid} unsaved")
                    
            except Exception as e:
                logger.error(f"Save error: {e}")
        
        if async_runner:
            async_runner.run_async(do_save())
        else:
            asyncio.create_task(do_save())
    
    return SaveArticleButton(card_frame, article_id, on_save=on_save)
