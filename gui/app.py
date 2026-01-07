"""
Tech News Scraper v5.0 - Professional GUI

Features:
- Auto-fetch latest tech news on startup
- Live statistics dashboard
- Clickable results with deep analysis popups
- Refresh functionality
- Professional black & white theme
"""

import asyncio
import logging
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
from typing import Optional, List
import sys
import webbrowser
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.engine import TechNewsOrchestrator, SearchResult
from src.core import NonTechQueryError, InvalidQueryError
from src.core.types import Article

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AsyncRunner:
    """Runs async tasks in a separate thread."""
    
    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
    
    def run_async(self, coro, callback=None):
        if self._loop is None:
            return
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        if callback:
            def on_done(f):
                try:
                    result = f.result()
                    callback(result, None)
                except Exception as e:
                    callback(None, e)
            future.add_done_callback(on_done)
    
    def stop(self):
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)


class ArticlePopup:
    """Popup window for displaying detailed article content."""
    
    def __init__(self, parent, article: Article, orchestrator: TechNewsOrchestrator, async_runner: AsyncRunner):
        self.parent = parent
        self.article = article
        self.orchestrator = orchestrator
        self.async_runner = async_runner
        
        self.window = tk.Toplevel(parent)
        self.window.title(f"📰 {article.title[:50]}...")
        self.window.geometry("900x700")
        self.window.configure(bg='#ffffff')
        self.window.transient(parent)
        self.window.grab_set()
        
        self._build_ui()
        self._load_deep_analysis()
    
    def _build_ui(self):
        # Header
        header = tk.Frame(self.window, bg='#000000', height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="📰 ARTICLE ANALYSIS", font=('Helvetica', 14, 'bold'),
                 fg='#ffffff', bg='#000000').pack(pady=12)
        
        # Content
        content = tk.Frame(self.window, bg='#ffffff', padx=25, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Title
        tk.Label(content, text=self.article.title, font=('Helvetica', 16, 'bold'),
                 fg='#000000', bg='#ffffff', wraplength=800, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 8))
        
        # Meta
        score = self.article.tech_score.score if self.article.tech_score else 0
        tk.Label(content, text=f"📊 Score: {score:.2f}  |  📰 {self.article.source}",
                 font=('Helvetica', 10), fg='#666666', bg='#ffffff').pack(anchor=tk.W)
        
        # URL
        url_frame = tk.Frame(content, bg='#ffffff')
        url_frame.pack(anchor=tk.W, pady=(5, 15))
        tk.Label(url_frame, text="🔗 ", font=('Helvetica', 10), fg='#666666', bg='#ffffff').pack(side=tk.LEFT)
        url_link = tk.Label(url_frame, text=self.article.url, font=('Helvetica', 10, 'underline'),
                            fg='#0066cc', bg='#ffffff', cursor='hand2')
        url_link.pack(side=tk.LEFT)
        url_link.bind('<Button-1>', lambda e: webbrowser.open(self.article.url))
        
        tk.Frame(content, bg='#cccccc', height=1).pack(fill=tk.X, pady=8)
        
        # Content frame
        self.content_frame = tk.Frame(content, bg='#ffffff')
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.loading_label = tk.Label(self.content_frame, text="⏳ Analyzing...",
                                       font=('Helvetica', 12), fg='#666666', bg='#ffffff')
        self.loading_label.pack(pady=40)
        
        # Buttons
        btn_frame = tk.Frame(self.window, bg='#f5f5f5', pady=12)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Button(btn_frame, text="🌐 Open in Browser", font=('Helvetica', 10, 'bold'),
                  bg='#000000', fg='#ffffff', padx=15, pady=6,
                  command=lambda: webbrowser.open(self.article.url)).pack(side=tk.LEFT, padx=15)
        tk.Button(btn_frame, text="✕ Close", font=('Helvetica', 10),
                  bg='#ffffff', fg='#000000', padx=15, pady=6,
                  command=self.window.destroy).pack(side=tk.RIGHT, padx=15)
    
    def _load_deep_analysis(self):
        async def do_analyze():
            return await self.orchestrator.analyze_url(self.article.url)
        
        def on_result(result, error):
            self.loading_label.destroy()
            if error or not result:
                self._show_basic_content()
            else:
                self._show_analysis(result)
        
        self.async_runner.run_async(do_analyze(), on_result)
    
    def _show_basic_content(self):
        if self.article.summary:
            tk.Label(self.content_frame, text="📋 Summary", font=('Helvetica', 12, 'bold'),
                     fg='#000000', bg='#ffffff').pack(anchor=tk.W, pady=(0, 5))
            tk.Label(self.content_frame, text=self.article.summary, font=('Helvetica', 11),
                     fg='#333333', bg='#ffffff', wraplength=800, justify=tk.LEFT).pack(anchor=tk.W)
        
        tk.Label(self.content_frame, text="📄 Content Preview", font=('Helvetica', 12, 'bold'),
                 fg='#000000', bg='#ffffff').pack(anchor=tk.W, pady=(15, 5))
        
        text = scrolledtext.ScrolledText(self.content_frame, font=('Helvetica', 10),
                                          bg='#f9f9f9', fg='#333333', wrap=tk.WORD, height=12)
        text.pack(fill=tk.BOTH, expand=True)
        preview = self.article.content[:1500] + "..." if len(self.article.content) > 1500 else self.article.content
        text.insert(tk.END, preview)
        text.config(state=tk.DISABLED)
    
    def _show_analysis(self, result):
        if result.key_points:
            tk.Label(self.content_frame, text="📌 Key Points", font=('Helvetica', 12, 'bold'),
                     fg='#000000', bg='#ffffff').pack(anchor=tk.W, pady=(0, 8))
            for i, point in enumerate(result.key_points[:5], 1):
                tk.Label(self.content_frame, text=f"  {i}. {point.text}", font=('Helvetica', 10),
                         fg='#333333', bg='#ffffff', wraplength=800, justify=tk.LEFT).pack(anchor=tk.W, pady=2)
        
        if result.entities.companies or result.entities.technologies:
            tk.Label(self.content_frame, text="", bg='#ffffff').pack(pady=3)
            if result.entities.companies:
                tk.Label(self.content_frame, text=f"🏢 Companies: {', '.join(result.entities.companies[:5])}",
                         font=('Helvetica', 10), fg='#333333', bg='#ffffff').pack(anchor=tk.W)
            if result.entities.technologies:
                tk.Label(self.content_frame, text=f"🔧 Technologies: {', '.join(result.entities.technologies[:5])}",
                         font=('Helvetica', 10), fg='#333333', bg='#ffffff').pack(anchor=tk.W)
        
        meta_frame = tk.Frame(self.content_frame, bg='#f5f5f5', pady=8, padx=10)
        meta_frame.pack(fill=tk.X, pady=12)
        tk.Label(meta_frame, text=f"💭 Sentiment: {result.sentiment.capitalize()}  |  ⏱️ {result.reading_time_min} min read",
                 font=('Helvetica', 10), fg='#333333', bg='#f5f5f5').pack(anchor=tk.W)


class TechNewsGUI:
    """Professional GUI for Tech News Scraper v5.0."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Tech News Scraper v5.0 ")
        self.root.geometry("1400x900")
        self.root.configure(bg='#ffffff')
        
        self.current_articles: List[Article] = []
        self._async_runner = AsyncRunner()
        self._async_runner.start()
        
        self._orchestrator: Optional[TechNewsOrchestrator] = None
        self._last_refresh = None
        
        self._build_ui()
        self._init_orchestrator()
    
    def _init_orchestrator(self):
        def init():
            self._orchestrator = TechNewsOrchestrator()
            self.root.after(0, self._on_ready)
        threading.Thread(target=init, daemon=True).start()
    
    def _on_ready(self):
        self._set_status("✓ Ready")
        self._update_stats()
        # Auto-fetch latest tech news
        self._auto_fetch_news()
    
    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg='#000000', height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        header_inner = tk.Frame(header, bg='#000000')
        header_inner.pack(fill=tk.X, padx=20)
        
        tk.Label(header_inner, text="🔍 TECH NEWS SCRAPER v5.0", font=('Helvetica', 20, 'bold'),
                 fg='#ffffff', bg='#000000').pack(side=tk.LEFT, pady=14)
        
        # Current time
        self.time_label = tk.Label(header_inner, text="", font=('Helvetica', 11),
                                    fg='#888888', bg='#000000')
        self.time_label.pack(side=tk.RIGHT, pady=14)
        self._update_time()
        
        # Main container
        main = tk.Frame(self.root, bg='#ffffff')
        main.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Main content
        left = tk.Frame(main, bg='#ffffff')
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Search section
        search_frame = tk.Frame(left, bg='#f5f5f5', padx=20, pady=15)
        search_frame.pack(fill=tk.X, pady=(0, 15))
        
        search_row = tk.Frame(search_frame, bg='#f5f5f5')
        search_row.pack(fill=tk.X)
        
        self.search_entry = tk.Entry(search_row, font=('Helvetica', 13), bg='#ffffff', fg='#000000',
                                      insertbackground='#000000', relief=tk.SOLID, borderwidth=1)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        self.search_entry.insert(0, "Search tech news...")
        self.search_entry.bind('<FocusIn>', lambda e: self.search_entry.delete(0, tk.END) if self.search_entry.get() == "Search tech news..." else None)
        self.search_entry.bind('<Return>', lambda e: self._on_search())
        
        tk.Button(search_row, text="🔍 Search", font=('Helvetica', 11, 'bold'), bg='#000000', fg='#ffffff',
                  padx=20, pady=8, relief=tk.FLAT, command=self._on_search).pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(search_row, text="🔄 Refresh", font=('Helvetica', 11), bg='#ffffff', fg='#000000',
                  padx=15, pady=8, relief=tk.SOLID, borderwidth=1, command=self._refresh).pack(side=tk.LEFT, padx=(10, 0))
        
        # Results section
        results_header = tk.Frame(left, bg='#ffffff')
        results_header.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(results_header, text="📰 Results", font=('Helvetica', 14, 'bold'),
                 fg='#000000', bg='#ffffff').pack(side=tk.LEFT)
        
        self.results_count = tk.Label(results_header, text="", font=('Helvetica', 11),
                                       fg='#666666', bg='#ffffff')
        self.results_count.pack(side=tk.LEFT, padx=(10, 0))
        
        # Results canvas
        self.results_canvas = tk.Canvas(left, bg='#ffffff', highlightthickness=0)
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.results_canvas.yview)
        self.results_frame = tk.Frame(self.results_canvas, bg='#ffffff')
        
        self.results_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas_window = self.results_canvas.create_window((0, 0), window=self.results_frame, anchor=tk.NW)
        
        self.results_frame.bind('<Configure>', lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all")))
        self.results_canvas.bind('<Configure>', lambda e: self.results_canvas.itemconfig(self.canvas_window, width=e.width))
        self.results_canvas.bind_all('<MouseWheel>', lambda e: self.results_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        
        # Right panel - Stats
        right = tk.Frame(main, bg='#f5f5f5', width=280)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 20), pady=15)
        right.pack_propagate(False)
        
        stats_inner = tk.Frame(right, bg='#f5f5f5', padx=20, pady=20)
        stats_inner.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(stats_inner, text="📊 Statistics", font=('Helvetica', 14, 'bold'),
                 fg='#000000', bg='#f5f5f5').pack(anchor=tk.W, pady=(0, 15))
        
        self.stats_labels = {}
        for stat, icon in [('Articles', '📰'), ('Sources', '🌐'), ('Queries', '🔍'), ('Rejected', '❌')]:
            frame = tk.Frame(stats_inner, bg='#f5f5f5')
            frame.pack(fill=tk.X, pady=6)
            tk.Label(frame, text=f"{icon} {stat}:", font=('Helvetica', 11), fg='#333333', bg='#f5f5f5').pack(side=tk.LEFT)
            self.stats_labels[stat] = tk.Label(frame, text="0", font=('Helvetica', 12, 'bold'), fg='#000000', bg='#f5f5f5')
            self.stats_labels[stat].pack(side=tk.RIGHT)
        
        tk.Frame(stats_inner, bg='#cccccc', height=1).pack(fill=tk.X, pady=15)
        
        tk.Label(stats_inner, text="⚡ Quick Actions", font=('Helvetica', 12, 'bold'),
                 fg='#000000', bg='#f5f5f5').pack(anchor=tk.W, pady=(0, 10))
        
        for text, cmd in [("🔥 Latest News", lambda: self._quick_search("latest tech news")),
                          ("🤖 AI News", lambda: self._quick_search("artificial intelligence")),
                          ("🔒 Security", lambda: self._quick_search("cybersecurity")),
                          ("💰 Startups", lambda: self._quick_search("startup funding"))]:
            tk.Button(stats_inner, text=text, font=('Helvetica', 10), bg='#ffffff', fg='#000000',
                      padx=10, pady=6, relief=tk.SOLID, borderwidth=1, command=cmd).pack(fill=tk.X, pady=3)
        
        tk.Frame(stats_inner, bg='#cccccc', height=1).pack(fill=tk.X, pady=15)
        
        self.last_refresh_label = tk.Label(stats_inner, text="Last refresh: --", font=('Helvetica', 9),
                                            fg='#888888', bg='#f5f5f5')
        self.last_refresh_label.pack(anchor=tk.W)
        
        # Developer dashboard button
        tk.Button(stats_inner, text="🛠️ Developer Dashboard", font=('Helvetica', 10, 'bold'),
                  bg='#333333', fg='#ffffff', padx=10, pady=8, relief=tk.FLAT,
                  command=self._open_developer_dashboard).pack(fill=tk.X, pady=(20, 0))
        
        # Status bar
        self.status_var = tk.StringVar(value="Initializing...")
        tk.Label(self.root, textvariable=self.status_var, font=('Helvetica', 10),
                 fg='#ffffff', bg='#000000', anchor=tk.W, padx=15, pady=6).pack(fill=tk.X, side=tk.BOTTOM)
        
        # Show welcome
        self._show_welcome()
    
    def _update_time(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=f"🕐 {now}")
        self.root.after(1000, self._update_time)
    
    def _set_status(self, status: str):
        self.status_var.set(status)
    
    def _show_welcome(self):
        frame = tk.Frame(self.results_frame, bg='#f5f5f5', padx=30, pady=25)
        frame.pack(fill=tk.X, pady=10)
        tk.Label(frame, text="Welcome to Tech News Scraper v5.0", font=('Helvetica', 16, 'bold'),
                 fg='#000000', bg='#f5f5f5').pack()
        tk.Label(frame, text="⏳ Loading latest tech news...", font=('Helvetica', 12),
                 fg='#666666', bg='#f5f5f5').pack(pady=10)
    
    def _clear_results(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        self.current_articles = []
    
    def _update_stats(self):
        if not self._orchestrator:
            return
        stats = self._orchestrator.stats
        self.stats_labels['Articles'].config(text=str(stats.get('total_articles', 0)))
        self.stats_labels['Sources'].config(text=str(stats.get('sources_scraped', 0)))
        self.stats_labels['Queries'].config(text=str(stats.get('queries_processed', 0)))
        self.stats_labels['Rejected'].config(text=str(stats.get('queries_rejected', 0)))
    
    def _auto_fetch_news(self):
        """Auto-fetch latest tech news on startup."""
        self._quick_search("latest technology news")
    
    def _refresh(self):
        """Refresh with latest news."""
        self._quick_search("latest tech news")
    
    def _quick_search(self, query: str):
        """Quick search for a preset query."""
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, query)
        self._on_search()
    
    def _on_search(self):
        query = self.search_entry.get().strip()
        if not query or query == "Search tech news...":
            return
        
        if not self._orchestrator:
            return
        
        self._clear_results()
        self._set_status(f"🔍 Searching: {query}...")
        
        loading = tk.Label(self.results_frame, text="⏳ Searching sources...", font=('Helvetica', 13),
                            fg='#666666', bg='#ffffff')
        loading.pack(pady=50)
        
        async def do_search():
            return await self._orchestrator.search(query)
        
        def on_result(result: Optional[SearchResult], error):
            loading.destroy()
            if error:
                if isinstance(error, NonTechQueryError):
                    self._show_rejection(query, error)
                else:
                    self._show_error(str(error))
            else:
                self._display_results(result)
            
            self._last_refresh = datetime.now()
            self.last_refresh_label.config(text=f"Last refresh: {self._last_refresh.strftime('%H:%M:%S')}")
            self._set_status("✓ Ready")
            self._update_stats()
        
        self._async_runner.run_async(do_search(), on_result)
    
    def _show_rejection(self, query: str, error: NonTechQueryError):
        frame = tk.Frame(self.results_frame, bg='#ffeeee', padx=25, pady=20)
        frame.pack(fill=tk.X, pady=10)
        tk.Label(frame, text="❌ Query Rejected", font=('Helvetica', 14, 'bold'),
                 fg='#cc0000', bg='#ffeeee').pack(anchor=tk.W)
        tk.Label(frame, text=error.message, font=('Helvetica', 11), fg='#666666',
                 bg='#ffeeee', wraplength=700, justify=tk.LEFT).pack(anchor=tk.W, pady=8)
    
    def _show_error(self, message: str):
        tk.Label(self.results_frame, text=f"❌ Error: {message}", font=('Helvetica', 13),
                 fg='#cc0000', bg='#ffffff').pack(pady=20)
    
    def _display_results(self, result: SearchResult):
        self.current_articles = result.articles
        self.results_count.config(text=f"({len(result.articles)} articles from {result.total_sources_scraped} sources)")
        
        if not result.articles:
            tk.Label(self.results_frame, text="No articles found.", font=('Helvetica', 13),
                     fg='#666666', bg='#ffffff').pack(pady=50)
            return
        
        for article in result.articles:
            self._create_article_card(article)
    
    def _create_article_card(self, article: Article):
        card = tk.Frame(self.results_frame, bg='#ffffff', relief=tk.SOLID, borderwidth=1, padx=15, pady=12)
        card.pack(fill=tk.X, pady=4)
        
        card.bind('<Enter>', lambda e: card.configure(bg='#fafafa'))
        card.bind('<Leave>', lambda e: card.configure(bg='#ffffff'))
        
        top = tk.Frame(card, bg=card.cget('bg'))
        top.pack(fill=tk.X)
        
        score = article.tech_score.score if article.tech_score else 0
        tk.Label(top, text=f"[{score:.2f}]", font=('Consolas', 10, 'bold'),
                 fg='#28a745' if score > 0.5 else '#888888', bg=card.cget('bg')).pack(side=tk.LEFT)
        tk.Label(top, text=article.title, font=('Helvetica', 12, 'bold'), fg='#000000',
                 bg=card.cget('bg'), anchor=tk.W, wraplength=800, justify=tk.LEFT).pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)
        
        tk.Label(card, text=f"📰 {article.source}  |  🔗 {article.url[:60]}...", font=('Helvetica', 9),
                 fg='#666666', bg=card.cget('bg')).pack(anchor=tk.W, pady=(4, 0))
        
        btn_frame = tk.Frame(card, bg=card.cget('bg'))
        btn_frame.pack(anchor=tk.E, pady=(8, 0))
        
        tk.Button(btn_frame, text="🔬 Analyze", font=('Helvetica', 9, 'bold'), bg='#000000', fg='#ffffff',
                  padx=12, pady=4, relief=tk.FLAT, command=lambda: ArticlePopup(self.root, article, self._orchestrator, self._async_runner)).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(btn_frame, text="🌐 Open", font=('Helvetica', 9), bg='#ffffff', fg='#000000',
                  padx=12, pady=4, relief=tk.SOLID, borderwidth=1, command=lambda: webbrowser.open(article.url)).pack(side=tk.LEFT)
    
    def _open_developer_dashboard(self):
        """Open the developer dashboard."""
        DeveloperDashboard(self.root, self._orchestrator, self._async_runner)
    
    def on_close(self):
        self._async_runner.stop()
        self.root.destroy()


class DeveloperDashboard:
    """Developer dashboard for monitoring application internals."""
    
    def __init__(self, parent, orchestrator: TechNewsOrchestrator, async_runner: AsyncRunner):
        self.parent = parent
        self.orchestrator = orchestrator
        self.async_runner = async_runner
        
        self.window = tk.Toplevel(parent)
        self.window.title("🛠️ Developer Dashboard - Tech News Scraper")
        self.window.geometry("1100x750")
        self.window.configure(bg='#1a1a1a')
        
        self._build_ui()
        self._update_data()
        self._start_refresh()
    
    def _build_ui(self):
        # Header
        header = tk.Frame(self.window, bg='#000000', height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🛠️ DEVELOPER DASHBOARD", font=('Consolas', 16, 'bold'),
                 fg='#00ff88', bg='#000000').pack(side=tk.LEFT, padx=20, pady=12)
        
        self.time_label = tk.Label(header, text="", font=('Consolas', 11), fg='#888888', bg='#000000')
        self.time_label.pack(side=tk.RIGHT, padx=20, pady=12)
        
        # Main content with tabs
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        style = ttk.Style()
        style.configure('TNotebook', background='#1a1a1a')
        style.configure('TNotebook.Tab', font=('Consolas', 10, 'bold'))
        
        # Stats tab
        stats_frame = tk.Frame(notebook, bg='#1a1a1a')
        notebook.add(stats_frame, text="📊 Performance")
        self._build_stats_tab(stats_frame)
        
        # Cache tab
        cache_frame = tk.Frame(notebook, bg='#1a1a1a')
        notebook.add(cache_frame, text="💾 Cache")
        self._build_cache_tab(cache_frame)
        
        # Logs tab
        logs_frame = tk.Frame(notebook, bg='#1a1a1a')
        notebook.add(logs_frame, text="📋 Logs")
        self._build_logs_tab(logs_frame)
        
        # Workflow tab
        workflow_frame = tk.Frame(notebook, bg='#1a1a1a')
        notebook.add(workflow_frame, text="🔄 Workflow")
        self._build_workflow_tab(workflow_frame)
    
    def _build_stats_tab(self, parent):
        # Grid of stats
        grid = tk.Frame(parent, bg='#1a1a1a', padx=20, pady=20)
        grid.pack(fill=tk.BOTH, expand=True)
        
        self.perf_labels = {}
        
        stats = [
            ('Total Requests', 'requests'),
            ('Successful', 'successes'),
            ('Failed', 'failures'),
            ('Cache Hits', 'cached_hits'),
            ('Articles Found', 'articles_found'),
            ('Queries Processed', 'queries_processed'),
            ('Queries Rejected', 'queries_rejected'),
            ('URLs Analyzed', 'urls_analyzed'),
        ]
        
        for i, (label, key) in enumerate(stats):
            row, col = i // 4, i % 4
            
            frame = tk.Frame(grid, bg='#2a2a2a', padx=20, pady=15)
            frame.grid(row=row, column=col, padx=8, pady=8, sticky='nsew')
            
            tk.Label(frame, text=label, font=('Consolas', 10), fg='#888888', bg='#2a2a2a').pack()
            self.perf_labels[key] = tk.Label(frame, text="0", font=('Consolas', 20, 'bold'),
                                              fg='#00ff88', bg='#2a2a2a')
            self.perf_labels[key].pack()
        
        for i in range(4):
            grid.columnconfigure(i, weight=1)
    
    def _build_cache_tab(self, parent):
        content = tk.Frame(parent, bg='#1a1a1a', padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(content, text="HTTP Response Cache", font=('Consolas', 14, 'bold'),
                 fg='#ffffff', bg='#1a1a1a').pack(anchor=tk.W, pady=(0, 15))
        
        self.cache_labels = {}
        for label in ['Size', 'Max Size', 'Hits', 'Misses', 'Hit Rate']:
            frame = tk.Frame(content, bg='#2a2a2a', padx=15, pady=10)
            frame.pack(fill=tk.X, pady=3)
            tk.Label(frame, text=f"{label}:", font=('Consolas', 11), fg='#888888', bg='#2a2a2a').pack(side=tk.LEFT)
            self.cache_labels[label] = tk.Label(frame, text="--", font=('Consolas', 11, 'bold'),
                                                 fg='#00ff88', bg='#2a2a2a')
            self.cache_labels[label].pack(side=tk.RIGHT)
        
        tk.Label(content, text="URL Deduplicator (Bloom Filter)", font=('Consolas', 14, 'bold'),
                 fg='#ffffff', bg='#1a1a1a').pack(anchor=tk.W, pady=(25, 15))
        
        self.bloom_labels = {}
        for label in ['Items', 'Size (KB)', 'False Positive Rate']:
            frame = tk.Frame(content, bg='#2a2a2a', padx=15, pady=10)
            frame.pack(fill=tk.X, pady=3)
            tk.Label(frame, text=f"{label}:", font=('Consolas', 11), fg='#888888', bg='#2a2a2a').pack(side=tk.LEFT)
            self.bloom_labels[label] = tk.Label(frame, text="--", font=('Consolas', 11, 'bold'),
                                                 fg='#ffaa00', bg='#2a2a2a')
            self.bloom_labels[label].pack(side=tk.RIGHT)
    
    def _build_logs_tab(self, parent):
        content = tk.Frame(parent, bg='#1a1a1a', padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(content, text="Application Logs (scraper.log)", font=('Consolas', 12, 'bold'),
                 fg='#ffffff', bg='#1a1a1a').pack(anchor=tk.W, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(content, font=('Consolas', 9), bg='#0a0a0a',
                                                    fg='#00ff88', wrap=tk.WORD, height=25)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        btn_frame = tk.Frame(content, bg='#1a1a1a')
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(btn_frame, text="🔄 Refresh Logs", font=('Consolas', 10), bg='#333333', fg='#ffffff',
                  padx=15, pady=5, command=self._load_logs).pack(side=tk.LEFT)
        
        self._load_logs()
    
    def _build_workflow_tab(self, parent):
        content = tk.Frame(parent, bg='#1a1a1a', padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(content, text="Application Workflow", font=('Consolas', 14, 'bold'),
                 fg='#ffffff', bg='#1a1a1a').pack(anchor=tk.W, pady=(0, 20))
        
        workflow = """
┌─────────────────────────────────────────────────────────────────┐
│                     TECH NEWS SCRAPER v5.0                      │
│                      Application Workflow                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Query ──► QueryEngine ──► Intent Classification           │
│                      │                                          │
│                      ▼                                          │
│              Tech Score Analysis (Trie-based)                   │
│                      │                                          │
│           ┌─────────┴─────────┐                                 │
│           ▼                   ▼                                 │
│       ACCEPTED            REJECTED                              │
│           │                   │                                 │
│           ▼                   ▼                                 │
│     DeepScraper         Show Suggestions                        │
│           │                                                     │
│           ▼                                                     │
│  ┌────────────────────────────┐                                │
│  │     Premium Sources        │                                │
│  │  • TechCrunch             │                                │
│  │  • The Verge              │                                │
│  │  • Wired                  │                                │
│  │  • Ars Technica           │                                │
│  │  • MIT Tech Review        │                                │
│  └────────────────────────────┘                                │
│           │                                                     │
│           ▼                                                     │
│   Link Discovery Algorithm ──► Content Extraction               │
│           │                         │                           │
│           ▼                         ▼                           │
│   URL Deduplication          Article Processing                 │
│   (Bloom Filter)             (Tech Score + Keywords)            │
│           │                         │                           │
│           └──────────┬──────────────┘                           │
│                      ▼                                          │
│              LRU Cache (HTTP Responses)                         │
│                      │                                          │
│                      ▼                                          │
│              Display Results                                    │
│                      │                                          │
│                      ▼                                          │
│              Deep Analysis (on click)                           │
│              • Entity Extraction                                │
│              • Key Points                                       │
│              • Sentiment Analysis                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
        """
        
        text = scrolledtext.ScrolledText(content, font=('Consolas', 10), bg='#0a0a0a',
                                          fg='#00ff88', wrap=tk.NONE, height=30)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, workflow)
        text.config(state=tk.DISABLED)
    
    def _load_logs(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        
        log_file = PROJECT_ROOT / "logs" / "scraper.log"
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()[-100:]  # Last 100 lines
                    self.log_text.insert(tk.END, "".join(lines))
            except Exception as e:
                self.log_text.insert(tk.END, f"Error reading logs: {e}")
        else:
            self.log_text.insert(tk.END, "No log file found.")
        
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)
    
    def _update_data(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=f"🕐 {now}")
        
        if not self.orchestrator:
            return
        
        # Update performance stats
        stats = self.orchestrator.stats
        scraper_stats = stats.get('scraper_stats', {})
        
        for key in self.perf_labels:
            value = scraper_stats.get(key, stats.get(key, 0))
            self.perf_labels[key].config(text=str(value))
        
        # Update cache stats
        cache_stats = scraper_stats.get('cache_stats', {})
        self.cache_labels['Size'].config(text=str(cache_stats.get('size', 0)))
        self.cache_labels['Max Size'].config(text=str(cache_stats.get('max_size', 0)))
        self.cache_labels['Hits'].config(text=str(cache_stats.get('hits', 0)))
        self.cache_labels['Misses'].config(text=str(cache_stats.get('misses', 0)))
        self.cache_labels['Hit Rate'].config(text=f"{cache_stats.get('hit_rate', 0):.1%}")
        
        # Update bloom filter stats
        dedup_stats = scraper_stats.get('dedup_stats', {})
        self.bloom_labels['Items'].config(text=str(dedup_stats.get('count', 0)))
        self.bloom_labels['Size (KB)'].config(text=f"{dedup_stats.get('size_kb', 0):.2f}")
        self.bloom_labels['False Positive Rate'].config(text=f"{dedup_stats.get('false_positive_rate', 0):.4f}")
    
    def _start_refresh(self):
        self._update_data()
        self.window.after(2000, self._start_refresh)


def main():
    root = tk.Tk()
    app = TechNewsGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()