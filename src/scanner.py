import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json
import numpy as np

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
            
            logger.info(f"Processing {len(pairs)} pairs to extract tokens...")
            
            for i, pair in enumerate(pairs):
                try:
                    logger.debug(f"[{i+1}/{len(pairs)}] Processing pair: {pair.get('pairAddress', 'unknown')}")
                    
                    # Debug: Show raw pair data for first few pairs
                    if i < 3:
                        logger.info(f"Sample pair {i+1}: chainId={pair.get('chainId')}, baseToken={pair.get('baseToken', {}).get('symbol', 'N/A')}")
                    
                    token_data = self._extract_token_data(pair)
                    logger.debug(f"Extracted basic data: symbol={token_data.get('symbol')}, address={token_data.get('address', 'N/A')[:10]}...")
                    
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
                    
                    logger.debug(f"Enhanced data: risk={token_data['risk_score']:.1f}, volume_score={token_data['volume_score']:.1f}")
                    
                    # Only apply minimal validation
                    if self._is_valid_token(token_data):
                        all_tokens.append(token_data)
                        logger.info(f"✅ Added token {len(all_tokens)}: {token_data['symbol']} (${token_data.get('price_usd', 0)})")
                    else:
                        logger.warning(f"❌ Rejected token: {token_data.get('symbol', 'UNKNOWN')} - reason logged above")
                
                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing pair {i+1}: {e}")
                    logger.debug(f"Problematic pair data: {pair}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error processing pair {i+1}: {e}")
                    continue
            
            logger.info(f"Found {len(all_tokens)} tokens from DexScreener (no pre-filtering)")
            
            # Add detailed logging if we found pairs but no valid tokens
            if len(pairs) > 0 and len(all_tokens) == 0:
                logger.warning(f"Found {len(pairs)} pairs but 0 valid tokens - validation too strict?")
                # Log first pair details for debugging
                if pairs:
                    sample_pair = pairs[0]
                    logger.warning(f"Sample pair data: {json.dumps(sample_pair, indent=2)[:500]}...")
            
            # Sort by recency and activity for AI to learn from fresh data first
            return sorted(all_tokens, key=lambda x: (x['age_hours'] * -1, x['volume_24h']), reverse=False)
                
        except Exception as e:
            logger.error(f"Error scanning DexScreener: {e}")
            return []
    
    def _extract_token_data(self, pair: Dict) -> Dict:
        """Extract relevant token data from DexScreener pair"""
        logger.debug(f"Extracting data from pair: {pair.get('pairAddress', 'unknown')}")
        
        base_token = pair.get('baseToken', {})
        txns = pair.get('txns', {})
        volume = pair.get('volume', {})
        liquidity = pair.get('liquidity', {})
        
        logger.debug(f"Base token data: {base_token}")
        logger.debug(f"Volume data: {volume}")
        logger.debug(f"Liquidity data: {liquidity}")
        
        # Calculate total transactions (m5 and h1 available in new API) - safe extraction
        def safe_float(value, default=0.0):
            try:
                if isinstance(value, dict):
                    return default
                return float(value) if value is not None else default
            except (ValueError, TypeError):
                return default
        
        def safe_int(value, default=0):
            try:
                if isinstance(value, dict):
                    return default
                return int(value) if value is not None else default
            except (ValueError, TypeError):
                return default

        txns_5m = safe_int(txns.get('m5', 0))
        txns_1h = safe_int(txns.get('h1', 0))
        
        # Extract all data with error handling
        try:
            symbol = base_token.get('symbol', 'UNKNOWN')
            address = base_token.get('address', '')
            price_usd = safe_float(pair.get('priceUsd'))
            
            logger.debug(f"Basic extraction: symbol={symbol}, address={address[:10] if address else 'empty'}, price=${price_usd}")
            
            extracted_data = {
                'symbol': symbol,
                'name': base_token.get('name', 'Unknown Token'),
                'address': address,
                'price': safe_float(pair.get('priceNative')),
                'price_usd': price_usd,
                'volume_24h': safe_float(volume.get('h24')),
                'volume_1h': safe_float(volume.get('h1')),
                'txns_24h': safe_int(txns_1h * 24) if txns_1h > 0 else 0,  # Safe comparison now
                'txns_1h': txns_1h,  # Already safe
                'txns_5m': txns_5m,  # Already safe
                'price_change_24h': safe_float(pair.get('priceChange', {}).get('h24')),
                'price_change_1h': safe_float(pair.get('priceChange', {}).get('h1')),
                'liquidity_usd': safe_float(liquidity.get('usd')),
                'market_cap': safe_float(pair.get('fdv')),  # Use fdv (fully diluted valuation)
                'dex': pair.get('dexId', ''),
                'pair_address': pair.get('pairAddress', ''),
                'created_at': safe_int(pair.get('pairCreatedAt')),
                'chain_id': pair.get('chainId', 'solana'),
                'source': 'dexscreener'
            }
            
            logger.debug(f"Successfully extracted token data for: {symbol}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error in _extract_token_data: {e}")
            logger.debug(f"Pair causing error: {json.dumps(pair, indent=2)[:500]}...")
            raise
    
    def _is_valid_token(self, token: Dict) -> bool:
        """Ultra-minimal validation - let AI learn from ALL data"""
        # Only skip tokens with completely missing symbol (address can be empty for testing)
        symbol = token.get('symbol', '').strip()
        if not symbol or symbol == 'UNKNOWN':
            logger.debug(f"Rejected: missing/invalid symbol '{symbol}'")
            return False
        
        # Allow empty addresses for learning (some pairs might have partial data)
        address = token.get('address', '').strip()
        if not address:
            logger.debug(f"Token {symbol} has no address - allowing for learning")
            # Don't reject, let AI learn from this too
        
        # Allow any price including 0 (some new tokens start at 0)
        try:
            price = float(token.get('price_usd', 0))
            if price < 0:  # Only reject negative prices
                logger.debug(f"Rejected: negative price {price}")
                return False
        except (ValueError, TypeError):
            logger.debug(f"Rejected: invalid price data")
            return False
        
        logger.debug(f"✅ Accepted token: {symbol} (${price})")
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
        
        # Volume-based risk (handle dict/string values)
        try:
            volume_24h = float(token.get('volume_24h', 0)) if not isinstance(token.get('volume_24h', 0), dict) else 0
            if volume_24h < 100:
                risk_score += 2.0  # Very low volume
            elif volume_24h < 1000:
                risk_score += 1.0  # Low volume
        except (ValueError, TypeError):
            risk_score += 1.0  # Unknown volume = some risk
        
        # Liquidity-based risk (handle dict/string values)
        try:
            liquidity_usd = float(token.get('liquidity_usd', 0)) if not isinstance(token.get('liquidity_usd', 0), dict) else 0
            if liquidity_usd < 1000:
                risk_score += 2.0  # Very low liquidity
            elif liquidity_usd < 5000:
                risk_score += 1.0  # Low liquidity
        except (ValueError, TypeError):
            risk_score += 1.0  # Unknown liquidity = some risk
        
        return min(risk_score, 10.0)  # Cap at 10
    
    def _calculate_volume_score(self, token: Dict) -> float:
        """Calculate volume activity score (0-10, higher = more active)"""
        # Handle dict/string values safely
        try:
            volume_24h = float(token.get('volume_24h', 0)) if not isinstance(token.get('volume_24h', 0), dict) else 0
        except (ValueError, TypeError):
            volume_24h = 0
            
        try:
            txns_1h = int(token.get('txns_1h', 0)) if not isinstance(token.get('txns_1h', 0), dict) else 0
        except (ValueError, TypeError):
            txns_1h = 0
        
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
        # Handle dict/string values safely
        try:
            liquidity_usd = float(token.get('liquidity_usd', 0)) if not isinstance(token.get('liquidity_usd', 0), dict) else 0
        except (ValueError, TypeError):
            liquidity_usd = 0
        
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