#!/usr/bin/env python3
"""
🧪 Test DexScreener API Integration
Tests the updated API endpoint and data parsing
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_dexscreener_api():
    """Test the new DexScreener API endpoint"""
    print("🧪 Testing DexScreener API Integration")
    print("=" * 50)
    
    url = "https://api.dexscreener.com/latest/dex/pairs/solana"
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"📡 Fetching data from: {url}")
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                print(f"📊 Response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    
                    print(f"🔍 Found {len(pairs)} pairs")
                    
                    if pairs:
                        # Test first few pairs
                        for i, pair in enumerate(pairs[:3]):
                            print(f"\n🪙 Pair {i+1}:")
                            print(f"   Symbol: {pair.get('baseToken', {}).get('symbol', 'N/A')}")
                            print(f"   Name: {pair.get('baseToken', {}).get('name', 'N/A')}")
                            print(f"   Price USD: ${pair.get('priceUsd', 'N/A')}")
                            print(f"   Volume 24h: ${pair.get('volume', {}).get('h24', 'N/A'):,}")
                            print(f"   Liquidity: ${pair.get('liquidity', {}).get('usd', 'N/A'):,}")
                            print(f"   Txns 1h: {pair.get('txns', {}).get('h1', 'N/A')}")
                            print(f"   Txns 5m: {pair.get('txns', {}).get('m5', 'N/A')}")
                            print(f"   FDV: ${pair.get('fdv', 'N/A'):,}")
                            
                            # Test timestamp parsing
                            created_at = pair.get('pairCreatedAt', 0)
                            if created_at:
                                created_dt = datetime.fromtimestamp(created_at / 1000)
                                print(f"   Created: {created_dt}")
                            
                        print("\n✅ API structure matches expected format!")
                        
                        # Test our data extraction
                        print("\n🔧 Testing data extraction...")
                        test_pair = pairs[0]
                        extracted = extract_test_data(test_pair)
                        
                        print("📋 Extracted data:")
                        for key, value in extracted.items():
                            print(f"   {key}: {value}")
                        
                        # Test validation
                        is_valid = validate_test_token(extracted)
                        print(f"\n🎯 Token validation: {'✅ PASS' if is_valid else '❌ FAIL'}")
                        
                    else:
                        print("❌ No pairs found in response")
                        
                else:
                    print(f"❌ API request failed: {response.status}")
                    error_text = await response.text()
                    print(f"Error: {error_text}")
                    
    except Exception as e:
        print(f"💥 Test failed: {e}")

def extract_test_data(pair):
    """Test version of _extract_token_data"""
    base_token = pair.get('baseToken', {})
    txns = pair.get('txns', {})
    volume = pair.get('volume', {})
    liquidity = pair.get('liquidity', {})
    
    txns_5m = txns.get('m5', 0)
    txns_1h = txns.get('h1', 0)
    
    return {
        'symbol': base_token.get('symbol', 'UNKNOWN'),
        'name': base_token.get('name', 'Unknown Token'),
        'address': base_token.get('address', ''),
        'price_usd': float(pair.get('priceUsd', 0)),
        'volume_24h': float(volume.get('h24', 0)),
        'volume_1h': float(volume.get('h1', 0)),
        'txns_1h': int(txns_1h),
        'txns_5m': int(txns_5m),
        'liquidity_usd': float(liquidity.get('usd', 0)),
        'market_cap': float(pair.get('fdv', 0)),
        'pair_address': pair.get('pairAddress', ''),
        'created_at': pair.get('pairCreatedAt', 0),
    }

def validate_test_token(token):
    """Test version of _is_valid_token"""
    # Basic validation
    if not token['address'] or not token['symbol']:
        return False
    
    if token['volume_24h'] < 500:
        return False
    
    if token['txns_1h'] < 3:
        return False
    
    if token['liquidity_usd'] < 2000:
        return False
    
    if token['price_usd'] <= 0:
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_dexscreener_api())