"""
Option Price Fetcher

Fetches real-time option prices from XTS API with estimation fallback
"""

import requests
import pandas as pd
from datetime import datetime
import math
import json
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE
import urllib3

# Disable SSL warnings for XTS API
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class OptionPriceFetcher:
    """Fetch or estimate option prices"""
    
    def __init__(self, use_xts=True):  # Enabled by default for spot price fetching
        self.use_xts = use_xts
        self.xts_token = None
        self.option_chain_cache = {}
        self.cache_time = None
        self.subscribed_instruments = set()  # Track subscribed instruments
        
        if use_xts:
            try:
                self.xts_login()
                print("[OK] Option Price Fetcher initialized - XTS API connected")
                print("[INFO] Real-time NIFTY spot price enabled")
            except Exception as e:
                print(f"[WARNING] XTS login failed: {e}")
                print("[INFO] Falling back to estimation model")
                self.use_xts = False
        else:
            print("[INFO] Option Price Fetcher - Using estimation model")
            print("[INFO] To enable XTS API: OptionPriceFetcher(use_xts=True)")
    
    def xts_login(self):
        """Login to XTS API and get token"""
        try:
            url = f"{XTS_BASE_URL}/auth/login"
            payload = {
                'secretKey': XTS_SECRET_KEY,
                'appKey': XTS_APP_KEY,
                'source': XTS_SOURCE
            }
            
            # Disable SSL verification for XTS API (common issue with broker APIs)
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, 
                                   timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                self.xts_token = data.get('result', {}).get('token')
                if self.xts_token:
                    print(f"[OK] XTS Token: {self.xts_token[:20]}...")
                    return True
            
            raise Exception(f"Login failed: {response.text}")
        except Exception as e:
            raise Exception(f"XTS login error: {str(e)}")
    
    def xts_subscribe_instrument(self, strike: int, option_type: str) -> bool:
        """Subscribe to option instrument before fetching quotes"""
        if not self.xts_token:
            return False
        
        # Create instrument identifier
        instrument_key = f"{strike}_{option_type}"
        
        # Check if already subscribed
        if instrument_key in self.subscribed_instruments:
            return True
        
        try:
            url = f"{XTS_BASE_URL}/instruments/subscription"
            headers = {
                'Authorization': self.xts_token,
                'Content-Type': 'application/json'
            }
            
            # Format: "NIFTY 30JAN26 25300 CE"
            # Get current expiry (weekly - next Thursday)
            from datetime import datetime, timedelta
            today = datetime.now()
            days_ahead = 3 - today.weekday()  # Thursday is 3
            if days_ahead <= 0:
                days_ahead += 7
            next_thursday = today + timedelta(days_ahead)
            expiry_str = next_thursday.strftime("%d%b%y").upper()
            
            instrument_symbol = f"NIFTY {expiry_str} {strike} {option_type}"
            
            payload = {
                'instruments': [{
                    'exchangeSegment': 2,  # NFO
                    'exchangeInstrumentID': instrument_symbol
                }],
                'xtsMessageCode': 1501  # Subscribe
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=5, verify=False)
            
            if response.status_code == 200:
                self.subscribed_instruments.add(instrument_key)
                print(f"[OK] Subscribed: {instrument_symbol}")
                return True
            else:
                print(f"[WARNING] Subscription failed: {response.text[:100]}")
                return False
                
        except Exception as e:
            print(f"[WARNING] Subscription error: {str(e)}")
            return False
    
    def get_xts_option_chain(self, expiry_date='30JAN2026'):
        """Fetch option chain from XTS API"""
        if not self.xts_token:
            return None
        
        try:
            # Check cache (refresh every 5 seconds)
            now = datetime.now()
            if self.cache_time and (now - self.cache_time).seconds < 5:
                return self.option_chain_cache
            
            # XTS API endpoint for option chain (NIFTY)
            url = f"{XTS_BASE_URL}/instruments/ohlc"
            headers = {
                'Authorization': self.xts_token,
                'Content-Type': 'application/json'
            }
            
            # Get NIFTY option chain
            # Note: XTS uses exchangeSegment 2 for NFO (NIFTY Options)
            params = {
                'exchangeSegment': 2,  # NFO
                'exchangeInstrumentID': 'NIFTY'  # This may need adjustment based on XTS format
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10, verify=False)
            
            if response.status_code == 200:
                self.option_chain_cache = response.json()
                self.cache_time = now
                return self.option_chain_cache
            else:
                print(f"[WARNING] XTS API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"[WARNING] XTS fetch error: {str(e)}")
            return None
    
    def get_nifty_spot(self) -> float:
        """Get real-time NIFTY spot price from XTS API"""
        if not self.xts_token:
            return 0
        
        try:
            url = f"{XTS_BASE_URL}/instruments/quotes"
            headers = {
                'Authorization': self.xts_token,
                'Content-Type': 'application/json'
            }
            
            # NIFTY 50 index on NSE (segment 1, instrument ID 26000)
            payload = {
                'instruments': [{
                    'exchangeSegment': 1,  # NSE
                    'exchangeInstrumentID': 26000  # NIFTY 50
                }],
                'xtsMessageCode': 1502,
                'publishFormat': 'JSON'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=5, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                
                # XTS returns nested JSON string in listQuotes
                if 'result' in data and 'listQuotes' in data['result']:
                    quotes_list = data['result']['listQuotes']
                    
                    if quotes_list and len(quotes_list) > 0:
                        quote_str = quotes_list[0]
                        if quote_str:
                            try:
                                quote_data = json.loads(quote_str)
                                
                                # Extract LTP from Touchline
                                if 'Touchline' in quote_data:
                                    ltp = quote_data['Touchline'].get('LastTradedPrice', 0)
                                    if ltp > 0:
                                        return float(ltp)
                            except json.JSONDecodeError:
                                pass
            
            return 0
            
        except Exception as e:
            print(f"[WARNING] XTS spot price fetch error: {str(e)}")
            return 0
    
    def get_option_ltp(self, strike: int, option_type: str, spot_price: float, 
                      atr: float = 50) -> float:
        """
        Get option LTP - tries NSE API first, then XTS, falls back to estimation
        
        Args:
            strike: Strike price (e.g., 25250)
            option_type: 'CE' or 'PE'
            spot_price: Current NIFTY spot price
            atr: Average True Range for volatility estimation
        
        Returns:
            Option price (premium)
        """
        
        # Try NSE option chain API first (most reliable)
        try:
            nse_price = self._fetch_from_nse(strike, option_type)
            if nse_price and nse_price > 0:
                return nse_price
        except Exception as e:
            pass  # Silently fall through to next method
        
        # Try XTS API if enabled
        if self.use_xts and self.xts_token:
            try:
                xts_price = self._fetch_from_xts(strike, option_type)
                if xts_price and xts_price > 0:
                    return xts_price
            except Exception as e:
                pass  # Silently fall through to estimation
        
        # Fallback to estimation
        return self._estimate_option_price(strike, option_type, spot_price, atr)
    

    def _fetch_from_nse(self, strike: int, option_type: str) -> float:
        """Fetch real option price from NSE option chain API"""
        try:
            # NSE API requires browser-like headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://www.nseindia.com/option-chain',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # First, get cookies by visiting the main page
            session = requests.Session()
            session.get('https://www.nseindia.com', headers=headers, timeout=5)
            
            # Now fetch option chain data
            url = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
            response = session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse option chain data
                if 'records' in data and 'data' in data['records']:
                    for record in data['records']['data']:
                        # Check if this strike matches
                        if record.get('strikePrice') == strike:
                            # Get CE or PE data
                            if option_type == 'CE' and 'CE' in record:
                                ltp = record['CE'].get('lastPrice', 0)
                                if ltp > 0:
                                    print(f"[OK] NSE: {strike} CE = Rs.{ltp:.2f}")
                                    return float(ltp)
                            elif option_type == 'PE' and 'PE' in record:
                                ltp = record['PE'].get('lastPrice', 0)
                                if ltp > 0:
                                    print(f"[OK] NSE: {strike} PE = Rs.{ltp:.2f}")
                                    return float(ltp)
            
            return 0
            
        except Exception as e:
            # Don't print error - fall through silently
            return 0
    
    def _fetch_from_xts(self, strike: int, option_type: str) -> float:
        """Fetch real option price from XTS API"""
        if not self.xts_token:
            return 0
        
        try:
            # Subscribe to instrument first (required for paid API)
            self.xts_subscribe_instrument(strike, option_type)
            
            # Format with expiry: "NIFTY 30JAN26 25300 CE"
            from datetime import datetime, timedelta
            today = datetime.now()
            days_ahead = 3 - today.weekday()  # Thursday
            if days_ahead <= 0:
                days_ahead += 7
            next_thursday = today + timedelta(days_ahead)
            expiry_str = next_thursday.strftime("%d%b%y").upper()
            
            option_symbol = f"NIFTY {expiry_str} {strike} {option_type}"
            
            # XTS API to get quotes
            url = f"{XTS_BASE_URL}/instruments/quotes"
            headers = {
                'Authorization': self.xts_token,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'instruments': [{
                    'exchangeSegment': 2,  # NFO (options)
                    'exchangeInstrumentID': option_symbol
                }],
                'xtsMessageCode': 1502,  # Quote request
                'publishFormat': 'JSON'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=5, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                
                # XTS returns nested JSON string in listQuotes
                if 'result' in data and 'listQuotes' in data['result']:
                    quotes_list = data['result']['listQuotes']
                    
                    if quotes_list and len(quotes_list) > 0:
                        # Parse the nested JSON string
                        quote_str = quotes_list[0]
                        if quote_str:  # Check if not empty
                            try:
                                quote_data = json.loads(quote_str)
                                
                                # Extract LTP from Touchline
                                if 'Touchline' in quote_data:
                                    ltp = quote_data['Touchline'].get('LastTradedPrice', 0)
                                    if ltp > 0:
                                        print(f"[OK] XTS: {option_symbol} = Rs.{ltp}")
                                        return float(ltp)
                            except json.JSONDecodeError:
                                print(f"[WARNING] Failed to parse quote JSON for {option_symbol}")
            
            return 0
            
        except Exception as e:
            print(f"[WARNING] XTS fetch error for {strike} {option_type}: {str(e)}")
            return 0
    
    def _estimate_option_price(self, strike: int, option_type: str, 
                               spot_price: float, atr: float) -> float:
        """
        Estimate option price using improved approximation
        Based on real market observations and volatility
        
        Formula:
        - ITM (In The Money): Intrinsic Value + Time Value
        - ATM (At The Money): Time Value (based on volatility)
        - OTM (Out The Money): Small time value
        """
        
        # Calculate intrinsic value
        if option_type == 'CE':
            intrinsic = max(0, spot_price - strike)
        else:  # PE
            intrinsic = max(0, strike - spot_price)
        
        # Calculate distance from ATM
        distance_from_atm = abs(spot_price - strike)
        
        # Improved time value calculation
        # Based on observed NIFTY option premiums
        # ATM options typically trade at 0.3-0.6% of spot price for intraday
        atm_base_premium = spot_price * 0.004  # 0.4% of spot as base (~100 Rs for 25000 spot)
        
        # Adjust based on volatility (ATR)
        # Higher ATR = Higher premiums
        # Note: 5-min candle ATR is much smaller than daily ATR
        # Minimum multiplier of 1.0 ensures base premium is not reduced below market reality
        volatility_multiplier = max(1.0, (atr / 50) * 1.2)  # Normalized to ATR=50 baseline
        
        # Calculate time value based on moneyness
        if distance_from_atm <= 50:  # ATM or very close (within 1 strike)
            # ATM options have maximum time value
            decay_factor = 1.0 - (distance_from_atm / 50) * 0.3
            time_value = atm_base_premium * volatility_multiplier * decay_factor
        elif distance_from_atm <= 150:  # Near money (1-3 strikes)
            # Gradual decay
            decay_factor = 0.7 - ((distance_from_atm - 50) / 100) * 0.4
            time_value = atm_base_premium * volatility_multiplier * decay_factor
        elif distance_from_atm <= 300:  # Slightly OTM/ITM (3-6 strikes)
            # Faster decay
            decay_factor = 0.3 - ((distance_from_atm - 150) / 150) * 0.2
            time_value = atm_base_premium * volatility_multiplier * decay_factor
        else:  # Deep OTM/ITM (>6 strikes away)
            # Minimal time value
            time_value = max(5, atm_base_premium * 0.1)
        
        # Total option price
        option_price = intrinsic + time_value
        
        # Round to nearest 0.05 (NSE tick size)
        option_price = round(option_price * 20) / 20
        
        # Minimum premium Rs.5
        return max(5.0, option_price)
    
    def get_option_greeks(self, strike: int, option_type: str, 
                         spot_price: float, price: float) -> dict:
        """Calculate approximate option Greeks"""
        
        distance = abs(spot_price - strike)
        
        # Delta: Rate of change of option price vs spot price
        # ATM ≈ 0.5, ITM → 1.0, OTM → 0.0
        if option_type == 'CE':
            if spot_price > strike:
                delta = 0.5 + min(0.5, distance / (strike * 0.02))
            else:
                delta = 0.5 - min(0.5, distance / (strike * 0.02))
        else:  # PE
            if spot_price < strike:
                delta = -(0.5 + min(0.5, distance / (strike * 0.02)))
            else:
                delta = -(0.5 - min(0.5, distance / (strike * 0.02)))
        
        return {
            'delta': round(delta, 2),
            'premium': price
        }
    
    def get_atm_strike(self, spot_price: float) -> int:
        """Calculate ATM strike (rounded to nearest 50)"""
        return round(spot_price / 50) * 50
    
    def get_option_data(self, signal_type: str, spot_price: float, atr: float = 50) -> dict:
        """
        Get complete option data for trading
        
        Args:
            signal_type: 'CALL' or 'PUT'
            spot_price: Current NIFTY spot price
            atr: Average True Range for volatility
        
        Returns:
            dict with strike, option_type, premium, stop_loss, target
        """
        # Calculate ATM strike
        atm_strike = self.get_atm_strike(spot_price)
        
        # Determine option type (CE for CALL signal, PE for PUT signal)
        option_type = 'CE' if signal_type == 'CALL' else 'PE'
        
        # Fetch option premium
        premium = self.get_option_ltp(atm_strike, option_type, spot_price, atr)
        
        # Calculate stop loss and target for options (based on premium)
        # SL: 30% loss from entry premium
        # Target: 50% profit from entry premium
        stop_loss = premium * 0.70  # 30% loss
        target = premium * 1.50     # 50% profit
        
        return {
            'strike': atm_strike,
            'option_type': option_type,
            'premium': premium,
            'stop_loss': stop_loss,
            'target': target,
            'spot_price': spot_price
        }


# Example usage
if __name__ == "__main__":
    fetcher = OptionPriceFetcher()
    
    spot = 25254.30
    atr = 50
    
    print(f"Spot: {spot}")
    print(f"ATR: {atr}")
    print("="*70)
    print()
    
    # Test different strikes
    strikes = [25150, 25200, 25250, 25300, 25350]  # 2 OTM, ATM, 2 ITM for CE
    
    print("CALL OPTIONS (CE):")
    print("-"*70)
    print(f"{'Strike':<10} {'Premium':<12} {'Intrinsic':<12} {'Time Value':<12} {'Cost (65 qty)'}")
    print("-"*70)
    
    for strike in strikes:
        ce_price = fetcher.get_option_ltp(strike, 'CE', spot, atr)
        intrinsic = max(0, spot - strike)
        time_val = ce_price - intrinsic
        cost = ce_price * 65
        
        status = "ITM" if spot > strike else "ATM" if spot == strike else "OTM"
        print(f"{strike:<10} Rs.{ce_price:<9.2f} Rs.{intrinsic:<9.2f} Rs.{time_val:<9.2f} Rs.{cost:>10,.2f}  [{status}]")
    
    print()
    print("PUT OPTIONS (PE):")
    print("-"*70)
    print(f"{'Strike':<10} {'Premium':<12} {'Intrinsic':<12} {'Time Value':<12} {'Cost (65 qty)'}")
    print("-"*70)
    
    for strike in strikes:
        pe_price = fetcher.get_option_ltp(strike, 'PE', spot, atr)
        intrinsic = max(0, strike - spot)
        time_val = pe_price - intrinsic
        cost = pe_price * 65
        
        status = "ITM" if spot < strike else "ATM" if spot == strike else "OTM"
        print(f"{strike:<10} Rs.{pe_price:<9.2f} Rs.{intrinsic:<9.2f} Rs.{time_val:<9.2f} Rs.{cost:>10,.2f}  [{status}]")
    
    print()
    print("="*70)
    print("ATM OPTION SUMMARY:")
    atm_strike = round(spot / 50) * 50
    ce = fetcher.get_option_ltp(atm_strike, 'CE', spot, atr)
    pe = fetcher.get_option_ltp(atm_strike, 'PE', spot, atr)
    print(f"Strike: {atm_strike}")
    print(f"CE Premium: Rs.{ce:.2f} | Total Cost: Rs.{ce*65:,.2f}")
    print(f"PE Premium: Rs.{pe:.2f} | Total Cost: Rs.{pe*65:,.2f}")
