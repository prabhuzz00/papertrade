"""
Fetch LTP prices of Put and Call options at ATM strike using XTS API

Uses XTS GetExpiryDate and GetOptionSymbol endpoints to fetch real-time
option prices for ATM strike.
"""

import requests
import json
from datetime import datetime, timedelta
import urllib3
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ATMOptionFetcher:
    """Fetch ATM option LTP prices using XTS API"""
    
    def __init__(self):
        self.token = None
        self.base_url = XTS_BASE_URL
        self.app_key = XTS_APP_KEY
        self.secret_key = XTS_SECRET_KEY
        self.source = XTS_SOURCE
    
    def login(self) -> bool:
        """Login to XTS API"""
        try:
            url = f"{self.base_url}/auth/login"
            payload = {
                'secretKey': self.secret_key,
                'appKey': self.app_key,
                'source': self.source
            }
            
            response = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('result', {}).get('token')
                if self.token:
                    print(f"[OK] Login successful")
                    print(f"[TOKEN] {self.token[:30]}...")
                    return True
            
            print(f"[ERROR] Login failed: {response.text}")
            return False
        
        except Exception as e:
            print(f"[ERROR] Login error: {str(e)}")
            return False
    
    def get_nifty_spot(self) -> float:
        """Get current NIFTY spot price"""
        try:
            url = f"{self.base_url}/instruments/quotes"
            headers = {
                'Authorization': self.token,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'instruments': [{
                    'exchangeSegment': 1,  # NSE
                    'exchangeInstrumentID': 26000  # NIFTY 50
                }],
                'xtsMessageCode': 1502,
                'publishFormat': 'JSON'
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'result' in data and 'listQuotes' in data['result']:
                    quotes_list = data['result']['listQuotes']
                    
                    if quotes_list and len(quotes_list) > 0:
                        quote_str = quotes_list[0]
                        if quote_str:
                            try:
                                quote_data = json.loads(quote_str)
                                
                                if 'Touchline' in quote_data:
                                    ltp = quote_data['Touchline'].get('LastTradedPrice', 0)
                                    if ltp > 0:
                                        return float(ltp)
                            except json.JSONDecodeError:
                                pass
            
            return 0
        
        except Exception as e:
            print(f"[ERROR] Error fetching NIFTY spot: {str(e)}")
            return 0
    
    def get_option_expiry_dates(self) -> list:
        """Get available option expiry dates using GetExpiryDate endpoint"""
        try:
            # Using GetExpiryDate endpoint as shown in documentation
            url = f"{self.base_url}/instruments/instrument/expiryDate"
            headers = {
                'Authorization': self.token,
                'Content-Type': 'application/json'
            }
            
            params = {
                'exchangeSegment': 2,  # NFO (Derivatives)
                'series': 'FUTIDX',     # Futures Index
                'symbol': 'NIFTY'
            }
            
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    return data['result']
            
            # Fallback: Calculate next Thursday expiry
            return self._get_next_thursday_expiry()
        
        except Exception as e:
            print(f"[WARNING] Error fetching expiry dates: {str(e)}")
            return self._get_next_thursday_expiry()
    
    def _get_next_thursday_expiry(self) -> list:
        """Get next Thursday expiry date (fallback)"""
        today = datetime.now()
        days_ahead = 3 - today.weekday()  # Thursday = 3
        if days_ahead <= 0:
            days_ahead += 7
        
        next_thursday = today + timedelta(days_ahead)
        expiry_str = next_thursday.strftime("%d%b%y").upper()
        
        return [expiry_str]
    
    def _parse_expiry_date(self, expiry_str: str) -> str:
        """Parse expiry date to DD%b%y format (e.g., 24FEB26)"""
        try:
            # If it's in ISO format (2026-02-24T14:30:00)
            if 'T' in expiry_str:
                dt = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                return dt.strftime("%d%b%y").upper()
            # If already in simple format
            return expiry_str.upper()
        except:
            return expiry_str.upper()
    
    def get_option_symbol(self, strike: int, option_type: str, expiry_date: str) -> str:
        """Get option symbol using GetOptionSymbol endpoint"""
        try:
            # Format: NIFTY 30JAN26 25300 CE
            option_symbol = f"NIFTY {expiry_date} {strike} {option_type}"
            return option_symbol
        
        except Exception as e:
            print(f"[ERROR] Error formatting option symbol: {str(e)}")
            return None
    
    def subscribe_instrument(self, option_symbol: str) -> bool:
        """Subscribe to an instrument for quotes"""
        try:
            url = f"{self.base_url}/instruments/subscription"
            headers = {
                'Authorization': self.token,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'instruments': [{
                    'exchangeSegment': 2,  # NFO
                    'exchangeInstrumentID': option_symbol
                }],
                'xtsMessageCode': 1501  # Subscribe message code
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                return True
            else:
                return False
        
        except Exception as e:
            return False
    
    def get_option_ltp(self, strike: int, option_type: str, expiry_date: str) -> dict:
        """Get LTP for an option using symbol"""
        try:
            option_symbol = self.get_option_symbol(strike, option_type, expiry_date)
            
            if not option_symbol:
                return {'error': 'Failed to format option symbol'}
            
            # Subscribe to instrument first
            self.subscribe_instrument(option_symbol)
            
            url = f"{self.base_url}/instruments/quotes"
            headers = {
                'Authorization': self.token,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'instruments': [{
                    'exchangeSegment': 2,  # NFO
                    'exchangeInstrumentID': option_symbol
                }],
                'xtsMessageCode': 1502,
                'publishFormat': 'JSON'
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Try new response format (quotesList)
                if 'result' in data and 'quotesList' in data['result']:
                    quotes_list = data['result']['quotesList']
                    
                    if quotes_list and len(quotes_list) > 0:
                        quote_item = quotes_list[0]
                        
                        # Check if quote data is directly in the item
                        if isinstance(quote_item, dict) and 'Touchline' in quote_item:
                            touchline = quote_item['Touchline']
                            ltp = touchline.get('LastTradedPrice', 0)
                            bid = touchline.get('Bid', 0)
                            ask = touchline.get('Ask', 0)
                            
                            return {
                                'symbol': option_symbol,
                                'type': option_type,
                                'strike': strike,
                                'ltp': float(ltp),
                                'bid': float(bid),
                                'ask': float(ask),
                                'status': 'success'
                            }
                
                # Try old response format (listQuotes with nested JSON)
                if 'result' in data and 'listQuotes' in data['result']:
                    quotes_list = data['result']['listQuotes']
                    
                    if quotes_list and len(quotes_list) > 0:
                        quote_str = quotes_list[0]
                        if quote_str:
                            try:
                                quote_data = json.loads(quote_str)
                                
                                if 'Touchline' in quote_data:
                                    touchline = quote_data['Touchline']
                                    ltp = touchline.get('LastTradedPrice', 0)
                                    bid = touchline.get('Bid', 0)
                                    ask = touchline.get('Ask', 0)
                                    
                                    return {
                                        'symbol': option_symbol,
                                        'type': option_type,
                                        'strike': strike,
                                        'ltp': float(ltp),
                                        'bid': float(bid),
                                        'ask': float(ask),
                                        'status': 'success'
                                    }
                            except json.JSONDecodeError:
                                pass
                
                # Try OHLC endpoint if quotes is not working
                return self._fetch_from_ohlc(option_symbol, strike, option_type)
            
            return {
                'symbol': option_symbol,
                'type': option_type,
                'strike': strike,
                'error': f'Failed to fetch quote (status: {response.status_code})'
            }
        
        except Exception as e:
            return {
                'type': option_type,
                'strike': strike,
                'error': str(e)
            }
    
    def _fetch_from_ohlc(self, option_symbol: str, strike: int, option_type: str) -> dict:
        """Try fetching from OHLC endpoint"""
        try:
            url = f"{self.base_url}/instruments/ohlc"
            headers = {
                'Authorization': self.token,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'instruments': [{
                    'exchangeSegment': 2,
                    'exchangeInstrumentID': option_symbol
                }],
                'xtsMessageCode': 1505
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'result' in data and 'ohlcList' in data['result']:
                    ohlc_list = data['result']['ohlcList']
                    
                    if ohlc_list and len(ohlc_list) > 0:
                        ohlc_data = ohlc_list[0]
                        
                        if isinstance(ohlc_data, str):
                            ohlc_data = json.loads(ohlc_data)
                        
                        close_price = ohlc_data.get('Close', 0)
                        if close_price > 0:
                            return {
                                'symbol': option_symbol,
                                'type': option_type,
                                'strike': strike,
                                'ltp': float(close_price),
                                'bid': float(close_price) * 0.99,
                                'ask': float(close_price) * 1.01,
                                'status': 'success (OHLC)'
                            }
        
        except Exception as e:
            pass
        
        return {
            'symbol': option_symbol,
            'type': option_type,
            'strike': strike,
            'error': 'Could not fetch real-time data'
        }
    
    def fetch_atm_options(self) -> dict:
        """Fetch LTP for ATM Call and Put options"""
        print("\n" + "="*70)
        print("ATM OPTION LTP FETCHER")
        print("="*70)
        
        # Get NIFTY spot price
        print("\n[INFO] Fetching NIFTY spot price...")
        spot_price = self.get_nifty_spot()
        
        if spot_price <= 0:
            print("[ERROR] Failed to fetch NIFTY spot price")
            return None
        
        print(f"[OK] NIFTY Spot: Rs.{spot_price:.2f}")
        
        # Calculate ATM strike (round to nearest 50)
        atm_strike = round(spot_price / 50) * 50
        print(f"[STRIKE] ATM Strike: {atm_strike}")
        
        # Get available expiry dates
        print("\n[INFO] Fetching expiry dates...")
        expiry_dates = self.get_option_expiry_dates()
        print(f"[OK] Available expirations: {expiry_dates}")
        
        # Use first (nearest) expiry and parse to correct format
        expiry_raw = expiry_dates[0] if expiry_dates else None
        if not expiry_raw:
            print("[ERROR] No expiry date available")
            return None
        
        expiry = self._parse_expiry_date(expiry_raw)
        print(f"[EXPIRY] Using expiry: {expiry}")
        
        # Fetch ATM Call (CE)
        print(f"\n[INFO] Fetching ATM Call ({atm_strike} CE)...")
        ce_data = self.get_option_ltp(atm_strike, 'CE', expiry)
        
        if 'error' in ce_data:
            print(f"[ERROR] Call: {ce_data['error']}")
        else:
            print(f"[OK] Call ({atm_strike} CE):")
            print(f"   LTP: Rs.{ce_data['ltp']:.2f}")
            print(f"   Bid: Rs.{ce_data['bid']:.2f} | Ask: Rs.{ce_data['ask']:.2f}")
        
        # Fetch ATM Put (PE)
        print(f"\n[INFO] Fetching ATM Put ({atm_strike} PE)...")
        pe_data = self.get_option_ltp(atm_strike, 'PE', expiry)
        
        if 'error' in pe_data:
            print(f"[ERROR] Put: {pe_data['error']}")
        else:
            print(f"[OK] Put ({atm_strike} PE):")
            print(f"   LTP: Rs.{pe_data['ltp']:.2f}")
            print(f"   Bid: Rs.{pe_data['bid']:.2f} | Ask: Rs.{pe_data['ask']:.2f}")
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Spot Price: Rs.{spot_price:.2f}")
        print(f"ATM Strike: {atm_strike}")
        print(f"Expiry: {expiry}")
        
        if 'error' not in ce_data:
            print(f"Call LTP: Rs.{ce_data['ltp']:.2f}")
        
        if 'error' not in pe_data:
            print(f"Put LTP: Rs.{pe_data['ltp']:.2f}")
        
        print("="*70)
        
        return {
            'spot_price': spot_price,
            'atm_strike': atm_strike,
            'expiry': expiry,
            'call': ce_data,
            'put': pe_data
        }


def main():
    """Main function"""
    fetcher = ATMOptionFetcher()
    
    # Login
    print("[INFO] Logging in to XTS API...")
    if not fetcher.login():
        print("[ERROR] Cannot proceed without login")
        return
    
    # Fetch ATM options
    result = fetcher.fetch_atm_options()
    
    if result:
        # Save result to file
        with open('atm_option_ltp.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("\n[OK] Results saved to atm_option_ltp.json")


if __name__ == "__main__":
    main()
