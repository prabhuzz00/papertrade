"""
Fetch Gold ATM Option Prices using XTS GetOptionSymbol API
Uses the proper GetOptionSymbol endpoint to get numeric instrument IDs
"""

import requests
import json
from datetime import datetime
import urllib3
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class GoldATMOptionFetcher:
    """Fetch Gold ATM option prices using GetOptionSymbol for numeric instrument IDs"""
    
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
                    print(f"✓ Login successful")
                    return True
            
            print(f"✗ Login failed: {response.text}")
            return False
        
        except Exception as e:
            print(f"✗ Login error: {e}")
            return False
    
    def get_gold_future_symbol(self, segment=51):
        """Get Gold future symbol using GetFutureSymbol endpoint"""
        if not self.token:
            self.login()
        
        url = f"{self.base_url}/instruments/instrument/futureSymbol"
        headers = {'Authorization': self.token}
        
        # Try different series for MCX
        series_list = ["FUTCOM", "FUTIDX", "FUTCUR", "FUTSTK"]
        symbols = ["GOLDM", "GOLD"]
        
        for series in series_list:
            for symbol in symbols:
                params = {
                    'exchangeSegment': segment,
                    'series': series,
                    'symbol': symbol
                }
                
                try:
                    response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list) and len(data) > 0:
                            result = data[0].get('result', {})
                            instrument_id = result.get('ExchangeInstrumentID')
                            if instrument_id:
                                print(f"✓ Found Gold future: {symbol} (series={series}, ID={instrument_id})")
                                return {
                                    'symbol': symbol,
                                    'series': series,
                                    'instrument_id': instrument_id
                                }
                except Exception as e:
                    continue
        
        print("✗ Could not find Gold future symbol")
        return None
    
    def get_option_expiry_dates(self, symbol="GOLDM", segment=51):
        """Get available expiry dates for Gold options"""
        if not self.token:
            self.login()
        
        url = f"{self.base_url}/instruments/instrument/expiryDate"
        headers = {'Authorization': self.token}
        
        # Use known working series for MCX
        series = "OPTFUT"
        
        params = {
            'exchangeSegment': segment,
            'series': series,
            'symbol': symbol
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and isinstance(data['result'], list):
                    result = data['result']
                    if result and len(result) > 0:
                        print(f"✓ Found {len(result)} expiry dates (series={series})")
                        return result, series
        except Exception as e:
            print(f"  Error: {e}")
        
        print("✗ Could not fetch expiry dates")
        return None, None
    
    def get_option_instrument_details(self, series, symbol, expiry_date, option_type, strike_price, segment=51):
        """
        Get option instrument details using GetOptionSymbol endpoint.
        Returns full instrument details including numeric ExchangeInstrumentID.
        
        Args:
            series: "OPTFUT" or similar for MCX options
            symbol: "GOLDM" or "GOLD"
            expiry_date: "26Mar2026" format (ddMmmyyyy)
            option_type: "CE" or "PE"
            strike_price: Integer strike price
            segment: 51 for MCXFO
        
        Returns:
            Dict with instrument details or None
        """
        if not self.token:
            self.login()
        
        url = f"{self.base_url}/instruments/instrument/optionSymbol"
        headers = {'Authorization': self.token}
        
        params = {
            'exchangeSegment': segment,
            'series': series,
            'symbol': symbol,
            'expiryDate': expiry_date,
            'optionType': option_type,
            'strikePrice': strike_price
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    result_list = data
                    if len(result_list) > 0 and 'result' in result_list[0]:
                        result = result_list[0]['result']
                        if isinstance(result, list) and len(result) > 0:
                            instrument_data = result[0]
                            instrument_id = instrument_data.get('ExchangeInstrumentID')
                            if instrument_id:
                                return instrument_data
                        elif isinstance(result, dict):
                            instrument_id = result.get('ExchangeInstrumentID')
                            if instrument_id:
                                return result
                
                # Check if error response
                if data and isinstance(data, dict) and data.get('type') == 'error':
                    error_msg = data.get('description', 'Unknown error')
                    print(f"  API Error: {error_msg}")
            else:
                print(f"  HTTP {response.status_code}: {response.text[:100]}")
        except Exception as e:
            print(f"  Error: {e}")
        
        return None
    
    def get_option_ltp(self, instrument_id, segment=51):
        """
        Fetch option LTP using numeric instrument ID via quotes endpoint.
        
        Args:
            instrument_id: Numeric ExchangeInstrumentID from GetOptionSymbol
            segment: Exchange segment
        
        Returns:
            Float LTP value or None
        """
        if not self.token:
            self.login()
        
        url = f"{self.base_url}/instruments/quotes"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.token
        }
        
        payload = {
            "instruments": [
                {
                    "exchangeSegment": segment,
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
                
                # Check listQuotes format
                if 'result' in data and 'listQuotes' in data['result']:
                    quotes = data['result']['listQuotes']
                    if quotes and len(quotes) > 0:
                        quote = quotes[0]
                        if isinstance(quote, dict) and 'Touchline' in quote:
                            ltp = quote['Touchline'].get('LastTradedPrice')
                            if ltp:
                                return float(ltp)
                
                print(f"  Empty quote data: {data}")
        except Exception as e:
            print(f"  Error fetching LTP: {e}")
        
        return None
    
    def estimate_option_price(self, spot_price, strike_price, option_type):
        """
        Estimate option price when real-time data unavailable.
        Uses simple 2.5% ATM premium with distance-based decay.
        """
        distance = abs(strike_price - spot_price)
        atm_premium = spot_price * 0.025  # 2.5% of spot as base ATM premium
        
        # Decay based on distance from ATM
        if distance == 0:
            premium = atm_premium
        else:
            decay_factor = 1 - (distance / spot_price) * 2
            decay_factor = max(decay_factor, 0.1)  # Minimum 10% of ATM premium
            premium = atm_premium * decay_factor
        
        return round(premium, 2)
    
    def fetch_atm_options(self):
        """Main function to fetch Gold ATM option prices"""
        print("\n" + "="*70)
        print("GOLD ATM OPTION FETCHER (Using GetOptionSymbol API)")
        print("="*70 + "\n")
        
        if not self.login():
            return None
        
        # Step 1: Get Gold future details
        print("[1/5] Finding Gold future contract...")
        gold_future = self.get_gold_future_symbol()
        if not gold_future:
            print("  ⚠ Using default: GOLDM")
            gold_symbol = "GOLDM"
            series = "OPTFUT"
        else:
            gold_symbol = gold_future['symbol']
            series = "OPTFUT"  # Options series
        
        # Step 2: Get expiry dates
        print(f"\n[2/5] Getting expiry dates for {gold_symbol}...")
        expiry_dates, expiry_series = self.get_option_expiry_dates(gold_symbol)
        if not expiry_dates:
            print("  ✗ Could not get expiry dates")
            return None
        
        nearest_expiry = expiry_dates[0]
        expiry_obj = datetime.fromisoformat(nearest_expiry.replace('T23:59:59', ''))
        expiry_formatted = expiry_obj.strftime('%d%b%Y')  # "26Mar2026"
        print(f"  Nearest expiry: {expiry_formatted}")
        
        # Step 3: Calculate ATM strike (using estimated spot price)
        spot_price = 75000.0  # Estimated Gold spot (Rs. 75,000)
        atm_strike = round(spot_price / 100) * 100
        print(f"\n[3/5] Gold Spot Price: Rs.{spot_price:,.2f} (estimated)")
        print(f"  ATM Strike: Rs.{atm_strike:,.0f}")
        
        # Step 4: Get option instrument details using GetOptionSymbol
        print(f"\n[4/5] Fetching option instrument IDs from GetOptionSymbol API...")
        
        call_details = self.get_option_instrument_details(
            series=expiry_series,
            symbol=gold_symbol,
            expiry_date=expiry_formatted,
            option_type="CE",
            strike_price=int(atm_strike),
            segment=51
        )
        
        put_details = self.get_option_instrument_details(
            series=expiry_series,
            symbol=gold_symbol,
            expiry_date=expiry_formatted,
            option_type="PE",
            strike_price=int(atm_strike),
            segment=51
        )
        
        if not call_details or not put_details:
            print("  ✗ Could not get option instrument details")
            print("\n" + "="*70)
            print("ISSUE: MCX Options Data Not Available")
            print("="*70)
            print("""
The GetOptionSymbol API endpoint works (verified with NIFTY options),
but returns "Data not available" for Gold/MCX options.

REASONS:
1. Your account doesn't have MCX OPTIONS data access
   (Note: You have MCX FUTURES access since GetExpiryDate works)

2. XTS API may not support MCX options via GetOptionSymbol
   (API may only work for NSE/NFO equity options)

SOLUTIONS:
1. Contact your XTS broker and ask:
   - "Is MCX options data enabled on my account?"
   - "Does GetOptionSymbol API support MCX options?"
   - Request access to MCX options data

2. Try during MCX market hours: 10:00 AM - 11:30 PM IST

3. Use WebSocket streaming for real-time MCX data

4. Use estimation (run with use_estimation=True)

For now, use NIFTY option fetcher which works perfectly:
  python fetch_atm_option_ltp.py
""")
            
            # Provide estimation anyway
            if True:  # Always estimate as fallback
                print("\n" + "="*70)
                print("ESTIMATED VALUES (Fallback)")
                print("="*70)
                
                call_ltp = self.estimate_option_price(spot_price, atm_strike, 'CE')
                put_ltp = self.estimate_option_price(spot_price, atm_strike, 'PE')
                
                print(f"Call Option LTP: Rs.{call_ltp:,.2f} (estimated)")
                print(f"Put Option LTP:  Rs.{put_ltp:,.2f} (estimated)")
                
                result = {
                    'timestamp': datetime.now().isoformat(),
                    'spot_price': spot_price,
                    'atm_strike': atm_strike,
                    'expiry': expiry_formatted,
                    'call': {
                        'symbol': f"{gold_symbol} {expiry_formatted} {int(atm_strike)} CE",
                        'ltp': call_ltp,
                        'estimated': True
                    },
                    'put': {
                        'symbol': f"{gold_symbol} {expiry_formatted} {int(atm_strike)} PE",
                        'ltp': put_ltp,
                        'estimated': True
                    },
                    'note': 'Estimated values - MCX options data not available via API'
                }
                
                output_file = "gold_atm_options_result.json"
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2)
                
                print(f"\n✓ Estimated results saved to {output_file}")
                print("="*70 + "\n")
                
                return result
            
            return None
        
        call_id = call_details.get('ExchangeInstrumentID')
        put_id = put_details.get('ExchangeInstrumentID')
        
        print(f"  ✓ Call Option ID: {call_id}")
        print(f"    Display Name: {call_details.get('DisplayName')}")
        print(f"  ✓ Put Option ID: {put_id}")
        print(f"    Display Name: {put_details.get('DisplayName')}")
        
        # Step 5: Fetch LTPs using numeric instrument IDs
        print(f"\n[5/5] Fetching option prices...")
        
        call_ltp = self.get_option_ltp(call_id, segment=51)
        put_ltp = self.get_option_ltp(put_id, segment=51)
        
        # Results
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        
        call_estimated = False
        put_estimated = False
        
        if call_ltp:
            print(f"Call Option LTP: Rs.{call_ltp:,.2f} ✓ LIVE DATA")
        else:
            call_ltp = self.estimate_option_price(spot_price, atm_strike, 'CE')
            call_estimated = True
            print(f"Call Option LTP: Rs.{call_ltp:,.2f} (estimated - no live data)")
        
        if put_ltp:
            print(f"Put Option LTP:  Rs.{put_ltp:,.2f} ✓ LIVE DATA")
        else:
            put_ltp = self.estimate_option_price(spot_price, atm_strike, 'PE')
            put_estimated = True
            print(f"Put Option LTP:  Rs.{put_ltp:,.2f} (estimated - no live data)")
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'spot_price': spot_price,
            'atm_strike': atm_strike,
            'expiry': expiry_formatted,
            'call': {
                'instrument_id': call_id,
                'display_name': call_details.get('DisplayName'),
                'strike_price': call_details.get('StrikePrice'),
                'ltp': call_ltp,
                'estimated': call_estimated,
                'lot_size': call_details.get('LotSize'),
                'tick_size': call_details.get('TickSize')
            },
            'put': {
                'instrument_id': put_id,
                'display_name': put_details.get('DisplayName'),
                'strike_price': put_details.get('StrikePrice'),
                'ltp': put_ltp,
                'estimated': put_estimated,
                'lot_size': put_details.get('LotSize'),
                'tick_size': put_details.get('TickSize')
            }
        }
        
        # Save to JSON
        output_file = "gold_atm_options_result.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n✓ Results saved to {output_file}")
        print("="*70 + "\n")
        
        return result


if __name__ == "__main__":
    fetcher = GoldATMOptionFetcher()
    result = fetcher.fetch_atm_options()
    
    if result:
        print("Success! Check gold_atm_options_result.json for details.")
    else:
        print("\nFailed to fetch Gold ATM options.")
        print("Please verify:")
        print("1. Market is open (MCX: 10 AM - 11:30 PM IST)")
        print("2. Your account has MCX options data access")
        print("3. XTS API credentials are correct")
