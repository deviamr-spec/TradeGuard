"""
Reporting and Analytics Module.
Handles trade logging, performance tracking, and report generation.
FIXED VERSION - ALL ERRORS RESOLVED
"""

import pandas as pd
import numpy as np
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import os

from utils.logging_setup import get_logger

class ReportingManager:
    """Comprehensive reporting and analytics system."""

    def __init__(self, mt5_client, config: Dict[str, Any] = None):
        self.logger = get_logger(__name__)
        self.mt5_client = mt5_client
        self.config = config or {}

        # Trade tracking
        self.trades = []
        self.equity_history = []
        self.session_start_balance = 0.0
        self.session_start_time = datetime.now()

        # Performance metrics
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_trades = 0
        self.best_trade = 0.0
        self.worst_trade = 0.0

        # Thread safety
        self.lock = threading.Lock()

        # Reports directory
        self.reports_dir = "reports"
        os.makedirs(self.reports_dir, exist_ok=True)

        self.logger.info("✅ Reporting Manager initialized")

    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """Log a new trade."""
        try:
            with self.lock:
                trade_record = {
                    "timestamp": datetime.now(),
                    "symbol": trade_data.get("symbol", ""),
                    "type": trade_data.get("type", ""),
                    "volume": trade_data.get("volume", 0.0),
                    "entry_price": trade_data.get("price", 0.0),
                    "stop_loss": trade_data.get("sl", 0.0),
                    "take_profit": trade_data.get("tp", 0.0),
                    "ticket": trade_data.get("ticket", 0),
                    "comment": trade_data.get("comment", ""),
                    "confidence": trade_data.get("confidence", 0.0),
                    "status": "OPEN"
                }

                self.trades.append(trade_record)
                self.total_trades += 1

                self.logger.info(f"✅ Trade logged: {trade_record['symbol']} {trade_record['type']}")

        except Exception as e:
            self.logger.error(f"❌ Trade logging error: {str(e)}")

    def update_trade_outcome(self, ticket: int, outcome_data: Dict[str, Any]) -> None:
        """Update trade with outcome data."""
        try:
            with self.lock:
                for trade in self.trades:
                    if trade.get("ticket") == ticket:
                        trade.update({
                            "exit_time": datetime.now(),
                            "exit_price": outcome_data.get("exit_price", 0.0),
                            "profit": outcome_data.get("profit", 0.0),
                            "commission": outcome_data.get("commission", 0.0),
                            "swap": outcome_data.get("swap", 0.0),
                            "status": "CLOSED"
                        })

                        # Update statistics
                        profit = outcome_data.get("profit", 0.0)
                        if profit > 0:
                            self.winning_trades += 1
                            self.total_profit += profit
                            if profit > self.best_trade:
                                self.best_trade = profit
                        else:
                            self.losing_trades += 1
                            self.total_loss += abs(profit)
                            if profit < self.worst_trade:
                                self.worst_trade = profit

                        self.logger.info(f"✅ Trade outcome updated: Ticket {ticket}, Profit: ${profit:.2f}")
                        break

        except Exception as e:
            self.logger.error(f"❌ Trade outcome update error: {str(e)}")

    def add_equity_point(self, equity: float) -> None:
        """Add equity data point for tracking."""
        try:
            with self.lock:
                self.equity_history.append({
                    "timestamp": datetime.now(),
                    "equity": equity
                })

                # Keep last 1000 points
                if len(self.equity_history) > 1000:
                    self.equity_history = self.equity_history[-1000:]

        except Exception as e:
            self.logger.error(f"❌ Equity tracking error: {str(e)}")

    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        try:
            with self.lock:
                # Basic metrics
                win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0
                profit_factor = abs(self.total_profit / self.total_loss) if self.total_loss != 0 else float('inf')
                average_win = self.total_profit / self.winning_trades if self.winning_trades > 0 else 0.0
                average_loss = self.total_loss / self.losing_trades if self.losing_trades > 0 else 0.0
                average_trade = (self.total_profit - self.total_loss) / self.total_trades if self.total_trades > 0 else 0.0

                # Risk metrics
                max_drawdown = self._calculate_max_drawdown()
                sharpe_ratio = self._calculate_sharpe_ratio()

                return {
                    "total_trades": self.total_trades,
                    "winning_trades": self.winning_trades,
                    "losing_trades": self.losing_trades,
                    "win_rate": win_rate,
                    "total_profit": self.total_profit - self.total_loss,
                    "gross_profit": self.total_profit,
                    "gross_loss": self.total_loss,
                    "profit_factor": profit_factor,
                    "average_win": average_win,
                    "average_loss": average_loss,
                    "average_trade": average_trade,
                    "best_trade": self.best_trade,
                    "worst_trade": self.worst_trade,
                    "max_drawdown": max_drawdown,
                    "sharpe_ratio": sharpe_ratio,
                    "session_duration": (datetime.now() - self.session_start_time).total_seconds() / 3600
                }

        except Exception as e:
            self.logger.error(f"❌ Performance calculation error: {str(e)}")
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
                "profit_factor": 1.0,
                "average_win": 0.0,
                "average_loss": 0.0,
                "average_trade": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "session_duration": 0.0
            }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics - alias for backward compatibility."""
        return self.calculate_performance_metrics()

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from equity history."""
        try:
            if len(self.equity_history) < 2:
                return 0.0

            equity_values = [point["equity"] for point in self.equity_history]
            peak = equity_values[0]
            max_dd = 0.0

            for equity in equity_values:
                if equity > peak:
                    peak = equity
                drawdown = (peak - equity) / peak if peak > 0 else 0.0
                if drawdown > max_dd:
                    max_dd = drawdown

            return max_dd * 100  # Return as percentage

        except Exception as e:
            self.logger.error(f"❌ Max drawdown calculation error: {str(e)}")
            return 0.0

    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from equity history."""
        try:
            if len(self.equity_history) < 2:
                return 0.0

            equity_values = [point["equity"] for point in self.equity_history]
            returns = []

            for i in range(1, len(equity_values)):
                if equity_values[i-1] > 0:
                    ret = (equity_values[i] - equity_values[i-1]) / equity_values[i-1]
                    returns.append(ret)

            if len(returns) < 2:
                return 0.0

            mean_return = np.mean(returns)
            std_return = np.std(returns)

            if std_return == 0:
                return 0.0

            # Annualized Sharpe ratio (assuming returns are calculated per update)
            return (mean_return * np.sqrt(252 * 24 * 60)) / std_return  # Daily minute-based data

        except Exception as e:
            self.logger.error(f"❌ Sharpe ratio calculation error: {str(e)}")
            return 0.0

    def generate_daily_report(self) -> Dict[str, Any]:
        """Generate daily performance report."""
        try:
            today = datetime.now().date()
            today_trades = [trade for trade in self.trades 
                          if trade["timestamp"].date() == today]

            daily_profit = sum(trade.get("profit", 0.0) for trade in today_trades 
                             if trade.get("status") == "CLOSED")

            daily_trades_count = len(today_trades)
            daily_winning = len([t for t in today_trades 
                               if t.get("profit", 0.0) > 0 and t.get("status") == "CLOSED"])

            return {
                "date": today,
                "trades_count": daily_trades_count,
                "profit": daily_profit,
                "winning_trades": daily_winning,
                "win_rate": (daily_winning / daily_trades_count * 100) if daily_trades_count > 0 else 0.0
            }

        except Exception as e:
            self.logger.error(f"❌ Daily report generation error: {str(e)}")
            return {"error": str(e)}

    def export_trades_to_csv(self, filename: Optional[str] = None) -> str:
        """Export trade history to CSV file."""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"trades_export_{timestamp}.csv"

            filepath = os.path.join(self.reports_dir, filename)

            if not self.trades:
                self.logger.warning("⚠️ No trades to export")
                return ""

            df = pd.DataFrame(self.trades)
            df.to_csv(filepath, index=False)

            self.logger.info(f"✅ Trades exported to {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"❌ CSV export error: {str(e)}")
            return ""

    def get_trade_history(self) -> List[Dict[str, Any]]:
        """Get complete trade history."""
        try:
            with self.lock:
                return self.trades.copy()
        except Exception as e:
            self.logger.error(f"❌ Trade history retrieval error: {str(e)}")
            return []

    def get_equity_curve(self) -> List[Dict[str, Any]]:
        """Get equity curve data."""
        try:
            with self.lock:
                return self.equity_history.copy()
        except Exception as e:
            self.logger.error(f"❌ Equity curve retrieval error: {str(e)}")
            return []

    def reset_session(self) -> None:
        """Reset session data."""
        try:
            with self.lock:
                self.trades.clear()
                self.equity_history.clear()
                self.session_start_time = datetime.now()
                self.total_profit = 0.0
                self.total_loss = 0.0
                self.winning_trades = 0
                self.losing_trades = 0
                self.total_trades = 0
                self.best_trade = 0.0
                self.worst_trade = 0.0

                self.logger.info("✅ Session data reset")

        except Exception as e:
            self.logger.error(f"❌ Session reset error: {str(e)}")