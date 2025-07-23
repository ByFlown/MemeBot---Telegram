import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Tuple
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class OnchainAnalyzer:
    def __init__(self):
        # Solana RPC endpoints (use your preferred RPC provider)
        self.rpc_endpoints = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-api.projectserum.com",
            "https://rpc.ankr.com/solana"
        ]
        self.current_rpc = 0
        self.session = None
        
        # API endpoints for additional data
        self.solscan_api = "https://public-api.solscan.io"
        self.birdeye_api = "https://public-api.birdeye.so"
        self.helius_api = "https://api.helius.xyz/v0"  # Add your API key if available
        
    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'MemeBot-OnchainAnalyzer/1.0'}
            )
        return self.session
    
    async def get_rpc_client(self) -> AsyncClient:
        """Get Solana RPC client with failover"""
        endpoint = self.rpc_endpoints[self.current_rpc]
        try:
            client = AsyncClient(endpoint)
            await client.__aenter__()
            return client
        except Exception as e:
            logger.warning(f"RPC endpoint {endpoint} failed: {e}")
            self.current_rpc = (self.current_rpc + 1) % len(self.rpc_endpoints)
            try:
                client = AsyncClient(self.rpc_endpoints[self.current_rpc])
                await client.__aenter__()
                return client
            except Exception as e:
                logger.error(f"All RPC endpoints failed: {e}")
                raise
    
    async def analyze_token(self, token_address: str) -> Dict:
        """Comprehensive onchain analysis of a token"""
        try:
            # Run all analysis in parallel for better performance
            results = await asyncio.gather(
                self._get_token_info(token_address),
                self._analyze_holders(token_address),
                self._analyze_liquidity(token_address),
                self._analyze_dev_activity(token_address),
                self._get_social_metrics(token_address),
                return_exceptions=True
            )
            
            # Combine all results
            analysis = {
                'token_info': results[0] if not isinstance(results[0], Exception) else {},
                'holder_analysis': results[1] if not isinstance(results[1], Exception) else {},
                'liquidity_analysis': results[2] if not isinstance(results[2], Exception) else {},
                'dev_analysis': results[3] if not isinstance(results[3], Exception) else {},
                'social_metrics': results[4] if not isinstance(results[4], Exception) else {},
                'risk_score': 0.0,
                'confidence_score': 0.0
            }
            
            # Calculate risk and confidence scores
            analysis['risk_score'] = self._calculate_risk_score(analysis)
            analysis['confidence_score'] = self._calculate_confidence_score(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing token {token_address}: {e}")
            return self._empty_analysis()
    
    async def _get_token_info(self, token_address: str) -> Dict:
        """Get basic token information"""
        try:
            session = await self.get_session()
            
            # Get token metadata from Solscan
            url = f"{self.solscan_api}/token/meta?tokenAddress={token_address}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'name': data.get('name', ''),
                        'symbol': data.get('symbol', ''),
                        'decimals': data.get('decimals', 9),
                        'supply': float(data.get('supply', 0)),
                        'holder_count': int(data.get('holder', 0)),
                        'created_time': data.get('createdTime', ''),
                        'website': data.get('website', ''),
                        'twitter': data.get('twitter', ''),
                        'telegram': data.get('telegram', '')
                    }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return {}
    
    async def _analyze_holders(self, token_address: str) -> Dict:
        """Analyze token holder distribution"""
        try:
            session = await self.get_session()
            
            # Get holder distribution from Solscan
            url = f"{self.solscan_api}/token/holders?tokenAddress={token_address}&limit=100"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    holders = data.get('data', [])
                    
                    if not holders:
                        return {'holder_concentration': 100, 'top_10_percentage': 100}
                    
                    total_supply = sum(float(h.get('amount', 0)) for h in holders)
                    top_10_amount = sum(float(h.get('amount', 0)) for h in holders[:10])
                    
                    return {
                        'total_holders': len(holders),
                        'top_10_percentage': (top_10_amount / total_supply * 100) if total_supply > 0 else 100,
                        'holder_concentration': self._calculate_holder_concentration(holders),
                        'whale_wallets': len([h for h in holders if float(h.get('amount', 0)) / total_supply > 0.05])
                    }
            
            return {'holder_concentration': 50, 'top_10_percentage': 50}
            
        except Exception as e:
            logger.error(f"Error analyzing holders: {e}")
            return {'holder_concentration': 50, 'top_10_percentage': 50}
    
    async def _analyze_liquidity(self, token_address: str) -> Dict:
        """Analyze liquidity and trading patterns"""
        try:
            session = await self.get_session()
            
            # Get liquidity info from Birdeye or similar
            url = f"{self.birdeye_api}/defi/token_overview?address={token_address}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    token_data = data.get('data', {})
                    
                    return {
                        'liquidity_usd': float(token_data.get('liquidity', 0)),
                        'volume_24h': float(token_data.get('v24hUSD', 0)),
                        'price_change_24h': float(token_data.get('priceChange24hPercent', 0)),
                        'market_cap': float(token_data.get('mc', 0)),
                        'is_liquidity_locked': False,  # Would need specific LP lock detection
                        'pool_count': len(token_data.get('pools', []))
                    }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error analyzing liquidity: {e}")
            return {}
    
    async def _analyze_dev_activity(self, token_address: str) -> Dict:
        """Analyze developer wallet activity and behavior"""
        try:
            # This would require more sophisticated analysis of the token's creation
            # and developer wallet transactions
            rpc_client = await self.get_rpc_client()
            
            try:
                # Get token account info
                pubkey = Pubkey.from_string(token_address)
                account_info = await rpc_client.get_account_info(pubkey)
                
                if account_info.value:
                    return {
                        'mint_authority_renounced': False,  # Would need to parse account data
                        'freeze_authority_renounced': False,
                        'dev_wallet_activity_score': 5.0,  # Placeholder scoring
                        'recent_dev_transactions': 0
                    }
                
                return {}
                
            finally:
                await rpc_client.__aexit__(None, None, None)
            
        except Exception as e:
            logger.error(f"Error analyzing dev activity: {e}")
            return {}
    
    async def _get_social_metrics(self, token_address: str) -> Dict:
        """Get social media metrics and community engagement"""
        try:
            # This would integrate with Twitter API, Telegram API, etc.
            # For now, return placeholder data
            return {
                'twitter_followers': 0,
                'telegram_members': 0,
                'social_sentiment_score': 5.0,
                'community_activity_score': 5.0,
                'influencer_mentions': 0
            }
            
        except Exception as e:
            logger.error(f"Error getting social metrics: {e}")
            return {}
    
    def _calculate_holder_concentration(self, holders: List[Dict]) -> float:
        """Calculate holder concentration (Gini coefficient approximation)"""
        if not holders:
            return 100
        
        amounts = [float(h.get('amount', 0)) for h in holders]
        amounts.sort()
        
        n = len(amounts)
        cumulative = sum((2 * (i + 1) - n - 1) * amount for i, amount in enumerate(amounts))
        total_amount = sum(amounts)
        
        if total_amount == 0:
            return 100
        
        gini = cumulative / (n * total_amount)
        return gini * 100  # Convert to percentage
    
    def _calculate_risk_score(self, analysis: Dict) -> float:
        """Calculate overall risk score (0-10, higher = riskier)"""
        risk_score = 5.0  # Base risk
        
        # Holder concentration risk
        holder_data = analysis.get('holder_analysis', {})
        top_10_pct = holder_data.get('top_10_percentage', 50)
        if top_10_pct > 80:
            risk_score += 2.0
        elif top_10_pct > 60:
            risk_score += 1.0
        
        # Liquidity risk
        liquidity_data = analysis.get('liquidity_analysis', {})
        liquidity_usd = liquidity_data.get('liquidity_usd', 0)
        if liquidity_usd < 10000:
            risk_score += 2.0
        elif liquidity_usd < 50000:
            risk_score += 1.0
        
        # Dev activity risk
        dev_data = analysis.get('dev_analysis', {})
        if not dev_data.get('mint_authority_renounced', False):
            risk_score += 1.5
        if not dev_data.get('freeze_authority_renounced', False):
            risk_score += 1.0
        
        return min(risk_score, 10.0)
    
    def _calculate_confidence_score(self, analysis: Dict) -> float:
        """Calculate confidence in the analysis (0-10, higher = more confident)"""
        confidence = 5.0  # Base confidence
        
        # More data = higher confidence
        if analysis.get('token_info', {}).get('holder_count', 0) > 1000:
            confidence += 1.0
        
        if analysis.get('liquidity_analysis', {}).get('volume_24h', 0) > 100000:
            confidence += 1.0
        
        if analysis.get('social_metrics', {}).get('twitter_followers', 0) > 1000:
            confidence += 0.5
        
        return min(confidence, 10.0)
    
    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure"""
        return {
            'token_info': {},
            'holder_analysis': {'holder_concentration': 50, 'top_10_percentage': 50},
            'liquidity_analysis': {},
            'dev_analysis': {},
            'social_metrics': {},
            'risk_score': 7.0,  # High risk for unknown tokens
            'confidence_score': 1.0  # Low confidence
        }
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()