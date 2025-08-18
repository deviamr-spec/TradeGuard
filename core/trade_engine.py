"""
Trade Engine Module.
Coordinates strategy signals, risk management, and trade execution.
"""

import threading
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    # MT5 not available - using mock constants
    MT5_AVAILABLE = False
    class MockMT5:
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TIME_GTC = 0
        ORDER_FILLING_IOC = 1
        TRADE_RETCODE_DONE = 10009
        POSITION_TYPE_BUY = 0
        POSITION_TYPE_SELL = 1
    mt5 = MockMT5()

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
        # Fix: Initialize ReportingManager with proper parameters
        self.reporting = ReportingManager(mt5_client, {})

        # Strategy management
        self.available_strategies = {
            "Scalping": ScalpingStrategy,
            # Future strategies can be added here
        }
        self.current_strategy_name = "Scalping"
        self.strategy_switch_lock = threading.Lock()

        # Engine state
        self.running = False
        self.trading_enabled = True  # AUTO-ENABLE TRADING BY DEFAULT
        self.engine_thread = None
        self.last_update = datetime.now()

        # Trading parameters
        self.symbols = config.get("trading.symbols", ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"])
        self.timeframe = config.get("trading.timeframe", "M1")
        self.update_interval = 2.0  # Increase to 2 seconds for better stability

        # Position tracking
        self.active_positions = {}
        self.pending_signals = {}
        self.last_signal_time = {}

        # Auto-trading configuration
        self.auto_tp_sl_enabled = True
        self.auto_order_enabled = True
        self.signal_confidence_threshold = 65.0  # Minimum confidence for auto trading

        # Thread safety
        self.trade_lock = threading.Lock()

        self.logger.info(f"⚙️ Trade Engine initialized:")
        self.logger.info(f"   Symbols: {self.symbols}")
        self.logger.info(f"   Timeframe: {self.timeframe}")
        self.logger.info(f"   Update interval: {self.update_interval}s")
        self.logger.info(f"   Auto-trading: {'ENABLED' if self.trading_enabled else 'DISABLED'}")
        self.logger.info(f"   Auto TP/SL: {'ENABLED' if self.auto_tp_sl_enabled else 'DISABLED'}")

    def start(self) -> bool:
        """
        Start the trading engine.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            if self.running:
                self.logger.warning("⚠️ Trade engine already running")
                return True

            self.logger.info("🚀 Starting trading engine...")

            # Verify MT5 connection
            if not self.mt5_client.connected:
                self.logger.error("❌ MT5 not connected")
                return False

            # Initialize session balances for reporting
            account_info = self.mt5_client.get_account_info()
            if account_info:
                current_balance = account_info.get('balance', 0.0)
                self.reporting.session_start_balance = current_balance
                self.risk_manager.session_start_balance = current_balance
                self.risk_manager.daily_start_balance = current_balance
                self.risk_manager.peak_balance = current_balance

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

            # Close all positions if requested
            self._emergency_close_all_positions()

            self.logger.info("✅ Trade engine stopped")

        except Exception as e:
            self.logger.error(f"❌ Trade engine stop error: {str(e)}")

    def _engine_loop(self) -> None:
        """Main trading engine loop."""
        try:
            self.logger.info("🔄 Trade engine loop started")

            while self.running:
                try:
                    loop_start = time.time()

                    # Monitor connection health
                    connection_status = self.mt5_client.monitor_connection() if hasattr(self.mt5_client, 'monitor_connection') else {"connected": self.mt5_client.connected}
                    if not connection_status["healthy"]:
                        self.logger.warning("⚠️ MT5 connection unhealthy, attempting reconnection...")
                        if self.mt5_client.auto_reconnect():
                            self.logger.info("✅ Reconnection successful")
                        else:
                            self.logger.error("❌ Reconnection failed, continuing in offline mode")
                            time.sleep(self.update_interval)
                            continue

                    # Update account information
                    account_info = self.mt5_client.get_account_info()
                    if not account_info:
                        self.logger.error("❌ Failed to get account info in loop")
                        time.sleep(self.update_interval)
                        continue

                    # Update risk manager and reporting
                    self.risk_manager.update_session_stats(account_info)
                    self.reporting.add_equity_point(account_info["equity"])

                    # Check for emergency stop conditions
                    if self.risk_manager.emergency_stop_check(account_info):
                        self.logger.critical("🚨 EMERGENCY STOP TRIGGERED")
                        self.trading_enabled = False
                        self._emergency_close_all_positions()
                        continue

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
                        continue

                    # Get current tick data
                    tick_data = self.mt5_client.get_tick_data(symbol)
                    if not tick_data:
                        continue

                    # Generate signal
                    signal = self.strategy.generate_signal(df, symbol)
                    signal["tick_data"] = tick_data

                    self.last_signal_time[symbol] = datetime.now()

                    # Process signal if valid and meets confidence threshold
                    if signal["signal"] in ["BUY", "SELL"] and signal.get("confidence", 0) >= self.signal_confidence_threshold:
                        self.logger.info(f"🎯 Strong signal detected: {symbol} {signal['signal']} (Confidence: {signal['confidence']:.1f}%)")
                        self._execute_signal(signal, account_info, current_positions)
                    elif signal["signal"] in ["BUY", "SELL"]:
                        self.logger.debug(f"⚠️ Signal below threshold: {symbol} {signal['signal']} (Confidence: {signal['confidence']:.1f}% < {self.signal_confidence_threshold}%)")

                except Exception as e:
                    self.logger.error(f"❌ Signal processing error for {symbol}: {str(e)}")

        except Exception as e:
            self.logger.error(f"❌ Trading signals processing error: {str(e)}")

    def _execute_signal(self, signal: Dict[str, Any], account_info: Dict[str, Any],
                       positions: List[Dict[str, Any]]) -> None:
        """Execute a trading signal with enhanced validation."""
        try:
            with self.trade_lock:
                symbol = signal["symbol"]

                # Get symbol information with auto-detection
                symbol_info = self.mt5_client.get_symbol_info(symbol)
                if not symbol_info:
                    self.logger.error(f"❌ Failed to get symbol info for {symbol}")
                    return

                # Get actual symbol name after auto-detection
                actual_symbol = symbol_info.get("symbol", symbol)

                # Validate trade with risk manager
                validation = self.risk_manager.validate_trade(signal, account_info, positions, symbol_info)
                if not validation["allowed"]:
                    self.logger.info(f"🚫 Trade rejected for {actual_symbol}: {validation['reason']}")
                    return

                # Log warnings if any
                if validation["warnings"]:
                    self.logger.warning(f"⚠️ Trade warnings for {actual_symbol}: {', '.join(validation['warnings'])}")

                # Calculate position sizing with enhanced logic
                confidence = signal["confidence"] / 100.0
                lot_size, stop_loss, take_profit = self.strategy.calculate_position_size(
                    signal, account_info["balance"], symbol_info
                )

                # Get fresh tick data for actual symbol
                fresh_tick = self.mt5_client.get_tick_data(symbol)
                if not fresh_tick:
                    self.logger.error(f"❌ Cannot get fresh tick data for {actual_symbol}")
                    return

                current_price = fresh_tick["ask"] if signal["signal"] == "BUY" else fresh_tick["bid"]

                # Enhanced order request with proper symbol
                order_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": actual_symbol,  # Use actual detected symbol
                    "volume": lot_size,
                    "type": mt5.ORDER_TYPE_BUY if signal["signal"] == "BUY" else mt5.ORDER_TYPE_SELL,
                    "price": current_price,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": f"AutoBot {signal['signal']} C:{signal['confidence']:.0f}%",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }

                # Add SL/TP if calculated
                if stop_loss > 0:
                    order_request["sl"] = stop_loss
                if take_profit > 0:
                    order_request["tp"] = take_profit

                # Execute order with retry logic
                self.logger.info(f"📤 Executing {signal['signal']} order for {actual_symbol}: {lot_size} lots @ {current_price:.5f}")

                result = None
                retry_count = 3

                for attempt in range(retry_count):
                    result = self.mt5_client.place_order(
                        symbol=actual_symbol,
                        order_type=signal["signal"],
                        volume=lot_size,
                        price=current_price,
                        sl=stop_loss if stop_loss > 0 else None,
                        tp=take_profit if take_profit > 0 else None,
                        comment=f"AutoBot {signal['signal']} C:{signal['confidence']:.0f}%"
                    )
                    if result:
                        break
                    elif attempt < retry_count - 1:
                        self.logger.warning(f"⚠️ Order attempt {attempt + 1} failed, retrying...")
                        time.sleep(1)

                if result:
                    # Get order/ticket from result
                    order_ticket = result.get("ticket", result.get("order", 0))

                    # Log successful trade
                    trade_data = {
                        "symbol": actual_symbol,
                        "original_symbol": symbol,
                        "type": signal["signal"],
                        "volume": lot_size,
                        "price": current_price,
                        "sl": stop_loss,
                        "tp": take_profit,
                        "ticket": order_ticket,
                        "comment": order_request["comment"],
                        "confidence": signal["confidence"],
                        "market_context": signal.get("market_context", {})
                    }

                    self.reporting.log_trade(trade_data)
                    self.risk_manager.on_trade_executed(result)

                    # Track position with enhanced data
                    self.active_positions[order_ticket] = {
                        "symbol": actual_symbol,
                        "original_symbol": symbol,
                        "type": signal["signal"],
                        "volume": lot_size,
                        "entry_time": datetime.now(),
                        "entry_price": current_price,
                        "sl": stop_loss,
                        "tp": take_profit,
                        "confidence": signal["confidence"],
                        "signal_data": signal
                    }

                    self.logger.info(f"✅ Trade executed successfully: {actual_symbol} {signal['signal']} {lot_size} lots (Confidence: {signal['confidence']:.1f}%)")

                else:
                    self.logger.error(f"❌ Trade execution failed for {actual_symbol} after {retry_count} attempts")

        except Exception as e:
            self.logger.error(f"❌ Signal execution error: {str(e)}")
            import traceback
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")

    def _update_positions(self) -> None:
        """Update status of active positions."""
        try:
            current_positions = self.mt5_client.get_positions()
            current_tickets = [pos["ticket"] for pos in current_positions]

            # Check for closed positions
            closed_orders = []
            for order_id, position_data in self.active_positions.items():
                if order_id not in current_tickets:
                    # Position was closed
                    closed_orders.append(order_id)

                    # Try to get trade history to update outcome
                    from datetime import datetime, timedelta
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=1)
                    history = self.mt5_client.get_trade_history(start_date, end_date)
                    for trade in history:
                        # Check both ticket and order fields for matching
                        trade_ticket = trade.get("ticket", trade.get("order", 0))
                        if trade_ticket == order_id:
                            outcome_data = {
                                "exit_price": trade["price"],
                                "profit": trade["profit"],
                                "commission": trade.get("commission", 0),
                                "swap": trade.get("swap", 0)
                            }
                            self.reporting.update_trade_outcome(order_id, outcome_data)
                            break

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

    def enable_trading(self) -> None:
        """Enable automated trading."""
        self.trading_enabled = True
        self.logger.info("✅ Automated trading enabled")

    def disable_trading(self) -> None:
        """Disable automated trading."""
        self.trading_enabled = False
        self.logger.info("🛑 Automated trading disabled")

    def get_engine_status(self) -> Dict[str, Any]:
        """
        Get current engine status.

        Returns:
            Engine status dictionary
        """
        try:
            account_info = self.mt5_client.get_account_info() or {}
            positions = self.mt5_client.get_positions()

            status = {
                "running": self.running,
                "trading_enabled": self.trading_enabled,
                "last_update": self.last_update,
                "mt5_connected": self.mt5_client.connected,
                "account_info": account_info,
                "active_positions": len(positions),
                "tracked_positions": len(self.active_positions),
                "symbols_monitored": len(self.symbols),
                "strategy_stats": self.strategy.get_strategy_stats(),
                "risk_report": self.risk_manager.get_risk_report(),
                "performance_metrics": self.reporting.calculate_performance_metrics()
            }

            return status

        except Exception as e:
            self.logger.error(f"❌ Engine status error: {str(e)}")
            return {"error": str(e)}

    def force_close_position(self, ticket: int) -> bool:
        """
        Manually close a specific position.

        Args:
            ticket: Position ticket to close

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.mt5_client.close_position(ticket):
                self.logger.info(f"✅ Manually closed position: {ticket}")

                # Remove from tracking if exists
                if ticket in self.active_positions:
                    del self.active_positions[ticket]

                return True
            else:
                self.logger.error(f"❌ Failed to close position: {ticket}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Force close position error: {str(e)}")
            return False

    def switch_strategy(self, strategy_name: str) -> bool:
        """
        Dynamically switch trading strategy.

        Args:
            strategy_name: Name of the strategy to switch to

        Returns:
            bool: True if switch successful, False otherwise
        """
        try:
            with self.strategy_switch_lock:
                if strategy_name not in self.available_strategies:
                    self.logger.error(f"❌ Unknown strategy: {strategy_name}")
                    return False

                if strategy_name == self.current_strategy_name:
                    self.logger.info(f"ℹ️ Already using strategy: {strategy_name}")
                    return True

                self.logger.info(f"🔄 Switching strategy from {self.current_strategy_name} to {strategy_name}")

                # Create new strategy instance
                strategy_class = self.available_strategies[strategy_name]
                new_strategy = strategy_class()

                # Switch strategy
                old_strategy = self.strategy
                self.strategy = new_strategy
                self.current_strategy_name = strategy_name

                # Log switch completion
                self.logger.info(f"✅ Strategy switched to {strategy_name}")

                # Optional: Clear old signals to prevent conflicts
                self.pending_signals.clear()
                self.last_signal_time.clear()

                return True

        except Exception as e:
            self.logger.error(f"❌ Strategy switch error: {str(e)}")
            return False

    def get_available_strategies(self) -> List[str]:
        """
        Get list of available strategies.

        Returns:
            List of strategy names
        """
        return list(self.available_strategies.keys())

    def get_current_strategy_name(self) -> str:
        """
        Get current strategy name.

        Returns:
            Current strategy name
        """
        return self.current_strategy_name

    def update_trading_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Update trading parameters dynamically.

        Args:
            parameters: Dictionary of parameters to update

        Returns:
            bool: True if update successful
        """
        try:
            updated_params = []

            # Update symbols
            if "symbols" in parameters:
                symbols = parameters["symbols"]
                if isinstance(symbols, list):
                    self.update_trading_symbols(symbols)
                    updated_params.append("symbols")

            # Update timeframe
            if "timeframe" in parameters:
                timeframe = parameters["timeframe"]
                valid_timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
                if timeframe in valid_timeframes:
                    self.timeframe = timeframe
                    updated_params.append("timeframe")
                    self.logger.info(f"📊 Updated timeframe to {timeframe}")
                else:
                    self.logger.error(f"❌ Invalid timeframe: {timeframe}")

            # Update update interval
            if "update_interval" in parameters:
                interval = parameters["update_interval"]
                if isinstance(interval, (int, float)) and interval > 0:
                    self.update_interval = interval
                    updated_params.append("update_interval")
                    self.logger.info(f"⏱️ Updated interval to {interval}s")

            # Update strategy
            if "strategy" in parameters:
                strategy_name = parameters["strategy"]
                if self.switch_strategy(strategy_name):
                    updated_params.append("strategy")

            if updated_params:
                self.logger.info(f"✅ Updated parameters: {', '.join(updated_params)}")
                return True
            else:
                self.logger.warning("⚠️ No valid parameters to update")
                return False

        except Exception as e:
            self.logger.error(f"❌ Parameter update error: {str(e)}")
            return False

    def update_trading_symbols(self, symbols: List[str]) -> None:
        """
        Update list of trading symbols.

        Args:
            symbols: New list of symbols to trade
        """
        try:
            # Validate symbols
            valid_symbols = []
            for symbol in symbols:
                symbol_info = self.mt5_client.get_symbol_info(symbol)
                if symbol_info:
                    valid_symbols.append(symbol)
                else:
                    self.logger.warning(f"⚠️ Invalid symbol: {symbol}")

            if valid_symbols:
                self.symbols = valid_symbols
                self.logger.info(f"📊 Updated trading symbols: {self.symbols}")
            else:
                self.logger.error("❌ No valid symbols provided")

        except Exception as e:
            self.logger.error(f"❌ Symbol update error: {str(e)}")