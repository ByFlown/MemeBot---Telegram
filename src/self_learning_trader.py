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
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
from sklearn.linear_model import SGDClassifier
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
        
        # ML Configuration
        self.learning_window_minutes = 20  # Preis nach X Minuten prüfen
        self.profit_threshold_good = 0.10   # +10% = "good"
        self.loss_threshold_bad = -0.10     # -10% = "bad"
        
        # Models
        self.model = None
        self.scaler = StandardScaler()
        self.online_model = SGDClassifier(random_state=42)  # Für Online-Learning
        self.is_trained = False
        
        # Database for training data
        self.db_path = self.data_dir / "training_data.db"
        self.init_database()
        
        # Price tracking for auto-labeling
        self.price_tracker = {}  # {token_address: {entry_time, entry_price, features}}
        
        # Load existing model if available
        self.load_models()
        
        # Flag for initial data generation
        self._initial_data_generated = False
    
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
                
                -- Label (Generated automatically)
                price_change_after_20min REAL,
                label TEXT,  -- 'good', 'bad', 'neutral'
                
                -- Metadata
                labeled INTEGER DEFAULT 0,
                trade_simulated INTEGER DEFAULT 0
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
    
    async def start_price_tracking(self, token_data: Dict):
        """
        📊 Startet Preis-Tracking für automatisches Labeling
        Speichert Token-Daten und startet Timer für spätere Label-Generierung
        """
        try:
            token_address = token_data.get('address')
            if not token_address:
                return
            
            # Extract features
            features = self.extract_features(token_data)
            if not features:
                return
            
            # Store tracking info
            self.price_tracker[token_address] = {
                'entry_time': datetime.now(),
                'entry_price': features['price_usd'],
                'features': features,
                'token_data': token_data
            }
            
            # Save to database (unlabeled)
            self.save_training_sample(token_address, features, label_price_change=None)
            
            # Schedule labeling after learning_window_minutes
            asyncio.create_task(self.schedule_labeling(token_address))
            
            ml_logger.analysis(
                f"Started price tracking for automatic labeling",
                token_address=token_address,
                analysis_data={
                    'entry_price': features['price_usd'],
                    'tracking_duration_minutes': self.learning_window_minutes
                }
            )
            
        except Exception as e:
            logger.error(f"Error starting price tracking: {e}")
    
    async def schedule_labeling(self, token_address: str):
        """
        ⏰ Wartet X Minuten und generiert dann automatisch Labels
        """
        try:
            # Wait for learning window
            await asyncio.sleep(self.learning_window_minutes * 60)
            
            # Generate label
            await self.generate_automatic_label(token_address)
            
        except Exception as e:
            logger.error(f"Error in scheduled labeling for {token_address}: {e}")
    
    async def generate_automatic_label(self, token_address: str):
        """
        🏷️ Generiert automatisch Labels durch Preisverfolgung
        KERN-FEATURE: Hier entstehen die Trainings-Labels!
        """
        try:
            if token_address not in self.price_tracker:
                return
            
            tracking_info = self.price_tracker[token_address]
            entry_price = tracking_info['entry_price']
            
            # Get current price (re-query DexScreener)
            current_price = await self.get_current_price(token_address)
            
            if current_price is None or current_price <= 0:
                logger.warning(f"Could not get current price for {token_address[:8]}... - labeling as 'neutral'")
                # Still create a label even if price fetch fails
                self.update_training_sample_label(token_address, 0.0, "neutral")
                if token_address in self.price_tracker:
                    del self.price_tracker[token_address]
                return
            
            # Calculate price change
            price_change = (current_price - entry_price) / entry_price
            
            # Generate label based on performance
            if price_change >= self.profit_threshold_good:
                label = "good"
            elif price_change <= self.loss_threshold_bad:
                label = "bad"
            else:
                label = "neutral"
            
            # Update database with label
            self.update_training_sample_label(token_address, price_change, label)
            
            # Remove from tracker and clean up memory
            if token_address in self.price_tracker:
                del self.price_tracker[token_address]
            
            # Clean up expired tracking entries to prevent memory leaks
            current_time = datetime.now()
            expired_tokens = []
            for addr, info in self.price_tracker.items():
                if (current_time - info['entry_time']).total_seconds() > 25 * 60:  # 25min cleanup
                    expired_tokens.append(addr)
            
            for addr in expired_tokens:
                del self.price_tracker[addr]
                logger.debug(f"Cleaned up expired tracking for {addr[:8]}...")
            
            # Log automatic labeling
            ml_logger.learning(
                f"Automatic label generated: {label}",
                learning_data={
                    'token': token_address[:8] + "...",
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'price_change_pct': price_change * 100,
                    'label': label,
                    'tracking_duration_min': self.learning_window_minutes
                },
                reward=price_change
            )
            
            # Trigger model retraining if enough new data
            await self.check_retrain_trigger()
            
        except Exception as e:
            logger.error(f"Error generating automatic label: {e}")
    
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
    
    def save_training_sample(self, token_address: str, features: Dict, label_price_change: Optional[float] = None):
        """
        💾 Speichert Training-Sample in Datenbank
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
                    liquidity_score, volume_score, momentum_score,
                    price_change_after_20min, labeled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                token_address, datetime.now(),
                features.get('price_usd', 0), features.get('volume_24h', 0), features.get('volume_5m', 0),
                features.get('liquidity_usd', 0), features.get('market_cap', 0),
                features.get('age_minutes', 0), features.get('price_change_24h', 0), features.get('volume_change_24h', 0),
                features.get('holder_count', 0), features.get('top_10_percentage', 0), features.get('whale_wallets', 0),
                features.get('risk_score', 5.0), features.get('confidence_score', 5.0),
                features.get('is_honeypot', 0), features.get('liq_locked', 0), features.get('has_social_links', 0),
                features.get('liquidity_score', 0), features.get('volume_score', 0), features.get('momentum_score', 0),
                label_price_change, 1 if label_price_change is not None else 0
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving training sample: {e}")
    
    def update_training_sample_label(self, token_address: str, price_change: float, label: str):
        """
        🏷️ Aktualisiert Training-Sample mit generiertem Label
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE training_data 
                SET price_change_after_20min = ?, label = ?, labeled = 1
                WHERE token_address = ? AND labeled = 0
            """, (price_change, label, token_address))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating training sample label: {e}")
    
    async def check_retrain_trigger(self):
        """
        🔄 Prüft ob Modell neu trainiert werden soll
        """
        try:
            labeled_count = self.get_labeled_sample_count()
            
            # Retrain every 50 new labeled samples
            if labeled_count > 0 and labeled_count % 50 == 0:
                logger.info(f"Triggering model retraining with {labeled_count} samples")
                await self.train_model()
            
        except Exception as e:
            logger.error(f"Error checking retrain trigger: {e}")
    
    def get_labeled_sample_count(self) -> int:
        """
        📊 Anzahl der gelabelten Training-Samples
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM training_data WHERE labeled = 1")
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
            
        except Exception as e:
            logger.error(f"Error getting labeled sample count: {e}")
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
            df = pd.read_sql_query("SELECT * FROM training_data WHERE labeled = 1", conn)
            conn.close()
            return df
            
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return pd.DataFrame()
    
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
    
    async def predict_token_score(self, token_data: Dict) -> Dict:
        """
        🎯 Scored neuen Token mit ML-Modell
        HAUPTFUNKTION: Hier entscheidet das System autonom!
        """
        try:
            # Generate initial training data if not done yet
            if not self.is_trained and not self._initial_data_generated:
                await self._generate_initial_training_data()
            
            if not self.is_trained:
                return {
                    'should_trade': False,
                    'confidence': 0.0,
                    'probabilities': {},
                    'reason': 'Model not trained yet'
                }
            
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
                'has_social_links', 'liquidity_score', 'volume_score', 'momentum_score'
            ]
            
            # Create DataFrame with feature names to avoid sklearn warning
            feature_data = {col: [features.get(col, 0)] for col in feature_columns}
            feature_df = pd.DataFrame(feature_data)
            
            # Scale features (now with consistent feature names)
            feature_vector_scaled = self.scaler.transform(feature_df)
            
            # Get prediction probabilities
            probabilities = self.model.predict_proba(feature_vector_scaled)[0]
            classes = self.model.classes_
            
            prob_dict = dict(zip(classes, probabilities))
            
            # Decision logic
            good_prob = prob_dict.get('good', 0.0)
            should_trade = good_prob > 0.7  # 70% Schwellwert für "good"
            
            result = {
                'should_trade': should_trade,
                'confidence': good_prob,
                'probabilities': prob_dict,
                'reason': f"ML prediction: {good_prob:.1%} good probability"
            }
            
            # Log prediction
            ml_logger.prediction(
                f"Token scored: {'TRADE' if should_trade else 'SKIP'}",
                predicted_value=good_prob,
                prediction_horizon=f"{self.learning_window_minutes}min",
                model_info={
                    'model_type': type(self.model).__name__,
                    'probabilities': {k: f"{v:.3f}" for k, v in prob_dict.items()},
                    'decision_threshold': 0.7
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error predicting token score: {e}")
            return {
                'should_trade': False,
                'confidence': 0.0,
                'probabilities': {},
                'reason': f'Prediction error: {e}'
            }
    
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
        📊 Statistiken über das Training
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Basic stats
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM training_data")
            total_samples = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM training_data WHERE labeled = 1")
            labeled_samples = cursor.fetchone()[0]
            
            # Label distribution
            cursor.execute("SELECT label, COUNT(*) FROM training_data WHERE labeled = 1 GROUP BY label")
            label_dist = dict(cursor.fetchall())
            
            # Recent performance
            cursor.execute("""
                SELECT AVG(price_change_after_20min) 
                FROM training_data 
                WHERE labeled = 1 AND timestamp > datetime('now', '-7 days')
            """)
            recent_avg_return = cursor.fetchone()[0] or 0
            
            # Model performance metrics (if available)
            model_performance = {}
            if self.is_trained:
                try:
                    # Get recent model accuracy from logs or calculate from recent predictions
                    cursor.execute("""
                        SELECT AVG(CASE WHEN label = 'good' THEN 1 ELSE 0 END) as good_ratio
                        FROM training_data 
                        WHERE labeled = 1 AND timestamp > datetime('now', '-7 days')
                    """)
                    good_ratio = cursor.fetchone()[0] or 0
                    
                    model_performance = {
                        'recent_good_ratio': good_ratio,
                        'model_type': type(self.model).__name__ if self.model else 'Unknown',
                        'features_count': 19  # Number of features used
                    }
                except Exception as e:
                    logger.debug(f"Could not calculate model performance: {e}")
            
            conn.close()
            
            return {
                'total_samples': total_samples,
                'labeled_samples': labeled_samples,
                'label_distribution': label_dist,
                'recent_avg_return_7d': recent_avg_return,
                'model_trained': self.is_trained,
                'learning_window_minutes': self.learning_window_minutes,
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
                logger.info(f"✅ Generated {samples_generated} training samples")
                
                # Now perform initial 80/20 training if we have enough data
                labeled_count = self.get_labeled_sample_count()
                if labeled_count >= 50:  # Minimum samples for meaningful 80/20 split
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
                    logger.info(f"⏳ Only {labeled_count} samples generated, need 50+ for meaningful training")
            else:
                logger.warning("⚠️ Could not generate immediate training data - will wait for real-time data")
            
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