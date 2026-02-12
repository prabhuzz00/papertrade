"""
Fetch Gold ATM Option Prices using XTS API
Uses instrument master download to get numeric instrument IDs,
then fetches real-time quotes via the quotes endpoint.

KEY FINDINGS (from debugging):
- GetOptionSymbol endpoint does NOT work for MCX options (segment 51)
- Instrument master via POST /instruments/master works for MCXFO
- GOLDM futures trade around Rs.155,000-162,000 (not 75,000)
- GOLDM option lot size = 10, GOLD lot size = 100
- Strikes are in 100-point increments
- opt_type_code in master: 3=CE, 4=PE
"""

import requests
import json
from datetime import datetime
import urllib3
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class GoldATMOptionFetcher:
    """Fetch Gold ATM option prices using instrument master for numeric IDs"""
    
    TOKEN_REFRESH_INTERVAL = 180  # 3 minutes
    
    def __init__(self):
        self.token = None
        self.base_url = XTS_BASE_URL
        self.app_key = XTS_APP_KEY
        self.secret_key = XTS_SECRET_KEY
        self.source = XTS_SOURCE
        self.instrument_cache = {}  # {(strike, 'CE'/'PE'): instrument_info}
        self._login_time = None
    
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
                    print(f"✓ Gold API Login successful")
                    return True
            
            print(f"✗ Gold API Login failed: {response.text}")
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
        This is the ONLY reliable way to get MCX option instrument IDs.
        GetOptionSymbol does NOT work for MCX.
        
        Returns:
            List of pipe-delimited instrument record strings, or None
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
    
    def parse_gold_options(self, master_lines, symbol="GOLD", expiry_filter=None):
        """
        Parse Gold option instruments from master data.
        
        Master record format (pipe-delimited):
        Index 0:  Segment (e.g., MCXFO)
        Index 1:  ExchangeInstrumentID (numeric)
        Index 3:  Symbol (e.g., GOLDM)
        Index 5:  Series (e.g., OPTFUT)
        Index 13: Lot size
        Index 16: Expiry date (ISO format: 2026-02-26T23:59:59)
        Index 17: Strike price
        Index 18: Option type code (3=CE, 4=PE)
        Index 19: Display name (e.g., "GOLDM 26FEB2026 CE 155000")
        
        Args:
            master_lines: List of pipe-delimited record strings
            symbol: "GOLDM" or "GOLD"
            expiry_filter: Optional date string to filter by (e.g., "2026-02-26")
            
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
                expiry = parts[16]          # e.g., 2026-02-26T23:59:59
                strike = int(parts[17])
                opt_type_code = parts[18]
                display_name = parts[19]
                lot_size = int(parts[13]) if parts[13].isdigit() else 10
                
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
    
    def parse_gold_futures(self, master_lines, symbol="GOLD"):
        """
        Parse Gold future instruments from master data.
        Used to find the nearest future contract for spot price reference.
        
        Args:
            master_lines: List of pipe-delimited record strings
            symbol: "GOLDM" or "GOLD"
            
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
    
    def get_gold_spot_price(self, master_lines, symbol="GOLD"):
        """
        Get Gold spot/future price from nearest future contract.
        
        Args:
            master_lines: Master data lines
            symbol: "GOLDM" or "GOLD"
            
        Returns:
            Float price or None
        """
        futures = self.parse_gold_futures(master_lines, symbol)
        
        if not futures:
            print("  ✗ No Gold futures found in master data")
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
        
        print("  ✗ Could not get Gold spot price (market may be closed)")
        return None
    
    def get_nearest_expiry(self, options):
        """
        Get nearest expiry date from parsed options data.
        
        Args:
            options: Dict from parse_gold_options()
            
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
        Uses simple 2.5% ATM premium with distance-based decay.
        
        Args:
            spot_price: Current spot/future price
            strike_price: Option strike price
            option_type: 'CE' or 'PE'
            
        Returns:
            Estimated premium (float)
        """
        distance = abs(strike_price - spot_price)
        atm_premium = spot_price * 0.025  # ~2.5% of spot as ATM estimate
        
        if distance < 1000:
            return round(atm_premium, 1)
        
        decay = max(0.1, 1 - (distance / spot_price) * 2)
        return round(atm_premium * decay, 1)
    
    def fetch_atm_options(self, symbol="GOLD"):
        """
        Main function to fetch Gold ATM option prices.
        
        Flow:
        1. Login to XTS API
        2. Download MCXFO instrument master (POST endpoint)
        3. Get spot price from nearest GOLDM future
        4. Parse options from master, find ATM strike
        5. Fetch real-time quotes using numeric instrument IDs
        
        Args:
            symbol: "GOLDM" (lot=10) or "GOLD" (lot=100)
            
        Returns:
            Dict with ATM option data or None
        """
        print("\n" + "=" * 70)
        print("GOLD ATM OPTION FETCHER (Using Instrument Master)")
        print("=" * 70 + "\n")
        
        # Step 1: Login
        if not self.login():
            return None
        
        # Step 2: Download instrument master
        print("\n[1/4] Downloading MCXFO instrument master...")
        master_lines = self.download_mcxfo_master()
        if not master_lines:
            return None
        
        # Step 3: Get Gold spot/future price
        print(f"\n[2/4] Getting {symbol} spot price from futures...")
        spot_price = self.get_gold_spot_price(master_lines, symbol)
        
        if not spot_price:
            # Reasonable default based on current market levels
            spot_price = 157000
            print(f"  ⚠ Using estimated spot price: ₹{spot_price:,.0f}")
        
        # Step 4: Parse options and find ATM
        print(f"\n[3/4] Parsing {symbol} options from master...")
        all_options = self.parse_gold_options(master_lines, symbol)
        print(f"  Found {len(all_options)} option contracts total")
        
        if len(all_options) == 0:
            print(f"  ✗ No {symbol} options found in master data")
            return None
        
        # Get nearest expiry
        nearest_expiry = self.get_nearest_expiry(all_options)
        if not nearest_expiry:
            print("  ✗ No expiry dates found")
            return None
        
        expiry_date = nearest_expiry.split('T')[0]  # e.g., 2026-02-26
        print(f"  Nearest expiry: {expiry_date}")
        
        # Filter for nearest expiry only
        options = self.parse_gold_options(master_lines, symbol, expiry_filter=expiry_date)
        print(f"  Options for {expiry_date}: {len(options)}")
        
        # Calculate ATM strike (GOLD strikes are in 1000 increments)
        strike_step = 1000 if symbol == "GOLD" else 100
        atm_strike = round(spot_price / strike_step) * strike_step
        print(f"  ATM Strike: {atm_strike} (Spot: ₹{spot_price:,.1f})")
        
        # Find the exact ATM strikes (may need to find nearest available)
        ce_key = (atm_strike, 'CE')
        pe_key = (atm_strike, 'PE')
        
        if ce_key not in options:
            available_ce = sorted([k[0] for k in options if k[1] == 'CE'])
            if available_ce:
                nearest_ce = min(available_ce, key=lambda x: abs(x - atm_strike))
                ce_key = (nearest_ce, 'CE')
                print(f"  Nearest CE strike: {nearest_ce}")
            else:
                print("  ✗ No CE options available")
                return None
        
        if pe_key not in options:
            available_pe = sorted([k[0] for k in options if k[1] == 'PE'])
            if available_pe:
                nearest_pe = min(available_pe, key=lambda x: abs(x - atm_strike))
                pe_key = (nearest_pe, 'PE')
                print(f"  Nearest PE strike: {nearest_pe}")
            else:
                print("  ✗ No PE options available")
                return None
        
        call_info = options[ce_key]
        put_info = options[pe_key]
        
        # Step 5: Fetch real-time prices
        print(f"\n[4/4] Fetching option prices...")
        print(f"  CE: {call_info['display_name']} (ID={call_info['instrument_id']})")
        print(f"  PE: {put_info['display_name']} (ID={put_info['instrument_id']})")
        
        call_quote = self.get_quote(call_info['instrument_id'])
        put_quote = self.get_quote(put_info['instrument_id'])
        
        # Process results
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        
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
        
        # Show nearby strikes (chain view)
        print(f"\n--- Option Chain (Nearby Strikes) ---")
        nearby_strikes = sorted(set(
            range(atm_strike - 5000, atm_strike + 6000, 1000)
        ))
        for strike in nearby_strikes:
            ce_k = (strike, 'CE')
            pe_k = (strike, 'PE')
            if ce_k in options and pe_k in options:
                ce_q = self.get_quote(options[ce_k]['instrument_id'])
                pe_q = self.get_quote(options[pe_k]['instrument_id'])
                
                ce_p = ce_q['ltp'] if ce_q and ce_q['ltp'] > 0 else (ce_q['close'] if ce_q else 0)
                pe_p = pe_q['ltp'] if pe_q and pe_q['ltp'] > 0 else (pe_q['close'] if pe_q else 0)
                
                atm_marker = " <-- ATM" if strike == atm_strike else ""
                print(f"  {strike}: CE=₹{ce_p:>8,.1f}  PE=₹{pe_p:>8,.1f}{atm_marker}")
        
        # Build result
        result = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'spot_price': spot_price,
            'atm_strike': atm_strike,
            'expiry': expiry_date,
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
        
        # Save to JSON
        output_file = "gold_atm_options_result.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\n✓ Results saved to {output_file}")
        print("=" * 70 + "\n")
        
        return result


if __name__ == "__main__":
    fetcher = GoldATMOptionFetcher()
    result = fetcher.fetch_atm_options("GOLD")
    
    if result:
        print("Success! Check gold_atm_options_result.json for details.")
    else:
        print("\nFailed to fetch Gold ATM options.")
        print("Please verify:")
        print("1. Market hours — MCX: 9:00 AM - 11:30 PM IST")
        print("2. XTS API credentials are correct")
        print("3. Account has MCXFO data access")
