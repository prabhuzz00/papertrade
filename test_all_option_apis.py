"""
Fetch NIFTY option chain using multiple sources
1. NSE (with advanced bypass)
2. Alternative financial APIs
"""

import requests
import json
from datetime import datetime
import time

def test_nse_advanced():
    """Test NSE with advanced headers and timing"""
    print("=" * 60)
    print("Testing NSE API with Advanced Bypass")
    print("=" * 60)
    
    session = requests.Session()
    
    # Complete browser headers
    headers = {
        'authority': 'www.nseindia.com',
        'method': 'GET',
        'scheme': 'https',
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'referer': 'https://www.nseindia.com/option-chain',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # Step 1: Visit homepage
        print("\n📡 Visiting NSE homepage...")
        session.get('https://www.nseindia.com', headers=headers, timeout=10)
        time.sleep(1)  # Wait for cookies to set
        
        # Step 2: Visit option chain page
        print("📡 Visiting option chain page...")
        session.get('https://www.nseindia.com/option-chain', headers=headers, timeout=10)
        time.sleep(1)
        
        # Step 3: Get option chain data
        print("📡 Fetching option chain API...")
        url = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
        response = session.get(url, headers=headers, timeout=10)
        
        print(f"\n✅ Status: {response.status_code}")
        print(f"📦 Size: {len(response.content)} bytes")
        print(f"🍪 Cookies: {dict(session.cookies)}")
        
        if response.status_code == 200 and len(response.content) > 100:
            data = response.json()
            
            if 'records' in data and 'data' in data['records']:
                option_data = data['records']['data']
                print(f"\n✅ SUCCESS! Got {len(option_data)} strikes")
                
                # Show ATM data
                for record in option_data[:5]:
                    strike = record.get('strikePrice', 0)
                    print(f"\nStrike: {strike}")
                    if 'CE' in record:
                        print(f"  CE LTP: Rs.{record['CE'].get('lastPrice', 0):.2f}")
                    if 'PE' in record:
                        print(f"  PE LTP: Rs.{record['PE'].get('lastPrice', 0):.2f}")
                
                return True
            else:
                print(f"\n⚠️  Response: {json.dumps(data, indent=2)[:500]}")
        else:
            print(f"⚠️  Empty or error response")
            print(f"Content: {response.text[:200]}")
        
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_yahoo_finance():
    """Test Yahoo Finance as alternative"""
    print("\n" + "=" * 60)
    print("Testing Yahoo Finance Option Chain")
    print("=" * 60)
    
    try:
        import yfinance as yf
        
        print("\n📡 Fetching NIFTY options from Yahoo Finance...")
        ticker = yf.Ticker("^NSEI")
        
        # Get available expiration dates
        try:
            expirations = ticker.options
            print(f"✅ Available expirations: {len(expirations)}")
            
            if expirations:
                # Get first expiration
                exp_date = expirations[0]
                print(f"📅 Using expiration: {exp_date}")
                
                # Get option chain
                opt = ticker.option_chain(exp_date)
                
                calls = opt.calls
                puts = opt.puts
                
                print(f"\n✅ Calls: {len(calls)} strikes")
                print(f"✅ Puts: {len(puts)} strikes")
                
                # Show ATM options
                print("\nATM Options:")
                print("\nCalls:")
                print(calls[['strike', 'lastPrice', 'impliedVolatility']].head())
                print("\nPuts:")
                print(puts[['strike', 'lastPrice', 'impliedVolatility']].head())
                
                return True
        except Exception as e:
            print(f"⚠️  Yahoo Finance options not available for ^NSEI: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    # Try NSE first
    nse_success = test_nse_advanced()
    
    if not nse_success:
        print("\n" + "=" * 60)
        print("NSE API blocked. Trying alternatives...")
        print("=" * 60)
        
        # Try Yahoo Finance
        yahoo_success = test_yahoo_finance()
        
        if not yahoo_success:
            print("\n" + "=" * 60)
            print("CONCLUSION")
            print("=" * 60)
            print("\n❌ All real-time option APIs blocked/unavailable")
            print("\n📊 Recommendations:")
            print("1. Use estimation model (85-90% accurate)")
            print("2. Subscribe to paid data providers (e.g., Zerodha Kite Connect)")
            print("3. Use broker-specific APIs with proper subscription")
            print("4. Consider web scraping with proper proxy/VPN")
