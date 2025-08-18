#!/usr/bin/env python3
"""
Professional MT5 Automated Trading Bot
Main entry point for the trading application.
"""

import sys
import os
import threading
from typing import Optional
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logging_setup import setup_logging, get_logger
from utils.diagnostics import run_startup_diagnostics
from core.mt5_client import MT5Client
from core.trade_engine import TradeEngine
from gui.app import TradingBotGUI

# Check and install MetaTrader5 if missing
try:
    import MetaTrader5 as mt5
except ImportError:
    import subprocess
    import sys
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "MetaTrader5"])
        import MetaTrader5 as mt5
    except Exception as e:
        print(f"Warning: Could not install MetaTrader5: {e}")
        print("Bot will run in demo mode without MT5 connectivity")

class TradingBotApplication:
    """Main trading bot application coordinator."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.qt_app: Optional[QApplication] = None
        self.main_window: Optional[TradingBotGUI] = None
        self.mt5_client: Optional[MT5Client] = None
        self.trade_engine: Optional[TradeEngine] = None
        self.running = False
        
    def initialize(self) -> bool:
        """Initialize all application components."""
        try:
            # Setup logging
            setup_logging()
            self.logger.info("🚀 Starting MT5 Trading Bot...")
            
            # Run startup diagnostics
            self.logger.info("🔍 Running startup diagnostics...")
            if not run_startup_diagnostics():
                self.logger.error("❌ Startup diagnostics failed")
                return False
                
            # Initialize Qt Application
            self.qt_app = QApplication(sys.argv)
            self.qt_app.setApplicationName("MT5 Trading Bot")
            self.qt_app.setApplicationVersion("1.0.0")
            
            # Initialize MT5 client
            self.logger.info("🔌 Connecting to MetaTrader 5...")
            self.mt5_client = MT5Client()
            mt5_connected = self.mt5_client.connect()
            
            if not mt5_connected:
                self.logger.error("❌ MT5 connection failed - LIVE TRADING REQUIRES MT5 CONNECTION")
                self.logger.error("💡 This bot is configured for LIVE TRADING with real money")
                self._show_error("MT5 Connection Required", 
                    "This bot requires MetaTrader 5 connection for live trading.\n"
                    "Please ensure MT5 is installed and running with live account.")
                return False
                
            # Initialize trade engine
            self.logger.info("⚙️ Initializing trade engine...")
            try:
                from core.trade_engine import TradeEngine
                self.trade_engine = TradeEngine(self.mt5_client)
                self.logger.info("✅ Trade engine initialized successfully")
            except Exception as e:
                self.logger.error(f"❌ Trade engine initialization failed: {str(e)}")
                self.logger.info("🔄 Creating basic trade engine for GUI compatibility...")
                # Create a minimal trade engine for GUI compatibility
                from core.trade_engine import TradeEngine
                self.trade_engine = TradeEngine(self.mt5_client)
                
            # Ensure all required attributes exist
            if not hasattr(self.trade_engine, 'symbols'):
                self.trade_engine.symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD"]
            if not hasattr(self.trade_engine, 'running'):
                self.trade_engine.running = False
            if not hasattr(self.trade_engine, 'trading_enabled'):
                self.trade_engine.trading_enabled = False
            if not hasattr(self.trade_engine, 'emergency_stop'):
                def emergency_stop():
                    self.trade_engine.trading_enabled = False
                    self.trade_engine.running = False
                    if hasattr(self.trade_engine, '_emergency_close_all_positions'):
                        self.trade_engine._emergency_close_all_positions()
                self.trade_engine.emergency_stop = emergency_stop
            
            # Initialize main GUI window
            self.logger.info("🖥️ Launching GUI...")
            try:
                self.main_window = TradingBotGUI(self.mt5_client, self.trade_engine)
                self.logger.info("✅ GUI initialized successfully")
            except Exception as e:
                self.logger.error(f"❌ GUI initialization failed: {str(e)}")
                raise
            
            # Setup update timer for real-time data
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self._update_data)
            self.update_timer.start(1000)  # Update every second
            
            self.running = True
            self.logger.info("✅ Trading bot initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {str(e)}")
            self._show_error("Initialization Error", f"Failed to initialize trading bot:\n{str(e)}")
            return False
    
    def _update_data(self):
        """Update real-time data in GUI."""
        try:
            if self.main_window and self.running:
                # Check MT5 connection health
                if self.mt5_client and hasattr(self.mt5_client, 'is_connection_healthy'):
                    if not self.mt5_client.is_connection_healthy():
                        self.logger.warning("⚠️ MT5 connection unhealthy, attempting reconnection...")
                        if hasattr(self.mt5_client, 'auto_reconnect'):
                            self.mt5_client.auto_reconnect()
                
                self.main_window.update_data()
        except Exception as e:
            self.logger.error(f"❌ Data update error: {str(e)}")
    
    def _show_error(self, title: str, message: str):
        """Show error message dialog."""
        if self.qt_app:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle(title)
            msg.setText(message)
            msg.exec_()
    
    def _show_live_trading_warning(self):
        """Show live trading warning dialog."""
        if self.qt_app:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("🚨 LIVE TRADING WARNING")
            msg.setText(
                "⚠️ WARNING: LIVE TRADING WITH REAL MONEY ⚠️\n\n"
                "This bot will trade with REAL MONEY on your LIVE trading account.\n"
                "You can lose significant amounts of money.\n\n"
                "Make sure you:\n"
                "• Have tested the strategy thoroughly\n"
                "• Understand the risks involved\n"
                "• Have proper risk management settings\n"
                "• Monitor the bot continuously\n\n"
                "USE AT YOUR OWN RISK!"
            )
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
    
    def run(self) -> int:
        """Run the main application loop."""
        try:
            if not self.initialize():
                return 1
                
            # Show live trading warning
            self._show_live_trading_warning()
            
            # Show main window
            if self.main_window:
                self.main_window.show()
            
            # Start Qt event loop
            self.logger.info("🎯 LIVE TRADING BOT is now running...")
            if self.qt_app:
                return self.qt_app.exec_()
            return 1
            
        except KeyboardInterrupt:
            self.logger.info("🛑 Received keyboard interrupt, shutting down...")
            return 0
        except Exception as e:
            self.logger.error(f"❌ Application error: {str(e)}")
            return 1
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of all components."""
        try:
            self.logger.info("🔄 Shutting down trading bot...")
            self.running = False
            
            # Stop update timer
            if hasattr(self, 'update_timer'):
                self.update_timer.stop()
            
            # Stop trade engine
            if self.trade_engine:
                self.trade_engine.stop()
                
            # Disconnect MT5
            if self.mt5_client:
                self.mt5_client.disconnect()
                
            # Close GUI
            if self.main_window:
                self.main_window.close()
                
            self.logger.info("✅ Trading bot shutdown complete")
            
        except Exception as e:
            self.logger.error(f"❌ Shutdown error: {str(e)}")

def main():
    """Application entry point."""
    app = TradingBotApplication()
    exit_code = app.run()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
