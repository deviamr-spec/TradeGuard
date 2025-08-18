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

class ConsoleTradingBot:
    """Console-based trading bot demonstration."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.running = False
        self.mt5_client = None
        self.trade_engine = None
        self.demo_mode = not MT5_AVAILABLE
        
        # Demo data for simulation
        self.demo_account = {
            "balance": 10000.0,
            "equity": 10000.0,
            "margin": 0.0,
            "free_margin": 10000.0,
            "leverage": 100
        }
        
        self.demo_positions = []
        self.demo_symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
        self.demo_prices = {
            "EURUSD": 1.0850,
            "GBPUSD": 1.2650,
            "USDJPY": 150.25,
            "AUDUSD": 0.6475,
            "USDCAD": 1.3625
        }
        
        # Statistics
        self.start_time = datetime.now()
        self.update_count = 0
        self.signal_count = 0
        
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
                    "name": "Demo Account",
                    "server": "Demo-Server",
                    "currency": "USD"
                }
            
            def get_symbol_info(self, symbol):
                if symbol in self.parent.demo_prices:
                    return {
                        "symbol": symbol,
                        "spread": 2.0,
                        "point": 0.00001 if "JPY" not in symbol else 0.001
                    }
                return None
            
            def get_current_price(self, symbol):
                if symbol in self.parent.demo_prices:
                    base_price = self.parent.demo_prices[symbol]
                    # Add small random fluctuation
                    fluctuation = np.random.uniform(-0.0010, 0.0010)
                    return {
                        "symbol": symbol,
                        "bid": base_price + fluctuation,
                        "ask": base_price + fluctuation + 0.0002,
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
            print(f"   Balance:      ${account_info.get('balance', 0):,.2f}")
            print(f"   Equity:       ${account_info.get('equity', 0):,.2f}")
            print(f"   Margin:       ${account_info.get('margin', 0):,.2f}")
            print(f"   Free Margin:  ${account_info.get('free_margin', 0):,.2f}")
            print(f"   Leverage:     1:{account_info.get('leverage', 0)}")
            
            if not self.demo_mode:
                print(f"   Name:         {account_info.get('name', 'N/A')}")
                print(f"   Server:       {account_info.get('server', 'N/A')}")
                
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
                    spread = (ask - bid) * (10000 if "JPY" not in symbol else 100)
                    time_str = price_info['time'].strftime("%H:%M:%S")
                    
                    print(f"{symbol:<10} {bid:<10.5f} {ask:<10.5f} {spread:<8.1f} {time_str:<12}")
                    
            except Exception as e:
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
        try:
            print(f"\n📊 STRATEGY ANALYSIS (EMA/RSI Scalping)")
            
            strategy = ScalpingStrategy()
            
            # Generate sample data for demo
            for symbol in self.demo_symbols[:3]:  # Show first 3 symbols
                try:
                    # Create sample price data
                    dates = pd.date_range(end=datetime.now(), periods=100, freq='1min')
                    base_price = self.demo_prices[symbol]
                    
                    # Generate realistic price movements
                    returns = np.random.normal(0, 0.0001, 100)
                    prices = [base_price]
                    for ret in returns[1:]:
                        prices.append(prices[-1] * (1 + ret))
                    
                    df = pd.DataFrame({
                        'timestamp': dates,
                        'close': prices,
                        'high': [p * 1.0002 for p in prices],
                        'low': [p * 0.9998 for p in prices],
                        'open': prices
                    })
                    
                    # Get strategy signal
                    signal = strategy.generate_signal(df, symbol)
                    
                    if signal and signal.get('action') != 'HOLD':
                        action = signal['action']
                        confidence = signal.get('confidence', 0)
                        strength = signal.get('strength', 0)
                        
                        print(f"   {symbol}: {action} (Confidence: {confidence:.1f}%, Strength: {strength:.2f})")
                        self.signal_count += 1
                    else:
                        print(f"   {symbol}: HOLD (No clear signal)")
                        
                except Exception as e:
                    print(f"   {symbol}: Analysis error")
                    
        except Exception as e:
            self.logger.error(f"Error in strategy analysis: {str(e)}")
    
    def _print_statistics(self):
        """Print bot statistics."""
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        print(f"\n📈 BOT STATISTICS")
        print(f"   Uptime:       {uptime_str}")
        print(f"   Updates:      {self.update_count}")
        print(f"   Signals:      {self.signal_count}")
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
            # Update prices with small random movements
            for symbol in self.demo_prices:
                change = np.random.uniform(-0.0005, 0.0005)
                self.demo_prices[symbol] *= (1 + change)
                
            # Simulate account changes
            if self.demo_positions:
                total_profit = sum(pos.get('profit', 0) for pos in self.demo_positions)
                self.demo_account['equity'] = self.demo_account['balance'] + total_profit
    
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
                    time.sleep(1)
            
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
    bot = ConsoleTradingBot()
    
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