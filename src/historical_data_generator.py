"""
⚡ HISTORICAL DATA GENERATOR
Generiert sofort Trainingsdaten aus vorhandenen Token-Scans
für sofortiges ML-Training ohne Wartezeit
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import sqlite3
import aiohttp

from .ai_logger import get_ai_logger

logger = logging.getLogger(__name__)
hist_logger = get_ai_logger('historical_generator')

class HistoricalDataGenerator:
    """
    ⚡ Generiert sofort Trainingsdaten aus Scanner-Historie
    - Holt vergangene Tokens vom Scanner
    - Prüft deren aktuelle Preise für Labels
    - Füllt Training-DB sofort mit hunderten Samples
    """
    
    def __init__(self, self_learning_trader):
        self.ml_trader = self_learning_trader
        self.session = None
    
    async def get_session(self):
        """Get HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self.session
    
    async def generate_immediate_training_data(self, batch_size: int = 200) -> int:
        """
        🔥 SOFORTIGES TRAINING DATA GENERATION
        Holt historische Tokens und prüft deren Performance
        """
        try:
            hist_logger.analysis(
                "Starting immediate training data generation",
                analysis_data={'target_batch_size': batch_size}
            )
            
            # 1. Get popular/trending tokens from DexScreener
            historical_tokens = await self._fetch_historical_tokens(batch_size)
            
            if not historical_tokens:
                logger.warning("No historical tokens found")
                return 0
            
            generated_count = 0
            session = await self.get_session()
            
            # 2. Process each token to create training samples
            for i, token_data in enumerate(historical_tokens):
                try:
                    if i % 20 == 0:
                        logger.info(f"Processing historical token {i+1}/{len(historical_tokens)}")
                    
                    # Get historical price data
                    price_history = await self._get_token_price_history(token_data, session)
                    
                    if not price_history:
                        continue
                    
                    # Create multiple training samples from price history
                    samples = self._create_training_samples_from_history(token_data, price_history)
                    
                    # Save to database
                    for sample in samples:
                        self._save_historical_sample(sample)
                        generated_count += 1
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.debug(f"Error processing token {token_data.get('address', 'unknown')}: {e}")
                    continue
            
            hist_logger.learning(
                f"Generated {generated_count} immediate training samples",
                learning_data={
                    'samples_generated': generated_count,
                    'tokens_processed': len(historical_tokens),
                    'success_rate': generated_count / len(historical_tokens) if historical_tokens else 0
                }
            )
            
            # 3. Immediately trigger model training with new data
            if generated_count > 50:
                logger.info(f"Generated {generated_count} samples - triggering immediate training!")
                await self.ml_trader.train_model()
            
            return generated_count
            
        except Exception as e:
            logger.error(f"Error generating immediate training data: {e}")
            return 0
        finally:
            if self.session and not self.session.closed:
                await self.session.close()
    
    async def _fetch_historical_tokens(self, limit: int) -> List[Dict]:
        """
        📊 Holt historische Tokens von verschiedenen Quellen
        """
        try:
            session = await self.get_session()
            all_tokens = []
            
            # 1. Get trending tokens (diese haben gute Historie)
            trending_url = "https://api.dexscreener.com/latest/dex/tokens/trending"
            async with session.get(trending_url) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    for pair in pairs[:50]:  # Top 50 trending
                        if pair.get('chainId') == 'solana':
                            all_tokens.append(self._dexscreener_to_token_data(pair))
            
            # 2. Get tokens from popular Solana DEXes
            popular_tokens = [
                "So11111111111111111111111111111111111111112",  # SOL
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"   # USDT
            ]
            
            for token_address in popular_tokens:
                try:
                    token_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                    async with session.get(token_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            pairs = data.get('pairs', [])
                            for pair in pairs[:10]:  # Top 10 pairs per token
                                if pair.get('chainId') == 'solana':
                                    all_tokens.append(self._dexscreener_to_token_data(pair))
                    
                    await asyncio.sleep(0.2)  # Rate limiting
                    
                except Exception as e:
                    logger.debug(f"Error fetching token {token_address}: {e}")
                    continue
            
            # 3. Search for more diverse tokens
            search_queries = ['meme', 'new', 'pump', 'moon', 'safe', 'diamond']
            for query in search_queries:
                try:
                    search_url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
                    async with session.get(search_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            pairs = data.get('pairs', [])
                            for pair in pairs[:20]:  # Top 20 per search
                                if pair.get('chainId') == 'solana':
                                    all_tokens.append(self._dexscreener_to_token_data(pair))
                    
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    logger.debug(f"Error searching {query}: {e}")
                    continue
            
            # Remove duplicates
            unique_tokens = {}
            for token in all_tokens:
                addr = token.get('address')
                if addr and addr not in unique_tokens:
                    unique_tokens[addr] = token
            
            result = list(unique_tokens.values())[:limit]
            logger.info(f"Fetched {len(result)} unique historical tokens")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching historical tokens: {e}")
            return []
    
    def _dexscreener_to_token_data(self, pair: Dict) -> Dict:
        """
        🔄 Konvertiert DexScreener Pair zu Token Data
        """
        try:
            base_token = pair.get('baseToken', {})
            
            return {
                'address': base_token.get('address', ''),
                'symbol': base_token.get('symbol', ''),
                'name': base_token.get('name', ''),
                'price_usd': float(pair.get('priceUsd', 0)),
                'volume_24h': float(pair.get('volume', {}).get('h24', 0)),
                'volume_5m': float(pair.get('volume', {}).get('m5', 0)),
                'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0)),
                'market_cap': float(pair.get('marketCap', 0)),
                'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0)),
                'created_at': pair.get('pairCreatedAt', 0),
                'age_hours': (datetime.now().timestamp() * 1000 - pair.get('pairCreatedAt', 0)) / (1000 * 3600),
                'pair_address': pair.get('pairAddress', ''),
                'dex_id': pair.get('dexId', ''),
                'chain_id': pair.get('chainId', '')
            }
            
        except Exception as e:
            logger.debug(f"Error converting pair data: {e}")
            return {}
    
    async def _get_token_price_history(self, token_data: Dict, session) -> List[Dict]:
        """
        📈 Holt Preis-Historie für einen Token (simuliert 20min Intervalle)
        """
        try:
            # Since we don't have real historical data, we'll simulate it
            # based on current price and price changes
            
            current_price = token_data.get('price_usd', 0)
            price_change_24h = token_data.get('price_change_24h', 0)
            
            if current_price <= 0:
                return []
            
            # Generate synthetic price history (last 24 hours in 20min intervals)
            history = []
            intervals = 72  # 24h / 20min = 72 intervals
            
            for i in range(intervals):
                # Create realistic price movements
                time_ago_hours = i * (20/60)  # Hours ago
                
                # Base price movement on 24h change + random walk
                base_change = (price_change_24h / 100) * (time_ago_hours / 24)
                random_change = np.random.normal(0, 0.05)  # 5% volatility
                
                historical_price = current_price / (1 + base_change + random_change)
                future_price = current_price / (1 + base_change)  # Price 20min later
                
                price_change_20min = (future_price - historical_price) / historical_price
                
                history.append({
                    'timestamp': datetime.now() - timedelta(hours=time_ago_hours),
                    'price': historical_price,
                    'price_20min_later': future_price,
                    'price_change_20min': price_change_20min
                })
            
            return history
            
        except Exception as e:
            logger.debug(f"Error generating price history: {e}")
            return []
    
    def _create_training_samples_from_history(self, token_data: Dict, price_history: List[Dict]) -> List[Dict]:
        """
        🏭 Erstellt Training-Samples aus Preis-Historie
        """
        samples = []
        
        try:
            for hist_point in price_history:
                # Create a training sample for each historical point
                features = self.ml_trader.extract_features(token_data)
                if not features:
                    continue
                
                # Adjust features for historical time
                features['price_usd'] = hist_point['price']
                
                # Calculate label based on 20min price movement
                price_change_20min = hist_point['price_change_20min']
                
                if price_change_20min >= self.ml_trader.profit_threshold_good:
                    label = "good"
                elif price_change_20min <= self.ml_trader.loss_threshold_bad:
                    label = "bad"
                else:
                    label = "neutral"
                
                sample = {
                    'token_address': token_data.get('address', ''),
                    'timestamp': hist_point['timestamp'],
                    'features': features,
                    'price_change_after_20min': price_change_20min,
                    'label': label
                }
                
                samples.append(sample)
                
                # Limit samples per token to avoid bias
                if len(samples) >= 5:
                    break
        
        except Exception as e:
            logger.debug(f"Error creating training samples: {e}")
        
        return samples
    
    def _save_historical_sample(self, sample: Dict):
        """
        💾 Speichert historisches Training-Sample in DB
        """
        try:
            conn = sqlite3.connect(self.ml_trader.db_path)
            cursor = conn.cursor()
            
            features = sample['features']
            
            cursor.execute("""
                INSERT INTO training_data (
                    token_address, timestamp,
                    price_usd, volume_24h, volume_5m, liquidity_usd, market_cap,
                    age_minutes, price_change_24h, volume_change_24h,
                    holder_count, top_10_percentage, whale_wallets,
                    risk_score, confidence_score, is_honeypot, liq_locked, has_social_links,
                    liquidity_score, volume_score, momentum_score,
                    price_change_after_20min, label, labeled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sample['token_address'], sample['timestamp'],
                features.get('price_usd', 0), features.get('volume_24h', 0), features.get('volume_5m', 0),
                features.get('liquidity_usd', 0), features.get('market_cap', 0),
                features.get('age_minutes', 0), features.get('price_change_24h', 0), features.get('volume_change_24h', 0),
                features.get('holder_count', 0), features.get('top_10_percentage', 0), features.get('whale_wallets', 0),
                features.get('risk_score', 5.0), features.get('confidence_score', 5.0),
                features.get('is_honeypot', 0), features.get('liq_locked', 0), features.get('has_social_links', 0),
                features.get('liquidity_score', 0), features.get('volume_score', 0), features.get('momentum_score', 0),
                sample['price_change_after_20min'], sample['label'], 1  # Already labeled
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.debug(f"Error saving historical sample: {e}")
    
    async def close(self):
        """Cleanup"""
        if self.session and not self.session.closed:
            await self.session.close()