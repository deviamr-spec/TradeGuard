"""
Reporting Module for MT5 Trading Bot.
Handles performance tracking, trade logging, and report generation.
"""

import pandas as pd
import numpy as np
import csv
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from utils.logging_setup import get_logger

class ReportingManager:
    """Performance reporting and analytics manager."""

    def __init__(self):
        self.logger = get_logger(__name__)

        # Data storage
        self.equity_curve = []
        self.trade_log = []
        self.session_data = {}

        # Performance metrics
        self.start_time = datetime.now()
        self.start_balance = 0.0

        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)

        self.logger.info("📊 Reporting Manager initialized")

    def initialize_session(self, account_info: Dict[str, Any]) -> None:
        """Initialize a new reporting session."""
        try:
            self.start_time = datetime.now()
            self.start_balance = account_info.get("balance", 0.0)

            self.session_data = {
                "start_time": self.start_time,
                "start_balance": self.start_balance,
                "account_login": account_info.get("login", "Unknown"),
                "account_server": account_info.get("server", "Unknown"),
                "account_currency": account_info.get("currency", "USD")
            }

            # Initialize equity curve
            self.equity_curve = [{
                "timestamp": self.start_time,
                "equity": account_info.get("equity", self.start_balance),
                "balance": self.start_balance
            }]

            self.logger.info(f"📊 Reporting session initialized: ${self.start_balance:,.2f}")

        except Exception as e:
            self.logger.error(f"❌ Reporting initialization error: {str(e)}")

    def add_equity_point(self, equity: float, balance: float = None) -> None:
        """Add a point to the equity curve."""
        try:
            equity_point = {
                "timestamp": datetime.now(),
                "equity": equity,
                "balance": balance or equity
            }

            self.equity_curve.append(equity_point)

            # Keep only last 1000 points to prevent memory issues
            if len(self.equity_curve) > 1000:
                self.equity_curve = self.equity_curve[-1000:]

        except Exception as e:
            self.logger.error(f"❌ Equity point error: {str(e)}")

    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """Log a trade execution."""
        try:
            trade_record = {
                "timestamp": datetime.now(),
                "symbol": trade_data.get("symbol"),
                "type": trade_data.get("type"),
                "volume": trade_data.get("volume"),
                "entry_price": trade_data.get("price"),
                "sl": trade_data.get("sl", 0),
                "tp": trade_data.get("tp", 0),
                "order": trade_data.get("order"),
                "deal": trade_data.get("deal"),
                "comment": trade_data.get("comment", ""),
                "exit_price": None,
                "profit": None,
                "commission": None,
                "swap": None,
                "closed": False
            }

            self.trade_log.append(trade_record)

            # Log to CSV
            self._log_trade_to_csv(trade_record)

            self.logger.info(f"📝 Trade logged: {trade_record['symbol']} {trade_record['type']}")

        except Exception as e:
            self.logger.error(f"❌ Trade logging error: {str(e)}")

    def update_trade_outcome(self, order_id: int, outcome_data: Dict[str, Any]) -> None:
        """Update trade outcome when position is closed."""
        try:
            # Find the trade in log
            for trade in self.trade_log:
                if trade.get("order") == order_id:
                    trade.update({
                        "exit_price": outcome_data.get("exit_price"),
                        "profit": outcome_data.get("profit"),
                        "commission": outcome_data.get("commission"),
                        "swap": outcome_data.get("swap"),
                        "closed": True,
                        "close_time": datetime.now()
                    })

                    self.logger.info(f"📝 Trade outcome updated: Order {order_id}, Profit: ${trade['profit']:.2f}")
                    break

        except Exception as e:
            self.logger.error(f"❌ Trade outcome update error: {str(e)}")

    def _log_trade_to_csv(self, trade_record: Dict[str, Any]) -> None:
        """Log trade to CSV file."""
        try:
            filename = "logs/trade_log.csv"
            file_exists = os.path.isfile(filename)

            fieldnames = [
                "timestamp", "symbol", "type", "volume", "entry_price",
                "sl", "tp", "order", "deal", "comment"
            ]

            with open(filename, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                # Filter record to only include fieldnames
                filtered_record = {k: v for k, v in trade_record.items() if k in fieldnames}
                writer.writerow(filtered_record)

        except Exception as e:
            self.logger.error(f"❌ CSV logging error: {str(e)}")

    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        try:
            if not self.equity_curve or len(self.equity_curve) < 2:
                return {"error": "Insufficient data"}

            # Current vs start
            current_equity = self.equity_curve[-1]["equity"]
            total_return = (current_equity - self.start_balance) / self.start_balance * 100

            # Equity curve analysis
            equity_values = [point["equity"] for point in self.equity_curve]
            equity_returns = np.diff(equity_values) / equity_values[:-1]

            # Drawdown calculation
            peak = np.maximum.accumulate(equity_values)
            drawdown = (peak - equity_values) / peak
            max_drawdown = np.max(drawdown) * 100

            # Trade statistics
            closed_trades = [t for t in self.trade_log if t.get("closed", False)]
            winning_trades = [t for t in closed_trades if t.get("profit", 0) > 0]
            losing_trades = [t for t in closed_trades if t.get("profit", 0) < 0]

            total_trades = len(closed_trades)
            win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

            # Profit statistics
            total_profit = sum(t.get("profit", 0) for t in closed_trades)
            avg_win = np.mean([t["profit"] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t["profit"] for t in losing_trades]) if losing_trades else 0
            profit_factor = abs(sum(t["profit"] for t in winning_trades) / sum(t["profit"] for t in losing_trades)) if losing_trades else float('inf')

            # Time-based metrics
            session_duration = datetime.now() - self.start_time

            metrics = {
                "session_duration": str(session_duration).split('.')[0],
                "start_balance": self.start_balance,
                "current_equity": current_equity,
                "total_return": total_return,
                "total_profit": total_profit,
                "max_drawdown": max_drawdown,
                "total_trades": total_trades,
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
                "sharpe_ratio": np.mean(equity_returns) / np.std(equity_returns) * np.sqrt(252) if len(equity_returns) > 1 and np.std(equity_returns) > 0 else 0
            }

            return metrics

        except Exception as e:
            self.logger.error(f"❌ Performance calculation error: {str(e)}")
            return {"error": str(e)}

    def export_report(self, filename: str = None) -> str:
        """Export comprehensive trading report."""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"logs/trading_report_{timestamp}.csv"

            # Get performance metrics
            metrics = self.calculate_performance_metrics()

            # Create report data
            report_data = []

            # Add session summary
            report_data.append(["=== SESSION SUMMARY ==="])
            report_data.append(["Metric", "Value"])
            for key, value in metrics.items():
                if key != "error":
                    report_data.append([key.replace("_", " ").title(), value])

            report_data.append([""])
            report_data.append(["=== TRADE LOG ==="])

            # Add trade headers
            if self.trade_log:
                headers = ["Timestamp", "Symbol", "Type", "Volume", "Entry Price", "Exit Price", "Profit", "Status"]
                report_data.append(headers)

                # Add trade data
                for trade in self.trade_log:
                    row = [
                        trade.get("timestamp", "").strftime("%Y-%m-%d %H:%M:%S") if trade.get("timestamp") else "",
                        trade.get("symbol", ""),
                        trade.get("type", ""),
                        trade.get("volume", ""),
                        trade.get("entry_price", ""),
                        trade.get("exit_price", "") or "Open",
                        trade.get("profit", "") or "Open",
                        "Closed" if trade.get("closed", False) else "Open"
                    ]
                    report_data.append(row)

            # Write to CSV
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(report_data)

            self.logger.info(f"📊 Report exported: {filename}")
            return filename

        except Exception as e:
            self.logger.error(f"❌ Report export error: {str(e)}")
            return f"Export failed: {str(e)}"

    def get_equity_data(self) -> List[Dict[str, Any]]:
        """Get equity curve data for charting."""
        try:
            return self.equity_curve[-100:]  # Return last 100 points
        except Exception as e:
            self.logger.error(f"❌ Equity data error: {str(e)}")
            return []

    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades for display."""
        try:
            return self.trade_log[-limit:] if self.trade_log else []
        except Exception as e:
            self.logger.error(f"❌ Recent trades error: {str(e)}")
            return []