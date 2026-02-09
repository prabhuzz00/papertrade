"""
Quick comparison script to fetch both NIFTY and Gold option LTPs

Usage: python fetch_all_options.py
"""

from fetch_atm_option_ltp import ATMOptionFetcher
from fetch_gold_option_ltp import GoldOptionFetcher
import json

def main():
    print("="*70)
    print("MULTI-ASSET OPTION LTP FETCHER")
    print("="*70)
    
    results = {}
    
    # Fetch NIFTY options
    print("\n[1/2] Fetching NIFTY Options...")
    print("-"*70)
    nifty_fetcher = ATMOptionFetcher()
    if nifty_fetcher.login():
        nifty_result = nifty_fetcher.fetch_atm_options()
        if nifty_result:
            results['NIFTY'] = nifty_result
    
    # Fetch Gold options
    print("\n\n[2/2] Fetching Gold Options...")
    print("-"*70)
    gold_fetcher = GoldOptionFetcher()
    if gold_fetcher.login():
        # Try segment 3 first
        gold_result = gold_fetcher.fetch_atm_options(segment=3)
        if gold_result:
            results['GOLD'] = gold_result
    
    # Summary comparison
    print("\n\n" + "="*70)
    print("FINAL SUMMARY - ALL ASSETS")
    print("="*70)
    
    if 'NIFTY' in results:
        nifty = results['NIFTY']
        print("\nNIFTY 50 (NSE):")
        print(f"  Spot: Rs.{nifty['spot_price']:.2f}")
        print(f"  ATM Strike: {nifty['atm_strike']}")
        print(f"  Expiry: {nifty['expiry']}")
        if 'error' not in nifty.get('call', {}):
            print(f"  Call LTP: Rs.{nifty['call']['ltp']:.2f}")
        if 'error' not in nifty.get('put', {}):
            print(f"  Put LTP: Rs.{nifty['put']['ltp']:.2f}")
    
    if 'GOLD' in results:
        gold = results['GOLD']
        print("\nGOLD (MCX):")
        print(f"  Price: Rs.{gold['spot_price']:.2f} per 10g")
        print(f"  ATM Strike: {gold['atm_strike']}")
        print(f"  Expiry: {gold['expiry']}")
        if 'error' not in gold.get('call', {}):
            print(f"  Call LTP: Rs.{gold['call']['ltp']:.2f}")
        if 'error' not in gold.get('put', {}):
            print(f"  Put LTP: Rs.{gold['put']['ltp']:.2f}")
    
    print("\n" + "="*70)
    
    # Save combined results
    with open('all_options_ltp.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\n[OK] Combined results saved to all_options_ltp.json")

if __name__ == "__main__":
    main()
