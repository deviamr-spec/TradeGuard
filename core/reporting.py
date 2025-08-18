
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
    """Comprehensive reporting and performance tracking system."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Initialize report storage
        self.trades_log = []
        self.equity_curve = []
        self.session_start_time = datetime.now()
        self.session_data = {
            "start_balance": 0.0,
            "current_balance": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_profit": 0.0,
            "max_equity": 0.0,
            "max_drawdown": 0.0
        }
        
        # Create reports directory
        self.reports_dir = "reports"
        os.makedirs(self.reports_dir, exist_ok=True)
        
        self.logger.info("📊 Reporting Manager initialized")
    
    def initialize_session(self, account_info: Dict[str, Any]) -> None:
        """Initialize reporting for a new trading session."""
        try:
            self.session_start_time = datetime.now()
            starting_balance = account_info.get("balance", 0.0)
            
            self.session_data.update({
                "start_balance": starting_balance,
                "current_balance": starting_balance,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_profit": 0.0,
                "max_equity": starting_balance,
                "max_drawdown": 0.0
            })
            
            # Initialize equity curve
            self.equity_curve = [{
                "timestamp": self.session_start_time,
                "equity": starting_balance,
                "balance": starting_balance
            }]
            
            self.logger.info(f"📊 Reporting session initialized with balance: ${starting_balance:,.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ Reporting initialization error: {str(e)}")
    
    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """Log a completed trade."""
        try:
            trade_entry = {
                "timestamp": datetime.now(),
                "symbol": trade_data.get("symbol", ""),
                "type": trade_data.get("type", ""),
                "volume": trade_data.get("volume", 0.0),
                "entry_price": trade_data.get("price", 0.0),
                "stop_loss": trade_data.get("sl", 0.0),
                "take_profit": trade_data.get("tp", 0.0),
                "order_id": trade_data.get("order", 0),
                "deal_id": trade_data.get("deal", 0),
                "comment": trade_data.get("comment", ""),
                "confidence": trade_data.get("confidence", 0.0),
                "market_context": trade_data.get("market_context", {}),
                "exit_price": None,
                "profit": None,
                "status": "OPEN"
            }
            
            self.trades_log.append(trade_entry)
            self.session_data["total_trades"] += 1
            
            self.logger.info(f"📝 Trade logged: {trade_entry['symbol']} {trade_entry['type']} {trade_entry['volume']}")
            
        except Exception as e:
            self.logger.error(f"❌ Trade logging error: {str(e)}")
    
    def update_trade_outcome(self, order_id: int, outcome_data: Dict[str, Any]) -> None:
        """Update trade with exit information."""
        try:
            for trade in self.trades_log:
                if trade.get("order_id") == order_id and trade.get("status") == "OPEN":
                    trade.update({
                        "exit_price": outcome_data.get("exit_price", 0.0),
                        "profit": outcome_data.get("profit", 0.0),
                        "commission": outcome_data.get("commission", 0.0),
                        "swap": outcome_data.get("swap", 0.0),
                        "exit_timestamp": datetime.now(),
                        "status": "CLOSED"
                    })
                    
                    # Update session statistics
                    profit = outcome_data.get("profit", 0.0)
                    self.session_data["total_profit"] += profit
                    
                    if profit > 0:
                        self.session_data["winning_trades"] += 1
                    else:
                        self.session_data["losing_trades"] += 1
                    
                    self.logger.info(f"💰 Trade closed: Order {order_id}, Profit: ${profit:.2f}")
                    break
            
        except Exception as e:
            self.logger.error(f"❌ Trade outcome update error: {str(e)}")
    
    def add_equity_point(self, current_equity: float) -> None:
        """Add equity data point for performance tracking."""
        try:
            equity_point = {
                "timestamp": datetime.now(),
                "equity": current_equity,
                "balance": self.session_data.get("current_balance", current_equity)
            }
            
            self.equity_curve.append(equity_point)
            
            # Update session data
            self.session_data["current_balance"] = current_equity
            
            # Track maximum equity
            if current_equity > self.session_data["max_equity"]:
                self.session_data["max_equity"] = current_equity
            
            # Calculate drawdown
            max_equity = self.session_data["max_equity"]
            current_drawdown = (max_equity - current_equity) / max_equity if max_equity > 0 else 0
            if current_drawdown > self.session_data["max_drawdown"]:
                self.session_data["max_drawdown"] = current_drawdown
            
            # Keep only last 1000 points to manage memory
            if len(self.equity_curve) > 1000:
                self.equity_curve = self.equity_curve[-1000:]
            
        except Exception as e:
            self.logger.error(f"❌ Equity tracking error: {str(e)}")
    
    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        try:
            closed_trades = [t for t in self.trades_log if t.get("status") == "CLOSED"]
            
            if not closed_trades:
                return {
                    "total_trades": 0,
                    "win_rate": 0.0,
                    "total_profit": 0.0,
                    "avg_profit": 0.0,
                    "max_drawdown": 0.0,
                    "sharpe_ratio": 0.0,
                    "profit_factor": 0.0
                }
            
            # Basic metrics
            total_trades = len(closed_trades)
            winning_trades = len([t for t in closed_trades if t.get("profit", 0) > 0])
            losing_trades = len([t for t in closed_trades if t.get("profit", 0) < 0])
            
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            profits = [t.get("profit", 0) for t in closed_trades]
            total_profit = sum(profits)
            avg_profit = total_profit / total_trades if total_trades > 0 else 0
            
            # Advanced metrics
            winning_profits = [p for p in profits if p > 0]
            losing_profits = [p for p in profits if p < 0]
            
            avg_win = sum(winning_profits) / len(winning_profits) if winning_profits else 0
            avg_loss = abs(sum(losing_profits) / len(losing_profits)) if losing_profits else 0
            
            profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
            
            # Calculate Sharpe ratio (simplified)
            if len(profits) > 1:
                profit_std = np.std(profits) if len(profits) > 1 else 1
                sharpe_ratio = (avg_profit / profit_std) if profit_std > 0 else 0
            else:
                sharpe_ratio = 0
            
            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "total_profit": total_profit,
                "avg_profit": avg_profit,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "max_drawdown": self.session_data["max_drawdown"] * 100,
                "sharpe_ratio": sharpe_ratio,
                "profit_factor": profit_factor,
                "session_duration_hours": (datetime.now() - self.session_start_time).total_seconds() / 3600
            }
            
        except Exception as e:
            self.logger.error(f"❌ Performance calculation error: {str(e)}")
            return {"error": str(e)}
    
    def generate_daily_report(self) -> str:
        """Generate a comprehensive daily trading report."""
        try:
            metrics = self.calculate_performance_metrics()
            current_time = datetime.now()
            
            report = f"""
📊 DAILY TRADING REPORT - {current_time.strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

💰 PERFORMANCE SUMMARY
   Total Trades:     {metrics.get('total_trades', 0)}
   Winning Trades:   {metrics.get('winning_trades', 0)}
   Losing Trades:    {metrics.get('losing_trades', 0)}
   Win Rate:         {metrics.get('win_rate', 0):.1f}%
   
   Total Profit:     ${metrics.get('total_profit', 0):.2f}
   Average Profit:   ${metrics.get('avg_profit', 0):.2f}
   Average Win:      ${metrics.get('avg_win', 0):.2f}
   Average Loss:     ${metrics.get('avg_loss', 0):.2f}
   
   Max Drawdown:     {metrics.get('max_drawdown', 0):.2f}%
   Profit Factor:    {metrics.get('profit_factor', 0):.2f}
   Sharpe Ratio:     {metrics.get('sharpe_ratio', 0):.2f}
   
📈 SESSION DATA
   Start Balance:    ${self.session_data.get('start_balance', 0):.2f}
   Current Balance:  ${self.session_data.get('current_balance', 0):.2f}
   Session Duration: {metrics.get('session_duration_hours', 0):.1f} hours
   
⚠️ RISK METRICS
   Max Equity:       ${self.session_data.get('max_equity', 0):.2f}
   Current Drawdown: {((self.session_data.get('max_equity', 0) - self.session_data.get('current_balance', 0)) / self.session_data.get('max_equity', 1)) * 100:.2f}%

📋 RECENT TRADES (Last 5)
"""
            
            # Add recent trades
            recent_trades = sorted(self.trades_log, key=lambda x: x.get('timestamp', datetime.now()), reverse=True)[:5]
            
            for trade in recent_trades:
                status = trade.get('status', 'UNKNOWN')
                profit = trade.get('profit', 0)
                profit_str = f"${profit:.2f}" if profit is not None else "OPEN"
                
                report += f"   {trade.get('timestamp', 'N/A').strftime('%H:%M:%S')} | {trade.get('symbol', 'N/A')} {trade.get('type', 'N/A')} | {profit_str}\n"
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Report generation error: {str(e)}")
            return f"Report generation failed: {str(e)}"
    
    def save_session_data(self) -> bool:
        """Save session data to file."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save trades log
            trades_file = os.path.join(self.reports_dir, f"trades_{timestamp}.json")
            with open(trades_file, 'w') as f:
                json.dump(self.trades_log, f, indent=2, default=str)
            
            # Save equity curve
            equity_file = os.path.join(self.reports_dir, f"equity_{timestamp}.json")
            with open(equity_file, 'w') as f:
                json.dump(self.equity_curve, f, indent=2, default=str)
            
            # Save performance metrics
            metrics_file = os.path.join(self.reports_dir, f"metrics_{timestamp}.json")
            metrics = self.calculate_performance_metrics()
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)
            
            self.logger.info(f"💾 Session data saved to {self.reports_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Session save error: {str(e)}")
            return False
