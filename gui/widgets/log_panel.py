
import logging
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from gui.theme import THEME, get_font
from src.core.protocol import LogMessage

# Global thread-safe log buffer (shared throughout the app)
_log_buffer = []
_log_buffer_lock = threading.Lock()
_log_buffer_max_size = 100

class RealTimeLogHandler(logging.Handler):
    """Handler that pushes logs to a thread-safe buffer for GUI polling."""
    
    def emit(self, record):
        global _log_buffer
        try:
            log_msg = LogMessage(
                level=record.levelname, # Keep as string
                message=record.getMessage(),
                component=record.name
            )
            # Add to thread-safe buffer
            with _log_buffer_lock:
                _log_buffer.append(log_msg)
                # Trim buffer if too large
                if len(_log_buffer) > _log_buffer_max_size:
                    _log_buffer = _log_buffer[-_log_buffer_max_size:]
        except Exception:
            self.handleError(record)

class LiveLogPanel:
    """
    Real-time log monitoring panel.
    Comprehensive tracking of all system processes: feed cycles, bypass ops,
    scraping, article processing, and user actions.
    """
    
    # Process categories with their status indicators
    PROCESS_DEFS = [
        ("system", "⚙️ System", "Initializing..."),
        ("feed", "📡 Live Feed", "Waiting"),
        ("bypass", "🔓 Bypass", "Standby"),
        ("scraper", "🌐 Scraper", "Idle"),
        ("orch", "🔄 Processor", "Idle"),
    ]
    
    # Comprehensive keyword-to-state mapping
    STATE_PATTERNS = {
        # System states
        "eventbus started": ("system", "Event bus ready", True),
        "database schema initialized": ("system", "DB initialized", True),
        "loaded": ("system", "Data loaded", True),
        "orchestrator initialized": ("system", "Ready", True),
        "orchestrator shutting down": ("system", "Shutting down...", True),
        "shutdown complete": ("system", "Stopped", False),
        
        # Feed states
        "realtimenewsfeeder started": ("feed", "Active", True),
        "refreshing real-time": ("feed", "Refreshing...", True),
        "refresh complete": ("feed", "Monitoring", True),
        "realtimenewsfeeder stopped": ("feed", "Stopped", False),
        "background refresh": ("feed", "Auto-refresh", True),
        
        # Bypass states
        "attempting smart bypass": ("bypass", "Initiating...", True),
        "neural dom eraser": ("bypass", "DOM Eraser", True),
        "cloudflare bypass": ("bypass", "Cloudflare", True),
        "fullbypass": ("bypass", "Full Bypass", True),
        "bypass successful": ("bypass", "Success ✓", True),
        "bypass failed": ("bypass", "Failed", False),
        "content platform bypass": ("bypass", "Platform", True),
        "stealth browser": ("bypass", "Browser", True),
        "metered storage cleared": ("bypass", "Cleared", True),
        "mutation observer": ("bypass", "DOM Defense", True),
        "script blocking": ("bypass", "Scripts Blocked", True),
        "css scrubbing": ("bypass", "CSS Cleaned", True),
        
        # Scraper states
        "scraping source": ("scraper", "Fetching...", True),
        "scraping directory": ("scraper", "Scanning...", True),
        "bulk harvesting": ("scraper", "Harvesting...", True),
        "extracted": ("scraper", "Extracting", True),
        "headlines harvested": ("scraper", "Complete", True),
        "http 4": ("scraper", "Error 4xx", False),
        "http 5": ("scraper", "Error 5xx", False),
        "timeout": ("scraper", "Timeout", False),
        "crawl complete": ("scraper", "Done", False),
        
        # Processor/Orchestrator states
        "new article": ("orch", "New Article", True),
        "analyzing url": ("orch", "Analyzing...", True),
        "analyzing pre-fetched": ("orch", "Processing", True),
        "quality filter": ("orch", "Filtering", True),
        "searching:": ("orch", "Searching", True),
        "deep analysis": ("orch", "Deep Analysis", True),
    }
    
    def __init__(self, parent):
        self.parent = parent
        
        # Container
        self.frame = tk.Frame(parent, bg=THEME.bg_dark, width=340)
        self.frame.pack(side=tk.RIGHT, fill=tk.Y, padx=0, pady=0)
        self.frame.pack_propagate(False)
        
        # Tracking
        self.status_items = {}
        self.activity_feed = []
        self.max_feed_items = 50
        self.reset_timers = {}
        self._log_buffer_idx = 0  # Track read position in global log buffer
        
        self._build_ui()
        
        # Spinner animation
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_idx = 0
        self._animate_spinner()
        
        # Start polling the log buffer
        self._poll_log_buffer()
        
    def _build_ui(self):
        # Header with gradient effect
        header = tk.Frame(self.frame, bg=THEME.bg_visual, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        header_inner = tk.Frame(header, bg=THEME.bg_visual)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)
        
        tk.Label(header_inner, text="⚡", font=get_font("lg"),
                 fg=THEME.yellow, bg=THEME.bg_visual).pack(side=tk.LEFT)
        tk.Label(header_inner, text="LIVE MONITOR", font=get_font("sm", "bold"),
                 fg=THEME.fg, bg=THEME.bg_visual).pack(side=tk.LEFT, padx=8)
        
        # Online indicator
        self.online_dot = tk.Label(header_inner, text="●", font=get_font("xs"),
                                   fg=THEME.green, bg=THEME.bg_visual)
        self.online_dot.pack(side=tk.RIGHT)
        tk.Label(header_inner, text="LIVE", font=get_font("xs"),
                 fg=THEME.green, bg=THEME.bg_visual).pack(side=tk.RIGHT, padx=3)
        
        # Process Monitor Section
        monitor_label = tk.Frame(self.frame, bg=THEME.bg_dark)
        monitor_label.pack(fill=tk.X, padx=15, pady=(15, 5))
        tk.Label(monitor_label, text="SYSTEM PROCESSES", font=get_font("xs", "bold"),
                 fg=THEME.comment, bg=THEME.bg_dark).pack(anchor=tk.W)
        
        self.proc_frame = tk.Frame(self.frame, bg=THEME.bg_highlight, padx=12, pady=8)
        self.proc_frame.pack(fill=tk.X, padx=12, pady=5)
        
        # Create status items
        for key, label, initial in self.PROCESS_DEFS:
            self._add_status_item(key, label, initial)
        
        # Divider
        tk.Frame(self.frame, bg=THEME.border, height=1).pack(fill=tk.X, padx=15, pady=12)
        
        # Activity Feed Section
        feed_header = tk.Frame(self.frame, bg=THEME.bg_dark)
        feed_header.pack(fill=tk.X, padx=15, pady=(0, 5))
        tk.Label(feed_header, text="ACTIVITY LOG", font=get_font("xs", "bold"),
                 fg=THEME.comment, bg=THEME.bg_dark).pack(side=tk.LEFT)
        
        # Clear button
        clear_btn = tk.Label(feed_header, text="Clear", font=get_font("xs"),
                             fg=THEME.cyan, bg=THEME.bg_dark, cursor="hand2")
        clear_btn.pack(side=tk.RIGHT)
        clear_btn.bind("<Button-1>", lambda e: self._clear_logs())
        
        # Log terminal
        self.log_text = scrolledtext.ScrolledText(
            self.frame, font=get_font("xs", mono=True),
            bg="#0d0d14", fg=THEME.fg,
            wrap=tk.WORD, height=18, relief=tk.FLAT,
            highlightthickness=1, highlightbackground=THEME.bg_highlight,
            borderwidth=0, insertbackground=THEME.cyan
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        self.log_text.configure(state='disabled')
        
        # Configure color tags
        self.log_text.tag_config("INFO", foreground=THEME.fg)
        self.log_text.tag_config("WARNING", foreground=THEME.orange)
        self.log_text.tag_config("ERROR", foreground=THEME.red)
        self.log_text.tag_config("DEBUG", foreground=THEME.comment)
        self.log_text.tag_config("SUCCESS", foreground=THEME.green)
        self.log_text.tag_config("ACTION", foreground=THEME.cyan)
        self.log_text.tag_config("timestamp", foreground="#565f89")
        self.log_text.tag_config("component", foreground=THEME.magenta)

        # Initial message
        self._add_log_entry("System", "Live monitor initialized", "INFO")
        
    def _add_status_item(self, key, label, initial_state):
        frame = tk.Frame(self.proc_frame, bg=THEME.bg_highlight)
        frame.pack(fill=tk.X, pady=3)
        
        # Spinner/Dot
        icon = tk.Label(frame, text="●", font=("Menlo", 8),
                        fg=THEME.comment, bg=THEME.bg_highlight, width=2)
        icon.pack(side=tk.LEFT)
        
        # Label
        name_lbl = tk.Label(frame, text=label, font=get_font("xs"),
                            fg=THEME.fg_dark, bg=THEME.bg_highlight)
        name_lbl.pack(side=tk.LEFT, padx=5)
        
        # State badge
        state_lbl = tk.Label(frame, text=initial_state, font=get_font("xs"),
                             fg=THEME.comment, bg=THEME.bg_highlight)
        state_lbl.pack(side=tk.RIGHT)
        
        self.status_items[key] = {
            'frame': frame,
            'icon': icon,
            'state_lbl': state_lbl,
            'active': False,
            'last_update': 0
        }

    def update_status(self, key, state, active=False, auto_reset_ms=None):
        """Update process status with optional auto-reset."""
        if key not in self.status_items:
            return
        try:
            item = self.status_items[key]
            item['state_lbl'].config(text=state)
            item['active'] = active
            
            if active:
                item['state_lbl'].config(fg=THEME.cyan)
                item['icon'].config(fg=THEME.cyan)
            else:
                item['state_lbl'].config(fg=THEME.comment)
                item['icon'].config(text="●", fg=THEME.comment)
            
            # Cancel previous reset timer for this key
            if key in self.reset_timers:
                try:
                    self.frame.after_cancel(self.reset_timers[key])
                except Exception:
                    pass
            
            # Set auto-reset if requested
            if auto_reset_ms and active:
                self.reset_timers[key] = self.frame.after(
                    auto_reset_ms, 
                    lambda: self.update_status(key, "Idle", False)
                )
        except Exception:
            pass

    def log(self, message: LogMessage):
        """Thread-safe log handler."""
        try:
            self.parent.after(0, lambda: self._handle_log(message))
        except Exception:
            pass

    def _handle_log(self, message: LogMessage):
        """Process incoming log message."""
        try:
            msg = message.message
            component = message.component
            level = message.level
            
            # Determine log tag based on content
            tag = level
            msg_lower = msg.lower()
            
            if "success" in msg_lower or "complete" in msg_lower:
                tag = "SUCCESS"
            elif "bypass" in msg_lower or "analyzing" in msg_lower:
                tag = "ACTION"
            
            # Add to activity log
            self._add_log_entry(component, msg, tag)
            
            # Update status indicators
            self._update_indicators(msg_lower)
            
        except Exception:
            pass

    def _add_log_entry(self, component, msg, tag="INFO"):
        """Add entry to the activity log."""
        try:
            if not self.frame.winfo_exists():
                return
                
            self.log_text.configure(state='normal')
            
            # Timestamp
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"{ts} ", "timestamp")
            
            # Component (shortened)
            comp_short = component.split('.')[-1][:12].ljust(12) if component else "system".ljust(12)
            self.log_text.insert(tk.END, f"{comp_short} ", "component")
            
            # Message (truncated if too long)
            display_msg = msg[:80] + "..." if len(msg) > 80 else msg
            self.log_text.insert(tk.END, f"{display_msg}\n", tag)
            
            self.log_text.configure(state='disabled')
            self.log_text.see(tk.END)
            
            # Limit buffer size
            self.activity_feed.append((ts, component, msg))
            if len(self.activity_feed) > self.max_feed_items:
                self.activity_feed.pop(0)
                self._trim_log_buffer()
        except Exception:
            pass
    
    def _trim_log_buffer(self):
        """Remove oldest entries from log widget."""
        try:
            self.log_text.configure(state='normal')
            # Delete first line
            self.log_text.delete("1.0", "2.0")
            self.log_text.configure(state='disabled')
        except Exception:
            pass

    def _clear_logs(self):
        """Clear the log display."""
        try:
            self.log_text.configure(state='normal')
            self.log_text.delete("1.0", tk.END)
            self.log_text.configure(state='disabled')
            self.activity_feed.clear()
            self._add_log_entry("System", "Log cleared", "INFO")
        except Exception:
            pass
    
    def _update_indicators(self, msg_lower: str):
        """Update status indicators based on log message content."""
        try:
            for pattern, (key, state, active) in self.STATE_PATTERNS.items():
                if pattern in msg_lower:
                    # Determine auto-reset time based on process type
                    reset_ms = None
                    if key == "orch":
                        reset_ms = 2000  # Quick reset for processor
                    elif key == "bypass":
                        reset_ms = 3000  # Longer for bypass operations
                    elif key == "scraper" and active:
                        reset_ms = 5000  # Even longer for scraper
                    
                    self.update_status(key, state, active, reset_ms)
                    return
        except Exception:
            pass
             
    def _animate_spinner(self):
        """Animate active process spinners."""
        try:
            if not self.frame.winfo_exists():
                return
            
            char = self.spinner_chars[self.spinner_idx]
            self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_chars)
            
            for key, item in self.status_items.items():
                if item['active']:
                    item['icon'].config(text=char, fg=THEME.cyan)
            
            self.frame.after(100, self._animate_spinner)
        except Exception:
            pass

    def log_user_action(self, action: str):
        """Log a user-initiated action."""
        try:
            self._add_log_entry("user", f"Action: {action}", "ACTION")
        except Exception:
            pass

    def _poll_log_buffer(self):
        """Poll the global log buffer for new messages (thread-safe)."""
        try:
            if not self.frame.winfo_exists():
                return
            
            # Read new messages from shared buffer
            with _log_buffer_lock:
                buffer_len = len(_log_buffer)
                if self._log_buffer_idx < buffer_len:
                    # Get new messages since last read
                    new_messages = _log_buffer[self._log_buffer_idx:buffer_len]
                    self._log_buffer_idx = buffer_len
                else:
                    new_messages = []
            
            # Process new messages (outside lock)
            for log_msg in new_messages[:10]:  # Limit per poll
                self.log(log_msg)
            
            # Schedule next poll
            self.frame.after(50, self._poll_log_buffer)
        except Exception:
            pass
