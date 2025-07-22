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
            
            # Use working DexScreener endpoints for Solana tokens
            all_pairs = []
            
            # Try direct search approaches that are known to work
            search_queries = ["SOL", "USDC", "solana"]
            
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
            
            # Filter for new tokens (created in last 24 hours)
            new_tokens = []
            current_time = datetime.utcnow()
            
            for pair in pairs:
                try:
                    # Parse creation time from timestamp
                    created_timestamp = pair.get('pairCreatedAt', 0)
                    if created_timestamp:
                        created_at = datetime.fromtimestamp(created_timestamp / 1000)  # Convert ms to seconds
                        
                        # Only include tokens created in last 24 hours
                        if (current_time - created_at) <= timedelta(hours=24):
                            token_data = self._extract_token_data(pair)
                            if self._is_valid_token(token_data):
                                new_tokens.append(token_data)
                    else:
                        # If no creation time, still process but mark as older
                        token_data = self._extract_token_data(pair)
                        if self._is_valid_token(token_data):
                            new_tokens.append(token_data)
                
                except (ValueError, TypeError) as e:
                    logger.debug(f"Error parsing pair data: {e}")
                    continue
            
            logger.info(f"Found {len(new_tokens)} new tokens from DexScreener")
            # Sort by a combination of volume and transaction activity
            return sorted(new_tokens, key=lambda x: (x['volume_24h'] * x['txns_1h']), reverse=True)
                
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
        """Filter tokens based on basic criteria"""
        # Skip if missing critical data
        if not token['address'] or not token['symbol']:
            return False
        
        # Skip obvious scams/rugs
        suspicious_symbols = ['TEST', 'SCAM', 'RUG', 'FAKE', 'HONEYPOT']
        if any(sus in token['symbol'].upper() for sus in suspicious_symbols):
            return False
        
        # Require minimum volume and transactions (adjusted for new API)
        if token['volume_24h'] < 500:  # Minimum $500 24h volume
            return False
        
        # Use 1h transactions as proxy since we have that data
        if token['txns_1h'] < 3:  # Minimum 3 transactions per hour
            return False
        
        # Require some liquidity
        if token['liquidity_usd'] < 2000:  # Minimum $2000 liquidity
            return False
        
        # Basic price validation
        if token['price_usd'] <= 0:
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