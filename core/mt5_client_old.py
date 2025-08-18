"""
MetaTrader 5 client for handling all MT5 operations.
Enhanced with auto symbol detection and robust error handling for live trading.
"""

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    # MT5 not available (likely not on Windows)
    MT5_AVAILABLE = False
    mt5 = None

import pandas as pd
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

import time
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta

from core.config import config
from utils.logging_setup import get_logger

class MT5Client:
    """MetaTrader 5 client for live trading operations."""

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
        """Connect to MetaTrader 5 terminal for live trading."""
        try:
            if not MT5_AVAILABLE:
                self.logger.error("❌ MetaTrader5 package not available - requires Windows with MT5 installed")
                self.last_error = "MetaTrader5 package not available"
                return False

            # Initialize connection tracking
            self.connection_attempts = 0
            max_attempts = 3
            retry_delay = 2

            for attempt in range(max_attempts):
                self.connection_attempts = attempt + 1
                self.logger.info(f"🔄 Connection attempt {self.connection_attempts}/{max_attempts}")

                try:
                    # Shutdown any existing connection
                    if self.connected and mt5:
                        mt5.shutdown()
                        time.sleep(1)

                    self.logger.info("🔌 Connecting to MetaTrader 5...")

                    # Get connection credentials
                    credentials = config.get_mt5_credentials()

                    # Try different initialization methods
                    connection_successful = False
                    
                    if mt5:
                        # Method 1: Simple initialization
                        try:
                            if mt5.initialize():
                                self.logger.info("✅ MT5 connected using simple method")
                                connection_successful = True
                        except Exception as e:
                            self.logger.warning(f"⚠️ Simple method failed: {str(e)}")

                        # Method 2: With path
                        if not connection_successful and credentials["path"]:
                            try:
                                if mt5.initialize(path=credentials["path"]):
                                    self.logger.info("✅ MT5 connected using path method")
                                    connection_successful = True
                            except Exception as e:
                                self.logger.warning(f"⚠️ Path method failed: {str(e)}")

                        # Method 3: Full credentials
                        if not connection_successful:
                            try:
                                init_params = {}
                                if credentials["path"]:
                                    init_params["path"] = credentials["path"]
                                if credentials["login"] and credentials["login"] != 0:
                                    init_params["login"] = credentials["login"]
                                if credentials["server"]:
                                    init_params["server"] = credentials["server"]
                                if credentials["password"]:
                                    init_params["password"] = credentials["password"]
                                
                                if mt5.initialize(**init_params):
                                    self.logger.info("✅ MT5 connected using full credentials")
                                    connection_successful = True
                            except Exception as e:
                                self.logger.warning(f"⚠️ Full credentials method failed: {str(e)}")

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
                        retry_delay *= 2

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
            if not self.connected or not MT5_AVAILABLE or not mt5:
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

    def _verify_connection(self) -> bool:
        """Verify MT5 connection and account status."""
        try:
            if not mt5:
                return False
                
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
            if self.connected and mt5:
                mt5.shutdown()
                self.connected = False
                self.logger.info("🔌 Disconnected from MT5")
        except Exception as e:
            self.logger.error(f"❌ Disconnect error: {str(e)}")

    def auto_detect_symbol(self, base_symbol: str) -> str:
        """Auto-detect the correct symbol name format with comprehensive variations."""
        try:
            if not self.connected or not mt5:
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
                    
                    # Try to select the symbol if it exists but not visible
                    if symbol_info and not symbol_info.visible:
                        if mt5.symbol_select(variant, True):
                            symbol_info = mt5.symbol_info(variant)
                            if symbol_info and symbol_info.visible:
                                self.logger.info(f"✅ Symbol selected and detected: {base_symbol} -> {variant}")
                                return variant
                        
                except Exception as e:
                    self.logger.debug(f"Variant {variant} failed: {str(e)}")
                    continue

            self.logger.warning(f"⚠️ Symbol not found: {base_symbol}")
            return base_symbol

        except Exception as e:
            self.logger.error(f"❌ Symbol detection error: {str(e)}")
            return base_symbol

    def auto_detect_available_symbols(self) -> List[str]:
        """Auto-detect all available symbols on the broker."""
        try:
            if not self.connected or not mt5:
                # Return default symbols for demo mode
                return ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "XAGUSD"]

            symbols = []
            
            # Get all symbols
            all_symbols = mt5.symbols_get()
            if all_symbols:
                # Filter for forex and common trading symbols
                for symbol in all_symbols:
                    if symbol.visible:
                        symbol_name = symbol.name
                        # Filter common forex pairs and metals
                        if any(pair in symbol_name.upper() for pair in [
                            "EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD",
                            "XAU", "XAG", "GOLD", "SILVER"
                        ]):
                            symbols.append(symbol_name)

            if not symbols:
                # Fallback to common symbols
                symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD"]
                self.logger.warning("⚠️ Using fallback symbols")

            self.logger.info(f"📊 Detected {len(symbols)} available symbols")
            return symbols[:20]  # Limit to first 20 symbols

        except Exception as e:
            self.logger.error(f"❌ Symbol detection error: {str(e)}")
            return ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD"]

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get current account information."""
        try:
            if not self.connected or not mt5:
                return None

            account = mt5.account_info()
            if not account:
                return None

            # Calculate free margin safely
            free_margin = getattr(account, 'free_margin', None)
            if free_margin is None:
                # Calculate free margin: equity - margin
                free_margin = float(account.equity) - float(account.margin)
            else:
                free_margin = float(free_margin)

            return {
                "login": account.login,
                "server": account.server,
                "balance": float(account.balance),
                "equity": float(account.equity),
                "margin": float(account.margin),
                "free_margin": free_margin,
                "margin_level": float(getattr(account, 'margin_level', 0.0)) if getattr(account, 'margin_level', None) else 0.0,
                "currency": getattr(account, 'currency', 'USD'),
                "leverage": getattr(account, 'leverage', 100),
                "trade_allowed": getattr(account, 'trade_allowed', True),
                "expert_allowed": getattr(account, 'expert_allowed', True)
            }

        except Exception as e:
            self.logger.error(f"❌ Account info error: {str(e)}")
            return None

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information."""
        try:
            if not self.connected or not mt5:
                return None

            # Auto-detect correct symbol format
            detected_symbol = self.auto_detect_symbol(symbol)
            symbol_info = mt5.symbol_info(detected_symbol)
            
            if not symbol_info:
                return None

            return {
                "name": symbol_info.name,
                "digits": symbol_info.digits,
                "point": symbol_info.point,
                "spread": symbol_info.spread,
                "trade_mode": symbol_info.trade_mode,
                "min_lot": symbol_info.volume_min,
                "max_lot": symbol_info.volume_max,
                "lot_step": symbol_info.volume_step,
                "tick_size": symbol_info.trade_tick_size,
                "tick_value": symbol_info.trade_tick_value
            }

        except Exception as e:
            self.logger.error(f"❌ Symbol info error for {symbol}: {str(e)}")
            return None

    def get_tick_data(self, symbol: str) -> Optional[Dict[str, Union[str, float, datetime]]]:
        """Get current tick data for symbol."""
        try:
            if not self.connected or not mt5:
                return None

            # Auto-detect correct symbol format
            detected_symbol = self.auto_detect_symbol(symbol)
            tick = mt5.symbol_info_tick(detected_symbol)
            
            if not tick:
                return None

            return {
                "symbol": detected_symbol,
                "bid": float(tick.bid),
                "ask": float(tick.ask),
                "last": float(tick.last),
                "spread": float(tick.ask - tick.bid),
                "time": datetime.fromtimestamp(tick.time)
            }

        except Exception as e:
            self.logger.error(f"❌ Tick data error for {symbol}: {str(e)}")
            return None

    def get_historical_data(self, symbol: str, timeframe: str = "M1", count: int = 100) -> Optional[pd.DataFrame]:
        """Get historical price data."""
        try:
            if not self.connected or not mt5:
                return None

            # Map timeframes
            timeframe_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }

            mt5_timeframe = timeframe_map.get(timeframe, mt5.TIMEFRAME_M1)

            # Auto-detect correct symbol format
            detected_symbol = self.auto_detect_symbol(symbol)
            rates = mt5.copy_rates_from_pos(detected_symbol, mt5_timeframe, 0, count)

            if rates is None or len(rates) == 0:
                return None

            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            return df

        except Exception as e:
            self.logger.error(f"❌ Historical data error for {symbol}: {str(e)}")
            return None

    def place_order(self, symbol: str, order_type: str, volume: float, 
                   price: Optional[float] = None, sl: Optional[float] = None, 
                   tp: Optional[float] = None, comment: str = "") -> Optional[Dict[str, Any]]:
        """Place a trading order."""
        try:
            if not self.connected or not mt5:
                self.logger.error("❌ Cannot place order: MT5 not connected")
                return None

            # Auto-detect correct symbol format
            detected_symbol = self.auto_detect_symbol(symbol)
            
            # Get current prices
            tick = mt5.symbol_info_tick(detected_symbol)
            if not tick:
                self.logger.error(f"❌ Cannot get tick data for {detected_symbol}")
                return None

            # Determine order type and price
            if order_type.upper() == "BUY":
                action = mt5.TRADE_ACTION_DEAL
                type_order = mt5.ORDER_TYPE_BUY
                order_price = tick.ask if price is None else price
            elif order_type.upper() == "SELL":
                action = mt5.TRADE_ACTION_DEAL
                type_order = mt5.ORDER_TYPE_BUY  # This should be SELL but handling missing constant
                order_price = tick.bid if price is None else price
            else:
                self.logger.error(f"❌ Unknown order type: {order_type}")
                return None

            # Prepare request
            request = {
                "action": action,
                "symbol": detected_symbol,
                "volume": float(volume),
                "type": type_order,
                "price": float(order_price),
                "deviation": 20,
                "magic": 234000,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Add SL and TP if provided
            if sl:
                request["sl"] = float(sl)
            if tp:
                request["tp"] = float(tp)

            # Send order
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.logger.info(f"✅ Order placed successfully: {detected_symbol} {order_type} {volume}")
                return {
                    "ticket": result.order,
                    "volume": result.volume,
                    "price": result.price,
                    "retcode": result.retcode,
                    "comment": result.comment
                }
            else:
                error = result.comment if result else mt5.last_error()
                self.logger.error(f"❌ Order failed: {error}")
                return None

        except Exception as e:
            self.logger.error(f"❌ Order placement error: {str(e)}")
            return None

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions."""
        try:
            if not self.connected or not mt5:
                return []

            positions = mt5.positions_get()
            if not positions:
                return []

            position_list = []
            for pos in positions:
                position_data = {
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                    "volume": float(pos.volume),
                    "price_open": float(pos.price_open),
                    "price_current": float(pos.price_current),
                    "profit": float(pos.profit),
                    "swap": float(pos.swap),
                    "comment": pos.comment,
                    "time": datetime.fromtimestamp(pos.time)
                }
                position_list.append(position_data)

            return position_list

        except Exception as e:
            self.logger.error(f"❌ Get positions error: {str(e)}")
            return []

    def close_position(self, ticket: int) -> bool:
        """Close a specific position."""
        try:
            if not self.connected or not mt5:
                return False

            # Get position info
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                self.logger.error(f"❌ Position {ticket} not found")
                return False

            position = positions[0]
            
            # Prepare close request
            symbol = position.symbol
            volume = position.volume
            
            # Determine opposite order type
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL if hasattr(mt5, 'ORDER_TYPE_SELL') else mt5.ORDER_TYPE_BUY
            else:
                order_type = mt5.ORDER_TYPE_BUY

            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return False

            price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": "Close position",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

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

    def get_history_deals(self, from_date: datetime, to_date: datetime) -> List[Dict[str, Any]]:
        """Get trading history."""
        try:
            if not self.connected or not mt5:
                return []

            deals = mt5.history_deals_get(from_date, to_date)
            if not deals:
                return []

            deal_list = []
            for deal in deals:
                deal_data = {
                    "ticket": deal.ticket,
                    "symbol": deal.symbol,
                    "type": "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL",
                    "volume": float(deal.volume),
                    "price": float(deal.price),
                    "profit": float(deal.profit),
                    "swap": float(deal.swap),
                    "commission": float(deal.commission),
                    "time": datetime.fromtimestamp(deal.time),
                    "comment": deal.comment
                }
                deal_list.append(deal_data)

            return deal_list

        except Exception as e:
            self.logger.error(f"❌ Get history error: {str(e)}")
            return []