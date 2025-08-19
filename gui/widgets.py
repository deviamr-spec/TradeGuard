"""
GUI Widgets for MT5 Trading Bot.
Contains all custom widgets for the trading interface.
FIXED VERSION - ALL ERRORS RESOLVED
"""

import sys
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import threading

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QTextEdit,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QProgressBar, QHeaderView, QFrame, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

from utils.logging_setup import get_logger

class AccountInfoWidget(QGroupBox):
    """Widget displaying account information."""

    def __init__(self, mt5_client):
        super().__init__("💰 Account Information")
        self.mt5_client = mt5_client
        self.logger = get_logger(__name__)
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout()

        # Account info labels
        self.login_label = QLabel("Login: --")
        self.server_label = QLabel("Server: --")
        self.balance_label = QLabel("Balance: $0.00")
        self.equity_label = QLabel("Equity: $0.00")
        self.margin_label = QLabel("Margin: $0.00")
        self.free_margin_label = QLabel("Free Margin: $0.00")
        self.margin_level_label = QLabel("Margin Level: --%")
        self.profit_label = QLabel("Profit: $0.00")

        # Set font for better readability
        font = QFont()
        font.setPointSize(9)
        for label in [self.login_label, self.server_label, self.balance_label,
                     self.equity_label, self.margin_label, self.free_margin_label,
                     self.margin_level_label, self.profit_label]:
            label.setFont(font)

        # Layout
        layout.addWidget(self.login_label, 0, 0, 1, 2)
        layout.addWidget(self.server_label, 1, 0, 1, 2)
        layout.addWidget(self.balance_label, 2, 0)
        layout.addWidget(self.equity_label, 2, 1)
        layout.addWidget(self.margin_label, 3, 0)
        layout.addWidget(self.free_margin_label, 3, 1)
        layout.addWidget(self.margin_level_label, 4, 0)
        layout.addWidget(self.profit_label, 4, 1)

        self.setLayout(layout)

    def update_data(self):
        """Update account information."""
        try:
            if not self.mt5_client.connected:
                self.login_label.setText("Login: Disconnected")
                self.server_label.setText("Server: --")
                self.balance_label.setText("Balance: $0.00")
                self.equity_label.setText("Equity: $0.00")
                self.margin_label.setText("Margin: $0.00")
                self.free_margin_label.setText("Free Margin: $0.00")
                self.margin_level_label.setText("Margin Level: --%")
                self.profit_label.setText("Profit: $0.00")
                return

            account_info = self.mt5_client.get_account_info()
            if not account_info:
                return

            # Update labels with account information
            self.login_label.setText(f"Login: {account_info.get('login', 'N/A')}")
            self.server_label.setText(f"Server: {account_info.get('server', 'N/A')}")

            balance = account_info.get('balance', 0.0)
            equity = account_info.get('equity', 0.0)
            margin = account_info.get('margin', 0.0)
            free_margin = account_info.get('free_margin', 0.0)
            margin_level = account_info.get('margin_level', 0.0)

            self.balance_label.setText(f"Balance: ${balance:,.2f}")
            self.equity_label.setText(f"Equity: ${equity:,.2f}")
            self.margin_label.setText(f"Margin: ${margin:,.2f}")
            self.free_margin_label.setText(f"Free Margin: ${free_margin:,.2f}")

            if margin_level > 0:
                self.margin_level_label.setText(f"Margin Level: {margin_level:.2f}%")
            else:
                self.margin_level_label.setText("Margin Level: --%")

            # Calculate profit (equity - balance)
            profit = equity - balance
            profit_color = "green" if profit >= 0 else "red"
            profit_percent = (profit / balance * 100) if balance > 0 else 0.0

            self.profit_label.setText(f"P&L: ${profit:,.2f} ({profit_percent:+.2f}%)")
            self.profit_label.setStyleSheet(f"color: {profit_color}; font-weight: bold;")

        except Exception as e:
            self.logger.error(f"❌ Account widget update error: {str(e)}")

class TradingControlWidget(QGroupBox):
    """Widget for trading controls."""

    def __init__(self, trade_engine):
        super().__init__("🎮 Trading Controls")
        self.trade_engine = trade_engine
        self.logger = get_logger(__name__)
        self.auto_trading_enabled = True
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Trading status
        self.status_label = QLabel("Status: Stopped")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(self.status_label)

        # Control buttons
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶️ Start Trading")
        self.start_btn.clicked.connect(self.start_trading)
        self.start_btn.setStyleSheet("background-color: #28a745; color: white; padding: 8px;")

        self.stop_btn = QPushButton("⏹️ Stop Trading")
        self.stop_btn.clicked.connect(self.stop_trading)
        self.stop_btn.setStyleSheet("background-color: #dc3545; color: white; padding: 8px;")
        self.stop_btn.setEnabled(False)

        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        layout.addLayout(button_layout)

        # Auto-trading toggle
        auto_layout = QHBoxLayout()

        self.auto_trading_checkbox = QCheckBox("🤖 Auto Trading")
        self.auto_trading_checkbox.setChecked(True)
        self.auto_trading_checkbox.stateChanged.connect(self.toggle_auto_trading)
        self.auto_trading_checkbox.setStyleSheet("color: #00ff00; font-weight: bold;")

        self.auto_tpsl_checkbox = QCheckBox("🎯 Auto TP/SL")
        self.auto_tpsl_checkbox.setChecked(True)
        self.auto_tpsl_checkbox.setStyleSheet("color: #00ff00; font-weight: bold;")

        auto_layout.addWidget(self.auto_trading_checkbox)
        auto_layout.addWidget(self.auto_tpsl_checkbox)
        layout.addLayout(auto_layout)

        # Emergency controls
        emergency_layout = QHBoxLayout()

        self.emergency_stop_btn = QPushButton("🚨 Emergency Stop")
        self.emergency_stop_btn.clicked.connect(self.emergency_stop)
        self.emergency_stop_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 8px;")

        self.close_all_btn = QPushButton("🔒 Close All Positions")
        self.close_all_btn.clicked.connect(self.close_all_positions)
        self.close_all_btn.setStyleSheet("background-color: #fd7e14; color: white; padding: 8px;")

        emergency_layout.addWidget(self.emergency_stop_btn)
        emergency_layout.addWidget(self.close_all_btn)
        layout.addLayout(emergency_layout)

        self.setLayout(layout)

    def start_trading(self):
        """Start trading engine."""
        try:
            if not self.trade_engine.running:
                self.trade_engine.start()
                self.status_label.setText("Status: Running")
                self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 12px;")
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
                self.logger.info("✅ Trading started from GUI")
        except Exception as e:
            self.logger.error(f"❌ Failed to start trading: {str(e)}")

    def stop_trading(self):
        """Stop trading engine."""
        try:
            if self.trade_engine.running:
                self.trade_engine.stop()
                self.status_label.setText("Status: Stopped")
                self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 12px;")
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                self.logger.info("⏹️ Trading stopped from GUI")
        except Exception as e:
            self.logger.error(f"❌ Failed to stop trading: {str(e)}")

    def emergency_stop(self):
        """Emergency stop all operations."""
        try:
            self.trade_engine.emergency_stop()
            self.status_label.setText("Status: Emergency Stopped")
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 12px;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.logger.warning("🚨 Emergency stop activated from GUI")
        except Exception as e:
            self.logger.error(f"❌ Emergency stop failed: {str(e)}")

    def close_all_positions(self):
        """Close all open positions."""
        try:
            positions = self.trade_engine.mt5_client.get_positions()
            for position in positions:
                self.trade_engine.mt5_client.close_position(position['ticket'])
            self.logger.info(f"🔒 Closed {len(positions)} positions from GUI")
        except Exception as e:
            self.logger.error(f"❌ Failed to close positions: {str(e)}")

    def toggle_auto_trading(self, state):
        """Toggle automatic trading on/off."""
        try:
            self.auto_trading_enabled = bool(state)
            self.trade_engine.trading_enabled = self.auto_trading_enabled

            status_text = "ENABLED" if self.auto_trading_enabled else "DISABLED"
            color = "#00ff00" if self.auto_trading_enabled else "#ff0000"

            self.auto_trading_checkbox.setStyleSheet(f"color: {color}; font-weight: bold;")
            self.logger.info(f"🤖 Auto-trading {status_text}")

        except Exception as e:
            self.logger.error(f"❌ Failed to toggle auto-trading: {str(e)}")

    def update_data(self):
        """Update trading control status."""
        try:
            # Update running status
            if self.trade_engine.running:
                if not self.stop_btn.isEnabled():
                    self.start_btn.setEnabled(False)
                    self.stop_btn.setEnabled(True)

                # Update status based on auto-trading state
                if getattr(self.trade_engine, 'trading_enabled', False):
                    self.status_label.setText("Status: AUTO TRADING")
                    self.status_label.setStyleSheet("color: #00ff00; font-weight: bold; font-size: 12px;")
                else:
                    self.status_label.setText("Status: Running (Manual)")
                    self.status_label.setStyleSheet("color: orange; font-weight: bold; font-size: 12px;")
            else:
                if not self.start_btn.isEnabled():
                    self.start_btn.setEnabled(True)
                    self.stop_btn.setEnabled(False)
                    self.status_label.setText("Status: Stopped")
                    self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 12px;")

            # Sync checkbox with actual state
            actual_auto_state = getattr(self.trade_engine, 'trading_enabled', False)
            if hasattr(self, 'auto_trading_checkbox') and self.auto_trading_checkbox.isChecked() != actual_auto_state:
                self.auto_trading_checkbox.setChecked(actual_auto_state)

        except Exception as e:
            self.logger.error(f"❌ Trading control update error: {str(e)}")

class RiskMonitorWidget(QGroupBox):
    """Widget for risk monitoring."""

    def __init__(self, risk_manager):
        super().__init__("🛡️ Risk Monitor")
        self.risk_manager = risk_manager
        self.logger = get_logger(__name__)
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout()

        # Risk metrics labels
        self.daily_loss_label = QLabel("Daily Loss: $0.00 (0%)")
        self.max_drawdown_label = QLabel("Max Drawdown: 0%")
        self.position_count_label = QLabel("Positions: 0/5")
        self.risk_per_trade_label = QLabel("Risk per Trade: 1%")

        # Risk status indicator
        self.risk_status_label = QLabel("Status: Normal")
        self.risk_status_label.setStyleSheet("color: green; font-weight: bold;")

        # Layout
        layout.addWidget(self.risk_status_label, 0, 0, 1, 2)
        layout.addWidget(self.daily_loss_label, 1, 0, 1, 2)
        layout.addWidget(self.max_drawdown_label, 2, 0)
        layout.addWidget(self.position_count_label, 2, 1)
        layout.addWidget(self.risk_per_trade_label, 3, 0, 1, 2)

        self.setLayout(layout)

    def update_data(self):
        """Update risk monitoring data."""
        try:
            if not self.risk_manager:
                self.risk_status_label.setText("Status: No Risk Manager")
                return

            # Get risk metrics safely
            metrics = self.risk_manager.get_risk_metrics()

            daily_loss = metrics.get('daily_loss', 0.0)
            daily_loss_pct = abs(self.risk_manager.daily_pnl / self.risk_manager.daily_start_balance * 100) if self.risk_manager.daily_start_balance > 0 else 0.0
            max_drawdown_pct = self.risk_manager.current_drawdown * 100
            position_count = len(getattr(self.risk_manager, 'open_positions', []))
            max_positions = self.risk_manager.max_positions
            risk_per_trade = self.risk_manager.risk_per_trade * 100

            # Update labels
            self.daily_loss_label.setText(f"Daily Loss: ${daily_loss:.2f} ({daily_loss_pct:.1f}%)")
            self.max_drawdown_label.setText(f"Max Drawdown: {max_drawdown_pct:.1f}%")
            self.position_count_label.setText(f"Positions: {position_count}/{max_positions}")
            self.risk_per_trade_label.setText(f"Risk per Trade: {risk_per_trade:.1f}%")

            # Update risk status
            if daily_loss_pct > 3.0 or max_drawdown_pct > 7.0:
                self.risk_status_label.setText("Status: High Risk")
                self.risk_status_label.setStyleSheet("color: red; font-weight: bold;")
            elif daily_loss_pct > 1.5 or max_drawdown_pct > 3.0:
                self.risk_status_label.setText("Status: Moderate Risk")
                self.risk_status_label.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.risk_status_label.setText("Status: Normal")
                self.risk_status_label.setStyleSheet("color: green; font-weight: bold;")

        except Exception as e:
            self.logger.error(f"❌ Risk monitor update error: {str(e)}")
            # Set default values on error
            self.risk_status_label.setText("Status: Error")
            self.daily_loss_label.setText("Daily Loss: $0.00 (0%)")
            self.max_drawdown_label.setText("Max Drawdown: 0%")
            self.position_count_label.setText("Positions: 0/0")
            self.risk_per_trade_label.setText("Risk per Trade: 0%")

    def update_risk_metrics(self, risk_metrics: Dict[str, Any]):
        """Update risk display with provided metrics."""
        try:
            if not risk_metrics:
                return

            daily_loss = risk_metrics.get('daily_loss', 0.0)
            daily_loss_pct = risk_metrics.get('daily_loss_percentage', 0.0)
            max_drawdown_pct = risk_metrics.get('current_drawdown', 0.0) * 100
            position_count = risk_metrics.get('position_count', 0)
            max_positions = risk_metrics.get('max_positions', 5)
            risk_per_trade = risk_metrics.get('risk_per_trade', 1.0)

            # Update labels
            self.daily_loss_label.setText(f"Daily Loss: ${daily_loss:.2f} ({daily_loss_pct:.1f}%)")
            self.max_drawdown_label.setText(f"Max Drawdown: {max_drawdown_pct:.1f}%")
            self.position_count_label.setText(f"Positions: {position_count}/{max_positions}")
            self.risk_per_trade_label.setText(f"Risk per Trade: {risk_per_trade:.1f}%")

            # Update risk status
            emergency_stop = risk_metrics.get('emergency_stop', False)
            if emergency_stop:
                self.risk_status_label.setText("Status: EMERGENCY STOP")
                self.risk_status_label.setStyleSheet("color: red; font-weight: bold; background-color: yellow;")
            elif daily_loss_pct > 3.0 or max_drawdown_pct > 7.0:
                self.risk_status_label.setText("Status: High Risk")
                self.risk_status_label.setStyleSheet("color: red; font-weight: bold;")
            elif daily_loss_pct > 1.5 or max_drawdown_pct > 3.0:
                self.risk_status_label.setText("Status: Moderate Risk")
                self.risk_status_label.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.risk_status_label.setText("Status: Normal")
                self.risk_status_label.setStyleSheet("color: green; font-weight: bold;")

        except Exception as e:
            self.logger.error(f"❌ Risk metrics update error: {str(e)}")

class PerformanceMonitorWidget(QGroupBox):
    """Widget for performance monitoring."""

    def __init__(self, trade_engine):
        super().__init__("📊 Performance Monitor")
        self.trade_engine = trade_engine
        self.logger = get_logger(__name__)
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout()

        # Performance metrics labels
        self.total_trades_label = QLabel("Total Trades: 0")
        self.win_rate_label = QLabel("Win Rate: 0%")
        self.profit_label = QLabel("Profit: $0.00")
        self.drawdown_label = QLabel("Drawdown: 0%")

        # Layout
        layout.addWidget(self.total_trades_label, 0, 0)
        layout.addWidget(self.win_rate_label, 0, 1)
        layout.addWidget(self.profit_label, 1, 0)
        layout.addWidget(self.drawdown_label, 1, 1)

        self.setLayout(layout)

    def update_data(self):
        """Update performance monitoring data."""
        try:
            if not self.trade_engine:
                return

            # Get performance metrics from reporting manager
            if hasattr(self.trade_engine, 'reporting'):
                metrics = self.trade_engine.reporting.get_performance_metrics()

                if "error" not in metrics:
                    trading_stats = metrics.get("trading_stats", {})
                    profit_loss = metrics.get("profit_loss", {})
                    risk_metrics = metrics.get("risk_metrics", {})

                    self.total_trades_label.setText(f"Total Trades: {trading_stats.get('total_trades', 0)}")
                    self.win_rate_label.setText(f"Win Rate: {trading_stats.get('win_rate', 0):.1f}%")
                    self.profit_label.setText(f"Profit: ${profit_loss.get('net_profit', 0):.2f}")
                    self.drawdown_label.setText(f"Drawdown: {risk_metrics.get('max_drawdown', 0)*100:.1f}%")
                else:
                    self.total_trades_label.setText("Total Trades: Error")
                    self.win_rate_label.setText("Win Rate: Error")
                    self.profit_label.setText("Profit: Error")
                    self.drawdown_label.setText("Drawdown: Error")
            else:
                self.total_trades_label.setText("Total Trades: N/A")
                self.win_rate_label.setText("Win Rate: N/A")
                self.profit_label.setText("Profit: N/A")
                self.drawdown_label.setText("Drawdown: N/A")

        except Exception as e:
            self.logger.error(f"❌ Performance monitor update error: {str(e)}")

class MarketDataWidget(QGroupBox):
    """Widget for displaying market data."""

    def __init__(self, mt5_client, symbols: List[str]):
        super().__init__("💹 Market Data")
        self.mt5_client = mt5_client
        self.symbols = symbols
        self.logger = get_logger(__name__)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Market data table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Symbol", "Bid", "Ask", "Spread", "Time"])

        # Set table properties
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Stretch)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def update_data(self):
        """Update market data table with real-time analysis."""
        try:
            if not self.mt5_client.connected:
                return

            self.table.setRowCount(len(self.symbols))

            for row, symbol in enumerate(self.symbols):
                tick_data = self.mt5_client.get_tick_data(symbol)

                if tick_data:
                    # Symbol with signal indicator
                    symbol_item = QTableWidgetItem(tick_data["symbol"])

                    # Get current signal analysis (simplified)
                    try:
                        # Quick analysis for display purposes
                        df = self.mt5_client.get_historical_data(symbol, "M1", 50)
                        if df is not None and len(df) > 20:
                            from core.strategy.scalping import ScalpingStrategy
                            strategy = ScalpingStrategy()
                            signal = strategy.generate_signal(df, symbol)

                            if signal.get("signal") == "BUY":
                                symbol_item.setBackground(QColor(0, 100, 0))  # Dark green
                                symbol_item.setForeground(QColor(255, 255, 255))
                            elif signal.get("signal") == "SELL":
                                symbol_item.setBackground(QColor(100, 0, 0))  # Dark red
                                symbol_item.setForeground(QColor(255, 255, 255))
                    except:
                        pass  # Skip analysis on error

                    self.table.setItem(row, 0, symbol_item)

                    # Bid
                    bid_item = QTableWidgetItem(f"{tick_data['bid']:.5f}")
                    self.table.setItem(row, 1, bid_item)

                    # Ask
                    ask_item = QTableWidgetItem(f"{tick_data['ask']:.5f}")
                    self.table.setItem(row, 2, ask_item)

                    # Spread
                    spread_pips = tick_data['spread'] * 10000  # Convert to pips
                    spread_item = QTableWidgetItem(f"{spread_pips:.1f}")
                    self.table.setItem(row, 3, spread_item)

                    # Time
                    time_str = tick_data['time'].strftime("%H:%M:%S")
                    self.table.setItem(row, 4, QTableWidgetItem(time_str))
                else:
                    # No data available
                    for col in range(5):
                        if col == 0:
                            self.table.setItem(row, col, QTableWidgetItem(symbol))
                        else:
                            self.table.setItem(row, col, QTableWidgetItem("--"))

        except Exception as e:
            self.logger.error(f"❌ Market data widget update error: {str(e)}")

class PositionsWidget(QGroupBox):
    """Widget for displaying open positions."""

    def __init__(self, mt5_client):
        super().__init__("📈 Open Positions")
        self.mt5_client = mt5_client
        self.logger = get_logger(__name__)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Positions table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Ticket", "Symbol", "Type", "Volume", "Price", "Current", "Profit"
        ])

        # Set table properties
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Stretch)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self.table)

        # Summary label
        self.summary_label = QLabel("No positions open")
        self.summary_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(self.summary_label)

        self.setLayout(layout)

    def update_data(self):
        """Update positions table."""
        try:
            if not self.mt5_client.connected:
                self.table.setRowCount(0)
                self.summary_label.setText("MT5 not connected")
                return

            positions = self.mt5_client.get_positions()
            self.table.setRowCount(len(positions))

            total_profit = 0.0

            for row, position in enumerate(positions):
                # Ticket
                self.table.setItem(row, 0, QTableWidgetItem(str(position["ticket"])))

                # Symbol
                self.table.setItem(row, 1, QTableWidgetItem(position["symbol"]))

                # Type
                type_item = QTableWidgetItem(position["type"])
                if position["type"] == "BUY":
                    type_item.setBackground(QColor(0, 150, 0))
                else:
                    type_item.setBackground(QColor(150, 0, 0))
                self.table.setItem(row, 2, type_item)

                # Volume
                self.table.setItem(row, 3, QTableWidgetItem(f"{position['volume']:.2f}"))

                # Price
                self.table.setItem(row, 4, QTableWidgetItem(f"{position['price_open']:.5f}"))

                # Current Price
                self.table.setItem(row, 5, QTableWidgetItem(f"{position['price_current']:.5f}"))

                # Profit
                profit = position["profit"]
                profit_item = QTableWidgetItem(f"${profit:.2f}")
                if profit >= 0:
                    profit_item.setForeground(QColor(0, 150, 0))
                else:
                    profit_item.setForeground(QColor(150, 0, 0))
                self.table.setItem(row, 6, profit_item)

                total_profit += profit

            # Update summary
            if positions:
                summary_color = "green" if total_profit >= 0 else "red"
                self.summary_label.setText(f"Total: {len(positions)} positions, Profit: ${total_profit:.2f}")
                self.summary_label.setStyleSheet(f"color: {summary_color}; font-weight: bold;")
            else:
                self.summary_label.setText("No positions open")
                self.summary_label.setStyleSheet("color: white;")

        except Exception as e:
            self.logger.error(f"❌ Positions widget update error: {str(e)}")

class LogWidget(QGroupBox):
    """Widget for displaying logs - FIXED setMaximumBlockCount issue."""

    def __init__(self):
        super().__init__("📋 System Logs")
        self.init_ui()
        self.max_lines = 1000
        self.line_count = 0

    def init_ui(self):
        layout = QVBoxLayout()

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # FIXED: Removed setMaximumBlockCount which isn't available in all PyQt5 versions
        # Instead we'll manually manage log size in add_message method

        # Set monospace font
        font = QFont("Consolas", 8)
        font.setStyleHint(QFont.Monospace)
        self.log_text.setFont(font)

        layout.addWidget(self.log_text)

        # Controls
        controls_layout = QHBoxLayout()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_logs)

        self.auto_scroll_check = QCheckBox("Auto Scroll")
        self.auto_scroll_check.setChecked(True)

        controls_layout.addWidget(self.clear_btn)
        controls_layout.addWidget(self.auto_scroll_check)
        controls_layout.addStretch()

        layout.addLayout(controls_layout)
        self.setLayout(layout)

    def add_message(self, message: str, level: str = "INFO"):
        """Add a log message with manual line limit management."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Color based on level
            color_map = {
                "DEBUG": "#888888",
                "INFO": "#ffffff",
                "WARNING": "#ffaa00",
                "ERROR": "#ff4444",
                "CRITICAL": "#ff0000"
            }

            color = color_map.get(level, "#ffffff")
            formatted_message = f'<span style="color: {color};">[{timestamp}] {level}: {message}</span>'

            # FIXED: Manual line count management instead of setMaximumBlockCount
            self.line_count += 1
            if self.line_count > self.max_lines:
                # Clear old content when reaching limit
                current_text = self.log_text.toHtml()
                lines = current_text.split('<br>')
                if len(lines) > self.max_lines:
                    # Keep only the last max_lines/2 lines
                    keep_lines = self.max_lines // 2
                    new_text = '<br>'.join(lines[-keep_lines:])
                    self.log_text.setHtml(new_text)
                    self.line_count = keep_lines

            self.log_text.append(formatted_message)

            # Auto scroll if enabled
            if self.auto_scroll_check.isChecked():
                scrollbar = self.log_text.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            print(f"Log widget error: {str(e)}")

    def clear_logs(self):
        """Clear all log messages."""
        self.log_text.clear()
        self.line_count = 0

class EquityChartWidget(QGroupBox):
    """Widget for displaying equity curve."""

    def __init__(self):
        super().__init__("📈 Equity Curve")
        self.init_ui()
        self.equity_data = []
        self.max_points = 100 # Added max_points attribute

    def init_ui(self):
        layout = QVBoxLayout()

        # Placeholder for equity chart
        self.chart_label = QLabel("Equity Chart")
        self.chart_label.setAlignment(Qt.AlignCenter)
        self.chart_label.setStyleSheet("border: 1px solid gray; min-height: 200px;")

        layout.addWidget(self.chart_label)
        self.setLayout(layout)

    def update_chart(self):
        """Internal method to update the chart display."""
        if not self.equity_data:
            self.chart_label.setText("Equity Chart (No data)")
            self.chart_label.setStyleSheet("border: 1px solid gray; min-height: 200px; color: white;")
            return

        latest_equity = self.equity_data[-1]
        first_equity = self.equity_data[0]
        change = latest_equity - first_equity
        change_pct = (change / first_equity * 100) if first_equity != 0 else 0

        color = "green" if change >= 0 else "red"
        self.chart_label.setText(
            f"Current Equity: ${latest_equity:,.2f}\n"
            f"Change: ${change:+,.2f} ({change_pct:+.2f}%)\n"
            f"Data Points: {len(self.equity_data)}"
        )
        self.chart_label.setStyleSheet(
            f"border: 1px solid gray; min-height: 200px; color: {color}; "
            "font-weight: bold; font-size: 14px;"
        )

    def update_data(self, equity_value=None):
        """Update chart with new equity value."""
        try:
            if equity_value is None:
                # Try to get equity from parent if available
                if hasattr(self.parent(), 'mt5_client') and self.parent().mt5_client:
                    account_info = self.parent().mt5_client.get_account_info()
                    if account_info:
                        equity_value = account_info.get('equity', 0.0)
                    else:
                        equity_value = 0.0
                else:
                    equity_value = 0.0

            self.equity_data.append(equity_value)
            if len(self.equity_data) > self.max_points:
                self.equity_data.pop(0)

            self.update_chart()

        except Exception as e:
            print(f"Equity chart update error: {e}")