"""
Test XTS API to understand response format
"""

import requests
import json
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE
from datetime import datetime
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
        print(f"✅ Login successful")
        print(f"Token: {token[:30]}...")
        return token
    else:
        print(f"❌ Login failed: {response.text}")
        return None

def test_search_instruments(token):
    """Search for NIFTY options"""
    print("\n" + "="*70)
    print("Testing instrument search...")
    print("="*70)
    
    url = f"{XTS_BASE_URL}/instruments/master"
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    # Get instruments for NFO (segment 2)
    params = {
        'exchangeSegment': 2  # NFO
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=10, verify=False)
    
    if response.status_code == 200:
        print(f"✅ Instruments fetched successfully")
        data = response.json()
        print(f"Response keys: {data.keys()}")
        
        # Save to file for analysis
        with open('xts_instruments.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("💾 Saved to xts_instruments.json")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

def test_get_quotes(token):
    """Test getting quotes for NIFTY index"""
    print("\n" + "="*70)
    print("Testing NIFTY quotes...")
    print("="*70)
    
    url = f"{XTS_BASE_URL}/instruments/quotes"
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    # Try to get NIFTY 50 index quotes
    payload = {
        'instruments': [{
            'exchangeSegment': 1,  # NSE
            'exchangeInstrumentID': 26000  # NIFTY 50 instrument ID
        }],
        'xtsMessageCode': 1502,
        'publishFormat': 'JSON'
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n📊 NIFTY Quote Data:")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Failed to get quotes")

def test_option_quote(token):
    """Test getting option quote"""
    print("\n" + "="*70)
    print("Testing option quotes...")
    print("="*70)
    
    # Common NIFTY option instrument IDs (you may need to adjust)
    test_instruments = [
        {'exchangeSegment': 2, 'exchangeInstrumentID': 'NIFTY 25250 CE'},
        {'exchangeSegment': 2, 'exchangeInstrumentID': 43507},  # Example ID
    ]
    
    url = f"{XTS_BASE_URL}/instruments/quotes"
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    for inst in test_instruments:
        print(f"\nTrying: {inst}")
        payload = {
            'instruments': [inst],
            'xtsMessageCode': 1502,
            'publishFormat': 'JSON'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Success!")
            print(json.dumps(response.json(), indent=2))
            break
        else:
            print(f"Response: {response.text[:200]}")

if __name__ == "__main__":
    print("XTS API Testing")
    print("="*70)
    
    # Login
    token = xts_login()
    
    if token:
        # Test different endpoints
        test_get_quotes(token)
        test_search_instruments(token)
        test_option_quote(token)
