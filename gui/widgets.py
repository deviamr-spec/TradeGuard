"""
GUI Widgets for MT5 Trading Bot.
Reusable PyQt5 components for trading interface.
"""

import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QTextEdit,
    QProgressBar, QGroupBox, QHeaderView, QFrame, QScrollArea,
    QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QPen, QBrush

from utils.logging_setup import get_logger

class AccountInfoWidget(QGroupBox):
    """Widget displaying account information."""
    
    def __init__(self, mt5_client):
        super().__init__("💰 Account Information")
        self.logger = get_logger(__name__)
        self.mt5_client = mt5_client
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components."""
        layout = QGridLayout(self)
        layout.setSpacing(8)
        
        # Account details labels
        self.labels = {
            "login": QLabel("Login:"),
            "server": QLabel("Server:"),
            "balance": QLabel("Balance:"),
            "equity": QLabel("Equity:"),
            "margin": QLabel("Margin:"),
            "free_margin": QLabel("Free Margin:"),
            "margin_level": QLabel("Margin Level:"),
            "profit": QLabel("Floating P&L:")
        }
        
        self.values = {
            "login": QLabel("N/A"),
            "server": QLabel("N/A"),
            "balance": QLabel("$0.00"),
            "equity": QLabel("$0.00"),
            "margin": QLabel("$0.00"),
            "free_margin": QLabel("$0.00"),
            "margin_level": QLabel("0.00%"),
            "profit": QLabel("$0.00")
        }
        
        # Set up labels
        for key, label in self.labels.items():
            label.setFont(QFont("Arial", 9, QFont.Bold))
            
        for key, value in self.values.items():
            value.setFont(QFont("Arial", 9))
            value.setStyleSheet("color: #ffffff; background-color: #1e1e1e; padding: 4px; border-radius: 2px;")
        
        # Layout
        row = 0
        for key in self.labels.keys():
            layout.addWidget(self.labels[key], row, 0)
            layout.addWidget(self.values[key], row, 1)
            row += 1
        
        # Connection status indicator
        self.connection_status = QLabel("🔴 Disconnected")
        self.connection_status.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(self.connection_status, row, 0, 1, 2)
        
        layout.setColumnStretch(1, 1)
    
    def update_data(self):
        """Update account information."""
        try:
            if not self.mt5_client or not self.mt5_client.connected:
                self.connection_status.setText("🔴 Disconnected")
                return
            
            account_info = self.mt5_client.get_account_info()
            if not account_info:
                return
            
            # Update values
            self.values["login"].setText(str(account_info.get("login", "N/A")))
            self.values["server"].setText(str(account_info.get("server", "N/A")))
            self.values["balance"].setText(f"${account_info.get('balance', 0):,.2f}")
            self.values["equity"].setText(f"${account_info.get('equity', 0):,.2f}")
            self.values["margin"].setText(f"${account_info.get('margin', 0):,.2f}")
            self.values["free_margin"].setText(f"${account_info.get('free_margin', 0):,.2f}")
            
            # Margin level with color coding
            margin_level = account_info.get('margin_level', 0)
            self.values["margin_level"].setText(f"{margin_level:.2f}%")
            if margin_level < 200:
                self.values["margin_level"].setStyleSheet("color: #ff4444; background-color: #1e1e1e; padding: 4px; border-radius: 2px;")
            elif margin_level < 500:
                self.values["margin_level"].setStyleSheet("color: #ffaa00; background-color: #1e1e1e; padding: 4px; border-radius: 2px;")
            else:
                self.values["margin_level"].setStyleSheet("color: #44ff44; background-color: #1e1e1e; padding: 4px; border-radius: 2px;")
            
            # Floating P&L with color coding
            profit = account_info.get('profit', 0)
            self.values["profit"].setText(f"${profit:,.2f}")
            if profit > 0:
                self.values["profit"].setStyleSheet("color: #44ff44; background-color: #1e1e1e; padding: 4px; border-radius: 2px;")
            elif profit < 0:
                self.values["profit"].setStyleSheet("color: #ff4444; background-color: #1e1e1e; padding: 4px; border-radius: 2px;")
            else:
                self.values["profit"].setStyleSheet("color: #ffffff; background-color: #1e1e1e; padding: 4px; border-radius: 2px;")
            
            self.connection_status.setText("🟢 Connected")
            
        except Exception as e:
            self.logger.error(f"❌ Account widget update error: {str(e)}")
            self.connection_status.setText("🔴 Error")
    
    def fast_update(self):
        """Fast update for real-time data."""
        try:
            if self.mt5_client and self.mt5_client.connected:
                # Quick update of equity and profit only
                account_info = self.mt5_client.get_account_info()
                if account_info:
                    equity = account_info.get('equity', 0)
                    profit = account_info.get('profit', 0)
                    
                    self.values["equity"].setText(f"${equity:,.2f}")
                    self.values["profit"].setText(f"${profit:,.2f}")
                    
                    # Update profit color
                    if profit > 0:
                        self.values["profit"].setStyleSheet("color: #44ff44; background-color: #1e1e1e; padding: 4px; border-radius: 2px;")
                    elif profit < 0:
                        self.values["profit"].setStyleSheet("color: #ff4444; background-color: #1e1e1e; padding: 4px; border-radius: 2px;")
                    else:
                        self.values["profit"].setStyleSheet("color: #ffffff; background-color: #1e1e1e; padding: 4px; border-radius: 2px;")
                        
        except Exception as e:
            pass  # Ignore errors in fast update

class TradingControlWidget(QGroupBox):
    """Widget for trading controls and settings."""
    
    def __init__(self, trade_engine):
        super().__init__("🎮 Trading Controls")
        self.logger = get_logger(__name__)
        self.trade_engine = trade_engine
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Trading status
        self.status_label = QLabel("🛑 Trading Stopped")
        self.status_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(self.status_label)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("▶️ Start")
        self.start_button.setMinimumHeight(35)
        self.start_button.setStyleSheet("QPushButton { background-color: #28a745; }")
        
        self.stop_button = QPushButton("⏹️ Stop")
        self.stop_button.setMinimumHeight(35)
        self.stop_button.setStyleSheet("QPushButton { background-color: #dc3545; }")
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)
        
        # Symbol selection
        symbols_layout = QVBoxLayout()
        symbols_layout.addWidget(QLabel("Trading Symbols:"))
        
        self.symbols_combo = QComboBox()
        self.symbols_combo.addItems(["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURJPY", "GBPJPY"])
        symbols_layout.addWidget(self.symbols_combo)
        
        layout.addLayout(symbols_layout)
        
        # Strategy settings
        strategy_group = QGroupBox("Strategy Settings")
        strategy_layout = QGridLayout(strategy_group)
        
        # Risk per trade
        strategy_layout.addWidget(QLabel("Risk per Trade:"), 0, 0)
        self.risk_spinbox = QDoubleSpinBox()
        self.risk_spinbox.setRange(0.1, 5.0)
        self.risk_spinbox.setValue(1.0)
        self.risk_spinbox.setSuffix("%")
        strategy_layout.addWidget(self.risk_spinbox, 0, 1)
        
        # Take Profit
        strategy_layout.addWidget(QLabel("Take Profit:"), 1, 0)
        self.tp_spinbox = QDoubleSpinBox()
        self.tp_spinbox.setRange(5, 100)
        self.tp_spinbox.setValue(10.0)
        self.tp_spinbox.setSuffix(" pips")
        strategy_layout.addWidget(self.tp_spinbox, 1, 1)
        
        # Stop Loss
        strategy_layout.addWidget(QLabel("Stop Loss:"), 2, 0)
        self.sl_spinbox = QDoubleSpinBox()
        self.sl_spinbox.setRange(3, 50)
        self.sl_spinbox.setValue(5.0)
        self.sl_spinbox.setSuffix(" pips")
        strategy_layout.addWidget(self.sl_spinbox, 2, 1)
        
        layout.addWidget(strategy_group)
        
        # Emergency controls
        emergency_layout = QVBoxLayout()
        
        self.close_all_button = QPushButton("🚨 Close All Positions")
        self.close_all_button.setMinimumHeight(35)
        self.close_all_button.setStyleSheet("QPushButton { background-color: #fd7e14; }")
        emergency_layout.addWidget(self.close_all_button)
        
        layout.addLayout(emergency_layout)
        
        # Add stretch to push everything to top
        layout.addStretch()
    
    def connect_signals(self):
        """Connect widget signals."""
        try:
            self.start_button.clicked.connect(self.start_trading)
            self.stop_button.clicked.connect(self.stop_trading)
            self.close_all_button.clicked.connect(self.close_all_positions)
            
        except Exception as e:
            self.logger.error(f"❌ Signal connection error: {str(e)}")
    
    def start_trading(self):
        """Start trading."""
        try:
            if not self.trade_engine.running:
                if self.trade_engine.start():
                    self.status_label.setText("🟢 Trading Active")
                    self.start_button.setEnabled(False)
                    self.stop_button.setEnabled(True)
            else:
                self.trade_engine.enable_trading()
                self.status_label.setText("🟢 Trading Active")
                
        except Exception as e:
            self.logger.error(f"❌ Start trading error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to start trading:\n{str(e)}")
    
    def stop_trading(self):
        """Stop trading."""
        try:
            self.trade_engine.disable_trading()
            self.status_label.setText("🛑 Trading Stopped")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
        except Exception as e:
            self.logger.error(f"❌ Stop trading error: {str(e)}")
    
    def close_all_positions(self):
        """Close all positions."""
        try:
            reply = QMessageBox.question(
                self,
                "Close All Positions",
                "Are you sure you want to close ALL positions?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # This would be handled by the main window
                self.parent().parent().parent().close_all_positions()
                
        except Exception as e:
            self.logger.error(f"❌ Close all positions error: {str(e)}")

class PositionsWidget(QGroupBox):
    """Widget displaying open positions."""
    
    def __init__(self, mt5_client, trade_engine):
        super().__init__("💼 Open Positions")
        self.logger = get_logger(__name__)
        self.mt5_client = mt5_client
        self.trade_engine = trade_engine
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        
        # Positions table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Ticket", "Symbol", "Type", "Volume", "Open Price", 
            "Current Price", "S/L", "T/P", "Profit"
        ])
        
        # Configure table
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        
        layout.addWidget(self.table)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("🔄 Refresh")
        self.close_selected_button = QPushButton("❌ Close Selected")
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.close_selected_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Connect signals
        self.refresh_button.clicked.connect(self.update_data)
        self.close_selected_button.clicked.connect(self.close_selected_position)
    
    def update_data(self):
        """Update positions table."""
        try:
            if not self.mt5_client or not self.mt5_client.connected:
                self.table.setRowCount(0)
                return
            
            positions = self.mt5_client.get_positions()
            self.table.setRowCount(len(positions))
            
            for row, position in enumerate(positions):
                # Ticket
                self.table.setItem(row, 0, QTableWidgetItem(str(position.get("ticket", ""))))
                
                # Symbol
                self.table.setItem(row, 1, QTableWidgetItem(position.get("symbol", "")))
                
                # Type
                pos_type = position.get("type", "")
                type_item = QTableWidgetItem(pos_type)
                if pos_type == "BUY":
                    type_item.setBackground(QColor(40, 167, 69, 100))
                else:
                    type_item.setBackground(QColor(220, 53, 69, 100))
                self.table.setItem(row, 2, type_item)
                
                # Volume
                self.table.setItem(row, 3, QTableWidgetItem(f"{position.get('volume', 0):.2f}"))
                
                # Open Price
                self.table.setItem(row, 4, QTableWidgetItem(f"{position.get('price_open', 0):.5f}"))
                
                # Current Price
                self.table.setItem(row, 5, QTableWidgetItem(f"{position.get('price_current', 0):.5f}"))
                
                # Stop Loss
                sl = position.get('sl', 0)
                self.table.setItem(row, 6, QTableWidgetItem(f"{sl:.5f}" if sl > 0 else "None"))
                
                # Take Profit
                tp = position.get('tp', 0)
                self.table.setItem(row, 7, QTableWidgetItem(f"{tp:.5f}" if tp > 0 else "None"))
                
                # Profit
                profit = position.get('profit', 0)
                profit_item = QTableWidgetItem(f"${profit:.2f}")
                if profit > 0:
                    profit_item.setForeground(QColor(68, 255, 68))
                elif profit < 0:
                    profit_item.setForeground(QColor(255, 68, 68))
                self.table.setItem(row, 8, profit_item)
            
        except Exception as e:
            self.logger.error(f"❌ Positions update error: {str(e)}")
    
    def close_selected_position(self):
        """Close selected position."""
        try:
            current_row = self.table.currentRow()
            if current_row < 0:
                QMessageBox.information(self, "Info", "Please select a position to close.")
                return
            
            ticket_item = self.table.item(current_row, 0)
            if not ticket_item:
                return
            
            ticket = int(ticket_item.text())
            symbol = self.table.item(current_row, 1).text()
            
            reply = QMessageBox.question(
                self,
                "Close Position",
                f"Close position {ticket} ({symbol})?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if self.trade_engine.force_close_position(ticket):
                    QMessageBox.information(self, "Success", "Position closed successfully.")
                    self.update_data()
                else:
                    QMessageBox.warning(self, "Error", "Failed to close position.")
                    
        except Exception as e:
            self.logger.error(f"❌ Close position error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error closing position:\n{str(e)}")

class EquityChartWidget(QGroupBox):
    """Widget displaying equity chart."""
    
    def __init__(self, reporting_manager):
        super().__init__("📈 Equity Chart")
        self.logger = get_logger(__name__)
        self.reporting_manager = reporting_manager
        self.equity_data = []
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        
        # Chart canvas (simplified)
        self.chart_widget = QWidget()
        self.chart_widget.setMinimumHeight(300)
        self.chart_widget.setStyleSheet("background-color: #1e1e1e; border: 1px solid #555555;")
        layout.addWidget(self.chart_widget)
        
        # Chart info
        info_layout = QHBoxLayout()
        
        self.start_equity_label = QLabel("Start: $0.00")
        self.current_equity_label = QLabel("Current: $0.00")
        self.profit_label = QLabel("P&L: $0.00")
        
        info_layout.addWidget(self.start_equity_label)
        info_layout.addWidget(self.current_equity_label)
        info_layout.addWidget(self.profit_label)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
    
    def paintEvent(self, event):
        """Custom paint event to draw equity chart."""
        super().paintEvent(event)
        try:
            if not self.equity_data or len(self.equity_data) < 2:
                return
            
            painter = QPainter(self.chart_widget)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Get widget dimensions
            rect = self.chart_widget.rect()
            margin = 20
            chart_rect = rect.adjusted(margin, margin, -margin, -margin)
            
            if chart_rect.width() <= 0 or chart_rect.height() <= 0:
                return
            
            # Calculate data ranges
            equity_values = [point["equity"] for point in self.equity_data]
            min_equity = min(equity_values)
            max_equity = max(equity_values)
            
            if max_equity == min_equity:
                max_equity += 1  # Avoid division by zero
            
            # Draw chart line
            painter.setPen(QPen(QColor(0, 120, 212), 2))
            
            for i in range(1, len(self.equity_data)):
                prev_point = self.equity_data[i-1]
                curr_point = self.equity_data[i]
                
                # Calculate positions
                x1 = chart_rect.left() + (i-1) * chart_rect.width() / (len(self.equity_data) - 1)
                y1 = chart_rect.bottom() - ((prev_point["equity"] - min_equity) / (max_equity - min_equity)) * chart_rect.height()
                
                x2 = chart_rect.left() + i * chart_rect.width() / (len(self.equity_data) - 1)
                y2 = chart_rect.bottom() - ((curr_point["equity"] - min_equity) / (max_equity - min_equity)) * chart_rect.height()
                
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            
        except Exception as e:
            self.logger.error(f"❌ Chart paint error: {str(e)}")
    
    def update_data(self):
        """Update equity chart data."""
        try:
            if not self.reporting_manager:
                return
            
            # Get equity data for last 24 hours
            self.equity_data = self.reporting_manager.get_equity_data_for_chart(24)
            
            if self.equity_data:
                start_equity = self.equity_data[0]["equity"]
                current_equity = self.equity_data[-1]["equity"]
                profit = current_equity - start_equity
                
                self.start_equity_label.setText(f"Start: ${start_equity:,.2f}")
                self.current_equity_label.setText(f"Current: ${current_equity:,.2f}")
                
                profit_text = f"P&L: ${profit:,.2f}"
                if profit > 0:
                    self.profit_label.setText(profit_text)
                    self.profit_label.setStyleSheet("color: #44ff44;")
                elif profit < 0:
                    self.profit_label.setText(profit_text)
                    self.profit_label.setStyleSheet("color: #ff4444;")
                else:
                    self.profit_label.setText(profit_text)
                    self.profit_label.setStyleSheet("color: #ffffff;")
                
                # Trigger repaint
                self.chart_widget.update()
            
        except Exception as e:
            self.logger.error(f"❌ Equity chart update error: {str(e)}")

class StrategyStatsWidget(QGroupBox):
    """Widget displaying strategy statistics."""
    
    def __init__(self, strategy):
        super().__init__("📊 Strategy Statistics")
        self.logger = get_logger(__name__)
        self.strategy = strategy
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components."""
        layout = QGridLayout(self)
        
        # Strategy stats labels
        self.labels = {
            "total_signals": QLabel("Total Signals:"),
            "buy_signals": QLabel("Buy Signals:"),
            "sell_signals": QLabel("Sell Signals:"),
            "avg_confidence": QLabel("Avg Confidence:"),
            "recent_signals": QLabel("Recent (24h):"),
            "symbols_analyzed": QLabel("Symbols Analyzed:")
        }
        
        self.values = {
            "total_signals": QLabel("0"),
            "buy_signals": QLabel("0"),
            "sell_signals": QLabel("0"),
            "avg_confidence": QLabel("0.0%"),
            "recent_signals": QLabel("0"),
            "symbols_analyzed": QLabel("0")
        }
        
        # Set up labels
        for key, label in self.labels.items():
            label.setFont(QFont("Arial", 9, QFont.Bold))
            
        for key, value in self.values.items():
            value.setFont(QFont("Arial", 9))
            value.setStyleSheet("color: #ffffff; background-color: #1e1e1e; padding: 4px; border-radius: 2px;")
        
        # Layout
        row = 0
        for key in self.labels.keys():
            layout.addWidget(self.labels[key], row, 0)
            layout.addWidget(self.values[key], row, 1)
            row += 1
        
        layout.setColumnStretch(1, 1)
    
    def update_data(self):
        """Update strategy statistics."""
        try:
            if not self.strategy:
                return
            
            stats = self.strategy.get_strategy_stats()
            
            if stats.get("no_data"):
                for value in self.values.values():
                    value.setText("N/A")
                return
            
            self.values["total_signals"].setText(str(stats.get("total_signals", 0)))
            self.values["buy_signals"].setText(str(stats.get("buy_signals", 0)))
            self.values["sell_signals"].setText(str(stats.get("sell_signals", 0)))
            self.values["avg_confidence"].setText(f"{stats.get('avg_confidence', 0):.1f}%")
            self.values["recent_signals"].setText(str(stats.get("recent_signals_24h", 0)))
            self.values["symbols_analyzed"].setText(str(stats.get("symbols_analyzed", 0)))
            
        except Exception as e:
            self.logger.error(f"❌ Strategy stats update error: {str(e)}")

class RiskMonitorWidget(QGroupBox):
    """Widget for risk monitoring."""
    
    def __init__(self, risk_manager):
        super().__init__("🛡️ Risk Monitor")
        self.logger = get_logger(__name__)
        self.risk_manager = risk_manager
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        
        # Risk metrics
        metrics_layout = QGridLayout()
        
        self.daily_trades_label = QLabel("Daily Trades:")
        self.daily_trades_value = QLabel("0 / 50")
        
        self.daily_pl_label = QLabel("Daily P&L:")
        self.daily_pl_value = QLabel("$0.00")
        
        self.max_dd_label = QLabel("Max Drawdown:")
        self.max_dd_value = QLabel("0.00%")
        
        self.risk_score_label = QLabel("Risk Score:")
        self.risk_score_value = QLabel("Low")
        
        metrics_layout.addWidget(self.daily_trades_label, 0, 0)
        metrics_layout.addWidget(self.daily_trades_value, 0, 1)
        metrics_layout.addWidget(self.daily_pl_label, 1, 0)
        metrics_layout.addWidget(self.daily_pl_value, 1, 1)
        metrics_layout.addWidget(self.max_dd_label, 2, 0)
        metrics_layout.addWidget(self.max_dd_value, 2, 1)
        metrics_layout.addWidget(self.risk_score_label, 3, 0)
        metrics_layout.addWidget(self.risk_score_value, 3, 1)
        
        layout.addLayout(metrics_layout)
        
        # Risk progress bars
        self.daily_limit_bar = QProgressBar()
        self.daily_limit_bar.setMaximum(100)
        self.daily_limit_bar.setTextVisible(True)
        self.daily_limit_bar.setFormat("Daily Limit: %p%")
        layout.addWidget(self.daily_limit_bar)
        
        self.drawdown_bar = QProgressBar()
        self.drawdown_bar.setMaximum(100)
        self.drawdown_bar.setTextVisible(True)
        self.drawdown_bar.setFormat("Drawdown: %p%")
        layout.addWidget(self.drawdown_bar)
    
    def update_data(self):
        """Update risk monitoring data."""
        try:
            if not self.risk_manager:
                return
            
            risk_report = self.risk_manager.get_risk_report()
            
            if "error" in risk_report:
                return
            
            # Update labels
            current_status = risk_report.get("current_status", {})
            session_stats = risk_report.get("session_stats", {})
            
            daily_trades = current_status.get("daily_trades", 0)
            max_trades = risk_report.get("risk_parameters", {}).get("max_daily_trades", 50)
            self.daily_trades_value.setText(f"{daily_trades} / {max_trades}")
            
            daily_profit = session_stats.get("profit", 0.0)
            self.daily_pl_value.setText(f"${daily_profit:.2f}")
            if daily_profit > 0:
                self.daily_pl_value.setStyleSheet("color: #44ff44;")
            elif daily_profit < 0:
                self.daily_pl_value.setStyleSheet("color: #ff4444;")
            else:
                self.daily_pl_value.setStyleSheet("color: #ffffff;")
            
            max_drawdown = session_stats.get("max_drawdown", 0.0)
            self.max_dd_value.setText(f"{max_drawdown:.2f}%")
            
            # Update progress bars
            trade_progress = (daily_trades / max_trades) * 100 if max_trades > 0 else 0
            self.daily_limit_bar.setValue(int(trade_progress))
            
            max_dd_limit = risk_report.get("risk_parameters", {}).get("max_drawdown", 0.10) * 100
            dd_progress = (max_drawdown / max_dd_limit) * 100 if max_dd_limit > 0 else 0
            self.drawdown_bar.setValue(int(dd_progress))
            
            # Color coding for progress bars
            if trade_progress > 80:
                self.daily_limit_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff4444; }")
            elif trade_progress > 60:
                self.daily_limit_bar.setStyleSheet("QProgressBar::chunk { background-color: #ffaa00; }")
            else:
                self.daily_limit_bar.setStyleSheet("QProgressBar::chunk { background-color: #44ff44; }")
            
            if dd_progress > 80:
                self.drawdown_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff4444; }")
            elif dd_progress > 60:
                self.drawdown_bar.setStyleSheet("QProgressBar::chunk { background-color: #ffaa00; }")
            else:
                self.drawdown_bar.setStyleSheet("QProgressBar::chunk { background-color: #44ff44; }")
            
            # Risk score
            violations = risk_report.get("violations", {})
            recent_violations = len(violations.get("recent_violations", []))
            
            if recent_violations > 3:
                self.risk_score_value.setText("High")
                self.risk_score_value.setStyleSheet("color: #ff4444;")
            elif recent_violations > 1:
                self.risk_score_value.setText("Medium")
                self.risk_score_value.setStyleSheet("color: #ffaa00;")
            else:
                self.risk_score_value.setText("Low")
                self.risk_score_value.setStyleSheet("color: #44ff44;")
            
        except Exception as e:
            self.logger.error(f"❌ Risk monitor update error: {str(e)}")

class LogWidget(QGroupBox):
    """Widget for displaying log messages."""
    
    def __init__(self):
        super().__init__("📋 System Logs")
        self.logger = get_logger(__name__)
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)  # Limit log entries
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)
        
        # Log controls
        controls_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("🗑️ Clear")
        self.export_button = QPushButton("💾 Export")
        
        controls_layout.addWidget(self.clear_button)
        controls_layout.addWidget(self.export_button)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Connect signals
        self.clear_button.clicked.connect(self.clear_logs)
        self.export_button.clicked.connect(self.export_logs)
        
        # Add initial message
        self.add_message("System initialized", "INFO")
    
    def add_message(self, message: str, level: str = "INFO"):
        """Add a log message."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Color coding by level
            color_map = {
                "INFO": "#ffffff",
                "WARNING": "#ffaa00", 
                "ERROR": "#ff4444",
                "SUCCESS": "#44ff44",
                "DEBUG": "#888888"
            }
            
            color = color_map.get(level, "#ffffff")
            
            formatted_message = f'<span style="color: {color};">[{timestamp}] {level}: {message}</span>'
            
            self.log_text.append(formatted_message)
            
            # Auto-scroll to bottom
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            self.logger.error(f"❌ Log message error: {str(e)}")
    
    def clear_logs(self):
        """Clear all log messages."""
        try:
            self.log_text.clear()
            self.add_message("Logs cleared", "INFO")
        except Exception as e:
            self.logger.error(f"❌ Clear logs error: {str(e)}")
    
    def export_logs(self):
        """Export logs to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gui_logs_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())
            
            self.add_message(f"Logs exported to {filename}", "SUCCESS")
            
        except Exception as e:
            self.logger.error(f"❌ Export logs error: {str(e)}")
            self.add_message(f"Export failed: {str(e)}", "ERROR")

