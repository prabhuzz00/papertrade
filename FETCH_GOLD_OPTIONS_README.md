# Fetch Gold Option LTP Script

## Overview

`fetch_gold_option_ltp.py` - A script to fetch Last Traded Price (LTP) of Put and Call options for Gold at ATM strike using XTS API.

## Features

- **Login to XTS API**: Authenticates with XTS MarketData API
- **Fetch Gold Spot/Future Price**: Gets real-time Gold price from MCX
- **Calculate ATM Strike**: Automatically rounds to nearest 100 (Gold strike intervals)
- **Get Expiry Dates**: Fetches available option expiry dates from XTS
- **Fetch Option Prices**: Retrieves LTP for both CE (Call) and PE (Put) at ATM strike
- **Multi-Segment Support**: Tries MCX segments 3 and 51 automatically

## Gold Trading Details

### Exchange
- **MCX** (Multi Commodity Exchange)
- Segment 3 or 51 in XTS API

### Gold Contracts
- **GOLD**: Standard Gold (100 grams)
- **GOLDM**: Gold Mini (10 grams) - More liquid, typically used for options
- **GOLDPETAL**: Gold Petal (1 gram)

### Option Symbol Format
```
GOLDM {expiryDate} {strike} {optionType}
```
Example: `GOLDM 05MAR26 75000 CE`

### Strike Prices
- Typically in multiples of **100 rupees** per 10 grams
- Example strikes: 74500, 74600, 74700, 74800, 74900, 75000, 75100, etc.

### Expiry Dates
- Gold options typically expire on the **5th of every month**
- Monthly contracts available

## Usage

### Basic Usage

```bash
python fetch_gold_option_ltp.py
```

### Sample Output

```
[INFO] Logging in to XTS API...
[OK] Login successful
[TOKEN] eyJhbGciOiJIUzI1NiIsInR5cCI6Ik...

======================================================================
TRYING MCX SEGMENT 3
======================================================================

======================================================================
GOLD ATM OPTION LTP FETCHER
======================================================================

[INFO] Fetching Gold price from MCX (Segment 3)...
[OK] Found MCX Gold: Rs.75250.00
[OK] Gold Price: Rs.75250.00 per 10g
[STRIKE] ATM Strike: 75200

[INFO] Fetching expiry dates...
[OK] Available expirations: ['05MAR26', '05APR26', '05MAY26']
[EXPIRY] Using expiry: 05MAR26

[INFO] Fetching ATM Call (75200 CE)...
[OK] Call (75200 CE):
   LTP: Rs.850.50
   Bid: Rs.845.00 | Ask: Rs.855.00

[INFO] Fetching ATM Put (75200 PE)...
[OK] Put (75200 PE):
   LTP: Rs.780.25
   Bid: Rs.775.00 | Ask: Rs.785.00

======================================================================
SUMMARY
======================================================================
Gold Price: Rs.75250.00 per 10g
ATM Strike: 75200
Expiry: 05MAR26
Exchange: MCX (Segment 3)
Call LTP: Rs.850.50
Put LTP: Rs.780.25
======================================================================

[OK] Results saved to gold_option_ltp_segment_3.json
[SUCCESS] Found working segment: 3
```

### Output File

Results are saved to `gold_option_ltp_segment_3.json` or `gold_option_ltp_segment_51.json`:

```json
{
  "commodity": "GOLD",
  "spot_price": 75250.00,
  "atm_strike": 75200,
  "expiry": "05MAR26",
  "exchange": "MCX",
  "segment": 3,
  "call": {
    "symbol": "GOLDM 05MAR26 75200 CE",
    "type": "CE",
    "strike": 75200,
    "ltp": 850.50,
    "bid": 845.00,
    "ask": 855.00,
    "status": "success"
  },
  "put": {
    "symbol": "GOLDM 05MAR26 75200 PE",
    "type": "PE",
    "strike": 75200,
    "ltp": 780.25,
    "bid": 775.00,
    "ask": 785.00,
    "status": "success"
  }
}
```

## Using as a Module

You can import and use the fetcher in your own code:

```python
from fetch_gold_option_ltp import GoldOptionFetcher

# Create fetcher instance
fetcher = GoldOptionFetcher()

# Login
if fetcher.login():
    # Fetch ATM options
    result = fetcher.fetch_atm_options(segment=3)
    
    if result:
        print(f"Gold Price: {result['spot_price']}")
        print(f"ATM Strike: {result['atm_strike']}")
        print(f"Call LTP: {result['call']['ltp']}")
        print(f"Put LTP: {result['put']['ltp']}")
```

### Fetch Specific Strike

```python
fetcher = GoldOptionFetcher()
fetcher.login()

# Get current Gold price
gold_price = fetcher.get_gold_spot()

# Get expiry list
expiry_dates = fetcher.get_option_expiry_dates(segment=3)
expiry = fetcher._parse_expiry_date(expiry_dates[0])

# Fetch specific strike (e.g., 75500)
ce_data = fetcher.get_option_ltp(75500, 'CE', expiry, segment=3)
pe_data = fetcher.get_option_ltp(75500, 'PE', expiry, segment=3)

print(f"75500 CE LTP: Rs.{ce_data['ltp']:.2f}")
print(f"75500 PE LTP: Rs.{pe_data['ltp']:.2f}")
```

### Try Different Gold Contracts

```python
# For standard Gold (100g)
fetcher.gold_symbol = "GOLD"
fetcher.gold_option_symbol = "GOLD"

# For Gold Mini (10g) - default and recommended
fetcher.gold_symbol = "GOLD"
fetcher.gold_option_symbol = "GOLDM"

# For Gold Petal (1g)
fetcher.gold_symbol = "GOLDPETAL"
fetcher.gold_option_symbol = "GOLDPETAL"
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

### 1. MCX Trading Hours

**Regular Market Hours**: 10:00 AM - 11:30 PM IST (extended hours for Gold)
- Morning Session: 10:00 AM - 5:00 PM
- Evening Session: 5:00 PM - 11:30 PM

Gold options are only available during trading hours.

### 2. Contract Specifications

**Gold Mini (GOLDM)** - Most liquid for options:
- Lot Size: 10 grams
- Quotation: INR per 10 grams
- Tick Size: Re. 1
- Strike Interval: Rs. 100

**Standard Gold**:
- Lot Size: 100 grams
- Quotation: INR per 10 grams
- Less liquid for options

### 3. MCX Segments

The script tries multiple segments:
- **Segment 3**: MCX Commodity Derivatives
- **Segment 51**: MCXSX (MCX Stock Exchange)
- **Segment 4/5**: Alternative MCX segments

### 4. Expiry Calculation

MCX Gold options typically expire on:
- **5th of every month** at 11:30 PM IST
- If 5th is a holiday, previous trading day

The script automatically calculates the next available expiry.

### 5. Strike Price Intervals

Gold strikes are typically in multiples of:
- **Rs. 100** for Gold Mini (GOLDM)
- **Rs. 100** for Standard Gold

ATM is calculated by rounding spot price to nearest 100.

## Troubleshooting

### Login Fails

```
[ERROR] Login failed: Invalid credentials
```

**Solution**: Check `xts_config.py` credentials.

### Gold Price Not Available

```
[WARNING] Could not fetch real-time Gold price, using estimate
```

**Possible reasons**:
1. Market is closed (before 10:00 AM or after 11:30 PM)
2. Incorrect segment ID
3. Instrument ID not found

**Solution**: 
- Verify MCX trading hours
- Check if Gold futures are trading
- Try running during market hours

### Quote Data Not Available

```
[ERROR] Could not fetch real-time data
```

**Possible reasons**:
1. Market is closed
2. Option contract doesn't exist or isn't traded
3. Strike price out of range
4. WebSocket subscription required

**Solution**: 
- Verify MCX option trading hours
- Check if strike price is valid (near ATM)
- Ensure contract is liquid (use GOLDM, not standard GOLD)
- Run during active trading hours

### All Segments Fail

If both segment 3 and 51 fail, you may need to:
1. Check XTS Master Instrument list
2. Verify exact segment IDs for your broker
3. Contact XTS support for correct MCX mapping

## Comparing with NIFTY Options

| Feature | NIFTY Options | Gold Options |
|---------|---------------|--------------|
| Exchange | NSE/NFO | MCX |
| Segment | 2 | 3 or 51 |
| Strike Interval | 50 points | Rs. 100 |
| Expiry | Weekly (Thursday) | Monthly (5th) |
| Trading Hours | 9:15 AM - 3:30 PM | 10:00 AM - 11:30 PM |
| Underlying | Index | Commodity Future |
| Lot Size | Fixed lots | Weight-based (10g) |

## Related Files

- `fetch_atm_option_ltp.py` - NIFTY option fetcher (similar structure)
- `test_xts_commodities.py` - XTS commodity testing utilities
- `xts_config.py` - XTS API credentials configuration
- `trading_app.py` - Main trading application with Gold support

## XTS API Endpoints Used

1. **Login**: `/auth/login`
2. **GetExpiryDate**: `/instruments/instrument/expiryDate`
3. **GetQuotes**: `/instruments/quotes`
4. **OHLC**: `/instruments/ohlc` (fallback)
5. **Subscription**: `/instruments/subscription`

## Future Enhancements

- [ ] Add support for Crude Oil options
- [ ] Add support for Silver options  
- [ ] WebSocket streaming for real-time updates
- [ ] Historical option price data
- [ ] Implied volatility calculation
- [ ] Option Greeks calculation

## License

Part of the Prediction Model v3 trading system.
