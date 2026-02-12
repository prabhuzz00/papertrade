"""
Fetch NIFTY ATM Option Prices using XTS API (Instrument Master approach)

Uses instrument master download to get numeric instrument IDs,
then fetches real-time quotes via the quotes endpoint.
Same reliable approach as the Gold option fetcher.

KEY POINTS:
- Uses POST /instruments/master with NSEFO segment to get instrument data
- Parses NIFTY option contracts with numeric instrument IDs
- Fetches real-time LTP via /instruments/quotes with numeric IDs
- Falls back to estimation only when API fails
- NIFTY lot size = 65, strikes in 50-point increments
"""

import requests
import json
from datetime import datetime
import urllib3
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NiftyATMOptionFetcher:
    """Fetch NIFTY ATM option prices using instrument master for numeric IDs"""
    
    TOKEN_REFRESH_INTERVAL = 180  # Re-login every 3 minutes to keep token fresh
    
    def __init__(self):
        self.token = None
        self.base_url = XTS_BASE_URL
        self.app_key = XTS_APP_KEY
        self.secret_key = XTS_SECRET_KEY
        self.source = XTS_SOURCE
        self.instrument_cache = {}  # {(strike, 'CE'/'PE'): instrument_info}
        self.master_lines = None
        self.expiry = None
        self._login_time = None  # Track when we last logged in
    
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
                    print(f"[OK] NIFTY Option Fetcher: XTS login successful")
                    return True
            
            print(f"[ERROR] NIFTY Option Fetcher: Login failed: {response.text[:200]}")
            return False
        
        except Exception as e:
            print(f"[ERROR] NIFTY Option Fetcher: Login error: {e}")
            return False
    
    def _ensure_token(self):
        """Check if token is still valid and refresh if needed."""
        if not self.token or not self._login_time:
            return self.login()
        
        elapsed = (datetime.now() - self._login_time).total_seconds()
        if elapsed > self.TOKEN_REFRESH_INTERVAL:
            print(f"[INFO] NIFTY Option Fetcher: Token expired ({elapsed:.0f}s), re-logging in...")
            return self.login()
        
        return True
    
    def download_nsefo_master(self):
        """
        Download NSEFO instrument master via POST endpoint.
        This gives us numeric instrument IDs for all NIFTY options.
        
        Returns:
            List of pipe-delimited instrument record strings, or None
        """
        if not self.token:
            if not self.login():
                return None
        
        url = f"{self.base_url}/instruments/master"
        headers = {
            'Authorization': self.token,
            'Content-Type': 'application/json'
        }
        
        payload = {'exchangeSegmentList': ['NSEFO']}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30, verify=False)
            if response.status_code == 200:
                data = response.json()
                master_text = data.get('result', '')
                lines = [l for l in master_text.split('\n') if l.strip()]
                print(f"[OK] Downloaded NSEFO master: {len(lines)} instruments")
                self.master_lines = lines
                return lines
            else:
                print(f"[ERROR] NSEFO master download failed: {response.status_code} - {response.text[:200]}")
                return None
        except Exception as e:
            print(f"[ERROR] NSEFO master download error: {e}")
            return None
    
    def parse_nifty_options(self, master_lines=None, expiry_filter=None):
        """
        Parse NIFTY option instruments from master data.
        
        Master record format (pipe-delimited):
        Index 0:  Segment (e.g., NSEFO)
        Index 1:  ExchangeInstrumentID (numeric)
        Index 3:  Symbol (e.g., NIFTY)
        Index 5:  Series (e.g., OPTIDX)
        Index 13: Lot size
        Index 16: Expiry date (ISO format: 2026-02-13T14:30:00)
        Index 17: Strike price
        Index 18: Option type code (3=CE, 4=PE)
        Index 19: Display name (e.g., "NIFTY 13FEB2026 CE 25000")
        
        Args:
            master_lines: List of pipe-delimited record strings
            expiry_filter: Optional date string to filter by (e.g., "2026-02-13")
            
        Returns:
            Dict mapping (strike, option_type) -> instrument info
        """
        if master_lines is None:
            master_lines = self.master_lines
        if not master_lines:
            return {}
        
        options = {}
        
        for line in master_lines:
            # Quick filter: must contain NIFTY and OPTIDX
            if 'NIFTY' not in line or 'OPTIDX' not in line:
                continue
            
            parts = line.split('|')
            if len(parts) < 20:
                continue
            
            try:
                inst_id = int(parts[1])
                sym = parts[3]
                series = parts[5]
                expiry = parts[16]          # e.g., 2026-02-13T14:30:00
                strike_raw = parts[17]
                opt_type_code = parts[18]
                display_name = parts[19]
                lot_size = int(parts[13]) if parts[13].isdigit() else 65
                
                # Only NIFTY options (exclude BANKNIFTY, FINNIFTY, etc.)
                if sym != 'NIFTY' or series != 'OPTIDX':
                    continue
                
                # Parse strike (may be float string like "25000.000000")
                strike = int(float(strike_raw))
                
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
    
    def get_nearest_expiry(self, options=None):
        """
        Get nearest expiry date from parsed options data.
        
        Args:
            options: Dict from parse_nifty_options(), or None to parse fresh
            
        Returns:
            Nearest expiry string or None
        """
        if options is None:
            options = self.parse_nifty_options()
        
        expiries = set()
        for key, opt in options.items():
            expiries.add(opt['expiry'])
        
        expiries = sorted(expiries)
        
        # Find the nearest expiry that is today or in the future
        today_str = datetime.now().strftime('%Y-%m-%d')
        for exp in expiries:
            exp_date = exp.split('T')[0]
            if exp_date >= today_str:
                return exp
        
        # If all are past, return the last one
        return expiries[-1] if expiries else None
    
    def get_quote(self, instrument_id, segment=2, _retried=False):
        """
        Fetch real-time quote for an instrument using quotes endpoint.
        Automatically refreshes token on any failure and retries once.
        
        Args:
            instrument_id: Numeric ExchangeInstrumentID from master
            segment: Exchange segment (2=NSEFO/NFO)
            _retried: Internal flag to prevent infinite retry loops
            
        Returns:
            Dict with ltp, close, open, high, low, volume, bid, ask or None
        """
        # Ensure token is fresh before making request
        if not self._ensure_token():
            if not _retried and self.login():
                return self.get_quote(instrument_id, segment, _retried=True)
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
            
            # Handle explicit auth failure
            if response.status_code in (401, 403):
                if not _retried:
                    print(f"[WARNING] XTS auth failed (HTTP {response.status_code}), refreshing token...")
                    if self.login():
                        return self.get_quote(instrument_id, segment, _retried=True)
                return None
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for error in response body (e.g., session invalidated)
                if data.get('type') == 'error':
                    if not _retried:
                        print(f"[WARNING] XTS API error: {data.get('description', 'unknown')}, refreshing token...")
                        if self.login():
                            return self.get_quote(instrument_id, segment, _retried=True)
                    return None
                
                if 'result' in data and 'listQuotes' in data['result']:
                    quotes = data['result']['listQuotes']
                    if quotes and len(quotes) > 0:
                        quote = quotes[0]
                        if isinstance(quote, str):
                            quote = json.loads(quote)
                        
                        touchline = quote.get('Touchline', {})
                        bid_info = touchline.get('BidInfo', {})
                        ask_info = touchline.get('AskInfo', {})
                        
                        result = {
                            'ltp': touchline.get('LastTradedPrice', 0),
                            'close': touchline.get('Close', 0),
                            'open': touchline.get('Open', 0),
                            'high': touchline.get('High', 0),
                            'low': touchline.get('Low', 0),
                            'volume': touchline.get('TotalTradedQuantity', 0),
                            'bid': bid_info.get('Price', 0) if isinstance(bid_info, dict) else 0,
                            'ask': ask_info.get('Price', 0) if isinstance(ask_info, dict) else 0,
                        }
                        
                        # If LTP and close are both 0, data may be stale - retry with fresh token
                        if result['ltp'] == 0 and result['close'] == 0 and not _retried:
                            print(f"[WARNING] Got empty quote for inst {instrument_id}, refreshing token and retrying...")
                            if self.login():
                                return self.get_quote(instrument_id, segment, _retried=True)
                        
                        return result
            
            # Non-200 status (not 401/403) - retry with fresh token
            if not _retried:
                print(f"[WARNING] XTS returned HTTP {response.status_code}, refreshing token...")
                if self.login():
                    return self.get_quote(instrument_id, segment, _retried=True)
            
            return None
        except Exception as e:
            # Network error / timeout - retry once with fresh login
            if not _retried:
                print(f"[WARNING] Quote fetch error for inst {instrument_id}: {e}, retrying...")
                if self.login():
                    return self.get_quote(instrument_id, segment, _retried=True)
            print(f"[ERROR] Quote fetch failed for instrument {instrument_id}: {e}")
            return None
    
    def get_nifty_spot(self):
        """
        Get NIFTY 50 spot price from XTS API.
        Uses NSE segment (1) with instrument ID 26000.
        
        Returns:
            Float price or 0
        """
        if not self.token:
            return 0
        
        try:
            quote = self.get_quote(26000, segment=1)  # NSE segment, NIFTY 50 ID
            if quote:
                ltp = quote['ltp']
                if ltp > 0:
                    return float(ltp)
                close = quote['close']
                if close > 0:
                    return float(close)
            return 0
        except Exception:
            return 0
    
    def get_option_ltp(self, strike, option_type, spot_price=0, atr=50):
        """
        Get real-time option LTP for a specific strike.
        Uses instrument master numeric IDs (reliable method).
        
        Args:
            strike: Option strike price (e.g., 25950)
            option_type: 'CE' or 'PE'
            spot_price: Current NIFTY spot price (for estimation fallback)
            atr: ATR for estimation fallback
            
        Returns:
            tuple: (float premium, str source) where source is 'LIVE' or 'ESTIMATED'
        """
        if not self.instrument_cache:
            price = self._estimate_option_price(strike, option_type, spot_price, atr)
            return price, 'ESTIMATED'
        
        key = (strike, option_type)
        if key not in self.instrument_cache:
            # Try to find nearest available strike
            available = sorted([k[0] for k in self.instrument_cache if k[1] == option_type])
            if available:
                nearest = min(available, key=lambda x: abs(x - strike))
                key = (nearest, option_type)
            else:
                price = self._estimate_option_price(strike, option_type, spot_price, atr)
                return price, 'ESTIMATED'
        
        option_info = self.instrument_cache[key]
        
        # Fetch live quote using numeric instrument ID
        quote = self.get_quote(option_info['instrument_id'], segment=2)
        
        if quote:
            ltp = quote['ltp']
            if ltp > 0:
                return float(ltp), 'LIVE'
            close = quote['close']
            if close > 0:
                return float(close), 'LIVE'
        
        # Fallback to estimation
        print(f"[WARNING] Could not get LIVE quote for {strike} {option_type} (inst_id={option_info['instrument_id']}), using estimation")
        price = self._estimate_option_price(strike, option_type, spot_price, atr)
        return price, 'ESTIMATED'
    
    def get_option_data(self, signal_type, spot_price, atr=50):
        """
        Get complete option data for trading.
        Fetches real premium from XTS, sets SL/Target.
        
        Args:
            signal_type: 'CALL' or 'PUT'
            spot_price: Current NIFTY spot price
            atr: Average True Range
            
        Returns:
            dict with strike, option_type, premium, stop_loss, target, spot_price, source
        """
        # Calculate ATM strike (rounded to nearest 50)
        atm_strike = round(spot_price / 50) * 50
        option_type = 'CE' if signal_type == 'CALL' else 'PE'
        
        # Fetch real option premium (returns tuple: price, source)
        premium, source = self.get_option_ltp(atm_strike, option_type, spot_price, atr)
        
        # SL: 30% loss, Target: 50% profit (based on premium)
        stop_loss = premium * 0.70
        target = premium * 1.50
        
        print(f"[OPTION] {atm_strike} {option_type}: ₹{premium:.2f} [{source}] | SL: ₹{stop_loss:.2f} | TGT: ₹{target:.2f}")
        
        return {
            'strike': atm_strike,
            'option_type': option_type,
            'premium': premium,
            'stop_loss': stop_loss,
            'target': target,
            'spot_price': spot_price,
            'source': source
        }
    
    def _estimate_option_price(self, strike, option_type, spot_price, atr=50):
        """
        Estimate option price when no live data available.
        Based on intrinsic value + time value model.
        
        Args:
            strike: Strike price
            option_type: 'CE' or 'PE'
            spot_price: Current spot price
            atr: ATR for volatility
            
        Returns:
            Estimated premium (float)
        """
        if spot_price <= 0:
            return 100.0  # Safe default
        
        # Calculate intrinsic value
        if option_type == 'CE':
            intrinsic = max(0, spot_price - strike)
        else:  # PE
            intrinsic = max(0, strike - spot_price)
        
        # Calculate distance from ATM
        distance_from_atm = abs(spot_price - strike)
        
        # ATM options typically trade at 0.3-0.5% of spot price for weekly expiry
        atm_base_premium = spot_price * 0.004  # ~0.4% of spot (~104 Rs for 26000 spot)
        
        # Volatility adjustment (minimum 1.0 to avoid underestimating)
        volatility_multiplier = max(1.0, (atr / 50) * 1.2)
        
        # Calculate time value based on moneyness
        if distance_from_atm <= 50:  # ATM or very close
            decay_factor = 1.0 - (distance_from_atm / 50) * 0.3
            time_value = atm_base_premium * volatility_multiplier * decay_factor
        elif distance_from_atm <= 150:  # Near money
            decay_factor = 0.7 - ((distance_from_atm - 50) / 100) * 0.4
            time_value = atm_base_premium * volatility_multiplier * decay_factor
        elif distance_from_atm <= 300:  # Slightly OTM/ITM
            decay_factor = 0.3 - ((distance_from_atm - 150) / 150) * 0.2
            time_value = atm_base_premium * volatility_multiplier * decay_factor
        else:  # Deep OTM/ITM
            time_value = max(5, atm_base_premium * 0.1)
        
        option_price = intrinsic + time_value
        option_price = round(option_price * 20) / 20  # NSE tick size
        
        return max(5.0, option_price)
    
    def initialize(self):
        """
        Full initialization: login, download master, parse NIFTY options.
        Call this once at startup.
        
        Returns:
            True if successful
        """
        try:
            # Step 1: Login
            if not self.login():
                return False
            
            # Step 2: Download NSEFO instrument master
            print("[INFO] Downloading NSEFO instrument master for NIFTY options...")
            master_lines = self.download_nsefo_master()
            if not master_lines:
                print("[WARNING] Failed to download NSEFO master - will use estimation")
                return False
            
            # Step 3: Parse all NIFTY options  
            all_options = self.parse_nifty_options(master_lines)
            print(f"[INFO] Found {len(all_options)} NIFTY option contracts total")
            
            if not all_options:
                print("[WARNING] No NIFTY options found in master data")
                return False
            
            # Step 4: Get nearest expiry
            nearest_expiry = self.get_nearest_expiry(all_options)
            if not nearest_expiry:
                print("[WARNING] No expiry dates found for NIFTY options")
                return False
            
            expiry_date = nearest_expiry.split('T')[0]
            self.expiry = expiry_date
            
            # Step 5: Filter for nearest expiry and cache
            self.instrument_cache = self.parse_nifty_options(
                master_lines, expiry_filter=expiry_date
            )
            print(f"[OK] NIFTY options loaded: {len(self.instrument_cache)} contracts, expiry={expiry_date}")
            
            # Show available strike range
            strikes = sorted(set(k[0] for k in self.instrument_cache.keys()))
            if strikes:
                print(f"[INFO] Strike range: {strikes[0]} - {strikes[-1]} (50-point steps)")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] NIFTY option initialization error: {e}")
            return False


if __name__ == "__main__":
    """Test the NIFTY ATM option fetcher"""
    fetcher = NiftyATMOptionFetcher()
    
    if not fetcher.initialize():
        print("\nFailed to initialize. Check XTS credentials and connectivity.")
        exit(1)
    
    # Get NIFTY spot price
    spot = fetcher.get_nifty_spot()
    if spot > 0:
        print(f"\nNIFTY 50 Spot: ₹{spot:,.2f}")
    else:
        spot = 25950  # Fallback
        print(f"\nUsing estimated NIFTY spot: ₹{spot:,.2f}")
    
    # Get ATM strike
    atm_strike = round(spot / 50) * 50
    print(f"ATM Strike: {atm_strike}")
    
    # Fetch real option data
    print("\n" + "=" * 70)
    print("NIFTY ATM OPTION PRICES (LIVE from XTS)")
    print("=" * 70)
    
    # Show nearby strikes
    for offset in [-200, -150, -100, -50, 0, 50, 100, 150, 200]:
        strike = atm_strike + offset
        ce_ltp, ce_src = fetcher.get_option_ltp(strike, 'CE', spot)
        pe_ltp, pe_src = fetcher.get_option_ltp(strike, 'PE', spot)
        
        atm_marker = " <-- ATM" if offset == 0 else ""
        print(f"  {strike}: CE=₹{ce_ltp:>8.2f} [{ce_src}]  PE=₹{pe_ltp:>8.2f} [{pe_src}]{atm_marker}")
    
    # Full option data for CALL and PUT
    print("\n" + "-" * 70)
    call_data = fetcher.get_option_data('CALL', spot)
    put_data = fetcher.get_option_data('PUT', spot)
    
    print(f"\nCALL Signal Trade Setup:")
    print(f"  Option: NIFTY {call_data['strike']} CE")
    print(f"  Premium: ₹{call_data['premium']:.2f}")
    print(f"  SL: ₹{call_data['stop_loss']:.2f} (-30%)")
    print(f"  Target: ₹{call_data['target']:.2f} (+50%)")
    print(f"  Cost (65 qty): ₹{call_data['premium'] * 65:,.2f}")
    
    print(f"\nPUT Signal Trade Setup:")
    print(f"  Option: NIFTY {put_data['strike']} PE")
    print(f"  Premium: ₹{put_data['premium']:.2f}")
    print(f"  SL: ₹{put_data['stop_loss']:.2f} (-30%)")
    print(f"  Target: ₹{put_data['target']:.2f} (+50%)")
    print(f"  Cost (65 qty): ₹{put_data['premium'] * 65:,.2f}")
    
    print("\n" + "=" * 70)
