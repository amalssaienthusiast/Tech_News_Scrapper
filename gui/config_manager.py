"""
Unified Configuration System - Central configuration management.

Provides single pane of glass for all system settings:
- System configuration (timeouts, caching, logging)
- AI configuration (providers, models, limits)
- Bypass configuration (techniques, rate limiting)
- Resilience configuration (auto-fix, monitoring)
- User preferences (display, notifications)
"""

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class SystemConfig:
    """System-wide configuration."""
    max_concurrent_scrapes: int = 5
    request_timeout_seconds: int = 30
    enable_cache: bool = True
    cache_ttl_seconds: int = 300
    log_level: str = "INFO"
    auto_start_feed: bool = True


@dataclass  
class AIConfig:
    """AI subsystem configuration."""
    primary_provider: str = "gemini"
    default_model: str = "gemini-pro"
    daily_cost_limit_usd: float = 10.0
    enable_summaries: bool = True
    enable_sentiment: bool = True
    cache_responses: bool = True


@dataclass
class BypassConfig:
    """Bypass engine configuration."""
    enable_stealth: bool = True
    enable_proxy_rotation: bool = False
    max_retries: int = 3
    backoff_factor: float = 1.5
    user_agent_rotation: bool = True
    respect_robots_txt: bool = True


@dataclass
class ResilienceConfig:
    """Resilience system configuration."""
    enable_auto_fix: bool = True
    enable_monitoring: bool = True
    health_check_interval_seconds: int = 300
    max_issues_before_alert: int = 5
    enable_deprecation_warnings: bool = True


@dataclass
class UserConfig:
    """User preference configuration."""
    theme_variant: str = "user"
    articles_per_page: int = 20
    enable_notifications: bool = True
    auto_refresh_interval_seconds: int = 300
    show_ai_summaries: bool = True
    compact_mode: bool = False


@dataclass
class UnifiedConfig:
    """Complete unified configuration."""
    system: SystemConfig = field(default_factory=SystemConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    bypass: BypassConfig = field(default_factory=BypassConfig)
    resilience: ResilienceConfig = field(default_factory=ResilienceConfig)
    user: UserConfig = field(default_factory=UserConfig)
    last_modified: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'system': asdict(self.system),
            'ai': asdict(self.ai),
            'bypass': asdict(self.bypass),
            'resilience': asdict(self.resilience),
            'user': asdict(self.user),
            'last_modified': self.last_modified
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedConfig':
        """Create from dictionary."""
        return cls(
            system=SystemConfig(**data.get('system', {})),
            ai=AIConfig(**data.get('ai', {})),
            bypass=BypassConfig(**data.get('bypass', {})),
            resilience=ResilienceConfig(**data.get('resilience', {})),
            user=UserConfig(**data.get('user', {})),
            last_modified=data.get('last_modified', '')
        )


class UnifiedConfiguration:
    """
    Central configuration management for all modules.
    
    Features:
    - Persistent storage in ~/.technews/config.json
    - Real-time configuration updates
    - Change notification callbacks
    - Export/import functionality
    
    Usage:
        config = UnifiedConfiguration()
        
        # Get values
        timeout = config.get('system.request_timeout_seconds')
        
        # Set values
        config.set('ai.enable_summaries', False)
        
        # Subscribe to changes
        config.on_change('system', my_handler)
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory for config storage (default ~/.technews)
        """
        self.config_dir = config_dir or Path.home() / '.technews'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.config_dir / 'unified_config.json'
        
        # Current configuration
        self._config = UnifiedConfig()
        
        # Change callbacks
        self._change_callbacks: Dict[str, List[Callable]] = {
            'system': [],
            'ai': [],
            'bypass': [],
            'resilience': [],
            'user': [],
            '*': []  # Global callbacks
        }
        
        # Load existing configuration
        self._load()
        
        logger.info(f"UnifiedConfiguration loaded from {self.config_file}")
    
    def _load(self) -> None:
        """Load configuration from disk."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self._config = UnifiedConfig.from_dict(data)
                    logger.debug("Configuration loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load config: {e}, using defaults")
            self._config = UnifiedConfig()
    
    def _save(self) -> None:
        """Save configuration to disk."""
        try:
            self._config.last_modified = datetime.now(timezone.utc).isoformat()
            with open(self.config_file, 'w') as f:
                json.dump(self._config.to_dict(), f, indent=2)
            logger.debug("Configuration saved")
        except Exception as e:
            logger.error(f"Could not save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notated key.
        
        Args:
            key: e.g., 'system.max_concurrent_scrapes'
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            parts = key.split('.')
            obj = self._config
            
            for part in parts:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                else:
                    return default
            
            return obj
        except Exception:
            return default
    
    def set(self, key: str, value: Any, save: bool = True) -> bool:
        """
        Set configuration value by dot-notated key.
        
        Args:
            key: e.g., 'system.max_concurrent_scrapes'
            value: New value
            save: Whether to persist immediately
            
        Returns:
            True if successful
        """
        try:
            parts = key.split('.')
            if len(parts) < 2:
                return False
            
            section = parts[0]
            attr = parts[1]
            
            section_obj = getattr(self._config, section, None)
            if section_obj is None:
                return False
            
            if hasattr(section_obj, attr):
                setattr(section_obj, attr, value)
                
                if save:
                    self._save()
                
                # Notify callbacks
                self._notify_change(section, attr, value)
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error setting config {key}: {e}")
            return False
    
    def get_section(self, section: str) -> Optional[Any]:
        """Get entire configuration section."""
        return getattr(self._config, section, None)
    
    def on_change(self, section: str, callback: Callable[[str, Any], None]) -> None:
        """
        Register callback for configuration changes.
        
        Args:
            section: Section to watch ('system', 'ai', etc.) or '*' for all
            callback: Function(attr_name, new_value) to call on change
        """
        if section in self._change_callbacks:
            self._change_callbacks[section].append(callback)
    
    def _notify_change(self, section: str, attr: str, value: Any) -> None:
        """Notify callbacks of configuration change."""
        # Section-specific callbacks
        for callback in self._change_callbacks.get(section, []):
            try:
                callback(attr, value)
            except Exception as e:
                logger.error(f"Config callback error: {e}")
        
        # Global callbacks
        for callback in self._change_callbacks.get('*', []):
            try:
                callback(f"{section}.{attr}", value)
            except Exception as e:
                logger.error(f"Global config callback error: {e}")
    
    def export_config(self, filepath: Path) -> bool:
        """Export configuration to file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self._config.to_dict(), f, indent=2)
            logger.info(f"Configuration exported to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def import_config(self, filepath: Path) -> bool:
        """Import configuration from file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self._config = UnifiedConfig.from_dict(data)
            self._save()
            
            # Notify all sections of potential changes
            for section in ['system', 'ai', 'bypass', 'resilience', 'user']:
                self._notify_change(section, '*', getattr(self._config, section))
            
            logger.info(f"Configuration imported from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False
    
    def reset_to_defaults(self, section: Optional[str] = None) -> None:
        """Reset configuration to defaults."""
        if section:
            default_section = {
                'system': SystemConfig(),
                'ai': AIConfig(),
                'bypass': BypassConfig(),
                'resilience': ResilienceConfig(),
                'user': UserConfig()
            }.get(section)
            
            if default_section:
                setattr(self._config, section, default_section)
                self._notify_change(section, '*', default_section)
        else:
            self._config = UnifiedConfig()
            for section in ['system', 'ai', 'bypass', 'resilience', 'user']:
                self._notify_change(section, '*', getattr(self._config, section))
        
        self._save()
        logger.info(f"Configuration reset to defaults: {section or 'all'}")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration."""
        return {
            'last_modified': self._config.last_modified,
            'sections': {
                'system': asdict(self._config.system),
                'ai': asdict(self._config.ai),
                'bypass': asdict(self._config.bypass),
                'resilience': asdict(self._config.resilience),
                'user': asdict(self._config.user)
            }
        }


# Singleton instance
_config_manager: Optional[UnifiedConfiguration] = None


def get_config() -> UnifiedConfiguration:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = UnifiedConfiguration()
    return _config_manager
