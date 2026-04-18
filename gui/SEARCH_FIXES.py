"""
Search Functionality Fixes for GUI App

Issues Found:
1. DUPLICATE _matches_query method (lines 1283 and 1374)
2. Local search doesn't work when articles haven't loaded yet
3. No debouncing - searches on every keystroke (inefficient)
4. Recreates ALL widgets on every search (slow)
5. Article attribute access errors (summary might not exist)
6. Scrolls to top every time (annoying UX)
"""

# =============================================================================
# FIX 1: Remove Duplicate _matches_query (CRITICAL)
# =============================================================================

# DELETE lines 1374-1387 (the duplicate commented method)
# Keep only the first definition at lines 1283-1290

# =============================================================================
# FIX 2: Safe Article Attribute Access
# =============================================================================

# REPLACE the _matches_query method (line 1283-1290) with this safer version:

def _matches_query(self, article, query: str) -> bool:
    """
    Check if article matches search query.
    
    Safely handles missing attributes and None values.
    """
    if not query:
        return True
    
    try:
        q = query.lower()
        
        # Safely get attributes with fallbacks
        title = getattr(article, 'title', '') or ''
        summary = getattr(article, 'summary', '') or ''
        source = getattr(article, 'source', '') or ''
        full_content = getattr(article, 'full_content', '') or ''
        
        # Search in all text fields
        searchable_text = f"{title} {summary} {source} {full_content}".lower()
        
        return q in searchable_text
        
    except Exception as e:
        logger.error(f"Error matching article '{getattr(article, 'title', 'Unknown')}': {e}")
        return False


# =============================================================================
# FIX 3: Add Search Debouncing
# =============================================================================

# Add these to your class __init__ method:
"""
self._search_after_id = None  # For debouncing
self._last_search_time = 0
self._search_debounce_ms = 300  # Wait 300ms after last keystroke
"""

# REPLACE _on_search method with debounced version:

def _on_search(self, event=None):
    """
    Handle search with debouncing.
    
    Waits for user to stop typing before executing search.
    """
    # Cancel previous pending search
    if self._search_after_id:
        self.root.after_cancel(self._search_after_id)
        self._search_after_id = None
    
    # Schedule new search after debounce delay
    self._search_after_id = self.root.after(
        self._search_debounce_ms,
        self._execute_search
    )

def _execute_search(self):
    """Actually perform the search (called after debounce)."""
    query = self.search_entry.get().strip()
    
    # Handle empty/placeholder query - restore full list
    if not query or query == "Search tech news...":
        self._restore_full_list()
        return
    
    # Check if articles are loaded
    if not self.current_articles:
        self._show_empty_state(message="No articles loaded yet. Please wait for the feed to load or start a search.")
        self._set_status("⏳ Waiting for articles to load...", "warning")
        return
    
    # Enter search mode
    self._search_mode = True
    self._current_query = query.lower()
    self._pending_updates.clear()
    self._hide_toast()
    
    # Show loading indicator
    self._set_status(f"🔍 Searching for '{query}'...", "info")
    self.root.update_idletasks()  # Force UI update
    
    # Filter existing articles LOCALLY
    matches = []
    for article in self.current_articles:
        if self._matches_query(article, query):
            matches.append(article)
    
    # Display results
    self._display_search_results(matches, query)


def _restore_full_list(self):
    """Restore the full article list (exit search mode)."""
    if self._search_mode:
        self._search_mode = False
        self._current_query = ""
        
        # Clear and restore
        self._clear_results()
        
        # Use efficient batch display
        self._display_articles_batch(self.current_articles[:self._page_size])
        
        self._set_status("🔴 Live Feed Restored", "info")
        self.results_count.config(text=f"({len(self.current_articles)} articles)")


def _display_search_results(self, matches: list, query: str):
    """Display search results efficiently."""
    # Clear current display
    self._clear_results()
    
    if matches:
        # Show results header
        header = tk.Frame(self.results_frame, bg=THEME.bg_visual, padx=15, pady=10)
        header.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(header, text="🔍", font=get_font("lg"),
                 fg=THEME.cyan, bg=THEME.bg_visual).pack(side=tk.LEFT)
        tk.Label(header, text=f"Search Results for '{query}'", font=get_font("md", "bold"),
                 fg=THEME.fg, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(header, text=f"{len(matches)} matches", font=get_font("sm"),
                 fg=THEME.comment, bg=THEME.bg_visual).pack(side=tk.RIGHT)
        
        # Display matching articles (first page only)
        display_count = min(len(matches), self._page_size)
        for article in matches[:display_count]:
            self._create_article_card(article)
        
        # Add "Show More" button if needed
        if len(matches) > self._page_size:
            self._add_show_more_button(matches[self._page_size:], query)
        
        self._set_status(f"🔍 Found {len(matches)} articles matching '{query}'", "success")
        self.results_count.config(text=f"({len(matches)} filtered)")
    else:
        # No matches
        self._show_empty_state(message=f"No articles match '{query}'")
        self._set_status(f"🔍 No results for '{query}'", "warning")
        self.results_count.config(text="(0 matches)")
    
    # Update scroll region but DON'T scroll to top
    self.root.after_idle(self._update_scroll_region)


def _add_show_more_button(self, remaining_articles: list, query: str):
    """Add 'Show More' button for additional search results."""
    btn_frame = tk.Frame(self.results_frame, bg=THEME.bg_card, padx=12, pady=8)
    btn_frame.pack(fill=tk.X, pady=(8, 0))
    
    remaining_count = len(remaining_articles)
    
    btn = tk.Button(
        btn_frame,
        text=f"📥 Show More Results ({remaining_count} remaining)",
        font=get_font('sm', 'bold'),
        bg=THEME.blue,
        fg=THEME.fg,
        activebackground=THEME.bright_blue,
        relief=tk.FLAT,
        cursor='hand2',
        command=lambda: self._show_more_results(remaining_articles, btn_frame)
    )
    btn.pack(fill=tk.X, ipady=8)


def _show_more_results(self, articles: list, button_frame: tk.Frame):
    """Display more search results."""
    # Remove button
    button_frame.destroy()
    
    # Display next batch
    for article in articles[:self._page_size]:
        self._create_article_card(article)
    
    # Add button again if more remain
    remaining = articles[self._page_size:]
    if remaining:
        self._add_show_more_button(remaining, self._current_query)
    
    # Update scroll region
    self.root.after_idle(self._update_scroll_region)


# =============================================================================
# FIX 4: Efficient Batch Display
# =============================================================================

def _display_articles_batch(self, articles: list, start_index: int = 0):
    """
    Display articles in batches to prevent UI freezing.
    
    Args:
        articles: List of articles to display
        start_index: Starting index in the list
    """
    batch_size = 10
    delay_ms = 50
    total = len(articles)
    
    def render_batch(index):
        if index >= total:
            return
        
        end_index = min(index + batch_size, total)
        batch = articles[index:end_index]
        
        for article in batch:
            try:
                self._create_article_card(article)
            except Exception as e:
                logger.error(f"Error creating card for '{getattr(article, 'title', 'Unknown')}': {e}")
        
        # Schedule next batch
        if end_index < total:
            self.root.after(delay_ms, lambda: render_batch(end_index))
        else:
            # Done - update scroll region
            self.root.after_idle(self._update_scroll_region)
    
    # Start rendering
    render_batch(start_index)


# =============================================================================
# FIX 5: Better Empty State
# =============================================================================

def _show_empty_state(self, message: str = "No articles found", suggestion: str = None):
    """Show empty state with optional suggestion."""
    # Clear existing
    self._clear_results()
    
    # Create empty state frame
    empty_frame = tk.Frame(self.results_frame, bg=THEME.bg_highlight, padx=30, pady=40)
    empty_frame.pack(fill=tk.BOTH, expand=True)
    
    # Icon
    tk.Label(empty_frame, text="📂", font=get_font("3xl"),
             fg=THEME.comment, bg=THEME.bg_highlight).pack()
    
    # Message
    tk.Label(empty_frame, text=message, font=get_font("lg"),
             fg=THEME.fg_dark, bg=THEME.bg_highlight).pack(pady=(15, 5))
    
    # Optional suggestion
    if suggestion:
        tk.Label(empty_frame, text=suggestion, font=get_font("sm"),
                 fg=THEME.comment, bg=THEME.bg_highlight,
                 wraplength=500, justify=tk.CENTER).pack(pady=(5, 0))
    
    # Action button for common actions
    if not self.current_articles:
        btn_frame = tk.Frame(empty_frame, bg=THEME.bg_highlight)
        btn_frame.pack(pady=(20, 0))
        
        tk.Button(
            btn_frame,
            text="🚀 Start Live Feed",
            font=get_font("sm", "bold"),
            bg=THEME.green,
            fg=THEME.black,
            relief=tk.FLAT,
            cursor='hand2',
            command=self._trigger_unified_live_feed
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="🔍 Global Search",
            font=get_font("sm", "bold"),
            bg=THEME.blue,
            fg=THEME.fg,
            relief=tk.FLAT,
            cursor='hand2',
            command=self._trigger_global_search
        ).pack(side=tk.LEFT, padx=5)


# =============================================================================
# FIX 6: Bind Search to Key Release Event
# =============================================================================

# In your _build_ui or search entry creation, add:
"""
self.search_entry.bind('<KeyRelease>', self._on_search)
# Remove any '<Key>' or '<KeyPress>' bindings if they exist
"""


# =============================================================================
# FIX 7: Add Network Search Option
# =============================================================================

def _trigger_global_search(self):
    """
    Trigger a global network search (not just local filtering).
    
    This fetches new articles from the web based on the search query.
    """
    query = self.search_entry.get().strip()
    
    if not query or query == "Search tech news...":
        messagebox.showwarning("No Query", "Please enter a search term.")
        return
    
    # Show loading state
    self._set_status(f"🌐 Searching globally for '{query}'...", "info")
    self._clear_results()
    
    # Show searching indicator
    searching_frame = tk.Frame(self.results_frame, bg=THEME.bg_highlight, padx=30, pady=40)
    searching_frame.pack(fill=tk.BOTH, expand=True)
    
    tk.Label(searching_frame, text="🔍", font=get_font("3xl"),
             fg=THEME.cyan, bg=THEME.bg_highlight).pack()
    tk.Label(searching_frame, text=f"Searching for '{query}'...", font=get_font("lg"),
             fg=THEME.fg_dark, bg=THEME.bg_highlight).pack(pady=(15, 5))
    tk.Label(searching_frame, text="This may take a moment", font=get_font("sm"),
             fg=THEME.comment, bg=THEME.bg_highlight).pack()
    
    # Run search in background
    def do_search():
        try:
            # Use the orchestrator to search
            if self._orchestrator:
                result = self._async_runner.run_sync(
                    self._orchestrator.search_news(query)
                )
                
                # Update UI in main thread
                self.root.after(0, lambda: self._handle_global_results(result, query))
            else:
                self.root.after(0, lambda: self._show_error("Orchestrator not ready"))
        except Exception as e:
            self.root.after(0, lambda: self._show_error(f"Search failed: {str(e)}"))
    
    # Run in thread
    import threading
    threading.Thread(target=do_search, daemon=True).start()


def _handle_global_results(self, result, query: str):
    """Handle results from global search."""
    if result and result.articles:
        # Add to current articles
        for article in result.articles:
            if article.url not in self._displayed_urls:
                self._displayed_urls.add(article.url)
                self.current_articles.append(article)
        
        # Display results
        self._display_search_results(result.articles, query)
        self._set_status(f"✅ Found {len(result.articles)} articles globally", "success")
    else:
        self._show_empty_state(
            message=f"No articles found for '{query}'",
            suggestion="Try different keywords or check your internet connection."
        )
        self._set_status(f"❌ No global results for '{query}'", "warning")
