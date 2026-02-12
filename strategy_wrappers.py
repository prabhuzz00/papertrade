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
        
        # print(f"[SIGNAL CHECK] Close: {close_val:.2f}, BB: [{bb_lower:.2f}, {bb_upper:.2f}], RSI: {rsi_val:.1f}, MACD: {macd_val:.2f}/{macd_sig:.2f}")
        
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
            # print(f"[CALL SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        
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
            # print(f"[PUT SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        else:
            # print("[WAITING] No signal - Conditions not met")
            pass
        
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
        
        # print(f"[SIGNAL CHECK] Close: {close_val:.2f}, Range: [{opening_range_low:.2f}, {opening_range_high:.2f}], Vol: {vol_val:.0f}/{avg_vol:.0f}")
        
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
            # print(f"[CALL SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        
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
            # print(f"[PUT SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        else:
            # print("[WAITING] No signal - Price within range")
            pass
        
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
            # print(f"[SIDEWAYS] Not sideways - ADX {adx_val:.1f} >= 25")
            return None
        
        # Volume check
        if vol_val < avg_vol * 0.5:
            print(f"[WARNING] Low volume: {vol_val:.0f} < {avg_vol * 0.5:.0f}")
            return None
        
        signal_info = None
        
        # print(f"[SIGNAL CHECK] Close: {close_val:.2f}, Range: [{support:.2f}, {resistance:.2f}], ADX: {adx_val:.1f}, RSI: {rsi_val:.1f}")
        
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
            # print(f"[PUT SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        
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
            # print(f"[CALL SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        else:
            # print("[WAITING] No signal - Not at support/resistance")
            pass
        
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
        
        # print(f"[MOMENTUM] Close: {close:.2f}, EMA Fast: {ema_fast:.2f}, Slow: {ema_slow:.2f}, RSI: {rsi:.1f}, Vol: {volume:.0f}/{volume_ma:.0f}")
        
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
            # print(f"[CALL SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        
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
            # print(f"[PUT SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        else:
            # print("[WAITING] No momentum signal")
            pass
        
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
        
        # print(f"[MEAN REV] Close: {close:.2f}, RSI: {rsi:.1f}, BB: [{bb_lower:.2f}, {bb_upper:.2f}], S/R: [{support:.2f}, {resistance:.2f}]")
        
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
            # print(f"[CALL SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        
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
            # print(f"[PUT SIGNAL] Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}")
        else:
            # print("[WAITING] No mean reversion signal")
            pass
        
        return signal_info
    
    def get_info(self):
        """Get strategy information"""
        return self.description


class EMACrossoverStrategy:
    """
    EMA Crossover Strategy
    9 EMA crosses 21 EMA for entry signals
    """
    
    def __init__(self):
        self.name = "EMA Crossover"
        self.description = """
        <h3>EMA Crossover Strategy</h3>
        <p><b>Entry Rules:</b></p>
        <ul>
            <li><b>CALL:</b> 9 EMA crosses above 21 EMA (bullish crossover)</li>
            <li><b>PUT:</b> 9 EMA crosses below 21 EMA (bearish crossover)</li>
        </ul>
        <p><b>Risk/Reward:</b> 1:3 ratio - Stop loss based on ATR, target 3x the risk</p>
        <p><b>Indicators:</b> 9 EMA, 21 EMA, ATR for stop loss</p>
        """
        self.prev_ema9 = None
        self.prev_ema21 = None
    
    def calc_atr(self, data, period=14):
        """Calculate Average True Range"""
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def calc_ema(self, data, period):
        """Calculate Exponential Moving Average"""
        return data['Close'].ewm(span=period, adjust=False).mean()
    
    def add_indicators(self, df):
        """Add all technical indicators to dataframe"""
        df['EMA_9'] = self.calc_ema(df, 9)
        df['EMA_21'] = self.calc_ema(df, 21)
        df['ATR'] = self.calc_atr(df)
        return df
    
    def get_signal(self, df):
        """Get current trading signal"""
        if len(df) < 30:
            return None
        
        # Add indicators if not present
        if 'EMA_9' not in df.columns:
            df = self.add_indicators(df)
        
        # Get current and previous values
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Extract values
        try:
            close = current['Close'].item() if hasattr(current['Close'], 'item') else current['Close']
            ema9_current = current['EMA_9'].item() if hasattr(current['EMA_9'], 'item') else current['EMA_9']
            ema21_current = current['EMA_21'].item() if hasattr(current['EMA_21'], 'item') else current['EMA_21']
            ema9_prev = previous['EMA_9'].item() if hasattr(previous['EMA_9'], 'item') else previous['EMA_9']
            ema21_prev = previous['EMA_21'].item() if hasattr(previous['EMA_21'], 'item') else previous['EMA_21']
            atr = current['ATR'].item() if hasattr(current['ATR'], 'item') else current['ATR']
            
            if pd.isna(ema9_current) or pd.isna(ema21_current) or pd.isna(atr):
                print("[ERROR] Invalid indicators (NaN values)")
                return None
        except (ValueError, TypeError, KeyError) as e:
            print(f"[ERROR] Error extracting indicators: {e}")
            return None
        
        signal_info = None
        
        # print(f"[EMA CROSSOVER] Close: {close:.2f}, EMA9: {ema9_current:.2f}, EMA21: {ema21_current:.2f}, ATR: {atr:.2f}")
        
        # Detect bullish crossover (9 EMA crosses above 21 EMA)
        if ema9_prev <= ema21_prev and ema9_current > ema21_current:
            entry_price = close
            stop_loss = entry_price - (atr * 1.0)  # 1 ATR stop loss
            risk = entry_price - stop_loss
            target = entry_price + (risk * 3.0)  # 1:3 risk/reward ratio
            
            signal_info = {
                'signal': 'CALL',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': min(1.0, abs(ema9_current - ema21_current) / atr),
                'reason': f'Bullish EMA Crossover - 9 EMA crossed above 21 EMA',
                'atr': atr
            }
            # print(f"[CALL SIGNAL] Bullish Crossover - Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}, R/R: 1:3")
        
        # Detect bearish crossover (9 EMA crosses below 21 EMA)
        elif ema9_prev >= ema21_prev and ema9_current < ema21_current:
            entry_price = close
            stop_loss = entry_price + (atr * 1.0)  # 1 ATR stop loss
            risk = stop_loss - entry_price
            target = entry_price - (risk * 3.0)  # 1:3 risk/reward ratio
            
            signal_info = {
                'signal': 'PUT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': min(1.0, abs(ema9_current - ema21_current) / atr),
                'reason': f'Bearish EMA Crossover - 9 EMA crossed below 21 EMA',
                'atr': atr
            }
            # print(f"[PUT SIGNAL] Bearish Crossover - Entry: {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}, R/R: 1:3")
        else:
            # No crossover detected
            if ema9_current > ema21_current:
                # print(f"[WAITING] 9 EMA above 21 EMA (bullish trend) - waiting for crossover")
                pass
            else:
                # print(f"[WAITING] 9 EMA below 21 EMA (bearish trend) - waiting for crossover")
                pass
        
        return signal_info
    
    def get_info(self):
        """Get strategy information"""
        return self.description


class FVGStrategy:
    """
    Fair Value Gap (FVG) Strategy
    
    Detects imbalance gaps in price action and trades when price returns to fill them.
    - Bullish FVG: Candle[0].High < Candle[2].Low (gap up, middle candle jumps)
    - Bearish FVG: Candle[0].Low > Candle[2].High (gap down, middle candle drops)
    - Entry when price re-enters the gap zone
    """
    
    FVG_MIN_SIZE = 10          # Minimum gap size in points
    FVG_VALIDITY_CANDLES = 20  # Gap stays valid for this many candles
    
    def __init__(self):
        self.name = "FVG Strategy"
        self.description = """
        <h3>Fair Value Gap (FVG) Strategy</h3>
        <p><b>Concept:</b> Trades price imbalances where no trading occurred.</p>
        <p><b>Entry Rules:</b></p>
        <ul>
            <li><b>CALL:</b> Bullish FVG detected (gap up) AND price returns into gap zone</li>
            <li><b>PUT:</b> Bearish FVG detected (gap down) AND price returns into gap zone</li>
        </ul>
        <p><b>Parameters:</b></p>
        <ul>
            <li>Min Gap Size: 10 points</li>
            <li>Gap Validity: 20 candles</li>
        </ul>
        """
        self._active_fvgs = []
    
    def calc_atr(self, data, period=14):
        """Calculate Average True Range"""
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def add_indicators(self, df):
        """Add ATR indicator (used for SL/Target sizing)"""
        df['ATR'] = self.calc_atr(df)
        return df
    
    def _detect_fvgs(self, df):
        """Scan the dataframe for all FVG zones within the validity window."""
        fvgs = []
        n = len(df)
        start_idx = max(0, n - self.FVG_VALIDITY_CANDLES - 3)
        
        for i in range(start_idx, n - 2):
            try:
                c0_high = df['High'].iloc[i]
                c0_low = df['Low'].iloc[i]
                c2_high = df['High'].iloc[i + 2]
                c2_low = df['Low'].iloc[i + 2]
                
                if hasattr(c0_high, 'item'):
                    c0_high = c0_high.item()
                    c0_low = c0_low.item()
                    c2_high = c2_high.item()
                    c2_low = c2_low.item()
                
                # Bullish FVG: candle[0] high < candle[2] low (gap up)
                gap_size = c2_low - c0_high
                if gap_size >= self.FVG_MIN_SIZE:
                    age = n - 1 - (i + 2)
                    if age <= self.FVG_VALIDITY_CANDLES:
                        fvgs.append({
                            'type': 'BULLISH',
                            'gap_low': c0_high,
                            'gap_high': c2_low,
                            'size': gap_size,
                            'formed_at': i + 1,
                            'age': age,
                        })
                
                # Bearish FVG: candle[0] low > candle[2] high (gap down)
                gap_size = c0_low - c2_high
                if gap_size >= self.FVG_MIN_SIZE:
                    age = n - 1 - (i + 2)
                    if age <= self.FVG_VALIDITY_CANDLES:
                        fvgs.append({
                            'type': 'BEARISH',
                            'gap_low': c2_high,
                            'gap_high': c0_low,
                            'size': gap_size,
                            'formed_at': i + 1,
                            'age': age,
                        })
            except Exception:
                continue
        
        return fvgs
    
    def _is_price_in_gap(self, price, fvg):
        """Check if current price is inside the FVG zone"""
        return fvg['gap_low'] <= price <= fvg['gap_high']
    
    def _is_gap_already_filled(self, df, fvg):
        """Check if price already traded through the entire gap after it formed"""
        formed_idx = fvg['formed_at'] + 1
        n = len(df)
        if formed_idx >= n - 1:
            return False
        
        for i in range(formed_idx + 1, n - 1):
            try:
                low = df['Low'].iloc[i]
                high = df['High'].iloc[i]
                if hasattr(low, 'item'):
                    low, high = low.item(), high.item()
                
                if fvg['type'] == 'BULLISH' and low <= fvg['gap_low']:
                    return True
                if fvg['type'] == 'BEARISH' and high >= fvg['gap_high']:
                    return True
            except Exception:
                continue
        
        return False
    
    def get_signal(self, df):
        """Get current trading signal based on FVG detection and fill"""
        if len(df) < 10:
            return None
        
        if 'ATR' not in df.columns:
            df = self.add_indicators(df)
        
        last = df.iloc[-1]
        try:
            close = last['Close'].item() if hasattr(last['Close'], 'item') else float(last['Close'])
            atr = last['ATR'].item() if hasattr(last['ATR'], 'item') else float(last['ATR'])
            if pd.isna(close) or pd.isna(atr):
                return None
        except Exception:
            return None
        
        fvgs = self._detect_fvgs(df)
        self._active_fvgs = fvgs
        
        if not fvgs:
            return None
        
        for fvg in fvgs:
            if self._is_gap_already_filled(df, fvg):
                continue
            
            if not self._is_price_in_gap(close, fvg):
                continue
            
            if fvg['type'] == 'BULLISH':
                entry_price = close
                stop_loss = fvg['gap_low'] - (atr * 0.5)
                target = fvg['gap_high'] + (atr * 1.0)
                
                return {
                    'signal': 'CALL',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'target': target,
                    'confidence': min(1.0, fvg['size'] / (atr * 2)) if atr > 0 else 0.5,
                    'reason': f"Bullish FVG fill - Gap [{fvg['gap_low']:.0f}-{fvg['gap_high']:.0f}], size={fvg['size']:.0f}, age={fvg['age']}",
                    'atr': atr,
                }
            
            elif fvg['type'] == 'BEARISH':
                entry_price = close
                stop_loss = fvg['gap_high'] + (atr * 0.5)
                target = fvg['gap_low'] - (atr * 1.0)
                
                return {
                    'signal': 'PUT',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'target': target,
                    'confidence': min(1.0, fvg['size'] / (atr * 2)) if atr > 0 else 0.5,
                    'reason': f"Bearish FVG fill - Gap [{fvg['gap_low']:.0f}-{fvg['gap_high']:.0f}], size={fvg['size']:.0f}, age={fvg['age']}",
                    'atr': atr,
                }
        
        return None
    
    def get_info(self):
        """Get strategy information"""
        return self.description


class LiquiditySweepStrategy:
    """
    Liquidity Sweep Strategy
    
    Detects when price briefly spikes beyond recent highs/lows to hunt stop losses,
    then reverses. Smart money sweeps retail stops before moving the other way.
    
    - Bearish sweep: price breaks above recent high but closes below it  → PUT
    - Bullish sweep: price breaks below recent low but closes above it   → CALL
    """
    
    SWEEP_LOOKBACK = 20    # Candles to establish recent high/low
    SWEEP_THRESHOLD = 5    # Minimum points beyond the level to count as a sweep
    
    def __init__(self):
        self.name = "Liquidity Sweep"
        self.description = """
        <h3>Liquidity Sweep Strategy</h3>
        <p><b>Concept:</b> Smart money hunts retail stop losses placed beyond obvious
        highs and lows. Price briefly spikes through a key level, triggers stops,
        then reverses sharply.</p>
        <p><b>Entry Rules:</b></p>
        <ul>
            <li><b>PUT:</b> Price wick breaks above the recent high by ≥ 5 pts,
                but closes back below it (bearish sweep)</li>
            <li><b>CALL:</b> Price wick breaks below the recent low by ≥ 5 pts,
                but closes back above it (bullish sweep)</li>
        </ul>
        <p><b>Parameters:</b></p>
        <ul>
            <li>Lookback: 20 candles</li>
            <li>Sweep Threshold: 5 points</li>
        </ul>
        """
    
    def calc_atr(self, data, period=14):
        """Calculate Average True Range"""
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def add_indicators(self, df):
        """Add ATR and recent high/low levels"""
        df['ATR'] = self.calc_atr(df)
        df['Recent_High'] = df['High'].rolling(self.SWEEP_LOOKBACK).max()
        df['Recent_Low'] = df['Low'].rolling(self.SWEEP_LOOKBACK).min()
        return df
    
    def get_signal(self, df):
        """Detect liquidity sweeps and generate signals"""
        if len(df) < self.SWEEP_LOOKBACK + 5:
            return None
        
        if 'ATR' not in df.columns or 'Recent_High' not in df.columns:
            df = self.add_indicators(df)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        try:
            close = last['Close'].item() if hasattr(last['Close'], 'item') else float(last['Close'])
            high = last['High'].item() if hasattr(last['High'], 'item') else float(last['High'])
            low = last['Low'].item() if hasattr(last['Low'], 'item') else float(last['Low'])
            atr = last['ATR'].item() if hasattr(last['ATR'], 'item') else float(last['ATR'])
            if pd.isna(close) or pd.isna(atr):
                return None
        except Exception:
            return None
        
        # Recent high/low computed from candles BEFORE the current one
        # to avoid including the current candle's own sweep in the level
        lookback_slice = df.iloc[-(self.SWEEP_LOOKBACK + 1):-1]
        recent_high = lookback_slice['High'].max()
        recent_low = lookback_slice['Low'].min()
        if hasattr(recent_high, 'item'):
            recent_high = recent_high.item()
            recent_low = recent_low.item()
        
        if pd.isna(recent_high) or pd.isna(recent_low):
            return None
        
        signal_info = None
        
        # --- Bearish liquidity sweep (hunted highs) ---
        # Current candle's HIGH exceeds recent high by threshold, but CLOSE is below it
        sweep_above = high - recent_high
        if sweep_above >= self.SWEEP_THRESHOLD and close < recent_high:
            entry_price = close
            stop_loss = high + (atr * 0.3)
            target = close - (atr * 2.0)
            confidence = min(1.0, sweep_above / (atr * 0.5)) if atr > 0 else 0.5
            
            signal_info = {
                'signal': 'PUT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': confidence,
                'reason': f"Bearish liquidity sweep - High {high:.0f} swept {recent_high:.0f} by {sweep_above:.0f} pts, closed back at {close:.0f}",
                'atr': atr,
            }
        
        # --- Bullish liquidity sweep (hunted lows) ---
        # Current candle's LOW dips below recent low by threshold, but CLOSE is above it
        sweep_below = recent_low - low
        if sweep_below >= self.SWEEP_THRESHOLD and close > recent_low:
            entry_price = close
            stop_loss = low - (atr * 0.3)
            target = close + (atr * 2.0)
            confidence = min(1.0, sweep_below / (atr * 0.5)) if atr > 0 else 0.5
            
            # If both sweeps happen (extreme volatility), prefer the stronger one
            if signal_info is not None:
                if sweep_below > sweep_above:
                    signal_info = {
                        'signal': 'CALL',
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'target': target,
                        'confidence': confidence,
                        'reason': f"Bullish liquidity sweep - Low {low:.0f} swept {recent_low:.0f} by {sweep_below:.0f} pts, closed back at {close:.0f}",
                        'atr': atr,
                    }
            else:
                signal_info = {
                    'signal': 'CALL',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'target': target,
                    'confidence': confidence,
                    'reason': f"Bullish liquidity sweep - Low {low:.0f} swept {recent_low:.0f} by {sweep_below:.0f} pts, closed back at {close:.0f}",
                    'atr': atr,
                }
        
        return signal_info
    
    def get_info(self):
        """Get strategy information"""
        return self.description


class OrderBlockStrategy:
    """
    Order Block Strategy
    
    Identifies the last strong candle before a significant move (where institutions
    placed their orders). When price returns to that zone it acts as support/resistance.
    
    - Bullish OB: strong green candle followed by a rally → when revisited, reversal expected → PUT
    - Bearish OB: strong red candle followed by a drop  → when revisited, reversal expected → CALL
    """
    
    OB_LOOKBACK = 50           # Candles to search for order blocks
    OB_MIN_BODY_PERCENT = 0.60 # Minimum body-to-range ratio for a "strong" candle
    OB_MIN_MOVE_MULTIPLIER = 1.5  # Move after OB must be >= 1.5x the OB candle range
    
    def __init__(self):
        self.name = "Order Block"
        self.description = """
        <h3>Order Block Strategy</h3>
        <p><b>Concept:</b> The last strong candle before a significant move marks
        where institutions placed orders. Price respects these zones when it returns.</p>
        <p><b>Entry Rules:</b></p>
        <ul>
            <li><b>CALL:</b> Strong bullish candle → upward move → price returns to
                OB zone (support)</li>
            <li><b>PUT:</b> Strong bearish candle → downward move → price returns to
                OB zone (resistance)</li>
        </ul>
        <p><b>Parameters:</b></p>
        <ul>
            <li>Lookback: 50 candles</li>
            <li>Min Body: 60% of candle range</li>
            <li>Min Move After OB: 1.5× candle range</li>
        </ul>
        """
    
    def calc_atr(self, data, period=14):
        """Calculate Average True Range"""
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def add_indicators(self, df):
        """Add ATR indicator"""
        df['ATR'] = self.calc_atr(df)
        return df
    
    def _is_strong_candle(self, row):
        """Check if a candle has a large body relative to its range"""
        try:
            o = row['Open'].item() if hasattr(row['Open'], 'item') else float(row['Open'])
            h = row['High'].item() if hasattr(row['High'], 'item') else float(row['High'])
            l = row['Low'].item() if hasattr(row['Low'], 'item') else float(row['Low'])
            c = row['Close'].item() if hasattr(row['Close'], 'item') else float(row['Close'])
        except Exception:
            return False, None, None, None, None
        
        candle_range = h - l
        if candle_range <= 0:
            return False, None, None, None, None
        
        body = abs(c - o)
        body_pct = body / candle_range
        
        if body_pct < self.OB_MIN_BODY_PERCENT:
            return False, None, None, None, None
        
        direction = 'BULLISH' if c > o else 'BEARISH'
        return True, direction, candle_range, l, h
    
    def _detect_order_blocks(self, df):
        """Scan for valid order blocks within the lookback window"""
        n = len(df)
        order_blocks = []
        start = max(0, n - self.OB_LOOKBACK - 1)
        
        for i in range(start, n - 3):
            row = df.iloc[i]
            is_strong, direction, candle_range, ob_low, ob_high = self._is_strong_candle(row)
            if not is_strong:
                continue
            
            # Check that a significant move followed in the OB direction
            min_move = candle_range * self.OB_MIN_MOVE_MULTIPLIER
            
            # Look at the next few candles for the move
            move_window = min(i + 8, n)
            if direction == 'BULLISH':
                max_high_after = df['High'].iloc[i + 1:move_window].max()
                if hasattr(max_high_after, 'item'):
                    max_high_after = max_high_after.item()
                move = max_high_after - ob_high
                if move >= min_move:
                    # Check that the OB zone hasn't been violated (price didn't
                    # close below OB low between formation and now)
                    violated = False
                    for j in range(i + 1, n - 1):
                        cl = df['Close'].iloc[j]
                        if hasattr(cl, 'item'):
                            cl = cl.item()
                        if cl < ob_low:
                            violated = True
                            break
                    if not violated:
                        order_blocks.append({
                            'type': 'BULLISH',
                            'ob_low': ob_low,
                            'ob_high': ob_high,
                            'candle_range': candle_range,
                            'move_size': move,
                            'formed_at': i,
                            'age': n - 1 - i,
                        })
            
            elif direction == 'BEARISH':
                min_low_after = df['Low'].iloc[i + 1:move_window].min()
                if hasattr(min_low_after, 'item'):
                    min_low_after = min_low_after.item()
                move = ob_low - min_low_after
                if move >= min_move:
                    violated = False
                    for j in range(i + 1, n - 1):
                        cl = df['Close'].iloc[j]
                        if hasattr(cl, 'item'):
                            cl = cl.item()
                        if cl > ob_high:
                            violated = True
                            break
                    if not violated:
                        order_blocks.append({
                            'type': 'BEARISH',
                            'ob_low': ob_low,
                            'ob_high': ob_high,
                            'candle_range': candle_range,
                            'move_size': move,
                            'formed_at': i,
                            'age': n - 1 - i,
                        })
        
        return order_blocks
    
    def get_signal(self, df):
        """Generate signal when price returns to an order block zone"""
        if len(df) < self.OB_LOOKBACK:
            return None
        
        if 'ATR' not in df.columns:
            df = self.add_indicators(df)
        
        last = df.iloc[-1]
        try:
            close = last['Close'].item() if hasattr(last['Close'], 'item') else float(last['Close'])
            low = last['Low'].item() if hasattr(last['Low'], 'item') else float(last['Low'])
            high = last['High'].item() if hasattr(last['High'], 'item') else float(last['High'])
            atr = last['ATR'].item() if hasattr(last['ATR'], 'item') else float(last['ATR'])
            if pd.isna(close) or pd.isna(atr):
                return None
        except Exception:
            return None
        
        order_blocks = self._detect_order_blocks(df)
        if not order_blocks:
            return None
        
        # Check the most recent (freshest) OB first
        order_blocks.sort(key=lambda ob: ob['age'])
        
        for ob in order_blocks:
            # Price must be touching / inside the OB zone on the current candle
            if ob['type'] == 'BULLISH':
                # Price dipping into bullish OB = reversal expected → PUT
                if low <= ob['ob_high'] and close >= ob['ob_low']:
                    entry_price = close
                    stop_loss = ob['ob_high'] + (atr * 0.5)
                    target = close - (atr * 2.0)
                    confidence = min(1.0, ob['move_size'] / (atr * 3)) if atr > 0 else 0.5
                    
                    return {
                        'signal': 'PUT',
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'target': target,
                        'confidence': confidence,
                        'reason': f"Bullish OB reversal [{ob['ob_low']:.0f}-{ob['ob_high']:.0f}], move={ob['move_size']:.0f} pts, age={ob['age']} candles",
                        'atr': atr,
                    }
            
            elif ob['type'] == 'BEARISH':
                # Price rising into bearish OB = reversal expected → CALL
                if high >= ob['ob_low'] and close <= ob['ob_high']:
                    entry_price = close
                    stop_loss = ob['ob_low'] - (atr * 0.5)
                    target = close + (atr * 2.0)
                    confidence = min(1.0, ob['move_size'] / (atr * 3)) if atr > 0 else 0.5
                    
                    return {
                        'signal': 'CALL',
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'target': target,
                        'confidence': confidence,
                        'reason': f"Bearish OB reversal [{ob['ob_low']:.0f}-{ob['ob_high']:.0f}], move={ob['move_size']:.0f} pts, age={ob['age']} candles",
                        'atr': atr,
                    }
        
        return None
    
    def get_info(self):
        """Get strategy information"""
        return self.description


class PremiumDiscountStrategy:
    """
    Premium/Discount Zone Strategy
    
    Determines if price is expensive (premium) or cheap (discount) relative to
    the recent range. Combines zone detection with a simple market structure
    shift (MSS) confirmation to avoid catching falling knives.
    
    - Discount zone (bottom 30%) + bullish MSS → CALL
    - Premium zone (top 30%)    + bearish MSS → PUT
    """
    
    RANGE_LOOKBACK = 100       # Candles to establish the range
    PREMIUM_THRESHOLD = 0.70   # Top 30% = premium
    DISCOUNT_THRESHOLD = 0.30  # Bottom 30% = discount
    MSS_LOOKBACK = 5           # Candles to detect structure shift
    
    def __init__(self):
        self.name = "Premium/Discount Zone"
        self.description = """
        <h3>Premium/Discount Zone Strategy</h3>
        <p><b>Concept:</b> Determine if price is expensive (premium) or cheap
        (discount) relative to the recent range, then trade reversals with
        market structure shift confirmation.</p>
        <p><b>Entry Rules:</b></p>
        <ul>
            <li><b>CALL:</b> Price in discount zone (bottom 30%) AND bullish
                market structure shift (higher low → break above recent swing high)</li>
            <li><b>PUT:</b> Price in premium zone (top 30%) AND bearish
                market structure shift (lower high → break below recent swing low)</li>
        </ul>
        <p><b>Parameters:</b></p>
        <ul>
            <li>Range Lookback: 100 candles</li>
            <li>Premium Threshold: 70% (top 30%)</li>
            <li>Discount Threshold: 30% (bottom 30%)</li>
            <li>MSS Lookback: 5 candles</li>
        </ul>
        """
    
    def calc_atr(self, data, period=14):
        """Calculate Average True Range"""
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def add_indicators(self, df):
        """Add ATR and range position indicator"""
        df['ATR'] = self.calc_atr(df)
        rolling_high = df['High'].rolling(self.RANGE_LOOKBACK).max()
        rolling_low = df['Low'].rolling(self.RANGE_LOOKBACK).min()
        range_size = rolling_high - rolling_low
        # Avoid division by zero
        range_size = range_size.replace(0, np.nan)
        df['Range_Position'] = (df['Close'] - rolling_low) / range_size
        df['Range_High'] = rolling_high
        df['Range_Low'] = rolling_low
        return df
    
    def _detect_bullish_mss(self, df):
        """
        Simple bullish market structure shift:
        Recent candles form a higher low AND current close breaks above
        the highest high of the last MSS_LOOKBACK candles (excluding current).
        """
        n = len(df)
        if n < self.MSS_LOOKBACK + 2:
            return False
        
        window = df.iloc[-(self.MSS_LOOKBACK + 1):-1]  # exclude current candle
        
        # Find the swing low in the window
        lows = []
        for i in range(len(window)):
            val = window['Low'].iloc[i]
            if hasattr(val, 'item'):
                val = val.item()
            lows.append(val)
        
        # Check higher low pattern: second half low > first half low
        mid = len(lows) // 2
        first_half_low = min(lows[:mid]) if lows[:mid] else None
        second_half_low = min(lows[mid:]) if lows[mid:] else None
        
        if first_half_low is None or second_half_low is None:
            return False
        
        if second_half_low <= first_half_low:
            return False
        
        # Current close breaks above the window's highest high
        window_high = window['High'].max()
        if hasattr(window_high, 'item'):
            window_high = window_high.item()
        
        current_close = df['Close'].iloc[-1]
        if hasattr(current_close, 'item'):
            current_close = current_close.item()
        
        return current_close > window_high
    
    def _detect_bearish_mss(self, df):
        """
        Simple bearish market structure shift:
        Recent candles form a lower high AND current close breaks below
        the lowest low of the last MSS_LOOKBACK candles (excluding current).
        """
        n = len(df)
        if n < self.MSS_LOOKBACK + 2:
            return False
        
        window = df.iloc[-(self.MSS_LOOKBACK + 1):-1]
        
        highs = []
        for i in range(len(window)):
            val = window['High'].iloc[i]
            if hasattr(val, 'item'):
                val = val.item()
            highs.append(val)
        
        mid = len(highs) // 2
        first_half_high = max(highs[:mid]) if highs[:mid] else None
        second_half_high = max(highs[mid:]) if highs[mid:] else None
        
        if first_half_high is None or second_half_high is None:
            return False
        
        if second_half_high >= first_half_high:
            return False
        
        window_low = window['Low'].min()
        if hasattr(window_low, 'item'):
            window_low = window_low.item()
        
        current_close = df['Close'].iloc[-1]
        if hasattr(current_close, 'item'):
            current_close = current_close.item()
        
        return current_close < window_low
    
    def get_signal(self, df):
        """Generate signal based on premium/discount zone + MSS confirmation"""
        if len(df) < self.RANGE_LOOKBACK + 5:
            return None
        
        if 'ATR' not in df.columns or 'Range_Position' not in df.columns:
            df = self.add_indicators(df)
        
        last = df.iloc[-1]
        try:
            close = last['Close'].item() if hasattr(last['Close'], 'item') else float(last['Close'])
            atr = last['ATR'].item() if hasattr(last['ATR'], 'item') else float(last['ATR'])
            range_pos = last['Range_Position'].item() if hasattr(last['Range_Position'], 'item') else float(last['Range_Position'])
            range_high = last['Range_High'].item() if hasattr(last['Range_High'], 'item') else float(last['Range_High'])
            range_low = last['Range_Low'].item() if hasattr(last['Range_Low'], 'item') else float(last['Range_Low'])
            if pd.isna(close) or pd.isna(atr) or pd.isna(range_pos):
                return None
        except Exception:
            return None
        
        range_size = range_high - range_low
        
        # --- Discount zone: buy the dip ---
        if range_pos <= self.DISCOUNT_THRESHOLD:
            if self._detect_bullish_mss(df):
                entry_price = close
                stop_loss = range_low - (atr * 0.5)
                target = close + (atr * 2.0)
                # Deeper discount = higher confidence
                confidence = min(1.0, (self.DISCOUNT_THRESHOLD - range_pos) / self.DISCOUNT_THRESHOLD + 0.4)
                
                return {
                    'signal': 'CALL',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'target': target,
                    'confidence': confidence,
                    'reason': f"Discount zone ({range_pos:.0%}) + bullish MSS — Range [{range_low:.0f}-{range_high:.0f}], size={range_size:.0f}",
                    'atr': atr,
                }
        
        # --- Premium zone: sell the rip ---
        if range_pos >= self.PREMIUM_THRESHOLD:
            if self._detect_bearish_mss(df):
                entry_price = close
                stop_loss = range_high + (atr * 0.5)
                target = close - (atr * 2.0)
                confidence = min(1.0, (range_pos - self.PREMIUM_THRESHOLD) / (1 - self.PREMIUM_THRESHOLD) + 0.4)
                
                return {
                    'signal': 'PUT',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'target': target,
                    'confidence': confidence,
                    'reason': f"Premium zone ({range_pos:.0%}) + bearish MSS — Range [{range_low:.0f}-{range_high:.0f}], size={range_size:.0f}",
                    'atr': atr,
                }
        
        return None
    
    def get_info(self):
        """Get strategy information"""
        return self.description


class MSSStrategy:
    """
    Market Structure Shift (MSS) Strategy
    
    Detects when price breaks out of the current trend structure, signaling a
    potential reversal.
    
    - Identifies swing highs / swing lows using a configurable pivot strength
    - Classifies trend as uptrend (HH + HL) or downtrend (LH + LL)
    - Bullish MSS: price in downtrend breaks above last swing high → CALL
    - Bearish MSS: price in uptrend breaks below last swing low  → PUT
    """
    
    PIVOT_STRENGTH = 3     # Bars left & right to confirm a swing point
    MIN_SWINGS = 3         # Minimum swing points needed to establish a trend
    LOOKBACK = 60          # Candles to scan for swing points
    
    def __init__(self):
        self.name = "Market Structure Shift"
        self.description = """
        <h3>Market Structure Shift (MSS) Strategy</h3>
        <p><b>Concept:</b> When price breaks the established trend structure
        (sequence of higher-highs/higher-lows or lower-highs/lower-lows),
        it signals a potential reversal.</p>
        <p><b>Entry Rules:</b></p>
        <ul>
            <li><b>CALL:</b> Downtrend identified (lower highs + lower lows)
                AND price breaks above the last swing high → bullish MSS</li>
            <li><b>PUT:</b> Uptrend identified (higher highs + higher lows)
                AND price breaks below the last swing low → bearish MSS</li>
        </ul>
        <p><b>Parameters:</b></p>
        <ul>
            <li>Pivot Strength: 3 bars each side</li>
            <li>Minimum Swings: 3</li>
            <li>Lookback: 60 candles</li>
        </ul>
        """
    
    def calc_atr(self, data, period=14):
        """Calculate Average True Range"""
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def add_indicators(self, df):
        """Add ATR indicator"""
        df['ATR'] = self.calc_atr(df)
        return df
    
    def _find_swing_highs(self, df, start_idx):
        """Find swing highs: a bar whose High is higher than PIVOT_STRENGTH bars on each side"""
        swings = []
        n = len(df)
        ps = self.PIVOT_STRENGTH
        
        for i in range(start_idx + ps, n - ps):
            try:
                h = df['High'].iloc[i]
                if hasattr(h, 'item'):
                    h = h.item()
                
                is_swing = True
                for j in range(1, ps + 1):
                    left = df['High'].iloc[i - j]
                    right = df['High'].iloc[i + j]
                    if hasattr(left, 'item'):
                        left = left.item()
                    if hasattr(right, 'item'):
                        right = right.item()
                    if h < left or h < right:
                        is_swing = False
                        break
                
                if is_swing:
                    swings.append({'index': i, 'price': h})
            except Exception:
                continue
        
        return swings
    
    def _find_swing_lows(self, df, start_idx):
        """Find swing lows: a bar whose Low is lower than PIVOT_STRENGTH bars on each side"""
        swings = []
        n = len(df)
        ps = self.PIVOT_STRENGTH
        
        for i in range(start_idx + ps, n - ps):
            try:
                l = df['Low'].iloc[i]
                if hasattr(l, 'item'):
                    l = l.item()
                
                is_swing = True
                for j in range(1, ps + 1):
                    left = df['Low'].iloc[i - j]
                    right = df['Low'].iloc[i + j]
                    if hasattr(left, 'item'):
                        left = left.item()
                    if hasattr(right, 'item'):
                        right = right.item()
                    if l > left or l > right:
                        is_swing = False
                        break
                
                if is_swing:
                    swings.append({'index': i, 'price': l})
            except Exception:
                continue
        
        return swings
    
    def _classify_trend(self, swing_highs, swing_lows):
        """
        Classify trend from swing points.
        Returns 'UPTREND', 'DOWNTREND', or None.
        """
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None
        
        # Use the last few swing points
        recent_highs = [s['price'] for s in swing_highs[-self.MIN_SWINGS:]]
        recent_lows = [s['price'] for s in swing_lows[-self.MIN_SWINGS:]]
        
        # Count higher-highs and higher-lows
        hh_count = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i] > recent_highs[i - 1])
        hl_count = sum(1 for i in range(1, len(recent_lows)) if recent_lows[i] > recent_lows[i - 1])
        
        # Count lower-highs and lower-lows
        lh_count = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i] < recent_highs[i - 1])
        ll_count = sum(1 for i in range(1, len(recent_lows)) if recent_lows[i] < recent_lows[i - 1])
        
        total = max(len(recent_highs) - 1, 1)
        
        if hh_count / total >= 0.5 and hl_count / total >= 0.5:
            return 'UPTREND'
        elif lh_count / total >= 0.5 and ll_count / total >= 0.5:
            return 'DOWNTREND'
        
        return None
    
    def get_signal(self, df):
        """Detect market structure shifts and generate reversal signals"""
        if len(df) < self.LOOKBACK:
            return None
        
        if 'ATR' not in df.columns:
            df = self.add_indicators(df)
        
        last = df.iloc[-1]
        try:
            close = last['Close'].item() if hasattr(last['Close'], 'item') else float(last['Close'])
            atr = last['ATR'].item() if hasattr(last['ATR'], 'item') else float(last['ATR'])
            if pd.isna(close) or pd.isna(atr):
                return None
        except Exception:
            return None
        
        n = len(df)
        start_idx = max(0, n - self.LOOKBACK)
        
        swing_highs = self._find_swing_highs(df, start_idx)
        swing_lows = self._find_swing_lows(df, start_idx)
        
        if len(swing_highs) < self.MIN_SWINGS or len(swing_lows) < self.MIN_SWINGS:
            return None
        
        trend = self._classify_trend(swing_highs, swing_lows)
        if trend is None:
            return None
        
        last_swing_high = swing_highs[-1]['price']
        last_swing_low = swing_lows[-1]['price']
        
        # --- Bullish MSS: downtrend + break above last swing high ---
        if trend == 'DOWNTREND' and close > last_swing_high:
            entry_price = close
            stop_loss = last_swing_low - (atr * 0.3)
            target = close + (atr * 2.5)
            # Stronger break = higher confidence
            break_size = close - last_swing_high
            confidence = min(1.0, break_size / atr + 0.3) if atr > 0 else 0.5
            
            swing_prices = [s['price'] for s in swing_highs[-3:]]
            return {
                'signal': 'CALL',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': confidence,
                'reason': f"Bullish MSS — Downtrend swing highs {[f'{p:.0f}' for p in swing_prices]}, broke {last_swing_high:.0f} at {close:.0f}",
                'atr': atr,
            }
        
        # --- Bearish MSS: uptrend + break below last swing low ---
        if trend == 'UPTREND' and close < last_swing_low:
            entry_price = close
            stop_loss = last_swing_high + (atr * 0.3)
            target = close - (atr * 2.5)
            break_size = last_swing_low - close
            confidence = min(1.0, break_size / atr + 0.3) if atr > 0 else 0.5
            
            swing_prices = [s['price'] for s in swing_lows[-3:]]
            return {
                'signal': 'PUT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': confidence,
                'reason': f"Bearish MSS — Uptrend swing lows {[f'{p:.0f}' for p in swing_prices]}, broke {last_swing_low:.0f} at {close:.0f}",
                'atr': atr,
            }
        
        return None
    
    def get_info(self):
        """Get strategy information"""
        return self.description


class VWAPReversalStrategy:
    """
    VWAP Reversal Strategy
    
    Mean reversion using Volume Weighted Average Price as the dynamic mean.
    Price crossing VWAP with above-average volume confirms a reversal.
    
    - Bullish: price was below VWAP, closes above it with high volume → CALL
    - Bearish: price was above VWAP, closes below it with high volume → PUT
    """
    
    VOLUME_MULTIPLIER = 1.5    # Current volume must be >= 1.5x average
    VWAP_PERIOD = 20           # Rolling VWAP lookback (intraday proxy)
    VOL_AVG_PERIOD = 20        # Period for average volume
    
    def __init__(self):
        self.name = "VWAP Reversal"
        self.description = """
        <h3>VWAP Reversal Strategy</h3>
        <p><b>Concept:</b> Mean reversion using Volume Weighted Average Price.
        Price tends to revert to VWAP; crossovers with high volume confirm
        the reversal.</p>
        <p><b>Entry Rules:</b></p>
        <ul>
            <li><b>CALL:</b> Previous close below VWAP, current close above VWAP,
                volume ≥ 1.5× average</li>
            <li><b>PUT:</b> Previous close above VWAP, current close below VWAP,
                volume ≥ 1.5× average</li>
        </ul>
        <p><b>Parameters:</b></p>
        <ul>
            <li>VWAP Period: 20 candles (rolling)</li>
            <li>Volume Multiplier: 1.5×</li>
            <li>Volume Average Period: 20 candles</li>
        </ul>
        """
    
    def calc_atr(self, data, period=14):
        """Calculate Average True Range"""
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def _calc_vwap(self, df):
        """
        Calculate rolling VWAP.
        True VWAP resets daily, but for a rolling approximation we use
        cumulative (TP × Volume) / cumulative Volume over VWAP_PERIOD.
        """
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        
        if 'Volume' in df.columns:
            vol = df['Volume'].replace(0, np.nan).fillna(1)
            tp_vol = typical_price * vol
            cum_tp_vol = tp_vol.rolling(self.VWAP_PERIOD).sum()
            cum_vol = vol.rolling(self.VWAP_PERIOD).sum()
            vwap = cum_tp_vol / cum_vol
        else:
            # No volume data — fall back to simple typical price SMA
            vwap = typical_price.rolling(self.VWAP_PERIOD).mean()
        
        return vwap
    
    def add_indicators(self, df):
        """Add VWAP, ATR, and volume average"""
        df['ATR'] = self.calc_atr(df)
        df['VWAP'] = self._calc_vwap(df)
        if 'Volume' in df.columns:
            df['Vol_Avg'] = df['Volume'].rolling(self.VOL_AVG_PERIOD).mean()
        return df
    
    def get_signal(self, df):
        """Generate signal on VWAP crossover with volume confirmation"""
        if len(df) < self.VWAP_PERIOD + 5:
            return None
        
        if 'VWAP' not in df.columns or 'ATR' not in df.columns:
            df = self.add_indicators(df)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        try:
            close = last['Close'].item() if hasattr(last['Close'], 'item') else float(last['Close'])
            prev_close = prev['Close'].item() if hasattr(prev['Close'], 'item') else float(prev['Close'])
            vwap = last['VWAP'].item() if hasattr(last['VWAP'], 'item') else float(last['VWAP'])
            prev_vwap = prev['VWAP'].item() if hasattr(prev['VWAP'], 'item') else float(prev['VWAP'])
            atr = last['ATR'].item() if hasattr(last['ATR'], 'item') else float(last['ATR'])
            if pd.isna(close) or pd.isna(vwap) or pd.isna(atr):
                return None
        except Exception:
            return None
        
        # Volume confirmation (skip if no volume data)
        high_volume = True  # default if no volume column
        vol_ratio = 1.0
        if 'Volume' in df.columns and 'Vol_Avg' in df.columns:
            try:
                vol = last['Volume'].item() if hasattr(last['Volume'], 'item') else float(last['Volume'])
                vol_avg = last['Vol_Avg'].item() if hasattr(last['Vol_Avg'], 'item') else float(last['Vol_Avg'])
                if pd.isna(vol) or pd.isna(vol_avg) or vol_avg <= 0:
                    high_volume = True
                    vol_ratio = 1.0
                else:
                    vol_ratio = vol / vol_avg
                    high_volume = vol_ratio >= self.VOLUME_MULTIPLIER
            except Exception:
                high_volume = True
                vol_ratio = 1.0
        
        if not high_volume:
            return None
        
        # --- Bullish VWAP reversal: was below, now above ---
        if prev_close < prev_vwap and close > vwap:
            entry_price = close
            stop_loss = vwap - (atr * 1.0)
            target = close + (atr * 2.0)
            distance_pct = abs(close - vwap) / atr if atr > 0 else 0
            confidence = min(1.0, 0.4 + (vol_ratio - 1.0) * 0.3 + distance_pct * 0.1)
            
            return {
                'signal': 'CALL',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': confidence,
                'reason': f"Bullish VWAP reversal — Crossed above VWAP {vwap:.0f}, close={close:.0f}, vol={vol_ratio:.1f}x avg",
                'atr': atr,
            }
        
        # --- Bearish VWAP reversal: was above, now below ---
        if prev_close > prev_vwap and close < vwap:
            entry_price = close
            stop_loss = vwap + (atr * 1.0)
            target = close - (atr * 2.0)
            distance_pct = abs(vwap - close) / atr if atr > 0 else 0
            confidence = min(1.0, 0.4 + (vol_ratio - 1.0) * 0.3 + distance_pct * 0.1)
            
            return {
                'signal': 'PUT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'confidence': confidence,
                'reason': f"Bearish VWAP reversal — Crossed below VWAP {vwap:.0f}, close={close:.0f}, vol={vol_ratio:.1f}x avg",
                'atr': atr,
            }
        
        return None
    
    def get_info(self):
        """Get strategy information"""
        return self.description


class MultiTimeframeConfluenceStrategy:
    """
    Multi-Timeframe Confluence Strategy
    
    Resamples the base data into 3 timeframes and runs lightweight directional
    checks on each. A trade is taken only when all 3 timeframes agree.
    
    Timeframe mapping (base data is treated as the lowest TF):
        LTF  = base candles              (e.g. 1-min / 5-min)
        MTF  = 3× resampled              (e.g. 3-min / 15-min)
        HTF  = 9× resampled              (e.g. 9-min / 45-min)
    
    Each timeframe is checked for:
        1. EMA trend direction  (9 EMA vs 21 EMA)
        2. FVG presence         (bullish / bearish gap)
        3. Price vs VWAP        (above / below)
    
    Signal only fires when ≥ 2 of the 3 checks agree on direction across
    ALL 3 timeframes.
    """
    
    MTF_MULTIPLIER = 3   # Resample factor for medium TF
    HTF_MULTIPLIER = 9   # Resample factor for high TF
    EMA_FAST = 9
    EMA_SLOW = 21
    FVG_MIN_SIZE = 5     # Smaller threshold per-TF
    MIN_CHECKS_PER_TF = 2  # At least 2/3 checks must agree per TF
    
    def __init__(self):
        self.name = "Multi-TF Confluence"
        self.description = """
        <h3>Multi-Timeframe Confluence Strategy</h3>
        <p><b>Concept:</b> Combine signals from 3 timeframes (LTF, MTF, HTF)
        for higher probability trades. Only enters when all timeframes align.</p>
        <p><b>Checks per timeframe:</b></p>
        <ul>
            <li>EMA trend (9 vs 21 EMA)</li>
            <li>FVG presence (bullish / bearish)</li>
            <li>Price vs rolling VWAP (above / below)</li>
        </ul>
        <p><b>Entry Rules:</b></p>
        <ul>
            <li><b>CALL:</b> All 3 timeframes show bullish confluence</li>
            <li><b>PUT:</b> All 3 timeframes show bearish confluence</li>
        </ul>
        <p><b>Parameters:</b></p>
        <ul>
            <li>MTF multiplier: 3× base</li>
            <li>HTF multiplier: 9× base</li>
            <li>Min checks per TF: 2 of 3</li>
        </ul>
        """
    
    # ── helpers ──────────────────────────────────────────────
    
    def calc_atr(self, data, period=14):
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def _resample(self, df, factor):
        """Resample OHLCV by grouping every *factor* rows."""
        n = len(df)
        if n < factor * 10:
            return None
        
        # Trim so length is divisible by factor
        trim = n % factor
        if trim:
            df_trimmed = df.iloc[trim:].copy()
        else:
            df_trimmed = df.copy()
        
        groups = np.arange(len(df_trimmed)) // factor
        
        resampled = pd.DataFrame()
        resampled['Open'] = df_trimmed.groupby(groups)['Open'].first()
        resampled['High'] = df_trimmed.groupby(groups)['High'].max()
        resampled['Low'] = df_trimmed.groupby(groups)['Low'].min()
        resampled['Close'] = df_trimmed.groupby(groups)['Close'].last()
        if 'Volume' in df_trimmed.columns:
            resampled['Volume'] = df_trimmed.groupby(groups)['Volume'].sum()
        
        resampled = resampled.reset_index(drop=True)
        return resampled
    
    def _tf_bias(self, df):
        """
        Return +1 (bullish), -1 (bearish), or 0 (neutral) for a single TF.
        Uses 3 lightweight checks and requires MIN_CHECKS_PER_TF agreement.
        """
        if df is None or len(df) < self.EMA_SLOW + 5:
            return 0, {}
        
        ema_fast = df['Close'].ewm(span=self.EMA_FAST, adjust=False).mean()
        ema_slow = df['Close'].ewm(span=self.EMA_SLOW, adjust=False).mean()
        
        try:
            ef = ema_fast.iloc[-1]
            es = ema_slow.iloc[-1]
            close = df['Close'].iloc[-1]
            if hasattr(ef, 'item'):
                ef, es = ef.item(), es.item()
            if hasattr(close, 'item'):
                close = close.item()
        except Exception:
            return 0, {}
        
        checks = {'ema': 0, 'fvg': 0, 'vwap': 0}
        
        # 1. EMA trend
        if ef > es:
            checks['ema'] = 1
        elif ef < es:
            checks['ema'] = -1
        
        # 2. Recent FVG (last 10 candles)
        fvg_dir = self._latest_fvg(df)
        checks['fvg'] = fvg_dir
        
        # 3. Price vs rolling VWAP (20-period)
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        if 'Volume' in df.columns:
            vol = df['Volume'].replace(0, np.nan).fillna(1)
            vwap = (tp * vol).rolling(20).sum() / vol.rolling(20).sum()
        else:
            vwap = tp.rolling(20).mean()
        
        try:
            vwap_val = vwap.iloc[-1]
            if hasattr(vwap_val, 'item'):
                vwap_val = vwap_val.item()
            if not pd.isna(vwap_val):
                checks['vwap'] = 1 if close > vwap_val else -1
        except Exception:
            pass
        
        # Count bullish / bearish
        bull = sum(1 for v in checks.values() if v > 0)
        bear = sum(1 for v in checks.values() if v < 0)
        
        if bull >= self.MIN_CHECKS_PER_TF:
            return 1, checks
        if bear >= self.MIN_CHECKS_PER_TF:
            return -1, checks
        return 0, checks
    
    def _latest_fvg(self, df):
        """Check if any FVG formed in the last 10 candles. Returns +1, -1, or 0."""
        n = len(df)
        for i in range(max(0, n - 12), n - 2):
            try:
                c0h = df['High'].iloc[i]
                c2l = df['Low'].iloc[i + 2]
                c0l = df['Low'].iloc[i]
                c2h = df['High'].iloc[i + 2]
                if hasattr(c0h, 'item'):
                    c0h, c2l = c0h.item(), c2l.item()
                    c0l, c2h = c0l.item(), c2h.item()
                
                if c2l - c0h >= self.FVG_MIN_SIZE:
                    return 1   # bullish FVG
                if c0l - c2h >= self.FVG_MIN_SIZE:
                    return -1  # bearish FVG
            except Exception:
                continue
        return 0
    
    # ── main interface ───────────────────────────────────────
    
    def add_indicators(self, df):
        df['ATR'] = self.calc_atr(df)
        return df
    
    def get_signal(self, df):
        if len(df) < self.HTF_MULTIPLIER * (self.EMA_SLOW + 10):
            return None
        
        if 'ATR' not in df.columns:
            df = self.add_indicators(df)
        
        # Build 3 timeframes
        ltf = df.copy()
        mtf = self._resample(df, self.MTF_MULTIPLIER)
        htf = self._resample(df, self.HTF_MULTIPLIER)
        
        ltf_bias, ltf_checks = self._tf_bias(ltf)
        mtf_bias, mtf_checks = self._tf_bias(mtf)
        htf_bias, htf_checks = self._tf_bias(htf)
        
        # All 3 must agree
        if ltf_bias == 0 or mtf_bias == 0 or htf_bias == 0:
            return None
        if not (ltf_bias == mtf_bias == htf_bias):
            return None
        
        direction = ltf_bias  # +1 or -1
        
        try:
            close = df['Close'].iloc[-1]
            atr = df['ATR'].iloc[-1]
            if hasattr(close, 'item'):
                close = close.item()
            if hasattr(atr, 'item'):
                atr = atr.item()
            if pd.isna(close) or pd.isna(atr):
                return None
        except Exception:
            return None
        
        def _fmt(checks):
            parts = []
            for k, v in checks.items():
                sym = '▲' if v > 0 else ('▼' if v < 0 else '—')
                parts.append(f"{k}:{sym}")
            return ' '.join(parts)
        
        reason_parts = f"LTF[{_fmt(ltf_checks)}] MTF[{_fmt(mtf_checks)}] HTF[{_fmt(htf_checks)}]"
        
        # Confidence: 3-TF alignment is inherently high conviction
        all_checks = list(ltf_checks.values()) + list(mtf_checks.values()) + list(htf_checks.values())
        agreeing = sum(1 for v in all_checks if v == direction)
        confidence = min(1.0, agreeing / 9 + 0.3)
        
        if direction == 1:
            return {
                'signal': 'CALL',
                'entry_price': close,
                'stop_loss': close - (atr * 1.5),
                'target': close + (atr * 2.5),
                'confidence': confidence,
                'reason': f"Multi-TF bullish confluence — {reason_parts}",
                'atr': atr,
            }
        else:
            return {
                'signal': 'PUT',
                'entry_price': close,
                'stop_loss': close + (atr * 1.5),
                'target': close - (atr * 2.5),
                'confidence': confidence,
                'reason': f"Multi-TF bearish confluence — {reason_parts}",
                'atr': atr,
            }
    
    def get_info(self):
        """Get strategy information"""
        return self.description