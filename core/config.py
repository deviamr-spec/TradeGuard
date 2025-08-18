"""
Configuration management for MT5 trading bot.
Handles MT5 credentials and trading parameters.
"""

import os
from typing import Dict, Any, Optional
from utils.logging_setup import get_logger

class Config:
    """Configuration manager for trading bot settings."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables with fallbacks."""
        config = {
            # MT5 Connection Settings
            "mt5": {
                "login": int(os.getenv("MT5_LOGIN", "0")),  # Will use current MT5 login if 0
                "password": os.getenv("MT5_PASSWORD", ""),
                "server": os.getenv("MT5_SERVER", ""),
                "path": os.getenv("MT5_PATH", "C:\\Program Files\\MetaTrader 5\\terminal64.exe"),
                "timeout": int(os.getenv("MT5_TIMEOUT", "60")),
            },
            
            # Trading Settings
            "trading": {
                "symbols": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"],
                "timeframe": "M1",  # 1-minute for scalping
                "max_positions": int(os.getenv("MAX_POSITIONS", "5")),
                "max_daily_trades": int(os.getenv("MAX_DAILY_TRADES", "50")),
                "trading_hours": {
                    "start": "00:00",
                    "end": "23:59"
                }
            },
            
            # Risk Management
            "risk": {
                "risk_per_trade": float(os.getenv("RISK_PER_TRADE", "0.01")),  # 1% per trade
                "max_daily_loss": float(os.getenv("MAX_DAILY_LOSS", "0.05")),  # 5% daily loss limit
                "max_drawdown": float(os.getenv("MAX_DRAWDOWN", "0.10")),  # 10% max drawdown
                "max_spread": float(os.getenv("MAX_SPREAD", "2.0")),  # 2 pip max spread
                "min_lot_size": float(os.getenv("MIN_LOT_SIZE", "0.01")),
                "max_lot_size": float(os.getenv("MAX_LOT_SIZE", "1.0")),
            },
            
            # Strategy Settings (EMA/RSI Scalping)
            "strategy": {
                "ema_fast": int(os.getenv("EMA_FAST", "12")),
                "ema_slow": int(os.getenv("EMA_SLOW", "26")),
                "rsi_period": int(os.getenv("RSI_PERIOD", "14")),
                "rsi_overbought": float(os.getenv("RSI_OVERBOUGHT", "70.0")),
                "rsi_oversold": float(os.getenv("RSI_OVERSOLD", "30.0")),
                "take_profit_pips": float(os.getenv("TP_PIPS", "10.0")),
                "stop_loss_pips": float(os.getenv("SL_PIPS", "5.0")),
            },
            
            # GUI Settings
            "gui": {
                "update_interval": int(os.getenv("GUI_UPDATE_INTERVAL", "1000")),  # ms
                "theme": os.getenv("GUI_THEME", "dark"),
                "window_width": int(os.getenv("WINDOW_WIDTH", "1200")),
                "window_height": int(os.getenv("WINDOW_HEIGHT", "800")),
            },
            
            # Logging
            "logging": {
                "level": os.getenv("LOG_LEVEL", "INFO"),
                "file_enabled": os.getenv("LOG_FILE_ENABLED", "true").lower() == "true",
                "max_file_size": int(os.getenv("LOG_MAX_FILE_SIZE", "10485760")),  # 10MB
                "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5")),
            }
        }
        
        self.logger.info("✅ Configuration loaded successfully")
        return config
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the configuration value (e.g., 'mt5.login')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            keys = key_path.split('.')
            value = self._config
            
            for key in keys:
                value = value[key]
                
            return value
            
        except (KeyError, TypeError):
            self.logger.warning(f"⚠️ Configuration key '{key_path}' not found, using default: {default}")
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the configuration key
            value: Value to set
        """
        try:
            keys = key_path.split('.')
            config_ref = self._config
            
            # Navigate to parent
            for key in keys[:-1]:
                if key not in config_ref:
                    config_ref[key] = {}
                config_ref = config_ref[key]
                
            # Set final value
            config_ref[keys[-1]] = value
            self.logger.debug(f"📝 Configuration updated: {key_path} = {value}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to set configuration {key_path}: {str(e)}")
    
    def get_mt5_credentials(self) -> Dict[str, Any]:
        """Get MT5 connection credentials."""
        return {
            "login": self.get("mt5.login"),
            "password": self.get("mt5.password"),
            "server": self.get("mt5.server"),
            "path": self.get("mt5.path"),
            "timeout": self.get("mt5.timeout")
        }
    
    def validate_credentials(self) -> bool:
        """Validate MT5 credentials."""
        credentials = self.get_mt5_credentials()
        
        # If login is 0, we'll use auto-detect (current MT5 login)
        if credentials["login"] == 0:
            self.logger.info("🔍 Using auto-detected MT5 login")
            return True
            
        # Check required fields for manual login
        required_fields = ["login", "password", "server"]
        missing_fields = [field for field in required_fields 
                         if not credentials.get(field)]
        
        if missing_fields:
            self.logger.error(f"❌ Missing MT5 credentials: {missing_fields}")
            return False
            
        return True

# Global configuration instance
config = Config()
