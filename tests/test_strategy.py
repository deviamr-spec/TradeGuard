
"""
Unit tests for ScalpingStrategy
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from core.strategy.scalping import ScalpingStrategy, DataValidationError, IndicatorCalculationError


class TestScalpingStrategy(unittest.TestCase):
    """Test cases for ScalpingStrategy class."""

    def setUp(self):
        """Set up test fixtures."""
        self.strategy = ScalpingStrategy()
        
        # Create sample valid OHLC data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        np.random.seed(42)  # For reproducible tests
        
        base_price = 1.0850
        price_changes = np.random.normal(0, 0.0001, 100).cumsum()
        close_prices = base_price + price_changes
        
        # Generate realistic OHLC data
        opens = close_prices.shift(1).fillna(base_price)
        highs = np.maximum(opens, close_prices) + np.abs(np.random.normal(0, 0.00005, 100))
        lows = np.minimum(opens, close_prices) - np.abs(np.random.normal(0, 0.00005, 100))
        
        self.valid_df = pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': close_prices,
            'tick_volume': np.random.randint(50, 200, 100)
        }, index=dates)

    def test_data_validation_valid_data(self):
        """Test data validation with valid data."""
        try:
            self.strategy.validate_data(self.valid_df, "EURUSD")
        except DataValidationError:
            self.fail("Valid data should not raise DataValidationError")

    def test_data_validation_empty_dataframe(self):
        """Test data validation with empty DataFrame."""
        empty_df = pd.DataFrame()
        with self.assertRaises(DataValidationError):
            self.strategy.validate_data(empty_df, "EURUSD")

    def test_data_validation_none_dataframe(self):
        """Test data validation with None DataFrame."""
        with self.assertRaises(DataValidationError):
            self.strategy.validate_data(None, "EURUSD")

    def test_data_validation_missing_columns(self):
        """Test data validation with missing columns."""
        invalid_df = self.valid_df.drop(columns=['close'])
        with self.assertRaises(DataValidationError):
            self.strategy.validate_data(invalid_df, "EURUSD")

    def test_data_validation_insufficient_data(self):
        """Test data validation with insufficient data."""
        small_df = self.valid_df.head(10)
        with self.assertRaises(DataValidationError):
            self.strategy.validate_data(small_df, "EURUSD")

    def test_ema_calculation(self):
        """Test EMA calculation."""
        ema = self.strategy.calculate_ema(self.valid_df['close'], 12)
        self.assertIsInstance(ema, pd.Series)
        self.assertFalse(ema.isna().all())
        self.assertEqual(len(ema), len(self.valid_df))

    def test_ema_calculation_invalid_period(self):
        """Test EMA calculation with invalid period."""
        with self.assertRaises(IndicatorCalculationError):
            self.strategy.calculate_ema(self.valid_df['close'], 0)

    def test_rsi_calculation(self):
        """Test RSI calculation."""
        rsi = self.strategy.calculate_rsi(self.valid_df['close'], 14)
        self.assertIsInstance(rsi, pd.Series)
        self.assertFalse(rsi.isna().all())
        # RSI should be between 0 and 100
        valid_rsi = rsi.dropna()
        self.assertTrue((valid_rsi >= 0).all())
        self.assertTrue((valid_rsi <= 100).all())

    def test_atr_calculation(self):
        """Test ATR calculation."""
        atr = self.strategy.calculate_atr(self.valid_df, 14)
        self.assertIsInstance(atr, pd.Series)
        self.assertFalse(atr.isna().all())
        # ATR should be positive
        valid_atr = atr.dropna()
        self.assertTrue((valid_atr > 0).all())

    def test_signal_generation(self):
        """Test signal generation."""
        signal = self.strategy.generate_signal(self.valid_df, "EURUSD")
        
        self.assertIsInstance(signal, dict)
        self.assertIn('signal', signal)
        self.assertIn('confidence', signal)
        self.assertIn('symbol', signal)
        self.assertIn('timestamp', signal)
        
        # Signal should be one of the valid types
        valid_signals = ['BUY', 'SELL', 'HOLD', 'ERROR', 'INVALID_DATA']
        self.assertIn(signal['signal'], valid_signals)
        
        # Confidence should be between 0 and 100
        self.assertGreaterEqual(signal['confidence'], 0)
        self.assertLessEqual(signal['confidence'], 100)

    def test_strategy_stats(self):
        """Test strategy statistics."""
        # Generate a few signals to populate stats
        for i in range(3):
            self.strategy.generate_signal(self.valid_df, f"TEST{i}")
        
        stats = self.strategy.get_strategy_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('total_signals', stats)
        self.assertGreaterEqual(stats['total_signals'], 3)


if __name__ == '__main__':
    unittest.main()
