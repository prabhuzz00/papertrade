"""
NIFTY Option Trader - Complete Demo
Simulates both CALL and PUT signals to demonstrate the full trading workflow
"""

from nifty_option_trader import NiftyOptionTrader
import time


def demo_complete_workflow():
    """Demonstrate complete option trading workflow"""
    print("\n" + "="*70)
    print("NIFTY OPTIONS PAPER TRADING - COMPLETE DEMO")
    print("="*70 + "\n")
    
    # Initialize trader with Rs. 1 lakh capital
    trader = NiftyOptionTrader(initial_capital=100000)
    
    print("Initial Setup Complete!")
    print(f"Starting Capital: Rs.{trader.initial_capital:,.2f}\n")
    
    # ==========================================
    # SCENARIO 1: CALL Signal Generated
    # ==========================================
    print("\n" + "="*70)
    print("SCENARIO 1: Bullish Signal - CALL Option Trade")
    print("="*70)
    input("Press Enter to execute CALL trade...")
    
    trade1 = trader.execute_signal('CALL', 'Bollinger+MACD')
    
    if trade1:
        trader.display_dashboard()
        
        # Simulate price checking after some time
        print("\n--- Monitoring Position ---")
        print("Checking if Stop Loss or Target hit...")
        trader.update_positions()
        
        # If position still open, update with current price
        if trader.open_positions:
            print("\nPosition still open. Current status:")
            for trade in trader.open_positions:
                current_ltp = trader.get_option_ltp(trade.instrument_id)
                if current_ltp:
                    trade.update_current_premium(current_ltp)
                    print(f"  {trade.trade_id}: Current LTP = Rs.{current_ltp:.2f}, "
                          f"P&L = Rs.{trade.pnl:.2f}")
                    
                    # Check distance to SL and Target
                    sl_distance = ((current_ltp - trade.stop_loss) / current_ltp) * 100
                    target_distance = ((trade.target - current_ltp) / current_ltp) * 100
                    print(f"  Stop Loss: {sl_distance:.1f}% away")
                    print(f"  Target: {target_distance:.1f}% away")
    
    # ==========================================
    # SCENARIO 2: Another CALL Signal (if capital available)
    # ==========================================
    if trader.capital > 20000:  # Check if enough capital
        print("\n" + "="*70)
        print("SCENARIO 2: Another CALL Signal")
        print("="*70)
        input("Press Enter to execute second trade...")
        
        trade2 = trader.execute_signal('CALL', 'Opening Range Breakout')
        trader.display_dashboard()
    
    # ==========================================
    # Save and Show Statistics
    # ==========================================
    print("\n" + "="*70)
    print("SAVING TRADE HISTORY")
    print("="*70)
    trader.save_trades('demo_option_trades.json')
    
    print("\n" + "="*70)
    print("FINAL STATISTICS")
    print("="*70)
    stats = trader.get_statistics()
    
    print(f"\nCapital Summary:")
    print(f"  Initial Capital:  Rs.{trader.initial_capital:,.2f}")
    print(f"  Free Capital:     Rs.{trader.capital:,.2f}")
    print(f"  Invested:         Rs.{trader.initial_capital - trader.capital:,.2f}")
    print(f"  Total Value:      Rs.{stats['total_capital']:,.2f}")
    print(f"  Total P&L:        Rs.{stats['total_pnl']:,.2f} ({stats['return_pct']:.2f}%)")
    
    print(f"\nTrade Summary:")
    print(f"  Open Positions:   {stats['open_positions']}")
    print(f"  Closed Trades:    {stats['closed_trades']}")
    print(f"  Win Rate:         {stats['win_rate']*100:.1f}%")
    
    if trader.open_positions:
        print(f"\nOpen Positions:")
        for i, trade in enumerate(trader.open_positions, 1):
            pnl_pct = (trade.pnl / (trade.entry_premium * trade.quantity)) * 100 if trade.entry_premium > 0 else 0
            print(f"\n  {i}. {trade.trade_id}")
            print(f"     Type: {trade.instrument_type} {trade.strike_price}")
            print(f"     Entry: Rs.{trade.entry_premium:.2f}")
            print(f"     Current: Rs.{trade.current_premium:.2f}")
            print(f"     P&L: Rs.{trade.pnl:.2f} ({pnl_pct:.1f}%)")
            print(f"     Stop Loss: Rs.{trade.stop_loss:.2f}")
            print(f"     Target: Rs.{trade.target:.2f}")
            print(f"     Strategy: {trade.strategy}")
    
    print("\n" + "="*70)
    print("DEMO COMPLETE")
    print("="*70)
    print("\nTrades saved to: demo_option_trades.json")
    print("You can load them later using: trader.load_trades('demo_option_trades.json')")
    print("\n")


def demo_manual_exit():
    """Demonstrate manual position closing"""
    print("\n" + "="*70)
    print("DEMO: Manual Exit")
    print("="*70 + "\n")
    
    trader = NiftyOptionTrader(initial_capital=50000)
    
    # Execute a trade
    trade = trader.execute_signal('CALL', 'Test Strategy')
    
    if trade:
        trader.display_dashboard()
        
        # Wait for user input
        input("\nPress Enter to manually close the position...")
        
        # Close manually
        success = trader.close_position_manual(trade.trade_id)
        
        if success:
            trader.display_dashboard()
            print("\n✓ Position successfully closed manually!")


def demo_load_existing_trades():
    """Demonstrate loading existing trades"""
    print("\n" + "="*70)
    print("DEMO: Load Existing Trades")
    print("="*70 + "\n")
    
    trader = NiftyOptionTrader(initial_capital=100000)
    
    # Try to load existing trades
    trader.load_trades('demo_option_trades.json')
    
    # Display dashboard
    trader.display_dashboard()
    
    # Update positions with current prices
    print("\nUpdating positions with current market prices...")
    trader.update_positions()
    
    # Show updated dashboard
    trader.display_dashboard()


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║         NIFTY OPTIONS PAPER TRADING - DEMO SUITE              ║
    ╚════════════════════════════════════════════════════════════════╝
    
    Choose a demo:
    
    1. Complete Workflow (Recommended)
       - Execute CALL trades
       - Monitor positions
       - Show statistics
    
    2. Manual Exit Demo
       - Execute trade
       - Manually close position
    
    3. Load Existing Trades
       - Load saved trades
       - Update with current prices
    
    """)
    
    choice = input("Enter your choice (1/2/3): ").strip()
    
    if choice == '1':
        demo_complete_workflow()
    elif choice == '2':
        demo_manual_exit()
    elif choice == '3':
        demo_load_existing_trades()
    else:
        print("\nInvalid choice. Running complete workflow demo...")
        demo_complete_workflow()
