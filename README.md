# NIFTY 50 Live Trading Application

A comprehensive PyQt5-based paper trading application that integrates three powerful trading strategies for NIFTY 50 index options.

## Features

✅ **Three Integrated Strategies:**
1. **Bollinger Band + MACD Breakout** - High-probability breakout trading
2. **Opening Range Breakout (ORB)** - First 15-30 min range trading
3. **Sideways Market Strategy** - Range-bound market exploitation

✅ **Real-time Market Data:**
- Live 5-minute candle updates from Yahoo Finance
- Interactive candlestick charts with technical indicators
- Bollinger Bands, MACD, RSI, ATR visualization

✅ **Paper Trading Engine:**
- Simulate trades without real money
- Automatic stop loss and target management
- Position tracking with P&L calculation
- Separate trade lists for each strategy

✅ **Advanced Features:**
- Auto-trading mode (automatic signal execution)
- Manual trade execution
- Trade history persistence (save/load)
- Real-time portfolio statistics
- Win rate and profit factor tracking

## Installation

### 1. Install Python Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Verify Installation

```powershell
python -c "import PyQt5; import pyqtgraph; import yfinance; print('All dependencies installed successfully!')"
```

## Usage

### Start the Application

```powershell
python trading_app.py
```

### Application Interface

#### Control Panel (Top)
- **Strategy Selector**: Choose from 3 strategies
- **Current Price**: Live NIFTY 50 price
- **Auto-Trade Toggle**: Enable/disable automatic trading
- **Save Trades**: Save all trade history

#### Chart Area (Left)
- Real-time candlestick chart
- Technical indicators overlay
- Auto-updates every minute

#### Signal Panel (Right)
- **Strategy Information**: Current strategy details
- **Current Signal**: Live trading signals (CALL/PUT/None)
- **Signal Details**: Entry, SL, Target, Risk/Reward
- **Manual Trade Button**: Execute trade manually
- **Portfolio Summary**: Capital, P&L, positions, win rate

#### Trade Tables (Bottom)
- Separate tabs for each strategy
- Complete trade history
- Entry/Exit prices, P&L, duration
- Status tracking (OPEN/TARGET/STOP_LOSS)

## Strategy Details

### 1. Bollinger Band + MACD Strategy

**Entry Rules:**
- **CALL**: Close > BB Upper + MACD > Signal + RSI 50-85
- **PUT**: Close < BB Lower + MACD < Signal + RSI 15-50

**Risk Management:**
- Stop Loss: ATR-based
- Target: 1.5x Stop Loss
- Minimum Risk/Reward: 1:1.5

**Best For:** Trending markets with clear breakouts

### 2. Opening Range Breakout (ORB)

**Entry Rules:**
- First 15-30 min sets opening range
- **CALL**: Breakout above range high with volume
- **PUT**: Breakdown below range low with volume

**Risk Management:**
- Stop Loss: Opposite side of range
- Target: 1.5x range width
- Mean reversion on strong opening moves

**Best For:** High volatility days, news-driven moves

### 3. Sideways Market Strategy

**Entry Rules:**
- ADX < 25 (sideways market confirmation)
- **PUT**: Short at resistance with RSI > 55
- **CALL**: Long at support with RSI < 45

**Risk Management:**
- Stop Loss: Beyond resistance/support + 1 ATR
- Target: Opposite side of range
- Minimum Risk/Reward: 1:2

**Best For:** Consolidation phases, low volatility

## Trading Workflow

### Auto-Trading Mode

1. Select strategy from dropdown
2. Click "Enable Auto-Trade"
3. Application monitors market automatically
4. Executes trades when signals appear
5. Manages stop loss and targets automatically

### Manual Trading Mode

1. Select strategy
2. Monitor signal panel for opportunities
3. Review signal details (entry, SL, target)
4. Click "Execute Manual Trade" when ready
5. Trade appears in strategy-specific table

## Trade Management

### Monitoring Positions

- **Open Positions**: Highlighted in yellow
- **Profitable Exits**: Green background
- **Loss Exits**: Red background
- **Real-time P&L**: Updates every second

### Exit Conditions

Trades automatically exit when:
- Target price reached ✅
- Stop loss hit ❌
- Manual close (coming in future update)

### Trade History

Each strategy maintains separate trade list:
- `trades_bollinger_+_macd.json`
- `trades_opening_range_breakout.json`
- `trades_sideways_market.json`

Auto-saved on application close or manual save.

## Risk Management

### Position Sizing

- **Lot Size**: 75 shares (NIFTY 50 standard)
- **Margin Required**: ~20% of position value
- **Default Capital**: ₹100,000

### Risk Guidelines

- Maximum 2-3 concurrent positions
- Never risk more than 2% per trade
- Use stop losses religiously
- Review win rate weekly

### Recommended Capital Allocation

| Capital | Lots/Trade | Max Positions |
|---------|-----------|---------------|
| ₹50,000 | 1 lot | 1 |
| ₹100,000 | 1 lot | 2-3 |
| ₹200,000 | 2 lots | 2-3 |

## Performance Tracking

### Key Metrics

- **Win Rate**: % of profitable trades
- **Profit Factor**: Gross profit / Gross loss
- **Average Win/Loss**: Points per trade
- **Total P&L**: Realized + Unrealized

### Strategy Optimization

Review weekly:
1. Which strategy performs best?
2. What market conditions suit each?
3. Adjust position sizing based on results

## Troubleshooting

### No Data Loading

```
Error: No data downloaded
```

**Solution:** Check internet connection, verify Yahoo Finance is accessible

### Application Won't Start

```
ModuleNotFoundError: No module named 'PyQt5'
```

**Solution:** Reinstall dependencies
```powershell
pip install -r requirements.txt --upgrade
```

### Slow Chart Updates

**Solution:** Reduce data fetching frequency in `trading_app.py` line 71
```python
self.msleep(60000)  # Change to 120000 for 2-min updates
```

### Trade Not Executing

**Possible Causes:**
- Insufficient capital
- No valid signal
- Auto-trade disabled

**Solution:** Check portfolio summary, ensure capital available

## File Structure

```
prediction model v3/
├── trading_app.py              # Main application
├── strategy_wrappers.py        # Strategy implementations
├── paper_trading_engine.py     # Trading engine
├── predictioncandle.py         # Original BB+MACD strategy
├── opening-range-breakout-fno.py  # Original ORB strategy
├── sideways.py                 # Original sideways strategy
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── trades_*.json              # Trade history files (auto-generated)
```

## Safety Features

- **Paper Trading Only**: No real money at risk
- **Automatic Stop Loss**: Enforced on every trade
- **Position Limits**: Margin-based position sizing
- **Data Validation**: Checks for valid signals before trading
- **Trade Logging**: Complete history preserved

## Future Enhancements

- [ ] Manual position close button
- [ ] Multi-timeframe analysis
- [ ] Alert notifications
- [ ] Backtesting on historical data
- [ ] Strategy performance comparison
- [ ] Export trades to Excel
- [ ] Mobile app integration

## Support

For issues or questions:
1. Check troubleshooting section
2. Review code comments
3. Test with individual strategy files first

## Disclaimer

⚠️ **IMPORTANT**: This is a paper trading application for educational purposes only. 

- Does NOT connect to any broker
- Does NOT execute real trades
- Does NOT guarantee profits
- Past performance does NOT predict future results

Always test strategies thoroughly before considering live trading.

## License

MIT License - Free for personal and educational use

---

**Happy Paper Trading! 📈**
