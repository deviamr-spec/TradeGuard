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

        # Strategy state
        self.last_signals = {}
        self.signal_history = {}
        self.market_context = {}

        self.logger.info(f"📊 Enhanced Scalping strategy initialized:")
        self.logger.info(f"   EMA Fast: {self.ema_fast}, EMA Slow: {self.ema_slow}")
        self.logger.info(f"   RSI Period: {self.rsi_period}")

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

    def _analyze_market_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Enhanced market structure and trend analysis with candle patterns."""
        try:
            if len(df) < 50:
                return {"trend": "SIDEWAYS", "strength": 0.0, "confidence": 50.0}

            # Price action analysis
            close_prices = df['close'].values
            high_prices = df['high'].values
            low_prices = df['low'].values
            open_prices = df['open'].values

            # Enhanced trend analysis using multiple EMAs
            ema_12 = self.calculate_ema(df['close'], 12)
            ema_26 = self.calculate_ema(df['close'], 26)
            ema_50 = self.calculate_ema(df['close'], 50)
            ema_200 = self.calculate_ema(df['close'], 200) if len(df) >= 200 else ema_50

            current_price = close_prices[-1]
            ema_12_current = ema_12.iloc[-1]
            ema_26_current = ema_26.iloc[-1]
            ema_50_current = ema_50.iloc[-1]
            ema_200_current = ema_200.iloc[-1]

            # Candle pattern analysis
            candle_patterns = self._analyze_candle_patterns(df)

            # Support/Resistance levels
            support_resistance = self._find_support_resistance(df)

            # Enhanced trend determination
            trend_score = 0

            # EMA alignment
            if ema_12_current > ema_26_current > ema_50_current > ema_200_current:
                trend_score += 4  # Strong bullish alignment
            elif ema_12_current > ema_26_current > ema_50_current:
                trend_score += 3  # Moderate bullish
            elif ema_12_current > ema_26_current:
                trend_score += 2  # Weak bullish
            elif ema_12_current < ema_26_current < ema_50_current < ema_200_current:
                trend_score -= 4  # Strong bearish alignment
            elif ema_12_current < ema_26_current < ema_50_current:
                trend_score -= 3  # Moderate bearish
            elif ema_12_current < ema_26_current:
                trend_score -= 2  # Weak bearish

            # Price position relative to EMAs
            if current_price > ema_12_current:
                trend_score += 1
            else:
                trend_score -= 1

            # Recent price momentum
            price_momentum = (current_price - close_prices[-10]) / close_prices[-10] * 100
            if price_momentum > 0.1:
                trend_score += 2
            elif price_momentum < -0.1:
                trend_score -= 2

            # Determine final trend
            if trend_score >= 4:
                trend = "STRONG_BULLISH"
            elif trend_score >= 2:
                trend = "BULLISH"
            elif trend_score <= -4:
                trend = "STRONG_BEARISH"
            elif trend_score <= -2:
                trend = "BEARISH"
            else:
                trend = "SIDEWAYS"

            # Enhanced strength calculation
            volatility = np.std(close_prices[-20:]) / np.mean(close_prices[-20:]) * 100

            # ATR-based strength
            atr_values = []
            for i in range(1, min(15, len(df))):
                high_low = high_prices[-i] - low_prices[-i]
                high_close = abs(high_prices[-i] - close_prices[-i-1])
                low_close = abs(low_prices[-i] - close_prices[-i-1])
                atr_values.append(max(high_low, high_close, low_close))

            atr = np.mean(atr_values) if atr_values else 0
            atr_strength = min((atr / current_price) * 10000, 100)  # Normalize ATR

            # Volume analysis (if available)
            volume_strength = 50.0  # Default if no volume data
            if 'tick_volume' in df.columns:
                recent_volume = df['tick_volume'].iloc[-10:].mean()
                avg_volume = df['tick_volume'].iloc[-50:-10].mean()
                if avg_volume > 0:
                    volume_strength = min((recent_volume / avg_volume) * 50, 100)

            # Combined strength
            base_strength = abs(trend_score) * 10
            final_strength = (base_strength + atr_strength + volume_strength) / 3

            # Enhanced confidence calculation
            consistency = self._calculate_trend_consistency(ema_12, ema_26, ema_50)
            pattern_confidence = candle_patterns.get("confidence", 50)
            volatility_penalty = min(volatility * 2, 30)  # Penalize high volatility

            confidence = max(30.0, min(95.0, 
                (consistency + pattern_confidence) / 2 - volatility_penalty))

            return {
                "trend": trend,
                "strength": final_strength,
                "confidence": confidence,
                "trend_score": trend_score,
                "volatility": volatility,
                "atr": atr,
                "ema_12": ema_12_current,
                "ema_26": ema_26_current,
                "ema_50": ema_50_current,
                "ema_200": ema_200_current,
                "candle_patterns": candle_patterns,
                "support_resistance": support_resistance,
                "volume_strength": volume_strength,
                "price_momentum": price_momentum
            }

        except Exception as e:
            self.logger.error(f"❌ Market structure analysis error: {str(e)}")
            return {"trend": "SIDEWAYS", "strength": 0.0, "confidence": 50.0}

    def _analyze_candle_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze candlestick patterns for additional confirmation."""
        try:
            if len(df) < 5:
                return {"patterns": [], "confidence": 50.0}

            patterns = []
            confidence = 50.0

            # Get last few candles
            last_candles = df.tail(5)

            for i in range(len(last_candles)):
                candle = last_candles.iloc[i]
                open_price = candle['open']
                high_price = candle['high']
                low_price = candle['low']
                close_price = candle['close']

                body_size = abs(close_price - open_price)
                total_range = high_price - low_price

                if total_range == 0:
                    continue

                body_ratio = body_size / total_range

                # Bullish patterns
                if close_price > open_price:  # Bullish candle
                    if body_ratio > 0.7:  # Strong bullish body
                        patterns.append("STRONG_BULLISH")
                        confidence += 5
                    elif body_ratio > 0.5:
                        patterns.append("BULLISH")
                        confidence += 3

                    # Hammer pattern (bullish reversal)
                    lower_shadow = open_price - low_price
                    upper_shadow = high_price - close_price
                    if lower_shadow > body_size * 2 and upper_shadow < body_size * 0.5:
                        patterns.append("HAMMER")
                        confidence += 8

                # Bearish patterns
                elif close_price < open_price:  # Bearish candle
                    if body_ratio > 0.7:  # Strong bearish body
                        patterns.append("STRONG_BEARISH")
                        confidence -= 5
                    elif body_ratio > 0.5:
                        patterns.append("BEARISH")
                        confidence -= 3

                    # Shooting star pattern (bearish reversal)
                    lower_shadow = open_price - low_price
                    upper_shadow = high_price - open_price
                    if upper_shadow > body_size * 2 and lower_shadow < body_size * 0.5:
                        patterns.append("SHOOTING_STAR")
                        confidence -= 8

                # Doji patterns (indecision)
                elif body_ratio < 0.1:
                    patterns.append("DOJI")
                    confidence -= 2  # Slight penalty for indecision

            # Multi-candle patterns
            if len(last_candles) >= 3:
                # Three white soldiers / Three black crows
                last_three = last_candles.tail(3)
                if all(candle['close'] > candle['open'] for _, candle in last_three.iterrows()):
                    if all(last_three.iloc[i]['close'] > last_three.iloc[i-1]['close'] 
                          for i in range(1, 3)):
                        patterns.append("THREE_WHITE_SOLDIERS")
                        confidence += 10
                elif all(candle['close'] < candle['open'] for _, candle in last_three.iterrows()):
                    if all(last_three.iloc[i]['close'] < last_three.iloc[i-1]['close'] 
                          for i in range(1, 3)):
                        patterns.append("THREE_BLACK_CROWS")
                        confidence -= 10

            return {
                "patterns": patterns,
                "confidence": max(20.0, min(80.0, confidence))
            }

        except Exception as e:
            self.logger.error(f"❌ Candle pattern analysis error: {str(e)}")
            return {"patterns": [], "confidence": 50.0}

    def _find_support_resistance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Find key support and resistance levels."""
        try:
            if len(df) < 20:
                return {"support": [], "resistance": [], "nearest_level": None}

            # Get highs and lows for pivot point analysis
            highs = df['high'].values
            lows = df['low'].values
            closes = df['close'].values

            current_price = closes[-1]

            # Find pivot highs and lows
            resistance_levels = []
            support_levels = []

            # Look for swing highs and lows in the last 50 periods
            period = min(50, len(df))

            for i in range(2, period - 2):
                # Swing high
                if (highs[-i] > highs[-i-1] and highs[-i] > highs[-i-2] and 
                    highs[-i] > highs[-i+1] and highs[-i] > highs[-i+2]):
                    resistance_levels.append(highs[-i])

                # Swing low
                if (lows[-i] < lows[-i-1] and lows[-i] < lows[-i-2] and 
                    lows[-i] < lows[-i+1] and lows[-i] < lows[-i+2]):
                    support_levels.append(lows[-i])

            # Filter and sort levels
            resistance_levels = sorted(list(set(resistance_levels)), reverse=True)[:5]
            support_levels = sorted(list(set(support_levels)), reverse=True)[:5]

            # Find nearest significant level
            all_levels = resistance_levels + support_levels
            if all_levels:
                nearest_level = min(all_levels, key=lambda x: abs(x - current_price))
                distance_pct = abs(nearest_level - current_price) / current_price * 100
            else:
                nearest_level = None
                distance_pct = None

            return {
                "support": support_levels,
                "resistance": resistance_levels,
                "nearest_level": nearest_level,
                "distance_to_nearest": distance_pct
            }

        except Exception as e:
            self.logger.error(f"❌ Support/Resistance analysis error: {str(e)}")
            return {"support": [], "resistance": [], "nearest_level": None}

    def _calculate_trend_consistency(self, ema_12: pd.Series, ema_26: pd.Series, ema_50: pd.Series) -> float:
        """Calculate how consistent the trend has been."""
        try:
            if len(ema_12) < 10:
                return 50.0

            # Check how often EMAs maintain their order
            consistent_periods = 0
            total_periods = min(20, len(ema_12))

            for i in range(total_periods):
                ema12_val = ema_12.iloc[-(i+1)]
                ema26_val = ema_26.iloc[-(i+1)]
                ema50_val = ema_50.iloc[-(i+1)]

                # Check for consistent bullish or bearish alignment
                if ((ema12_val > ema26_val > ema50_val) or 
                    (ema12_val < ema26_val < ema50_val)):
                    consistent_periods += 1

            consistency = (consistent_periods / total_periods) * 100
            return max(20.0, min(80.0, consistency))

        except Exception as e:
            return 50.0

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
            df['atr'] = self.calculate_atr(df, 14) # Defaulting ATR period to 14 as per common practice

            # Bollinger Bands
            df['bb_upper'], df['bb_middle'], df['bb_lower'] = self.calculate_bollinger_bands(
                df['close'], 20, 2.0 # Defaulting BB period to 20 and std dev to 2.0
            )

            # Stochastic
            df['stoch_k'], df['stoch_d'] = self.calculate_stochastic(df, 14, 3) # Defaulting Stochastic periods

            # MACD
            ema_12 = self.calculate_ema(df['close'], 12)
            ema_26 = self.calculate_ema(df['close'], 26)
            df['macd'] = ema_12 - ema_26
            df['macd_signal'] = self.calculate_ema(df['macd'], 9)
            df['macd_histogram'] = df['macd'] - df['macd_signal']

            # Price action indicators
            df['body'] = abs(df['close'] - df['open'])
            df['total_range'] = df['high'] - df['low']
            df['body_ratio'] = df['body'] / df['total_range'] if df['total_range'] > 0 else 0

            return df

        except Exception as e:
            self.logger.error(f"❌ Indicator calculation error: {str(e)}")
            return df

    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Generate trading signal with enhanced analysis."""
        try:
            # Calculate indicators
            df = self.calculate_indicators(df)

            # Define required data points for indicators
            required_data_points = {
                'ema_slow': self.ema_slow,
                'rsi': self.rsi_period,
                'bb_period': 20,
                'stoch_k': 14,
                'macd_signal': 9,
                'atr': 14,
                'ema_50': 50,
                'ema_200': 200
            }
            max_required = max(required_data_points.values()) if required_data_points else 0

            if len(df) < max_required:
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
            market_structure = self._analyze_market_structure(df)

            # --- Signal Generation Logic ---
            # Initialize signal components
            rsi_signal = "HOLD"
            rsi_confidence = 0.0
            ema_signal = "HOLD"
            ema_confidence = 0.0
            market_confidence = market_structure.get("confidence", 50.0)
            final_signal = "HOLD"
            auto_execute = False
            auto_trade_threshold = 75.0

            # RSI Signal Calculation
            if current['rsi'] < self.rsi_oversold:
                rsi_signal = "BUY"
                rsi_confidence = min(95.0, (30.0 - current['rsi']) / 30.0 * 100) # More oversold, higher confidence
                if previous['rsi'] is not None and previous['rsi'] <= self.rsi_oversold:
                    rsi_confidence = min(98.0, rsi_confidence * 1.1) # Recovery confirmation
            elif current['rsi'] > self.rsi_overbought:
                rsi_signal = "SELL"
                rsi_confidence = min(95.0, (current['rsi'] - 70.0) / 30.0 * 100) # More overbought, higher confidence
                if previous['rsi'] is not None and previous['rsi'] >= self.rsi_overbought:
                    rsi_confidence = min(98.0, rsi_confidence * 1.1) # Decline confirmation
            else:
                rsi_signal = "HOLD"
                rsi_confidence = 50.0

            # EMA Signal Calculation
            if current['ema_fast'] > current['ema_slow'] and previous['ema_fast'] <= previous['ema_slow']:
                ema_signal = "BUY"
                ema_confidence = 70.0
            elif current['ema_fast'] < current['ema_slow'] and previous['ema_fast'] >= previous['ema_slow']:
                ema_signal = "SELL"
                ema_confidence = 70.0
            else:
                ema_signal = "HOLD"
                ema_confidence = 50.0

            # Check for BB signals (optional - can be added as another factor)
            # bb_buy_signal = current['close'] > current['bb_lower'] and previous['close'] <= previous['bb_lower']
            # bb_sell_signal = current['close'] < current['bb_upper'] and previous['close'] >= previous['bb_upper']

            # Check for MACD signals (optional)
            macd_buy_signal = current['macd_histogram'] > 0 and previous['macd_histogram'] <= 0
            macd_sell_signal = current['macd_histogram'] < 0 and previous['macd_histogram'] >= 0

            # --- Combining Signals and Market Context ---

            # Price action context
            price_above_ema_fast = current['close'] > current['ema_fast']
            ema_alignment = "UP" if current['ema_fast'] > current['ema_slow'] else "DOWN" if current['ema_fast'] < current['ema_slow'] else "FLAT"
            bb_position = market_structure.get("bb_position", 0.5) # Get bb_position from market_structure if available

            # Risk metrics
            current_atr = current['atr']
            atr_risk = "NORMAL"
            if current_atr is not None and current_atr > 0:
                # Define risk thresholds based on ATR relative to price
                atr_threshold_high = (current['close'] * 0.01) # e.g., 1% of price
                if current_atr > atr_threshold_high:
                    atr_risk = "HIGH"

            # Enhanced signal determination with auto-decision capability
            if rsi_signal in ["BUY", "SELL"] and ema_signal == rsi_signal:
                final_signal = rsi_signal
                confidence = min(95.0, (rsi_confidence + ema_confidence + market_confidence) / 3)

                # Boost confidence for strong confirmations
                if market_structure["trend"] == "STRONG_BULLISH" and final_signal == "BUY":
                    confidence = min(98.0, confidence * 1.2)
                elif market_structure["trend"] == "STRONG_BEARISH" and final_signal == "SELL":
                    confidence = min(98.0, confidence * 1.2)

            elif rsi_signal in ["BUY", "SELL"] and market_structure["trend"] in ["STRONG_BULLISH", "STRONG_BEARISH"]:
                # Strong trend can override weak EMA signal
                if (rsi_signal == "BUY" and market_structure["trend"] == "STRONG_BULLISH") or \
                   (rsi_signal == "SELL" and market_structure["trend"] == "STRONG_BEARISH"):
                    final_signal = rsi_signal
                    confidence = min(88.0, (rsi_confidence + market_confidence) / 2)
            
            # Consider MACD signals if they align with other indicators
            elif macd_buy_signal and (rsi_signal == "BUY" or ema_signal == "BUY") and market_confidence > 60:
                final_signal = "BUY"
                confidence = min(85.0, (rsi_confidence + ema_confidence + market_confidence + 80) / 4) # Boost confidence
            elif macd_sell_signal and (rsi_signal == "SELL" or ema_signal == "SELL") and market_confidence > 60:
                final_signal = "SELL"
                confidence = min(85.0, (rsi_confidence + ema_confidence + market_confidence + 80) / 4) # Boost confidence

            elif market_structure["trend"] in ["STRONG_BULLISH", "STRONG_BEARISH"] and market_confidence > 80:
                # Very strong market trend with high confidence
                final_signal = "BUY" if market_structure["trend"] == "STRONG_BULLISH" else "SELL"
                confidence = min(85.0, market_confidence * 0.9)
            else:
                final_signal = "HOLD"
                confidence = max(20.0, min(40.0, (rsi_confidence + ema_confidence + market_confidence) / 6))

            # Auto-trading decision
            auto_execute = confidence >= auto_trade_threshold and final_signal in ["BUY", "SELL"]

            # --- Prepare Return Dictionary ---
            current_rsi = current['rsi']
            current_ema_fast = current['ema_fast']
            current_ema_slow = current['ema_slow']
            current_bb_upper = current['bb_upper']
            current_bb_lower = current['bb_lower']
            current_atr = current['atr']
            current_price = current['close']

            # Additional context for return dictionary
            reason = "No clear signal"
            if final_signal == "BUY":
                if rsi_signal == "BUY" and ema_signal == "BUY": reason = "RSI and EMA confluence"
                elif rsi_signal == "BUY": reason = "RSI bullish signal"
                elif ema_signal == "BUY": reason = "EMA bullish crossover"
                elif market_structure["trend"] == "STRONG_BULLISH": reason = "Strong bullish trend alignment"
            elif final_signal == "SELL":
                if rsi_signal == "SELL" and ema_signal == "SELL": reason = "RSI and EMA confluence"
                elif rsi_signal == "SELL": reason = "RSI bearish signal"
                elif ema_signal == "SELL": reason = "EMA bearish crossover"
                elif market_structure["trend"] == "STRONG_BEARISH": reason = "Strong bearish trend alignment"
            
            if auto_execute:
                reason = f"Auto-execute: {reason}"
            
            if final_signal == "HOLD":
                reason = market_structure.get("trend", "SIDEWAYS") # Use trend as reason for HOLD

            # Store signal for history and last signal
            signal_result = {
                "signal": final_signal,
                "confidence": confidence,
                "strength": market_structure.get("strength", 0.0),
                "symbol": symbol,
                "timestamp": datetime.now(),
                "auto_execute": auto_execute,
                "auto_threshold": auto_trade_threshold,
                "indicators": {
                    "rsi": current_rsi,
                    "ema_fast": current_ema_fast,
                    "ema_slow": current_ema_slow,
                    "bb_upper": current_bb_upper,
                    "bb_lower": current_bb_lower,
                    "atr": current_atr
                },
                "market_context": {
                    "trend": market_structure.get("trend", "SIDEWAYS"),
                    "volatility": market_structure.get("volatility", 0.0),
                    "support_resistance": market_structure.get("support_resistance", {}),
                    "candle_patterns": market_structure.get("candle_patterns", {}),
                    "price_action": {
                        "current_price": current_price,
                        "price_above_ema_fast": price_above_ema_fast,
                        "ema_alignment": ema_alignment,
                        "bb_position": bb_position
                    }
                },
                "risk_metrics": {
                    "atr_risk": atr_risk,
                    "volatility_risk": "HIGH" if market_structure.get("volatility", 0) > 2.0 else "NORMAL"
                },
                "trade_decision": {
                    "should_execute": auto_execute,
                    "confidence_level": "HIGH" if confidence >= 85 else "MEDIUM" if confidence >= 65 else "LOW",
                    "decision_factors": {
                        "rsi_signal": rsi_signal,
                        "ema_signal": ema_signal,
                        "trend_alignment": market_structure.get("trend", "SIDEWAYS"),
                        "pattern_confirmation": len(market_structure.get("candle_patterns", {}).get("patterns", []))
                    }
                }
            }

            self.last_signals[symbol] = signal_result

            if symbol not in self.signal_history:
                self.signal_history[symbol] = []
            self.signal_history[symbol].append(signal_result)

            if len(self.signal_history[symbol]) > 100:
                self.signal_history[symbol] = self.signal_history[symbol][-100:]

            if final_signal != "HOLD":
                self.logger.info(f"📊 {symbol} Signal: {final_signal} (Confidence: {confidence:.1f}%) - {reason}")
            
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
            confidence_factor = signal.get("confidence", 0.0) / 100.0
            adjusted_risk = risk_per_trade * confidence_factor

            # Calculate risk amount
            risk_amount = account_balance * adjusted_risk

            # Get symbol info
            point = symbol_info.get("point", 0.00001)
            pip_value = symbol_info.get("pip_value", 1.0)
            min_lot = symbol_info.get("volume_min", 0.01)
            max_lot = symbol_info.get("volume_max", 1.0)

            # Adjust TP/SL based on market conditions (using ATR from signal context)
            market_context = signal.get("market_context", {})
            atr_ratio = market_context.get("atr_ratio", 1.0) # ATR ratio might not be directly available, use ATR value
            current_atr = signal.get("indicators", {}).get("atr")

            if current_atr is not None and current_atr > 0:
                # Dynamic TP/SL based on ATR
                atr_multiplier_tp = 1.0
                atr_multiplier_sl = 1.0
                
                # Example: Adjust based on ATR relative to current price
                atr_to_price_ratio = current_atr / signal.get("market_context", {}).get("price_action", {}).get("current_price", 1)
                
                if atr_to_price_ratio > 0.005: # If ATR is more than 0.5% of price (moderate volatility)
                    atr_multiplier_tp = 1.2
                    atr_multiplier_sl = 1.1
                if atr_to_price_ratio > 0.01: # If ATR is more than 1% of price (high volatility)
                    atr_multiplier_tp = 1.5
                    atr_multiplier_sl = 1.2

                tp_pips *= atr_multiplier_tp
                sl_pips *= atr_multiplier_sl

            # Calculate lot size
            pip_risk = sl_pips * pip_value
            lot_size = risk_amount / pip_risk if pip_risk > 0 else min_lot

            # Ensure lot size is within limits and respects tick size
            lot_size = max(min_lot, min(lot_size, max_lot))
            # Assuming lot size needs to be a multiple of min_lot (e.g., 0.01)
            lot_size = round(lot_size / min_lot) * min_lot 

            # Calculate SL and TP levels
            entry_price = signal.get("entry_price", signal.get("market_context", {}).get("price_action", {}).get("current_price"))
            if entry_price is None:
                raise ValueError("Entry price not found in signal data.")

            # Adjust SL/TP calculation based on the point value
            if signal["signal"] == "BUY":
                stop_loss = entry_price - (sl_pips * point * 10) # Multiply by 10 if pip_value is per 1000 units etc. Adjust as needed.
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
            hold_signals = len([s for s in history if s["signal"] == "HOLD"])
            none_signals = len([s for s in history if s["signal"] == "NONE"])

            # Confidence statistics
            valid_signals = [s for s in history if s["signal"] in ["BUY", "SELL"]]
            avg_confidence = np.mean([s["confidence"] for s in valid_signals]) if valid_signals else 0
            high_confidence_signals = len([s for s in valid_signals if s["confidence"] >= 70])
            low_confidence_signals = len([s for s in valid_signals if s["confidence"] < 40])

            # Signal quality analysis
            bullish_scores = [s.get("strength", 0) for s in valid_signals if s.get("signal") == "BUY"] # Using strength as a proxy for score here
            bearish_scores = [s.get("strength", 0) for s in valid_signals if s.get("signal") == "SELL"]

            avg_bullish_score = np.mean(bullish_scores) if bullish_scores else 0
            avg_bearish_score = np.mean(bearish_scores) if bearish_scores else 0
            
            # Auto execution statistics
            auto_executed_trades = len([s for s in valid_signals if s.get("auto_execute", False)])
            high_confidence_auto_execute = len([s for s in valid_signals if s.get("auto_execute", False) and s.get("confidence", 0) >= 85])

            # Recent activity
            recent_signals_24h = len([s for s in history if 
                            (datetime.now() - s["timestamp"]).total_seconds() < 86400])

            stats = {
                "total_signals_processed": total_signals,
                "buy_signals": buy_signals,
                "sell_signals": sell_signals,
                "hold_signals": hold_signals,
                "none_signals": none_signals,
                "valid_trade_signals": len(valid_signals),
                "avg_confidence": avg_confidence,
                "high_confidence_signals": high_confidence_signals,
                "low_confidence_signals": low_confidence_signals,
                "avg_bullish_strength": avg_bullish_score,
                "avg_bearish_strength": avg_bearish_score,
                "auto_executed_trades": auto_executed_trades,
                "high_confidence_auto_execute": high_confidence_auto_execute,
                "recent_signals_24h": recent_signals_24h,
                "symbols_analyzed": len(symbols),
                "last_signal_time": max([s["timestamp"] for s in history]) if history else None,
                "confidence_distribution": {
                    "high": len([s for s in valid_signals if s["confidence"] >= 85]),
                    "medium": len([s for s in valid_signals if 65 <= s["confidence"] < 85]),
                    "low": len([s for s in valid_signals if s["confidence"] < 65])
                }
            }

            return stats

        except Exception as e:
            self.logger.error(f"❌ Strategy stats error: {str(e)}")
            return {"error": str(e)}