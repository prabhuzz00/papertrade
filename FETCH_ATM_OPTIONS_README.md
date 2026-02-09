# Fetch ATM Option LTP Script

## Overview

`fetch_atm_option_ltp.py` - A script to fetch Last Traded Price (LTP) of Put and Call options at ATM strike using XTS API.

## Features

- **Login to XTS API**: Authenticates with XTS MarketData API
- **Fetch NIFTY Spot Price**: Gets real-time NIFTY 50 index price
- **Calculate ATM Strike**: Automatically rounds to nearest 50
- **Get Expiry Dates**: Fetches available option expiry dates from XTS
- **Fetch Option Prices**: Retrieves LTP for both CE (Call) and PE (Put) at ATM strike

## XTS API Endpoints Used

Based on the provided XTS documentation:

### 1. GetExpiryDate
```
GET /instruments/instrument/expiryDate
Parameters:
- exchangeSegment: 2 (NFO)
- series: FUTIDX
- symbol: NIFTY
```

### 2. GetOptionSymbol
Format: `NIFTY {expiryDate} {strike} {optionType}`
Example: `NIFTY 24FEB26 25850 CE`

### 3. GetQuotes
```
POST /instruments/quotes
Headers:
- Authorization: <token>
Parameters:
- instruments: [{exchangeSegment, exchangeInstrumentID}]
- xtsMessageCode: 1502
- publishFormat: JSON
```

## Usage

### Basic Usage

```python
python fetch_atm_option_ltp.py
```

### Sample Output

```
[INFO] Logging in to XTS API...
[OK] Login successful
[TOKEN] eyJhbGciOiJIUzI1NiIsInR5cCI6Ik...

======================================================================
ATM OPTION LTP FETCHER
======================================================================

[INFO] Fetching NIFTY spot price...
[OK] NIFTY Spot: Rs.25867.30
[STRIKE] ATM Strike: 25850

[INFO] Fetching expiry dates...
[OK] Available expirations: ['2026-02-24T14:30:00', ...]
[EXPIRY] Using expiry: 24FEB26

[INFO] Fetching ATM Call (25850 CE)...
[OK] Call (25850 CE):
   LTP: Rs.150.25
   Bid: Rs.148.50 | Ask: Rs.152.00

[INFO] Fetching ATM Put (25850 PE)...
[OK] Put (25850 PE):
   LTP: Rs.145.75
   Bid: Rs.144.00 | Ask: Rs.147.50

======================================================================
SUMMARY
======================================================================
Spot Price: Rs.25867.30
ATM Strike: 25850
Expiry: 24FEB26
Call LTP: Rs.150.25
Put LTP: Rs.145.75
======================================================================

[OK] Results saved to atm_option_ltp.json
```

### Output File

Results are saved to `atm_option_ltp.json`:

```json
{
  "spot_price": 25867.30,
  "atm_strike": 25850,
  "expiry": "24FEB26",
  "call": {
    "symbol": "NIFTY 24FEB26 25850 CE",
    "type": "CE",
    "strike": 25850,
    "ltp": 150.25,
    "bid": 148.50,
    "ask": 152.00,
    "status": "success"
  },
  "put": {
    "symbol": "NIFTY 24FEB26 25850 PE",
    "type": "PE",
    "strike": 25850,
    "ltp": 145.75,
    "bid": 144.00,
    "ask": 147.50,
    "status": "success"
  }
}
```

## Using as a Module

You can import and use the fetcher in your own code:

```python
from fetch_atm_option_ltp import ATMOptionFetcher

# Create fetcher instance
fetcher = ATMOptionFetcher()

# Login
if fetcher.login():
    # Fetch ATM options
    result = fetcher.fetch_atm_options()
    
    if result:
        print(f"Spot: {result['spot_price']}")
        print(f"ATM Strike: {result['atm_strike']}")
        print(f"Call LTP: {result['call']['ltp']}")
        print(f"Put LTP: {result['put']['ltp']}")
```

### Fetch Specific Strike

```python
fetcher = ATMOptionFetcher()
fetcher.login()

# Get current spot
spot = fetcher.get_nifty_spot()

# Get expiry list
expiry_dates = fetcher.get_option_expiry_dates()
expiry = fetcher._parse_expiry_date(expiry_dates[0])

# Fetch specific strike (e.g., 26000)
ce_data = fetcher.get_option_ltp(26000, 'CE', expiry)
pe_data = fetcher.get_option_ltp(26000, 'PE', expiry)

print(f"26000 CE LTP: Rs.{ce_data['ltp']:.2f}")
print(f"26000 PE LTP: Rs.{pe_data['ltp']:.2f}")
```

## Configuration

The script uses credentials from `xts_config.py`:

```python
XTS_BASE_URL = 'https://eztrade.wealthdiscovery.in/apimarketdata'
XTS_APP_KEY = 'your_app_key'
XTS_SECRET_KEY = 'your_secret_key'
XTS_SOURCE = 'WebAPI'
```

## Important Notes

### 1. Real-time Data Availability

XTS API may require:
- **Active market hours**: Option quotes are only available during trading hours (9:15 AM - 3:30 PM IST)
- **WebSocket connection**: For continuous real-time data, WebSocket subscription might be needed
- **Subscription**: Some endpoints require prior subscription to instruments

### 2. Instrument Symbol Format

XTS uses specific format for option symbols:
- Format: `NIFTY {DD}{MMM}{YY} {STRIKE} {CE/PE}`
- Example: `NIFTY 24FEB26 25850 CE`
- Strike: Must be valid traded strike (typically multiples of 50 for NIFTY)

### 3. Exchange Segments

- **1**: NSE (Cash) - for NIFTY index
- **2**: NFO (Derivatives) - for NIFTY options

### 4. API Rate Limits

Be mindful of API rate limits. The script uses reasonable timeouts and spacing.

## Troubleshooting

### Login Fails

```
[ERROR] Login failed: Invalid credentials
```

**Solution**: Check `xts_config.py` credentials

### Quote Data Not Available

```
[ERROR] Could not fetch real-time data
```

**Possible reasons**:
1. Market is closed
2. Option contract doesn't exist or is not traded
3. WebSocket subscription required
4. Instrument ID format incorrect

**Solution**: 
- Verify market hours
- Check if the strike price is valid
- Try using the NSE option chain API as fallback (see `option_price_fetcher.py`)

### SSL Certificate Errors

The script disables SSL verification (`verify=False`) for XTS API, which is common with broker APIs.

## Related Files

- `option_price_fetcher.py` - More comprehensive option price fetcher with NSE fallback
- `test_atm_options.py` - Test script for ATM option prices
- `xts_config.py` - XTS API credentials configuration
- `test_xts_api.py` - XTS API testing utilities

## XTS API Documentation

- **GetExpiryDate**: Get available expiry dates for futures/options
- **GetFutureSymbol**: Get future contract symbols
- **GetOptionSymbol**: Get option contract symbols
- **GetQuotes**: Fetch real-time quotes for instruments

## License

Part of the Prediction Model v3 trading system.
