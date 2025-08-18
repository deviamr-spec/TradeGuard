
"""
Configuration Management Module.
Handles all configuration settings for the trading bot.
"""

import os
import json
from typing import Dict, Any, Optional

class Config:
    """Configuration manager for the trading bot."""

    def __init__(self):
        self.config_file = "config.json"
        self.config_data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                return self._create_default_config()
        except Exception as e:
            print(f"❌ Config load error: {e}")
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration."""
        default_config = {
            "mt5": {
                "path": "",
                "login": 0,
                "password": "",
                "server": ""
            },
            "trading": {
                "symbols": ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"],
                "timeframe": "M1",
                "max_positions": 5,
                "max_daily_loss": 0.05,
                "max_drawdown": 0.10
            },
            "strategy": {
                "ema_fast": 12,
                "ema_slow": 26,
                "rsi_period": 14,
                "rsi_overbought": 70.0,
                "rsi_oversold": 30.0,
                "take_profit_pips": 10.0,
                "stop_loss_pips": 5.0,
                "min_confidence": 60.0
            },
            "risk_management": {
                "risk_per_trade": 0.01,
                "max_spread_pips": 3
            },
            "logging": {
                "level": "INFO",
                "file_logging": True
            }
        }

        # Save default config
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            print(f"❌ Default config save error: {e}")

        return default_config

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        try:
            keys = key.split('.')
            value = self.config_data
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
        except Exception:
            return default

    def get_mt5_credentials(self) -> Dict[str, Any]:
        """Get MT5 connection credentials."""
        return {
            "path": self.get("mt5.path", ""),
            "login": self.get("mt5.login", 0),
            "password": self.get("mt5.password", ""),
            "server": self.get("mt5.server", "")
        }

    def update(self, key: str, value: Any) -> bool:
        """Update configuration value."""
        try:
            keys = key.split('.')
            config_ref = self.config_data
            
            for k in keys[:-1]:
                if k not in config_ref:
                    config_ref[k] = {}
                config_ref = config_ref[k]
            
            config_ref[keys[-1]] = value
            
            # Save updated config
            with open(self.config_file, 'w') as f:
                json.dump(self.config_data, f, indent=4)
            
            return True
        except Exception as e:
            print(f"❌ Config update error: {e}")
            return False

# Global config instance
config = Config()
