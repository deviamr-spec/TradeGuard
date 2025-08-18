"""
Configuration management for MT5 trading bot.
Handles MT5 credentials and trading parameters.
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from utils.logging_setup import get_logger
from datetime import datetime
import shutil

class Config:
    """Configuration manager for MT5 trading bot."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config_file = Path("config.json")
        self.config = self._load_config() # Renamed from config_data to config for consistency with changes

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                self.logger.info("📁 Configuration loaded from file")
                return config
            else:
                config = self._get_default_config()
                self._save_config(config)
                self.logger.info("📁 Default configuration created")
                return config

        except Exception as e:
            self.logger.error(f"❌ Failed to load config: {str(e)}")
            # Returning default config in case of any loading error
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "mt5": {
                "path": "",
                "login": 0,
                "server": "",
                "password": ""
            },
            "trading": {
                "symbols": ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"],
                "timeframe": "M1",
                "max_positions": 5,
                "max_risk_per_trade": 0.02,
                "max_daily_loss": 0.05,
                "max_drawdown": 0.10,
                "trading_hours": {
                    "start": "00:00",
                    "end": "23:59",
                    "timezone": "UTC"
                }
            },
            "strategy": {
                "name": "Scalping",
                "parameters": {
                    "ema_fast": 12,
                    "ema_slow": 26,
                    "rsi_period": 14,
                    "rsi_overbought": 70,
                    "rsi_oversold": 30,
                    "min_confidence": 60.0
                }
            },
            "risk_management": {
                "use_fixed_lot_size": False,
                "fixed_lot_size": 0.01,
                "risk_per_trade": 0.02,
                "max_spread_pips": 3,
                "slippage_tolerance": 2
            },
            "gui": {
                "update_interval": 1000,
                "chart_history_days": 30,
                "auto_save_reports": True
            },
            "logging": {
                "level": "INFO",
                "max_file_size": "10MB",
                "backup_count": 5
            }
        }

    def _save_config(self, config_data: Dict[str, Any]) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            self.logger.info("💾 Configuration saved")
        except Exception as e:
            self.logger.error(f"❌ Failed to save config: {str(e)}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key."""
        try:
            keys = key.split('.')
            value = self.config # Use self.config directly

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default

            return value

        except Exception as e:
            self.logger.error(f"❌ Failed to get config key {key}: {str(e)}")
            return default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value by dot notation key."""
        try:
            keys = key.split('.')
            config = self.config # Use self.config directly

            # Navigate to the parent dictionary
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]

            # Set the value
            config[keys[-1]] = value

            # Save configuration
            self._save_config(self.config)
            self.logger.info(f"⚙️ Configuration updated: {key} = {value}")

        except Exception as e:
            self.logger.error(f"❌ Failed to set config key {key}: {str(e)}")

    def get_mt5_credentials(self) -> Dict[str, Any]:
        """Get MT5 connection credentials."""
        return {
            "path": self.get("mt5.path", ""),
            "login": self.get("mt5.login", 0),
            "server": self.get("mt5.server", ""),
            "password": self.get("mt5.password", "")
        }

    def update_mt5_credentials(self, credentials: Dict[str, Any]) -> None:
        """Update MT5 credentials."""
        for key, value in credentials.items():
            self.set(f"mt5.{key}", value)

    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading configuration."""
        return self.get("trading", {})

    def get_strategy_config(self) -> Dict[str, Any]:
        """Get strategy configuration."""
        return self.get("strategy", {})

    def get_risk_config(self) -> Dict[str, Any]:
        """Get risk management configuration."""
        return self.get("risk_management", {})

    # --- New/Modified methods from changes ---
    def save_config(self):
        """Save current configuration to file."""
        try:
            # Create backup before saving
            self.create_config_backup()

            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"✅ Configuration saved to {self.config_file}")
        except Exception as e:
            self.logger.error(f"❌ Error saving configuration: {e}")

    def create_config_backup(self):
        """Create backup of current configuration."""
        try:
            if os.path.exists(self.config_file):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = f"{self.config_file}.backup_{timestamp}"
                shutil.copy2(self.config_file, backup_file)
                self.logger.info(f"📁 Config backup created: {backup_file}")
        except Exception as e:
            self.logger.error(f"❌ Error creating config backup: {e}")

    def update_runtime_parameter(self, section: str, key: str, value: Any):
        """Update configuration parameter at runtime."""
        try:
            if section not in self.config:
                self.config[section] = {}

            old_value = self.config[section].get(key)
            self.config[section][key] = value

            self.logger.info(f"🔧 Runtime config update: {section}.{key} = {value} (was: {old_value})")

            # Auto-save for critical parameters
            critical_sections = ['trading', 'risk']
            if section in critical_sections:
                self.save_config()

        except Exception as e:
            self.logger.error(f"❌ Error updating runtime parameter: {e}")

    def validate_config(self) -> bool: # Return type changed to bool as per new method
        """Validate configuration integrity."""
        try:
            required_sections = ['mt5', 'trading', 'strategy', 'risk_management'] # Corrected 'risk' to 'risk_management' to match default config structure

            for section in required_sections:
                if section not in self.config:
                    self.logger.error(f"❌ Missing required config section: {section}")
                    return False

            # Validate MT5 credentials - check if any of the fields are empty
            mt5_creds = self.get_mt5_credentials()
            if not all(mt5_creds.values()):
                 # Allowing empty credentials if auto-detection is intended, but warning about it
                 # For strict validation, uncomment the following and adjust the warning logic
                 # self.logger.error("❌ Incomplete MT5 credentials provided.")
                 # return False
                 self.logger.warning("MT5 credentials are not fully configured. Auto-detection will be used if possible.")


            # Validate numeric ranges and specific values
            trading_config = self.config.get('trading', {})
            risk_config = self.config.get('risk_management', {}) # Use correct key

            max_positions = trading_config.get('max_positions', 0)
            if max_positions <= 0:
                self.logger.error("❌ Invalid max_positions value in 'trading' section. Must be greater than 0.")
                return False

            max_risk_per_trade = risk_config.get('max_risk_per_trade', 0)
            if not (0 < max_risk_per_trade <= 0.1): # Changed condition to match typical risk percentages (0% to 10%)
                self.logger.error("❌ Invalid max_risk_per_trade value in 'risk_management' section. Must be between 0 (exclusive) and 0.1 (inclusive).")
                return False

            # Validate timeframe
            timeframe = trading_config.get('timeframe', '')
            valid_timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "MN", "W1"] # Added more common timeframes
            if timeframe not in valid_timeframes:
                self.logger.error(f"❌ Invalid timeframe '{timeframe}' in 'trading' section. Valid timeframes are: {valid_timeframes}")
                return False

            # Validate trading hours
            trading_hours = trading_config.get('trading_hours', {})
            if not all(k in trading_hours for k in ['start', 'end', 'timezone']):
                self.logger.error("❌ 'trading_hours' section is incomplete in 'trading' config.")
                return False
            # Further validation on time format could be added here if needed


            self.logger.info("✅ Configuration validation passed")
            return True

        except Exception as e:
            self.logger.error(f"❌ Config validation error: {e}")
            return False

# Global configuration instance
config = Config()