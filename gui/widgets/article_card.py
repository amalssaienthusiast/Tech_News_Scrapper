
import tkinter as tk
import webbrowser
from datetime import datetime
from gui.theme import THEME, get_font

class ArticleCard(tk.Frame):
    """
    A card component representing a single news article.
    """
    def __init__(self, parent, article, on_click_analyze=None, on_click_source=None):
        super().__init__(parent, bg=THEME.bg_highlight, padx=15, pady=12)
        self.article = article
        self.on_click_analyze = on_click_analyze
        self.on_click_source = on_click_source
        
        self._build_ui()
        
    def _build_ui(self):
        # Top Row: Source & Time
        top_row = tk.Frame(self, bg=THEME.bg_highlight)
        top_row.pack(fill=tk.X, pady=(0, 6))
        
        # Source Badge
        tier_color = THEME.cyan # Default
        if hasattr(self.article, 'source_tier'):
            if self.article.source_tier == 1: tier_color = THEME.green
            elif self.article.source_tier == 2: tier_color = THEME.blue
            
        source_badge = tk.Label(top_row, text=self.article.source.upper(), 
                               font=get_font("xs", "bold"), fg=THEME.bg_dark, bg=tier_color)
        source_badge.pack(side=tk.LEFT, padx=(0, 8), ipadx=6, ipady=1)
        
        # Time
        time_text = self._format_time(self.article.published_at)
        tk.Label(top_row, text=time_text, font=get_font("xs"),
                 fg=THEME.comment, bg=THEME.bg_highlight).pack(side=tk.LEFT)
                 
        # Tech Score (Right)
        if hasattr(self.article, 'tech_score') and self.article.tech_score:
            score = int(self.article.tech_score.score * 100)
            score_color = THEME.green if score > 80 else (THEME.yellow if score > 50 else THEME.comment)
            tk.Label(top_row, text=f"Tech Score: {score}", font=get_font("xs", "bold"),
                     fg=score_color, bg=THEME.bg_highlight).pack(side=tk.RIGHT)

        # Title
        title = tk.Label(self, text=self.article.title, font=get_font("lg", "bold"),
                         fg=THEME.fg, bg=THEME.bg_highlight, justify=tk.LEFT, wraplength=700, anchor=tk.W)
        title.pack(fill=tk.X, pady=(0, 6))
        
        if self.on_click_source:
             title.bind("<Button-1>", lambda e: self.on_click_source(self.article.url))
             title.config(cursor="hand2")

        # Summary (truncated)
        if self.article.summary:
            summary_text = self.article.summary[:200] + "..." if len(self.article.summary) > 200 else self.article.summary
            tk.Label(self, text=summary_text, font=get_font("sm"),
                     fg=THEME.fg_dark, bg=THEME.bg_highlight, justify=tk.LEFT, wraplength=700, anchor=tk.W).pack(fill=tk.X, pady=(0, 10))

        # Action Bar
        actions = tk.Frame(self, bg=THEME.bg_highlight)
        actions.pack(fill=tk.X)
        
        # Analyze Button
        if self.on_click_analyze:
            btn = tk.Button(actions, text="🔍 Analysis & Full Content", font=get_font("xs", "bold"),
                           fg=THEME.cyan, bg=THEME.bg_highlight, activeforeground=THEME.fg,
                           activebackground=THEME.bg_visual, borderwidth=0, cursor="hand2",
                           command=lambda: self.on_click_analyze(self.article))
            btn.pack(side=tk.LEFT)
            
        # Read Original Button
        if self.on_click_source:
            btn = tk.Button(actions, text="↗ Read Original", font=get_font("xs", "bold"),
                           fg=THEME.comment, bg=THEME.bg_highlight, activeforeground=THEME.fg,
                           activebackground=THEME.bg_visual, borderwidth=0, cursor="hand2",
                           command=lambda: self.on_click_source(self.article.url))
            btn.pack(side=tk.RIGHT)

    def _format_time(self, dt):
        if not dt: return ""
        if isinstance(dt, str): return dt
        now = datetime.now(dt.tzinfo)
        diff = now - dt
        if diff.days > 0:
            return dt.strftime("%b %d")
        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = diff.seconds // 60
        return f"{minutes}m ago"
