"""
Main GUI Application for MT5 Trading Bot.
PyQt5-based interface with real-time trading dashboard.
"""

import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import threading

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QTextEdit, QProgressBar, QGroupBox, QScrollArea, QSplitter,
    QMessageBox, QStatusBar, QMenuBar, QAction, QHeaderView,
    QFrame, QSizePolicy
)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt, QSize
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QPainter, QPen

from core.mt5_client import MT5Client
from core.trade_engine import TradeEngine
from gui.widgets import (
    AccountInfoWidget, PositionsWidget, EquityChartWidget,
    TradingControlWidget, LogWidget, StrategyStatsWidget,
    RiskMonitorWidget
)
from utils.logging_setup import get_logger

class MainWindow(QMainWindow):
    """Main trading bot GUI window."""
    
    def __init__(self, mt5_client: MT5Client, trade_engine: TradeEngine):
        super().__init__()
        
        self.logger = get_logger(__name__)
        self.mt5_client = mt5_client
        self.trade_engine = trade_engine
        
        # GUI state
        self.update_timer = None
        self.last_update = datetime.now()
        self.gui_thread_id = threading.current_thread().ident
        
        # Initialize UI
        self.init_ui()
        self.setup_timers()
        self.connect_signals()
        
        self.logger.info("🖥️ Main GUI window initialized")
    
    def init_ui(self):
        """Initialize user interface."""
        try:
            # Window properties
            self.setWindowTitle("MT5 Trading Bot - Professional Edition")
            self.setGeometry(100, 100, 1400, 900)
            self.setMinimumSize(1200, 800)
            
            # Set application icon (using text-based icon for now)
            self.setWindowIcon(self.create_app_icon())
            
            # Apply dark theme
            self.apply_dark_theme()
            
            # Create central widget
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # Main layout
            main_layout = QHBoxLayout(central_widget)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
            
            # Create splitter for resizable panes
            main_splitter = QSplitter(Qt.Horizontal)
            main_layout.addWidget(main_splitter)
            
            # Left panel (Account & Controls)
            left_panel = self.create_left_panel()
            main_splitter.addWidget(left_panel)
            
            # Center panel (Charts & Positions)
            center_panel = self.create_center_panel()
            main_splitter.addWidget(center_panel)
            
            # Right panel (Logs & Stats)
            right_panel = self.create_right_panel()
            main_splitter.addWidget(right_panel)
            
            # Set splitter proportions
            main_splitter.setSizes([350, 700, 350])
            
            # Create menu bar
            self.create_menu_bar()
            
            # Create status bar
            self.create_status_bar()
            
            self.logger.info("✅ GUI layout initialized")
            
        except Exception as e:
            self.logger.error(f"❌ GUI initialization error: {str(e)}")
            QMessageBox.critical(self, "GUI Error", f"Failed to initialize interface:\n{str(e)}")
    
    def create_app_icon(self):
        """Create application icon."""
        try:
            # Create a simple icon using text
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(0, 100, 200))
            
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setFont(QFont("Arial", 16, QFont.Bold))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "MT5")
            painter.end()
            
            return pixmap
            
        except Exception as e:
            self.logger.error(f"❌ Icon creation error: {str(e)}")
            return QPixmap()
    
    def apply_dark_theme(self):
        """Apply dark theme to the application."""
        try:
            # Dark theme stylesheet
            dark_style = """
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #3c3c3c;
            }
            QTabBar::tab {
                background-color: #2b2b2b;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #555555;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555555;
                margin: 5px 0px;
                padding: 10px 0px;
                background-color: #3c3c3c;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0px 5px 0px 5px;
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
            self.account_widget = AccountInfoWidget(self.mt5_client)
            layout.addWidget(self.account_widget)
            
            # Trading Controls
            self.trading_control_widget = TradingControlWidget(self.trade_engine)
            layout.addWidget(self.trading_control_widget)
            
            # Risk Monitor
            self.risk_monitor_widget = RiskMonitorWidget(self.trade_engine.risk_manager)
            layout.addWidget(self.risk_monitor_widget)
            
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
            
            # Create tab widget for different views
            tab_widget = QTabWidget()
            
            # Equity Chart Tab
            self.equity_chart_widget = EquityChartWidget(self.trade_engine.reporting)
            tab_widget.addTab(self.equity_chart_widget, "📈 Equity Chart")
            
            # Positions Tab
            self.positions_widget = PositionsWidget(self.mt5_client, self.trade_engine)
            tab_widget.addTab(self.positions_widget, "💼 Positions")
            
            # Strategy Stats Tab
            self.strategy_stats_widget = StrategyStatsWidget(self.trade_engine.strategy)
            tab_widget.addTab(self.strategy_stats_widget, "📊 Strategy")
            
            layout.addWidget(tab_widget)
            
            return panel
            
        except Exception as e:
            self.logger.error(f"❌ Center panel creation error: {str(e)}")
            return QWidget()
    
    def create_right_panel(self) -> QWidget:
        """Create right panel with logs and additional info."""
        try:
            panel = QWidget()
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(10)
            
            # Log Widget
            self.log_widget = LogWidget()
            layout.addWidget(self.log_widget)
            
            return panel
            
        except Exception as e:
            self.logger.error(f"❌ Right panel creation error: {str(e)}")
            return QWidget()
    
    def create_menu_bar(self):
        """Create application menu bar."""
        try:
            menubar = self.menuBar()
            
            # File Menu
            file_menu = menubar.addMenu('&File')
            
            export_action = QAction('&Export Report', self)
            export_action.setShortcut('Ctrl+E')
            export_action.triggered.connect(self.export_report)
            file_menu.addAction(export_action)
            
            file_menu.addSeparator()
            
            exit_action = QAction('E&xit', self)
            exit_action.setShortcut('Ctrl+Q')
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)
            
            # Trading Menu
            trading_menu = menubar.addMenu('&Trading')
            
            start_trading_action = QAction('&Start Trading', self)
            start_trading_action.triggered.connect(self.start_trading)
            trading_menu.addAction(start_trading_action)
            
            stop_trading_action = QAction('&Stop Trading', self)
            stop_trading_action.triggered.connect(self.stop_trading)
            trading_menu.addAction(stop_trading_action)
            
            trading_menu.addSeparator()
            
            close_all_action = QAction('&Close All Positions', self)
            close_all_action.triggered.connect(self.close_all_positions)
            trading_menu.addAction(close_all_action)
            
            # Help Menu
            help_menu = menubar.addMenu('&Help')
            
            about_action = QAction('&About', self)
            about_action.triggered.connect(self.show_about)
            help_menu.addAction(about_action)
            
        except Exception as e:
            self.logger.error(f"❌ Menu bar creation error: {str(e)}")
    
    def create_status_bar(self):
        """Create status bar."""
        try:
            status_bar = self.statusBar()
            
            # Connection status
            self.connection_label = QLabel("🔴 Disconnected")
            status_bar.addWidget(self.connection_label)
            
            # Trading status
            self.trading_status_label = QLabel("🛑 Trading Stopped")
            status_bar.addWidget(self.trading_status_label)
            
            # Last update time
            self.update_time_label = QLabel("Last Update: Never")
            status_bar.addPermanentWidget(self.update_time_label)
            
        except Exception as e:
            self.logger.error(f"❌ Status bar creation error: {str(e)}")
    
    def setup_timers(self):
        """Setup update timers."""
        try:
            # Main update timer
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.update_data)
            self.update_timer.start(1000)  # Update every second
            
            # Fast update timer for real-time data
            self.fast_timer = QTimer()
            self.fast_timer.timeout.connect(self.fast_update)
            self.fast_timer.start(200)  # Fast update every 200ms
            
        except Exception as e:
            self.logger.error(f"❌ Timer setup error: {str(e)}")
    
    def connect_signals(self):
        """Connect widget signals."""
        try:
            # Connect trading control signals
            if hasattr(self, 'trading_control_widget'):
                pass  # Signals will be connected in the widget itself
                
        except Exception as e:
            self.logger.error(f"❌ Signal connection error: {str(e)}")
    
    def update_data(self):
        """Update all GUI components with latest data."""
        try:
            if not self.mt5_client.connected:
                return
            
            # Update account info
            if hasattr(self, 'account_widget'):
                self.account_widget.update_data()
            
            # Update positions
            if hasattr(self, 'positions_widget'):
                self.positions_widget.update_data()
            
            # Update equity chart
            if hasattr(self, 'equity_chart_widget'):
                self.equity_chart_widget.update_data()
            
            # Update strategy stats
            if hasattr(self, 'strategy_stats_widget'):
                self.strategy_stats_widget.update_data()
            
            # Update risk monitor
            if hasattr(self, 'risk_monitor_widget'):
                self.risk_monitor_widget.update_data()
            
            # Update status bar
            self.update_status_bar()
            
            self.last_update = datetime.now()
            
        except Exception as e:
            self.logger.error(f"❌ Data update error: {str(e)}")
    
    def fast_update(self):
        """Fast update for real-time elements."""
        try:
            # Update only time-critical elements
            if hasattr(self, 'account_widget'):
                self.account_widget.fast_update()
                
        except Exception as e:
            self.logger.error(f"❌ Fast update error: {str(e)}")
    
    def update_status_bar(self):
        """Update status bar information."""
        try:
            # Connection status
            if self.mt5_client.connected:
                self.connection_label.setText("🟢 Connected")
            else:
                self.connection_label.setText("🔴 Disconnected")
            
            # Trading status
            if self.trade_engine.trading_enabled:
                self.trading_status_label.setText("🟢 Trading Active")
            else:
                self.trading_status_label.setText("🛑 Trading Stopped")
            
            # Update time
            self.update_time_label.setText(f"Last Update: {self.last_update.strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.logger.error(f"❌ Status bar update error: {str(e)}")
    
    def start_trading(self):
        """Start automated trading."""
        try:
            if not self.mt5_client.connected:
                QMessageBox.warning(self, "Connection Error", "MT5 is not connected!")
                return
            
            reply = QMessageBox.question(
                self, 
                "Start Trading", 
                "Are you sure you want to start automated trading?\n\n"
                "This will trade with REAL MONEY on your live account!",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if not self.trade_engine.running:
                    if self.trade_engine.start():
                        self.log_widget.add_message("🚀 Automated trading started", "INFO")
                    else:
                        QMessageBox.critical(self, "Error", "Failed to start trading engine!")
                else:
                    self.trade_engine.enable_trading()
                    self.log_widget.add_message("✅ Automated trading enabled", "INFO")
                    
        except Exception as e:
            self.logger.error(f"❌ Start trading error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to start trading:\n{str(e)}")
    
    def stop_trading(self):
        """Stop automated trading."""
        try:
            self.trade_engine.disable_trading()
            self.log_widget.add_message("🛑 Automated trading stopped", "INFO")
            
        except Exception as e:
            self.logger.error(f"❌ Stop trading error: {str(e)}")
    
    def close_all_positions(self):
        """Close all open positions."""
        try:
            reply = QMessageBox.question(
                self,
                "Close All Positions",
                "Are you sure you want to close ALL open positions?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                positions = self.mt5_client.get_positions()
                if not positions:
                    QMessageBox.information(self, "Info", "No open positions to close.")
                    return
                
                closed_count = 0
                for position in positions:
                    if self.trade_engine.force_close_position(position["ticket"]):
                        closed_count += 1
                
                self.log_widget.add_message(f"✅ Closed {closed_count} positions", "INFO")
                QMessageBox.information(self, "Success", f"Closed {closed_count} out of {len(positions)} positions.")
                
        except Exception as e:
            self.logger.error(f"❌ Close all positions error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to close positions:\n{str(e)}")
    
    def export_report(self):
        """Export trading report."""
        try:
            filename = self.trade_engine.reporting.export_report()
            if filename and not filename.startswith("Export failed"):
                QMessageBox.information(self, "Export Success", f"Report exported to:\n{filename}")
            else:
                QMessageBox.warning(self, "Export Failed", f"Failed to export report:\n{filename}")
                
        except Exception as e:
            self.logger.error(f"❌ Export report error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Export error:\n{str(e)}")
    
    def show_about(self):
        """Show about dialog."""
        try:
            about_text = """
            <h2>MT5 Trading Bot - Professional Edition</h2>
            <p><b>Version:</b> 1.0.0</p>
            <p><b>Author:</b> Professional Trading Systems</p>
            <br>
            <p>This is a professional automated trading bot for MetaTrader 5 platform.</p>
            <p><b>Features:</b></p>
            <ul>
            <li>EMA/RSI Scalping Strategy</li>
            <li>Comprehensive Risk Management</li>
            <li>Real-time Performance Monitoring</li>
            <li>Live Account Integration</li>
            </ul>
            <br>
            <p><b>⚠️ WARNING:</b> This software trades with real money. Use at your own risk!</p>
            """
            
            QMessageBox.about(self, "About MT5 Trading Bot", about_text)
            
        except Exception as e:
            self.logger.error(f"❌ About dialog error: {str(e)}")
    
    def closeEvent(self, event):
        """Handle application close event."""
        try:
            reply = QMessageBox.question(
                self,
                "Exit Application",
                "Are you sure you want to exit?\n\n"
                "This will stop all trading activities!",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.logger.info("🔄 Closing application...")
                
                # Stop timers
                if self.update_timer:
                    self.update_timer.stop()
                if hasattr(self, 'fast_timer'):
                    self.fast_timer.stop()
                
                # Stop trade engine
                if self.trade_engine.running:
                    self.trade_engine.stop()
                
                event.accept()
            else:
                event.ignore()
                
        except Exception as e:
            self.logger.error(f"❌ Close event error: {str(e)}")
            event.accept()  # Close anyway to prevent hanging

