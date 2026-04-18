
import tkinter as tk
from gui.theme import THEME, get_font

class LiveStatusBanner:
    """
    Dynamic real-time status banner that shows actual fetch processes.
    
    Displays live procedural steps as they happen:
    - Connecting to sources
    - Loading from actual source names
    - Processing article counts
    - Filtering duplicates
    - Finalizing results
    """
    
    def __init__(self, parent):
        self.parent = parent
        self.frame = tk.Frame(parent, bg=THEME.bg_highlight, height=45) # Reduced height
        self.frame.pack(fill=tk.X, side=tk.TOP)
        self.frame.pack_propagate(False)
        
        # Status Label (Center)
        self.label = tk.Label(self.frame, text="", font=get_font("sm"),
                              fg=THEME.fg, bg=THEME.bg_highlight)
        self.label.pack(side=tk.LEFT, padx=15, pady=10)
        
        # Steps Indicators (Right)
        self.steps_frame = tk.Frame(self.frame, bg=THEME.bg_highlight)
        self.steps_frame.pack(side=tk.RIGHT, padx=15)
        
        self.steps = []
        for i in range(5):
            step = tk.Label(self.steps_frame, text="●", font=get_font("xs"),
                            fg=THEME.bg_visual, bg=THEME.bg_highlight)
            step.pack(side=tk.LEFT, padx=2)
            self.steps.append(step)
            
        self.is_visible = False

    def show(self):
        self.is_visible = True
        self.frame.pack(fill=tk.X, side=tk.TOP, before=self.parent.winfo_children()[0] if self.parent.winfo_children() else None)
        self._animate_pulse()
        
    def _animate_pulse(self):
        if not self.is_visible or not self.frame.winfo_exists():
            return
            
        # Subtle pulsing of text color
        current_fg = self.label.cget("fg")
        next_fg = THEME.cyan if current_fg == THEME.fg else THEME.fg
        self.label.config(fg=next_fg)
        
        self.frame.after(800, self._animate_pulse)

    def _add_status(self, text: str, color=None):
        if not self.frame.winfo_exists(): return
        self.label.config(text=text, fg=color or THEME.fg)

    def update_status(self, text: str, color=None):
        if self.frame.winfo_exists():
            try:
                self.frame.after(0, lambda: self._add_status(text, color))
            except Exception:
                pass

    def connecting(self):
        self.update_status("🔌 Connecting to realtime info-stream...", THEME.cyan)
        self.steps[0].config(fg=THEME.cyan)

    def loading_source(self, source_name: str, url: str = ""):
        msg = f"📥 Fetching from {source_name}..."
        if url:
            msg += f" ({url})"
        self.update_status(msg, THEME.blue)
        self.steps[0].config(fg=THEME.green)
        self.steps[1].config(fg=THEME.cyan)

    def using_api(self, api_name: str):
         self.update_status(f"🤖 Orchestrating via {api_name}...", THEME.purple)

    def fetched_articles(self, source: str, count: int):
        self.update_status(f"📄 Retrieved {count} articles from {source}", THEME.fg)

    def processing(self, total: int):
        self.update_status(f"⚙️ Processing {total} raw items...", THEME.orange)
        self.steps[2].config(fg=THEME.cyan)

    def filtering(self, duplicates: int):
        self.update_status(f"🔍 Removing {duplicates} duplicates & low quality items...", THEME.yellow)
        self.steps[3].config(fg=THEME.cyan)

    def finalizing(self, count: int):
        self.update_status(f"✨ Finalizing {count} unique articles...", THEME.magenta)
        self.steps[4].config(fg=THEME.cyan)

    def complete(self, count: int):
        self.update_status(f"✅ Ready! Displaying {count} live articles.", THEME.success)
        for step in self.steps:
            step.config(fg=THEME.success)

    def error(self, msg: str):
        self.update_status(f"❌ Error: {msg}", THEME.error)
        for step in self.steps:
            step.config(fg=THEME.error)

    def destroy(self):
        self.is_visible = False
        if self.frame.winfo_exists():
            self.frame.destroy()
