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
from gui.app import MainWindow

class TradingBotApplication:
    """Main trading bot application coordinator."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.qt_app: Optional[QApplication] = None
        self.main_window: Optional[MainWindow] = None
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
                self.logger.warning("⚠️ MT5 connection failed - running in demo mode")
                self.logger.warning("💡 Demo mode will show simulated trading data")
                
            # Initialize trade engine
            self.logger.info("⚙️ Initializing trade engine...")
            self.trade_engine = TradeEngine(self.mt5_client)
            
            # Initialize main GUI window
            self.logger.info("🖥️ Launching GUI...")
            self.main_window = MainWindow(self.mt5_client, self.trade_engine)
            
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
    
    def run(self) -> int:
        """Run the main application loop."""
        try:
            if not self.initialize():
                return 1
                
            # Show main window
            self.main_window.show()
            
            # Start Qt event loop
            self.logger.info("🎯 Trading bot is now running...")
            return self.qt_app.exec_()
            
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
