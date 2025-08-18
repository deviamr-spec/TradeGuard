
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
        
    def connect(self) -> bool:
        """
        Connect to MetaTrader 5 terminal with enhanced validation and retry logic.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Check if MT5 is available
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
        """
        Check if the MT5 connection is healthy.
        
        Returns:
            bool: True if connection is healthy
        """
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
        """
        Attempt automatic reconnection.
        
        Returns:
            bool: True if reconnection successful
        """
        try:
            self.logger.info("🔄 Attempting automatic reconnection...")
            
            # Mark as disconnected
            self.connected = False
            
            # Wait a moment before reconnecting
            time.sleep(2)
            
            # Attempt reconnection
            if self.connect():
                self.logger.info("✅ Automatic reconnection successful")
                return True
            else:
                self.logger.error("❌ Automatic reconnection failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Auto-reconnection error: {str(e)}")
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
    
    def auto_detect_symbol(self, base_symbol: str) -> Optional[str]:
        """
        Auto-detect the correct symbol name for the broker.
        
        Args:
            base_symbol: Base symbol name (e.g., 'XAUUSD', 'EURUSD')
            
        Returns:
            Actual symbol name or None if not found
        """
        try:
            if not self.connected:
                return None
            
            # Define common symbol variations
            variations = []
            
            if "XAU" in base_symbol.upper() or "GOLD" in base_symbol.upper():
                # Gold variations - Enhanced list
                variations = [
                    "XAUUSD", "XAUUSDm", "XAUUSDM", "XAUUSDc", "XAUUSDC",
                    "GOLD", "GOLDm", "GOLDM", "GOLDc", "GOLDC", "Gold",
                    "XAUUSD.a", "XAUUSD.b", "XAUUSD.raw", "XAUUSD_m",
                    "XAU/USD", "XAU_USD", "XAUUSD.pro", "XAUUSD#",
                    "XAUUSD.", "XAUUSD-", "XAUUSDi", "XAUUSDf",
                    "GC", "GCm", "XAUUSD_raw", "GOLD_USD"
                ]
            elif "XAG" in base_symbol.upper() or "SILVER" in base_symbol.upper():
                # Silver variations
                variations = [
                    "XAGUSD", "XAGUSDm", "XAGUSDM", "XAGUSDc", "XAGUSDC",
                    "SILVER", "SILVERm", "SILVERM", "SILVERc", "SILVERC",
                    "XAGUSD.a", "XAGUSD.b", "XAG/USD", "XAG_USD"
                ]
            elif len(base_symbol) == 6:
                # Forex pairs
                variations = [
                    base_symbol,
                    base_symbol + "m",
                    base_symbol + "M", 
                    base_symbol + "c",
                    base_symbol + "C",
                    base_symbol + ".a",
                    base_symbol + ".b",
                    base_symbol + ".raw",
                    base_symbol + ".pro",
                    base_symbol + "#",
                    base_symbol[:3] + "/" + base_symbol[3:],
                    base_symbol[:3] + "_" + base_symbol[3:],
                ]
            else:
                variations = [base_symbol]
            
            # Test each variation
            for symbol in variations:
                try:
                    # Test symbol info
                    info = mt5.symbol_info(symbol)
                    if info:
                        # Try to activate if not visible
                        if not info.visible:
                            if mt5.symbol_select(symbol, True):
                                time.sleep(0.5)
                                info = mt5.symbol_info(symbol)
                        
                        # Test tick data
                        if info and info.visible:
                            tick = mt5.symbol_info_tick(symbol)
                            if tick and hasattr(tick, 'bid') and hasattr(tick, 'ask'):
                                if tick.bid > 0 and tick.ask > 0:
                                    self.logger.info(f"✅ Auto-detected symbol: {symbol} for {base_symbol}")
                                    self.validated_symbols[base_symbol] = symbol
                                    return symbol
                                    
                except Exception as e:
                    continue
            
            self.logger.warning(f"⚠️ Could not auto-detect symbol for: {base_symbol}")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Symbol auto-detection error: {str(e)}")
            return None
    
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
            
            # Send order
            result = mt5.order_send(order_request)
            if not result:
                error = mt5.last_error()
                self.logger.error(f"❌ Order failed: {error}")
                return None
            
            # Check result
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"❌ Order rejected: {result.retcode} - {result.comment}")
                return None
            
            self.logger.info(f"✅ Order executed: {result.order} - {result.comment}")
            
            return {
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
            return None
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions.
        
        Returns:
            List of position dictionaries
        """
        try:
            if not self.connected:
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
                return False
                
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                self.logger.error(f"❌ Position {ticket} not found")
                return False
                
            position = position[0]
            
            # Prepare close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "position": ticket,
                "deviation": 20,
                "magic": 234000,
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
