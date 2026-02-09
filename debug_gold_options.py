"""
Debug script to investigate Gold option data fetching issues
"""

import requests
import json
from datetime import datetime
import urllib3
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def login():
    """Login to XTS API"""
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
        print(f"[OK] Login successful")
        return token
    return None

def search_gold_instruments(token, segment):
    """Search for Gold instruments in a segment"""
    print(f"\n{'='*70}")
    print(f"SEARCHING FOR GOLD INSTRUMENTS IN SEGMENT {segment}")
    print(f"{'='*70}")
    
    url = f"{XTS_BASE_URL}/instruments/master"
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    
    params = {
        'exchangeSegment': segment
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30, verify=False)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            # Save full response
            filename = f'debug_segment_{segment}_master.json'
            with open(filename, 'w') as f:
                f.write(response.text)
            print(f"[OK] Saved full response to {filename}")
            
            # Search for GOLD in the response
            text = response.text.upper()
            if 'GOLD' in text:
                print(f"[OK] 'GOLD' found in segment {segment} master data")
                
                # Try to parse and find Gold instruments
                try:
                    data = response.json()
                    if 'result' in data:
                        instruments = data['result']
                        
                        # Search for Gold options
                        gold_options = []
                        gold_futures = []
                        
                        for inst in instruments[:1000]:  # Check first 1000
                            if isinstance(inst, dict):
                                name = inst.get('Name', '').upper()
                                symbol = inst.get('Symbol', '').upper()
                                description = inst.get('Description', '').upper()
                                
                                if 'GOLD' in name or 'GOLD' in symbol or 'GOLD' in description:
                                    inst_id = inst.get('ExchangeInstrumentID', 'N/A')
                                    
                                    if 'CE' in name or 'PE' in name or 'CALL' in name or 'PUT' in name:
                                        gold_options.append({
                                            'id': inst_id,
                                            'name': inst.get('Name', 'N/A'),
                                            'symbol': inst.get('Symbol', 'N/A'),
                                            'description': inst.get('Description', 'N/A')
                                        })
                                    else:
                                        gold_futures.append({
                                            'id': inst_id,
                                            'name': inst.get('Name', 'N/A'),
                                            'symbol': inst.get('Symbol', 'N/A'),
                                            'description': inst.get('Description', 'N/A')
                                        })
                        
                        print(f"\n[FOUND] {len(gold_futures)} Gold Futures")
                        for i, inst in enumerate(gold_futures[:5]):
                            print(f"  {i+1}. ID: {inst['id']}")
                            print(f"     Name: {inst['name']}")
                            print(f"     Symbol: {inst['symbol']}")
                        
                        print(f"\n[FOUND] {len(gold_options)} Gold Options")
                        for i, inst in enumerate(gold_options[:10]):
                            print(f"  {i+1}. ID: {inst['id']}")
                            print(f"     Name: {inst['name']}")
                            print(f"     Symbol: {inst['symbol']}")
                        
                        # Save to separate files
                        if gold_futures:
                            with open(f'gold_futures_segment_{segment}.json', 'w') as f:
                                json.dump(gold_futures[:20], f, indent=2)
                        
                        if gold_options:
                            with open(f'gold_options_segment_{segment}.json', 'w') as f:
                                json.dump(gold_options[:50], f, indent=2)
                        
                except Exception as e:
                    print(f"[ERROR] Parsing error: {e}")
            else:
                print(f"[WARNING] 'GOLD' not found in segment {segment}")
        else:
            print(f"[ERROR] Request failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
    
    except Exception as e:
        print(f"[ERROR] {e}")

def test_gold_quote(token, segment, instrument_id, description):
    """Test fetching a quote for a Gold instrument"""
    print(f"\n{'='*70}")
    print(f"TESTING QUOTE: {description}")
    print(f"Segment: {segment}, Instrument ID: {instrument_id}")
    print(f"{'='*70}")
    
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
    
    print(f"\n[REQUEST]")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5, verify=False)
        
        print(f"\n[RESPONSE]")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n[PARSED RESPONSE]")
            print(json.dumps(data, indent=2))
            
            # Try to extract price
            if 'result' in data:
                result = data['result']
                
                # Check all possible keys
                print(f"\n[RESULT KEYS]: {list(result.keys())}")
                
                # Try listQuotes
                if 'listQuotes' in result and result['listQuotes']:
                    print(f"\n[LIST QUOTES]: {result['listQuotes']}")
                
                # Try quotesList
                if 'quotesList' in result and result['quotesList']:
                    print(f"\n[QUOTES LIST]: {result['quotesList']}")
            
            return True
        else:
            print(f"[ERROR] Quote request failed")
            return False
    
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def test_option_symbol_formats(token, segment):
    """Test different Gold option symbol formats"""
    print(f"\n{'='*70}")
    print(f"TESTING DIFFERENT SYMBOL FORMATS")
    print(f"{'='*70}")
    
    # Different formats to try
    formats = [
        "GOLDM 26MAR26 75000 CE",
        "GOLDM26MAR2675000CE",
        "GOLDM 26MAR2026 75000 CE",
        "GOLDM APR 2026 75000 CE",
        "GOLDM26MAR26 75000CE",
        "GOLD 26MAR26 75000 CE",
        "GOLD MAR 2026 75000 CE",
        "55555",  # Try numeric ID
        "GOLDM FEB 2026 75000 CE",
        "GOLDM05MAR2675000CE",
    ]
    
    for symbol in formats:
        print(f"\nTrying: {symbol}")
        test_gold_quote(token, segment, symbol, f"Format test: {symbol}")

def main():
    print("="*70)
    print("GOLD OPTIONS DEBUG TOOL")
    print("="*70)
    
    # Login
    print("\n[STEP 1] Logging in...")
    token = login()
    if not token:
        print("[ERROR] Login failed")
        return
    
    # Search for Gold instruments in different segments
    print("\n[STEP 2] Searching for Gold instruments...")
    for segment in [3, 51, 4, 5]:
        search_gold_instruments(token, segment)
    
    # Test some common formats
    print("\n[STEP 3] Testing option symbol formats in segment 51...")
    test_option_symbol_formats(token, 51)
    
    print("\n" + "="*70)
    print("DEBUG COMPLETE - Check generated JSON files")
    print("="*70)

if __name__ == "__main__":
    main()
