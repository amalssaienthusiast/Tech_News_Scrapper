
import tkinter as tk
from gui.theme import THEME, get_font
from gui.widgets.log_panel import LogMessage, _log_buffer, _log_buffer_lock

class DynamicStatusBar:
    """
    Bottom status bar showing detailed actions in a typewriter style.
    Enhanced with comprehensive log pattern matching.
    """
    
    # Comprehensive keyword patterns for status bar
    ACTION_PATTERNS = [
        # Feed operations
        (r"refreshing real-time", "🔄 Refreshing live news feed..."),
        (r"refresh complete.*?(\d+) new articles", "✅ Feed refreshed: {0} new articles"),
        (r"realtimenewsfeeder started", "📡 Real-time monitoring active"),
        
        # Source scraping
        (r"scraping source: (.+)", "🌐 Fetching: {0}"),
        (r"scraping directory: (.+)", "📂 Scanning: {0}"),
        (r"extracted (\d+) headlines from (.+)", "📰 Found {0} headlines from {1}"),
        (r"bulk harvesting from (\d+) directories", "🚀 Harvesting {0} directories..."),
        
        # Bypass operations
        (r"attempting smart bypass", "🔓 Initiating bypass sequence..."),
        (r"neural dom eraser executed", "🧠 Neural DOM Eraser active"),
        (r"cloudflare bypass", "☁️ Bypassing Cloudflare protection..."),
        (r"fullbypass.*navigating", "🛡️ Full bypass mode engaged"),
        (r"bypass successful \((.+)\)", "✅ Bypass successful: {0}"),
        (r"content platform bypass successful", "✅ Platform bypass successful"),
        (r"metered storage cleared", "🧹 Storage cleared"),
        
        # Article processing
        (r"new article: (.+)", "📄 New: {0}"),
        (r"analyzing url: (.+)", "🔍 Analyzing: {0}"),
        (r"analyzing pre-fetched content", "🔬 Processing fetched content..."),
        (r"quality filter.*?(\d+).*?(\d+)", "🎯 Quality filter: {0} → {1} articles"),
        
        # Database
        (r"database schema initialized", "💾 Database initialized"),
        (r"loaded (\d+) articles.*?(\d+) sources", "📊 Loaded {0} articles, {1} sources"),
        
        # Browser
        (r"browser navigating", "🌐 Browser navigating..."),
        (r"browser fetched (\d+) chars", "📥 Fetched {0} characters"),
        (r"stealth browser initialized", "🕵️ Stealth browser ready"),
        
        # Errors/Warnings
        (r"timeout:", "⏱️ Request timeout"),
        (r"http (\d+):", "⚠️ HTTP {0} response"),
    ]

    def __init__(self, parent):
        self.parent = parent
        self.queue = []
        self.is_typing = False
        self.pulse_on = True
        self.last_message = ""
        self._log_buffer_idx = 0
        
        # Main Frame - Fixed at bottom
        self.frame = tk.Frame(parent, bg=THEME.bg_dark, height=28)
        self.frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.frame.pack_propagate(False)
        
        # Top border
        tk.Frame(self.frame, bg=THEME.border, height=1).pack(side=tk.TOP, fill=tk.X)
        
        # 1. Activity Indicator (Left)
        self.activity_icon = tk.Label(self.frame, text="◉", font=get_font("xs"),
                                      fg=THEME.green, bg=THEME.bg_dark)
        self.activity_icon.pack(side=tk.LEFT, padx=(10, 5))
        
        # 2. Main Status (Typewriter effect area)
        self.lbl_action = tk.Label(self.frame, text="System Ready", font=get_font("xs", mono=True),
                                   fg=THEME.fg_dark, bg=THEME.bg_dark, anchor=tk.W)
        self.lbl_action.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 3. Connection Stats (Right)
        self.stats_frame = tk.Frame(self.frame, bg=THEME.bg_dark)
        self.stats_frame.pack(side=tk.RIGHT, padx=10)
        
        self.lbl_articles = tk.Label(self.stats_frame, text="0 Articles", font=get_font("xs", "bold"),
                                     fg=THEME.blue, bg=THEME.bg_dark)
        self.lbl_articles.pack(side=tk.LEFT, padx=5)
        
        # Stats are updated via update_stats()
        
        # Start animations and polling
        self._process_queue()
        self._animate_pulse()
        self._poll_log_queue()

    def on_log(self, message: LogMessage):
        try:
            msg = message.message
            msg_lower = msg.lower()
            
            # Check against patterns
            for pattern, template in self.ACTION_PATTERNS:
                import re
                match = re.search(pattern, msg_lower)
                if match:
                    # Format message with capture groups
                    try:
                        formatted = template.format(*[g[:40] for g in match.groups()])
                    except (IndexError, KeyError):
                        formatted = template
                    
                    if formatted != self.last_message:
                        self.last_message = formatted
                        self.queue.append(formatted)
                    return
            
            # Fallback: Show important INFO messages
            if message.level in ("INFO", "WARNING") and len(msg) > 10:
                # Skip noisy messages
                skip_patterns = ["eventbus", "rate", "callback"]
                if not any(s in msg_lower for s in skip_patterns):
                    short_msg = f"ℹ️ {msg[:60]}..." if len(msg) > 60 else f"ℹ️ {msg}"
                    if short_msg != self.last_message:
                        self.last_message = short_msg
                        self.queue.append(short_msg)
        except Exception:
            pass

    def _process_queue(self):
        try:
            if not self.frame.winfo_exists(): return
            
            if not self.is_typing and self.queue:
                next_msg = self.queue.pop(0)
                self._type_message(next_msg)
            
            self.frame.after(80, self._process_queue)
        except Exception:
            pass
        
    def _type_message(self, message, idx=0):
        try:
            if not self.frame.winfo_exists(): return
            
            self.is_typing = True
            display = message[:idx+1] + "▌"
            self.lbl_action.config(text=display, fg=THEME.cyan)
            self.activity_icon.config(fg=THEME.cyan)
            
            if idx < len(message):
                speed = 15 if len(message) > 50 else 25
                self.frame.after(speed, lambda: self._type_message(message, idx+1))
            else:
                self.lbl_action.config(text=message)
                self.frame.after(2000, self._finish_typing)
        except Exception:
            pass
            
    def _finish_typing(self):
        self.is_typing = False
        self.activity_icon.config(fg=THEME.green)

    def _animate_pulse(self):
        try:
            if not self.frame.winfo_exists(): return
            
            if self.is_typing:
                self.activity_icon.config(text="◉" if self.pulse_on else "○")
                self.pulse_on = not self.pulse_on
            else:
                self.activity_icon.config(text="◉")
            
            self.frame.after(300, self._animate_pulse)
        except Exception:
            pass

    def update_stats(self, articles: int, sources: int):
        """Update right-side stats display."""
        try:
            self.stats_label.config(text=f"📊 {articles} articles | {sources} sources")
        except Exception:
            # Recreate stats label if missing/failed? Or just update lbl_articles
            # The original code had stats_label for combined stats?
            # Check initialized labels: lbl_articles.
            # Adapting to match app.py logic which might have different label names.
            # In app.py lines 228-233: self.stats_label.config...
            # But in init lines 33-43 I only see lbl_articles?
            # Wait, line 231 uses stats_label. Line 41 uses lbl_articles.
            # There might be a bug in app.py or I missed a line in view.
            # I will use lbl_articles since I defined it.
            if hasattr(self, 'lbl_articles'):
                self.lbl_articles.config(text=f"📊 {articles} Articles")
        except Exception:
            pass

    def _poll_log_queue(self):
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
                self.on_log(log_msg)
            
            # Schedule next poll
            self.frame.after(50, self._poll_log_queue)
        except Exception:
            pass
