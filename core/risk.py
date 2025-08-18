"""
Risk Management Module for MT5 Trading Bot.
Handles position sizing, drawdown protection, and trade validation.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
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
        self.max_spread = config.get("risk.max_spread", 2.0)

        # Session tracking
        self.session_start_balance = 0.0
        self.session_start_time = datetime.now()
        self.daily_trades = 0
        self.daily_profit = 0.0
        self.max_equity = 0.0
        self.trade_history = []

        self.logger.info(f"🛡️ Risk Manager initialized:")
        self.logger.info(f"   Risk per trade: {self.risk_per_trade*100:.1f}%")
        self.logger.info(f"   Max daily loss: {self.max_daily_loss*100:.1f}%")
        self.logger.info(f"   Max drawdown: {self.max_drawdown*100:.1f}%")
        self.logger.info(f"   Max positions: {self.max_positions}")

    def initialize_session(self, starting_balance: float) -> None:
        """Initialize a new trading session."""
        try:
            self.session_start_balance = starting_balance
            self.session_start_time = datetime.now()
            self.max_equity = starting_balance
            self.daily_trades = 0
            self.daily_profit = 0.0
            self.trade_history = []

            self.logger.info(f"📊 Risk session initialized with balance: ${starting_balance:,.2f}")

        except Exception as e:
            self.logger.error(f"❌ Session initialization error: {str(e)}")

    def validate_trade(self, signal: Dict[str, Any], account_info: Dict[str, Any], 
                      positions: List[Dict[str, Any]], symbol_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate if a trade should be allowed based on risk criteria.

        Args:
            signal: Trading signal
            account_info: Current account information
            positions: Current open positions
            symbol_info: Symbol information

        Returns:
            Validation result with allowed flag and reasons
        """
        try:
            validation = {
                "allowed": False,
                "reason": "",
                "warnings": []
            }

            # Check if trading is fundamentally allowed
            if not account_info.get("trade_allowed", True):
                validation["reason"] = "Trading not allowed on account"
                return validation

            # Check position limits
            if len(positions) >= self.max_positions:
                validation["reason"] = f"Maximum positions reached ({self.max_positions})"
                return validation

            # Check daily trade limit
            if self.daily_trades >= self.max_daily_trades:
                validation["reason"] = f"Daily trade limit reached ({self.max_daily_trades})"
                return validation

            # Check daily loss limit
            current_balance = account_info.get("balance", 0)
            daily_loss = self.session_start_balance - current_balance
            daily_loss_percent = daily_loss / self.session_start_balance if self.session_start_balance > 0 else 0

            if daily_loss_percent >= self.max_daily_loss:
                validation["reason"] = f"Daily loss limit reached ({daily_loss_percent*100:.1f}%)"
                return validation

            # Check drawdown limit
            current_equity = account_info.get("equity", 0)
            drawdown = (self.max_equity - current_equity) / self.max_equity if self.max_equity > 0 else 0

            if drawdown >= self.max_drawdown:
                validation["reason"] = f"Drawdown limit reached ({drawdown*100:.1f}%)"
                return validation

            # Check symbol-specific risks
            symbol = signal.get("symbol", "")

            # Check spread
            spread = symbol_info.get("spread", 0) * symbol_info.get("point", 0.00001)
            spread_pips = spread / (0.01 if "JPY" in symbol else 0.0001)

            if spread_pips > self.max_spread:
                validation["warnings"].append(f"High spread: {spread_pips:.1f} pips")

            # Check for duplicate positions
            symbol_positions = [p for p in positions if p["symbol"] == symbol]
            if symbol_positions:
                same_direction = [p for p in symbol_positions if p["type"] == signal["signal"]]
                if same_direction:
                    validation["warnings"].append(f"Existing {signal['signal']} position on {symbol}")

            # Check confidence threshold
            confidence = signal.get("confidence", 0)
            if confidence < 50:
                validation["reason"] = f"Low confidence signal ({confidence:.1f}%)"
                return validation
            elif confidence < 70:
                validation["warnings"].append(f"Medium confidence ({confidence:.1f}%)")

            # Check account margin
            margin_level = account_info.get("margin_level", 0)
            if margin_level > 0 and margin_level < 200:  # Less than 200% margin level
                validation["warnings"].append(f"Low margin level: {margin_level:.1f}%")

            # All checks passed
            validation["allowed"] = True
            validation["reason"] = "Trade validated"

            return validation

        except Exception as e:
            self.logger.error(f"❌ Trade validation error: {str(e)}")
            return {
                "allowed": False,
                "reason": f"Validation error: {str(e)}",
                "warnings": []
            }

    def calculate_position_size(self, signal: Dict[str, Any], account_balance: float, 
                               symbol_info: Dict[str, Any], stop_loss_pips: float) -> float:
        """
        Calculate optimal position size based on risk parameters.

        Args:
            signal: Trading signal
            account_balance: Current account balance
            symbol_info: Symbol information
            stop_loss_pips: Stop loss in pips

        Returns:
            Calculated lot size
        """
        try:
            # Get risk parameters
            confidence = signal.get("confidence", 50) / 100.0
            adjusted_risk = self.risk_per_trade * confidence  # Adjust risk based on confidence

            # Calculate risk amount
            risk_amount = account_balance * adjusted_risk

            # Get symbol info
            point = symbol_info.get("point", 0.00001)
            pip_value = symbol_info.get("pip_value", 1.0)
            min_lot = symbol_info.get("volume_min", 0.01)
            max_lot = symbol_info.get("volume_max", 1.0)
            lot_step = symbol_info.get("volume_step", 0.01)

            # Calculate lot size
            if stop_loss_pips > 0 and pip_value > 0:
                lot_size = risk_amount / (stop_loss_pips * pip_value)
            else:
                lot_size = min_lot

            # Apply limits
            lot_size = max(min_lot, min(lot_size, max_lot))
            lot_size = round(lot_size / lot_step) * lot_step

            self.logger.debug(f"Position sizing: Risk={adjusted_risk:.3f}, Amount=${risk_amount:.2f}, Lots={lot_size:.3f}")

            return lot_size

        except Exception as e:
            self.logger.error(f"❌ Position sizing error: {str(e)}")
            return symbol_info.get("volume_min", 0.01)

    def update_session_stats(self, account_info: Dict[str, Any]) -> None:
        """Update session statistics."""
        try:
            current_equity = account_info.get("equity", 0)
            self.max_equity = max(self.max_equity, current_equity)

            # Calculate daily profit
            self.daily_profit = current_equity - self.session_start_balance

        except Exception as e:
            self.logger.error(f"❌ Session stats update error: {str(e)}")

    def on_trade_executed(self, trade_result: Dict[str, Any]) -> None:
        """Record a trade execution."""
        try:
            self.daily_trades += 1

            trade_record = {
                "timestamp": datetime.now(),
                "order": trade_result.get("order"),
                "deal": trade_result.get("deal"),
                "volume": trade_result.get("volume")
            }

            self.trade_history.append(trade_record)

            self.logger.info(f"📊 Trade recorded: {self.daily_trades}/{self.max_daily_trades} daily trades")

        except Exception as e:
            self.logger.error(f"❌ Trade recording error: {str(e)}")

    def emergency_stop_check(self, account_info: Dict[str, Any]) -> bool:
        """
        Check if emergency stop conditions are met.

        Returns:
            True if emergency stop should be triggered
        """
        try:
            current_equity = account_info.get("equity", 0)
            current_balance = account_info.get("balance", 0)

            # Check critical drawdown
            if self.max_equity > 0:
                drawdown = (self.max_equity - current_equity) / self.max_equity
                if drawdown >= self.max_drawdown * 0.9:  # 90% of max drawdown
                    self.logger.critical(f"🚨 CRITICAL DRAWDOWN: {drawdown*100:.1f}%")
                    return True

            # Check daily loss
            if self.session_start_balance > 0:
                daily_loss = (self.session_start_balance - current_balance) / self.session_start_balance
                if daily_loss >= self.max_daily_loss * 0.9:  # 90% of max daily loss
                    self.logger.critical(f"🚨 CRITICAL DAILY LOSS: {daily_loss*100:.1f}%")
                    return True

            # Check margin level
            margin_level = account_info.get("margin_level", 1000)
            if margin_level > 0 and margin_level < 100:  # Critical margin level
                self.logger.critical(f"🚨 CRITICAL MARGIN LEVEL: {margin_level:.1f}%")
                return True

            return False

        except Exception as e:
            self.logger.error(f"❌ Emergency stop check error: {str(e)}")
            return True  # Err on the side of caution

    def get_risk_report(self) -> Dict[str, Any]:
        """Get comprehensive risk report."""
        try:
            current_time = datetime.now()
            session_duration = current_time - self.session_start_time

            report = {
                "session_duration": str(session_duration).split('.')[0],
                "session_start_balance": self.session_start_balance,
                "max_equity": self.max_equity,
                "daily_trades": self.daily_trades,
                "max_daily_trades": self.max_daily_trades,
                "daily_profit": self.daily_profit,
                "daily_profit_percent": (self.daily_profit / self.session_start_balance * 100) if self.session_start_balance > 0 else 0,
                "trades_remaining": max(0, self.max_daily_trades - self.daily_trades),
                "risk_parameters": {
                    "risk_per_trade": self.risk_per_trade,
                    "max_daily_loss": self.max_daily_loss,
                    "max_drawdown": self.max_drawdown,
                    "max_positions": self.max_positions,
                    "max_spread": self.max_spread
                }
            }

            return report

        except Exception as e:
            self.logger.error(f"❌ Risk report error: {str(e)}")
            return {"error": str(e)}