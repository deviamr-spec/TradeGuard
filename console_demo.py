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

        # Enhanced demo data with realistic values
        self.demo_account = {
            "login": 12345678,
            "server": "Demo-Server",
            "balance": 10000.0,
            "equity": 10000.0,
            "margin": 0.0,
            "free_margin": 10000.0,
            "margin_level": 0.0,
            "profit": 0.0,
            "currency": "USD",
            "trade_allowed": True,
            "leverage": 100
        }

        # Enhanced symbol list with precious metals
        self.demo_symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "XAGUSD"]
        self.demo_positions = []
        self.demo_prices = {}

        # Initialize demo prices with realistic values
        self._initialize_demo_prices()

        # Statistics
        self.start_time = datetime.now()
        self.update_count = 0
        self.signal_count = 0
        self.last_signals = {}

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
            price = base_price + random.uniform(-base_price * 0.001, base_price * 0.001)

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
                "spread": spread
            }

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

            def get_account_info(self):
                return {
                    "balance": self.parent.demo_account["balance"],
                    "equity": self.parent.demo_account["equity"],
                    "margin": self.parent.demo_account["margin"],
                    "free_margin": self.parent.demo_account["free_margin"],
                    "leverage": self.parent.demo_account["leverage"],
                    "name": self.parent.demo_account.get("login", "Demo Account"),
                    "server": self.parent.demo_account.get("server", "Demo-Server"),
                    "currency": self.parent.demo_account.get("currency", "USD"),
                    "trade_allowed": self.parent.demo_account.get("trade_allowed", True)
                }

            def get_symbol_info(self, symbol):
                if symbol in self.parent.demo_prices:
                    point = 0.00001 if "JPY" not in symbol else 0.001
                    if symbol in ["XAUUSD", "XAGUSD"]:
                        point = 0.01
                    return {
                        "symbol": symbol,
                        "spread": self.parent.demo_prices[symbol]["spread"],
                        "point": point
                    }
                return None

            def get_current_price(self, symbol):
                if symbol in self.parent.demo_prices:
                    price_data = self.parent.demo_prices[symbol]
                    return {
                        "symbol": symbol,
                        "bid": price_data["bid"],
                        "ask": price_data["ask"],
                        "time": datetime.now()
                    }
                return None

            def get_positions(self):
                return self.parent.demo_positions.copy()

            def disconnect(self):
                self.connected = False

        self.mt5_client = MockMT5Client(self)
        self.trade_engine = TradeEngine(self.mt5_client)

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
            account_info = self.mt5_client.get_account_info()

            print(f"\n📊 ACCOUNT INFORMATION")
            print(f"   Login:        {account_info.get('login', 'N/A')}")
            print(f"   Server:       {account_info.get('server', 'N/A')}")
            print(f"   Balance:      ${account_info.get('balance', 0):,.2f} {account_info.get('currency', 'USD')}")
            print(f"   Equity:       ${account_info.get('equity', 0):,.2f} {account_info.get('currency', 'USD')}")
            print(f"   Margin:       ${account_info.get('margin', 0):,.2f} {account_info.get('currency', 'USD')}")
            print(f"   Free Margin:  ${account_info.get('free_margin', 0):,.2f} {account_info.get('currency', 'USD')}")
            print(f"   Margin Level: {account_info.get('margin_level', 0):,.2f}%")
            print(f"   Leverage:     1:{account_info.get('leverage', 0)}")
            print(f"   Trading Allowed: {'Yes' if account_info.get('trade_allowed', False) else 'No'}")

        except Exception as e:
            self.logger.error(f"Error getting account info: {str(e)}")

    def _print_market_data(self):
        """Print current market data."""
        print(f"\n💹 MARKET DATA (Real-time)")
        print(f"{'Symbol':<10} {'Bid':<10} {'Ask':<10} {'Spread':<8} {'Time':<12}")
        print("-" * 60)

        for symbol in self.demo_symbols:
            try:
                price_info = self.mt5_client.get_current_price(symbol)
                if price_info:
                    bid = price_info['bid']
                    ask = price_info['ask']

                    # Calculate spread in pips for display
                    symbol_info = self.mt5_client.get_symbol_info(symbol)
                    if symbol_info:
                        spread_value = symbol_info.get('spread', 0)
                        if symbol == "XAUUSD" or symbol == "XAGUSD":
                            spread_display = f"{spread_value:.2f}"
                        elif "JPY" in symbol:
                            spread_display = f"{spread_value / 0.01:.1f}"
                        else:
                            spread_display = f"{spread_value / 0.0001:.1f}"
                    else:
                        spread_display = "N/A"

                    time_str = price_info['time'].strftime("%H:%M:%S")

                    print(f"{symbol:<10} {bid:<10.5f} {ask:<10.5f} {spread_display:<8} {time_str:<12}")

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
        for symbol in self.demo_symbols:
            try:
                # Fetch historical data for analysis
                # In a real scenario, this would fetch data from MT5
                # For demo, we'll create dummy data based on current prices
                current_price_info = self.mt5_client.get_current_price(symbol)
                if not current_price_info:
                    print(f"   {symbol:<10} {'N/A':<8} {'N/A':<12} {'N/A':<10} {'N/A'}")
                    continue

                # Create a dummy DataFrame simulating recent price data
                # This is a placeholder; real strategy would need proper historical data
                dates = pd.date_range(end=datetime.now(), periods=50, freq='1min')
                base_close = current_price_info['bid']
                # Simulate some price variation
                prices = [base_close * (1 + random.uniform(-0.0005, 0.0005)) for _ in range(50)]
                highs = [price * (1 + random.uniform(0, 0.0002)) for price in prices]
                lows = [price * (1 - random.uniform(0, 0.0002)) for price in prices]
                opens = [base_close * (1 + random.uniform(-0.0003, 0.0003)) for _ in range(50)]
                
                df = pd.DataFrame({
                    'open': opens,
                    'high': highs,
                    'low': lows,
                    'close': prices,
                    'tick_volume': [random.randint(50, 200) for _ in range(50)]
                }, index=dates)

                signal_result = self.strategy.generate_signal(df, symbol)

                if signal_result:
                    action = signal_result.get('action', 'HOLD')
                    confidence = signal_result.get('confidence', 0)
                    strength = signal_result.get('strength', 0)
                    timestamp = datetime.now().strftime("%H:%M:%S")

                    self.last_signals[symbol] = {
                        'action': action,
                        'confidence': confidence,
                        'strength': strength,
                        'timestamp': timestamp
                    }

                    print(f"   {symbol:<10} {action:<8} {confidence:<12.1f} {strength:<10.2f} {timestamp}")
                    if action != 'HOLD':
                        self.signal_count += 1
                    analyzed_count += 1
                else:
                    print(f"   {symbol:<10} {'HOLD':<8} {'N/A':<12} {'N/A':<10} {'N/A'}")

            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {str(e)}")
                print(f"   {symbol:<10} {'ERROR':<8} {'N/A':<12} {'N/A':<10} {'N/A'}")

        if analyzed_count == 0:
            print("   No symbols analyzed.")


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
        print(f"   Auto-refresh: Every 5 seconds")

    def _update_demo_data(self):
        """Update demo data with realistic changes."""
        if self.demo_mode:
            # Update prices with realistic simulation
            for symbol in self.demo_symbols:
                if symbol not in self.demo_prices:
                    self._initialize_demo_prices()

                # Simulate price movement
                current_price = self.demo_prices[symbol]["mid"]

                # Random walk with some trend
                change = random.uniform(-0.0001, 0.0001)
                if symbol == "XAUUSD":  # Gold has larger movements
                    change *= 10
                elif "JPY" in symbol:
                    change *= 100

                new_price = current_price + change

                # Calculate spread based on symbol type
                if symbol == "XAUUSD":
                    spread = 0.50  # $0.50 spread for gold
                elif symbol == "XAGUSD":
                    spread = 0.03  # $0.03 spread for silver
                elif "JPY" in symbol:
                    spread = 0.020  # 2 pip spread for JPY pairs
                else:
                    spread = 0.00020  # 2 pip spread for major pairs

                bid = new_price - spread/2
                ask = new_price + spread/2

                self.demo_prices[symbol] = {
                    "mid": new_price,
                    "bid": bid,
                    "ask": ask,
                    "spread": spread
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

            while self.running:
                try:
                    # Clear screen (works on most terminals)
                    os.system('clear' if os.name == 'posix' else 'cls')

                    # Update demo data
                    self._update_demo_data()

                    # Print dashboard
                    self._print_header()
                    self._print_account_info()
                    self._print_market_data()
                    self._print_positions()
                    self._print_strategy_signals()
                    self._print_statistics()
                    self._print_controls()

                    print(f"\n🔄 Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                    self.update_count += 1

                    # Wait before next update
                    time.sleep(5)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"Error in main loop: {str(e)}")
                    time.sleep(1) # Prevent rapid error logging on persistent issues

        except Exception as e:
            self.logger.error(f"❌ Console demo failed: {str(e)}")
        finally:
            self.shutdown()

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