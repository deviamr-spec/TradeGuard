"""
Risk Management Module.
Handles position sizing, risk limits, and safety checks.
"""

import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from core.config import config
from utils.logging_setup import get_logger

class RiskManager:
    """Comprehensive risk management system."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Risk parameters
        self.risk_per_trade = config.get("risk.risk_per_trade", 0.01)
        self.max_daily_loss = config.get("risk.max_daily_loss", 0.05)
        self.max_drawdown = config.get("risk.max_drawdown", 0.10)
        self.max_positions = config.get("trading.max_positions", 5)
        self.max_daily_trades = config.get("trading.max_daily_trades", 50)
        
        # Session tracking
        self.session_start_time = None
        self.session_start_balance = 0.0
        self.session_trades = 0
        self.session_max_equity = 0.0
        self.daily_trades = 0
        self.last_trade_reset = datetime.now().date()
        
        # Emergency flags
        self.emergency_stop = False
        self.trading_halted = False
        
        # Thread safety
        self.lock = threading.Lock()
        
        self.logger.info(f"🛡️ Risk Manager initialized:")
        self.logger.info(f"   Risk per trade: {self.risk_per_trade*100:.1f}%")
        self.logger.info(f"   Max daily loss: {self.max_daily_loss*100:.1f}%")
        self.logger.info(f"   Max drawdown: {self.max_drawdown*100:.1f}%")
        self.logger.info(f"   Max positions: {self.max_positions}")
    
    def initialize_session(self, starting_balance: float) -> None:
        """Initialize a new trading session."""
        try:
            with self.lock:
                self.session_start_time = datetime.now()
                self.session_start_balance = starting_balance
                self.session_max_equity = starting_balance
                self.session_trades = 0
                self.emergency_stop = False
                self.trading_halted = False
                
                self.logger.info(f"💼 Risk session initialized with balance: ${starting_balance:,.2f}")
                
        except Exception as e:
            self.logger.error(f"❌ Risk session initialization error: {str(e)}")
    
    def validate_trade(self, signal: Dict[str, Any], account_info: Dict[str, Any], 
                      positions: List[Dict[str, Any]], symbol_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate if a trade should be allowed.
        
        Returns:
            Dict with 'allowed' (bool), 'reason' (str), and 'warnings' (list)
        """
        try:
            with self.lock:
                warnings = []
                
                # Reset daily counter if new day
                current_date = datetime.now().date()
                if current_date != self.last_trade_reset:
                    self.daily_trades = 0
                    self.last_trade_reset = current_date
                
                # Check emergency stop
                if self.emergency_stop:
                    return {
                        "allowed": False,
                        "reason": "Emergency stop activated",
                        "warnings": warnings
                    }
                
                # Check if trading is halted
                if self.trading_halted:
                    return {
                        "allowed": False,
                        "reason": "Trading halted due to risk limits",
                        "warnings": warnings
                    }
                
                # Check max positions
                if len(positions) >= self.max_positions:
                    return {
                        "allowed": False,
                        "reason": f"Maximum positions reached ({self.max_positions})",
                        "warnings": warnings
                    }
                
                # Check daily trade limit
                if self.daily_trades >= self.max_daily_trades:
                    return {
                        "allowed": False,
                        "reason": f"Daily trade limit reached ({self.max_daily_trades})",
                        "warnings": warnings
                    }
                
                # Check account balance
                current_balance = account_info.get("balance", 0)
                if current_balance <= 0:
                    return {
                        "allowed": False,
                        "reason": "Insufficient account balance",
                        "warnings": warnings
                    }
                
                # Check margin level
                margin_level = account_info.get("margin_level", 0)
                if margin_level > 0 and margin_level < 200:  # 200% minimum margin level
                    return {
                        "allowed": False,
                        "reason": f"Margin level too low ({margin_level:.1f}%)",
                        "warnings": warnings
                    }
                
                # Check daily loss limit
                current_equity = account_info.get("equity", 0)
                if self.session_start_balance > 0:
                    daily_loss = (self.session_start_balance - current_equity) / self.session_start_balance
                    if daily_loss >= self.max_daily_loss:
                        return {
                            "allowed": False,
                            "reason": f"Daily loss limit exceeded ({daily_loss:.1%})",
                            "warnings": warnings
                        }
                    
                    # Risk warnings (don't block trade but warn)
                    if daily_loss >= self.max_daily_loss * 0.7:
                        warnings.append(f"Approaching daily loss limit ({daily_loss:.1%})")
                
                # Check signal quality
                confidence = signal.get("confidence", 0)
                if confidence < 50:
                    warnings.append(f"Low signal confidence ({confidence:.1f}%)")
                
                # Position count warning
                if len(positions) >= self.max_positions * 0.8:
                    warnings.append(f"High position count ({len(positions)})")
                
                return {
                    "allowed": True,
                    "reason": "",
                    "warnings": warnings
                }
                
        except Exception as e:
            self.logger.error(f"❌ Trade validation error: {str(e)}")
            return {
                "allowed": False,
                "reason": f"Validation error: {str(e)}",
                "warnings": []
            }
    
    def calculate_position_size(self, account_balance: float, risk_amount: float, 
                               stop_loss_pips: float, pip_value: float) -> float:
        """Calculate position size based on risk parameters."""
        try:
            if stop_loss_pips <= 0 or pip_value <= 0:
                return config.get("risk.min_lot_size", 0.01)
            
            # Calculate lot size
            pip_risk = stop_loss_pips * pip_value
            lot_size = risk_amount / pip_risk
            
            # Apply limits
            min_lot = config.get("risk.min_lot_size", 0.01)
            max_lot = config.get("risk.max_lot_size", 1.0)
            
            lot_size = max(min_lot, min(lot_size, max_lot))
            
            # Round to valid lot size
            lot_size = round(lot_size / min_lot) * min_lot
            
            return lot_size
            
        except Exception as e:
            self.logger.error(f"❌ Position size calculation error: {str(e)}")
            return config.get("risk.min_lot_size", 0.01)
    
    def on_trade_executed(self, trade_result: Dict[str, Any]) -> None:
        """Update counters when a trade is executed."""
        try:
            with self.lock:
                self.session_trades += 1
                self.daily_trades += 1
                
                self.logger.debug(f"📊 Trade executed: Session {self.session_trades}, Daily {self.daily_trades}")
                
        except Exception as e:
            self.logger.error(f"❌ Trade execution tracking error: {str(e)}")
    
    def update_session_stats(self, account_info: Dict[str, Any]) -> None:
        """Update session statistics."""
        try:
            with self.lock:
                current_equity = account_info.get("equity", 0)
                
                # Update max equity
                if current_equity > self.session_max_equity:
                    self.session_max_equity = current_equity
                
        except Exception as e:
            self.logger.error(f"❌ Session stats update error: {str(e)}")
    
    def emergency_stop_check(self, account_info: Dict[str, Any]) -> bool:
        """Check if emergency stop should be triggered."""
        try:
            current_equity = account_info.get("equity", 0)
            
            # Check critical drawdown
            if current_equity < self.session_max_equity:
                drawdown = (self.session_max_equity - current_equity) / self.session_max_equity
                if drawdown >= self.max_drawdown * 1.5:  # 1.5x emergency threshold
                    self.emergency_stop = True
                    self.logger.critical(f"🚨 EMERGENCY STOP: Critical drawdown {drawdown*100:.1f}%")
                    return True
            
            # Check critical daily loss
            daily_pnl = current_equity - self.session_start_balance
            if daily_pnl < 0:
                daily_loss_pct = abs(daily_pnl) / self.session_start_balance
                if daily_loss_pct >= self.max_daily_loss * 1.5:  # 1.5x emergency threshold
                    self.emergency_stop = True
                    self.logger.critical(f"🚨 EMERGENCY STOP: Critical daily loss {daily_loss_pct*100:.1f}%")
                    return True
            
            # Check margin level
            margin_level = account_info.get("margin_level", 1000)
            if margin_level < 50 and margin_level > 0:
                self.emergency_stop = True
                self.logger.critical(f"🚨 EMERGENCY STOP: Critical margin level {margin_level:.1f}%")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Emergency stop check error: {str(e)}")
            return False
    
    def get_risk_report(self) -> Dict[str, Any]:
        """Get comprehensive risk report."""
        try:
            if not self.session_start_time:
                return {"error": "No active session"}
            
            session_duration = datetime.now() - self.session_start_time
            hours = session_duration.total_seconds() / 3600
            
            return {
                "session_duration": f"{hours:.1f}h",
                "session_trades": self.session_trades,
                "daily_trades": self.daily_trades,
                "max_daily_trades": self.max_daily_trades,
                "session_start_balance": self.session_start_balance,
                "max_equity": self.session_max_equity,
                "emergency_stop": self.emergency_stop,
                "trading_halted": self.trading_halted,
                "risk_limits": {
                    "risk_per_trade": f"{self.risk_per_trade*100:.1f}%",
                    "max_daily_loss": f"{self.max_daily_loss*100:.1f}%",
                    "max_drawdown": f"{self.max_drawdown*100:.1f}%",
                    "max_positions": self.max_positions
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Risk report error: {str(e)}")
            return {"error": str(e)}
    
    def reset_emergency_stop(self) -> bool:
        """Reset emergency stop (manual override)."""
        try:
            with self.lock:
                self.emergency_stop = False
                self.trading_halted = False
                self.logger.warning("⚠️ Emergency stop manually reset")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Emergency stop reset error: {str(e)}")
            return False