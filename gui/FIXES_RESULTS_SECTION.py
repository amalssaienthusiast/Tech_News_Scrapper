"""
Quick Fix Guide for GUI Results Section Issues

Apply these fixes to /Users/sci_coderamalamicia/PROJECTS/tech_news_scraper/gui/app.py
"""

# =============================================================================
# FIX 1: Remove Duplicate _matches_query Method
# =============================================================================
# DELETE the second definition at lines 1374-1387
# Keep only the first definition at lines 1283-1290

# =============================================================================
# FIX 2: Add Pagination to _display_realtime_results
# =============================================================================
# REPLACE the batch rendering code (lines 3109-3134) with this:

"""
OLD CODE (lines 3109-3134):
----------------------------
            batch_size = 20
            delay_ms = 50
            total = len(articles)

            def render_batch(start_index):
                if start_index >= total:
                    return
                end_index = min(start_index + batch_size, total)
                batch = articles[start_index:end_index]
                
                for article in batch:
                    self._create_article_card(article)
                
                self.root.after(delay_ms, lambda: render_batch(end_index))

            render_batch(0)

NEW CODE:
---------
            # PAGINATION: Only display first page initially
            self._all_articles = articles
            self._page_size = 20
            self._current_page = 0
            
            # Display first page only
            first_page = articles[:self._page_size]
            for article in first_page:
                self._create_article_card(article)
            
            # Add "Load More" button if there are more articles
            if len(articles) > self._page_size:
                self._add_load_more_button(len(articles) - self._page_size)
"""

# Add this helper method:
"""
def _add_load_more_button(self, remaining_count):
    \"\"\"Add a 'Load More' button for pagination.\"\"\"
    load_more_frame = tk.Frame(self.results_frame, bg=THEME.bg_card, padx=12, pady=8)
    load_more_frame.pack(fill=tk.X, pady=(8, 0))
    
    btn = tk.Button(
        load_more_frame,
        text=f"📥 Load More ({remaining_count} remaining)",
        font=get_font('sm', 'bold'),
        bg=THEME.blue,
        fg=THEME.fg,
        activebackground=THEME.bright_blue,
        relief=tk.FLAT,
        cursor='hand2',
        command=self._load_more_results
    )
    btn.pack(fill=tk.X, ipady=8)
    
    self._load_more_button = load_more_frame

def _load_more_results(self):
    \"\"\"Load next page of results.\"\"\"
    if hasattr(self, '_load_more_button'):
        self._load_more_button.destroy()
    
    start = self._current_page * self._page_size
    end = start + self._page_size
    
    next_page = self._all_articles[start:end]
    for article in next_page:
        self._create_article_card(article)
    
    self._current_page += 1
    
    # Add button again if more articles
    remaining = len(self._all_articles) - end
    if remaining > 0:
        self._add_load_more_button(remaining)
"""

# =============================================================================
# FIX 3: Fix Memory Leak in _clear_results
# =============================================================================
# REPLACE line 2594-2599 with:

"""
OLD CODE:
---------
    def _clear_results(self):
        \"\"\"Clear all article cards and reset tracking.\"\"\"
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        self.current_articles = []
        self._displayed_urls.clear()

NEW CODE:
---------
    def _clear_results(self):
        \"\"\"Clear all article cards and reset tracking.\"\"\"
        # Cancel any pending updates
        if hasattr(self, '_update_after_id') and self._update_after_id:
            self.root.after_cancel(self._update_after_id)
            self._update_after_id = None
        
        # Destroy widgets properly
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Clear all references
        self.current_articles.clear()
        self._displayed_urls.clear()
        
        # Reset pagination
        if hasattr(self, '_all_articles'):
            self._all_articles.clear()
        self._current_page = 0
        
        # Force garbage collection
        import gc
        gc.collect()
"""

# =============================================================================
# FIX 4: Fix Scroll Jump Issue
# =============================================================================
# REPLACE _update_scroll_region method (lines 3144-3157) with:

"""
OLD CODE:
---------
    def _update_scroll_region(self):
        try:
            if hasattr(self, 'results_canvas') and self.results_canvas.winfo_exists():
                self.results_canvas.update_idletasks()
                bbox = self.results_canvas.bbox("all")
                if bbox:
                    self.results_canvas.configure(scrollregion=bbox)
                self.results_canvas.yview_moveto(0)  # PROBLEM: Always scrolls to top!
        except Exception as e:
            logger.debug(f"Scroll region update error: {e}")

NEW CODE:
---------
    def _update_scroll_region(self, scroll_to_top=False):
        \"\"\"Update scroll region. Only scroll to top on initial load.\"\"\"
        try:
            if hasattr(self, 'results_canvas') and self.results_canvas.winfo_exists():
                bbox = self.results_canvas.bbox("all")
                if bbox:
                    self.results_canvas.configure(scrollregion=bbox)
                
                # Only scroll to top on initial load, not during streaming
                if scroll_to_top:
                    self.results_canvas.yview_moveto(0)
        except Exception as e:
            logger.debug(f"Scroll region update error: {e}")
"""

# =============================================================================
# FIX 5: Simplify _create_article_card (Reduce Widget Count)
# =============================================================================
# The current method creates 15+ widgets per card. Simplify it:

"""
KEY CHANGES:
1. Remove the recursive bind_recursive function (lines 3488-3493)
2. Remove complex score bar with multiple nested frames
3. Use simple labels instead of complex hierarchies
4. Remove unused widgets

EXAMPLE SIMPLIFIED CARD:
------------------------
    def _create_article_card(self, article):
        \"\"\"Create a simplified article card.\"\"\"
        # Main card frame - single level
        card = tk.Frame(
            self.results_frame,
            bg=THEME.bg_card,
            padx=12,
            pady=8,
            cursor='hand2'
        )
        card.pack(fill=tk.X, pady=2)
        
        # Store reference
        self._article_cards.append(card)
        
        # Row 1: Title (single label)
        title = article.get('title', 'Untitled')
        title_lbl = tk.Label(
            card,
            text=title[:120] + '...' if len(title) > 120 else title,
            font=get_font('sm', 'bold'),
            fg=THEME.fg,
            bg=THEME.bg_card,
            wraplength=550,
            justify=tk.LEFT,
            anchor=tk.W
        )
        title_lbl.pack(fill=tk.X, pady=(0, 4))
        
        # Row 2: Source | Time | Score (single frame, 3 labels)
        info_frame = tk.Frame(card, bg=THEME.bg_card)
        info_frame.pack(fill=tk.X)
        
        source = article.get('source', 'Unknown')
        tk.Label(
            info_frame,
            text=f"📰 {source}",
            font=get_font('xs'),
            fg=THEME.cyan,
            bg=THEME.bg_card
        ).pack(side=tk.LEFT)
        
        # Only show score if > 0
        score = article.get('tech_score', 0)
        if score > 0:
            score_color = THEME.green if score >= 8 else THEME.yellow if score >= 5 else THEME.red
            tk.Label(
                info_frame,
                text=f"⭐ {score:.1f}",
                font=get_font('xs', 'bold'),
                fg=score_color,
                bg=THEME.bg_card
            ).pack(side=tk.RIGHT)
        
        # Simple click handler
        def on_click(event, url=article.get('url')):
            import webbrowser
            webbrowser.open(url)
        
        # Bind only to card and title
        card.bind('<Button-1>', on_click)
        title_lbl.bind('<Button-1>', on_click)
"""

# =============================================================================
# FIX 6: Fix Race Condition in _init_app_logic
# =============================================================================
# Add a flag to prevent premature access:

"""
In _init_app_logic (around line 669), add:

    self._pipeline_ready = False
    
    def init_pipeline():
        try:
            self._pipeline = EnhancedNewsPipeline(...)
            # ... initialization code ...
            self._pipeline_ready = True  # Set flag when ready
            logger.info("✅ Pipeline ready")
        except Exception as e:
            logger.error(f"Pipeline init failed: {e}")
    
Then check flag before using pipeline:

    def _trigger_unified_live_feed(self):
        if not getattr(self, '_pipeline_ready', False):
            messagebox.showwarning("Not Ready", "Pipeline is still initializing. Please wait...")
            return
        # ... rest of method
"""

# =============================================================================
# FIX 7: Remove Duplicate Results Section Code
# =============================================================================
# The code you showed has the entire RESULTS SECTION duplicated.
# Delete the second copy (everything from the second occurrence of 
# "# ═══════════════════════════════════════════════════════════════
# # RESULTS SECTION" to the next section)

# =============================================================================
# USAGE: Import and Use Optimized Version
# =============================================================================

"""
# At the top of app.py, add:
from gui.optimized_results import create_optimized_results_section

# In _build_ui method, replace results section creation with:
results_section = create_optimized_results_section(left, THEME, get_font)
self.results_canvas = results_section['canvas']
self.results_frame = results_section['frame']
self._virtual_display = results_section['virtual_display']
self._article_feeder = results_section['feeder']

# To display articles:
self._article_feeder.feed_articles(articles, streaming=True)

# To clear:
self._article_feeder.clear()
self._virtual_display.clear()
"""
