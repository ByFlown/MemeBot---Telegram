#!/usr/bin/env python3
"""
🧪 MemeBot Deployment Test
Simple test to check if the app can start without crashing
"""

import sys
import os
import asyncio
from datetime import datetime

print(f"🧪 MemeBot Deployment Test - {datetime.now()}")
print("=" * 50)

def test_imports():
    """Test all critical imports"""
    print("📦 Testing imports...")
    
    try:
        print("   ✅ Basic Python modules")
        import json, logging, time, threading
        
        print("   ✅ Async modules") 
        import asyncio
        from datetime import datetime, timedelta
        
        print("   ✅ HTTP modules")
        from aiohttp import web, ClientSession
        
        print("   ✅ Environment modules")
        from dotenv import load_dotenv
        
        print("   ✅ Telegram modules")
        from telegram import Update, BotCommand
        from telegram.ext import Application, CommandHandler, ContextTypes
        
        print("   ✅ Scheduler modules")
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        
        print("   ✅ Data modules")
        import numpy as np
        import pandas as pd
        
        print("   ✅ AI/ML modules")
        import sklearn
        import stable_baselines3
        import gymnasium
        
        print("   ✅ Solana modules")
        import solana
        import solders
        
        print("   ✅ Config module")
        from config import TELEGRAM_TOKEN, OWNER_ID
        
        return True
        
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"   💥 Unexpected error: {e}")
        return False

def test_config():
    """Test configuration"""
    print("\n⚙️ Testing configuration...")
    
    try:
        from config import TELEGRAM_TOKEN, OWNER_ID
        
        print(f"   TELEGRAM_TOKEN: {'✅ Set' if TELEGRAM_TOKEN != 'DEIN_TELEGRAM_BOT_TOKEN' else '❌ Not set'}")
        print(f"   OWNER_ID: {OWNER_ID}")
        print(f"   FLY_APP_NAME: {os.getenv('FLY_APP_NAME', 'Not set (local)')}")
        print(f"   PORT: {os.getenv('PORT', '8080')}")
        
        return True
        
    except Exception as e:
        print(f"   💥 Config error: {e}")
        return False

def test_module_loading():
    """Test loading our modules"""
    print("\n🔧 Testing module loading...")
    
    modules_to_test = [
        "src.scanner",
        "src.onchain_analyzer", 
        "src.ai_trader",
        "src.wallet_manager",
        "src.backtester",
        "src.logger",
        "src.performance_monitor",
        "src.web_interface"
    ]
    
    success_count = 0
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"   ✅ {module_name}")
            success_count += 1
        except ImportError as e:
            print(f"   ❌ {module_name}: {e}")
        except Exception as e:
            print(f"   ⚠️  {module_name}: {e}")
    
    print(f"\n📊 Module loading: {success_count}/{len(modules_to_test)} successful")
    return success_count == len(modules_to_test)

async def test_async_functionality():
    """Test basic async functionality"""
    print("\n🔄 Testing async functionality...")
    
    try:
        # Simple async test
        await asyncio.sleep(0.1)
        print("   ✅ Asyncio working")
        
        # Test aiohttp
        from aiohttp import web
        app = web.Application()
        print("   ✅ aiohttp working")
        
        return True
        
    except Exception as e:
        print(f"   💥 Async error: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting deployment tests...\n")
    
    # Run tests
    import_success = test_imports()
    config_success = test_config()
    module_success = test_module_loading()
    async_success = await test_async_functionality()
    
    print("\n📋 Test Results:")
    print("=" * 30)
    print(f"Imports:        {'✅ PASS' if import_success else '❌ FAIL'}")
    print(f"Configuration:  {'✅ PASS' if config_success else '❌ FAIL'}")
    print(f"Module Loading: {'✅ PASS' if module_success else '❌ FAIL'}")
    print(f"Async Funcs:    {'✅ PASS' if async_success else '❌ FAIL'}")
    
    all_tests_passed = all([import_success, config_success, module_success, async_success])
    
    print(f"\n{'🎉 ALL TESTS PASSED!' if all_tests_passed else '💥 SOME TESTS FAILED!'}")
    
    if os.getenv('FLY_APP_NAME'):
        print("\n🛫 Running on Fly.io - keeping container alive...")
        print(f"   App Name: {os.getenv('FLY_APP_NAME')}")
        print(f"   Region: {os.getenv('FLY_REGION', 'unknown')}")
        
        # Keep container alive for debugging
        while True:
            print(f"🕐 {datetime.now()}: Test container still running...")
            await asyncio.sleep(300)  # 5 minutes
    else:
        print("\n🏠 Running locally - test complete!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled by user")
    except Exception as e:
        print(f"\n💥 Test crashed: {e}")
        
        # Keep alive on Fly.io for debugging
        if os.getenv('FLY_APP_NAME'):
            print("🛫 Keeping container alive for debugging...")
            import time
            while True:
                time.sleep(300)