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
    
    async def scan_new_tokens(self, chain: str = "solana") -> List[Dict]:
        """Scan for new tokens on specified chain"""
        try:
            session = await self.get_session()
            
            # Get recent pairs with high volume
            url = f"{self.base_url}/pairs/{chain}?order=txns24h&limit=100"
            
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"DexScreener API error: {response.status}")
                    return []
                
                data = await response.json()
                pairs = data.get('pairs', [])
                
                # Filter for new tokens (created in last 24 hours)
                new_tokens = []
                current_time = datetime.utcnow()
                
                for pair in pairs:
                    try:
                        # Parse creation time
                        created_at = datetime.fromisoformat(
                            pair.get('pairCreatedAt', '').replace('Z', '+00:00')
                        )
                        
                        # Only include tokens created in last 24 hours
                        if (current_time - created_at) <= timedelta(hours=24):
                            token_data = self._extract_token_data(pair)
                            if self._is_valid_token(token_data):
                                new_tokens.append(token_data)
                    
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Error parsing pair data: {e}")
                        continue
                
                logger.info(f"Found {len(new_tokens)} new tokens from DexScreener")
                return sorted(new_tokens, key=lambda x: x['volume_24h'], reverse=True)
                
        except Exception as e:
            logger.error(f"Error scanning DexScreener: {e}")
            return []
    
    def _extract_token_data(self, pair: Dict) -> Dict:
        """Extract relevant token data from DexScreener pair"""
        base_token = pair.get('baseToken', {})
        
        return {
            'symbol': base_token.get('symbol', 'UNKNOWN'),
            'name': base_token.get('name', 'Unknown Token'),
            'address': base_token.get('address', ''),
            'price': float(pair.get('priceNative', 0)),
            'price_usd': float(pair.get('priceUsd', 0)),
            'volume_24h': float(pair.get('volume', {}).get('h24', 0)),
            'volume_1h': float(pair.get('volume', {}).get('h1', 0)),
            'txns_24h': int(pair.get('txns', {}).get('h24', {}).get('buys', 0) + 
                            pair.get('txns', {}).get('h24', {}).get('sells', 0)),
            'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0)),
            'price_change_1h': float(pair.get('priceChange', {}).get('h1', 0)),
            'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0)),
            'market_cap': float(pair.get('marketCap', 0)),
            'dex': pair.get('dexId', ''),
            'pair_address': pair.get('pairAddress', ''),
            'created_at': pair.get('pairCreatedAt', ''),
            'chain_id': pair.get('chainId', ''),
            'source': 'dexscreener'
        }
    
    def _is_valid_token(self, token: Dict) -> bool:
        """Filter tokens based on basic criteria"""
        # Skip if missing critical data
        if not token['address'] or not token['symbol']:
            return False
        
        # Skip obvious scams/rugs
        suspicious_symbols = ['TEST', 'SCAM', 'RUG', 'FAKE']
        if any(sus in token['symbol'].upper() for sus in suspicious_symbols):
            return False
        
        # Require minimum volume and transactions
        if token['volume_24h'] < 1000:  # Minimum $1000 24h volume
            return False
        
        if token['txns_24h'] < 50:  # Minimum 50 transactions
            return False
        
        # Require some liquidity
        if token['liquidity_usd'] < 5000:  # Minimum $5000 liquidity
            return False
        
        return True
    
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