"""
NIFTY Option Price Checker
==========================

Quick tool to verify real-time option prices from XTS API.
Run this script anytime to check current option premiums.

Usage:
    python check_nifty_option_price.py
    python check_nifty_option_price.py --strike 25950 --type PE
    python check_nifty_option_price.py --chain
"""

import argparse
from datetime import datetime
from fetch_nifty_atm_options import NiftyATMOptionFetcher


def check_single_option(fetcher, strike, option_type, spot):
    """Check a single option's real-time price"""
    ltp, source = fetcher.get_option_ltp(strike, option_type, spot)
    source = f"{source} (XTS)" if source == 'LIVE' else source
    
    print(f"\n{'='*50}")
    print(f"  NIFTY {strike} {option_type}")
    print(f"{'='*50}")
    print(f"  Premium:   ₹{ltp:.2f}  [{source}]")
    print(f"  SL (-30%): ₹{ltp * 0.70:.2f}")
    print(f"  TGT(+50%): ₹{ltp * 1.50:.2f}")
    print(f"  Cost (65): ₹{ltp * 65:,.2f}")
    print(f"  Spot:      ₹{spot:,.2f}")
    
    # Get quote details if live
    key = (strike, option_type)
    if key in fetcher.instrument_cache:
        info = fetcher.instrument_cache[key]
        quote = fetcher.get_quote(info['instrument_id'], segment=2)
        if quote:
            print(f"  Open:      ₹{quote['open']:.2f}")
            print(f"  High:      ₹{quote['high']:.2f}")
            print(f"  Low:       ₹{quote['low']:.2f}")
            print(f"  LTP:       ₹{quote['ltp']:.2f}")
            print(f"  Close:     ₹{quote['close']:.2f}")
            print(f"  Bid:       ₹{quote['bid']:.2f}")
            print(f"  Ask:       ₹{quote['ask']:.2f}")
            print(f"  Volume:    {quote['volume']}")
            print(f"  Expiry:    {info['expiry'].split('T')[0]}")
            print(f"  Inst ID:   {info['instrument_id']}")
    print(f"{'='*50}")
    return ltp


def show_option_chain(fetcher, spot, num_strikes=10):
    """Show option chain around ATM"""
    atm_strike = round(spot / 50) * 50
    
    print(f"\n{'='*70}")
    print(f"  NIFTY OPTION CHAIN (Live from XTS)")
    print(f"  Spot: ₹{spot:,.2f} | ATM: {atm_strike} | Expiry: {fetcher.expiry}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    print(f"  {'Strike':>8}  {'CE LTP':>10}  {'CE Cost':>12}  {'PE LTP':>10}  {'PE Cost':>12}  {'Total':>10}")
    print(f"  {'-'*8}  {'-'*10}  {'-'*12}  {'-'*10}  {'-'*12}  {'-'*10}")
    
    half = num_strikes // 2
    for offset in range(-half, half + 1):
        strike = atm_strike + (offset * 50)
        
        ce_ltp, _ = fetcher.get_option_ltp(strike, 'CE', spot)
        pe_ltp, _ = fetcher.get_option_ltp(strike, 'PE', spot)
        
        ce_cost = ce_ltp * 65
        pe_cost = pe_ltp * 65
        
        marker = " <-- ATM" if offset == 0 else ""
        
        # Color coding hint
        itm_ce = "ITM" if spot > strike else "OTM"
        itm_pe = "ITM" if spot < strike else "OTM"
        
        print(f"  {strike:>8}  ₹{ce_ltp:>8.2f}  ₹{ce_cost:>10,.2f}  ₹{pe_ltp:>8.2f}  ₹{pe_cost:>10,.2f}  ₹{(ce_ltp+pe_ltp):>8.2f}{marker}")
    
    print(f"{'='*70}")


def show_trade_setup(fetcher, spot):
    """Show trade setup for both CALL and PUT signals"""
    atm_strike = round(spot / 50) * 50
    
    print(f"\n{'='*60}")
    print(f"  TRADE SETUP (as trading app would execute)")
    print(f"{'='*60}")
    
    for signal_type in ['CALL', 'PUT']:
        data = fetcher.get_option_data(signal_type, spot)
        opt = data['option_type']
        premium = data['premium']
        
        print(f"\n  {signal_type} Signal:")
        print(f"    Option:    NIFTY {data['strike']} {opt}")
        print(f"    Premium:   ₹{premium:.2f}")
        print(f"    Stop Loss: ₹{data['stop_loss']:.2f} (-30%)")
        print(f"    Target:    ₹{data['target']:.2f} (+50%)")
        print(f"    Cost (65): ₹{premium * 65:,.2f}")
        print(f"    R:R Ratio: 1:1.67")
    
    print(f"\n{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='Check NIFTY option prices from XTS API')
    parser.add_argument('--strike', type=int, help='Strike price to check (e.g., 25950)')
    parser.add_argument('--type', dest='opt_type', choices=['CE', 'PE'], help='Option type (CE or PE)')
    parser.add_argument('--chain', action='store_true', help='Show full option chain')
    parser.add_argument('--strikes', type=int, default=10, help='Number of strikes to show in chain (default: 10)')
    parser.add_argument('--setup', action='store_true', help='Show trade setup for CALL/PUT signals')
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("  NIFTY OPTION PRICE CHECKER")
    print("=" * 60)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize fetcher
    fetcher = NiftyATMOptionFetcher()
    if not fetcher.initialize():
        print("\n[ERROR] Failed to connect to XTS API.")
        print("Please check:")
        print("  1. XTS credentials in xts_config.py")
        print("  2. Market hours: 9:15 AM - 3:30 PM IST")
        print("  3. Network connectivity")
        return
    
    # Get spot price
    spot = fetcher.get_nifty_spot()
    if spot <= 0:
        print("[WARNING] Could not get NIFTY spot price from XTS. Using last known.")
        spot = 25950  # Fallback
    
    print(f"  NIFTY Spot: ₹{spot:,.2f}")
    print(f"  Expiry: {fetcher.expiry}")
    print(f"  Contracts: {len(fetcher.instrument_cache)}")
    
    # Determine what to show
    if args.strike and args.opt_type:
        # Check specific option
        check_single_option(fetcher, args.strike, args.opt_type, spot)
    elif args.strike:
        # Check both CE and PE for the strike
        check_single_option(fetcher, args.strike, 'CE', spot)
        check_single_option(fetcher, args.strike, 'PE', spot)
    elif args.chain:
        show_option_chain(fetcher, spot, args.strikes)
    elif args.setup:
        show_trade_setup(fetcher, spot)
    else:
        # Default: show ATM prices + chain + trade setup
        atm = round(spot / 50) * 50
        print(f"  ATM Strike: {atm}")
        
        # Quick ATM check
        check_single_option(fetcher, atm, 'CE', spot)
        check_single_option(fetcher, atm, 'PE', spot)
        
        # Show nearby chain
        show_option_chain(fetcher, spot, 10)
        
        # Show trade setup
        show_trade_setup(fetcher, spot)


if __name__ == "__main__":
    main()
