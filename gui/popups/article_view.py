
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import logging
import webbrowser
from gui.theme import THEME, get_font
from datetime import datetime
from src.core.types import Article
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine.orchestrator import TechNewsOrchestrator
    from gui.managers.async_runner import AsyncRunner

logger = logging.getLogger(__name__)

# Import bypass module for protected content
try:
    from src.bypass import (
        AntiBotBypass, 
        PaywallBypass, 
        ContentPlatformBypass, 
        ContentPlatform
    )
    BYPASS_AVAILABLE = True
except ImportError:
    BYPASS_AVAILABLE = False


class FullContentPopup:
    """
    Popup for viewing clean, ad-free article content.
    Shows: Pure article text, author, date/time only.
    No ads, sponsors, or extraneous content.
    """
    
    def __init__(self, parent, article, orchestrator, async_runner):
        self.parent = parent
        self.article = article
        self.orchestrator = orchestrator
        self.async_runner = async_runner
        
        # Initialize bypass handlers if available
        self.anti_bot = AntiBotBypass() if BYPASS_AVAILABLE else None
        self.paywall_bypass = PaywallBypass() if BYPASS_AVAILABLE else None
        
        self.window = tk.Toplevel(parent)
        self.window.title(f"📄 {article.title[:50]}..." if article.title else "News Article")
        self.window.geometry("900x800")
        self.window.configure(bg=THEME.bg)
        self.window.transient(parent)
        
        self._build_ui()
        self._fetch_full_content()
    
    def _build_ui(self):
        # Header
        header = tk.Frame(self.window, bg=THEME.bg_dark, height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Frame(header, bg=THEME.green, height=3).pack(fill=tk.X, side=tk.TOP)
        
        header_inner = tk.Frame(header, bg=THEME.bg_dark)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=20)
        
        tk.Label(header_inner, text="📄", font=get_font("xl"),
                 fg=THEME.green, bg=THEME.bg_dark).pack(side=tk.LEFT, pady=10)
        tk.Label(header_inner, text="FULL ARTICLE CONTENT", font=get_font("lg", "bold"),
                 fg=THEME.fg, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=(8, 0), pady=10)
        
        # Close button in header
        tk.Button(header_inner, text="✕", font=get_font("lg"),
                  bg=THEME.bg_dark, fg=THEME.red, relief=tk.FLAT,
                  cursor='hand2', command=self.window.destroy).pack(side=tk.RIGHT, pady=10)
        
        # Content area with padding
        content = tk.Frame(self.window, bg=THEME.bg, padx=30, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Article Title
        tk.Label(content, text=self.article.title, font=get_font("xl", "bold"),
                 fg=THEME.fg, bg=THEME.bg, wraplength=800, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 15))
        
        # Meta info card (Author, Date, Source)
        meta_card = tk.Frame(content, bg=THEME.bg_visual, padx=15, pady=12)
        meta_card.pack(fill=tk.X, pady=(0, 20))
        
        # Author (from article or placeholder)
        author_text = getattr(self.article, 'author', None) or "Unknown Author"
        tk.Label(meta_card, text=f"✍️ Author: {author_text}", font=get_font("sm", "bold"),
                 fg=THEME.cyan, bg=THEME.bg_visual).pack(anchor=tk.W)
        
        # Published Date
        if self.article.published_at:
            pub_str = self.article.published_at.strftime("%A, %B %d, %Y at %I:%M %p")
            tk.Label(meta_card, text=f"📅 Published: {pub_str}", font=get_font("sm"),
                     fg=THEME.fg_dark, bg=THEME.bg_visual).pack(anchor=tk.W, pady=(5, 0))
        
        # Source
        tk.Label(meta_card, text=f"📰 Source: {self.article.source}", font=get_font("sm"),
                 fg=THEME.orange, bg=THEME.bg_visual).pack(anchor=tk.W, pady=(5, 0))
        
        # Divider
        tk.Frame(content, bg=THEME.border, height=1).pack(fill=tk.X, pady=10)
        
        # Article content frame
        self.article_frame = tk.Frame(content, bg=THEME.bg)
        self.article_frame.pack(fill=tk.BOTH, expand=True)
        
        # Loading indicator
        self.loading_frame = tk.Frame(self.article_frame, bg=THEME.bg)
        self.loading_frame.pack(expand=True)
        
        self.loading_label = tk.Label(self.loading_frame, text="⏳ Fetching clean article content...",
                                       font=get_font("md"), fg=THEME.fg_dark, bg=THEME.bg)
        self.loading_label.pack(pady=30)
        
        self.status_label = tk.Label(self.loading_frame, text="Attempting bypass if needed...",
                                      font=get_font("sm"), fg=THEME.comment, bg=THEME.bg)
        self.status_label.pack()
    
    def _fetch_full_content(self):
        """Fetch the full article content with bypass support."""
        async def do_fetch():
            # Try to get content using various methods
            content = None
            author = None
            last_error = None
            
            # Method 1: Use orchestrator's analyze_url which has bypass built-in
            try:
                result = await self.orchestrator.analyze_url(self.article.url)
                # FIX: URLAnalysisResult stores content in result.article.content, NOT result.content
                if result and result.article and result.article.content:
                    content = self._extract_clean_content(result.article.content)
                    author = getattr(result.article, 'author', None)
                    logger.debug(f"Method 1 (orchestrator) success: {len(content)} chars")
            except Exception as e:
                last_error = f"Orchestrator analysis failed: {e}"
                logger.warning(last_error)
            
            # Method 2: Try direct fetch with anti-bot bypass
            if not content and self.anti_bot:
                try:
                    self.window.after(0, lambda: self.status_label.config(text="Trying anti-bot bypass..."))
                    result = await self.anti_bot.fetch_with_bypass(self.article.url)
                    if result.success and result.content:
                        content = self._extract_clean_content(result.content)
                        logger.debug(f"Method 2 (anti-bot) success: {len(content)} chars")
                except Exception as e:
                    last_error = f"Anti-bot bypass failed: {e}"
                    logger.warning(last_error)
            
            # Method 3: Try paywall bypass
            if not content and self.paywall_bypass:
                try:
                    self.window.after(0, lambda: self.status_label.config(text="Trying paywall bypass..."))
                    result = await self.paywall_bypass.bypass_paywall(self.article.url)
                    if result.success and result.content:
                        content = self._extract_clean_content(result.content)
                        logger.debug(f"Method 3 (paywall) success: {len(content)} chars")
                except Exception as e:
                    last_error = f"Paywall bypass failed: {e}"
                    logger.warning(last_error)
            
            # Method 4: Use cached article content (if available)
            if not content and self.article.content:
                content = self._extract_clean_content(self.article.content)
                logger.debug(f"Method 4 (cached) used: {len(content)} chars")
            
            # Provide meaningful error message if all methods failed
            if not content:
                error_msg = "Unable to fetch article content. The site may be blocking access."
                if last_error:
                    logger.error(f"All fetch methods failed. Last error: {last_error}")
                content = error_msg
            
            return {
                'content': content,
                'author': author or getattr(self.article, 'author', None)
            }
        
        def on_result(result, error):
            if self.loading_frame.winfo_exists():
                self.loading_frame.destroy()
            if error:
                self._display_error(str(error))
            else:
                self._display_content(result)
        
        self.async_runner.run_async(do_fetch(), on_result)
    
    def _extract_clean_content(self, raw_content: str) -> str:
        """Extract clean article text, removing ads, sponsors, navigation, etc."""
        if not raw_content:
            return ""
        
        import re
        
        # Remove common ad/sponsor patterns
        patterns_to_remove = [
            r'<script[^>]*>.*?</script>',  # Scripts
            r'<style[^>]*>.*?</style>',     # Styles
            r'<nav[^>]*>.*?</nav>',         # Navigation
            r'<footer[^>]*>.*?</footer>',   # Footer
            r'<aside[^>]*>.*?</aside>',     # Sidebars
            r'<header[^>]*>.*?</header>',   # Headers
            r'advertisement|sponsored|promotion|subscribe|newsletter',  # Ad keywords
            r'\[ad\]|\[advertisement\]',    # Ad markers
            r'related articles?|you may also like|recommended',  # Related content
        ]
        
        content = raw_content
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean HTML tags but preserve paragraphs
        content = re.sub(r'<br\s*/?>', '\n', content)
        content = re.sub(r'</p>', '\n\n', content)
        content = re.sub(r'<[^>]+>', '', content)  # Remove remaining tags
        
        # Clean up whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)  # Max 2 newlines
        content = re.sub(r'[ \t]+', ' ', content)     # Single spaces
        content = content.strip()
        
        # Decode HTML entities
        import html
        content = html.unescape(content)
        
        return content
    
    def _display_content(self, result: dict):
        """Display the clean article content."""
        # Update author if available
        if result.get('author'):
            # Find and update the author label (simplified approach - recreate)
            pass
        
        # Article text with scrolling
        text_frame = tk.Frame(self.article_frame, bg=THEME.bg)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Label for section
        tk.Label(text_frame, text="📖 Article Content", font=get_font("md", "bold"),
                 fg=THEME.cyan, bg=THEME.bg).pack(anchor=tk.W, pady=(0, 10))
        
        # Scrollable text area for content
        content_text = scrolledtext.ScrolledText(
            text_frame, font=get_font("md"),
            bg=THEME.bg_highlight, fg=THEME.fg,
            wrap=tk.WORD, relief=tk.FLAT,
            highlightthickness=1, highlightbackground=THEME.bg_visual,
            insertbackground=THEME.cyan, padx=15, pady=15
        )
        content_text.pack(fill=tk.BOTH, expand=True)
        
        # Insert content
        content_text.insert(tk.END, result['content'])
        content_text.config(state=tk.DISABLED)
        
        # Word count
        word_count = len(result['content'].split())
        reading_time = max(1, word_count // 200)  # ~200 words per minute
        
        stats_frame = tk.Frame(self.article_frame, bg=THEME.bg)
        stats_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Label(stats_frame, text=f"📊 {word_count:,} words  |  ⏱️ ~{reading_time} min read",
                 font=get_font("sm"), fg=THEME.comment, bg=THEME.bg).pack(side=tk.RIGHT)
    
    def _display_error(self, error: str):
        """Display error message when content fetch fails."""
        error_frame = tk.Frame(self.article_frame, bg=THEME.bg_visual, padx=20, pady=15)
        error_frame.pack(fill=tk.X, pady=20)
        
        tk.Label(error_frame, text="⚠️", font=get_font("xl"),
                 fg=THEME.yellow, bg=THEME.bg_visual).pack(side=tk.LEFT)
        
        msg_frame = tk.Frame(error_frame, bg=THEME.bg_visual)
        msg_frame.pack(side=tk.LEFT, padx=15)
        
        tk.Label(msg_frame, text="Content Unavailable", font=get_font("md", "bold"),
                 fg=THEME.fg, bg=THEME.bg_visual).pack(anchor=tk.W)
        tk.Label(msg_frame, text="Unable to fetch clean content. Try opening in browser.",
                 font=get_font("sm"), fg=THEME.fg_dark, bg=THEME.bg_visual).pack(anchor=tk.W)
        
        # Fallback: Show cached content if available
        if self.article.content:
            tk.Label(self.article_frame, text="📋 Cached Preview", font=get_font("md", "bold"),
                     fg=THEME.cyan, bg=THEME.bg).pack(anchor=tk.W, pady=(20, 10))
            
            preview_text = scrolledtext.ScrolledText(
                self.article_frame, font=get_font("sm"),
                bg=THEME.bg_highlight, fg=THEME.fg_dark,
                wrap=tk.WORD, height=12, relief=tk.FLAT
            )
            preview_text.pack(fill=tk.BOTH, expand=True)
            
            clean = self._extract_clean_content(self.article.content)
            preview_text.insert(tk.END, clean[:3000])
            preview_text.config(state=tk.DISABLED)


class ArticlePopup:
    """Popup window for displaying detailed article content with Tokyo Night theme."""
    
    def __init__(self, parent, article: Article, orchestrator: "TechNewsOrchestrator", async_runner: "AsyncRunner"):
        self.parent = parent
        self.article = article
        self.orchestrator = orchestrator
        self.async_runner = async_runner
        
        self.window = tk.Toplevel(parent)
        self.window.title(f"📰 {article.title[:50]}...")
        self.window.geometry("950x750")
        self.window.configure(bg=THEME.bg)
        self.window.transient(parent)
        self.window.grab_set()
        
        self._build_ui()
        self._load_deep_analysis()
    
    def _build_ui(self):
        # Header
        header = tk.Frame(self.window, bg=THEME.bg_dark, height=55)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Frame(header, bg=THEME.cyan, height=3).pack(fill=tk.X, side=tk.TOP)
        
        header_inner = tk.Frame(header, bg=THEME.bg_dark)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=20)
        
        tk.Label(header_inner, text="📰", font=get_font("xl"),
                 fg=THEME.orange, bg=THEME.bg_dark).pack(side=tk.LEFT, pady=10)
        tk.Label(header_inner, text="ARTICLE ANALYSIS", font=get_font("lg", "bold"),
                 fg=THEME.fg, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=(8, 0), pady=10)
        
        # Content area
        content = tk.Frame(self.window, bg=THEME.bg, padx=25, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Title
        tk.Label(content, text=self.article.title, font=get_font("xl", "bold"),
                 fg=THEME.fg, bg=THEME.bg, wraplength=850, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 12))
        
        # Meta info row
        meta_frame = tk.Frame(content, bg=THEME.bg)
        meta_frame.pack(fill=tk.X, pady=(0, 15))
        
        score = self.article.tech_score.score if self.article.tech_score else 0
        score_color = THEME.green if score > 0.7 else THEME.yellow if score > 0.4 else THEME.red
        
        tk.Label(meta_frame, text=f"📊 Score: {score:.2f}", font=get_font("sm"),
                 fg=score_color, bg=THEME.bg).pack(side=tk.LEFT)
        tk.Label(meta_frame, text=" | ", fg=THEME.comment, bg=THEME.bg).pack(side=tk.LEFT)
        tk.Label(meta_frame, text=f"📰 {self.article.source}", font=get_font("sm"),
                 fg=THEME.orange, bg=THEME.bg).pack(side=tk.LEFT)
        
        if self.article.published_at:
            tk.Label(meta_frame, text=" | ", fg=THEME.comment, bg=THEME.bg).pack(side=tk.LEFT)
            pub_str = self.article.published_at.strftime("%b %d, %Y at %I:%M %p")
            tk.Label(meta_frame, text=f"📅 {pub_str}", font=get_font("sm"),
                     fg=THEME.fg_dark, bg=THEME.bg).pack(side=tk.LEFT)
        
        # URL
        url_frame = tk.Frame(content, bg=THEME.bg)
        url_frame.pack(anchor=tk.W, pady=(0, 15))
        tk.Label(url_frame, text="🔗", font=get_font("sm"),
                 fg=THEME.blue, bg=THEME.bg).pack(side=tk.LEFT)
        url_link = tk.Label(url_frame, text=self.article.url, font=get_font("sm"),
                            fg=THEME.blue, bg=THEME.bg, cursor='hand2')
        url_link.pack(side=tk.LEFT, padx=(5, 0))
        url_link.bind('<Button-1>', lambda e: webbrowser.open(self.article.url))
        
        # Divider
        tk.Frame(content, bg=THEME.border, height=1).pack(fill=tk.X, pady=10)
        
        # Content frame (for analysis results)
        self.content_frame = tk.Frame(content, bg=THEME.bg)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.loading_label = tk.Label(self.content_frame, text="⏳ Analyzing article...",
                                       font=get_font("md"), fg=THEME.fg_dark, bg=THEME.bg)
        self.loading_label.pack(pady=40)
        
        # Bottom buttons
        btn_frame = tk.Frame(self.window, bg=THEME.bg_highlight, pady=14)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Button(btn_frame, text="🌐 Open in Browser", font=get_font("sm", "bold"),
                  bg=THEME.blue, fg=THEME.fg, activebackground=THEME.bright_blue,
                  padx=18, pady=8, relief=tk.FLAT, cursor='hand2',
                  command=lambda: webbrowser.open(self.article.url)).pack(side=tk.LEFT, padx=20)
        
        # View Full Content button - Opens clean content viewer
        tk.Button(btn_frame, text="📄 View Full Content", font=get_font("sm", "bold"),
                  bg=THEME.green, fg=THEME.black, activebackground=THEME.cyan,
                  padx=18, pady=8, relief=tk.FLAT, cursor='hand2',
                  command=self._open_full_content).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(btn_frame, text="✕ Close", font=get_font("sm"),
                  bg=THEME.bg_visual, fg=THEME.fg_dark, activebackground=THEME.bg_search,
                  padx=18, pady=8, relief=tk.FLAT, cursor='hand2',
                  command=self.window.destroy).pack(side=tk.RIGHT, padx=20)
    
    def _load_deep_analysis(self):
        async def do_analyze():
            return await self.orchestrator.analyze_url(self.article.url)
        
        def on_result(result, error):
            if self.loading_label.winfo_exists():
                self.loading_label.destroy()
            if error or not result:
                self._show_basic_content()
            else:
                self._show_analysis(result)
        
        self.async_runner.run_async(do_analyze(), on_result)
    
    def _show_basic_content(self):
        """Show basic article content when deep analysis fails."""
        # Warning about failed fetch
        warning_frame = tk.Frame(self.content_frame, bg=THEME.bg_visual, padx=15, pady=10)
        warning_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(warning_frame, text="⚠️", font=get_font("md"),
                 fg=THEME.yellow, bg=THEME.bg_visual).pack(side=tk.LEFT)
        tk.Label(warning_frame, text="Deep analysis unavailable. Showing cached data.", 
                 font=get_font("sm"), fg=THEME.fg_dark, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(8, 0))
        
        # Summary section (if available)
        if self.article.summary:
            tk.Label(self.content_frame, text="📋 Summary", font=get_font("md", "bold"),
                     fg=THEME.cyan, bg=THEME.bg).pack(anchor=tk.W, pady=(0, 8))
            summary_text = tk.Label(self.content_frame, text=self.article.summary, 
                                    font=get_font("md"), fg=THEME.fg,
                                    bg=THEME.bg, wraplength=850, justify=tk.LEFT)
            summary_text.pack(anchor=tk.W, pady=(0, 15))
        
        # Keywords section (if available)
        if self.article.keywords:
            tk.Label(self.content_frame, text="🏷️ Keywords", font=get_font("md", "bold"),
                     fg=THEME.cyan, bg=THEME.bg).pack(anchor=tk.W, pady=(0, 8))
            
            kw_frame = tk.Frame(self.content_frame, bg=THEME.bg)
            kw_frame.pack(anchor=tk.W, pady=(0, 15))
            
            for kw in self.article.keywords[:8]:
                badge = tk.Frame(kw_frame, bg=THEME.bg_visual, padx=10, pady=4)
                badge.pack(side=tk.LEFT, padx=(0, 6), pady=2)
                tk.Label(badge, text=kw, font=get_font("xs"),
                         fg=THEME.cyan, bg=THEME.bg_visual).pack()
        
        # Tech score details (if available)
        if self.article.tech_score and self.article.tech_score.matched_keywords:
            tk.Label(self.content_frame, text="🔧 Matched Tech Keywords", font=get_font("md", "bold"),
                     fg=THEME.cyan, bg=THEME.bg).pack(anchor=tk.W, pady=(0, 8))
            
            tech_kw_frame = tk.Frame(self.content_frame, bg=THEME.bg)
            tech_kw_frame.pack(anchor=tk.W, pady=(0, 15))
            
            for kw in self.article.tech_score.matched_keywords[:10]:
                badge = tk.Frame(tech_kw_frame, bg=THEME.green, padx=10, pady=4)
                badge.pack(side=tk.LEFT, padx=(0, 6), pady=2)
                tk.Label(badge, text=kw, font=get_font("xs"),
                         fg=THEME.black, bg=THEME.green).pack()
        
        # Content preview section
        tk.Label(self.content_frame, text="📄 Content Preview", font=get_font("md", "bold"),
                 fg=THEME.cyan, bg=THEME.bg).pack(anchor=tk.W, pady=(10, 8))
        
        content_text = self.article.content if self.article.content else "Content not available. Click 'Open in Browser' to view the full article."
        
        text = scrolledtext.ScrolledText(self.content_frame, font=get_font("sm"),
                                          bg=THEME.bg_highlight, fg=THEME.fg_dark, 
                                          wrap=tk.WORD, height=10, relief=tk.FLAT,
                                          insertbackground=THEME.cyan)
        text.pack(fill=tk.BOTH, expand=True)
        
        preview = content_text[:2000] + "..." if len(content_text) > 2000 else content_text
        text.insert(tk.END, preview)
        text.config(state=tk.DISABLED)
    
    def _show_analysis(self, result):
        """Show detailed analysis results with Tokyo Night styling."""
        # Key points
        if result.key_points:
            tk.Label(self.content_frame, text="📌 Key Points", font=get_font("md", "bold"),
                     fg=THEME.cyan, bg=THEME.bg).pack(anchor=tk.W, pady=(0, 10))
            
            for i, point in enumerate(result.key_points[:5], 1):
                point_frame = tk.Frame(self.content_frame, bg=THEME.bg_highlight, padx=12, pady=8)
                point_frame.pack(fill=tk.X, pady=3)
                tk.Label(point_frame, text=f"{i}.", font=get_font("sm", "bold"),
                         fg=THEME.cyan, bg=THEME.bg_highlight).pack(side=tk.LEFT)
                tk.Label(point_frame, text=point.text, font=get_font("sm"),
                         fg=THEME.fg, bg=THEME.bg_highlight, wraplength=800, 
                         justify=tk.LEFT).pack(side=tk.LEFT, padx=(8, 0))
        
        # Entities
        if result.entities.companies or result.entities.technologies:
            entity_frame = tk.Frame(self.content_frame, bg=THEME.bg)
            entity_frame.pack(fill=tk.X, pady=(15, 0))
            
            if result.entities.companies:
                tk.Label(entity_frame, text=f"🏢 Companies: {', '.join(result.entities.companies[:5])}",
                         font=get_font("sm"), fg=THEME.orange, bg=THEME.bg).pack(anchor=tk.W)
            if result.entities.technologies:
                tk.Label(entity_frame, text=f"🔧 Technologies: {', '.join(result.entities.technologies[:5])}",
                         font=get_font("sm"), fg=THEME.green, bg=THEME.bg).pack(anchor=tk.W, pady=(5, 0))
        
        # Meta info
        meta_frame = tk.Frame(self.content_frame, bg=THEME.bg_visual, pady=10, padx=15)
        meta_frame.pack(fill=tk.X, pady=15)
        
        sentiment = result.sentiment.value if hasattr(result.sentiment, 'value') else str(result.sentiment)
        tk.Label(meta_frame, text=f"💭 Sentiment: {sentiment.capitalize()}", 
                 font=get_font("sm"), fg=THEME.fg_dark, bg=THEME.bg_visual).pack(side=tk.LEFT)
        tk.Label(meta_frame, text=f"  |  ⏱️ {result.reading_time_min} min read",
                 font=get_font("sm"), fg=THEME.fg_dark, bg=THEME.bg_visual).pack(side=tk.LEFT)

    def _open_full_content(self):
        """Open the full content viewer popup."""
        FullContentPopup(self.parent, self.article, self.orchestrator, self.async_runner)
