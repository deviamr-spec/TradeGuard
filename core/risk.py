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

        # Risk parameters from config
        self.max_risk_per_trade = config.get("risk_management.risk_per_trade", 0.02)
        self.risk_per_trade = self.max_risk_per_trade  # Add missing attribute
        self.max_daily_loss = config.get("trading.max_daily_loss", 0.05)
        self.max_drawdown = config.get("trading.max_drawdown", 0.10)
        self.max_positions = config.get("trading.max_positions", 5)
        self.max_spread_pips = config.get("risk_management.max_spread_pips", 3)

        # Session tracking
        self.session_start_balance = 0.0
        self.daily_start_balance = 0.0
        self.peak_balance = 0.0
        self.current_drawdown = 0.0
        self.daily_loss = 0.0
        self.current_balance = 0.0
        self.daily_pnl = 0.0

        # Trade tracking
        self.trades_today = 0
        self.max_trades_per_day = 20
        self.max_daily_trades = 20
        self.daily_trades = 0
        self.losing_streak = 0
        self.max_losing_streak = 5
        
        # Missing attributes
        self.margin_usage_percent = 0.0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.emergency_stop = False
        self.emergency_stop_triggered = False
        self.emergency_stop_reason = ""
        self.trading_halted = False
        self.session_max_equity = 0.0
        self.session_trades = 0
        self.open_positions = []
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Date tracking
        self.session_start_time = datetime.now()
        self.last_trade_reset = datetime.now().date()

        # Initialize daily tracking
        if self.daily_start_balance == 0.0:
            self.daily_start_balance = 10000.0  # Default demo balance
        if self.session_start_balance == 0.0:
            self.session_start_balance = self.daily_start_balance

        self.logger.info("✅ Risk Manager initialized")

    def update_margin_usage(self, account_info: Dict[str, Any]) -> None:
        """Update margin usage percentage."""
        try:
            equity = account_info.get('equity', 0.0)
            margin = account_info.get('margin', 0.0)
            
            if equity > 0:
                self.margin_usage_percent = (margin / equity) * 100
            else:
                self.margin_usage_percent = 0.0
                
        except Exception as e:
            self.logger.error(f"❌ Margin usage update error: {str(e)}")
            self.margin_usage_percent = 0.0

    def _calculate_risk_score(self) -> float:
        """Calculate overall risk score (0-100)."""
        try:
            risk_score = 0.0
            
            # Drawdown risk (0-30 points)
            drawdown_risk = min(30, (self.current_drawdown / self.max_drawdown) * 30) if self.max_drawdown > 0 else 0
            risk_score += drawdown_risk
            
            # Margin risk (0-25 points)
            margin_risk = min(25, (self.margin_usage_percent / 100) * 25)
            risk_score += margin_risk
            
            # Performance risk (0-25 points)
            if self.total_trades > 0:
                win_rate = (self.winning_trades / self.total_trades) * 100
                if win_rate < 40:
                    risk_score += 25
                elif win_rate < 50:
                    risk_score += 15
                elif win_rate < 60:
                    risk_score += 10
            
            # Daily loss risk (0-20 points)
            if self.daily_start_balance > 0:
                daily_loss_pct = abs(self.daily_pnl / self.daily_start_balance) * 100
                risk_score += min(20, (daily_loss_pct / self.max_daily_loss) * 20)
            
            return min(100, max(0, risk_score))
            
        except Exception as e:
            self.logger.error(f"❌ Risk score calculation error: {str(e)}")
            return 50.0

    def get_risk_metrics(self) -> Dict[str, Any]:
        """
        Get current risk metrics for GUI display.

        Returns:
            Risk metrics dictionary
        """
        try:
            return {
                "current_drawdown": self.current_drawdown,
                "max_drawdown": self.max_drawdown,
                "margin_usage": self.margin_usage_percent,
                "win_rate": (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
                "profit_factor": abs(self.total_profit / self.total_loss) if self.total_loss != 0 else float('inf'),
                "total_trades": self.total_trades,
                "emergency_stop": self.emergency_stop_triggered,
                "risk_score": self._calculate_risk_score()
            }
        except Exception as e:
            self.logger.error(f"❌ Risk metrics error: {str(e)}")
            return {
                "current_drawdown": 0.0,
                "max_drawdown": 0.0,
                "margin_usage": 0.0,
                "win_rate": 0.0,
                "profit_factor": 1.0,
                "total_trades": 0,
                "emergency_stop": False,
                "risk_score": 0.0
            }

    def update_session_stats(self, account_info: Dict[str, Any]) -> None:
        """Update session statistics with current account info."""
        try:
            current_balance = account_info.get('balance', 0.0)
            current_equity = account_info.get('equity', 0.0)

            # Initialize session start balance if not set
            if self.session_start_balance == 0.0:
                self.session_start_balance = current_balance
                self.daily_start_balance = current_balance
                self.peak_balance = current_balance

            # Update peak balance
            if current_equity > self.peak_balance:
                self.peak_balance = current_equity

            # Calculate current drawdown
            if self.peak_balance > 0:
                self.current_drawdown = (self.peak_balance - current_equity) / self.peak_balance

            # Calculate daily loss
            if self.daily_start_balance > 0:
                self.daily_loss = (self.daily_start_balance - current_equity) / self.daily_start_balance

        except Exception as e:
            self.logger.error(f"❌ Error updating session stats: {str(e)}")

    def on_trade_executed(self, trade_result: Dict[str, Any]) -> None:
        """Update risk tracking when a trade is executed."""
        try:
            self.trades_today += 1
            self.logger.debug(f"Trade executed, total today: {self.trades_today}")
        except Exception as e:
            self.logger.error(f"❌ Error updating trade execution stats: {str(e)}")

    def initialize_session(self, starting_balance: float) -> None:
        """Initialize a new trading session."""
        try:
            self.session_start_time = datetime.now()
            self.session_start_balance = starting_balance
            self.session_max_equity = starting_balance
            self.session_trades = 0
            self.emergency_stop = False
            self.trading_halted = False
            self.current_balance = starting_balance

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
        """
        Generate comprehensive risk report.

        Returns:
            Risk report dictionary
        """
        try:
            current_time = datetime.now()

            return {
                "timestamp": current_time,
                "session_duration_hours": (current_time - self.session_start_time).total_seconds() / 3600,
                "session_start_balance": self.session_start_balance,
                "current_balance": self.current_balance,
                "session_pnl": self.current_balance - self.session_start_balance,
                "session_pnl_percent": ((self.current_balance - self.session_start_balance) / self.session_start_balance * 100) if self.session_start_balance > 0 else 0,
                "daily_pnl": self.daily_pnl,
                "daily_pnl_percent": (self.daily_pnl / self.daily_start_balance * 100) if self.daily_start_balance > 0 else 0,
                "peak_balance": self.peak_balance,
                "current_drawdown": self.current_drawdown,
                "max_drawdown": self.max_drawdown,
                "drawdown_percent": (self.current_drawdown / self.peak_balance * 100) if self.peak_balance > 0 else 0,
                "risk_score": self._calculate_risk_score(),
                "emergency_stop_active": self.emergency_stop_triggered,
                "emergency_stop_reason": self.emergency_stop_reason,
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
                "average_profit": self.total_profit / self.winning_trades if self.winning_trades > 0 else 0,
                "average_loss": abs(self.total_loss / self.losing_trades) if self.losing_trades > 0 else 0,
                "profit_factor": abs(self.total_profit / self.total_loss) if self.total_loss != 0 else float('inf'),
                "margin_usage_percent": self.margin_usage_percent,
                "free_margin_percent": 100 - self.margin_usage_percent,
                "position_count": len(self.open_positions),
                "max_position_limit": self.max_positions,
                "position_limit_usage": (len(self.open_positions) / self.max_positions * 100) if self.max_positions > 0 else 0
            }

        except Exception as e:
            self.logger.error(f"❌ Risk report generation error: {str(e)}")
            return {"error": str(e), "timestamp": datetime.now()}

    def reset_emergency_stop(self) -> bool:
        """Reset emergency stop (manual override)."""
        try:
            self.emergency_stop = False
            self.trading_halted = False
            self.emergency_stop_triggered = False
            self.emergency_stop_reason = ""
            self.logger.warning("⚠️ Emergency stop manually reset")
            return True

        except Exception as e:
            self.logger.error(f"❌ Emergency stop reset error: {str(e)}")
            return False