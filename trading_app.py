"""
================================================================================
                    LIVE TRADING APPLICATION - NIFTY 50
================================================================================

PyQt5-based live trading application with three integrated strategies:
1. Bollinger Band + MACD Breakout (predictioncandle.py)
2. Opening Range Breakout (opening-range-breakout-fno.py)
3. Sideways Market Strategy (sideways.py)

Features:
- Real-time candlestick chart
- Live strategy predictions
- Paper trading with trade management
- Separate trade lists for each strategy
- Trade history persistence

================================================================================
"""

import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox, 
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QTextEdit, QGroupBox, QGridLayout, QMessageBox,
                             QSplitter, QHeaderView, QDialog, QCheckBox, QDialogButtonBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor
import pyqtgraph as pg
from pyqtgraph import PlotWidget, mkPen, BarGraphItem
import yfinance as yf

# Import strategy modules
from strategy_wrappers import (BollingerMACDStrategy, 
                               OpeningRangeBreakoutStrategy, 
                               SidewaysStrategy,
                               MomentumBreakoutStrategy,
                               MeanReversionStrategy,
                               EMACrossoverStrategy)
from paper_trading_engine import PaperTradingEngine, Trade
from option_price_fetcher import OptionPriceFetcher
from fetch_gold_atm_options import GoldATMOptionFetcher


class LiveDataThread(QThread):
    """Thread for fetching live market data without blocking UI"""
    data_ready = pyqtSignal(pd.DataFrame)
    
    def __init__(self, symbol='^NSEI', interval='5m', option_fetcher=None):
        super().__init__()
        self.symbol = symbol
        self.interval = interval
        self.running = True
        self._stop_requested = False
        self.option_fetcher = option_fetcher
        
    def run(self):
        """Fetch data periodically"""
        while self.running and not self._stop_requested:
            try:
                # Try XTS for real-time spot price first (only for NIFTY)
                xts_spot = 0
                if self.option_fetcher and self.option_fetcher.use_xts and self.symbol == '^NSEI':
                    xts_spot = self.option_fetcher.get_nifty_spot()
                
                # Fetch historical data from Yahoo Finance
                end = datetime.now()
                start = end - timedelta(days=2)
                df = yf.download(self.symbol, start=start, end=end, 
                               interval=self.interval, progress=False, auto_adjust=True)
                
                if not df.empty and not self._stop_requested:
                    # If XTS spot available, update the last close with real-time price
                    if xts_spot > 0:
                        df.loc[df.index[-1], 'Close'] = xts_spot
                        print(f"✅ XTS Spot: Rs.{xts_spot:.2f}")
                    
                    self.data_ready.emit(df)
                    
            except Exception as e:
                if not self._stop_requested:
                    print(f"Error fetching data: {e}")
            
            # Wait 1 second before next update
            if not self._stop_requested:
                self.msleep(1000)
    
    def stop(self):
        """Stop the thread"""
        self._stop_requested = True
        self.running = False


class StrategySelectionDialog(QDialog):
    """Dialog for selecting strategies to use in auto trading"""
    
    def __init__(self, strategies, selected_strategies=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Auto Trading Strategies")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        # Store strategy list
        self.strategies = strategies
        self.checkboxes = {}
        
        # Setup UI
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Title label
        title_label = QLabel("<h3>Select Strategies for Auto Trading</h3>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Info label
        info_label = QLabel("Only checked strategies will be used for automatic trading:")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addSpacing(10)
        
        # Create checkbox for each strategy
        for strategy_name in strategies:
            checkbox = QCheckBox(strategy_name)
            # Check by default if in selected_strategies, or all if none selected
            if selected_strategies is None:
                checkbox.setChecked(True)
            else:
                checkbox.setChecked(strategy_name in selected_strategies)
            self.checkboxes[strategy_name] = checkbox
            layout.addWidget(checkbox)
        
        layout.addSpacing(10)
        
        # Select/Deselect all buttons
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all)
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        layout.addLayout(button_layout)
        
        layout.addSpacing(10)
        
        # Dialog buttons (OK/Cancel)
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def select_all(self):
        """Select all strategy checkboxes"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)
    
    def deselect_all(self):
        """Deselect all strategy checkboxes"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)
    
    def get_selected_strategies(self):
        """Return list of selected strategy names"""
        return [name for name, checkbox in self.checkboxes.items() 
                if checkbox.isChecked()]


class CandlestickChart(QWidget):
    """Candlestick chart widget using pyqtgraph"""
    
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('left', 'Price', units='₹')
        self.plot_widget.setLabel('bottom', 'Time')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        self.layout.addWidget(self.plot_widget)
        
        # Store data
        self.df = None
        
    def update_chart(self, df):
        """Update candlestick chart with new data"""
        if df is None or df.empty:
            return
            
        self.df = df
        self.plot_widget.clear()
        
        # Take only last 100 candles for better visibility
        df_display = df.tail(100).copy()
        
        # Prepare candlestick data
        times = np.arange(len(df_display))
        
        # Draw candlesticks
        for i in range(len(df_display)):
            row = df_display.iloc[i]
            open_price = row['Open'].item()
            close_price = row['Close'].item()
            high_price = row['High'].item()
            low_price = row['Low'].item()
            
            # Determine color
            if close_price >= open_price:
                color = pg.mkBrush(0, 255, 0, 150)  # Green
                pen_color = pg.mkPen('g', width=1)
            else:
                color = pg.mkBrush(255, 0, 0, 150)  # Red
                pen_color = pg.mkPen('r', width=1)
            
            # Draw high-low line (wick)
            self.plot_widget.plot([i, i], [low_price, high_price], 
                                pen=pen_color)
            
            # Draw body (only if there's a difference)
            body_height = abs(close_price - open_price)
            if body_height < 0.1:  # Very small body
                body_height = 0.1
            
            body_y = min(open_price, close_price)
            
            bar = pg.BarGraphItem(x=[i], height=[body_height],
                                 y0=[body_y], width=0.6, 
                                 brush=color, pen=pen_color)
            self.plot_widget.addItem(bar)
        
        # Add Bollinger Bands if available
        if 'BB_upper' in df_display.columns and not df_display['BB_upper'].isna().all():
            bb_upper = df_display['BB_upper'].ffill().bfill()
            bb_lower = df_display['BB_lower'].ffill().bfill()
            bb_middle = df_display['BB_middle'].ffill().bfill()
            
            self.plot_widget.plot(times, bb_upper.values, 
                                pen=pg.mkPen('b', width=2, style=Qt.DashLine))
            self.plot_widget.plot(times, bb_lower.values, 
                                pen=pg.mkPen('b', width=2, style=Qt.DashLine))
            self.plot_widget.plot(times, bb_middle.values, 
                                pen=pg.mkPen((255, 165, 0), width=2))  # Orange
        
        # Add EMA lines if available
        if 'EMA_9' in df_display.columns and not df_display['EMA_9'].isna().all():
            ema9 = df_display['EMA_9'].ffill().bfill()
            ema21 = df_display['EMA_21'].ffill().bfill()
            
            self.plot_widget.plot(times, ema9.values, 
                                pen=pg.mkPen((0, 255, 0), width=2))  # Green for 9 EMA
            self.plot_widget.plot(times, ema21.values, 
                                pen=pg.mkPen((255, 0, 0), width=2))  # Red for 21 EMA
        
        # Set axis range manually
        if len(df_display) > 0:
            price_min = df_display['Low'].min().item()
            price_max = df_display['High'].max().item()
            price_range = price_max - price_min
            
            self.plot_widget.setYRange(price_min - price_range * 0.1, 
                                      price_max + price_range * 0.1)
            self.plot_widget.setXRange(0, len(df_display))


class TradingMainWindow(QMainWindow):
    """Main trading application window"""
    
    # Instrument configurations
    INSTRUMENTS = {
        'NIFTY 50': {'symbol': '^NSEI', 'name': 'NIFTY 50', 'xts_enabled': True, 'interval': '5m', 'lot_size': 75},
        'CRUDE OIL': {'symbol': 'CL=F', 'name': 'Crude Oil', 'xts_enabled': False, 'interval': '1m', 'lot_size': 1},
        'GOLD': {'symbol': 'GC=F', 'name': 'Gold', 'xts_enabled': True, 'interval': '1m', 'lot_size': 100}
    }
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NIFTY 50 Options Live Trading System")
        self.setGeometry(100, 100, 1400, 900)
        
        # Current instrument
        self.current_instrument = 'NIFTY 50'
        
        # Initialize strategies
        self.strategies = {
            'Bollinger + MACD': BollingerMACDStrategy(),
            'Opening Range Breakout': OpeningRangeBreakoutStrategy(),
            'Sideways Market': SidewaysStrategy(),
            'Momentum Breakout': MomentumBreakoutStrategy(),
            'Mean Reversion': MeanReversionStrategy(),
            'EMA Crossover': EMACrossoverStrategy()
        }
        
        self.current_strategy = 'Bollinger + MACD'
        
        # Initialize paper trading engines (one per instrument-strategy combination)
        # Key format: "INSTRUMENT_STRATEGY"
        self.trading_engines = {}
        for instrument_name in self.INSTRUMENTS.keys():
            for strategy_name in self.strategies.keys():
                engine_key = f"{instrument_name}_{strategy_name}"
                self.trading_engines[engine_key] = PaperTradingEngine(initial_capital=1000000)
        
        # Current market data
        self.current_data = None
        self.current_price = 0
        
        # Store selected strategies for auto trading
        self.selected_auto_trade_strategies = list(self.strategies.keys())  # All selected by default
        
        # Initialize option price fetcher
        self.option_fetcher = OptionPriceFetcher(use_xts=True)
        
        # Initialize Gold option fetcher (MCX via instrument master)
        self.gold_option_fetcher = None
        self.gold_master_lines = None
        self.gold_options_cache = {}
        self.gold_spot_price = 0
        self.gold_future_id = None
        self.gold_expiry = None
        self.init_gold_options()
        
        # Setup UI
        self.setup_ui()
        
        # Get initial instrument config
        initial_config = self.INSTRUMENTS[self.current_instrument]
        
        # Start live data thread with option fetcher
        self.data_thread = LiveDataThread(
            symbol=initial_config['symbol'],
            interval=initial_config['interval'],
            option_fetcher=self.option_fetcher
        )
        self.data_thread.data_ready.connect(self.on_data_update)
        self.data_thread.start()
        
        # Setup timer for UI updates
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start(1000)  # Update every second
        
        # Load saved trades
        self.load_all_trades()
        
        # Load initial data immediately
        self.load_initial_data()
        
        # Print startup capital info
        print("\n" + "="*70)
        print("   LIVE OPTIONS TRADING SYSTEM")
        print("="*70)
        print(f"Starting Capital: ₹{1000000:,} (10 Lakhs)")
        print(f"Trading Mode: Paper Trading (Options)")
        print(f"NIFTY Lot Size: 75 | GOLD Lot Size: 100")
        if self.gold_spot_price > 0:
            print(f"MCX Gold Spot: ₹{self.gold_spot_price:,.1f}")
        if self.gold_expiry:
            print(f"Gold Options Expiry: {self.gold_expiry}")
        print("="*70 + "\n")
        
    def load_initial_data(self):
        """Load initial market data on startup"""
        try:
            end = datetime.now()
            start = end - timedelta(days=2)
            instrument_config = self.INSTRUMENTS[self.current_instrument]
            print(f"Loading initial market data for {instrument_config['name']}...")
            df = yf.download(instrument_config['symbol'], start=start, end=end, 
                           interval=instrument_config['interval'], progress=False, auto_adjust=True)
            
            if not df.empty:
                print(f"Loaded {len(df)} candles")
                self.on_data_update(df)
            else:
                print("No data available. Market might be closed.")
        except Exception as e:
            print(f"Error loading initial data: {e}")
    
    def init_gold_options(self):
        """Initialize Gold option data from XTS instrument master"""
        try:
            self.gold_option_fetcher = GoldATMOptionFetcher()
            if not self.gold_option_fetcher.login():
                print("[WARNING] Gold option fetcher login failed")
                return False
            
            print("[INFO] Downloading MCXFO instrument master for Gold options...")
            self.gold_master_lines = self.gold_option_fetcher.download_mcxfo_master()
            if not self.gold_master_lines:
                print("[WARNING] Failed to download MCXFO master")
                return False
            
            # Get nearest GOLD future instrument ID for spot price
            futures = self.gold_option_fetcher.parse_gold_futures(self.gold_master_lines, "GOLD")
            if futures:
                self.gold_future_id = futures[0]['instrument_id']
                # Try to get initial spot price
                quote = self.gold_option_fetcher.get_quote(self.gold_future_id)
                if quote:
                    spot = quote['ltp'] if quote['ltp'] > 0 else quote['close']
                    if spot > 0:
                        self.gold_spot_price = spot
                        print(f"[INFO] MCX Gold Spot: ₹{self.gold_spot_price:,.1f}")
            
            # Parse all GOLD options
            all_options = self.gold_option_fetcher.parse_gold_options(self.gold_master_lines, "GOLD")
            nearest_expiry = self.gold_option_fetcher.get_nearest_expiry(all_options)
            
            if nearest_expiry:
                self.gold_expiry = nearest_expiry.split('T')[0]
                self.gold_options_cache = self.gold_option_fetcher.parse_gold_options(
                    self.gold_master_lines, "GOLD", expiry_filter=self.gold_expiry
                )
                print(f"[INFO] Gold options loaded: {len(self.gold_options_cache)} contracts, expiry={self.gold_expiry}")
            
            return True
        except Exception as e:
            print(f"[WARNING] Gold options init error: {e}")
            return False
    
    def get_gold_option_data(self, signal_type, spot_price, atr=500):
        """
        Get Gold option data for trading (similar to OptionPriceFetcher.get_option_data)
        
        Args:
            signal_type: 'CALL' or 'PUT'
            spot_price: MCX Gold spot price (INR)
            atr: Average True Range
        
        Returns:
            dict with strike, option_type, premium, stop_loss, target, spot_price
        """
        if not self.gold_options_cache or not self.gold_option_fetcher:
            return None
        
        # ATM strike rounded to nearest 1000 (GOLD strike step)
        atm_strike = round(spot_price / 1000) * 1000
        option_type = 'CE' if signal_type == 'CALL' else 'PE'
        
        key = (atm_strike, option_type)
        if key not in self.gold_options_cache:
            available = sorted([k[0] for k in self.gold_options_cache if k[1] == option_type])
            if available:
                nearest = min(available, key=lambda x: abs(x - atm_strike))
                key = (nearest, option_type)
            else:
                return None
        
        option_info = self.gold_options_cache[key]
        
        # Fetch live premium
        quote = self.gold_option_fetcher.get_quote(option_info['instrument_id'])
        premium = 0
        if quote:
            premium = quote['ltp'] if quote['ltp'] > 0 else quote['close']
        
        if premium <= 0:
            premium = self.gold_option_fetcher.estimate_option_price(spot_price, key[0], option_type)
        
        # SL: 30% loss, Target: 50% profit (same as NIFTY)
        stop_loss = premium * 0.70
        target = premium * 1.50
        
        return {
            'strike': key[0],
            'option_type': option_type,
            'premium': premium,
            'stop_loss': stop_loss,
            'target': target,
            'spot_price': spot_price,
            'instrument_id': option_info['instrument_id'],
            'display_name': option_info.get('display_name', '')
        }
    
    def get_gold_option_ltp(self, strike, option_type, spot_price, atr=500):
        """
        Get current Gold option LTP for a specific strike
        
        Args:
            strike: Option strike price
            option_type: 'CE' or 'PE'
            spot_price: MCX Gold spot price
        
        Returns:
            Float premium value
        """
        if not self.gold_options_cache or not self.gold_option_fetcher:
            if self.gold_option_fetcher:
                return self.gold_option_fetcher.estimate_option_price(spot_price, strike, option_type)
            return 0
        
        key = (strike, option_type)
        if key not in self.gold_options_cache:
            return self.gold_option_fetcher.estimate_option_price(spot_price, strike, option_type)
        
        option_info = self.gold_options_cache[key]
        quote = self.gold_option_fetcher.get_quote(option_info['instrument_id'])
        
        if quote:
            ltp = quote['ltp'] if quote['ltp'] > 0 else quote['close']
            if ltp > 0:
                return ltp
        
        return self.gold_option_fetcher.estimate_option_price(spot_price, strike, option_type)
        
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Top control panel
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # Create splitter for chart and info
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Chart
        chart_widget = self.create_chart_widget()
        splitter.addWidget(chart_widget)
        
        # Right side: Info and signals
        info_widget = self.create_info_widget()
        splitter.addWidget(info_widget)
        
        splitter.setStretchFactor(0, 2)  # Chart takes more space
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        # Bottom: Trade tables
        trade_tables = self.create_trade_tables()
        main_layout.addWidget(trade_tables)
        
    def create_control_panel(self):
        """Create top control panel"""
        group = QGroupBox("Control Panel")
        layout = QHBoxLayout()
        
        # Instrument selector
        layout.addWidget(QLabel("Instrument:"))
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems(list(self.INSTRUMENTS.keys()))
        self.instrument_combo.setCurrentText(self.current_instrument)
        self.instrument_combo.currentTextChanged.connect(self.on_instrument_changed)
        layout.addWidget(self.instrument_combo)
        
        layout.addWidget(QLabel("  "))
        
        # Strategy selector
        layout.addWidget(QLabel("Strategy:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(list(self.strategies.keys()))
        self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)
        layout.addWidget(self.strategy_combo)
        
        layout.addStretch()
        
        # Current price display
        self.price_label = QLabel("Price: ₹0.00")
        self.price_label.setFont(QFont('Arial', 14, QFont.Bold))
        layout.addWidget(self.price_label)
        
        # Option trading indicator
        self.option_indicator = QLabel("📊 Options")
        self.option_indicator.setStyleSheet("color: #0066cc; font-weight: bold; padding: 5px;")
        self.option_indicator.setToolTip("Trading Options with real-time premiums via XTS")
        layout.addWidget(self.option_indicator)
        # Hide initially, show only for options-enabled instruments
        if self.current_instrument not in ['NIFTY 50', 'GOLD']:
            self.option_indicator.hide()
        
        layout.addStretch()
        
        # Auto-trade toggle
        self.auto_trade_btn = QPushButton("Enable Auto-Trade")
        self.auto_trade_btn.setCheckable(True)
        self.auto_trade_btn.clicked.connect(self.toggle_auto_trade)
        layout.addWidget(self.auto_trade_btn)
        
        # Save trades button
        save_btn = QPushButton("Save All Trades")
        save_btn.clicked.connect(self.save_all_trades)
        layout.addWidget(save_btn)
        
        # Reset button
        reset_btn = QPushButton("Reset All")
        reset_btn.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
        reset_btn.clicked.connect(self.reset_all_data)
        layout.addWidget(reset_btn)
        
        group.setLayout(layout)
        return group
        
    def create_chart_widget(self):
        """Create chart area"""
        group = QGroupBox("Live Market Chart")
        layout = QVBoxLayout()
        
        self.chart = CandlestickChart()
        layout.addWidget(self.chart)
        
        group.setLayout(layout)
        return group
        
    def create_info_widget(self):
        """Create information and signals widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Strategy info
        info_group = QGroupBox("Strategy Information")
        info_layout = QVBoxLayout()
        self.strategy_info_text = QTextEdit()
        self.strategy_info_text.setReadOnly(True)
        self.strategy_info_text.setMaximumHeight(150)
        info_layout.addWidget(self.strategy_info_text)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Current signal
        signal_group = QGroupBox("Current Signal")
        signal_layout = QVBoxLayout()
        self.signal_label = QLabel("Waiting for data...")
        self.signal_label.setFont(QFont('Arial', 16, QFont.Bold))
        self.signal_label.setAlignment(Qt.AlignCenter)
        self.signal_label.setMinimumHeight(60)
        signal_layout.addWidget(self.signal_label)
        
        self.signal_details = QTextEdit()
        self.signal_details.setReadOnly(True)
        self.signal_details.setMaximumHeight(120)
        signal_layout.addWidget(self.signal_details)
        
        # Manual trade button
        self.manual_trade_btn = QPushButton("Execute Manual Trade")
        self.manual_trade_btn.clicked.connect(self.execute_manual_trade)
        self.manual_trade_btn.setEnabled(False)
        signal_layout.addWidget(self.manual_trade_btn)
        
        signal_group.setLayout(signal_layout)
        layout.addWidget(signal_group)
        
        # Portfolio summary
        portfolio_group = QGroupBox("Portfolio Summary")
        portfolio_layout = QGridLayout()
        
        portfolio_layout.addWidget(QLabel("Capital:"), 0, 0)
        self.capital_label = QLabel("₹100,000")
        portfolio_layout.addWidget(self.capital_label, 0, 1)
        
        portfolio_layout.addWidget(QLabel("P&L:"), 1, 0)
        self.pnl_label = QLabel("₹0.00")
        portfolio_layout.addWidget(self.pnl_label, 1, 1)
        
        portfolio_layout.addWidget(QLabel("Open Positions:"), 2, 0)
        self.positions_label = QLabel("0")
        portfolio_layout.addWidget(self.positions_label, 2, 1)
        
        portfolio_layout.addWidget(QLabel("Total Trades:"), 3, 0)
        self.trades_label = QLabel("0")
        portfolio_layout.addWidget(self.trades_label, 3, 1)
        
        portfolio_layout.addWidget(QLabel("Win Rate:"), 4, 0)
        self.winrate_label = QLabel("0%")
        portfolio_layout.addWidget(self.winrate_label, 4, 1)
        
        # View Details button
        self.view_details_btn = QPushButton("View Details")
        self.view_details_btn.setStyleSheet("background-color: #3498db; color: white; padding: 5px;")
        self.view_details_btn.clicked.connect(self.show_portfolio_details)
        portfolio_layout.addWidget(self.view_details_btn, 5, 0, 1, 2)
        
        portfolio_group.setLayout(portfolio_layout)
        layout.addWidget(portfolio_group)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
        
    def create_trade_tables(self):
        """Create trade tables for each strategy"""
        tabs = QTabWidget()
        
        self.trade_tables = {}
        
        for strategy_name in self.strategies.keys():
            table = QTableWidget()
            table.setColumnCount(11)
            table.setHorizontalHeaderLabels([
                'Time', 'Signal', 'Strike/Type', 'Premium (Entry)', 'Current', 'SL', 'Target', 
                'P&L', 'Status', 'Duration', 'Notes'
            ])
            table.horizontalHeader().setStretchLastSection(True)
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setSelectionMode(QTableWidget.SingleSelection)
            
            self.trade_tables[strategy_name] = table
            tabs.addTab(table, strategy_name)
        
        # Add manual exit button below tables
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.addWidget(tabs)
        
        self.manual_exit_btn = QPushButton("[EXIT] Close Selected Trade")
        self.manual_exit_btn.clicked.connect(self.execute_manual_exit)
        self.manual_exit_btn.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; font-weight: bold; padding: 8px; }")
        container_layout.addWidget(self.manual_exit_btn)
        
        container.setLayout(container_layout)
        
        return container
    
    def on_instrument_changed(self, instrument_name):
        """Handle instrument selection change"""
        if instrument_name == self.current_instrument:
            return
            
        self.current_instrument = instrument_name
        instrument_config = self.INSTRUMENTS[instrument_name]
        
        # Stop current data thread
        if hasattr(self, 'data_thread') and self.data_thread:
            self.data_thread.stop()
            self.data_thread.wait()
        
        # Determine if XTS should be used
        use_xts = instrument_config['xts_enabled'] and self.option_fetcher and self.option_fetcher.use_xts
        
        # Start new data thread with correct symbol and interval
        self.data_thread = LiveDataThread(
            symbol=instrument_config['symbol'],
            interval=instrument_config['interval'],
            option_fetcher=self.option_fetcher if use_xts else None
        )
        self.data_thread.data_ready.connect(self.on_data_update)
        self.data_thread.start()
        
        # Update window title
        title_suffix = " Options Trading" if instrument_name in ['NIFTY 50', 'GOLD'] else " Live Trading"
        self.setWindowTitle(f"{instrument_config['name']}{title_suffix} System")
        
        # Show/hide option indicator
        if instrument_name in ['NIFTY 50', 'GOLD']:
            self.option_indicator.show()
        else:
            self.option_indicator.hide()
        
        # Load initial data
        self.load_initial_data()
        
        print(f"[INFO] Switched to {instrument_config['name']}")
        if instrument_name == 'NIFTY 50':
            print(f"[INFO] Trading NIFTY Options with real-time premiums")
        elif instrument_name == 'GOLD':
            print(f"[INFO] Trading MCX GOLD Options with real-time premiums")
            if self.gold_spot_price > 0:
                print(f"[INFO] MCX Gold Spot: ₹{self.gold_spot_price:,.1f}")
            if self.gold_expiry:
                print(f"[INFO] Gold Options Expiry: {self.gold_expiry}")
        
    def on_strategy_changed(self, strategy_name):
        """Handle strategy selection change"""
        self.current_strategy = strategy_name
        self.update_strategy_info()
        self.update_chart_with_indicators()
        
    def on_data_update(self, df):
        """Handle new market data"""
        self.current_data = df
        
        if not df.empty:
            self.current_price = df['Close'].iloc[-1].item()
            print(f"Data updated: {len(df)} candles, Latest price: Rs.{self.current_price:.2f}")
            
            # Update chart
            self.update_chart_with_indicators()
            
            # Check for signals
            self.check_signals()
        else:
            print("Received empty dataframe")
    
    def update_chart_with_indicators(self):
        """Update chart with current strategy indicators"""
        if self.current_data is None or self.current_data.empty:
            print("No data to display on chart")
            return
            
        try:
            # Get strategy and add indicators
            strategy = self.strategies[self.current_strategy]
            df_with_indicators = strategy.add_indicators(self.current_data.copy())
            
            # Update chart
            self.chart.update_chart(df_with_indicators)
            print(f"Chart updated with {len(df_with_indicators)} candles")
        except Exception as e:
            print(f"Error updating chart: {e}") 
            import traceback
            traceback.print_exc()
        
    def check_signals(self):
        """Check for trading signals from ALL strategies"""
        if self.current_data is None or self.current_data.empty:
            return
        
        # Calculate ATR for option pricing volatility
        atr = self.calculate_atr()
        
        # Check all strategies, not just the current one
        for strategy_name, strategy in self.strategies.items():
            signal_info = strategy.get_signal(self.current_data.copy())
            
            if signal_info:
                signal_type = signal_info['signal']
                confidence = signal_info.get('confidence', 0)
                reason = signal_info.get('reason', 'No reason provided')
                
                # For NIFTY options, fetch real option data
                option_data = None
                if self.current_instrument == 'NIFTY 50' and self.option_fetcher:
                    option_data = self.option_fetcher.get_option_data(
                        signal_type=signal_type,
                        spot_price=self.current_price,
                        atr=atr
                    )
                    
                    # Use option premium as entry price
                    entry_price = option_data['premium']
                    stop_loss = option_data['stop_loss']
                    target = option_data['target']
                    
                    # Add option details to signal_info
                    signal_info['entry_price'] = entry_price
                    signal_info['stop_loss'] = stop_loss
                    signal_info['target'] = target
                    signal_info['strike'] = option_data['strike']
                    signal_info['option_type'] = option_data['option_type']
                    signal_info['spot_price'] = option_data['spot_price']
                
                # For GOLD options, fetch from MCX via instrument master
                elif self.current_instrument == 'GOLD' and self.gold_spot_price > 0:
                    option_data = self.get_gold_option_data(
                        signal_type=signal_type,
                        spot_price=self.gold_spot_price,
                        atr=atr
                    )
                    
                    if option_data:
                        entry_price = option_data['premium']
                        stop_loss = option_data['stop_loss']
                        target = option_data['target']
                        
                        signal_info['entry_price'] = entry_price
                        signal_info['stop_loss'] = stop_loss
                        signal_info['target'] = target
                        signal_info['strike'] = option_data['strike']
                        signal_info['option_type'] = option_data['option_type']
                        signal_info['spot_price'] = option_data['spot_price']
                    else:
                        entry_price = signal_info.get('entry_price', self.current_price)
                        stop_loss = signal_info.get('stop_loss', 0)
                        target = signal_info.get('target', 0)
                else:
                    # For other instruments, use existing values
                    entry_price = signal_info.get('entry_price', self.current_price)
                    stop_loss = signal_info.get('stop_loss', 0)
                    target = signal_info.get('target', 0)
                
                # Only update UI if this is the currently selected strategy
                if strategy_name == self.current_strategy:
                    # Update signal display
                    color = 'green' if signal_type == 'CALL' else 'red' if signal_type == 'PUT' else 'gray'
                    self.signal_label.setText(f"[SIGNAL] {signal_type}")
                    self.signal_label.setStyleSheet(f"background-color: {color}; color: white; padding: 10px; border-radius: 5px;")
                    
                    # Build details display
                    details = f"""<b>Strategy:</b> {strategy_name}<br>
<b>Signal Type:</b> {signal_type}<br>
<b>Confidence:</b> {confidence:.1%}<br>"""
                    
                    # Add option details for NIFTY / GOLD
                    if option_data:
                        lot_size = self.INSTRUMENTS[self.current_instrument].get('lot_size', 75)
                        instrument_name = 'NIFTY' if self.current_instrument == 'NIFTY 50' else self.current_instrument
                        details += f"""<b>Spot Price:</b> ₹{option_data['spot_price']:,.2f}<br>
<b>Option:</b> {instrument_name} {option_data['strike']} {option_data['option_type']}<br>
<b>Premium:</b> ₹{entry_price:.2f}<br>
<b>Stop Loss:</b> ₹{stop_loss:.2f} (-30%)<br>
<b>Target:</b> ₹{target:.2f} (+50%)<br>
<b>Cost ({lot_size} qty):</b> ₹{entry_price * lot_size:,.2f}<br>"""
                    else:
                        details += f"""<b>Entry Price:</b> ₹{entry_price:.2f}<br>
<b>Stop Loss:</b> ₹{stop_loss:.2f}<br>
<b>Target:</b> ₹{target:.2f}<br>"""
                    
                    if stop_loss > 0 and entry_price > stop_loss:
                        risk_reward = (target - entry_price) / (entry_price - stop_loss)
                        details += f"<b>Risk/Reward:</b> 1:{risk_reward:.2f}<br>"
                    
                    details += f"<br><b>Reason:</b> {reason}"
                    
                    self.signal_details.setHtml(details)
                    self.manual_trade_btn.setEnabled(True)
                
                # Auto-execute if enabled AND strategy is selected for auto trading
                if self.auto_trade_btn.isChecked():
                    if strategy_name in self.selected_auto_trade_strategies:
                        # Check if strategy already has an open position (prevent duplicate trades)
                        engine_key = f"{self.current_instrument}_{strategy_name}"
                        engine = self.trading_engines.get(engine_key)
                        
                        if engine and len(engine.open_positions) == 0:
                            print(f"[AUTO-TRADE] Executing {strategy_name} - Selected strategies: {self.selected_auto_trade_strategies}")
                            self.execute_trade(signal_info, strategy_name)
                        elif engine and len(engine.open_positions) > 0:
                            print(f"[AUTO-TRADE] Skipping {strategy_name} - Already has {len(engine.open_positions)} open position(s)")
                    else:
                        print(f"[AUTO-TRADE] Skipping {strategy_name} - Not in selected strategies: {self.selected_auto_trade_strategies}")
        
        # Clear signal display if current strategy has no signal
        current_strategy = self.strategies[self.current_strategy]
        current_signal = current_strategy.get_signal(self.current_data.copy())
        if not current_signal:
            self.signal_label.setText("No Signal")
            self.signal_label.setStyleSheet("background-color: gray; color: white; padding: 10px; border-radius: 5px;")
            self.signal_details.setPlainText("Waiting for trading opportunity...")
            self.manual_trade_btn.setEnabled(False)
    
    def calculate_atr(self, period: int = 14) -> float:
        """Calculate Average True Range for volatility estimation"""
        if self.current_data is None or len(self.current_data) < period:
            return 50.0  # Default ATR
        
        try:
            df = self.current_data.copy()
            
            # Calculate True Range
            df['H-L'] = df['High'] - df['Low']
            df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
            df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
            
            df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
            
            # Calculate ATR
            atr = df['TR'].rolling(window=period).mean().iloc[-1]
            
            return float(atr) if not pd.isna(atr) else 50.0
        except Exception as e:
            print(f"[WARNING] ATR calculation error: {e}")
            return 50.0
    
    def execute_manual_trade(self):
        """Execute trade manually from current signal"""
        strategy = self.strategies[self.current_strategy]
        signal_info = strategy.get_signal(self.current_data)
        
        if signal_info:
            self.execute_trade(signal_info)
    
    def execute_manual_exit(self):
        """Manually exit the selected trade"""
        # Get current strategy tab
        current_tab_index = self.findChild(QTabWidget).currentIndex()
        strategy_names = list(self.strategies.keys())
        
        if current_tab_index >= len(strategy_names):
            return
            
        strategy_name = strategy_names[current_tab_index]
        table = self.trade_tables[strategy_name]
        
        # Get engine for current instrument and strategy
        engine_key = f"{self.current_instrument}_{strategy_name}"
        engine = self.trading_engines.get(engine_key)
        if not engine:
            return
        
        # Get selected row
        selected_rows = table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a trade to exit.")
            return
        
        row = selected_rows[0].row()
        
        # Get the trade at this row
        all_trades = engine.open_positions + engine.closed_trades
        
        if row >= len(all_trades):
            return
            
        trade = all_trades[row]
        
        # Check if trade is still open
        if trade.status != "OPEN":
            QMessageBox.information(self, "Trade Closed", "This trade is already closed.")
            return
        
        # Get current exit price (option premium for NIFTY/GOLD options, spot for others)
        exit_price = self.current_price
        if self.current_instrument == 'NIFTY 50' and self.option_fetcher:
            if hasattr(trade, 'strike') and trade.strike > 0 and hasattr(trade, 'option_type'):
                atr = self.calculate_atr()
                exit_price = self.option_fetcher.get_option_ltp(
                    trade.strike,
                    trade.option_type,
                    self.current_price,
                    atr
                )
        elif self.current_instrument == 'GOLD' and self.gold_spot_price > 0:
            if hasattr(trade, 'strike') and trade.strike > 0 and hasattr(trade, 'option_type'):
                exit_price = self.get_gold_option_ltp(
                    trade.strike,
                    trade.option_type,
                    self.gold_spot_price
                )
        
        # Calculate potential P&L
        potential_pnl = (exit_price - trade.entry_price) * trade.quantity
        if trade.signal_type == 'PUT':
            potential_pnl = (trade.entry_price - exit_price) * trade.quantity
        
        # Confirm exit
        reply = QMessageBox.question(
            self, 
            "Confirm Exit", 
            f"Exit {trade.signal_type} trade at ₹{exit_price:.2f}?\n\n"
            f"Entry: ₹{trade.entry_price:.2f}\n"
            f"Potential P&L: ₹{potential_pnl:,.2f}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Close the position
            success = engine.close_position(trade, exit_price, "MANUAL_EXIT")
            
            if success:
                self.update_trade_table(strategy_name)
                QMessageBox.information(
                    self, 
                    "Trade Exited", 
                    f"Trade {trade.trade_id} closed at ₹{exit_price:.2f}\n"
                    f"P&L: ₹{trade.pnl:,.2f}"
                )
            else:
                QMessageBox.warning(self, "Error", "Failed to close position.")
    
    def execute_trade(self, signal_info, strategy_name=None):
        """Execute a trade through paper trading engine"""
        # Use provided strategy name or fall back to current strategy
        if strategy_name is None:
            strategy_name = self.current_strategy
        
        print(f"[EXECUTE_TRADE] Strategy: {strategy_name}, Signal: {signal_info['signal']}")
        
        # Get the trading engine for current instrument and strategy
        engine_key = f"{self.current_instrument}_{strategy_name}"
        engine = self.trading_engines.get(engine_key)
        if not engine:
            return
        
        # Extract option details if available
        strike = signal_info.get('strike', 0)
        option_type = signal_info.get('option_type', '')
        spot_price = signal_info.get('spot_price', self.current_price)
        entry_price = signal_info.get('entry_price', self.current_price)
        
        # Get instrument-specific lot size
        lot_size = self.INSTRUMENTS[self.current_instrument].get('lot_size', 75)
        instrument_prefix = 'NIFTY' if self.current_instrument == 'NIFTY 50' else self.current_instrument
        
        # Execute trade with all option parameters
        trade = engine.open_position(
            signal_type=signal_info['signal'],
            entry_price=entry_price,
            stop_loss=signal_info.get('stop_loss', 0),
            target=signal_info.get('target', 0),
            quantity=lot_size,
            strategy=strategy_name,
            notes=signal_info.get('reason', ''),
            strike=strike,
            option_type=option_type,
            spot_price=spot_price
        )
            
        if trade:
            self.update_trade_table(strategy_name)
            
            # Log trade details
            if strike > 0 and option_type:
                print(f"[TRADE EXECUTED] {strategy_name}: {trade.signal_type}")
                print(f"  Option: {instrument_prefix} {strike} {option_type}")
                print(f"  Spot: Rs.{spot_price:,.2f}")
                print(f"  Premium: Rs.{entry_price:.2f} | Total: Rs.{entry_price * lot_size:,.2f}")
                print(f"  SL: Rs.{trade.stop_loss:.2f} | Target: Rs.{trade.target:.2f}")
            else:
                print(f"[TRADE EXECUTED] {strategy_name}: {trade.signal_type} @ Rs.{trade.entry_price:.2f}")
            
            # Only show message box if not in auto-trade mode
            if not self.auto_trade_btn.isChecked():
                if strike > 0 and option_type:
                    QMessageBox.information(self, "Trade Executed", 
                                           f"Strategy: {strategy_name}\n"
                                           f"Option: {instrument_prefix} {strike} {option_type}\n"
                                           f"Premium: Rs.{entry_price:.2f}\n"
                                           f"Total Cost: Rs.{entry_price * lot_size:,.2f}\n"
                                           f"SL: Rs.{trade.stop_loss:.2f} | Target: Rs.{trade.target:.2f}")
                else:
                    QMessageBox.information(self, "Trade Executed", 
                                           f"Strategy: {strategy_name}\n"
                                           f"Entry: Rs.{entry_price:.2f}\n"
                                           f"SL: Rs.{trade.stop_loss:.2f} | Target: Rs.{trade.target:.2f}")
    
    def show_portfolio_details(self):
        """Show detailed portfolio statistics dialog"""
        # Collect all trades from all strategies
        all_trades = []
        for strategy_name, engine in self.trading_engines.items():
            all_trades.extend(engine.closed_trades)
        
        if not all_trades:
            QMessageBox.information(self, "Portfolio Details", "No closed trades yet.")
            return
        
        # Calculate detailed statistics
        winning_trades = [t for t in all_trades if t.pnl > 0]
        losing_trades = [t for t in all_trades if t.pnl < 0]
        breakeven_trades = [t for t in all_trades if t.pnl == 0]
        
        num_winning = len(winning_trades)
        num_losing = len(losing_trades)
        num_breakeven = len(breakeven_trades)
        total_trades = len(all_trades)
        
        win_rate = (num_winning / total_trades * 100) if total_trades > 0 else 0
        
        # Max profit and loss on single trade
        max_profit = max([t.pnl for t in all_trades]) if all_trades else 0
        max_loss = min([t.pnl for t in all_trades]) if all_trades else 0
        
        # Profit factor (total profits / total losses)
        total_profits = sum([t.pnl for t in winning_trades]) if winning_trades else 0
        total_losses = abs(sum([t.pnl for t in losing_trades])) if losing_trades else 0
        profit_factor = (total_profits / total_losses) if total_losses > 0 else float('inf') if total_profits > 0 else 0
        
        # Get starting capital from any engine
        starting_capital = 100000  # Default
        if self.trading_engines:
            first_engine = next(iter(self.trading_engines.values()))
            starting_capital = first_engine.initial_capital
        
        # Max drawdown
        cumulative_pnl = 0
        peak_equity = starting_capital
        max_drawdown = 0
        peak_at_max_dd = starting_capital
        
        for trade in all_trades:
            cumulative_pnl += trade.pnl
            current_equity = starting_capital + cumulative_pnl
            
            if current_equity > peak_equity:
                peak_equity = current_equity
            
            drawdown = peak_equity - current_equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                peak_at_max_dd = peak_equity
        
        # Calculate max drawdown percentage relative to peak equity
        max_drawdown_pct = (max_drawdown / peak_at_max_dd * 100) if peak_at_max_dd > 0 else 0
        
        # Average winning trade and average losing trade
        avg_win = (total_profits / num_winning) if num_winning > 0 else 0
        avg_loss = (total_losses / num_losing) if num_losing > 0 else 0
        
        # Total P&L
        total_pnl = sum([t.pnl for t in all_trades])
        
        # Format profit factor for display
        profit_factor_str = f"{profit_factor:.2f}" if profit_factor != float('inf') else '\u221e'
        
        # Format colors and backgrounds
        pnl_bg_color = '#d4edda' if total_pnl >= 0 else '#f8d7da'
        pnl_text_color = 'green' if total_pnl >= 0 else 'red'
        
        # Create detailed message
        details = f"""
<b>PORTFOLIO PERFORMANCE SUMMARY</b>
<br><br>
<b>Trade Statistics:</b>
<table cellpadding='5' style='border-collapse: collapse;'>
<tr><td>Total Trades:</td><td style='text-align: right;'><b>{total_trades}</b></td></tr>
<tr style='background-color: #d4edda;'><td>Winning Trades:</td><td style='text-align: right;'><b>{num_winning}</b></td></tr>
<tr style='background-color: #f8d7da;'><td>Losing Trades:</td><td style='text-align: right;'><b>{num_losing}</b></td></tr>
<tr><td>Breakeven Trades:</td><td style='text-align: right;'><b>{num_breakeven}</b></td></tr>
</table>
<br>
<b>Performance Metrics:</b>
<table cellpadding='5' style='border-collapse: collapse;'>
<tr style='background-color: #e7f3ff;'><td>Win Rate:</td><td style='text-align: right;'><b>{win_rate:.2f}%</b></td></tr>
<tr style='background-color: #d4edda;'><td>Max Profit (Single Trade):</td><td style='text-align: right; color: green;'><b>Rs.{max_profit:,.2f}</b></td></tr>
<tr style='background-color: #f8d7da;'><td>Max Loss (Single Trade):</td><td style='text-align: right; color: red;'><b>Rs.{max_loss:,.2f}</b></td></tr>
<tr><td>Avg Winning Trade:</td><td style='text-align: right; color: green;'><b>Rs.{avg_win:,.2f}</b></td></tr>
<tr><td>Avg Losing Trade:</td><td style='text-align: right; color: red;'><b>Rs.{avg_loss:,.2f}</b></td></tr>
</table>
<br>
<b>Risk Metrics:</b>
<table cellpadding='5' style='border-collapse: collapse;'>
<tr style='background-color: #fff3cd;'><td>Profit Factor:</td><td style='text-align: right;'><b>{profit_factor_str}</b></td></tr>
<tr style='background-color: #f8d7da;'><td>Max Drawdown:</td><td style='text-align: right; color: red;'><b>Rs.{max_drawdown:,.2f} ({max_drawdown_pct:.2f}%)</b></td></tr>
<tr style='background-color: {pnl_bg_color};'><td>Total P&L:</td><td style='text-align: right; color: {pnl_text_color};'><b>Rs.{total_pnl:,.2f}</b></td></tr>
</table>
"""
        
        # Create dialog
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Portfolio Details")
        dialog.setTextFormat(Qt.RichText)
        dialog.setText(details)
        dialog.setIcon(QMessageBox.Information)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec_()
    
    def update_ui(self):
        """Update UI elements periodically"""
        # Refresh Gold spot price from XTS if GOLD selected
        if self.current_instrument == 'GOLD' and self.gold_option_fetcher and self.gold_future_id:
            try:
                quote = self.gold_option_fetcher.get_quote(self.gold_future_id)
                if quote:
                    spot = quote['ltp'] if quote['ltp'] > 0 else quote['close']
                    if spot > 0:
                        self.gold_spot_price = spot
            except Exception:
                pass
        
        # Update price display
        if self.current_instrument == 'GOLD' and self.gold_spot_price > 0:
            self.price_label.setText(f"MCX Gold: ₹{self.gold_spot_price:,.1f}")
        elif self.current_price > 0:
            self.price_label.setText(f"Price: ₹{self.current_price:.2f}")
        
        # Update positions for all strategies of current instrument with current price
        if self.current_price > 0:
            atr = self.calculate_atr()
            
            for strategy_name in self.strategies.keys():
                engine_key = f"{self.current_instrument}_{strategy_name}"
                engine = self.trading_engines.get(engine_key)
                if engine:
                    # For NIFTY options, update with current option premium
                    if self.current_instrument == 'NIFTY 50' and self.option_fetcher:
                        # Update each open position with its current option premium
                        for position in engine.open_positions:
                            if hasattr(position, 'strike') and hasattr(position, 'option_type') and position.strike > 0:
                                current_premium = self.option_fetcher.get_option_ltp(
                                    position.strike,
                                    position.option_type,
                                    self.current_price,
                                    atr
                                )
                                engine.update_positions(current_premium)
                            else:
                                engine.update_positions(self.current_price)
                    
                    # For GOLD options, update with current MCX option premium
                    elif self.current_instrument == 'GOLD' and self.gold_spot_price > 0:
                        for position in engine.open_positions:
                            if hasattr(position, 'strike') and hasattr(position, 'option_type') and position.strike > 0:
                                current_premium = self.get_gold_option_ltp(
                                    position.strike,
                                    position.option_type,
                                    self.gold_spot_price
                                )
                                engine.update_positions(current_premium)
                            else:
                                engine.update_positions(self.gold_spot_price)
                    else:
                        # For other instruments, use spot price
                        engine.update_positions(self.current_price)
                    
                    # Update trade table if any position closed
                    prev_key = f'_prev_positions_{engine_key}'
                    if len(engine.open_positions) != getattr(self, prev_key, 0):
                        self.update_trade_table(strategy_name)
                        setattr(self, prev_key, len(engine.open_positions))
        
        # Update portfolio display for current strategy and instrument
        engine_key = f"{self.current_instrument}_{self.current_strategy}"
        engine = self.trading_engines.get(engine_key)
        if not engine:
            return
        
        self.capital_label.setText(f"₹{engine.capital:,.2f}")
        
        total_pnl = engine.get_total_pnl()
        self.pnl_label.setText(f"₹{total_pnl:,.2f}")
        if total_pnl > 0:
            self.pnl_label.setStyleSheet("color: green; font-weight: bold;")
        elif total_pnl < 0:
            self.pnl_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.pnl_label.setStyleSheet("")
        
        self.positions_label.setText(str(len(engine.open_positions)))
        self.trades_label.setText(str(len(engine.closed_trades)))
        
        win_rate = engine.get_win_rate()
        self.winrate_label.setText(f"{win_rate:.1%}")
        
        # Update trade table if there are changes
        self.update_trade_table(self.current_strategy)
    
    def update_trade_table(self, strategy_name):
        """Update trade table for specific strategy and current instrument"""
        engine_key = f"{self.current_instrument}_{strategy_name}"
        engine = self.trading_engines.get(engine_key)
        if not engine:
            return
            
        table = self.trade_tables[strategy_name]
        
        all_trades = engine.open_positions + engine.closed_trades
        
        table.setRowCount(len(all_trades))
        
        for i, trade in enumerate(all_trades):
            # Column 0: Time
            table.setItem(i, 0, QTableWidgetItem(trade.entry_time.strftime('%Y-%m-%d %H:%M')))
            
            # Column 1: Signal Type (CALL/PUT)
            signal_item = QTableWidgetItem(trade.signal_type)
            if trade.signal_type == 'CALL':
                signal_item.setForeground(QColor('green'))
            else:
                signal_item.setForeground(QColor('red'))
            table.setItem(i, 1, signal_item)
            
            # Column 2: Strike/Type (Option details)
            if trade.strike > 0 and trade.option_type:
                strike_text = f"{trade.strike} {trade.option_type}"
            else:
                strike_text = "-"
            table.setItem(i, 2, QTableWidgetItem(strike_text))
            
            # Column 3: Premium (Entry)
            table.setItem(i, 3, QTableWidgetItem(f"₹{trade.entry_price:.2f}"))
            
            # Column 4: Current/Exit Price
            if trade.exit_price:
                current_text = f"₹{trade.exit_price:.2f}"
            elif trade.current_price > 0:
                current_text = f"₹{trade.current_price:.2f}"
            else:
                current_text = "-"
            table.setItem(i, 4, QTableWidgetItem(current_text))
            
            # Column 5: Stop Loss
            table.setItem(i, 5, QTableWidgetItem(f"₹{trade.stop_loss:.2f}"))
            
            # Column 6: Target
            table.setItem(i, 6, QTableWidgetItem(f"₹{trade.target:.2f}"))
            
            # Column 7: P&L
            pnl = trade.pnl if trade.pnl else 0
            pnl_item = QTableWidgetItem(f"₹{pnl:,.2f}")
            if pnl > 0:
                pnl_item.setForeground(QColor('green'))
                pnl_item.setBackground(QColor(230, 255, 230))  # Light green
            elif pnl < 0:
                pnl_item.setForeground(QColor('red'))
                pnl_item.setBackground(QColor(255, 230, 230))  # Light red
            table.setItem(i, 7, pnl_item)
            
            # Column 8: Status
            status = trade.status
            status_item = QTableWidgetItem(status)
            if status == 'OPEN':
                status_item.setBackground(QColor('yellow'))
            elif status in ['TARGET', 'PROFIT']:
                status_item.setBackground(QColor('lightgreen'))
            elif status in ['STOP_LOSS', 'LOSS']:
                status_item.setBackground(QColor('lightcoral'))
            table.setItem(i, 8, status_item)
            
            # Column 9: Duration
            duration = ""
            if trade.exit_time:
                duration_seconds = (trade.exit_time - trade.entry_time).total_seconds()
                duration = f"{int(duration_seconds // 60)} min"
            table.setItem(i, 9, QTableWidgetItem(duration))
            
            # Column 10: Notes
            notes_text = trade.notes[:50] if trade.notes else ""
            table.setItem(i, 10, QTableWidgetItem(notes_text))
    
    def update_strategy_info(self):
        """Update strategy information display"""
        strategy = self.strategies[self.current_strategy]
        info = strategy.get_info()
        self.strategy_info_text.setHtml(info)
    
    def toggle_auto_trade(self, checked):
        """Toggle auto-trading"""
        if checked:
            # Show strategy selection dialog
            dialog = StrategySelectionDialog(
                list(self.strategies.keys()),
                self.selected_auto_trade_strategies,
                self
            )
            
            if dialog.exec_() == QDialog.Accepted:
                selected = dialog.get_selected_strategies()
                
                # Check if at least one strategy is selected
                if not selected:
                    QMessageBox.warning(
                        self,
                        "No Strategies Selected",
                        "Please select at least one strategy for auto trading."
                    )
                    self.auto_trade_btn.setChecked(False)
                    return
                
                # Update selected strategies
                self.selected_auto_trade_strategies = selected
                print(f"[AUTO-TRADE CONFIG] Selected strategies: {self.selected_auto_trade_strategies}")
                
                # Update button appearance
                self.auto_trade_btn.setText("Disable Auto-Trade")
                self.auto_trade_btn.setStyleSheet("background-color: green; color: white;")
                
                # Show confirmation message
                strategy_list = "\n• ".join(selected)
                QMessageBox.information(
                    self,
                    "Auto Trading Enabled",
                    f"Auto trading enabled for:\n\n• {strategy_list}"
                )
            else:
                # User cancelled, uncheck the button
                self.auto_trade_btn.setChecked(False)
        else:
            self.auto_trade_btn.setText("Enable Auto-Trade")
            self.auto_trade_btn.setStyleSheet("")
            QMessageBox.information(
                self,
                "Auto Trading Disabled",
                "Auto trading has been disabled."
            )
    
    def save_all_trades(self):
        """Save all trades to JSON files for each instrument-strategy combination"""
        for engine_key, engine in self.trading_engines.items():
            # Parse instrument and strategy from key format: "INSTRUMENT_STRATEGY"
            parts = engine_key.split('_', 1)
            instrument = parts[0].lower().replace(' ', '_')
            strategy = parts[1].lower().replace(' ', '_').replace('+', '')
            filename = f"trades_{instrument}_{strategy}.json"
            engine.save_trades(filename)
        
        QMessageBox.information(self, "Saved", "All trades saved successfully!")
    
    def load_all_trades(self):
        """Load all saved trades for each instrument-strategy combination"""
        for engine_key, engine in self.trading_engines.items():
            # Parse instrument and strategy from key format: "INSTRUMENT_STRATEGY"
            parts = engine_key.split('_', 1)
            instrument = parts[0].lower().replace(' ', '_')
            strategy = parts[1].lower().replace(' ', '_').replace('+', '')
            filename = f"trades_{instrument}_{strategy}.json"
            try:
                engine.load_trades(filename)
                print(f"[INFO] Loaded trades from {filename}")
            except FileNotFoundError:
                pass  # No saved file yet
            except Exception as e:
                print(f"[WARNING] Failed to load {filename}: {e}")
    
    def reset_all_data(self):
        """Reset all trading data - capital and trades"""
        reply = QMessageBox.question(
            self,
            "Reset All Data",
            "This will delete ALL trades and reset capital to ₹10,00,000 for all strategies.\n\n"
            "This action cannot be undone.\n\nAre you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Reset all engines in memory
                for engine_key in self.trading_engines.keys():
                    self.trading_engines[engine_key] = PaperTradingEngine(initial_capital=1000000)
                
                # Delete all trade files
                import os
                import glob
                trade_files = glob.glob("trades_*.json")
                for file in trade_files:
                    try:
                        os.remove(file)
                        print(f"[INFO] Deleted {file}")
                    except Exception as e:
                        print(f"[WARNING] Could not delete {file}: {e}")
                
                # Update UI
                for strategy_name in self.strategies.keys():
                    self.update_trade_table(strategy_name)
                
                self.update_ui()
                
                QMessageBox.information(
                    self,
                    "Reset Complete",
                    "All trades cleared and capital reset to ₹10,00,000 per strategy.\n\n"
                    "Ready for fresh option trading!"
                )
                
                print("\n" + "="*70)
                print("   DATA RESET COMPLETE")
                print("="*70)
                print(f"Starting Capital: ₹10,00,000 (All Strategies)")
                print(f"Total Trades: 0")
                print(f"Trade History: Cleared")
                print("="*70 + "\n")
                
            except Exception as e:
                QMessageBox.critical(self, "Reset Failed", f"Error resetting data: {e}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        print("Closing application...")
        
        # Stop timers first
        if hasattr(self, 'ui_timer'):
            self.ui_timer.stop()
        
        # Stop data thread
        if hasattr(self, 'data_thread'):
            print("Stopping data thread...")
            self.data_thread.stop()
            self.data_thread.quit()
            self.data_thread.wait(2000)  # Wait max 2 seconds
            
            if self.data_thread.isRunning():
                print("Force terminating thread...")
                self.data_thread.terminate()
                self.data_thread.wait(1000)
        
        # Save trades
        try:
            self.save_all_trades()
        except Exception as e:
            print(f"Error saving trades: {e}")
        
        print("Application closed successfully")
        event.accept()
        
        # Force quit the application
        QApplication.quit()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = TradingMainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
