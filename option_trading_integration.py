"""
Integration Example: NIFTY Option Trader with Signal Strategies

This example shows how to integrate the option trader with existing
signal generation strategies (Bollinger+MACD, ORB, Sideways, etc.)
"""

from nifty_option_trader import NiftyOptionTrader
from strategy_wrappers import (BollingerMACDStrategy, 
                               OpeningRangeBreakoutStrategy, 
                               SidewaysStrategy)
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time


class OptionTradingSystem:
    """
    Complete option trading system with strategy integration
    """
    
    def __init__(self, initial_capital=100000):
        # Initialize option trader
        self.option_trader = NiftyOptionTrader(initial_capital=initial_capital)
        
        # Initialize strategies
        self.strategies = {
            'Bollinger+MACD': BollingerMACDStrategy(),
            'Opening Range Breakout': OpeningRangeBreakoutStrategy(),
            'Sideways Market': SidewaysStrategy()
        }
        
        # Track last signal per strategy to avoid duplicate trades
        self.last_signals = {name: None for name in self.strategies.keys()}
        
        print("✓ Option Trading System Initialized")
        print(f"  Capital: Rs.{initial_capital:,.2f}")
        print(f"  Strategies: {len(self.strategies)}")
    
    def fetch_market_data(self, symbol='^NSEI', interval='5m', period='2d'):
        """Fetch latest market data"""
        try:
            df = yf.download(symbol, period=period, interval=interval, 
                           progress=False, auto_adjust=True)
            
            if not df.empty:
                # Update last close with XTS real-time spot if available
                xts_spot = self.option_trader.get_nifty_spot()
                if xts_spot:
                    df.loc[df.index[-1], 'Close'] = xts_spot
                    print(f"✓ Data fetched | Last Close: Rs.{xts_spot:.2f}")
                
                return df
        except Exception as e:
            print(f"✗ Error fetching data: {e}")
        
        return None
    
    def check_signals(self, df):
        """
        Check all strategies for signals and execute option trades
        
        Returns dict of signals from each strategy
        """
        signals = {}
        
        for strategy_name, strategy in self.strategies.items():
            try:
                # Get signal from strategy
                signal = strategy.predict(df)
                signals[strategy_name] = signal
                
                # Execute option trade if signal is valid and different from last
                if signal in ['CALL', 'PUT'] and signal != self.last_signals[strategy_name]:
                    print(f"\n🔔 NEW SIGNAL: {signal} from {strategy_name}")
                    
                    # Execute option trade
                    trade = self.option_trader.execute_signal(signal, strategy_name)
                    
                    if trade:
                        # Update last signal
                        self.last_signals[strategy_name] = signal
                        print(f"✓ Trade executed via {strategy_name}")
                    else:
                        print(f"✗ Trade execution failed")
                
                # Reset last signal if no signal
                elif signal == 'HOLD':
                    self.last_signals[strategy_name] = None
                    
            except Exception as e:
                print(f"✗ Error in {strategy_name}: {e}")
                signals[strategy_name] = 'HOLD'
        
        return signals
    
    def run_live_monitoring(self, update_interval=60):
        """
        Run live monitoring and trading
        
        Args:
            update_interval: Seconds between updates (default 60)
        """
        print("\n" + "="*70)
        print("LIVE OPTION TRADING STARTED")
        print("="*70)
        print(f"Update interval: {update_interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                print(f"\n{'='*70}")
                print(f"Update #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*70}")
                
                # Fetch latest data
                df = self.fetch_market_data()
                
                if df is not None and not df.empty:
                    # Check for signals and execute trades
                    signals = self.check_signals(df)
                    
                    # Display current signals
                    print(f"\nCurrent Signals:")
                    for strategy_name, signal in signals.items():
                        print(f"  {strategy_name}: {signal}")
                    
                    # Update all open positions (check SL/Target)
                    if self.option_trader.open_positions:
                        print(f"\n--- Updating {len(self.option_trader.open_positions)} Open Position(s) ---")
                        self.option_trader.update_positions()
                    
                    # Show quick stats
                    stats = self.option_trader.get_statistics()
                    print(f"\nQuick Stats:")
                    print(f"  Open: {stats['open_positions']} | "
                          f"Closed: {stats['closed_trades']} | "
                          f"Total P&L: Rs.{stats['total_pnl']:,.2f} | "
                          f"Capital: Rs.{stats['current_capital']:,.2f}")
                    
                    # Save trades
                    self.option_trader.save_trades()
                else:
                    print("✗ No data available")
                
                # Wait before next update
                print(f"\nNext update in {update_interval} seconds...")
                time.sleep(update_interval)
                
        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("TRADING STOPPED BY USER")
            print("="*70)
            
            # Show final dashboard
            self.option_trader.display_dashboard()
            
            # Save trades
            self.option_trader.save_trades()
            print("\n✓ All trades saved")
    
    def run_single_check(self):
        """Run a single check (useful for testing)"""
        print("\n" + "="*70)
        print("SINGLE CHECK MODE")
        print("="*70 + "\n")
        
        # Fetch data
        df = self.fetch_market_data()
        
        if df is not None and not df.empty:
            # Check signals
            signals = self.check_signals(df)
            
            # Update positions
            self.option_trader.update_positions()
            
            # Show dashboard
            self.option_trader.display_dashboard()
            
            # Save
            self.option_trader.save_trades()
        else:
            print("✗ Could not fetch market data")


def example_usage():
    """Example of how to use the system"""
    
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║      NIFTY OPTION TRADING WITH STRATEGY INTEGRATION           ║
    ╚════════════════════════════════════════════════════════════════╝
    
    This system:
    1. Monitors NIFTY using multiple strategies
    2. Generates CALL/PUT signals
    3. Automatically executes option trades at ATM strike
    4. Manages risk with 1:2 SL:Target ratio
    5. Updates positions in real-time
    
    """)
    
    # Create trading system
    system = OptionTradingSystem(initial_capital=100000)
    
    print("\nChoose mode:")
    print("1. Live Monitoring (continuous)")
    print("2. Single Check (one-time)")
    
    choice = input("\nEnter choice (1/2): ").strip()
    
    if choice == '1':
        interval = input("Update interval in seconds (default 60): ").strip()
        interval = int(interval) if interval else 60
        system.run_live_monitoring(update_interval=interval)
    else:
        system.run_single_check()


if __name__ == "__main__":
    example_usage()
