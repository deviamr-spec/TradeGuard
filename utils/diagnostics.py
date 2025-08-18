"""
System Diagnostics for MT5 Trading Bot.
Performs startup checks and system validation.
"""

import os
import sys
import platform
import subprocess
import socket
import time
import threading
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import requests

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from utils.logging_setup import get_logger

class SystemDiagnostics:
    """Comprehensive system diagnostics and health checks."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.results = {}
        self.start_time = datetime.now()
        
    def run_all_checks(self) -> Dict[str, Any]:
        """
        Run all diagnostic checks.
        
        Returns:
            Dictionary with all diagnostic results
        """
        try:
            self.logger.info("🔍 Starting system diagnostics...")
            
            checks = [
                ("System Info", self.check_system_info),
                ("Python Environment", self.check_python_environment),
                ("Dependencies", self.check_dependencies),
                ("MT5 Installation", self.check_mt5_installation),
                ("Network Connectivity", self.check_network_connectivity),
                ("Disk Space", self.check_disk_space),
                ("Memory", self.check_memory),
                ("Permissions", self.check_file_permissions),
                ("MT5 Process", self.check_mt5_process),
                ("Trading Account", self.check_trading_account)
            ]
            
            total_checks = len(checks)
            passed_checks = 0
            
            for i, (check_name, check_func) in enumerate(checks):
                self.logger.info(f"🔄 Running check {i+1}/{total_checks}: {check_name}")
                
                try:
                    result = check_func()
                    self.results[check_name] = result
                    
                    if result.get("status") == "PASS":
                        passed_checks += 1
                        self.logger.info(f"✅ {check_name}: PASSED")
                    elif result.get("status") == "WARN":
                        self.logger.warning(f"⚠️ {check_name}: WARNING - {result.get('message', '')}")
                    else:
                        self.logger.error(f"❌ {check_name}: FAILED - {result.get('message', '')}")
                        
                except Exception as e:
                    self.results[check_name] = {
                        "status": "ERROR",
                        "message": f"Check failed: {str(e)}",
                        "timestamp": datetime.now()
                    }
                    self.logger.error(f"❌ {check_name}: ERROR - {str(e)}")
            
            # Calculate overall health score
            health_score = (passed_checks / total_checks) * 100
            
            # Generate summary
            duration = (datetime.now() - self.start_time).total_seconds()
            
            summary = {
                "overall_status": "HEALTHY" if health_score >= 80 else "UNHEALTHY" if health_score < 50 else "DEGRADED",
                "health_score": health_score,
                "checks_passed": passed_checks,
                "total_checks": total_checks,
                "duration_seconds": duration,
                "timestamp": datetime.now(),
                "results": self.results
            }
            
            self.logger.info(f"🏁 Diagnostics completed in {duration:.2f}s")
            self.logger.info(f"📊 Health Score: {health_score:.1f}% ({passed_checks}/{total_checks} checks passed)")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ Diagnostics failed: {str(e)}")
            return {
                "overall_status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now()
            }
    
    def check_system_info(self) -> Dict[str, Any]:
        """Check basic system information."""
        try:
            info = {
                "os": platform.system(),
                "os_version": platform.release(),
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "hostname": platform.node(),
                "python_version": sys.version.split()[0]
            }
            
            # Validate Windows requirement
            if info["os"] != "Windows":
                return {
                    "status": "FAIL",
                    "message": f"MT5 Python API requires Windows, detected: {info['os']}",
                    "details": info
                }
            
            # Check architecture compatibility
            if info["architecture"] != "64bit":
                return {
                    "status": "WARN",
                    "message": f"Recommended 64-bit architecture, detected: {info['architecture']}",
                    "details": info
                }
            
            return {
                "status": "PASS",
                "message": "System information validated",
                "details": info
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"System info check failed: {str(e)}"
            }
    
    def check_python_environment(self) -> Dict[str, Any]:
        """Check Python environment and version."""
        try:
            version_info = sys.version_info
            python_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
            
            details = {
                "version": python_version,
                "executable": sys.executable,
                "path": sys.path[:3],  # First 3 paths
                "prefix": sys.prefix
            }
            
            # Check Python version compatibility
            if version_info < (3, 6):
                return {
                    "status": "FAIL",
                    "message": f"Python 3.6+ required, found: {python_version}",
                    "details": details
                }
            
            if version_info >= (3, 14):
                return {
                    "status": "WARN",
                    "message": f"Python version {python_version} may not be fully tested",
                    "details": details
                }
            
            return {
                "status": "PASS",
                "message": f"Python {python_version} is compatible",
                "details": details
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Python environment check failed: {str(e)}"
            }
    
    def check_dependencies(self) -> Dict[str, Any]:
        """Check required Python packages."""
        try:
            required_packages = {
                "MetaTrader5": "MetaTrader5 API",
                "PyQt5": "GUI Framework",
                "pandas": "Data Analysis",
                "numpy": "Numerical Computing"
            }
            
            installed = {}
            missing = []
            
            for package, description in required_packages.items():
                try:
                    module = __import__(package.lower() if package == "MetaTrader5" else package)
                    version = getattr(module, '__version__', 'Unknown')
                    installed[package] = {
                        "version": version,
                        "description": description,
                        "status": "OK"
                    }
                except ImportError:
                    missing.append(package)
                    installed[package] = {
                        "version": "Not installed",
                        "description": description,
                        "status": "MISSING"
                    }
            
            if missing:
                return {
                    "status": "FAIL",
                    "message": f"Missing required packages: {', '.join(missing)}",
                    "details": installed
                }
            
            return {
                "status": "PASS",
                "message": "All required packages are installed",
                "details": installed
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Dependency check failed: {str(e)}"
            }
    
    def check_mt5_installation(self) -> Dict[str, Any]:
        """Check MetaTrader 5 installation."""
        try:
            if not mt5:
                return {
                    "status": "FAIL",
                    "message": "MetaTrader5 package not available",
                }
            
            # Common MT5 installation paths
            possible_paths = [
                "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
                "C:\\Program Files (x86)\\MetaTrader 5\\terminal.exe",
                "C:\\Users\\%USERNAME%\\AppData\\Roaming\\MetaQuotes\\Terminal\\D0E8209F77C8CF37AD8BF550E51FF075\\terminal64.exe"
            ]
            
            found_paths = []
            for path in possible_paths:
                expanded_path = os.path.expandvars(path)
                if os.path.exists(expanded_path):
                    found_paths.append(expanded_path)
            
            if not found_paths:
                return {
                    "status": "WARN",
                    "message": "MT5 terminal not found in common locations",
                    "details": {
                        "searched_paths": possible_paths,
                        "recommendation": "Ensure MT5 is installed and running"
                    }
                }
            
            # Try to get MT5 version info (requires MT5 to be running)
            try:
                if mt5.initialize():
                    version = mt5.version()
                    mt5.shutdown()
                    
                    if version:
                        return {
                            "status": "PASS",
                            "message": "MT5 installation verified",
                            "details": {
                                "found_paths": found_paths,
                                "version": str(version),
                                "build": getattr(version, 'build', 'Unknown')
                            }
                        }
                
                return {
                    "status": "WARN",
                    "message": "MT5 found but not running or accessible",
                    "details": {
                        "found_paths": found_paths,
                        "recommendation": "Start MT5 and login to your trading account"
                    }
                }
                
            except Exception as init_error:
                return {
                    "status": "WARN",
                    "message": "MT5 installation found but connection failed",
                    "details": {
                        "found_paths": found_paths,
                        "init_error": str(init_error),
                        "recommendation": "Restart MT5 as Administrator"
                    }
                }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"MT5 installation check failed: {str(e)}"
            }
    
    def check_network_connectivity(self) -> Dict[str, Any]:
        """Check network connectivity to trading servers."""
        try:
            # Test general internet connectivity
            test_urls = [
                ("Google DNS", "8.8.8.8", 53),
                ("MetaQuotes", "mt5.metaquotes.net", 443),
                ("Trading Server", "mt5.roboforex.com", 443)  # Example broker
            ]
            
            connectivity_results = {}
            
            for name, host, port in test_urls:
                try:
                    start_time = time.time()
                    sock = socket.create_connection((host, port), timeout=5)
                    sock.close()
                    latency = (time.time() - start_time) * 1000
                    
                    connectivity_results[name] = {
                        "status": "OK",
                        "latency_ms": round(latency, 2),
                        "host": host,
                        "port": port
                    }
                    
                except Exception as e:
                    connectivity_results[name] = {
                        "status": "FAILED",
                        "error": str(e),
                        "host": host,
                        "port": port
                    }
            
            # Check if at least basic connectivity works
            successful_connections = sum(1 for result in connectivity_results.values() 
                                       if result["status"] == "OK")
            
            if successful_connections == 0:
                return {
                    "status": "FAIL",
                    "message": "No network connectivity detected",
                    "details": connectivity_results
                }
            elif successful_connections < len(test_urls):
                return {
                    "status": "WARN",
                    "message": "Partial network connectivity",
                    "details": connectivity_results
                }
            else:
                return {
                    "status": "PASS",
                    "message": "Network connectivity verified",
                    "details": connectivity_results
                }
                
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Network check failed: {str(e)}"
            }
    
    def check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space."""
        try:
            if platform.system() == "Windows":
                import shutil
                total, used, free = shutil.disk_usage("C:\\")
            else:
                import shutil
                total, used, free = shutil.disk_usage("/")
            
            free_gb = free // (1024**3)
            total_gb = total // (1024**3)
            used_percent = (used / total) * 100
            
            details = {
                "free_gb": free_gb,
                "total_gb": total_gb,
                "used_percent": round(used_percent, 1),
                "free_percent": round(100 - used_percent, 1)
            }
            
            if free_gb < 1:  # Less than 1GB free
                return {
                    "status": "FAIL",
                    "message": f"Critical: Only {free_gb}GB free space remaining",
                    "details": details
                }
            elif free_gb < 5:  # Less than 5GB free
                return {
                    "status": "WARN",
                    "message": f"Low disk space: {free_gb}GB free",
                    "details": details
                }
            else:
                return {
                    "status": "PASS",
                    "message": f"Sufficient disk space: {free_gb}GB free",
                    "details": details
                }
                
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Disk space check failed: {str(e)}"
            }
    
    def check_memory(self) -> Dict[str, Any]:
        """Check available system memory."""
        try:
            if platform.system() == "Windows":
                # Use Windows-specific memory check
                try:
                    import psutil
                    memory = psutil.virtual_memory()
                    available_gb = memory.available / (1024**3)
                    total_gb = memory.total / (1024**3)
                    used_percent = memory.percent
                    
                except ImportError:
                    # Fallback to basic check without psutil
                    return {
                        "status": "WARN",
                        "message": "Memory check requires psutil package",
                        "details": {"recommendation": "pip install psutil"}
                    }
                    
            else:
                # Basic memory check for non-Windows
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                available_gb = 2  # Assume 2GB as fallback
                total_gb = 8  # Assume 8GB as fallback
                used_percent = 50  # Assume 50% usage
            
            details = {
                "available_gb": round(available_gb, 2),
                "total_gb": round(total_gb, 2),
                "used_percent": round(used_percent, 1)
            }
            
            if available_gb < 0.5:  # Less than 500MB
                return {
                    "status": "FAIL",
                    "message": f"Critical: Only {available_gb:.1f}GB memory available",
                    "details": details
                }
            elif available_gb < 2:  # Less than 2GB
                return {
                    "status": "WARN",
                    "message": f"Low memory: {available_gb:.1f}GB available",
                    "details": details
                }
            else:
                return {
                    "status": "PASS",
                    "message": f"Sufficient memory: {available_gb:.1f}GB available",
                    "details": details
                }
                
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Memory check failed: {str(e)}"
            }
    
    def check_file_permissions(self) -> Dict[str, Any]:
        """Check file system permissions."""
        try:
            test_paths = [
                ("Current Directory", os.getcwd()),
                ("Logs Directory", os.path.join(os.getcwd(), "logs")),
                ("Temp Directory", os.path.join(os.path.expanduser("~"), "temp"))
            ]
            
            permission_results = {}
            
            for name, path in test_paths:
                try:
                    # Test write permissions
                    test_file = os.path.join(path, f"test_write_{int(time.time())}.tmp")
                    
                    # Create directory if it doesn't exist
                    os.makedirs(path, exist_ok=True)
                    
                    # Test write
                    with open(test_file, 'w') as f:
                        f.write("test")
                    
                    # Test read
                    with open(test_file, 'r') as f:
                        content = f.read()
                    
                    # Cleanup
                    os.remove(test_file)
                    
                    permission_results[name] = {
                        "status": "OK",
                        "path": path,
                        "read": True,
                        "write": True
                    }
                    
                except PermissionError as pe:
                    permission_results[name] = {
                        "status": "FAILED",
                        "path": path,
                        "error": f"Permission denied: {str(pe)}",
                        "read": False,
                        "write": False
                    }
                    
                except Exception as e:
                    permission_results[name] = {
                        "status": "ERROR",
                        "path": path,
                        "error": str(e)
                    }
            
            # Check results
            failed_permissions = [name for name, result in permission_results.items() 
                                if result["status"] in ["FAILED", "ERROR"]]
            
            if failed_permissions:
                return {
                    "status": "FAIL",
                    "message": f"Permission errors in: {', '.join(failed_permissions)}",
                    "details": permission_results
                }
            else:
                return {
                    "status": "PASS",
                    "message": "File permissions verified",
                    "details": permission_results
                }
                
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Permission check failed: {str(e)}"
            }
    
    def check_mt5_process(self) -> Dict[str, Any]:
        """Check if MT5 process is running."""
        try:
            if platform.system() != "Windows":
                return {
                    "status": "SKIP",
                    "message": "MT5 process check only available on Windows"
                }
            
            try:
                import psutil
                
                mt5_processes = []
                for proc in psutil.process_iter(['pid', 'name', 'exe', 'create_time']):
                    try:
                        if 'terminal' in proc.info['name'].lower() and 'metatrader' in (proc.info['exe'] or '').lower():
                            mt5_processes.append({
                                "pid": proc.info['pid'],
                                "name": proc.info['name'],
                                "exe": proc.info['exe'],
                                "running_since": datetime.fromtimestamp(proc.info['create_time'])
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                if not mt5_processes:
                    return {
                        "status": "WARN",
                        "message": "No MT5 processes detected",
                        "details": {"recommendation": "Start MetaTrader 5 application"}
                    }
                
                return {
                    "status": "PASS",
                    "message": f"Found {len(mt5_processes)} MT5 process(es)",
                    "details": {"processes": mt5_processes}
                }
                
            except ImportError:
                return {
                    "status": "WARN",
                    "message": "Process check requires psutil package",
                    "details": {"recommendation": "pip install psutil"}
                }
                
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"MT5 process check failed: {str(e)}"
            }
    
    def check_trading_account(self) -> Dict[str, Any]:
        """Check trading account connectivity and status."""
        try:
            if not mt5:
                return {
                    "status": "SKIP",
                    "message": "MT5 package not available"
                }
            
            # Try to initialize MT5
            if not mt5.initialize():
                last_error = mt5.last_error()
                return {
                    "status": "FAIL",
                    "message": f"Cannot connect to MT5: {last_error}",
                    "details": {
                        "error_code": last_error,
                        "recommendation": "Ensure MT5 is running and logged in"
                    }
                }
            
            try:
                # Get account information
                account_info = mt5.account_info()
                if not account_info:
                    return {
                        "status": "FAIL",
                        "message": "Cannot retrieve account information",
                        "details": {"recommendation": "Login to your trading account in MT5"}
                    }
                
                # Check account type
                trade_mode = getattr(account_info, 'trade_mode', None)
                
                account_details = {
                    "login": account_info.login,
                    "server": account_info.server,
                    "balance": account_info.balance,
                    "currency": account_info.currency,
                    "trade_allowed": getattr(account_info, 'trade_allowed', True),
                    "trade_mode": trade_mode
                }
                
                # Verify live account
                if trade_mode == 0:  # ACCOUNT_TRADE_MODE_DEMO
                    return {
                        "status": "WARN",
                        "message": "DEMO account detected - Bot is configured for LIVE trading",
                        "details": account_details
                    }
                elif trade_mode == 2:  # ACCOUNT_TRADE_MODE_REAL
                    return {
                        "status": "PASS",
                        "message": "LIVE trading account verified",
                        "details": account_details
                    }
                else:
                    return {
                        "status": "WARN",
                        "message": f"Unknown account trade mode: {trade_mode}",
                        "details": account_details
                    }
                
            finally:
                mt5.shutdown()
                
        except Exception as e:
            try:
                mt5.shutdown()
            except:
                pass
            
            return {
                "status": "ERROR",
                "message": f"Trading account check failed: {str(e)}"
            }

def run_startup_diagnostics() -> bool:
    """
    Run comprehensive startup diagnostics.
    
    Returns:
        True if system is ready, False if critical issues found
    """
    logger = get_logger(__name__)
    
    try:
        logger.info("🔍 Running startup diagnostics...")
        
        diagnostics = SystemDiagnostics()
        results = diagnostics.run_all_checks()
        
        overall_status = results.get("overall_status", "ERROR")
        health_score = results.get("health_score", 0)
        
        if overall_status == "ERROR":
            logger.error("❌ System diagnostics failed")
            return False
        
        if overall_status == "UNHEALTHY":
            logger.warning(f"⚠️ Running in DEMO MODE (Health Score: {health_score:.1f}%)")
            logger.warning("🔧 The following components are unavailable:")
            
            for check_name, result in results.get("results", {}).items():
                if result.get("status") in ["FAIL", "ERROR"]:
                    logger.warning(f"   • {check_name}: {result.get('message', 'Unknown error')}")
            
            logger.warning("💡 Application will run in demo mode with simulated data")
            return True
        
        elif overall_status == "DEGRADED":
            logger.warning(f"⚠️ System degraded (Score: {health_score:.1f}%)")
            logger.warning("🔧 Consider resolving these warnings:")
            
            for check_name, result in results.get("results", {}).items():
                if result.get("status") == "WARN":
                    logger.warning(f"   • {check_name}: {result.get('message', 'Unknown warning')}")
            
            # Continue with degraded system but log warnings
            logger.info("✅ Continuing with degraded system status")
            return True
        
        else:  # HEALTHY
            logger.info(f"✅ System healthy (Score: {health_score:.1f}%)")
            logger.info("🚀 All systems ready for trading")
            return True
        
    except Exception as e:
        logger.error(f"❌ Startup diagnostics failed: {str(e)}")
        return False

def check_mt5_connection() -> bool:
    """
    Quick MT5 connection check.
    
    Returns:
        True if MT5 can be connected, False otherwise
    """
    logger = get_logger(__name__)
    
    try:
        if not mt5:
            logger.error("❌ MetaTrader5 package not available")
            return False
        
        if mt5.initialize():
            account_info = mt5.account_info()
            mt5.shutdown()
            
            if account_info:
                logger.info(f"✅ MT5 connection verified - Account: {account_info.login}")
                return True
            else:
                logger.error("❌ MT5 connected but no account info available")
                return False
        else:
            error = mt5.last_error()
            logger.error(f"❌ MT5 connection failed: {error}")
            return False
            
    except Exception as e:
        logger.error(f"❌ MT5 connection check failed: {str(e)}")
        return False

def log_system_specs():
    """Log detailed system specifications."""
    logger = get_logger(__name__)
    
    try:
        logger.info("💻 System Specifications:")
        logger.info(f"   OS: {platform.system()} {platform.release()}")
        logger.info(f"   Architecture: {platform.architecture()[0]}")
        logger.info(f"   Processor: {platform.processor()}")
        logger.info(f"   Python: {sys.version.split()[0]}")
        logger.info(f"   Executable: {sys.executable}")
        
        # Try to get more detailed specs if psutil is available
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            logger.info(f"   Memory: {memory.total / (1024**3):.1f}GB total, {memory.available / (1024**3):.1f}GB available")
            
            cpu_count = psutil.cpu_count()
            logger.info(f"   CPU Cores: {cpu_count}")
            
            disk = psutil.disk_usage('C:' if platform.system() == 'Windows' else '/')
            logger.info(f"   Disk: {disk.free / (1024**3):.1f}GB free of {disk.total / (1024**3):.1f}GB")
            
        except ImportError:
            logger.info("   (Install psutil for detailed memory/CPU info)")
            
    except Exception as e:
        logger.error(f"❌ Failed to log system specs: {str(e)}")

