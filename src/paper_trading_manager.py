"""
🧾 Paper Trading Balance Manager
Manages virtual SOL balance for paper trading mode with persistence
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class PaperTradingManager:
    """
    Manages virtual SOL balance for paper trading
    Features:
    - Persistent balance storage
    - Trade execution simulation with balance tracking
    - Position management for paper trades
    - Transaction history
    """
    
    def __init__(self, initial_balance: float = 100.0):
        self.data_dir = Path("storage/paper_trading")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.balance_file = self.data_dir / "balance.json"
        self.trades_file = self.data_dir / "trades_history.json"
        
        # Default configuration
        self.initial_balance = initial_balance
        self.min_trade_amount = 0.001  # Minimum 0.001 SOL per trade
        self.max_trade_percentage = 0.10  # Maximum 10% of balance per trade
        
        # Current state
        self.current_balance = 0.0
        self.total_invested = 0.0
        self.total_profit_loss = 0.0
        self.active_positions = {}  # {token_address: position_data}
        self.trade_history = []
        
        # Load existing data
        self._load_balance_data()
        
        logger.info(f"Paper Trading Manager initialized with {self.current_balance:.4f} SOL")
    
    def _load_balance_data(self):
        """Load balance and trade data from files"""
        try:
            # Load balance data
            if self.balance_file.exists():
                with open(self.balance_file, 'r') as f:
                    data = json.load(f)
                    self.current_balance = data.get('current_balance', self.initial_balance)
                    self.total_invested = data.get('total_invested', 0.0)
                    self.total_profit_loss = data.get('total_profit_loss', 0.0)
                    self.active_positions = data.get('active_positions', {})
                    
                    # Convert datetime strings back to datetime objects for positions
                    for pos in self.active_positions.values():
                        if 'entry_time' in pos:
                            pos['entry_time'] = datetime.fromisoformat(pos['entry_time'])
            else:
                # First time - initialize with starting balance
                self.current_balance = self.initial_balance
                self._save_balance_data()
                logger.info(f"Initialized new paper trading account with {self.initial_balance} SOL")
            
            # Load trade history
            if self.trades_file.exists():
                with open(self.trades_file, 'r') as f:
                    self.trade_history = json.load(f)
            else:
                self.trade_history = []
                
        except Exception as e:
            logger.error(f"Error loading paper trading data: {e}")
            # Fallback to defaults
            self.current_balance = self.initial_balance
            self.total_invested = 0.0
            self.total_profit_loss = 0.0
            self.active_positions = {}
            self.trade_history = []
    
    def _save_balance_data(self):
        """Save balance and position data to file"""
        try:
            # Convert datetime objects to strings for JSON serialization
            positions_serializable = {}
            for token_addr, pos in self.active_positions.items():
                pos_copy = pos.copy()
                if 'entry_time' in pos_copy and isinstance(pos_copy['entry_time'], datetime):
                    pos_copy['entry_time'] = pos_copy['entry_time'].isoformat()
                positions_serializable[token_addr] = pos_copy
            
            balance_data = {
                'current_balance': self.current_balance,
                'total_invested': self.total_invested,
                'total_profit_loss': self.total_profit_loss,
                'active_positions': positions_serializable,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.balance_file, 'w') as f:
                json.dump(balance_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving paper trading balance: {e}")
    
    def _save_trade_history(self):
        """Save trade history to file"""
        try:
            with open(self.trades_file, 'w') as f:
                json.dump(self.trade_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving trade history: {e}")
    
    def get_balance(self) -> float:
        """Get current SOL balance"""
        return self.current_balance
    
    def get_total_portfolio_value(self) -> float:
        """Get total portfolio value (balance + active positions estimated value)"""
        return self.current_balance + self.total_invested
    
    def get_available_balance(self) -> float:
        """Get balance available for new trades"""
        return self.current_balance
    
    def can_afford_trade(self, amount_sol: float) -> bool:
        """Check if we can afford a trade of given amount"""
        if amount_sol < self.min_trade_amount:
            return False
        if amount_sol > self.current_balance:
            return False
        if amount_sol > (self.current_balance * self.max_trade_percentage):
            return False
        return True
    
    def get_max_trade_amount(self) -> float:
        """Get maximum allowed trade amount"""
        max_by_percentage = self.current_balance * self.max_trade_percentage
        return min(max_by_percentage, self.current_balance)
    
    def execute_buy_trade(self, token_address: str, amount_sol: float, token_price: float, token_symbol: str = "UNKNOWN") -> Dict:
        """Execute a buy trade in paper mode"""
        try:
            # Validate trade
            if not self.can_afford_trade(amount_sol):
                return {
                    'success': False,
                    'error': f'Insufficient balance. Available: {self.current_balance:.4f} SOL, Requested: {amount_sol:.4f} SOL',
                    'type': 'insufficient_balance'
                }
            
            # Calculate token amount
            tokens_bought = amount_sol / token_price if token_price > 0 else 0
            
            # Deduct from balance
            self.current_balance -= amount_sol
            self.total_invested += amount_sol
            
            # Create position
            position = {
                'token_address': token_address,
                'token_symbol': token_symbol,
                'entry_price': token_price,
                'entry_amount_sol': amount_sol,
                'tokens_owned': tokens_bought,
                'entry_time': datetime.now(),
                'type': 'buy'
            }
            
            # Track position
            if token_address in self.active_positions:
                # Add to existing position
                existing = self.active_positions[token_address]
                total_sol = existing['entry_amount_sol'] + amount_sol
                total_tokens = existing['tokens_owned'] + tokens_bought
                avg_price = total_sol / total_tokens if total_tokens > 0 else token_price
                
                existing['entry_amount_sol'] = total_sol
                existing['tokens_owned'] = total_tokens
                existing['entry_price'] = avg_price  # Average price
            else:
                self.active_positions[token_address] = position
            
            # Add to trade history
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'action': 'buy',
                'token_address': token_address,
                'token_symbol': token_symbol,
                'amount_sol': amount_sol,
                'token_price': token_price,
                'tokens_amount': tokens_bought,
                'balance_after': self.current_balance,
                'success': True,
                'type': 'paper'
            }
            self.trade_history.append(trade_record)
            
            # Save data
            self._save_balance_data()
            self._save_trade_history()
            
            logger.info(f"Paper BUY: {amount_sol:.4f} SOL → {tokens_bought:.2f} {token_symbol} @ ${token_price:.6f}")
            
            return {
                'success': True,
                'action': 'buy',
                'amount_sol': amount_sol,
                'tokens_bought': tokens_bought,
                'price': token_price,
                'balance_after': self.current_balance,
                'type': 'paper'
            }
            
        except Exception as e:
            logger.error(f"Error executing paper buy trade: {e}")
            return {
                'success': False,
                'error': str(e),
                'type': 'execution_error'
            }
    
    def execute_sell_trade(self, token_address: str, exit_price: float, sell_percentage: float = 1.0) -> Dict:
        """Execute a sell trade in paper mode"""
        try:
            if token_address not in self.active_positions:
                return {
                    'success': False,
                    'error': f'No active position for token {token_address}',
                    'type': 'position_not_found'
                }
            
            position = self.active_positions[token_address]
            tokens_to_sell = position['tokens_owned'] * sell_percentage
            sol_received = tokens_to_sell * exit_price
            
            # Calculate profit/loss
            entry_amount = position['entry_amount_sol'] * sell_percentage
            profit_loss = sol_received - entry_amount
            profit_percentage = (profit_loss / entry_amount) * 100 if entry_amount > 0 else 0
            
            # Update balance
            self.current_balance += sol_received
            self.total_invested -= entry_amount
            self.total_profit_loss += profit_loss
            
            # Update or remove position
            if sell_percentage >= 1.0:
                # Selling entire position
                del self.active_positions[token_address]
            else:
                # Partial sell
                position['tokens_owned'] *= (1 - sell_percentage)
                position['entry_amount_sol'] *= (1 - sell_percentage)
            
            # Add to trade history
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'action': 'sell',
                'token_address': token_address,
                'token_symbol': position.get('token_symbol', 'UNKNOWN'),
                'tokens_sold': tokens_to_sell,
                'exit_price': exit_price,
                'sol_received': sol_received,
                'profit_loss_sol': profit_loss,
                'profit_loss_percentage': profit_percentage,
                'balance_after': self.current_balance,
                'success': True,
                'type': 'paper'
            }
            self.trade_history.append(trade_record)
            
            # Save data
            self._save_balance_data()
            self._save_trade_history()
            
            logger.info(f"Paper SELL: {tokens_to_sell:.2f} tokens → {sol_received:.4f} SOL (P&L: {profit_loss:+.4f} SOL, {profit_percentage:+.2f}%)")
            
            return {
                'success': True,
                'action': 'sell',
                'tokens_sold': tokens_to_sell,
                'sol_received': sol_received,
                'profit_loss': profit_loss,
                'profit_percentage': profit_percentage,
                'balance_after': self.current_balance,
                'type': 'paper'
            }
            
        except Exception as e:
            logger.error(f"Error executing paper sell trade: {e}")
            return {
                'success': False,
                'error': str(e),
                'type': 'execution_error'
            }
    
    def get_position_info(self, token_address: str) -> Optional[Dict]:
        """Get information about a specific position"""
        return self.active_positions.get(token_address)
    
    def get_all_positions(self) -> Dict:
        """Get all active positions"""
        return self.active_positions.copy()
    
    def close_all_positions(self, current_prices: Dict[str, float]) -> List[Dict]:
        """Close all active positions (emergency sell)"""
        closed_positions = []
        
        for token_address in list(self.active_positions.keys()):
            if token_address in current_prices:
                exit_price = current_prices[token_address]
                result = self.execute_sell_trade(token_address, exit_price, 1.0)
                if result['success']:
                    closed_positions.append({
                        'token_address': token_address,
                        'result': result
                    })
        
        return closed_positions
    
    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        total_positions_value = sum(
            pos['tokens_owned'] * pos.get('current_price', pos['entry_price'])
            for pos in self.active_positions.values()
        )
        
        return {
            'current_balance': self.current_balance,
            'active_positions_count': len(self.active_positions),
            'total_invested': self.total_invested,
            'positions_estimated_value': total_positions_value,
            'total_portfolio_value': self.current_balance + total_positions_value,
            'total_profit_loss': self.total_profit_loss,
            'total_trades': len(self.trade_history),
            'starting_balance': self.initial_balance,
            'performance_percentage': ((self.current_balance + total_positions_value - self.initial_balance) / self.initial_balance) * 100
        }
    
    def add_funds(self, amount: float, reason: str = "Manual deposit"):
        """Add funds to paper trading account"""
        if amount > 0:
            self.current_balance += amount
            
            # Record transaction
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'action': 'deposit',
                'amount_sol': amount,
                'reason': reason,
                'balance_after': self.current_balance,
                'type': 'paper'
            }
            self.trade_history.append(trade_record)
            
            self._save_balance_data()
            self._save_trade_history()
            
            logger.info(f"Added {amount:.4f} SOL to paper trading account. New balance: {self.current_balance:.4f} SOL")
    
    def reset_account(self, new_balance: float = None):
        """Reset paper trading account to initial state"""
        if new_balance is not None:
            self.initial_balance = new_balance
        
        self.current_balance = self.initial_balance
        self.total_invested = 0.0
        self.total_profit_loss = 0.0
        self.active_positions = {}
        self.trade_history = []
        
        self._save_balance_data()
        self._save_trade_history()
        
        logger.info(f"Paper trading account reset to {self.initial_balance:.4f} SOL")