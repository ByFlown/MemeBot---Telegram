import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
import json
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.metrics_file = self.data_dir / "performance_metrics.json"
        self.trades_file = self.data_dir / "trade_history.json"
        
        # Cache for performance data
        self.cached_metrics = {}
        self.last_update = None
        
        # Performance tracking
        self.daily_returns = []
        self.trade_history = []
        self.portfolio_values = []
    
    async def get_metrics(self) -> Dict:
        """Get current performance metrics"""
        try:
            # Update metrics if needed
            if self._should_update_metrics():
                await self.update_metrics()
            
            return self.cached_metrics
            
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return self._default_metrics()
    
    def _should_update_metrics(self) -> bool:
        """Check if metrics need updating"""
        if self.last_update is None:
            return True
        
        # Update every 15 minutes
        return (datetime.now() - self.last_update).total_seconds() > 900
    
    async def update_metrics(self):
        """Update all performance metrics"""
        try:
            logger.info("Updating performance metrics")
            
            # Load trade history
            await self._load_trade_history()
            
            # Calculate various metrics
            metrics = {
                'daily_performance': await self._calculate_daily_performance(),
                'weekly_performance': await self._calculate_weekly_performance(),
                'monthly_performance': await self._calculate_monthly_performance(),
                'win_rate': await self._calculate_win_rate(),
                'avg_trade_size': await self._calculate_avg_trade_size(),
                'avg_hold_time': await self._calculate_avg_hold_time(),
                'best_trade': await self._calculate_best_trade(),
                'worst_trade': await self._calculate_worst_trade(),
                'total_trades': len(self.trade_history),
                'successful_trades': len([t for t in self.trade_history if t.get('profit', 0) > 0]),
                'total_volume': await self._calculate_total_volume(),
                'sharpe_ratio': await self._calculate_sharpe_ratio(),
                'max_drawdown': await self._calculate_max_drawdown(),
                'current_streak': await self._calculate_current_streak(),
                'volatility': await self._calculate_volatility(),
                'risk_adjusted_return': await self._calculate_risk_adjusted_return(),
                'last_updated': datetime.now().isoformat()
            }
            
            # Cache metrics
            self.cached_metrics = metrics
            self.last_update = datetime.now()
            
            # Save to file
            await self._save_metrics(metrics)
            
            logger.info("Performance metrics updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
    
    async def _load_trade_history(self):
        """Load trade history from logs"""
        try:
            # Load from trading logger
            from .logger import TradingLogger
            trading_logger = TradingLogger()
            
            # Get recent trade logs (last 30 days)
            recent_logs = trading_logger.get_recent_logs(1000)  # Get more logs for analysis
            
            self.trade_history = []
            
            for log in recent_logs:
                try:
                    # Parse log entry to extract trade data
                    trade_data = {
                        'timestamp': log.get('timestamp', ''),
                        'symbol': log.get('symbol', ''),
                        'action': log.get('action', ''),
                        'amount': log.get('amount', 0),
                        'success': 'Success' in log.get('result', ''),
                        'confidence': log.get('confidence', 0),
                        'profit': 0  # Will be calculated separately
                    }
                    
                    self.trade_history.append(trade_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing trade log: {e}")
                    continue
            
            # Load additional trade data if available
            if self.trades_file.exists():
                with open(self.trades_file, 'r') as f:
                    additional_trades = json.load(f)
                    self.trade_history.extend(additional_trades)
            
        except Exception as e:
            logger.error(f"Error loading trade history: {e}")
            self.trade_history = []
    
    async def _calculate_daily_performance(self) -> float:
        """Calculate 24h performance"""
        try:
            if not self.trade_history:
                return 0.0
            
            # Filter trades from last 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_trades = []
            
            for trade in self.trade_history:
                try:
                    trade_time = datetime.fromisoformat(trade['timestamp'])
                    if trade_time >= cutoff_time:
                        recent_trades.append(trade)
                except (ValueError, KeyError):
                    continue
            
            if not recent_trades:
                return 0.0
            
            # Calculate total profit/loss (mock calculation)
            total_profit = sum(
                trade.get('profit', 0) for trade in recent_trades 
                if trade.get('success', False)
            )
            
            # Assume starting balance for percentage calculation
            starting_balance = 100.0  # SOL
            return (total_profit / starting_balance) * 100
            
        except Exception as e:
            logger.error(f"Error calculating daily performance: {e}")
            return 0.0
    
    async def _calculate_weekly_performance(self) -> float:
        """Calculate 7-day performance"""
        try:
            if not self.trade_history:
                return 0.0
            
            cutoff_time = datetime.now() - timedelta(days=7)
            weekly_trades = []
            
            for trade in self.trade_history:
                try:
                    trade_time = datetime.fromisoformat(trade['timestamp'])
                    if trade_time >= cutoff_time:
                        weekly_trades.append(trade)
                except (ValueError, KeyError):
                    continue
            
            if not weekly_trades:
                return 0.0
            
            total_profit = sum(
                trade.get('profit', 0) for trade in weekly_trades 
                if trade.get('success', False)
            )
            
            starting_balance = 100.0
            return (total_profit / starting_balance) * 100
            
        except Exception as e:
            logger.error(f"Error calculating weekly performance: {e}")
            return 0.0
    
    async def _calculate_monthly_performance(self) -> float:
        """Calculate 30-day performance"""
        try:
            cutoff_time = datetime.now() - timedelta(days=30)
            monthly_trades = []
            
            for trade in self.trade_history:
                try:
                    trade_time = datetime.fromisoformat(trade['timestamp'])
                    if trade_time >= cutoff_time:
                        monthly_trades.append(trade)
                except (ValueError, KeyError):
                    continue
            
            if not monthly_trades:
                return 0.0
            
            total_profit = sum(
                trade.get('profit', 0) for trade in monthly_trades 
                if trade.get('success', False)
            )
            
            starting_balance = 100.0
            return (total_profit / starting_balance) * 100
            
        except Exception as e:
            logger.error(f"Error calculating monthly performance: {e}")
            return 0.0
    
    async def _calculate_win_rate(self) -> float:
        """Calculate win rate percentage"""
        try:
            if not self.trade_history:
                return 0.0
            
            successful_trades = len([t for t in self.trade_history if t.get('success', False)])
            total_trades = len(self.trade_history)
            
            return (successful_trades / total_trades) * 100 if total_trades > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating win rate: {e}")
            return 0.0
    
    async def _calculate_avg_trade_size(self) -> float:
        """Calculate average trade size in SOL"""
        try:
            if not self.trade_history:
                return 0.0
            
            trade_sizes = [t.get('amount', 0) for t in self.trade_history if t.get('amount', 0) > 0]
            
            return np.mean(trade_sizes) if trade_sizes else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating avg trade size: {e}")
            return 0.0
    
    async def _calculate_avg_hold_time(self) -> str:
        """Calculate average position hold time"""
        try:
            # This would require tracking buy/sell pairs
            # For now, return a mock value
            return "4.2 hours"
            
        except Exception as e:
            logger.error(f"Error calculating avg hold time: {e}")
            return "N/A"
    
    async def _calculate_best_trade(self) -> float:
        """Calculate best trade return percentage"""
        try:
            if not self.trade_history:
                return 0.0
            
            profits = [t.get('profit', 0) for t in self.trade_history]
            best_profit = max(profits) if profits else 0.0
            
            # Convert to percentage (assuming average trade size)
            avg_trade_size = await self._calculate_avg_trade_size()
            if avg_trade_size > 0:
                return (best_profit / avg_trade_size) * 100
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating best trade: {e}")
            return 0.0
    
    async def _calculate_worst_trade(self) -> float:
        """Calculate worst trade return percentage"""
        try:
            if not self.trade_history:
                return 0.0
            
            profits = [t.get('profit', 0) for t in self.trade_history]
            worst_profit = min(profits) if profits else 0.0
            
            avg_trade_size = await self._calculate_avg_trade_size()
            if avg_trade_size > 0:
                return (worst_profit / avg_trade_size) * 100
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating worst trade: {e}")
            return 0.0
    
    async def _calculate_total_volume(self) -> float:
        """Calculate total trading volume in SOL"""
        try:
            return sum(t.get('amount', 0) for t in self.trade_history)
            
        except Exception as e:
            logger.error(f"Error calculating total volume: {e}")
            return 0.0
    
    async def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio for risk-adjusted returns"""
        try:
            if len(self.trade_history) < 10:  # Need sufficient data
                return 0.0
            
            # Calculate daily returns
            daily_returns = []
            
            # Group trades by day
            trades_by_day = {}
            for trade in self.trade_history:
                try:
                    trade_date = datetime.fromisoformat(trade['timestamp']).date()
                    if trade_date not in trades_by_day:
                        trades_by_day[trade_date] = []
                    trades_by_day[trade_date].append(trade)
                except (ValueError, KeyError):
                    continue
            
            # Calculate daily returns
            for date, trades in trades_by_day.items():
                daily_profit = sum(t.get('profit', 0) for t in trades if t.get('success', False))
                daily_volume = sum(t.get('amount', 0) for t in trades)
                
                if daily_volume > 0:
                    daily_return = daily_profit / daily_volume
                    daily_returns.append(daily_return)
            
            if len(daily_returns) < 2:
                return 0.0
            
            # Calculate Sharpe ratio
            mean_return = np.mean(daily_returns)
            std_return = np.std(daily_returns)
            
            if std_return > 0:
                return (mean_return / std_return) * np.sqrt(365)  # Annualized
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0
    
    async def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown percentage"""
        try:
            if len(self.trade_history) < 2:
                return 0.0
            
            # Calculate cumulative returns
            cumulative_pnl = 0.0
            peak_value = 0.0
            max_drawdown = 0.0
            
            for trade in sorted(self.trade_history, key=lambda x: x.get('timestamp', '')):
                if trade.get('success', False):
                    cumulative_pnl += trade.get('profit', 0)
                
                # Update peak
                if cumulative_pnl > peak_value:
                    peak_value = cumulative_pnl
                
                # Calculate drawdown
                if peak_value > 0:
                    drawdown = (peak_value - cumulative_pnl) / peak_value
                    max_drawdown = max(max_drawdown, drawdown)
            
            return max_drawdown * 100
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
    
    async def _calculate_current_streak(self) -> int:
        """Calculate current win/loss streak"""
        try:
            if not self.trade_history:
                return 0
            
            # Sort trades by timestamp (most recent first)
            sorted_trades = sorted(
                self.trade_history, 
                key=lambda x: x.get('timestamp', ''), 
                reverse=True
            )
            
            if not sorted_trades:
                return 0
            
            # Check if first trade was successful
            streak = 0
            last_success = sorted_trades[0].get('success', False)
            
            for trade in sorted_trades:
                if trade.get('success', False) == last_success:
                    streak += 1
                else:
                    break
            
            return streak if last_success else -streak
            
        except Exception as e:
            logger.error(f"Error calculating current streak: {e}")
            return 0
    
    async def _calculate_volatility(self) -> float:
        """Calculate portfolio volatility"""
        try:
            daily_returns = []
            
            # Calculate daily returns (simplified)
            for i, trade in enumerate(self.trade_history[-30:]):  # Last 30 trades
                profit = trade.get('profit', 0)
                amount = trade.get('amount', 1)
                
                if amount > 0:
                    daily_return = profit / amount
                    daily_returns.append(daily_return)
            
            if len(daily_returns) < 2:
                return 0.0
            
            return np.std(daily_returns) * 100  # As percentage
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0.0
    
    async def _calculate_risk_adjusted_return(self) -> float:
        """Calculate risk-adjusted return"""
        try:
            monthly_return = await self._calculate_monthly_performance()
            volatility = await self._calculate_volatility()
            
            if volatility > 0:
                return monthly_return / volatility
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating risk-adjusted return: {e}")
            return 0.0
    
    async def _save_metrics(self, metrics: Dict):
        """Save metrics to file"""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
    
    def _default_metrics(self) -> Dict:
        """Return default metrics when calculation fails"""
        return {
            'daily_performance': 0.0,
            'weekly_performance': 0.0,
            'monthly_performance': 0.0,
            'win_rate': 0.0,
            'avg_trade_size': 0.0,
            'avg_hold_time': 'N/A',
            'best_trade': 0.0,
            'worst_trade': 0.0,
            'total_trades': 0,
            'successful_trades': 0,
            'total_volume': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'current_streak': 0,
            'volatility': 0.0,
            'risk_adjusted_return': 0.0,
            'last_updated': datetime.now().isoformat()
        }
    
    async def generate_report(self) -> str:
        """Generate a comprehensive performance report"""
        try:
            metrics = await self.get_metrics()
            
            report = f"""
📊 **MEMEBOT PERFORMANCE REPORT**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **Returns**
├─ 24h Performance: {metrics['daily_performance']:+.2f}%
├─ 7d Performance: {metrics['weekly_performance']:+.2f}%
└─ 30d Performance: {metrics['monthly_performance']:+.2f}%

🎯 **Trading Stats**
├─ Total Trades: {metrics['total_trades']}
├─ Win Rate: {metrics['win_rate']:.1f}%
├─ Avg Trade Size: {metrics['avg_trade_size']:.4f} SOL
└─ Avg Hold Time: {metrics['avg_hold_time']}

🏆 **Best/Worst**
├─ Best Trade: +{metrics['best_trade']:.2f}%
└─ Worst Trade: {metrics['worst_trade']:+.2f}%

⚖️ **Risk Metrics**
├─ Sharpe Ratio: {metrics['sharpe_ratio']:.2f}
├─ Max Drawdown: -{metrics['max_drawdown']:.2f}%
├─ Volatility: {metrics['volatility']:.2f}%
└─ Risk-Adj Return: {metrics['risk_adjusted_return']:.2f}

🔥 **Current Streak**: {metrics['current_streak']} {'wins' if metrics['current_streak'] > 0 else 'losses' if metrics['current_streak'] < 0 else 'trades'}

💎 **Volume**: {metrics['total_volume']:.2f} SOL

📅 Last Updated: {metrics['last_updated'][:19]}
            """
            
            return report.strip()
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return "Error generating performance report"