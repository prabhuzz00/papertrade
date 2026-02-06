"""
Debug XTS option quotes
"""
import requests
import json
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Login
url = f"{XTS_BASE_URL}/auth/login"
payload = {'secretKey': XTS_SECRET_KEY, 'appKey': XTS_APP_KEY, 'source': XTS_SOURCE}
response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10, verify=False)
token = response.json().get('result', {}).get('token')

print(f"Token: {token[:30]}...")

# Try different option formats
test_formats = [
    "NIFTY 25300 CE",
    "NIFTY25300CE",
    "NIFTY 30JAN2026 25300 CE",
    "NIFTY30JAN202625300CE",
    43507,  # Example instrument ID
    "NIFTY",
]

url = f"{XTS_BASE_URL}/instruments/quotes"
headers = {'Authorization': token, 'Content-Type': 'application/json'}

for fmt in test_formats:
    print(f"\n{'='*60}")
    print(f"Testing format: {fmt}")
    print('='*60)
    
    payload = {
        'instruments': [{'exchangeSegment': 2, 'exchangeInstrumentID': fmt}],
        'xtsMessageCode': 1502,
        'publishFormat': 'JSON'
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=5, verify=False)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Status: {response.status_code}")
        print(f"Response type: {data.get('type')}")
        print(f"Description: {data.get('description')}")
        
        if 'result' in data:
            result = data['result']
            print(f"MDG: {result.get('mdp')}")
            print(f"listQuotes length: {len(result.get('listQuotes', []))}")
            
            if result.get('listQuotes'):
                quote_str = result['listQuotes'][0]
                if quote_str:
                    print(f"\n📊 Quote data found!")
                    try:
                        quote = json.loads(quote_str)
                        print(f"Instrument: {quote.get('ExchangeInstrumentID')}")
                        if 'Touchline' in quote:
                            ltp = quote['Touchline'].get('LastTradedPrice')
                            print(f"✅ LTP: Rs.{ltp}")
                    except:
                        print(f"Raw: {quote_str[:200]}")
                else:
                    print("⚠️ Empty quote string")
            else:
                print("⚠️ listQuotes is empty")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"Response: {response.text[:200]}")
