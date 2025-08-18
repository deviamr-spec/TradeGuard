
"""
Reporting and Performance Tracking Module.
Handles trade logging, performance metrics, and report generation.
"""

import json
import csv
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import os

from core.config import config
from utils.logging_setup import get_logger

class ReportingManager:
    """Performance tracking and reporting system."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Session data
        self.session_start_time = None
        self.session_trades = []
        self.equity_history = []
        self.session_stats = {}
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_commission = 0.0
        self.max_winning_streak = 0
        self.max_losing_streak = 0
        self.current_streak = 0
        self.streak_type = None  # 'win' or 'loss'
        
        # Ensure reports directory exists
        self.reports_dir = "reports"
        os.makedirs(self.reports_dir, exist_ok=True)
        
        self.logger.info("📊 Reporting Manager initialized")
    
    def initialize_session(self, account_info: Dict[str, Any]) -> None:
        """Initialize a new reporting session."""
        try:
            self.session_start_time = datetime.now()
            self.session_trades = []
            self.equity_history = []
            
            self.session_stats = {
                "start_time": self.session_start_time,
                "start_balance": account_info.get("balance", 0),
                "start_equity": account_info.get("equity", 0),
                "account_login": account_info.get("login", "Unknown"),
                "server": account_info.get("server", "Unknown"),
                "currency": account_info.get("currency", "USD")
            }
            
            # Add initial equity point
            self.add_equity_point(account_info.get("equity", 0))
            
            self.logger.info(f"📈 Reporting session initialized for account {account_info.get('login', 'Unknown')}")
            
        except Exception as e:
            self.logger.error(f"❌ Reporting session initialization error: {str(e)}")
    
    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """Log a completed trade."""
        try:
            trade_record = {
                "timestamp": datetime.now(),
                "symbol": trade_data.get("symbol", "Unknown"),
                "type": trade_data.get("type", "Unknown"),
                "volume": trade_data.get("volume", 0),
                "entry_price": trade_data.get("price", 0),
                "stop_loss": trade_data.get("sl", 0),
                "take_profit": trade_data.get("tp", 0),
                "order_id": trade_data.get("order", 0),
                "deal_id": trade_data.get("deal", 0),
                "comment": trade_data.get("comment", ""),
                "confidence": trade_data.get("confidence", 0),
                "market_context": trade_data.get("market_context", {}),
                "status": "OPEN"
            }
            
            self.session_trades.append(trade_record)
            self.total_trades += 1
            
            self.logger.info(f"📝 Trade logged: {trade_record['symbol']} {trade_record['type']} {trade_record['volume']}")
            
        except Exception as e:
            self.logger.error(f"❌ Trade logging error: {str(e)}")
    
    def update_trade_outcome(self, order_id: int, outcome_data: Dict[str, Any]) -> None:
        """Update trade with exit information."""
        try:
            for trade in self.session_trades:
                if trade.get("order_id") == order_id:
                    trade.update({
                        "exit_time": datetime.now(),
                        "exit_price": outcome_data.get("exit_price", 0),
                        "profit": outcome_data.get("profit", 0),
                        "commission": outcome_data.get("commission", 0),
                        "swap": outcome_data.get("swap", 0),
                        "status": "CLOSED"
                    })
                    
                    # Update performance metrics
                    self._update_performance_metrics(trade)
                    
                    self.logger.info(f"📊 Trade outcome updated: Order {order_id}, Profit: ${outcome_data.get('profit', 0):.2f}")
                    break
            
        except Exception as e:
            self.logger.error(f"❌ Trade outcome update error: {str(e)}")
    
    def _update_performance_metrics(self, trade: Dict[str, Any]) -> None:
        """Update performance metrics after trade closure."""
        try:
            profit = trade.get("profit", 0)
            commission = trade.get("commission", 0)
            
            self.total_profit += profit
            self.total_commission += commission
            
            if profit > 0:
                self.winning_trades += 1
                if self.streak_type == "win":
                    self.current_streak += 1
                else:
                    self.current_streak = 1
                    self.streak_type = "win"
                self.max_winning_streak = max(self.max_winning_streak, self.current_streak)
            else:
                self.losing_trades += 1
                if self.streak_type == "loss":
                    self.current_streak += 1
                else:
                    self.current_streak = 1
                    self.streak_type = "loss"
                self.max_losing_streak = max(self.max_losing_streak, self.current_streak)
            
        except Exception as e:
            self.logger.error(f"❌ Performance metrics update error: {str(e)}")
    
    def add_equity_point(self, equity: float) -> None:
        """Add equity data point for curve tracking."""
        try:
            equity_point = {
                "timestamp": datetime.now(),
                "equity": equity
            }
            
            self.equity_history.append(equity_point)
            
            # Keep only last 1000 points to manage memory
            if len(self.equity_history) > 1000:
                self.equity_history = self.equity_history[-1000:]
            
        except Exception as e:
            self.logger.error(f"❌ Equity point addition error: {str(e)}")
    
    def get_equity_data(self) -> List[Dict[str, Any]]:
        """Get equity curve data."""
        return self.equity_history.copy()
    
    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        try:
            if not self.session_start_time:
                return {"error": "No active session"}
            
            session_duration = datetime.now() - self.session_start_time
            hours = session_duration.total_seconds() / 3600
            
            # Basic metrics
            win_rate = (self.winning_trades / max(self.total_trades, 1)) * 100
            avg_profit_per_trade = self.total_profit / max(self.total_trades, 1)
            
            # Profit factor
            gross_profit = sum([t.get("profit", 0) for t in self.session_trades if t.get("profit", 0) > 0])
            gross_loss = abs(sum([t.get("profit", 0) for t in self.session_trades if t.get("profit", 0) < 0]))
            profit_factor = gross_profit / max(gross_loss, 0.01)
            
            # Drawdown calculation
            equity_values = [point["equity"] for point in self.equity_history]
            if equity_values:
                peak_equity = max(equity_values)
                current_equity = equity_values[-1]
                current_drawdown = (peak_equity - current_equity) / peak_equity * 100
                
                # Calculate maximum drawdown
                max_drawdown = 0
                peak = equity_values[0]
                for equity in equity_values:
                    if equity > peak:
                        peak = equity
                    drawdown = (peak - equity) / peak * 100
                    max_drawdown = max(max_drawdown, drawdown)
            else:
                current_drawdown = 0
                max_drawdown = 0
            
            # Return metrics
            start_equity = self.session_stats.get("start_equity", 1)
            current_equity = equity_values[-1] if equity_values else start_equity
            total_return = ((current_equity - start_equity) / start_equity) * 100
            
            return {
                "session_duration_hours": hours,
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": win_rate,
                "total_profit": self.total_profit,
                "total_commission": self.total_commission,
                "net_profit": self.total_profit - self.total_commission,
                "avg_profit_per_trade": avg_profit_per_trade,
                "profit_factor": profit_factor,
                "max_winning_streak": self.max_winning_streak,
                "max_losing_streak": self.max_losing_streak,
                "current_drawdown": current_drawdown,
                "max_drawdown": max_drawdown,
                "total_return": total_return,
                "start_equity": start_equity,
                "current_equity": current_equity,
                "trades_per_hour": self.total_trades / max(hours, 1)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Performance metrics calculation error: {str(e)}")
            return {"error": str(e)}
    
    def export_report(self, format: str = "json") -> str:
        """Export comprehensive trading report."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            report_data = {
                "session_info": self.session_stats,
                "performance_metrics": self.calculate_performance_metrics(),
                "trades": self.session_trades,
                "equity_history": self.equity_history,
                "export_timestamp": datetime.now().isoformat()
            }
            
            if format.lower() == "json":
                filename = f"{self.reports_dir}/trading_report_{timestamp}.json"
                with open(filename, 'w') as f:
                    json.dump(report_data, f, indent=2, default=str)
                    
            elif format.lower() == "csv":
                filename = f"{self.reports_dir}/trading_report_{timestamp}.csv"
                with open(filename, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        'timestamp', 'symbol', 'type', 'volume', 'entry_price', 
                        'exit_price', 'profit', 'commission', 'confidence'
                    ])
                    writer.writeheader()
                    for trade in self.session_trades:
                        writer.writerow({
                            'timestamp': trade.get('timestamp', ''),
                            'symbol': trade.get('symbol', ''),
                            'type': trade.get('type', ''),
                            'volume': trade.get('volume', ''),
                            'entry_price': trade.get('entry_price', ''),
                            'exit_price': trade.get('exit_price', ''),
                            'profit': trade.get('profit', ''),
                            'commission': trade.get('commission', ''),
                            'confidence': trade.get('confidence', '')
                        })
            else:
                return f"Export failed: Unsupported format '{format}'"
            
            self.logger.info(f"📋 Report exported: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"❌ Report export error: {str(e)}")
            return f"Export failed: {str(e)}"
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """Get quick trade summary for GUI display."""
        try:
            open_trades = [t for t in self.session_trades if t.get("status") == "OPEN"]
            closed_trades = [t for t in self.session_trades if t.get("status") == "CLOSED"]
            
            return {
                "total_trades": len(self.session_trades),
                "open_trades": len(open_trades),
                "closed_trades": len(closed_trades),
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "total_profit": self.total_profit,
                "win_rate": (self.winning_trades / max(len(closed_trades), 1)) * 100
            }
            
        except Exception as e:
            self.logger.error(f"❌ Trade summary error: {str(e)}")
            return {"error": str(e)}
