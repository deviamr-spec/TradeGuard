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

class StrategyError(Exception):
    """Custom exception for strategy-related errors."""
    pass

class DataValidationError(StrategyError):
    """Exception for data validation failures."""
    pass

class IndicatorCalculationError(StrategyError):
    """Exception for indicator calculation failures."""
    pass

class ScalpingStrategy:
    """Enhanced EMA/RSI scalping strategy with comprehensive error handling."""

    def __init__(self):
        self.logger = get_logger(__name__)

        # Strategy parameters from config with validation
        try:
            self.ema_fast = max(1, config.get("strategy.ema_fast", 12))
            self.ema_slow = max(self.ema_fast + 1, config.get("strategy.ema_slow", 26))
            self.rsi_period = max(2, config.get("strategy.rsi_period", 14))
            self.rsi_overbought = min(100, max(50, config.get("strategy.rsi_overbought", 70.0)))
            self.rsi_oversold = max(0, min(50, config.get("strategy.rsi_oversold", 30.0)))
            self.take_profit_pips = max(1, config.get("strategy.take_profit_pips", 10.0))
            self.stop_loss_pips = max(1, config.get("strategy.stop_loss_pips", 5.0))
            self.min_confidence = max(0, min(100, config.get("strategy.min_confidence", 60.0)))

            # Strategy state tracking
            self.signal_history = []
            self.last_signal_time = {}
            self.strategy_stats = {
                "total_signals": 0,
                "buy_signals": 0,
                "sell_signals": 0,
                "avg_confidence": 0.0,
                "symbols_analyzed": set(),
                "last_signal_time": None
            }

            self.logger.info(f"✅ Strategy initialized: EMA({self.ema_fast}/{self.ema_slow}), RSI({self.rsi_period})")

        except Exception as e:
            self.logger.error(f"❌ Strategy initialization failed: {str(e)}")
            raise StrategyError(f"Failed to initialize strategy: {str(e)}")

    def validate_data(self, df: pd.DataFrame, symbol: str) -> None:
        """
        Validate input data for strategy analysis.

        Args:
            df: Price data DataFrame
            symbol: Trading symbol

        Raises:
            DataValidationError: If data validation fails
        """
        try:
            if df is None or df.empty:
                raise DataValidationError(f"Empty or None DataFrame for {symbol}")

            required_columns = ['open', 'high', 'low', 'close', 'tick_volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise DataValidationError(f"Missing columns for {symbol}: {missing_columns}")

            if len(df) < max(self.ema_slow, self.rsi_period) + 10:
                raise DataValidationError(f"Insufficient data for {symbol}: {len(df)} bars (need at least {max(self.ema_slow, self.rsi_period) + 10})")

            # Check for valid price data
            for col in ['open', 'high', 'low', 'close']:
                if df[col].isna().any():
                    raise DataValidationError(f"NaN values found in {col} for {symbol}")
                if (df[col] <= 0).any():
                    raise DataValidationError(f"Invalid price values in {col} for {symbol}")

            # Validate OHLC logic
            if ((df['high'] < df['low']) | 
                (df['high'] < df['open']) | 
                (df['high'] < df['close']) |
                (df['low'] > df['open']) | 
                (df['low'] > df['close'])).any():
                raise DataValidationError(f"Invalid OHLC data for {symbol}")

        except Exception as e:
            self.logger.error(f"❌ Data validation failed for {symbol}: {str(e)}")
            if isinstance(e, DataValidationError):
                raise
            raise DataValidationError(f"Data validation error for {symbol}: {str(e)}")

    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average with error handling.

        Args:
            data: Price data series
            period: EMA period

        Returns:
            EMA series

        Raises:
            IndicatorCalculationError: If calculation fails
        """
        try:
            if data is None or data.empty:
                raise IndicatorCalculationError("Empty data series for EMA calculation")

            if period <= 0:
                raise IndicatorCalculationError(f"Invalid EMA period: {period}")

            if len(data) < period:
                raise IndicatorCalculationError(f"Insufficient data for EMA({period}): {len(data)} bars")

            ema = data.ewm(span=period, adjust=False).mean()

            if ema.isna().all():
                raise IndicatorCalculationError(f"EMA calculation produced all NaN values")

            return ema

        except Exception as e:
            self.logger.error(f"❌ EMA calculation error: {str(e)}")
            if isinstance(e, IndicatorCalculationError):
                raise
            raise IndicatorCalculationError(f"EMA calculation failed: {str(e)}")

    def calculate_rsi(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Relative Strength Index with error handling.

        Args:
            data: Price data series
            period: RSI period

        Returns:
            RSI series

        Raises:
            IndicatorCalculationError: If calculation fails
        """
        try:
            if data is None or data.empty:
                raise IndicatorCalculationError("Empty data series for RSI calculation")

            if period <= 1:
                raise IndicatorCalculationError(f"Invalid RSI period: {period}")

            if len(data) < period + 1:
                raise IndicatorCalculationError(f"Insufficient data for RSI({period}): {len(data)} bars")

            delta = data.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            # Avoid division by zero
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))

            if rsi.isna().all():
                raise IndicatorCalculationError("RSI calculation produced all NaN values")

            return rsi

        except Exception as e:
            self.logger.error(f"❌ RSI calculation error: {str(e)}")
            if isinstance(e, IndicatorCalculationError):
                raise
            raise IndicatorCalculationError(f"RSI calculation failed: {str(e)}")

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range with error handling.

        Args:
            df: OHLC DataFrame
            period: ATR period

        Returns:
            ATR series

        Raises:
            IndicatorCalculationError: If calculation fails
        """
        try:
            if df is None or df.empty:
                raise IndicatorCalculationError("Empty DataFrame for ATR calculation")

            required_cols = ['high', 'low', 'close']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise IndicatorCalculationError(f"Missing columns for ATR: {missing_cols}")

            if len(df) < period + 1:
                raise IndicatorCalculationError(f"Insufficient data for ATR({period}): {len(df)} bars")

            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())

            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = true_range.rolling(window=period).mean()

            if atr.isna().all():
                raise IndicatorCalculationError("ATR calculation produced all NaN values")

            return atr

        except Exception as e:
            self.logger.error(f"❌ ATR calculation error: {str(e)}")
            if isinstance(e, IndicatorCalculationError):
                raise
            raise IndicatorCalculationError(f"ATR calculation failed: {str(e)}")

    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Generate trading signal with comprehensive error handling.

        Args:
            df: Price data DataFrame
            symbol: Trading symbol

        Returns:
            Signal dictionary with error handling
        """
        try:
            # Validate input data
            self.validate_data(df, symbol)

            # Update strategy stats
            self.strategy_stats["symbols_analyzed"].add(symbol)

            # Calculate indicators with error handling
            try:
                ema_fast = self.calculate_ema(df['close'], self.ema_fast)
                ema_slow = self.calculate_ema(df['close'], self.ema_slow)
                rsi = self.calculate_rsi(df['close'], self.rsi_period)
                atr = self.calculate_atr(df)

            except (IndicatorCalculationError, Exception) as e:
                self.logger.error(f"❌ Indicator calculation failed for {symbol}: {str(e)}")
                return self._create_hold_signal(symbol, f"Indicator calculation error: {str(e)}")

            # Get latest values safely
            try:
                latest_ema_fast = float(ema_fast.iloc[-1])
                latest_ema_slow = float(ema_slow.iloc[-1])
                latest_rsi = float(rsi.iloc[-1])
                latest_atr = float(atr.iloc[-1])
                latest_close = float(df['close'].iloc[-1])

                # Validate indicator values
                if any(np.isnan([latest_ema_fast, latest_ema_slow, latest_rsi, latest_atr])):
                    return self._create_hold_signal(symbol, "Invalid indicator values (NaN)")

            except (IndexError, ValueError, TypeError) as e:
                self.logger.error(f"❌ Error extracting indicator values for {symbol}: {str(e)}")
                return self._create_hold_signal(symbol, f"Value extraction error: {str(e)}")

            # Signal generation logic
            signal_data = {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "signal": "HOLD",
                "confidence": 0.0,
                "entry_price": latest_close,
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "market_context": {
                    "ema_fast": latest_ema_fast,
                    "ema_slow": latest_ema_slow,
                    "rsi": latest_rsi,
                    "atr": latest_atr
                },
                "errors": []
            }

            # EMA crossover analysis
            ema_bullish = latest_ema_fast > latest_ema_slow
            ema_trend_strength = abs(latest_ema_fast - latest_ema_slow) / latest_ema_slow * 100

            # RSI analysis
            rsi_oversold = latest_rsi < self.rsi_oversold
            rsi_overbought = latest_rsi > self.rsi_overbought
            rsi_neutral = self.rsi_oversold <= latest_rsi <= self.rsi_overbought

            # Signal logic with confidence calculation
            confidence = 0.0

            # BUY signal conditions
            if ema_bullish and rsi_oversold:
                signal_data["signal"] = "BUY"
                confidence += 50  # Base confidence for alignment
                confidence += min(30, (self.rsi_oversold - latest_rsi) * 2)  # More oversold = higher confidence
                if ema_trend_strength > 0.1:
                    confidence += 15  # Strong trend bonus

            # SELL signal conditions
            elif not ema_bullish and rsi_overbought:
                signal_data["signal"] = "SELL"
                confidence += 50  # Base confidence for alignment
                confidence += min(30, (latest_rsi - self.rsi_overbought) * 2)  # More overbought = higher confidence
                if ema_trend_strength > 0.1:
                    confidence += 15  # Strong trend bonus

            # Apply confidence limits and minimum threshold
            signal_data["confidence"] = min(95.0, max(0.0, confidence))

            # Calculate stop loss and take profit
            if signal_data["signal"] in ["BUY", "SELL"]:
                try:
                    signal_data["stop_loss"], signal_data["take_profit"] = self._calculate_sl_tp(
                        signal_data["signal"], latest_close, latest_atr
                    )
                except Exception as e:
                    self.logger.error(f"❌ SL/TP calculation error for {symbol}: {str(e)}")
                    signal_data["errors"].append(f"SL/TP calculation error: {str(e)}")

            # Update statistics
            self._update_strategy_stats(signal_data)

            # Filter by minimum confidence
            if signal_data["confidence"] < self.min_confidence and signal_data["signal"] != "HOLD":
                signal_data["signal"] = "HOLD"
                signal_data["confidence"] = 0.0
                signal_data["stop_loss"] = 0.0
                signal_data["take_profit"] = 0.0

            return signal_data

        except Exception as e:
            self.logger.error(f"❌ Signal generation failed for {symbol}: {str(e)}")
            return self._create_error_signal(symbol, str(e))

    def _create_hold_signal(self, symbol: str, reason: str = "") -> Dict[str, Any]:
        """Create a HOLD signal with error information."""
        return {
            "symbol": symbol,
            "timestamp": datetime.now(),
            "signal": "HOLD",
            "confidence": 0.0,
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "market_context": {},
            "errors": [reason] if reason else []
        }

    def _create_error_signal(self, symbol: str, error: str) -> Dict[str, Any]:
        """Create an error signal."""
        return {
            "symbol": symbol,
            "timestamp": datetime.now(),
            "signal": "ERROR",
            "confidence": 0.0,
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "market_context": {},
            "errors": [error]
        }

    def _calculate_sl_tp(self, signal_type: str, entry_price: float, atr: float) -> Tuple[float, float]:
        """
        Calculate stop loss and take profit levels.

        Args:
            signal_type: BUY or SELL
            entry_price: Entry price
            atr: Average True Range

        Returns:
            Tuple of (stop_loss, take_profit)
        """
        try:
            # Use ATR-based SL/TP for dynamic adjustment
            atr_multiplier = 1.5
            sl_distance = max(atr * atr_multiplier, entry_price * 0.001)  # Minimum 0.1%
            tp_distance = sl_distance * 2  # 2:1 reward-to-risk ratio

            if signal_type == "BUY":
                stop_loss = entry_price - sl_distance
                take_profit = entry_price + tp_distance
            else:  # SELL
                stop_loss = entry_price + sl_distance
                take_profit = entry_price - tp_distance

            return stop_loss, take_profit

        except Exception as e:
            self.logger.error(f"❌ SL/TP calculation error: {str(e)}")
            return 0.0, 0.0

    def _update_strategy_stats(self, signal_data: Dict[str, Any]) -> None:
        """Update strategy statistics."""
        try:
            self.strategy_stats["total_signals"] += 1

            if signal_data["signal"] == "BUY":
                self.strategy_stats["buy_signals"] += 1
            elif signal_data["signal"] == "SELL":
                self.strategy_stats["sell_signals"] += 1

            # Update average confidence
            total_confidence = (self.strategy_stats["avg_confidence"] * 
                              (self.strategy_stats["total_signals"] - 1) + 
                              signal_data["confidence"])
            self.strategy_stats["avg_confidence"] = total_confidence / self.strategy_stats["total_signals"]

            self.strategy_stats["last_signal_time"] = signal_data["timestamp"]

        except Exception as e:
            self.logger.error(f"❌ Stats update error: {str(e)}")

    def calculate_position_size(self, signal: Dict[str, Any], balance: float, 
                              symbol_info: Dict[str, Any]) -> Tuple[float, float, float]:
        """
        Calculate position size with enhanced validation.

        Args:
            signal: Trading signal
            balance: Account balance
            symbol_info: Symbol information

        Returns:
            Tuple of (lot_size, stop_loss, take_profit)
        """
        try:
            # Validate inputs
            if balance <= 0:
                raise ValueError(f"Invalid balance: {balance}")

            if not symbol_info:
                raise ValueError("Missing symbol information")

            # Risk management parameters
            risk_percent = config.get("risk.risk_per_trade", 0.01)  # 1% risk
            min_lot = symbol_info.get("volume_min", 0.01)
            max_lot = symbol_info.get("volume_max", 1.0)
            lot_step = symbol_info.get("volume_step", 0.01)

            # Calculate position size based on risk
            risk_amount = balance * risk_percent
            entry_price = signal.get("entry_price", 0)
            stop_loss = signal.get("stop_loss", 0)

            if entry_price <= 0 or stop_loss <= 0:
                self.logger.warning("⚠️ Invalid price levels, using minimum lot size")
                return min_lot, stop_loss, signal.get("take_profit", 0)

            # Calculate lot size based on risk
            price_diff = abs(entry_price - stop_loss)
            if price_diff > 0:
                contract_size = symbol_info.get("contract_size", 100000)
                pip_value = symbol_info.get("pip_value", 10)

                # Calculate lot size
                lot_size = risk_amount / (price_diff * contract_size / pip_value)

                # Round to valid lot size
                lot_size = round(lot_size / lot_step) * lot_step
                lot_size = max(min_lot, min(lot_size, max_lot))
            else:
                lot_size = min_lot

            return lot_size, stop_loss, signal.get("take_profit", 0)

        except Exception as e:
            self.logger.error(f"❌ Position size calculation error: {str(e)}")
            return symbol_info.get("volume_min", 0.01), 0.0, 0.0

    def get_strategy_stats(self) -> Dict[str, Any]:
        """Get strategy statistics with error handling."""
        try:
            stats = self.strategy_stats.copy()
            stats["symbols_analyzed"] = len(stats["symbols_analyzed"])

            # Calculate recent signals (last 24 hours)
            if hasattr(self, 'signal_history'):
                recent_signals = [
                    s for s in self.signal_history 
                    if (datetime.now() - s.get("timestamp", datetime.now())).total_seconds() < 86400
                ]
                stats["recent_signals_24h"] = len(recent_signals)
            else:
                stats["recent_signals_24h"] = 0

            return stats

        except Exception as e:
            self.logger.error(f"❌ Strategy stats error: {str(e)}")
            return {"no_data": True, "error": str(e)}