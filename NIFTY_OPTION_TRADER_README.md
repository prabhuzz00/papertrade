# NIFTY Options Paper Trading Platform

Automated option trading system that executes NIFTY option trades based on signals with automatic risk management.

## Features

✅ **Automatic Option Selection**
- Fetches ATM strike price based on current NIFTY spot
- Uses XTS GetOptionSymbol API for accurate instrument IDs
- Gets real-time option LTP via XTS Quotes API

✅ **Risk Management (1:2 Risk:Reward)**
- Stop Loss: 10% below entry premium
- Target: 20% above entry premium (1:2 ratio)
- Automatic position sizing based on 2% capital risk per trade

✅ **Trade Execution**
- CALL signal → Buy ATM CE option
- PUT signal → Buy ATM PE option
- Uses weekly expiry for better liquidity

✅ **Real-time Monitoring**
- Tracks all open positions
- Automatic SL/Target hit detection
- Updates P&L in real-time

## Quick Start

### Basic Usage

```python
from nifty_option_trader import NiftyOptionTrader

# Initialize trader with Rs. 1 lakh capital
trader = NiftyOptionTrader(initial_capital=100000)

# Execute option trade on CALL signal
trade = trader.execute_signal('CALL', 'Bollinger+MACD')

# Update positions (checks SL/Target)
trader.update_positions()

# Display dashboard
trader.display_dashboard()

# Save trades
trader.save_trades()
```

### Integration with Signal Generation

```python
from nifty_option_trader import NiftyOptionTrader

# Initialize
trader = NiftyOptionTrader(initial_capital=100000)

# Your signal generation logic
def get_market_signal():
    # Your strategy logic here
    # Returns: 'CALL', 'PUT', or None
    pass

# Main trading loop
while True:
    signal = get_market_signal()
    
    if signal in ['CALL', 'PUT']:
        # Execute option trade
        trader.execute_signal(signal, 'MyStrategy')
    
    # Update all open positions
    trader.update_positions()
    
    # Save state
    trader.save_trades()
    
    time.sleep(60)  # Check every minute
```

## Trade Execution Example

When a CALL signal is detected:

```
======================================================================
SIGNAL DETECTED: CALL from Bollinger+MACD
======================================================================
NIFTY Spot: Rs.25,867.30
Expiry: 10Feb2026
ATM Strike: 25850
Option: NIFTY 10FEB2026 CE 25850 (ID: 42538)
Entry Premium: Rs.77.70

Trade Setup:
  Quantity: 195 (3 lots)
  Investment: Rs.15,151.50
  Stop Loss: Rs.69.93 (-10%)
  Target: Rs.93.24 (+20%)
  Risk: Rs.1,515.15
  Potential Reward: Rs.3,030.30
  Risk:Reward = 1:2

✓ TRADE EXECUTED: OPT-0001
  Remaining Capital: Rs.84,848.50
```

## Risk Management Details

### Position Sizing
- **Risk Per Trade**: 2% of capital
- **Calculation**: Based on stop loss to entry premium difference
- **Lot Sizing**: Automatically calculates number of lots needed

Example with Rs. 1 lakh capital:
- Risk per trade: Rs. 2,000
- If SL risk is Rs. 7.77 per share (10% of Rs. 77.70)
- With lot size 65: Risk per lot = Rs. 505
- Number of lots = 2000 / 505 ≈ 3 lots
- Total quantity = 3 × 65 = 195 shares

### Stop Loss & Target
- **Stop Loss**: 10% below entry premium (Rs. 77.70 → Rs. 69.93)
- **Target**: 20% above entry premium (Rs. 77.70 → Rs. 93.24)
- **Risk:Reward**: 1:2 ratio

### Capital Management
- Investment deducted when trade opens
- Investment + P&L returned when trade closes
- Tracks available capital for new trades

## API Integration

Uses XTS Market Data API for:
1. **NIFTY Spot Price** - Instrument ID: 26000
2. **Option Expiry Dates** - GetExpiryDate endpoint
3. **Option Details** - GetOptionSymbol endpoint (returns numeric IDs)
4. **Real-time LTP** - Quotes endpoint

All API calls are authenticated and use proper error handling.

## Dashboard

View comprehensive trading statistics:

```
======================================================================
NIFTY OPTIONS TRADING DASHBOARD
======================================================================
Initial Capital:  Rs.100,000.00
Current Capital:  Rs.84,848.50
Total Capital:    Rs.100,000.00
Total P&L:        Rs.0.00 (0.00%)
Realized P&L:     Rs.0.00
Unrealized P&L:   Rs.0.00
----------------------------------------------------------------------
Total Trades:     1
Open Positions:   1
Closed Trades:    0
Winning Trades:   0
Losing Trades:    0
Win Rate:         0.00%
======================================================================

OPEN POSITIONS:
----------------------------------------------------------------------
OPT-0001 | CE 25850 | Entry: Rs.77.70 | Current: Rs.77.70 | P&L: Rs.0.00
----------------------------------------------------------------------
```

## Methods Reference

### `execute_signal(signal_type, strategy)`
Execute an option trade based on signal.
- **signal_type**: 'CALL' or 'PUT'
- **strategy**: Strategy name (for tracking)
- **Returns**: OptionTrade object or None

### `update_positions()`
Update all open positions with current market prices.
Automatically closes positions when SL or Target hit.

### `close_position_manual(trade_id)`
Manually close a specific position.
- **trade_id**: Trade ID (e.g., 'OPT-0001')
- **Returns**: True if successful

### `get_statistics()`
Get comprehensive trading statistics.
- **Returns**: Dict with all metrics

### `save_trades(filename)`
Save all trades to JSON file.
- **filename**: Default 'nifty_option_trades.json'

### `load_trades(filename)`
Load trades from JSON file.
- **filename**: Default 'nifty_option_trades.json'

### `display_dashboard()`
Print comprehensive trading dashboard to console.

## Configuration

Modify trader settings:

```python
trader = NiftyOptionTrader(initial_capital=100000)

# Change defaults
trader.lot_size = 65  # NIFTY lot size
trader.risk_reward_ratio = 2  # 1:2 ratio
trader.risk_percent = 2  # Risk 2% per trade
```

## Trade History

All trades are saved to `nifty_option_trades.json`:

```json
{
  "initial_capital": 100000,
  "current_capital": 84848.5,
  "open_positions": [{
    "trade_id": "OPT-0001",
    "signal_type": "CALL",
    "instrument_type": "CE",
    "strike_price": 25850,
    "spot_price": 25867.3,
    "entry_premium": 77.7,
    "quantity": 195,
    "stop_loss": 69.93,
    "target": 93.24,
    "instrument_id": 42538,
    "expiry": "10Feb2026"
  }],
  "closed_trades": []
}
```

## Testing

Run the test script:

```bash
python nifty_option_trader.py
```

This will:
1. Login to XTS API
2. Execute a sample CALL trade
3. Display dashboard
4. Save trades to file

## Requirements

- Python 3.7+
- XTS API credentials in `xts_config.py`
- Active XTS account with NFO options access
- Packages: `requests`, `urllib3`

## Notes

⚠️ **Paper Trading Only**: This is for simulation/backtesting
⚠️ **Market Hours**: XTS API requires market hours for real-time data
⚠️ **Risk Warning**: Options trading involves significant risk

## Benefits vs Futures Trading

| Feature | Options | Futures |
|---------|---------|---------|
| Risk | Limited to premium paid | Unlimited |
| Capital | Lower (only premium) | Higher (margin) |
| Leverage | High | Moderate |
| Time Decay | Affects premium | No time decay |
| Stop Loss | Premium-based | Spot price-based |

## Next Steps

1. ✅ Integrate with existing strategy signals
2. ✅ Add GUI for monitoring
3. ✅ Implement trailing stop loss
4. ✅ Add multiple timeframe analysis
5. ✅ Generate performance reports

---

**Happy Trading!** 🚀

For issues or questions, check the XTS API documentation or verify your account has NFO options data access.
