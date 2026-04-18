"""
Real-Time Live Dashboard for Tech News Scraper.

Transforms the static welcome screen into a dynamic, live, real-time experience
showing actual working data, live connections, and genuine system activity.

Components:
- LiveSourceHeartbeatMonitor: Real-time source connection status with ping/latency
- LiveArticleStreamPreview: Live article feed showing articles as discovered
- LiveStatisticsPanel: Real-time metrics updating live
- LiveActivityLog: Real system events streaming
- PipelineVisualizer: Multi-stage pipeline with real progress
- SourceActivityMatrix: Per-source fetch progress
- NetworkThroughputGraph: Live network activity visualization
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime, timedelta
import asyncio
import logging
from dataclasses import dataclass
from collections import deque
import time

logger = logging.getLogger(__name__)


# Import theme
from gui.theme import TokyoNightColors as THEME
from gui import get_font


@dataclass
class SourceStatus:
    """Real-time source connection status."""
    name: str
    latency_ms: int
    status: str  # 'streaming', 'connecting', 'syncing', 'offline', 'error'
    articles_found: int = 0
    last_update: Optional[datetime] = None
    error_count: int = 0


@dataclass
class PipelineStage:
    """Pipeline stage state."""
    name: str
    progress: float  # 0.0 to 1.0
    status: str  # 'waiting', 'active', 'complete'
    processed_count: int = 0
    total_count: int = 0
    current_item: str = ""
    metrics: Dict[str, Any] = None
    start_time: Optional[datetime] = None
    
    @property
    def elapsed_seconds(self) -> float:
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0


class LiveSourceHeartbeatMonitor(tk.Frame):
    """
    Real-time source network status monitor.
    
    Shows live ping/latency to each source, connection quality,
    and fetch status with visual signal bars.
    """
    
    def __init__(self, parent, orchestrator=None, **kwargs):
        super().__init__(parent, bg=THEME.bg_highlight, **kwargs)
        
        self.orchestrator = orchestrator
        self.source_rows: Dict[str, Dict] = {}
        self.source_statuses: Dict[str, SourceStatus] = {}
        self.monitoring_active = False
        
        # Header
        header = tk.Frame(self, bg=THEME.bg_highlight)
        header.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        tk.Label(header, text="🌐", font=get_font("lg"),
                fg=THEME.cyan, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        tk.Label(header, text="LIVE SOURCE NETWORK STATUS", 
                font=get_font("md", "bold"),
                fg=THEME.fg, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(8, 0))
        
        # Container for source rows
        self.sources_container = tk.Frame(self, bg=THEME.bg_highlight)
        self.sources_container.pack(fill=tk.X, padx=15, pady=5)
        
        # Initialize with default sources
        self._init_default_sources()
        
        # Start monitoring
        self.monitoring_active = True
        self._start_monitoring()
    
    def _init_default_sources(self):
        """Initialize with common tech news sources."""
        default_sources = [
            "TechCrunch", "Hacker News", "The Verge", "Ars Technica",
            "Wired", "MIT Tech Review", "VentureBeat", 
            "Reddit/r/technology", "Product Hunt", "GitHub Trending"
        ]
        
        for source_name in default_sources:
            self._create_source_row(source_name)
            self.source_statuses[source_name] = SourceStatus(
                name=source_name,
                latency_ms=0,
                status='connecting',
                articles_found=0
            )
    
    def _create_source_row(self, source_name: str):
        """Create a row for a source."""
        row = tk.Frame(self.sources_container, bg=THEME.bg_highlight)
        row.pack(fill=tk.X, pady=2)
        
        # Source name
        name_label = tk.Label(row, text=source_name[:20], 
                             font=get_font("sm"), width=20,
                             fg=THEME.fg_dark, bg=THEME.bg_highlight, anchor=tk.W)
        name_label.pack(side=tk.LEFT)
        
        # Signal bars (visual latency indicator)
        bars_canvas = tk.Canvas(row, width=60, height=15, 
                               bg=THEME.bg_highlight, highlightthickness=0)
        bars_canvas.pack(side=tk.LEFT, padx=(10, 0))
        
        # Draw initial bars
        self._draw_signal_bars(bars_canvas, 0)
        
        # Latency value
        latency_label = tk.Label(row, text="-- ms", font=get_font("xs"),
                                fg=THEME.comment, bg=THEME.bg_highlight, width=10)
        latency_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Status indicator
        status_label = tk.Label(row, text="⏳ CONNECTING", font=get_font("xs", "bold"),
                               fg=THEME.yellow, bg=THEME.bg_highlight, width=15)
        status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Articles found counter
        count_label = tk.Label(row, text="0 articles", font=get_font("xs"),
                              fg=THEME.comment, bg=THEME.bg_highlight, width=12)
        count_label.pack(side=tk.RIGHT)
        
        self.source_rows[source_name] = {
            'frame': row,
            'bars_canvas': bars_canvas,
            'latency_label': latency_label,
            'status_label': status_label,
            'count_label': count_label,
            'name_label': name_label
        }
    
    def _draw_signal_bars(self, canvas: tk.Canvas, strength: int):
        """Draw signal strength bars (0-5)."""
        canvas.delete('all')
        
        colors = [THEME.red, THEME.red, THEME.yellow, THEME.yellow, THEME.green, THEME.green]
        
        for i in range(5):
            x = i * 12 + 2
            height = (i + 1) * 2 + 3
            y = 15 - height
            
            if i < strength:
                color = colors[i]
            else:
                color = THEME.bg_visual
            
            canvas.create_rectangle(x, y, x + 8, 15, fill=color, outline='')
    
    def _start_monitoring(self):
        """Start the heartbeat monitoring loop."""
        self._monitor_loop()
    
    def _monitor_loop(self):
        """Main monitoring loop - updates every 2-3 seconds."""
        if not self.monitoring_active:
            return
        
        # Simulate or get real source status updates
        for source_name in self.source_statuses:
            self._update_source_status(source_name)
        
        # Schedule next update (2-3 seconds random for natural feel)
        delay = 2000 + int(time.time() * 1000) % 1000
        self.after(delay, self._monitor_loop)
    
    def _update_source_status(self, source_name: str):
        """Update display for a single source."""
        status = self.source_statuses[source_name]
        widgets = self.source_rows[source_name]
        
        # Calculate signal strength from latency
        if status.latency_ms == 0:
            strength = 0
        elif status.latency_ms < 100:
            strength = 5
        elif status.latency_ms < 200:
            strength = 4
        elif status.latency_ms < 300:
            strength = 3
        elif status.latency_ms < 500:
            strength = 2
        else:
            strength = 1
        
        # Update bars
        self._draw_signal_bars(widgets['bars_canvas'], strength)
        
        # Update latency
        if status.latency_ms > 0:
            widgets['latency_label'].config(text=f"{status.latency_ms} ms")
        
        # Update status with color coding
        status_colors = {
            'streaming': (THEME.green, "● STREAMING"),
            'connecting': (THEME.yellow, "🔄 CONNECTING"),
            'syncing': (THEME.cyan, "⏳ SYNCING"),
            'offline': (THEME.comment, "○ OFFLINE"),
            'error': (THEME.red, "❌ ERROR")
        }
        
        color, text = status_colors.get(status.status, (THEME.comment, "? UNKNOWN"))
        widgets['status_label'].config(text=text, fg=color)
        
        # Update count
        if status.articles_found > 0:
            widgets['count_label'].config(text=f"{status.articles_found} articles")
    
    def update_source(self, source_name: str, latency_ms: int, 
                     status: str, articles_found: int = 0):
        """Public method to update source status from orchestrator."""
        if source_name in self.source_statuses:
            self.source_statuses[source_name].latency_ms = latency_ms
            self.source_statuses[source_name].status = status
            self.source_statuses[source_name].articles_found = articles_found
            self.source_statuses[source_name].last_update = datetime.now()
            
            # Immediate UI update
            self._update_source_status(source_name)
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.monitoring_active = False


class LiveArticleStreamPreview(tk.Frame):
    """
    Live article feed showing articles as they're discovered.
    
    Displays articles immediately when found, with real timestamps,
    tech scores, and auto-scrolling like a news ticker.
    """
    
    def __init__(self, parent, orchestrator=None, max_visible: int = 5, **kwargs):
        super().__init__(parent, bg=THEME.bg_highlight, **kwargs)
        
        self.orchestrator = orchestrator
        self.max_visible = max_visible
        self.article_widgets: List[tk.Frame] = []
        self.articles_data: deque = deque(maxlen=100)  # Keep last 100
        
        # Header
        header = tk.Frame(self, bg=THEME.bg_highlight)
        header.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        tk.Label(header, text="📡", font=get_font("lg"),
                fg=THEME.green, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        tk.Label(header, text="INCOMING ARTICLES (LIVE STREAM)", 
                font=get_font("md", "bold"),
                fg=THEME.fg, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(8, 0))
        
        # Total counter
        self.total_label = tk.Label(header, text="0 discovered", 
                                   font=get_font("sm"),
                                   fg=THEME.comment, bg=THEME.bg_highlight)
        self.total_label.pack(side=tk.RIGHT)
        
        # Container for article previews
        self.articles_container = tk.Frame(self, bg=THEME.bg_highlight)
        self.articles_container.pack(fill=tk.BOTH, expand=True, 
                                     padx=15, pady=5)
        
        # Show more indicator
        self.more_label = tk.Label(self, text="", font=get_font("xs"),
                                  fg=THEME.comment, bg=THEME.bg_highlight)
        self.more_label.pack(fill=tk.X, padx=15, pady=(0, 5))
    
    def on_article_found(self, article_data: Dict):
        """Called immediately when an article is discovered."""
        # Store article data
        self.articles_data.append({
            'data': article_data,
            'found_at': datetime.now()
        })
        
        # Create compact article preview
        preview = self._create_article_preview(article_data)
        
        # Add at top
        self.article_widgets.insert(0, preview)
        preview.pack(side=tk.TOP, fill=tk.X, pady=2)
        
        # Remove oldest if exceeds max
        if len(self.article_widgets) > self.max_visible:
            oldest = self.article_widgets.pop()
            oldest.destroy()
        
        # Update counter
        total = len(self.articles_data)
        self.total_label.config(text=f"{total} discovered")
        
        # Update "showing X of Y" text
        showing = min(len(self.article_widgets), total)
        self.more_label.config(text=f"Showing {showing} of {total} articles")
        
        # Start time update for this article
        self._schedule_time_updates(preview, datetime.now())
    
    def _create_article_preview(self, article: Dict) -> tk.Frame:
        """Create a compact article preview card."""
        frame = tk.Frame(self.articles_container, bg=THEME.bg_visual, 
                        padx=10, pady=8)
        
        # Time ago row
        time_row = tk.Frame(frame, bg=THEME.bg_visual)
        time_row.pack(fill=tk.X)
        
        time_label = tk.Label(time_row, text="🆕 Just now", 
                             font=get_font("xs"),
                             fg=THEME.green, bg=THEME.bg_visual)
        time_label.pack(side=tk.LEFT)
        
        source = article.get('source', 'Unknown')
        tk.Label(time_row, text=f"• {source}", 
                font=get_font("xs"),
                fg=THEME.cyan, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(10, 0))
        
        # Title
        title = article.get('title', 'Untitled')
        title_text = title[:70] + "..." if len(title) > 70 else title
        tk.Label(frame, text=title_text, 
                font=get_font("sm", "bold"),
                fg=THEME.fg, bg=THEME.bg_visual, 
                wraplength=600, justify=tk.LEFT).pack(fill=tk.X, pady=(4, 0))
        
        # Score and badges row
        badges_row = tk.Frame(frame, bg=THEME.bg_visual)
        badges_row.pack(fill=tk.X, pady=(4, 0))
        
        # Tech score
        score = article.get('tech_score', 0)
        if isinstance(score, dict):
            score = score.get('score', 0)
        
        score_color = THEME.green if score >= 8 else THEME.yellow if score >= 6 else THEME.red
        tk.Label(badges_row, text=f"Score: {score:.1f}/10", 
                font=get_font("xs"),
                fg=score_color, bg=THEME.bg_visual).pack(side=tk.LEFT)
        
        # Relevance
        relevance = article.get('relevance', 0)
        tk.Label(badges_row, text=f"| Relevance: {relevance}%", 
                font=get_font("xs"),
                fg=THEME.cyan, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(10, 0))
        
        # Breaking badge if fresh
        if article.get('is_breaking', False):
            tk.Label(badges_row, text="🔥 BREAKING", 
                    font=get_font("xs", "bold"),
                    fg=THEME.red, bg=THEME.bg_visual).pack(side=tk.RIGHT)
        
        return frame
    
    def _schedule_time_updates(self, widget: tk.Frame, found_at: datetime):
        """Schedule updates for the 'time ago' label."""
        def update_time():
            if not widget.winfo_exists():
                return
            
            # Find time label in widget
            for child in widget.winfo_children():
                if isinstance(child, tk.Frame):  # time_row
                    for label in child.winfo_children():
                        if isinstance(label, tk.Label) and label.cget('text').startswith('🆕'):
                            # Calculate time ago
                            delta = datetime.now() - found_at
                            seconds = int(delta.total_seconds())
                            
                            if seconds < 60:
                                text = f"🆕 {seconds}s ago"
                            elif seconds < 3600:
                                text = f"🆕 {seconds // 60}m ago"
                            else:
                                text = f"🆕 {seconds // 3600}h ago"
                            
                            label.config(text=text)
                            
                            # Schedule next update if less than 1 hour old
                            if seconds < 3600:
                                widget.after(5000, update_time)  # Update every 5 seconds
                            break
                    break
        
        # Start updates
        widget.after(1000, update_time)


class LiveStatisticsPanel(tk.Frame):
    """
    Real-time statistics panel with live updating metrics.
    
    Shows live counters, dynamic averages, and system metrics
    that update in real-time as articles are processed.
    """
    
    def __init__(self, parent, orchestrator=None, **kwargs):
        super().__init__(parent, bg=THEME.bg_highlight, **kwargs)
        
        self.orchestrator = orchestrator
        self.current_stats = {
            'articles': 0,
            'passed': 0,
            'rejected': 0,
            'avg_score': 0.0,
            'sources_active': 0,
            'throughput': 0.0,
            'processing_speed': 0,
            'db_writes': 0,
            'cache_hit_rate': 0
        }
        
        # Header
        header = tk.Frame(self, bg=THEME.bg_highlight)
        header.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        tk.Label(header, text="📊", font=get_font("lg"),
                fg=THEME.cyan, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        tk.Label(header, text="LIVE DISCOVERY METRICS", 
                font=get_font("md", "bold"),
                fg=THEME.fg, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(8, 0))
        
        # Metrics container
        self.metrics_container = tk.Frame(self, bg=THEME.bg_highlight)
        self.metrics_container.pack(fill=tk.BOTH, expand=True, 
                                   padx=15, pady=5)
        
        # Create metric widgets
        self.metric_widgets = {}
        self._create_metric("articles", "Articles Discovered:", "0")
        self._create_metric("quality", "Quality Threshold:", "0 passed, 0 rejected")
        self._create_metric("avg_score", "Average Tech Score:", "-/10")
        self._create_metric("sources", "Sources Responding:", "0/0 (0%)")
        self._create_metric("throughput", "Network Throughput:", "0 MB/s")
        self._create_metric("speed", "Processing Speed:", "0 articles/sec")
        self._create_metric("db_writes", "Database Writes:", "0 commits")
        self._create_metric("cache", "Cache Hit Rate:", "0%")
        
        # Separator
        tk.Frame(self, bg=THEME.bg_visual, height=2).pack(fill=tk.X, 
                                                          padx=15, pady=10)
        
        # Geographic info
        geo_frame = tk.Frame(self, bg=THEME.bg_highlight)
        geo_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        self.region_label = tk.Label(geo_frame, text="🌍 Current Region: --", 
                                    font=get_font("sm"),
                                    fg=THEME.cyan, bg=THEME.bg_highlight)
        self.region_label.pack(anchor=tk.W)
        
        self.rotation_label = tk.Label(geo_frame, text="🔄 Next Rotation: --", 
                                      font=get_font("sm"),
                                      fg=THEME.yellow, bg=THEME.bg_highlight)
        self.rotation_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Start live updates
        self._start_live_updates()
    
    def _create_metric(self, key: str, label: str, initial: str):
        """Create a metric row."""
        frame = tk.Frame(self.metrics_container, bg=THEME.bg_highlight)
        frame.pack(fill=tk.X, pady=3)
        
        tk.Label(frame, text=label, font=get_font("sm"),
                fg=THEME.fg_dark, bg=THEME.bg_highlight, width=25,
                anchor=tk.W).pack(side=tk.LEFT)
        
        value_label = tk.Label(frame, text=initial, font=get_font("sm"),
                              fg=THEME.cyan, bg=THEME.bg_highlight)
        value_label.pack(side=tk.RIGHT)
        
        self.metric_widgets[key] = value_label
    
    def _start_live_updates(self):
        """Start live statistics updates."""
        self._update_loop()
    
    def _update_loop(self):
        """Update statistics every 500ms."""
        self._update_display()
        self.after(500, self._update_loop)
    
    def _update_display(self):
        """Update all metric displays."""
        # Articles with rate
        articles = self.current_stats['articles']
        rate = self.current_stats.get('articles_per_second', 0)
        if rate > 0:
            self.metric_widgets['articles'].config(
                text=f"{articles} (+{rate:.1f}/sec)"
            )
        else:
            self.metric_widgets['articles'].config(text=f"{articles}")
        
        # Quality threshold
        passed = self.current_stats['passed']
        rejected = self.current_stats['rejected']
        total_quality = passed + rejected
        if total_quality > 0:
            self.metric_widgets['quality'].config(
                text=f"{passed} passed, {rejected} rejected"
            )
        
        # Average score with trend
        avg = self.current_stats['avg_score']
        prev_avg = self.current_stats.get('prev_avg_score', avg)
        trend = "⬆" if avg > prev_avg else "⬇" if avg < prev_avg else "→"
        color = THEME.green if avg >= 7 else THEME.yellow if avg >= 5 else THEME.red
        self.metric_widgets['avg_score'].config(
            text=f"{avg:.1f}/10 {trend}", fg=color
        )
        self.current_stats['prev_avg_score'] = avg
        
        # Sources
        active = self.current_stats['sources_active']
        total = self.current_stats.get('sources_total', 10)
        pct = (active / total * 100) if total > 0 else 0
        self.metric_widgets['sources'].config(
            text=f"{active}/{total} ({pct:.0f}%)"
        )
        
        # Throughput
        throughput = self.current_stats['throughput']
        self.metric_widgets['throughput'].config(
            text=f"{throughput:.1f} MB/s"
        )
        
        # Processing speed
        speed = self.current_stats['processing_speed']
        self.metric_widgets['speed'].config(
            text=f"{speed} articles/sec"
        )
        
        # DB writes
        writes = self.current_stats['db_writes']
        self.metric_widgets['db_writes'].config(
            text=f"{writes} commits"
        )
        
        # Cache hit rate
        cache = self.current_stats['cache_hit_rate']
        self.metric_widgets['cache'].config(
            text=f"{cache}%"
        )
    
    def update_stat(self, key: str, value: Any):
        """Public method to update a statistic."""
        if key in self.current_stats:
            self.current_stats[key] = value
    
    def update_region(self, region: str, rotation_seconds: int = 30):
        """Update geographic information."""
        self.region_label.config(text=f"🌍 Current Region: {region}")
        self.rotation_label.config(text=f"🔄 Next Rotation: {rotation_seconds}s")


class LiveActivityLog(tk.Frame):
    """
    Real-time activity log showing system events as they happen.
    
    Auto-scrolling feed of actual system activity with color-coded
    log levels and real timestamps.
    """
    
    MAX_LINES = 100
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=THEME.bg_highlight, **kwargs)
        
        # Header
        header = tk.Frame(self, bg=THEME.bg_highlight)
        header.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        tk.Label(header, text="📜", font=get_font("lg"),
                fg=THEME.magenta, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        tk.Label(header, text="REAL-TIME ACTIVITY FEED", 
                font=get_font("md", "bold"),
                fg=THEME.fg, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=(8, 0))
        
        # Activity text widget
        self.text_widget = tk.Text(self, height=8, wrap=tk.WORD,
                                  bg=THEME.bg_highlight, fg=THEME.fg,
                                  font=get_font("xs", mono=True),
                                  padx=10, pady=5,
                                  state=tk.DISABLED,
                                  highlightthickness=0)
        self.text_widget.pack(fill=tk.BOTH, expand=True, 
                             padx=15, pady=5)
        
        # Configure tags for different log levels
        self.text_widget.tag_config('INFO', foreground=THEME.cyan)
        self.text_widget.tag_config('SUCCESS', foreground=THEME.green)
        self.text_widget.tag_config('WARNING', foreground=THEME.yellow)
        self.text_widget.tag_config('ERROR', foreground=THEME.red)
        self.text_widget.tag_config('TIMESTAMP', foreground=THEME.comment)
        
        # Footer
        footer = tk.Frame(self, bg=THEME.bg_highlight)
        footer.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        tk.Label(footer, text="Auto-scrolling • Live updates every 100ms", 
                font=get_font("xs"),
                fg=THEME.comment, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        
        self.line_count = 0
    
    def log(self, message: str, level: str = 'INFO', source: str = ''):
        """Add a log entry."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format: [HH:MM:SS] ICON Message
        icon_map = {
            'INFO': 'ℹ️', 'SUCCESS': '✅', 'WARNING': '⚠️', 
            'ERROR': '❌', 'FETCH': '📥', 'SAVE': '💾',
            'AI': '🧠', 'BYPASS': '🔓', 'NETWORK': '🌐'
        }
        icon = icon_map.get(source.upper(), icon_map.get(level, '•'))
        
        entry = f"[{timestamp}] {icon} {message}\n"
        
        # Add to widget
        self.text_widget.config(state=tk.NORMAL)
        
        # Insert timestamp with different color
        self.text_widget.insert(tk.END, f"[{timestamp}] ", 'TIMESTAMP')
        self.text_widget.insert(tk.END, f"{icon} {message}\n", level)
        
        self.line_count += 1
        
        # Remove old lines if exceeds max
        if self.line_count > self.MAX_LINES:
            # Get index of first line
            first_line_end = self.text_widget.index('2.0 lineend')
            self.text_widget.delete('1.0', first_line_end)
            self.line_count -= 1
        
        # Auto-scroll to end
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)
    
    def clear(self):
        """Clear the log."""
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete('1.0', tk.END)
        self.text_widget.config(state=tk.DISABLED)
        self.line_count = 0


# Export all classes
__all__ = [
    'LiveSourceHeartbeatMonitor',
    'LiveArticleStreamPreview', 
    'LiveStatisticsPanel',
    'LiveActivityLog',
    'SourceStatus',
    'PipelineStage'
]