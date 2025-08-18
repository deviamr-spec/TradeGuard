"""
Logging Configuration for MT5 Trading Bot.
Provides structured logging with file rotation and console output.
"""

import os
import sys
import logging
import logging.handlers
from datetime import datetime
from typing import Optional

# Global logger registry
_loggers = {}

def setup_logging(log_level: str = "INFO", 
                 log_file: bool = True,
                 log_dir: str = "logs",
                 max_file_size: int = 10485760,  # 10MB
                 backup_count: int = 5) -> None:
    """
    Set up comprehensive logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Enable file logging
        log_dir: Directory for log files
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup log files to keep
    """
    try:
        # Create logs directory if it doesn't exist
        if log_file and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Convert log level string to constant
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Create root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Console handler with color support
        console_handler = ColoredConsoleHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler with rotation
        if log_file:
            log_filename = os.path.join(log_dir, "mt5_trading_bot.log")
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_filename,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)  # Always debug for file
            file_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(file_handler)
            
            # Create separate error log
            error_log_filename = os.path.join(log_dir, "mt5_trading_bot_errors.log")
            error_handler = logging.handlers.RotatingFileHandler(
                filename=error_log_filename,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(error_handler)
            
            # Create trading activity log
            trading_log_filename = os.path.join(log_dir, "trading_activity.log")
            trading_handler = TradingLogHandler(trading_log_filename, max_file_size, backup_count)
            trading_handler.setLevel(logging.INFO)
            trading_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(trading_handler)
        
        # Log the initialization
        logger = get_logger("logging_setup")
        logger.info(f"🔧 Logging initialized - Level: {log_level}, File: {log_file}")
        
        # Log system information
        logger.info(f"🖥️ Platform: {sys.platform}")
        logger.info(f"🐍 Python: {sys.version.split()[0]}")
        logger.info(f"📂 Working Directory: {os.getcwd()}")
        
    except Exception as e:
        # Fallback to basic console logging if setup fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        logging.error(f"❌ Logging setup failed: {str(e)}")

class ColoredConsoleHandler(logging.StreamHandler):
    """Console handler with color support for different log levels."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[37m',       # White
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def emit(self, record):
        try:
            # Add color if terminal supports it
            if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
                color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
                record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
            
            super().emit(record)
            
        except Exception:
            self.handleError(record)

class TradingLogHandler(logging.handlers.RotatingFileHandler):
    """Specialized handler for trading activities."""
    
    def __init__(self, filename, max_bytes, backup_count):
        super().__init__(filename, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
        self.trading_keywords = [
            'trade', 'order', 'position', 'buy', 'sell', 'profit', 'loss',
            'signal', 'executed', 'closed', 'opened', 'risk', 'balance'
        ]
    
    def emit(self, record):
        try:
            # Only log trading-related messages
            message = record.getMessage().lower()
            if any(keyword in message for keyword in self.trading_keywords):
                super().emit(record)
        except Exception:
            self.handleError(record)

def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the specified name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    try:
        if name not in _loggers:
            logger = logging.getLogger(name)
            _loggers[name] = logger
        
        return _loggers[name]
        
    except Exception as e:
        # Fallback to root logger
        fallback_logger = logging.getLogger()
        fallback_logger.error(f"❌ Failed to get logger '{name}': {str(e)}")
        return fallback_logger

class LogFilter:
    """Custom log filter for specific modules or levels."""
    
    def __init__(self, allowed_modules: Optional[list] = None, min_level: int = logging.INFO):
        self.allowed_modules = allowed_modules or []
        self.min_level = min_level
    
    def filter(self, record):
        """Filter log records based on module and level."""
        try:
            # Check level
            if record.levelno < self.min_level:
                return False
            
            # Check module
            if self.allowed_modules:
                module_match = any(allowed in record.name for allowed in self.allowed_modules)
                if not module_match:
                    return False
            
            return True
            
        except Exception:
            return True  # Allow record through on error

def log_performance(func):
    """Decorator to log function performance."""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = datetime.now()
        
        try:
            result = func(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            logger.debug(f"⏱️ {func.__name__} completed in {duration:.3f}s")
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ {func.__name__} failed after {duration:.3f}s: {str(e)}")
            raise
    
    return wrapper

def log_method_calls(cls):
    """Class decorator to log all method calls."""
    def decorate(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(cls.__module__)
            method_name = func.__name__
            
            if not method_name.startswith('_'):  # Skip private methods
                logger.debug(f"📞 {cls.__name__}.{method_name} called")
            
            return func(*args, **kwargs)
        
        return wrapper
    
    for attr in dir(cls):
        if callable(getattr(cls, attr)) and not attr.startswith("__"):
            setattr(cls, attr, decorate(getattr(cls, attr)))
    
    return cls

def create_trade_logger(trade_id: str) -> logging.Logger:
    """
    Create a specialized logger for individual trades.
    
    Args:
        trade_id: Unique trade identifier
        
    Returns:
        Trade-specific logger
    """
    try:
        logger_name = f"trade.{trade_id}"
        trade_logger = get_logger(logger_name)
        
        # Add trade-specific context
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.trade_id = trade_id
            return record
        
        logging.setLogRecordFactory(record_factory)
        
        return trade_logger
        
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"❌ Failed to create trade logger for {trade_id}: {str(e)}")
        return get_logger("trade.fallback")

# Convenience functions for common logging patterns
def log_startup_info():
    """Log system startup information."""
    logger = get_logger("startup")
    logger.info("=" * 60)
    logger.info("🚀 MT5 Trading Bot Starting Up")
    logger.info(f"📅 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🖥️ Platform: {sys.platform}")
    logger.info(f"🐍 Python Version: {sys.version.split()[0]}")
    logger.info(f"📂 Working Directory: {os.getcwd()}")
    logger.info("=" * 60)

def log_shutdown_info():
    """Log system shutdown information."""
    logger = get_logger("shutdown")
    logger.info("=" * 60)
    logger.info("🛑 MT5 Trading Bot Shutting Down")
    logger.info(f"📅 End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

def log_trade_execution(symbol: str, action: str, volume: float, price: float, result: str):
    """Log trade execution with standardized format."""
    logger = get_logger("trading")
    emoji = "✅" if result == "SUCCESS" else "❌"
    logger.info(f"{emoji} Trade {result}: {action} {volume} {symbol} @ {price}")

def log_connection_status(connected: bool, details: str = ""):
    """Log MT5 connection status changes."""
    logger = get_logger("connection")
    status = "🟢 CONNECTED" if connected else "🔴 DISCONNECTED"
    message = f"MT5 {status}"
    if details:
        message += f" - {details}"
    logger.info(message)

def log_risk_alert(alert_type: str, message: str, severity: str = "WARNING"):
    """Log risk management alerts."""
    logger = get_logger("risk")
    emoji_map = {
        "WARNING": "⚠️",
        "ERROR": "❌", 
        "CRITICAL": "🚨"
    }
    emoji = emoji_map.get(severity, "⚠️")
    
    log_method = getattr(logger, severity.lower(), logger.warning)
    log_method(f"{emoji} RISK ALERT [{alert_type}]: {message}")

