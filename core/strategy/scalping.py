"""
EMA/RSI Scalping Strategy Implementation.
Uses EMA crossover with RSI confirmation for entry signals.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from core.config import config
from utils.logging_setup import get_logger

class ScalpingStrategy:
    """EMA/RSI scalping strategy for high-frequency trading."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Strategy parameters from config
        self.ema_fast = config.get("strategy.ema_fast", 12)
        self.ema_slow = config.get("strategy.ema_slow", 26)
        self.rsi_period = config.get("strategy.rsi_period", 14)
        self.rsi_overbought = config.get("strategy.rsi_overbought", 70.0)
        self.rsi_oversold = config.get("strategy.rsi_oversold", 30.0)
        
        # Strategy state
        self.last_signals = {}  # Track last signals per symbol
        self.signal_history = {}  # Keep signal history for analysis
        
        self.logger.info(f"📊 Scalping strategy initialized:")
        self.logger.info(f"   EMA Fast: {self.ema_fast}, EMA Slow: {self.ema_slow}")
        self.logger.info(f"   RSI Period: {self.rsi_period}")
        self.logger.info(f"   RSI Levels: {self.rsi_oversold}-{self.rsi_overbought}")
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average.
        
        Args:
            data: Price data series
            period: EMA period
            
        Returns:
            EMA series
        """
        return data.ewm(span=period).mean()
    
    def calculate_rsi(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Relative Strength Index.
        
        Args:
            data: Price data series
            period: RSI period
            
        Returns:
            RSI series
        """
        try:
            delta = data.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"❌ RSI calculation error: {str(e)}")
            return pd.Series(index=data.index, dtype=float)
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            DataFrame with added indicators
        """
        try:
            # Calculate EMAs
            df['ema_fast'] = self.calculate_ema(df['close'], self.ema_fast)
            df['ema_slow'] = self.calculate_ema(df['close'], self.ema_slow)
            
            # Calculate RSI
            df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
            
            # Calculate EMA signal
            df['ema_signal'] = np.where(df['ema_fast'] > df['ema_slow'], 1, -1)
            df['ema_cross'] = df['ema_signal'].diff()
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Indicator calculation error: {str(e)}")
            return df
    
    def analyze_market_conditions(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Analyze current market conditions.
        
        Args:
            df: DataFrame with indicators
            symbol: Trading symbol
            
        Returns:
            Market analysis results
        """
        try:
            if len(df) < max(self.ema_slow, self.rsi_period):
                return {"valid": False, "reason": "Insufficient data"}
            
            current = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else current
            
            # Market trend analysis
            trend = "BULLISH" if current['ema_fast'] > current['ema_slow'] else "BEARISH"
            trend_strength = abs(current['ema_fast'] - current['ema_slow']) / current['close'] * 100
            
            # Volatility analysis (using recent price range)
            recent_data = df.tail(20)
            volatility = (recent_data['high'].max() - recent_data['low'].min()) / recent_data['close'].mean() * 100
            
            # RSI momentum
            rsi_momentum = "OVERSOLD" if current['rsi'] < self.rsi_oversold else \
                          "OVERBOUGHT" if current['rsi'] > self.rsi_overbought else "NEUTRAL"
            
            analysis = {
                "valid": True,
                "symbol": symbol,
                "timestamp": datetime.now(),
                "trend": trend,
                "trend_strength": trend_strength,
                "volatility": volatility,
                "rsi_value": current['rsi'],
                "rsi_momentum": rsi_momentum,
                "ema_fast": current['ema_fast'],
                "ema_slow": current['ema_slow'],
                "current_price": current['close']
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ Market analysis error for {symbol}: {str(e)}")
            return {"valid": False, "reason": f"Analysis error: {str(e)}"}
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Generate trading signal based on EMA/RSI strategy.
        
        Args:
            df: DataFrame with price data and indicators
            symbol: Trading symbol
            
        Returns:
            Signal dictionary
        """
        try:
            # Calculate indicators
            df = self.calculate_indicators(df)
            
            # Analyze market conditions
            market_analysis = self.analyze_market_conditions(df, symbol)
            if not market_analysis["valid"]:
                return {
                    "symbol": symbol,
                    "signal": "NONE",
                    "confidence": 0.0,
                    "reason": market_analysis.get("reason", "Invalid analysis"),
                    "timestamp": datetime.now()
                }
            
            if len(df) < 3:  # Need at least 3 bars for signal generation
                return {
                    "symbol": symbol,
                    "signal": "NONE",
                    "confidence": 0.0,
                    "reason": "Insufficient data for signal",
                    "timestamp": datetime.now()
                }
            
            current = df.iloc[-1]
            previous = df.iloc[-2]
            
            signal = "NONE"
            confidence = 0.0
            reason = "No signal conditions met"
            
            # Check for EMA crossover signals
            ema_cross_bullish = (current['ema_fast'] > current['ema_slow'] and 
                               previous['ema_fast'] <= previous['ema_slow'])
            ema_cross_bearish = (current['ema_fast'] < current['ema_slow'] and 
                               previous['ema_fast'] >= previous['ema_slow'])
            
            # RSI confirmation
            rsi_supports_buy = current['rsi'] < 70 and current['rsi'] > 30  # Not overbought
            rsi_supports_sell = current['rsi'] > 30 and current['rsi'] < 70  # Not oversold
            
            # Strong trend confirmation
            trend_strength = market_analysis["trend_strength"]
            volatility = market_analysis["volatility"]
            
            # Buy signal conditions
            if (ema_cross_bullish and rsi_supports_buy):
                signal = "BUY"
                confidence = min(90.0, 60.0 + trend_strength * 10 + (50 - current['rsi']) * 0.5)
                reason = "EMA bullish crossover with RSI confirmation"
                
            # Sell signal conditions  
            elif (ema_cross_bearish and rsi_supports_sell):
                signal = "SELL"
                confidence = min(90.0, 60.0 + trend_strength * 10 + (current['rsi'] - 50) * 0.5)
                reason = "EMA bearish crossover with RSI confirmation"
                
            # Additional signal filters
            if signal != "NONE":
                # Filter by volatility (avoid trading in very low volatility)
                if volatility < 0.1:
                    signal = "NONE"
                    confidence = 0.0
                    reason = "Low volatility - no trade"
                    
                # Filter by trend strength
                elif trend_strength < 0.01:
                    confidence *= 0.5  # Reduce confidence for weak trends
                    
                # Check for conflicting signals from previous analysis
                last_signal = self.last_signals.get(symbol, {})
                if (last_signal.get("signal") == signal and 
                    (datetime.now() - last_signal.get("timestamp", datetime.min)).seconds < 300):
                    signal = "NONE"
                    confidence = 0.0
                    reason = "Recent similar signal - avoiding duplicate"
            
            # Create signal result
            signal_result = {
                "symbol": symbol,
                "signal": signal,
                "confidence": confidence,
                "reason": reason,
                "timestamp": datetime.now(),
                "market_analysis": market_analysis,
                "entry_price": current['close'],
                "indicators": {
                    "ema_fast": current['ema_fast'],
                    "ema_slow": current['ema_slow'],
                    "rsi": current['rsi']
                }
            }
            
            # Store signal for future reference
            self.last_signals[symbol] = signal_result
            
            # Add to signal history
            if symbol not in self.signal_history:
                self.signal_history[symbol] = []
            self.signal_history[symbol].append(signal_result)
            
            # Keep only recent history (last 100 signals)
            if len(self.signal_history[symbol]) > 100:
                self.signal_history[symbol] = self.signal_history[symbol][-100:]
            
            if signal != "NONE":
                self.logger.info(f"📊 {symbol} Signal: {signal} (Confidence: {confidence:.1f}%) - {reason}")
            
            return signal_result
            
        except Exception as e:
            self.logger.error(f"❌ Signal generation error for {symbol}: {str(e)}")
            return {
                "symbol": symbol,
                "signal": "NONE",
                "confidence": 0.0,
                "reason": f"Error: {str(e)}",
                "timestamp": datetime.now()
            }
    
    def calculate_position_size(self, signal: Dict[str, Any], account_balance: float, 
                              symbol_info: Dict[str, Any]) -> Tuple[float, float, float]:
        """
        Calculate position size, stop loss, and take profit levels.
        
        Args:
            signal: Trading signal
            account_balance: Current account balance
            symbol_info: Symbol information
            
        Returns:
            Tuple of (lot_size, stop_loss, take_profit)
        """
        try:
            risk_per_trade = config.get("risk.risk_per_trade", 0.01)
            tp_pips = config.get("strategy.take_profit_pips", 10.0)
            sl_pips = config.get("strategy.stop_loss_pips", 5.0)
            
            # Calculate risk amount
            risk_amount = account_balance * risk_per_trade
            
            # Get symbol info
            point = symbol_info.get("point", 0.00001)
            pip_value = symbol_info.get("pip_value", 1.0)
            min_lot = symbol_info.get("volume_min", 0.01)
            max_lot = symbol_info.get("volume_max", 1.0)
            
            # Calculate lot size based on risk
            pip_risk = sl_pips * pip_value
            lot_size = risk_amount / pip_risk if pip_risk > 0 else min_lot
            
            # Ensure lot size is within limits
            lot_size = max(min_lot, min(lot_size, max_lot))
            lot_size = round(lot_size / min_lot) * min_lot  # Round to lot step
            
            # Calculate SL and TP levels
            entry_price = signal["entry_price"]
            
            if signal["signal"] == "BUY":
                stop_loss = entry_price - (sl_pips * point * 10)
                take_profit = entry_price + (tp_pips * point * 10)
            else:  # SELL
                stop_loss = entry_price + (sl_pips * point * 10)
                take_profit = entry_price - (tp_pips * point * 10)
            
            self.logger.debug(f"📊 Position sizing for {signal['symbol']}:")
            self.logger.debug(f"   Risk Amount: ${risk_amount:.2f}")
            self.logger.debug(f"   Lot Size: {lot_size}")
            self.logger.debug(f"   SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
            
            return lot_size, stop_loss, take_profit
            
        except Exception as e:
            self.logger.error(f"❌ Position sizing error: {str(e)}")
            # Return safe defaults
            return config.get("risk.min_lot_size", 0.01), 0.0, 0.0
    
    def get_strategy_stats(self, symbol: str = None) -> Dict[str, Any]:
        """
        Get strategy performance statistics.
        
        Args:
            symbol: Specific symbol stats (None for all symbols)
            
        Returns:
            Strategy statistics
        """
        try:
            if symbol:
                history = self.signal_history.get(symbol, [])
                symbols = [symbol]
            else:
                history = []
                symbols = list(self.signal_history.keys())
                for sym in symbols:
                    history.extend(self.signal_history[sym])
            
            if not history:
                return {"no_data": True}
            
            # Calculate basic stats
            total_signals = len(history)
            buy_signals = len([s for s in history if s["signal"] == "BUY"])
            sell_signals = len([s for s in history if s["signal"] == "SELL"])
            
            # Average confidence
            avg_confidence = np.mean([s["confidence"] for s in history if s["signal"] != "NONE"])
            
            # Recent activity (last 24 hours)
            recent_signals = [s for s in history if 
                            (datetime.now() - s["timestamp"]).total_seconds() < 86400]
            
            stats = {
                "total_signals": total_signals,
                "buy_signals": buy_signals,
                "sell_signals": sell_signals,
                "avg_confidence": avg_confidence,
                "recent_signals_24h": len(recent_signals),
                "symbols_analyzed": len(symbols),
                "last_signal_time": max([s["timestamp"] for s in history]) if history else None
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"❌ Strategy stats error: {str(e)}")
            return {"error": str(e)}
