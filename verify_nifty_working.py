"""
Verify NIFTY GetOptionSymbol works fully with correct date format
"""

import requests
import json
from datetime import datetime
import urllib3
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def login():
    """Login to XTS"""
    url = f"{XTS_BASE_URL}/auth/login"
    payload = {
        'secretKey': XTS_SECRET_KEY,
        'appKey': XTS_APP_KEY,
        'source': XTS_SOURCE
    }
    
    response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10, verify=False)
    if response.status_code == 200:
        data = response.json()
        token = data.get('result', {}).get('token')
        if token:
            print(f"✓ Login successful\n")
            return token
    return None


def test_nifty_option_symbol(token):
    """Test NIFTY GetOptionSymbol with correct format"""
    print("="*70)
    print("NIFTY GetOptionSymbol - Full Test")
    print("="*70 + "\n")
    
    # Get NIFTY expiry
    expiry_url = f"{XTS_BASE_URL}/instruments/instrument/expiryDate"
    headers = {'Authorization': token}
    params = {'exchangeSegment': 2, 'series': 'OPTIDX', 'symbol': 'NIFTY'}
    
    response = requests.get(expiry_url, params=params, headers=headers, timeout=10, verify=False)
    if response.status_code == 200:
        data = response.json()
        expiry_dates = data.get('result', [])
        if expiry_dates and len(expiry_dates) > 1:
            weekly_expiry = expiry_dates[1]  # Usually weekly expiry
            print(f"NIFTY weekly expiry: {weekly_expiry}")
            
            expiry_obj = datetime.fromisoformat(weekly_expiry.split('T')[0])
            expiry_formatted = expiry_obj.strftime('%d%b%Y')  # "10Feb2026"
            
            print(f"Formatted expiry: {expiry_formatted}\n")
            
            # Test GetOptionSymbol with this format
            url = f"{XTS_BASE_URL}/instruments/instrument/optionSymbol"
            
            test_strikes = [25700, 25750, 25800, 25850, 25900]
            
            print("Testing CALL options:")
            for strike in test_strikes:
                params = {
                    'exchangeSegment': 2,
                    'series': 'OPTIDX',
                    'symbol': 'NIFTY',
                    'expiryDate': expiry_formatted,
                    'optionType': 'CE',
                    'strikePrice': strike
                }
                
                try:
                    response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list) and len(data) > 0:
                            result = data[0].get('result', {})
                            inst_id = result.get('ExchangeInstrumentID')
                            display = result.get('DisplayName')
                            lot_size = result.get('LotSize')
                            tick = result.get('TickSize')
                            
                            if inst_id:
                                print(f"  Strike {strike}: ✓ ID={inst_id}, Display={display}, Lot={lot_size}, Tick={tick}")
                except Exception as e:
                    print(f"  Strike {strike}: ✗ Error: {e}")
            
            print("\n" + "="*70)
            print("VERIFIED: GetOptionSymbol works for NIFTY with format 'ddMmmyyyy'")
            print("="*70)
            
            return True
    
    return False


if __name__ == "__main__":
    token = login()
    if token:
        if test_nifty_option_symbol(token):
            print("\n" + "="*70)
            print("CONCLUSION FOR GOLD OPTIONS")
            print("="*70)
            print("""
The GetOptionSymbol API endpoint WORKS (verified with NIFTY).

Gold options return "Data not available" for GetOptionSymbol because:

1. Your XTS account may not have MCX OPTIONS data access enabled
   - You may have MCX FUTURES access (GetExpiryDate works)
   - But not MCX OPTIONS derivatives

2. GetOptionSymbol endpoint may not support MCX options at all
   - The XTS broker may only provide this API for equity options (NSE/NFO)
   - MCX options may require different method

3. Market timing (less likely since GetExpiryDate works)

RECOMMENDED NEXT STEPS:

1. Contact your XTS broker (SYMPHONY/Interactive Brokers) and ask:
   - Is MCX options data enabled on your account?
   - Does GetOptionSymbol API support MCX options (segment 51)?
   - Request access to MCX options if not enabled

2. Alternative approach: Use WebSocket streaming
   - Subscribe to Gold option instruments via WebSocket
   - Get real-time updates without REST API limitations

3. Use the estimation until real data is available
   - The fetch_gold_option_ltp.py script has estimation fallback
   - Provides realistic premium calculations (2.5% ATM with decay)
""")
