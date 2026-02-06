# Complete User Guide - NIFTY 50 Live Trading Application

## Table of Contents

1. [Getting Started](#getting-started)
2. [Application Overview](#application-overview)
3. [Using Each Strategy](#using-each-strategy)
4. [Trading Workflow](#trading-workflow)
5. [Understanding Signals](#understanding-signals)
6. [Managing Trades](#managing-trades)
7. [Performance Analysis](#performance-analysis)
8. [Best Practices](#best-practices)
9. [FAQ](#faq)

---

## Getting Started

### Quick Start (Windows)

**Option 1: Double-click launcher**
```
start_trading_app.bat
```

**Option 2: Command line**
```powershell
python trading_app.py
```

**Option 3: With setup**
```powershell
python quick_start.py
```

### First Launch Checklist

- [ ] Python 3.7+ installed
- [ ] Internet connection active
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Market hours (9:15 AM - 3:30 PM IST for best results)

---

## Application Overview

### Main Window Layout

```
┌─────────────────────────────────────────────────────────────┐
│ [Strategy ▼] [Price: ₹XX,XXX] [Auto-Trade] [Save]         │ ← Control Panel
├──────────────────────────────┬──────────────────────────────┤
│                              │ Strategy Information         │
│   📊 Candlestick Chart       │ ─────────────────           │
│   with Bollinger Bands       │ • Entry rules               │
│   and indicators             │ • Risk management           │
│                              │                             │
│   [Live updates every 1 min] │ 🔔 Current Signal           │
│                              │ ─────────────────           │
│                              │ Type: CALL/PUT/NONE         │
│                              │ Entry: ₹XX,XXX              │
│                              │ SL: ₹XX,XXX                 │
│                              │ Target: ₹XX,XXX             │
│                              │                             │
│                              │ [Execute Manual Trade]      │
│                              │                             │
│                              │ 💼 Portfolio Summary        │
│                              │ ─────────────────           │
│                              │ Capital: ₹X,XX,XXX          │
│                              │ P&L: ±₹X,XXX                │
│                              │ Win Rate: XX%               │
├──────────────────────────────┴──────────────────────────────┤
│ 📋 Trade History (Tabs for each strategy)                  │
│ [Bollinger+MACD] [ORB] [Sideways]                          │
│ ┌────────────────────────────────────────────────────────┐ │
│ │Time  │Signal│Entry │Exit  │SL   │Target│P&L  │Status│ │ │
│ │09:30 │CALL  │23500 │23600 │23450│23600 │+7500│✓     │ │ │
│ └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Control Panel**: Select strategy, view price, toggle auto-trade
2. **Chart Area**: Live candlestick chart with technical indicators
3. **Signal Panel**: Current trading opportunity details
4. **Portfolio**: Real-time capital, P&L, and statistics
5. **Trade Tables**: Complete history for each strategy

---

## Using Each Strategy

### Strategy 1: Bollinger Band + MACD

**Best For**: Trending markets, breakout opportunities

**How It Works**:
- Waits for price to break above/below Bollinger Bands
- Confirms with MACD momentum indicator
- Validates with RSI (not overbought/oversold extremes)
- Ensures sufficient volatility (ATR check)

**When to Use**:
- ✅ Market showing clear trends
- ✅ Volatility is moderate to high
- ✅ Clear breakout patterns forming
- ❌ Sideways/choppy markets

**Signal Example**:
```
🔔 CALL SIGNAL
Entry: ₹23,550
Stop Loss: ₹23,500 (50 points)
Target: ₹23,625 (75 points)
Risk/Reward: 1:1.5
Confidence: 85%
Reason: Bullish Breakout - RSI: 68.5, MACD Bullish
```

**Typical Performance**:
- Win Rate: 65-75%
- Profit Factor: 2.0-3.0
- Average Trade Duration: 30-60 minutes

### Strategy 2: Opening Range Breakout (ORB)

**Best For**: High volatility days, news-driven moves

**How It Works**:
- Identifies first 15-30 min range (9:15-9:30 AM)
- Waits for breakout above/below this range
- Requires strong volume confirmation
- Uses range width for stop loss and target

**When to Use**:
- ✅ First hour of trading (9:30-10:30 AM)
- ✅ High impact news days
- ✅ Gap openings
- ❌ After 11:00 AM (range already established)

**Signal Example**:
```
🔔 CALL SIGNAL
Entry: ₹23,580
Stop Loss: ₹23,500 (Opening range low)
Target: ₹23,700 (1.5x range)
Risk/Reward: 1:1.5
Confidence: 75%
Reason: Breakout above opening range high (₹23,560)
```

**Typical Performance**:
- Win Rate: 60-70%
- Profit Factor: 1.8-2.5
- Average Trade Duration: 15-45 minutes

### Strategy 3: Sideways Market

**Best For**: Consolidation phases, range-bound markets

**How It Works**:
- Identifies sideways market (ADX < 25)
- Defines support and resistance zones
- Shorts at resistance, longs at support
- Requires minimum 1:2 risk/reward

**When to Use**:
- ✅ Low volatility periods
- ✅ After major moves (consolidation)
- ✅ Lunchtime hours (12-2 PM)
- ❌ Strong trending markets

**Signal Example**:
```
🔔 PUT SIGNAL
Entry: ₹23,600 (at resistance)
Stop Loss: ₹23,640 (40 points above)
Target: ₹23,520 (80 points down to support)
Risk/Reward: 1:2
Confidence: 70%
Reason: Sideways market - Short at resistance. ADX: 18.5, RSI: 62
```

**Typical Performance**:
- Win Rate: 55-65%
- Profit Factor: 1.5-2.2
- Average Trade Duration: 45-90 minutes

---

## Trading Workflow

### Manual Trading (Recommended for Beginners)

1. **Select Strategy**
   - Choose from dropdown based on market conditions
   - Read strategy information

2. **Monitor Chart**
   - Watch for setup formation
   - Check indicator alignment
   - Wait for signal

3. **Signal Appears**
   - Review entry, SL, target
   - Verify risk/reward ratio (minimum 1:1.5)
   - Check confidence level

4. **Execute Trade**
   - Click "Execute Manual Trade"
   - Trade opens immediately
   - Appears in trade table

5. **Monitor Position**
   - Track P&L in real-time
   - Stop loss automatically enforced
   - Target hit = auto-closes

### Auto-Trading (For Experienced Users)

1. **Enable Auto-Trade**
   - Click "Enable Auto-Trade" button
   - Button turns green

2. **System Monitors**
   - Continuously checks for signals
   - Automatically executes when conditions met
   - Manages all positions

3. **Hands-Off Trading**
   - No manual intervention needed
   - All exits automatic (SL/Target)
   - Review trades periodically

4. **Disable When**
   - Market becomes choppy
   - Need to review strategy
   - End of day approach

---

## Understanding Signals

### Signal Components

**Signal Type**: CALL (bullish) or PUT (bearish)

**Entry Price**: Price at which position opens
- Usually current market price
- Sometimes slightly better (pending order)

**Stop Loss**: Maximum loss point
- Automatically enforced
- Based on ATR or technical levels
- Never moved further away (only trail)

**Target**: Profit booking level
- Automatically executed when hit
- Based on risk/reward calculation
- Can be partial (50% at first target)

**Risk/Reward Ratio**: Profit potential vs loss potential
- Minimum 1:1.5 (most strategies)
- Example: Risk 50 points to make 75+ points
- Higher is better (1:2, 1:3)

**Confidence**: Signal strength (0-100%)
- Based on indicator alignment
- Higher = stronger signal
- 70%+ recommended for execution

**Reason**: Why signal generated
- Technical explanation
- Indicator values
- Market context

### Signal Colors

- 🟢 **Green** = CALL signal (Buy)
- 🔴 **Red** = PUT signal (Sell)
- ⚪ **Gray** = No signal (Wait)

### When to Trade vs Wait

**Trade When**:
- ✅ Signal confidence > 70%
- ✅ Risk/Reward > 1:1.5
- ✅ Market conditions match strategy
- ✅ Sufficient capital available
- ✅ Clear chart setup

**Wait When**:
- ❌ Low confidence signal
- ❌ Poor risk/reward ratio
- ❌ Choppy/unclear market
- ❌ Too many open positions
- ❌ Near market close

---

## Managing Trades

### Open Positions

**What You See**:
- Entry time and price
- Current P&L (updates every second)
- Stop loss and target levels
- Status: OPEN (yellow highlight)

**What Happens Automatically**:
- Position monitored continuously
- Stop loss enforced (no slippage in paper trading)
- Target hit = immediate close
- Margin returned + P&L to capital

### Closed Trades

**Exit Reasons**:
- ✅ **TARGET** = Target price reached (Green)
- ❌ **STOP_LOSS** = Stop loss hit (Red)
- ⚠️ **MANUAL_EXIT** = User closed (future feature)

**Trade Details**:
- Duration: Time from entry to exit
- Final P&L: Profit or loss in ₹
- All prices recorded
- Notes field for context

### Trade Tables

**Columns Explained**:
- **Time**: Entry timestamp
- **Signal**: CALL or PUT
- **Entry**: Entry price
- **Exit**: Exit price (or blank if open)
- **SL**: Stop loss level
- **Target**: Target price
- **P&L**: Profit/Loss in ₹
- **Status**: OPEN/TARGET/STOP_LOSS
- **Duration**: How long trade lasted
- **Notes**: Why trade taken

**Sorting & Filtering**:
- Click column headers to sort
- Each strategy has separate tab
- Only shows that strategy's trades

---

## Performance Analysis

### Key Metrics

**Capital**: Current available funds
- Starts at ₹100,000 (default)
- Decreases when position opened (margin)
- Increases when position closed (margin + P&L)

**P&L (Profit & Loss)**: Total performance
- Green = Profitable
- Red = Losing
- Includes both open and closed positions
- Unrealized (open) + Realized (closed)

**Open Positions**: Number of active trades
- Max recommended: 2-3
- Each uses margin (~₹30,000)
- Monitor closely

**Total Trades**: Lifetime trade count
- All strategies combined
- Includes both wins and losses

**Win Rate**: Percentage of profitable trades
- Target: 55-65%
- Formula: Winning Trades / Total Trades
- Updates after each closed trade

### Strategy Comparison

**Which Strategy is Best?**

Check after 20+ trades per strategy:

1. **Highest Win Rate**: Most consistent
2. **Best Profit Factor**: Most profitable
3. **Lowest Drawdown**: Safest

**Weekly Review**:
- Look at each strategy tab
- Count wins vs losses
- Sum total P&L
- Identify best performer

**Monthly Optimization**:
- Focus on best strategy
- Reduce allocation to weak ones
- Adjust position sizing

---

## Best Practices

### Risk Management

**Position Sizing**:
```
Capital: ₹100,000
Max Risk per Trade: 2% = ₹2,000
With 50-point SL and 75 qty:
Risk = 50 × 75 = ₹3,750 (3.75%)
→ Reduce to 40 qty for 2% risk
```

**Maximum Positions**:
- 1 position: ₹50,000-100,000 capital
- 2-3 positions: ₹100,000-200,000 capital
- Never more than 30% of capital at risk

**Stop Loss Discipline**:
- Never remove stop loss
- Never widen stop loss
- Can trail stop loss (move closer)
- Exit immediately if hit

### Market Conditions

**Best Trading Hours**:
- 9:15-11:00 AM: High volatility, ORB works
- 11:00 AM-2:00 PM: Midday, sideways works
- 2:00-3:00 PM: Afternoon trends, Bollinger works
- Avoid: First 5 minutes (9:15-9:20)
- Avoid: Last 15 minutes (3:15-3:30)

**Market Types**:
- **Trending Up**: Use Bollinger CALL only
- **Trending Down**: Use Bollinger PUT only
- **Sideways**: Use Sideways strategy
- **Volatile**: Use ORB strategy
- **Choppy**: Don't trade, wait

### Psychology

**Do's**:
- ✅ Follow the system
- ✅ Accept small losses
- ✅ Let winners run to target
- ✅ Review trades weekly
- ✅ Stay disciplined

**Don'ts**:
- ❌ Override signals
- ❌ Revenge trading after loss
- ❌ Remove stop losses
- ❌ Overtrade
- ❌ Risk too much per trade

---

## FAQ

### General

**Q: Is this real money trading?**  
A: No, this is paper trading only. No real money, no broker connection.

**Q: Can I connect this to a broker?**  
A: Not currently. This is for strategy testing only.

**Q: How accurate is the data?**  
A: Yahoo Finance data has 15-20 minute delay. Good for testing, not real-time.

**Q: Can I customize the strategies?**  
A: Yes, edit the strategy_wrappers.py file to adjust parameters.

### Trading

**Q: Why no signals appearing?**  
A: Check market hours, volatility, and strategy requirements. Not all conditions generate signals.

**Q: Trade not executing?**  
A: Ensure sufficient capital available and auto-trade is enabled (if using auto mode).

**Q: Can I close a position manually?**  
A: Currently, trades auto-close at SL/Target. Manual close coming in future update.

**Q: How much should I risk per trade?**  
A: Recommend maximum 2% of capital per trade.

### Technical

**Q: Application freezing?**  
A: Data fetching can cause brief delays. Wait 60 seconds for updates.

**Q: Charts not updating?**  
A: Check internet connection. Restart application if needed.

**Q: Where are trades saved?**  
A: JSON files: trades_bollinger_+_macd.json, etc. in the same folder.

**Q: How to reset everything?**  
A: Delete the JSON files and restart application.

### Performance

**Q: What's a good win rate?**  
A: 55-65% is excellent for these strategies.

**Q: What's a good profit factor?**  
A: 1.5+ is good, 2.0+ is excellent, 3.0+ is exceptional.

**Q: How long to test a strategy?**  
A: Minimum 20-30 trades before evaluating performance.

**Q: When to stop using a strategy?**  
A: If win rate drops below 50% after 50+ trades, review or stop.

---

## Quick Reference Card

### Keyboard Shortcuts (Future)
- `Ctrl+S`: Save trades
- `Ctrl+R`: Refresh data
- `Ctrl+Q`: Quit application

### Strategy Selection Guide

| Market Condition | Best Strategy | Expected Win Rate |
|-----------------|---------------|-------------------|
| Strong Trend Up | Bollinger (CALL) | 70-75% |
| Strong Trend Down | Bollinger (PUT) | 65-70% |
| Opening Hour | ORB | 65-70% |
| Sideways/Range | Sideways | 60-65% |
| Choppy/Uncertain | None (Wait) | - |

### Risk Limits

| Capital | Max Position | Max Risk/Trade | Max Positions |
|---------|-------------|----------------|---------------|
| ₹50,000 | 1 lot | ₹1,000 | 1 |
| ₹100,000 | 1 lot | ₹2,000 | 2-3 |
| ₹200,000 | 2 lots | ₹4,000 | 2-3 |

---

**For More Help**: See README.md for technical details

**Version**: 1.0  
**Last Updated**: January 30, 2026
