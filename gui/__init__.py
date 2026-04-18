
"""
Tech News Scraper GUI Library.

Exports all major components, widgets, and managers for the main application.
"""

from gui.theme import (
    THEME, FONTS, get_font, configure_ttk_styles,
    get_mode_theme, apply_mode_theme, get_status_color,
    ModeThemeVariant, MODE_VARIANTS
)
from gui.security import SecurityManager, PasscodeDialog
from gui.managers.async_runner import AsyncRunner
from gui.widgets.log_panel import LiveLogPanel, RealTimeLogHandler, LogMessage
from gui.widgets.status_banner import LiveStatusBanner
from gui.widgets.status_bar import DynamicStatusBar
from gui.widgets.article_card import ArticleCard
from gui.popups.analysis_view import URLAnalysisPopup
from gui.popups.article_view import FullContentPopup, ArticlePopup
from gui.popups.dialogs import CustomSourcesPopup
from gui.components import ScrollableFrame
from gui.event_manager import RealTimeEventManager, get_event_manager, EventType, GUIEvent
from gui.config_manager import UnifiedConfiguration, get_config
from gui.user_interface import UserInterface
from gui.developer_dashboard import DeveloperDashboard

__all__ = [
    # Theme
    'THEME', 'FONTS', 'get_font', 'configure_ttk_styles',
    'get_mode_theme', 'apply_mode_theme', 'get_status_color',
    'ModeThemeVariant', 'MODE_VARIANTS',
    # Security
    'SecurityManager', 'PasscodeDialog',
    # Managers
    'AsyncRunner',
    'RealTimeEventManager', 'get_event_manager', 'EventType', 'GUIEvent',
    'UnifiedConfiguration', 'get_config',
    # Interfaces
    'UserInterface',
    # Widgets
    'LiveLogPanel', 'RealTimeLogHandler', 'LogMessage',
    'LiveStatusBanner',
    'DynamicStatusBar',
    'ArticleCard',
    # Popups
    'URLAnalysisPopup',
    'FullContentPopup', 'ArticlePopup',
    'CustomSourcesPopup',
    # Components
    'ScrollableFrame',
    # Developer Dashboard
    'DeveloperDashboard',
]


