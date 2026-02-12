"""
Fetch Crude Oil ATM Option Prices using XTS API
Uses instrument master download to get numeric instrument IDs,
then fetches real-time quotes via the quotes endpoint.

KEY NOTES:
- Crude Oil options trade on MCX (segment 51 = MCXFO)
- Symbol: CRUDEOIL (big contract) or CRUDEOILM (mini)
- CRUDEOIL lot size = 100 barrels, CRUDEOILM lot size = 10 barrels
- Strikes are typically in 50-point increments
- Price is in INR per barrel (e.g., ~₹5,500-7,500)
- Series: OPTFUT for options, FUTCOM for futures
- opt_type_code in master: 3=CE, 4=PE
"""

import requests
import json
from datetime import datetime
import urllib3
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CrudeOilATMOptionFetcher:
    """Fetch Crude Oil ATM option prices using instrument master for numeric IDs"""
    
    TOKEN_REFRESH_INTERVAL = 180  # 3 minutes
    
    def __init__(self):
        self.token = None
        self.base_url = XTS_BASE_URL
        self.app_key = XTS_APP_KEY
        self.secret_key = XTS_SECRET_KEY
        self.source = XTS_SOURCE
        self.instrument_cache = {}  # {(strike, 'CE'/'PE'): instrument_info}
        self._login_time = None
        self.expiry = None
        self.spot_price = 0
        self.future_id = None
    
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
                    self._login_time = datetime.now()
                    print(f"✓ Crude Oil API Login successful")
                    return True
            
            print(f"✗ Crude Oil API Login failed: {response.text}")
            return False
        
        except Exception as e:
            print(f"✗ Login error: {e}")
            return False
    
    def _ensure_token(self):
        """Ensure token is fresh - re-login if older than TOKEN_REFRESH_INTERVAL seconds"""
        if not self.token or not self._login_time:
            return self.login()
        
        elapsed = (datetime.now() - self._login_time).total_seconds()
        if elapsed > self.TOKEN_REFRESH_INTERVAL:
            return self.login()
        return True
    
    def download_mcxfo_master(self):
        """
        Download MCXFO instrument master via POST endpoint.
        Returns list of pipe-delimited instrument record strings, or None
        """
        if not self.token:
            self.login()
        
        url = f"{self.base_url}/instruments/master"
        headers = {
            'Authorization': self.token,
            'Content-Type': 'application/json'
        }
        
        payload = {'exchangeSegmentList': ['MCXFO']}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30, verify=False)
            if response.status_code == 200:
                data = response.json()
                master_text = data.get('result', '')
                lines = [l for l in master_text.split('\n') if l.strip()]
                print(f"✓ Downloaded MCXFO master: {len(lines)} instruments")
                return lines
            else:
                print(f"✗ Master download failed: {response.status_code} - {response.text[:200]}")
                return None
        except Exception as e:
            print(f"✗ Master download error: {e}")
            return None
    
    def parse_crude_options(self, master_lines, symbol="CRUDEOIL", expiry_filter=None):
        """
        Parse Crude Oil option instruments from master data.
        
        Master record format (pipe-delimited):
        Index 0:  Segment (e.g., MCXFO)
        Index 1:  ExchangeInstrumentID (numeric)
        Index 3:  Symbol (e.g., CRUDEOIL)
        Index 5:  Series (e.g., OPTFUT)
        Index 13: Lot size
        Index 16: Expiry date (ISO format)
        Index 17: Strike price
        Index 18: Option type code (3=CE, 4=PE)
        Index 19: Display name
        
        Returns:
            Dict mapping (strike, option_type) -> instrument info
        """
        options = {}
        
        for line in master_lines:
            if symbol not in line or 'OPTFUT' not in line:
                continue
            
            parts = line.split('|')
            if len(parts) < 20:
                continue
            
            try:
                inst_id = int(parts[1])
                sym = parts[3]
                series = parts[5]
                expiry = parts[16]
                strike = int(parts[17])
                opt_type_code = parts[18]
                display_name = parts[19]
                lot_size = int(parts[13]) if parts[13].isdigit() else 100
                
                if sym != symbol or series != 'OPTFUT':
                    continue
                
                # Filter by expiry if specified
                if expiry_filter and expiry_filter not in expiry:
                    continue
                
                opt_type = 'CE' if opt_type_code == '3' else 'PE' if opt_type_code == '4' else None
                if not opt_type:
                    continue
                
                options[(strike, opt_type)] = {
                    'instrument_id': inst_id,
                    'display_name': display_name,
                    'strike': strike,
                    'option_type': opt_type,
                    'expiry': expiry,
                    'lot_size': lot_size,
                    'symbol': sym
                }
                
            except (ValueError, IndexError):
                continue
        
        return options
    
    def parse_crude_futures(self, master_lines, symbol="CRUDEOIL"):
        """
        Parse Crude Oil future instruments from master data.
        Used to find the nearest future contract for spot price reference.
        
        Returns:
            List of future instrument dicts sorted by expiry (nearest first)
        """
        futures = []
        
        for line in master_lines:
            if symbol not in line or 'FUTCOM' not in line:
                continue
            
            parts = line.split('|')
            if len(parts) < 17:
                continue
            
            try:
                inst_id = int(parts[1])
                sym = parts[3]
                series = parts[5]
                name = parts[4]
                expiry = parts[16] if len(parts) > 16 else ''
                
                if sym != symbol or series != 'FUTCOM':
                    continue
                
                futures.append({
                    'instrument_id': inst_id,
                    'name': name,
                    'expiry': expiry,
                    'symbol': sym
                })
            except (ValueError, IndexError):
                continue
        
        # Sort by expiry (nearest first)
        futures.sort(key=lambda x: x.get('expiry', ''))
        return futures
    
    def get_quote(self, instrument_id, segment=51, _retried=False):
        """
        Fetch real-time quote for an instrument using quotes endpoint.
        Auto-retries on auth failure with fresh token.
        
        Args:
            instrument_id: Numeric ExchangeInstrumentID from master
            segment: Exchange segment (51=MCXFO)
            _retried: Internal flag to prevent infinite retry loops
            
        Returns:
            Dict with ltp, close, open, high, low, volume, bid, ask or None
        """
        self._ensure_token()
        
        if not self.token:
            return None
        
        url = f"{self.base_url}/instruments/quotes"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.token
        }
        
        payload = {
            "instruments": [{
                "exchangeSegment": segment,
                "exchangeInstrumentID": instrument_id
            }],
            "xtsMessageCode": 1502,
            "publishFormat": "JSON"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
            
            # Auth failure: retry with fresh token
            if response.status_code in (401, 403) and not _retried:
                self.login()
                return self.get_quote(instrument_id, segment, _retried=True)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for API-level auth errors in body
                if data.get('type') == 'error' and not _retried:
                    self.login()
                    return self.get_quote(instrument_id, segment, _retried=True)
                
                if 'result' in data and 'listQuotes' in data['result']:
                    quotes = data['result']['listQuotes']
                    if quotes and len(quotes) > 0:
                        quote = quotes[0]
                        if isinstance(quote, str):
                            quote = json.loads(quote)
                        
                        touchline = quote.get('Touchline', {})
                        bid_info = touchline.get('BidInfo', {})
                        ask_info = touchline.get('AskInfo', {})
                        
                        ltp = touchline.get('LastTradedPrice', 0)
                        close = touchline.get('Close', 0)
                        
                        # If both LTP and close are 0, retry once
                        if ltp == 0 and close == 0 and not _retried:
                            self.login()
                            return self.get_quote(instrument_id, segment, _retried=True)
                        
                        return {
                            'ltp': ltp,
                            'close': close,
                            'open': touchline.get('Open', 0),
                            'high': touchline.get('High', 0),
                            'low': touchline.get('Low', 0),
                            'volume': touchline.get('TotalTradedQuantity', 0),
                            'bid': bid_info.get('Price', 0) if isinstance(bid_info, dict) else 0,
                            'ask': ask_info.get('Price', 0) if isinstance(ask_info, dict) else 0,
                        }
            
            # Non-200 status: retry once
            if not _retried:
                self.login()
                return self.get_quote(instrument_id, segment, _retried=True)
            
            return None
        except Exception as e:
            if not _retried:
                self.login()
                return self.get_quote(instrument_id, segment, _retried=True)
            return None
    
    def get_crude_spot_price(self, master_lines, symbol="CRUDEOIL"):
        """
        Get Crude Oil spot/future price from nearest future contract.
        
        Returns:
            Float price or None
        """
        futures = self.parse_crude_futures(master_lines, symbol)
        
        if not futures:
            print("  ✗ No Crude Oil futures found in master data")
            return None
        
        # Try nearest futures first (up to 3)
        for future in futures[:3]:
            quote = self.get_quote(future['instrument_id'])
            if quote:
                ltp = quote['ltp']
                close = quote['close']
                price = ltp if ltp > 0 else close
                if price > 0:
                    print(f"  ✓ {future['name']}: LTP=₹{ltp:,.1f}, Close=₹{close:,.1f}")
                    return price
        
        print("  ✗ Could not get Crude Oil spot price (market may be closed)")
        return None
    
    def get_nearest_expiry(self, options):
        """
        Get nearest expiry date from parsed options data.
        
        Returns:
            Nearest expiry string or None
        """
        expiries = set()
        for key, opt in options.items():
            expiries.add(opt['expiry'])
        
        expiries = sorted(expiries)
        return expiries[0] if expiries else None
    
    def estimate_option_price(self, spot_price, strike_price, option_type):
        """
        Estimate option premium when no live data available.
        Uses simple 3% ATM premium with distance-based decay.
        
        Returns:
            Estimated premium (float)
        """
        distance = abs(strike_price - spot_price)
        atm_premium = spot_price * 0.03  # ~3% of spot as ATM estimate
        
        if distance < 100:
            return round(atm_premium, 1)
        
        decay = max(0.1, 1 - (distance / spot_price) * 3)
        return round(atm_premium * decay, 1)
    
    def initialize(self, symbol="CRUDEOIL"):
        """
        Initialize the fetcher: login, download master, parse futures & options.
        Call this once at startup. After this, instrument_cache, expiry,
        spot_price, and future_id are ready.
        
        Args:
            symbol: "CRUDEOIL" (lot=100) or "CRUDEOILM" (lot=10)
            
        Returns:
            True if initialized successfully
        """
        print(f"\n[CRUDE OIL] Initializing {symbol} option fetcher...")
        
        # Step 1: Login
        if not self.login():
            return False
        
        # Step 2: Download instrument master
        master_lines = self.download_mcxfo_master()
        if not master_lines:
            return False
        self._master_lines = master_lines
        
        # Step 3: Get nearest future for spot price
        futures = self.parse_crude_futures(master_lines, symbol)
        if futures:
            self.future_id = futures[0]['instrument_id']
            quote = self.get_quote(self.future_id)
            if quote:
                spot = quote['ltp'] if quote['ltp'] > 0 else quote['close']
                if spot > 0:
                    self.spot_price = spot
                    print(f"  ✓ {symbol} Spot: ₹{self.spot_price:,.1f}")
        
        # Step 4: Parse all options
        all_options = self.parse_crude_options(master_lines, symbol)
        nearest_expiry = self.get_nearest_expiry(all_options)
        
        if nearest_expiry:
            self.expiry = nearest_expiry.split('T')[0]
            self.instrument_cache = self.parse_crude_options(
                master_lines, symbol, expiry_filter=self.expiry
            )
            print(f"  ✓ {symbol} options loaded: {len(self.instrument_cache)} contracts, expiry={self.expiry}")
        else:
            print(f"  ✗ No {symbol} options found")
            return False
        
        # List available strikes
        strikes = sorted(set(k[0] for k in self.instrument_cache.keys()))
        if strikes:
            print(f"  Available strikes: {strikes[:5]}...{strikes[-5:]} ({len(strikes)} total)")
        
        return len(self.instrument_cache) > 0
    
    def get_option_data(self, signal_type, spot_price, atr=100):
        """
        Get Crude Oil option data for trading.
        
        Args:
            signal_type: 'CALL' or 'PUT'
            spot_price: MCX Crude Oil spot price (INR per barrel)
            atr: Average True Range
        
        Returns:
            dict with strike, option_type, premium, stop_loss, target, spot_price
        """
        if not self.instrument_cache:
            return None
        
        # ATM strike rounded to nearest 50 (CRUDEOIL strike step)
        strike_step = 50
        atm_strike = round(spot_price / strike_step) * strike_step
        option_type = 'CE' if signal_type == 'CALL' else 'PE'
        
        key = (atm_strike, option_type)
        if key not in self.instrument_cache:
            available = sorted([k[0] for k in self.instrument_cache if k[1] == option_type])
            if available:
                nearest = min(available, key=lambda x: abs(x - atm_strike))
                key = (nearest, option_type)
            else:
                return None
        
        option_info = self.instrument_cache[key]
        
        # Fetch live premium
        quote = self.get_quote(option_info['instrument_id'])
        premium = 0
        if quote:
            premium = quote['ltp'] if quote['ltp'] > 0 else quote['close']
        
        if premium <= 0:
            premium = self.estimate_option_price(spot_price, key[0], option_type)
        
        # SL: 30% loss, Target: 50% profit (defaults, overridden by UI)
        stop_loss = premium * 0.70
        target = premium * 1.50
        
        return {
            'strike': key[0],
            'option_type': option_type,
            'premium': premium,
            'stop_loss': stop_loss,
            'target': target,
            'spot_price': spot_price,
            'instrument_id': option_info['instrument_id'],
            'display_name': option_info.get('display_name', '')
        }
    
    def get_option_ltp(self, strike, option_type, spot_price, atr=100):
        """
        Get current Crude Oil option LTP for a specific strike.
        
        Returns:
            Float premium value
        """
        if not self.instrument_cache:
            return self.estimate_option_price(spot_price, strike, option_type)
        
        key = (strike, option_type)
        if key not in self.instrument_cache:
            return self.estimate_option_price(spot_price, strike, option_type)
        
        option_info = self.instrument_cache[key]
        quote = self.get_quote(option_info['instrument_id'])
        
        if quote:
            ltp = quote['ltp'] if quote['ltp'] > 0 else quote['close']
            if ltp > 0:
                return ltp
        
        return self.estimate_option_price(spot_price, strike, option_type)
    
    def fetch_atm_options(self, symbol="CRUDEOIL"):
        """
        Standalone function to fetch and display Crude Oil ATM option prices.
        
        Args:
            symbol: "CRUDEOIL" (lot=100) or "CRUDEOILM" (lot=10)
            
        Returns:
            Dict with ATM option data or None
        """
        print("\n" + "=" * 70)
        print("CRUDE OIL ATM OPTION FETCHER (Using Instrument Master)")
        print("=" * 70 + "\n")
        
        if not self.initialize(symbol):
            return None
        
        spot_price = self.spot_price
        if not spot_price:
            spot_price = 6000  # Reasonable default
            print(f"  ⚠ Using estimated spot price: ₹{spot_price:,.0f}")
        
        # Calculate ATM strike
        strike_step = 50
        atm_strike = round(spot_price / strike_step) * strike_step
        
        ce_key = (atm_strike, 'CE')
        pe_key = (atm_strike, 'PE')
        
        if ce_key not in self.instrument_cache:
            available_ce = sorted([k[0] for k in self.instrument_cache if k[1] == 'CE'])
            if available_ce:
                nearest_ce = min(available_ce, key=lambda x: abs(x - atm_strike))
                ce_key = (nearest_ce, 'CE')
        
        if pe_key not in self.instrument_cache:
            available_pe = sorted([k[0] for k in self.instrument_cache if k[1] == 'PE'])
            if available_pe:
                nearest_pe = min(available_pe, key=lambda x: abs(x - atm_strike))
                pe_key = (nearest_pe, 'PE')
        
        if ce_key not in self.instrument_cache or pe_key not in self.instrument_cache:
            print("  ✗ Could not find ATM options")
            return None
        
        call_info = self.instrument_cache[ce_key]
        put_info = self.instrument_cache[pe_key]
        
        # Fetch real-time prices
        print(f"\n  Fetching option prices...")
        print(f"  CE: {call_info['display_name']} (ID={call_info['instrument_id']})")
        print(f"  PE: {put_info['display_name']} (ID={put_info['instrument_id']})")
        
        call_quote = self.get_quote(call_info['instrument_id'])
        put_quote = self.get_quote(put_info['instrument_id'])
        
        call_ltp = 0
        put_ltp = 0
        call_estimated = True
        put_estimated = True
        
        if call_quote and call_quote['ltp'] > 0:
            call_ltp = call_quote['ltp']
            call_estimated = False
            print(f"  Call ({call_info['display_name']}): ₹{call_ltp:,.1f}  ✓ LIVE")
        elif call_quote and call_quote['close'] > 0:
            call_ltp = call_quote['close']
            call_estimated = False
            print(f"  Call ({call_info['display_name']}): ₹{call_ltp:,.1f}  (Last Close)")
        else:
            call_ltp = self.estimate_option_price(spot_price, ce_key[0], 'CE')
            print(f"  Call ({call_info['display_name']}): ₹{call_ltp:,.1f}  (Estimated)")
        
        if put_quote and put_quote['ltp'] > 0:
            put_ltp = put_quote['ltp']
            put_estimated = False
            print(f"  Put  ({put_info['display_name']}): ₹{put_ltp:,.1f}  ✓ LIVE")
        elif put_quote and put_quote['close'] > 0:
            put_ltp = put_quote['close']
            put_estimated = False
            print(f"  Put  ({put_info['display_name']}): ₹{put_ltp:,.1f}  (Last Close)")
        else:
            put_ltp = self.estimate_option_price(spot_price, pe_key[0], 'PE')
            print(f"  Put  ({put_info['display_name']}): ₹{put_ltp:,.1f}  (Estimated)")
        
        lot_size = call_info.get('lot_size', 100)
        print(f"\n  Lot Size:     {lot_size}")
        print(f"  CE Cost:      ₹{call_ltp * lot_size:,.2f} ({lot_size} × ₹{call_ltp:,.1f})")
        print(f"  PE Cost:      ₹{put_ltp * lot_size:,.2f} ({lot_size} × ₹{put_ltp:,.1f})")
        print(f"  Straddle:     ₹{(call_ltp + put_ltp) * lot_size:,.2f}")
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'spot_price': spot_price,
            'atm_strike': atm_strike,
            'expiry': self.expiry,
            'lot_size': lot_size,
            'call': {
                'instrument_id': call_info['instrument_id'],
                'display_name': call_info['display_name'],
                'strike': ce_key[0],
                'ltp': call_ltp,
                'estimated': call_estimated,
                'quote': call_quote
            },
            'put': {
                'instrument_id': put_info['instrument_id'],
                'display_name': put_info['display_name'],
                'strike': pe_key[0],
                'ltp': put_ltp,
                'estimated': put_estimated,
                'quote': put_quote
            }
        }
        
        output_file = "crude_atm_options_result.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\n✓ Results saved to {output_file}")
        print("=" * 70 + "\n")
        
        return result


if __name__ == "__main__":
    fetcher = CrudeOilATMOptionFetcher()
    result = fetcher.fetch_atm_options("CRUDEOIL")
    
    if result:
        print("Success! Check crude_atm_options_result.json for details.")
    else:
        print("\nFailed to fetch Crude Oil ATM options.")
        print("Please verify:")
        print("1. Market hours — MCX: 9:00 AM - 11:30 PM IST")
        print("2. XTS API credentials are correct")
        print("3. Account has MCXFO data access")
