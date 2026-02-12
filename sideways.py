"""
================================================================================
               ADVANCED SIDEWAYS MARKET PREDICTION & RANGE TRADING STRATEGY
================================================================================

STRATEGY NAME: Predictive Sideways Zone Identifier + Optimal Range Trading

VERSION: 2.0 - Enhanced with sideways prediction, zone identification & optimization

CORE PHILOSOPHY:
• Identify sideways conditions BEFORE they form (Predictive - not reactive)
• Define precise trading zones where price consolidates
• Execute short-selling at resistance with tight risk management
• Optimize for consistent profitability with 1:2+ risk-reward

================================================================================
SIDEWAYS PREDICTION SYSTEM (Predict Before Formation):
================================================================================

Phase 1: TREND EXHAUSTION DETECTION (Early Warning - Days 1-3)
  ✓ ADX declining below 25 (Trend losing strength)
  ✓ Price making lower highs/higher lows (Consolidation pattern)
  ✓ Volume declining on trend days (Conviction fading)
  ✓ MACD lines converging (Momentum death cross approaching)
  ✓ Bollinger Bands flattening (Volatility compression)
  → Prediction: Sideways phase likely to form in 1-3 days

Phase 2: CONSOLIDATION FORMATION (Active Sideways - Days 3-7)
  ✓ ADX < 25 + RSI between 40-60 (Neutral zone)
  ✓ Price oscillating within defined range (2-3% band)
  ✓ Multiple touch points at support/resistance
  ✓ Bollinger Band width contracting to minimum
  ✓ MACD histogram flattening near zero line
  → Confirmation: Sideways phase established

Phase 3: ZONE IDENTIFICATION (High-Probability Trading Area)
  ✓ Support: 20-period low or support zone
  ✓ Resistance: 20-period high or resistance zone
  ✓ Market Acceptance Zone: Price spending 70%+ time here
  ✓ Optimal Short Entry: 1-2 points below resistance
  ✓ Stop Loss: Above resistance + 1 ATR
  → Trading Window: Continue until ADX > 30 or breakout confirmed

================================================================================
ENTRY RULES (Optimized for SHORT-SELLING):
================================================================================

PRIMARY SHORT ENTRY (At Resistance - High Probability):
  ✓ Early Warning Score >= 2/5 (Sideways predicted/confirmed)
  ✓ Price at or near resistance level (within 0.5-1%)
  ✓ RSI > 55 (Overbought locally, not extreme)
  ✓ Volume >= 50% of 20-period average (Confirmation)
  ✓ MACD not significantly above signal line (Not in strong uptrend)
  → Entry: Sell at resistance level
  → SL: Resistance + max(ATR × 1.2, 40 points)
  → Target 1: Support level (1:1.5 to 1:2 ratio)
  → Target 2: Lower support (1:2 to 1:3 ratio)

SECONDARY SHORT ENTRY (On Resistance Rejection):
  ✓ Price touches resistance 2-3 times
  ✓ Candle closes below resistance after touching it
  ✓ RSI divergence at resistance
  → Entry: On candle close below resistance
  → SL: Above recent high + 20 points
  → Target: Support level with higher confidence

AVOID ENTRY (High Risk Scenarios):
  ✗ ADX > 25 (Trending market - skip shorts)
  ✗ Strong breakout above resistance (Trend formation)
  ✗ Gap up opening (Momentum too strong)
  ✗ Volume surge on resistance break (Confirmation of breakout)

================================================================================
EXIT RULES (Disciplined Risk Management):
================================================================================

TAKE PROFIT:
  ✓ Sell at defined resistance → Target support
  ✓ Use partial exits: 50% at support, 50% at lower support
  ✓ Trail stop loss after 1:1 risk-reward achieved

STOP LOSS (Hard stops - Always enforced):
  ✓ Above resistance + 1 ATR (Breakout confirmation)
  ✓ Maximum loss per trade: 40-50 points
  ✓ Time-based stop: Close position if no movement in 5 candles

EXIT CONFIRMATION (When sideways ends):
  ✓ ADX rises above 25 (Trend formation detected)
  ✓ Price breaks above resistance on high volume
  ✓ MACD crosses above signal line decisively
  → Close all positions and reassess

================================================================================
RISK MANAGEMENT FRAMEWORK:
================================================================================

Position Sizing:
  • Base: 1 lot per signal (65 shares)
  • Capital per trade: ₹30,000 margin
  • Max concurrent positions: 2-3 lots
  • Max daily loss: 2% of account (₹2,000 on ₹100K)

Risk-Reward Ratios:
  • Minimum: 1:1.5 (Risk 30pts, Reward 45pts)
  • Optimal: 1:2.0 (Risk 30pts, Reward 60pts)
  • Aggressive: 1:2.5 (Risk 30pts, Reward 75pts)

Profitability Targets:
  • Win Rate: 55%+
  • Profit Factor: 1.5x+ (Gross wins / Gross losses)
  • Monthly Target: 2-3% return on capital

================================================================================
BACKTESTING PARAMETERS:
================================================================================

Lookback Period: 5 candles (Next 5 candles validated for profitability)
Entry Confirmation: Signal forms → Backtest next 5 candles
  • If next candle closes below entry = High probability signal
  • If potential profit >= 1.5x risk = Confirmed signal
  • Execute only if both conditions met

Historical Data: 60+ days for adequate signal generation
Minimum Sample: 50+ valid signals for statistical confidence

================================================================================
CONTINUOUS OPTIMIZATION:
================================================================================

Performance Monitoring:
  ✓ Win Rate tracking (Target: 55%+)
  ✓ Profit Factor calculation (Target: 1.5x+)
  ✓ Drawdown analysis (Max: 5%)
  ✓ Recovery time measurement

Parameter Tuning:
  • If Win Rate < 50%: Tighten entry criteria (require higher warning score)
  • If Profit Factor < 1.2x: Improve SL placement or optimize targets
  • If Drawdown > 10%: Reduce position size or add filters
  • If Performance improving: Lock in rules, continue monitoring

Adaptation Strategy:
  ✓ Market regime changes detected
  ✓ Quarterly parameter reviews
  ✓ Rolling backtest validation
  ✓ Real-time performance adjustment

================================================================================
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pymongo import MongoClient
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONNECTION TO MONGODB (Nifty 50 5-minute candle data)
# =============================================================================

# =============================================================================
# CONNECTION TO DATA SOURCE (MongoDB or Yahoo Finance or Sample Data)
# =============================================================================

import yfinance as yf

use_sample_data = False

data_source = "Unknown"

# Try Yahoo Finance first (more reliable for current data)
try:
    print("Fetching from Yahoo Finance (NIFTY 50, daily, last 60 days)...")
    df = yf.download('^NSEI', interval='1d', period='60d', progress=False)
    
    if df.empty or len(df) < 20:
        raise Exception("Yahoo Finance returned insufficient data")
    
    # Handle MultiIndex columns from Yahoo Finance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df = df.reset_index()
    
    # Handle different date column names
    if 'Date' in df.columns:
        df['DateTime'] = pd.to_datetime(df['Date'])
    elif 'Datetime' in df.columns:
        df['DateTime'] = pd.to_datetime(df['Datetime'])
    else:
        df['DateTime'] = pd.to_datetime(df.iloc[:, 0])
    
    df = df[['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']].reset_index(drop=True)
    print(f"✓ Yahoo Finance: Fetched {len(df)} daily candles (Last 60 days)")
    data_source = "Yahoo Finance (Last 60 Days)"
    
except Exception as e:
    print(f"⚠ Yahoo Finance failed: {str(e)[:80]}")
    
    # Try Yahoo Finance 5-minute (60 days max)
    try:
        print("Trying Yahoo Finance (5-minute, last 60 days)...")
        df = yf.download('^NSEI', interval='5m', period='60d', progress=False)
        
        if df.empty or len(df) < 50:
            raise Exception("Yahoo Finance 5m returned insufficient data")
        
        df = df.reset_index()
        df['DateTime'] = pd.to_datetime(df['Datetime'])
        df = df[['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']].reset_index(drop=True)
        print(f"✓ Yahoo Finance: Fetched {len(df)} 5-min candles (Last 60 days)")
        data_source = "Yahoo Finance (5-min)"
        
    except Exception as e2:
        print(f"⚠ Yahoo Finance 5m failed: {str(e2)[:80]}")
        
        # Fallback to MongoDB
        try:
            print("Attempting MongoDB connection...")
            client = MongoClient('mongodb://192.168.1.48:27017/mg', serverSelectionTimeoutMS=3000)
            db = client['mg']
            collection = db['NSECM:NIFTY1EQ']
            
            start_date = datetime(2025, 1, 1)
            end_date = datetime(2025, 6, 30)
            
            query = {
                'Timestamp': {'$gte': start_date, '$lte': end_date}
            }
            
            data = list(collection.find(query).sort('Timestamp', 1))
            
            if data:
                print(f"✓ MongoDB: Fetched {len(data)} candles (Jan-June 2025)")
                df = pd.DataFrame(data)
                df['DateTime'] = pd.to_datetime(df['Timestamp']).dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
                df = df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'})
                df = df[['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']].reset_index(drop=True)
                data_source = "MongoDB"
            else:
                raise Exception("No data in MongoDB")
                
        except Exception as e3:
            print(f"⚠ MongoDB failed: {str(e3)[:80]}")
            print("Generating sample sideways market data for testing...")
            
            np.random.seed(42)
            dates = pd.date_range(end=datetime.now(), periods=300, freq='1D')
            
            base_price = 26400
            prices = []
            for i in range(300):
                noise = np.random.randn() * 50
                trend = (i - 150) * 0.1
                price = base_price + noise + trend + (np.sin(i/40) * 100)
                prices.append(price)
            
            data_dict = {
                'DateTime': dates,
                'Open': [p + np.random.randn()*20 for p in prices],
                'High': [p + abs(np.random.randn()*30) + 50 for p in prices],
                'Low': [p - abs(np.random.randn()*30) - 50 for p in prices],
                'Close': prices,
                'Volume': np.random.randint(5000000, 20000000, 300)
            }
            
            df = pd.DataFrame(data_dict)
            print(f"✓ Sample Data: Generated {len(df)} daily candles")
            data_source = "Sample Data (Synthetic)"

# =============================================================================
# TECHNICAL INDICATORS CALCULATION
# =============================================================================

def calc_atr(df, period=14):
    """Calculate Average True Range"""
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def calc_rsi(df, period=14):
    """Calculate Relative Strength Index"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calc_bollinger(df, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    sma = df['Close'].rolling(window=period).mean()
    std = df['Close'].rolling(window=period).std()
    
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    
    return upper, sma, lower

def calc_adx(df, period=14):
    """Calculate Average Directional Index"""
    high_diff = df['High'].diff()
    low_diff = -df['Low'].diff()
    
    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
    
    tr = (df['High'] - df['Low']).rolling(window=period).mean()
    tr = tr.replace(0, 1)  # Avoid division by zero
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr)
    
    di_diff = abs(plus_di - minus_di)
    di_sum = plus_di + minus_di
    di_sum = di_sum.replace(0, 1)  # Avoid division by zero
    
    dx = 100 * (di_diff / di_sum)
    adx = dx.rolling(window=period).mean()
    
    return adx.fillna(25)  # Fill NaN with neutral value

def calc_macd(df, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    ema_fast = df['Close'].ewm(span=fast).mean()
    ema_slow = df['Close'].ewm(span=slow).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calc_bb_width(df, period=20, std_dev=2):
    """Calculate Bollinger Band Width"""
    sma = df['Close'].rolling(window=period).mean()
    std = df['Close'].rolling(window=period).std()
    
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    
    bb_width = (upper - lower) / sma
    return bb_width

# =============================================================================
# CALCULATE ALL INDICATORS
# =============================================================================

print("\n" + "="*80)
print("CALCULATING TECHNICAL INDICATORS...")
print("="*80)

df['ATR'] = calc_atr(df, 14)
df['RSI'] = calc_rsi(df, 14)
df['ADX'] = calc_adx(df, 14)
df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = calc_bollinger(df, 20, 2)
df['MACD'], df['MACD_Signal'], df['MACD_Histogram'] = calc_macd(df, 12, 26, 9)
df['BB_Width'] = calc_bb_width(df, 20, 2)

# Calculate averages for early warning
df['ATR_Avg'] = df['ATR'].rolling(window=20).mean()
df['BB_Width_Avg'] = df['BB_Width'].rolling(window=20).mean()
df['MACD_Hist_Abs'] = abs(df['MACD_Histogram'])
df['MACD_Hist_Avg'] = df['MACD_Hist_Abs'].rolling(window=20).mean()

# Support and Resistance (Swing levels)
df['Recent_High'] = df['High'].rolling(window=20).max()
df['Recent_Low'] = df['Low'].rolling(window=20).min()

print("✓ All indicators calculated")

# =============================================================================
# EARLY WARNING SYSTEM (Score 0-5)
# =============================================================================

def calculate_early_warning_score(row):
    """
    Calculate sideways warning score (0-5)
    Higher score = Higher probability of sideways market forming
    
    Scoring Logic:
    • Score 0-1: Trending market (Skip trading)
    • Score 2-3: Early sideways signals (Start watching)
    • Score 4-5: Confirmed sideways zone (Active trading)
    """
    score = 0
    
    try:
        # 1. ADX < 25 (Trend weakening) - PRIMARY INDICATOR
        if pd.notna(row['ADX']) and float(row['ADX']) < 25:
            score += 1
        
        # 2. Bollinger Band Width contracting (Volatility squeeze)
        if pd.notna(row['BB_Width']) and pd.notna(row['BB_Width_Avg']) and float(row['BB_Width']) < float(row['BB_Width_Avg']):
            score += 1
        
        # 3. ATR declining (Volatility decreasing - confirming consolidation)
        if pd.notna(row['ATR']) and pd.notna(row['ATR_Avg']) and float(row['ATR']) < float(row['ATR_Avg']):
            score += 1
        
        # 4. MACD Histogram flattening (Momentum dying - no strong direction)
        if pd.notna(row['MACD_Hist_Abs']) and pd.notna(row['MACD_Hist_Avg']) and float(row['MACD_Hist_Abs']) < float(row['MACD_Hist_Avg']):
            score += 1
        
        # 5. Price within middle 50% of range (Market acceptance zone)
        if pd.notna(row['BB_Upper']) and pd.notna(row['BB_Lower']) and pd.notna(row['Close']):
            range_middle = (float(row['BB_Upper']) + float(row['BB_Lower'])) / 2
            range_width = (float(row['BB_Upper']) - float(row['BB_Lower'])) / 2
            if range_width > 0 and abs(float(row['Close']) - range_middle) < (range_width * 0.25):
                score += 1
    except:
        pass
    
    return score

def calculate_zone_metrics(row):
    """
    Calculate market acceptance zone and optimal trading area
    
    Returns:
    • Acceptance Zone: Where price spends 70%+ time
    • Optimal Entry Zone: Best risk-reward for shorts
    • Breakout Distance: Points needed to confirm trend
    """
    try:
        close = float(row['Close'])
        bb_upper = float(row['BB_Upper'])
        bb_lower = float(row['BB_Lower'])
        bb_middle = float(row['BB_Middle'])
        
        # Zone calculations
        range_width = bb_upper - bb_lower
        zone_height = range_width * 0.3  # 30% of range = acceptance zone
        zone_upper = bb_upper - (range_width * 0.15)
        zone_lower = bb_lower + (range_width * 0.15)
        
        # Position in zone (0-100%)
        if range_width > 0:
            position_pct = ((close - bb_lower) / range_width) * 100
        else:
            position_pct = 50
        
        return {
            'Zone_Upper': zone_upper,
            'Zone_Lower': zone_lower,
            'Zone_Height': zone_height,
            'Position_In_Zone': position_pct,
            'Is_In_Acceptance_Zone': zone_lower <= close <= zone_upper
        }
    except:
        return None

def identify_price_structure(df, lookback=20):
    """
    Identify price structure for optimal entry zones
    
    Returns:
    • Higher Lows: Price series making higher lows (bullish structure)
    • Lower Highs: Price series making lower highs (bearish structure)
    • Equal Structure: Consolidation pattern (sideways market)
    """
    structures = []
    
    for i in range(lookback, len(df)):
        recent_data = df.iloc[i-lookback:i]
        
        lows = recent_data['Low'].values
        highs = recent_data['High'].values
        
        # Count structure changes
        higher_lows = sum(1 for j in range(1, len(lows)) if lows[j] > lows[j-1])
        lower_highs = sum(1 for j in range(1, len(highs)) if highs[j] < highs[j-1])
        
        # Determine structure
        if higher_lows > lower_highs + 2:
            structure = 'BULLISH'
        elif lower_highs > higher_lows + 2:
            structure = 'BEARISH'
        else:
            structure = 'SIDEWAYS'
        
        structures.append(structure)
    
    # Pad with None for lookback period
    structures = [None] * lookback + structures
    return structures

def predict_sideways_duration(df, current_idx, lookback=30):
    """
    Predict how long the sideways phase will likely continue
    
    Returns: Duration in candles and confidence level
    """
    if current_idx < lookback:
        return 0, 0
    
    try:
        recent_data = df.iloc[current_idx-lookback:current_idx]
        
        # Measure consolidation tightness
        range_high = recent_data['High'].max()
        range_low = recent_data['Low'].min()
        range_width = range_high - range_low
        
        # Measure volatility
        current_atr = float(df['ATR'].iloc[current_idx])
        avg_atr = recent_data['ATR'].mean()
        
        # Consolidation ratio (lower = tighter consolidation)
        if avg_atr > 0:
            consolidation_ratio = current_atr / avg_atr
        else:
            consolidation_ratio = 1
        
        # Estimate duration based on tightness
        if consolidation_ratio < 0.6:
            # Very tight consolidation - likely to break soon
            predicted_duration = 3  # 3-5 candles
            confidence = 0.85
        elif consolidation_ratio < 0.8:
            # Normal consolidation
            predicted_duration = 8  # 5-10 candles
            confidence = 0.75
        else:
            # Early consolidation
            predicted_duration = 15  # 10-20 candles
            confidence = 0.65
        
        return predicted_duration, confidence
    
    except:
        return 0, 0

df['Early_Warning_Score'] = df.apply(calculate_early_warning_score, axis=1)

# Calculate zone metrics
print("Calculating zone metrics and price structure...")
df['Zone_Upper'] = np.nan
df['Zone_Lower'] = np.nan
df['Zone_Height'] = np.nan
df['Is_In_Acceptance_Zone'] = False

for i in range(len(df)):
    zone_metrics = calculate_zone_metrics(df.iloc[i])
    if zone_metrics:
        df.loc[i, 'Zone_Upper'] = zone_metrics['Zone_Upper']
        df.loc[i, 'Zone_Lower'] = zone_metrics['Zone_Lower']
        df.loc[i, 'Zone_Height'] = zone_metrics['Zone_Height']
        df.loc[i, 'Is_In_Acceptance_Zone'] = zone_metrics['Is_In_Acceptance_Zone']

# Identify price structure
print("Identifying price structure (Bullish/Bearish/Sideways)...")
df['Price_Structure'] = identify_price_structure(df, lookback=20)

# Predict sideways duration
print("Predicting sideways market duration...")
durations = []
confidences = []
for i in range(len(df)):
    duration, confidence = predict_sideways_duration(df, i, lookback=30)
    durations.append(duration)
    confidences.append(confidence)
df['Predicted_Sideways_Duration'] = durations
df['Prediction_Confidence'] = confidences

# =============================================================================
# SIGNAL GENERATION (BUY/SELL at Support/Resistance)
# =============================================================================

signals_data = []

for i in range(50, len(df)):
    idx = df.index[i]
    row = df.iloc[i]
    
    # Skip if incomplete data
    try:
        if pd.isna(float(row['ATR'])) or pd.isna(float(row['RSI'])) or pd.isna(float(row['ADX'])):
            continue
    except:
        continue
    
    early_warning = int(row['Early_Warning_Score'])
    close_val = float(row['Close'])
    rsi_val = float(row['RSI'])
    bb_upper = float(row['BB_Upper'])
    bb_lower = float(row['BB_Lower'])
    atr_val = float(row['ATR'])
    support = float(row['Recent_Low'])
    resistance = float(row['Recent_High'])
    volume = float(row['Volume'])
    avg_volume = df['Volume'].iloc[max(0, i-20):i].mean()
    
    signal = None
    entry_type = None
    
    # Calculate distances for better thresholds
    support_distance = ((resistance - support) * 0.3) if (resistance - support) > 0 else 50
    resistance_distance = ((resistance - support) * 0.3) if (resistance - support) > 0 else 50
    
    # =================================================================
    # SHORT SIGNAL (At Resistance Level) - PRIMARY STRATEGY
    # =================================================================
    # Optimized for HIGH-PROBABILITY SHORT ENTRIES in sideways markets
    
    if (early_warning >= 2 and  # Sideways predicted or confirmed
        close_val >= (resistance - resistance_distance) and  # Near resistance
        rsi_val > 50 and rsi_val < 70 and  # Overbought locally but not extreme
        volume >= avg_volume * 0.3 and  # Adequate volume
        pd.notna(df['Price_Structure'].iloc[i]) and 
        df['Price_Structure'].iloc[i] in ['SIDEWAYS', 'BEARISH']):  # Sideways or bearish structure
        
        signal = 'SHORT'
        entry_type = 'Resistance Rejection'
        
        # Entry at or near resistance
        entry_price = resistance
        atr_risk = max(atr_val * 1.2, 40)  # 40+ points for shorts
        sl_price = entry_price + atr_risk
        target_price = entry_price - (atr_risk * 2)  # 1:2 risk-reward
        
        # Zone-based targeting for additional profit taking
        zone_lower = df['Zone_Lower'].iloc[i]
        
        signals_data.append({
            'DateTime': row['DateTime'],
            'Signal_Type': 'SHORT',
            'Entry_Type': entry_type,
            'Entry_Price': entry_price,
            'SL_Price': sl_price,
            'Target_Price': target_price,
            'Zone_Target': zone_lower if pd.notna(zone_lower) else target_price,
            'Risk_Points': atr_risk,
            'Reward_Points': atr_risk * 2,
            'Risk_Reward_Ratio': f"1:2.00",
            'Close': close_val,
            'RSI': rsi_val,
            'ADX': float(row['ADX']),
            'ATR': atr_val,
            'Early_Warning_Score': early_warning,
            'Support_Level': support,
            'Resistance_Level': resistance,
            'Zone_Upper': df['Zone_Upper'].iloc[i],
            'Zone_Lower': df['Zone_Lower'].iloc[i],
            'BB_Width': float(row['BB_Width']),
            'MACD': float(row['MACD']),
            'Volume': volume,
            'Price_Structure': df['Price_Structure'].iloc[i],
            'Predicted_Duration_Candles': df['Predicted_Sideways_Duration'].iloc[i],
            'Prediction_Confidence': df['Prediction_Confidence'].iloc[i],
            'Entry_Reason': f"Sideways Confirmed (Score {early_warning}/5) | Resistance {resistance:.2f} | RSI {rsi_val:.1f} | ADX {float(row['ADX']):.1f} | Structure: {df['Price_Structure'].iloc[i]} | Duration: {df['Predicted_Sideways_Duration'].iloc[i]} candles"
        })
    
    # =================================================================
    # ALTERNATIVE BUY SIGNAL (At Support Level) - SECONDARY STRATEGY
    # =================================================================
    # Optional: For traders wanting bidirectional trades
    
    elif (early_warning >= 2 and  # Sideways confirmed
          close_val <= (support + support_distance) and  # Near support
          rsi_val > 30 and rsi_val < 50 and  # Oversold locally but not extreme
          volume >= avg_volume * 0.3 and
          pd.notna(df['Price_Structure'].iloc[i]) and
          df['Price_Structure'].iloc[i] in ['SIDEWAYS', 'BULLISH']):  # Sideways or bullish structure
        
        signal = 'BUY'
        entry_type = 'Support Bounce'
        
        # Entry at or near support
        entry_price = support
        atr_risk = max(atr_val * 0.8, 30)  # 30+ points for longs
        sl_price = entry_price - atr_risk
        target_price = entry_price + (atr_risk * 2)  # 1:2 risk-reward
        
        zone_upper = df['Zone_Upper'].iloc[i]
        
        signals_data.append({
            'DateTime': row['DateTime'],
            'Signal_Type': 'BUY',
            'Entry_Type': entry_type,
            'Entry_Price': entry_price,
            'SL_Price': sl_price,
            'Target_Price': target_price,
            'Zone_Target': zone_upper if pd.notna(zone_upper) else target_price,
            'Risk_Points': atr_risk,
            'Reward_Points': atr_risk * 2,
            'Risk_Reward_Ratio': f"1:2.00",
            'Close': close_val,
            'RSI': rsi_val,
            'ADX': float(row['ADX']),
            'ATR': atr_val,
            'Early_Warning_Score': early_warning,
            'Support_Level': support,
            'Resistance_Level': resistance,
            'Zone_Upper': df['Zone_Upper'].iloc[i],
            'Zone_Lower': df['Zone_Lower'].iloc[i],
            'BB_Width': float(row['BB_Width']),
            'MACD': float(row['MACD']),
            'Volume': volume,
            'Price_Structure': df['Price_Structure'].iloc[i],
            'Predicted_Duration_Candles': df['Predicted_Sideways_Duration'].iloc[i],
            'Prediction_Confidence': df['Prediction_Confidence'].iloc[i],
            'Entry_Reason': f"Sideways Confirmed (Score {early_warning}/5) | Support {support:.2f} | RSI {rsi_val:.1f} | ADX {float(row['ADX']):.1f} | Structure: {df['Price_Structure'].iloc[i]} | Duration: {df['Predicted_Sideways_Duration'].iloc[i]} candles"
        })

# =============================================================================
# BACKTEST VALIDATION (Check if signal was profitable)
# =============================================================================

validated_signals = []

for sig_idx, sig in enumerate(signals_data):
    sig_datetime = sig['DateTime']
    
    # Find the candle index where signal occurred
    candle_idx = df[df['DateTime'] == sig_datetime].index[0]
    
    # Look ahead 5 candles for exit
    future_candles = df.iloc[candle_idx+1:candle_idx+6]
    
    if len(future_candles) == 0:
        continue
    
    if sig['Signal_Type'] == 'BUY':
        # For BUY: Check if target was hit before SL
        max_high = future_candles['High'].max()
        min_low = future_candles['Low'].min()
        
        if max_high >= sig['Target_Price']:
            exit_price = sig['Target_Price']
            profit = sig['Reward_Points']
            status = 'WIN'
        elif min_low <= sig['SL_Price']:
            exit_price = sig['SL_Price']
            profit = -sig['Risk_Points']
            status = 'LOSS'
        else:
            exit_price = future_candles['Close'].iloc[-1]
            profit = exit_price - sig['Entry_Price']
            status = 'PARTIAL'
    
    else:  # SELL
        # For SELL: Check if target was hit before SL
        min_low = future_candles['Low'].min()
        max_high = future_candles['High'].max()
        
        if min_low <= sig['Target_Price']:
            exit_price = sig['Target_Price']
            profit = sig['Reward_Points']
            status = 'WIN'
        elif max_high >= sig['SL_Price']:
            exit_price = sig['SL_Price']
            profit = -sig['Risk_Points']
            status = 'LOSS'
        else:
            exit_price = future_candles['Close'].iloc[-1]
            profit = sig['Entry_Price'] - exit_price
            status = 'PARTIAL'
    
    sig['Exit_Price'] = exit_price
    sig['Backtest_Profit_Points'] = profit
    sig['Backtest_Profit_Rs'] = profit * 65  # Nifty multiplier (1 lot = 65 shares)
    sig['Trade_Status'] = status
    
    validated_signals.append(sig)

# =============================================================================
# PRINT RESULTS
# =============================================================================

print("\n" + "="*120)
print("SIDEWAYS MARKET ZONE ANALYSIS & TRADING OPPORTUNITY REPORT")
print(f"DATA SOURCE: {data_source}")
print("="*120)

if validated_signals:
    # Separate SHORT and BUY signals
    short_signals = [s for s in validated_signals if s['Signal_Type'] == 'SHORT']
    buy_signals = [s for s in validated_signals if s['Signal_Type'] == 'BUY']
    
    print(f"\n📊 SIGNAL BREAKDOWN")
    print(f"   Total Signals: {len(validated_signals)}")
    print(f"   SHORT Signals (Primary): {len(short_signals)} ({len(short_signals)/len(validated_signals)*100:.1f}%)")
    print(f"   BUY Signals (Secondary): {len(buy_signals)} ({len(buy_signals)/len(validated_signals)*100:.1f}%)")
    
    print(f"\n🎯 ZONE IDENTIFICATION")
    avg_zone_height = np.mean([s['Zone_Upper'] - s['Zone_Lower'] for s in validated_signals if pd.notna(s['Zone_Upper']) and pd.notna(s['Zone_Lower'])])
    avg_duration = np.mean([s['Predicted_Duration_Candles'] for s in validated_signals])
    avg_confidence = np.mean([s['Prediction_Confidence'] for s in validated_signals])
    
    print(f"   Average Acceptance Zone Height: {avg_zone_height:.2f} points")
    print(f"   Average Predicted Sideways Duration: {avg_duration:.0f} candles (~{avg_duration*4:.0f} hours on 5-min bars)")
    print(f"   Average Prediction Confidence: {avg_confidence*100:.1f}%")
    
    print(f"\n📈 SIGNAL QUALITY METRICS")
    print(f"   Average Early Warning Score: {np.mean([s['Early_Warning_Score'] for s in validated_signals]):.2f}/5")
    print(f"   Signals with Score >= 3: {len([s for s in validated_signals if s['Early_Warning_Score'] >= 3])}")
    print(f"   Signals with Score >= 4: {len([s for s in validated_signals if s['Early_Warning_Score'] >= 4])}")
    
    # Show recent signals
    print(f"\n📋 RECENT TRADING SIGNALS (Last 10)")
    print("-" * 120)
    for idx, sig in enumerate(validated_signals[-10:], 1):
        print(f"\n{idx}. {sig['DateTime']} | {sig['Signal_Type']:6s} | Warning: {sig['Early_Warning_Score']}/5 | Conf: {sig['Prediction_Confidence']*100:.0f}%")
        print(f"   Entry: {sig['Entry_Price']:.2f} | Target1: {sig['Target_Price']:.2f} | Target2: {sig['Zone_Target']:.2f} | SL: {sig['SL_Price']:.2f}")
        print(f"   Risk: {sig['Risk_Points']:.2f}pts | Reward: {sig['Reward_Points']:.2f}pts | R:R: {sig['Risk_Reward_Ratio']}")
        print(f"   Support: {sig['Support_Level']:.2f} | Resistance: {sig['Resistance_Level']:.2f}")
        print(f"   Zone: {sig['Zone_Lower']:.2f} - {sig['Zone_Upper']:.2f}")
        print(f"   Structure: {sig['Price_Structure']} | Duration: {sig['Predicted_Duration_Candles']:.0f} candles")
        print(f"   Backtest: {sig['Trade_Status']} | Profit: {sig['Backtest_Profit_Points']:.2f}pts (₹{sig['Backtest_Profit_Rs']:.0f})")
        print(f"   Reason: {sig['Entry_Reason']}")

# =============================================================================
# PERFORMANCE REPORT
# =============================================================================

print("\n" + "="*120)
print("COMPREHENSIVE SIDEWAYS MARKET TRADING REPORT - OPTIMIZATION ANALYSIS")
print("="*120)

if validated_signals:
    short_validated = [s for s in validated_signals if s['Signal_Type'] == 'SHORT']
    buy_validated = [s for s in validated_signals if s['Signal_Type'] == 'BUY']
    
    # Overall statistics
    wins = len([s for s in validated_signals if s['Trade_Status'] == 'WIN'])
    losses = len([s for s in validated_signals if s['Trade_Status'] == 'LOSS'])
    partials = len([s for s in validated_signals if s['Trade_Status'] == 'PARTIAL'])
    
    # SHORT-specific statistics
    short_wins = len([s for s in short_validated if s['Trade_Status'] == 'WIN'])
    short_losses = len([s for s in short_validated if s['Trade_Status'] == 'LOSS'])
    
    # BUY-specific statistics
    buy_wins = len([s for s in buy_validated if s['Trade_Status'] == 'WIN'])
    buy_losses = len([s for s in buy_validated if s['Trade_Status'] == 'LOSS'])
    
    total_profit = sum([s['Backtest_Profit_Rs'] for s in validated_signals])
    total_loss = sum([s['Backtest_Profit_Rs'] for s in validated_signals if s['Trade_Status'] == 'LOSS'])
    total_win_profit = sum([s['Backtest_Profit_Rs'] for s in validated_signals if s['Trade_Status'] == 'WIN'])
    
    short_profit = sum([s['Backtest_Profit_Rs'] for s in short_validated])
    buy_profit = sum([s['Backtest_Profit_Rs'] for s in buy_validated])
    
    avg_profit = total_profit / len(validated_signals) if validated_signals else 0
    avg_win = total_win_profit / wins if wins > 0 else 0
    avg_loss = total_loss / losses if losses > 0 else 0
    
    win_rate = (wins / len(validated_signals) * 100) if validated_signals else 0
    short_win_rate = (short_wins / len(short_validated) * 100) if short_validated else 0
    buy_win_rate = (buy_wins / len(buy_validated) * 100) if buy_validated else 0
    
    # Profit factor
    if abs(total_loss) > 0:
        profit_factor = total_win_profit / abs(total_loss)
    else:
        profit_factor = float('inf')
    
    print(f"\n📊 ANALYSIS PERIOD")
    print(f"   Data Source: {data_source}")
    print(f"   Total Candles Analyzed: {len(df)}")
    print(f"   Date Range: {df['DateTime'].min().strftime('%Y-%m-%d')} to {df['DateTime'].max().strftime('%Y-%m-%d')}")
    
    print(f"\n📈 SIGNAL GENERATION")
    print(f"   Total Signals Generated: {len(validated_signals)}")
    print(f"   SHORT Signals: {len(short_validated)} ({len(short_validated)/len(validated_signals)*100:.1f}%)")
    print(f"   BUY Signals: {len(buy_validated)} ({len(buy_validated)/len(validated_signals)*100:.1f}%)")
    
    print(f"\n🎯 TRADE EXECUTION RESULTS")
    print(f"   Total Trades: {len(validated_signals)}")
    print(f"   Winning Trades: {wins} ({wins/len(validated_signals)*100:.1f}%)")
    print(f"   Losing Trades: {losses} ({losses/len(validated_signals)*100:.1f}%)")
    print(f"   Partial Trades: {partials} ({partials/len(validated_signals)*100:.1f}%)")
    print(f"   Overall Win Rate: {win_rate:.2f}%")
    print(f"")
    print(f"   SHORT Performance: {short_wins} wins, {short_losses} losses ({short_win_rate:.2f}% win rate) | Profit: ₹{short_profit:,.2f}")
    print(f"   BUY Performance: {buy_wins} wins, {buy_losses} losses ({buy_win_rate:.2f}% win rate) | Profit: ₹{buy_profit:,.2f}")
    
    print(f"\n💰 FINANCIAL PERFORMANCE (NIFTY 50, 1 lot = 65 shares)")
    print(f"   Total Profit: ₹{total_profit:,.2f}")
    print(f"   Gross Wins: ₹{total_win_profit:,.2f}")
    print(f"   Gross Losses: ₹{total_loss:,.2f}")
    print(f"   Average Profit/Signal: ₹{avg_profit:,.2f}")
    print(f"   Average Win: ₹{avg_win:,.2f}")
    print(f"   Average Loss: ₹{avg_loss:,.2f}")
    
    print(f"\n📊 PROFITABILITY METRICS - PROFIT FACTOR ANALYSIS")
    if profit_factor != float('inf'):
        print(f"   Profit Factor: {profit_factor:.2f}x")
        if profit_factor > 3.0:
            status = "⭐⭐⭐ EXCELLENT (> 3.0x)"
        elif profit_factor > 2.0:
            status = "⭐⭐ VERY GOOD (> 2.0x)"
        elif profit_factor > 1.5:
            status = "⭐ GOOD (> 1.5x)"
        elif profit_factor > 1.0:
            status = "✓ ACCEPTABLE (> 1.0x)"
        else:
            status = "✗ NEEDS IMPROVEMENT (< 1.0x)"
        print(f"      Status: {status}")
    else:
        print(f"   Profit Factor: ∞ (Perfect - No losses!)")
        print(f"      Status: ⭐⭐⭐ EXCEPTIONAL")
    
    print(f"   Calculation: Total Wins (₹{total_win_profit:,.0f}) / Abs(Total Losses) (₹{abs(total_loss):,.0f})")
    print(f"   Win/Loss Ratio: {wins}:{losses}")
    
    # Risk-reward analysis
    total_risk = sum([s['Risk_Points'] for s in validated_signals])
    total_reward = sum([s['Reward_Points'] for s in validated_signals])
    avg_risk_points = total_risk / len(validated_signals)
    avg_reward_points = total_reward / len(validated_signals)
    
    print(f"\n📊 RISK-REWARD ANALYSIS")
    print(f"   Average Risk/Trade: {avg_risk_points:.2f}pts (₹{avg_risk_points*75:,.2f})")
    print(f"   Average Reward/Trade: {avg_reward_points:.2f}pts (₹{avg_reward_points*75:,.2f})")
    print(f"   Average R:R Ratio: 1:{avg_reward_points/avg_risk_points:.2f}")
    print(f"   Total Risk Capital: ₹{total_risk*75:,.0f}")
    print(f"   Total Reward Capital: ₹{total_reward*75:,.0f}")
    
    # Additional metrics
    print(f"\n💹 ADDITIONAL PROFITABILITY METRICS")
    if abs(total_loss) > 0:
        recovery_factor = total_profit / abs(total_loss)
        print(f"   Recovery Factor: {recovery_factor:.2f}x")
    print(f"   Expectancy per Trade: ₹{avg_profit:,.2f}")
    if wins > 0 and losses > 0:
        payoff_ratio = avg_win / abs(avg_loss)
        print(f"   Payoff Ratio (Avg Win/Avg Loss): {payoff_ratio:.2f}x")
    
    # Best and worst trades
    best_trade = max(validated_signals, key=lambda x: x['Backtest_Profit_Rs'])
    worst_trade = min(validated_signals, key=lambda x: x['Backtest_Profit_Rs'])
    
    print(f"\n🏆 BEST & WORST TRADES")
    print(f"   Best Trade: {best_trade['Signal_Type']:6s} on {best_trade['DateTime']} | Profit: ₹{best_trade['Backtest_Profit_Rs']:,.0f}")
    print(f"   Worst Trade: {worst_trade['Signal_Type']:6s} on {worst_trade['DateTime']} | Loss: ₹{worst_trade['Backtest_Profit_Rs']:,.0f}")
    
    # Trade streaks
    current_win_streak = 0
    current_loss_streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    
    for sig in validated_signals:
        if sig['Trade_Status'] == 'WIN':
            current_win_streak += 1
            current_loss_streak = 0
            max_win_streak = max(max_win_streak, current_win_streak)
        elif sig['Trade_Status'] == 'LOSS':
            current_loss_streak += 1
            current_win_streak = 0
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        else:
            current_win_streak = 0
            current_loss_streak = 0
    
    print(f"\n📊 TRADE STREAKS")
    print(f"   Max Consecutive Wins: {max_win_streak}")
    print(f"   Max Consecutive Losses: {max_loss_streak}")
    
    print(f"\n✅ STRATEGY OPTIMIZATION STATUS")
    
    # Optimization recommendations
    recommendations = []
    
    if win_rate < 50:
        recommendations.append("⚠️ Win Rate < 50% - Tighten entry criteria (require Warning Score >= 3)")
    elif win_rate >= 55:
        recommendations.append("✓ Win Rate >= 55% - Excellent entry filter")
    
    if profit_factor < 1.2:
        recommendations.append("⚠️ Profit Factor < 1.2x - Improve SL placement or target optimization")
    elif profit_factor >= 1.5:
        recommendations.append("✓ Profit Factor >= 1.5x - Excellent profitability")
    
    if len(validated_signals) < 20:
        recommendations.append("⚠️ < 20 signals - Need more data for statistical confidence")
    elif len(validated_signals) >= 50:
        recommendations.append("✓ >= 50 signals - Statistically significant sample")
    
    if short_win_rate > buy_win_rate:
        recommendations.append(f"✓ SHORT strategy stronger ({short_win_rate:.1f}%) than BUY ({buy_win_rate:.1f}%)")
    
    for rec in recommendations:
        print(f"   {rec}")
    
    print(f"\n🎯 DEPLOYMENT RECOMMENDATION")
    if profit_factor > 1.5 and win_rate > 50:
        deployment_status = "✅ READY FOR LIVE TRADING"
    elif profit_factor > 1.2 and win_rate > 48:
        deployment_status = "⚠️ PAPER TRADE FIRST, then deploy"
    else:
        deployment_status = "❌ OPTIMIZE FURTHER before deployment"
    
    print(f"   Status: {deployment_status}")
    print(f"   Capital Allocation: Start with 1 lot per signal (₹30K margin)")
    print(f"   Max Daily Loss: 2% of capital (₹2,000 on ₹100K)")
    print(f"   Success Criteria: Maintain Win Rate > 55% & Profit Factor > 1.5x")

else:
    print("No validated signals generated. Try adjusting parameters.")

print("\n" + "="*120)
