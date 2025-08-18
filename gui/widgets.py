"""
GUI Widgets for MT5 Trading Bot.
Contains all custom widgets for the trading interface.
"""

import sys
from typing import Dict, List, Any, Optional
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
            if account_info:
                self.login_label.setText(f"Login: {account_info['login']}")
                self.server_label.setText(f"Server: {account_info['server']}")
                self.balance_label.setText(f"Balance: ${account_info['balance']:,.2f}")
                self.equity_label.setText(f"Equity: ${account_info['equity']:,.2f}")
                self.margin_label.setText(f"Margin: ${account_info['margin']:,.2f}")
                self.free_margin_label.setText(f"Free Margin: ${account_info['free_margin']:,.2f}")

                # Color code margin level
                margin_level = account_info['margin_level']
                if margin_level > 0:
                    self.margin_level_label.setText(f"Margin Level: {margin_level:.1f}%")
                    if margin_level < 100:
                        self.margin_level_label.setStyleSheet("color: red;")
                    elif margin_level < 200:
                        self.margin_level_label.setStyleSheet("color: orange;")
                    else:
                        self.margin_level_label.setStyleSheet("color: green;")
                else:
                    self.margin_level_label.setText("Margin Level: --%")
                    self.margin_level_label.setStyleSheet("color: white;")

                # Color code profit
                profit = account_info['profit']
                self.profit_label.setText(f"Profit: ${profit:,.2f}")
                if profit > 0:
                    self.profit_label.setStyleSheet("color: green;")
                elif profit < 0:
                    self.profit_label.setStyleSheet("color: red;")
                else:
                    self.profit_label.setStyleSheet("color: white;")

        except Exception as e:
            self.logger.error(f"❌ Account widget update error: {str(e)}")

    def fast_update(self):
        """Fast update for critical info only."""
        try:
            if self.mt5_client.connected:
                account_info = self.mt5_client.get_account_info()
                if account_info:
                    self.equity_label.setText(f"Equity: ${account_info['equity']:,.2f}")
                    profit = account_info['profit']
                    self.profit_label.setText(f"Profit: ${profit:,.2f}")
                    if profit > 0:
                        self.profit_label.setStyleSheet("color: green;")
                    elif profit < 0:
                        self.profit_label.setStyleSheet("color: red;")
                    else:
                        self.profit_label.setStyleSheet("color: white;")
        except Exception as e:
            pass

class TradingControlWidget(QGroupBox):
    """Widget for trading controls."""

    def __init__(self, trade_engine):
        super().__init__("🎮 Trading Controls")
        self.trade_engine = trade_engine
        self.logger = get_logger(__name__)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Trading status
        self.status_label = QLabel("Status: Stopped")
        self.status_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(self.status_label)

        # Control buttons
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("🚀 Start Trading")
        self.start_btn.clicked.connect(self.start_trading)
        self.start_btn.setStyleSheet("QPushButton { background-color: #28a745; }")

        self.stop_btn = QPushButton("🛑 Stop Trading")
        self.stop_btn.clicked.connect(self.stop_trading)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #dc3545; }")
        self.stop_btn.setEnabled(False)

        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        layout.addLayout(button_layout)

        # Symbol selection
        symbol_layout = QHBoxLayout()
        symbol_layout.addWidget(QLabel("Symbols:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "XAGUSD"])
        self.symbol_combo.setEditable(True)
        symbol_layout.addWidget(self.symbol_combo)
        layout.addLayout(symbol_layout)

        # Trading parameters
        params_group = QGroupBox("Trading Parameters")
        params_layout = QGridLayout()

        # Lot size
        params_layout.addWidget(QLabel("Lot Size:"), 0, 0)
        self.lot_spin = QDoubleSpinBox()
        self.lot_spin.setRange(0.01, 100.0)
        self.lot_spin.setSingleStep(0.01)
        self.lot_spin.setValue(0.01)
        self.lot_spin.setDecimals(2)
        params_layout.addWidget(self.lot_spin, 0, 1)

        # Risk percentage
        params_layout.addWidget(QLabel("Risk %:"), 1, 0)
        self.risk_spin = QDoubleSpinBox()
        self.risk_spin.setRange(0.1, 10.0)
        self.risk_spin.setSingleStep(0.1)
        self.risk_spin.setValue(1.0)
        self.risk_spin.setDecimals(1)
        params_layout.addWidget(self.risk_spin, 1, 1)

        # Max positions
        params_layout.addWidget(QLabel("Max Positions:"), 2, 0)
        self.max_pos_spin = QSpinBox()
        self.max_pos_spin.setRange(1, 20)
        self.max_pos_spin.setValue(5)
        params_layout.addWidget(self.max_pos_spin, 2, 1)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Auto trading options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        self.auto_lot_check = QCheckBox("Auto Lot Sizing")
        self.auto_lot_check.setChecked(True)
        options_layout.addWidget(self.auto_lot_check)

        self.news_filter_check = QCheckBox("News Filter")
        self.news_filter_check.setChecked(True)
        options_layout.addWidget(self.news_filter_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Emergency close button
        self.emergency_btn = QPushButton("🚨 EMERGENCY CLOSE ALL")
        self.emergency_btn.clicked.connect(self.emergency_close)
        self.emergency_btn.setStyleSheet("QPushButton { background-color: #ff6b6b; font-weight: bold; }")
        layout.addWidget(self.emergency_btn)

        self.setLayout(layout)

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(1000)

    def start_trading(self):
        """Start automated trading."""
        try:
            if not self.trade_engine.running:
                if self.trade_engine.start():
                    self.start_btn.setEnabled(False)
                    self.stop_btn.setEnabled(True)
                    self.status_label.setText("Status: Starting...")
                    self.status_label.setStyleSheet("color: orange;")
            else:
                self.trade_engine.enable_trading()
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)

        except Exception as e:
            self.logger.error(f"❌ Start trading error: {str(e)}")

    def stop_trading(self):
        """Stop automated trading."""
        try:
            self.trade_engine.disable_trading()
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("Status: Stopped")
            self.status_label.setStyleSheet("color: red;")

        except Exception as e:
            self.logger.error(f"❌ Stop trading error: {str(e)}")

    def emergency_close(self):
        """Emergency close all positions."""
        try:
            positions = self.trade_engine.mt5_client.get_positions()
            for position in positions:
                self.trade_engine.force_close_position(position["ticket"])

            self.logger.info("🚨 Emergency close executed")

        except Exception as e:
            self.logger.error(f"❌ Emergency close error: {str(e)}")

    def update_status(self):
        """Update trading status."""
        try:
            if self.trade_engine.running and self.trade_engine.trading_enabled:
                self.status_label.setText("Status: 🟢 Trading Active")
                self.status_label.setStyleSheet("color: green;")
            elif self.trade_engine.running:
                self.status_label.setText("Status: 🟡 Monitoring")
                self.status_label.setStyleSheet("color: orange;")
            else:
                self.status_label.setText("Status: 🔴 Stopped")
                self.status_label.setStyleSheet("color: red;")

        except Exception as e:
            pass

class PositionsWidget(QGroupBox):
    """Widget displaying open positions."""

    def __init__(self, mt5_client, trade_engine):
        super().__init__("💼 Open Positions")
        self.mt5_client = mt5_client
        self.trade_engine = trade_engine
        self.logger = get_logger(__name__)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Positions table
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(8)
        self.positions_table.setHorizontalHeaderLabels([
            "Symbol", "Type", "Volume", "Entry", "Current", "SL", "TP", "Profit"
        ])

        # Set column widths
        header = self.positions_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        # Context menu for closing positions
        self.positions_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.positions_table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.positions_table)

        # Summary
        self.summary_label = QLabel("No positions open")
        layout.addWidget(self.summary_label)

        self.setLayout(layout)

    def update_data(self):
        """Update positions data."""
        try:
            positions = self.mt5_client.get_positions()

            self.positions_table.setRowCount(len(positions))

            total_profit = 0.0

            for i, pos in enumerate(positions):
                # Symbol
                self.positions_table.setItem(i, 0, QTableWidgetItem(pos["symbol"]))

                # Type
                item = QTableWidgetItem(pos["type"])
                if pos["type"] == "BUY":
                    item.setBackground(QColor(0, 255, 0, 50))
                else:
                    item.setBackground(QColor(255, 0, 0, 50))
                self.positions_table.setItem(i, 1, item)

                # Volume
                self.positions_table.setItem(i, 2, QTableWidgetItem(f"{pos['volume']:.2f}"))

                # Entry price
                self.positions_table.setItem(i, 3, QTableWidgetItem(f"{pos['price_open']:.5f}"))

                # Current price
                self.positions_table.setItem(i, 4, QTableWidgetItem(f"{pos['price_current']:.5f}"))

                # SL
                sl_text = f"{pos['sl']:.5f}" if pos['sl'] > 0 else "-"
                self.positions_table.setItem(i, 5, QTableWidgetItem(sl_text))

                # TP
                tp_text = f"{pos['tp']:.5f}" if pos['tp'] > 0 else "-"
                self.positions_table.setItem(i, 6, QTableWidgetItem(tp_text))

                # Profit
                profit = pos["profit"]
                profit_item = QTableWidgetItem(f"${profit:.2f}")
                if profit > 0:
                    profit_item.setForeground(QColor(0, 255, 0))
                elif profit < 0:
                    profit_item.setForeground(QColor(255, 0, 0))
                self.positions_table.setItem(i, 7, profit_item)

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

    def show_context_menu(self, position):
        """Show context menu for position actions."""
        # Implement context menu for closing individual positions
        pass

class LogWidget(QGroupBox):
    """Widget for displaying logs."""

    def __init__(self):
        super().__init__("📋 System Logs")
        self.init_ui()
        self.max_lines = 1000

    def init_ui(self):
        layout = QVBoxLayout()

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(self.max_lines)

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
        """Add a log message."""
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

            color = color_map.get(level.upper(), "#ffffff")

            formatted_message = f'<span style="color: {color};">[{timestamp}] {level}: {message}</span>'

            self.log_text.append(formatted_message)

            if self.auto_scroll_check.isChecked():
                scrollbar = self.log_text.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            pass

    def clear_logs(self):
        """Clear all logs."""
        self.log_text.clear()

class EquityChartWidget(QGroupBox):
    """Widget for displaying equity chart."""

    def __init__(self, reporting_manager):
        super().__init__("📈 Equity Chart")
        self.reporting_manager = reporting_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Simple text-based chart for now
        self.chart_text = QTextEdit()
        self.chart_text.setReadOnly(True)
        self.chart_text.setMaximumHeight(200)

        layout.addWidget(QLabel("Equity curve (text-based):"))
        layout.addWidget(self.chart_text)

        self.setLayout(layout)

    def update_data(self):
        """Update equity chart."""
        try:
            equity_data = self.reporting_manager.get_equity_data()

            if equity_data:
                chart_text = "Time        Equity\n"
                chart_text += "-" * 20 + "\n"

                for point in equity_data[-10:]:  # Show last 10 points
                    time_str = point["timestamp"].strftime("%H:%M:%S")
                    equity = point["equity"]
                    chart_text += f"{time_str}   ${equity:,.2f}\n"

                self.chart_text.setText(chart_text)
            else:
                self.chart_text.setText("No equity data available")

        except Exception as e:
            self.chart_text.setText(f"Chart update error: {str(e)}")

class StrategyStatsWidget(QGroupBox):
    """Widget for displaying strategy statistics."""

    def __init__(self, strategy):
        super().__init__("📊 Strategy Statistics")
        self.strategy = strategy
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(150)

        layout.addWidget(self.stats_text)
        self.setLayout(layout)

    def update_data(self):
        """Update strategy statistics."""
        try:
            stats = self.strategy.get_strategy_stats()

            if stats.get("no_data"):
                self.stats_text.setText("No strategy data available")
                return

            stats_text = ""
            stats_text += f"Total Signals: {stats.get('total_signals', 0)}\n"
            stats_text += f"Buy Signals: {stats.get('buy_signals', 0)}\n"
            stats_text += f"Sell Signals: {stats.get('sell_signals', 0)}\n"
            stats_text += f"Avg Confidence: {stats.get('avg_confidence', 0):.1f}%\n"
            stats_text += f"24h Signals: {stats.get('recent_signals_24h', 0)}\n"
            stats_text += f"Symbols: {stats.get('symbols_analyzed', 0)}\n"

            if stats.get('last_signal_time'):
                last_time = stats['last_signal_time'].strftime("%H:%M:%S")
                stats_text += f"Last Signal: {last_time}\n"

            self.stats_text.setText(stats_text)

        except Exception as e:
            self.stats_text.setText(f"Stats error: {str(e)}")

class RiskMonitorWidget(QGroupBox):
    """Widget for risk monitoring."""

    def __init__(self, risk_manager):
        super().__init__("🛡️ Risk Monitor")
        self.risk_manager = risk_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.risk_text = QTextEdit()
        self.risk_text.setReadOnly(True)
        self.risk_text.setMaximumHeight(120)

        layout.addWidget(self.risk_text)
        self.setLayout(layout)

    def update_data(self):
        """Update risk monitor."""
        try:
            risk_report = self.risk_manager.get_risk_report()

            if risk_report.get("error"):
                self.risk_text.setText(f"Risk monitor error: {risk_report['error']}")
                return

            risk_text = ""
            risk_text += f"Session: {risk_report.get('session_duration', 'Unknown')}\n"
            risk_text += f"Daily Trades: {risk_report.get('daily_trades', 0)}/{risk_report.get('max_daily_trades', 0)}\n"
            risk_text += f"Daily P&L: ${risk_report.get('daily_profit', 0):.2f} ({risk_report.get('daily_profit_percent', 0):.1f}%)\n"
            risk_text += f"Max Equity: ${risk_report.get('max_equity', 0):,.2f}\n"

            # Color code based on performance
            daily_profit_percent = risk_report.get('daily_profit_percent', 0)
            if daily_profit_percent > 0:
                self.risk_text.setStyleSheet("color: green;")
            elif daily_profit_percent < -2:
                self.risk_text.setStyleSheet("color: red;")
            else:
                self.risk_text.setStyleSheet("color: white;")

            self.risk_text.setText(risk_text)

        except Exception as e:
            self.risk_text.setText(f"Risk monitor error: {str(e)}")