"""
XTS Paid API - Complete Option Chain Test
Since you have paid XTS API, let's find the correct way to fetch option prices
"""

import requests
import json
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def xts_login():
    """Login to XTS"""
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
        print(f"✅ XTS Login Success")
        print(f"🔑 Token: {token[:30]}...")
        return token
    else:
        print(f"❌ Login failed: {response.text}")
        return None

def test_instruments_master(token):
    """Test instruments/master endpoint to get instrument IDs"""
    print("\n" + "=" * 60)
    print("Test 1: Instruments Master File")
    print("=" * 60)
    
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    # Try to get instrument master for NFO
    url = f"{XTS_BASE_URL}/instruments/master"
    
    # Try different exchange segments
    for segment in [1, 2, 3]:  # 1=NSE, 2=NFO, 3=BSE
        print(f"\n📡 Trying exchangeSegment={segment}...")
        params = {'exchangeSegment': segment}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10, verify=False)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                # Master file is usually CSV or JSON
                content = response.text[:500]
                print(f"Content preview: {content}")
                
                # Save to file for inspection
                filename = f"xts_master_segment_{segment}.csv"
                with open(filename, 'w') as f:
                    f.write(response.text)
                print(f"✅ Saved to {filename}")
            else:
                print(f"Error: {response.text[:200]}")
        except Exception as e:
            print(f"Error: {e}")

def test_option_search(token):
    """Test search endpoint for option instruments"""
    print("\n" + "=" * 60)
    print("Test 2: Search Option Instruments")
    print("=" * 60)
    
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    # Try search endpoint
    url = f"{XTS_BASE_URL}/search/instruments"
    
    search_terms = ["NIFTY", "NIFTY 25300", "NIFTY25300CE", "NIFTY 25300 CE", "NIFTY26JAN25300CE"]
    
    for term in search_terms:
        print(f"\n📡 Searching: '{term}'")
        params = {'searchString': term}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10, verify=False)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)[:500]}")
            else:
                print(f"Error: {response.text[:200]}")
        except Exception as e:
            print(f"Error: {e}")

def test_option_chain_endpoint(token):
    """Test if there's an option chain endpoint"""
    print("\n" + "=" * 60)
    print("Test 3: Option Chain Endpoints")
    print("=" * 60)
    
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    # Try various endpoints
    endpoints = [
        '/instruments/optionchain',
        '/instruments/derivative',
        '/instruments/options',
        '/market/optionchain',
        '/instruments/quotes/nfo',
        '/instruments/subscription'
    ]
    
    for endpoint in endpoints:
        url = f"{XTS_BASE_URL}{endpoint}"
        print(f"\n📡 Trying: {url}")
        
        # Try with NIFTY parameter
        try:
            response = requests.get(url, headers=headers, params={'symbol': 'NIFTY'}, timeout=5, verify=False)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ Success! Response: {response.text[:300]}")
            else:
                print(f"Response: {response.text[:150]}")
        except Exception as e:
            print(f"Error: {type(e).__name__}")

def test_specific_instrument_id(token):
    """Test with known instrument IDs from NSE"""
    print("\n" + "=" * 60)
    print("Test 4: Specific Instrument IDs")
    print("=" * 60)
    
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    # Based on NSE, option instrument IDs are usually numeric
    # Let's try some known patterns
    url = f"{XTS_BASE_URL}/instruments/quotes"
    
    # Try different instrument ID formats
    test_instruments = [
        {"exchangeSegment": 2, "exchangeInstrumentID": "NIFTY26JAN2025300CE"},
        {"exchangeSegment": 2, "exchangeInstrumentID": "NIFTY 26JAN26 25300 CE"},
        {"exchangeSegment": 2, "exchangeInstrumentID": "NIFTY 30JAN26 25300 CE"},
        {"exchangeSegment": 2, "exchangeInstrumentID": "35009"},  # Numeric ID example
        {"exchangeSegment": 2, "exchangeInstrumentID": 35009},    # Numeric without quotes
    ]
    
    for instrument in test_instruments:
        print(f"\n📡 Testing: {instrument}")
        
        payload = {
            'instruments': [instrument],
            'xtsMessageCode': 1502,
            'publishFormat': 'JSON'
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=5, verify=False)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                # Check if we got quotes
                if 'result' in data and 'listQuotes' in data['result']:
                    quotes = data['result']['listQuotes']
                    if quotes and len(quotes) > 0 and quotes[0]:
                        print(f"✅ GOT DATA! Quote: {quotes[0][:200]}")
            else:
                print(f"Error: {response.text[:200]}")
        except Exception as e:
            print(f"Error: {e}")

def test_subscription_mode(token):
    """Test if we need to subscribe to instruments first"""
    print("\n" + "=" * 60)
    print("Test 5: Subscription Mode")
    print("=" * 60)
    print("Note: Some APIs require subscribing to instruments before getting quotes")
    
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    # Try subscription endpoints
    subscribe_urls = [
        f"{XTS_BASE_URL}/instruments/subscription",
        f"{XTS_BASE_URL}/market/subscription",
    ]
    
    for url in subscribe_urls:
        print(f"\n📡 Trying: {url}")
        
        payload = {
            'instruments': [{
                'exchangeSegment': 2,
                'exchangeInstrumentID': 'NIFTY 25300 CE'
            }],
            'xtsMessageCode': 1501  # Subscribe code
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=5, verify=False)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
        except Exception as e:
            print(f"Error: {type(e).__name__}: {str(e)[:100]}")

if __name__ == "__main__":
    print("=" * 60)
    print("XTS Paid API - Complete Option Chain Exploration")
    print("=" * 60)
    
    # Login
    token = xts_login()
    
    if not token:
        print("\n❌ Cannot proceed without token")
        exit(1)
    
    # Run all tests
    test_instruments_master(token)
    test_option_search(token)
    test_option_chain_endpoint(token)
    test_specific_instrument_id(token)
    test_subscription_mode(token)
    
    print("\n" + "=" * 60)
    print("Testing Complete!")
    print("=" * 60)
    print("\n💡 Next Steps:")
    print("1. Check saved CSV files for instrument IDs")
    print("2. If search found instruments, use those exact formats")
    print("3. Contact XTS support for option data documentation")
