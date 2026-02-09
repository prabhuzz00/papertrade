"""
Test different expiry date formats for GetOptionSymbol
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


def test_option_symbol_date_formats(token):
    """Test GetOptionSymbol with different date formats"""
    print("="*70)
    print("TESTING GetOptionSymbol with Different Date Formats")
    print("="*70)
    
    url = f"{XTS_BASE_URL}/instruments/instrument/optionSymbol"
    headers = {'Authorization': token}
    
    # First get actual expiry from GetExpiryDate
    expiry_url = f"{XTS_BASE_URL}/instruments/instrument/expiryDate"
    params = {'exchangeSegment': 51, 'series': 'OPTFUT', 'symbol': 'GOLDM'}
    response = requests.get(expiry_url, params=params, headers=headers, timeout=10, verify=False)
    
    if response.status_code == 200:
        data = response.json()
        expiry_dates = data.get('result', [])
        if expiry_dates:
            nearest_expiry = expiry_dates[0]  # "2026-03-26T23:59:59"
            print(f"Nearest GOLDM expiry from API: {nearest_expiry}\n")
            
            # Parse and create different formats
            expiry_obj = datetime.fromisoformat(nearest_expiry.replace('T23:59:59', ''))
            
            date_formats = [
                nearest_expiry,                           # "2026-03-26T23:59:59"
                expiry_obj.strftime('%Y-%m-%d'),          # "2026-03-26"
                expiry_obj.strftime('%d%b%Y'),            # "26Mar2026"
                expiry_obj.strftime('%d%b%y'),            # "26Mar26"
                expiry_obj.strftime('%d %b %Y'),          # "26 Mar 2026"
                expiry_obj.strftime('%Y-%m-%dT23:59:59'), # "2026-03-26T23:59:59"
                expiry_obj.strftime('%d%B%Y'),            # "26March2026"
                expiry_obj.strftime('%d%m%Y'),            # "26032026"
                expiry_obj.strftime('%Y%m%d'),            # "20260326"
                expiry_obj.strftime('%d/%m/%Y'),          # "26/03/2026"
            ]
            
            # Test with different strike prices too
            strikes = [74900, 75000, 75100, 75200]
            
            print("Testing combinations:\n")
            
            for strike in strikes:
                print(f"Strike {strike}:")
                for fmt in date_formats[:3]:  # Test first 3 formats
                    params = {
                        'exchangeSegment': 51,
                        'series': 'OPTFUT',
                        'symbol': 'GOLDM',
                        'expiryDate': fmt,
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
                                if inst_id:
                                    print(f"  ✓ Format '{fmt}' -> ID: {inst_id}, Name: {display}")
                                else:
                                    print(f"  ✗ Format '{fmt}' -> Empty result")
                            else:
                                print(f"  ✗ Format '{fmt}' -> No data: {response.text[:100]}")
                        else:
                            print(f"  ✗ Format '{fmt}' -> {response.status_code}: {response.text[:60]}")
                    except Exception as e:
                        print(f"  ✗ Format '{fmt}' -> Error: {e}")
                print()


def test_nifty_comparison(token):
    """Test NIFTY to see working date format"""
    print("\n" + "="*70)
    print("REFERENCE: Testing NIFTY GetOptionSymbol (Known Working)")
    print("="*70 + "\n")
    
    # Get NIFTY expiry
    expiry_url = f"{XTS_BASE_URL}/instruments/instrument/expiryDate"
    headers = {'Authorization': token}
    params = {'exchangeSegment': 2, 'series': 'OPTIDX', 'symbol': 'NIFTY'}
    
    response = requests.get(expiry_url, params=params, headers=headers, timeout=10, verify=False)
    if response.status_code == 200:
        data = response.json()
        expiry_dates = data.get('result', [])
        if expiry_dates:
            # Try weekly expiry (usually second one)
            if len(expiry_dates) > 1:
                weekly_expiry = expiry_dates[1]  # "2026-02-10T14:30:00"
            else:
                weekly_expiry = expiry_dates[0]
            
            print(f"NIFTY expiry from API: {weekly_expiry}\n")
            
            expiry_obj = datetime.fromisoformat(weekly_expiry.split('T')[0])
            
            # Test different formats
            date_formats = [
                weekly_expiry,                            # Full with time
                expiry_obj.strftime('%Y-%m-%d'),          # "2026-02-10"
                expiry_obj.strftime('%d%b%Y'),            # "10Feb2026"
                expiry_obj.strftime('%d%b%y'),            # "10Feb26"
            ]
            
            url = f"{XTS_BASE_URL}/instruments/instrument/optionSymbol"
            
            for fmt in date_formats:
                params = {
                    'exchangeSegment': 2,
                    'series': 'OPTIDX',
                    'symbol': 'NIFTY',
                    'expiryDate': fmt,
                    'optionType': 'CE',
                    'strikePrice': 25800
                }
                
                try:
                    response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list) and len(data) > 0:
                            result = data[0].get('result', {})
                            inst_id = result.get('ExchangeInstrumentID')
                            display = result.get('DisplayName')
                            if inst_id:
                                print(f"✓ Format '{fmt}' WORKS -> ID: {inst_id}, Name: {display}")
                            else:
                                print(f"✗ Format '{fmt}' -> Empty result")
                        else:
                            print(f"✗ Format '{fmt}' -> {response.text[:100]}")
                    else:
                        print(f"✗ Format '{fmt}' -> {response.status_code}: {response.text[:80]}")
                except Exception as e:
                    print(f"✗ Format '{fmt}' -> Error: {e}")


if __name__ == "__main__":
    token = login()
    if token:
        test_nifty_comparison(token)
        test_option_symbol_date_formats(token)
        print("\n" + "="*70)
        print("TEST COMPLETE")
        print("="*70)
