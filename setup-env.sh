#!/bin/bash

# 🤖 MemeBot Environment Setup Script
# Sets up environment variables for use with one-click deployment

set -e

echo "🔧 MemeBot Environment Setup"
echo "============================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if .env exists
if [[ -f ".env" ]]; then
    print_status "Found existing .env file"
    echo "Current configuration:"
    grep -v "^#" .env | grep "=" | while IFS= read -r line; do
        key=$(echo "$line" | cut -d'=' -f1)
        value=$(echo "$line" | cut -d'=' -f2-)
        if [[ "$key" == *"TOKEN"* || "$key" == *"KEY"* ]]; then
            echo "  $key=${value:0:10}..."
        else
            echo "  $line"
        fi
    done
    echo ""
    
    read -p "Update existing configuration? [y/N]: " UPDATE_EXISTING
    if [[ "$UPDATE_EXISTING" != "y" && "$UPDATE_EXISTING" != "Y" ]]; then
        print_status "Loading existing configuration into environment..."
        set -a  # automatically export variables
        source .env
        set +a
        
        echo ""
        print_success "Environment variables loaded! You can now run:"
        echo "  ./one-click-deploy.sh"
        echo ""
        echo "Or export manually:"
        echo "  export TELEGRAM_TOKEN=\"$TELEGRAM_TOKEN\""
        echo "  export OWNER_ID=\"$OWNER_ID\""
        echo "  ./one-click-deploy.sh"
        exit 0
    fi
fi

print_status "Setting up new configuration..."

# Collect information
echo ""
print_status "App Configuration"
read -p "App name (default: memebot-ai): " APP_NAME
APP_NAME=${APP_NAME:-memebot-ai}

read -p "Fly.io region (default: fra): " REGION
REGION=${REGION:-fra}

echo ""
print_status "Telegram Bot Setup"
echo "1. Go to https://t.me/BotFather"
echo "2. Create a new bot with /newbot"
echo "3. Copy the bot token"
echo ""
read -p "Telegram Bot Token: " TELEGRAM_TOKEN

echo ""
echo "1. Go to https://t.me/userinfobot"
echo "2. Send /start to get your user ID"
echo ""
read -p "Your Telegram User ID: " OWNER_ID

echo ""
print_status "Trading Configuration"
read -p "Enable real trading? (DANGEROUS) [y/N]: " ENABLE_REAL
ENABLE_REAL=${ENABLE_REAL:-n}

if [[ "$ENABLE_REAL" == "y" || "$ENABLE_REAL" == "Y" ]]; then
    print_warning "⚠️  REAL TRADING ENABLED - USE AT YOUR OWN RISK!"
    echo ""
    echo "You need a Solana wallet private key in Base58 format"
    echo "You can export from Phantom: Settings → Export Private Key"
    echo ""
    read -p "Solana Private Key (Base58): " SOLANA_PRIVATE_KEY
    REAL_TRADING_ENABLED="true"
    PAPER_TRADING_ONLY="false"
else
    print_success "Paper trading mode (safe for testing)"
    SOLANA_PRIVATE_KEY=""
    REAL_TRADING_ENABLED="false"
    PAPER_TRADING_ONLY="true"
fi

echo ""
print_status "Web Dashboard"
read -p "Web admin password (default: admin123): " WEB_ADMIN_TOKEN
WEB_ADMIN_TOKEN=${WEB_ADMIN_TOKEN:-admin123}

echo ""
print_status "API Keys (Optional - press Enter to skip)"
read -p "Birdeye API Key: " BIRDEYE_API_KEY
read -p "Helius API Key: " HELIUS_API_KEY
read -p "DexScreener API Key: " DEXSCREENER_API_KEY

# Create .env file
print_status "Creating .env file..."

cat > .env << EOF
# MemeBot Configuration
# Generated on $(date)

# App Configuration
FLY_APP_NAME=$APP_NAME
FLY_REGION=$REGION

# Telegram Bot
TELEGRAM_TOKEN=$TELEGRAM_TOKEN
OWNER_ID=$OWNER_ID

# Trading Configuration
REAL_TRADING_ENABLED=$REAL_TRADING_ENABLED
PAPER_TRADING_ONLY=$PAPER_TRADING_ONLY
MAX_POSITION_SIZE_SOL=1.0
MAX_TOTAL_PORTFOLIO_SOL=10.0
MIN_CONFIDENCE_THRESHOLD=0.6
SCAN_INTERVAL_MINUTES=5

# Wallet (for real trading only)
SOLANA_PRIVATE_KEY=$SOLANA_PRIVATE_KEY

# Web Dashboard
WEB_ADMIN_TOKEN=$WEB_ADMIN_TOKEN

# API Keys (optional)
BIRDEYE_API_KEY=$BIRDEYE_API_KEY
HELIUS_API_KEY=$HELIUS_API_KEY
DEXSCREENER_API_KEY=$DEXSCREENER_API_KEY

# Safety Configuration
EMERGENCY_STOP_LOSS_PERCENT=50.0
MAX_TRADES_PER_HOUR=10

# Development
DEBUG_MODE=false
LOG_LEVEL=INFO
EOF

print_success ".env file created!"

# Export to current environment
print_status "Loading into current environment..."
set -a
source .env
set +a

print_success "Environment configured!"

echo ""
echo "📋 Next Steps:"
echo ""
echo "1. 🚀 Deploy with one-click script:"
echo "   ./one-click-deploy.sh"
echo ""
echo "2. 📦 Or deploy with GitHub Actions:"
echo "   - Fork the repository"
echo "   - Add secrets to GitHub repo settings"
echo "   - Push to main branch"
echo ""
echo "3. 🔧 Or export variables manually:"
echo "   export TELEGRAM_TOKEN=\"$TELEGRAM_TOKEN\""
echo "   export OWNER_ID=\"$OWNER_ID\""
echo "   ./one-click-deploy.sh"
echo ""

if [[ "$REAL_TRADING_ENABLED" == "true" ]]; then
    print_warning "⚠️  REMEMBER: Real trading is ENABLED!"
    print_warning "    Start with small amounts and monitor closely!"
else
    print_success "✅ Paper trading mode - safe for testing"
fi

echo ""
print_success "Setup complete! Ready to deploy 🚀"