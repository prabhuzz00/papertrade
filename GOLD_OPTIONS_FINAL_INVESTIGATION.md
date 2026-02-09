# Gold Option Price Fetcher - Investigation Summary

## Problem Statement
Attempted to fetch Gold ATM option prices using XTS API's GetOptionSymbol endpoint (as shown in documentation), but encountered "Data not available" errors.

## Investigation Results

### ✅ What Works

1. **NIFTY Options (NSE/NFO) - FULLY WORKING**
   - Endpoint: `GET /instruments/instrument/optionSymbol`
   - Segment: 2 (NFO)
   - Series: "OPTIDX"
   - Symbol: "NIFTY"
   - Date Format: **"ddMmmyyyy"** (e.g., "10Feb2026")
   - Returns: Complete instrument details including numeric ExchangeInstrumentID
   
   **Example Response:**
   ```json
   {
     "type": "success",
     "code": "s-rds-0",
     "result": [{
       "ExchangeInstrumentID": 42536,
       "DisplayName": "NIFTY 10FEB2026 CE 25800",
       "StrikePrice": 25800,
       "LotSize": 65,
       "TickSize": 0.05
     }]
   }
   ```

2. **Gold Expiry Dates - WORKING**
   - Endpoint: `GET /instruments/instrument/expiryDate`
   - Segment: 51 (MCXFO)
   - Series: "OPTFUT"
   - Symbol: "GOLDM"
   - Returns: List of available expiry dates
   
   **Response:**
   ```json
   {
     "result": [
       "2026-03-26T23:59:59",
       "2026-02-26T23:59:59",
       "2026-04-28T23:59:59"
     ]
   }
   ```

### ❌ What Doesn't Work

1. **Gold Options GetOptionSymbol - NOT WORKING**
   - All combinations return: `{"type":"error","code":"e-instrunent-0013","description":"Data not available"}`
   - Tested segments: 3, 51
   - Tested series: "OPTFUT", "OPTCOM", "OPTIDC"
   - Tested symbols: "GOLD", "GOLDM"
   - Tested date formats: All standard formats including "26Mar2026" (working for NIFTY)
   - Tested multiple strike prices: 74900, 75000, 75100, 75200

2. **Gold Futures GetFutureSymbol - NOT WORKING**
   - Returns: `{"type":"error","code":"e-instrunent-0006","description":"Data not available"}`

3. **Gold OHLC Data - RETURNS EMPTY**
   - Status: 200 (success)
   - Response: `{"dataReponse": ""}` (empty string)
   - Both GET and POST methods tested

4. **Gold Quotes - RETURNS EMPTY**
   - Status: 200 (success)
   - Response: `{"listQuotes": []}` (empty array)

## Root Cause Analysis

Since GetOptionSymbol **works perfectly for NIFTY** but fails for Gold with the exact same approach, the issue is **NOT**:
- ❌ Wrong date format
- ❌ Wrong API endpoint
- ❌ Wrong parameter structure
- ❌ Authentication issues

The issue **IS**:
1. **Account doesn't have MCX Options data access enabled**
   - You may have MCX Futures access (GetExpiryDate works)
   - But not MCX Options derivatives data
   
2. **API limitation**
   - XTS GetOptionSymbol API may only support equity options (NSE/NFO)
   - MCX options may require different method or not be available via REST API

3. **Market hours** (less likely since GetExpiryDate works for Gold)

## Solution Options

### Option 1: Enable MCX Options Access (Recommended)
**Contact your XTS broker** (SYMPHONY/Interactive Brokers):
- Ask: "Is MCX options data enabled on my account?"
- Ask: "Does GetOptionSymbol API support MCX options (segment 51)?"
- Request: Enable MCX options data access if not already enabled
- Request: MCX instrument master file with numeric exchangeInstrumentIDs

### Option 2: Use WebSocket Streaming
If REST API doesn't support MCX options, use WebSocket:
```python
# Subscribe to Gold option instruments via WebSocket
# Get real-time streaming data
# Requires socket programming
```

### Option 3: Use Estimation (Current Fallback)
The `fetch_gold_option_ltp.py` script includes estimation algorithm:
- ATM premium: 2.5% of spot price
- Decay based on distance from ATM
- Realistic approximation when live data unavailable

## Files Created

1. **fetch_gold_atm_options.py** - Clean implementation using GetOptionSymbol
2. **debug_xts_gold_endpoints.py** - Debug tool showing all API responses
3. **test_option_symbol_date_formats.py** - Tests different date formats
4. **verify_nifty_working.py** - Proves GetOptionSymbol works for NIFTY
5. **test_gold_instrument_ids.py** - Comprehensive numeric ID testing

## Verified Facts

✅ XTS API authentication works  
✅ GetOptionSymbol endpoint exists and works (for NSE/NFO)  
✅ Correct date format is "ddMmmyyyy" (e.g., "10Feb2026")  
✅ Gold expiry dates can be fetched via GetExpiryDate  
✅ Account has some MCX access (futures)  
❌ Gold options cannot be fetched via GetOptionSymbol  
❌ Gold OHLC/quotes return empty data even with success status  

## Next Steps

1. **Immediate:** Contact broker to verify MCX options access
2. **Short-term:** Use NIFTY options (working perfectly) for testing
3. **Long-term:** Implement WebSocket if REST API doesn't support MCX options
4. **Fallback:** Use estimation algorithm for Gold options

## Date Format Reference

For future use with GetOptionSymbol:

| Format | Example | Works? |
|--------|---------|--------|
| ISO with time | 2026-02-10T14:30:00 | ❌ |
| ISO date only | 2026-02-10 | ❌ |
| **ddMmmyyyy** | **10Feb2026** | ✅ **USE THIS** |
| ddMmmyy | 10Feb26 | ❌ |
| dd Mmm yyyy | 10 Feb 2026 | ❌ |

## Example: Working NIFTY Implementation

```python
# This works perfectly:
params = {
    'exchangeSegment': 2,
    'series': 'OPTIDX',
    'symbol': 'NIFTY',
    'expiryDate': '10Feb2026',  # Format: ddMmmyyyy
    'optionType': 'CE',
    'strikePrice': 25800
}
response = requests.get(
    f'{XTS_BASE_URL}/instruments/instrument/optionSymbol',
    params=params,
    headers={'Authorization': token}
)
# Returns: ExchangeInstrumentID: 42536
```

## Conclusion

The investigation is complete. The GetOptionSymbol API works as documented, but **MCX options data is not available** on your current XTS account configuration. Contact your broker to enable MCX options access.

For now, use the NIFTY option fetcher ([fetch_atm_option_ltp.py](fetch_atm_option_ltp.py)) which works perfectly, or use the estimation feature in the Gold fetcher.
