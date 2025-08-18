
#!/usr/bin/env python3
"""
Console Demo for MT5 Trading Bot
Displays real-time trading data and bot status in terminal format.
Enhanced with robust error handling and demo mode support.
"""

import sys
import os
import time
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logging_setup import setup_logging, get_logger
from core.mt5_client import MT5Client
from core.trade_engine import TradeEngine
from core.strategy.scalping import ScalpingStrategy

class ConsoleTradingBot:
    """Console-based trading bot interface."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.running = False
        self.mt5_client = None
        self.trade_engine = None
        self.strategy = None
        self.start_time = datetime.now()
        self.update_count = 0
        self.signals_found = 0
        
    def initialize(self) -> bool:
        """Initialize bot components."""
        try:
            # Setup logging
            setup_logging()
            
            # Initialize MT5 client
            self.mt5_client = MT5Client()
            if not self.mt5_client.connect():
                self.logger.error("❌ Failed to initialize MT5 client")
                return False
            
            # Initialize strategy
            self.strategy = ScalpingStrategy()
            
            # Initialize trade engine
            self.trade_engine = TradeEngine(self.mt5_client)
            if not self.trade_engine.start():
                self.logger.warning("⚠️ Trade engine start issues")
            
            self.running = True
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {str(e)}")
            return False
    
    def display_header(self):
        """Display console header."""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("=" * 80)
        print("             🚀 MT5 TRADING BOT - LIVE CONSOLE DASHBOARD 🚀")
        print("=" * 80)
        
        if getattr(self.mt5_client, 'demo_mode', False):
            print("                    ⚠️  DEMO MODE - SIMULATED DATA ⚠️")
        else:
            print("                    💰 LIVE MODE - REAL TRADING 💰")
        print("=" * 80)
    
    def display_account_info(self):
        """Display account information."""
        try:
            account_info = self.mt5_client.get_account_info()
            if not account_info:
                print("❌ Account information unavailable")
                return
            
            print("📊 ACCOUNT INFORMATION")
            print(f"   Login:        {account_info.get('login', 'N/A')}")
            print(f"   Server:       {account_info.get('server', 'N/A')}")
            print(f"   Balance:      ${account_info.get('balance', 0):,.2f} {account_info.get('currency', 'USD')}")
            print(f"   Equity:       ${account_info.get('equity', 0):,.2f} {account_info.get('currency', 'USD')}")
            print(f"   Margin:       ${account_info.get('margin', 0):,.2f} {account_info.get('currency', 'USD')}")
            print(f"   Free Margin:  ${account_info.get('free_margin', 0):,.2f} {account_info.get('currency', 'USD')}")
            
            margin_level = account_info.get('margin_level', 0)
            if margin_level > 0:
                print(f"   Margin Level: {margin_level:.2f}%")
            else:
                print(f"   Margin Level: ∞%")
                
            print(f"   Leverage:     1:{account_info.get('leverage', 100)}")
            print(f"   Trading Allowed: {'Yes' if account_info.get('trade_allowed', True) else 'No'}")
            print()
            
        except Exception as e:
            print(f"❌ Account info error: {str(e)}")
    
    def display_market_data(self):
        """Display market data."""
        try:
            symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "XAGUSD"]
            
            print("💹 MARKET DATA (Real-time)")
            print("Symbol     Bid        Ask        Spread   Time        ")
            print("-" * 60)
            
            for symbol in symbols:
                try:
                    tick_data = self.mt5_client.get_tick_data(symbol)
                    if tick_data:
                        spread = tick_data['spread']
                        time_str = tick_data['time'].strftime("%H:%M:%S")
                        
                        print(f"{symbol:<10} {tick_data['bid']:<10.5f} {tick_data['ask']:<10.5f} "
                              f"{spread:<8.1f} {time_str:<12}")
                    else:
                        print(f"{symbol:<10} {'N/A':<10} {'N/A':<10} {'N/A':<8} {'N/A':<12}")
                        
                except Exception as e:
                    print(f"{symbol:<10} ERROR: {str(e)[:30]}")
            print()
            
        except Exception as e:
            print(f"❌ Market data error: {str(e)}")
    
    def display_positions(self):
        """Display open positions."""
        try:
            positions = self.mt5_client.get_positions()
            
            print(f"📈 OPEN POSITIONS ({len(positions)})")
            
            if not positions:
                print("   No open positions")
            else:
                print("Symbol     Type   Volume   Entry     Current   Profit    Time")
                print("-" * 70)
                
                for pos in positions:
                    time_str = pos['time'].strftime("%H:%M:%S")
                    print(f"{pos['symbol']:<10} {pos['type']:<6} {pos['volume']:<8.2f} "
                          f"{pos['price_open']:<9.5f} {pos['price_current']:<9.5f} "
                          f"{pos['profit']:<9.2f} {time_str}")
            print()
            
        except Exception as e:
            print(f"❌ Positions error: {str(e)}")
    
    def display_strategy_analysis(self):
        """Display strategy analysis."""
        try:
            symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "XAGUSD"]
            
            print("📊 STRATEGY ANALYSIS")
            print("Symbol     Action   Confidence   Strength   Timestamp")
            print("-" * 70)
            
            for symbol in symbols:
                try:
                    # Get historical data
                    df = self.mt5_client.get_historical_data(symbol, "M1", 100)
                    if df is not None and len(df) >= 50:
                        # Generate signal
                        signal = self.strategy.generate_signal(df, symbol)
                        if signal:
                            action = signal.get('signal', 'HOLD')
                            confidence = signal.get('confidence', 0.0)
                            strength = signal.get('strength', 0.0)
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            
                            print(f"   {symbol:<10} {action:<8} {confidence:<12.1f} {strength:<10.2f} {timestamp}")
                            
                            if action in ['BUY', 'SELL']:
                                self.signals_found += 1
                        else:
                            print(f"   {symbol:<10} {'HOLD':<8} {0.0:<12.1f} {0.00:<10.2f} {datetime.now().strftime('%H:%M:%S')}")
                    else:
                        print(f"   {symbol:<10} {'HOLD':<8} {0.0:<12.1f} {0.00:<10.2f} {datetime.now().strftime('%H:%M:%S')}")
                        
                except Exception as e:
                    print(f"   {symbol:<10} ERROR: {str(e)[:40]}")
            print()
            
        except Exception as e:
            print(f"❌ Strategy analysis error: {str(e)}")
    
    def display_bot_statistics(self):
        """Display bot statistics."""
        try:
            uptime = datetime.now() - self.start_time
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds
            
            mode = "DEMO" if getattr(self.mt5_client, 'demo_mode', False) else "LIVE"
            status = "🟢 RUNNING" if self.running else "🔴 STOPPED"
            
            print("📈 BOT STATISTICS")
            print(f"   Uptime:       {uptime_str}")
            print(f"   Updates:      {self.update_count}")
            print(f"   Signals Found:{self.signals_found}")
            print(f"   Mode:         {mode}")
            print(f"   Status:       {status}")
            print()
            
        except Exception as e:
            print(f"❌ Statistics error: {str(e)}")
    
    def display_controls(self):
        """Display control information."""
        print("🎮 CONTROLS")
        print("   Ctrl+C:       Stop the bot")
        print("   Auto-refresh: Every 5 seconds")
    
    def run_dashboard(self):
        """Run the main dashboard loop."""
        try:
            while self.running:
                try:
                    # Display dashboard
                    self.display_header()
                    self.display_account_info()
                    self.display_market_data()
                    self.display_positions()
                    self.display_strategy_analysis()
                    self.display_bot_statistics()
                    self.display_controls()
                    
                    self.update_count += 1
                    
                    # Wait for next update
                    time.sleep(5)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"❌ Dashboard error: {str(e)}")
                    time.sleep(2)
                    
        except Exception as e:
            self.logger.error(f"❌ Dashboard fatal error: {str(e)}")
    
    def shutdown(self):
        """Shutdown the bot."""
        try:
            self.logger.info("📱 Shutdown signal received...")
            self.running = False
            
            if self.trade_engine:
                self.trade_engine.stop()
            
            if self.mt5_client:
                self.mt5_client.disconnect()
                
            self.logger.info("✅ Trading bot shutdown complete")
            
        except Exception as e:
            self.logger.error(f"❌ Shutdown error: {str(e)}")

def signal_handler(signum, frame):
    """Handle shutdown signal."""
    print("\n📱 Shutdown signal received...")
    sys.exit(0)

def main():
    """Main entry point."""
    try:
        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create and run bot
        bot = ConsoleTradingBot()
        
        if not bot.initialize():
            print("❌ Failed to initialize trading bot")
            return 1
        
        try:
            bot.run_dashboard()
        except KeyboardInterrupt:
            pass
        finally:
            bot.shutdown()
        
        return 0
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
