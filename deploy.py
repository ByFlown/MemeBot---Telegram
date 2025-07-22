#!/usr/bin/env python3
"""
Fly.io deployment script for MemeBot
"""

import subprocess
import sys
import os
import json
from pathlib import Path

def run_command(command, description, check=True):
    """Run a command and handle errors"""
    print(f"🚀 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr and not check:
            print(f"Warning: {result.stderr}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False

def check_flyctl():
    """Check if flyctl is installed"""
    print("🔍 Checking flyctl installation...")
    if not run_command("flyctl version", "Checking flyctl version", check=False):
        print("❌ flyctl not found. Please install it first:")
        print("   curl -L https://fly.io/install.sh | sh")
        return False
    print("✅ flyctl is installed")
    return True

def check_login():
    """Check if user is logged in to fly.io"""
    print("🔍 Checking fly.io authentication...")
    if not run_command("flyctl auth whoami", "Checking authentication", check=False):
        print("❌ Not logged in to fly.io")
        print("   Please run: flyctl auth login")
        return False
    print("✅ Authenticated with fly.io")
    return True

def create_volumes():
    """Create persistent volumes for data, models, and logs"""
    print("💾 Creating persistent volumes...")
    
    volumes = [
        ("memebot_data", "data", 1),
        ("memebot_models", "models", 2), 
        ("memebot_logs", "logs", 1)
    ]
    
    for volume_name, description, size_gb in volumes:
        print(f"   Creating {volume_name} ({size_gb}GB) for {description}...")
        command = f"flyctl volumes create {volume_name} --size {size_gb}"
        if not run_command(command, f"Creating {volume_name} volume", check=False):
            print(f"   Volume {volume_name} might already exist, continuing...")
    
    print("✅ Volumes created/verified")

def set_secrets():
    """Set environment secrets"""
    print("🔐 Setting up secrets...")
    
    # Check if .env exists
    if not Path('.env').exists():
        print("❌ .env file not found. Please create it first:")
        print("   cp .env.example .env")
        print("   # Then edit .env with your values")
        return False
    
    # Read .env file
    secrets = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if value and value != 'your_telegram_bot_token_here':
                        secrets[key] = value
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return False
    
    if not secrets:
        print("❌ No valid secrets found in .env file")
        return False
    
    # Set secrets
    for key, value in secrets.items():
        command = f"flyctl secrets set {key}='{value}'"
        if not run_command(command, f"Setting secret {key}", check=False):
            print(f"   Failed to set {key}, continuing...")
    
    print("✅ Secrets configured")
    return True

def deploy_app():
    """Deploy the application"""
    print("🚀 Deploying MemeBot to Fly.io...")
    
    if not run_command("flyctl deploy", "Deploying application"):
        return False
    
    print("✅ Deployment completed")
    return True

def check_deployment():
    """Check if deployment was successful"""
    print("🔍 Checking deployment status...")
    
    if not run_command("flyctl status", "Checking app status"):
        return False
    
    print("🔍 Checking app logs...")
    run_command("flyctl logs --lines=20", "Getting recent logs", check=False)
    
    return True

def main():
    """Main deployment process"""
    print("🤖 MemeBot Fly.io Deployment Script")
    print("=" * 50)
    
    # Pre-deployment checks
    if not check_flyctl():
        sys.exit(1)
    
    if not check_login():
        sys.exit(1)
    
    # Check if app exists
    print("🔍 Checking if app exists...")
    if not run_command("flyctl status", "Checking app status", check=False):
        print("📝 App doesn't exist, creating it...")
        app_name = input("Enter app name (or press Enter for 'memebot-ai'): ").strip()
        if not app_name:
            app_name = "memebot-ai"
        
        command = f"flyctl apps create {app_name}"
        if not run_command(command, f"Creating app {app_name}"):
            sys.exit(1)
    
    # Create volumes
    create_volumes()
    
    # Set secrets
    if not set_secrets():
        print("⚠️  Warning: Secrets not configured. Bot may not work properly.")
        response = input("Continue anyway? (y/N): ").lower()
        if response != 'y':
            sys.exit(1)
    
    # Deploy
    if not deploy_app():
        sys.exit(1)
    
    # Check deployment
    check_deployment()
    
    print("\n🎉 Deployment completed successfully!")
    print("\n📋 Next steps:")
    print("1. Check logs: flyctl logs")
    print("2. Monitor status: flyctl status")
    print("3. Scale if needed: flyctl scale count 1")
    print("4. Test your bot in Telegram")
    print("\n🔗 Useful commands:")
    print("- flyctl ssh console    # SSH into the container")
    print("- flyctl logs --follow  # Follow logs in real-time")
    print("- flyctl secrets list   # List configured secrets")
    print("- flyctl volumes list   # List volumes")

if __name__ == "__main__":
    main()