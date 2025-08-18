"""
GUI Widgets for MT5 Trading Bot.
Contains all custom widgets for the trading interface.
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
        self.symbol_combo.addItems(["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD"])
        self.symbol_combo.setEditable(True)
        symbol_layout.addWidget(self.symbol_combo)

        self.add_symbol_btn = QPushButton("Add Symbol")
        self.add_symbol_btn.clicked.connect(self.add_symbol)
        symbol_layout.addWidget(self.add_symbol_btn)

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

        # Strategy settings
        strategy_group = QGroupBox("Strategy Settings")
        strategy_layout = QGridLayout()

        # Min confidence
        strategy_layout.addWidget(QLabel("Min Confidence %:"), 0, 0)
        self.min_confidence_spin = QDoubleSpinBox()
        self.min_confidence_spin.setRange(50.0, 95.0)
        self.min_confidence_spin.setValue(75.0)
        self.min_confidence_spin.setDecimals(1)
        strategy_layout.addWidget(self.min_confidence_spin, 0, 1)

        # Auto execute
        self.auto_execute_check = QCheckBox("Auto Execute High Confidence Signals")
        self.auto_execute_check.setChecked(True)
        strategy_layout.addWidget(self.auto_execute_check, 1, 0, 1, 2)

        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)

        # Auto trading options
        options_group = QGroupBox("Live Trading Options")
        options_layout = QVBoxLayout()

        self.auto_lot_check = QCheckBox("Auto Lot Sizing")
        self.auto_lot_check.setChecked(True)
        options_layout.addWidget(self.auto_lot_check)

        self.news_filter_check = QCheckBox("News Filter")
        self.news_filter_check.setChecked(True)
        options_layout.addWidget(self.news_filter_check)

        self.live_trading_check = QCheckBox("⚠️ LIVE TRADING ENABLED")
        self.live_trading_check.setChecked(False)
        self.live_trading_check.setStyleSheet("QCheckBox { color: red; font-weight: bold; }")
        options_layout.addWidget(self.live_trading_check)

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

    def validate_symbol_input(self, symbol: str) -> Tuple[bool, str]:
        """
        Validate trading symbol input.
        
        Args:
            symbol: Symbol to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not symbol or not symbol.strip():
                return False, "Symbol cannot be empty"
            
            symbol = symbol.strip().upper()
            
            # Basic symbol format validation
            if len(symbol) < 6 or len(symbol) > 10:
                return False, "Symbol must be 6-10 characters long"
            
            # Check for valid characters (letters and numbers only)
            if not symbol.replace('/', '').replace('_', '').replace('.', '').replace('#', '').isalnum():
                return False, "Symbol contains invalid characters"
            
            # Check for common forex pairs and metals
            valid_patterns = [
                r'^[A-Z]{6}$',  # Standard forex pairs (EURUSD)
                r'^XAU[A-Z]{3}$',  # Gold (XAUUSD)
                r'^XAG[A-Z]{3}$',  # Silver (XAGUSD)
                r'^[A-Z]{3}[A-Z]{3}$',  # General 6-char pairs
                r'^[A-Z]+[/.#_][A-Z]+$',  # Broker-specific formats
            ]
            
            import re
            if not any(re.match(pattern, symbol) for pattern in valid_patterns):
                return False, "Symbol format not recognized"
            
            return True, ""
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def validate_lot_size(self, lot_size: float) -> Tuple[bool, str]:
        """
        Validate lot size input.
        
        Args:
            lot_size: Lot size to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if lot_size <= 0:
                return False, "Lot size must be greater than 0"
            
            if lot_size > 100:
                return False, "Lot size too large (max: 100)"
            
            # Check minimum increment (0.01)
            if round(lot_size, 2) != lot_size:
                return False, "Lot size must be in 0.01 increments"
            
            return True, ""
            
        except Exception as e:
            return False, f"Lot size validation error: {str(e)}"
    
    def validate_risk_percentage(self, risk_pct: float) -> Tuple[bool, str]:
        """
        Validate risk percentage input.
        
        Args:
            risk_pct: Risk percentage to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if risk_pct <= 0:
                return False, "Risk percentage must be greater than 0"
            
            if risk_pct > 10:
                return False, "Risk percentage too high (max: 10%)"
            
            if risk_pct > 5:
                return True, "WARNING: High risk percentage (>5%)"
            
            return True, ""
            
        except Exception as e:
            return False, f"Risk validation error: {str(e)}"
    
    def validate_confidence_level(self, confidence: float) -> Tuple[bool, str]:
        """
        Validate confidence level input.
        
        Args:
            confidence: Confidence level to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if confidence < 0 or confidence > 100:
                return False, "Confidence must be between 0 and 100"
            
            if confidence < 50:
                return True, "WARNING: Low confidence threshold (<50%)"
            
            return True, ""
            
        except Exception as e:
            return False, f"Confidence validation error: {str(e)}"

    def add_symbol(self):
        """Add a new symbol to the list with validation."""
        try:
            symbol = self.symbol_combo.currentText().strip().upper()
            
            # Validate symbol
            is_valid, error_msg = self.validate_symbol_input(symbol)
            if not is_valid:
                self.logger.error(f"❌ Invalid symbol: {error_msg}")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Invalid Symbol", f"Symbol validation failed:\n{error_msg}")
                return
            
            # Check if already exists
            if symbol in [self.symbol_combo.itemText(i) for i in range(self.symbol_combo.count())]:
                self.logger.warning(f"⚠️ Symbol {symbol} already exists")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "Symbol Exists", f"Symbol {symbol} is already in the list")
                return
            
            # Try to validate with MT5 if available
            if hasattr(self, 'trade_engine') and self.trade_engine.mt5_client.connected:
                symbol_info = self.trade_engine.mt5_client.get_symbol_info(symbol)
                if not symbol_info:
                    self.logger.warning(f"⚠️ Symbol {symbol} not found in MT5")
                    from PyQt5.QtWidgets import QMessageBox
                    reply = QMessageBox.question(
                        self, "Symbol Not Found", 
                        f"Symbol {symbol} not found in MT5. Add anyway?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
            
            # Add symbol
            self.symbol_combo.addItem(symbol)
            self.symbol_combo.setCurrentText(symbol)
            self.logger.info(f"✅ Added symbol: {symbol}")

        except Exception as e:
            self.logger.error(f"❌ Add symbol error: {str(e)}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to add symbol:\n{str(e)}")
    
    def validate_trading_parameters(self) -> Tuple[bool, List[str]]:
        """
        Validate all trading parameters.
        
        Returns:
            Tuple of (all_valid, error_messages)
        """
        errors = []
        
        try:
            # Validate lot size
            lot_size = self.lot_spin.value()
            is_valid, error_msg = self.validate_lot_size(lot_size)
            if not is_valid:
                errors.append(f"Lot Size: {error_msg}")
            
            # Validate risk percentage
            risk_pct = self.risk_spin.value()
            is_valid, error_msg = self.validate_risk_percentage(risk_pct)
            if not is_valid:
                errors.append(f"Risk %: {error_msg}")
            elif "WARNING" in error_msg:
                self.logger.warning(f"⚠️ {error_msg}")
            
            # Validate max positions
            max_pos = self.max_pos_spin.value()
            if max_pos <= 0:
                errors.append("Max Positions: Must be greater than 0")
            elif max_pos > 20:
                errors.append("Max Positions: Too high (max: 20)")
            
            # Validate confidence level
            confidence = self.min_confidence_spin.value()
            is_valid, error_msg = self.validate_confidence_level(confidence)
            if not is_valid:
                errors.append(f"Min Confidence: {error_msg}")
            elif "WARNING" in error_msg:
                self.logger.warning(f"⚠️ {error_msg}")
            
            # Validate symbol selection
            current_symbol = self.symbol_combo.currentText().strip()
            if current_symbol:
                is_valid, error_msg = self.validate_symbol_input(current_symbol)
                if not is_valid:
                    errors.append(f"Selected Symbol: {error_msg}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            self.logger.error(f"❌ Parameter validation error: {str(e)}")
            errors.append(f"Validation error: {str(e)}")
            return False, errors

    def update_status(self):
        """Update trading status."""
        try:
            if self.trade_engine.running and self.trade_engine.trading_enabled:
                if self.live_trading_check.isChecked():
                    self.status_label.setText("Status: 🔴 LIVE TRADING ACTIVE")
                    self.status_label.setStyleSheet("color: red; font-weight: bold;")
                else:
                    self.status_label.setText("Status: 🟡 Monitoring Only")
                    self.status_label.setStyleSheet("color: orange;")
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
        # Note: setMaximumBlockCount is not available in all PyQt5 versions
        # Instead we'll manually manage log size in append_log method

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

class PerformanceMonitorWidget(QGroupBox):
    """Widget for real-time performance monitoring."""

    def __init__(self, trade_engine):
        super().__init__("📊 Performance Monitor")
        self.trade_engine = trade_engine
        self.logger = get_logger(__name__)
        self.performance_history = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Performance metrics display
        self.performance_text = QTextEdit()
        self.performance_text.setReadOnly(True)
        self.performance_text.setMaximumHeight(200)
        self.performance_text.setFont(QFont("Consolas", 9))

        layout.addWidget(self.performance_text)
        self.setLayout(layout)

    def update_data(self):
        """Update performance monitoring data."""
        try:
            # Get engine status
            engine_status = self.trade_engine.get_engine_status()
            account_info = engine_status.get("account_info", {})
            
            if not account_info:
                self.performance_text.setText("No account data available")
                return

            # Calculate performance metrics
            current_time = datetime.now()
            equity = account_info.get("equity", 0)
            balance = account_info.get("balance", 0)
            profit = account_info.get("profit", 0)
            
            # Store performance point
            perf_point = {
                "timestamp": current_time,
                "equity": equity,
                "balance": balance,
                "profit": profit,
                "positions": engine_status.get("active_positions", 0)
            }
            
            self.performance_history.append(perf_point)
            
            # Keep only last 1000 points
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]

            # Calculate statistics
            if len(self.performance_history) > 1:
                start_equity = self.performance_history[0]["equity"]
                current_equity = equity
                total_return = ((current_equity - start_equity) / start_equity * 100) if start_equity > 0 else 0
                
                # Calculate hourly performance
                one_hour_ago = current_time - timedelta(hours=1)
                recent_points = [p for p in self.performance_history if p["timestamp"] >= one_hour_ago]
                
                hourly_return = 0
                if len(recent_points) > 1:
                    start_hour_equity = recent_points[0]["equity"]
                    hourly_return = ((current_equity - start_hour_equity) / start_hour_equity * 100) if start_hour_equity > 0 else 0
                
                # Calculate win rate (simplified)
                strategy_stats = engine_status.get("strategy_stats", {})
                total_signals = strategy_stats.get("total_signals", 0)
                avg_confidence = strategy_stats.get("avg_confidence", 0)
                
                # Calculate volatility (equity changes)
                if len(self.performance_history) > 10:
                    recent_equities = [p["equity"] for p in self.performance_history[-10:]]
                    equity_changes = [abs(recent_equities[i] - recent_equities[i-1]) for i in range(1, len(recent_equities))]
                    avg_volatility = sum(equity_changes) / len(equity_changes) if equity_changes else 0
                    volatility_pct = (avg_volatility / equity * 100) if equity > 0 else 0
                else:
                    volatility_pct = 0

                # Format performance text
                perf_text = f"""📈 REAL-TIME PERFORMANCE METRICS

💰 ACCOUNT STATUS:
   Balance:     ${balance:,.2f}
   Equity:      ${equity:,.2f}
   P&L:         ${profit:,.2f}
   Margin:      ${account_info.get('margin', 0):,.2f}

📊 PERFORMANCE:
   Total Return:    {total_return:+.2f}%
   Hourly Return:   {hourly_return:+.2f}%
   Volatility:      {volatility_pct:.2f}%

🎯 TRADING STATS:
   Active Positions: {engine_status.get('active_positions', 0)}
   Total Signals:    {total_signals}
   Avg Confidence:   {avg_confidence:.1f}%
   Engine Status:    {'🟢 Running' if engine_status.get('running') else '🔴 Stopped'}
   Trading:          {'🟢 Active' if engine_status.get('trading_enabled') else '🛑 Disabled'}

⏱️ UPTIME:
   Last Update:      {engine_status.get('last_update', 'Never')}
   Data Points:      {len(self.performance_history)}
   Symbols:          {engine_status.get('symbols_monitored', 0)}
"""

                # Color coding based on performance
                if total_return > 2:
                    self.performance_text.setStyleSheet("color: #00ff00; font-weight: bold;")  # Bright green
                elif total_return > 0:
                    self.performance_text.setStyleSheet("color: #90EE90;")  # Light green
                elif total_return > -2:
                    self.performance_text.setStyleSheet("color: #ffffff;")  # White
                elif total_return > -5:
                    self.performance_text.setStyleSheet("color: #FFA500;")  # Orange
                else:
                    self.performance_text.setStyleSheet("color: #ff4444; font-weight: bold;")  # Red

                self.performance_text.setText(perf_text)

            else:
                self.performance_text.setText("Collecting performance data...")

        except Exception as e:
            self.logger.error(f"❌ Performance monitor update error: {str(e)}")
            self.performance_text.setText(f"Performance monitor error: {str(e)}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for export."""
        try:
            if not self.performance_history:
                return {"error": "No performance data available"}

            latest = self.performance_history[-1]
            start = self.performance_history[0]
            
            return {
                "start_time": start["timestamp"],
                "end_time": latest["timestamp"],
                "start_equity": start["equity"],
                "current_equity": latest["equity"],
                "total_return_pct": ((latest["equity"] - start["equity"]) / start["equity"] * 100) if start["equity"] > 0 else 0,
                "data_points": len(self.performance_history),
                "max_equity": max(p["equity"] for p in self.performance_history),
                "min_equity": min(p["equity"] for p in self.performance_history)
            }

        except Exception as e:
            return {"error": str(e)}

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