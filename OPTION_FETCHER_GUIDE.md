# Option Price Fetcher - User Guide

## Quick Start

### ✅ For NIFTY Options (Working Perfectly)

```bash
python fetch_atm_option_ltp.py
```

**Output:**
- NIFTY spot price (live)
- ATM strike calculation
- Call and Put option LTP (live data)
- Saved to JSON file

**Status:** ✅ Fully functional with real-time data

---

### ⚠️ For Gold Options (Estimation Mode)

```bash
python fetch_gold_atm_options.py
```

**Output:**
- Gold spot price (estimated Rs.75,000)
- ATM strike calculation
- Call and Put option LTP (estimated at 2.5% ATM premium)
- Saved to `gold_atm_options_result.json`

**Status:** ⚠️ Estimation only - Real-time MCX options data not available

---

## Why Gold Options Don't Work

### Investigation Summary

After comprehensive testing, we discovered:

1. **GetOptionSymbol API works** ✅
   - Verified with NIFTY options
   - Returns complete instrument details including numeric IDs
   - Date format: `ddMmmyyyy` (e.g., "10Feb2026")

2. **Gold expiry dates work** ✅
   - GetExpiryDate returns available expiries
   - Segment 51, Series "OPTFUT", Symbol "GOLDM"

3. **Gold options return "Data not available"** ❌
   - All combinations tested
   - HTTP 400 error from GetOptionSymbol
   - OHLC and Quotes endpoints return empty data

### Root Cause

Your XTS account has:
- ✅ MCX Futures access (GetExpiryDate works)
- ❌ MCX Options data access (GetOptionSymbol fails)

**OR** the XTS API simply doesn't support MCX options via REST endpoints.

---

## Solutions

### Option 1: Enable MCX Options Access (Recommended)

Contact your XTS broker:

**Questions to ask:**
1. "Is MCX options data enabled on my account?"
2. "Does GetOptionSymbol API support MCX options (segment 51)?"
3. "Can you provide the MCX instrument master file with exchangeInstrumentIDs?"

**Action:** Request MCX options data access

### Option 2: Use During Market Hours

MCX Gold trading hours: **10:00 AM - 11:30 PM IST**

Try running during active trading when:
- Market is open
- Options have sufficient liquidity
- Real-time data might be available

### Option 3: WebSocket Streaming

If REST API doesn't support MCX options, use WebSocket:
- Subscribe to instrument streams
- Real-time tick data
- Requires implementing XTS WebSocket client

### Option 4: Use Estimation (Current)

The scripts provide realistic estimation:
- ATM premium: 2.5% of spot price
- Distance-based decay for OTM strikes
- Reasonable approximation for strategy testing

---

## What Was Tested

### ✅ Working Components

| Component | Status | Details |
|-----------|--------|---------|
| XTS Login | ✅ Working | Token authentication successful |
| NIFTY GetOptionSymbol | ✅ Working | Returns instrument ID, LTP available |
| NIFTY options data | ✅ Working | Real-time data flowing |
| Gold GetExpiryDate | ✅ Working | Returns expiry dates for GOLDM |
| Date format discovery | ✅ Complete | Format is "ddMmmyyyy" |

### ❌ Not Working Components

| Component | Status | Details |
|-----------|--------|---------|
| Gold GetOptionSymbol | ❌ Fails | HTTP 400 "Data not available" |
| Gold GetFutureSymbol | ❌ Fails | HTTP 400 "Data not available" |
| Gold OHLC endpoint | ❌ Empty | Returns `{"dataReponse": ""}` |
| Gold Quotes endpoint | ❌ Empty | Returns `{"listQuotes": []}` |

---

## Files Reference

### Working Scripts

| File | Purpose | Status |
|------|---------|--------|
| `fetch_atm_option_ltp.py` | NIFTY ATM options | ✅ Working |
| `fetch_gold_atm_options.py` | Gold ATM options | ⚠️ Estimation only |

### Debug/Test Scripts

| File | Purpose |
|------|---------|
| `debug_xts_gold_endpoints.py` | Shows all API responses |
| `test_option_symbol_date_formats.py` | Tests date format combinations |
| `verify_nifty_working.py` | Proves GetOptionSymbol works |
| `test_gold_instrument_ids.py` | Tests numeric ID ranges |

### Documentation

| File | Content |
|------|---------|
| `GOLD_OPTIONS_FINAL_INVESTIGATION.md` | Complete investigation summary |
| `OPTION_PRICING_TECHNICAL.md` | Technical details |
| `FETCH_GOLD_OPTIONS_README.md` | Previous documentation |

---

## API Reference

### GetOptionSymbol Endpoint (Documented)

**URL:** `GET /instruments/instrument/optionSymbol`

**Parameters:**
```json
{
  "exchangeSegment": 2,
  "series": "OPTIDX",
  "symbol": "NIFTY",
  "expiryDate": "10Feb2026",
  "optionType": "CE",
  "strikePrice": 25800
}
```

**Response:**
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

---

## Next Steps

1. **For immediate trading:** Use NIFTY options (working perfectly)
2. **For Gold options:** Contact broker for MCX options access
3. **For development:** Use estimation mode for strategy testing
4. **For production:** Implement WebSocket streaming if needed

---

## Example Usage

### NIFTY Options (Real Data)

```python
from fetch_atm_option_ltp import ATMOptionFetcher

fetcher = ATMOptionFetcher()
result = fetcher.fetch_atm_options()

print(f"Spot: {result['spot_price']}")
print(f"Call LTP: {result['call']['ltp']}")  # Real-time data ✅
print(f"Put LTP: {result['put']['ltp']}")    # Real-time data ✅
```

### Gold Options (Estimated Data)

```python
from fetch_gold_atm_options import GoldATMOptionFetcher

fetcher = GoldATMOptionFetcher()
result = fetcher.fetch_atm_options()

print(f"Spot: {result['spot_price']}")
print(f"Call LTP: {result['call']['ltp']}")  # Estimated ⚠️
print(f"Put LTP: {result['put']['ltp']}")    # Estimated ⚠️
print(f"Note: {result['note']}")
```

---

## Support

**Issues Found:**
- MCX options data not available via GetOptionSymbol API
- Account may need MCX options access enabled
- Alternative: WebSocket streaming for real-time MCX data

**Contact:**
- Your XTS broker for account access
- XTS API support for endpoint availability
- Check during MCX market hours (10 AM - 11:30 PM IST)

---

## Summary

✅ **NIFTY Options:** Fully functional  
⚠️ **Gold Options:** Estimation only (broker contact needed)  
📚 **Documentation:** Complete investigation documented  
🔧 **Tools:** Debug scripts available for troubleshooting  

Use NIFTY for live option trading. Use Gold estimation for strategy development until broker enables MCX options data access.
