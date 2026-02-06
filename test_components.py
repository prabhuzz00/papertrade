"""
Test Script - Verify all components work correctly
Run this before launching the main application
"""

import sys

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    
    try:
        import PyQt5
        print("  ✓ PyQt5")
    except ImportError as e:
        print(f"  ✗ PyQt5: {e}")
        return False
    
    try:
        import pyqtgraph
        print("  ✓ pyqtgraph")
    except ImportError as e:
        print(f"  ✗ pyqtgraph: {e}")
        return False
    
    try:
        import pandas
        print("  ✓ pandas")
    except ImportError as e:
        print(f"  ✗ pandas: {e}")
        return False
    
    try:
        import numpy
        print("  ✓ numpy")
    except ImportError as e:
        print(f"  ✗ numpy: {e}")
        return False
    
    try:
        import yfinance
        print("  ✓ yfinance")
    except ImportError as e:
        print(f"  ✗ yfinance: {e}")
        return False
    
    return True

def test_strategy_wrappers():
    """Test strategy wrapper classes"""
    print("\nTesting strategy wrappers...")
    
    try:
        from strategy_wrappers import (BollingerMACDStrategy, 
                                       OpeningRangeBreakoutStrategy,
                                       SidewaysStrategy)
        
        # Test instantiation
        s1 = BollingerMACDStrategy()
        print(f"  ✓ {s1.name}")
        
        s2 = OpeningRangeBreakoutStrategy()
        print(f"  ✓ {s2.name}")
        
        s3 = SidewaysStrategy()
        print(f"  ✓ {s3.name}")
        
        # Test indicator calculation
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # Create dummy data
        dates = pd.date_range(end=datetime.now(), periods=100, freq='5min')
        df = pd.DataFrame({
            'Open': np.random.randn(100).cumsum() + 23500,
            'High': np.random.randn(100).cumsum() + 23520,
            'Low': np.random.randn(100).cumsum() + 23480,
            'Close': np.random.randn(100).cumsum() + 23500,
            'Volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        
        # Test adding indicators
        df_with_indicators = s1.add_indicators(df.copy())
        assert 'ATR' in df_with_indicators.columns
        assert 'RSI' in df_with_indicators.columns
        print("  ✓ Indicator calculations work")
        
        return True
    except Exception as e:
        print(f"  ✗ Strategy wrappers: {e}")
        return False

def test_paper_trading_engine():
    """Test paper trading engine"""
    print("\nTesting paper trading engine...")
    
    try:
        from paper_trading_engine import PaperTradingEngine, Trade
        
        # Create engine
        engine = PaperTradingEngine(initial_capital=100000)
        print(f"  ✓ Engine initialized with ₹{engine.capital:,.2f}")
        
        # Open position (with smaller quantity to avoid margin issues)
        trade = engine.open_position(
            signal_type='CALL',
            entry_price=23500,
            stop_loss=23450,
            target=23600,
            quantity=10,  # Smaller quantity for testing
            strategy='Test',
            notes='Test trade'
        )
        
        if trade:
            print(f"  ✓ Position opened: {trade.trade_id}")
        else:
            print("  ✗ Failed to open position")
            return False
        
        # Update position
        engine.update_positions(23550)
        print(f"  ✓ Position updated, P&L: ₹{trade.pnl:,.2f}")
        
        # Test target hit
        engine.update_positions(23600)
        if trade.status == 'TARGET':
            print(f"  ✓ Target hit correctly, Final P&L: ₹{trade.pnl:,.2f}")
        else:
            print(f"  ✗ Target not detected")
            return False
        
        # Test statistics
        stats = engine.get_statistics()
        print(f"  ✓ Statistics: Win Rate = {stats['win_rate']:.0%}")
        
        # Test save/load
        import os
        test_file = 'test_trades_temp.json'
        engine.save_trades(test_file)
        
        if os.path.exists(test_file):
            print(f"  ✓ Trades saved to {test_file}")
            
            # Load trades
            engine2 = PaperTradingEngine()
            engine2.load_trades(test_file)
            print(f"  ✓ Trades loaded successfully")
            
            # Cleanup
            os.remove(test_file)
        else:
            print("  ✗ Failed to save trades")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ Paper trading engine: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_fetch():
    """Test data fetching from Yahoo Finance"""
    print("\nTesting data fetch...")
    
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        
        end = datetime.now()
        start = end - timedelta(days=2)
        
        print(f"  Fetching NIFTY 50 data from Yahoo Finance...")
        df = yf.download('^NSEI', start=start, end=end, interval='5m', progress=False)
        
        if df.empty:
            print("  ⚠ No data received (might be outside market hours)")
            print("  ℹ This is normal if markets are closed")
            return True  # Not a failure, just no data available
        else:
            print(f"  ✓ Received {len(df)} candles")
            latest_price = float(df['Close'].iloc[-1])
            print(f"  ✓ Latest price: ₹{latest_price:.2f}")
            return True
    except Exception as e:
        print(f"  ✗ Data fetch: {e}")
        return False

def main():
    """Run all tests"""
    print("="*70)
    print("  COMPONENT VERIFICATION TEST")
    print("="*70)
    
    results = {
        'Imports': test_imports(),
        'Strategy Wrappers': test_strategy_wrappers(),
        'Paper Trading Engine': test_paper_trading_engine(),
        'Data Fetch': test_data_fetch()
    }
    
    print("\n" + "="*70)
    print("  TEST RESULTS")
    print("="*70)
    
    all_passed = True
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {test_name:.<50} {status}")
        if not result:
            all_passed = False
    
    print("="*70)
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED - Application is ready to run!")
        print("\nTo start the application, run:")
        print("    python trading_app.py")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Please fix issues before running")
        print("\nTroubleshooting:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Check internet connection")
        print("  3. Verify Python version (3.7+)")
        return 1

if __name__ == '__main__':
    sys.exit(main())
