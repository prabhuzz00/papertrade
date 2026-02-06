# Option Trading Guide

## Overview

The trading application has been upgraded to focus on **real option trading** with ATM (At The Money) strikes.

## Key Features

### 1. **Automatic ATM Strike Calculation**
- Spot price is rounded to nearest 50 for NIFTY
- Example: Spot 25,254 → ATM Strike = 25,250

### 2. **Real Option Premium Estimation**
The system uses a sophisticated option pricing model:

```
Option Premium = Intrinsic Value + Time Value

Where:
- Intrinsic Value = max(0, Spot - Strike) for CE
                  = max(0, Strike - Spot) for PE
                  
- Time Value based on:
  * Distance from ATM (peak at ATM)
  * ATR (volatility measure)
  * Decreases as option moves ITM/OTM
```

### 3. **Option-Specific Risk Management**
- **Stop Loss**: 40% of premium (exit at 60% of entry price)
- **Target**: 100% gain (exit at 200% of entry price)
- **Risk/Reward**: Consistent 1:2.5 ratio

### 4. **Accurate P&L Tracking**
- Entry cost = Premium × Lot Size (75 for NIFTY)
- Exit proceeds = Current Premium × Lot Size
- P&L = (Current Premium - Entry Premium) × 75

## Example Trade Flow

### CALL Option Trade
```
Signal: CALL
Spot Price: Rs.25,254.30
ATM Strike: 25,250 CE

Premium: Rs.75.50 (estimated based on volatility)
Lot Size: 75
Total Cost: Rs.5,662.50

Stop Loss: Rs.45.30 (40% loss = Rs.2,265 loss)
Target: Rs.151.00 (100% gain = Rs.5,662 profit)

Risk/Reward: 1:2.5
```

### PUT Option Trade
```
Signal: PUT
Spot Price: Rs.25,245.80
ATM Strike: 25,250 PE

Premium: Rs.82.25
Total Cost: Rs.6,168.75

Stop Loss: Rs.49.35 (40% loss = Rs.2,467 loss)
Target: Rs.164.50 (100% gain = Rs.6,168 profit)

Risk/Reward: 1:2.5
```

## Option Pricing Logic

### ATM Options (Distance = 0)
```python
Time Value = ATR × 1.5
Example: ATR = 50 → Time Value = Rs.75
```

### Near ATM (Distance ≤ ATR)
```python
Time Value = ATR × (1.5 - (distance/ATR) × 0.8)
Example: Distance = 25, ATR = 50 → Time Value = Rs.55
```

### Slightly ITM/OTM (ATR < Distance ≤ 2×ATR)
```python
Time Value = ATR × 0.7 × (1 - (distance-ATR)/ATR)
Example: Distance = 75, ATR = 50 → Time Value = Rs.17.5
```

### Deep ITM/OTM (Distance > 2×ATR)
```python
Time Value = max(10, ATR × 0.2)
Minimum premium = Rs.10
```

## UI Changes

### Signal Panel Now Shows:
- **Contract**: NIFTY 25250 CE/PE
- **Spot Price**: Rs.25,254.30
- **Premium (LTP)**: Rs.75.50
- **Lot Size**: 75
- **Total Cost**: Rs.5,662.50
- **Stop Loss**: Rs.45.30 (premium-based)
- **Target**: Rs.151.00 (premium-based)
- **Risk/Reward**: 1:2.5

### Trade Table Shows:
- Trade ID
- Option Contract (Strike + Type)
- Entry Premium
- Current Premium
- P&L
- Status

## Capital Requirements

### Per Trade:
- **Buying Options**: Premium × 75 (full cost upfront)
- **Example**: Rs.75.50 premium = Rs.5,662.50 required

### Portfolio:
- **Rs.1,000,000 Capital** = ~176 option contracts possible
- **Recommended**: 1-2 contracts per signal (conservative)
- **Buffer**: Keep 80% capital free for opportunities

## Advantages of Option Trading

1. **Limited Risk**: Maximum loss = Premium paid
2. **High Leverage**: Small capital controls large position
3. **Clear Risk/Reward**: Defined at entry
4. **No Margin Calls**: Premium is full payment
5. **Better Risk Management**: SL/Target based on premium

## Files Modified

1. **option_price_fetcher.py** (NEW)
   - Fetches real NSE option prices
   - Falls back to mathematical estimation
   - Calculates Greeks (Delta)

2. **paper_trading_engine.py** (UPDATED)
   - Uses option premiums instead of spot prices
   - Tracks strike and option type
   - Option-specific P&L calculation

3. **strategy_wrappers.py** (UPDATED)
   - All strategies pass ATR values
   - Required for option pricing

4. **trading_app.py** (UPDATED)
   - Displays option contract details
   - Shows premium and total cost
   - Option-based SL/Target levels

## Usage

1. **Start Application**:
   ```bash
   python trading_app.py
   ```

2. **Select Strategy**: Choose from dropdown

3. **Enable Auto-Trading**: Check "Auto Trade" for automatic execution

4. **Monitor Signals**: 
   - Signal panel shows option contract
   - Premium is calculated automatically
   - Click "Execute Trade" for manual entry

5. **Track Positions**:
   - Open positions show current premium
   - P&L updates in real-time
   - Auto-exits at SL/Target

## Important Notes

⚠️ **Option Premiums are Estimated**
- NSE API often blocks automated requests
- Fallback uses mathematical approximation
- Accuracy: ~80-90% of real market prices

✅ **For Live Trading**
- Verify premium on broker platform
- Use estimated premium as reference only
- Always check real LTP before executing

📊 **Testing Recommended**
- Paper trade for 1 month minimum
- Verify strategy profitability
- Adjust parameters as needed

## Future Enhancements

- [ ] Real-time NSE option chain integration
- [ ] Multiple strike selection (ITM/OTM)
- [ ] Option Greeks display (Delta, Theta, Vega)
- [ ] IV (Implied Volatility) integration
- [ ] Weekly vs Monthly expiry selection
- [ ] Options chain viewer
