"""
MetaTrader 5 client for handling all MT5 operations.
Enhanced with auto symbol detection and robust error handling.
"""

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    # MT5 not available (likely not on Windows)
    MT5_AVAILABLE = False
    mt5 = None
import pandas as pd
import numpy as np
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

from core.config import config
from utils.logging_setup import get_logger

class MT5Client:
    """MetaTrader 5 client for trading operations."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.connected = False
        self.account_info = None
        self.symbols_info = {}
        self.last_error = None
        self.validated_symbols = {}
        self.connection_attempts = 0
        self.consecutive_failures = 0
        self.last_connection_time = None
        self.last_health_check = None

    def connect(self) -> bool:
        """Connect to MetaTrader 5 terminal with enhanced validation and retry logic."""
        try:
            if not MT5_AVAILABLE:
                self.logger.error("❌ MetaTrader5 package not available - requires Windows with MT5 installed")
                self.last_error = "MetaTrader5 package not available"
                return False

            # Initialize connection tracking
            self.connection_attempts = 0
            max_attempts = 3
            retry_delay = 2  # seconds

            for attempt in range(max_attempts):
                self.connection_attempts = attempt + 1
                self.logger.info(f"🔄 Connection attempt {self.connection_attempts}/{max_attempts}")

                try:
                    # Shutdown any existing connection
                    if self.connected:
                        mt5.shutdown()
                        time.sleep(1)

                    self.logger.info("🔌 Connecting to MetaTrader 5...")

                    # Get connection credentials
                    credentials = config.get_mt5_credentials()

                    # Try different initialization methods
                    init_methods = [
                        lambda: mt5.initialize(),
                        lambda: mt5.initialize(path=credentials["path"]),
                        lambda: mt5.initialize(
                            path=credentials["path"],
                            login=credentials["login"] if credentials["login"] != 0 else None,
                            server=credentials["server"] if credentials["server"] else None,
                            password=credentials["password"] if credentials["password"] else None
                        ),
                    ]

                    connection_successful = False
                    for i, init_method in enumerate(init_methods):
                        try:
                            self.logger.info(f"🔄 Trying connection method {i + 1}...")

                            if init_method():
                                self.logger.info(f"✅ MT5 connected using method {i + 1}")
                                connection_successful = True
                                break
                            else:
                                error = mt5.last_error()
                                self.logger.warning(f"⚠️ Method {i + 1} failed: {error}")

                        except Exception as e:
                            self.logger.warning(f"⚠️ Method {i + 1} exception: {str(e)}")
                            continue

                    if not connection_successful:
                        raise ConnectionError("All initialization methods failed")

                    # Verify connection and get account info
                    if not self._verify_connection():
                        raise ConnectionError("Connection verification failed")

                    self.connected = True
                    self.last_connection_time = datetime.now()
                    self.consecutive_failures = 0
                    self.logger.info(f"✅ MT5 client connected successfully (attempt {self.connection_attempts})")
                    return True

                except Exception as e:
                    self.logger.warning(f"⚠️ Connection attempt {self.connection_attempts} failed: {str(e)}")
                    self.last_error = str(e)

                    if attempt < max_attempts - 1:
                        self.logger.info(f"🔄 Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff

            # All attempts failed
            self.connected = False
            self.consecutive_failures = getattr(self, 'consecutive_failures', 0) + 1
            self.logger.error(f"❌ All connection attempts failed ({max_attempts} attempts)")
            return False

        except Exception as e:
            self.logger.error(f"❌ Connection failed: {str(e)}")
            self.last_error = str(e)
            self.connected = False
            return False

    def is_connection_healthy(self) -> bool:
        """Check if MT5 connection is healthy."""
        try:
            if not self.connected:
                return False

            if not MT5_AVAILABLE:
                return False

            # Test connection with a simple call
            account_info = mt5.account_info()
            if not account_info:
                self.logger.warning("⚠️ Connection health check failed: No account info")
                self.connected = False
                return False

            # Check if we can get tick data for a common symbol
            tick = mt5.symbol_info_tick("EURUSD")
            if not tick:
                # Try alternative symbols if EURUSD is not available
                for test_symbol in ["GBPUSD", "USDJPY", "XAUUSD"]:
                    tick = mt5.symbol_info_tick(test_symbol)
                    if tick:
                        break
                else:
                    self.logger.warning("⚠️ Connection health check failed: No tick data available")
                    self.connected = False
                    return False

            # Update last successful health check time
            self.last_health_check = datetime.now()
            return True

        except Exception as e:
            self.logger.warning(f"⚠️ Connection health check error: {str(e)}")
            self.connected = False
            return False

    def auto_reconnect(self) -> bool:
        """Attempt automatic reconnection with exponential backoff."""
        try:
            if self.is_connection_healthy():
                return True

            self.logger.warning("🔄 Connection unhealthy, attempting auto-reconnection...")

            # Exponential backoff: 2, 4, 8, 16, 30 seconds
            backoff_delays = [2, 4, 8, 16, 30]

            for i, delay in enumerate(backoff_delays):
                self.logger.info(f"🔄 Reconnection attempt {i + 1}/{len(backoff_delays)} in {delay}s...")
                time.sleep(delay)

                if self.connect():
                    self.logger.info("✅ Auto-reconnection successful!")
                    return True

            self.logger.error("❌ Auto-reconnection failed after all attempts")
            return False

        except Exception as e:
            self.logger.exception(f"Auto-reconnection error: {e}")
            return False

    def monitor_connection(self) -> Dict[str, Any]:
        """
        Monitor connection status and return health information.

        Returns:
            Dict with connection status information
        """
        try:
            status = {
                "connected": self.connected,
                "healthy": False,
                "last_error": self.last_error,
                "consecutive_failures": getattr(self, 'consecutive_failures', 0),
                "connection_attempts": getattr(self, 'connection_attempts', 0),
                "last_connection_time": getattr(self, 'last_connection_time', None),
                "uptime_seconds": 0
            }

            if self.connected:
                status["healthy"] = self.is_connection_healthy()

                if hasattr(self, 'last_connection_time') and self.last_connection_time:
                    uptime = datetime.now() - self.last_connection_time
                    status["uptime_seconds"] = int(uptime.total_seconds())

            return status

        except Exception as e:
            self.logger.error(f"❌ Connection monitoring error: {str(e)}")
            return {
                "connected": False,
                "healthy": False,
                "error": str(e)
            }

    def _verify_connection(self) -> bool:
        """Verify MT5 connection and account status."""
        try:
            # Get account information
            self.account_info = mt5.account_info()
            if not self.account_info:
                self.logger.error("❌ Failed to get account information")
                return False

            # Log account details
            self.logger.info(f"📊 Account: {self.account_info.login}")
            self.logger.info(f"💰 Balance: ${self.account_info.balance:,.2f}")
            self.logger.info(f"📈 Equity: ${self.account_info.equity:,.2f}")
            self.logger.info(f"🏦 Server: {self.account_info.server}")

            # Check if auto trading is enabled
            if hasattr(self.account_info, 'trade_allowed'):
                if not self.account_info.trade_allowed:
                    self.logger.error("❌ Trading is not allowed on this account")
                    return False
                else:
                    self.logger.info("✅ Trading is allowed")

            return True

        except Exception as e:
            self.logger.error(f"❌ Connection verification failed: {str(e)}")
            return False

    def disconnect(self) -> None:
        """Disconnect from MetaTrader 5."""
        try:
            if self.connected:
                mt5.shutdown()
                self.connected = False
                self.logger.info("🔌 Disconnected from MT5")
        except Exception as e:
            self.logger.error(f"❌ Disconnect error: {str(e)}")

    def auto_detect_symbol(self, base_symbol: str) -> str:
        """Auto-detect the correct symbol name format with comprehensive variations."""
        try:
            if not self.connected:
                return base_symbol

            # Try the symbol as-is first
            symbol_info = mt5.symbol_info(base_symbol)
            if symbol_info and symbol_info.visible:
                return base_symbol

            # Comprehensive variations for different brokers
            variations = [
                base_symbol,
                base_symbol + "m",              # mini lots
                base_symbol + ".m",
                base_symbol + "_m",
                base_symbol + "pro",            # pro accounts
                base_symbol + ".pro",
                base_symbol + "_pro",
                base_symbol + "c",              # cent accounts
                base_symbol + ".c",
                base_symbol + "_c",
                base_symbol + "raw",            # raw spread
                base_symbol + ".raw",
                base_symbol + "_raw",
                base_symbol.lower(),            # lowercase
                base_symbol.upper(),            # uppercase
                f"{base_symbol[:3]}{base_symbol[3:]}.fx",  # FX suffix
                f"{base_symbol}#",              # Hash suffix
                f"#{base_symbol}",              # Hash prefix
            ]

            # Try each variation
            for variant in variations:
                try:
                    symbol_info = mt5.symbol_info(variant)
                    if symbol_info and symbol_info.visible:
                        self.logger.info(f"✅ Symbol detected: {base_symbol} -> {variant}")
                        return variant
                except:
                    continue

            # If not found, try to make symbol visible
            for variant in variations[:5]:  # Try most common variants
                try:
                    if mt5.symbol_select(variant, True):
                        symbol_info = mt5.symbol_info(variant)
                        if symbol_info:
                            self.logger.info(f"✅ Symbol activated: {base_symbol} -> {variant}")
                            return variant
                except:
                    continue

            self.logger.warning(f"⚠️ Symbol not found or unavailable: {base_symbol}")
            return base_symbol

        except Exception as e:
            self.logger.error(f"Symbol detection error: {e}")
            return base_symbol

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current account information.

        Returns:
            Dict with account information or None if failed
        """
        try:
            if not self.connected:
                return None

            account = mt5.account_info()
            if not account:
                return None

            return {
                "login": account.login,
                "balance": account.balance,
                "equity": account.equity,
                "margin": account.margin,
                "free_margin": account.margin_free,
                "margin_level": account.margin_level,
                "profit": account.profit,
                "server": account.server,
                "currency": account.currency,
                "trade_allowed": getattr(account, 'trade_allowed', True),
                "trade_mode": getattr(account, 'trade_mode', None)
            }

        except Exception as e:
            self.logger.error(f"❌ Failed to get account info: {str(e)}")
            return None

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get symbol information with auto-detection.

        Args:
            symbol: Trading symbol (e.g., 'EURUSD')

        Returns:
            Dict with symbol information or None if failed
        """
        try:
            if not self.connected:
                return None

            # Try auto-detection first
            actual_symbol = self.auto_detect_symbol(symbol)
            if not actual_symbol:
                return None

            # Cache symbol info
            if actual_symbol not in self.symbols_info:
                info = mt5.symbol_info(actual_symbol)
                if not info:
                    self.logger.error(f"❌ Symbol {actual_symbol} not found")
                    return None

                self.symbols_info[actual_symbol] = {
                    "symbol": info.name,
                    "digits": info.digits,
                    "point": info.point,
                    "spread": info.spread,
                    "volume_min": info.volume_min,
                    "volume_max": info.volume_max,
                    "volume_step": info.volume_step,
                    "contract_size": info.trade_contract_size,
                    "margin_required": info.margin_initial,
                    "pip_value": info.trade_tick_value,
                    "original_symbol": symbol
                }

            return self.symbols_info[actual_symbol]

        except Exception as e:
            self.logger.error(f"❌ Failed to get symbol info for {symbol}: {str(e)}")
            return None

    def get_tick_data(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Get current tick data for symbol with auto-detection.

        Args:
            symbol: Trading symbol

        Returns:
            Dict with tick data or None if failed
        """
        try:
            if not self.connected:
                return None

            # Get actual symbol
            actual_symbol = self.auto_detect_symbol(symbol)
            if not actual_symbol:
                return None

            tick = mt5.symbol_info_tick(actual_symbol)
            if not tick:
                return None

            return {
                "symbol": actual_symbol,
                "original_symbol": symbol,
                "time": tick.time,
                "bid": tick.bid,
                "ask": tick.ask,
                "spread": tick.ask - tick.bid,
                "volume": tick.volume
            }

        except Exception as e:
            self.logger.error(f"❌ Failed to get tick data for {symbol}: {str(e)}")
            return None

    def get_historical_data(self, symbol: str, timeframe: str, count: int) -> Optional[pd.DataFrame]:
        """
        Get historical price data with enhanced validation.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M1, M5, H1, etc.)
            count: Number of bars to retrieve

        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            if not self.connected:
                return None

            # Get actual symbol
            actual_symbol = self.auto_detect_symbol(symbol)
            if not actual_symbol:
                return None

            # Map timeframe string to MT5 constant
            timeframe_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }

            tf = timeframe_map.get(timeframe, mt5.TIMEFRAME_M1)

            # Get rates
            rates = mt5.copy_rates_from_pos(actual_symbol, tf, 0, count)
            if rates is None or len(rates) == 0:
                return None

            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)

            # Add tick_volume if not present (common in demo data)
            if 'tick_volume' not in df.columns:
                df['tick_volume'] = 100  # Default volume for demo mode

            # Add symbol metadata
            df.attrs['symbol'] = actual_symbol
            df.attrs['original_symbol'] = symbol
            df.attrs['timeframe'] = timeframe

            return df

        except Exception as e:
            self.logger.error(f"❌ Failed to get historical data for {symbol}: {str(e)}")
            return None

    def place_order(self, order_request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Place a trading order with enhanced error handling.

        Args:
            order_request: Order parameters

        Returns:
            Order result or None if failed
        """
        try:
            if not self.connected:
                self.logger.error("❌ Not connected to MT5")
                return None

            # Auto-detect symbol if needed
            if 'symbol' in order_request:
                actual_symbol = self.auto_detect_symbol(order_request['symbol'])
                if actual_symbol:
                    order_request['symbol'] = actual_symbol
                else:
                    self.logger.error(f"❌ Could not auto-detect symbol for {order_request['symbol']}")
                    return None

            # Send order
            result = mt5.order_send(order_request)
            if not result:
                error = mt5.last_error()
                self.logger.error(f"❌ Order failed: {error}")
                return {"success": False, "error_code": error, "error_description": "Order send failed"}

            # Check result
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"❌ Order rejected: {result.retcode} - {result.comment}")
                return {"success": False, "error_code": result.retcode, "error_description": result.comment}

            self.logger.info(f"✅ Order executed: {result.order} - {result.comment}")

            return {
                "success": True,
                "order": result.order,
                "deal": result.deal,
                "retcode": result.retcode,
                "comment": result.comment,
                "volume": result.volume,
                "price": result.price,
                "request_id": result.request_id
            }

        except Exception as e:
            self.logger.error(f"❌ Order placement failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def place_order_with_retry(self, symbol: str, order_type: str, volume: float,
                              price: float = 0.0, sl: float = 0.0, tp: float = 0.0,
                              max_retries: int = 3) -> Dict[str, Any]:
        """Place order with retry logic and enhanced error handling."""
        try:
            for attempt in range(max_retries):
                # Construct order request
                order_request = {
                    "symbol": symbol,
                    "volume": volume,
                    "type": order_type,
                    "price": price,
                    "sl": sl,
                    "tp": tp,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": "Trading Bot Order",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }

                result = self.place_order(order_request)

                if result and result.get('success', False):
                    return result

                error_code = result.get('error_code', 0) if result else 0

                # Handle specific error codes
                if error_code == 10006:  # No connection
                    self.logger.warning(f"🔄 Connection lost, attempting reconnection (attempt {attempt + 1})")
                    if self.auto_reconnect():
                        continue
                elif error_code == 10016:  # Invalid stops
                    self.logger.warning(f"⚠️ Invalid stops, adjusting... (attempt {attempt + 1})")
                    # Adjust stops and retry
                    adjusted_sl, adjusted_tp = self.adjust_stops(symbol, order_type, price, sl, tp)
                    if adjusted_sl != sl or adjusted_tp != tp:
                        sl, tp = adjusted_sl, adjusted_tp
                        continue # Retry with adjusted stops
                    else:
                        self.logger.error("❌ Failed to adjust stops, cannot place order.")
                        break
                elif error_code == 10019:  # Not enough money
                    self.logger.error("❌ Insufficient funds for trade")
                    break
                else:
                    self.logger.warning(f"⚠️ Order failed (attempt {attempt + 1}): {result.get('error_description', 'Unknown error')}")

                time.sleep(1)  # Wait before retry

            # If loop finishes without success
            if result and result.get('success', False):
                return result
            else:
                return {"success": False, "error": "Failed to place order after retries"}

        except Exception as e:
            self.logger.exception(f"Order placement error: {e}")
            return {"success": False, "error": str(e)}

    def adjust_stops(self, symbol: str, order_type: str, price: float,
                    sl: float, tp: float) -> tuple:
        """Adjust stop loss and take profit to valid levels."""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                self.logger.error(f"Symbol info not available for {symbol}")
                return sl, tp

            # Ensure symbol_info has the required attributes
            if not all(hasattr(symbol_info, attr) for attr in ['trade_stops_level', 'point']):
                self.logger.error(f"Symbol info incomplete for {symbol}")
                return sl, tp

            min_distance_points = symbol_info.trade_stops_level
            min_distance = min_distance_points * symbol_info.point

            # Ensure price is valid before calculations
            if price == 0.0:
                 # Try to get tick data if price is not provided
                 tick_data = self.get_tick_data(symbol)
                 if tick_data:
                     price = tick_data['ask'] if order_type in [mt5.ORDER_TYPE_BUY, "BUY"] else tick_data['bid']
                 else:
                     self.logger.error(f"Cannot determine price for stop adjustment for {symbol}")
                     return sl, tp


            # Adjust Stop Loss
            if sl > 0:
                if order_type in [mt5.ORDER_TYPE_BUY, "BUY"]:
                    if (price - sl) < min_distance:
                        sl = price - min_distance
                else:  # SELL
                    if (sl - price) < min_distance:
                        sl = price + min_distance

            # Adjust Take Profit
            if tp > 0:
                if order_type in [mt5.ORDER_TYPE_BUY, "BUY"]:
                    if (tp - price) < min_distance:
                        tp = price + min_distance
                else:  # SELL
                    if (price - tp) < min_distance:
                        tp = price - min_distance

            # Ensure SL/TP are not zero if they were valid initially
            if sl > 0 and (price - sl) < 0: sl = 0.0
            if tp > 0 and (tp - price) < 0: tp = 0.0

            return sl, tp

        except Exception as e:
            self.logger.error(f"Stop adjustment error for {symbol}: {e}")
            return sl, tp

    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions.

        Returns:
            List of position dictionaries
        """
        try:
            if not self.connected:
                self.logger.warning("Not connected, cannot get positions.")
                return []

            positions = mt5.positions_get()
            if not positions:
                return []

            result = []
            for pos in positions:
                result.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                    "volume": pos.volume,
                    "price_open": pos.price_open,
                    "price_current": pos.price_current,
                    "profit": pos.profit,
                    "swap": pos.swap,
                    "commission": pos.commission,
                    "time": pos.time,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "comment": pos.comment,
                    "magic": pos.magic
                })

            return result

        except Exception as e:
            self.logger.error(f"❌ Failed to get positions: {str(e)}")
            return []

    def close_position(self, ticket: int) -> bool:
        """
        Close a position by ticket.

        Args:
            ticket: Position ticket

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.connected:
                self.logger.warning("Not connected, cannot close position.")
                return False

            # Get position info
            position_data = mt5.positions_get(ticket=ticket)
            if not position_data:
                self.logger.error(f"❌ Position {ticket} not found")
                return False

            position = position_data[0]

            # Prepare close request
            close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": close_type,
                "position": ticket,
                "deviation": 20,
                "magic": position.magic, # Use original magic number
                "comment": "Close by bot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Send close request
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.logger.info(f"✅ Position {ticket} closed successfully")
                return True
            else:
                error = result.comment if result else mt5.last_error()
                self.logger.error(f"❌ Failed to close position {ticket}: {error}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Close position error: {str(e)}")
            return False

    def get_trade_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get trade history for the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of trade history records
        """
        try:
            if not self.connected:
                self.logger.warning("Not connected, cannot get trade history.")
                return []

            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)

            # Get deals
            deals = mt5.history_deals_get(from_date, to_date)
            if not deals:
                return []

            result = []
            for deal in deals:
                result.append({
                    "ticket": deal.ticket,
                    "order": deal.order,
                    "time": deal.time,
                    "symbol": deal.symbol,
                    "type": "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL",
                    "volume": deal.volume,
                    "price": deal.price,
                    "profit": deal.profit,
                    "swap": deal.swap,
                    "commission": deal.commission,
                    "comment": deal.comment,
                    "magic": deal.magic
                })

            return result

        except Exception as e:
            self.logger.error(f"❌ Failed to get trade history: {str(e)}")
            return []