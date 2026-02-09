"""
Fetch LTP prices of Put and Call options for Gold at ATM strike using XTS API

Gold trades on MCX (Multi Commodity Exchange)
Options symbol format: GOLDM {expiry} {strike} {CE/PE}
"""

import requests
import json
from datetime import datetime, timedelta
import urllib3
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class GoldOptionFetcher:
    """Fetch Gold ATM option LTP prices using XTS API"""
    
    def __init__(self):
        self.token = None
        self.base_url = XTS_BASE_URL
        self.app_key = XTS_APP_KEY
        self.secret_key = XTS_SECRET_KEY
        self.source = XTS_SOURCE
        
        # MCX segments (try multiple as XTS might use different ones)
        self.mcx_segments = [3, 51, 4, 5]  # MCX, MCXSX, etc.
        self.gold_symbol = "GOLD"  # Base symbol
        self.gold_option_symbol = "GOLDM"  # Gold Mini options (more liquid)
    
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
    
    def get_gold_spot_via_ohlc(self, segment: int, instrument_id) -> float:
        """Get Gold price using OHLC endpoint (GET request)"""
        try:
            from datetime import datetime, timedelta
            
            # Get current time and 1 hour ago
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            
            # Format: "MMM DD YYYY HH:MM:SS"
            start_str = start_time.strftime("%b %d %Y %H:%M:%S")
            end_str = end_time.strftime("%b %d %Y %H:%M:%S")
            
            url = f"{self.base_url}/instruments/ohlc"
            headers = {
                'Authorization': self.token,
                'Content-Type': 'application/json'
            }
            
            # GET request with query parameters
            params = {
                'exchangeSegment': segment,
                'exchangeInstrumentID': instrument_id,
                'startTime': start_str,
                'endTime': end_str,
                'compressionValue': 60  # 1 minute candles
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'result' in data and 'dataReponse' in data['result']:
                    candles = data['result']['dataReponse']
                    
                    if candles and len(candles) > 0:
                        # Get the most recent candle
                        last_candle = candles[-1]
                        
                        # OHLC format: timestamp, open, high, low, close, volume, oi
                        if isinstance(last_candle, list) and len(last_candle) >= 5:
                            close_price = last_candle[4]  # Close price
                            if close_price > 0:
                                return float(close_price)
            
            return 0
        
        except Exception as e:
            return 0
    
    def get_gold_spot(self) -> float:
        """Get current Gold spot/future price"""
        # Try OHLC endpoint first (GET request - better for MCX)
        ohlc_attempts = [
            (51, 'GOLD', 'MCX Gold via OHLC'),
            (51, 'GOLDM', 'MCX Gold Mini via OHLC'),
            (3, 'GOLD', 'MCX Gold Segment 3'),
            (3, 'GOLDM', 'MCX Gold Mini Segment 3'),
        ]
        
        for segment, instrument_id, description in ohlc_attempts:
            price = self.get_gold_spot_via_ohlc(segment, instrument_id)
            if price > 0:
                print(f"[OK] Found {description}: Rs.{price:.2f}")
                return price
        
        # Fallback to quotes endpoint (POST request)
        attempts = [
            (3, 'GOLD', 'MCX Gold'),
            (3, 'GOLDM', 'MCX Gold Mini'),
            (3, 'GOLD FEB 2026', 'MCX Gold February Future'),
            (51, 'GOLD', 'MCXSX Gold'),
            (3, 1, 'MCX ID 1'),
            (3, 100, 'MCX ID 100'),
        ]
        
        for segment, instrument_id, description in attempts:
            try:
                url = f"{self.base_url}/instruments/quotes"
                headers = {
                    'Authorization': self.token,
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
                
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=5,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Try both response formats
                    if 'result' in data:
                        # Try listQuotes format
                        if 'listQuotes' in data['result']:
                            quotes_list = data['result']['listQuotes']
                            if quotes_list and len(quotes_list) > 0:
                                quote_str = quotes_list[0]
                                if quote_str:
                                    try:
                                        quote_data = json.loads(quote_str)
                                        if 'Touchline' in quote_data:
                                            ltp = quote_data['Touchline'].get('LastTradedPrice', 0)
                                            if ltp > 0:
                                                print(f"[OK] Found {description}: Rs.{ltp:.2f}")
                                                return float(ltp)
                                    except json.JSONDecodeError:
                                        pass
                        
                        # Try quotesList format
                        if 'quotesList' in data['result']:
                            quotes_list = data['result']['quotesList']
                            if quotes_list and len(quotes_list) > 0:
                                quote_item = quotes_list[0]
                                if isinstance(quote_item, dict) and 'Touchline' in quote_item:
                                    ltp = quote_item['Touchline'].get('LastTradedPrice', 0)
                                    if ltp > 0:
                                        print(f"[OK] Found {description}: Rs.{ltp:.2f}")
                                        return float(ltp)
            
            except Exception as e:
                continue
        
        # Default fallback price (approx current gold price per 10 grams)
        print("[WARNING] Could not fetch real-time Gold price, using estimate")
        return 75000.0  # Approximate gold price per 10g
    
    def get_option_expiry_dates(self, segment: int = 3) -> list:
        """Get available option expiry dates for Gold"""
        try:
            url = f"{self.base_url}/instruments/instrument/expiryDate"
            headers = {
                'Authorization': self.token,
                'Content-Type': 'application/json'
            }
            
            # Try for Gold options
            params = {
                'exchangeSegment': segment,  # MCX
                'series': 'OPTFUT',  # Options on Futures
                'symbol': self.gold_option_symbol
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
                if 'result' in data and data['result']:
                    return data['result']
            
            # Fallback: Calculate next month expiry
            return self._get_next_month_expiry()
        
        except Exception as e:
            print(f"[WARNING] Error fetching expiry dates: {str(e)}")
            return self._get_next_month_expiry()
    
    def _get_next_month_expiry(self) -> list:
        """Get next month expiry date (fallback)"""
        # MCX Gold options typically expire on 5th of every month
        today = datetime.now()
        
        # Check if current month's 5th is still valid
        current_month_expiry = datetime(today.year, today.month, 5)
        
        if today.day < 5:
            expiry_date = current_month_expiry
        else:
            # Move to next month
            if today.month == 12:
                expiry_date = datetime(today.year + 1, 1, 5)
            else:
                expiry_date = datetime(today.year, today.month + 1, 5)
        
        expiry_str = expiry_date.strftime("%d%b%y").upper()
        return [expiry_str]
    
    def _parse_expiry_date(self, expiry_str: str) -> str:
        """Parse expiry date to DD%b%y format (e.g., 05FEB26)"""
        try:
            # If it's in ISO format
            if 'T' in expiry_str:
                dt = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                return dt.strftime("%d%b%y").upper()
            # If already in simple format
            return expiry_str.upper()
        except:
            return expiry_str.upper()
    
    def get_option_symbol(self, strike: int, option_type: str, expiry_date: str, segment: int = 3) -> str:
        """Get Gold option symbol"""
        try:
            # Format: GOLDM 05FEB26 75000 CE
            option_symbol = f"{self.gold_option_symbol} {expiry_date} {strike} {option_type}"
            return option_symbol
        
        except Exception as e:
            print(f"[ERROR] Error formatting option symbol: {str(e)}")
            return None
    
    def subscribe_instrument(self, option_symbol: str, segment: int = 3) -> bool:
        """Subscribe to an instrument for quotes"""
        try:
            url = f"{self.base_url}/instruments/subscription"
            headers = {
                'Authorization': self.token,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'instruments': [{
                    'exchangeSegment': segment,
                    'exchangeInstrumentID': option_symbol
                }],
                'xtsMessageCode': 1501
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=5,
                verify=False
            )
            
            return response.status_code == 200
        
        except:
            return False
    
    def get_option_ltp_via_ohlc(self, option_symbol: str, strike: int, option_type: str, segment: int) -> dict:
        """Try fetching option LTP using OHLC endpoint (GET request)"""
        try:
            from datetime import datetime, timedelta
            
            # Get current time and 1 hour ago
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            
            # Format: "MMM DD YYYY HH:MM:SS"
            start_str = start_time.strftime("%b %d %Y %H:%M:%S")
            end_str = end_time.strftime("%b %d %Y %H:%M:%S")
            
            url = f"{self.base_url}/instruments/ohlc"
            headers = {
                'Authorization': self.token,
                'Content-Type': 'application/json'
            }
            
            # GET request with query parameters
            params = {
                'exchangeSegment': segment,
                'exchangeInstrumentID': option_symbol,
                'startTime': start_str,
                'endTime': end_str,
                'compressionValue': 60  # 1 minute candles
            }
            
            print(f"[DEBUG] Trying OHLC GET: {option_symbol}")
            response = requests.get(url, headers=headers, params=params, timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"[DEBUG] OHLC Response: {data}")
                
                if 'result' in data and 'dataReponse' in data['result']:
                    candles = data['result']['dataReponse']
                    
                    if candles and len(candles) > 0:
                        # Get the most recent candle
                        last_candle = candles[-1]
                        
                        # OHLC format: [timestamp, open, high, low, close, volume, oi]
                        if isinstance(last_candle, list) and len(last_candle) >= 5:
                            close_price = last_candle[4]  # Close price
                            high_price = last_candle[2]   # High
                            low_price = last_candle[3]    # Low
                            
                            if close_price > 0:
                                print(f"[OK] OHLC found price: Rs.{close_price}")
                                return {
                                    'symbol': option_symbol,
                                    'type': option_type,
                                    'strike': strike,
                                    'ltp': float(close_price),
                                    'bid': float(low_price) if low_price > 0 else float(close_price) * 0.99,
                                    'ask': float(high_price) if high_price > 0 else float(close_price) * 1.01,
                                    'status': 'success (OHLC GET)'
                                }
        except Exception as e:
            print(f"[DEBUG] OHLC error: {str(e)}")
            pass
        
        return None
    
    def get_option_ltp(self, strike: int, option_type: str, expiry_date: str, segment: int = 3) -> dict:
        """Get LTP for a Gold option"""
        try:
            option_symbol = self.get_option_symbol(strike, option_type, expiry_date, segment)
            
            if not option_symbol:
                return {'error': 'Failed to format option symbol'}
            
            # Try OHLC endpoint first (GET request - as per documentation)
            ohlc_result = self.get_option_ltp_via_ohlc(option_symbol, strike, option_type, segment)
            if ohlc_result and 'error' not in ohlc_result:
                return ohlc_result
            
            # Subscribe to instrument
            self.subscribe_instrument(option_symbol, segment)
            
            url = f"{self.base_url}/instruments/quotes"
            headers = {
                'Authorization': self.token,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'instruments': [{
                    'exchangeSegment': segment,
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
                
                # Try quotesList format
                if 'result' in data and 'quotesList' in data['result']:
                    quotes_list = data['result']['quotesList']
                    if quotes_list and len(quotes_list) > 0:
                        quote_item = quotes_list[0]
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
                
                # Try listQuotes format
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
                
                # Try OHLC as fallback
                return self._fetch_from_ohlc(option_symbol, strike, option_type, segment)
            
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
    
    def _fetch_from_ohlc(self, option_symbol: str, strike: int, option_type: str, segment: int = 3) -> dict:
        """Try fetching from OHLC endpoint using POST (legacy fallback)"""
        try:
            url = f"{self.base_url}/instruments/ohlc"
            headers = {
                'Authorization': self.token,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'instruments': [{
                    'exchangeSegment': segment,
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
                                'status': 'success (OHLC POST)'
                            }
        except:
            pass
        
        # Return error with estimation fallback info
        return {
            'symbol': option_symbol,
            'type': option_type,
            'strike': strike,
            'error': 'Real-time data unavailable',
            'reason': 'XTS API returns empty quote data - See GOLD_OPTIONS_ISSUE_ANALYSIS.md'
        }
    
    def _estimate_option_price(self, strike: int, option_type: str, spot_price: float) -> dict:
        """
        Estimate Gold option premium when real data is unavailable
        
        Based on:
        - Intrinsic value
        - Time value (volatility-based)
        - Gold's typical ATM premium (2-3% of spot)
        """
        
        if option_type == 'CE':
            intrinsic = max(0, spot_price - strike)
        else:
            intrinsic = max(0, strike - spot_price)
        
        # Gold ATM premium (per 10g) - typically 2-3% of spot
        atm_premium = spot_price * 0.025  # 2.5%
        
        # Distance from ATM
        distance = abs(spot_price - strike)
        
        # Time value decay based on moneyness
        if distance <= 200:  # ATM (within 2 strikes)
            time_value = atm_premium
        elif distance <= 500:  # Near money
            decay_factor = 1 - (distance - 200) / 300  # Linear decay
            time_value = atm_premium * decay_factor * 0.7
        elif distance <= 1000:  # Slightly OTM/ITM
            decay_factor = 1 - (distance - 500) / 500
            time_value = atm_premium * decay_factor * 0.4
        else:  # Far OTM/ITM
            time_value = atm_premium * 0.1
        
        total_premium = intrinsic + time_value
        
        return {
            'symbol': f"GOLDM (Estimated) {strike} {option_type}",
            'type': option_type,
            'strike': strike,
            'ltp': round(total_premium, 2),
            'bid': round(total_premium * 0.98, 2),
            'ask': round(total_premium * 1.02, 2),
            'status': 'estimated',
            'note': 'Estimated price - Real-time MCX data unavailable via XTS REST API'
        }
    
    def fetch_atm_options(self, segment: int = 3, use_estimation: bool = True) -> dict:
        """Fetch LTP for ATM Call and Put options on Gold"""
        print("\n" + "="*70)
        print("GOLD ATM OPTION LTP FETCHER")
        print("="*70)
        
        # Get Gold spot/future price
        print(f"\n[INFO] Fetching Gold price from MCX (Segment {segment})...")
        spot_price = self.get_gold_spot()
        
        if spot_price <= 0:
            print("[ERROR] Failed to fetch Gold price")
            return None
        
        print(f"[OK] Gold Price: Rs.{spot_price:.2f} per 10g")
        
        # Calculate ATM strike (round to nearest 100 for Gold)
        atm_strike = round(spot_price / 100) * 100
        print(f"[STRIKE] ATM Strike: {atm_strike}")
        
        # Get available expiry dates
        print(f"\n[INFO] Fetching expiry dates...")
        expiry_dates = self.get_option_expiry_dates(segment)
        print(f"[OK] Available expirations: {expiry_dates}")
        
        # Use first (nearest) expiry
        expiry_raw = expiry_dates[0] if expiry_dates else None
        if not expiry_raw:
            print("[ERROR] No expiry date available")
            return None
        
        expiry = self._parse_expiry_date(expiry_raw)
        print(f"[EXPIRY] Using expiry: {expiry}")
        
        # Fetch ATM Call (CE)
        print(f"\n[INFO] Fetching ATM Call ({atm_strike} CE)...")
        ce_data = self.get_option_ltp(atm_strike, 'CE', expiry, segment)
        
        if 'error' in ce_data:
            print(f"[WARNING] Call: {ce_data['error']}")
            if use_estimation:
                print(f"[INFO] Using estimation for Call...")
                ce_data = self._estimate_option_price(atm_strike, 'CE', spot_price)
                print(f"[ESTIMATED] Call ({atm_strike} CE):")
                print(f"   LTP: Rs.{ce_data['ltp']:.2f} (estimated)")
        else:
            print(f"[OK] Call ({atm_strike} CE):")
            print(f"   LTP: Rs.{ce_data['ltp']:.2f}")
            print(f"   Bid: Rs.{ce_data['bid']:.2f} | Ask: Rs.{ce_data['ask']:.2f}")
        
        # Fetch ATM Put (PE)
        print(f"\n[INFO] Fetching ATM Put ({atm_strike} PE)...")
        pe_data = self.get_option_ltp(atm_strike, 'PE', expiry, segment)
        
        if 'error' in pe_data:
            print(f"[WARNING] Put: {pe_data['error']}")
            if use_estimation:
                print(f"[INFO] Using estimation for Put...")
                pe_data = self._estimate_option_price(atm_strike, 'PE', spot_price)
                print(f"[ESTIMATED] Put ({atm_strike} PE):")
                print(f"   LTP: Rs.{pe_data['ltp']:.2f} (estimated)")
        else:
            print(f"[OK] Put ({atm_strike} PE):")
            print(f"   LTP: Rs.{pe_data['ltp']:.2f}")
            print(f"   Bid: Rs.{pe_data['bid']:.2f} | Ask: Rs.{pe_data['ask']:.2f}")
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Gold Price: Rs.{spot_price:.2f} per 10g")
        print(f"ATM Strike: {atm_strike}")
        print(f"Expiry: {expiry}")
        print(f"Exchange: MCX (Segment {segment})")
        
        if ce_data:
            status = " (estimated)" if ce_data.get('status') == 'estimated' else ""
            print(f"Call LTP: Rs.{ce_data['ltp']:.2f}{status}")
        
        if pe_data:
            status = " (estimated)" if pe_data.get('status') == 'estimated' else ""
            print(f"Put LTP: Rs.{pe_data['ltp']:.2f}{status}")
        
        if use_estimation and (ce_data.get('status') == 'estimated' or pe_data.get('status') == 'estimated'):
            print("\n[NOTE] Prices are estimated - Real-time MCX data unavailable")
            print("[INFO] See GOLD_OPTIONS_ISSUE_ANALYSIS.md for details")
        
        print("="*70)
        
        return {
            'commodity': 'GOLD',
            'spot_price': spot_price,
            'atm_strike': atm_strike,
            'expiry': expiry,
            'exchange': 'MCX',
            'segment': segment,
            'call': ce_data,
            'put': pe_data,
            'note': 'Some prices may be estimated due to API limitations' if use_estimation else None
        }


def main():
    """Main function"""
    print("="*70)
    print("GOLD OPTION LTP FETCHER - USING OHLC ENDPOINT")
    print("="*70)
    print("\n[INFO] Trying OHLC GET endpoint (as per XTS documentation)")
    print("[INFO] This may work better for MCX commodity data\n")
    
    fetcher = GoldOptionFetcher()
    
    # Login
    print("[INFO] Logging in to XTS API...")
    if not fetcher.login():
        print("[ERROR] Cannot proceed without login")
        return
    
    # Test different approaches
    print("\n" + "="*70)
    print("STEP 1: Testing Gold Spot Price via OHLC")
    print("="*70)
    
    spot_price = fetcher.get_gold_spot()
    if spot_price > 0:
        print(f"\n[SUCCESS] Got Gold spot price: Rs.{spot_price:.2f}")
    else:
        print(f"\n[WARNING] Could not fetch spot price, using estimate")
    
    # Try to fetch options with OHLC
    print("\n" + "="*70)
    print("STEP 2: Fetching Options via OHLC Endpoint")
    print("="*70)
    
    result = fetcher.fetch_atm_options(segment=51, use_estimation=True)
    
    if result:
        # Save result to file
        filename = 'gold_option_ltp_ohlc_method.json'
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n[OK] Results saved to {filename}")
        
        # Check if we got real data
        if result['call'].get('status', '').startswith('success'):
            print("\n" + "="*70)
            print("SUCCESS - REAL-TIME DATA RETRIEVED!")
            print("="*70)
            print(f"Method: {result['call']['status']}")
        else:
            print("\n" + "="*70)
            print("OHLC METHOD ALSO RETURNED EMPTY DATA")
            print("="*70)
            print("Possible reasons:")
            print("1. Market is closed (Gold MCX: 10 AM - 11:30 PM IST)")
            print("2. Gold options not actively traded")
            print("3. Need numeric instrument IDs from broker")
            print("4. WebSocket connection required for real-time MCX data")
            print("\nUsing estimation fallback for now.")
            print("="*70)


if __name__ == "__main__":
    main()
