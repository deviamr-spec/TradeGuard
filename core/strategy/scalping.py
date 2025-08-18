
"""
Enhanced EMA/RSI Scalping Strategy with Advanced Market Analysis.
Includes trend detection, candle structure analysis, and confidence-based signals.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from core.config import config
from utils.logging_setup import get_logger

class ScalpingStrategy:
    """Enhanced EMA/RSI scalping strategy with advanced market analysis."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Strategy parameters from config
        self.ema_fast = config.get("strategy.ema_fast", 12)
        self.ema_slow = config.get("strategy.ema_slow", 26)
        self.rsi_period = config.get("strategy.rsi_period", 14)
        self.rsi_overbought = config.get("strategy.rsi_overbought", 70.0)
        self.rsi_oversold = config.get("strategy.rsi_oversold", 30.0)
        
        # Enhanced parameters
        self.atr_period = 14
        self.bb_period = 20
        self.bb_std = 2.0
        self.stoch_k = 14
        self.stoch_d = 3
        
        # Strategy state
        self.last_signals = {}
        self.signal_history = {}
        self.market_context = {}
        
        self.logger.info(f"📊 Enhanced Scalping strategy initialized:")
        self.logger.info(f"   EMA Fast: {self.ema_fast}, EMA Slow: {self.ema_slow}")
        self.logger.info(f"   RSI Period: {self.rsi_period}")
        self.logger.info(f"   ATR Period: {self.atr_period}")
        self.logger.info(f"   Bollinger Bands: {self.bb_period} periods, {self.bb_std} std")
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return data.ewm(span=period).mean()
    
    def calculate_rsi(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Relative Strength Index."""
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
    
    def calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range."""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
            
            return atr
            
        except Exception as e:
            self.logger.error(f"❌ ATR calculation error: {str(e)}")
            return pd.Series(index=df.index, dtype=float)
    
    def calculate_bollinger_bands(self, data: pd.Series, period: int, std_dev: float) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        try:
            sma = data.rolling(window=period).mean()
            std = data.rolling(window=period).std()
            
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            
            return upper, sma, lower
            
        except Exception as e:
            self.logger.error(f"❌ Bollinger Bands calculation error: {str(e)}")
            return pd.Series(index=data.index, dtype=float), pd.Series(index=data.index, dtype=float), pd.Series(index=data.index, dtype=float)
    
    def calculate_stochastic(self, df: pd.DataFrame, k_period: int, d_period: int) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator."""
        try:
            low_min = df['low'].rolling(window=k_period).min()
            high_max = df['high'].rolling(window=k_period).max()
            
            k = 100 * ((df['close'] - low_min) / (high_max - low_min))
            d = k.rolling(window=d_period).mean()
            
            return k, d
            
        except Exception as e:
            self.logger.error(f"❌ Stochastic calculation error: {str(e)}")
            return pd.Series(index=df.index, dtype=float), pd.Series(index=df.index, dtype=float)
    
    def analyze_candle_patterns(self, df: pd.DataFrame) -> Dict[str, bool]:
        """Analyze candlestick patterns."""
        try:
            if len(df) < 3:
                return {}
            
            current = df.iloc[-1]
            prev = df.iloc[-2]
            prev2 = df.iloc[-3] if len(df) > 2 else prev
            
            # Basic candle properties
            body = abs(current['close'] - current['open'])
            total_range = current['high'] - current['low']
            upper_shadow = current['high'] - max(current['close'], current['open'])
            lower_shadow = min(current['close'], current['open']) - current['low']
            
            body_ratio = body / total_range if total_range > 0 else 0
            
            patterns = {
                # Bullish patterns
                'bullish_engulfing': (
                    current['close'] > current['open'] and
                    prev['close'] < prev['open'] and
                    current['open'] < prev['close'] and
                    current['close'] > prev['open']
                ),
                'hammer': (
                    body_ratio < 0.3 and
                    lower_shadow > body * 2 and
                    upper_shadow < body * 0.1
                ),
                'doji': (
                    body_ratio < 0.1
                ),
                'piercing_line': (
                    current['close'] > current['open'] and
                    prev['close'] < prev['open'] and
                    current['open'] < prev['low'] and
                    current['close'] > (prev['open'] + prev['close']) / 2
                ),
                
                # Bearish patterns
                'bearish_engulfing': (
                    current['close'] < current['open'] and
                    prev['close'] > prev['open'] and
                    current['open'] > prev['close'] and
                    current['close'] < prev['open']
                ),
                'shooting_star': (
                    body_ratio < 0.3 and
                    upper_shadow > body * 2 and
                    lower_shadow < body * 0.1
                ),
                'dark_cloud_cover': (
                    current['close'] < current['open'] and
                    prev['close'] > prev['open'] and
                    current['open'] > prev['high'] and
                    current['close'] < (prev['open'] + prev['close']) / 2
                ),
                
                # Continuation patterns
                'strong_bullish': (
                    current['close'] > current['open'] and
                    body_ratio > 0.7 and
                    current['close'] > prev['close']
                ),
                'strong_bearish': (
                    current['close'] < current['open'] and
                    body_ratio > 0.7 and
                    current['close'] < prev['close']
                )
            }
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"❌ Candle pattern analysis error: {str(e)}")
            return {}
    
    def analyze_trend_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze market trend structure."""
        try:
            if len(df) < 20:
                return {"trend": "UNKNOWN", "strength": 0.0}
            
            # Get recent data
            recent = df.tail(20)
            
            # Calculate trend indicators
            ema_fast = self.calculate_ema(recent['close'], 5)
            ema_slow = self.calculate_ema(recent['close'], 20)
            
            # Trend direction
            if ema_fast.iloc[-1] > ema_slow.iloc[-1]:
                if ema_fast.iloc[-1] > ema_fast.iloc[-5]:
                    trend = "STRONG_BULLISH"
                else:
                    trend = "BULLISH"
            elif ema_fast.iloc[-1] < ema_slow.iloc[-1]:
                if ema_fast.iloc[-1] < ema_fast.iloc[-5]:
                    trend = "STRONG_BEARISH"
                else:
                    trend = "BEARISH"
            else:
                trend = "SIDEWAYS"
            
            # Trend strength
            price_range = recent['high'].max() - recent['low'].min()
            ema_separation = abs(ema_fast.iloc[-1] - ema_slow.iloc[-1])
            strength = min(1.0, (ema_separation / recent['close'].iloc[-1]) * 100)
            
            # Higher highs and lower lows
            highs = recent['high'].rolling(3).max()
            lows = recent['low'].rolling(3).min()
            
            higher_highs = (highs.diff() > 0).sum()
            lower_lows = (lows.diff() < 0).sum()
            
            structure = {
                "trend": trend,
                "strength": strength,
                "higher_highs": higher_highs,
                "lower_lows": lower_lows,
                "price_range": price_range,
                "ema_separation": ema_separation
            }
            
            return structure
            
        except Exception as e:
            self.logger.error(f"❌ Trend structure analysis error: {str(e)}")
            return {"trend": "UNKNOWN", "strength": 0.0}
    
    def calculate_confidence(self, signals: Dict[str, Any], market_context: Dict[str, Any]) -> float:
        """Calculate signal confidence based on multiple factors."""
        try:
            confidence = 0.0
            factors = []
            
            # EMA alignment (20 points)
            if signals.get('ema_bullish'):
                confidence += 20
                factors.append("EMA Bullish")
            elif signals.get('ema_bearish'):
                confidence += 20
                factors.append("EMA Bearish")
            
            # RSI confirmation (15 points)
            rsi = market_context.get('rsi', 50)
            if 30 < rsi < 70:
                confidence += 15
                factors.append("RSI Optimal")
            elif rsi < 30:
                confidence += 10
                factors.append("RSI Oversold")
            elif rsi > 70:
                confidence += 10
                factors.append("RSI Overbought")
            
            # Trend structure (20 points)
            trend = market_context.get('trend_structure', {}).get('trend', 'UNKNOWN')
            if 'STRONG' in trend:
                confidence += 20
                factors.append("Strong Trend")
            elif trend != 'UNKNOWN':
                confidence += 10
                factors.append("Trend Identified")
            
            # Candle patterns (15 points)
            patterns = market_context.get('candle_patterns', {})
            bullish_patterns = ['bullish_engulfing', 'hammer', 'piercing_line', 'strong_bullish']
            bearish_patterns = ['bearish_engulfing', 'shooting_star', 'dark_cloud_cover', 'strong_bearish']
            
            if any(patterns.get(p, False) for p in bullish_patterns + bearish_patterns):
                confidence += 15
                factors.append("Candle Pattern")
            
            # Volatility (10 points)
            atr_ratio = market_context.get('atr_ratio', 1.0)
            if 0.5 < atr_ratio < 2.0:
                confidence += 10
                factors.append("Good Volatility")
            
            # Bollinger Bands position (10 points)
            bb_position = market_context.get('bb_position', 0.5)
            if bb_position < 0.2 or bb_position > 0.8:
                confidence += 10
                factors.append("BB Extreme")
            
            # Volume confirmation (10 points)
            if market_context.get('volume_above_average', False):
                confidence += 10
                factors.append("Volume Confirmation")
            
            self.logger.debug(f"Confidence factors: {factors}")
            return min(100.0, confidence)
            
        except Exception as e:
            self.logger.error(f"❌ Confidence calculation error: {str(e)}")
            return 0.0
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators."""
        try:
            # Basic EMAs
            df['ema_fast'] = self.calculate_ema(df['close'], self.ema_fast)
            df['ema_slow'] = self.calculate_ema(df['close'], self.ema_slow)
            
            # Additional EMAs
            df['ema_5'] = self.calculate_ema(df['close'], 5)
            df['ema_20'] = self.calculate_ema(df['close'], 20)
            df['ema_50'] = self.calculate_ema(df['close'], 50)
            
            # RSI
            df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
            df['rsi_9'] = self.calculate_rsi(df['close'], 9)
            
            # ATR
            df['atr'] = self.calculate_atr(df, self.atr_period)
            
            # Bollinger Bands
            df['bb_upper'], df['bb_middle'], df['bb_lower'] = self.calculate_bollinger_bands(
                df['close'], self.bb_period, self.bb_std
            )
            
            # Stochastic
            df['stoch_k'], df['stoch_d'] = self.calculate_stochastic(df, self.stoch_k, self.stoch_d)
            
            # MACD
            ema_12 = self.calculate_ema(df['close'], 12)
            ema_26 = self.calculate_ema(df['close'], 26)
            df['macd'] = ema_12 - ema_26
            df['macd_signal'] = self.calculate_ema(df['macd'], 9)
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Price action indicators
            df['body'] = abs(df['close'] - df['open'])
            df['total_range'] = df['high'] - df['low']
            df['body_ratio'] = df['body'] / df['total_range']
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Indicator calculation error: {str(e)}")
            return df
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Generate trading signal with enhanced analysis."""
        try:
            # Calculate indicators
            df = self.calculate_indicators(df)
            
            if len(df) < max(self.ema_slow, self.rsi_period, self.bb_period):
                return {
                    "symbol": symbol,
                    "signal": "NONE",
                    "confidence": 0.0,
                    "reason": "Insufficient data",
                    "timestamp": datetime.now()
                }
            
            current = df.iloc[-1]
            previous = df.iloc[-2]
            
            # Analyze market context
            candle_patterns = self.analyze_candle_patterns(df)
            trend_structure = self.analyze_trend_structure(df)
            
            # Calculate additional context
            atr_avg = df['atr'].rolling(20).mean().iloc[-1] if len(df) >= 20 else current['atr']
            atr_ratio = current['atr'] / atr_avg if atr_avg > 0 else 1.0
            
            bb_range = current['bb_upper'] - current['bb_lower']
            bb_position = (current['close'] - current['bb_lower']) / bb_range if bb_range > 0 else 0.5
            
            volume_avg = df['tick_volume'].rolling(20).mean().iloc[-1] if 'tick_volume' in df.columns and len(df) >= 20 else 1
            volume_above_average = current.get('tick_volume', 1) > volume_avg * 1.2
            
            market_context = {
                'candle_patterns': candle_patterns,
                'trend_structure': trend_structure,
                'rsi': current['rsi'],
                'rsi_9': current['rsi_9'],
                'atr_ratio': atr_ratio,
                'bb_position': bb_position,
                'volume_above_average': volume_above_average,
                'stoch_k': current['stoch_k'],
                'stoch_d': current['stoch_d'],
                'macd_histogram': current['macd_histogram']
            }
            
            # Generate signals
            signals = {}
            
            # EMA signals
            signals['ema_bullish'] = (
                current['ema_fast'] > current['ema_slow'] and
                previous['ema_fast'] <= previous['ema_slow']
            )
            signals['ema_bearish'] = (
                current['ema_fast'] < current['ema_slow'] and
                previous['ema_fast'] >= previous['ema_slow']
            )
            
            # RSI signals
            signals['rsi_oversold_recovery'] = current['rsi'] > 30 and previous['rsi'] <= 30
            signals['rsi_overbought_decline'] = current['rsi'] < 70 and previous['rsi'] >= 70
            
            # Bollinger Bands signals
            signals['bb_bounce_up'] = current['close'] > current['bb_lower'] and previous['close'] <= previous['bb_lower']
            signals['bb_bounce_down'] = current['close'] < current['bb_upper'] and previous['close'] >= previous['bb_upper']
            
            # MACD signals
            signals['macd_bullish'] = current['macd_histogram'] > 0 and previous['macd_histogram'] <= 0
            signals['macd_bearish'] = current['macd_histogram'] < 0 and previous['macd_histogram'] >= 0
            
            # Determine main signal
            signal = "NONE"
            reason = "No clear signal"
            
            # Bullish signals
            bullish_score = 0
            if signals['ema_bullish']: bullish_score += 3
            if signals['rsi_oversold_recovery']: bullish_score += 2
            if signals['bb_bounce_up']: bullish_score += 2
            if signals['macd_bullish']: bullish_score += 2
            if candle_patterns.get('bullish_engulfing'): bullish_score += 3
            if candle_patterns.get('hammer'): bullish_score += 2
            if trend_structure.get('trend') in ['BULLISH', 'STRONG_BULLISH']: bullish_score += 2
            
            # Bearish signals
            bearish_score = 0
            if signals['ema_bearish']: bearish_score += 3
            if signals['rsi_overbought_decline']: bearish_score += 2
            if signals['bb_bounce_down']: bearish_score += 2
            if signals['macd_bearish']: bearish_score += 2
            if candle_patterns.get('bearish_engulfing'): bearish_score += 3
            if candle_patterns.get('shooting_star'): bearish_score += 2
            if trend_structure.get('trend') in ['BEARISH', 'STRONG_BEARISH']: bearish_score += 2
            
            # Decision logic
            if bullish_score >= 5 and bullish_score > bearish_score:
                signal = "BUY"
                reason = f"Bullish confluence (score: {bullish_score})"
            elif bearish_score >= 5 and bearish_score > bullish_score:
                signal = "SELL"
                reason = f"Bearish confluence (score: {bearish_score})"
            
            # Calculate confidence
            confidence = self.calculate_confidence(signals, market_context)
            
            # Additional filters
            if signal != "NONE":
                # Volatility filter
                if atr_ratio < 0.5:
                    signal = "NONE"
                    reason = "Low volatility"
                    confidence = 0.0
                
                # Trend filter
                elif trend_structure.get('trend') == 'SIDEWAYS' and confidence < 70:
                    signal = "NONE"
                    reason = "Sideways market"
                    confidence = 0.0
                
                # Recent signal filter
                last_signal = self.last_signals.get(symbol, {})
                if (last_signal.get("signal") == signal and 
                    (datetime.now() - last_signal.get("timestamp", datetime.min)).seconds < 300):
                    signal = "NONE"
                    reason = "Recent similar signal"
                    confidence = 0.0
            
            # Create result
            signal_result = {
                "symbol": symbol,
                "signal": signal,
                "confidence": confidence,
                "reason": reason,
                "timestamp": datetime.now(),
                "entry_price": current['close'],
                "market_context": market_context,
                "signals": signals,
                "bullish_score": bullish_score,
                "bearish_score": bearish_score,
                "indicators": {
                    "ema_fast": current['ema_fast'],
                    "ema_slow": current['ema_slow'],
                    "rsi": current['rsi'],
                    "atr": current['atr'],
                    "bb_position": bb_position
                }
            }
            
            # Store signal
            self.last_signals[symbol] = signal_result
            
            # Add to history
            if symbol not in self.signal_history:
                self.signal_history[symbol] = []
            self.signal_history[symbol].append(signal_result)
            
            # Keep only recent history
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
        """Calculate position size with confidence-based adjustments."""
        try:
            risk_per_trade = config.get("risk.risk_per_trade", 0.01)
            tp_pips = config.get("strategy.take_profit_pips", 10.0)
            sl_pips = config.get("strategy.stop_loss_pips", 5.0)
            
            # Adjust risk based on confidence
            confidence_factor = signal["confidence"] / 100.0
            adjusted_risk = risk_per_trade * confidence_factor
            
            # Calculate risk amount
            risk_amount = account_balance * adjusted_risk
            
            # Get symbol info
            point = symbol_info.get("point", 0.00001)
            pip_value = symbol_info.get("pip_value", 1.0)
            min_lot = symbol_info.get("volume_min", 0.01)
            max_lot = symbol_info.get("volume_max", 1.0)
            
            # Adjust TP/SL based on market conditions
            market_context = signal.get("market_context", {})
            atr_ratio = market_context.get("atr_ratio", 1.0)
            
            # Dynamic TP/SL based on volatility
            if atr_ratio > 1.5:  # High volatility
                tp_pips *= 1.5
                sl_pips *= 1.2
            elif atr_ratio < 0.7:  # Low volatility
                tp_pips *= 0.8
                sl_pips *= 0.8
            
            # Calculate lot size
            pip_risk = sl_pips * pip_value
            lot_size = risk_amount / pip_risk if pip_risk > 0 else min_lot
            
            # Ensure lot size is within limits
            lot_size = max(min_lot, min(lot_size, max_lot))
            lot_size = round(lot_size / min_lot) * min_lot
            
            # Calculate SL and TP levels
            entry_price = signal["entry_price"]
            
            if signal["signal"] == "BUY":
                stop_loss = entry_price - (sl_pips * point * 10)
                take_profit = entry_price + (tp_pips * point * 10)
            else:  # SELL
                stop_loss = entry_price + (sl_pips * point * 10)
                take_profit = entry_price - (tp_pips * point * 10)
            
            self.logger.debug(f"📊 Enhanced position sizing for {signal['symbol']}:")
            self.logger.debug(f"   Confidence: {signal['confidence']:.1f}%")
            self.logger.debug(f"   Adjusted Risk: {adjusted_risk:.3f} (from {risk_per_trade:.3f})")
            self.logger.debug(f"   Lot Size: {lot_size}")
            self.logger.debug(f"   SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
            
            return lot_size, stop_loss, take_profit
            
        except Exception as e:
            self.logger.error(f"❌ Position sizing error: {str(e)}")
            return config.get("risk.min_lot_size", 0.01), 0.0, 0.0
    
    def get_strategy_stats(self, symbol: str = None) -> Dict[str, Any]:
        """Get enhanced strategy statistics."""
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
            
            # Calculate advanced stats
            total_signals = len(history)
            buy_signals = len([s for s in history if s["signal"] == "BUY"])
            sell_signals = len([s for s in history if s["signal"] == "SELL"])
            
            # Confidence statistics
            valid_signals = [s for s in history if s["signal"] != "NONE"]
            avg_confidence = np.mean([s["confidence"] for s in valid_signals]) if valid_signals else 0
            high_confidence_signals = len([s for s in valid_signals if s["confidence"] >= 70])
            
            # Signal quality analysis
            bullish_scores = [s.get("bullish_score", 0) for s in valid_signals]
            bearish_scores = [s.get("bearish_score", 0) for s in valid_signals]
            
            avg_bullish_score = np.mean(bullish_scores) if bullish_scores else 0
            avg_bearish_score = np.mean(bearish_scores) if bearish_scores else 0
            
            # Recent activity
            recent_signals = [s for s in history if 
                            (datetime.now() - s["timestamp"]).total_seconds() < 86400]
            
            stats = {
                "total_signals": total_signals,
                "buy_signals": buy_signals,
                "sell_signals": sell_signals,
                "valid_signals": len(valid_signals),
                "avg_confidence": avg_confidence,
                "high_confidence_signals": high_confidence_signals,
                "avg_bullish_score": avg_bullish_score,
                "avg_bearish_score": avg_bearish_score,
                "recent_signals_24h": len(recent_signals),
                "symbols_analyzed": len(symbols),
                "last_signal_time": max([s["timestamp"] for s in history]) if history else None,
                "confidence_distribution": {
                    "high": len([s for s in valid_signals if s["confidence"] >= 70]),
                    "medium": len([s for s in valid_signals if 40 <= s["confidence"] < 70]),
                    "low": len([s for s in valid_signals if s["confidence"] < 40])
                }
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"❌ Strategy stats error: {str(e)}")
            return {"error": str(e)}
