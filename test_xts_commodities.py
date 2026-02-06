"""
Test script to check if XTS API can fetch Gold and Crude Oil data
"""

import requests
import json
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def xts_login():
    """Login to XTS API"""
    try:
        url = f"{XTS_BASE_URL}/auth/login"
        payload = {
            'secretKey': XTS_SECRET_KEY,
            'appKey': XTS_APP_KEY,
            'source': XTS_SOURCE
        }
        
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, 
                               timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('result', {}).get('token')
            print(f"✅ XTS Login successful")
            print(f"Token: {token[:30]}...")
            return token
        else:
            print(f"❌ Login failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_instrument(token, segment, instrument_id, name):
    """Test fetching quotes for an instrument"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Segment: {segment}, Instrument ID: {instrument_id}")
    print(f"{'='*60}")
    
    try:
        url = f"{XTS_BASE_URL}/instruments/quotes"
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'instruments': [{
                'exchangeSegment': segment,
                'exchangeInstrumentID': instrument_id
            }],
            'xtsMessageCode': 1502,
            'publishFormat': 'JSON'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=5, verify=False)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            # Try to extract price
            if 'result' in data and 'listQuotes' in data['result']:
                quotes_list = data['result']['listQuotes']
                if quotes_list and len(quotes_list) > 0:
                    quote_str = quotes_list[0]
                    if quote_str:
                        try:
                            quote_data = json.loads(quote_str)
                            if 'Touchline' in quote_data:
                                ltp = quote_data['Touchline'].get('LastTradedPrice', 0)
                                print(f"✅ Last Traded Price: {ltp}")
                                return True
                        except:
                            pass
            
            print(f"⚠️ Could not extract price from response")
            return False
        else:
            print(f"❌ Request failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def search_instruments(token, search_term):
    """Search for instruments by name"""
    print(f"\n{'='*60}")
    print(f"Searching for: {search_term}")
    print(f"{'='*60}")
    
    try:
        url = f"{XTS_BASE_URL}/instruments/master"
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        
        # Try different segments
        # 1 = NSE, 2 = NFO, 3 = MCX (Commodities)
        for segment in [1, 2, 3, 4, 5]:
            print(f"\nSearching in Segment {segment}...")
            payload = {
                'exchangeSegment': segment
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                # Response might be large, search for our term
                text = response.text.lower()
                if search_term.lower() in text:
                    print(f"✅ Found '{search_term}' in segment {segment}")
                    # Try to parse and find specific entries
                    try:
                        data = response.json()
                        if 'result' in data:
                            # Save to file for inspection
                            filename = f"xts_segment_{segment}_master.json"
                            with open(filename, 'w') as f:
                                json.dump(data, f, indent=2)
                            print(f"   Saved to {filename}")
                    except:
                        pass
                else:
                    print(f"   '{search_term}' not found in segment {segment}")
            else:
                print(f"   Segment {segment} request failed: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Search error: {e}")

if __name__ == "__main__":
    print("XTS API - Commodity Testing")
    print("="*60)
    
    # Login
    token = xts_login()
    if not token:
        print("Failed to login. Exiting.")
        exit(1)
    
    # Test known instruments
    print("\n\nTesting Known Instruments:")
    test_instrument(token, 1, 26000, "NIFTY 50 Index (NSE)")
    test_instrument(token, 1, 26009, "BANK NIFTY Index (NSE)")
    
    # Try common MCX segment IDs (segment 3 is typically MCX)
    print("\n\nTesting Potential Commodity Instruments:")
    test_instrument(token, 3, 1, "MCX Gold (Test ID 1)")
    test_instrument(token, 3, 2, "MCX Crude Oil (Test ID 2)")
    test_instrument(token, 3, 100, "MCX Test ID 100")
    test_instrument(token, 3, 1000, "MCX Test ID 1000")
    
    # Search for Gold and Crude Oil
    print("\n\nSearching for instruments:")
    search_instruments(token, "GOLD")
    search_instruments(token, "CRUDE")
    
    print("\n" + "="*60)
    print("Testing complete!")
    print("="*60)
