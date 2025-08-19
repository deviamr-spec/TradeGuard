"""
Trade Engine Module.
Coordinates strategy signals, risk management, and trade execution.
Enhanced with demo mode support and comprehensive error handling.
"""

import threading
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from core.config import config
from core.mt5_client import MT5Client
from core.strategy.scalping import ScalpingStrategy
from core.risk import RiskManager
from core.reporting import ReportingManager
from utils.logging_setup import get_logger

class TradeEngine:
    """Main trading engine coordinating all trading operations."""

    def __init__(self, mt5_client: MT5Client):
        self.logger = get_logger(__name__)

        # Core components
        self.mt5_client = mt5_client
        self.strategy = ScalpingStrategy()
        self.risk_manager = RiskManager()
        self.reporting = ReportingManager(mt5_client, {})

        # Engine state
        self.running = False
        self.trading_enabled = True
        self.engine_thread = None
        self.last_update = datetime.now()

        # Trading parameters
        self.symbols = config.get("trading.symbols", ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"])
        self.timeframe = config.get("trading.timeframe", "M1")
        self.update_interval = 3.0

        # Position tracking
        self.active_positions = {}
        self.pending_signals = {}
        self.last_signal_time = {}

        # Auto-trading configuration
        self.auto_tp_sl_enabled = True
        self.auto_order_enabled = True
        self.signal_confidence_threshold = 60.0

        # Thread safety
        self.trade_lock = threading.Lock()

        # Initialize session balances
        try:
            account_info = self.mt5_client.get_account_info()
            if account_info:
                balance = account_info.get('balance', 10000.0)
                self.reporting.session_start_balance = balance
                self.risk_manager.session_start_balance = balance
                self.risk_manager.daily_start_balance = balance
                self.risk_manager.peak_balance = balance
        except Exception as e:
            self.logger.error(f"❌ Balance initialization error: {str(e)}")

        self.logger.info(f"⚙️ Trade Engine initialized:")
        self.logger.info(f"   Symbols: {self.symbols}")
        self.logger.info(f"   Timeframe: {self.timeframe}")
        self.logger.info(f"   Update interval: {self.update_interval}s")
        self.logger.info(f"   Demo mode: {getattr(self.mt5_client, 'demo_mode', False)}")

    def start(self) -> bool:
        """Start the trading engine."""
        try:
            if self.running:
                self.logger.warning("⚠️ Trade engine already running")
                return True

            self.logger.info("🚀 Starting trading engine...")

            # Verify connection
            if not self.mt5_client.connected:
                self.logger.error("❌ MT5 not connected")
                return False

            # Initialize components
            self.running = True
            self.last_update = datetime.now()

            # Start engine thread
            self.engine_thread = threading.Thread(target=self._engine_loop, daemon=True)
            self.engine_thread.start()

            self.logger.info("✅ Trade engine started successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to start trade engine: {str(e)}")
            return False

    def stop(self) -> None:
        """Stop the trading engine."""
        try:
            self.logger.info("🛑 Stopping trade engine...")

            self.running = False
            self.trading_enabled = False

            # Wait for thread to finish
            if self.engine_thread and self.engine_thread.is_alive():
                self.engine_thread.join(timeout=5.0)

            self.logger.info("✅ Trade engine stopped")

        except Exception as e:
            self.logger.error(f"❌ Trade engine stop error: {str(e)}")

    def _engine_loop(self) -> None:
        """Main trading engine loop with enhanced error handling."""
        try:
            self.logger.info("🔄 Trade engine loop started")

            while self.running:
                try:
                    loop_start = time.time()

                    # Monitor connection health (less frequent to prevent spam)
                    current_time = datetime.now()
                    if hasattr(self.mt5_client, 'last_health_check'):
                        time_since_check = (current_time - (self.mt5_client.last_health_check or current_time)).total_seconds()
                        if time_since_check > 30:  # Check health every 30 seconds
                            if hasattr(self.mt5_client, 'monitor_connection'):
                                connection_status = self.mt5_client.monitor_connection()
                                if not connection_status.get("healthy", False) and not connection_status.get("demo_mode", False):
                                    self.logger.warning("⚠️ Connection unhealthy, attempting reconnection...")
                                    if hasattr(self.mt5_client, 'auto_reconnect'):
                                        self.mt5_client.auto_reconnect()

                    # Update account information
                    account_info = self.mt5_client.get_account_info()
                    if not account_info:
                        self.logger.debug("⚠️ No account info available, using defaults")
                        account_info = {
                            "balance": 10000.0,
                            "equity": 10000.0,
                            "margin": 0.0,
                            "free_margin": 10000.0
                        }

                    # Update risk manager and reporting
                    try:
                        self.risk_manager.update_session_stats(account_info)
                        if hasattr(self.reporting, 'add_equity_point'):
                            self.reporting.add_equity_point(account_info["equity"])
                    except Exception as e:
                        self.logger.debug(f"Risk/reporting update error: {str(e)}")

                    # Check for emergency stop conditions
                    try:
                        if hasattr(self.risk_manager, 'emergency_stop_check'):
                            if self.risk_manager.emergency_stop_check(account_info):
                                self.logger.critical("🚨 EMERGENCY STOP TRIGGERED")
                                self.trading_enabled = False
                                self._emergency_close_all_positions()
                                continue
                    except Exception as e:
                        self.logger.debug(f"Emergency stop check error: {str(e)}")

                    # Update position status
                    self._update_positions()

                    # Process trading signals if trading is enabled
                    if self.trading_enabled:
                        self._process_trading_signals(account_info)

                    # Calculate loop timing
                    loop_duration = time.time() - loop_start
                    sleep_time = max(0, self.update_interval - loop_duration)

                    if sleep_time > 0:
                        time.sleep(sleep_time)

                    self.last_update = datetime.now()

                except Exception as e:
                    self.logger.error(f"❌ Engine loop error: {str(e)}")
                    time.sleep(self.update_interval)

        except Exception as e:
            self.logger.error(f"❌ Engine loop fatal error: {str(e)}")
        finally:
            self.logger.info("🔄 Trade engine loop ended")

    def _process_trading_signals(self, account_info: Dict[str, Any]) -> None:
        """Process trading signals for all symbols."""
        try:
            current_positions = self.mt5_client.get_positions()

            for symbol in self.symbols:
                try:
                    # Skip if too recent signal
                    last_signal = self.last_signal_time.get(symbol)
                    if last_signal and (datetime.now() - last_signal).seconds < 60:
                        continue

                    # Get market data
                    df = self.mt5_client.get_historical_data(symbol, self.timeframe, 100)
                    if df is None or len(df) < 50:
                        self.logger.debug(f"⚠️ Insufficient data for {symbol}")
                        continue

                    # Get current tick data
                    tick_data = self.mt5_client.get_tick_data(symbol)
                    if not tick_data:
                        self.logger.debug(f"⚠️ No tick data for {symbol}")
                        continue

                    # Generate signal
                    signal = self.strategy.generate_signal(df, symbol)
                    if not signal:
                        continue

                    signal["tick_data"] = tick_data
                    self.last_signal_time[symbol] = datetime.now()

                    # Process signal if valid and meets confidence threshold
                    confidence = signal.get("confidence", 0)
                    if signal["signal"] in ["BUY", "SELL"] and confidence >= self.signal_confidence_threshold:
                        self.logger.info(f"🎯 Strong signal detected: {symbol} {signal['signal']} (Confidence: {confidence:.1f}%)")
                        if self.auto_order_enabled:
                            self._execute_signal(signal, account_info, current_positions)
                    elif signal["signal"] in ["BUY", "SELL"]:
                        self.logger.debug(f"⚠️ Signal below threshold: {symbol} {signal['signal']} (Confidence: {confidence:.1f}% < {self.signal_confidence_threshold}%)")

                except Exception as e:
                    self.logger.error(f"❌ Signal processing error for {symbol}: {str(e)}")

        except Exception as e:
            self.logger.error(f"❌ Trading signals processing error: {str(e)}")

    def _execute_signal(self, signal: Dict[str, Any], account_info: Dict[str, Any],
                       positions: List[Dict[str, Any]]) -> None:
        """Execute a trading signal with comprehensive validation."""
        try:
            with self.trade_lock:
                symbol = signal["symbol"]

                # Get symbol information
                symbol_info = self.mt5_client.get_symbol_info(symbol)
                if not symbol_info:
                    self.logger.error(f"❌ Failed to get symbol info for {symbol}")
                    return

                # Validate trade with risk manager
                try:
                    validation = self.risk_manager.validate_trade(signal, account_info, positions, symbol_info)
                    if not validation["allowed"]:
                        self.logger.info(f"🚫 Trade rejected for {symbol}: {validation['reason']}")
                        return
                except Exception as e:
                    self.logger.warning(f"⚠️ Risk validation error, proceeding: {str(e)}")

                # Calculate position sizing
                try:
                    lot_size, stop_loss, take_profit = self.strategy.calculate_position_size(
                        signal, account_info["balance"], symbol_info
                    )
                except Exception as e:
                    self.logger.error(f"❌ Position sizing error: {str(e)}")
                    lot_size, stop_loss, take_profit = 0.01, 0.0, 0.0

                # Get fresh tick data
                fresh_tick = self.mt5_client.get_tick_data(symbol)
                if not fresh_tick:
                    self.logger.error(f"❌ Cannot get fresh tick data for {symbol}")
                    return

                current_price = fresh_tick["ask"] if signal["signal"] == "BUY" else fresh_tick["bid"]

                # Execute order
                self.logger.info(f"📤 Executing {signal['signal']} order for {symbol}: {lot_size} lots @ {current_price:.5f}")

                result = None
                retry_count = 3

                for attempt in range(retry_count):
                    try:
                        result = self.mt5_client.place_order(
                            symbol=symbol,
                            order_type=signal["signal"],
                            volume=lot_size,
                            price=current_price,
                            sl=stop_loss if stop_loss > 0 else None,
                            tp=take_profit if take_profit > 0 else None,
                            comment=f"AutoBot {signal['signal']} C:{signal['confidence']:.0f}%"
                        )
                        if result:
                            break
                    except Exception as e:
                        self.logger.warning(f"⚠️ Order attempt {attempt + 1} failed: {str(e)}")
                        if attempt < retry_count - 1:
                            time.sleep(1)

                if result:
                    order_ticket = result.get("ticket", result.get("order", 0))

                    # Log successful trade
                    trade_data = {
                        "symbol": symbol,
                        "type": signal["signal"],
                        "volume": lot_size,
                        "price": current_price,
                        "sl": stop_loss,
                        "tp": take_profit,
                        "ticket": order_ticket,
                        "comment": f"AutoBot {signal['signal']} C:{signal['confidence']:.0f}%",
                        "confidence": signal["confidence"]
                    }

                    try:
                        self.reporting.log_trade(trade_data)
                        if hasattr(self.risk_manager, 'on_trade_executed'):
                            self.risk_manager.on_trade_executed(result)
                    except Exception as e:
                        self.logger.debug(f"Trade logging error: {str(e)}")

                    # Track position
                    self.active_positions[order_ticket] = {
                        "symbol": symbol,
                        "type": signal["signal"],
                        "volume": lot_size,
                        "entry_time": datetime.now(),
                        "entry_price": current_price,
                        "sl": stop_loss,
                        "tp": take_profit,
                        "confidence": signal["confidence"]
                    }

                    self.logger.info(f"✅ Trade executed successfully: {symbol} {signal['signal']} {lot_size} lots")

                else:
                    self.logger.error(f"❌ Trade execution failed for {symbol}")

        except Exception as e:
            self.logger.error(f"❌ Signal execution error: {str(e)}")

    def _update_positions(self) -> None:
        """Update status of active positions."""
        try:
            current_positions = self.mt5_client.get_positions()
            current_tickets = [pos["ticket"] for pos in current_positions]

            # Check for closed positions
            closed_orders = []
            for order_id, position_data in self.active_positions.items():
                if order_id not in current_tickets:
                    closed_orders.append(order_id)
                    self.logger.info(f"📊 Position closed: {position_data['symbol']} {position_data['type']}")

            # Remove closed positions from tracking
            for order_id in closed_orders:
                del self.active_positions[order_id]

        except Exception as e:
            self.logger.error(f"❌ Position update error: {str(e)}")

    def _emergency_close_all_positions(self) -> None:
        """Emergency close all open positions."""
        try:
            self.logger.warning("🚨 Emergency closing all positions...")

            positions = self.mt5_client.get_positions()
            for position in positions:
                try:
                    if self.mt5_client.close_position(position["ticket"]):
                        self.logger.info(f"✅ Emergency closed: {position['symbol']}")
                    else:
                        self.logger.error(f"❌ Failed to close: {position['symbol']}")
                except Exception as e:
                    self.logger.error(f"❌ Emergency close error for {position['symbol']}: {str(e)}")

        except Exception as e:
            self.logger.error(f"❌ Emergency close all error: {str(e)}")

    def emergency_stop(self) -> None:
        """Emergency stop function."""
        try:
            self.trading_enabled = False
            self.running = False
            self._emergency_close_all_positions()
            self.logger.critical("🚨 EMERGENCY STOP EXECUTED")
        except Exception as e:
            self.logger.error(f"❌ Emergency stop error: {str(e)}")

    def enable_trading(self) -> None:
        """Enable automated trading."""
        self.trading_enabled = True
        self.logger.info("✅ Automated trading enabled")

    def disable_trading(self) -> None:
        """Disable automated trading."""
        self.trading_enabled = False
        self.logger.info("🛑 Automated trading disabled")

    def get_engine_status(self) -> Dict[str, Any]:
        """Get current engine status."""
        try:
            account_info = self.mt5_client.get_account_info() or {}
            positions = self.mt5_client.get_positions()

            status = {
                "running": self.running,
                "trading_enabled": self.trading_enabled,
                "last_update": self.last_update,
                "mt5_connected": self.mt5_client.connected,
                "demo_mode": getattr(self.mt5_client, 'demo_mode', False),
                "account_info": account_info,
                "active_positions": len(positions),
                "tracked_positions": len(self.active_positions),
                "symbols_monitored": len(self.symbols),
                "strategy_stats": getattr(self.strategy, 'get_strategy_stats', lambda: {})(),
                "risk_report": getattr(self.risk_manager, 'get_risk_report', lambda: {})(),
                "performance_metrics": getattr(self.reporting, 'calculate_performance_metrics', lambda: {})()
            }

            return status

        except Exception as e:
            self.logger.error(f"❌ Engine status error: {str(e)}")
            return {
                "error": str(e),
                "running": self.running,
                "trading_enabled": self.trading_enabled
            }

    def force_close_position(self, ticket: int) -> bool:
        """Manually close a specific position."""
        try:
            if self.mt5_client.close_position(ticket):
                self.logger.info(f"✅ Manually closed position: {ticket}")
                if ticket in self.active_positions:
                    del self.active_positions[ticket]
                return True
            else:
                self.logger.error(f"❌ Failed to close position: {ticket}")
                return False
        except Exception as e:
            self.logger.error(f"❌ Force close position error: {str(e)}")
            return False