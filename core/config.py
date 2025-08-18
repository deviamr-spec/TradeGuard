
"""
Configuration management for MT5 trading bot.
Handles MT5 credentials and trading parameters.
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from utils.logging_setup import get_logger

class Config:
    """Configuration manager for MT5 trading bot."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config_file = Path("config.json")
        self.config_data = self._load_config()
        
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
            value = self.config_data
            
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
            config = self.config_data
            
            # Navigate to the parent dictionary
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # Set the value
            config[keys[-1]] = value
            
            # Save configuration
            self._save_config(self.config_data)
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
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return status."""
        issues = []
        warnings = []
        
        try:
            # Check MT5 credentials
            mt5_creds = self.get_mt5_credentials()
            if not any(mt5_creds.values()):
                warnings.append("MT5 credentials not configured - will use auto-detection")
            
            # Check trading symbols
            symbols = self.get("trading.symbols", [])
            if not symbols:
                issues.append("No trading symbols configured")
            
            # Check risk parameters
            max_risk = self.get("trading.max_risk_per_trade", 0)
            if max_risk <= 0 or max_risk > 0.1:
                issues.append("Invalid max risk per trade (should be 0-10%)")
            
            # Check timeframe
            timeframe = self.get("trading.timeframe", "")
            valid_timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
            if timeframe not in valid_timeframes:
                issues.append(f"Invalid timeframe: {timeframe}")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "issues": [f"Configuration validation error: {str(e)}"],
                "warnings": []
            }

# Global configuration instance
config = Config()
