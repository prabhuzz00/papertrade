"""
NIFTY Options Paper Trading Platform

Automated option trading based on NIFTY signals:
- CALL signal → Buy ATM CE option
- PUT signal → Buy ATM PE option
- Stop Loss and Target at 1:2 ratio (Risk:Reward)
- Real-time option prices via XTS GetOptionSymbol API
"""

import json
from datetime import datetime
from typing import Optional, Dict
import requests
import urllib3
from dataclasses import dataclass, asdict
from xts_config import XTS_BASE_URL, XTS_APP_KEY, XTS_SECRET_KEY, XTS_SOURCE

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class OptionTrade:
    """Represents a single option trade"""
    trade_id: str
    signal_type: str  # 'CALL' or 'PUT'
    instrument_type: str  # 'CE' or 'PE'
    strike_price: int
    spot_price: float  # NIFTY spot at entry
    entry_premium: float  # Option LTP at entry
    entry_time: datetime
    quantity: int  # Lot size
    stop_loss: float  # Premium level
    target: float  # Premium level
    strategy: str
    instrument_id: int  # XTS ExchangeInstrumentID
    expiry: str
    
    exit_premium: Optional[float] = None
    exit_time: Optional[datetime] = None
    status: str = "OPEN"  # OPEN, TARGET, STOP_LOSS, MANUAL_EXIT
    pnl: float = 0.0
    current_premium: float = 0.0
    
    def update_current_premium(self, premium: float):
        """Update current option premium and unrealized P&L"""
        self.current_premium = premium
        
        if self.status == "OPEN":
            # Long option: profit when premium increases
            self.pnl = (premium - self.entry_premium) * self.quantity
    
    def check_exit_conditions(self, current_premium: float) -> bool:
        """Check if stop loss or target hit"""
        if self.status != "OPEN":
            return False
        
        # Long option: exit when premium reaches target or hits SL
        if current_premium >= self.target:
            self.close_trade(current_premium, "TARGET")
            return True
        elif current_premium <= self.stop_loss:
            self.close_trade(current_premium, "STOP_LOSS")
            return True
        
        return False
    
    def close_trade(self, exit_premium: float, status: str):
        """Close the trade"""
        self.exit_premium = exit_premium
        self.exit_time = datetime.now()
        self.status = status
        
        # Calculate P&L (always long options)
        self.pnl = (exit_premium - self.entry_premium) * self.quantity
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['entry_time'] = self.entry_time.isoformat()
        if self.exit_time:
            data['exit_time'] = self.exit_time.isoformat()
        return data
    
    @staticmethod
    def from_dict(data):
        """Create OptionTrade from dictionary"""
        data['entry_time'] = datetime.fromisoformat(data['entry_time'])
        if data.get('exit_time'):
            data['exit_time'] = datetime.fromisoformat(data['exit_time'])
        return OptionTrade(**data)


class NiftyOptionTrader:
    """
    NIFTY Options Paper Trading Engine
    Executes option trades based on signals with automatic SL and target
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.open_positions = []
        self.closed_trades = []
        self.trade_counter = 0
        
        # XTS API connection
        self.token = None
        self.base_url = XTS_BASE_URL
        self.app_key = XTS_APP_KEY
        self.secret_key = XTS_SECRET_KEY
        self.source = XTS_SOURCE
        
        # Default settings
        self.lot_size = 65  # NIFTY lot size
        self.risk_reward_ratio = 2  # 1:2 (Risk:Reward)
        self.risk_percent = 2  # Risk 2% per trade
        
        # Login on initialization
        self.login()
    
    def login(self) -> bool:
        """Login to XTS API"""
        try:
            url = f"{self.base_url}/auth/login"
            payload = {
                'secretKey': self.secret_key,
                'appKey': self.app_key,
                'source': self.source
            }
            
            response = requests.post(
                url, json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10, verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('result', {}).get('token')
                if self.token:
                    print("✓ XTS Login successful")
                    return True
            
            print(f"✗ XTS Login failed: {response.text}")
            return False
        
        except Exception as e:
            print(f"✗ XTS Login error: {e}")
            return False
    
    def get_nifty_spot(self) -> Optional[float]:
        """Get current NIFTY spot price"""
        if not self.token:
            self.login()
        
        url = f"{self.base_url}/instruments/quotes"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.token
        }
        
        payload = {
            "instruments": [
                {
                    "exchangeSegment": 1,
                    "exchangeInstrumentID": 26000
                }
            ],
            "xtsMessageCode": 1502,
            "publishFormat": "JSON"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and 'listQuotes' in data['result']:
                    quotes = data['result']['listQuotes']
                    if quotes and len(quotes) > 0:
                        quote = quotes[0]
                        if isinstance(quote, str):
                            quote = json.loads(quote)
                        
                        if isinstance(quote, dict) and 'Touchline' in quote:
                            ltp = quote['Touchline'].get('LastTradedPrice')
                            if ltp:
                                return float(ltp)
        except Exception as e:
            print(f"Error fetching NIFTY spot: {e}")
        
        return None
    
    def get_weekly_expiry(self) -> Optional[str]:
        """Get nearest weekly expiry for NIFTY options"""
        if not self.token:
            self.login()
        
        url = f"{self.base_url}/instruments/instrument/expiryDate"
        headers = {'Authorization': self.token}
        
        params = {
            'exchangeSegment': 2,
            'series': 'OPTIDX',
            'symbol': 'NIFTY'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and len(data['result']) > 1:
                    # Use weekly expiry (usually second in list)
                    weekly_expiry = data['result'][1]
                    expiry_obj = datetime.fromisoformat(weekly_expiry.split('T')[0])
                    return expiry_obj.strftime('%d%b%Y')  # "10Feb2026"
        except Exception as e:
            print(f"Error fetching expiry: {e}")
        
        return None
    
    def get_atm_option_details(self, spot_price: float, option_type: str, expiry: str) -> Optional[Dict]:
        """
        Get ATM option details using GetOptionSymbol API
        
        Args:
            spot_price: Current NIFTY spot price
            option_type: 'CE' or 'PE'
            expiry: Expiry in 'ddMmmyyyy' format
        
        Returns:
            Dict with instrument_id, strike, display_name, lot_size
        """
        if not self.token:
            self.login()
        
        # Calculate ATM strike (round to nearest 50)
        atm_strike = round(spot_price / 50) * 50
        
        url = f"{self.base_url}/instruments/instrument/optionSymbol"
        headers = {'Authorization': self.token}
        
        params = {
            'exchangeSegment': 2,
            'series': 'OPTIDX',
            'symbol': 'NIFTY',
            'expiryDate': expiry,
            'optionType': option_type,
            'strikePrice': int(atm_strike)
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                data = response.json()
                if data.get('type') == 'success' and 'result' in data:
                    result = data['result']
                    if isinstance(result, list) and len(result) > 0:
                        instrument = result[0]
                        return {
                            'instrument_id': instrument.get('ExchangeInstrumentID'),
                            'strike': instrument.get('StrikePrice'),
                            'display_name': instrument.get('DisplayName'),
                            'lot_size': instrument.get('LotSize', 65)
                        }
        except Exception as e:
            print(f"Error fetching option details: {e}")
        
        return None
    
    def get_option_ltp(self, instrument_id: int) -> Optional[float]:
        """Get current LTP of an option"""
        if not self.token:
            self.login()
        
        url = f"{self.base_url}/instruments/quotes"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.token
        }
        
        payload = {
            "instruments": [
                {
                    "exchangeSegment": 2,
                    "exchangeInstrumentID": instrument_id
                }
            ],
            "xtsMessageCode": 1502,
            "publishFormat": "JSON"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and 'listQuotes' in data['result']:
                    quotes = data['result']['listQuotes']
                    if quotes and len(quotes) > 0:
                        quote = quotes[0]
                        if isinstance(quote, str):
                            quote = json.loads(quote)
                        
                        if isinstance(quote, dict) and 'Touchline' in quote:
                            ltp = quote['Touchline'].get('LastTradedPrice')
                            if ltp:
                                return float(ltp)
        except Exception as e:
            print(f"Error fetching option LTP: {e}")
        
        return None
    
    def execute_signal(self, signal_type: str, strategy: str) -> Optional[OptionTrade]:
        """
        Execute option trade based on signal
        
        Args:
            signal_type: 'CALL' or 'PUT'
            strategy: Strategy name
        
        Returns:
            OptionTrade object if successful
        """
        print(f"\n{'='*70}")
        print(f"SIGNAL DETECTED: {signal_type} from {strategy}")
        print(f"{'='*70}")
        
        # Get NIFTY spot price
        spot_price = self.get_nifty_spot()
        if not spot_price:
            print("✗ Could not fetch NIFTY spot price")
            return None
        
        print(f"NIFTY Spot: Rs.{spot_price:,.2f}")
        
        # Get weekly expiry
        expiry = self.get_weekly_expiry()
        if not expiry:
            print("✗ Could not fetch expiry date")
            return None
        
        print(f"Expiry: {expiry}")
        
        # Determine option type (CE for CALL signal, PE for PUT signal)
        option_type = 'CE' if signal_type == 'CALL' else 'PE'
        
        # Get ATM option details
        option_details = self.get_atm_option_details(spot_price, option_type, expiry)
        if not option_details:
            print(f"✗ Could not fetch ATM {option_type} option details")
            return None
        
        instrument_id = option_details['instrument_id']
        strike = option_details['strike']
        lot_size = option_details['lot_size']
        display_name = option_details['display_name']
        
        print(f"ATM Strike: {strike}")
        print(f"Option: {display_name} (ID: {instrument_id})")
        
        # Get option LTP
        entry_premium = self.get_option_ltp(instrument_id)
        if not entry_premium:
            print("✗ Could not fetch option LTP")
            return None
        
        print(f"Entry Premium: Rs.{entry_premium:.2f}")
        
        # Calculate risk per trade (2% of capital)
        risk_amount = self.capital * (self.risk_percent / 100)
        
        # Calculate stop loss (10% below entry for safety)
        stop_loss_percent = 10
        stop_loss = entry_premium * (1 - stop_loss_percent / 100)
        
        # Calculate target (1:2 risk:reward)
        risk_per_lot = entry_premium - stop_loss
        target = entry_premium + (risk_per_lot * self.risk_reward_ratio)
        
        # Calculate quantity (number of lots)
        # Risk per lot in rupees = risk_per_point * lot_size
        risk_per_lot_rupees = risk_per_lot * lot_size
        num_lots = max(1, int(risk_amount / risk_per_lot_rupees))
        quantity = lot_size * num_lots
        
        # Calculate total investment
        investment = entry_premium * quantity
        
        print(f"\nTrade Setup:")
        print(f"  Quantity: {quantity} ({num_lots} lot{'s' if num_lots > 1 else ''})")
        print(f"  Investment: Rs.{investment:,.2f}")
        print(f"  Stop Loss: Rs.{stop_loss:.2f} (-{stop_loss_percent}%)")
        print(f"  Target: Rs.{target:.2f} (+{stop_loss_percent * self.risk_reward_ratio}%)")
        print(f"  Risk: Rs.{risk_per_lot * quantity:,.2f}")
        print(f"  Potential Reward: Rs.{(target - entry_premium) * quantity:,.2f}")
        print(f"  Risk:Reward = 1:{self.risk_reward_ratio}")
        
        # Check if sufficient capital
        if investment > self.capital:
            print(f"\n✗ Insufficient capital. Required: Rs.{investment:,.2f}, Available: Rs.{self.capital:,.2f}")
            return None
        
        # Create trade
        self.trade_counter += 1
        trade = OptionTrade(
            trade_id=f"OPT-{self.trade_counter:04d}",
            signal_type=signal_type,
            instrument_type=option_type,
            strike_price=strike,
            spot_price=spot_price,
            entry_premium=entry_premium,
            entry_time=datetime.now(),
            quantity=quantity,
            stop_loss=stop_loss,
            target=target,
            strategy=strategy,
            instrument_id=instrument_id,
            expiry=expiry,
            current_premium=entry_premium  # Initialize with entry premium
        )
        
        # Deduct investment from capital
        self.capital -= investment
        
        self.open_positions.append(trade)
        
        print(f"\n✓ TRADE EXECUTED: {trade.trade_id}")
        print(f"  Remaining Capital: Rs.{self.capital:,.2f}")
        print(f"{'='*70}\n")
        
        return trade
    
    def update_positions(self):
        """Update all open positions with current market prices"""
        if not self.open_positions:
            return
        
        positions_to_close = []
        
        for trade in self.open_positions:
            # Get current option premium
            current_premium = self.get_option_ltp(trade.instrument_id)
            
            if current_premium:
                trade.update_current_premium(current_premium)
                
                # Check exit conditions
                if trade.check_exit_conditions(current_premium):
                    positions_to_close.append(trade)
        
        # Close positions that hit SL or target
        for trade in positions_to_close:
            # Return investment + P&L
            exit_value = trade.exit_premium * trade.quantity
            self.capital += exit_value
            
            self.open_positions.remove(trade)
            self.closed_trades.append(trade)
            
            print(f"\n✓ TRADE CLOSED: {trade.trade_id}")
            print(f"  Status: {trade.status}")
            print(f"  Entry: Rs.{trade.entry_premium:.2f} → Exit: Rs.{trade.exit_premium:.2f}")
            print(f"  P&L: Rs.{trade.pnl:,.2f}")
            print(f"  Capital: Rs.{self.capital:,.2f}\n")
    
    def close_position_manual(self, trade_id: str) -> bool:
        """Manually close a position"""
        trade = next((t for t in self.open_positions if t.trade_id == trade_id), None)
        
        if not trade:
            print(f"✗ Trade {trade_id} not found in open positions")
            return False
        
        # Get current premium
        current_premium = self.get_option_ltp(trade.instrument_id)
        if not current_premium:
            print("✗ Could not fetch current premium")
            return False
        
        trade.close_trade(current_premium, "MANUAL_EXIT")
        
        # Return investment + P&L
        exit_value = trade.exit_premium * trade.quantity
        self.capital += exit_value
        
        self.open_positions.remove(trade)
        self.closed_trades.append(trade)
        
        print(f"\n✓ Position manually closed: {trade.trade_id}")
        print(f"  P&L: Rs.{trade.pnl:,.2f}")
        print(f"  Capital: Rs.{self.capital:,.2f}\n")
        
        return True
    
    def get_statistics(self) -> dict:
        """Get trading statistics"""
        if not self.closed_trades:
            total_pnl = sum(t.pnl for t in self.open_positions if t.pnl is not None)
            return {
                'total_trades': len(self.open_positions),
                'open_positions': len(self.open_positions),
                'closed_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': total_pnl,
                'realized_pnl': 0.0,
                'unrealized_pnl': total_pnl,
                'current_capital': self.capital,
                'total_capital': self.capital + sum(t.entry_premium * t.quantity for t in self.open_positions),
                'return_pct': 0.0
            }
        
        winning_trades = [t for t in self.closed_trades if t.pnl is not None and t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl is not None and t.pnl < 0]
        
        realized_pnl = sum(t.pnl for t in self.closed_trades if t.pnl is not None)
        unrealized_pnl = sum(t.pnl for t in self.open_positions if t.pnl is not None)
        total_pnl = realized_pnl + unrealized_pnl
        
        total_capital = self.capital + sum(t.current_premium * t.quantity for t in self.open_positions)
        return_pct = ((total_capital - self.initial_capital) / self.initial_capital) * 100
        
        return {
            'total_trades': len(self.closed_trades) + len(self.open_positions),
            'open_positions': len(self.open_positions),
            'closed_trades': len(self.closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(self.closed_trades) if self.closed_trades else 0,
            'total_pnl': total_pnl,
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'current_capital': self.capital,
            'total_capital': total_capital,
            'return_pct': return_pct
        }
    
    def save_trades(self, filename: str = "nifty_option_trades.json"):
        """Save all trades to JSON file"""
        data = {
            'initial_capital': self.initial_capital,
            'current_capital': self.capital,
            'open_positions': [trade.to_dict() for trade in self.open_positions],
            'closed_trades': [trade.to_dict() for trade in self.closed_trades],
            'trade_counter': self.trade_counter,
            'settings': {
                'lot_size': self.lot_size,
                'risk_reward_ratio': self.risk_reward_ratio,
                'risk_percent': self.risk_percent
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Trades saved to {filename}")
    
    def load_trades(self, filename: str = "nifty_option_trades.json"):
        """Load trades from JSON file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            self.initial_capital = data['initial_capital']
            self.capital = data['current_capital']
            self.trade_counter = data['trade_counter']
            
            self.open_positions = [OptionTrade.from_dict(t) for t in data['open_positions']]
            self.closed_trades = [OptionTrade.from_dict(t) for t in data['closed_trades']]
            
            if 'settings' in data:
                self.lot_size = data['settings'].get('lot_size', 65)
                self.risk_reward_ratio = data['settings'].get('risk_reward_ratio', 2)
                self.risk_percent = data['settings'].get('risk_percent', 2)
            
            print(f"✓ Trades loaded from {filename}")
            print(f"  Open positions: {len(self.open_positions)}")
            print(f"  Closed trades: {len(self.closed_trades)}")
        except FileNotFoundError:
            print(f"✗ File {filename} not found")
    
    def display_dashboard(self):
        """Display trading dashboard"""
        stats = self.get_statistics()
        
        print("\n" + "="*70)
        print("NIFTY OPTIONS TRADING DASHBOARD")
        print("="*70)
        print(f"Initial Capital:  Rs.{self.initial_capital:,.2f}")
        print(f"Current Capital:  Rs.{self.capital:,.2f}")
        print(f"Total Capital:    Rs.{stats['total_capital']:,.2f}")
        print(f"Total P&L:        Rs.{stats['total_pnl']:,.2f} ({stats['return_pct']:.2f}%)")
        print(f"Realized P&L:     Rs.{stats['realized_pnl']:,.2f}")
        print(f"Unrealized P&L:   Rs.{stats['unrealized_pnl']:,.2f}")
        print("-"*70)
        print(f"Total Trades:     {stats['total_trades']}")
        print(f"Open Positions:   {stats['open_positions']}")
        print(f"Closed Trades:    {stats['closed_trades']}")
        print(f"Winning Trades:   {stats['winning_trades']}")
        print(f"Losing Trades:    {stats['losing_trades']}")
        print(f"Win Rate:         {stats['win_rate']*100:.2f}%")
        print("="*70)
        
        if self.open_positions:
            print("\nOPEN POSITIONS:")
            print("-"*70)
            for trade in self.open_positions:
                pnl = trade.pnl if trade.pnl else 0.0
                print(f"{trade.trade_id} | {trade.instrument_type} {trade.strike_price} | "
                      f"Entry: Rs.{trade.entry_premium:.2f} | Current: Rs.{trade.current_premium:.2f} | "
                      f"P&L: Rs.{pnl:.2f}")
            print("-"*70)
        
        print()


# Example usage
if __name__ == "__main__":
    # Create trader
    trader = NiftyOptionTrader(initial_capital=100000)
    
    # Simulate CALL signal
    print("\n--- Simulating CALL Signal ---")
    trade1 = trader.execute_signal('CALL', 'Bollinger+MACD')
    
    # Display dashboard
    trader.display_dashboard()
    
    # Update positions (check SL/Target)
    print("\n--- Checking positions ---")
    trader.update_positions()
    
    # Save trades
    trader.save_trades()
    
    # Show final stats
    trader.display_dashboard()
