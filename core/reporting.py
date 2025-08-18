"""
Reporting Module.
Handles account monitoring, performance tracking, and report generation.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Any
from datetime import datetime, timedelta
import json

from utils.logging_setup import get_logger

class ReportingManager:
    """Comprehensive reporting and performance tracking."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Performance tracking
        self.session_data = {
            "start_time": datetime.now(),
            "start_balance": 0.0,
            "trades": [],
            "equity_history": [],
            "daily_stats": {},
            "monthly_stats": {}
        }
        
        self.performance_metrics = {}
        self.equity_curve = []
        
        self.logger.info("📊 Reporting Manager initialized")
    
    def initialize_session(self, account_info: Dict[str, Any]) -> None:
        """
        Initialize reporting session with account data.
        
        Args:
            account_info: Current account information
        """
        try:
            self.session_data.update({
                "start_time": datetime.now(),
                "start_balance": account_info.get("balance", 0.0),
                "start_equity": account_info.get("equity", 0.0),
                "account_login": account_info.get("login", "Unknown"),
                "account_server": account_info.get("server", "Unknown"),
                "account_currency": account_info.get("currency", "USD")
            })
            
            # Initialize equity tracking
            self.add_equity_point(account_info.get("equity", 0.0))
            
            self.logger.info(f"📊 Reporting session initialized:")
            self.logger.info(f"   Account: {self.session_data['account_login']}")
            self.logger.info(f"   Balance: ${self.session_data['start_balance']:,.2f}")
            self.logger.info(f"   Equity: ${self.session_data['start_equity']:,.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ Session initialization error: {str(e)}")
    
    def add_equity_point(self, equity: float) -> None:
        """
        Add equity data point for tracking.
        
        Args:
            equity: Current equity value
        """
        try:
            equity_point = {
                "timestamp": datetime.now(),
                "equity": equity,
                "balance": equity  # Assuming equity equals balance for simplicity
            }
            
            self.equity_curve.append(equity_point)
            self.session_data["equity_history"].append(equity_point)
            
            # Keep only recent equity points (last 1000 points)
            if len(self.equity_curve) > 1000:
                self.equity_curve = self.equity_curve[-1000:]
            
        except Exception as e:
            self.logger.error(f"❌ Equity tracking error: {str(e)}")
    
    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """
        Log executed trade for performance tracking.
        
        Args:
            trade_data: Trade execution data
        """
        try:
            trade_record = {
                "timestamp": datetime.now(),
                "symbol": trade_data.get("symbol", "Unknown"),
                "type": trade_data.get("type", "Unknown"),
                "volume": trade_data.get("volume", 0.0),
                "entry_price": trade_data.get("price", 0.0),
                "stop_loss": trade_data.get("sl", 0.0),
                "take_profit": trade_data.get("tp", 0.0),
                "order_id": trade_data.get("order", 0),
                "deal_id": trade_data.get("deal", 0),
                "comment": trade_data.get("comment", ""),
                "status": "EXECUTED"
            }
            
            self.session_data["trades"].append(trade_record)
            
            self.logger.info(f"📝 Trade logged: {trade_record['type']} {trade_record['volume']} {trade_record['symbol']} @ {trade_record['entry_price']}")
            
        except Exception as e:
            self.logger.error(f"❌ Trade logging error: {str(e)}")
    
    def update_trade_outcome(self, order_id: int, outcome_data: Dict[str, Any]) -> None:
        """
        Update trade with outcome (profit/loss).
        
        Args:
            order_id: Order ID to update
            outcome_data: Trade outcome data
        """
        try:
            # Find trade by order ID
            for trade in self.session_data["trades"]:
                if trade.get("order_id") == order_id:
                    trade.update({
                        "exit_time": datetime.now(),
                        "exit_price": outcome_data.get("exit_price", 0.0),
                        "profit": outcome_data.get("profit", 0.0),
                        "commission": outcome_data.get("commission", 0.0),
                        "swap": outcome_data.get("swap", 0.0),
                        "status": "CLOSED"
                    })
                    
                    self.logger.info(f"📝 Trade updated: Order {order_id} - Profit: ${trade['profit']:.2f}")
                    break
            
        except Exception as e:
            self.logger.error(f"❌ Trade outcome update error: {str(e)}")
    
    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        try:
            closed_trades = [t for t in self.session_data["trades"] if t.get("status") == "CLOSED"]
            
            if not closed_trades:
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "total_profit": 0.0,
                    "avg_profit": 0.0,
                    "profit_factor": 0.0,
                    "max_drawdown": 0.0,
                    "sharpe_ratio": 0.0
                }
            
            # Basic metrics
            total_trades = len(closed_trades)
            profits = [t.get("profit", 0.0) for t in closed_trades]
            winning_trades = len([p for p in profits if p > 0])
            losing_trades = len([p for p in profits if p < 0])
            
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
            total_profit = sum(profits)
            avg_profit = total_profit / total_trades if total_trades > 0 else 0.0
            
            # Profit factor
            gross_profit = sum([p for p in profits if p > 0])
            gross_loss = abs(sum([p for p in profits if p < 0]))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Drawdown calculation
            max_drawdown = self._calculate_max_drawdown()
            
            # Sharpe ratio (simplified)
            if len(profits) > 1:
                returns_std = np.std(profits)
                sharpe_ratio = avg_profit / returns_std if returns_std > 0 else 0.0
            else:
                sharpe_ratio = 0.0
            
            # Additional metrics
            largest_win = max(profits) if profits else 0.0
            largest_loss = min(profits) if profits else 0.0
            
            # Consecutive wins/losses
            consecutive_wins, consecutive_losses = self._calculate_consecutive_results(profits)
            
            metrics = {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "total_profit": total_profit,
                "avg_profit": avg_profit,
                "gross_profit": gross_profit,
                "gross_loss": gross_loss,
                "profit_factor": profit_factor,
                "largest_win": largest_win,
                "largest_loss": largest_loss,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe_ratio,
                "max_consecutive_wins": consecutive_wins,
                "max_consecutive_losses": consecutive_losses,
                "avg_trade_duration": self._calculate_avg_duration(),
                "recovery_factor": total_profit / abs(max_drawdown) if max_drawdown != 0 else float('inf')
            }
            
            self.performance_metrics = metrics
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ Performance calculation error: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from equity curve."""
        try:
            if len(self.equity_curve) < 2:
                return 0.0
                
            equity_values = [point["equity"] for point in self.equity_curve]
            
            peak = equity_values[0]
            max_dd = 0.0
            
            for equity in equity_values:
                if equity > peak:
                    peak = equity
                
                drawdown = (peak - equity) / peak if peak > 0 else 0.0
                max_dd = max(max_dd, drawdown)
            
            return max_dd * 100  # Return as percentage
            
        except Exception as e:
            self.logger.error(f"❌ Drawdown calculation error: {str(e)}")
            return 0.0
    
    def _calculate_consecutive_results(self, profits: List[float]) -> Tuple[int, int]:
        """Calculate maximum consecutive wins and losses."""
        try:
            if not profits:
                return 0, 0
                
            max_wins = 0
            max_losses = 0
            current_wins = 0
            current_losses = 0
            
            for profit in profits:
                if profit > 0:
                    current_wins += 1
                    current_losses = 0
                    max_wins = max(max_wins, current_wins)
                elif profit < 0:
                    current_losses += 1
                    current_wins = 0
                    max_losses = max(max_losses, current_losses)
                else:
                    current_wins = 0
                    current_losses = 0
            
            return max_wins, max_losses
            
        except Exception as e:
            self.logger.error(f"❌ Consecutive results calculation error: {str(e)}")
            return 0, 0
    
    def _calculate_avg_duration(self) -> float:
        """Calculate average trade duration in minutes."""
        try:
            closed_trades = [t for t in self.session_data["trades"] 
                           if t.get("status") == "CLOSED" and "exit_time" in t]
            
            if not closed_trades:
                return 0.0
                
            durations = []
            for trade in closed_trades:
                entry_time = trade["timestamp"]
                exit_time = trade["exit_time"]
                duration = (exit_time - entry_time).total_seconds() / 60  # Convert to minutes
                durations.append(duration)
            
            return sum(durations) / len(durations)
            
        except Exception as e:
            self.logger.error(f"❌ Duration calculation error: {str(e)}")
            return 0.0
    
    def get_account_summary(self, account_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get comprehensive account summary.
        
        Args:
            account_info: Current account information
            
        Returns:
            Account summary dictionary
        """
        try:
            current_equity = account_info.get("equity", 0.0)
            start_equity = self.session_data.get("start_equity", current_equity)
            
            # Session performance
            session_profit = current_equity - start_equity
            session_profit_pct = (session_profit / start_equity * 100) if start_equity > 0 else 0.0
            
            # Calculate session duration
            session_duration = datetime.now() - self.session_data["start_time"]
            
            summary = {
                "account_info": {
                    "login": account_info.get("login", "Unknown"),
                    "server": account_info.get("server", "Unknown"),
                    "currency": account_info.get("currency", "USD"),
                    "balance": account_info.get("balance", 0.0),
                    "equity": current_equity,
                    "margin": account_info.get("margin", 0.0),
                    "free_margin": account_info.get("free_margin", 0.0),
                    "margin_level": account_info.get("margin_level", 0.0)
                },
                "session_info": {
                    "start_time": self.session_data["start_time"],
                    "duration_hours": session_duration.total_seconds() / 3600,
                    "start_equity": start_equity,
                    "current_equity": current_equity,
                    "session_profit": session_profit,
                    "session_profit_pct": session_profit_pct,
                    "total_trades": len(self.session_data["trades"])
                },
                "performance": self.calculate_performance_metrics(),
                "risk_info": {
                    "max_drawdown": self._calculate_max_drawdown(),
                    "current_positions": len([t for t in self.session_data["trades"] if t.get("status") == "EXECUTED"])
                }
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ Account summary error: {str(e)}")
            return {"error": str(e)}
    
    def get_equity_data_for_chart(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get equity data for chart display.
        
        Args:
            hours: Number of hours of data to return
            
        Returns:
            List of equity data points
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            chart_data = [
                point for point in self.equity_curve 
                if point["timestamp"] >= cutoff_time
            ]
            
            # If no recent data, return at least the latest point
            if not chart_data and self.equity_curve:
                chart_data = [self.equity_curve[-1]]
            
            return chart_data
            
        except Exception as e:
            self.logger.error(f"❌ Chart data error: {str(e)}")
            return []
    
    def export_report(self, filename: Optional[str] = None) -> str:
        """
        Export comprehensive trading report to file.
        
        Args:
            filename: Optional filename for export
            
        Returns:
            Export filename or error message
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"trading_report_{timestamp}.json"
            
            # Prepare comprehensive report
            report = {
                "export_time": datetime.now().isoformat(),
                "session_data": self.session_data,
                "performance_metrics": self.performance_metrics,
                "equity_curve": self.equity_curve
            }
            
            # Convert datetime objects to strings for JSON serialization
            def datetime_handler(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            # Write to file
            with open(filename, 'w') as f:
                json.dump(report, f, default=datetime_handler, indent=2)
            
            self.logger.info(f"📁 Report exported to: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"❌ Report export error: {str(e)}")
            return f"Export failed: {str(e)}"
    
    def get_daily_summary(self) -> Dict[str, Any]:
        """
        Get daily trading summary.
        
        Returns:
            Daily summary statistics
        """
        try:
            today = datetime.now().date()
            today_trades = [
                t for t in self.session_data["trades"]
                if t["timestamp"].date() == today
            ]
            
            closed_today = [t for t in today_trades if t.get("status") == "CLOSED"]
            
            daily_profit = sum([t.get("profit", 0.0) for t in closed_today])
            
            summary = {
                "date": today.isoformat(),
                "total_trades": len(today_trades),
                "closed_trades": len(closed_today),
                "open_trades": len(today_trades) - len(closed_today),
                "daily_profit": daily_profit,
                "winning_trades": len([t for t in closed_today if t.get("profit", 0.0) > 0]),
                "losing_trades": len([t for t in closed_today if t.get("profit", 0.0) < 0]),
                "win_rate": (len([t for t in closed_today if t.get("profit", 0.0) > 0]) / len(closed_today) * 100) if closed_today else 0.0
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ Daily summary error: {str(e)}")
            return {"error": str(e)}
