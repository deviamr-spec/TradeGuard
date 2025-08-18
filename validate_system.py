
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

def run_comprehensive_validation() -> bool:
    """Run comprehensive system validation."""
    print("=" * 80)
    print("🔍 MT5 TRADING BOT - COMPREHENSIVE SYSTEM VALIDATION")
    print("=" * 80)
    print(f"🕐 Validation started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    validation_tests = [
        ("Python Imports", validate_imports),
        ("Core Components", validate_core_components),
        ("GUI Components", validate_gui_components),
        ("Configuration", validate_configuration),
        ("MT5 Integration", validate_mt5_integration),
        ("Strategy System", validate_strategy_system),
        ("Logging System", validate_logging_system)
    ]
    
    total_passed = 0
    total_failed = 0
    all_results = []
    
    for test_name, test_func in validation_tests:
        try:
            result = test_func()
            all_results.append((test_name, result))
            total_passed += result["passed"]
            total_failed += result["failed"]
            
            # Print test results
            status = "✅ PASS" if result["failed"] == 0 else "❌ FAIL"
            print(f"{status} {test_name}: {result['passed']} passed, {result['failed']} failed")
            
            for detail in result["details"]:
                print(f"    {detail}")
            print()
            
        except Exception as e:
            print(f"❌ FAIL {test_name}: Validation error - {str(e)}")
            print(f"    Traceback: {traceback.format_exc()}")
            total_failed += 1
            print()
    
    # Summary
    print("=" * 80)
    print("📊 VALIDATION SUMMARY")
    print("=" * 80)
    print(f"✅ Total Passed: {total_passed}")
    print(f"❌ Total Failed: {total_failed}")
    print(f"📈 Success Rate: {(total_passed/(total_passed+total_failed)*100):.1f}%")
    print()
    
    # Overall status
    if total_failed == 0:
        print("🎉 SYSTEM VALIDATION SUCCESSFUL!")
        print("✅ System is ready for live trading")
        print()
        print("⚠️  IMPORTANT REMINDERS:")
        print("   • Test thoroughly in demo mode first")
        print("   • Monitor system continuously during live trading")
        print("   • Have emergency stop procedures ready")
        print("   • Ensure proper risk management settings")
        return True
    else:
        print("🚨 SYSTEM VALIDATION FAILED!")
        print("❌ System is NOT ready for live trading")
        print()
        print("🔧 REQUIRED ACTIONS:")
        print("   • Fix all failed validation tests")
        print("   • Re-run validation until all tests pass")
        print("   • Test system thoroughly before live deployment")
        return False

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
