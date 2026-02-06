"""
Strategy Wrapper Classes

Wraps the three trading strategies into a unified interface for the GUI application.
Each strategy class provides:
- add_indicators(): Add technical indicators to dataframe
- get_signal(): Get current trading signal
- get_info(): Get strategy description
"""

import pandas as pd
import numpy as np
from datetime import datetime


class BollingerMACDStrategy:
    """
    Bollinger Band + MACD Breakout Strategy
    Based on predictioncandle.py
    """
    
    def __init__(self):
        self.name = "Bollinger + MACD Strategy"
        self.description = """
        <h3>Bollinger Band + MACD Breakout</h3>
        <p><b>Entry Rules:</b></p>
        <ul>
            <li><b>CALL:</b> Close > BB Upper + MACD > Signal + RSI 50-85</li>
            <li><b>PUT:</b> Close < BB Lower + MACD < Signal + RSI 15-50</li>
        </ul>
        <p><b>Risk/Reward:</b> Minimum 1:1.5</p>
        """
    
    def calc_atr(self, data, period=14):
        """Calculate Average True Range"""
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def calc_rsi(self, data, period=14):
        """Calculate RSI"""
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calc_macd(self, data, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        ema_fast = data['Close'].ewm(span=fast).mean()
        ema_slow = data['Close'].ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        return macd, macd_signal
    
    def calc_bollinger(self, data, period=20, num_std=2):
        """Calculate Bollinger Bands"""
        sma = data['Close'].rolling(window=period).mean()
        std = data['Close'].rolling(window=period).std()
        upper = sma + (num_std * std)
        lower = sma - (num_std * std)
        return upper, lower, sma
    
    def add_indicators(self, df):
        """Add all technical indicators to dataframe"""
        df['ATR'] = self.calc_atr(df)
        df['RSI'] = self.calc_rsi(df)
        df['MACD'], df['MACD_signal'] = self.calc_macd(df)
        df['BB_upper'], df['BB_lower'], df['BB_middle'] = self.calc_bollinger(df)
        df['AvgVol'] = df['Volume'].rolling(window=20).mean()
        return df
    
    def get_signal(self, df):
        """Get current trading signal"""
        if len(df) < 30:
            return None
        
        # Add indicators if not present
        if 'ATR' not in df.columns:
            df = self.add_indicators(df)
        
        # Get last candle
        last = df.iloc[-1]
        
        # Check for NaN values and extract scalar values
        try:
            close_val = last['Close'].item()
            bb_upper = last['BB_upper'].item()
            bb_lower = last['BB_lower'].item()
            macd_val = last['MACD'].item()
            macd_sig = last['MACD_signal'].item()
            rsi_val = last['RSI'].item()
            atr_val = last['ATR'].item()
            vol_val = last['Volume'].item()
            avg_vol = last['AvgVol'].item()
            
            if pd.isna(atr_val) or pd.isna(rsi_val) or pd.isna(macd_val):
                print("[ERROR] Invalid indicators (NaN values)")
                return None
        except (ValueError, TypeError, KeyError) as e:
            print(f"[ERROR] Error extracting indicators: {e}")
            return None
        
        # Volatility check
        recent_atr = df['ATR'].iloc[-10:].mean()
        atr_median = df['ATR'].median()
        
        if recent_atr < atr_median * 0.75:
            print(f"[WARNING] Low volatility: Recent ATR {recent_atr:.2f} < Threshold {atr_median * 0.75:.2f}")
            return None
        
        # Volume check
        if vol_val < avg_vol * 0.5:
            print(f"[WARNING] Low volume: {vol_val:.0f} < Threshold {avg_vol * 0.5:.0f}")
            return None
        
        signal_info = None
        
        print(f"[SIGNAL CHECK] Close: {close_val:.2f}, BB: [{bb_lower:.2f}, {bb_upper:.2f}], RSI: {rsi_val:.1f}, MACD: {macd_val:.2f}/{macd_sig:.2f}")
        
        # CALL signal
        if (close_val > bb_upper and macd_val > macd_sig and 50 <= rsi_val <= 85):
            entry_price = close_val
            stop_loss = entry_price - atr_val
            target = entry_price + 10  # Fixed 10 points target
            
            signal_info = {
                'signal': 'CALL',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': min(1.0, (rsi_val - 50) / 35),
                'reason': f'Bullish Breakout - RSI: {rsi_val:.1f}, MACD Bullish',
                'atr': atr_val
            }
            print(f"[CALL SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        
        # PUT signal
        elif (close_val < bb_lower and macd_val < macd_sig and 15 <= rsi_val <= 50):
            entry_price = close_val
            stop_loss = entry_price + atr_val
            target = entry_price - 10  # Fixed 10 points target
            
            signal_info = {
                'signal': 'PUT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': min(1.0, (50 - rsi_val) / 35),
                'reason': f'Bearish Breakout - RSI: {rsi_val:.1f}, MACD Bearish',
                'atr': atr_val
            }
            print(f"[PUT SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        else:
            print("[WAITING] No signal - Conditions not met")
        
        return signal_info
    
    def get_info(self):
        """Get strategy information"""
        return self.description


class OpeningRangeBreakoutStrategy:
    """
    Opening Range Breakout Strategy
    Based on opening-range-breakout-fno.py
    """
    
    def __init__(self):
        self.name = "Opening Range Breakout"
        self.description = """
        <h3>Opening Range Breakout (ORB)</h3>
        <p><b>Logic:</b></p>
        <ul>
            <li>First 15-30 min sets opening range</li>
            <li>Entry on breakout with volume confirmation</li>
            <li>Mean reversion on strong opening moves</li>
        </ul>
        <p><b>Risk/Reward:</b> 20pt SL, 30pt Target</p>
        """
        self.opening_range_high = None
        self.opening_range_low = None
        self.range_set = False
    
    def calc_atr(self, data, period=14):
        """Calculate ATR"""
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def calc_rsi(self, data, period=14):
        """Calculate RSI"""
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def add_indicators(self, df):
        """Add indicators"""
        df['ATR'] = self.calc_atr(df)
        df['RSI'] = self.calc_rsi(df)
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['AvgVol'] = df['Volume'].rolling(window=20).mean()
        return df
    
    def get_signal(self, df):
        """Get current trading signal"""
        if len(df) < 20:
            return None
        
        # Add indicators if not present
        if 'ATR' not in df.columns:
            df = self.add_indicators(df)
        
        current_time = df.index[-1].time()
        
        # Calculate opening range fresh from current data (first 15 min: 9:15 - 9:30)
        opening_candles = df.between_time('09:15', '09:30')
        if len(opening_candles) >= 3:
            opening_range_high = opening_candles['High'].max().item()
            opening_range_low = opening_candles['Low'].min().item()
            if not self.range_set:
                print(f"[ORB] Opening Range Set - High: {opening_range_high:.2f}, Low: {opening_range_low:.2f}")
                self.range_set = True
        else:
            return None
        
        # Only generate signals after 9:30
        if current_time.hour == 9 and current_time.minute < 30:
            return None
        
        last = df.iloc[-1]
        close_val = last['Close'].item()
        high_val = last['High'].item()
        low_val = last['Low'].item()
        vol_val = last['Volume'].item()
        avg_vol = last['AvgVol'].item()
        
        # Volume confirmation
        if vol_val < avg_vol * 1.2:
            print(f"[ORB] Low volume: {vol_val:.0f} < {avg_vol * 1.2:.0f}")
            return None
        
        signal_info = None
        
        print(f"[SIGNAL CHECK] Close: {close_val:.2f}, Range: [{opening_range_low:.2f}, {opening_range_high:.2f}], Vol: {vol_val:.0f}/{avg_vol:.0f}")
        
        # Bullish breakout
        if close_val > opening_range_high:
            entry_price = close_val
            stop_loss = opening_range_low
            target = entry_price + 10  # Fixed 10 points target
            
            signal_info = {
                'signal': 'CALL',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': 0.75,
                'reason': f'Breakout above opening range high ({opening_range_high:.2f})',
                'atr': 50.0  # Default ATR estimate
            }
            print(f"[CALL SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        
        # Bearish breakdown
        elif close_val < opening_range_low:
            entry_price = close_val
            stop_loss = opening_range_high
            target = entry_price - 10  # Fixed 10 points target
            
            signal_info = {
                'signal': 'PUT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': 0.75,
                'reason': f'Breakdown below opening range low ({opening_range_low:.2f})',
                'atr': 50.0  # Default ATR estimate
            }
            print(f"[PUT SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        else:
            print("[WAITING] No signal - Price within range")
        
        return signal_info
    
    def get_info(self):
        """Get strategy information"""
        return self.description


class SidewaysStrategy:
    """
    Sideways Market Strategy
    Based on sideways.py
    """
    
    def __init__(self):
        self.name = "Sideways Market Strategy"
        self.description = """
        <h3>Sideways Market Range Trading</h3>
        <p><b>Entry Rules:</b></p>
        <ul>
            <li>ADX < 25 (Sideways market)</li>
            <li>Short at resistance with RSI > 55</li>
            <li>Target support level</li>
        </ul>
        <p><b>Risk/Reward:</b> 1:2 minimum</p>
        """
        self.support = None
        self.resistance = None
    
    def calc_atr(self, df, period=14):
        """Calculate ATR"""
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def calc_rsi(self, df, period=14):
        """Calculate RSI"""
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calc_adx(self, df, period=14):
        """Calculate ADX (Average Directional Index)"""
        # Ensure we're working with Series, not DataFrames
        high = df['High'].squeeze()
        low = df['Low'].squeeze()
        
        # Calculate +DM and -DM
        high_diff = high.diff()
        low_diff = -low.diff()
        
        # Use .where() to create the directional movement series
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        # Get ATR
        atr = self.calc_atr(df, period)
        if isinstance(atr, pd.DataFrame):
            atr = atr.squeeze()
        
        # Calculate +DI and -DI
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        # Calculate DX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # Calculate ADX (smoothed DX)
        adx = dx.rolling(window=period).mean()
        
        # Ensure result is a Series
        if isinstance(adx, pd.DataFrame):
            adx = adx.squeeze()
        
        return adx
    
    def calc_bollinger(self, df, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        sma = df['Close'].rolling(window=period).mean()
        std = df['Close'].rolling(window=period).std()
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        return upper, lower, sma
    
    def add_indicators(self, df):
        """Add indicators"""
        df['ATR'] = self.calc_atr(df)
        df['RSI'] = self.calc_rsi(df)
        df['ADX'] = self.calc_adx(df)
        df['BB_upper'], df['BB_lower'], df['BB_middle'] = self.calc_bollinger(df)
        df['AvgVol'] = df['Volume'].rolling(window=20).mean()
        
        # Calculate support and resistance
        lookback = 20
        df['Resistance'] = df['High'].rolling(window=lookback).max()
        df['Support'] = df['Low'].rolling(window=lookback).min()
        
        return df
    
    def get_signal(self, df):
        """Get current trading signal"""
        if len(df) < 30:
            return None
        
        # Add indicators if not present
        if 'ADX' not in df.columns:
            df = self.add_indicators(df)
        
        last = df.iloc[-1]
        
        # Check for NaN - extract scalar values
        try:
            close_val = last['Close'].item()
            adx_val = last['ADX'].item()
            rsi_val = last['RSI'].item()
            atr_val = last['ATR'].item()
            resistance = last['Resistance'].item()
            support = last['Support'].item()
            vol_val = last['Volume'].item()
            avg_vol = last['AvgVol'].item()
            
            if pd.isna(adx_val) or pd.isna(rsi_val) or pd.isna(atr_val):
                return None
        except (ValueError, TypeError, KeyError):
            return None
        
        # Only trade in sideways market
        if adx_val >= 25:
            print(f"[SIDEWAYS] Not sideways - ADX {adx_val:.1f} >= 25")
            return None
        
        # Volume check
        if vol_val < avg_vol * 0.5:
            print(f"[WARNING] Low volume: {vol_val:.0f} < {avg_vol * 0.5:.0f}")
            return None
        
        signal_info = None
        
        print(f"[SIGNAL CHECK] Close: {close_val:.2f}, Range: [{support:.2f}, {resistance:.2f}], ADX: {adx_val:.1f}, RSI: {rsi_val:.1f}")
        
        # SHORT at resistance
        if close_val >= resistance * 0.985 and rsi_val > 55:  # Within 1.5% of resistance
            entry_price = close_val
            stop_loss = resistance + atr_val * 1.2
            target = entry_price - 10  # Fixed 10 points target
            
            signal_info = {
                'signal': 'PUT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': min(1.0, (rsi_val - 55) / 30),
                'reason': f'Sideways market - Short at resistance. ADX: {adx_val:.1f}, RSI: {rsi_val:.1f}'
            }
            print(f"[PUT SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        
        # LONG at support (optional - less reliable)
        elif close_val <= support * 1.015 and rsi_val < 45:  # Within 1.5% of support
            entry_price = close_val
            stop_loss = support - atr_val * 1.2
            target = entry_price + 10  # Fixed 10 points target
            
            signal_info = {
                'signal': 'CALL',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': min(1.0, (45 - rsi_val) / 30),
                'reason': f'Sideways market - Long at support. ADX: {adx_val:.1f}, RSI: {rsi_val:.1f}',
                'atr': atr_val
            }
            print(f"[CALL SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        else:
            print("[WAITING] No signal - Not at support/resistance")
        
        return signal_info
    
    def get_info(self):
        """Get strategy information"""
        return self.description


class MomentumBreakoutStrategy:
    """
    Momentum Breakout Strategy - Optimized for Crude Oil
    Uses EMA crossovers with momentum confirmation
    """
    
    def __init__(self):
        self.name = "Momentum Breakout"
        self.description = """
        <h3>Momentum Breakout Strategy</h3>
        <p><b>Best for:</b> Crude Oil (high volatility, trending)</p>
        <p><b>Entry Rules:</b></p>
        <ul>
            <li><b>CALL:</b> Fast EMA crosses above Slow EMA + RSI > 50 + Strong volume</li>
            <li><b>PUT:</b> Fast EMA crosses below Slow EMA + RSI < 50 + Strong volume</li>
        </ul>
        <p><b>Features:</b> Captures strong momentum moves, filters false breakouts</p>
        """
    
    def calc_atr(self, data, period=14):
        """Calculate Average True Range"""
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def calc_rsi(self, data, period=14):
        """Calculate RSI"""
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calc_ema(self, data, period):
        """Calculate Exponential Moving Average"""
        return data['Close'].ewm(span=period, adjust=False).mean()
    
    def add_indicators(self, df):
        """Add momentum indicators"""
        df['ATR'] = self.calc_atr(df)
        df['RSI'] = self.calc_rsi(df)
        df['EMA_fast'] = self.calc_ema(df, 9)
        df['EMA_slow'] = self.calc_ema(df, 21)
        df['EMA_trend'] = self.calc_ema(df, 50)
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        return df
    
    def get_signal(self, df):
        """Generate trading signals based on EMA crossovers and momentum"""
        df = self.add_indicators(df)
        
        if len(df) < 50:
            return None
        
        # Get latest values
        close = df['Close'].iloc[-1].item() if hasattr(df['Close'].iloc[-1], 'item') else df['Close'].iloc[-1]
        ema_fast = df['EMA_fast'].iloc[-1].item() if hasattr(df['EMA_fast'].iloc[-1], 'item') else df['EMA_fast'].iloc[-1]
        ema_slow = df['EMA_slow'].iloc[-1].item() if hasattr(df['EMA_slow'].iloc[-1], 'item') else df['EMA_slow'].iloc[-1]
        ema_trend = df['EMA_trend'].iloc[-1].item() if hasattr(df['EMA_trend'].iloc[-1], 'item') else df['EMA_trend'].iloc[-1]
        rsi = df['RSI'].iloc[-1].item() if hasattr(df['RSI'].iloc[-1], 'item') else df['RSI'].iloc[-1]
        atr = df['ATR'].iloc[-1].item() if hasattr(df['ATR'].iloc[-1], 'item') else df['ATR'].iloc[-1]
        volume = df['Volume'].iloc[-1].item() if hasattr(df['Volume'].iloc[-1], 'item') else df['Volume'].iloc[-1]
        volume_ma = df['Volume_MA'].iloc[-1].item() if hasattr(df['Volume_MA'].iloc[-1], 'item') else df['Volume_MA'].iloc[-1]
        
        # Previous values for crossover detection
        ema_fast_prev = df['EMA_fast'].iloc[-2].item() if hasattr(df['EMA_fast'].iloc[-2], 'item') else df['EMA_fast'].iloc[-2]
        ema_slow_prev = df['EMA_slow'].iloc[-2].item() if hasattr(df['EMA_slow'].iloc[-2], 'item') else df['EMA_slow'].iloc[-2]
        
        signal_info = None
        
        # Check for bullish crossover
        bullish_cross = (ema_fast > ema_slow) and (ema_fast_prev <= ema_slow_prev)
        bearish_cross = (ema_fast < ema_slow) and (ema_fast_prev >= ema_slow_prev)
        
        # Volume confirmation
        strong_volume = volume > volume_ma * 1.2
        
        print(f"[MOMENTUM] Close: {close:.2f}, EMA Fast: {ema_fast:.2f}, Slow: {ema_slow:.2f}, RSI: {rsi:.1f}, Vol: {volume:.0f}/{volume_ma:.0f}")
        
        # CALL Signal: Bullish crossover with momentum
        if bullish_cross and rsi > 50 and close > ema_trend and strong_volume:
            entry_price = close
            stop_loss = close - (atr * 2)
            target = close + 10  # Fixed 10 point target
            
            signal_info = {
                'signal': 'CALL',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': min(1.0, rsi / 100),
                'reason': f'Momentum breakout - EMA cross bullish, RSI: {rsi:.1f}',
                'atr': atr
            }
            print(f"[CALL SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        
        # PUT Signal: Bearish crossover with momentum
        elif bearish_cross and rsi < 50 and close < ema_trend and strong_volume:
            entry_price = close
            stop_loss = close + (atr * 2)
            target = close - 10  # Fixed 10 point target
            
            signal_info = {
                'signal': 'PUT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': min(1.0, (100 - rsi) / 100),
                'reason': f'Momentum breakdown - EMA cross bearish, RSI: {rsi:.1f}',
                'atr': atr
            }
            print(f"[PUT SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        else:
            print("[WAITING] No momentum signal")
        
        return signal_info
    
    def get_info(self):
        """Get strategy information"""
        return self.description


class MeanReversionStrategy:
    """
    Mean Reversion Strategy - Optimized for Gold
    Uses RSI extremes with support/resistance bounce
    """
    
    def __init__(self):
        self.name = "Mean Reversion"
        self.description = """
        <h3>Mean Reversion Strategy</h3>
        <p><b>Best for:</b> Gold (range-bound, mean-reverting)</p>
        <p><b>Entry Rules:</b></p>
        <ul>
            <li><b>CALL:</b> RSI < 30 (oversold) + Price near support + BB lower touch</li>
            <li><b>PUT:</b> RSI > 70 (overbought) + Price near resistance + BB upper touch</li>
        </ul>
        <p><b>Features:</b> Trades mean reversion, good for ranging markets</p>
        """
    
    def calc_atr(self, data, period=14):
        """Calculate Average True Range"""
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def calc_rsi(self, data, period=14):
        """Calculate RSI"""
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calc_bollinger(self, df, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        sma = df['Close'].rolling(window=period).mean()
        std = df['Close'].rolling(window=period).std()
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        return upper, lower, sma
    
    def calc_sma(self, data, period):
        """Calculate Simple Moving Average"""
        return data['Close'].rolling(window=period).mean()
    
    def add_indicators(self, df):
        """Add mean reversion indicators"""
        df['ATR'] = self.calc_atr(df)
        df['RSI'] = self.calc_rsi(df)
        df['BB_upper'], df['BB_lower'], df['BB_middle'] = self.calc_bollinger(df)
        df['SMA_20'] = self.calc_sma(df, 20)
        df['SMA_50'] = self.calc_sma(df, 50)
        
        # Calculate support and resistance (20-period highs/lows)
        lookback = 20
        df['Resistance'] = df['High'].rolling(window=lookback).max()
        df['Support'] = df['Low'].rolling(window=lookback).min()
        
        return df
    
    def get_signal(self, df):
        """Generate mean reversion signals"""
        df = self.add_indicators(df)
        
        if len(df) < 50:
            return None
        
        # Get latest values
        close = df['Close'].iloc[-1].item() if hasattr(df['Close'].iloc[-1], 'item') else df['Close'].iloc[-1]
        rsi = df['RSI'].iloc[-1].item() if hasattr(df['RSI'].iloc[-1], 'item') else df['RSI'].iloc[-1]
        bb_upper = df['BB_upper'].iloc[-1].item() if hasattr(df['BB_upper'].iloc[-1], 'item') else df['BB_upper'].iloc[-1]
        bb_lower = df['BB_lower'].iloc[-1].item() if hasattr(df['BB_lower'].iloc[-1], 'item') else df['BB_lower'].iloc[-1]
        bb_middle = df['BB_middle'].iloc[-1].item() if hasattr(df['BB_middle'].iloc[-1], 'item') else df['BB_middle'].iloc[-1]
        atr = df['ATR'].iloc[-1].item() if hasattr(df['ATR'].iloc[-1], 'item') else df['ATR'].iloc[-1]
        support = df['Support'].iloc[-1].item() if hasattr(df['Support'].iloc[-1], 'item') else df['Support'].iloc[-1]
        resistance = df['Resistance'].iloc[-1].item() if hasattr(df['Resistance'].iloc[-1], 'item') else df['Resistance'].iloc[-1]
        sma_20 = df['SMA_20'].iloc[-1].item() if hasattr(df['SMA_20'].iloc[-1], 'item') else df['SMA_20'].iloc[-1]
        sma_50 = df['SMA_50'].iloc[-1].item() if hasattr(df['SMA_50'].iloc[-1], 'item') else df['SMA_50'].iloc[-1]
        
        signal_info = None
        
        # Distance from support/resistance
        dist_to_support = close - support
        dist_to_resistance = resistance - close
        
        print(f"[MEAN REV] Close: {close:.2f}, RSI: {rsi:.1f}, BB: [{bb_lower:.2f}, {bb_upper:.2f}], S/R: [{support:.2f}, {resistance:.2f}]")
        
        # CALL Signal: Oversold near support
        if rsi < 30 and close < bb_lower and dist_to_support < (atr * 0.5):
            entry_price = close
            stop_loss = support - (atr * 1.5)
            target = close + 10  # Fixed 10 point target
            
            signal_info = {
                'signal': 'CALL',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': min(1.0, (30 - rsi) / 30),
                'reason': f'Oversold bounce - RSI: {rsi:.1f}, near support',
                'atr': atr
            }
            print(f"[CALL SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        
        # PUT Signal: Overbought near resistance
        elif rsi > 70 and close > bb_upper and dist_to_resistance < (atr * 0.5):
            entry_price = close
            stop_loss = resistance + (atr * 1.5)
            target = close - 10  # Fixed 10 point target
            
            signal_info = {
                'signal': 'PUT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': min(1.0, (rsi - 70) / 30),
                'reason': f'Overbought reversal - RSI: {rsi:.1f}, near resistance',
                'atr': atr
            }
            print(f"[PUT SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        else:
            print("[WAITING] No mean reversion signal")
        
        return signal_info
    
    def get_info(self):
        """Get strategy information"""
        return self.description
