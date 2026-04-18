
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import webbrowser
import logging
from gui.theme import THEME, get_font
from src.bypass import ContentPlatform

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


class URLAnalysisPopup:
    """Popup window for analyzing custom URLs with bypass support - Tokyo Night themed."""
    
    def __init__(self, parent, url: str, orchestrator, async_runner):
        self.parent = parent
        self.url = url
        self.orchestrator = orchestrator
        self.async_runner = async_runner
        self.bypass_method_used = None
        
        # Initialize bypass handlers
        self.anti_bot = AntiBotBypass() if BYPASS_AVAILABLE else None
        self.paywall_bypass = PaywallBypass() if BYPASS_AVAILABLE else None
        self.content_platform_bypass = ContentPlatformBypass() if BYPASS_AVAILABLE else None
        
        self.window = tk.Toplevel(parent)
        self.window.title("🔗 URL Analysis")
        self.window.geometry("1050x850")
        self.window.configure(bg=THEME.bg)
        self.window.transient(parent)
        self.window.grab_set()
        
        self._build_ui()
        self._analyze_url()
    
    def _build_ui(self):
        # Header
        header = tk.Frame(self.window, bg=THEME.bg_dark, height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Frame(header, bg=THEME.magenta, height=3).pack(fill=tk.X, side=tk.TOP)
        
        header_inner = tk.Frame(header, bg=THEME.bg_dark)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=20)
        
        tk.Label(header_inner, text="🔗", font=get_font("xl"),
                 fg=THEME.magenta, bg=THEME.bg_dark).pack(side=tk.LEFT, pady=12)
        tk.Label(header_inner, text="CUSTOM URL ANALYSIS", font=get_font("lg", "bold"),
                 fg=THEME.fg, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=(8, 0), pady=12)
        
        self.bypass_indicator = tk.Label(header_inner, text="", font=get_font("sm"),
                                          fg=THEME.green, bg=THEME.bg_dark)
        self.bypass_indicator.pack(side=tk.RIGHT, pady=12)
        
        # URL display bar
        url_frame = tk.Frame(self.window, bg=THEME.bg_highlight, padx=20, pady=12)
        url_frame.pack(fill=tk.X)
        
        tk.Label(url_frame, text="📎 URL:", font=get_font("sm", "bold"),
                 fg=THEME.fg_dark, bg=THEME.bg_highlight).pack(side=tk.LEFT)
        
        url_display = tk.Label(url_frame, text=self.url[:80] + "..." if len(self.url) > 80 else self.url,
                                font=get_font("sm"), fg=THEME.blue, bg=THEME.bg_highlight, cursor='hand2')
        url_display.pack(side=tk.LEFT, padx=(8, 0))
        url_display.bind('<Button-1>', lambda e: webbrowser.open(self.url))
        
        # Content area
        content = tk.Frame(self.window, bg=THEME.bg, padx=25, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Title area
        self.title_label = tk.Label(content, text="⏳ Loading...", font=get_font("xl", "bold"),
                                     fg=THEME.fg, bg=THEME.bg, wraplength=950, justify=tk.LEFT)
        self.title_label.pack(anchor=tk.W, pady=(0, 12))
        
        # Meta info bar
        self.meta_frame = tk.Frame(content, bg=THEME.bg_visual, padx=15, pady=12)
        self.meta_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.meta_labels = {}
        meta_items = [
            ('📊 Score', 'score', THEME.green),
            ('📰 Source', 'source', THEME.orange),
            ('⏱️ Read Time', 'time', THEME.cyan),
            ('💭 Sentiment', 'sentiment', THEME.purple),
            ('🔓 Bypass', 'bypass', THEME.fg_dark),
        ]
        for label, key, color in meta_items:
            frame = tk.Frame(self.meta_frame, bg=THEME.bg_visual)
            frame.pack(side=tk.LEFT, padx=(0, 25))
            tk.Label(frame, text=f"{label}:", font=get_font("xs"),
                     fg=THEME.comment, bg=THEME.bg_visual).pack(side=tk.LEFT)
            self.meta_labels[key] = tk.Label(frame, text="--", font=get_font("xs", "bold"),
                                              fg=color, bg=THEME.bg_visual)
            self.meta_labels[key].pack(side=tk.LEFT, padx=(4, 0))
        
        # Tabbed content - configure ttk style
        style = ttk.Style()
        style.configure("Tokyo.TNotebook", background=THEME.bg, borderwidth=0)
        style.configure("Tokyo.TNotebook.Tab", background=THEME.bg_highlight, 
                       foreground=THEME.fg_dark, padding=[12, 6])
        style.map("Tokyo.TNotebook.Tab", 
                 background=[("selected", THEME.bg_visual)],
                 foreground=[("selected", THEME.cyan)])
        
        self.notebook = ttk.Notebook(content, style="Tokyo.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Tab 1: Summary
        self.summary_frame = tk.Frame(self.notebook, bg=THEME.bg, padx=10, pady=10)
        self.notebook.add(self.summary_frame, text="📋 Summary")
        
        self.summary_text = scrolledtext.ScrolledText(self.summary_frame, font=get_font("md"),
                                                       bg=THEME.bg_highlight, fg=THEME.fg, 
                                                       wrap=tk.WORD, height=10, relief=tk.FLAT,
                                                       insertbackground=THEME.cyan)
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        self.summary_text.insert(tk.END, "Loading summary...")
        self.summary_text.config(state=tk.DISABLED)
        
        # Tab 2: Full Content
        self.content_frame = tk.Frame(self.notebook, bg=THEME.bg, padx=10, pady=10)
        self.notebook.add(self.content_frame, text="📄 Full Content")
        
        self.content_text = scrolledtext.ScrolledText(self.content_frame, font=get_font("sm"),
                                                       bg=THEME.bg_highlight, fg=THEME.fg_dark,
                                                       wrap=tk.WORD, height=15, relief=tk.FLAT,
                                                       insertbackground=THEME.cyan)
        self.content_text.pack(fill=tk.BOTH, expand=True)
        self.content_text.insert(tk.END, "Loading content...")
        self.content_text.config(state=tk.DISABLED)
        
        # Tab 3: Key Points
        self.keypoints_frame = tk.Frame(self.notebook, bg=THEME.bg, padx=10, pady=10)
        self.notebook.add(self.keypoints_frame, text="📌 Key Points")
        
        # Tab 4: Entities
        self.entities_frame = tk.Frame(self.notebook, bg=THEME.bg, padx=10, pady=10)
        self.notebook.add(self.entities_frame, text="🏢 Entities")
        
        # Button bar
        btn_frame = tk.Frame(self.window, bg=THEME.bg_highlight, pady=14)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Button(btn_frame, text="🔬 Re-Analyze with Bypass", font=get_font("sm", "bold"),
                  bg=THEME.purple, fg=THEME.fg, activebackground=THEME.bright_magenta,
                  padx=15, pady=8, relief=tk.FLAT, cursor='hand2',
                  command=self._analyze_with_bypass).pack(side=tk.LEFT, padx=15)
        tk.Button(btn_frame, text="📋 Copy Summary", font=get_font("sm"),
                  bg=THEME.bg_visual, fg=THEME.fg_dark, activebackground=THEME.bg_search,
                  padx=15, pady=8, relief=tk.FLAT, cursor='hand2',
                  command=self._copy_summary).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🌐 Open in Browser", font=get_font("sm"),
                  bg=THEME.bg_visual, fg=THEME.cyan, activebackground=THEME.bg_search,
                  padx=15, pady=8, relief=tk.FLAT, cursor='hand2',
                  command=lambda: webbrowser.open(self.url)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="✕ Close", font=get_font("sm"),
                  bg=THEME.red, fg=THEME.fg, activebackground=THEME.bright_red,
                  padx=15, pady=8, relief=tk.FLAT, cursor='hand2',
                  command=self.window.destroy).pack(side=tk.RIGHT, padx=15)
    
    def _window_exists(self) -> bool:
        """Check if the popup window still exists and is valid."""
        try:
            return self.window.winfo_exists()
        except tk.TclError:
            return False
    
    def _analyze_url(self):
        """Analyze URL using orchestrator."""
        async def do_analyze():
            return await self.orchestrator.analyze_url(self.url)
        
        def on_result(result, error):
            if error or not result:
                self._analyze_with_bypass()
            else:
                self._display_result(result, bypass_used=False)
        
        self.async_runner.run_async(do_analyze(), on_result)
    
    def _analyze_with_bypass(self):
        """Analyze URL with bypass enabled."""
        if not BYPASS_AVAILABLE:
            self._show_error("Bypass module not available")
            return
        
        self.title_label.config(text="⏳ Fetching with bypass...")
        self.bypass_indicator.config(text="🔄 Bypass in progress...")
        
        async def do_bypass_fetch():
            # Try ContentPlatformBypass first for known platforms (Medium, Substack, Ghost)
            try:
                if self.content_platform_bypass:
                    platform = self.content_platform_bypass.detect_platform(self.url)
                    if platform != ContentPlatform.UNKNOWN:
                        logger.info(f"📱 Detected {platform.value} platform, using smart bypass...")
                        result = await self.content_platform_bypass.bypass(self.url, strategy="auto")
                        if result.success:
                            logger.info(f"✅ Content platform bypass: {result.content_length} chars")
                            return result.content, f"Content Platform ({platform.value})"
                
                # Try anti-bot bypass (HTTP-based)
                result = await self.anti_bot.fetch_with_bypass(self.url)
                
                if result.success:
                    content = result.content
                    bypass_method = f"Anti-bot ({result.protection_type.value})"
                    
                    # Check for paywall
                    if self.paywall_bypass.detect_paywall(content):
                        paywall_result = await self.paywall_bypass.bypass_paywall(self.url)
                        if paywall_result.success:
                            content = paywall_result.content
                            bypass_method = f"Paywall ({paywall_result.method_used.value})"
                    
                    return content, bypass_method
                
                # Try paywall bypass directly (HTTP-based)
                paywall_result = await self.paywall_bypass.bypass_paywall(self.url)
                if paywall_result.success:
                    return paywall_result.content, f"Paywall ({paywall_result.method_used.value})"
                
                # Try browser-based bypass as final fallback (uses Playwright + Neural DOM Eraser)
                logger.info("HTTP bypasses failed, trying browser automation...")
                browser_result = await self.paywall_bypass.dom_manipulation_with_browser(self.url)
                if browser_result.success:
                    return browser_result.content, "Browser (Neural DOM Eraser)"
                
                return None, None
            finally:
                # Ensure sessions are closed to prevent warnings
                await self.anti_bot.close()
                await self.paywall_bypass.close()
                if self.content_platform_bypass:
                    await self.content_platform_bypass.close()
        
        def on_bypass_result(result, error):
            # Check if window still exists before updating
            if not self._window_exists():
                return
                
            if error:
                self._show_error(f"Error: {error}")
            elif not result or not result[0]:
                msg = "Failed to fetch content."
                if not BYPASS_AVAILABLE:
                     msg += "\n\nPlaywright is not installed. Neural DOM Eraser disabled.\nTry running: playwright install"
                self._show_error(msg)
                return
            
            content, bypass_method = result
            self.bypass_method_used = bypass_method
            
            # Now analyze the fetched content using the pre-fetched HTML
            # Use synchronous method that accepts pre-fetched HTML
            try:
                analysis_result = self.orchestrator.analyze_url_with_content(self.url, content)
                if self._window_exists():  # Check again before display
                    if analysis_result:
                        self._display_result(analysis_result, bypass_used=True, 
                                             bypass_method=bypass_method, raw_content=content)
                    else:
                        self._display_raw_content(content, bypass_method)
            except Exception as e:
                logger.error(f"Analysis failed: {e}")
                self._display_raw_content(content, bypass_method)
        
        self.async_runner.run_async(do_bypass_fetch(), on_bypass_result)
    
    def _display_result(self, result, bypass_used: bool = False, bypass_method: str = None, raw_content: str = None):
        """Display analysis result."""
        # Update title
        self.title_label.config(text=result.article.title)
        
        # Update meta info
        score = result.article.tech_score.score if result.article.tech_score else 0
        self.meta_labels['score'].config(text=f"{score:.2f}")
        self.meta_labels['source'].config(text=result.article.source[:20])
        self.meta_labels['time'].config(text=f"{result.reading_time_min} min")
        self.meta_labels['sentiment'].config(text=result.sentiment.capitalize())
        
        if bypass_used:
            self.meta_labels['bypass'].config(text=bypass_method or "Yes", fg='#00aa00')
            self.bypass_indicator.config(text=f"🔓 Bypassed: {bypass_method}", fg='#00ff88')
        else:
            self.meta_labels['bypass'].config(text="Not needed", fg='#666666')
            self.bypass_indicator.config(text="✓ Direct access", fg='#888888')
        
        # Update summary tab
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        summary = result.article.summary if result.article.summary else "No summary available."
        self.summary_text.insert(tk.END, summary)
        self.summary_text.config(state=tk.DISABLED)
        
        # Update content tab
        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        content = raw_content if raw_content else result.article.content
        self.content_text.insert(tk.END, content[:5000] if len(content) > 5000 else content)
        self.content_text.config(state=tk.DISABLED)
        
        # Update key points tab
        for widget in self.keypoints_frame.winfo_children():
            widget.destroy()
        
        if result.key_points:
            for i, point in enumerate(result.key_points[:8], 1):
                frame = tk.Frame(self.keypoints_frame, bg=THEME.bg_highlight, padx=12, pady=8)
                frame.pack(fill=tk.X, pady=4)
                tk.Label(frame, text=f"📌 {i}.", font=get_font("md", "bold"),
                         fg=THEME.cyan, bg=THEME.bg_highlight).pack(side=tk.LEFT)
                tk.Label(frame, text=point.text, font=get_font("md"),
                         fg=THEME.fg, bg=THEME.bg_highlight, wraplength=800, justify=tk.LEFT).pack(side=tk.LEFT, padx=8)
        else:
            tk.Label(self.keypoints_frame, text="No key points extracted.",
                     font=get_font("md"), fg=THEME.comment, bg=THEME.bg).pack(pady=20)
        
        # Update entities tab
        for widget in self.entities_frame.winfo_children():
            widget.destroy()
        
        if result.entities:
            entity_types = [
                ('🏢 Companies', result.entities.companies, THEME.orange),
                ('🔧 Technologies', result.entities.technologies, THEME.green),
                ('👤 People', getattr(result.entities, 'people', []), THEME.cyan),
            ]
            for label, items, color in entity_types:
                if items:
                    frame = tk.Frame(self.entities_frame, bg=THEME.bg_visual, padx=15, pady=10)
                    frame.pack(fill=tk.X, pady=5)
                    tk.Label(frame, text=label, font=get_font("md", "bold"),
                             fg=color, bg=THEME.bg_visual).pack(anchor=tk.W)
                    tk.Label(frame, text=', '.join(items[:10]), font=get_font("sm"),
                             fg=THEME.fg_dark, bg=THEME.bg_visual, wraplength=800).pack(anchor=tk.W, pady=(4, 0))
        else:
            tk.Label(self.entities_frame, text="No entities extracted.",
                     font=get_font("md"), fg=THEME.comment, bg=THEME.bg).pack(pady=20)
    
    def _display_raw_content(self, content: str, bypass_method: str):
        """Display raw content when analysis fails."""
        self.title_label.config(text="Content Retrieved Successfully")
        self.meta_labels['score'].config(text="--")
        self.meta_labels['source'].config(text="Unknown")
        self.meta_labels['time'].config(text="--")
        self.meta_labels['sentiment'].config(text="--")
        self.meta_labels['bypass'].config(text=bypass_method, fg=THEME.green)
        self.bypass_indicator.config(text=f"🔓 Bypassed: {bypass_method}", fg=THEME.green)
        
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, "Full analysis unavailable. Raw content retrieved below.")
        self.summary_text.config(state=tk.DISABLED)
        
        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        self.content_text.insert(tk.END, content[:8000] if len(content) > 8000 else content)
        self.content_text.config(state=tk.DISABLED)
    
    def _show_error(self, message: str):
        """Show error in popup with safety check."""
        if not self._window_exists():
            return
        try:
            self.title_label.config(text=f"❌ Error: {message}", fg=THEME.red)
            self.bypass_indicator.config(text="❌ Failed", fg=THEME.red)
        except tk.TclError:
            pass  # Window was destroyed
    
    def _copy_summary(self):
        """Copy summary to clipboard."""
        self.summary_text.config(state=tk.NORMAL)
        summary = self.summary_text.get(1.0, tk.END)
        self.summary_text.config(state=tk.DISABLED)
        self.window.clipboard_clear()
        self.window.clipboard_append(summary)
        messagebox.showinfo("Copied", "Summary copied to clipboard!")
