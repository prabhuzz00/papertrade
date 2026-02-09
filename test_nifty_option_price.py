"""
Test script to fetch NIFTY option prices using GetOptionSymbol API
Demonstrates working implementation of the documented XTS API
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
    
    response = requests.post(
        url, json=payload,
        headers={'Content-Type': 'application/json'},
        timeout=10, verify=False
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get('result', {}).get('token')
        if token:
            print("✓ Login successful\n")
            return token
    
    print(f"✗ Login failed: {response.text}")
    return None


def get_nifty_spot(token):
    """Get NIFTY 50 spot price"""
    url = f"{XTS_BASE_URL}/instruments/quotes"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': token
    }
    
    payload = {
        "instruments": [
            {
                "exchangeSegment": 1,
                "exchangeInstrumentID": 26000
            }
        ],
        "xtsMessageCode": 1502,
        "publishFormat": "JSON"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'listQuotes' in data['result']:
                quotes = data['result']['listQuotes']
                if quotes and len(quotes) > 0:
                    quote = quotes[0]
                    # Quote might be a JSON string that needs parsing
                    if isinstance(quote, str):
                        quote = json.loads(quote)
                    
                    if isinstance(quote, dict) and 'Touchline' in quote:
                        ltp = quote['Touchline'].get('LastTradedPrice')
                        if ltp:
                            return float(ltp)
    except Exception as e:
        print(f"Error fetching NIFTY spot: {e}")
    
    return None


def get_expiry_dates(token):
    """Get available NIFTY option expiry dates"""
    url = f"{XTS_BASE_URL}/instruments/instrument/expiryDate"
    headers = {'Authorization': token}
    
    params = {
        'exchangeSegment': 2,  # NFO
        'series': 'OPTIDX',
        'symbol': 'NIFTY'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            data = response.json()
            if 'result' in data:
                return data['result']
    except Exception as e:
        print(f"Error fetching expiry dates: {e}")
    
    return None


def get_option_details(token, expiry_date, option_type, strike_price):
    """
    Get option instrument details using GetOptionSymbol endpoint
    
    Args:
        token: XTS auth token
        expiry_date: Date in 'ddMmmyyyy' format (e.g., '10Feb2026')
        option_type: 'CE' or 'PE'
        strike_price: Strike price (integer)
    
    Returns:
        Dict with instrument details including ExchangeInstrumentID
    """
    url = f"{XTS_BASE_URL}/instruments/instrument/optionSymbol"
    headers = {'Authorization': token}
    
    params = {
        'exchangeSegment': 2,
        'series': 'OPTIDX',
        'symbol': 'NIFTY',
        'expiryDate': expiry_date,
        'optionType': option_type,
        'strikePrice': strike_price
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            data = response.json()
            # Response format: {"type":"success", "code":"s-rds-0", "result": [{instrument_details}]}
            if data.get('type') == 'success' and 'result' in data:
                result = data['result']
                if isinstance(result, list) and len(result) > 0:
                    return result[0]  # Return first instrument
        
        print(f"  GetOptionSymbol failed: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"  Error: {e}")
    
    return None


def get_option_ltp(token, instrument_id):
    """
    Fetch option LTP using numeric instrument ID
    
    Args:
        token: XTS auth token
        instrument_id: Numeric ExchangeInstrumentID
    
    Returns:
        Dict with LTP, bid, ask, volume or None
    """
    url = f"{XTS_BASE_URL}/instruments/quotes"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': token
    }
    
    payload = {
        "instruments": [
            {
                "exchangeSegment": 2,
                "exchangeInstrumentID": instrument_id
            }
        ],
        "xtsMessageCode": 1502,
        "publishFormat": "JSON"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'listQuotes' in data['result']:
                quotes = data['result']['listQuotes']
                if quotes and len(quotes) > 0:
                    quote = quotes[0]
                    # Quote might be a JSON string
                    if isinstance(quote, str):
                        quote = json.loads(quote)
                    
                    if isinstance(quote, dict) and 'Touchline' in quote:
                        touchline = quote['Touchline']
                        return {
                            'ltp': float(touchline.get('LastTradedPrice', 0)),
                            'bid': float(touchline.get('BidPrice', 0)),
                            'ask': float(touchline.get('AskPrice', 0)),
                            'volume': int(touchline.get('TotalTradedQuantity', 0))
                        }
    except Exception as e:
        print(f"  Error fetching LTP: {e}")
    
    return None


def test_nifty_options():
    """Main test function"""
    print("="*70)
    print("NIFTY OPTION PRICE FETCHER - TEST SCRIPT")
    print("="*70 + "\n")
    
    # Step 1: Login
    print("[1/6] Logging in...")
    token = login()
    if not token:
        print("✗ Failed to login")
        return
    
    # Step 2: Get NIFTY spot
    print("[2/6] Fetching NIFTY spot price...")
    spot = get_nifty_spot(token)
    if spot:
        print(f"  ✓ NIFTY Spot: Rs.{spot:,.2f}\n")
    else:
        print("  ✗ Could not fetch spot price\n")
        spot = 25800.0  # Use default
    
    # Step 3: Get expiry dates
    print("[3/6] Fetching expiry dates...")
    expiries = get_expiry_dates(token)
    if not expiries:
        print("  ✗ Could not fetch expiry dates")
        return
    
    # Use weekly expiry (usually second one)
    if len(expiries) > 1:
        selected_expiry = expiries[1]
    else:
        selected_expiry = expiries[0]
    
    expiry_obj = datetime.fromisoformat(selected_expiry.split('T')[0])
    expiry_formatted = expiry_obj.strftime('%d%b%Y')  # "10Feb2026"
    
    print(f"  ✓ Using expiry: {expiry_formatted}")
    print(f"  Available expiries: {len(expiries)}\n")
    
    # Step 4: Calculate ATM strike
    atm_strike = round(spot / 50) * 50  # Round to nearest 50
    print(f"[4/6] ATM Strike: Rs.{atm_strike:,.0f}")
    
    # Test strikes around ATM
    test_strikes = [
        atm_strike - 100,
        atm_strike - 50,
        atm_strike,
        atm_strike + 50,
        atm_strike + 100
    ]
    
    print(f"  Testing strikes: {test_strikes}\n")
    
    # Step 5: Get CALL option details
    print("[5/6] Fetching CALL options using GetOptionSymbol API...")
    print("-" * 70)
    
    call_results = []
    for strike in test_strikes:
        details = get_option_details(token, expiry_formatted, 'CE', strike)
        if details:
            inst_id = details.get('ExchangeInstrumentID')
            display_name = details.get('DisplayName')
            lot_size = details.get('LotSize')
            
            # Get LTP
            quote_data = get_option_ltp(token, inst_id)
            
            if quote_data and quote_data['ltp']:
                ltp = quote_data['ltp']
                bid = quote_data['bid']
                ask = quote_data['ask']
                volume = quote_data['volume']
                
                call_results.append({
                    'strike': strike,
                    'instrument_id': inst_id,
                    'display_name': display_name,
                    'ltp': ltp,
                    'bid': bid,
                    'ask': ask,
                    'volume': volume,
                    'lot_size': lot_size
                })
                
                print(f"Strike {strike}: ✓ ID={inst_id}, LTP=Rs.{ltp:,.2f}, Bid={bid:.2f}, Ask={ask:.2f}, Vol={volume:,}")
            else:
                print(f"Strike {strike}: ✓ ID={inst_id} (No LTP data)")
    
    # Step 6: Get PUT option details
    print(f"\n[6/6] Fetching PUT options using GetOptionSymbol API...")
    print("-" * 70)
    
    put_results = []
    for strike in test_strikes:
        details = get_option_details(token, expiry_formatted, 'PE', strike)
        if details:
            inst_id = details.get('ExchangeInstrumentID')
            display_name = details.get('DisplayName')
            lot_size = details.get('LotSize')
            
            # Get LTP
            quote_data = get_option_ltp(token, inst_id)
            
            if quote_data and quote_data['ltp']:
                ltp = quote_data['ltp']
                bid = quote_data['bid']
                ask = quote_data['ask']
                volume = quote_data['volume']
                
                put_results.append({
                    'strike': strike,
                    'instrument_id': inst_id,
                    'display_name': display_name,
                    'ltp': ltp,
                    'bid': bid,
                    'ask': ask,
                    'volume': volume,
                    'lot_size': lot_size
                })
                
                print(f"Strike {strike}: ✓ ID={inst_id}, LTP=Rs.{ltp:,.2f}, Bid={bid:.2f}, Ask={ask:.2f}, Vol={volume:,}")
            else:
                print(f"Strike {strike}: ✓ ID={inst_id} (No LTP data)")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"NIFTY Spot: Rs.{spot:,.2f}")
    print(f"Expiry: {expiry_formatted}")
    print(f"ATM Strike: Rs.{atm_strike:,.0f}")
    print(f"\nCALL Options fetched: {len(call_results)}")
    print(f"PUT Options fetched: {len(put_results)}")
    
    if call_results:
        print(f"\nATM CALL (Strike {atm_strike}):")
        atm_call = next((r for r in call_results if r['strike'] == atm_strike), None)
        if atm_call:
            print(f"  LTP: Rs.{atm_call['ltp']:,.2f}")
            print(f"  Bid: Rs.{atm_call['bid']:,.2f}")
            print(f"  Ask: Rs.{atm_call['ask']:,.2f}")
            print(f"  Volume: {atm_call['volume']:,}")
            print(f"  Lot Size: {atm_call['lot_size']}")
    
    if put_results:
        print(f"\nATM PUT (Strike {atm_strike}):")
        atm_put = next((r for r in put_results if r['strike'] == atm_strike), None)
        if atm_put:
            print(f"  LTP: Rs.{atm_put['ltp']:,.2f}")
            print(f"  Bid: Rs.{atm_put['bid']:,.2f}")
            print(f"  Ask: Rs.{atm_put['ask']:,.2f}")
            print(f"  Volume: {atm_put['volume']:,}")
            print(f"  Lot Size: {atm_put['lot_size']}")
    
    # Save results
    result = {
        'timestamp': datetime.now().isoformat(),
        'spot_price': spot,
        'expiry': expiry_formatted,
        'atm_strike': atm_strike,
        'calls': call_results,
        'puts': put_results
    }
    
    output_file = "nifty_option_test_result.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n✓ Results saved to {output_file}")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_nifty_options()
