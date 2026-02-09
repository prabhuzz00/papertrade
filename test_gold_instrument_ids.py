"""
Comprehensive test to find working Gold instrument IDs using OHLC endpoint
"""

import requests
import json
from datetime import datetime, timedelta
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
        print(f"[OK] Login successful\n")
        return token
    return None

def test_ohlc_get(token, segment, instrument_id, description):
    """Test OHLC GET endpoint with an instrument ID"""
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=2)
        
        start_str = start_time.strftime("%b %d %Y %H:%M:%S")
        end_str = end_time.strftime("%b %d %Y %H:%M:%S")
        
        url = f"{XTS_BASE_URL}/instruments/ohlc"
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        
        params = {
            'exchangeSegment': segment,
            'exchangeInstrumentID': instrument_id,
            'startTime': start_str,
            'endTime': end_str,
            'compressionValue': 60
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if we have actual data
            if 'result' in data and 'dataReponse' in data['result']:
                candles = data['result']['dataReponse']
                
                if candles and candles != '' and len(candles) > 0:
                    print(f"[SUCCESS] {description}")
                    print(f"   Segment: {segment}, ID: {instrument_id}")
                    print(f"   Candles found: {len(candles)}")
                    if isinstance(candles, list) and len(candles) > 0:
                        last_candle = candles[-1]
                        print(f"   Last candle: {last_candle}")
                    print()
                    return True
                else:
                    print(f"[EMPTY] {description} - No candle data")
            else:
                print(f"[FAIL] {description} - No result")
        else:
            print(f"[ERROR] {description} - Status {response.status_code}")
    
    except Exception as e:
        print(f"[ERROR] {description} - {str(e)}")
    
    return False

def main():
    print("="*70)
    print("COMPREHENSIVE GOLD INSTRUMENT ID TEST")
    print("="*70)
    print("Testing OHLC GET endpoint with various instrument IDs\n")
    
    token = login()
    if not token:
        print("[ERROR] Login failed")
        return
    
    # Test 1: Known working instrument (NIFTY)
    print("="*70)
    print("TEST 1: Known Working Instrument (NIFTY 50)")
    print("="*70)
    test_ohlc_get(token, 1, 26000, "NIFTY 50 Index (NSE)")
    test_ohlc_get(token, 1, "NIFTY 50", "NIFTY 50 String Symbol")
    
    # Test 2: Gold string symbols
    print("\n" + "="*70)
    print("TEST 2: Gold String Symbols")
    print("="*70)
    gold_symbols = [
        "GOLD",
        "GOLDM",
        "GOLD FEB 2026",
        "GOLDM FEB 2026",
        "GOLD26FEB2026FUT",
        "GOLDM26FEB2026FUT",
    ]
    
    for symbol in gold_symbols:
        for segment in [3, 51]:
            test_ohlc_get(token, segment, symbol, f"Seg {segment}: {symbol}")
    
    # Test 3: Numeric IDs (try range)
    print("\n" + "="*70)
    print("TEST 3: Numeric Instrument IDs (MCX)")
    print("="*70)
    
    # Try common ranges for MCX
    test_ranges = [
        (3, list(range(1, 20))),         # 1-19
        (3, list(range(100, 120))),      # 100-119
        (3, list(range(1000, 1020))),    # 1000-1019
        (51, list(range(1, 20))),        # MCXSX 1-19
        (51, list(range(100, 120))),     # MCXSX 100-119
        (51, list(range(50000, 50020))), # Higher range
    ]
    
    found_any = False
    for segment, id_range in test_ranges:
        print(f"\nTrying Segment {segment}, IDs {id_range[0]}-{id_range[-1]}:")
        for instrument_id in id_range:
            result = test_ohlc_get(token, segment, instrument_id, f"Seg {segment} ID {instrument_id}")
            if result:
                found_any = True
                print(f"*** FOUND WORKING ID: {instrument_id} in Segment {segment} ***\n")
    
    # Test 4: Gold future months (try actual contract format)
    print("\n" + "="*70)
    print("TEST 4: Gold Future Contract Formats")
    print("="*70)
    
    future_formats = [
        "GOLD 5 FEB 26",
        "GOLDM 5 FEB 26",
        "GOLDPETAL 5 FEB 26",
        "GOLD FEB26 FUT",
        "GOLDM FEB26 FUT",
    ]
    
    for fmt in future_formats:
        for segment in [3, 51]:
            test_ohlc_get(token, segment, fmt, f"Seg {segment}: {fmt}")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    
    if found_any:
        print("\n[SUCCESS] Found working instrument IDs!")
        print("Use these IDs to fetch Gold data.")
    else:
        print("\n[CONCLUSION] No Gold instruments found with data.")
        print("\nPossible reasons:")
        print("1. Market is closed (current time may be outside 10 AM - 11:30 PM IST)")
        print("2. Need exact numeric IDs from broker's instrument master file")
        print("3. XTS broker account may not have MCX data access enabled")
        print("4. MCX data requires WebSocket subscription")
        print("\n[RECOMMENDATION] Contact your XTS broker for:")
        print("- MCX instrument master CSV file")
        print("- Numeric exchangeInstrumentID for Gold/GoldM futures and options")
        print("- Account access verification for MCX data feed")

if __name__ == "__main__":
    main()
