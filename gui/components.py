"""
Reusable GUI components for the Tech News Scraper application.
"""

import tkinter as tk
from tkinter import ttk
import platform

class ScrollableFrame(tk.Frame):
    """
    A scrollable frame component that wraps a frame in a canvas with a scrollbar.
    Handles cross-platform mousewheel scrolling.
    """
    
    def __init__(self, container, bg_color=None, width=None, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        if bg_color:
            self.canvas.configure(bg=bg_color)
            self.configure(bg=bg_color)
            
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        # Determine styling for scrollbar if possible (custom theme matching)
        # Note: Standard Tkinter scrollbar styling is limited, ttk is better but clashes with dark themes sometimes
        # We'll stick to standard for now, but allow color config
        if bg_color:
            self.scrollbar.configure(bg=bg_color, troughcolor=bg_color)
            
        self.scrollable_frame = tk.Frame(self.canvas)
        if bg_color:
            self.scrollable_frame.configure(bg=bg_color)
            
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configure canvas to resize the window
        self.canvas.bind('<Configure>', self._configure_window_width)
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel
        self.bind_mousewheel(self.canvas)
        self.bind_mousewheel(self.scrollable_frame)
        
    def _configure_window_width(self, event):
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def bind_mousewheel(self, widget):
        """Bind mousewheel events to widget and its children."""
        widget.bind('<Enter>', self._bound_to_mousewheel)
        widget.bind('<Leave>', self._unbound_to_mousewheel)

    def _bound_to_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)  # Windows/macOS
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)    # Linux
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)    # Linux

    def _unbound_to_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if platform.system() == 'Windows':
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif platform.system() == 'Darwin': # macOS
            self.canvas.yview_scroll(int(-1 * event.delta), "units")
        else: # Linux
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
