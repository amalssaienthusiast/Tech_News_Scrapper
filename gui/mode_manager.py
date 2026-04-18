"""
Mode Manager - Handles switching between User and Developer modes.

Features:
- Dual-mode operation (user/developer)
- State preservation during mode switches
- Persistent mode preference
- Password-protected developer mode
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ModeState:
    """State preserved during mode switches."""
    scroll_position: float = 0.0
    selected_tab: int = 0
    search_query: str = ""
    filter_settings: Dict[str, Any] = None
    expanded_panels: list = None
    
    def __post_init__(self):
        if self.filter_settings is None:
            self.filter_settings = {}
        if self.expanded_panels is None:
            self.expanded_panels = []


class ModeManager:
    """
    Manages switching between User and Developer modes.
    
    Features:
    - State preservation between switches
    - Persistent mode preference (saved to disk)
    - Password-protected developer access
    """
    
    USER_MODE_CONFIG = {
        'name': 'user',
        'display_name': 'User Mode',
        'icon': '👤',
        'panels': ['news_feed', 'search', 'settings'],
        'description': 'Simplified news browsing experience'
    }
    
    DEVELOPER_MODE_CONFIG = {
        'name': 'developer',
        'display_name': 'Developer Mode',
        'icon': '🛠️',
        'panels': [
            'system_monitor',
            'ai_laboratory',
            'bypass_control',
            'resilience_dashboard',
            'security_tools',
            'debug_console',
            'performance_analytics'
        ],
        'description': 'Full system control and monitoring'
    }
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize mode manager.
        
        Args:
            config_dir: Directory for persistent config (defaults to ~/.technews)
        """
        self.config_dir = config_dir or Path.home() / '.technews'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.config_dir / 'mode_config.json'
        
        # Current state
        self.current_mode = 'user'
        self.mode_states: Dict[str, ModeState] = {
            'user': ModeState(),
            'developer': ModeState()
        }
        
        # Callbacks
        self._on_switch_callbacks: list = []
        
        # Load persistent config
        self._load_config()
        
        logger.info(f"ModeManager initialized with mode: {self.current_mode}")
    
    def _load_config(self) -> None:
        """Load persistent configuration."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.current_mode = data.get('last_mode', 'user')
                    logger.debug(f"Loaded mode preference: {self.current_mode}")
        except Exception as e:
            logger.warning(f"Could not load mode config: {e}")
            self.current_mode = 'user'
    
    def _save_config(self) -> None:
        """Save persistent configuration."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump({
                    'last_mode': self.current_mode,
                    'states': {k: asdict(v) for k, v in self.mode_states.items()}
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save mode config: {e}")
    
    def get_current_mode(self) -> str:
        """Get current mode name."""
        return self.current_mode
    
    def get_mode_config(self, mode: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for a mode."""
        mode = mode or self.current_mode
        if mode == 'developer':
            return self.DEVELOPER_MODE_CONFIG.copy()
        return self.USER_MODE_CONFIG.copy()
    
    def save_state(self, mode: str, state: ModeState) -> None:
        """Save state for a mode."""
        self.mode_states[mode] = state
    
    def get_state(self, mode: str) -> ModeState:
        """Get saved state for a mode."""
        return self.mode_states.get(mode, ModeState())
    
    def switch_mode(self, target_mode: str, current_state: Optional[ModeState] = None) -> Dict[str, Any]:
        """
        Switch to a different mode.
        
        Args:
            target_mode: Mode to switch to ('user' or 'developer')
            current_state: Current state to save before switching
        
        Returns:
            Dict with new mode config and restored state
        """
        if target_mode not in ('user', 'developer'):
            raise ValueError(f"Invalid mode: {target_mode}")
        
        # Save current state
        if current_state:
            self.mode_states[self.current_mode] = current_state
        
        # Switch mode
        old_mode = self.current_mode
        self.current_mode = target_mode
        
        # Get restored state
        restored_state = self.mode_states.get(target_mode, ModeState())
        
        # Save config
        self._save_config()
        
        # Notify callbacks
        for callback in self._on_switch_callbacks:
            try:
                callback(old_mode, target_mode)
            except Exception as e:
                logger.error(f"Mode switch callback error: {e}")
        
        logger.info(f"Switched mode: {old_mode} -> {target_mode}")
        
        return {
            'mode': target_mode,
            'config': self.get_mode_config(target_mode),
            'state': restored_state
        }
    
    def toggle_mode(self, current_state: Optional[ModeState] = None) -> Dict[str, Any]:
        """Toggle between user and developer modes."""
        target = 'developer' if self.current_mode == 'user' else 'user'
        return self.switch_mode(target, current_state)
    
    def on_mode_switch(self, callback: Callable[[str, str], None]) -> None:
        """Register callback for mode switches."""
        self._on_switch_callbacks.append(callback)
    
    def is_developer_mode(self) -> bool:
        """Check if currently in developer mode."""
        return self.current_mode == 'developer'


# Global instance
_mode_manager: Optional[ModeManager] = None


def get_mode_manager() -> ModeManager:
    """Get the global mode manager instance."""
    global _mode_manager
    if _mode_manager is None:
        _mode_manager = ModeManager()
    return _mode_manager
