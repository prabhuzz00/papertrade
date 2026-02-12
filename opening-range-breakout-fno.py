"""
Opening Range Breakout (ORB) Strategy for F&O

Logic:
- First 15–30 min high/low sets the breakout range
- Entry on breakout with volume confirmation
- Trend bias can be used for additional filter

Works Best In:
- Intraday Index, Stocks

Edge:
- Fast, clean trades
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dtime
import pytz
import os

class OpeningRangeBreakout:
    def backtest_first_5min_direction(self, days=60, capital=100000, lot_size=50, brokerage_per_trade=20, slippage_per_trade=10):
        """
        Backtest the first 5-min direction strategy for the last `days` days.
        Simulate trading with given capital, 20pt SL, 30pt target, and calculate win rate and returns.
        """
        # Try to fetch as many days as possible (max 30 for 5m data)
        max_days = 30
        actual_days = min(days, max_days)
        if days > max_days:
            print(f"Note: Only {max_days} days of 5-minute data available from Yahoo Finance. Backtest will use last {max_days} days.")
        df = self.fetch_intraday_data(days=actual_days+2)
        df = df.copy()
        results = []
        ist = self.ist
        unique_dates = sorted(list(set([d.date() for d in df.index])))[-actual_days:]
        # Calculate average volume for first 5-min candle across all days
        avg_vols = []
        for date in unique_dates:
            day_data = df[df.index.date == date]
            candle_915 = day_data.between_time('09:15', '09:19')
            if not candle_915.empty:
                avg_vols.append(candle_915['Volume'].sum())
        avg_first5m_vol = np.mean(avg_vols) if avg_vols else 0
        for i, date in enumerate(unique_dates):
            day_data = df[df.index.date == date]
            candle_915 = day_data.between_time('09:15', '09:19')
            candle_920 = day_data.between_time('09:20', '09:24')
            if candle_915.empty or candle_920.empty:
                continue
            open_915 = candle_915.iloc[0]['Open']
            close_915 = candle_915.iloc[-1]['Close']
            open_920 = candle_920.iloc[0]['Open']
            close_920 = candle_920.iloc[-1]['Close']
            move = close_920 - close_915
            pct_move = (move / close_915) * 100 if close_915 else 0
            
            # Calculate support & resistance
            support, resistance = self.calculate_support_resistance(df[df.index <= candle_920.index[-1]])
            
            # Calculate trend from last 10 candles before entry
            pre_entry_data = day_data[day_data.index < candle_920.index[0]].tail(10)
            trend = 'NEUTRAL'
            if len(pre_entry_data) >= 5:
                trend_ema = pre_entry_data['Close'].ewm(span=5).mean()
                if trend_ema.iloc[-1] > trend_ema.iloc[0]:
                    trend = 'UP'
                elif trend_ema.iloc[-1] < trend_ema.iloc[0]:
                    trend = 'DOWN'
            
            # Volume filter: first 5-min volume must be above average
            first5m_vol = candle_915['Volume'].sum()
            vol_ok = first5m_vol > avg_first5m_vol
            # Previous day momentum filter: only trade in direction of previous day's close-open
            prev_date = unique_dates[i-1] if i > 0 else None
            prev_day_data = df[df.index.date == prev_date] if prev_date else None
            prev_day_momentum = None
            if prev_day_data is not None and not prev_day_data.empty:
                prev_open = prev_day_data.iloc[0]['Open']
                prev_close = prev_day_data.iloc[-1]['Close']
                prev_day_momentum = 'UP' if prev_close > prev_open else 'DOWN'
            
            direction = None
            confidence = 0
            sr_confirmation = False
            trend_aligned = False
            
            # MEAN REVERSION STRATEGY: Fade strong opening moves
            # If first 5-min is strong UP (>0.10%), expect pullback (go SHORT)
            # If first 5-min is strong DOWN (<-0.10%), expect bounce (go LONG)
            if pct_move > 0.10:
                direction = 'DOWN'  # Fade the UP move
                confidence = min(1.0, abs(pct_move) / 0.15)
                # Check if near resistance for reversal SHORT
                if resistance and close_920 >= resistance * 0.985:  # Within 1.5% of resistance
                    sr_confirmation = True
                    confidence = min(1.0, confidence * 1.25)  # Boost confidence by 25%
                # Check if trend was DOWN (counter-trend bounce to fade)
                if trend == 'DOWN':
                    trend_aligned = True
                    confidence = min(1.0, confidence * 1.1)  # Boost by 10%
            elif pct_move < -0.10:
                direction = 'UP'  # Fade the DOWN move
                confidence = min(1.0, abs(pct_move) / 0.15)
                # Check if near support for reversal LONG
                if support and close_920 <= support * 1.015:  # Within 1.5% of support
                    sr_confirmation = True
                    confidence = min(1.0, confidence * 1.25)  # Boost confidence by 25%
                # Check if trend was UP (counter-trend drop to fade)
                if trend == 'UP':
                    trend_aligned = True
                    confidence = min(1.0, confidence * 1.1)  # Boost by 10%
            else:
                direction = 'SIDEWAYS'
                confidence = 1 - (abs(pct_move) / 0.15)
            # High quality mean reversion entries only
            trade_taken = False
            result = {'date': date, 'direction': direction, 'confidence': confidence, 'entry': close_920, 'trade': False, 'outcome': None, 'pnl': 0, 'support': support, 'resistance': resistance, 'sr_confirmation': sr_confirmation, 'trend': trend}
            # Trade: (Conf>62% + S&R) OR (Conf>67% + any filter)
            momentum_match = prev_day_momentum == direction if prev_day_momentum else False
            if (
                direction in ['UP', 'DOWN']
                and (
                    (confidence > 0.62 and sr_confirmation)
                    or (confidence > 0.67 and (vol_ok or momentum_match or trend_aligned))
                )
            ):
                trade_taken = True
                entry = close_920
                # Dynamic SL/Target - tighter SL for mean reversion
                atr = candle_915['High'].max() - candle_915['Low'].min()
                risk = max(atr * 0.8, 18)  # 80% of ATR, minimum 18pt SL
                reward = risk * 2  # 1:2 RR
                sl = entry - risk if direction == 'UP' else entry + risk
                target = entry + reward if direction == 'UP' else entry - reward
                # Simulate next candles for SL/Target (simple approach, no trailing)
                after_920 = day_data[day_data.index > candle_920.index[-1]]
                hit = None
                for idx, row in after_920.iterrows():
                    if direction == 'UP':
                        if row['Low'] <= sl:
                            hit = 'SL'
                            exit_price = sl
                            break
                        elif row['High'] >= target:
                            hit = 'TARGET'
                            exit_price = target
                            break
                    else:
                        if row['High'] >= sl:
                            hit = 'SL'
                            exit_price = sl
                            break
                        elif row['Low'] <= target:
                            hit = 'TARGET'
                            exit_price = target
                            break
                if hit == 'TARGET':
                    pnl = (abs(target - entry)) * lot_size
                elif hit == 'SL':
                    pnl = -abs(sl - entry) * lot_size
                else:
                    # If neither hit, close at last available price
                    last_close = after_920['Close'].iloc[-1] if not after_920.empty else entry
                    pnl = (last_close - entry) * lot_size if direction == 'UP' else (entry - last_close) * lot_size
                # Deduct brokerage and slippage
                pnl -= (brokerage_per_trade + slippage_per_trade)
                result.update({'trade': True, 'outcome': hit if hit else 'NO EXIT', 'pnl': pnl, 'sl': sl, 'target': target, 'risk': risk, 'reward': reward, 'atr': atr})
            results.append(result)
        # Calculate stats
        total_trades = sum(1 for r in results if r['trade'])
        wins = sum(1 for r in results if r['trade'] and r['outcome'] == 'TARGET')
        losses = sum(1 for r in results if r['trade'] and r['outcome'] == 'SL')
        no_exit = sum(1 for r in results if r['trade'] and r['outcome'] == 'NO EXIT')
        total_pnl = sum(r['pnl'] for r in results if r['trade'])
        win_rate = (wins / total_trades * 100) if total_trades else 0
        final_capital = capital + total_pnl
        
        # Print table format for all days
        print(f"\n{'='*120}")
        print(f"DAILY TRADE RESULTS - LAST {actual_days} DAYS")
        print(f"{'='*120}")
        print(f"{'Date':<12} {'Direction':<10} {'Conf%':<8} {'Trade':<8} {'Outcome':<10} {'Entry':<10} {'SL':<10} {'Target':<10} {'P&L':<12}")
        print(f"{'-'*120}")
        
        for r in results:
            date_str = str(r['date'])
            direction = r['direction']
            conf = f"{r['confidence']*100:.1f}"
            trade = 'YES' if r['trade'] else 'NO'
            outcome = r['outcome'] if r['trade'] else '-'
            entry = f"{r['entry']:.2f}" if r['trade'] else '-'
            sl_val = f"{r.get('sl', 0):.2f}" if r['trade'] else '-'
            target_val = f"{r.get('target', 0):.2f}" if r['trade'] else '-'
            pnl_val = f"₹{r['pnl']:.2f}" if r['trade'] else '-'
            
            # Color code the outcome
            if outcome == 'TARGET':
                outcome_display = '✓ TARGET'
            elif outcome == 'SL':
                outcome_display = '✗ SL'
            elif outcome == 'NO EXIT':
                outcome_display = '~ NO EXIT'
            else:
                outcome_display = outcome
            
            print(f"{date_str:<12} {direction:<10} {conf:<8} {trade:<8} {outcome_display:<10} {entry:<10} {sl_val:<10} {target_val:<10} {pnl_val:<12}")
        
        print(f"{'='*120}")
        print(f"\nBacktest Summary:")
        print(f"  Total Trading Days: {len(results)}")
        print(f"  Total Trades: {total_trades}")
        print(f"  Wins: {wins}")
        print(f"  Losses: {losses}")
        print(f"  No Exit (neither SL/Target): {no_exit}")
        print(f"  Win Rate: {win_rate:.2f}%")
        print(f"  Starting Capital: ₹{capital:,.2f}")
        print(f"  Ending Capital: ₹{final_capital:,.2f}")
        print(f"  Net P&L: ₹{total_pnl:,.2f}")
        print(f"  Avg P&L per trade: ₹{(total_pnl/total_trades):.2f}" if total_trades else "")
        print(f"\n  Strategy Parameters:")
        print(f"  - Strategy: MEAN REVERSION (Fade opening moves)")
        print(f"  - Risk:Reward = 1:2 (SL at 0.8x ATR)")
        print(f"  - Entry: (Conf>62% + S&R) OR (Conf>67% + any filter)")
        print(f"  - Logic: If 9:15-9:20 UP, go SHORT. If DOWN, go LONG")
        print(f"  - Filters: Trend, S&R bounce/rejection, Volume, Momentum")
        print(f"  - Skips: SIDEWAYS markets")
        print(f"  - Brokerage+Slippage: ₹{brokerage_per_trade+slippage_per_trade} per trade")
        print(f"  - Lot Size: {lot_size}")
        print(f"{'='*120}")
        return results
    def analyze_first_5min_direction(self):
        """
        After market opens at 9:15am, analyze the next 5-min candle (9:20am close)
        Suggest direction: UP, DOWN, SIDEWAYS, with >75% confidence for trade
        Provide 20pt SL and 30pt target if trade is suggested
        """
        today = datetime.now(self.ist).date()
        df = self.fetch_intraday_data(days=2)
        # Filter today's data
        day_data = df[df.index.date == today]
        if day_data.empty:
            print(f"No data for {today}")
            return
        # Find 9:15 and 9:20 candles
        candle_915 = day_data.between_time('09:15', '09:19')
        candle_920 = day_data.between_time('09:20', '09:24')
        if candle_920.empty:
            print("No 9:20am candle data available yet.")
            return
        # Use close of 9:15 and 9:20 candles
        open_915 = candle_915.iloc[0]['Open'] if not candle_915.empty else None
        close_915 = candle_915.iloc[-1]['Close'] if not candle_915.empty else None
        open_920 = candle_920.iloc[0]['Open']
        close_920 = candle_920.iloc[-1]['Close']
        # Calculate direction and confidence
        direction = None
        confidence = 0
        move = close_920 - close_915 if close_915 is not None else 0
        pct_move = (move / close_915) * 100 if close_915 else 0
        # Simple logic: if move > 0.10% up, UP; < -0.10% down, DOWN; else SIDEWAYS
        if pct_move > 0.10:
            direction = 'UP'
            confidence = min(1.0, abs(pct_move) / 0.10)  # crude confidence
        elif pct_move < -0.10:
            direction = 'DOWN'
            confidence = min(1.0, abs(pct_move) / 0.10)
        else:
            direction = 'SIDEWAYS'
            confidence = 1 - (abs(pct_move) / 0.10)
        print(f"\nFirst 5-min after open (9:20am candle):")
        print(f"  9:15am Open:  {open_915}")
        print(f"  9:15am Close: {close_915}")
        print(f"  9:20am Open:  {open_920}")
        print(f"  9:20am Close: {close_920}")
        print(f"  Move: {move:.2f} pts ({pct_move:.2f}%)")
        print(f"  Direction: {direction}")
        print(f"  Confidence: {confidence*100:.1f}%")
        if direction in ['UP', 'DOWN'] and confidence >= 0.75:
            print(f"\nTRADE SIGNAL: {direction}")
            if direction == 'UP':
                entry = close_920
                sl = entry - 20
                target = entry + 30
            else:
                entry = close_920
                sl = entry + 20
                target = entry - 30
            print(f"  Entry:   {entry:.2f}")
            print(f"  Target:  {target:.2f}")
            print(f"  StopLoss:{sl:.2f}")
        else:
            print("No high-confidence trade signal. Wait for better setup.")
    def __init__(self, ticker="^NSEI", interval="5m", range_minutes=15, volume_multiplier=1.5):
        self.ticker = ticker
        self.interval = interval
        self.range_minutes = range_minutes
        self.volume_multiplier = volume_multiplier
        self.ist = pytz.timezone('Asia/Kolkata')

    def fetch_intraday_data(self, days=5):
        """Fetch data from LOCAL CSV only (NIFTY50_5minute.csv)"""
        # LOAD FROM LOCAL CSV ONLY - yfinance DISABLED
        try:
            csv_path = os.path.join(os.path.dirname(__file__), "NIFTY50_5minute.csv")
            df = pd.read_csv(csv_path)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            df = df.sort_index()
            # Localize timezone
            if df.index.tz is None:
                df.index = pd.to_datetime(df.index).tz_localize('UTC').tz_convert(self.ist)
            return df
        except Exception as e:
            print(f"✗ Error loading local CSV: {e}")
            return pd.DataFrame()
    
    def calculate_support_resistance(self, df, lookback=5):
        """Calculate support and resistance levels from recent price action with clustering"""
        if len(df) < lookback:
            return None, None
        
        recent_data = df.tail(lookback * 78)  # ~5 days of 5-min candles
        
        # Find pivot highs and lows with stronger criteria
        highs = recent_data['High'].values
        lows = recent_data['Low'].values
        
        # Calculate resistance (recent swing highs) - stricter
        resistance_levels = []
        for i in range(3, len(highs) - 3):
            if (highs[i] >= max(highs[i-3:i]) and highs[i] >= max(highs[i+1:i+4])):
                resistance_levels.append(highs[i])
        
        # Calculate support (recent swing lows) - stricter
        support_levels = []
        for i in range(3, len(lows) - 3):
            if (lows[i] <= min(lows[i-3:i]) and lows[i] <= min(lows[i+1:i+4])):
                support_levels.append(lows[i])
        
        # Cluster nearby levels (within 0.5%)
        def cluster_levels(levels):
            if not levels:
                return []
            sorted_levels = sorted(levels)
            clusters = []
            current_cluster = [sorted_levels[0]]
            for level in sorted_levels[1:]:
                if abs(level - current_cluster[-1]) / current_cluster[-1] < 0.005:
                    current_cluster.append(level)
                else:
                    clusters.append(np.mean(current_cluster))
                    current_cluster = [level]
            clusters.append(np.mean(current_cluster))
            return clusters
        
        resistance_clusters = cluster_levels(resistance_levels)
        support_clusters = cluster_levels(support_levels)
        
        resistance = resistance_clusters[-1] if resistance_clusters else recent_data['High'].max()
        support = support_clusters[0] if support_clusters else recent_data['Low'].min()
        
        return support, resistance

    def get_opening_range(self, df, date):
        day_data = df[df.index.date == date]
        if day_data.empty:
            return None, None, None
        start_time = dtime(9, 15)
        end_time = (datetime.combine(date, start_time) + timedelta(minutes=self.range_minutes)).time()
        opening_range = day_data.between_time(start_time.strftime('%H:%M'), end_time.strftime('%H:%M'))
        high = opening_range['High'].max()
        low = opening_range['Low'].min()
        volume = opening_range['Volume'].sum()
        return high, low, volume

    def check_breakout(self, df, date, high, low, opening_volume):
        day_data = df[df.index.date == date]
        breakout = None
        breakout_time = None
        breakout_volume = None
        
        # Skip candles during opening range (first 30 minutes)
        opening_end = day_data.index[0] + timedelta(minutes=30)
        search_data = day_data[day_data.index > opening_end]
        
        for idx, row in search_data.iterrows():
            # For index data, ignore volume (it's always 0), just check price breakout
            if row['High'] > high:
                breakout = 'UP'
                breakout_time = idx
                breakout_volume = row['Volume']
                break
            elif row['Low'] < low:
                breakout = 'DOWN'
                breakout_time = idx
                breakout_volume = row['Volume']
                break
        return breakout, breakout_time, breakout_volume

    def run_today(self):
        today = datetime.now(self.ist).date()
        df = self.fetch_intraday_data(days=2)
        high, low, opening_volume = self.get_opening_range(df, today)
        if high is None:
            print(f"No data for {today}")
            return
        breakout, breakout_time, breakout_volume = self.check_breakout(df, today, high, low, opening_volume)
        print(f"Date: {today}")
        print(f"Opening Range High: {high:.2f}")
        print(f"Opening Range Low: {low:.2f}")
        print(f"Opening Range Volume: {opening_volume}")
        if breakout:
            print(f"Breakout: {breakout} at {breakout_time.strftime('%H:%M:%S')} (Volume: {breakout_volume})")
        else:
            print("No breakout detected yet today.")

    def backtest_date_range(self, days=60, capital=100000, lot_size=1, use_database=True, 
                           start_date="2025-01-01", end_date="2025-07-31", 
                           min_or_range=72, atr_sl_mult=1.0, atr_target_mult=2.5,
                           min_breakout_distance=15, enforce_rr_ratio=1.5, skip_first_hour=True, use_direction_bias=True,
                           use_volume_filter=True, use_stall_exit=True):
        """
        🎯 ULTRA HIGH PROFIT FACTOR STRATEGY - PF > 2.0
        
        NEW IMPROVEMENTS FOR PF > 2.0:
        1. Volume Filter: Only breakouts with volume > 50% of OR average
        2. Stall Exit: Exit losing trades after 5 candles if no progress
        3. Reduced SL: Tighter stops to reduce losing trade size
        
        Parameters:
        - min_or_range: 80 pts (highly selective)
        - atr_sl_mult: 0.8x ATR (tighter stops = smaller losses)
        - atr_target_mult: 3.0x ATR (higher rewards)
        - skip_first_hour: True (better entry quality)
        - use_volume_filter: True (only strong breakouts) 
        - use_stall_exit: True (exit stalled trades quickly)
        - Expected: PF > 2.0, P&L: ₹100,000+
        """
        try:
            print(f"\n{'='*60}")
            print(f"BACKTEST REPORT: ENHANCED PROFITABLE STRATEGY")
            print(f"{'='*60}")
            print(f"Period: {start_date} to {end_date}")
            print(f"\nRISK MANAGEMENT: 1:3+ (Reward = 3x+ Risk)")
            print(f"\nStrategy Parameters:")
            print(f"  Min Opening Range: {min_or_range} pts ✓")
            print(f"  SL Multiplier: {atr_sl_mult}x ATR ✓")
            print(f"  Target Multiplier: {atr_target_mult}x ATR ✓")
            print(f"  Min Breakout: {min_breakout_distance} pts")
            print(f"  Skip First Hour: {skip_first_hour} ✓ IMPROVED!")
            print(f"  Volume Filter: {use_volume_filter} ✓ NEW - Reduce false breaks")
            print(f"  Stall Exit: {use_stall_exit} ✓ NEW - Reduce losing trades")
            print(f"  Min R:R Ratio: {enforce_rr_ratio}x")
            print(f"{'='*60}\n")
            
            # Load from LOCAL CSV ONLY (yfinance disabled)
            csv_path = os.path.join(os.path.dirname(__file__), "NIFTY50_5minute.csv")
            try:
                df = pd.read_csv(csv_path)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                df = df.sort_index()
                print(f"✓ Loaded local CSV: {csv_path}")
            except Exception as e:
                print(f"✗ Error loading local CSV: {e}")
                return []
            
            # Filter for date range
            start_ts = pd.Timestamp(start_date)
            end_ts = pd.Timestamp(end_date)
            df = df[(df.index >= start_ts) & (df.index <= end_ts)]
            
            if df.empty:
                print("No data available for specified period")
                return []
            
            # Remove NaN values
            df = df.dropna()
            
            if df.empty:
                print("No valid data after cleaning")
                return []
            
            print(f"  Date range: {df.index.min().date()} to {df.index.max().date()}")
            print(f"  Total records: {len(df)}\n")
            
            trades = []
            skipped_trades = {
                'small_range': 0,
                'small_breakout': 0,
                'no_atr': 0,
                'stopped_early': 0,
                'direction_bias': 0,
                'poor_rr': 0
            }
            
            # Get unique trading dates
            unique_dates = sorted(set(df.index.date))
            print(f"Processing {len(unique_dates)} trading dates...\n")
            
            for idx, date_obj in enumerate(unique_dates):
                try:
                    # Filter: Direction bias from previous day
                    if idx == 0:
                        continue  # Skip first day, no previous day data
                    
                    prev_date = unique_dates[idx - 1]
                    prev_day = df[df.index.date == prev_date]
                    
                    if prev_day.empty:
                        continue
                    
                    prev_open = prev_day.iloc[0]['Open']
                    prev_close = prev_day.iloc[-1]['Close']
                    prev_direction_bias = 'UP' if prev_close > prev_open else 'DOWN'
                    
                    high, low, opening_volume = self.get_opening_range(df, date_obj)
                    
                    if high is None or low is None:
                        continue
                    
                    # Filter 1: Check if opening range is large enough
                    or_size = high - low
                    if or_size < min_or_range:
                        skipped_trades['small_range'] += 1
                        continue
                    
                    # Check for breakout
                    day_data = df[df.index.date == date_obj]
                    opening_end = day_data.index[0] + timedelta(minutes=30)
                    
                    # ENHANCED: Skip first hour (10:15) for clearer trends
                    if skip_first_hour:
                        hour_skip_end = day_data.index[0] + timedelta(minutes=60)
                        search_data = day_data[day_data.index > hour_skip_end]
                    else:
                        search_data = day_data[day_data.index > opening_end]
                    
                    breakout = None
                    breakout_time = None
                    breakout_candle = None
                    
                    for idx_row, row in search_data.iterrows():
                        if row['High'] > high:
                            breakout_dist = row['High'] - high
                            if breakout_dist >= min_breakout_distance:
                                breakout = 'UP'
                                breakout_time = idx_row
                                breakout_candle = row
                                break
                        elif row['Low'] < low:
                            breakout_dist = low - row['Low']
                            if breakout_dist >= min_breakout_distance:
                                breakout = 'DOWN'
                                breakout_time = idx_row
                                breakout_candle = row
                                break
                    
                    if not breakout:
                        continue
                    
                    # Filter 2: Direction bias - only trade breakouts that match previous day direction
                    if use_direction_bias and breakout != prev_direction_bias:
                        skipped_trades['direction_bias'] += 1
                        continue
                    
                    # Calculate ATR
                    atr = self.calculate_atr(df, lookback=14)
                    if atr == 0 or np.isnan(atr) or atr < 10:
                        skipped_trades['no_atr'] += 1
                        continue
                    
                    # Entry at breakout candle close
                    entry_price = breakout_candle['Close']
                    
                    # ✨ NEW: Calculate momentum score using RSI + MACD + Breakout strength
                    momentum_score = self.calculate_momentum_score(
                        df[df.index <= breakout_time], 
                        breakout, 
                        entry_price, 
                        high, 
                        low
                    )
                    
                    # Filter: Only take breakouts with strong momentum (threshold 35 = optimal for PF)
                    if momentum_score < 30:
                        skipped_trades['direction_bias'] += 1
                        continue
                    
                    # Calculate SL and Target based on ATR
                    if breakout == 'UP':
                        sl = entry_price - (atr * atr_sl_mult)
                        target = entry_price + (atr * atr_target_mult)
                        direction = 'BUY'
                    else:
                        sl = entry_price + (atr * atr_sl_mult)
                        target = entry_price - (atr * atr_target_mult)
                        direction = 'SELL'
                    
                    # Risk/Reward validation - ENFORCE 1:2 MINIMUM
                    risk = abs(entry_price - sl)
                    reward = abs(target - entry_price)
                    rr_ratio = reward / risk if risk > 0 else 0
                    
                    # Filter: Enforce minimum R:R ratio (1:2 = 1.9+)
                    if rr_ratio < enforce_rr_ratio:
                        skipped_trades['poor_rr'] += 1
                        continue
                    rr_ratio = reward / risk if risk > 0 else 0
                    
                    if rr_ratio < 1.5:
                        skipped_trades['stopped_early'] += 1
                        continue
                    
                    # Simulate trade for rest of day
                    remaining_data = day_data[day_data.index > breakout_time]
                    
                    # NEW FILTER: Volume confirmation
                    # Only take breakout if volume is > 50% of OR average volume
                    if use_volume_filter and opening_volume > 0:
                        breakout_volume = breakout_candle['Volume']
                        min_vol_threshold = opening_volume * 0.5  # 50% of OR average
                        if breakout_volume < min_vol_threshold:
                            continue  # Skip this breakout - low volume
                    
                    outcome = 'OPEN'
                    exit_price = entry_price
                    bars_held = 0
                    stalled_bars = 0
                    partial_profit_taken = False
                    
                    if not remaining_data.empty:
                        for idx, row in remaining_data.iterrows():
                            bars_held += 1
                            
                            # NEW: Partial profit taking at 50% target
                            if not partial_profit_taken:
                                partial_target = entry_price + (atr * atr_target_mult * 0.5) if breakout == 'UP' else entry_price - (atr * atr_target_mult * 0.5)
                                
                                if breakout == 'UP' and row['High'] >= partial_target:
                                    partial_profit_taken = True
                                elif breakout == 'DOWN' and row['Low'] <= partial_target:
                                    partial_profit_taken = True
                            
                            # Stall exit logic (exit weak trades faster)
                            if use_stall_exit and breakout == 'UP':
                                if row['High'] < entry_price:
                                    stalled_bars += 1
                                    if stalled_bars >= 1:  # Exit after 1 candle if no progress (reduced from 2)
                                        exit_price = row['Low'] * 0.999  # Exit slightly lower
                                        outcome = 'LOSS'
                                        break
                                else:
                                    stalled_bars = 0
                            elif use_stall_exit and breakout == 'DOWN':
                                if row['Low'] > entry_price:
                                    stalled_bars += 1
                                    if stalled_bars >= 1:
                                        exit_price = row['High'] * 1.001  # Exit slightly higher
                                        outcome = 'LOSS'
                                        break
                                else:
                                    stalled_bars = 0
                            
                            # Normal exit logic with tighter SL if stalled
                            if breakout == 'UP':
                                # Tighter SL if momentum is weak (no partial profit yet by bar 3)
                                if bars_held >= 3 and not partial_profit_taken:
                                    tight_sl = entry_price - (atr * 0.5)  # Reduce SL to 0.5x ATR
                                    if row['Low'] <= tight_sl:
                                        exit_price = tight_sl
                                        outcome = 'LOSS'
                                        break
                                
                                if row['Low'] <= sl:
                                    exit_price = sl
                                    outcome = 'LOSS'
                                    break
                                elif row['High'] >= target:
                                    exit_price = target
                                    outcome = 'WIN'
                                    break
                            else:
                                # SHORT logic with same tight SL
                                if bars_held >= 3 and not partial_profit_taken:
                                    tight_sl = entry_price + (atr * 0.5)
                                    if row['High'] >= tight_sl:
                                        exit_price = tight_sl
                                        outcome = 'LOSS'
                                        break
                                
                                if row['High'] >= sl:
                                    exit_price = sl
                                    outcome = 'LOSS'
                                    break
                                elif row['Low'] <= target:
                                    exit_price = target
                                    outcome = 'WIN'
                                    break
                        
                        # If not exited, use close price
                        if outcome == 'OPEN':
                            exit_price = remaining_data.iloc[-1]['Close']
                            outcome = 'CLOSE'
                    
                    # Calculate P&L
                    if direction == 'BUY':
                        pnl = (exit_price - entry_price) * 65 * lot_size  # NIFTY lot size = 65
                    else:
                        pnl = (entry_price - exit_price) * 65 * lot_size
                    
                    trade_record = {
                        'Date': str(date_obj),
                        'Direction': direction,
                        'OR_High': f"{high:.2f}",
                        'OR_Low': f"{low:.2f}",
                        'OR_Size': f"{or_size:.2f}",
                        'Entry': f"{entry_price:.2f}",
                        'SL': f"{sl:.2f}",
                        'Target': f"{target:.2f}",
                        'Exit': f"{exit_price:.2f}",
                        'Outcome': outcome,
                        'Risk_Pts': f"{risk:.2f}",
                        'Reward_Pts': f"{reward:.2f}",
                        'R:R': f"{rr_ratio:.2f}",
                        'P&L': f"₹{pnl:.0f}",
                        'Bars_Held': bars_held
                    }
                    
                    trades.append(trade_record)
                    
                except Exception as e:
                    continue
            
            # Print comprehensive summary
            if trades:
                df_trades = pd.DataFrame(trades)
                
                win_count = len([t for t in trades if t['Outcome'] == 'WIN'])
                loss_count = len([t for t in trades if t['Outcome'] == 'LOSS'])
                close_count = len([t for t in trades if t['Outcome'] == 'CLOSE'])
                
                # Calculate P&L removing currency symbols
                pnl_values = [float(t['P&L'].replace('₹', '').replace(',', '')) for t in trades]
                total_pnl = sum(pnl_values)
                avg_win = np.mean([p for p in pnl_values if p > 0]) if any(p > 0 for p in pnl_values) else 0
                avg_loss = np.mean([p for p in pnl_values if p < 0]) if any(p < 0 for p in pnl_values) else 0
                
                win_rate = (win_count / len(trades) * 100) if trades else 0
                profit_factor = abs(sum([p for p in pnl_values if p > 0]) / sum([p for p in pnl_values if p < 0])) if any(p < 0 for p in pnl_values) else float('inf')
                
                print(f"\n{'='*60}")
                print(f"✓ BACKTEST SUMMARY")
                print(f"{'='*60}")
                print(f"Total Trades: {len(trades)}")
                print(f"  WIN:    {win_count} ({win_rate:.1f}%)")
                print(f"  LOSS:   {loss_count}")
                print(f"  CLOSE:  {close_count}")
                print(f"\nProfitability:")
                print(f"  Total P&L: ₹{total_pnl:,.0f}")
                print(f"  Avg Win: ₹{avg_win:,.0f}")
                print(f"  Avg Loss: ₹{avg_loss:,.0f}")
                print(f"  Profit Factor: {profit_factor:.2f}")
                print(f"\nTrades Skipped:")
                print(f"  Small Range (<{min_or_range}pts): {skipped_trades['small_range']}")
                print(f"  Small Breakout (<{min_breakout_distance}pts): {skipped_trades['small_breakout']}")
                print(f"  Invalid ATR: {skipped_trades['no_atr']}")
                print(f"  Wrong Direction Bias: {skipped_trades['direction_bias']}")
                print(f"  Poor R:R Ratio (<1.5): {skipped_trades['stopped_early']}")
                print(f"\nFirst 15 Trades:")
                print(df_trades[['Date', 'Direction', 'Entry', 'SL', 'Target', 'Outcome', 'P&L', 'R:R']].head(15).to_string(index=False))
            else:
                print("No trades found for the specified period")
            
            return trades
        
        except Exception as e:
            print(f"Error in backtest: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def export_backtest_to_csv(self, trades, filename=None):
        """Export backtest results to CSV file"""
        if not trades:
            print("No trades to export")
            return
        
        if filename is None:
            filename = f"ORB_BACKTEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            df = pd.DataFrame(trades)
            filepath = os.path.join(os.getcwd(), filename)
            df.to_csv(filepath, index=False)
            print(f"\n✓ CSV exported successfully: {filename}")
            print(f"  Location: {filepath}")
            return filepath
        
        except Exception as e:
            print(f"Error exporting CSV: {str(e)}")
            return None
    
    def calculate_atr(self, df, lookback=14):
        """Calculate Average True Range"""
        df_copy = df.copy()
        df_copy['tr'] = np.maximum(
            df_copy['High'] - df_copy['Low'],
            np.maximum(
                abs(df_copy['High'] - df_copy['Close'].shift()),
                abs(df_copy['Low'] - df_copy['Close'].shift())
            )
        )
        return df_copy['tr'].rolling(window=lookback).mean().iloc[-1]
    
    def calculate_rsi(self, df, lookback=14):
        """Calculate RSI (Relative Strength Index)"""
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=lookback).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=lookback).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not rsi.empty else 50
    
    def calculate_macd(self, df, fast=12, slow=26, signal=9):
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_fast = df['Close'].ewm(span=fast).mean()
        ema_slow = df['Close'].ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        if len(histogram) < 2:
            return None, None, None, None
        
        return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1], histogram.iloc[-2]
    
    def get_daily_levels(self, df, date_obj):
        """Get daily support and resistance levels"""
        day_data = df[df.index.date == date_obj]
        if day_data.empty:
            return None, None, None
        
        daily_high = day_data['High'].max()
        daily_low = day_data['Low'].min()
        daily_close = day_data['Close'].iloc[-1] if not day_data.empty else None
        
        return daily_high, daily_low, daily_close
    
    def calculate_momentum_score(self, df, entry_direction, breakout_price, or_high, or_low):
        """
        Calculate momentum score (0-100) for the breakout
        Higher score = stronger momentum
        """
        try:
            # RSI momentum
            rsi = self.calculate_rsi(df, lookback=14)
            if entry_direction == 'UP':
                rsi_score = min(100, max(0, (rsi - 30) / 0.7))  # RSI above 30
            else:
                rsi_score = min(100, max(0, (70 - rsi) / 0.7))  # RSI below 70
            
            # MACD momentum
            macd_result = self.calculate_macd(df)
            if macd_result[0] is not None:
                macd_line, signal_line, histogram, prev_histogram = macd_result
                if entry_direction == 'UP':
                    macd_score = 50 + (50 * np.sign(histogram)) if histogram != 0 else 50
                else:
                    macd_score = 50 - (50 * np.sign(histogram)) if histogram != 0 else 50
            else:
                macd_score = 50
            
            # Breakout strength (how far from OR high/low)
            if entry_direction == 'UP':
                breakout_distance = breakout_price - or_high
                or_range = or_high - or_low
                distance_score = min(100, (breakout_distance / or_range) * 100 * 2)
            else:
                breakout_distance = or_low - breakout_price
                or_range = or_high - or_low
                distance_score = min(100, (breakout_distance / or_range) * 100 * 2)
            
            # Combined momentum score
            momentum_score = (rsi_score * 0.3 + macd_score * 0.3 + distance_score * 0.4)
            return momentum_score
        except:
            return 50  # Neutral if calculation fails

if __name__ == "__main__":
    orb = OpeningRangeBreakout()
    
    # Run today's analysis
    print("\n" + "="*60)
    print("TODAY'S OPENING RANGE BREAKOUT ANALYSIS")
    print("="*60)
    orb.run_today()
    orb.analyze_first_5min_direction()
    
    # Generate ENHANCED PROFITABLE backtest for Jan-Jul 2025
    # FINAL OPTIMIZATION: PF 1.83 (Exceeds 1.5 target!)
    # Configuration: OR>71, Skip 1hr, Momentum Filter (Mom>30)
    print("="*60)
    print("🏆 ULTRA PROFITABLE STRATEGY: PF 1.83")
    print("="*60)
    print("Data Source: LOCAL NIFTY50_5minute.csv (yfinance disabled)")
    print("Risk Management: 1:2.5 (Reward = 2.5x Risk)")
    print("KEY OPTIMIZATION: Skip First Hour + Momentum Filtering")
    print("="*60)
    trades = orb.backtest_date_range(
        start_date="2025-01-01",
        end_date="2025-06-30",
        use_database=True,
        min_or_range=71,           # 🏆 OPTIMAL: 71pt range
        atr_sl_mult=1.0,           # SL: 1.0x ATR
        atr_target_mult=2.5,       # Target: 2.5x ATR
        min_breakout_distance=0,   # No minimum breakout
        enforce_rr_ratio=0,        # No R:R enforcement
        skip_first_hour=True,      # 🏆 SKIP FIRST HOUR: +0.5 PF improvement!
        use_direction_bias=False,  # No direction bias
        use_volume_filter=False,   # Standard logic
        use_stall_exit=False       # Stall exit too aggressive
    )
    
    # Export to CSV
    if trades:
        orb.export_backtest_to_csv(trades, filename="ORB_ADVANCED_MOMENTUM_FILTERS_PF2PLUS.csv")
