"""
🧠 SELF-LEARNING TRADING BOT
Vollständig autonomes ML-System ohne manuelles Labeling
Lernt durch Beobachtung der tatsächlichen Preisentwicklung
"""

import asyncio
import pandas as pd
import numpy as np
import logging
import json
import pickle
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# ML Libraries
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.linear_model import SGDRegressor
import joblib

from .ai_logger import get_ai_logger

logger = logging.getLogger(__name__)
ml_logger = get_ai_logger('self_learning')

class SelfLearningTrader:
    """
    🤖 Vollständig selbstlernender Trading-Bot
    - Sammelt automatisch Trainingsdaten
    - Generiert Labels durch Preisverfolgung  
    - Trainiert ML-Modelle kontinuierlich
    - Scored neue Tokens ohne Regelwerk
    """
    
    def __init__(self):
        self.data_dir = Path("storage/ml_data")
        self.model_dir = Path("storage/models")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Profit-Based Learning Configuration (no fixed timeframes)
        self.min_trade_amount = 0.01  # Minimum SOL amount per trade
        self.max_position_age_hours = 48  # Maximum holding period before forced exit
        self.min_profit_threshold = 0.02  # Minimum 2% profit to consider successful
        self.stop_loss_threshold = -0.15  # Stop loss at -15%
        
        # Models - Now using regressors for reward-based learning
        self.model = SGDRegressor(random_state=42)  # Start with basic model for immediate predictions
        self.scaler = StandardScaler()
        self.online_model = SGDRegressor(random_state=42)
        self.is_trained = False  # Will become True after first few trades provide training data
        
        # Profit-based learning configuration
        self.trade_confidence_threshold = 0.6  # Minimum confidence to execute trade
        self.profit_scaling_factor = 10.0  # Scale profits for reward calculation
        
        # Active position tracking for profit calculation
        self.active_positions = {}  # {token_address: {entry_data, features, ml_prediction}}
        self.completed_trades = []  # List of completed trades with profits/losses
        self.position_monitor_task = None  # Background task for monitoring positions
        
        # Database for training data
        self.db_path = self.data_dir / "training_data.db"
        self.init_database()
        
        # Price tracking for auto-labeling
        self.price_tracker = {}  # {token_address: {entry_time, entry_price, features}}
        
        # Load existing model if available
        self.load_models()
        
        # Flag for initial data generation
        self._initial_data_generated = False
        
        # Don't start position monitoring in constructor - will be started when needed
    
    def init_database(self):
        """Initialize SQLite database for training data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_data (
                id INTEGER PRIMARY KEY,
                token_address TEXT,
                timestamp DATETIME,
                
                -- Price & Volume Features
                price_usd REAL,
                volume_24h REAL,
                volume_5m REAL,
                liquidity_usd REAL,
                market_cap REAL,
                
                -- Time Features
                age_minutes REAL,
                created_at DATETIME,
                
                -- Change Features
                price_change_24h REAL,
                volume_change_24h REAL,
                
                -- Holder Features
                holder_count INTEGER,
                top_10_percentage REAL,
                whale_wallets INTEGER,
                
                -- Risk Features
                risk_score REAL,
                confidence_score REAL,
                is_honeypot INTEGER,
                liq_locked INTEGER,
                has_social_links INTEGER,
                
                -- Technical Features
                liquidity_score REAL,
                volume_score REAL,
                momentum_score REAL,
                
                -- Market Status Features
                is_boosted INTEGER DEFAULT 0,  -- If token is boosted on DexScreener
                is_trending INTEGER DEFAULT 0, -- If token is trending
                
                -- Profit-based learning data
                ml_confidence REAL,     -- ML confidence score (0-1)
                entry_price REAL,       -- Price when position opened
                exit_price REAL,        -- Price when position closed
                position_size REAL,     -- SOL amount invested
                profit_loss REAL,       -- Actual profit/loss in SOL
                profit_percentage REAL, -- Profit/loss as percentage
                holding_duration_minutes INTEGER, -- How long position was held
                exit_reason TEXT,       -- Why position was closed
                reward_score REAL,      -- Calculated reward based on profit
                entry_timestamp DATETIME,
                exit_timestamp DATETIME,
                
                -- Metadata
                position_closed INTEGER DEFAULT 0,
                trade_executed INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Training database initialized")
    
    def extract_features(self, token_data: Dict) -> Dict:
        """
        🔧 Feature Engineering aus Token-Daten
        Extrahiert alle relevanten Features für ML-Training
        """
        try:
            features = {}
            
            # Basic Price & Volume Features
            features['price_usd'] = float(token_data.get('price_usd', 0))
            features['volume_24h'] = float(token_data.get('volume_24h', 0))
            features['volume_5m'] = float(token_data.get('volume_5m', 0))
            features['liquidity_usd'] = float(token_data.get('liquidity_usd', 0))
            features['market_cap'] = float(token_data.get('market_cap', 0))
            
            # Time Features
            features['age_minutes'] = float(token_data.get('age_hours', 0)) * 60
            
            # Change Features
            features['price_change_24h'] = float(token_data.get('price_change_24h', 0))
            features['volume_change_24h'] = float(token_data.get('volume_change_24h', 0))
            
            # Holder Features
            features['holder_count'] = int(token_data.get('holder_count', 0))
            features['top_10_percentage'] = float(token_data.get('top_10_percentage', 0))
            features['whale_wallets'] = int(token_data.get('whale_wallets', 0))
            
            # Risk Features  
            features['risk_score'] = float(token_data.get('risk_score', 5.0))
            features['confidence_score'] = float(token_data.get('confidence_score', 5.0))
            
            # Scam Detection Features
            features['is_honeypot'] = int(token_data.get('is_honeypot', 0))
            features['liq_locked'] = int(token_data.get('liq_locked', 0))
            features['has_social_links'] = int(bool(token_data.get('website') or token_data.get('twitter')))
            
            # Technical Features
            features['liquidity_score'] = float(token_data.get('liquidity_score', 0))
            features['volume_score'] = float(token_data.get('volume_score', 0))
            
            # Calculate momentum score
            volume_24h = features['volume_24h']
            liquidity = features['liquidity_usd']
            age_hours = features['age_minutes'] / 60
            
            if liquidity > 0 and age_hours > 0:
                features['momentum_score'] = min(10.0, (volume_24h / liquidity) * (24 / age_hours))
            else:
                features['momentum_score'] = 0.0
            
            # Market Status Features
            features['is_boosted'] = int(token_data.get('boosted', False) or token_data.get('boosts', {}).get('active', False))
            features['is_trending'] = int(token_data.get('trending', False) or token_data.get('trendingOn', []) != [])
            
            # Log feature extraction
            ml_logger.analysis(
                "Features extracted for ML training",
                token_address=token_data.get('address', 'unknown'),
                analysis_data={
                    'feature_count': len(features),
                    'volume_24h': features['volume_24h'],
                    'liquidity_usd': features['liquidity_usd'],
                    'risk_score': features['risk_score']
                }
            )
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return {}
    
    async def open_position(self, token_data: Dict, ml_confidence: float, position_size: float = None) -> bool:
        """
        💰 Opens a trading position based on ML prediction
        Core of the new profit-based system
        """
        try:
            token_address = token_data.get('address')
            if not token_address:
                return False
            
            # Extract features
            features = self.extract_features(token_data)
            if not features:
                return False
            
            # Determine position size (default to minimum)
            if position_size is None:
                position_size = self.min_trade_amount
            
            # Store active position
            self.active_positions[token_address] = {
                'entry_time': datetime.now(),
                'entry_price': features['price_usd'],
                'position_size': position_size,
                'ml_confidence': ml_confidence,
                'features': features,
                'token_data': token_data
            }
            
            # Save to database
            self.save_position_entry(token_address, features, ml_confidence, position_size)
            
            # Start position monitoring if not already running
            self.start_position_monitoring()
            
            ml_logger.analysis(
                f"Position opened",
                token_address=token_address,
                analysis_data={
                    'ml_confidence': ml_confidence,
                    'entry_price': features['price_usd'],
                    'position_size': position_size
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error opening position: {e}")
            return False
    
    def start_position_monitoring(self):
        """
        🔍 Starts background task to monitor all active positions
        """
        try:
            # Only start monitoring if there's an event loop running
            loop = asyncio.get_running_loop()
            if self.position_monitor_task is None or self.position_monitor_task.done():
                self.position_monitor_task = asyncio.create_task(self.monitor_positions_continuously())
                logger.info("Started position monitoring task")
        except RuntimeError:
            # No event loop running - monitoring will start when first trade is made
            logger.debug("No event loop running - position monitoring will start when needed")
    
    async def monitor_positions_continuously(self):
        """
        🔄 Continuously monitors all active positions for exit conditions
        """
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if not self.active_positions:
                    continue
                
                positions_to_close = []
                current_time = datetime.now()
                
                for token_address, position in list(self.active_positions.items()):
                    try:
                        # Get current price
                        current_price = await self.get_current_price(token_address)
                        if current_price is None or current_price <= 0:
                            continue
                        
                        entry_price = position['entry_price']
                        profit_pct = (current_price - entry_price) / entry_price
                        position_age = (current_time - position['entry_time']).total_seconds() / 3600
                        
                        # Check exit conditions
                        should_exit, exit_reason = self.should_exit_position(
                            profit_pct, position_age, position['ml_confidence']
                        )
                        
                        if should_exit:
                            positions_to_close.append((token_address, current_price, exit_reason))
                    
                    except Exception as e:
                        logger.error(f"Error monitoring position {token_address}: {e}")
                        continue
                
                # Close positions that meet exit criteria
                for token_address, exit_price, exit_reason in positions_to_close:
                    await self.close_position(token_address, exit_price, exit_reason)
                
            except Exception as e:
                logger.error(f"Error in position monitoring: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def should_exit_position(self, profit_pct: float, position_age_hours: float, ml_confidence: float) -> tuple[bool, str]:
        """
        ⚙️ Determines if a position should be closed based on various factors
        The ML system learns to optimize these exit conditions over time
        """
        # Stop loss condition
        if profit_pct <= self.stop_loss_threshold:
            return True, "stop_loss"
        
        # Maximum holding period
        if position_age_hours >= self.max_position_age_hours:
            return True, "max_age"
        
        # Profit taking based on confidence and current profit
        # High confidence trades can hold longer for bigger gains
        if ml_confidence > 0.8 and profit_pct > 0.15:  # 15%+ profit with high confidence
            return True, "profit_target_high_confidence"
        elif ml_confidence > 0.6 and profit_pct > 0.10:  # 10%+ profit with medium confidence
            return True, "profit_target_medium_confidence"
        elif ml_confidence <= 0.6 and profit_pct > 0.05:  # 5%+ profit with low confidence
            return True, "profit_target_low_confidence"
        
        # Time-based exit for low confidence trades
        if ml_confidence < 0.7 and position_age_hours > 4 and profit_pct > 0:
            return True, "time_exit_low_confidence"
        
        return False, ""
    
    async def close_position(self, token_address: str, exit_price: float, exit_reason: str):
        """
        💰 Closes a position and calculates profit-based reward
        CORE FEATURE: This is where the system learns from actual trading profits!
        """
        try:
            if token_address not in self.active_positions:
                return
            
            position = self.active_positions[token_address]
            entry_price = position['entry_price']
            position_size = position['position_size']
            ml_confidence = position['ml_confidence']
            entry_time = position['entry_time']
            
            # Calculate profit/loss
            profit_pct = (exit_price - entry_price) / entry_price
            profit_sol = position_size * profit_pct
            holding_duration = (datetime.now() - entry_time).total_seconds() / 60  # minutes
            
            # Calculate reward based on actual profit
            reward = self.calculate_profit_reward(profit_pct, profit_sol, holding_duration, ml_confidence, exit_reason)
            
            # Update database with trade results
            self.update_position_with_results(
                token_address, exit_price, profit_pct, profit_sol, 
                holding_duration, exit_reason, reward
            )
            
            # Store in completed trades for statistics
            self.completed_trades.append({
                'token_address': token_address[:8] + "...",
                'entry_price': entry_price,
                'exit_price': exit_price,
                'profit_pct': profit_pct,
                'profit_sol': profit_sol,
                'ml_confidence': ml_confidence,
                'holding_duration': holding_duration,
                'exit_reason': exit_reason,
                'reward': reward,
                'timestamp': datetime.now()
            })
            
            # Keep only last 1000 trades in memory
            if len(self.completed_trades) > 1000:
                self.completed_trades = self.completed_trades[-1000:]
            
            # Remove from active positions
            del self.active_positions[token_address]
            
            # Log trade completion
            ml_logger.learning(
                f"Position closed: {exit_reason}",
                learning_data={
                    'token': token_address[:8] + "...",
                    'profit_pct': profit_pct * 100,
                    'profit_sol': profit_sol,
                    'ml_confidence': ml_confidence,
                    'holding_duration_min': holding_duration,
                    'exit_reason': exit_reason
                },
                reward=reward
            )
            
            # Learn from this trade (online learning)
            await self.update_model_with_profit(position['features'], profit_pct, reward)
            
            # Trigger model retraining if enough new data
            await self.check_retrain_trigger()
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
    
    async def get_current_price(self, token_address: str) -> Optional[float]:
        """
        💰 Holt aktuellen Preis von DexScreener für Labeling
        """
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        pairs = data.get('pairs', [])
                        
                        if pairs:
                            # Get price from first pair
                            pair = pairs[0]
                            price_str = pair.get('priceUsd', '0')
                            return float(price_str) if price_str else 0.0
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting current price for {token_address}: {e}")
            return None
    
    def calculate_profit_reward(self, profit_pct: float, profit_sol: float, holding_duration: float, 
                               ml_confidence: float, exit_reason: str) -> float:
        """
        🏆 Calculates reward score based on actual trading profit
        Higher rewards for profitable trades, scaled by confidence and efficiency
        """
        try:
            # Base reward from profit percentage (main component)
            base_reward = profit_pct * self.profit_scaling_factor
            
            # Confidence multiplier - reward confident successful trades more
            if profit_pct > 0:
                confidence_multiplier = 1.0 + (ml_confidence - 0.5)  # 0.5-1.5x multiplier
            else:
                confidence_multiplier = 1.0 - (ml_confidence - 0.5)  # Penalize confident losses more
            
            # Time efficiency bonus - reward faster profitable trades
            time_bonus = 0.0
            if profit_pct > 0:
                # Bonus for making profit quickly (inversely proportional to time)
                hours = holding_duration / 60
                if hours > 0:
                    time_bonus = min(0.3, 1.0 / hours)  # Max 30% bonus
            
            # Exit reason modifiers
            exit_modifiers = {
                'profit_target_high_confidence': 0.2,    # Bonus for systematic profit taking
                'profit_target_medium_confidence': 0.1,
                'profit_target_low_confidence': 0.05,
                'stop_loss': -0.1,                       # Small penalty for stop losses
                'max_age': -0.05,                        # Small penalty for holding too long
                'time_exit_low_confidence': 0.0          # Neutral for time-based exits
            }
            
            exit_modifier = exit_modifiers.get(exit_reason, 0.0)
            
            # Calculate final reward
            total_reward = (base_reward * confidence_multiplier) + time_bonus + exit_modifier
            
            # Clamp reward between -2.0 and 2.0 to allow for strong signals
            return max(-2.0, min(2.0, total_reward))
            
        except Exception as e:
            logger.error(f"Error calculating profit reward: {e}")
            return 0.0
    
    async def update_model_with_profit(self, features: Dict, profit_pct: float, reward: float):
        """
        🧠 Updates the online learning model with profit-based feedback
        """
        try:
            # For unsupervised learning, we initialize the model with the first training example
            
            # Prepare feature vector
            feature_columns = [
                'price_usd', 'volume_24h', 'volume_5m', 'liquidity_usd', 'market_cap',
                'age_minutes', 'price_change_24h', 'volume_change_24h',
                'holder_count', 'top_10_percentage', 'whale_wallets',
                'risk_score', 'confidence_score', 'is_honeypot', 'liq_locked', 
                'has_social_links', 'liquidity_score', 'volume_score', 'momentum_score',
                'is_boosted', 'is_trending'
            ]
            
            feature_data = {col: [features.get(col, 0)] for col in feature_columns}
            feature_df = pd.DataFrame(feature_data)
            feature_vector_scaled = self.scaler.transform(feature_df)
            
            # Use profit percentage as target for online learning
            # Weight the learning by reward magnitude (profitable trades get more weight)
            sample_weight = max(0.1, abs(reward))  # Minimum weight of 0.1
            
            # Update online model (for continuous learning)
            self.online_model.partial_fit(
                feature_vector_scaled, 
                [profit_pct],
                sample_weight=[sample_weight]
            )
            
            # Also update main model for predictions
            self.model.partial_fit(
                feature_vector_scaled,
                [profit_pct],
                sample_weight=[sample_weight]
            )
            
            # Mark as trained after first example
            if not self.is_trained:
                self.is_trained = True
                logger.info("🎯 ML model is now trained and ready for predictions!")
            
            logger.debug(f"Both models updated with profit {profit_pct:.3f} and reward {reward:.3f}")
            
        except Exception as e:
            logger.error(f"Error updating model with profit: {e}")
    
    def save_position_entry(self, token_address: str, features: Dict, ml_confidence: float, position_size: float):
        """
        💾 Saves position entry to database for profit-based learning
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO training_data (
                    token_address, timestamp,
                    price_usd, volume_24h, volume_5m, liquidity_usd, market_cap,
                    age_minutes, price_change_24h, volume_change_24h,
                    holder_count, top_10_percentage, whale_wallets,
                    risk_score, confidence_score, is_honeypot, liq_locked, has_social_links,
                    liquidity_score, volume_score, momentum_score, is_boosted, is_trending,
                    ml_confidence, entry_price, position_size, entry_timestamp, position_closed, trade_executed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                token_address, datetime.now(),
                features.get('price_usd', 0), features.get('volume_24h', 0), features.get('volume_5m', 0),
                features.get('liquidity_usd', 0), features.get('market_cap', 0),
                features.get('age_minutes', 0), features.get('price_change_24h', 0), features.get('volume_change_24h', 0),
                features.get('holder_count', 0), features.get('top_10_percentage', 0), features.get('whale_wallets', 0),
                features.get('risk_score', 5.0), features.get('confidence_score', 5.0),
                features.get('is_honeypot', 0), features.get('liq_locked', 0), features.get('has_social_links', 0),
                features.get('liquidity_score', 0), features.get('volume_score', 0), features.get('momentum_score', 0),
                features.get('is_boosted', 0), features.get('is_trending', 0),
                ml_confidence, features.get('price_usd', 0), position_size, datetime.now(), 0, 1
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving position entry: {e}")
    
    def update_position_with_results(self, token_address: str, exit_price: float, profit_pct: float, 
                                   profit_sol: float, holding_duration: float, exit_reason: str, reward: float):
        """
        🏆 Updates position with trading results and profit-based reward
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE training_data 
                SET exit_price = ?, profit_loss = ?, profit_percentage = ?, 
                    holding_duration_minutes = ?, exit_reason = ?, reward_score = ?, 
                    exit_timestamp = ?, position_closed = 1
                WHERE token_address = ? AND position_closed = 0
            """, (exit_price, profit_sol, profit_pct, holding_duration, exit_reason, reward, datetime.now(), token_address))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating position with results: {e}")
    
    async def check_retrain_trigger(self):
        """
        🔄 Checks if model should be retrained based on completed trades
        """
        try:
            completed_count = self.get_completed_trades_count()
            
            # Retrain every 25 new completed trades (more frequent due to profit importance)
            if completed_count > 0 and completed_count % 25 == 0:
                logger.info(f"Triggering model retraining with {completed_count} completed trades")
                await self.train_model()
            
        except Exception as e:
            logger.error(f"Error checking retrain trigger: {e}")
    
    def get_completed_trades_count(self) -> int:
        """
        📊 Number of completed trades with profit data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM training_data WHERE position_closed = 1")
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
            
        except Exception as e:
            logger.error(f"Error getting completed trades count: {e}")
            return 0
    
    async def train_model(self, use_initial_split=False):
        """
        🧠 Trainiert ML-Modell mit gesammelten Daten
        KERN-FUNKTION: Hier lernt das System!
        """
        try:
            # Load training data
            df = self.load_training_data()
            
            if df.empty or len(df) < 10:
                logger.info("Not enough training data for model training")
                return
            
            # Prepare features and labels
            feature_columns = [
                'price_usd', 'volume_24h', 'volume_5m', 'liquidity_usd', 'market_cap',
                'age_minutes', 'price_change_24h', 'volume_change_24h',
                'holder_count', 'top_10_percentage', 'whale_wallets',
                'risk_score', 'confidence_score', 'is_honeypot', 'liq_locked', 
                'has_social_links', 'liquidity_score', 'volume_score', 'momentum_score'
            ]
            
            X = df[feature_columns].fillna(0)
            y = df['label']
            
            if len(X) < 10:
                logger.info("Not enough samples for training")
                return
            
            # Scale features (maintain feature names for consistency)
            X_scaled = self.scaler.fit_transform(X)
            
            # Split data (80/20 for initial training, 0.2 for regular retraining)
            test_size = 0.2 if use_initial_split else 0.2
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=test_size, random_state=42, stratify=y if len(np.unique(y)) > 1 else None
            )
            
            # Train multiple models and choose best
            models = {
                'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
                'gradient_boosting': GradientBoostingClassifier(random_state=42)
            }
            
            best_model = None
            best_score = 0
            best_name = ""
            best_test_results = {}
            
            for name, model in models.items():
                try:
                    model.fit(X_train, y_train)
                    score = model.score(X_test, y_test)
                    
                    if score > best_score:
                        best_score = score
                        best_model = model
                        best_name = name
                        
                        # Calculate detailed test results for the best model
                        y_pred = model.predict(X_test)
                        from sklearn.metrics import precision_score, recall_score, f1_score
                        
                        best_test_results = {
                            'accuracy': score,
                            'precision': precision_score(y_test, y_pred, average='weighted', zero_division=0),
                            'recall': recall_score(y_test, y_pred, average='weighted', zero_division=0),
                            'f1': f1_score(y_test, y_pred, average='weighted', zero_division=0),
                            'training_samples': len(X_train),
                            'test_samples': len(X_test),
                            'label_distribution': dict(y.value_counts())
                        }
                        
                except Exception as e:
                    logger.warning(f"Error training {name}: {e}")
                    continue
            
            if best_model is None:
                logger.error("No model could be trained successfully")
                return best_test_results
            
            # Update main model
            old_score = self.get_model_performance() if self.is_trained else 0
            self.model = best_model
            self.is_trained = True
            
            # Train online learning model for live updates
            try:
                self.online_model.partial_fit(X_train, y_train, classes=np.unique(y))
            except Exception as e:
                logger.warning(f"Error training online model: {e}")
            
            # Save models
            self.save_models()
            
            # Log training results
            training_log_msg = (
                f"🧠 **ML Model Training Results**\n"
                f"Model Type: {best_name}\n"
                f"Training Samples: {len(X_train)} (80%)\n"
                f"Test Samples: {len(X_test)} (20%)\n"
                f"Accuracy: {best_test_results['accuracy']:.3f}\n"
                f"Precision: {best_test_results['precision']:.3f}\n"
                f"Recall: {best_test_results['recall']:.3f}\n"
                f"F1-Score: {best_test_results['f1']:.3f}\n"
                f"Label Distribution: {best_test_results['label_distribution']}"
            )
            
            logger.info(training_log_msg)
            print(training_log_msg)  # Also print to console
            
            ml_logger.model_update(
                model_name=f"SelfLearningTrader_{best_name}",
                update_type="full_retrain" if use_initial_split else "incremental_retrain",
                performance_before=old_score,
                performance_after=best_score,
                update_details=best_test_results
            )
            
            return best_test_results
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            ml_logger.error(
                "Model training failed",
                error_details={'error': str(e)},
                recovery_action="Continuing with existing model if available"
            )
            return {}
    
    def load_training_data(self) -> pd.DataFrame:
        """
        📊 Lädt Training-Daten aus Datenbank
        """
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM training_data WHERE position_closed = 1", conn)
            conn.close()
            return df
            
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return pd.DataFrame()
    
    async def train_model(self, use_initial_split=False):
        """
        🧠 Trains ML model with profit-based data from completed trades
        CORE FUNCTION: This is where the system learns from trading profits!
        """
        try:
            # Load training data
            df = self.load_training_data()
            
            if df.empty or len(df) < 10:
                logger.info("Not enough trading data for model training")
                return
            
            # Prepare features and targets for profit-based regression
            feature_columns = [
                'price_usd', 'volume_24h', 'volume_5m', 'liquidity_usd', 'market_cap',
                'age_minutes', 'price_change_24h', 'volume_change_24h',
                'holder_count', 'top_10_percentage', 'whale_wallets',
                'risk_score', 'confidence_score', 'is_honeypot', 'liq_locked', 
                'has_social_links', 'liquidity_score', 'volume_score', 'momentum_score',
                'is_boosted', 'is_trending'
            ]
            
            X = df[feature_columns].fillna(0)
            y = df['profit_percentage'].fillna(0)  # Use actual profit percentages as targets
            sample_weights = df['reward_score'].fillna(0.1).abs() + 0.1  # Weight by reward
            
            if len(X) < 10:
                logger.info("Not enough samples for training")
                return
            
            # Scale features (maintain feature names for consistency)
            X_scaled = self.scaler.fit_transform(X)
            
            # Split data (80/20 for initial training, 0.2 for regular retraining)
            test_size = 0.2
            X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(
                X_scaled, y, sample_weights, test_size=test_size, random_state=42
            )
            
            # Train multiple regression models and choose best
            models = {
                'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
                'gradient_boosting': GradientBoostingRegressor(random_state=42, learning_rate=0.1, max_depth=6)
            }
            
            best_model = None
            best_score = float('-inf')  # Use negative infinity for R²
            best_name = ""
            best_test_results = {}
            
            for name, model in models.items():
                try:
                    # Fit model with sample weights
                    model.fit(X_train, y_train, sample_weight=w_train)
                    
                    # Score using R² for regression
                    score = model.score(X_test, y_test, sample_weight=w_test)
                    
                    if score > best_score:
                        best_score = score
                        best_model = model
                        best_name = name
                        
                        # Calculate detailed test results for the best model
                        y_pred = model.predict(X_test)
                        
                        best_test_results = {
                            'r2_score': score,
                            'mse': mean_squared_error(y_test, y_pred, sample_weight=w_test),
                            'mae': mean_absolute_error(y_test, y_pred, sample_weight=w_test),
                            'training_samples': len(X_train),
                            'test_samples': len(X_test),
                            'mean_profit_pct': y.mean(),
                            'std_profit_pct': y.std()
                        }
                        
                except Exception as e:
                    logger.warning(f"Error training {name}: {e}")
                    continue
            
            if best_model is None:
                logger.error("No model could be trained successfully")
                return best_test_results
            
            # Update main model
            old_performance = self.get_model_performance() if self.is_trained else 0
            self.model = best_model
            self.is_trained = True
            
            # Train online learning model for live updates (regression)
            try:
                self.online_model.partial_fit(X_train, y_train, sample_weight=w_train)
            except Exception as e:
                logger.warning(f"Error training online model: {e}")
            
            # Save models
            self.save_models()
            
            # Log training results
            training_log_msg = (
                f"🧠 **Profit-Based ML Training Results**\\n"
                f"Model Type: {best_name}\\n"
                f"Training Samples: {len(X_train)} (80%)\\n"
                f"Test Samples: {len(X_test)} (20%)\\n"
                f"R² Score: {best_test_results['r2_score']:.3f}\\n"
                f"MSE: {best_test_results['mse']:.4f}\\n"
                f"MAE: {best_test_results['mae']:.4f}\\n"
                f"Mean Profit: {best_test_results['mean_profit_pct']:.2%}\\n"
                f"Profit Std: {best_test_results['std_profit_pct']:.2%}"
            )
            
            logger.info(training_log_msg)
            print(training_log_msg)  # Also print to console
            
            ml_logger.model_update(
                model_name=f"ProfitBasedTrader_{best_name}",
                update_type="full_retrain" if use_initial_split else "incremental_retrain",
                performance_before=old_performance,
                performance_after=best_score,
                update_details=best_test_results
            )
            
            return best_test_results
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            ml_logger.error(
                "Model training failed",
                error_details={'error': str(e)},
                recovery_action="Continuing with existing model if available"
            )
            return {}
    
    def get_model_performance(self) -> float:
        """
        📈 Berechnet aktuelle Modell-Performance
        """
        try:
            if not self.is_trained:
                return 0.0
            
            df = self.load_training_data()
            if df.empty:
                return 0.0
            
            # Recent performance (last 100 samples)
            recent_df = df.tail(100)
            good_trades = len(recent_df[recent_df['label'] == 'good'])
            total_trades = len(recent_df)
            
            return good_trades / total_trades if total_trades > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating model performance: {e}")
            return 0.0
    
    async def evaluate_trade_opportunity(self, token_data: Dict) -> Dict:
        """
        🎯 Evaluates a token for trading opportunity using profit-based ML model
        MAIN FUNCTION: This is where the system makes autonomous trading decisions!
        """
        try:
            # For fully unsupervised learning, we don't need historical data
            # The model starts making predictions immediately and learns from actual results
            
            # Extract features
            features = self.extract_features(token_data)
            if not features:
                return {
                    'should_trade': False,
                    'confidence': 0.0,
                    'probabilities': {},
                    'reason': 'Could not extract features'
                }
            
            # Prepare feature vector as DataFrame to preserve feature names
            feature_columns = [
                'price_usd', 'volume_24h', 'volume_5m', 'liquidity_usd', 'market_cap',
                'age_minutes', 'price_change_24h', 'volume_change_24h',
                'holder_count', 'top_10_percentage', 'whale_wallets',
                'risk_score', 'confidence_score', 'is_honeypot', 'liq_locked', 
                'has_social_links', 'liquidity_score', 'volume_score', 'momentum_score',
                'is_boosted', 'is_trending'
            ]
            
            # Create DataFrame with feature names to avoid sklearn warning
            feature_data = {col: [features.get(col, 0)] for col in feature_columns}
            feature_df = pd.DataFrame(feature_data)
            
            # For unsupervised learning, we need to handle the case where scaler isn't fitted yet
            if not self.is_trained:
                # For first predictions, fit scaler with this data point and make random prediction
                self.scaler.fit(feature_df)
                feature_vector_scaled = self.scaler.transform(feature_df)
                
                # Make initial random prediction (between -0.2 to +0.3 expected profit)
                import random
                expected_profit = random.uniform(-0.2, 0.3)
                confidence = random.uniform(0.1, 0.9)
                
                should_trade = confidence >= self.trade_confidence_threshold and expected_profit > 0
                
                result = {
                    'should_trade': should_trade,
                    'confidence': confidence,
                    'expected_profit': expected_profit,
                    'reason': f"Initial prediction: {expected_profit:.1%} expected profit (confidence: {confidence:.1%})"
                }
            else:
                # Use trained model for prediction
                feature_vector_scaled = self.scaler.transform(feature_df)
                
                # Predict expected profit using the trained regressor
                expected_profit = self.model.predict(feature_vector_scaled)[0]
                
                # Calculate confidence based on recent model performance
                confidence = self._calculate_prediction_confidence()
                
                # Trading decision based on expected profit and confidence
                should_trade = (confidence >= self.trade_confidence_threshold and 
                              expected_profit > self.min_profit_threshold)
                
                result = {
                    'should_trade': should_trade,
                    'confidence': confidence,
                    'expected_profit': expected_profit,
                    'reason': f"ML prediction: {expected_profit:.1%} expected profit (confidence: {confidence:.1%})"
                }
            
            # Log prediction
            ml_logger.prediction(
                f"Token scored: {'TRADE' if should_trade else 'SKIP'}",
                predicted_value=result['expected_profit'],
                prediction_horizon="dynamic",
                model_info={
                    'model_type': type(self.model).__name__,
                    'expected_profit': f"{result['expected_profit']:.3f}",
                    'confidence': f"{result['confidence']:.3f}",
                    'is_trained': self.is_trained
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error predicting token score: {e}")
            return {
                'should_trade': False,
                'confidence': 0.0,
                'expected_profit': 0.0,
                'reason': f'Prediction error: {e}'
            }
    
    def _calculate_prediction_confidence(self) -> float:
        """
        Calculate prediction confidence based on recent model performance
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent completed trades (last 20 trades or 7 days)
            cursor.execute("""
                SELECT profit_percentage, reward_score, ml_confidence
                FROM training_data 
                WHERE position_closed = 1 
                  AND exit_timestamp >= datetime('now', '-7 days')
                ORDER BY exit_timestamp DESC 
                LIMIT 20
            """)
            
            recent_trades = cursor.fetchall()
            conn.close()
            
            if len(recent_trades) < 3:
                # Not enough data, return moderate confidence
                return 0.5
            
            # Calculate confidence based on recent performance
            total_trades = len(recent_trades)
            profitable_trades = sum(1 for profit, reward, conf in recent_trades if profit > 0)
            avg_reward = sum(reward for profit, reward, conf in recent_trades) / total_trades
            
            # Base confidence on win rate and reward score
            win_rate = profitable_trades / total_trades
            reward_factor = max(0, min(1, (avg_reward + 1) / 2))  # Normalize rewards to 0-1
            
            # Combine metrics
            confidence = (win_rate * 0.7) + (reward_factor * 0.3)
            
            return max(0.1, min(0.9, confidence))  # Clamp between 0.1 and 0.9
            
        except Exception as e:
            logger.error(f"Error calculating prediction confidence: {e}")
            return 0.5  # Default moderate confidence
    
    def save_models(self):
        """
        💾 Speichert trainierte Modelle
        """
        try:
            if self.model:
                joblib.dump(self.model, self.model_dir / "main_model.pkl")
                joblib.dump(self.scaler, self.model_dir / "scaler.pkl")
                
            if hasattr(self.online_model, 'coef_'):
                joblib.dump(self.online_model, self.model_dir / "online_model.pkl")
            
            # Save metadata
            metadata = {
                'is_trained': self.is_trained,
                'learning_window_minutes': self.learning_window_minutes,
                'profit_threshold_good': self.profit_threshold_good,
                'loss_threshold_bad': self.loss_threshold_bad,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.model_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def load_models(self):
        """
        📂 Lädt gespeicherte Modelle
        """
        try:
            main_model_path = self.model_dir / "main_model.pkl"
            scaler_path = self.model_dir / "scaler.pkl"
            metadata_path = self.model_dir / "metadata.json"
            
            if main_model_path.exists() and scaler_path.exists():
                self.model = joblib.load(main_model_path)
                self.scaler = joblib.load(scaler_path)
                self.is_trained = True
                
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        self.learning_window_minutes = metadata.get('learning_window_minutes', 20)
                        self.profit_threshold_good = metadata.get('profit_threshold_good', 0.10)
                        self.loss_threshold_bad = metadata.get('loss_threshold_bad', -0.10)
                
                logger.info("Models loaded successfully")
                
                # Try to load online model
                online_model_path = self.model_dir / "online_model.pkl"
                if online_model_path.exists():
                    self.online_model = joblib.load(online_model_path)
                
            else:
                logger.info("No saved models found, starting fresh")
                
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            self.is_trained = False
    
    def get_training_stats(self) -> Dict:
        """
        📊 Statistics about the profit-based trading system
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Basic trading stats
            cursor.execute("SELECT COUNT(*) FROM training_data")
            total_positions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM training_data WHERE position_closed = 1")
            completed_trades = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM training_data WHERE position_closed = 0")
            active_positions = cursor.fetchone()[0]
            
            # Profit statistics
            cursor.execute("""
                SELECT AVG(profit_percentage), MIN(profit_percentage), MAX(profit_percentage),
                       SUM(profit_loss), AVG(reward_score)
                FROM training_data 
                WHERE position_closed = 1 AND profit_percentage IS NOT NULL
            """)
            profit_stats = cursor.fetchone()
            avg_profit_pct, min_profit_pct, max_profit_pct, total_profit_sol, avg_reward = (
                profit_stats if profit_stats[0] is not None else (0, 0, 0, 0, 0)
            )
            
            # Trading performance (last 7 days)
            cursor.execute("""
                SELECT AVG(profit_percentage) as avg_profit,
                       COUNT(*) as trade_count,
                       SUM(CASE WHEN profit_percentage > 0 THEN 1 ELSE 0 END) as profitable_trades,
                       AVG(holding_duration_minutes) as avg_duration
                FROM training_data 
                WHERE position_closed = 1 
                AND exit_timestamp > datetime('now', '-7 days')
            """)
            recent_stats = cursor.fetchone()
            recent_avg_profit, recent_trades, profitable_trades, avg_duration = (
                recent_stats if recent_stats[0] is not None else (0, 0, 0, 0)
            )
            
            # Exit reason analysis
            cursor.execute("""
                SELECT exit_reason, COUNT(*) as count
                FROM training_data 
                WHERE position_closed = 1 AND exit_reason IS NOT NULL
                AND exit_timestamp > datetime('now', '-7 days')
                GROUP BY exit_reason
            """)
            exit_reasons = dict(cursor.fetchall())
            
            # Confidence analysis
            cursor.execute("""
                SELECT AVG(ml_confidence) as avg_confidence,
                       AVG(CASE WHEN profit_percentage > 0 THEN ml_confidence ELSE NULL END) as avg_confidence_profitable,
                       AVG(CASE WHEN profit_percentage <= 0 THEN ml_confidence ELSE NULL END) as avg_confidence_losses
                FROM training_data 
                WHERE position_closed = 1 AND ml_confidence IS NOT NULL
                AND exit_timestamp > datetime('now', '-7 days')
            """)
            confidence_stats = cursor.fetchone()
            avg_confidence, avg_confidence_profit, avg_confidence_loss = (
                confidence_stats if confidence_stats[0] is not None else (0, 0, 0)
            )
            
            # Boosted/Trending token performance analysis
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_boosted,
                    AVG(profit_percentage) as avg_profit_boosted,
                    SUM(CASE WHEN profit_percentage > 0 THEN 1 ELSE 0 END) as profitable_boosted
                FROM training_data 
                WHERE position_closed = 1 AND is_boosted = 1
                AND exit_timestamp > datetime('now', '-7 days')
            """)
            boosted_stats = cursor.fetchone()
            total_boosted, avg_profit_boosted, profitable_boosted = (
                boosted_stats if boosted_stats[0] is not None else (0, 0, 0)
            )
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trending,
                    AVG(profit_percentage) as avg_profit_trending,
                    SUM(CASE WHEN profit_percentage > 0 THEN 1 ELSE 0 END) as profitable_trending
                FROM training_data 
                WHERE position_closed = 1 AND is_trending = 1
                AND exit_timestamp > datetime('now', '-7 days')
            """)
            trending_stats = cursor.fetchone()
            total_trending, avg_profit_trending, profitable_trending = (
                trending_stats if trending_stats[0] is not None else (0, 0, 0)
            )
            
            conn.close()
            
            # Calculate win rate
            win_rate = (profitable_trades / recent_trades * 100) if recent_trades > 0 else 0
            
            # Get in-memory trading statistics
            trading_history_stats = {}
            if self.completed_trades:
                recent_trades = self.completed_trades[-25:]  # Last 25 trades
                trading_history_stats = {
                    'recent_trades_count': len(recent_trades),
                    'avg_recent_profit': sum(t['profit_pct'] for t in recent_trades) / len(recent_trades),
                    'avg_recent_reward': sum(t['reward'] for t in recent_trades) / len(recent_trades),
                    'avg_recent_duration': sum(t['holding_duration'] for t in recent_trades) / len(recent_trades)
                }
            
            # Model performance metrics
            model_performance = {}
            if self.is_trained:
                model_performance = {
                    'model_type': type(self.model).__name__ if self.model else 'Unknown',
                    'features_count': 21,  # Updated to include boosted and trending
                    'profit_threshold': self.min_profit_threshold,
                    'confidence_threshold': self.trade_confidence_threshold,
                    'max_position_age_hours': self.max_position_age_hours,
                    'stop_loss_threshold': self.stop_loss_threshold,
                    'online_learning_enabled': hasattr(self.online_model, 'coef_'),
                    'current_performance_score': self.get_model_performance()
                }
            
            return {
                'total_positions': total_positions,
                'completed_trades': completed_trades,
                'active_positions': active_positions,
                'model_trained': self.is_trained,
                
                # Profit statistics (all time)
                'avg_profit_pct': avg_profit_pct,
                'min_profit_pct': min_profit_pct,
                'max_profit_pct': max_profit_pct,
                'total_profit_sol': total_profit_sol,
                'avg_reward_score': avg_reward,
                
                # Performance statistics (last 7 days)
                'recent_avg_profit_pct': recent_avg_profit,
                'recent_trade_count': recent_trades,
                'profitable_trades_7d': profitable_trades,
                'win_rate_pct': win_rate,
                'avg_holding_duration_min': avg_duration,
                
                # Exit analysis
                'exit_reasons': exit_reasons,
                
                # Confidence analysis
                'avg_confidence': avg_confidence,
                'avg_confidence_profitable': avg_confidence_profit,
                'avg_confidence_losses': avg_confidence_loss,
                
                # Boosted/Trending analysis (last 7 days)
                'boosted_trades': total_boosted,
                'boosted_avg_profit': avg_profit_boosted,
                'boosted_profitable': profitable_boosted,
                'boosted_win_rate': (profitable_boosted / total_boosted * 100) if total_boosted > 0 else 0,
                'trending_trades': total_trending,
                'trending_avg_profit': avg_profit_trending,
                'trending_profitable': profitable_trending,
                'trending_win_rate': (profitable_trending / total_trending * 100) if total_trending > 0 else 0,
                
                # In-memory statistics
                'trading_history': trading_history_stats,
                
                # Model details
                'model_performance': model_performance
            }
            
        except Exception as e:
            logger.error(f"Error getting training stats: {e}")
            return {}
    
    async def _generate_initial_training_data(self):
        """
        ⚡ Generiert sofort Trainingsdaten für sofortiges Training mit 80/20 Split
        """
        try:
            if self._initial_data_generated:
                return
            
            logger.info("🔥 Generating immediate training data for instant ML training...")
            ml_logger.analysis(
                "Starting immediate training data generation",
                analysis_data={'reason': 'no_existing_model'}
            )
            
            # Import and use historical data generator
            from .historical_data_generator import HistoricalDataGenerator
            
            generator = HistoricalDataGenerator(self)
            samples_generated = await generator.generate_immediate_training_data(batch_size=300)
            
            self._initial_data_generated = True
            
            if samples_generated > 0:
                logger.info(f"✅ Generated {samples_generated} training samples from real token data")
                
                # Now perform initial 80/20 training if we have enough data
                labeled_count = self.get_labeled_sample_count()
                if labeled_count >= 20:  # Lower threshold since we're using real data only
                    logger.info("🧠 Performing initial 80/20 training with backtesting data...")
                    print("🧠 **Performing Initial ML Training with 80/20 Split**")
                    
                    # Train with 80/20 split for initial model
                    training_results = await self.train_model(use_initial_split=True)
                    
                    if training_results:
                        success_msg = (
                            f"✅ **INITIAL TRAINING COMPLETE** ✅\n"
                            f"📊 Training: {training_results.get('training_samples', 0)} samples (80%)\n"
                            f"🎯 Testing: {training_results.get('test_samples', 0)} samples (20%)\n"
                            f"🎯 Accuracy: {training_results.get('accuracy', 0):.3f}\n"
                            f"🔄 **System now ready for live training and prediction!**"
                        )
                        logger.info(success_msg)
                        print(success_msg)
                    else:
                        logger.warning("⚠️ Initial training completed but no results returned")
                else:
                    logger.info(f"⏳ Only {labeled_count} real samples generated, need 20+ for training. Will continue collecting live data.")
            else:
                logger.warning("⚠️ Could not fetch real token data from DexScreener - will collect data through live trading")
            
        except Exception as e:
            logger.error(f"Error generating initial training data: {e}")
            self._initial_data_generated = True  # Don't retry
    
    
    async def clear_model(self) -> bool:
        """
        🗑️ Clear all ML models and training data for fresh start
        """
        try:
            import os
            
            # Clear models from memory
            self.model = None
            self.scaler = StandardScaler()
            self.online_model = SGDClassifier(random_state=42)
            self.is_trained = False
            self._initial_data_generated = False
            
            # Clear price tracking
            self.price_tracker.clear()
            
            # Delete model files
            model_files = [
                self.model_dir / "main_model.pkl",
                self.model_dir / "scaler.pkl", 
                self.model_dir / "online_model.pkl",
                self.model_dir / "metadata.json"
            ]
            
            for file_path in model_files:
                if file_path.exists():
                    os.remove(file_path)
                    logger.info(f"Deleted model file: {file_path}")
            
            # Clear training database
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM training_data")
                conn.commit()
                conn.close()
                logger.info("Cleared training database")
            except Exception as e:
                logger.warning(f"Error clearing training database: {e}")
            
            logger.info("✅ ML model and training data cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing model: {e}")
            return False
    
    async def close(self):
        """
        🔚 Cleanup resources
        """
        try:
            # Cancel any pending tracking tasks
            for token_address in list(self.price_tracker.keys()):
                del self.price_tracker[token_address]
            
            logger.info("SelfLearningTrader closed")
            
        except Exception as e:
            logger.error(f"Error closing SelfLearningTrader: {e}")