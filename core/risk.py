"""
Risk Management Module.
Handles position sizing, drawdown control, and risk validation.
"""

import math
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

from core.config import config
from utils.logging_setup import get_logger

class RiskManager:
    """Comprehensive risk management for trading operations."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Risk parameters from config
        self.risk_per_trade = config.get("risk.risk_per_trade", 0.01)
        self.max_daily_loss = config.get("risk.max_daily_loss", 0.05)
        self.max_drawdown = config.get("risk.max_drawdown", 0.10)
        self.max_spread = config.get("risk.max_spread", 2.0)
        self.min_lot_size = config.get("risk.min_lot_size", 0.01)
        self.max_lot_size = config.get("risk.max_lot_size", 1.0)
        self.max_positions = config.get("trading.max_positions", 5)
        self.max_daily_trades = config.get("trading.max_daily_trades", 50)
        
        # Risk tracking
        self.daily_stats = {}
        self.session_start_balance = 0.0
        self.max_session_equity = 0.0
        self.daily_trade_count = 0
        self.risk_violations = []
        
        self.logger.info(f"🛡️ Risk Manager initialized:")
        self.logger.info(f"   Risk per trade: {self.risk_per_trade * 100:.1f}%")
        self.logger.info(f"   Max daily loss: {self.max_daily_loss * 100:.1f}%")
        self.logger.info(f"   Max drawdown: {self.max_drawdown * 100:.1f}%")
        self.logger.info(f"   Max positions: {self.max_positions}")
    
    def initialize_session(self, starting_balance: float) -> None:
        """
        Initialize risk tracking for new trading session.
        
        Args:
            starting_balance: Starting account balance
        """
        try:
            self.session_start_balance = starting_balance
            self.max_session_equity = starting_balance
            self.daily_trade_count = 0
            self.daily_stats = {
                "date": datetime.now().date(),
                "start_balance": starting_balance,
                "trades": 0,
                "profit": 0.0,
                "max_equity": starting_balance,
                "max_drawdown": 0.0,
                "violations": []
            }
            
            self.logger.info(f"🛡️ Risk session initialized with balance: ${starting_balance:,.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ Risk session initialization error: {str(e)}")
    
    def calculate_lot_size(self, account_balance: float, symbol_info: Dict[str, Any], 
                          stop_loss_pips: float, confidence: float = 1.0) -> float:
        """
        Calculate optimal lot size based on risk parameters.
        
        Args:
            account_balance: Current account balance
            symbol_info: Symbol information
            stop_loss_pips: Stop loss in pips
            confidence: Signal confidence (0.0-1.0)
            
        Returns:
            Calculated lot size
        """
        try:
            if stop_loss_pips <= 0:
                self.logger.warning("⚠️ Invalid stop loss pips, using minimum lot size")
                return self.min_lot_size
            
            # Adjust risk based on confidence
            adjusted_risk = self.risk_per_trade * confidence
            risk_amount = account_balance * adjusted_risk
            
            # Get symbol specifications
            pip_value = symbol_info.get("pip_value", 1.0)
            min_lot = symbol_info.get("volume_min", 0.01)
            max_lot = symbol_info.get("volume_max", 1.0)
            lot_step = symbol_info.get("volume_step", 0.01)
            
            # Calculate lot size
            total_risk = stop_loss_pips * pip_value
            if total_risk <= 0:
                return min_lot
                
            lot_size = risk_amount / total_risk
            
            # Apply constraints
            lot_size = max(min_lot, min(lot_size, max_lot))
            lot_size = max(min_lot, min(lot_size, self.max_lot_size))
            
            # Round to lot step
            lot_size = math.floor(lot_size / lot_step) * lot_step
            
            # Final validation
            if lot_size < min_lot:
                lot_size = min_lot
                
            self.logger.debug(f"📊 Calculated lot size: {lot_size} (Risk: ${risk_amount:.2f}, Confidence: {confidence:.2f})")
            
            return lot_size
            
        except Exception as e:
            self.logger.error(f"❌ Lot size calculation error: {str(e)}")
            return self.min_lot_size
    
    def validate_trade(self, signal: Dict[str, Any], account_info: Dict[str, Any], 
                      positions: List[Dict[str, Any]], symbol_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate if trade should be executed based on risk parameters.
        
        Args:
            signal: Trading signal
            account_info: Current account information
            positions: Current open positions
            symbol_info: Symbol information
            
        Returns:
            Validation result with allowed flag and reason
        """
        try:
            validation = {
                "allowed": True,
                "reason": "Trade approved",
                "warnings": [],
                "risk_score": 0.0
            }
            
            current_balance = account_info.get("balance", 0.0)
            current_equity = account_info.get("equity", 0.0)
            symbol = signal["symbol"]
            
            # Check daily trade limit
            if self.daily_trade_count >= self.max_daily_trades:
                validation["allowed"] = False
                validation["reason"] = f"Daily trade limit reached ({self.max_daily_trades})"
                return validation
            
            # Check maximum positions
            if len(positions) >= self.max_positions:
                validation["allowed"] = False
                validation["reason"] = f"Maximum positions limit reached ({self.max_positions})"
                return validation
            
            # Check for existing position in same symbol
            existing_positions = [p for p in positions if p["symbol"] == symbol]
            if existing_positions:
                validation["warnings"].append(f"Existing position in {symbol}")
                validation["risk_score"] += 0.2
            
            # Check daily loss limit
            if self.session_start_balance > 0:
                daily_loss = (self.session_start_balance - current_equity) / self.session_start_balance
                if daily_loss > self.max_daily_loss:
                    validation["allowed"] = False
                    validation["reason"] = f"Daily loss limit exceeded ({daily_loss*100:.1f}% > {self.max_daily_loss*100:.1f}%)"
                    return validation
                    
                # Warning if approaching daily loss limit
                if daily_loss > self.max_daily_loss * 0.8:
                    validation["warnings"].append(f"Approaching daily loss limit ({daily_loss*100:.1f}%)")
                    validation["risk_score"] += 0.3
            
            # Check maximum drawdown
            if self.max_session_equity > 0:
                current_drawdown = (self.max_session_equity - current_equity) / self.max_session_equity
                if current_drawdown > self.max_drawdown:
                    validation["allowed"] = False
                    validation["reason"] = f"Maximum drawdown exceeded ({current_drawdown*100:.1f}% > {self.max_drawdown*100:.1f}%)"
                    return validation
                    
                # Warning if approaching max drawdown
                if current_drawdown > self.max_drawdown * 0.8:
                    validation["warnings"].append(f"Approaching max drawdown ({current_drawdown*100:.1f}%)")
                    validation["risk_score"] += 0.4
            
            # Check spread
            tick_data = signal.get("tick_data")
            if tick_data:
                spread = tick_data.get("spread", 0.0)
                spread_pips = spread * 100000  # Convert to pips for major pairs
                
                if spread_pips > self.max_spread:
                    validation["allowed"] = False
                    validation["reason"] = f"Spread too high ({spread_pips:.1f} pips > {self.max_spread} pips)"
                    return validation
                    
                # Warning for high spread
                if spread_pips > self.max_spread * 0.7:
                    validation["warnings"].append(f"High spread ({spread_pips:.1f} pips)")
                    validation["risk_score"] += 0.1
            
            # Check margin requirements
            free_margin = account_info.get("free_margin", 0.0)
            required_margin = symbol_info.get("margin_required", 0.0)
            
            if required_margin > 0 and free_margin < required_margin * 2:  # 200% margin safety
                validation["allowed"] = False
                validation["reason"] = f"Insufficient margin (Required: ${required_margin:.2f}, Available: ${free_margin:.2f})"
                return validation
            
            # Check signal confidence
            confidence = signal.get("confidence", 0.0)
            if confidence < 60.0:  # Minimum confidence threshold
                validation["allowed"] = False
                validation["reason"] = f"Signal confidence too low ({confidence:.1f}% < 60%)"
                return validation
            
            # Risk score adjustments
            if confidence < 75.0:
                validation["warnings"].append(f"Moderate signal confidence ({confidence:.1f}%)")
                validation["risk_score"] += 0.1
            
            # Market conditions check
            market_analysis = signal.get("market_analysis", {})
            volatility = market_analysis.get("volatility", 0.0)
            
            if volatility > 2.0:  # Very high volatility
                validation["warnings"].append(f"High market volatility ({volatility:.1f}%)")
                validation["risk_score"] += 0.2
            elif volatility < 0.1:  # Very low volatility
                validation["warnings"].append(f"Low market volatility ({volatility:.1f}%)")
                validation["risk_score"] += 0.1
            
            # Final risk assessment
            if validation["risk_score"] > 0.8:
                validation["allowed"] = False
                validation["reason"] = f"High risk score ({validation['risk_score']:.2f})"
            elif validation["risk_score"] > 0.5:
                validation["warnings"].append(f"Elevated risk score ({validation['risk_score']:.2f})")
            
            # Log validation result
            if not validation["allowed"]:
                self.logger.warning(f"⚠️ Trade validation failed for {symbol}: {validation['reason']}")
                self._log_risk_violation(symbol, validation["reason"])
            elif validation["warnings"]:
                self.logger.info(f"🟡 Trade validation passed for {symbol} with warnings: {', '.join(validation['warnings'])}")
            else:
                self.logger.debug(f"✅ Trade validation passed for {symbol}")
            
            return validation
            
        except Exception as e:
            self.logger.error(f"❌ Trade validation error: {str(e)}")
            return {
                "allowed": False,
                "reason": f"Validation error: {str(e)}",
                "warnings": [],
                "risk_score": 1.0
            }
    
    def _log_risk_violation(self, symbol: str, reason: str) -> None:
        """Log risk violation for analysis."""
        violation = {
            "timestamp": datetime.now(),
            "symbol": symbol,
            "reason": reason
        }
        self.risk_violations.append(violation)
        
        # Keep only recent violations (last 100)
        if len(self.risk_violations) > 100:
            self.risk_violations = self.risk_violations[-100:]
    
    def update_session_stats(self, account_info: Dict[str, Any]) -> None:
        """
        Update session risk statistics.
        
        Args:
            account_info: Current account information
        """
        try:
            current_equity = account_info.get("equity", 0.0)
            
            # Update maximum equity
            if current_equity > self.max_session_equity:
                self.max_session_equity = current_equity
            
            # Update daily stats
            if self.session_start_balance > 0:
                current_profit = current_equity - self.session_start_balance
                current_drawdown = (self.max_session_equity - current_equity) / self.max_session_equity
                
                self.daily_stats.update({
                    "current_equity": current_equity,
                    "profit": current_profit,
                    "profit_pct": (current_profit / self.session_start_balance) * 100,
                    "max_equity": self.max_session_equity,
                    "current_drawdown": current_drawdown,
                    "max_drawdown": max(self.daily_stats.get("max_drawdown", 0.0), current_drawdown),
                    "trades": self.daily_trade_count
                })
            
        except Exception as e:
            self.logger.error(f"❌ Session stats update error: {str(e)}")
    
    def on_trade_executed(self, trade_result: Dict[str, Any]) -> None:
        """
        Handle post-trade risk tracking.
        
        Args:
            trade_result: Trade execution result
        """
        try:
            self.daily_trade_count += 1
            
            # Log trade for risk analysis
            self.logger.info(f"📊 Trade executed #{self.daily_trade_count}: {trade_result.get('symbol', 'Unknown')}")
            
            # Check if approaching limits
            if self.daily_trade_count >= self.max_daily_trades * 0.9:
                self.logger.warning(f"⚠️ Approaching daily trade limit: {self.daily_trade_count}/{self.max_daily_trades}")
            
        except Exception as e:
            self.logger.error(f"❌ Post-trade risk tracking error: {str(e)}")
    
    def get_risk_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive risk report.
        
        Returns:
            Risk report dictionary
        """
        try:
            report = {
                "session_stats": self.daily_stats.copy(),
                "risk_parameters": {
                    "risk_per_trade": self.risk_per_trade,
                    "max_daily_loss": self.max_daily_loss,
                    "max_drawdown": self.max_drawdown,
                    "max_positions": self.max_positions,
                    "max_daily_trades": self.max_daily_trades
                },
                "current_status": {
                    "daily_trades": self.daily_trade_count,
                    "trades_remaining": max(0, self.max_daily_trades - self.daily_trade_count),
                    "session_start_balance": self.session_start_balance,
                    "max_session_equity": self.max_session_equity
                },
                "violations": {
                    "total_violations": len(self.risk_violations),
                    "recent_violations": [v for v in self.risk_violations 
                                        if (datetime.now() - v["timestamp"]).total_seconds() < 3600]
                }
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Risk report generation error: {str(e)}")
            return {"error": str(e)}
    
    def emergency_stop_check(self, account_info: Dict[str, Any]) -> bool:
        """
        Check if emergency stop should be triggered.
        
        Args:
            account_info: Current account information
            
        Returns:
            True if emergency stop should be triggered
        """
        try:
            if self.session_start_balance <= 0:
                return False
                
            current_equity = account_info.get("equity", 0.0)
            
            # Check for catastrophic loss
            loss_pct = (self.session_start_balance - current_equity) / self.session_start_balance
            if loss_pct > self.max_daily_loss * 1.5:  # 150% of max daily loss
                self.logger.critical(f"🚨 EMERGENCY STOP: Catastrophic loss {loss_pct*100:.1f}%")
                return True
            
            # Check for rapid drawdown
            if self.max_session_equity > 0:
                drawdown = (self.max_session_equity - current_equity) / self.max_session_equity
                if drawdown > self.max_drawdown * 1.2:  # 120% of max drawdown
                    self.logger.critical(f"🚨 EMERGENCY STOP: Excessive drawdown {drawdown*100:.1f}%")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Emergency stop check error: {str(e)}")
            return True  # Trigger stop on error for safety
