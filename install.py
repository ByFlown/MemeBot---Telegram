#!/usr/bin/env python3
"""
Installation and setup script for MemeBot
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """Check Python version compatibility"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"❌ Python 3.9+ required, found {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    directories = ['models', 'logs', 'data']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   Created: {directory}/")
    
    print("✅ Directories created")

def setup_environment():
    """Setup environment file"""
    print("⚙️ Setting up environment...")
    
    if not Path('.env').exists():
        if Path('.env.example').exists():
            print("   Copying .env.example to .env...")
            subprocess.run(['cp', '.env.example', '.env'], check=True)
            print("   📝 Please edit .env file with your actual configuration!")
        else:
            print("   Creating basic .env file...")
            with open('.env', 'w') as f:
                f.write("# MemeBot Configuration\n")
                f.write("TELEGRAM_TOKEN=your_telegram_bot_token_here\n")
                f.write("OWNER_ID=your_telegram_user_id_here\n")
                f.write("PAPER_TRADING_ONLY=true\n")
                f.write("DEBUG_MODE=true\n")
        print("✅ Environment file created")
    else:
        print("✅ .env file already exists")

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    # Upgrade pip first
    if not run_command(f"{sys.executable} -m pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install requirements
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing dependencies"):
        return False
    
    return True

def verify_installation():
    """Verify that key modules can be imported"""
    print("🔍 Verifying installation...")
    
    test_imports = [
        ("telegram", "python-telegram-bot"),
        ("solana", "solana"),
        ("aiohttp", "aiohttp"),
        ("numpy", "numpy"),
        ("sklearn", "scikit-learn"),
        ("stable_baselines3", "stable-baselines3")
    ]
    
    all_good = True
    for module, package in test_imports:
        try:
            __import__(module)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - installation failed")
            all_good = False
    
    return all_good

def main():
    """Main installation process"""
    print("🤖 MemeBot Installation Script")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Setup environment
    setup_environment()
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Dependency installation failed!")
        sys.exit(1)
    
    # Verify installation
    if not verify_installation():
        print("❌ Installation verification failed!")
        sys.exit(1)
    
    print("\n🎉 Installation completed successfully!")
    print("\n📝 Next steps:")
    print("1. Edit .env file with your Telegram bot token and settings")
    print("2. Run: python main.py (or python watchdog.py for auto-restart)")
    print("3. Start with paper trading first (PAPER_TRADING_ONLY=true)")
    print("\n🚨 Remember: Only use money you can afford to lose!")

if __name__ == "__main__":
    main()