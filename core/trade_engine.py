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
        self.reporting = ReportingManager()
        
        # Engine state
        self.running = False
        self.trading_enabled = False
        self.engine_thread = None
        self.last_update = datetime.now()
        
        # Trading parameters
        self.symbols = config.get("trading.symbols", ["EURUSD", "GBPUSD", "USDJPY"])
        self.timeframe = config.get("trading.timeframe", "M1")
        self.update_interval = 1.0  # seconds
        
        # Position tracking
        self.active_positions = {}
        self.pending_signals = {}
        self.last_signal_time = {}
        
        # Thread safety
        self.trade_lock = threading.Lock()
        
        self.logger.info(f"⚙️ Trade Engine initialized:")
        self.logger.info(f"   Symbols: {self.symbols}")
        self.logger.info(f"   Timeframe: {self.timeframe}")
        self.logger.info(f"   Update interval: {self.update_interval}s")
    
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
            
            # Verify MT5 connection
            if not self.mt5_client.connected:
                self.logger.error("❌ MT5 not connected")
                return False
            
            # Initialize components
            account_info = self.mt5_client.get_account_info()
            if not account_info:
                self.logger.error("❌ Failed to get account info")
                return False
            
            # Initialize risk manager and reporting
            self.risk_manager.initialize_session(account_info["balance"])
            self.reporting.initialize_session(account_info)
            
            # Enable trading
            self.running = True
            self.trading_enabled = True
            
            # Start engine thread
            self.engine_thread = threading.Thread(target=self._engine_loop, daemon=True)
            self.engine_thread.start()
            
            self.logger.info("🚀 Trade Engine started successfully")
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
                    
                    # Process signal if valid
                    if signal["signal"] in ["BUY", "SELL"]:
                        self._execute_signal(signal, account_info, current_positions)
                        
                except Exception as e:
                    self.logger.error(f"❌ Signal processing error for {symbol}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"❌ Trading signals processing error: {str(e)}")
    
    def _execute_signal(self, signal: Dict[str, Any], account_info: Dict[str, Any], 
                       positions: List[Dict[str, Any]]) -> None:
        """Execute a trading signal."""
        try:
            with self.trade_lock:
                symbol = signal["symbol"]
                
                # Get symbol information
                symbol_info = self.mt5_client.get_symbol_info(symbol)
                if not symbol_info:
                    self.logger.error(f"❌ Failed to get symbol info for {symbol}")
                    return
                
                # Validate trade with risk manager
                validation = self.risk_manager.validate_trade(signal, account_info, positions, symbol_info)
                if not validation["allowed"]:
                    self.logger.info(f"🚫 Trade rejected for {symbol}: {validation['reason']}")
                    return
                
                # Log warnings if any
                if validation["warnings"]:
                    self.logger.warning(f"⚠️ Trade warnings for {symbol}: {', '.join(validation['warnings'])}")
                
                # Calculate position sizing
                confidence = signal["confidence"] / 100.0  # Convert to 0-1 scale
                lot_size, stop_loss, take_profit = self.strategy.calculate_position_size(
                    signal, account_info["balance"], symbol_info
                )
                
                # Prepare order request
                tick_data = signal["tick_data"]
                current_price = tick_data["ask"] if signal["signal"] == "BUY" else tick_data["bid"]
                
                order_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": lot_size,
                    "type": mt5.ORDER_TYPE_BUY if signal["signal"] == "BUY" else mt5.ORDER_TYPE_SELL,
                    "price": current_price,
                    "sl": stop_loss if stop_loss > 0 else 0.0,
                    "tp": take_profit if take_profit > 0 else 0.0,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": f"Bot {signal['signal']} - Conf:{signal['confidence']:.1f}%",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                
                # Execute order
                self.logger.info(f"📤 Executing {signal['signal']} order for {symbol}: {lot_size} lots @ {current_price}")
                
                result = self.mt5_client.place_order(order_request)
                if result:
                    # Log successful trade
                    trade_data = {
                        "symbol": symbol,
                        "type": signal["signal"],
                        "volume": lot_size,
                        "price": current_price,
                        "sl": stop_loss,
                        "tp": take_profit,
                        "order": result["order"],
                        "deal": result["deal"],
                        "comment": order_request["comment"]
                    }
                    
                    self.reporting.log_trade(trade_data)
                    self.risk_manager.on_trade_executed(result)
                    
                    # Track position
                    self.active_positions[result["order"]] = {
                        "symbol": symbol,
                        "type": signal["signal"],
                        "volume": lot_size,
                        "entry_time": datetime.now(),
                        "entry_price": current_price,
                        "signal_data": signal
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
                    # Position was closed
                    closed_orders.append(order_id)
                    
                    # Try to get trade history to update outcome
                    history = self.mt5_client.get_trade_history(days=1)
                    for trade in history:
                        if trade["order"] == order_id:
                            outcome_data = {
                                "exit_price": trade["price"],
                                "profit": trade["profit"],
                                "commission": trade["commission"],
                                "swap": trade["swap"]
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
