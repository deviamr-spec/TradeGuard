#!/usr/bin/env python3
"""
MT5 Trading Bot Console Demo
A console-based demonstration of the trading bot functionality without GUI requirements.
"""

import os
import sys
import time
import threading
import signal
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Optional

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logging_setup import setup_logging, get_logger
from utils.diagnostics import run_startup_diagnostics
from core.mt5_client import MT5Client, MT5_AVAILABLE
from core.trade_engine import TradeEngine
from core.strategy.scalping import ScalpingStrategy
from core.risk import RiskManager
from core.reporting import ReportingManager

class TradingBotConsoleDemo:
    """Enhanced console-based demonstration of the trading bot."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.running = False
        self.demo_mode = not MT5_AVAILABLE

        # Initialize components
        self.mt5_client = None
        self.trade_engine = None
        self.strategy = ScalpingStrategy()
        self.risk_manager = RiskManager()
        self.reporting = ReportingManager()

        # Mock account info with all required fields
        self.demo_account = {
            "login": 12345678,
            "balance": 10000.0,
            "equity": 10000.0,
            "margin": 0.0,
            "free_margin": 10000.0,
            "margin_level": 0.0,
            "profit": 0.0,
            "server": "Demo-Server",
            "currency": "USD",
            "trade_allowed": True,
            "trade_mode": None,
            "leverage": 100  # Add missing leverage field
        }

        # Enhanced symbol list with precious metals
        self.demo_symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "XAGUSD"]
        self.demo_positions = []
        self.demo_prices = {} # Initialize to prevent error in _update_demo_data if _initialize_demo_prices is not called first

        # Initialize demo prices with realistic values
        self._initialize_demo_prices()

        # Statistics
        self.start_time = datetime.now()
        self.update_count = 0
        self.signal_count = 0
        self.last_signals = {}
        self.refresh_interval = 5 # seconds

    def _initialize_demo_prices(self):
        """Initialize realistic demo prices."""
        base_prices = {
            "EURUSD": 1.0850,
            "GBPUSD": 1.2700,
            "USDJPY": 149.80,
            "AUDUSD": 0.6450,
            "USDCAD": 1.3600,
            "XAUUSD": 2025.50,
            "XAGUSD": 24.75
        }

        self.demo_prices = {}
        for symbol, base_price in base_prices.items():
            # Add some random variation
            price = base_price + random.uniform(-base_price * 0.0005, base_price * 0.0005)

            # Calculate spread
            if symbol == "XAUUSD":
                spread = 0.50
            elif symbol == "XAGUSD":
                spread = 0.03
            elif "JPY" in symbol:
                spread = 0.020
            else:
                spread = 0.00020

            self.demo_prices[symbol] = {
                "mid": price,
                "bid": price - spread/2,
                "ask": price + spread/2,
                "spread": spread,
                "time": datetime.now()
            }
        # Store initial prices for _update_demo_prices
        self.symbol_prices = self.demo_prices.copy()


    def initialize(self) -> bool:
        """Initialize the trading bot."""
        try:
            # Setup logging
            setup_logging()
            self.logger.info("🚀 Starting MT5 Trading Bot Console Demo...")

            # Run diagnostics
            self.logger.info("🔍 Running startup diagnostics...")
            if not run_startup_diagnostics():
                self.logger.error("❌ Startup diagnostics failed")
                return False

            if self.demo_mode:
                self.logger.warning("💡 Running in DEMO MODE with simulated data")
                self._initialize_demo_mode()
            else:
                self.logger.info("🔌 Connecting to MetaTrader 5...")
                self.mt5_client = MT5Client()
                if not self.mt5_client.connect():
                    self.logger.warning("⚠️ MT5 connection failed - switching to demo mode")
                    self.demo_mode = True
                    self._initialize_demo_mode()
                else:
                    self.logger.info("✅ MT5 connected successfully")
                    self.trade_engine = TradeEngine(self.mt5_client)

            self.logger.info("✅ Trading bot initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {str(e)}")
            return False

    def _initialize_demo_mode(self):
        """Initialize demo mode components."""
        self.logger.info("🎭 Initializing demo mode components...")

        # Create mock MT5 client for demo
        class MockMT5Client:
            def __init__(self, parent_bot):
                self.connected = True
                self.parent = parent_bot
                # This needs to be initialized before being used by get_account_info
                self.symbol_prices = parent_bot.demo_prices.copy()

            def get_account_info(self):
                return {
                    "login": self.parent.demo_account.get("login", "Demo Account"),
                    "balance": self.parent.demo_account["balance"],
                    "equity": self.parent.demo_account["equity"],
                    "margin": self.parent.demo_account["margin"],
                    "free_margin": self.parent.demo_account["free_margin"],
                    "margin_level": self.parent.demo_account.get("margin_level", 0.0),
                    "profit": self.parent.demo_account.get("profit", 0.0),
                    "leverage": self.parent.demo_account["leverage"], # This was missing in the original mock
                    "server": self.parent.demo_account.get("server", "Demo-Server"),
                    "currency": self.parent.demo_account.get("currency", "USD"),
                    "trade_allowed": self.parent.demo_account.get("trade_allowed", True)
                }

            def get_symbol_info(self, symbol):
                if symbol in self.symbol_prices:
                    point = 0.00001 if "JPY" not in symbol else 0.001
                    if symbol in ["XAUUSD", "XAGUSD"]:
                        point = 0.01
                    
                    # Convert spread to pips for display
                    spread_pips = self.symbol_prices[symbol]["spread"]
                    if "JPY" in symbol:
                        spread_pips = spread_pips / 0.01
                    elif symbol in ["XAUUSD", "XAGUSD"]:
                        spread_pips = spread_pips
                    else:
                        spread_pips = spread_pips / 0.0001
                    
                    return {
                        "symbol": symbol,
                        "spread": spread_pips,
                        "point": point
                    }
                return None

            def get_current_price(self, symbol):
                if symbol in self.symbol_prices:
                    price_data = self.symbol_prices[symbol]
                    return {
                        "symbol": symbol,
                        "bid": price_data["bid"],
                        "ask": price_data["ask"],
                        "spread": price_data["spread"],
                        "time": price_data.get("time", datetime.now())
                    }
                return None

            def get_positions(self):
                return self.parent.demo_positions.copy()

            def disconnect(self):
                self.connected = False

            # Add get_historical_data for demo mode
            def get_historical_data(self, symbol: str, timeframe: str, count: int) -> Optional[pd.DataFrame]:
                """Generate mock historical data with valid OHLC structure."""
                try:
                    base_price = self.symbol_prices[symbol]["bid"]
                    dates = pd.date_range(end=datetime.now(), periods=count, freq='1min')

                    # Generate realistic OHLC data with proper validation
                    np.random.seed(hash(symbol) % 2**32)  # Different seed per symbol

                    opens = []
                    highs = []
                    lows = []
                    closes = []

                    current_price = base_price

                    for i in range(count):
                        # Generate price movement
                        change = np.random.normal(0, base_price * 0.0001)  # Small realistic movements

                        # Generate OHLC for this candle
                        open_price = current_price
                        close_price = current_price + change

                        # Ensure high >= max(open, close) and low <= min(open, close)
                        high_spread = abs(np.random.normal(0, base_price * 0.00005))
                        low_spread = abs(np.random.normal(0, base_price * 0.00005))

                        high_price = max(open_price, close_price) + high_spread
                        low_price = min(open_price, close_price) - low_spread

                        # Ensure all prices are positive and realistic
                        open_price = max(0.00001, open_price)
                        high_price = max(0.00001, high_price)
                        low_price = max(0.00001, low_price)
                        close_price = max(0.00001, close_price)

                        # Validate OHLC logic
                        high_price = max(high_price, open_price, close_price)
                        low_price = min(low_price, open_price, close_price)

                        opens.append(open_price)
                        highs.append(high_price)
                        lows.append(low_price)
                        closes.append(close_price)

                        current_price = close_price

                    df = pd.DataFrame({
                        'open': opens,
                        'high': highs,
                        'low': lows,
                        'close': closes,
                        'tick_volume': np.random.randint(50, 200, count)
                    }, index=dates)

                    # Final validation to ensure OHLC integrity
                    df = df[
                        (df['high'] >= df['open']) &
                        (df['high'] >= df['close']) &
                        (df['low'] <= df['open']) &
                        (df['low'] <= df['close']) &
                        (df['open'] > 0) &
                        (df['high'] > 0) &
                        (df['low'] > 0) &
                        (df['close'] > 0)
                    ]

                    if len(df) < count * 0.8:  # If too much data was filtered out
                        self.parent_bot.logger.warning(f"⚠️ Generated data quality low for {symbol}, regenerating...")
                        return self.get_historical_data(symbol, timeframe, count)

                    return df

                except Exception as e:
                    self.parent_bot.logger.error(f"❌ Demo historical data error: {str(e)}")
                    return None

        self.mt5_client = MockMT5Client(self)
        self.trade_engine = TradeEngine(self.mt5_client)
        # Ensure symbol_prices is initialized in MockMT5Client for strategy analysis if needed
        if hasattr(self.mt5_client, 'symbol_prices'):
            self.symbol_prices = self.mt5_client.symbol_prices


    def _print_header(self):
        """Print console header."""
        print("\n" + "=" * 80)
        print("             🚀 MT5 TRADING BOT - LIVE CONSOLE DASHBOARD 🚀")
        print("=" * 80)

        if self.demo_mode:
            print("                    ⚠️  DEMO MODE - SIMULATED DATA ⚠️")
            print("=" * 80)

    def _print_account_info(self):
        """Print account information."""
        try:
            # Get account info
            account_info = self.mt5_client.get_account_info() if hasattr(self, 'mt5_client') else None
            if account_info:
                print(f"📊 ACCOUNT INFORMATION")
                print(f"   Login:        {account_info['login']}")
                print(f"   Server:       {account_info['server']}")
                print(f"   Balance:      ${account_info['balance']:,.2f} {account_info['currency']}")
                print(f"   Equity:       ${account_info['equity']:,.2f} {account_info['currency']}")
                print(f"   Margin:       ${account_info['margin']:,.2f} {account_info['currency']}")
                print(f"   Free Margin:  ${account_info['free_margin']:,.2f} {account_info['currency']}")
                print(f"   Margin Level: {account_info['margin_level']:.2f}%")
                # Handle missing leverage field gracefully
                leverage = account_info.get('leverage', 'Unknown')
                if leverage != 'Unknown':
                    print(f"   Leverage:     1:{leverage}")
                else:
                    print(f"   Leverage:     Not Available")
                print(f"   Trading Allowed: {'Yes' if account_info['trade_allowed'] else 'No'}")
            else:
                print("📊 ACCOUNT INFORMATION")
                print("   Status: Unable to retrieve account information")

        except Exception as e:
            self.logger.error(f"Error getting account info: {str(e)}")
            print("📊 ACCOUNT INFORMATION")
            print("   Status: Error retrieving account information")


    def _print_market_data(self):
        """Print current market data."""
        print(f"\n💹 MARKET DATA (Real-time)")
        print(f"{'Symbol':<10} {'Bid':<10} {'Ask':<10} {'Spread':<8} {'Time':<12}")
        print("-" * 60)

        for symbol in self.demo_symbols:
            try:
                price_info = self.mt5_client.get_current_price(symbol)
                if price_info:
                    bid = price_info.get('bid', 0)
                    ask = price_info.get('ask', 0)
                    spread_raw = price_info.get('spread', 0)

                    # Calculate spread in pips for display
                    symbol_info = self.mt5_client.get_symbol_info(symbol)
                    if symbol_info:
                        spread_display = f"{symbol_info.get('spread', 0):.1f}"
                    else:
                        # Fallback calculation
                        if symbol == "XAUUSD" or symbol == "XAGUSD":
                            spread_display = f"{spread_raw:.2f}"
                        elif "JPY" in symbol:
                            spread_display = f"{spread_raw / 0.01:.1f}"
                        else:
                            spread_display = f"{spread_raw / 0.0001:.1f}"

                    time_str = price_info.get('time', datetime.now()).strftime("%H:%M:%S")

                    print(f"{symbol:<10} {bid:<10.5f} {ask:<10.5f} {spread_display:<8} {time_str:<12}")

            except KeyError as e:
                self.logger.error(f"Missing key in price data for {symbol}: {str(e)}")
                print(f"{symbol:<10} {'KeyError':<10} {'KeyError':<10} {'N/A':<8} {'N/A':<12}")
            except Exception as e:
                self.logger.error(f"Error fetching price for {symbol}: {str(e)}")
                print(f"{symbol:<10} {'Error':<10} {'Error':<10} {'N/A':<8} {'N/A':<12}")

    def _print_positions(self):
        """Print current positions."""
        try:
            positions = self.mt5_client.get_positions()

            print(f"\n📈 OPEN POSITIONS ({len(positions)})")
            if positions:
                print(f"{'Symbol':<10} {'Type':<6} {'Volume':<8} {'Price':<10} {'Profit':<10} {'Time':<12}")
                print("-" * 70)

                for pos in positions:
                    pos_type = "BUY" if pos.get('type', 0) == 0 else "SELL"
                    volume = pos.get('volume', 0)
                    price = pos.get('price_open', 0)
                    profit = pos.get('profit', 0)
                    time_str = pos.get('time', datetime.now()).strftime("%H:%M:%S")
                    symbol = pos.get('symbol', 'Unknown')

                    print(f"{symbol:<10} {pos_type:<6} {volume:<8.2f} {price:<10.5f} {profit:<10.2f} {time_str:<12}")
            else:
                print("   No open positions")

        except Exception as e:
            self.logger.error(f"Error getting positions: {str(e)}")
            print("   Error retrieving positions")

    def _print_strategy_signals(self):
        """Print strategy analysis and signals."""
        print(f"\n📊 STRATEGY ANALYSIS")
        print(f"{'Symbol':<10} {'Action':<8} {'Confidence':<12} {'Strength':<10} {'Timestamp'}")
        print("-" * 70)

        analyzed_count = 0
        strategy_signals = []
        for symbol in self.demo_symbols:
            try:
                # Get historical data with timeout protection
                df = self.mt5_client.get_historical_data(symbol, "M1", 100)
                if df is not None and len(df) > 50:
                    # Validate data before strategy analysis
                    if self._validate_dataframe(df, symbol):
                        signal = self.strategy.generate_signal(df, symbol)
                        strategy_signals.append((symbol, signal))
                        analyzed_count += 1
                    else:
                        self.logger.warning(f"⚠️ Invalid data structure for {symbol}")
                        strategy_signals.append((symbol, {"signal": "INVALID_DATA", "confidence": 0.0}))
                else:
                    self.logger.debug(f"📊 Insufficient data for {symbol}: {len(df) if df is not None else 0} bars")
                    strategy_signals.append((symbol, {"signal": "NO_DATA", "confidence": 0.0}))
            except (ValueError, TypeError) as e:
                self.logger.error(f"❌ Data error for {symbol}: {str(e)}")
                strategy_signals.append((symbol, {"signal": "DATA_ERROR", "confidence": 0.0}))
            except Exception as e:
                self.logger.error(f"❌ Strategy error for {symbol}: {str(e)}")
                strategy_signals.append((symbol, {"signal": "ERROR", "confidence": 0.0}))

        # Process and print signals
        for symbol, signal_result in strategy_signals:
            if signal_result and signal_result.get('signal'):
                action = signal_result.get('signal', 'HOLD')
                confidence = signal_result.get('confidence', 0)
                # Use ATR from a dummy context for strength if available, otherwise 0
                strength = signal_result.get('market_context', {}).get('atr', 0)
                timestamp = datetime.now().strftime("%H:%M:%S")

                self.last_signals[symbol] = {
                    'action': action,
                    'confidence': confidence,
                    'strength': strength,
                    'timestamp': timestamp
                }

                print(f"   {symbol:<10} {action:<8} {confidence:<12.1f} {strength:<10.2f} {timestamp}")
                if action != 'HOLD':
                    pass # Signal count updated below
                analyzed_count += 1
            else:
                print(f"   {symbol:<10} {'HOLD':<8} {'0.0':<12} {'0.00':<10} {'N/A'}")

        if analyzed_count == 0:
            print("   No symbols analyzed.")

        # Signal statistics with better error handling
        valid_signals = [s for _, s in strategy_signals if s.get("signal") not in ["HOLD", "NO_DATA", "ERROR", "INVALID_DATA"]]
        total_signals = len(valid_signals)
        self.signal_count += total_signals

        # Track error rates
        error_signals = len([s for _, s in strategy_signals if s.get("signal") in ["ERROR", "INVALID_DATA"]])
        if error_signals > 0:
            self.logger.warning(f"⚠️ {error_signals}/{len(strategy_signals)} symbols had analysis errors")

    def _print_statistics(self):
        """Print bot statistics."""
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds

        print(f"\n📈 BOT STATISTICS")
        print(f"   Uptime:       {uptime_str}")
        print(f"   Updates:      {self.update_count}")
        print(f"   Signals Found:{self.signal_count}")
        print(f"   Mode:         {'DEMO' if self.demo_mode else 'LIVE'}")
        print(f"   Status:       {'🟢 RUNNING' if self.running else '🔴 STOPPED'}")

    def _print_controls(self):
        """Print control instructions."""
        print(f"\n🎮 CONTROLS")
        print(f"   Ctrl+C:       Stop the bot")
        print(f"   Auto-refresh: Every {self.refresh_interval} seconds")

    def _update_demo_prices(self):
        """Update demo data with realistic changes."""
        if self.demo_mode:
            # Update prices with small random movements
            for symbol in self.symbol_prices:
                current_bid = self.symbol_prices[symbol]["bid"]
                current_spread = self.symbol_prices[symbol]["spread"]

                # Different volatility for different instrument types
                if "XAU" in symbol:  # Gold
                    volatility = 0.0002  # 0.02%
                    min_spread = 0.5
                elif "XAG" in symbol:  # Silver
                    volatility = 0.0003  # 0.03%
                    min_spread = 0.03
                else:  # Forex
                    volatility = 0.0001  # 0.01%
                    min_spread = 0.00020  # 2 pips

                change_percent = np.random.normal(0, volatility)
                new_bid = current_bid * (1 + change_percent)

                # Ensure minimum price and proper spread
                new_bid = max(0.00001, new_bid)
                new_ask = new_bid + min_spread

                self.symbol_prices[symbol] = {
                    "mid": (new_bid + new_ask) / 2,
                    "bid": round(new_bid, 5),
                    "ask": round(new_ask, 5),
                    "spread": min_spread,
                    "time": datetime.now()
                }

            # Simulate account changes (simplified)
            if self.demo_positions:
                total_profit = sum(pos.get('profit', 0) for pos in self.demo_positions)
                self.demo_account['equity'] = self.demo_account['balance'] + total_profit
                # Simulate margin level changes based on equity and margin used
                total_margin_used = sum(pos.get('margin', 0) for pos in self.demo_positions)
                self.demo_account['margin'] = total_margin_used
                self.demo_account['free_margin'] = self.demo_account['equity'] - total_margin_used
                if total_margin_used > 0:
                    self.demo_account['margin_level'] = (self.demo_account['equity'] / total_margin_used) * 100
                else:
                    self.demo_account['margin_level'] = 0.0
            else: # Reset account stats if no positions
                self.demo_account['equity'] = self.demo_account['balance']
                self.demo_account['margin'] = 0.0
                self.demo_account['free_margin'] = self.demo_account['equity']
                self.demo_account['margin_level'] = 0.0


    def run(self):
        """Run the console demo."""
        try:
            self.running = True

            # Setup signal handler for graceful shutdown
            def signal_handler(sig, frame):
                self.logger.info("📱 Shutdown signal received...")
                self.running = False

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            self.logger.info("✅ Console demo started - Press Ctrl+C to stop")

            error_count = 0
            max_errors = 10

            while self.running:
                try:
                    start_time = time.time()

                    # System health check with connection monitoring
                    if not self._health_check():
                        self.logger.warning("⚠️ System health check failed, attempting recovery...")
                        if not self._attempt_recovery():
                            self.logger.error("❌ Recovery failed, continuing with limited functionality")
                            # Log connection status for monitoring
                            if hasattr(self, 'mt5_client'):
                                connection_status = getattr(self.mt5_client, 'connected', False)
                                self.logger.warning(f"🔗 Connection status: {'Connected' if connection_status else 'Disconnected'}")

                    # Clear screen and print header
                    self._clear_screen()
                    self._print_header()

                    # Update demo prices
                    self._update_demo_prices()

                    # Display sections
                    self._print_account_info()
                    self._print_market_data()
                    self._print_positions()
                    self._print_strategy_signals()
                    self._print_statistics()
                    self._print_controls()

                    # Reset error count on successful iteration
                    error_count = 0

                    # Calculate sleep time to maintain consistent refresh rate
                    elapsed = time.time() - start_time
                    sleep_time = max(0, self.refresh_interval - elapsed)
                    time.sleep(sleep_time)

                except Exception as loop_error:
                    error_count += 1
                    self.logger.error(f"❌ Dashboard loop error {error_count}/{max_errors}: {str(loop_error)}")

                    if error_count >= max_errors:
                        self.logger.critical("🚨 Too many consecutive errors, shutting down")
                        break

                    time.sleep(min(error_count, 5))  # Progressive delay

        except KeyboardInterrupt:
            self.logger.info("📱 Shutdown signal received...")
        except Exception as e:
            self.logger.error(f"❌ Dashboard error: {str(e)}")
        finally:
            self.shutdown()

    def _clear_screen(self):
        """Clear the console screen."""
        os.system('clear' if os.name == 'posix' else 'cls')

    def _health_check(self) -> bool:
        """Perform system health check."""
        try:
            # Check if MT5 client is responsive
            if hasattr(self, 'mt5_client') and hasattr(self.mt5_client, 'connected'):
                if not self.mt5_client.connected:
                    return False

            # Check if strategy is working by validating a dummy dataframe
            if hasattr(self, 'strategy'):
                test_df = pd.DataFrame({
                    'open': [1.0, 1.0],
                    'high': [1.1, 1.1],
                    'low': [0.9, 0.9],
                    'close': [1.0, 1.0],
                    'tick_volume': [100, 100]
                })
                if not self._validate_dataframe(test_df, "TEST_SYMBOL"):
                    self.logger.warning("Strategy validation failed for test data.")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"❌ Health check error: {str(e)}")
            return False

    def _attempt_recovery(self) -> bool:
        """Attempt system recovery."""
        try:
            self.logger.info("🔄 Attempting system recovery...")

            # Reinitialize demo mode if it's enabled and MT5 client exists
            if self.demo_mode and hasattr(self, 'mt5_client') and isinstance(self.mt5_client, MockMT5Client):
                try:
                    self._initialize_demo_mode()
                    self.logger.info("✅ Demo mode reinitialized")
                    return True
                except Exception as e:
                    self.logger.error(f"❌ Demo mode recovery failed: {str(e)}")

            # Try to reconnect MT5 if not in demo mode and MT5 client exists
            elif not self.demo_mode and hasattr(self, 'mt5_client') and not isinstance(self.mt5_client, MockMT5Client):
                try:
                    # Assuming MT5Client has an auto_reconnect method
                    if hasattr(self.mt5_client, 'auto_reconnect'):
                        if self.mt5_client.auto_reconnect():
                            self.logger.info("✅ MT5 reconnection successful")
                            return True
                    # If no auto_reconnect, try a manual reconnect
                    elif self.mt5_client.connect():
                         self.logger.info("✅ MT5 manual reconnection successful")
                         return True
                except Exception as e:
                    self.logger.error(f"❌ MT5 reconnection failed: {str(e)}")

            return False

        except Exception as e:
            self.logger.error(f"❌ Recovery attempt failed: {str(e)}")
            return False

    def _validate_dataframe(self, df, symbol):
        """Validate DataFrame structure for strategy analysis."""
        try:
            if df is None or df.empty:
                return False

            required_columns = ['open', 'high', 'low', 'close', 'tick_volume']
            if not all(col in df.columns for col in required_columns):
                self.logger.warning(f"DataFrame missing required columns: {required_columns}")
                return False

            # Check for valid OHLC relationships
            if ((df['high'] < df['low']) |
                (df['high'] < df['open']) |
                (df['high'] < df['close']) |
                (df['low'] > df['open']) |
                (df['low'] > df['close'])).any():
                self.logger.warning("DataFrame contains invalid OHLC relationships.")
                return False

            # Check for positive values
            if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
                self.logger.warning("DataFrame contains non-positive prices.")
                return False

            return True

        except Exception as e:
            self.logger.error(f"❌ DataFrame validation error for {symbol}: {str(e)}")
            return False


    def shutdown(self):
        """Shutdown the trading bot."""
        try:
            self.running = False
            self.logger.info("🔄 Shutting down trading bot...")

            if self.mt5_client and hasattr(self.mt5_client, 'disconnect'):
                self.mt5_client.disconnect()

            self.logger.info("✅ Trading bot shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")

    # Placeholder for _cleanup if needed in the future, currently shutdown handles it.
    def _cleanup(self):
        self.shutdown()


def main():
    """Main entry point."""
    bot = TradingBotConsoleDemo()

    try:
        if bot.initialize():
            bot.run()
        else:
            print("❌ Failed to initialize trading bot")
            return 1

    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())