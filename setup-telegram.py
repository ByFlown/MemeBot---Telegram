#!/usr/bin/env python3
"""
🤖 MemeBot Telegram Configuration Setup
This script helps you configure your Telegram bot properly.
"""

import os
import sys
from dotenv import load_dotenv, set_key
import requests

def print_header():
    print("🤖 MemeBot Telegram Configuration Setup")
    print("=" * 50)
    print()

def print_section(title):
    print(f"\n📋 {title}")
    print("-" * (len(title) + 5))

def get_user_id_from_username():
    """Help user get their Telegram user ID"""
    print("\n🔍 To get your Telegram User ID:")
    print("1. Start a chat with @userinfobot on Telegram")
    print("2. Send any message to the bot")
    print("3. The bot will reply with your User ID")
    print("4. Copy that number (e.g., 123456789)")
    print()

def validate_bot_token(token):
    """Validate if the bot token is working"""
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info['ok']:
                username = bot_info['result']['username']
                print(f"✅ Bot token is valid!")
                print(f"   Bot username: @{username}")
                return True
            else:
                print(f"❌ Bot token error: {bot_info.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ API request failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error validating bot token: {e}")
        return False

def main():
    print_header()
    
    # Load existing .env file if it exists
    load_dotenv()
    
    env_file = ".env"
    if not os.path.exists(env_file):
        print("📝 Creating new .env file...")
        with open(env_file, 'w') as f:
            f.write("# MemeBot Configuration\n")
    
    # Get current values
    current_token = os.getenv('TELEGRAM_TOKEN', '')
    current_owner_id = os.getenv('OWNER_ID', '')
    
    print_section("Step 1: Telegram Bot Token")
    
    if current_token and current_token != 'DEIN_TELEGRAM_BOT_TOKEN':
        print(f"Current token: {current_token[:10]}...{current_token[-10:]}")
        use_current = input("Use current bot token? [Y/n]: ").strip().lower()
        if use_current in ['', 'y', 'yes']:
            bot_token = current_token
        else:
            bot_token = None
    else:
        print("🚫 No valid bot token found.")
        bot_token = None
    
    if not bot_token:
        print("\n🤖 To create a Telegram bot:")
        print("1. Start a chat with @BotFather on Telegram")
        print("2. Send: /newbot")
        print("3. Follow the instructions to create your bot")
        print("4. Copy the bot token (looks like: 1234567890:ABCD...)")
        print()
        
        while True:
            bot_token = input("Enter your bot token: ").strip()
            if bot_token:
                if validate_bot_token(bot_token):
                    break
                else:
                    print("Please try again with a valid bot token.")
            else:
                print("Bot token cannot be empty!")
    
    # Save bot token
    set_key(env_file, 'TELEGRAM_TOKEN', bot_token)
    
    print_section("Step 2: Owner User ID")
    
    if current_owner_id and current_owner_id != '123456789':
        print(f"Current Owner ID: {current_owner_id}")
        use_current = input("Use current Owner ID? [Y/n]: ").strip().lower()
        if use_current in ['', 'y', 'yes']:
            owner_id = current_owner_id
        else:
            owner_id = None
    else:
        print("🚫 No valid Owner ID found.")
        owner_id = None
    
    if not owner_id:
        get_user_id_from_username()
        
        while True:
            owner_id = input("Enter your Telegram User ID: ").strip()
            if owner_id:
                try:
                    # Validate it's a number
                    int(owner_id)
                    break
                except ValueError:
                    print("❌ User ID must be a number!")
            else:
                print("Owner ID cannot be empty!")
    
    # Save owner ID
    set_key(env_file, 'OWNER_ID', owner_id)
    
    print_section("Step 3: Optional Configuration")
    
    # Ask about Solana wallet (optional)
    current_wallet = os.getenv('SOLANA_PRIVATE_KEY', '')
    if not current_wallet:
        print("\n💎 Solana Wallet Configuration (Optional)")
        print("For real trading, you need to configure your Solana private key.")
        print("⚠️  WARNING: Only do this if you understand the risks!")
        print()
        setup_wallet = input("Setup Solana wallet now? [y/N]: ").strip().lower()
        
        if setup_wallet in ['y', 'yes']:
            print("\n📝 To get your Solana private key:")
            print("1. Export from Phantom/Solflare (Settings > Export Private Key)")
            print("2. Or use: solana-keygen new --outfile wallet.json")
            print("3. Then: base58 encode the private key bytes")
            print()
            
            wallet_key = input("Enter your Solana private key (Base58): ").strip()
            if wallet_key:
                set_key(env_file, 'SOLANA_PRIVATE_KEY', wallet_key)
                print("✅ Wallet configuration saved!")
            else:
                print("⏭️  Skipping wallet configuration")
        else:
            print("⏭️  Skipping wallet configuration (paper trading only)")
    else:
        print("✅ Solana wallet already configured")
    
    print_section("Configuration Complete!")
    
    print("✅ Your MemeBot is now configured!")
    print(f"📁 Configuration saved to: {os.path.abspath(env_file)}")
    print()
    print("🚀 Next steps:")
    print("1. Deploy to Fly.io: ./one-click-deploy.sh")
    print("2. Or run locally: python main.py")
    print()
    print("📱 Start chatting with your bot:")
    print("   Send /start to begin")
    print("   All available commands will be shown in the menu")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Setup error: {e}")
        sys.exit(1)