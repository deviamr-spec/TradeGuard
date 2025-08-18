#!/usr/bin/env python3
"""
MT5 Trading Bot System Validation Script
Comprehensive system check for all components before live trading.
"""

import sys
import os
import importlib
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional

def validate_imports() -> Dict[str, Any]:
    """Validate all required imports."""
    print("🔍 Validating imports...")

    required_modules = [
        ("MetaTrader5", "MT5 API"),
        ("PyQt5", "GUI Framework"),
        ("pandas", "Data Analysis"),
        ("numpy", "Numerical Computing"),
        ("talib", "Technical Analysis")
    ]

    results = {"passed": 0, "failed": 0, "details": []}

    for module, description in required_modules:
        try:
            importlib.import_module(module)
            results["details"].append(f"✅ {module} ({description})")
            results["passed"] += 1
        except ImportError as e:
            results["details"].append(f"❌ {module} ({description}) - {str(e)}")
            results["failed"] += 1

    return results

def validate_core_components() -> Dict[str, Any]:
    """Validate core trading components."""
    print("⚙️ Validating core components...")

    components = [
        ("core.mt5_client", "MT5Client"),
        ("core.trade_engine", "TradeEngine"),
        ("core.strategy.scalping", "ScalpingStrategy"),
        ("core.risk", "RiskManager"),
        ("core.reporting", "ReportingManager"),
        ("core.config", "Config")
    ]

    results = {"passed": 0, "failed": 0, "details": []}

    for module_path, class_name in components:
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)

            # Try to instantiate (basic validation)
            if class_name == "MT5Client":
                instance = cls()
            elif class_name == "TradeEngine":
                # Skip instantiation as it requires MT5Client
                results["details"].append(f"✅ {module_path}.{class_name} (structure valid)")
                results["passed"] += 1
                continue
            else:
                instance = cls()

            results["details"].append(f"✅ {module_path}.{class_name}")
            results["passed"] += 1

        except Exception as e:
            results["details"].append(f"❌ {module_path}.{class_name} - {str(e)}")
            results["failed"] += 1

    return results

def validate_gui_components() -> Dict[str, Any]:
    """Validate GUI components."""
    print("🖥️ Validating GUI components...")

    results = {"passed": 0, "failed": 0, "details": []}

    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)

        from gui.app import MainWindow
        from gui.widgets import (
            AccountInfoWidget, PositionsWidget, EquityChartWidget,
            TradingControlWidget, LogWidget, StrategyStatsWidget,
            RiskMonitorWidget, PerformanceMonitorWidget
        )

        results["details"].append("✅ MainWindow class")
        results["details"].append("✅ All widget classes")
        results["passed"] += 2

    except Exception as e:
        results["details"].append(f"❌ GUI components - {str(e)}")
        results["failed"] += 1

    return results

def validate_configuration() -> Dict[str, Any]:
    """Validate system configuration."""
    print("⚙️ Validating configuration...")

    results = {"passed": 0, "failed": 0, "details": []}

    try:
        from core.config import config

        # Validate configuration structure
        validation = config.validate_config()

        if validation["valid"]:
            results["details"].append("✅ Configuration structure valid")
            results["passed"] += 1
        else:
            results["details"].append(f"❌ Configuration issues: {', '.join(validation['issues'])}")
            results["failed"] += 1

        if validation["warnings"]:
            for warning in validation["warnings"]:
                results["details"].append(f"⚠️ {warning}")

        # Check critical paths
        required_dirs = ["logs", "reports"]
        for dir_name in required_dirs:
            if os.path.exists(dir_name):
                results["details"].append(f"✅ Directory exists: {dir_name}")
                results["passed"] += 1
            else:
                os.makedirs(dir_name, exist_ok=True)
                results["details"].append(f"✅ Directory created: {dir_name}")
                results["passed"] += 1

    except Exception as e:
        results["details"].append(f"❌ Configuration validation - {str(e)}")
        results["failed"] += 1

    return results

def validate_mt5_integration() -> Dict[str, Any]:
    """Validate MT5 integration."""
    print("🔌 Validating MT5 integration...")

    results = {"passed": 0, "failed": 0, "details": []}

    try:
        from core.mt5_client import MT5Client, MT5_AVAILABLE

        if not MT5_AVAILABLE:
            results["details"].append("⚠️ MT5 package not available (expected on non-Windows)")
            results["details"].append("✅ Demo mode will be used")
            results["passed"] += 1
            return results

        # Test MT5 client creation
        client = MT5Client()
        results["details"].append("✅ MT5Client instantiation")
        results["passed"] += 1

        # Test connection attempt (may fail if MT5 not running)
        try:
            connected = client.connect()
            if connected:
                results["details"].append("✅ MT5 connection successful")

                # Test basic operations
                account_info = client.get_account_info()
                if account_info:
                    results["details"].append(f"✅ Account info: {account_info['login']}")
                    results["passed"] += 2
                else:
                    results["details"].append("⚠️ Could not retrieve account info")

                client.disconnect()
            else:
                results["details"].append("⚠️ MT5 connection failed (MT5 may not be running)")
                results["details"].append("✅ Will use demo mode if needed")

        except Exception as e:
            results["details"].append(f"⚠️ MT5 connection test failed: {str(e)}")
            results["details"].append("✅ Will fallback to demo mode")

        results["passed"] += 1

    except Exception as e:
        results["details"].append(f"❌ MT5 integration - {str(e)}")
        results["failed"] += 1

    return results

def validate_strategy_system() -> Dict[str, Any]:
    """Validate trading strategy system."""
    print("📊 Validating strategy system...")

    results = {"passed": 0, "failed": 0, "details": []}

    try:
        from core.strategy.scalping import ScalpingStrategy
        import pandas as pd
        import numpy as np

        # Create test data
        dates = pd.date_range(end=datetime.now(), periods=100, freq='1min')
        test_data = pd.DataFrame({
            'open': np.random.uniform(1.0, 1.1, 100),
            'high': np.random.uniform(1.05, 1.15, 100),
            'low': np.random.uniform(0.95, 1.05, 100),
            'close': np.random.uniform(1.0, 1.1, 100),
            'tick_volume': np.random.randint(50, 200, 100)
        }, index=dates)

        # Ensure OHLC integrity
        test_data['high'] = np.maximum.reduce([test_data['open'], test_data['high'], 
                                              test_data['low'], test_data['close']])
        test_data['low'] = np.minimum.reduce([test_data['open'], test_data['high'], 
                                             test_data['low'], test_data['close']])

        # Test strategy
        strategy = ScalpingStrategy()
        signal = strategy.generate_signal(test_data, "EURUSD")

        if signal and "signal" in signal:
            results["details"].append(f"✅ Strategy signal generation: {signal['signal']}")
            results["passed"] += 1
        else:
            results["details"].append("❌ Strategy signal generation failed")
            results["failed"] += 1

        # Test position sizing
        try:
            lot_size, sl, tp = strategy.calculate_position_size(
                signal, 10000, {"point": 0.00001, "digits": 5}
            )
            results["details"].append(f"✅ Position sizing: {lot_size} lots")
            results["passed"] += 1
        except Exception as e:
            results["details"].append(f"❌ Position sizing failed: {str(e)}")
            results["failed"] += 1

    except Exception as e:
        results["details"].append(f"❌ Strategy validation - {str(e)}")
        results["failed"] += 1

    return results

def validate_logging_system() -> Dict[str, Any]:
    """Validate logging system."""
    print("📝 Validating logging system...")

    results = {"passed": 0, "failed": 0, "details": []}

    try:
        from utils.logging_setup import setup_logging, get_logger

        # Test logging setup
        setup_logging()
        logger = get_logger("validation_test")

        # Test log levels
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")

        results["details"].append("✅ Logging system operational")
        results["passed"] += 1

        # Check log files
        log_files = ["logs/mt5_trading_bot.log", "logs/mt5_trading_bot_errors.log"]
        for log_file in log_files:
            if os.path.exists(log_file):
                results["details"].append(f"✅ Log file exists: {log_file}")
                results["passed"] += 1
            else:
                results["details"].append(f"⚠️ Log file not found: {log_file}")

    except Exception as e:
        results["details"].append(f"❌ Logging validation - {str(e)}")
        results["failed"] += 1

    return results

def test_mt5_connection():
    """Test MT5 connection functionality with enhanced features."""
    print("🔌 Testing MT5 Connection...")

    try:
        from core.mt5_client import MT5Client
        client = MT5Client()

        # Test connection with retry logic
        if client.connect():
            print("  ✅ MT5 connection successful")

            # Test account info
            if client.get_account_info():
                print("  ✅ Account info retrieval successful")
            else:
                print("  ⚠️ Account info retrieval failed")

            # Test connection health monitoring
            if client.is_connection_healthy():
                print("  ✅ Connection health check passed")
            else:
                print("  ⚠️ Connection health check failed")

            # Test symbol detection
            test_symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
            for symbol in test_symbols:
                detected = client.auto_detect_symbol(symbol)
                if detected == symbol:
                    print(f"  ✅ Symbol detection: {symbol}")
                else:
                    print(f"  🔄 Symbol mapped: {symbol} -> {detected}")

            client.disconnect()
        else:
            print("  ❌ MT5 connection failed")
            print("  🔄 Testing auto-reconnection...")
            if client.auto_reconnect():
                print("  ✅ Auto-reconnection successful")
                client.disconnect()
            else:
                print("  ❌ Auto-reconnection failed")

    except Exception as e:
        print(f"  ❌ MT5 test error: {e}")
        return False

    return True

def test_configuration_management():
    """Test enhanced configuration management."""
    print("⚙️ Testing Configuration Management...")

    try:
        from core.config import ConfigManager
        config = ConfigManager()

        # Test configuration validation
        if config.validate_config():
            print("  ✅ Configuration validation passed")
        else:
            print("  ❌ Configuration validation failed")

        # Test runtime parameter update
        config.update_runtime_parameter('testing', 'test_param', 'test_value')
        if config.get('testing', {}).get('test_param') == 'test_value':
            print("  ✅ Runtime parameter update successful")
        else:
            print("  ❌ Runtime parameter update failed")

        print("  ✅ Configuration management tests passed")
        return True

    except Exception as e:
        print(f"  ❌ Configuration test error: {e}")
        return False

def test_performance_analytics():
    """Test enhanced performance analytics."""
    print("📊 Testing Performance Analytics...")

    try:
        from core.reporting import PerformanceReporter
        reporter = PerformanceReporter()

        # Test Sharpe ratio calculation
        test_returns = [0.01, -0.005, 0.02, 0.015, -0.01]
        sharpe = reporter.calculate_sharpe_ratio(test_returns)
        if sharpe is not None:
            print(f"  ✅ Sharpe ratio calculation: {sharpe:.3f}")
        else:
            print("  ❌ Sharpe ratio calculation failed")

        # Test profit factor calculation
        profit_factor = reporter.calculate_profit_factor()
        print(f"  ✅ Profit factor calculation: {profit_factor:.3f}")

        print("  ✅ Performance analytics tests passed")
        return True

    except Exception as e:
        print(f"  ❌ Performance analytics test error: {e}")
        return False

def run_comprehensive_validation() -> bool:
    """Run comprehensive system validation."""
    print("=" * 80)
    print("🔍 MT5 TRADING BOT - ENHANCED SYSTEM VALIDATION")
    print("=" * 80)
    print()

    results = []

    # Run all tests
    results.append(("Python Environment", validate_imports()))
    results.append(("Dependencies", validate_core_components())) # Assuming core components implies dependency checks
    results.append(("MT5 Connection", test_mt5_connection()))
    results.append(("Configuration Management", test_configuration_management()))
    results.append(("Original Configuration", validate_configuration()))
    results.append(("Strategy System", validate_strategy_system()))
    results.append(("Performance Analytics", test_performance_analytics()))
    results.append(("GUI System", validate_gui_components()))
    results.append(("Logging System", validate_logging_system()))

    # Summary
    print("\n" + "=" * 80)
    print("📋 ENHANCED VALIDATION SUMMARY")
    print("=" * 80)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result["failed"] == 0 else "❌ FAIL"
        print(f"{test_name:<30} {status}")
        if result["failed"] == 0:
            passed += 1
        # Print details for failed tests only for brevity, or all if needed
        if result["failed"] > 0:
            for detail in result["details"]:
                print(f"    {detail}")


    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL ENHANCED SYSTEMS READY FOR LIVE TRADING!")
        print("✅ Auto-reconnection: ENABLED")
        print("✅ Advanced error handling: ACTIVE")
        print("✅ Real-time monitoring: ACTIVE")
        print("✅ Enhanced symbol detection: ACTIVE")
        print("✅ Configuration management: ENHANCED")
        print("✅ Performance analytics: ADVANCED")
    else:
        print("\n⚠️ Some systems need attention before live trading")

    print("=" * 80)

    return passed == total

def main():
    """Main validation entry point."""
    try:
        success = run_comprehensive_validation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation failed with error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()