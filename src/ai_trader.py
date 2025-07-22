import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
import json
import os
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import pickle
import asyncio

# Reinforcement Learning components
import gymnasium as gym
from stable_baselines3 import PPO, A2C
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import BaseCallback

logger = logging.getLogger(__name__)

class TradingEnvironment(gym.Env):
    """Custom trading environment for reinforcement learning"""
    
    def __init__(self, historical_data: List[Dict]):
        super().__init__()
        self.historical_data = historical_data
        self.current_step = 0
        self.max_steps = len(historical_data) - 1
        
        # Action space: 0=hold, 1=buy, 2=sell
        self.action_space = gym.spaces.Discrete(3)
        
        # Observation space: price, volume, technical indicators, onchain metrics
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(20,), dtype=np.float32
        )
        
        self.initial_balance = 100.0  # Starting with 100 SOL
        self.balance = self.initial_balance
        self.position = 0.0
        self.position_value = 0.0
        self.total_trades = 0
        self.successful_trades = 0
    
    def reset(self, seed=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0.0
        self.position_value = 0.0
        self.total_trades = 0
        self.successful_trades = 0
        
        return self._get_observation(), {}
    
    def step(self, action):
        if self.current_step >= self.max_steps:
            return self._get_observation(), 0, True, True, {}
        
        current_data = self.historical_data[self.current_step]
        price = current_data.get('price_usd', 0)
        
        reward = 0
        info = {}
        
        # Execute action
        if action == 1 and self.balance > 0:  # Buy
            # Use 10% of balance for each trade
            trade_amount = self.balance * 0.1
            if price > 0:
                tokens_bought = trade_amount / price
                self.position += tokens_bought
                self.balance -= trade_amount
                self.total_trades += 1
                info['action'] = 'buy'
                info['amount'] = trade_amount
        
        elif action == 2 and self.position > 0:  # Sell
            # Sell all position
            if price > 0:
                sell_value = self.position * price
                self.balance += sell_value
                
                # Calculate reward based on profit/loss
                if self.position_value > 0:
                    profit_pct = (sell_value - self.position_value) / self.position_value
                    reward = profit_pct * 10  # Scale reward
                    if profit_pct > 0:
                        self.successful_trades += 1
                
                self.position = 0.0
                self.position_value = 0.0
                info['action'] = 'sell'
                info['profit'] = sell_value - self.position_value if self.position_value > 0 else 0
        
        # Update position value
        if self.position > 0 and price > 0:
            current_position_value = self.position * price
            if self.position_value == 0:
                self.position_value = current_position_value
        
        # Calculate portfolio value
        portfolio_value = self.balance + (self.position * price if price > 0 else 0)
        
        # Additional reward shaping
        if action == 0:  # Hold - small penalty to encourage action
            reward -= 0.001
        
        # Risk penalty for holding too long
        if self.position > 0 and self.current_step > 0:
            volatility = current_data.get('price_change_24h', 0) / 100
            reward -= abs(volatility) * 0.1
        
        self.current_step += 1
        done = self.current_step >= self.max_steps
        
        return self._get_observation(), reward, done, False, info
    
    def _get_observation(self):
        """Get current state observation"""
        if self.current_step >= len(self.historical_data):
            return np.zeros(20, dtype=np.float32)
        
        data = self.historical_data[self.current_step]
        
        # Normalize and extract features
        obs = np.array([
            data.get('price_usd', 0) / 1000,  # Normalized price
            data.get('volume_24h', 0) / 1000000,  # Normalized volume
            data.get('price_change_24h', 0) / 100,  # Price change %
            data.get('price_change_1h', 0) / 100,  # Price change 1h %
            data.get('liquidity_usd', 0) / 100000,  # Normalized liquidity
            data.get('txns_24h', 0) / 1000,  # Normalized transactions
            data.get('market_cap', 0) / 10000000,  # Normalized market cap
            data.get('risk_score', 5) / 10,  # Risk score
            data.get('confidence_score', 5) / 10,  # Confidence score
            data.get('holder_concentration', 50) / 100,  # Holder concentration
            data.get('top_10_percentage', 50) / 100,  # Top 10 holder %
            data.get('social_sentiment_score', 5) / 10,  # Social sentiment
            self.balance / self.initial_balance,  # Remaining balance ratio
            self.position,  # Current position size
            self.total_trades / 100,  # Total trades normalized
            self.successful_trades / max(self.total_trades, 1),  # Success rate
            1.0 if self.position > 0 else 0.0,  # Position indicator
            self.current_step / self.max_steps,  # Progress indicator
            np.sin(self.current_step / 24),  # Time of day feature
            np.cos(self.current_step / 168)  # Day of week feature
        ], dtype=np.float32)
        
        return obs

class AITrader:
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        # Traditional ML models
        self.price_predictor = RandomForestRegressor(n_estimators=100, random_state=42)
        self.risk_assessor = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        
        # RL models
        self.rl_model = None
        self.trading_env = None
        
        # Training data storage
        self.training_data = []
        self.performance_history = []
        
        # Model parameters
        self.min_confidence_threshold = 0.6
        self.max_risk_threshold = 7.0
        self.position_size_factor = 0.1  # Use 10% of balance per trade
        
        self.load_models()
    
    def load_models(self):
        """Load existing models if available"""
        try:
            # Load traditional ML models
            if os.path.exists(f"{self.model_dir}/price_predictor.pkl"):
                with open(f"{self.model_dir}/price_predictor.pkl", 'rb') as f:
                    self.price_predictor = pickle.load(f)
                logger.info("Loaded price predictor model")
            
            if os.path.exists(f"{self.model_dir}/risk_assessor.pkl"):
                with open(f"{self.model_dir}/risk_assessor.pkl", 'rb') as f:
                    self.risk_assessor = pickle.load(f)
                logger.info("Loaded risk assessor model")
            
            if os.path.exists(f"{self.model_dir}/scaler.pkl"):
                with open(f"{self.model_dir}/scaler.pkl", 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info("Loaded feature scaler")
            
            # Load RL model
            if os.path.exists(f"{self.model_dir}/rl_model.zip"):
                self.rl_model = PPO.load(f"{self.model_dir}/rl_model.zip")
                logger.info("Loaded RL model")
            
            # Load training data
            if os.path.exists(f"{self.model_dir}/training_data.json"):
                with open(f"{self.model_dir}/training_data.json", 'r') as f:
                    self.training_data = json.load(f)
                logger.info(f"Loaded {len(self.training_data)} training samples")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    def save_models(self):
        """Save all models"""
        try:
            # Save traditional ML models
            with open(f"{self.model_dir}/price_predictor.pkl", 'wb') as f:
                pickle.dump(self.price_predictor, f)
            
            with open(f"{self.model_dir}/risk_assessor.pkl", 'wb') as f:
                pickle.dump(self.risk_assessor, f)
            
            with open(f"{self.model_dir}/scaler.pkl", 'wb') as f:
                pickle.dump(self.scaler, f)
            
            # Save RL model
            if self.rl_model:
                self.rl_model.save(f"{self.model_dir}/rl_model.zip")
            
            # Save training data
            with open(f"{self.model_dir}/training_data.json", 'w') as f:
                json.dump(self.training_data[-10000:], f)  # Keep only recent data
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    async def should_trade(self, token_data: Dict) -> Dict:
        """Determine if we should trade this token"""
        try:
            # Extract features for analysis
            features = self._extract_features(token_data)
            
            # Get predictions from different models
            ml_decision = self._get_ml_decision(features, token_data)
            rl_decision = self._get_rl_decision(token_data)
            
            # Combine decisions (weighted average)
            ml_weight = 0.6
            rl_weight = 0.4
            
            combined_confidence = (ml_decision['confidence'] * ml_weight + 
                                 rl_decision['confidence'] * rl_weight)
            
            # Risk assessment
            risk_score = token_data.get('risk_score', 5.0)
            
            # Final decision logic
            should_trade = (
                combined_confidence > self.min_confidence_threshold and
                risk_score < self.max_risk_threshold and
                token_data.get('volume_24h', 0) > 10000  # Minimum volume
            )
            
            # Calculate position size based on confidence and risk
            if should_trade:
                base_size = self.position_size_factor
                confidence_multiplier = min(combined_confidence * 1.5, 1.0)
                risk_multiplier = max(1 - (risk_score / 10), 0.1)
                position_size = base_size * confidence_multiplier * risk_multiplier
            else:
                position_size = 0.0
            
            return {
                'should_trade': should_trade,
                'confidence': combined_confidence,
                'risk_score': risk_score,
                'amount': position_size,
                'reasoning': self._generate_reasoning(token_data, ml_decision, rl_decision),
                'ml_confidence': ml_decision['confidence'],
                'rl_confidence': rl_decision['confidence']
            }
            
        except Exception as e:
            logger.error(f"Error in trading decision: {e}")
            return {
                'should_trade': False,
                'confidence': 0.0,
                'risk_score': 10.0,
                'amount': 0.0,
                'reasoning': f"Error in analysis: {e}"
            }
    
    def _extract_features(self, token_data: Dict) -> np.ndarray:
        """Extract numerical features for ML models"""
        features = [
            token_data.get('price_usd', 0),
            token_data.get('volume_24h', 0),
            token_data.get('volume_1h', 0),
            token_data.get('price_change_24h', 0),
            token_data.get('price_change_1h', 0),
            token_data.get('liquidity_usd', 0),
            token_data.get('txns_24h', 0),
            token_data.get('market_cap', 0),
            token_data.get('risk_score', 5.0),
            token_data.get('confidence_score', 5.0),
            token_data.get('holder_concentration', 50),
            token_data.get('top_10_percentage', 50),
            token_data.get('social_sentiment_score', 5.0),
            token_data.get('community_activity_score', 5.0)
        ]
        
        return np.array(features).reshape(1, -1)
    
    def _get_ml_decision(self, features: np.ndarray, token_data: Dict) -> Dict:
        """Get decision from traditional ML models"""
        try:
            if len(self.training_data) < 100:  # Not enough training data
                return {'confidence': 0.5, 'prediction': 0.5}
            
            # Scale features
            scaled_features = self.scaler.transform(features)
            
            # Get price prediction
            price_prediction = self.price_predictor.predict(scaled_features)[0]
            risk_prediction = self.risk_assessor.predict(scaled_features)[0]
            
            # Calculate confidence based on predictions
            confidence = max(0, min(1, (price_prediction + (10 - risk_prediction)) / 15))
            
            return {
                'confidence': confidence,
                'price_prediction': price_prediction,
                'risk_prediction': risk_prediction
            }
            
        except Exception as e:
            logger.error(f"Error in ML decision: {e}")
            return {'confidence': 0.5, 'prediction': 0.5}
    
    def _get_rl_decision(self, token_data: Dict) -> Dict:
        """Get decision from reinforcement learning model"""
        try:
            if not self.rl_model:
                return {'confidence': 0.5, 'action': 0}
            
            # Create observation from token data
            obs = self._create_rl_observation(token_data)
            
            # Get action from RL model
            action, _states = self.rl_model.predict(obs, deterministic=True)
            
            # Convert action to confidence
            # Action 0=hold, 1=buy, 2=sell
            if action == 1:  # Buy
                confidence = 0.7
            elif action == 2:  # Sell (shouldn't happen for new tokens)
                confidence = 0.3
            else:  # Hold
                confidence = 0.4
            
            return {
                'confidence': confidence,
                'action': action,
                'raw_prediction': action
            }
            
        except Exception as e:
            logger.error(f"Error in RL decision: {e}")
            return {'confidence': 0.5, 'action': 0}
    
    def _create_rl_observation(self, token_data: Dict) -> np.ndarray:
        """Create observation for RL model"""
        obs = np.array([
            token_data.get('price_usd', 0) / 1000,
            token_data.get('volume_24h', 0) / 1000000,
            token_data.get('price_change_24h', 0) / 100,
            token_data.get('price_change_1h', 0) / 100,
            token_data.get('liquidity_usd', 0) / 100000,
            token_data.get('txns_24h', 0) / 1000,
            token_data.get('market_cap', 0) / 10000000,
            token_data.get('risk_score', 5) / 10,
            token_data.get('confidence_score', 5) / 10,
            token_data.get('holder_concentration', 50) / 100,
            token_data.get('top_10_percentage', 50) / 100,
            token_data.get('social_sentiment_score', 5) / 10,
            1.0,  # Balance ratio (placeholder)
            0.0,  # Position (placeholder)
            0.0,  # Total trades (placeholder)
            0.5,  # Success rate (placeholder)
            0.0,  # Position indicator
            0.5,  # Progress indicator
            0.0,  # Time features
            0.0
        ], dtype=np.float32)
        
        return obs
    
    def _generate_reasoning(self, token_data: Dict, ml_decision: Dict, rl_decision: Dict) -> str:
        """Generate human-readable reasoning for the decision"""
        reasons = []
        
        # Volume analysis
        volume_24h = token_data.get('volume_24h', 0)
        if volume_24h > 100000:
            reasons.append(f"High volume: ${volume_24h:,.0f}")
        elif volume_24h < 10000:
            reasons.append(f"Low volume: ${volume_24h:,.0f}")
        
        # Risk analysis
        risk_score = token_data.get('risk_score', 5)
        if risk_score < 4:
            reasons.append("Low risk score")
        elif risk_score > 7:
            reasons.append("High risk score")
        
        # Price movement
        price_change = token_data.get('price_change_24h', 0)
        if abs(price_change) > 50:
            reasons.append(f"High volatility: {price_change:+.1f}%")
        
        # Liquidity
        liquidity = token_data.get('liquidity_usd', 0)
        if liquidity < 50000:
            reasons.append("Low liquidity")
        
        return "; ".join(reasons) if reasons else "Standard analysis"
    
    async def update_model(self, token_data: Dict, trade_result: Dict):
        """Update models with new trading result"""
        try:
            # Add to training data
            training_sample = {
                'token_data': token_data,
                'trade_result': trade_result,
                'timestamp': datetime.now().isoformat(),
                'profit_loss': trade_result.get('profit_loss', 0)
            }
            
            self.training_data.append(training_sample)
            
            # Retrain models periodically
            if len(self.training_data) % 100 == 0:  # Retrain every 100 samples
                await self.retrain_model()
            
        except Exception as e:
            logger.error(f"Error updating model: {e}")
    
    async def retrain_model(self):
        """Retrain all models with recent data"""
        try:
            if len(self.training_data) < 50:
                logger.info("Not enough data for retraining")
                return
            
            logger.info(f"Retraining models with {len(self.training_data)} samples")
            
            # Prepare training data
            X, y_price, y_risk = self._prepare_training_data()
            
            if len(X) == 0:
                logger.warning("No valid training data")
                return
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train traditional ML models
            self.price_predictor.fit(X_scaled, y_price)
            self.risk_assessor.fit(X_scaled, y_risk)
            
            # Train RL model
            await self._train_rl_model()
            
            # Save models
            self.save_models()
            
            logger.info("Models retrained successfully")
            
        except Exception as e:
            logger.error(f"Error retraining models: {e}")
    
    def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare training data for ML models"""
        X = []
        y_price = []
        y_risk = []
        
        for sample in self.training_data[-1000:]:  # Use recent 1000 samples
            try:
                token_data = sample['token_data']
                trade_result = sample['trade_result']
                
                # Extract features
                features = self._extract_features(token_data)[0]
                X.append(features)
                
                # Target: profit/loss percentage
                profit_loss = trade_result.get('profit_loss', 0)
                y_price.append(profit_loss)
                
                # Risk target: actual risk experienced
                risk_score = token_data.get('risk_score', 5)
                y_risk.append(risk_score)
                
            except Exception as e:
                logger.warning(f"Error processing training sample: {e}")
                continue
        
        return np.array(X), np.array(y_price), np.array(y_risk)
    
    async def _train_rl_model(self):
        """Train the reinforcement learning model"""
        try:
            if len(self.training_data) < 200:
                return
            
            # Create environment with historical data
            historical_data = [sample['token_data'] for sample in self.training_data[-500:]]
            env = TradingEnvironment(historical_data)
            env = DummyVecEnv([lambda: env])
            
            # Create or update RL model
            if self.rl_model is None:
                self.rl_model = PPO(
                    "MlpPolicy",
                    env,
                    learning_rate=3e-4,
                    n_steps=2048,
                    batch_size=64,
                    n_epochs=10,
                    gamma=0.99,
                    gae_lambda=0.95,
                    clip_range=0.2,
                    verbose=0
                )
            else:
                self.rl_model.set_env(env)
            
            # Train the model
            self.rl_model.learn(total_timesteps=10000, reset_num_timesteps=False)
            
            logger.info("RL model trained successfully")
            
        except Exception as e:
            logger.error(f"Error training RL model: {e}")
    
    async def get_top_opportunities(self, limit: int = 5) -> List[Dict]:
        """Get top trading opportunities from recent analysis"""
        try:
            # This would typically query recent token analyses
            # For now, return placeholder data
            opportunities = []
            
            for i in range(limit):
                opportunities.append({
                    'symbol': f'TOKEN{i+1}',
                    'score': 8.5 - i * 0.5,
                    'volume': 150000 - i * 20000,
                    'price_change': 25.0 - i * 5.0
                })
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error getting top opportunities: {e}")
            return []