import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class DexScreenerScanner:
    def __init__(self):
        self.base_url = "https://api.dexscreener.com/latest/dex"
        self.session = None
        self.last_scan_time = None
        
    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'MemeBot/1.0'}
            )
        return self.session
    
    async def scan_all_tokens(self, chain: str = "solana") -> List[Dict]:
        """Scan for ALL tokens on specified chain - no pre-filtering for AI learning"""
        try:
            session = await self.get_session()
            
            # Use working DexScreener endpoints for Solana tokens
            all_pairs = []
            
            # Comprehensive search to get maximum token variety for AI learning
            search_queries = [
                "SOL", "USDC", "USDT",  # Major tokens
                "raydium", "orca", "jupiter",  # Major DEXes
                "meme", "dog", "cat", "pepe",  # Meme categories  
                "new", "launch", "token",  # New launches
                "moon", "safe", "diamond",  # Common meme terms
                "pump", "gem", "x100"  # High-risk terms
            ]
            
            for query in search_queries:
                try:
                    search_url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
                    logger.debug(f"Searching DexScreener with query: {query}")
                    
                    async with session.get(search_url) as search_response:
                        if search_response.status == 200:
                            search_data = await search_response.json()
                            pairs = search_data.get('pairs', [])
                            logger.debug(f"Got {len(pairs)} pairs from query '{query}'")
                            
                            # Filter for Solana chain and add to collection
                            solana_pairs = [p for p in pairs if p.get('chainId') == 'solana']
                            all_pairs.extend(solana_pairs)
                            logger.debug(f"Added {len(solana_pairs)} Solana pairs")
                        else:
                            logger.warning(f"DexScreener search failed for '{query}': {search_response.status}")
                        
                        await asyncio.sleep(0.2)  # Rate limiting
                        
                except Exception as e:
                    logger.error(f"Search query '{query}' failed: {e}")
                    continue
            
            # Remove duplicates and use all collected pairs
            pairs = []
            seen_addresses = set()
            for pair in all_pairs:
                pair_addr = pair.get('pairAddress', '')
                if pair_addr and pair_addr not in seen_addresses:
                    pairs.append(pair)
                    seen_addresses.add(pair_addr)
                    
            logger.info(f"Collected {len(pairs)} unique Solana pairs from search")
            
            # If no pairs found, try fallback method
            if not pairs:
                logger.warning("No pairs found from search, trying fallback method...")
                try:
                    # Try getting popular token pairs directly
                    fallback_url = "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112"  # SOL token
                    async with session.get(fallback_url) as fallback_response:
                        if fallback_response.status == 200:
                            fallback_data = await fallback_response.json()
                            pairs = fallback_data.get('pairs', [])[:50]  # Limit to first 50
                            logger.info(f"Fallback method found {len(pairs)} SOL pairs")
                        else:
                            logger.error(f"Fallback method also failed: {fallback_response.status}")
                except Exception as e:
                    logger.error(f"Fallback method error: {e}")
            
            # Process ALL tokens - let AI learn from everything
            all_tokens = []
            current_time = datetime.utcnow()
            
            for pair in pairs:
                try:
                    token_data = self._extract_token_data(pair)
                    
                    # Add age calculation for AI features (but don't filter by it)
                    created_timestamp = pair.get('pairCreatedAt', 0)
                    if created_timestamp:
                        created_at = datetime.fromtimestamp(created_timestamp / 1000)
                        age_hours = (current_time - created_at).total_seconds() / 3600
                        token_data['age_hours'] = age_hours
                        token_data['is_new'] = age_hours <= 24  # Feature for AI
                    else:
                        token_data['age_hours'] = 999  # Unknown age
                        token_data['is_new'] = False
                    
                    # Add risk indicators as features for AI learning
                    token_data['risk_score'] = self._calculate_risk_score(token_data)
                    token_data['volume_score'] = self._calculate_volume_score(token_data)
                    token_data['liquidity_score'] = self._calculate_liquidity_score(token_data)
                    
                    # Only apply minimal validation
                    if self._is_valid_token(token_data):
                        all_tokens.append(token_data)
                
                except (ValueError, TypeError) as e:
                    logger.debug(f"Error parsing pair data: {e}")
                    continue
            
            logger.info(f"Found {len(all_tokens)} tokens from DexScreener (no pre-filtering)")
            
            # Sort by recency and activity for AI to learn from fresh data first
            return sorted(all_tokens, key=lambda x: (x['age_hours'] * -1, x['volume_24h']), reverse=False)
                
        except Exception as e:
            logger.error(f"Error scanning DexScreener: {e}")
            return []
    
    def _extract_token_data(self, pair: Dict) -> Dict:
        """Extract relevant token data from DexScreener pair"""
        base_token = pair.get('baseToken', {})
        txns = pair.get('txns', {})
        volume = pair.get('volume', {})
        liquidity = pair.get('liquidity', {})
        
        # Calculate total transactions (m5 and h1 available in new API)
        txns_5m = txns.get('m5', 0)
        txns_1h = txns.get('h1', 0)
        
        return {
            'symbol': base_token.get('symbol', 'UNKNOWN'),
            'name': base_token.get('name', 'Unknown Token'),
            'address': base_token.get('address', ''),
            'price': float(pair.get('priceNative', 0)),
            'price_usd': float(pair.get('priceUsd', 0)),
            'volume_24h': float(volume.get('h24', 0)),
            'volume_1h': float(volume.get('h1', 0)),
            'txns_24h': int(txns_1h * 24) if txns_1h > 0 else 0,  # Estimate 24h from 1h
            'txns_1h': int(txns_1h),
            'txns_5m': int(txns_5m),
            'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0)),
            'price_change_1h': float(pair.get('priceChange', {}).get('h1', 0)),
            'liquidity_usd': float(liquidity.get('usd', 0)),
            'market_cap': float(pair.get('fdv', 0)),  # Use fdv (fully diluted valuation)
            'dex': pair.get('dexId', ''),
            'pair_address': pair.get('pairAddress', ''),
            'created_at': pair.get('pairCreatedAt', 0),
            'chain_id': pair.get('chainId', 'solana'),
            'source': 'dexscreener'
        }
    
    def _is_valid_token(self, token: Dict) -> bool:
        """Minimal validation - let AI learn from ALL data"""
        # Only skip tokens with completely missing critical data
        if not token.get('address') or not token.get('symbol'):
            return False
        
        # Only skip completely broken price data
        try:
            price = float(token.get('price_usd', 0))
            if price < 0:  # Negative prices are invalid
                return False
        except (ValueError, TypeError):
            return False
        
        # That's it! Let the AI model learn from everything else:
        # - Low volume tokens
        # - New tokens with few transactions
        # - Low liquidity tokens  
        # - Suspicious looking symbols
        # - High risk tokens
        # The model will learn which patterns lead to good vs bad trades
        
        return True
    
    def _calculate_risk_score(self, token: Dict) -> float:
        """Calculate risk score (0-10, higher = riskier) for AI learning"""
        risk_score = 0.0
        
        # Symbol-based risk indicators
        symbol = token.get('symbol', '').upper()
        suspicious_keywords = ['SCAM', 'RUG', 'FAKE', 'TEST', 'HONEYPOT', 'PONZI', 'PUMP', 'DUMP']
        meme_keywords = ['DOGE', 'SHIB', 'PEPE', 'FLOKI', 'SAFE', 'MOON', 'ROCKET', 'DIAMOND']
        
        for keyword in suspicious_keywords:
            if keyword in symbol:
                risk_score += 3.0
        
        for keyword in meme_keywords:
            if keyword in symbol:
                risk_score += 1.0
        
        # Age-based risk
        age_hours = token.get('age_hours', 999)
        if age_hours < 1:
            risk_score += 2.0  # Very new = risky
        elif age_hours < 24:
            risk_score += 1.0  # New = somewhat risky
        
        # Volume-based risk  
        volume_24h = token.get('volume_24h', 0)
        if volume_24h < 100:
            risk_score += 2.0  # Very low volume
        elif volume_24h < 1000:
            risk_score += 1.0  # Low volume
        
        # Liquidity-based risk
        liquidity_usd = token.get('liquidity_usd', 0)
        if liquidity_usd < 1000:
            risk_score += 2.0  # Very low liquidity
        elif liquidity_usd < 5000:
            risk_score += 1.0  # Low liquidity
        
        return min(risk_score, 10.0)  # Cap at 10
    
    def _calculate_volume_score(self, token: Dict) -> float:
        """Calculate volume activity score (0-10, higher = more active)"""
        volume_24h = token.get('volume_24h', 0)
        txns_1h = token.get('txns_1h', 0)
        
        # Volume scoring
        if volume_24h >= 1000000:  # $1M+
            volume_score = 10.0
        elif volume_24h >= 100000:  # $100K+
            volume_score = 8.0
        elif volume_24h >= 10000:  # $10K+
            volume_score = 6.0
        elif volume_24h >= 1000:   # $1K+
            volume_score = 4.0
        elif volume_24h >= 100:    # $100+
            volume_score = 2.0
        else:
            volume_score = 0.0
        
        # Transaction frequency bonus
        if txns_1h >= 100:
            volume_score += 2.0
        elif txns_1h >= 10:
            volume_score += 1.0
        elif txns_1h >= 1:
            volume_score += 0.5
        
        return min(volume_score, 10.0)
    
    def _calculate_liquidity_score(self, token: Dict) -> float:
        """Calculate liquidity score (0-10, higher = more liquid)"""
        liquidity_usd = token.get('liquidity_usd', 0)
        
        if liquidity_usd >= 1000000:  # $1M+
            return 10.0
        elif liquidity_usd >= 100000:  # $100K+
            return 8.0
        elif liquidity_usd >= 50000:   # $50K+
            return 6.0
        elif liquidity_usd >= 10000:   # $10K+
            return 4.0
        elif liquidity_usd >= 5000:    # $5K+
            return 3.0
        elif liquidity_usd >= 1000:    # $1K+
            return 2.0
        elif liquidity_usd > 0:
            return 1.0
        else:
            return 0.0
    
    async def scan_new_tokens(self, chain: str = "solana") -> List[Dict]:
        """Backwards compatibility - calls scan_all_tokens"""
        return await self.scan_all_tokens(chain)
    
    async def get_token_details(self, token_address: str) -> Optional[Dict]:
        """Get detailed information for a specific token"""
        try:
            session = await self.get_session()
            url = f"{self.base_url}/tokens/{token_address}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('pairs', [])[0] if data.get('pairs') else None
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting token details for {token_address}: {e}")
            return None
    
    async def get_trending_tokens(self, limit: int = 50) -> List[Dict]:
        """Get trending tokens across all DEXes"""
        try:
            session = await self.get_session()
            url = f"{self.base_url}/tokens/trending?limit={limit}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return [self._extract_token_data(pair) for pair in data.get('pairs', [])]
                
                return []
                
        except Exception as e:
            logger.error(f"Error getting trending tokens: {e}")
            return []
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()