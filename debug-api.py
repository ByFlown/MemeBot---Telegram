#!/usr/bin/env python3
"""
Debug DexScreener API to see actual response structure
"""
import asyncio
import aiohttp
import json

async def test_api():
    """Test the exact API calls our scanner makes"""
    print("🧪 Testing DexScreener API calls...")
    
    search_queries = [
        "SOL", "USDC", "USDT",  # Major tokens
        "raydium", "orca", "jupiter",  # Major DEXes
        "meme", "dog", "cat", "pepe",  # Meme categories  
        "new", "launch", "token",  # New launches
        "moon", "safe", "diamond",  # Common meme terms
        "pump", "gem", "x100"  # High-risk terms
    ]
    
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        headers={'User-Agent': 'MemeBot/1.0'}
    ) as session:
        
        for query in search_queries[:3]:  # Test first 3 only
            try:
                search_url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
                print(f"\n🔍 Testing query: {query}")
                print(f"URL: {search_url}")
                
                async with session.get(search_url) as response:
                    print(f"Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        pairs = data.get('pairs', [])
                        print(f"Total pairs found: {len(pairs)}")
                        
                        # Filter for Solana
                        solana_pairs = [p for p in pairs if p.get('chainId') == 'solana']
                        print(f"Solana pairs: {len(solana_pairs)}")
                        
                        if solana_pairs:
                            # Show first solana pair structure
                            sample = solana_pairs[0]
                            print(f"\n📋 Sample Solana pair structure:")
                            print(f"Symbol: {sample.get('baseToken', {}).get('symbol', 'N/A')}")
                            print(f"Address: {sample.get('baseToken', {}).get('address', 'N/A')}")
                            print(f"Price USD: {sample.get('priceUsd', 'N/A')}")
                            print(f"Chain ID: {sample.get('chainId', 'N/A')}")
                            print(f"Pair Address: {sample.get('pairAddress', 'N/A')}")
                            print(f"Volume 24h: {sample.get('volume', {}).get('h24', 'N/A')}")
                            print(f"Liquidity: {sample.get('liquidity', {}).get('usd', 'N/A')}")
                            print(f"Created At: {sample.get('pairCreatedAt', 'N/A')}")
                            
                            # Show full structure (truncated)
                            print(f"\n🔬 Full structure (first 800 chars):")
                            print(json.dumps(sample, indent=2)[:800] + "...")
                        else:
                            print("❌ No Solana pairs found")
                    else:
                        error_text = await response.text()
                        print(f"❌ Error: {response.status} - {error_text[:200]}")
                
                await asyncio.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"💥 Query '{query}' failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())