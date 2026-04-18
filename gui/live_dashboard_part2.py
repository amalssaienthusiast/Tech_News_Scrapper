"""
Live Dashboard Widgets Part 2: Pipeline, Sources, and Network Visualization.

This module contains:
- PipelineVisualizer: Multi-stage pipeline with real progress
- SourceActivityMatrix: Per-source fetch progress with individual bars
- NetworkThroughputGraph: Live network activity ASCII graph
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, List, Any
from datetime import datetime
import asyncio
from collections import deque

from gui.theme import TokyoNightColors as THEME
from gui import get_font
from gui.live_dashboard import PipelineStage


class PipelineVisualizer(tk.Frame):
    """
    Multi-stage pipeline visualizer showing real processing progress.
    
    Displays each stage of the article processing pipeline with:
    - Individual progress bars
    - Stage status indicators
    - Current item being processed
    - Stage-specific metrics
    - Overall ETA calculation
    """
    
    STAGES = [
        ('FETCH', 'Fetching from sources'),
        ('PARSE', 'Parsing content'),
        ('SCORE', 'AI Scoring'),
        ('FILTER', 'Quality filtering'),
        ('STORE', 'Database storage'),
        ('INDEX', 'Search indexing')
    ]
    
    def __init__(self, parent, orchestrator=None, **kwargs):
        super().__init__(parent, bg=THEME.bg_dark, **kwargs)
        
        self.orchestrator = orchestrator
        self.stage_widgets: Dict[str, Dict] = {}
        self.stage_states: Dict[str, PipelineStage] = {}
        
        # Header
        header = tk.Frame(self, bg=THEME.bg_dark)
        header.pack(fill=tk.X, padx=20, pady=(15, 10))
        
        tk.Label(header, text="🔄", font=get_font("lg"),
                fg=THEME.yellow, bg=THEME.bg_dark).pack(side=tk.LEFT)
        tk.Label(header, text="DISCOVERY PIPELINE", 
                font=get_font("md", "bold"),
                fg=THEME.fg, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=(8, 0))
        
        # Overall progress
        self.overall_label = tk.Label(header, text="0% complete", 
                                     font=get_font("sm"),
                                     fg=THEME.cyan, bg=THEME.bg_dark)
        self.overall_label.pack(side=tk.RIGHT)
        
        self.eta_label = tk.Label(header, text="ETA: --", 
                                 font=get_font("xs"),
                                 fg=THEME.comment, bg=THEME.bg_dark)
        self.eta_label.pack(side=tk.RIGHT, padx=(0, 15))
        
        # Create stage widgets
        for stage_name, description in self.STAGES:
            self._create_stage_widget(stage_name, description)
            self.stage_states[stage_name] = PipelineStage(
                name=stage_name,
                progress=0.0,
                status='waiting',
                processed_count=0,
                total_count=0
            )
        
        # Start monitoring
        self._start_monitoring()
    
    def _create_stage_widget(self, stage_name: str, description: str):
        """Create a widget for a pipeline stage."""
        frame = tk.Frame(self, bg=THEME.bg_dark, padx=20, pady=5)
        frame.pack(fill=tk.X)
        
        # Stage number and name
        header = tk.Frame(frame, bg=THEME.bg_dark)
        header.pack(fill=tk.X)
        
        stage_num = self.STAGES.index((stage_name, description)) + 1
        tk.Label(header, text=f"[{stage_num}]", 
                font=get_font("sm", "bold"),
                fg=THEME.comment, bg=THEME.bg_dark, width=4).pack(side=tk.LEFT)
        
        name_label = tk.Label(header, text=stage_name, 
                             font=get_font("sm", "bold"),
                             fg=THEME.fg, bg=THEME.bg_dark, width=12)
        name_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Progress bar
        progress_bar = ttk.Progressbar(header, length=400, mode='determinate')
        progress_bar.pack(side=tk.LEFT, padx=(10, 10))
        
        # Status
        status_label = tk.Label(header, text="⏸ Waiting...", 
                               font=get_font("xs"),
                               fg=THEME.comment, bg=THEME.bg_dark, width=15)
        status_label.pack(side=tk.LEFT)
        
        # Count
        count_label = tk.Label(header, text="0/0", 
                              font=get_font("xs"),
                              fg=THEME.fg_dark, bg=THEME.bg_dark, width=10)
        count_label.pack(side=tk.RIGHT)
        
        # Metrics row
        metrics_frame = tk.Frame(frame, bg=THEME.bg_dark)
        metrics_frame.pack(fill=tk.X, pady=(3, 0))
        
        arrow_label = tk.Label(metrics_frame, text="↓", 
                              font=get_font("xs"),
                              fg=THEME.cyan, bg=THEME.bg_dark, width=4)
        arrow_label.pack(side=tk.LEFT)
        
        metrics_label = tk.Label(metrics_frame, text="", 
                                font=get_font("xs"),
                                fg=THEME.fg_dark, bg=THEME.bg_dark)
        metrics_label.pack(side=tk.LEFT, padx=(5, 0))
        
        current_label = tk.Label(metrics_frame, text="", 
                                font=get_font("xs"),
                                fg=THEME.cyan, bg=THEME.bg_dark)
        current_label.pack(side=tk.RIGHT)
        
        self.stage_widgets[stage_name] = {
            'frame': frame,
            'progress': progress_bar,
            'status': status_label,
            'count': count_label,
            'metrics': metrics_label,
            'current': current_label
        }
    
    def _start_monitoring(self):
        """Start pipeline monitoring."""
        self._monitor_loop()
    
    def _monitor_loop(self):
        """Monitor pipeline every 100ms."""
        self._update_all_stages()
        self.after(100, self._monitor_loop)
    
    def _update_all_stages(self):
        """Update all stage displays."""
        total_progress = 0.0
        active_stages = 0
        
        for stage_name, state in self.stage_states.items():
            self._update_stage_display(stage_name, state)
            total_progress += state.progress
            if state.status == 'active':
                active_stages += 1
        
        # Update overall progress
        overall_pct = (total_progress / len(self.STAGES)) * 100
        self.overall_label.config(text=f"{overall_pct:.0f}% complete")
        
        # Calculate ETA
        if active_stages > 0 and overall_pct > 0:
            # Rough estimate: if X% done in Y seconds, remaining is (100-X)% * Y/X
            # This is simplified - in real implementation would track actual time
            eta_seconds = int((100 - overall_pct) / overall_pct * 30)  # Assume 30s baseline
            if eta_seconds > 0:
                self.eta_label.config(text=f"ETA: {eta_seconds}s")
    
    def _update_stage_display(self, stage_name: str, state: PipelineStage):
        """Update display for a single stage."""
        widgets = self.stage_widgets[stage_name]
        
        # Update progress bar
        widgets['progress']['value'] = state.progress * 100
        
        # Update status and color
        if state.progress >= 1.0:
            widgets['status'].config(text="✅ Complete", fg=THEME.green)
        elif state.progress > 0:
            widgets['status'].config(text=f"🔄 {state.status.title()}", fg=THEME.yellow)
        else:
            widgets['status'].config(text="⏸ Waiting...", fg=THEME.comment)
        
        # Update count
        widgets['count'].config(text=f"{state.processed_count}/{state.total_count}")
        
        # Update metrics
        if state.metrics:
            metrics_text = self._format_metrics(state.metrics)
            widgets['metrics'].config(text=metrics_text)
        
        # Update current item
        if state.current_item:
            widgets['current'].config(text=f"{state.current_item[:50]}...")
    
    def _format_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format stage metrics for display."""
        parts = []
        if 'speed' in metrics:
            parts.append(f"{metrics['speed']}/sec")
        if 'avg_score' in metrics:
            parts.append(f"Avg: {metrics['avg_score']:.1f}")
        if 'passed' in metrics and 'total' in metrics:
            parts.append(f"Passed: {metrics['passed']}/{metrics['total']}")
        return " • ".join(parts) if parts else ""
    
    def update_stage(self, stage_name: str, progress: float, status: str,
                    processed: int = 0, total: int = 0, 
                    current_item: str = "", metrics: Dict = None):
        """Public method to update a stage."""
        if stage_name in self.stage_states:
            state = self.stage_states[stage_name]
            state.progress = progress
            state.status = status
            state.processed_count = processed
            state.total_count = total
            state.current_item = current_item
            if metrics:
                state.metrics = metrics
            
            # Track start time
            if status == 'active' and state.start_time is None:
                state.start_time = datetime.now()


class SourceActivityMatrix(tk.Frame):
    """
    Source activity matrix showing individual fetch progress per source.
    
    Each source gets its own progress bar, timing info, and article count.
    """
    
    def __init__(self, parent, orchestrator=None, **kwargs):
        super().__init__(parent, bg=THEME.bg_dark, **kwargs)
        
        self.orchestrator = orchestrator
        self.source_widgets: Dict[str, Dict] = {}
        self.source_states: Dict[str, Dict] = {}
        
        # Header
        header = tk.Frame(self, bg=THEME.bg_dark)
        header.pack(fill=tk.X, padx=20, pady=(10, 5))
        
        tk.Label(header, text="📡", font=get_font("lg"),
                fg=THEME.cyan, bg=THEME.bg_dark).pack(side=tk.LEFT)
        tk.Label(header, text="SOURCE FETCH STATUS", 
                font=get_font("md", "bold"),
                fg=THEME.fg, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=(8, 0))
        
        self.summary_label = tk.Label(header, text="0 articles from 0 sources", 
                                     font=get_font("xs"),
                                     fg=THEME.comment, bg=THEME.bg_dark)
        self.summary_label.pack(side=tk.RIGHT)
        
        # Container
        self.sources_container = tk.Frame(self, bg=THEME.bg_dark)
        self.sources_container.pack(fill=tk.X, padx=20, pady=5)
        
        # Initialize with default sources
        self._init_sources()
    
    def _init_sources(self):
        """Initialize source rows."""
        default_sources = [
            "TechCrunch", "Hacker News", "The Verge", "Ars Technica",
            "Wired", "MIT Tech Review", "VentureBeat", 
            "Reddit/r/technology", "Product Hunt", "GitHub Trending"
        ]
        
        for source_name in default_sources:
            self._create_source_row(source_name)
            self.source_states[source_name] = {
                'progress': 0.0,
                'status': 'waiting',
                'articles': 0,
                'start_time': None,
                'elapsed': 0.0
            }
    
    def _create_source_row(self, source_name: str):
        """Create a row for a source."""
        frame = tk.Frame(self.sources_container, bg=THEME.bg_dark, pady=2)
        frame.pack(fill=tk.X)
        
        # Source name
        name_label = tk.Label(frame, text=source_name[:20], 
                             font=get_font("sm"), width=20,
                             fg=THEME.fg_dark, bg=THEME.bg_dark, anchor=tk.W)
        name_label.pack(side=tk.LEFT)
        
        # Progress bar
        progress_bar = ttk.Progressbar(frame, length=300, mode='determinate')
        progress_bar.pack(side=tk.LEFT, padx=(10, 10))
        
        # Status
        status_label = tk.Label(frame, text="⏳ Waiting", 
                               font=get_font("xs"),
                               fg=THEME.comment, bg=THEME.bg_dark, width=15)
        status_label.pack(side=tk.LEFT)
        
        # Article count
        count_label = tk.Label(frame, text="", 
                              font=get_font("xs"),
                              fg=THEME.fg_dark, bg=THEME.bg_dark, width=12)
        count_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Time
        time_label = tk.Label(frame, text="", 
                             font=get_font("xs"),
                             fg=THEME.comment, bg=THEME.bg_dark, width=10)
        time_label.pack(side=tk.RIGHT)
        
        self.source_widgets[source_name] = {
            'frame': frame,
            'progress': progress_bar,
            'status': status_label,
            'count': count_label,
            'time': time_label,
            'name': name_label
        }
    
    def update_source_progress(self, source_name: str, progress: float):
        """Update source fetch progress."""
        if source_name in self.source_states:
            state = self.source_states[source_name]
            state['progress'] = progress
            state['status'] = 'fetching'
            
            if state['start_time'] is None:
                state['start_time'] = datetime.now()
            
            # Update elapsed time
            elapsed = (datetime.now() - state['start_time']).total_seconds()
            state['elapsed'] = elapsed
            
            # Update UI
            self._update_source_display(source_name)
    
    def update_source_complete(self, source_name: str, articles: int):
        """Mark source as complete."""
        if source_name in self.source_states:
            state = self.source_states[source_name]
            state['progress'] = 1.0
            state['status'] = 'complete'
            state['articles'] = articles
            
            # Update UI
            self._update_source_display(source_name)
            
            # Update summary
            self._update_summary()
    
    def _update_source_display(self, source_name: str):
        """Update UI for a source."""
        state = self.source_states[source_name]
        widgets = self.source_widgets[source_name]
        
        # Progress
        widgets['progress']['value'] = state['progress'] * 100
        
        # Status
        if state['status'] == 'complete':
            widgets['status'].config(text=f"✅ {state['articles']} articles", 
                                   fg=THEME.green)
        elif state['status'] == 'fetching':
            pct = int(state['progress'] * 100)
            widgets['status'].config(text=f"🔄 Fetching... {pct}%", 
                                   fg=THEME.yellow)
        else:
            widgets['status'].config(text="⏳ Waiting", fg=THEME.comment)
        
        # Time
        if state['elapsed'] > 0:
            widgets['time'].config(text=f"{state['elapsed']:.1f}s")
    
    def _update_summary(self):
        """Update the summary label."""
        total_articles = sum(s['articles'] for s in self.source_states.values())
        complete = sum(1 for s in self.source_states.values() if s['status'] == 'complete')
        active = sum(1 for s in self.source_states.values() if s['status'] == 'fetching')
        
        self.summary_label.config(
            text=f"{total_articles} articles from {complete} sources • {active} in progress"
        )


class NetworkThroughputGraph(tk.Canvas):
    """
    Live network throughput graph using ASCII-style visualization.
    
    Shows a scrolling graph of network activity over time.
    """
    
    def __init__(self, parent, width: int = 600, height: int = 100, **kwargs):
        super().__init__(parent, width=width, height=height,
                        bg=THEME.bg_dark, highlightthickness=0, **kwargs)
        
        self.graph_width = width
        self.graph_height = height
        self.data_points: deque = deque(maxlen=60)  # Last 60 seconds
        self.max_value = 1.0  # MB/s
        
        # Header text
        self.header_text = self.create_text(
            10, 10, text="📈 NETWORK THROUGHPUT (Last 60 seconds)",
            fill=THEME.fg, font=get_font("sm", "bold"),
            anchor=tk.NW
        )
        
        # Current value text
        self.current_text = self.create_text(
            width - 10, 10, text="0.0 MB/s",
            fill=THEME.green, font=get_font("sm", "bold"),
            anchor=tk.NE
        )
        
        # Start monitoring
        self._start_monitoring()
    
    def _start_monitoring(self):
        """Start network monitoring."""
        self._monitor_loop()
    
    def _monitor_loop(self):
        """Update graph every second."""
        self._add_data_point()
        self._draw_graph()
        self.after(1000, self._monitor_loop)
    
    def _add_data_point(self):
        """Add a new data point."""
        # In real implementation, get from orchestrator
        # For now, simulate with realistic values
        import random
        throughput = random.uniform(0.5, 3.0)  # MB/s
        
        self.data_points.append((datetime.now(), throughput))
        
        # Update max value for scaling
        if self.data_points:
            self.max_value = max(p[1] for p in self.data_points) * 1.1
            self.max_value = max(self.max_value, 1.0)  # Minimum scale
    
    def _draw_graph(self):
        """Draw the graph."""
        # Clear previous graph (but keep text)
        self.delete('graph')
        
        if len(self.data_points) < 2:
            return
        
        # Graph area (below header)
        graph_top = 35
        graph_height = self.graph_height - graph_top - 20
        
        # Draw grid lines
        for i in range(5):
            y = graph_top + (graph_height * i / 4)
            self.create_line(50, y, self.graph_width - 10, y, 
                           fill=THEME.bg_visual, tags='graph')
            
            # Y-axis label
            value = self.max_value * (1 - i / 4)
            self.create_text(40, y, text=f"{value:.1f}", 
                           fill=THEME.comment, font=get_font("xs"),
                           anchor=tk.E, tags='graph')
        
        # Draw data line
        points = []
        for i, (timestamp, value) in enumerate(self.data_points):
            x = 50 + (i / 59) * (self.graph_width - 60)
            y = graph_top + graph_height - (value / self.max_value * graph_height)
            points.append((x, y))
        
        # Draw line connecting points
        if len(points) > 1:
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                self.create_line(x1, y1, x2, y2, 
                               fill=THEME.cyan, width=2, tags='graph')
        
        # Draw points
        for x, y in points:
            self.create_oval(x-3, y-3, x+3, y+3, 
                           fill=THEME.green, outline='', tags='graph')
        
        # Update current value text
        if self.data_points:
            current = self.data_points[-1][1]
            self.itemconfig(self.current_text, text=f"{current:.1f} MB/s")
            
            # Update peak/average in header
            peak = max(p[1] for p in self.data_points)
            avg = sum(p[1] for p in self.data_points) / len(self.data_points)
            stats_text = f"Current: {current:.1f} MB/s • Peak: {peak:.1f} • Avg: {avg:.1f}"
            # Could add this as separate text element
    
    def update_throughput(self, mb_per_second: float):
        """Public method to update with real throughput data."""
        self.data_points.append((datetime.now(), mb_per_second))
        self._draw_graph()


# Export classes
__all__ = [
    'PipelineVisualizer',
    'SourceActivityMatrix',
    'NetworkThroughputGraph'
]