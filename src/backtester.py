import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
import json
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class BacktestTrade:
    timestamp: datetime
    symbol: str
    action: str  # 'buy' or 'sell'
    price: float
    amount_sol: float
    tokens_received: float
    confidence: float
    risk_score: float

@dataclass
class BacktestResult:
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    avg_trade_return: float
    best_trade: float
    worst_trade: float
    total_fees: float
    final_balance: float

class Backtester:
    def __init__(self, initial_balance: float = 100.0):
        self.initial_balance = initial_balance
        self.trading_fee = 0.0025  # 0.25% trading fee
        self.slippage = 0.005  # 0.5% slippage
    
    async def run_backtest(self, days: int = 30, strategy_params: Optional[Dict] = None) -> Dict:
        """Run a backtest simulation"""
        try:
            logger.info(f"Starting backtest for {days} days")
            
            # Load historical data (mock data for now)
            historical_data = await self._load_historical_data(days)
            
            if not historical_data:
                logger.warning("No historical data available for backtesting")
                return self._empty_result()
            
            # Run simulation
            result = await self._simulate_trading(historical_data, strategy_params or {})
            
            logger.info(f"Backtest completed: {result.total_return:+.2f}% return")
            
            return {
                'total_return': result.total_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'win_rate': result.win_rate,
                'total_trades': result.total_trades,
                'avg_trade_return': result.avg_trade_return,
                'best_trade': result.best_trade,
                'worst_trade': result.worst_trade,
                'total_fees': result.total_fees,
                'final_balance': result.final_balance,
                'initial_balance': self.initial_balance
            }
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return self._empty_result()
    
    async def _load_historical_data(self, days: int) -> List[Dict]:
        """Load or generate historical market data"""
        try:
            # For now, generate mock historical data
            # In a real implementation, this would load from saved market data
            
            historical_data = []
            current_time = datetime.now() - timedelta(days=days)
            end_time = datetime.now()
            
            # Generate mock data every hour
            while current_time < end_time:
                # Simulate random tokens with various characteristics
                for i in range(np.random.randint(5, 15)):  # 5-15 tokens per hour
                    token_data = self._generate_mock_token_data(current_time)
                    historical_data.append(token_data)
                
                current_time += timedelta(hours=1)
            
            logger.info(f"Generated {len(historical_data)} historical data points")
            return historical_data
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            return []
    
    def _generate_mock_token_data(self, timestamp: datetime) -> Dict:
        """Generate mock token data for backtesting"""
        # Random token characteristics
        base_price = np.random.uniform(0.0001, 10.0)
        volume = np.random.uniform(1000, 1000000)
        
        # Price movements (some tokens moon, most don't)
        moon_probability = 0.05  # 5% chance of significant gains
        rug_probability = 0.10   # 10% chance of significant loss
        
        if np.random.random() < moon_probability:
            price_change_24h = np.random.uniform(100, 1000)  # 100-1000% gain
            future_performance = np.random.uniform(50, 500)  # Additional gains
        elif np.random.random() < rug_probability:
            price_change_24h = np.random.uniform(-95, -50)  # Major loss
            future_performance = np.random.uniform(-90, -20)  # Further decline
        else:
            price_change_24h = np.random.uniform(-50, 50)  # Normal volatility
            future_performance = np.random.uniform(-30, 30)  # Normal movement
        
        return {
            'timestamp': timestamp,
            'address': f"token_{np.random.randint(100000, 999999)}",
            'symbol': f"MOCK{np.random.randint(100, 999)}",
            'name': f"Mock Token {np.random.randint(100, 999)}",
            'price_usd': base_price,
            'volume_24h': volume,
            'volume_1h': volume / 24,
            'price_change_24h': price_change_24h,
            'price_change_1h': np.random.uniform(-20, 20),
            'liquidity_usd': np.random.uniform(5000, 500000),
            'txns_24h': np.random.randint(50, 5000),
            'market_cap': base_price * np.random.uniform(1000000, 100000000),
            'holder_count': np.random.randint(100, 10000),
            'risk_score': np.random.uniform(1, 10),
            'confidence_score': np.random.uniform(1, 10),
            'holder_concentration': np.random.uniform(20, 90),
            'top_10_percentage': np.random.uniform(30, 95),
            'social_sentiment_score': np.random.uniform(1, 10),
            'community_activity_score': np.random.uniform(1, 10),
            # Future performance for backtesting (unknown in real trading)
            '_future_performance': future_performance,
            '_will_moon': price_change_24h > 100,
            '_will_rug': price_change_24h < -80
        }
    
    async def _simulate_trading(self, historical_data: List[Dict], strategy_params: Dict) -> BacktestResult:
        """Simulate trading strategy on historical data"""
        balance = self.initial_balance
        positions = {}
        trades = []
        daily_returns = []
        portfolio_values = []
        
        current_day = None
        daily_start_balance = balance
        
        # Import AI trader for decision making
        from .ai_trader import AITrader
        ai_trader = AITrader()
        
        for data_point in historical_data:
            try:
                timestamp = data_point['timestamp']
                
                # Track daily performance
                day = timestamp.date()
                if day != current_day:
                    if current_day is not None:
                        daily_return = (balance - daily_start_balance) / daily_start_balance
                        daily_returns.append(daily_return)
                    current_day = day
                    daily_start_balance = balance
                
                # Skip if no balance
                if balance <= 0.01:  # Minimum 0.01 SOL
                    continue
                
                # Get trading decision from AI
                decision = await ai_trader.should_trade(data_point)
                
                if decision['should_trade'] and balance > 0.1:  # Minimum trade size
                    # Execute buy trade
                    trade_amount = min(decision['amount'] * balance, balance * 0.9)  # Max 90% of balance
                    
                    if trade_amount >= 0.01:  # Minimum trade size
                        # Calculate tokens received (with fees and slippage)
                        effective_price = data_point['price_usd'] * (1 + self.slippage)
                        fee = trade_amount * self.trading_fee
                        net_amount = trade_amount - fee
                        tokens_received = net_amount / effective_price if effective_price > 0 else 0
                        
                        if tokens_received > 0:
                            # Record trade
                            trade = BacktestTrade(
                                timestamp=timestamp,
                                symbol=data_point['symbol'],
                                action='buy',
                                price=effective_price,
                                amount_sol=trade_amount,
                                tokens_received=tokens_received,
                                confidence=decision['confidence'],
                                risk_score=decision['risk_score']
                            )
                            trades.append(trade)
                            
                            # Update balance and positions
                            balance -= trade_amount
                            positions[data_point['symbol']] = {
                                'tokens': tokens_received,
                                'entry_price': effective_price,
                                'entry_time': timestamp,
                                'entry_sol': trade_amount
                            }
                
                # Simulate selling positions after some time or based on performance
                positions_to_sell = []
                for symbol, position in positions.items():
                    hold_time = timestamp - position['entry_time']
                    
                    # Sell conditions
                    should_sell = False
                    
                    # Time-based selling (hold for 1-24 hours randomly)
                    max_hold_hours = np.random.randint(1, 25)
                    if hold_time.total_seconds() > max_hold_hours * 3600:
                        should_sell = True
                    
                    # Performance-based selling (if this token appears again)
                    if symbol == data_point['symbol']:
                        future_perf = data_point.get('_future_performance', 0)
                        # Add some randomness to simulate market timing difficulty
                        noise = np.random.uniform(-20, 20)
                        actual_perf = future_perf + noise
                        
                        # Simulate selling at actual performance
                        if should_sell or np.random.random() < 0.1:  # 10% chance to sell
                            positions_to_sell.append((symbol, actual_perf))
                
                # Execute sells
                for symbol, performance in positions_to_sell:
                    if symbol in positions:
                        position = positions[symbol]
                        
                        # Calculate sell value
                        sell_price = position['entry_price'] * (1 + performance / 100)
                        sell_price *= (1 - self.slippage)  # Apply slippage
                        
                        gross_value = position['tokens'] * sell_price
                        fee = gross_value * self.trading_fee
                        net_value = gross_value - fee
                        
                        # Record sell trade
                        sell_trade = BacktestTrade(
                            timestamp=timestamp,
                            symbol=symbol,
                            action='sell',
                            price=sell_price,
                            amount_sol=net_value,
                            tokens_received=0,
                            confidence=0,
                            risk_score=0
                        )
                        trades.append(sell_trade)
                        
                        # Update balance
                        balance += net_value
                        del positions[symbol]
                
                # Record portfolio value
                portfolio_value = balance
                for position in positions.values():
                    # Estimate current position value (would be current market price)
                    estimated_price = position['entry_price']  # Simplified
                    portfolio_value += position['tokens'] * estimated_price
                
                portfolio_values.append(portfolio_value)
                
            except Exception as e:
                logger.warning(f"Error processing data point: {e}")
                continue
        
        # Calculate final metrics
        final_balance = balance
        
        # Add final day return
        if current_day is not None:
            daily_return = (final_balance - daily_start_balance) / daily_start_balance
            daily_returns.append(daily_return)
        
        return self._calculate_metrics(trades, daily_returns, portfolio_values, final_balance)
    
    def _calculate_metrics(self, trades: List[BacktestTrade], daily_returns: List[float], 
                          portfolio_values: List[float], final_balance: float) -> BacktestResult:
        """Calculate backtest performance metrics"""
        try:
            # Basic metrics
            total_return = ((final_balance - self.initial_balance) / self.initial_balance) * 100
            
            # Trade analysis
            buy_trades = [t for t in trades if t.action == 'buy']
            sell_trades = [t for t in trades if t.action == 'sell']
            
            total_trades = len(buy_trades)
            
            # Calculate individual trade returns
            trade_returns = []
            total_fees = 0
            
            # Match buy and sell trades (simplified)
            for sell_trade in sell_trades:
                # Find corresponding buy trade (by symbol and time)
                buy_trade = None
                for bt in buy_trades:
                    if (bt.symbol == sell_trade.symbol and 
                        bt.timestamp < sell_trade.timestamp):
                        buy_trade = bt
                        break
                
                if buy_trade:
                    trade_return = ((sell_trade.amount_sol - buy_trade.amount_sol) / 
                                  buy_trade.amount_sol) * 100
                    trade_returns.append(trade_return)
                    total_fees += buy_trade.amount_sol * self.trading_fee * 2  # Buy + sell fees
            
            # Win rate
            winning_trades = len([r for r in trade_returns if r > 0])
            win_rate = (winning_trades / len(trade_returns)) * 100 if trade_returns else 0
            
            # Average trade return
            avg_trade_return = np.mean(trade_returns) if trade_returns else 0
            
            # Best and worst trades
            best_trade = max(trade_returns) if trade_returns else 0
            worst_trade = min(trade_returns) if trade_returns else 0
            
            # Sharpe ratio (annualized)
            if daily_returns and len(daily_returns) > 1:
                returns_array = np.array(daily_returns)
                avg_daily_return = np.mean(returns_array)
                std_daily_return = np.std(returns_array)
                
                if std_daily_return > 0:
                    sharpe_ratio = (avg_daily_return / std_daily_return) * np.sqrt(365)
                else:
                    sharpe_ratio = 0
            else:
                sharpe_ratio = 0
            
            # Maximum drawdown
            if portfolio_values:
                portfolio_array = np.array(portfolio_values)
                running_max = np.maximum.accumulate(portfolio_array)
                drawdown = (portfolio_array - running_max) / running_max
                max_drawdown = abs(np.min(drawdown)) * 100
            else:
                max_drawdown = 0
            
            return BacktestResult(
                total_return=total_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                total_trades=total_trades,
                avg_trade_return=avg_trade_return,
                best_trade=best_trade,
                worst_trade=worst_trade,
                total_fees=total_fees,
                final_balance=final_balance
            )
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return BacktestResult(0, 0, 0, 0, 0, 0, 0, 0, 0, self.initial_balance)
    
    def _empty_result(self) -> Dict:
        """Return empty backtest result"""
        return {
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'total_trades': 0,
            'avg_trade_return': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
            'total_fees': 0.0,
            'final_balance': self.initial_balance,
            'initial_balance': self.initial_balance
        }
    
    async def run_monte_carlo(self, num_simulations: int = 1000, days: int = 30) -> Dict:
        """Run Monte Carlo simulation with multiple random scenarios"""
        try:
            logger.info(f"Running Monte Carlo simulation with {num_simulations} iterations")
            
            results = []
            
            for i in range(num_simulations):
                if i % 100 == 0:
                    logger.info(f"Monte Carlo progress: {i}/{num_simulations}")
                
                # Run single backtest
                result = await self.run_backtest(days)
                results.append(result['total_return'])
            
            # Calculate statistics
            results_array = np.array(results)
            
            return {
                'simulations': num_simulations,
                'mean_return': np.mean(results_array),
                'std_return': np.std(results_array),
                'min_return': np.min(results_array),
                'max_return': np.max(results_array),
                'percentile_5': np.percentile(results_array, 5),
                'percentile_25': np.percentile(results_array, 25),
                'percentile_75': np.percentile(results_array, 75),
                'percentile_95': np.percentile(results_array, 95),
                'probability_positive': len([r for r in results if r > 0]) / len(results) * 100,
                'probability_loss_over_50': len([r for r in results if r < -50]) / len(results) * 100
            }
            
        except Exception as e:
            logger.error(f"Error in Monte Carlo simulation: {e}")
            return {'error': str(e)}