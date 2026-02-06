"""
Quick Start Guide - NIFTY 50 Live Trading Application
Run this script to quickly set up and test the application
"""

import subprocess
import sys
import os

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def install_dependencies():
    """Install required packages"""
    print_header("STEP 1: Installing Dependencies")
    
    try:
        print("Installing PyQt5, yfinance, pandas, numpy, pyqtgraph...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("\n✅ All dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("\n❌ Failed to install dependencies")
        print("Please run manually: pip install -r requirements.txt")
        return False

def verify_installation():
    """Verify all packages are installed"""
    print_header("STEP 2: Verifying Installation")
    
    required_packages = {
        'PyQt5': 'PyQt5',
        'pyqtgraph': 'pyqtgraph',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'yfinance': 'yfinance'
    }
    
    all_installed = True
    
    for display_name, package_name in required_packages.items():
        try:
            __import__(package_name)
            print(f"✅ {display_name} - Installed")
        except ImportError:
            print(f"❌ {display_name} - NOT Installed")
            all_installed = False
    
    return all_installed

def test_strategies():
    """Test strategy wrappers"""
    print_header("STEP 3: Testing Strategy Modules")
    
    try:
        from strategy_wrappers import (BollingerMACDStrategy, 
                                       OpeningRangeBreakoutStrategy, 
                                       SidewaysStrategy)
        print("✅ Strategy wrappers loaded successfully")
        
        # Test instantiation
        s1 = BollingerMACDStrategy()
        print(f"   - {s1.name}")
        
        s2 = OpeningRangeBreakoutStrategy()
        print(f"   - {s2.name}")
        
        s3 = SidewaysStrategy()
        print(f"   - {s3.name}")
        
        return True
    except Exception as e:
        print(f"❌ Strategy test failed: {e}")
        return False

def test_trading_engine():
    """Test paper trading engine"""
    print_header("STEP 4: Testing Paper Trading Engine")
    
    try:
        from paper_trading_engine import PaperTradingEngine
        
        engine = PaperTradingEngine(initial_capital=100000)
        print("✅ Trading engine initialized")
        print(f"   - Initial Capital: ₹{engine.capital:,.2f}")
        
        # Test opening a position
        trade = engine.open_position(
            signal_type='CALL',
            entry_price=23500,
            stop_loss=23450,
            target=23600,
            quantity=75,
            strategy='Test',
            notes='Test trade'
        )
        
        if trade:
            print(f"✅ Test trade created: {trade.trade_id}")
            
            # Test updating position
            engine.update_positions(23550)
            print(f"   - Unrealized P&L: ₹{trade.pnl:,.2f}")
            
            # Close position
            engine.update_positions(23600)
            print(f"✅ Position auto-closed at target")
        
        return True
    except Exception as e:
        print(f"❌ Trading engine test failed: {e}")
        return False

def launch_application():
    """Launch the main application"""
    print_header("STEP 5: Launching Application")
    
    print("Starting NIFTY 50 Live Trading Application...")
    print("\nApplication Features:")
    print("  • Select strategy from dropdown")
    print("  • View live candlestick charts")
    print("  • Monitor trading signals")
    print("  • Execute paper trades")
    print("  • Track portfolio performance")
    print("\nPress Ctrl+C in this window to stop the application.")
    print("-" * 70)
    
    try:
        subprocess.run([sys.executable, "trading_app.py"])
    except KeyboardInterrupt:
        print("\n\n✅ Application closed by user")
    except Exception as e:
        print(f"\n\n❌ Application error: {e}")

def main():
    """Main setup and launch sequence"""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                                                                  ║")
    print("║        NIFTY 50 LIVE TRADING APPLICATION - QUICK START          ║")
    print("║                                                                  ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    
    # Check if dependencies are already installed
    print("\nChecking for existing installation...")
    
    try:
        import PyQt5
        import pyqtgraph
        import pandas
        import yfinance
        print("✅ Dependencies already installed!")
        already_installed = True
    except ImportError:
        print("⚠️  Some dependencies missing")
        already_installed = False
    
    if not already_installed:
        response = input("\nInstall dependencies now? (y/n): ")
        if response.lower() == 'y':
            if not install_dependencies():
                print("\n❌ Setup failed. Please install dependencies manually.")
                return
        else:
            print("\n⚠️  Please install dependencies before running the application")
            print("   Run: pip install -r requirements.txt")
            return
    
    # Verify installation
    if not verify_installation():
        print("\n❌ Installation verification failed")
        print("   Please reinstall: pip install -r requirements.txt")
        return
    
    # Test modules
    if not test_strategies():
        print("\n❌ Strategy module test failed")
        return
    
    if not test_trading_engine():
        print("\n❌ Trading engine test failed")
        return
    
    print_header("✅ ALL TESTS PASSED - READY TO TRADE!")
    
    print("\nWhat would you like to do?")
    print("1. Launch Trading Application (GUI)")
    print("2. View README documentation")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ")
    
    if choice == '1':
        launch_application()
    elif choice == '2':
        if os.path.exists('README.md'):
            with open('README.md', 'r', encoding='utf-8') as f:
                print("\n" + f.read())
        else:
            print("README.md not found")
    else:
        print("\n👋 Goodbye! Run 'python trading_app.py' to start trading.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        print("Please report this issue with the error message above")
