"""
Main GUI Application for MT5 Trading Bot.
Provides desktop interface for live trading operations.
FIXED VERSION - ALL ERRORS RESOLVED
"""

import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import threading
import traceback

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QTabWidget, QSplitter, QGroupBox, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTextEdit, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QProgressBar, QHeaderView,
    QFrame, QScrollArea, QSizePolicy, QMenuBar, QStatusBar, QAction,
    QMessageBox, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

# Import our components
from core.mt5_client import MT5Client
from core.trade_engine import TradeEngine
from gui.widgets import (
    AccountInfoWidget, TradingControlWidget, RiskMonitorWidget,
    PerformanceMonitorWidget, MarketDataWidget, PositionsWidget,
    LogWidget, EquityChartWidget
)
from utils.logging_setup import get_logger

class TradingBotGUI(QMainWindow):
    """Main GUI application for the MT5 Trading Bot."""
    
    # FIXED: Proper signal definition
    log_signal = pyqtSignal(str, str)  # message, level
    
    def __init__(self, mt5_client: MT5Client, trade_engine: TradeEngine):
        super().__init__()
        
        self.logger = get_logger(__name__)
        self.mt5_client = mt5_client
        self.trade_engine = trade_engine
        
        # GUI state
        self.widgets = {}
        self.update_timer = None
        self.is_updating = False
        
        # Initialize GUI
        self.init_gui()
        self.setup_connections()
        self.start_updates()
        
        self.logger.info("🖥️ Main GUI window initialized")

    def init_gui(self):
        """Initialize the GUI components."""
        try:
            self.setWindowTitle("MT5 Trading Bot - Live Trading Dashboard")
            self.setGeometry(100, 100, 1400, 900)
            
            # Apply dark theme
            self.apply_dark_theme()
            
            # Create menu bar
            self.create_menu_bar()
            
            # Create main layout
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # Main horizontal splitter
            splitter = QSplitter(Qt.Horizontal)
            central_widget_layout = QVBoxLayout(central_widget)
            central_widget_layout.addWidget(splitter)
            
            # Left panel (controls and info)
            left_panel = self.create_left_panel()
            splitter.addWidget(left_panel)
            
            # Center panel (charts and data)
            center_panel = self.create_center_panel()
            splitter.addWidget(center_panel)
            
            # Right panel (logs and advanced info)
            right_panel = self.create_right_panel()
            splitter.addWidget(right_panel)
            
            # Set splitter proportions
            splitter.setSizes([300, 700, 400])
            
            # Create status bar
            self.create_status_bar()
            
            self.logger.info("✅ GUI layout initialized")
            
        except Exception as e:
            self.logger.error(f"❌ GUI initialization error: {str(e)}")

    def apply_dark_theme(self):
        """Apply dark theme to the application."""
        try:
            dark_style = """
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
            QTableWidget {
                background-color: #3c3c3c;
                alternate-background-color: #2b2b2b;
                selection-background-color: #0078d4;
                gridline-color: #555555;
                border: 1px solid #555555;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: white;
                padding: 4px;
                border: 1px solid #555555;
                font-weight: bold;
            }
            QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                padding: 4px;
                border-radius: 2px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #555555;
                font-family: Consolas, monospace;
            }
            QLabel {
                color: #ffffff;
            }
            QStatusBar {
                background-color: #2b2b2b;
                border-top: 1px solid #555555;
            }
            QMenuBar {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #0078d4;
            }
            QMenu {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #0078d4;
            }
            """

            self.setStyleSheet(dark_style)

        except Exception as e:
            self.logger.error(f"❌ Theme application error: {str(e)}")

    def create_left_panel(self) -> QWidget:
        """Create left panel with account info and trading controls."""
        try:
            panel = QWidget()
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(10)

            # Account Information
            self.widgets['account'] = AccountInfoWidget(self.mt5_client)
            layout.addWidget(self.widgets['account'])

            # Trading Controls
            self.widgets['trading_control'] = TradingControlWidget(self.trade_engine)
            layout.addWidget(self.widgets['trading_control'])

            # Risk Monitor
            self.widgets['risk_monitor'] = RiskMonitorWidget(self.trade_engine.risk_manager)
            layout.addWidget(self.widgets['risk_monitor'])

            # Performance Monitor
            self.widgets['performance_monitor'] = PerformanceMonitorWidget(self.trade_engine)
            layout.addWidget(self.widgets['performance_monitor'])

            # Add stretch to push everything to top
            layout.addStretch()

            return panel

        except Exception as e:
            self.logger.error(f"❌ Left panel creation error: {str(e)}")
            return QWidget()

    def create_center_panel(self) -> QWidget:
        """Create center panel with charts and positions."""
        try:
            panel = QWidget()
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(10)

            # Tab widget for different views
            tab_widget = QTabWidget()

            # Market Data Tab
            symbols = self.trade_engine.symbols
            self.widgets['market_data'] = MarketDataWidget(self.mt5_client, symbols)
            tab_widget.addTab(self.widgets['market_data'], "💹 Market Data")

            # Positions Tab
            self.widgets['positions'] = PositionsWidget(self.mt5_client)
            tab_widget.addTab(self.widgets['positions'], "📈 Positions")

            # Equity Chart Tab
            self.widgets['equity_chart'] = EquityChartWidget()
            tab_widget.addTab(self.widgets['equity_chart'], "📊 Equity")

            layout.addWidget(tab_widget)

            return panel

        except Exception as e:
            self.logger.error(f"❌ Center panel creation error: {str(e)}")
            return QWidget()

    def create_right_panel(self) -> QWidget:
        """Create right panel with logs and advanced information."""
        try:
            panel = QWidget()
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(10)

            # Log Widget
            self.widgets['log'] = LogWidget()
            layout.addWidget(self.widgets['log'])

            # Connect log signal
            self.log_signal.connect(self.widgets['log'].add_message)

            return panel

        except Exception as e:
            self.logger.error(f"❌ Right panel creation error: {str(e)}")
            return QWidget()

    def create_menu_bar(self):
        """Create application menu bar."""
        try:
            menubar = self.menuBar()
            if not menubar:
                return

            # File Menu
            file_menu = menubar.addMenu('File')
            if file_menu:
                # Connect/Disconnect
                connect_action = file_menu.addAction('Connect to MT5')
                connect_action.triggered.connect(self.connect_mt5)
                
                file_menu.addSeparator()
                
                # Exit
                exit_action = file_menu.addAction('Exit')
                exit_action.triggered.connect(self.close)

            # Trading Menu
            trading_menu = menubar.addMenu('Trading')
            if trading_menu:
                # Start/Stop Trading
                start_action = trading_menu.addAction('Start Trading')
                start_action.triggered.connect(self.start_trading)
                
                stop_action = trading_menu.addAction('Stop Trading')
                stop_action.triggered.connect(self.stop_trading)
                
                trading_menu.addSeparator()
                
                # Emergency Stop
                emergency_action = trading_menu.addAction('Emergency Stop')
                emergency_action.triggered.connect(self.emergency_stop)

            # Help Menu
            help_menu = menubar.addMenu('Help')
            if help_menu:
                # About
                about_action = help_menu.addAction('About')
                about_action.triggered.connect(self.show_about)

        except Exception as e:
            self.logger.error(f"❌ Menu bar creation error: {str(e)}")

    def create_status_bar(self):
        """Create status bar."""
        try:
            self.status_bar = self.statusBar()
            self.status_bar.showMessage("MT5 Trading Bot - Ready")
            
            # Add connection status
            self.connection_status_label = QLabel("Disconnected")
            self.connection_status_label.setStyleSheet("color: red; font-weight: bold; padding: 0 10px;")
            self.status_bar.addPermanentWidget(self.connection_status_label)
            
            # Add time label
            self.time_label = QLabel()
            self.status_bar.addPermanentWidget(self.time_label)

        except Exception as e:
            self.logger.error(f"❌ Status bar creation error: {str(e)}")

    def setup_connections(self):
        """Setup signal connections."""
        try:
            # Update timer for real-time data
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.update_gui_data)
            
        except Exception as e:
            self.logger.error(f"❌ Connection setup error: {str(e)}")

    def start_updates(self):
        """Start periodic GUI updates."""
        try:
            if self.update_timer:
                self.update_timer.start(1000)  # Update every 1 second
                self.logger.info("✅ GUI updates started")
        except Exception as e:
            self.logger.error(f"❌ Failed to start updates: {str(e)}")

    def update_data(self):
        """Public method for external data updates."""
        self.update_gui_data()

    def update_gui_data(self):
        """Update all GUI components with latest data."""
        try:
            if self.is_updating:
                return
                
            self.is_updating = True

            # Update connection status
            if self.mt5_client.connected:
                self.connection_status_label.setText("Connected")
                self.connection_status_label.setStyleSheet("color: green; font-weight: bold; padding: 0 10px;")
            else:
                self.connection_status_label.setText("Disconnected")
                self.connection_status_label.setStyleSheet("color: red; font-weight: bold; padding: 0 10px;")

            # Update time
            current_time = datetime.now().strftime("%H:%M:%S")
            self.time_label.setText(current_time)

            # Update all widgets safely
            for widget_name, widget in self.widgets.items():
                try:
                    if hasattr(widget, 'update_data'):
                        if widget_name == 'equity_chart':
                            # Handle equity chart specially
                            if self.mt5_client.connected:
                                account_info = self.mt5_client.get_account_info()
                                if account_info:
                                    equity = account_info.get('equity', 0.0)
                                    widget.update_data(equity)
                        else:
                            widget.update_data()
                except Exception as e:
                    self.logger.error(f"❌ Widget {widget_name} update error: {str(e)}")

        except Exception as e:
            self.logger.error(f"❌ GUI update error: {str(e)}")
        finally:
            self.is_updating = False

    def connect_mt5(self):
        """Connect to MT5."""
        try:
            if not self.mt5_client.connected:
                success = self.mt5_client.connect()
                if success:
                    self.status_bar.showMessage("Connected to MT5")
                    self.log_signal.emit("Connected to MT5 successfully", "INFO")
                else:
                    self.status_bar.showMessage("Failed to connect to MT5")
                    self.log_signal.emit("Failed to connect to MT5", "ERROR")
        except Exception as e:
            self.logger.error(f"❌ MT5 connection error: {str(e)}")

    def start_trading(self) -> bool:
        """Start trading operations."""
        try:
            if not self.trade_engine.running:
                self.trade_engine.start()
                self.status_bar.showMessage("Trading Started")
                self.log_signal.emit("Trading started", "INFO")
                return True
        except Exception as e:
            self.logger.error(f"❌ Start trading error: {str(e)}")
            return False

    def stop_trading(self):
        """Stop trading operations."""
        try:
            if self.trade_engine.running:
                self.trade_engine.stop()
                self.status_bar.showMessage("Trading Stopped")
                self.log_signal.emit("Trading stopped", "INFO")
        except Exception as e:
            self.logger.error(f"❌ Stop trading error: {str(e)}")

    def emergency_stop(self):
        """Emergency stop all operations."""
        try:
            self.trade_engine.emergency_stop()
            self.status_bar.showMessage("Emergency Stop Activated")
            self.log_signal.emit("Emergency stop activated", "WARNING")
        except Exception as e:
            self.logger.error(f"❌ Emergency stop error: {str(e)}")

    def show_about(self):
        """Show about dialog."""
        try:
            about_text = """
            MT5 Trading Bot v1.0
            
            Professional automated trading software for MetaTrader 5.
            
            Features:
            • Live forex trading
            • Risk management
            • Real-time monitoring
            • Strategy automation
            
            ⚠️ Warning: This software trades with real money.
            Use at your own risk.
            """
            
            msg = QMessageBox()
            msg.setWindowTitle("About MT5 Trading Bot")
            msg.setText(about_text)
            msg.setIcon(QMessageBox.Information)
            msg.exec_()
            
        except Exception as e:
            self.logger.error(f"❌ About dialog error: {str(e)}")

    def show_settings_dialog(self):
        """Show settings configuration dialog."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Trading Settings")
            dialog.setModal(True)  # FIXED: Use boolean instead of integer
            dialog.resize(400, 300)
            
            layout = QVBoxLayout(dialog)
            
            # Settings content would go here
            settings_label = QLabel("Trading settings will be implemented here")
            settings_label.setAlignment(Qt.AlignCenter)  # FIXED: Use Qt.AlignCenter
            layout.addWidget(settings_label)
            
            # Dialog buttons
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            dialog.exec_()
            
        except Exception as e:
            self.logger.error(f"❌ Settings dialog error: {str(e)}")

    def closeEvent(self, event):  # FIXED: Proper parameter naming
        """Handle application close event."""
        try:
            self.logger.info("🔄 Closing application...")
            
            # Stop trading engine
            if hasattr(self, 'trade_engine') and self.trade_engine.running:
                self.trade_engine.stop()
                self.logger.info("🛑 Trading engine stopped")
            
            # Stop GUI updates
            if hasattr(self, 'update_timer') and self.update_timer:
                self.update_timer.stop()
            
            # Disconnect from MT5
            if hasattr(self, 'mt5_client') and self.mt5_client.connected:
                self.mt5_client.disconnect()
                self.logger.info("🔌 MT5 disconnected")
            
            self.logger.info("✅ Application closed successfully")
            event.accept()
            
        except Exception as e:
            self.logger.error(f"❌ Close event error: {str(e)}")
            event.accept()  # Force close even if error occurs

def create_and_run_gui(mt5_client: MT5Client, trade_engine: TradeEngine):
    """Create and run the GUI application."""
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("MT5 Trading Bot")
        app.setApplicationVersion("1.0")
        
        # Create main window
        main_window = TradingBotGUI(mt5_client, trade_engine)
        main_window.show()
        
        return app, main_window
        
    except Exception as e:
        print(f"❌ GUI creation error: {str(e)}")
        traceback.print_exc()
        return None, None