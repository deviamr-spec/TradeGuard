
"""
Reporting and Performance Analytics Module.
Handles trade logging, performance calculations, and report generation.
"""

import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import os

from core.config import config
from utils.logging_setup import get_logger

class ReportingManager:
    """Comprehensive reporting and performance analytics system."""

    def __init__(self, mt5_client, initial_config: Dict[str, Any]):
        self.logger = get_logger(__name__)
        self.mt5_client = mt5_client
        
        # Performance tracking
        self.session_start_balance = 10000.0
        self.session_start_time = datetime.now()
        self.trades_log = []
        self.equity_curve = []
        self.daily_returns = []
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.max_consecutive_wins = 0
        self.max_consecutive_losses = 0
        self.current_streak = 0
        self.streak_type = None  # 'win' or 'loss'
        
        # Advanced metrics
        self.sharpe_ratio = 0.0
        self.sortino_ratio = 0.0
        self.max_drawdown = 0.0
        self.profit_factor = 0.0
        self.recovery_factor = 0.0
        
        # Thread safety
        self.reporting_lock = threading.Lock()
        
        # Initialize reports directory
        self.reports_dir = "reports"
        os.makedirs(self.reports_dir, exist_ok=True)
        
        self.logger.info("✅ Reporting Manager initialized")

    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """
        Log a completed trade.
        
        Args:
            trade_data: Trade information dictionary
        """
        try:
            with self.reporting_lock:
                # Add timestamp if not present
                if "timestamp" not in trade_data:
                    trade_data["timestamp"] = datetime.now()
                
                # Add to trades log
                self.trades_log.append(trade_data.copy())
                self.total_trades += 1
                
                # Calculate profit/loss if available
                profit = trade_data.get("profit", 0.0)
                if profit > 0:
                    self.winning_trades += 1
                    self.total_profit += profit
                    self._update_streak("win")
                elif profit < 0:
                    self.losing_trades += 1
                    self.total_loss += abs(profit)
                    self._update_streak("loss")
                
                # Update performance metrics
                self._calculate_performance_metrics()
                
                self.logger.info(f"📊 Trade logged: {trade_data.get('symbol', 'Unknown')} "
                               f"{trade_data.get('type', 'Unknown')} "
                               f"P/L: {profit:.2f}")
                
        except Exception as e:
            self.logger.error(f"❌ Trade logging error: {str(e)}")

    def update_trade_outcome(self, trade_id: int, outcome_data: Dict[str, Any]) -> None:
        """
        Update trade outcome for existing trade.
        
        Args:
            trade_id: Trade identifier
            outcome_data: Trade outcome information
        """
        try:
            with self.reporting_lock:
                # Find and update trade
                for trade in self.trades_log:
                    if trade.get("ticket") == trade_id or trade.get("order") == trade_id:
                        trade.update(outcome_data)
                        trade["updated_at"] = datetime.now()
                        
                        # Recalculate metrics
                        self._calculate_performance_metrics()
                        break
                        
        except Exception as e:
            self.logger.error(f"❌ Trade outcome update error: {str(e)}")

    def add_equity_point(self, equity: float) -> None:
        """
        Add equity point to equity curve.
        
        Args:
            equity: Current equity value
        """
        try:
            with self.reporting_lock:
                equity_point = {
                    "timestamp": datetime.now(),
                    "equity": float(equity),
                    "balance": float(equity)  # Assuming equity = balance for simplicity
                }
                
                self.equity_curve.append(equity_point)
                
                # Keep only last 1000 points to prevent memory issues
                if len(self.equity_curve) > 1000:
                    self.equity_curve = self.equity_curve[-1000:]
                
                # Calculate daily returns
                if len(self.equity_curve) >= 2:
                    prev_equity = self.equity_curve[-2]["equity"]
                    if prev_equity > 0:
                        daily_return = (equity - prev_equity) / prev_equity
                        self.daily_returns.append(daily_return)
                        
                        # Keep only last 100 returns
                        if len(self.daily_returns) > 100:
                            self.daily_returns = self.daily_returns[-100:]
                
        except Exception as e:
            self.logger.error(f"❌ Equity point error: {str(e)}")

    def _update_streak(self, result_type: str) -> None:
        """Update win/loss streak counters."""
        try:
            if self.streak_type == result_type:
                self.current_streak += 1
            else:
                # End of previous streak, record if it's a record
                if self.streak_type == "win":
                    self.max_consecutive_wins = max(self.max_consecutive_wins, self.current_streak)
                elif self.streak_type == "loss":
                    self.max_consecutive_losses = max(self.max_consecutive_losses, self.current_streak)
                
                # Start new streak
                self.streak_type = result_type
                self.current_streak = 1
                
        except Exception as e:
            self.logger.error(f"❌ Streak update error: {str(e)}")

    def _calculate_performance_metrics(self) -> None:
        """Calculate advanced performance metrics."""
        try:
            # Profit factor
            if self.total_loss > 0:
                self.profit_factor = self.total_profit / self.total_loss
            else:
                self.profit_factor = float('inf') if self.total_profit > 0 else 0.0
            
            # Win rate
            win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0
            
            # Average win/loss
            avg_win = self.total_profit / self.winning_trades if self.winning_trades > 0 else 0.0
            avg_loss = self.total_loss / self.losing_trades if self.losing_trades > 0 else 0.0
            
            # Sharpe ratio (simplified)
            if len(self.daily_returns) > 1:
                import statistics
                try:
                    avg_return = statistics.mean(self.daily_returns)
                    std_return = statistics.stdev(self.daily_returns)
                    if std_return > 0:
                        self.sharpe_ratio = avg_return / std_return
                    else:
                        self.sharpe_ratio = 0.0
                except:
                    self.sharpe_ratio = 0.0
            
            # Max drawdown from equity curve
            if len(self.equity_curve) > 1:
                peak = self.equity_curve[0]["equity"]
                max_dd = 0.0
                
                for point in self.equity_curve:
                    equity = point["equity"]
                    if equity > peak:
                        peak = equity
                    else:
                        drawdown = (peak - equity) / peak if peak > 0 else 0.0
                        max_dd = max(max_dd, drawdown)
                
                self.max_drawdown = max_dd
            
            # Recovery factor
            if self.max_drawdown > 0:
                net_profit = self.total_profit - self.total_loss
                self.recovery_factor = net_profit / (self.max_drawdown * self.session_start_balance)
            else:
                self.recovery_factor = float('inf') if (self.total_profit - self.total_loss) > 0 else 0.0
                
        except Exception as e:
            self.logger.error(f"❌ Performance metrics calculation error: {str(e)}")

    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate and return comprehensive performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        try:
            # Ensure metrics are up to date
            self._calculate_performance_metrics()
            
            # Calculate additional metrics
            net_profit = self.total_profit - self.total_loss
            win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0
            avg_win = self.total_profit / self.winning_trades if self.winning_trades > 0 else 0.0
            avg_loss = self.total_loss / self.losing_trades if self.losing_trades > 0 else 0.0
            
            # Session duration
            session_duration = datetime.now() - self.session_start_time
            
            # Current equity
            current_equity = self.equity_curve[-1]["equity"] if self.equity_curve else self.session_start_balance
            
            return {
                "trading_stats": {
                    "total_trades": self.total_trades,
                    "winning_trades": self.winning_trades,
                    "losing_trades": self.losing_trades,
                    "win_rate": win_rate,
                    "profit_factor": self.profit_factor
                },
                "profit_loss": {
                    "total_profit": self.total_profit,
                    "total_loss": self.total_loss,
                    "net_profit": net_profit,
                    "avg_win": avg_win,
                    "avg_loss": avg_loss
                },
                "risk_metrics": {
                    "max_drawdown": self.max_drawdown,
                    "sharpe_ratio": self.sharpe_ratio,
                    "sortino_ratio": self.sortino_ratio,
                    "recovery_factor": self.recovery_factor
                },
                "streaks": {
                    "max_consecutive_wins": self.max_consecutive_wins,
                    "max_consecutive_losses": self.max_consecutive_losses,
                    "current_streak": self.current_streak,
                    "current_streak_type": self.streak_type
                },
                "session_info": {
                    "start_time": self.session_start_time,
                    "duration": str(session_duration).split('.')[0],
                    "start_balance": self.session_start_balance,
                    "current_equity": current_equity,
                    "total_return": ((current_equity - self.session_start_balance) / self.session_start_balance * 100) if self.session_start_balance > 0 else 0.0
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Performance metrics error: {str(e)}")
            return {
                "error": str(e),
                "trading_stats": {"total_trades": 0, "win_rate": 0.0},
                "profit_loss": {"net_profit": 0.0},
                "risk_metrics": {"max_drawdown": 0.0, "sharpe_ratio": 0.0}
            }

    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> Optional[float]:
        """
        Calculate Sharpe ratio from returns.
        
        Args:
            returns: List of returns
            risk_free_rate: Risk-free rate (default: 0.0)
            
        Returns:
            Sharpe ratio or None if calculation fails
        """
        try:
            if len(returns) < 2:
                return None
                
            import statistics
            avg_return = statistics.mean(returns)
            std_return = statistics.stdev(returns)
            
            if std_return == 0:
                return None
                
            return (avg_return - risk_free_rate) / std_return
            
        except Exception as e:
            self.logger.error(f"❌ Sharpe ratio calculation error: {str(e)}")
            return None

    def calculate_profit_factor(self) -> float:
        """
        Calculate profit factor.
        
        Returns:
            Profit factor value
        """
        try:
            if self.total_loss == 0:
                return float('inf') if self.total_profit > 0 else 0.0
            return self.total_profit / self.total_loss
        except Exception as e:
            self.logger.error(f"❌ Profit factor calculation error: {str(e)}")
            return 0.0

    def generate_daily_report(self) -> Dict[str, Any]:
        """
        Generate daily trading report.
        
        Returns:
            Daily report dictionary
        """
        try:
            today = datetime.now().date()
            
            # Filter today's trades
            today_trades = [
                trade for trade in self.trades_log
                if trade.get("timestamp", datetime.now()).date() == today
            ]
            
            # Calculate daily metrics
            daily_profit = sum(trade.get("profit", 0) for trade in today_trades)
            daily_trades_count = len(today_trades)
            daily_wins = sum(1 for trade in today_trades if trade.get("profit", 0) > 0)
            daily_losses = sum(1 for trade in today_trades if trade.get("profit", 0) < 0)
            
            report = {
                "date": today.isoformat(),
                "summary": {
                    "total_trades": daily_trades_count,
                    "winning_trades": daily_wins,
                    "losing_trades": daily_losses,
                    "win_rate": (daily_wins / daily_trades_count * 100) if daily_trades_count > 0 else 0.0,
                    "total_profit": daily_profit
                },
                "trades": today_trades,
                "generated_at": datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Daily report generation error: {str(e)}")
            return {"error": str(e)}

    def export_trades_csv(self, filename: Optional[str] = None) -> str:
        """
        Export trades to CSV file.
        
        Args:
            filename: Optional filename (will generate if not provided)
            
        Returns:
            Path to exported file
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"trades_export_{timestamp}.csv"
            
            filepath = os.path.join(self.reports_dir, filename)
            
            # Create CSV content
            csv_lines = ["Timestamp,Symbol,Type,Volume,Entry_Price,Exit_Price,Profit,Comment"]
            
            for trade in self.trades_log:
                line = f"{trade.get('timestamp', '')},{trade.get('symbol', '')}," \
                      f"{trade.get('type', '')},{trade.get('volume', '')}," \
                      f"{trade.get('price', '')},{trade.get('exit_price', '')}," \
                      f"{trade.get('profit', '')},{trade.get('comment', '')}"
                csv_lines.append(line)
            
            with open(filepath, 'w') as f:
                f.write('\n'.join(csv_lines))
            
            self.logger.info(f"✅ Trades exported to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"❌ CSV export error: {str(e)}")
            return ""

    def get_equity_curve_data(self) -> List[Dict[str, Any]]:
        """
        Get equity curve data for plotting.
        
        Returns:
            List of equity curve points
        """
        try:
            return self.equity_curve.copy()
        except Exception as e:
            self.logger.error(f"❌ Equity curve data error: {str(e)}")
            return []

    def reset_session(self) -> None:
        """Reset session statistics for new trading session."""
        try:
            with self.reporting_lock:
                self.session_start_time = datetime.now()
                
                # Get current balance for new session
                if self.mt5_client:
                    account_info = self.mt5_client.get_account_info()
                    if account_info:
                        self.session_start_balance = account_info.get("balance", 10000.0)
                
                # Clear session data
                self.trades_log.clear()
                self.equity_curve.clear()
                self.daily_returns.clear()
                
                # Reset counters
                self.total_trades = 0
                self.winning_trades = 0
                self.losing_trades = 0
                self.total_profit = 0.0
                self.total_loss = 0.0
                self.current_streak = 0
                self.streak_type = None
                
                self.logger.info("🔄 Reporting session reset")
                
        except Exception as e:
            self.logger.error(f"❌ Session reset error: {str(e)}")
