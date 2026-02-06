"""
Test XTS after subscription - check if quotes work post-subscribe
"""

import requests
import json
import time
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def xts_login():
    url = f"{XTS_BASE_URL}/auth/login"
    payload = {'secretKey': XTS_SECRET_KEY, 'appKey': XTS_APP_KEY, 'source': XTS_SOURCE}
    response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10, verify=False)
    
    if response.status_code == 200:
        token = response.json().get('result', {}).get('token')
        print(f"✅ Login: {token[:30]}...")
        return token
    return None

def subscribe_and_test():
    token = xts_login()
    if not token:
        return
    
    headers = {'Authorization': token, 'Content-Type': 'application/json'}
    
    # Calculate next Thursday expiry
    today = datetime.now()
    days_ahead = 3 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_thursday = today + timedelta(days_ahead)
    expiry = next_thursday.strftime("%d%b%y").upper()
    
    # Test instruments
    instruments = [
        f"NIFTY {expiry} 25300 CE",
        f"NIFTY {expiry} 25300 PE",
    ]
    
    print("\n" + "=" * 60)
    print("Step 1: Subscribe to instruments")
    print("=" * 60)
    
    for instrument in instruments:
        print(f"\n📡 Subscribing: {instrument}")
        
        url = f"{XTS_BASE_URL}/instruments/subscription"
        payload = {
            'instruments': [{'exchangeSegment': 2, 'exchangeInstrumentID': instrument}],
            'xtsMessageCode': 1501
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=5, verify=False)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("Step 2: Wait 2 seconds for data to populate")
    print("=" * 60)
    time.sleep(2)
    
    print("\n" + "=" * 60)
    print("Step 3: Fetch quotes after subscription")
    print("=" * 60)
    
    for instrument in instruments:
        print(f"\n📡 Fetching quotes: {instrument}")
        
        url = f"{XTS_BASE_URL}/instruments/quotes"
        payload = {
            'instruments': [{'exchangeSegment': 2, 'exchangeInstrumentID': instrument}],
            'xtsMessageCode': 1502,
            'publishFormat': 'JSON'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=5, verify=False)
        print(f"Status: {response.status_code}")
        data = response.json()
        
        print(f"\nFull response:")
        print(json.dumps(data, indent=2))
        
        # Check quotes
        if 'result' in data and 'listQuotes' in data['result']:
            quotes = data['result']['listQuotes']
            print(f"\nlistQuotes length: {len(quotes)}")
            
            if quotes and len(quotes) > 0:
                quote_str = quotes[0]
                print(f"Quote string: {quote_str}")
                
                if quote_str:
                    try:
                        quote_data = json.loads(quote_str)
                        print(f"\n✅ PARSED QUOTE DATA:")
                        print(json.dumps(quote_data, indent=2))
                        
                        if 'Touchline' in quote_data:
                            ltp = quote_data['Touchline'].get('LastTradedPrice', 0)
                            print(f"\n🎯 LTP: Rs.{ltp:.2f}")
                    except:
                        print(f"Cannot parse quote string")
            else:
                print("❌ Empty listQuotes - No data returned")
    
    print("\n" + "=" * 60)
    print("Step 4: Try OHLC endpoint")
    print("=" * 60)
    
    for instrument in instruments:
        print(f"\n📡 OHLC for: {instrument}")
        
        url = f"{XTS_BASE_URL}/instruments/ohlc"
        payload = {
            'instruments': [{'exchangeSegment': 2, 'exchangeInstrumentID': instrument}],
            'xtsMessageCode': 1512,
            'publishFormat': 'JSON'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=5, verify=False)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    print("\n📊 If listQuotes are still empty after subscription:")
    print("1. XTS may require WebSocket connection for streaming data")
    print("2. Option data might not be included in your subscription plan")
    print("3. Contact XTS support: support@symphonyfintech.com")
    print("4. Check if XTS Interactive API (not MarketData) is needed")
    print("\n📞 Recommended: Contact XTS support with:")
    print("   - Your APP_KEY")
    print("   - Ask about option chain data access")
    print("   - Ask if WebSocket is required for option quotes")

if __name__ == "__main__":
    subscribe_and_test()
