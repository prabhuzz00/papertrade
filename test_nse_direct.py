"""
Test NSE Option Chain API directly
"""

import requests
import json

def test_nse_api():
    """Test NSE option chain API with proper headers"""
    
    print("=" * 60)
    print("Testing NSE Option Chain API")
    print("=" * 60)
    
    # Enhanced browser-like headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    try:
        # Step 1: Get cookies by visiting main page
        print("\n📡 Step 1: Getting cookies from NSE homepage...")
        session = requests.Session()
        
        # First visit to get initial cookies
        base_response = session.get('https://www.nseindia.com', headers=headers, timeout=10)
        print(f"✅ Homepage Status: {base_response.status_code}")
        
        # Visit option chain page to get more cookies
        headers['Referer'] = 'https://www.nseindia.com/'
        oc_response = session.get('https://www.nseindia.com/option-chain', headers=headers, timeout=10)
        print(f"✅ Option Chain Page Status: {oc_response.status_code}")
        print(f"🍪 Cookies received: {len(session.cookies)}")
        
        # Step 2: Fetch option chain
        print("\n📡 Step 2: Fetching option chain data...")
        headers['Referer'] = 'https://www.nseindia.com/option-chain'
        url = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
        response = session.get(url, headers=headers, timeout=10)
        print(f"✅ API Status: {response.status_code}")
        print(f"📦 Response size: {len(response.content)} bytes")
        print(f"✅ API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check data structure
            print(f"\n📊 Response keys: {list(data.keys())}")
            
            if 'records' in data:
                records = data['records']
                print(f"📊 Records keys: {list(records.keys())}")
                
                if 'data' in records:
                    option_data = records['data']
                    print(f"📊 Total strike records: {len(option_data)}")
                    
                    # Find ATM strikes (around 25300)
                    print("\n" + "=" * 60)
                    print("ATM Option Prices (Strike 25250-25350)")
                    print("=" * 60)
                    
                    for record in option_data:
                        strike = record.get('strikePrice', 0)
                        
                        if 25250 <= strike <= 25350:
                            print(f"\n📍 Strike: {strike}")
                            
                            # Call option data
                            if 'CE' in record:
                                ce = record['CE']
                                ce_ltp = ce.get('lastPrice', 0)
                                ce_iv = ce.get('impliedVolatility', 0)
                                ce_oi = ce.get('openInterest', 0)
                                print(f"  📈 CE: LTP=Rs.{ce_ltp:.2f}, IV={ce_iv:.2f}%, OI={ce_oi}")
                            
                            # Put option data
                            if 'PE' in record:
                                pe = record['PE']
                                pe_ltp = pe.get('lastPrice', 0)
                                pe_iv = pe.get('impliedVolatility', 0)
                                pe_oi = pe.get('openInterest', 0)
                                print(f"  📉 PE: LTP=Rs.{pe_ltp:.2f}, IV={pe_iv:.2f}%, OI={pe_oi}")
                    
                    print("\n" + "=" * 60)
                    print("✅ NSE API is working!")
                    print("=" * 60)
                else:
                    print("\n❌ No 'data' field in records")
                    print(f"Records content: {json.dumps(records, indent=2)[:500]}")
            else:
                print("\n❌ No 'records' field in response")
                print(f"Response content: {json.dumps(data, indent=2)[:500]}")
        else:
            print(f"\n❌ Failed with status code: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out")
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection error - check internet")
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_nse_api()
