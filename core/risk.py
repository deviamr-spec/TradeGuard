
"""
Risk Management Module.
Handles position sizing, risk validation, and risk monitoring.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import threading

from core.config import config
from utils.logging_setup import get_logger

class RiskManager:
    """Comprehensive risk management system."""

    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Risk parameters from config
        self.max_risk_per_trade = config.get("risk.max_risk_per_trade", 0.02)
        self.max_daily_loss = config.get("risk.max_daily_loss", 0.05)
        self.max_drawdown = config.get("risk.max_drawdown", 0.10)
        self.max_positions = config.get("risk.max_positions", 5)
        self.max_correlation = config.get("risk.max_correlation", 0.7)
        
        # Session tracking
        self.session_start_balance = 10000.0
        self.daily_start_balance = 10000.0
        self.peak_balance = 10000.0
        self.session_trades = 0
        self.daily_trades = 0
        self.last_trade_time = None
        
        # Risk metrics
        self.current_drawdown = 0.0
        self.daily_pnl = 0.0
        self.session_pnl = 0.0
        self.risk_per_trade = self.max_risk_per_trade
        self.margin_usage_percent = 0.0
        self.var_95 = 0.0
        
        # Thread safety
        self.risk_lock = threading.Lock()
        
        self.logger.info("✅ Risk Manager initialized")
        self.logger.info(f"   Max risk per trade: {self.max_risk_per_trade:.1%}")
        self.logger.info(f"   Max daily loss: {self.max_daily_loss:.1%}")
        self.logger.info(f"   Max drawdown: {self.max_drawdown:.1%}")

    def validate_trade(self, signal: Dict[str, Any], account_info: Dict[str, Any], 
                      positions: List[Dict[str, Any]], symbol_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate if a trade meets risk management criteria.
        
        Args:
            signal: Trading signal dictionary
            account_info: Current account information
            positions: List of current positions
            symbol_info: Symbol information
            
        Returns:
            Dictionary with validation result and details
        """
        try:
            with self.risk_lock:
                validation = {
                    "allowed": True,
                    "reason": "",
                    "warnings": []
                }
                
                # Check maximum positions
                if len(positions) >= self.max_positions:
                    validation["allowed"] = False
                    validation["reason"] = f"Maximum positions limit reached ({self.max_positions})"
                    return validation
                
                # Check daily loss limit
                current_balance = account_info.get("balance", 0)
                if current_balance > 0:
                    daily_loss_pct = (self.daily_start_balance - current_balance) / self.daily_start_balance
                    if daily_loss_pct >= self.max_daily_loss:
                        validation["allowed"] = False
                        validation["reason"] = f"Daily loss limit exceeded ({daily_loss_pct:.1%} >= {self.max_daily_loss:.1%})"
                        return validation
                
                # Check drawdown limit
                if current_balance > 0 and self.peak_balance > 0:
                    current_drawdown = (self.peak_balance - current_balance) / self.peak_balance
                    if current_drawdown >= self.max_drawdown:
                        validation["allowed"] = False
                        validation["reason"] = f"Maximum drawdown exceeded ({current_drawdown:.1%} >= {self.max_drawdown:.1%})"
                        return validation
                
                # Check free margin
                free_margin = account_info.get("free_margin", 0)
                if free_margin <= 0:
                    validation["allowed"] = False
                    validation["reason"] = "Insufficient free margin"
                    return validation
                
                # Check symbol correlation (basic check for same symbol)
                symbol = signal.get("symbol", "")
                same_symbol_positions = [pos for pos in positions if pos.get("symbol") == symbol]
                if len(same_symbol_positions) >= 2:
                    validation["warnings"].append(f"Multiple positions on {symbol}")
                
                # Check trade timing (prevent overtrading)
                if self.last_trade_time:
                    time_since_last = datetime.now() - self.last_trade_time
                    if time_since_last.total_seconds() < 30:  # 30 seconds minimum between trades
                        validation["allowed"] = False
                        validation["reason"] = "Too frequent trading"
                        return validation
                
                return validation
                
        except Exception as e:
            self.logger.error(f"❌ Trade validation error: {str(e)}")
            return {
                "allowed": False,
                "reason": f"Validation error: {str(e)}",
                "warnings": []
            }

    def calculate_position_size(self, signal: Dict[str, Any], balance: float, 
                              symbol_info: Dict[str, Any]) -> float:
        """
        Calculate optimal position size based on risk parameters.
        
        Args:
            signal: Trading signal
            balance: Account balance
            symbol_info: Symbol information
            
        Returns:
            Position size in lots
        """
        try:
            # Get basic parameters
            risk_amount = balance * self.risk_per_trade
            
            # Get symbol information
            point = symbol_info.get("point", 0.00001)
            volume_min = symbol_info.get("volume_min", 0.01)
            volume_max = symbol_info.get("volume_max", 100.0)
            volume_step = symbol_info.get("volume_step", 0.01)
            contract_size = symbol_info.get("contract_size", 100000.0)
            
            # Calculate stop loss distance (basic calculation)
            sl_distance_pips = 20  # Default 20 pips
            confidence = signal.get("confidence", 50.0)
            
            # Adjust SL based on confidence
            if confidence >= 80:
                sl_distance_pips = 15
            elif confidence >= 70:
                sl_distance_pips = 20
            else:
                sl_distance_pips = 25
            
            sl_distance_price = sl_distance_pips * point * 10  # Convert pips to price
            
            # Calculate position size
            # Risk Amount = Position Size * Contract Size * SL Distance
            if sl_distance_price > 0:
                position_size = risk_amount / (contract_size * sl_distance_price)
            else:
                position_size = volume_min
            
            # Round to valid step size
            position_size = round(position_size / volume_step) * volume_step
            
            # Ensure within limits
            position_size = max(volume_min, min(volume_max, position_size))
            
            # Additional safety check - limit to 10% of free margin
            free_margin = signal.get("tick_data", {}).get("ask", 1.0) * contract_size * position_size
            if balance > 0:
                margin_usage = free_margin / balance
                if margin_usage > 0.1:  # 10% max margin usage per trade
                    position_size = (balance * 0.1) / (signal.get("tick_data", {}).get("ask", 1.0) * contract_size)
                    position_size = max(volume_min, round(position_size / volume_step) * volume_step)
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"❌ Position size calculation error: {str(e)}")
            return symbol_info.get("volume_min", 0.01)

    def update_session_stats(self, account_info: Dict[str, Any]) -> None:
        """
        Update session statistics and risk metrics.
        
        Args:
            account_info: Current account information
        """
        try:
            with self.risk_lock:
                current_balance = account_info.get("balance", 0)
                current_equity = account_info.get("equity", 0)
                current_margin = account_info.get("margin", 0)
                free_margin = account_info.get("free_margin", 0)
                
                # Update peak balance
                if current_balance > self.peak_balance:
                    self.peak_balance = current_balance
                
                # Calculate drawdown
                if self.peak_balance > 0:
                    self.current_drawdown = (self.peak_balance - current_balance) / self.peak_balance
                
                # Calculate PnL
                if self.session_start_balance > 0:
                    self.session_pnl = current_balance - self.session_start_balance
                
                if self.daily_start_balance > 0:
                    self.daily_pnl = current_balance - self.daily_start_balance
                
                # Calculate margin usage
                if current_balance > 0 and current_margin >= 0:
                    self.margin_usage_percent = (current_margin / current_balance) * 100
                else:
                    self.margin_usage_percent = 0.0
                
                # Update VaR estimate (simplified)
                if self.session_start_balance > 0:
                    returns = abs(self.session_pnl / self.session_start_balance)
                    self.var_95 = returns * 1.645  # 95% confidence level
                
        except Exception as e:
            self.logger.error(f"❌ Session stats update error: {str(e)}")

    def on_trade_executed(self, trade_result: Dict[str, Any]) -> None:
        """
        Update risk tracking when a trade is executed.
        
        Args:
            trade_result: Trade execution result
        """
        try:
            with self.risk_lock:
                self.session_trades += 1
                self.daily_trades += 1
                self.last_trade_time = datetime.now()
                
                self.logger.info(f"📊 Trade executed - Session: {self.session_trades}, Daily: {self.daily_trades}")
                
        except Exception as e:
            self.logger.error(f"❌ Trade tracking error: {str(e)}")

    def emergency_stop_check(self, account_info: Dict[str, Any]) -> bool:
        """
        Check if emergency stop conditions are met.
        
        Args:
            account_info: Current account information
            
        Returns:
            True if emergency stop should be triggered
        """
        try:
            current_balance = account_info.get("balance", 0)
            
            # Check daily loss limit
            if self.daily_start_balance > 0:
                daily_loss_pct = (self.daily_start_balance - current_balance) / self.daily_start_balance
                if daily_loss_pct >= self.max_daily_loss:
                    self.logger.critical(f"🚨 EMERGENCY STOP: Daily loss limit exceeded ({daily_loss_pct:.1%})")
                    return True
            
            # Check maximum drawdown
            if self.current_drawdown >= self.max_drawdown:
                self.logger.critical(f"🚨 EMERGENCY STOP: Maximum drawdown exceeded ({self.current_drawdown:.1%})")
                return True
            
            # Check margin level
            margin_level = account_info.get("margin_level", 1000)
            if margin_level > 0 and margin_level < 100:  # Less than 100% margin level
                self.logger.critical(f"🚨 EMERGENCY STOP: Low margin level ({margin_level:.1f}%)")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Emergency stop check error: {str(e)}")
            return False

    def get_risk_metrics(self) -> Dict[str, Any]:
        """
        Get current risk metrics for GUI display.
        
        Returns:
            Risk metrics dictionary
        """
        try:
            return {
                "daily_loss": self.daily_pnl,
                "daily_loss_percentage": (abs(self.daily_pnl) / self.daily_start_balance * 100) if self.daily_start_balance > 0 else 0.0,
                "current_drawdown": self.current_drawdown,
                "position_count": self.session_trades,
                "max_positions": self.max_positions,
                "risk_per_trade": self.risk_per_trade * 100,
                "emergency_stop": self.current_drawdown >= self.max_drawdown,
                "margin_usage": self.margin_usage_percent,
                "session_trades": self.session_trades,
                "daily_trades": self.daily_trades
            }
        except Exception as e:
            self.logger.error(f"❌ Risk metrics error: {str(e)}")
            return {
                "daily_loss": 0.0,
                "daily_loss_percentage": 0.0,
                "current_drawdown": 0.0,
                "position_count": 0,
                "max_positions": 5,
                "risk_per_trade": 1.0,
                "emergency_stop": False
            }

    def get_risk_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive risk report.
        
        Returns:
            Risk report dictionary
        """
        try:
            return {
                "session_stats": {
                    "start_balance": self.session_start_balance,
                    "peak_balance": self.peak_balance,
                    "current_drawdown": self.current_drawdown,
                    "session_pnl": self.session_pnl,
                    "session_trades": self.session_trades
                },
                "daily_stats": {
                    "start_balance": self.daily_start_balance,
                    "daily_pnl": self.daily_pnl,
                    "daily_trades": self.daily_trades
                },
                "risk_metrics": {
                    "risk_per_trade": self.risk_per_trade,
                    "margin_usage_percent": self.margin_usage_percent,
                    "var_95": self.var_95,
                    "max_positions": self.max_positions
                },
                "limits": {
                    "max_risk_per_trade": self.max_risk_per_trade,
                    "max_daily_loss": self.max_daily_loss,
                    "max_drawdown": self.max_drawdown,
                    "max_positions": self.max_positions
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Risk report generation error: {str(e)}")
            return {"error": str(e)}

    def reset_daily_stats(self) -> None:
        """Reset daily statistics for new trading day."""
        try:
            with self.risk_lock:
                self.daily_start_balance = self.session_start_balance
                self.daily_trades = 0
                self.daily_pnl = 0.0
                
                self.logger.info("🔄 Daily risk statistics reset")
                
        except Exception as e:
            self.logger.error(f"❌ Daily stats reset error: {str(e)}")
