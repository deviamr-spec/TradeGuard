
#!/usr/bin/env python3
"""
Professional MT5 Automated Trading Bot
Main entry point for the trading application.
Enhanced with cross-platform support and robust error handling.
"""

import sys
import os
import threading
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Check if we're on a system that supports PyQt5
GUI_AVAILABLE = True
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import QTimer
except ImportError:
    GUI_AVAILABLE = False
    print("⚠️ GUI not available - running in console mode")

from utils.logging_setup import setup_logging, get_logger
from utils.diagnostics import run_startup_diagnostics
from core.mt5_client import MT5Client
from core.trade_engine import TradeEngine

if GUI_AVAILABLE:
    from gui.app import TradingBotGUI

class TradingBotApplication:
    """Main trading bot application coordinator with cross-platform support."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.qt_app: Optional[QApplication] = None
        self.main_window = None
        self.mt5_client: Optional[MT5Client] = None
        self.trade_engine: Optional[TradeEngine] = None
        self.running = False
        self.gui_mode = GUI_AVAILABLE
        
    def initialize(self) -> bool:
        """Initialize all application components."""
        try:
            # Setup logging
            setup_logging()
            self.logger.info("🚀 Starting MT5 Trading Bot...")
            
            # Run startup diagnostics
            self.logger.info("🔍 Running startup diagnostics...")
            diagnostic_result = run_startup_diagnostics()
            
            # Initialize Qt Application if available
            if self.gui_mode:
                try:
                    self.qt_app = QApplication(sys.argv)
                    self.qt_app.setApplicationName("MT5 Trading Bot")
                    self.qt_app.setApplicationVersion("1.0.0")
                except Exception as e:
                    self.logger.warning(f"⚠️ GUI initialization failed: {str(e)}")
                    self.gui_mode = False
            
            # Initialize MT5 client
            self.logger.info("🔌 Initializing MT5 client...")
            self.mt5_client = MT5Client()
            
            # Always attempt connection (will fallback to demo mode if needed)
            mt5_connected = self.mt5_client.connect()
            
            if not mt5_connected:
                self.logger.error("❌ MT5 client initialization failed")
                return False
                
            # Initialize trade engine
            self.logger.info("⚙️ Initializing trade engine...")
            try:
                self.trade_engine = TradeEngine(self.mt5_client)
                
                # Start the trading engine
                if self.trade_engine.start():
                    self.logger.info("✅ Trade engine started successfully")
                else:
                    self.logger.warning("⚠️ Trade engine start failed")
                    
            except Exception as e:
                self.logger.error(f"❌ Trade engine initialization failed: {str(e)}")
                return False
                
            # Initialize GUI if available
            if self.gui_mode:
                self.logger.info("🖥️ Launching GUI...")
                try:
                    self.main_window = TradingBotGUI(self.mt5_client, self.trade_engine)
                    
                    # Setup update timer for real-time data (optimized for Windows)
                    self.update_timer = QTimer()
                    self.update_timer.timeout.connect(self._update_data)
                    self.update_timer.start(3000)  # Update every 3 seconds to reduce lag
                    
                    self.logger.info("✅ GUI initialized successfully")
                except Exception as e:
                    self.logger.error(f"❌ GUI initialization failed: {str(e)}")
                    self.gui_mode = False
            
            self.running = True
            self.logger.info("✅ Trading bot initialized successfully")
            
            # Show mode information
            if getattr(self.mt5_client, 'demo_mode', False):
                self.logger.warning("🎭 Running in DEMO MODE with simulated data")
            else:
                self.logger.info("💰 Running in LIVE MODE with real trading")
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {str(e)}")
            return False
    
    def _update_data(self):
        """Update real-time data in GUI."""
        try:
            if self.main_window and self.running and self.gui_mode:
                # Check MT5 connection health
                if self.mt5_client and hasattr(self.mt5_client, 'monitor_connection'):
                    connection_status = self.mt5_client.monitor_connection()
                    if not connection_status.get("healthy", False) and not connection_status.get("demo_mode", False):
                        if hasattr(self.mt5_client, 'auto_reconnect'):
                            self.mt5_client.auto_reconnect()
                
                self.main_window.update_data()
        except Exception as e:
            self.logger.error(f"❌ Data update error: {str(e)}")
    
    def _show_error(self, title: str, message: str):
        """Show error message dialog."""
        if self.qt_app and self.gui_mode:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle(title)
            msg.setText(message)
            msg.exec_()
    
    def _show_demo_mode_info(self):
        """Show demo mode information."""
        if self.qt_app and self.gui_mode:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("🎭 Demo Mode Active")
            msg.setText(
                "🎭 DEMO MODE ACTIVE 🎭\n\n"
                "The bot is running with simulated data because:\n"
                "• MetaTrader5 package is not available on this platform\n"
                "• This is a safe environment for testing\n\n"
                "Features available in demo mode:\n"
                "✅ Strategy analysis and signals\n"
                "✅ Risk management simulation\n"
                "✅ Performance tracking\n"
                "✅ Full GUI functionality\n\n"
                "For live trading, run on Windows with MT5 installed."
            )
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
    
    def run(self) -> int:
        """Run the main application loop."""
        try:
            if not self.initialize():
                return 1
            
            if self.gui_mode:
                # Show demo mode info if applicable
                if getattr(self.mt5_client, 'demo_mode', False):
                    self._show_demo_mode_info()
                
                # Show main window
                if self.main_window:
                    self.main_window.show()
                
                # Start Qt event loop
                self.logger.info("🎯 Trading bot GUI is now running...")
                if self.qt_app:
                    return self.qt_app.exec_()
                return 1
            else:
                # Console mode
                self.logger.info("🎯 Trading bot is running in console mode...")
                self._run_console_mode()
                return 0
            
        except KeyboardInterrupt:
            self.logger.info("🛑 Received keyboard interrupt, shutting down...")
            return 0
        except Exception as e:
            self.logger.error(f"❌ Application error: {str(e)}")
            return 1
        finally:
            self.shutdown()
    
    def _run_console_mode(self):
        """Run in console mode without GUI."""
        try:
            self.logger.info("📊 Console mode - monitoring trading activity...")
            
            while self.running:
                try:
                    # Get basic status
                    if self.trade_engine:
                        status = self.trade_engine.get_engine_status()
                        account_info = status.get("account_info", {})
                        
                        self.logger.info(f"💰 Balance: ${account_info.get('balance', 0):,.2f}")
                        self.logger.info(f"📈 Equity: ${account_info.get('equity', 0):,.2f}")
                        self.logger.info(f"📊 Positions: {status.get('active_positions', 0)}")
                        self.logger.info(f"⚙️ Engine: {'Running' if status.get('running') else 'Stopped'}")
                        self.logger.info(f"🎯 Trading: {'Enabled' if status.get('trading_enabled') else 'Disabled'}")
                    
                    time.sleep(30)  # Update every 30 seconds in console mode
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"❌ Console mode error: {str(e)}")
                    time.sleep(5)
                    
        except Exception as e:
            self.logger.error(f"❌ Console mode fatal error: {str(e)}")
    
    def shutdown(self):
        """Clean shutdown of all components."""
        try:
            self.logger.info("🔄 Shutting down trading bot...")
            self.running = False
            
            # Stop update timer
            if hasattr(self, 'update_timer') and self.gui_mode:
                self.update_timer.stop()
            
            # Stop trade engine
            if self.trade_engine:
                self.trade_engine.stop()
                
            # Disconnect MT5
            if self.mt5_client:
                self.mt5_client.disconnect()
                
            # Close GUI
            if self.main_window and self.gui_mode:
                self.main_window.close()
                
            self.logger.info("✅ Trading bot shutdown complete")
            
        except Exception as e:
            self.logger.error(f"❌ Shutdown error: {str(e)}")

def main():
    """Application entry point."""
    try:
        app = TradingBotApplication()
        exit_code = app.run()
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
