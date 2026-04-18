"""
CRITICAL SEARCH FIXES - Apply These Immediately

These are the minimal changes needed to fix the search functionality.
"""

# =============================================================================
# FIX 1: Delete Duplicate _matches_query (LINES 1374-1387)
# =============================================================================
# In gui/app.py, delete lines 1374-1387 completely:
#     def _matches_query(self, article, query: str) -> bool:  # DUPLICATE - Removed, see line ~1180
# #         """Check if article matches current search query."""
# #         if not query:
# #             return False
#         try:
#             query_lower = query.lower()
#             title = getattr(article, 'title', '') or ''
#             summary = getattr(article, 'summary', '') or ''
#             source = getattr(article, 'source', '') or ''
#             searchable = (title + summary + source).lower()
#             return query_lower in searchable
#         except Exception as e:
#             logger.error(f"Error in _matches_query: {e}")
#             return False

# =============================================================================
# FIX 2: Update _matches_query to handle missing attributes (LINE 1283)
# =============================================================================
# REPLACE lines 1283-1290 with:

def _matches_query(self, article, query: str) -> bool:
    """Check if article matches search query."""
    if not query:
        return True
    
    try:
        q = query.lower()
        
        # Safely get attributes (handles missing/None values)
        title = (getattr(article, 'title', '') or '').lower()
        summary = (getattr(article, 'summary', '') or '').lower()
        source = (getattr(article, 'source', '') or '').lower()
        
        return q in title or q in summary or q in source
        
    except Exception as e:
        logger.error(f"Error in _matches_query: {e}")
        return False

# =============================================================================
# FIX 3: Add debouncing to search (in __init__ around line 150)
# =============================================================================
# Add these lines to __init__:
"""
self._search_after_id = None
self._search_debounce_ms = 300  # 300ms debounce
"""

# =============================================================================
# FIX 4: Replace _on_search with debounced version (around line 1240)
# =============================================================================
# REPLACE the _on_search method with:

def _on_search(self, event=None):
    """Handle search with debouncing."""
    # Cancel previous pending search
    if self._search_after_id:
        self.root.after_cancel(self._search_after_id)
    
    # Schedule new search after debounce delay
    self._search_after_id = self.root.after(
        self._search_debounce_ms,
        self._execute_search
    )

def _execute_search(self):
    """Execute the actual search."""
    query = self.search_entry.get().strip()
    
    # Handle empty query
    if not query or query == "Search tech news...":
        if self._search_mode:
            self._search_mode = False
            self._current_query = ""
            self._clear_results()
            
            # Show first page only (not all articles)
            for article in self.current_articles[:self._page_size]:
                self._create_article_card(article)
            
            self._set_status("🔴 Live Feed Restored", "info")
            self.results_count.config(text=f"({len(self.current_articles)} articles)")
        return
    
    # Check if articles are loaded
    if not self.current_articles:
        self._show_empty_state("No articles loaded yet. Start the live feed to load articles.")
        self._set_status("⏳ No articles loaded", "warning")
        return
    
    # Perform search
    self._search_mode = True
    self._current_query = query.lower()
    
    # Filter articles
    matches = [a for a in self.current_articles if self._matches_query(a, query)]
    
    # Display results
    self._clear_results()
    
    if matches:
        # Show header
        header = tk.Frame(self.results_frame, bg=THEME.bg_visual, padx=15, pady=10)
        header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(header, text="🔍", font=get_font("lg"),
                 fg=THEME.cyan, bg=THEME.bg_visual).pack(side=tk.LEFT)
        tk.Label(header, text=f"Results for '{query}'", font=get_font("md", "bold"),
                 fg=THEME.fg, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(header, text=f"{len(matches)} matches", font=get_font("sm"),
                 fg=THEME.comment, bg=THEME.bg_visual).pack(side=tk.RIGHT)
        
        # Show first page only
        for article in matches[:self._page_size]:
            self._create_article_card(article)
        
        self._set_status(f"🔍 Found {len(matches)} matches", "success")
    else:
        self._show_empty_state(f"No articles match '{query}'")
        self._set_status(f"🔍 No results for '{query}'", "warning")

# =============================================================================
# FIX 5: Remove scroll to top in _display_results (line ~1367)
# =============================================================================
# Find this line in _display_results:
#     self.results_canvas.yview_moveto(0)
# 
# DELETE or comment it out - it shouldn't scroll to top

# =============================================================================
# FIX 6: Change search entry binding (in _build_ui around line 280)
# =============================================================================
# Find where search_entry is created and change the binding:
# FROM:
#     self.search_entry.bind('<Key>', self._on_search)
# TO:
#     self.search_entry.bind('<KeyRelease>', self._on_search)
#     # Or better yet, add a search button:
#     search_btn = tk.Button(..., command=self._execute_search)

# =============================================================================
# SUMMARY OF CHANGES
# =============================================================================
"""
1. DELETE duplicate _matches_query (lines 1374-1387)
2. UPDATE _matches_query to handle missing attributes safely
3. ADD debounce timer to __init__
4. REPLACE _on_search with debounced version
5. REMOVE scroll to top in _display_results
6. CHANGE search binding from '<Key>' to '<KeyRelease>'

These changes will:
- Fix the "functionality not accurate" issue
- Prevent crashes from missing article attributes
- Make search responsive (300ms debounce)
- Keep scroll position (no jump to top)
- Only show first 20 results (pagination)
"""
