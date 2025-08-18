"""
Reporting and Performance Tracking Module.
Handles trade logging, performance metrics, and report generation.
"""

import json
import csv
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import os

from core.config import config
from utils.logging_setup import get_logger

class ReportingManager:
    """Enhanced reporting and analytics system."""

    def __init__(self, mt5_client=None, config_dict=None):
        self.logger = get_logger(__name__)
        self.mt5_client = mt5_client
        self.config = config_dict or {}

        # Trading session tracking
        self.session_start_time = datetime.now()
        # Fix: Safely handle None config_dict
        if config_dict and isinstance(config_dict, dict):
            self.session_start_balance = config_dict.get('initial_balance', 10000.0)
        else:
            self.session_start_balance = 10000.0

        # Reporting configuration
        self.reports_dir = config.get('reports_dir', 'reports')
        self.enable_daily_reports = config.get('enable_daily_reports', True)
        self.enable_trade_journal = config.get('enable_trade_journal', True)

        # Create reports directory
        os.makedirs(self.reports_dir, exist_ok=True)

        # Performance tracking
        self.trades_data = [] # Initialize trades_data
        self.equity_history = [self.session_start_balance] # Initialize equity_history

        self.trades_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0

        self.logger.info("✅ Reporting Manager initialized")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics for GUI display.

        Returns:
            Performance metrics dictionary
        """
        return self.calculate_performance_metrics()

    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.

        Returns:
            Performance metrics dictionary
        """
        try:
            if not self.trades_data:
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "total_profit": 0.0,
                    "total_loss": 0.0,
                    "net_profit": 0.0,
                    "profit_factor": 0.0,
                    "average_win": 0.0,
                    "average_loss": 0.0,
                    "largest_win": 0.0,
                    "largest_loss": 0.0,
                    "max_consecutive_wins": 0,
                    "max_consecutive_losses": 0,
                    "sharpe_ratio": 0.0,
                    "max_drawdown": 0.0,
                    "recovery_factor": 0.0,
                    "profit_per_trade": 0.0,
                    "session_duration_hours": 0.0,
                    "trades_per_hour": 0.0
                }

            # Calculate basic metrics
            total_trades = len(self.trades_data)
            profits = [trade.get('profit', 0) for trade in self.trades_data]

            winning_trades = len([p for p in profits if p > 0])
            losing_trades = len([p for p in profits if p < 0])

            total_profit = sum([p for p in profits if p > 0])
            total_loss = sum([p for p in profits if p < 0])
            net_profit = sum(profits)

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            profit_factor = abs(total_profit / total_loss) if total_loss != 0 else 0

            average_win = total_profit / winning_trades if winning_trades > 0 else 0
            average_loss = total_loss / losing_trades if losing_trades > 0 else 0

            largest_win = max(profits) if profits else 0
            largest_loss = min(profits) if profits else 0

            # Calculate consecutive wins/losses
            max_consecutive_wins, max_consecutive_losses = self._calculate_consecutive_streaks(profits)

            # Calculate advanced metrics
            sharpe_ratio = self._calculate_sharpe_ratio(profits)
            max_drawdown = self._calculate_max_drawdown()
            recovery_factor = abs(net_profit / max_drawdown) if max_drawdown != 0 else 0

            profit_per_trade = net_profit / total_trades if total_trades > 0 else 0

            # Session metrics
            session_duration = (datetime.now() - self.session_start_time).total_seconds() / 3600
            trades_per_hour = total_trades / session_duration if session_duration > 0 else 0

            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
                "total_profit": round(total_profit, 2),
                "total_loss": round(total_loss, 2),
                "net_profit": round(net_profit, 2),
                "profit_factor": round(profit_factor, 2),
                "average_win": round(average_win, 2),
                "average_loss": round(average_loss, 2),
                "largest_win": round(largest_win, 2),
                "largest_loss": round(largest_loss, 2),
                "max_consecutive_wins": max_consecutive_wins,
                "max_consecutive_losses": max_consecutive_losses,
                "sharpe_ratio": round(sharpe_ratio, 3),
                "max_drawdown": round(max_drawdown, 2),
                "recovery_factor": round(recovery_factor, 2),
                "profit_per_trade": round(profit_per_trade, 2),
                "session_duration_hours": round(session_duration, 2),
                "trades_per_hour": round(trades_per_hour, 2),
                "session_start_balance": self.session_start_balance,
                "current_equity": self.equity_history[-1] if self.equity_history else self.session_start_balance
            }

        except Exception as e:
            self.logger.error(f"❌ Performance calculation error: {str(e)}")
            return {"error": str(e)}

    def _calculate_consecutive_streaks(self, profits: List[float]) -> tuple:
        """Helper to calculate max consecutive wins and losses."""
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        for p in profits:
            if p > 0:
                current_wins += 1
                max_losses = max(max_losses, current_losses)
                current_losses = 0
            elif p < 0:
                current_losses += 1
                max_wins = max(max_wins, current_wins)
                current_wins = 0
            else: # Draw
                max_wins = max(max_wins, current_wins)
                max_losses = max(max_losses, current_losses)
                current_wins = 0
                current_losses = 0
        max_wins = max(max_wins, current_wins)
        max_losses = max(max_losses, current_losses)
        return max_wins, max_losses

    def _calculate_sharpe_ratio(self, profits: List[float]) -> float:
        """Helper to calculate Sharpe ratio."""
        return self.calculate_sharpe_ratio(profits) # Re-using existing method

    def _calculate_max_drawdown(self) -> float:
        """Helper to calculate maximum drawdown."""
        if not self.equity_history:
            return 0.0

        max_drawdown = 0.0
        peak = self.equity_history[0]

        for equity in self.equity_history[1:]:
            if equity > peak:
                peak = equity
            else:
                drawdown = peak - equity
                max_drawdown = max(max_drawdown, drawdown)
        return max_drawdown

    def initialize_session(self, account_info: Dict[str, Any]) -> None:
        """Initialize reporting for a new trading session."""
        try:
            self.session_start_time = datetime.now()
            starting_balance = account_info.get("balance", 0.0)

            self.session_start_balance = starting_balance
            self.trades_data = [] # Reset trades data
            self.equity_history = [self.session_start_balance] # Reset equity history

            self.trades_count = 0
            self.winning_trades = 0
            self.losing_trades = 0
            self.total_profit = 0.0
            self.total_loss = 0.0

            self.logger.info(f"📊 Reporting session initialized with balance: ${starting_balance:,.2f}")

        except Exception as e:
            self.logger.error(f"❌ Reporting initialization error: {str(e)}")

    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """Log a completed trade."""
        try:
            self.trades_data.append(trade_data) # Append trade data

            self.trades_count += 1
            profit = trade_data.get("profit", 0.0)

            if profit > 0:
                self.winning_trades += 1
                self.total_profit += profit
            else:
                self.losing_trades += 1
                self.total_loss += profit # Store loss as negative value

            self.logger.info(f"📝 Trade logged: Symbol={trade_data.get('symbol')}, Type={trade_data.get('type')}, Profit=${profit:.2f}")

        except Exception as e:
            self.logger.error(f"❌ Trade logging error: {str(e)}")

    def update_trade_outcome(self, order_id: int, outcome_data: Dict[str, Any]) -> None:
        """Update trade with exit information."""
        # This method might need adjustment based on how trades are managed and tracked
        # For now, it's a placeholder if not directly used by the new logic.
        self.logger.warning(f"⚠️ update_trade_outcome called for Order ID {order_id}, but may not be fully integrated with current reporting logic.")
        pass


    def add_equity_point(self, current_equity: float) -> None:
        """Add equity data point for performance tracking."""
        # This method is not directly used in the current simplified reporting,
        # but can be re-integrated if detailed equity curve tracking is needed.
        self.equity_history.append(current_equity)
        self.logger.debug(f"Debug: Equity point added: {current_equity}")
        pass

    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        try:
            if not self.trades_data:
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "total_profit": 0.0,
                    "total_loss": 0.0,
                    "net_profit": 0.0,
                    "profit_factor": 0.0,
                    "average_win": 0.0,
                    "average_loss": 0.0,
                    "largest_win": 0.0,
                    "largest_loss": 0.0,
                    "max_consecutive_wins": 0,
                    "max_consecutive_losses": 0,
                    "sharpe_ratio": 0.0,
                    "max_drawdown": 0.0,
                    "recovery_factor": 0.0,
                    "profit_per_trade": 0.0,
                    "session_duration_hours": 0.0,
                    "trades_per_hour": 0.0,
                    "session_start_balance": self.session_start_balance,
                    "current_equity": self.equity_history[-1] if self.equity_history else self.session_start_balance
                }

            # Calculate basic metrics
            total_trades = len(self.trades_data)
            profits = [trade.get('profit', 0) for trade in self.trades_data]

            winning_trades = len([p for p in profits if p > 0])
            losing_trades = len([p for p in profits if p < 0])

            total_profit = sum([p for p in profits if p > 0])
            total_loss = sum([p for p in profits if p < 0])
            net_profit = sum(profits)

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            profit_factor = abs(total_profit / total_loss) if total_loss != 0 else 0

            average_win = total_profit / winning_trades if winning_trades > 0 else 0
            average_loss = total_loss / losing_trades if losing_trades > 0 else 0

            largest_win = max(profits) if profits else 0
            largest_loss = min(profits) if profits else 0

            # Calculate consecutive wins/losses
            max_consecutive_wins, max_consecutive_losses = self._calculate_consecutive_streaks(profits)

            # Calculate advanced metrics
            sharpe_ratio = self._calculate_sharpe_ratio(profits)
            max_drawdown = self._calculate_max_drawdown()
            recovery_factor = abs(net_profit / max_drawdown) if max_drawdown != 0 else 0

            profit_per_trade = net_profit / total_trades if total_trades > 0 else 0

            # Session metrics
            session_duration = (datetime.now() - self.session_start_time).total_seconds() / 3600
            trades_per_hour = total_trades / session_duration if session_duration > 0 else 0

            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
                "total_profit": round(total_profit, 2),
                "total_loss": round(total_loss, 2),
                "net_profit": round(net_profit, 2),
                "profit_factor": round(profit_factor, 2),
                "average_win": round(average_win, 2),
                "average_loss": round(average_loss, 2),
                "largest_win": round(largest_win, 2),
                "largest_loss": round(largest_loss, 2),
                "max_consecutive_wins": max_consecutive_wins,
                "max_consecutive_losses": max_consecutive_losses,
                "sharpe_ratio": round(sharpe_ratio, 3),
                "max_drawdown": round(max_drawdown, 2),
                "recovery_factor": round(recovery_factor, 2),
                "profit_per_trade": round(profit_per_trade, 2),
                "session_duration_hours": round(session_duration, 2),
                "trades_per_hour": round(trades_per_hour, 2),
                "session_start_balance": self.session_start_balance,
                "current_equity": self.equity_history[-1] if self.equity_history else self.session_start_balance
            }

        except Exception as e:
            self.logger.error(f"❌ Performance calculation error: {str(e)}")
            return {"error": str(e)}

    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio for performance evaluation."""
        try:
            if not returns or len(returns) < 2:
                return 0.0

            import numpy as np
            returns_array = np.array(returns)
            daily_risk_free_rate = risk_free_rate / 252 # Assuming 252 trading days in a year
            excess_returns = returns_array - daily_risk_free_rate

            std_dev = np.std(excess_returns)
            if std_dev == 0:
                return 0.0

            return np.mean(excess_returns) / std_dev * np.sqrt(252)

        except Exception as e:
            self.logger.error(f"Sharpe ratio calculation error: {e}")
            return 0.0

    def calculate_max_drawdown_duration(self) -> int:
        """Calculate maximum drawdown duration in days."""
        # This method relies on equity curve data, which is not actively managed
        # in this revised ReportingManager. It would require re-integration of equity tracking.
        self.logger.warning("⚠️ calculate_max_drawdown_duration called, but equity curve tracking is not active.")
        return 0

    def calculate_profit_factor(self) -> float:
        """Calculate profit factor (gross profit / gross loss)."""
        try:
            # Re-using the logic from get_performance_metrics
            metrics = self.get_performance_metrics()
            return metrics.get("profit_factor", 0.0)

        except Exception as e:
            self.logger.error(f"Profit factor calculation error: {e}")
            return 0.0

    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report with advanced metrics."""
        try:
            metrics = self.get_performance_metrics()
            current_time = datetime.now()

            report = f"""
📊 TRADING REPORT - {current_time.strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

💰 PERFORMANCE SUMMARY
   Session Duration: {metrics.get('session_duration', 'N/A')}
   Total Trades:     {metrics.get('trades_count', 0)}
   Winning Trades:   {metrics.get('winning_trades', 0)}
   Losing Trades:    {metrics.get('losing_trades', 0)}
   Win Rate:         {metrics.get('win_rate', 0):.1f}%

   Total P/L:        ${metrics.get('total_pnl', 0):.2f}
   Total Profit:     ${metrics.get('total_profit', 0):.2f}
   Total Loss:       ${metrics.get('total_loss', 0):.2f}
   Profit Factor:    {metrics.get('profit_factor', 0):.2f}

📈 ACCOUNT STATUS
   Start Balance:    ${metrics.get('session_start_balance', 0):.2f}
   Current Balance:  ${metrics.get('balance', 0):.2f}
   Current Equity:   ${metrics.get('equity', 0):.2f}
   Start Time:       {metrics.get('session_start_time', 'N/A')}

"""
            # Note: The original report included more detailed trade-specific metrics and recent trades.
            # This version focuses on session-level summary metrics as per the updated `get_performance_metrics`.
            # If detailed trade logs or charting data are needed, the ReportingManager would need to store and process them.

            return report

        except Exception as e:
            self.logger.error(f"❌ Report generation error: {str(e)}")
            return f"Report generation failed: {str(e)}"

    def save_session_data(self) -> bool:
        """Save session data to file."""
        # This method would need to be adapted to save the relevant metrics from get_performance_metrics
        # and potentially trade logs if they are being stored.
        self.logger.warning("⚠️ save_session_data called, but implementation for saving current metrics is minimal.")
        try:
            metrics = self.get_performance_metrics()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            metrics_file = os.path.join(self.reports_dir, f"session_metrics_{timestamp}.json")
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)
            self.logger.info(f"💾 Session metrics saved to {metrics_file}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Session save error: {str(e)}")
            return False


    def export_report(self, format: str = "csv") -> str:
        """Export trading report in specified format."""
        # This method would need significant adaptation to export the session-level metrics
        # and potentially historical trade data if that is being tracked.
        self.logger.warning(f"⚠️ export_report called with format '{format}', but implementation is not fully adapted to new metrics structure.")
        try:
            metrics = self.get_performance_metrics()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            if format.lower() == "csv":
                filename = f"trading_report_{timestamp}.csv"
                filepath = os.path.join(self.reports_dir, filename)
                with open(filepath, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["Metric", "Value"])
                    for key, value in metrics.items():
                        writer.writerow([key.replace('_', ' ').title(), value])
                self.logger.info(f"📄 Report exported to {filepath}")
                return filepath

            elif format.lower() == "json":
                filename = f"session_data_{timestamp}.json"
                filepath = os.path.join(self.reports_dir, filename)
                export_data = {
                    "session_info": {
                        "start_time": self.session_start_time.isoformat(),
                        "export_time": datetime.now().isoformat(),
                    },
                    "performance_metrics": metrics
                }
                with open(filepath, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                self.logger.info(f"📄 Session data exported to {filepath}")
                return filepath

            else:
                raise ValueError(f"Unsupported export format: {format}")

        except Exception as e:
            self.logger.error(f"❌ Export error: {str(e)}")
            return f"Export failed: {str(e)}"


    def get_equity_data(self) -> List[Dict]:
        """Get equity curve data for chart display."""
        # This method is not supported in the current implementation as equity curve is not stored.
        self.logger.warning("⚠️ get_equity_data called, but equity curve data is not tracked.")
        return []