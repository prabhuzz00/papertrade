"""
Debug XTS API endpoints to see exact responses for Gold instruments
"""

import requests
import json
import urllib3
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class XTSDebugger:
    def __init__(self):
        self.token = None
        self.base_url = XTS_BASE_URL
        self.app_key = XTS_APP_KEY
        self.secret_key = XTS_SECRET_KEY
        self.source = XTS_SOURCE
    
    def login(self):
        """Login to XTS API"""
        try:
            url = f"{self.base_url}/auth/login"
            payload = {
                'secretKey': self.secret_key,
                'appKey': self.app_key,
                'source': self.source
            }
            
            response = requests.post(
                url, json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10, verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('result', {}).get('token')
                if self.token:
                    print(f"✓ Login successful\n")
                    return True
            
            print(f"✗ Login failed: {response.text}")
            return False
        
        except Exception as e:
            print(f"✗ Login error: {e}")
            return False
    
    def test_get_future_symbol(self):
        """Test GetFutureSymbol endpoint with different parameters"""
        print("="*70)
        print("TEST: GetFutureSymbol Endpoint")
        print("="*70)
        
        url = f"{self.base_url}/instruments/instrument/futureSymbol"
        headers = {'Authorization': self.token}
        
        # Test combinations
        test_cases = [
            {'exchangeSegment': 3, 'series': 'FUTCOM', 'symbol': 'GOLD'},
            {'exchangeSegment': 3, 'series': 'FUTCOM', 'symbol': 'GOLDM'},
            {'exchangeSegment': 51, 'series': 'FUTCOM', 'symbol': 'GOLD'},
            {'exchangeSegment': 51, 'series': 'FUTCOM', 'symbol': 'GOLDM'},
            {'exchangeSegment': 51, 'series': 'FUTCUR', 'symbol': 'GOLD'},
            {'exchangeSegment': 51, 'series': 'FUTIDX', 'symbol': 'GOLDM'},
        ]
        
        for i, params in enumerate(test_cases, 1):
            try:
                response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
                print(f"\n{i}. Params: {params}")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
            except Exception as e:
                print(f"\n{i}. Params: {params}")
                print(f"   Error: {e}")
    
    def test_get_expiry_date(self):
        """Test GetExpiryDate endpoint with different parameters"""
        print("\n" + "="*70)
        print("TEST: GetExpiryDate Endpoint")
        print("="*70)
        
        url = f"{self.base_url}/instruments/instrument/expiryDate"
        headers = {'Authorization': self.token}
        
        # Test combinations
        test_cases = [
            {'exchangeSegment': 3, 'series': 'OPTFUT', 'symbol': 'GOLD'},
            {'exchangeSegment': 3, 'series': 'OPTFUT', 'symbol': 'GOLDM'},
            {'exchangeSegment': 51, 'series': 'OPTFUT', 'symbol': 'GOLD'},
            {'exchangeSegment': 51, 'series': 'OPTFUT', 'symbol': 'GOLDM'},
            {'exchangeSegment': 51, 'series': 'OPTCOM', 'symbol': 'GOLDM'},
            {'exchangeSegment': 51, 'series': 'OPTIDC', 'symbol': 'GOLD'},
        ]
        
        for i, params in enumerate(test_cases, 1):
            try:
                response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
                print(f"\n{i}. Params: {params}")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
            except Exception as e:
                print(f"\n{i}. Params: {params}")
                print(f"   Error: {e}")
    
    def test_get_option_symbol(self):
        """Test GetOptionSymbol endpoint"""
        print("\n" + "="*70)
        print("TEST: GetOptionSymbol Endpoint")
        print("="*70)
        
        url = f"{self.base_url}/instruments/instrument/optionSymbol"
        headers = {'Authorization': self.token}
        
        # Test combinations
        test_cases = [
            {
                'exchangeSegment': 51,
                'series': 'OPTFUT',
                'symbol': 'GOLDM',
                'expiryDate': '26Mar2026',
                'optionType': 'CE',
                'strikePrice': 75000
            },
            {
                'exchangeSegment': 3,
                'series': 'OPTFUT',
                'symbol': 'GOLD',
                'expiryDate': '5Feb2026',
                'optionType': 'CE',
                'strikePrice': 75000
            },
            {
                'exchangeSegment': 51,
                'series': 'OPTCOM',
                'symbol': 'GOLDM',
                'expiryDate': '26Feb2026',
                'optionType': 'CE',
                'strikePrice': 75000
            },
        ]
        
        for i, params in enumerate(test_cases, 1):
            try:
                response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
                print(f"\n{i}. Params: {params}")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text[:300]}")
            except Exception as e:
                print(f"\n{i}. Params: {params}")
                print(f"   Error: {e}")
    
    def test_nse_for_comparison(self):
        """Test with NSE instruments that we know work"""
        print("\n" + "="*70)
        print("TEST: NSE Instruments (Known Working)")
        print("="*70)
        
        # Test GetExpiryDate for NIFTY options
        url = f"{self.base_url}/instruments/instrument/expiryDate"
        headers = {'Authorization': self.token}
        
        params = {
            'exchangeSegment': 2,  # NFO
            'series': 'OPTIDX',
            'symbol': 'NIFTY'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
            print(f"\nNIFTY GetExpiryDate:")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:300]}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Test GetOptionSymbol for NIFTY
        url = f"{self.base_url}/instruments/instrument/optionSymbol"
        
        params = {
            'exchangeSegment': 2,
            'series': 'OPTIDX',
            'symbol': 'NIFTY',
            'expiryDate': '13Feb2026',
            'optionType': 'CE',
            'strikePrice': 25800
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
            print(f"\nNIFTY GetOptionSymbol:")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:500]}")
        except Exception as e:
            print(f"  Error: {e}")
    
    def run_all_tests(self):
        """Run all debug tests"""
        print("\n" + "="*70)
        print("XTS API ENDPOINT DEBUGGER - GOLD INSTRUMENTS")
        print("="*70 + "\n")
        
        if not self.login():
            return
        
        self.test_nse_for_comparison()
        self.test_get_future_symbol()
        self.test_get_expiry_date()
        self.test_get_option_symbol()
        
        print("\n" + "="*70)
        print("DEBUG COMPLETE")
        print("="*70)


if __name__ == "__main__":
    debugger = XTSDebugger()
    debugger.run_all_tests()
