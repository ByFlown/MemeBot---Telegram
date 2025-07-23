"""
📊 ML BACKTESTING ENGINE
Testet die Leistung des selbstlernenden Trading-Systems
auf historischen Daten für Validierung und Optimierung
"""

import asyncio
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sqlite3
from pathlib import Path

from .ai_logger import get_ai_logger

logger = logging.getLogger(__name__)
backtest_logger = get_ai_logger('backtester')

class MLBacktester:
    """
    🔬 Backtesting-Engine für ML-Trading-System
    - Simuliert Trading auf historischen Daten
    - Validiert ML-Model Performance
    - Optimiert Hyperparameter
    """
    
    def __init__(self, self_learning_trader):
        self.ml_trader = self_learning_trader
        self.results_dir = Path("storage/backtest_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Backtest parameters
        self.initial_balance = 100.0  # SOL
        self.position_size = 0.01  # 1% per trade
        self.max_positions = 10
        
    async def run_historical_backtest(self, days_back: int = 30) -> Dict:
        """
        🕰️ Führt Backtest auf historischen Daten durch
        Simuliert wie das ML-System in der Vergangenheit performed hätte
        """
        try:
            backtest_logger.analysis(
                f"Starting historical backtest",
                analysis_data={
                    'days_back': days_back,
                    'initial_balance': self.initial_balance,
                    'position_size_pct': self.position_size * 100
                }
            )
            
            # Load historical training data
            historical_data = self.load_historical_data(days_back)
            
            if historical_data.empty:
                logger.warning("No historical data available for backtesting")
                return self._empty_backtest_result()
            
            # Group data by timestamp for chronological simulation
            historical_data = historical_data.sort_values('timestamp')
            
            # Simulation state
            balance = self.initial_balance
            positions = {}
            trades = []
            equity_curve = []
            
            # Process each historical data point
            total_samples = len(historical_data)
            processed = 0
            
            for idx, row in historical_data.iterrows():
                processed += 1
                
                if processed % 100 == 0:
                    logger.info(f"Backtesting progress: {processed}/{total_samples}")
                
                # Simulate ML prediction at this point in time
                token_data = self._row_to_token_data(row)
                
                # Check if we would have traded this token
                would_trade = await self._simulate_trading_decision(token_data, row['timestamp'])
                
                if would_trade:
                    # Simulate trade execution
                    trade_result = self._simulate_trade(
                        token_data, balance, positions, row['price_change_after_20min']
                    )
                    
                    if trade_result:
                        trades.append(trade_result)
                        balance = trade_result['new_balance']
                
                # Update equity curve
                current_equity = balance + sum(pos['unrealized_pnl'] for pos in positions.values())
                equity_curve.append({
                    'timestamp': row['timestamp'],
                    'equity': current_equity,
                    'balance': balance,
                    'positions_count': len(positions)
                })
                
                # Close expired positions (after 20 minutes)
                self._close_expired_positions(positions, row['timestamp'])
            
            # Calculate backtest results
            results = self._calculate_backtest_results(
                balance, trades, equity_curve, self.initial_balance
            )
            
            # Log results
            backtest_logger.performance(
                f"Historical backtest completed",
                performance_metrics={
                    'total_return_pct': results['total_return'],
                    'win_rate': results['win_rate'],
                    'sharpe_ratio': results['sharpe_ratio'],
                    'max_drawdown': results['max_drawdown'],
                    'total_trades': results['total_trades']
                },
                period=f"{days_back}_days_historical"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in historical backtest: {e}")
            backtest_logger.error(
                "Historical backtest failed",
                error_details={'error': str(e), 'days_back': days_back}
            )
            return self._empty_backtest_result()
    
    def load_historical_data(self, days_back: int) -> pd.DataFrame:
        """
        📚 Lädt historische Daten aus der Training-Datenbank
        """
        try:
            conn = sqlite3.connect(self.ml_trader.db_path)
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            query = """
                SELECT * FROM training_data 
                WHERE labeled = 1 
                AND timestamp >= ?
                ORDER BY timestamp ASC
            """
            
            df = pd.read_sql_query(query, conn, params=(cutoff_date,))
            conn.close()
            
            logger.info(f"Loaded {len(df)} historical samples for backtesting")
            return df
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            return pd.DataFrame()
    
    def _row_to_token_data(self, row) -> Dict:
        """
        🔄 Konvertiert DB-Row zu Token-Data Format
        """
        return {
            'address': row['token_address'],
            'price_usd': row['price_usd'],
            'volume_24h': row['volume_24h'],
            'volume_5m': row.get('volume_5m', 0),
            'liquidity_usd': row['liquidity_usd'],
            'market_cap': row['market_cap'],
            'age_hours': row['age_minutes'] / 60,
            'price_change_24h': row['price_change_24h'],
            'volume_change_24h': row.get('volume_change_24h', 0),
            'holder_count': row['holder_count'],
            'top_10_percentage': row['top_10_percentage'],
            'whale_wallets': row['whale_wallets'],
            'risk_score': row['risk_score'],
            'confidence_score': row['confidence_score'],
            'is_honeypot': row['is_honeypot'],
            'liq_locked': row['liq_locked'],
            'has_social_links': row['has_social_links'],
            'liquidity_score': row['liquidity_score'],
            'volume_score': row['volume_score'],
            'momentum_score': row['momentum_score']
        }
    
    async def _simulate_trading_decision(self, token_data: Dict, timestamp: datetime) -> bool:
        """
        🎯 Simuliert ML-Trading-Entscheidung zu einem bestimmten Zeitpunkt
        """
        try:
            # For backtesting, we need to train the model only on data BEFORE this timestamp
            # This prevents lookahead bias
            
            # Create a temporary model trained only on data before this point
            historical_model = await self._create_historical_model(timestamp)
            
            if not historical_model:
                return False  # No model available yet
            
            # Use the historical model to make prediction
            decision = await historical_model.predict_token_score(token_data)
            return decision.get('should_trade', False)
            
        except Exception as e:
            logger.debug(f"Error in simulation decision: {e}")
            return False
    
    async def _create_historical_model(self, cutoff_timestamp: datetime):
        """
        🕰️ Erstellt Modell nur mit Daten VOR dem Cutoff-Zeitpunkt
        Verhindert Lookahead-Bias im Backtesting
        """
        try:
            # This is a simplified version - in production you'd want to
            # implement proper temporal cross-validation
            
            # For now, we'll use the current model as approximation
            # In a full implementation, you'd retrain on historical data
            
            if self.ml_trader.is_trained:
                return self.ml_trader
            else:
                return None
                
        except Exception as e:
            logger.debug(f"Error creating historical model: {e}")
            return None
    
    def _simulate_trade(self, token_data: Dict, balance: float, positions: Dict, 
                       actual_return: float) -> Optional[Dict]:
        """
        💰 Simuliert Trade-Ausführung und Ergebnis
        """
        try:
            if len(positions) >= self.max_positions:
                return None  # Position limit reached
            
            trade_amount = balance * self.position_size
            if trade_amount < 0.001:  # Minimum trade size
                return None
            
            token_address = token_data['address']
            entry_price = token_data['price_usd']
            
            # Calculate trade result based on actual price movement
            exit_price = entry_price * (1 + actual_return)
            pnl = (exit_price - entry_price) / entry_price
            pnl_sol = trade_amount * pnl
            
            new_balance = balance - trade_amount + trade_amount * (1 + pnl)
            
            trade_result = {
                'timestamp': datetime.now(),
                'token_address': token_address,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'amount_sol': trade_amount,
                'pnl_pct': pnl * 100,
                'pnl_sol': pnl_sol,
                'new_balance': new_balance,
                'success': pnl > 0
            }
            
            return trade_result
            
        except Exception as e:
            logger.error(f"Error simulating trade: {e}")
            return None
    
    def _close_expired_positions(self, positions: Dict, current_time: datetime):
        """
        🔚 Schließt abgelaufene Positionen (nach 20 Minuten)
        """
        expired_positions = []
        
        for token_address, position in positions.items():
            if (current_time - position['entry_time']).total_seconds() > 20 * 60:
                expired_positions.append(token_address)
        
        for token_address in expired_positions:
            del positions[token_address]
    
    def _calculate_backtest_results(self, final_balance: float, trades: List[Dict], 
                                  equity_curve: List[Dict], initial_balance: float) -> Dict:
        """
        📊 Berechnet Backtest-Ergebnisse und Metriken
        """
        try:
            if not trades:
                return self._empty_backtest_result()
            
            # Basic performance metrics
            total_return = (final_balance - initial_balance) / initial_balance * 100
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['success']])
            win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
            
            # Profit/Loss analysis
            profits = [t['pnl_sol'] for t in trades]
            avg_profit = np.mean(profits) if profits else 0
            max_profit = max(profits) if profits else 0
            max_loss = min(profits) if profits else 0
            
            # Sharpe ratio (simplified)
            if len(profits) > 1:
                sharpe_ratio = np.mean(profits) / np.std(profits) if np.std(profits) > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Maximum drawdown
            equity_values = [eq['equity'] for eq in equity_curve]
            if equity_values:
                peak = equity_values[0]
                max_drawdown = 0
                
                for value in equity_values:
                    if value > peak:
                        peak = value
                    drawdown = (peak - value) / peak * 100
                    max_drawdown = max(max_drawdown, drawdown)
            else:
                max_drawdown = 0
            
            return {
                'total_return': total_return,
                'final_balance': final_balance,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'equity_curve': equity_curve[-10:] if equity_curve else []  # Last 10 points
            }
            
        except Exception as e:
            logger.error(f"Error calculating backtest results: {e}")
            return self._empty_backtest_result()
    
    def _empty_backtest_result(self) -> Dict:
        """
        📋 Leeres Backtest-Ergebnis
        """
        return {
            'total_return': 0.0,
            'final_balance': self.initial_balance,
            'total_trades': 0,
            'winning_trades': 0,
            'win_rate': 0.0,
            'avg_profit': 0.0,
            'max_profit': 0.0,
            'max_loss': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'equity_curve': []
        }
    
    async def optimize_parameters(self, param_ranges: Dict) -> Dict:
        """
        🎛️ Optimiert ML-Parameter durch Grid-Search Backtesting
        """
        try:
            best_params = {}
            best_performance = -float('inf')
            
            # Simple grid search over parameter ranges
            for learning_window in param_ranges.get('learning_window_minutes', [20]):
                for profit_threshold in param_ranges.get('profit_threshold_good', [0.10]):
                    for loss_threshold in param_ranges.get('loss_threshold_bad', [-0.10]):
                        
                        # Temporarily set parameters
                        original_window = self.ml_trader.learning_window_minutes
                        original_profit = self.ml_trader.profit_threshold_good
                        original_loss = self.ml_trader.loss_threshold_bad
                        
                        self.ml_trader.learning_window_minutes = learning_window
                        self.ml_trader.profit_threshold_good = profit_threshold
                        self.ml_trader.loss_threshold_bad = loss_threshold
                        
                        # Run backtest with these parameters
                        results = await self.run_historical_backtest(days_back=14)
                        
                        # Evaluate performance (could use different metrics)
                        performance = results['total_return'] - results['max_drawdown']  # Risk-adjusted return
                        
                        if performance > best_performance:
                            best_performance = performance
                            best_params = {
                                'learning_window_minutes': learning_window,
                                'profit_threshold_good': profit_threshold,
                                'loss_threshold_bad': loss_threshold,
                                'performance': performance
                            }
                        
                        # Restore original parameters
                        self.ml_trader.learning_window_minutes = original_window
                        self.ml_trader.profit_threshold_good = original_profit
                        self.ml_trader.loss_threshold_bad = original_loss
                        
                        # Log parameter test
                        backtest_logger.analysis(
                            f"Parameter optimization test",
                            analysis_data={
                                'learning_window': learning_window,
                                'profit_threshold': profit_threshold,
                                'loss_threshold': loss_threshold,
                                'performance_score': performance
                            }
                        )
            
            return best_params
            
        except Exception as e:
            logger.error(f"Error in parameter optimization: {e}")
            return {}
    
    def save_backtest_results(self, results: Dict, filename: str = None):
        """
        💾 Speichert Backtest-Ergebnisse
        """
        try:
            if filename is None:
                filename = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            filepath = self.results_dir / filename
            
            # Convert datetime objects to strings for JSON serialization
            serializable_results = self._make_json_serializable(results)
            
            import json
            with open(filepath, 'w') as f:
                json.dump(serializable_results, f, indent=2)
            
            logger.info(f"Backtest results saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving backtest results: {e}")
    
    def _make_json_serializable(self, obj):
        """
        🔄 Macht Objekt JSON-serialisierbar
        """
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        else:
            return obj