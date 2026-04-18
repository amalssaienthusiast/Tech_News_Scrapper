"""
Tokyo Night Theme System for Tech News Scraper GUI.

A professional-grade theming system implementing the Tokyo Night
color palette with modern UI patterns for a stunning visual experience.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class TokyoNightColors:
    """
    Tokyo Night color palette.
    
    A beautiful, carefully crafted dark theme inspired by the
    lights of Tokyo at night.
    """
    
    # Background colors (dark to light)
    bg_dark: str = "#1a1b26"      # Darkest background
    bg: str = "#1f2335"           # Main background
    bg_highlight: str = "#292e42" # Highlighted/selected background
    bg_visual: str = "#33467c"    # Visual selection
    bg_search: str = "#3d59a1"    # Search highlight
    bg_input: str = "#16161e"     # Input field background (darker than bg)
    bg_input_active: str = "#1a1b26" # Active input background

    
    # Foreground colors
    fg: str = "#c0caf5"           # Main text
    fg_dark: str = "#a9b1d6"      # Secondary text
    fg_gutter: str = "#3b4261"    # Muted text (line numbers, etc.)
    
    # Terminal colors
    black: str = "#15161e"
    red: str = "#f7768e"
    green: str = "#9ece6a"
    yellow: str = "#e0af68"
    blue: str = "#7aa2f7"
    magenta: str = "#bb9af7"
    cyan: str = "#7dcfff"
    white: str = "#a9b1d6"
    
    # Bright variants
    bright_black: str = "#414868"
    bright_red: str = "#f7768e"
    bright_green: str = "#9ece6a"
    bright_yellow: str = "#e0af68"
    bright_blue: str = "#7aa2f7"
    bright_magenta: str = "#bb9af7"
    bright_cyan: str = "#7dcfff"
    bright_white: str = "#c0caf5"
    
    # Accent colors
    orange: str = "#ff9e64"
    teal: str = "#1abc9c"
    purple: str = "#9d7cd8"
    pink: str = "#ff007c"
    
    # UI semantic colors
    border: str = "#3b4261"
    selection: str = "#364a82"
    comment: str = "#565f89"
    
    # Status colors
    success: str = "#9ece6a"
    warning: str = "#e0af68"
    error: str = "#f7768e"
    info: str = "#7aa2f7"
    
    # Special
    git_add: str = "#449dab"
    git_change: str = "#6183bb"
    git_delete: str = "#914c54"


# Global theme instance
THEME = TokyoNightColors()


@dataclass
class FontConfig:
    """Typography configuration."""
    
    # Font families (will fallback gracefully)
    primary: str = "Inter"
    secondary: str = "SF Pro Display"
    mono: str = "JetBrains Mono"
    fallback: str = "Helvetica"
    
    # Sizes
    size_xs: int = 9
    size_sm: int = 10
    size_base: int = 11
    size_md: int = 12
    size_lg: int = 14
    size_xl: int = 16
    size_2xl: int = 20
    size_3xl: int = 24
    size_4xl: int = 32


FONTS = FontConfig()


def get_font(size: str = "base", weight: str = "normal", *, mono: bool = False) -> tuple:
    """
    Get font tuple for tkinter.
    
    Args:
        size: xs, sm, base, md, lg, xl, 2xl, 3xl, 4xl
        weight: normal, bold
        mono: Use monospace font (default: False)
        
    Returns:
        Font tuple for tkinter: (family, size, weight)
    """
    family = FONTS.mono if mono else FONTS.fallback
    
    size_map = {
        "xs": FONTS.size_xs,
        "sm": FONTS.size_sm,
        "base": FONTS.size_base,
        "md": FONTS.size_md,
        "lg": FONTS.size_lg,
        "xl": FONTS.size_xl,
        "2xl": FONTS.size_2xl,
        "3xl": FONTS.size_3xl,
        "4xl": FONTS.size_4xl,
    }
    
    return (family, size_map.get(size, FONTS.size_base), weight)


def configure_ttk_styles():
    """Configure ttk styles for Tokyo Night theme."""
    from tkinter import ttk
    
    style = ttk.Style()
    
    # Configure Notebook (tabs)
    style.configure(
        "Tokyo.TNotebook",
        background=THEME.bg,
        borderwidth=0,
        tabmargins=[0, 0, 0, 0],
    )
    
    style.configure(
        "Tokyo.TNotebook.Tab",
        background=THEME.bg_highlight,
        foreground=THEME.fg_dark,
        padding=[16, 8],
        font=get_font("sm", "bold"),
        borderwidth=0,
    )
    
    style.map(
        "Tokyo.TNotebook.Tab",
        background=[("selected", THEME.bg_visual)],
        foreground=[("selected", THEME.cyan)],
    )
    
    # Configure Scrollbar
    style.configure(
        "Tokyo.Vertical.TScrollbar",
        background=THEME.bg_highlight,
        troughcolor=THEME.bg,
        borderwidth=0,
        arrowsize=0,
    )
    
    style.map(
        "Tokyo.Vertical.TScrollbar",
        background=[("active", THEME.bg_visual)],
    )
    
    # Configure Entry
    style.configure(
        "Tokyo.TEntry",
        fieldbackground=THEME.bg_highlight,
        foreground=THEME.fg,
        insertcolor=THEME.cyan,
        borderwidth=1,
        relief="solid",
    )
    
    # Configure Button
    style.configure(
        "Tokyo.TButton",
        background=THEME.blue,
        foreground=THEME.fg,
        padding=[12, 6],
        font=get_font("sm", "bold"),
        borderwidth=0,
    )
    
    style.map(
        "Tokyo.TButton",
        background=[("active", THEME.bright_blue)],
    )


def create_gradient_frame(parent, start_color: str, end_color: str, **kwargs):
    """Create a frame with gradient effect (simulated with canvas)."""
    import tkinter as tk
    
    canvas = tk.Canvas(parent, highlightthickness=0, **kwargs)
    
    def draw_gradient(event=None):
        canvas.delete("gradient")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        
        if width > 1 and height > 1:
            # Simple gradient simulation with bands
            bands = 20
            for i in range(bands):
                # Interpolate between colors
                ratio = i / bands
                r1, g1, b1 = int(start_color[1:3], 16), int(start_color[3:5], 16), int(start_color[5:7], 16)
                r2, g2, b2 = int(end_color[1:3], 16), int(end_color[3:5], 16), int(end_color[5:7], 16)
                
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)
                
                color = f"#{r:02x}{g:02x}{b:02x}"
                y1 = int(height * i / bands)
                y2 = int(height * (i + 1) / bands) + 1
                
                canvas.create_rectangle(0, y1, width, y2, fill=color, outline="", tags="gradient")
    
    canvas.bind("<Configure>", draw_gradient)
    return canvas


# =============================================================================
# MODE-SPECIFIC THEME VARIANTS
# =============================================================================

@dataclass
class ModeThemeVariant:
    """Theme variant for a specific mode (user/developer)."""
    background: str
    card_background: str
    accent: str
    accent_secondary: str
    header_gradient_start: str
    header_gradient_end: str
    text: str
    description: str


# Mode-specific color variations
MODE_VARIANTS: Dict[str, ModeThemeVariant] = {
    'user': ModeThemeVariant(
        background='#1a1b26',
        card_background='#24283b',
        accent='#7aa2f7',         # Blue - friendly, calm
        accent_secondary='#7dcfff',  # Cyan
        header_gradient_start='#1a1b26',
        header_gradient_end='#24283b',
        text='#c0caf5',
        description='Simplified news browsing experience'
    ),
    'developer': ModeThemeVariant(
        background='#16161e',      # Slightly darker for dev mode
        card_background='#1f2335',
        accent='#bb9af7',          # Purple/Magenta - power user
        accent_secondary='#ff9e64',  # Orange
        header_gradient_start='#16161e',
        header_gradient_end='#1f2335',
        text='#a9b1d6',
        description='Full system control and monitoring'
    )
}


def get_mode_theme(mode: str = 'user') -> ModeThemeVariant:
    """
    Get theme variant for specified mode.
    
    Args:
        mode: 'user' or 'developer'
        
    Returns:
        ModeThemeVariant with mode-specific colors
    """
    return MODE_VARIANTS.get(mode, MODE_VARIANTS['user'])


def apply_mode_theme(root, mode: str = 'user') -> None:
    """
    Apply mode-specific theme to root window.
    
    Args:
        root: Tkinter root window
        mode: 'user' or 'developer'
    """
    variant = get_mode_theme(mode)
    root.configure(bg=variant.background)


def get_status_color(status: str) -> str:
    """
    Get appropriate color for status type.
    
    Args:
        status: 'success', 'warning', 'error', 'info'
        
    Returns:
        Hex color string
    """
    return {
        'success': THEME.success,
        'warning': THEME.warning,
        'error': THEME.error,
        'info': THEME.info,
        'critical': THEME.red,
    }.get(status, THEME.fg_dark)

