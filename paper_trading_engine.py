"""
Paper Trading Engine

Simulates live trading without real money.
Tracks positions, calculates P&L, and manages trade history.
"""

import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional
from option_price_fetcher import OptionPriceFetcher


@dataclass
class Trade:
    """Represents a single trade"""
    trade_id: str
    signal_type: str  # 'CALL' or 'PUT'
    entry_price: float  # Option premium, not spot price
    entry_time: datetime
    quantity: int
    stop_loss: float
    target: float
    strategy: str
    notes: str = ""
    strike: int = 0  # Option strike price
    option_type: str = ""  # CE or PE
    spot_price: float = 0  # Spot price at entry
    
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    status: str = "OPEN"  # OPEN, TARGET, STOP_LOSS, MANUAL_EXIT
    pnl: Optional[float] = None
    current_price: float = 0
    
    def update_current_price(self, price: float):
        """Update current market price and unrealized P&L"""
        self.current_price = price
        
        if self.status == "OPEN":
            # For option trades (both CALL/PUT), we BUY the option
            # P&L = (current_premium - entry_premium) * quantity
            # PUT option premium rises when spot falls, so this is always correct
            if self.strike > 0 and self.option_type:
                # Option trade - always long (bought option)
                self.pnl = (price - self.entry_price) * self.quantity
            else:
                # Spot/futures trade - directional
                if self.signal_type == "CALL":
                    self.pnl = (price - self.entry_price) * self.quantity
                else:  # PUT (short)
                    self.pnl = (self.entry_price - price) * self.quantity
    
    def check_exit_conditions(self, current_price: float) -> bool:
        """Check if stop loss or target hit"""
        if self.status != "OPEN":
            return False
        
        # For option trades (both CALL/PUT), we BUY the option
        # SL triggers when premium drops below stop_loss
        # Target triggers when premium rises above target
        if self.strike > 0 and self.option_type:
            # Option trade - always long position
            if current_price >= self.target:
                self.close_trade(current_price, "TARGET")
                return True
            elif current_price <= self.stop_loss:
                self.close_trade(current_price, "STOP_LOSS")
                return True
        else:
            # Spot/futures trade - directional
            if self.signal_type == "CALL":
                if current_price >= self.target:
                    self.close_trade(current_price, "TARGET")
                    return True
                elif current_price <= self.stop_loss:
                    self.close_trade(current_price, "STOP_LOSS")
                    return True
            else:  # PUT (short)
                if current_price <= self.target:
                    self.close_trade(current_price, "TARGET")
                    return True
                elif current_price >= self.stop_loss:
                    self.close_trade(current_price, "STOP_LOSS")
                    return True
        
        return False
    
    def close_trade(self, exit_price: float, status: str):
        """Close the trade"""
        self.exit_price = exit_price
        self.exit_time = datetime.now()
        self.status = status
        
        # For option trades (both CALL/PUT), we BUY the option
        # P&L = (exit_premium - entry_premium) * quantity
        if self.strike > 0 and self.option_type:
            # Option trade - always long (bought option)
            self.pnl = (exit_price - self.entry_price) * self.quantity
        else:
            # Spot/futures trade - directional
            if self.signal_type == "CALL":
                self.pnl = (exit_price - self.entry_price) * self.quantity
            else:  # PUT (short)
                self.pnl = (self.entry_price - exit_price) * self.quantity
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['entry_time'] = self.entry_time.isoformat()
        if self.exit_time:
            data['exit_time'] = self.exit_time.isoformat()
        return data
    
    @staticmethod
    def from_dict(data):
        """Create Trade from dictionary"""
        data['entry_time'] = datetime.fromisoformat(data['entry_time'])
        if data.get('exit_time'):
            data['exit_time'] = datetime.fromisoformat(data['exit_time'])
        return Trade(**data)


class PaperTradingEngine:
    """
    Paper trading engine for simulating trades
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.open_positions: List[Trade] = []
        self.closed_trades: List[Trade] = []
        self.trade_counter = 0
    
    def open_position(self, signal_type: str, entry_price: float, 
                     stop_loss: float, target: float, quantity: int,
                     strategy: str, notes: str = "",
                     strike: int = 0, option_type: str = "", spot_price: float = 0) -> Optional[Trade]:
        """
        Open a new position
        
        Args:
            signal_type: 'CALL' or 'PUT'
            entry_price: Entry price (option premium for options)
            stop_loss: Stop loss price
            target: Target price
            quantity: Number of shares/contracts
            strategy: Strategy name
            notes: Additional notes
            strike: Option strike price
            option_type: 'CE' or 'PE'
            spot_price: Spot price at entry
        
        Returns:
            Trade object if successful, None otherwise
        """
        # Calculate required margin
        margin_required = entry_price * quantity * 0.20  # 20% margin for F&O
        
        if margin_required > self.capital:
            print(f"Insufficient capital. Required: ₹{margin_required:,.2f}, Available: ₹{self.capital:,.2f}")
            return None
        
        # Create trade
        self.trade_counter += 1
        trade = Trade(
            trade_id=f"{strategy[:3].upper()}-{self.trade_counter:04d}",
            signal_type=signal_type,
            entry_price=entry_price,
            entry_time=datetime.now(),
            quantity=quantity,
            stop_loss=stop_loss,
            target=target,
            strategy=strategy,
            notes=notes,
            strike=strike,
            option_type=option_type,
            spot_price=spot_price
        )
        
        # Deduct margin
        self.capital -= margin_required
        
        self.open_positions.append(trade)
        
        print(f"✓ Position opened: {trade.trade_id} - {signal_type} @ ₹{entry_price:.2f}")
        
        return trade
    
    def close_position(self, trade: Trade, exit_price: float, status: str = "MANUAL_EXIT"):
        """Manually close a position"""
        if trade not in self.open_positions:
            return False
        
        trade.close_trade(exit_price, status)
        
        # For options: Return premium received from selling
        # P&L already calculated in trade.pnl
        sale_proceeds = exit_price * trade.quantity
        self.capital += sale_proceeds
        
        # Move to closed trades
        self.open_positions.remove(trade)
        self.closed_trades.append(trade)
        
        print(f"✓ Position closed: {trade.trade_id} - P&L: ₹{trade.pnl:,.2f}")
        
        return True
    
    def update_positions(self, current_price: float):
        """
        Update all open positions with current market price
        Check for stop loss and target hits
        """
        positions_to_close = []
        
        for trade in self.open_positions:
            trade.update_current_price(current_price)
            
            # Check exit conditions
            if trade.check_exit_conditions(current_price):
                positions_to_close.append(trade)
        
        # Close positions that hit SL or target
        for trade in positions_to_close:
            margin = trade.entry_price * trade.quantity * 0.20
            self.capital += margin + trade.pnl
            
            self.open_positions.remove(trade)
            self.closed_trades.append(trade)
            
            print(f"✓ Auto-closed: {trade.trade_id} - {trade.status} - P&L: ₹{trade.pnl:,.2f}")
    
    def get_total_pnl(self) -> float:
        """Calculate total P&L (realized + unrealized)"""
        realized_pnl = sum(trade.pnl for trade in self.closed_trades if trade.pnl)
        unrealized_pnl = sum(trade.pnl for trade in self.open_positions if trade.pnl)
        return realized_pnl + unrealized_pnl
    
    def get_win_rate(self) -> float:
        """Calculate win rate from closed trades"""
        if not self.closed_trades:
            return 0.0
        
        winning_trades = sum(1 for trade in self.closed_trades if trade.pnl and trade.pnl > 0)
        return winning_trades / len(self.closed_trades)
    
    def get_statistics(self) -> dict:
        """Get trading statistics"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0
            }
        
        winning_trades = [t for t in self.closed_trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl and t.pnl < 0]
        
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        
        return {
            'total_trades': len(self.closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(self.closed_trades),
            'total_pnl': self.get_total_pnl(),
            'avg_win': total_wins / len(winning_trades) if winning_trades else 0,
            'avg_loss': total_losses / len(losing_trades) if losing_trades else 0,
            'profit_factor': total_wins / total_losses if total_losses > 0 else float('inf')
        }
    
    def save_trades(self, filename: str):
        """Save all trades to JSON file"""
        data = {
            'initial_capital': self.initial_capital,
            'current_capital': self.capital,
            'open_positions': [trade.to_dict() for trade in self.open_positions],
            'closed_trades': [trade.to_dict() for trade in self.closed_trades],
            'trade_counter': self.trade_counter
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Trades saved to {filename}")
    
    def load_trades(self, filename: str):
        """Load trades from JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        self.initial_capital = data['initial_capital']
        self.capital = data['current_capital']
        self.trade_counter = data['trade_counter']
        
        self.open_positions = [Trade.from_dict(t) for t in data['open_positions']]
        self.closed_trades = [Trade.from_dict(t) for t in data['closed_trades']]
        
        print(f"✓ Trades loaded from {filename}")
        print(f"  Open positions: {len(self.open_positions)}")
        print(f"  Closed trades: {len(self.closed_trades)}")
    
    def reset(self):
        """Reset engine to initial state"""
        self.capital = self.initial_capital
        self.open_positions = []
        self.closed_trades = []
        self.trade_counter = 0
        print("✓ Trading engine reset")


# Example usage
if __name__ == "__main__":
    # Create engine
    engine = PaperTradingEngine(initial_capital=100000)
    
    # Open a CALL position
    trade1 = engine.open_position(
        signal_type='CALL',
        entry_price=23500,
        stop_loss=23450,
        target=23600,
        quantity=75,
        strategy='Bollinger + MACD',
        notes='Bullish breakout above BB upper'
    )
    
    # Simulate price movement
    print("\n--- Price updates ---")
    engine.update_positions(23520)  # Price moves up
    print(f"Unrealized P&L: ₹{trade1.pnl:,.2f}")
    
    engine.update_positions(23600)  # Target hit
    
    # Statistics
    print("\n--- Statistics ---")
    stats = engine.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Save trades
    engine.save_trades('test_trades.json')
