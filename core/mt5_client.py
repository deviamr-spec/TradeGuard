
"""
MetaTrader 5 client for handling all MT5 operations.
Enhanced with robust error handling and demo mode for cross-platform compatibility.
"""

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

import pandas as pd
import numpy as np
import time
import random
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta

from core.config import config
from utils.logging_setup import get_logger

class MT5Client:
    """MetaTrader 5 client with demo mode fallback for cross-platform compatibility."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.connected = False
        self.demo_mode = not MT5_AVAILABLE
        self.account_info = None
        self.symbols_info = {}
        self.last_error = None
        self.validated_symbols = {}
        self.connection_attempts = 0
        self.consecutive_failures = 0
        self.last_connection_time = None
        self.last_health_check = None
        
        # Demo mode data
        self.demo_account = {
            "login": 12345678,
            "server": "Demo-Server",
            "balance": 10000.0,
            "equity": 10000.0,
            "margin": 0.0,
            "free_margin": 10000.0,
            "margin_level": 0.0,
            "currency": "USD",
            "leverage": 100,
            "trade_allowed": True,
            "expert_allowed": True
        }
        
        # Demo symbols mapping
        self.demo_symbols = {
            "EURUSD": "EURUSD",
            "GBPUSD": "GBPUSD", 
            "USDJPY": "USDJPY",
            "AUDUSD": "AUDUSD",
            "USDCAD": "USDCAD",
            "XAUUSD": "XAUUSD",
            "XAGUSD": "XAGUSD"
        }
        
        if self.demo_mode:
            self.logger.warning("⚠️ Running in DEMO MODE - MetaTrader5 not available")
            self.connected = True
            self.last_connection_time = datetime.now()

    def connect(self) -> bool:
        """Connect to MetaTrader 5 or enable demo mode."""
        try:
            if self.demo_mode:
                self.logger.info("🎭 Demo mode connection successful")
                self.connected = True
                self.last_connection_time = datetime.now()
                self.consecutive_failures = 0
                return True

            if not MT5_AVAILABLE:
                self.logger.error("❌ MetaTrader5 package not available")
                self.demo_mode = True
                self.connected = True
                return True

            self.connection_attempts = 0
            max_attempts = 3
            retry_delay = 2

            for attempt in range(max_attempts):
                self.connection_attempts = attempt + 1
                self.logger.info(f"🔄 Connection attempt {self.connection_attempts}/{max_attempts}")

                try:
                    if self.connected and mt5:
                        mt5.shutdown()
                        time.sleep(1)

                    self.logger.info("🔌 Connecting to MetaTrader 5...")
                    
                    if mt5 and mt5.initialize():
                        self.logger.info("✅ MT5 connected using simple method")
                        
                        if self._verify_connection():
                            self.connected = True
                            self.last_connection_time = datetime.now()
                            self.consecutive_failures = 0
                            self.logger.info(f"✅ MT5 client connected successfully (attempt {self.connection_attempts})")
                            return True
                    
                    raise ConnectionError("MT5 initialization failed")

                except Exception as e:
                    self.logger.warning(f"⚠️ Connection attempt {self.connection_attempts} failed: {str(e)}")
                    self.last_error = str(e)

                    if attempt < max_attempts - 1:
                        self.logger.info(f"🔄 Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2

            # Fallback to demo mode
            self.logger.warning("🎭 Falling back to demo mode")
            self.demo_mode = True
            self.connected = True
            self.consecutive_failures = 0
            return True

        except Exception as e:
            self.logger.error(f"❌ Connection failed: {str(e)}")
            self.demo_mode = True
            self.connected = True
            return True

    def is_connection_healthy(self) -> bool:
        """Check if connection is healthy."""
        try:
            if self.demo_mode:
                return True
                
            if not self.connected or not MT5_AVAILABLE or not mt5:
                return False

            # Check if MT5 is still initialized
            try:
                account_info = mt5.account_info()
                if not account_info:
                    self.logger.warning("⚠️ Connection health check failed: No account info")
                    return False
            except Exception as e:
                self.logger.warning(f"⚠️ Connection health check failed: Account info error - {str(e)}")
                return False

            # Test tick data availability
            tick_available = False
            for test_symbol in ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]:
                try:
                    detected_symbol = self.auto_detect_symbol(test_symbol)
                    tick = mt5.symbol_info_tick(detected_symbol)
                    if tick and hasattr(tick, 'bid') and hasattr(tick, 'ask') and tick.bid > 0 and tick.ask > 0:
                        tick_available = True
                        break
                except Exception:
                    continue

            if not tick_available:
                self.logger.warning("⚠️ Connection health check failed: No tick data available")
                return False

            self.last_health_check = datetime.now()
            return True

        except Exception as e:
            self.logger.debug(f"Health check error: {str(e)}")
            return False

    def auto_reconnect(self) -> bool:
        """Attempt automatic reconnection."""
        try:
            if self.demo_mode:
                return True
                
            # Prevent multiple simultaneous reconnection attempts
            current_time = datetime.now()
            if hasattr(self, 'last_reconnect_attempt'):
                time_since_reconnect = (current_time - self.last_reconnect_attempt).total_seconds()
                if time_since_reconnect < 10:  # Wait at least 10 seconds between attempts
                    return self.connected
            
            self.last_reconnect_attempt = current_time
                
            # Quick health check first
            if self.is_connection_healthy():
                return True

            self.logger.warning("🔄 Connection unhealthy, attempting auto-reconnection...")
            
            # Limit reconnection attempts
            max_reconnect_attempts = 5
            if not hasattr(self, 'reconnect_count'):
                self.reconnect_count = 0
                
            self.reconnect_count += 1
            if self.reconnect_count > max_reconnect_attempts:
                self.logger.warning(f"⚠️ Max reconnection attempts ({max_reconnect_attempts}) reached")
                return False
                
            self.logger.info(f"🔄 Reconnection attempt {self.reconnect_count}/{max_reconnect_attempts} in 2s...")
            time.sleep(2)
            
            success = self.connect()
            if success:
                self.reconnect_count = 0  # Reset counter on successful reconnection
                self.logger.info("✅ Auto-reconnection successful!")
            
            return success

        except Exception as e:
            self.logger.error(f"Auto-reconnection error: {e}")
            self.demo_mode = True
            self.connected = True
            return True

    def _verify_connection(self) -> bool:
        """Verify MT5 connection and account status."""
        try:
            if self.demo_mode:
                return True
                
            if not mt5:
                return False
                
            self.account_info = mt5.account_info()
            if not self.account_info:
                return False

            self.logger.info(f"📊 Account: {self.account_info.login}")
            self.logger.info(f"💰 Balance: ${self.account_info.balance:,.2f}")
            self.logger.info(f"📈 Equity: ${self.account_info.equity:,.2f}")
            self.logger.info(f"🏦 Server: {self.account_info.server}")

            if hasattr(self.account_info, 'trade_allowed'):
                if self.account_info.trade_allowed:
                    self.logger.info("✅ Trading is allowed")
                else:
                    self.logger.warning("⚠️ Trading is not allowed")

            return True

        except Exception as e:
            self.logger.error(f"❌ Connection verification failed: {str(e)}")
            return False

    def disconnect(self) -> None:
        """Disconnect from MetaTrader 5."""
        try:
            if self.demo_mode:
                self.connected = False
                self.logger.info("🎭 Demo mode disconnected")
                return
                
            if self.connected and mt5:
                mt5.shutdown()
                self.connected = False
                self.logger.info("🔌 Disconnected from MT5")
        except Exception as e:
            self.logger.error(f"❌ Disconnect error: {str(e)}")

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get current account information."""
        try:
            if self.demo_mode:
                return self.demo_account.copy()
                
            if not self.connected or not mt5:
                return None

            account = mt5.account_info()
            if not account:
                return None

            try:
                free_margin = float(account.free_margin)
            except AttributeError:
                free_margin = float(account.equity) - float(account.margin)

            return {
                "login": account.login,
                "server": account.server,
                "balance": float(account.balance),
                "equity": float(account.equity),
                "margin": float(account.margin),
                "free_margin": free_margin,
                "margin_level": float(getattr(account, 'margin_level', 0.0)),
                "currency": getattr(account, 'currency', 'USD'),
                "leverage": getattr(account, 'leverage', 100),
                "trade_allowed": getattr(account, 'trade_allowed', True),
                "expert_allowed": getattr(account, 'expert_allowed', True)
            }

        except Exception as e:
            self.logger.error(f"❌ Account info error: {str(e)}")
            return self.demo_account.copy() if self.demo_mode else None

    def auto_detect_symbol(self, base_symbol: str) -> str:
        """Auto-detect the correct symbol name format."""
        try:
            if self.demo_mode:
                return self.demo_symbols.get(base_symbol, base_symbol)
                
            if not self.connected or not mt5:
                return base_symbol

            # Check if symbol exists as-is
            symbol_info = mt5.symbol_info(base_symbol)
            if symbol_info and symbol_info.visible:
                return base_symbol

            # Try variations
            variations = [
                base_symbol + "m", base_symbol + ".m", base_symbol + "_m",
                base_symbol + "pro", base_symbol + ".pro", base_symbol + "_pro",
                base_symbol + "c", base_symbol + ".c", base_symbol + "_c",
                base_symbol + "raw", base_symbol + ".raw", base_symbol + "_raw",
                base_symbol.lower(), base_symbol.upper()
            ]

            for variant in variations:
                try:
                    symbol_info = mt5.symbol_info(variant)
                    if symbol_info and symbol_info.visible:
                        self.logger.info(f"✅ Symbol detected: {base_symbol} -> {variant}")
                        return variant
                    
                    if symbol_info and not symbol_info.visible:
                        if mt5.symbol_select(variant, True):
                            symbol_info = mt5.symbol_info(variant)
                            if symbol_info and symbol_info.visible:
                                self.logger.info(f"✅ Symbol selected and detected: {base_symbol} -> {variant}")
                                return variant
                        
                except Exception:
                    continue

            self.logger.debug(f"Using original symbol: {base_symbol}")
            return base_symbol

        except Exception as e:
            self.logger.error(f"❌ Symbol detection error: {str(e)}")
            return base_symbol

    def get_tick_data(self, symbol: str) -> Optional[Dict[str, Union[str, float, datetime]]]:
        """Get current tick data for symbol."""
        try:
            if self.demo_mode:
                # Generate realistic demo data
                base_prices = {
                    "EURUSD": 1.0830, "GBPUSD": 1.2750, "USDJPY": 150.50,
                    "AUDUSD": 0.6400, "USDCAD": 1.3450, "XAUUSD": 1950.0, "XAGUSD": 23.0
                }
                
                base_price = base_prices.get(symbol, 1.0000)
                spread = 0.00020 if "USD" in symbol else 0.50
                
                bid = base_price + random.uniform(-0.001, 0.001)
                ask = bid + spread
                
                return {
                    "symbol": symbol,
                    "bid": round(bid, 5),
                    "ask": round(ask, 5),
                    "last": round((bid + ask) / 2, 5),
                    "spread": round(ask - bid, 5),
                    "time": datetime.now()
                }
                
            if not self.connected or not mt5:
                return None

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
            if self.demo_mode:
                # Generate demo historical data
                dates = pd.date_range(end=datetime.now(), periods=count, freq='1min')
                
                base_prices = {
                    "EURUSD": 1.0830, "GBPUSD": 1.2750, "USDJPY": 150.50,
                    "AUDUSD": 0.6400, "USDCAD": 1.3450, "XAUUSD": 1950.0, "XAGUSD": 23.0
                }
                
                base_price = base_prices.get(symbol, 1.0000)
                
                # Generate realistic OHLC data with proper validation
                data = []
                current_price = base_price
                
                for _ in range(count):
                    # Generate open price (previous close or slight variation)
                    open_price = current_price
                    
                    # Generate price movement
                    change_percent = random.uniform(-0.002, 0.002)
                    price_range = abs(change_percent * current_price)
                    
                    # Generate high and low ensuring proper OHLC relationships
                    high_add = random.uniform(0, price_range)
                    low_sub = random.uniform(0, price_range)
                    
                    high = open_price + high_add
                    low = open_price - low_sub
                    
                    # Generate close within high-low range
                    close = random.uniform(low, high)
                    
                    # Ensure OHLC relationships are valid
                    high = max(high, open_price, close)
                    low = min(low, open_price, close)
                    
                    data.append({
                        'open': round(open_price, 5),
                        'high': round(high, 5),
                        'low': round(low, 5),
                        'close': round(close, 5),
                        'tick_volume': random.randint(50, 200)
                    })
                    current_price = close
                
                df = pd.DataFrame(data, index=dates)
                return df
                
            if not self.connected or not mt5:
                return None

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
            detected_symbol = self.auto_detect_symbol(symbol)
            rates = mt5.copy_rates_from_pos(detected_symbol, mt5_timeframe, 0, count)

            if rates is None or len(rates) == 0:
                return None

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
            if self.demo_mode:
                # Simulate order placement
                tick_data = self.get_tick_data(symbol)
                if not tick_data:
                    return None
                    
                order_price = tick_data["ask"] if order_type.upper() == "BUY" else tick_data["bid"]
                if price:
                    order_price = price
                    
                order_ticket = random.randint(100000, 999999)
                
                self.logger.info(f"🎭 Demo order placed: {symbol} {order_type} {volume} @ {order_price}")
                
                return {
                    "ticket": order_ticket,
                    "volume": volume,
                    "price": order_price,
                    "retcode": 10009,  # TRADE_RETCODE_DONE
                    "comment": "Demo order"
                }
                
            if not self.connected or not mt5:
                self.logger.error("❌ Cannot place order: MT5 not connected")
                return None

            detected_symbol = self.auto_detect_symbol(symbol)
            tick = mt5.symbol_info_tick(detected_symbol)
            if not tick:
                self.logger.error(f"❌ Cannot get tick data for {detected_symbol}")
                return None

            if order_type.upper() == "BUY":
                action = mt5.TRADE_ACTION_DEAL
                type_order = mt5.ORDER_TYPE_BUY
                order_price = tick.ask if price is None else price
            elif order_type.upper() == "SELL":
                action = mt5.TRADE_ACTION_DEAL
                type_order = mt5.ORDER_TYPE_SELL
                order_price = tick.bid if price is None else price
            else:
                self.logger.error(f"❌ Unknown order type: {order_type}")
                return None

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

            if sl:
                request["sl"] = float(sl)
            if tp:
                request["tp"] = float(tp)

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
                error = result.comment if result else "Unknown error"
                self.logger.error(f"❌ Order failed: {error}")
                return None

        except Exception as e:
            self.logger.error(f"❌ Order placement error: {str(e)}")
            return None

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions."""
        try:
            if self.demo_mode:
                return []  # No demo positions for now
                
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
            if self.demo_mode:
                self.logger.info(f"🎭 Demo position {ticket} closed")
                return True
                
            if not self.connected or not mt5:
                return False

            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                self.logger.error(f"❌ Position {ticket} not found")
                return False

            position = positions[0]
            symbol = position.symbol
            volume = position.volume
            
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
            else:
                order_type = mt5.ORDER_TYPE_BUY

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
                error = result.comment if result else "Unknown error"
                self.logger.error(f"❌ Failed to close position {ticket}: {error}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Close position error: {str(e)}")
            return False

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information."""
        try:
            if self.demo_mode:
                return {
                    "symbol": symbol,
                    "point": 0.00001,
                    "digits": 5,
                    "spread": 20,
                    "volume_min": 0.01,
                    "volume_max": 1000.0,
                    "volume_step": 0.01,
                    "currency_base": symbol[:3],
                    "currency_profit": symbol[3:6],
                    "currency_margin": symbol[3:6],
                    "contract_size": 100000.0
                }
                
            if not self.connected or not mt5:
                return None

            detected_symbol = self.auto_detect_symbol(symbol)
            symbol_info = mt5.symbol_info(detected_symbol)
            
            if not symbol_info:
                return None

            return {
                "symbol": detected_symbol,
                "point": float(symbol_info.point),
                "digits": symbol_info.digits,
                "spread": int(symbol_info.spread),
                "volume_min": float(symbol_info.volume_min),
                "volume_max": float(symbol_info.volume_max),
                "volume_step": float(symbol_info.volume_step),
                "currency_base": symbol_info.currency_base,
                "currency_profit": symbol_info.currency_profit,
                "currency_margin": symbol_info.currency_margin,
                "contract_size": float(symbol_info.trade_contract_size)
            }

        except Exception as e:
            self.logger.error(f"❌ Symbol info error for {symbol}: {str(e)}")
            return None

    def get_trade_history(self, from_date: datetime, to_date: datetime) -> List[Dict[str, Any]]:
        """Get trading history."""
        try:
            if self.demo_mode:
                return []  # No demo history for now
                
            if not self.connected or not mt5:
                return []

            deals = mt5.history_deals_get(from_date, to_date)
            if not deals:
                return []

            deal_list = []
            for deal in deals:
                deal_data = {
                    "ticket": deal.ticket,
                    "order": deal.order,
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

    def monitor_connection(self) -> Dict[str, Any]:
        """Monitor connection status."""
        try:
            if self.demo_mode:
                return {
                    "connected": True,
                    "healthy": True,
                    "demo_mode": True,
                    "last_error": None,
                    "uptime_seconds": int((datetime.now() - self.last_connection_time).total_seconds()) if self.last_connection_time else 0
                }
                
            status = {
                "connected": self.connected,
                "healthy": False,
                "demo_mode": False,
                "last_error": self.last_error,
                "consecutive_failures": self.consecutive_failures,
                "connection_attempts": self.connection_attempts,
                "last_connection_time": self.last_connection_time,
                "uptime_seconds": 0
            }

            if self.connected:
                status["healthy"] = self.is_connection_healthy()

                if self.last_connection_time:
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
