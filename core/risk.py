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

        # Trade tracking
        self.trades_today = 0
        self.max_trades_per_day = 20
        self.losing_streak = 0
        self.max_losing_streak = 5

        self.logger.info("✅ Risk Manager initialized")

    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics for monitoring."""
        try:
            return {
                "max_risk_per_trade": self.max_risk_per_trade,
                "max_daily_loss": self.max_daily_loss,
                "max_drawdown": self.max_drawdown,
                "current_drawdown": self.current_drawdown,
                "daily_loss": self.daily_loss,
                "trades_today": self.trades_today,
                "max_trades_per_day": self.max_trades_per_day,
                "losing_streak": self.losing_streak,
                "max_losing_streak": self.max_losing_streak,
                "session_start_balance": self.session_start_balance,
                "peak_balance": self.peak_balance
            }
        except Exception as e:
            self.logger.error(f"❌ Error getting risk metrics: {str(e)}")
            return {}

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

    # Removed on_trade_executed from here as it was duplicated and modified above.
    # The original on_trade_executed was:
    # def on_trade_executed(self, trade_result: Dict[str, Any]) -> None:
    #     """Update counters when a trade is executed."""
    #     try:
    #         with self.lock:
    #             self.session_trades += 1
    #             self.daily_trades += 1
    #
    #             self.logger.debug(f"📊 Trade executed: Session {self.session_trades}, Daily {self.daily_trades}")
    #
    #     except Exception as e:
    #         self.logger.error(f"❌ Trade execution tracking error: {str(e)}")

    # Removed update_session_stats from here as it was duplicated and modified above.
    # The original update_session_stats was:
    # def update_session_stats(self, account_info: Dict[str, Any]) -> None:
    #     """Update session statistics."""
    #     try:
    #         with self.lock:
    #             current_equity = account_info.get("equity", 0)
    #
    #             # Update max equity
    #             if current_equity > self.session_max_equity:
    #                 self.session_max_equity = current_equity
    #
    #     except Exception as e:
    #         self.logger.error(f"❌ Session stats update error: {str(e)}")

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