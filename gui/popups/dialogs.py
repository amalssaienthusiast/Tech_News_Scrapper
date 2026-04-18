
import tkinter as tk
from tkinter import ttk, messagebox
import json
from pathlib import Path
from gui.theme import THEME, get_font

class CustomSourcesPopup:
    """Popup for managing custom source URLs with Tokyo Night theme."""
    
    def __init__(self, parent, orchestrator):
        self.parent = parent
        self.orchestrator = orchestrator
        
        self.window = tk.Toplevel(parent)
        self.window.title("⚙️ Manage Custom Sources")
        self.window.geometry("1080x720")
        self.window.configure(bg=THEME.bg)
        self.window.transient(parent)
        self.window.grab_set()
        
        self._load_custom_sources()
        self._build_ui()
    
    def _load_custom_sources(self):
        """Load custom sources from file."""
        self.sources_file = Path(__file__).parent.parent.parent / "data" / "custom_sources.json"
        
        if self.sources_file.exists():
            try:
                with open(self.sources_file, 'r') as f:
                    self.custom_sources = json.load(f)
            except:
                self.custom_sources = []
        else:
            self.custom_sources = []
    
    def _save_custom_sources(self):
        """Save custom sources to file."""
        self.sources_file.parent.mkdir(exist_ok=True, parents=True)
        with open(self.sources_file, 'w') as f:
            json.dump(self.custom_sources, f, indent=2)
    
    def _build_ui(self):
        # Header
        header = tk.Frame(self.window, bg=THEME.bg_dark, height=55)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Frame(header, bg=THEME.cyan, height=3).pack(fill=tk.X, side=tk.TOP)
        
        header_inner = tk.Frame(header, bg=THEME.bg_dark)
        header_inner.pack(fill=tk.BOTH, expand=True, padx=20)
        
        tk.Label(header_inner, text="⚙️", font=get_font("xl"),
                 fg=THEME.cyan, bg=THEME.bg_dark).pack(side=tk.LEFT, pady=10)
        tk.Label(header_inner, text="MANAGE CUSTOM SOURCES", font=get_font("lg", "bold"),
                 fg=THEME.fg, bg=THEME.bg_dark).pack(side=tk.LEFT, padx=(8, 0), pady=10)
        
        # Main content
        content = tk.Frame(self.window, bg=THEME.bg, padx=25, pady=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Add URL section
        add_frame = tk.Frame(content, bg=THEME.bg_highlight, padx=15, pady=15)
        add_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(add_frame, text="➕ Add New Source URL", font=get_font("md", "bold"),
                 fg=THEME.green, bg=THEME.bg_highlight).pack(anchor=tk.W, pady=(0, 10))
        
        input_frame = tk.Frame(add_frame, bg=THEME.bg_highlight)
        input_frame.pack(fill=tk.X)
        
        self.url_entry = tk.Entry(input_frame, font=get_font("sm"), width=50,
                                   bg=THEME.bg_dark, fg=THEME.fg, insertbackground=THEME.fg,
                                   relief=tk.FLAT)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 10))
        self.url_entry.insert(0, "https://example.com/news")
        
        add_btn = tk.Button(input_frame, text="Add", font=get_font("sm", "bold"),
                           bg=THEME.green, fg=THEME.black,
                           activebackground=THEME.bright_green, activeforeground=THEME.black,
                           padx=20, pady=6, relief=tk.FLAT, cursor='hand2',
                           command=self._add_source)
        add_btn.pack(side=tk.LEFT)
        
        # Current sources list
        list_frame = tk.Frame(content, bg=THEME.bg_highlight, padx=15, pady=15)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(list_frame, text=f"📋 Current Custom Sources ({len(self.custom_sources)})", 
                 font=get_font("md", "bold"),
                 fg=THEME.cyan, bg=THEME.bg_highlight).pack(anchor=tk.W, pady=(0, 10))
        
        # Scrollable list
        list_container = tk.Frame(list_frame, bg=THEME.bg_dark)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        self.sources_listbox = tk.Listbox(list_container, font=get_font("sm", mono=True),
                                          bg=THEME.bg_dark, fg=THEME.fg,
                                          selectbackground=THEME.bg_visual,
                                          selectforeground=THEME.cyan,
                                          relief=tk.FLAT, height=12)
        self.sources_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_container, command=self.sources_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sources_listbox.config(yscrollcommand=scrollbar.set)
        
        # Populate list
        for source in self.custom_sources:
            self.sources_listbox.insert(tk.END, source.get('url', source) if isinstance(source, dict) else source)
        
        # Delete button
        delete_btn = tk.Button(list_frame, text="🗑️ Delete Selected", font=get_font("sm", "bold"),
                              bg=THEME.red, fg=THEME.fg,
                              activebackground=THEME.bright_red, activeforeground=THEME.black,
                              padx=15, pady=8, relief=tk.FLAT, cursor='hand2',
                              command=self._delete_source)
        delete_btn.pack(anchor=tk.E, pady=(10, 0))
        
        # Close button
        close_btn = tk.Button(self.window, text="Close", font=get_font("md", "bold"),
                             bg=THEME.bg_visual, fg=THEME.fg,
                             activebackground=THEME.bg_highlight,
                             padx=30, pady=10, relief=tk.FLAT, cursor='hand2',
                             command=self.window.destroy)
        close_btn.pack(pady=15)
    
    def _add_source(self):
        """Add a new source URL."""
        url = self.url_entry.get().strip()
        if not url or not url.startswith(('http://', 'https://')):
            messagebox.showwarning("Invalid URL", "Please enter a valid URL starting with http:// or https://")
            return
        
        # Add to list
        source_entry = {"url": url, "name": url.split('/')[2], "type": "custom"}
        self.custom_sources.append(source_entry)
        self._save_custom_sources()
        
        # Update listbox
        self.sources_listbox.insert(tk.END, url)
        self.url_entry.delete(0, tk.END)
        
        messagebox.showinfo("Added", f"Source added: {url}")
    
    def _delete_source(self):
        """Delete selected source."""
        selection = self.sources_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a source to delete.")
            return
        
        idx = selection[0]
        url = self.sources_listbox.get(idx)
        
        # Remove from list
        self.custom_sources = [s for s in self.custom_sources 
                               if (s.get('url') if isinstance(s, dict) else s) != url]
        self._save_custom_sources()
        
        # Update listbox
        self.sources_listbox.delete(idx)
        
        messagebox.showinfo("Deleted", f"Source removed: {url}")
