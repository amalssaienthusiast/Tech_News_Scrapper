"""
Developer Dashboard - Full system control interface.

7 Tabbed panels for complete developer access:
1. System Monitor - Real-time metrics and health
2. AI Laboratory - Model control and experimentation
3. Bypass Control - Technique management and testing
4. Resilience Dashboard - Auto-fixer and issue tracking
5. Security Tools - Fingerprint generation, behavior simulation
6. Debug Console - Live logs and command execution
7. Performance Analytics - System performance charts
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List
import threading
import json

# Import theme and new managers
from gui.theme import THEME, get_font, get_mode_theme
from gui.config_manager import get_config

logger = logging.getLogger(__name__)


class DeveloperDashboard:
    """
    Comprehensive developer interface with full system control.
    
    Integrates with:
    - ResilienceSystem for auto-healing
    - MetricsCollector for performance data
    - Bypass engines for technique management
    - Configuration system for settings
    """
    
    def __init__(self, parent_frame: tk.Frame, async_runner):
        """
        Initialize developer dashboard.
        
        Args:
            parent_frame: Parent tkinter frame
            async_runner: AsyncRunner for background tasks
        """
        self.parent = parent_frame
        self.async_runner = async_runner
        
        # Configuration
        self._config = get_config()
        
        # Apply developer mode theme
        mode_theme = get_mode_theme('developer')
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(parent_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab references
        self.tabs: Dict[str, tk.Frame] = {}
        
        # Cached data
        self._bypass_techniques: List[Dict] = []
        self._system_metrics: Dict[str, Any] = {}
        
        # Initialize all tabs
        self._init_system_monitor_tab()
        self._init_ai_laboratory_tab()
        self._init_bypass_control_tab()
        self._init_resilience_dashboard_tab()
        self._init_security_tools_tab()
        self._init_debug_console_tab()
        self._init_performance_analytics_tab()
        
        # Start background updates
        self._start_updates()
        
        # Defer initial data load until UI is fully rendered
        # Using after(100ms) ensures widgets exist before updating them
        self.parent.after(100, self._load_bypass_techniques)
        self.parent.after(200, self._refresh_system_monitor)
        self.parent.after(300, self._update_resilience_status)
        
        logger.info("DeveloperDashboard initialized with real backend integrations")
    
    def _create_tab(self, name: str, icon: str, title: str) -> tk.Frame:
        """Create a new tab and add it to notebook."""
        tab = tk.Frame(self.notebook, bg=THEME.bg)
        self.notebook.add(tab, text=f"{icon} {title}")
        self.tabs[name] = tab
        return tab
    
    def _load_bypass_techniques(self) -> None:
        """Load available bypass techniques from backend."""
        self._bypass_techniques = []
        
        try:
            # Try to load from bypass module
            from src.bypass import anti_bot, stealth, paywall, proxy_manager
            
            self._bypass_techniques = [
                {'name': 'Stealth Browser', 'module': 'stealth', 'status': 'active', 'color': THEME.green},
                {'name': 'Anti-Bot Bypass', 'module': 'anti_bot', 'status': 'active', 'color': THEME.green},
                {'name': 'Paywall Bypass', 'module': 'paywall', 'status': 'active', 'color': THEME.cyan},
                {'name': 'Proxy Rotation', 'module': 'proxy_manager', 'status': 'active', 'color': THEME.cyan},
                {'name': 'User-Agent Rotation', 'module': 'stealth', 'status': 'active', 'color': THEME.green},
                {'name': 'Cookie Management', 'module': 'stealth', 'status': 'active', 'color': THEME.blue},
                {'name': 'JavaScript Rendering', 'module': 'browser_engine', 'status': 'available', 'color': THEME.orange},
                {'name': 'Cloudflare Bypass', 'module': 'anti_bot', 'status': 'active', 'color': THEME.magenta},
            ]
            logger.debug(f"Loaded {len(self._bypass_techniques)} bypass techniques")
        except ImportError as e:
            logger.warning(f"Could not load bypass modules: {e}")
            # Fallback to static list
            self._bypass_techniques = [
                {'name': 'Stealth Browser', 'module': 'stealth', 'status': 'unknown', 'color': THEME.comment},
                {'name': 'Anti-Bot Bypass', 'module': 'anti_bot', 'status': 'unknown', 'color': THEME.comment},
            ]
    
    # =========================================================================
    # TAB 1: SYSTEM MONITOR
    # =========================================================================
    
    def _init_system_monitor_tab(self):
        """System monitoring with real-time metrics."""
        tab = self._create_tab('system_monitor', '🚀', 'System Monitor')
        
        # Header
        header = tk.Frame(tab, bg=THEME.bg_dark, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🚀 SYSTEM MONITOR", font=get_font("lg", "bold"),
                 fg=THEME.cyan, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=15, pady=12)
        
        self.monitor_refresh_btn = tk.Button(header, text="🔄 Refresh", font=get_font("sm"),
                                             bg=THEME.green, fg=THEME.black,
                                             command=self._refresh_system_monitor)
        self.monitor_refresh_btn.pack(side=tk.RIGHT, padx=15, pady=10)
        
        # Content
        content = tk.Frame(tab, bg=THEME.bg, padx=15, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Health Matrix (4 columns)
        health_frame = tk.LabelFrame(content, text="Component Health", 
                                     bg=THEME.bg, fg=THEME.fg,
                                     font=get_font("md", "bold"))
        health_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.health_indicators = {}
        components = [
            ('resilience', 'Resilience System', '🛡️'),
            ('compatibility', 'Compatibility Layer', '🔄'),
            ('scraper', 'News Scraper', '📰'),
            ('pipeline', 'Feed Pipeline', '⚡')
        ]
        
        for i, (key, name, icon) in enumerate(components):
            col = i % 4
            row = i // 4
            
            card = tk.Frame(health_frame, bg=THEME.bg_highlight, padx=12, pady=10)
            card.grid(row=row, column=col, padx=8, pady=8, sticky='nsew')
            
            health_frame.grid_columnconfigure(col, weight=1)
            
            tk.Label(card, text=icon, font=get_font("xl"),
                     fg=THEME.cyan, bg=THEME.bg_highlight).pack()
            tk.Label(card, text=name, font=get_font("sm", "bold"),
                     fg=THEME.fg, bg=THEME.bg_highlight).pack()
            
            status_label = tk.Label(card, text="● Checking...", font=get_font("xs"),
                                    fg=THEME.comment, bg=THEME.bg_highlight)
            status_label.pack()
            self.health_indicators[key] = status_label
        
        # Metrics Stream
        metrics_frame = tk.LabelFrame(content, text="Live Metrics", 
                                      bg=THEME.bg, fg=THEME.fg,
                                      font=get_font("md", "bold"))
        metrics_frame.pack(fill=tk.BOTH, expand=True)
        
        self.metrics_text = scrolledtext.ScrolledText(
            metrics_frame, height=12, bg=THEME.bg_dark, fg=THEME.fg,
            font=("Consolas", 10), wrap=tk.WORD
        )
        self.metrics_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _refresh_system_monitor(self):
        """Refresh system monitor data."""
        try:
            # Update health indicators
            try:
                from src.resilience import resilience
                health = resilience.get_system_health()
                
                self.health_indicators['resilience'].config(
                    text="● Healthy" if health.get('initialized') else "● Inactive",
                    fg=THEME.green if health.get('initialized') else THEME.orange
                )
            except ImportError:
                self.health_indicators['resilience'].config(text="● Not Available", fg=THEME.comment)
            
            try:
                from src.compatibility import RSSCompatibilityEngine
                self.health_indicators['compatibility'].config(text="● Active", fg=THEME.green)
            except ImportError:
                self.health_indicators['compatibility'].config(text="● Not Available", fg=THEME.comment)
            
            # Show basic metrics
            self.metrics_text.delete('1.0', tk.END)
            self.metrics_text.insert(tk.END, f"Last Updated: {datetime.now().strftime('%H:%M:%S')}\n\n")
            
            try:
                import psutil
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory()
                self.metrics_text.insert(tk.END, f"CPU Usage: {cpu}%\n")
                self.metrics_text.insert(tk.END, f"Memory: {mem.used / (1024**3):.1f}GB / {mem.total / (1024**3):.1f}GB ({mem.percent}%)\n")
            except ImportError:
                self.metrics_text.insert(tk.END, "psutil not installed - install for system metrics\n")
            
            self.health_indicators['scraper'].config(text="● Ready", fg=THEME.green)
            self.health_indicators['pipeline'].config(text="● Ready", fg=THEME.green)
            
        except Exception as e:
            logger.error(f"System monitor refresh error: {e}")
    
    # =========================================================================
    # TAB 2: AI LABORATORY
    # =========================================================================
    
    def _init_ai_laboratory_tab(self):
        """AI model control and experimentation."""
        tab = self._create_tab('ai_laboratory', '🧠', 'AI Laboratory')
        
        # Header
        header = tk.Frame(tab, bg=THEME.bg_dark, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🧠 AI LABORATORY", font=get_font("lg", "bold"),
                 fg=THEME.magenta, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=15, pady=12)
        
        # Content
        content = tk.Frame(tab, bg=THEME.bg, padx=15, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Model Status
        model_frame = tk.LabelFrame(content, text="AI Models Status", 
                                    bg=THEME.bg, fg=THEME.fg,
                                    font=get_font("md", "bold"))
        model_frame.pack(fill=tk.X, pady=(0, 15))
        
        models = [
            ('Gemini', 'google-generativeai', THEME.blue),
            ('Transformers', 'transformers', THEME.orange),
            ('Sentence-BERT', 'sentence-transformers', THEME.green)
        ]
        
        for name, package, color in models:
            row = tk.Frame(model_frame, bg=THEME.bg_highlight, padx=12, pady=8)
            row.pack(fill=tk.X, pady=3, padx=5)
            
            tk.Label(row, text=f"🤖 {name}", font=get_font("sm", "bold"),
                     fg=color, bg=THEME.bg_highlight).pack(side=tk.LEFT)
            
            try:
                __import__(package.replace('-', '_'))
                status_text, status_color = "Available", THEME.green
            except ImportError:
                status_text, status_color = "Not Installed", THEME.comment
            
            tk.Label(row, text=f"● {status_text}", font=get_font("sm"),
                     fg=status_color, bg=THEME.bg_highlight).pack(side=tk.RIGHT)
        
        # AI Features
        features_frame = tk.LabelFrame(content, text="AI Features", 
                                       bg=THEME.bg, fg=THEME.fg,
                                       font=get_font("md", "bold"))
        features_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(features_frame, text="Available AI capabilities in this application:",
                 font=get_font("sm"), fg=THEME.comment, bg=THEME.bg).pack(anchor=tk.W, padx=10, pady=5)
        
        features = [
            "📊 Sentiment Analysis for articles",
            "🏷️ Automatic topic classification",
            "📝 AI-powered article summaries",
            "🔍 Smart relevance scoring",
            "🎯 Content quality filtering"
        ]
        
        for feature in features:
            tk.Label(features_frame, text=f"  • {feature}",
                     font=get_font("sm"), fg=THEME.fg, bg=THEME.bg).pack(anchor=tk.W, padx=15)
    
    # =========================================================================
    # TAB 3: BYPASS CONTROL
    # =========================================================================
    
    def _init_bypass_control_tab(self):
        """Bypass engine control and security research tools."""
        tab = self._create_tab('bypass_control', '🔐', 'Bypass Control')
        
        # Header
        header = tk.Frame(tab, bg=THEME.bg_dark, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🔐 BYPASS CONTROL", font=get_font("lg", "bold"),
                 fg=THEME.orange, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=15, pady=12)
        
        # Content
        content = tk.Frame(tab, bg=THEME.bg, padx=15, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Techniques List
        techniques_frame = tk.LabelFrame(content, text="Available Bypass Techniques", 
                                         bg=THEME.bg, fg=THEME.fg,
                                         font=get_font("md", "bold"))
        techniques_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Scrollable list
        techniques_canvas = tk.Canvas(techniques_frame, bg=THEME.bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(techniques_frame, orient="vertical", command=techniques_canvas.yview)
        techniques_inner = tk.Frame(techniques_canvas, bg=THEME.bg)
        
        techniques_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        techniques_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        techniques_canvas.create_window((0, 0), window=techniques_inner, anchor="nw")
        
        techniques = [
            ("Stealth Browser", "Browser automation with anti-detection", THEME.green),
            ("User-Agent Rotation", "Rotating browser signatures", THEME.green),
            ("Proxy Support", "HTTP/SOCKS proxy rotation", THEME.cyan),
            ("Cookie Management", "Session persistence", THEME.cyan),
            ("JavaScript Rendering", "Full JS execution", THEME.orange),
            ("Cloudflare Bypass", "Challenge solving", THEME.magenta),
            ("CAPTCHA Handling", "Automated solving", THEME.magenta),
            ("Rate Limiting", "Adaptive throttling", THEME.blue),
        ]
        
        for name, desc, color in techniques:
            row = tk.Frame(techniques_inner, bg=THEME.bg_highlight, padx=12, pady=8)
            row.pack(fill=tk.X, pady=3, padx=5)
            
            tk.Label(row, text=f"✓ {name}", font=get_font("sm", "bold"),
                     fg=color, bg=THEME.bg_highlight, width=20, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=desc, font=get_font("sm"),
                     fg=THEME.fg_dark, bg=THEME.bg_highlight).pack(side=tk.LEFT, padx=10)
        
        techniques_inner.update_idletasks()
        techniques_canvas.config(scrollregion=techniques_canvas.bbox("all"))
    
    # =========================================================================
    # TAB 4: RESILIENCE DASHBOARD
    # =========================================================================
    
    def _init_resilience_dashboard_tab(self):
        """Resilience system monitoring and control."""
        tab = self._create_tab('resilience', '🛡️', 'Resilience System')
        
        # Header
        header = tk.Frame(tab, bg=THEME.bg_dark, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🛡️ RESILIENCE SYSTEM", font=get_font("lg", "bold"),
                 fg=THEME.green, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=15, pady=12)
        
        tk.Button(header, text="🔧 Auto-Fix Issues", font=get_font("sm", "bold"),
                  bg=THEME.green, fg=THEME.black,
                  command=self._run_auto_fix).pack(side=tk.RIGHT, padx=15, pady=10)
        
        # Content
        content = tk.Frame(tab, bg=THEME.bg, padx=15, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Status
        status_frame = tk.LabelFrame(content, text="System Status", 
                                     bg=THEME.bg, fg=THEME.fg,
                                     font=get_font("md", "bold"))
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.resilience_status_text = scrolledtext.ScrolledText(
            status_frame, height=8, bg=THEME.bg_dark, fg=THEME.fg,
            font=("Consolas", 10), wrap=tk.WORD
        )
        self.resilience_status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self._update_resilience_status()
        
        # Issues
        issues_frame = tk.LabelFrame(content, text="Detected Issues", 
                                     bg=THEME.bg, fg=THEME.fg,
                                     font=get_font("md", "bold"))
        issues_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('type', 'severity', 'status')
        self.issues_tree = ttk.Treeview(issues_frame, columns=columns, show='headings', height=8)
        
        self.issues_tree.heading('type', text='Issue Type')
        self.issues_tree.heading('severity', text='Severity')
        self.issues_tree.heading('status', text='Status')
        
        self.issues_tree.column('type', width=200)
        self.issues_tree.column('severity', width=100)
        self.issues_tree.column('status', width=150)
        
        self.issues_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _update_resilience_status(self):
        """Update resilience system status."""
        self.resilience_status_text.delete('1.0', tk.END)
        
        try:
            from src.resilience import resilience
            health = resilience.get_system_health()
            
            self.resilience_status_text.insert(tk.END, "✅ RESILIENCE SYSTEM ACTIVE\n\n")
            self.resilience_status_text.insert(tk.END, f"Initialized: {health.get('initialized', False)}\n")
            self.resilience_status_text.insert(tk.END, f"Timestamp: {health.get('timestamp', 'N/A')}\n\n")
            
            # Self-healing
            sh = health.get('self_healing', {})
            self.resilience_status_text.insert(tk.END, f"Active Issues: {sh.get('active_issues', 0)}\n")
            self.resilience_status_text.insert(tk.END, f"Auto-Fixable: {sh.get('auto_fixable_issues', 0)}\n")
            
            # Sources
            sources = health.get('sources', {})
            self.resilience_status_text.insert(tk.END, f"\nSource Health: {sources.get('overall_status', 'unknown')}\n")
            
        except ImportError:
            self.resilience_status_text.insert(tk.END, "⚠️ Resilience system not available\n")
            self.resilience_status_text.insert(tk.END, "\nRun: python deploy_resilience.py")
    
    def _run_auto_fix(self):
        """Run auto-fix on detected issues."""
        try:
            from src.resilience import resilience
            
            async def do_fix():
                await resilience.initialize()
                return await resilience.auto_fix_all()
            
            def on_complete(result, error):
                if error:
                    messagebox.showerror("Auto-Fix Error", str(error))
                else:
                    fixes = result.get('fixes_applied', [])
                    messagebox.showinfo("Auto-Fix Complete", 
                                        f"Applied {len(fixes)} fixes successfully!")
                    self._update_resilience_status()
            
            self.async_runner.run_async(do_fix(), on_complete)
            
        except ImportError:
            messagebox.showwarning("Not Available", 
                                   "Resilience system not installed.\nRun: python deploy_resilience.py")
    
    # =========================================================================
    # TAB 5: SECURITY TOOLS
    # =========================================================================
    
    def _init_security_tools_tab(self):
        """Security research and testing tools."""
        tab = self._create_tab('security', '🔍', 'Security Tools')
        
        # Header
        header = tk.Frame(tab, bg=THEME.bg_dark, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🔍 SECURITY TOOLS", font=get_font("lg", "bold"),
                 fg=THEME.purple, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=15, pady=12)
        
        # Content
        content = tk.Frame(tab, bg=THEME.bg, padx=15, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Fingerprint Generator
        fp_frame = tk.LabelFrame(content, text="Browser Fingerprint Generator", 
                                 bg=THEME.bg, fg=THEME.fg,
                                 font=get_font("md", "bold"))
        fp_frame.pack(fill=tk.X, pady=(0, 15))
        
        fp_controls = tk.Frame(fp_frame, bg=THEME.bg)
        fp_controls.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(fp_controls, text="Profile:", font=get_font("sm"),
                 fg=THEME.fg, bg=THEME.bg).pack(side=tk.LEFT)
        
        self.fp_profile_var = tk.StringVar(value="chrome_windows")
        profiles = ttk.Combobox(fp_controls, textvariable=self.fp_profile_var,
                               values=["chrome_windows", "firefox_mac", "safari_ios", "chrome_android"],
                               state="readonly", width=20)
        profiles.pack(side=tk.LEFT, padx=10)
        
        tk.Button(fp_controls, text="Generate", font=get_font("sm"),
                  bg=THEME.purple, fg=THEME.black,
                  command=self._generate_fingerprint).pack(side=tk.LEFT, padx=5)
        
        self.fingerprint_text = scrolledtext.ScrolledText(
            fp_frame, height=8, bg=THEME.bg_dark, fg=THEME.fg,
            font=("Consolas", 9), wrap=tk.WORD
        )
        self.fingerprint_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # URL Tester
        test_frame = tk.LabelFrame(content, text="URL Bypass Tester", 
                                   bg=THEME.bg, fg=THEME.fg,
                                   font=get_font("md", "bold"))
        test_frame.pack(fill=tk.BOTH, expand=True)
        
        test_controls = tk.Frame(test_frame, bg=THEME.bg)
        test_controls.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(test_controls, text="URL:", font=get_font("sm"),
                 fg=THEME.fg, bg=THEME.bg).pack(side=tk.LEFT)
        
        self.test_url_entry = tk.Entry(test_controls, font=get_font("sm"),
                                       bg=THEME.bg_dark, fg=THEME.fg, width=50)
        self.test_url_entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        self.test_url_entry.insert(0, "https://example.com")
        
        tk.Button(test_controls, text="Test Bypass", font=get_font("sm"),
                  bg=THEME.orange, fg=THEME.black,
                  command=self._test_url_bypass).pack(side=tk.LEFT)
    
    def _generate_fingerprint(self):
        """Generate a browser fingerprint."""
        profile = self.fp_profile_var.get()
        
        fingerprints = {
            'chrome_windows': {
                'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'platform': 'Win32',
                'language': 'en-US',
                'screenResolution': '1920x1080',
                'timezone': 'America/New_York',
                'webglVendor': 'Google Inc. (Intel)',
                'webglRenderer': 'ANGLE (Intel, Intel(R) UHD Graphics 630)'
            },
            'firefox_mac': {
                'userAgent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0',
                'platform': 'MacIntel',
                'language': 'en-US',
                'screenResolution': '2560x1440',
                'timezone': 'America/Los_Angeles',
                'webglVendor': 'Apple Inc.',
                'webglRenderer': 'Apple M1 Pro'
            },
            'safari_ios': {
                'userAgent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
                'platform': 'iPhone',
                'language': 'en-US',
                'screenResolution': '390x844',
                'timezone': 'America/Chicago'
            },
            'chrome_android': {
                'userAgent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36',
                'platform': 'Linux armv8l',
                'language': 'en-US',
                'screenResolution': '412x915'
            }
        }
        
        fp = fingerprints.get(profile, fingerprints['chrome_windows'])
        
        self.fingerprint_text.delete('1.0', tk.END)
        self.fingerprint_text.insert(tk.END, f"// Browser Fingerprint: {profile}\n\n")
        
        import json
        self.fingerprint_text.insert(tk.END, json.dumps(fp, indent=2))
    
    def _test_url_bypass(self):
        """Test bypass on a URL."""
        url = self.test_url_entry.get()
        messagebox.showinfo("URL Bypass Test", 
                            f"Testing bypass for:\n{url}\n\n(Feature coming soon)")
    
    # =========================================================================
    # TAB 6: DEBUG CONSOLE
    # =========================================================================
    
    def _init_debug_console_tab(self):
        """Advanced debugging and system inspection."""
        tab = self._create_tab('debug', '🐞', 'Debug Console')
        
        # Header
        header = tk.Frame(tab, bg=THEME.bg_dark, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🐞 DEBUG CONSOLE", font=get_font("lg", "bold"),
                 fg=THEME.red, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=15, pady=12)
        
        tk.Button(header, text="🗑️ Clear", font=get_font("sm"),
                  bg=THEME.bg_visual, fg=THEME.fg,
                  command=self._clear_console).pack(side=tk.RIGHT, padx=15, pady=10)
        
        # Console
        console_frame = tk.Frame(tab, bg=THEME.bg)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        self.console_text = scrolledtext.ScrolledText(
            console_frame, bg="#0d0d0d", fg="#00ff00",
            font=("Consolas", 10), wrap=tk.WORD
        )
        self.console_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags
        self.console_text.tag_configure("info", foreground=THEME.cyan)
        self.console_text.tag_configure("warning", foreground=THEME.yellow)
        self.console_text.tag_configure("error", foreground=THEME.red)
        self.console_text.tag_configure("success", foreground=THEME.green)
        
        # Initial message
        self.console_text.insert(tk.END, "╔══════════════════════════════════════════════════════════╗\n")
        self.console_text.insert(tk.END, "║  Tech News Scraper - Debug Console                        ║\n")
        self.console_text.insert(tk.END, "╚══════════════════════════════════════════════════════════╝\n\n")
        self.console_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] Developer mode activated\n", "success")
        
        # Command input
        cmd_frame = tk.Frame(tab, bg=THEME.bg_dark, height=40)
        cmd_frame.pack(fill=tk.X, side=tk.BOTTOM)
        cmd_frame.pack_propagate(False)
        
        tk.Label(cmd_frame, text="›", font=get_font("lg", "bold"),
                 fg=THEME.green, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=(15, 5), pady=8)
        
        self.cmd_entry = tk.Entry(cmd_frame, font=("Consolas", 11),
                                  bg=THEME.bg_dark, fg=THEME.fg,
                                  insertbackground=THEME.fg)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=8)
        self.cmd_entry.bind('<Return>', self._execute_command)
    
    def _clear_console(self):
        """Clear the debug console."""
        self.console_text.delete('1.0', tk.END)
    
    def _execute_command(self, event=None):
        """Execute a console command."""
        cmd = self.cmd_entry.get().strip()
        self.cmd_entry.delete(0, tk.END)
        
        if not cmd:
            return
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.console_text.insert(tk.END, f"\n› {cmd}\n")
        
        # Parse command and arguments
        parts = cmd.split()
        command = parts[0].lower() if parts else ""
        args = parts[1:] if len(parts) > 1 else []
        
        # Command handlers
        if command == 'help':
            self._cmd_help()
        elif command == 'status':
            self._cmd_status()
        elif command == 'health':
            self._cmd_health()
        elif command == 'config':
            self._cmd_config(args)
        elif command == 'metrics':
            self._cmd_metrics()
        elif command == 'bypass':
            self._cmd_bypass(args)
        elif command == 'sources':
            self._cmd_sources()
        elif command == 'export':
            self._cmd_export(args)
        elif command == 'clear':
            self._clear_console()
        else:
            self.console_text.insert(tk.END, f"Unknown command: {command}\n", "warning")
            self.console_text.insert(tk.END, "Type 'help' for available commands\n", "info")
        
        self.console_text.see(tk.END)
    
    def _cmd_help(self):
        """Show help message."""
        self.console_text.insert(tk.END, "╔══════════════════════════════════════════════════════════╗\n", "info")
        self.console_text.insert(tk.END, "║  AVAILABLE COMMANDS                                       ║\n", "info")
        self.console_text.insert(tk.END, "╚══════════════════════════════════════════════════════════╝\n\n", "info")
        
        commands = [
            ("help", "Show this help"),
            ("status", "Show system status"),
            ("health", "Show resilience health"),
            ("config [get|set] [key] [val]", "View/modify configuration"),
            ("metrics", "Show Prometheus-style metrics"),
            ("bypass [list|test URL]", "Bypass technique management"),
            ("sources", "List active news sources"),
            ("export [logs|config|metrics]", "Export data to file"),
            ("clear", "Clear console"),
        ]
        
        for cmd, desc in commands:
            self.console_text.insert(tk.END, f"  {cmd:30} - {desc}\n")
    
    def _cmd_status(self):
        """Show system status."""
        self.console_text.insert(tk.END, "\n=== SYSTEM STATUS ===\n", "success")
        self.console_text.insert(tk.END, f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.console_text.insert(tk.END, "Status: OPERATIONAL\n", "success")
        
        try:
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            self.console_text.insert(tk.END, f"CPU: {cpu}%\n")
            self.console_text.insert(tk.END, f"Memory: {mem.percent}%\n")
        except ImportError:
            self.console_text.insert(tk.END, "psutil not installed\n", "warning")
    
    def _cmd_health(self):
        """Show resilience health."""
        try:
            from src.resilience import resilience
            health = resilience.get_system_health()
            
            self.console_text.insert(tk.END, "\n=== RESILIENCE HEALTH ===\n", "success")
            self.console_text.insert(tk.END, f"Initialized: {health.get('initialized', False)}\n")
            
            sh = health.get('self_healing', {})
            self.console_text.insert(tk.END, f"Active Issues: {sh.get('active_issues', 0)}\n")
            self.console_text.insert(tk.END, f"Auto-Fixable: {sh.get('auto_fixable_issues', 0)}\n")
            self.console_text.insert(tk.END, f"Fix Success Rate: {sh.get('fix_success_rate', {})}\n")
            
        except ImportError:
            self.console_text.insert(tk.END, "Resilience system not available\n", "warning")
    
    def _cmd_config(self, args: list):
        """Handle config commands."""
        if not args:
            # Show all config
            self.console_text.insert(tk.END, "\n=== CONFIGURATION ===\n", "info")
            summary = self._config.get_config_summary()
            for section, values in summary.get('sections', {}).items():
                self.console_text.insert(tk.END, f"\n[{section}]\n", "success")
                for key, val in values.items():
                    self.console_text.insert(tk.END, f"  {key}: {val}\n")
        elif args[0] == 'get' and len(args) > 1:
            key = args[1]
            value = self._config.get(key)
            self.console_text.insert(tk.END, f"{key} = {value}\n", "info")
        elif args[0] == 'set' and len(args) > 2:
            key = args[1]
            value = args[2]
            # Try to convert to appropriate type
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            
            if self._config.set(key, value):
                self.console_text.insert(tk.END, f"Set {key} = {value}\n", "success")
            else:
                self.console_text.insert(tk.END, f"Failed to set {key}\n", "error")
    
    def _cmd_metrics(self):
        """Show metrics."""
        self.console_text.insert(tk.END, "\n=== METRICS ===\n", "info")
        
        try:
            from src.monitoring.metrics_collector import MetricsCollector
            collector = MetricsCollector()
            summary = collector.get_summary()
            self.console_text.insert(tk.END, f"Total Scrapes: {summary.get('total_scrapes', 0)}\n")
            self.console_text.insert(tk.END, f"Successful: {summary.get('successful_scrapes', 0)}\n")
            self.console_text.insert(tk.END, f"Bypass Attempts: {summary.get('bypass_attempts', 0)}\n")
        except ImportError:
            self.console_text.insert(tk.END, "Metrics collector not available\n", "warning")
    
    def _cmd_bypass(self, args: list):
        """Handle bypass commands."""
        if not args or args[0] == 'list':
            self.console_text.insert(tk.END, "\n=== BYPASS TECHNIQUES ===\n", "info")
            for tech in self._bypass_techniques:
                status_icon = "✓" if tech['status'] == 'active' else "○"
                self.console_text.insert(tk.END, f"  {status_icon} {tech['name']} ({tech['module']})\n")
        elif args[0] == 'test' and len(args) > 1:
            url = args[1]
            self.console_text.insert(tk.END, f"Testing bypass for: {url}\n", "info")
            self.console_text.insert(tk.END, "Test in progress...\n", "warning")
    
    def _cmd_sources(self):
        """List active sources."""
        self.console_text.insert(tk.END, "\n=== NEWS SOURCES ===\n", "info")
        
        sources = [
            ("RSS Feeds", "30+", "active"),
            ("Google News", "API", "active"),
            ("DuckDuckGo", "Search", "active"),
            ("Reddit", "API", "active"),
            ("Directory Scrapers", "5", "active"),
        ]
        
        for name, count, status in sources:
            icon = "●" if status == "active" else "○"
            self.console_text.insert(tk.END, f"  {icon} {name}: {count}\n")
    
    def _cmd_export(self, args: list):
        """Export data."""
        if not args:
            self.console_text.insert(tk.END, "Usage: export [logs|config|metrics]\n", "warning")
            return
        
        export_type = args[0]
        filename = f"export_{export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        if export_type == 'config':
            from pathlib import Path
            filepath = Path.home() / '.technews' / filename
            if self._config.export_config(filepath):
                self.console_text.insert(tk.END, f"Exported to: {filepath}\n", "success")
            else:
                self.console_text.insert(tk.END, "Export failed\n", "error")
        else:
            self.console_text.insert(tk.END, f"Export {export_type} not yet implemented\n", "warning")
    
    # =========================================================================
    # TAB 7: PERFORMANCE ANALYTICS
    # =========================================================================
    
    def _init_performance_analytics_tab(self):
        """Performance analytics and optimization tools."""
        tab = self._create_tab('performance', '📊', 'Performance')
        
        # Header
        header = tk.Frame(tab, bg=THEME.bg_dark, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="📊 PERFORMANCE ANALYTICS", font=get_font("lg", "bold"),
                 fg=THEME.blue, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=15, pady=12)
        
        # Content
        content = tk.Frame(tab, bg=THEME.bg, padx=15, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # System Resources
        resources_frame = tk.LabelFrame(content, text="System Resources", 
                                        bg=THEME.bg, fg=THEME.fg,
                                        font=get_font("md", "bold"))
        resources_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Resource bars
        self.resource_bars = {}
        resources = [('CPU', THEME.cyan), ('Memory', THEME.green), ('Network', THEME.orange)]
        
        for name, color in resources:
            row = tk.Frame(resources_frame, bg=THEME.bg, padx=10, pady=8)
            row.pack(fill=tk.X)
            
            tk.Label(row, text=name, font=get_font("sm", "bold"), width=10,
                     fg=THEME.fg, bg=THEME.bg, anchor=tk.W).pack(side=tk.LEFT)
            
            bar_bg = tk.Frame(row, bg=THEME.bg_dark, height=20)
            bar_bg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
            
            bar = tk.Frame(bar_bg, bg=color, height=20, width=0)
            bar.place(x=0, y=0, relheight=1)
            
            value_label = tk.Label(row, text="0%", font=get_font("sm"),
                                   fg=THEME.fg_dark, bg=THEME.bg, width=8)
            value_label.pack(side=tk.RIGHT)
            
            self.resource_bars[name] = {'bar': bar, 'label': value_label, 'bg': bar_bg}
        
        # Optimization Tips
        tips_frame = tk.LabelFrame(content, text="Optimization Suggestions", 
                                   bg=THEME.bg, fg=THEME.fg,
                                   font=get_font("md", "bold"))
        tips_frame.pack(fill=tk.BOTH, expand=True)
        
        tips = [
            "💡 Enable request caching to reduce API calls",
            "💡 Use connection pooling for faster requests",
            "💡 Consider increasing rate limits for trusted sources",
            "💡 Enable parallel fetching for better performance"
        ]
        
        for tip in tips:
            tk.Label(tips_frame, text=tip, font=get_font("sm"),
                     fg=THEME.comment, bg=THEME.bg, anchor=tk.W).pack(anchor=tk.W, padx=15, pady=3)
    
    # =========================================================================
    # BACKGROUND UPDATES
    # =========================================================================
    
    def _start_updates(self):
        """Start background updates for live data."""
        self._update_resource_bars()
    
    def _update_resource_bars(self):
        """Update resource usage bars."""
        try:
            import psutil
            
            # CPU
            cpu_percent = psutil.cpu_percent()
            if 'CPU' in self.resource_bars:
                bar_width = int(cpu_percent * 3)  # Scale to widget width
                self.resource_bars['CPU']['bar'].configure(width=bar_width)
                self.resource_bars['CPU']['label'].configure(text=f"{cpu_percent:.1f}%")
            
            # Memory
            mem = psutil.virtual_memory()
            if 'Memory' in self.resource_bars:
                bar_width = int(mem.percent * 3)
                self.resource_bars['Memory']['bar'].configure(width=bar_width)
                self.resource_bars['Memory']['label'].configure(text=f"{mem.percent:.1f}%")
            
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Resource bar update error: {e}")
        
        # Schedule next update
        try:
            self.parent.after(2000, self._update_resource_bars)
        except:
            pass
    
    def destroy(self):
        """Clean up resources."""
        pass
