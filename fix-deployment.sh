#!/bin/bash

# 🔧 Fix Fly.io Deployment Issues
# This script diagnoses and fixes common deployment problems

echo "🔧 MemeBot Deployment Fixer"
echo "============================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if flyctl is available
if ! command -v flyctl >/dev/null 2>&1; then
    print_error "flyctl not found. Please install Fly.io CLI first."
    echo ""
    echo "💻 Installation:"
    echo "  # Linux/WSL:"
    echo "  curl -L https://fly.io/install.sh | sh"
    echo "  # Windows:"
    echo "  iwr https://fly.io/install.ps1 -useb | iex"
    echo ""
    exit 1
fi

print_status "Checking deployment status..."

# Check if app exists
if ! flyctl status 2>/dev/null | grep -q "app"; then
    print_error "App not found or not deployed yet"
    echo ""
    print_status "Deploy the app first:"
    echo "  ./one-click-deploy.sh"
    exit 1
fi

# Get current app name
APP_NAME=$(grep "^app" fly.toml | cut -d'"' -f2)
print_status "Found app: $APP_NAME"

# Check secrets
print_status "Checking secrets configuration..."
echo ""

# Check if secrets are set
SECRETS=$(flyctl secrets list 2>/dev/null || echo "")

if echo "$SECRETS" | grep -q "TELEGRAM_TOKEN"; then
    print_success "✅ TELEGRAM_TOKEN is configured"
else
    print_error "❌ TELEGRAM_TOKEN not found in secrets"
    echo ""
    print_status "To fix this:"
    read -p "Enter your Telegram Bot Token: " BOT_TOKEN
    
    if [[ -n "$BOT_TOKEN" ]]; then
        if flyctl secrets set TELEGRAM_TOKEN="$BOT_TOKEN"; then
            print_success "✅ TELEGRAM_TOKEN set successfully"
        else
            print_error "Failed to set TELEGRAM_TOKEN"
            exit 1
        fi
    else
        print_error "Bot token cannot be empty"
        exit 1
    fi
fi

if echo "$SECRETS" | grep -q "OWNER_ID"; then
    print_success "✅ OWNER_ID is configured"
else
    print_error "❌ OWNER_ID not found in secrets"
    echo ""
    print_status "To get your Telegram User ID:"
    print_status "1. Send a message to @userinfobot on Telegram"
    print_status "2. Copy the User ID it shows"
    echo ""
    read -p "Enter your Telegram User ID: " OWNER_ID
    
    if [[ -n "$OWNER_ID" ]] && [[ "$OWNER_ID" =~ ^[0-9]+$ ]]; then
        if flyctl secrets set OWNER_ID="$OWNER_ID"; then
            print_success "✅ OWNER_ID set successfully"
        else
            print_error "Failed to set OWNER_ID"
            exit 1
        fi
    else
        print_error "Owner ID must be a valid number"
        exit 1
    fi
fi

# Check for optional Solana wallet
if ! echo "$SECRETS" | grep -q "SOLANA_PRIVATE_KEY"; then
    print_warning "⚠️ SOLANA_PRIVATE_KEY not configured (paper trading only)"
    echo ""
    read -p "Configure Solana wallet for real trading? [y/N]: " SETUP_WALLET
    
    if [[ "$SETUP_WALLET" =~ ^[Yy]$ ]]; then
        print_warning "⚠️ WARNING: Only use wallets you trust and understand the risks!"
        read -p "Enter your Solana private key (Base58 encoded): " WALLET_KEY
        
        if [[ -n "$WALLET_KEY" ]]; then
            if flyctl secrets set SOLANA_PRIVATE_KEY="$WALLET_KEY"; then
                print_success "✅ SOLANA_PRIVATE_KEY set successfully"
            else
                print_error "Failed to set SOLANA_PRIVATE_KEY"
            fi
        else
            print_warning "Skipping wallet configuration"
        fi
    else
        print_status "Keeping paper trading mode"
    fi
fi

print_status "Redeploying with updated configuration..."
echo ""

# Restart the app to pick up new secrets
if flyctl deploy --strategy=restart; then
    print_success "✅ App redeployed successfully!"
    echo ""
    
    print_status "Checking app logs..."
    echo "=============================="
    flyctl logs --lines=20
    echo "=============================="
    echo ""
    
    print_success "🎉 Deployment fix complete!"
    print_status "Your bot should now be working. Check logs with:"
    echo "  flyctl logs --follow"
    
    echo ""
    print_status "📱 Test your bot:"
    echo "  1. Start a chat with your bot on Telegram"
    echo "  2. Send /start command"
    echo "  3. You should see the command menu"
    
else
    print_error "❌ Deployment failed"
    echo ""
    print_status "Debug steps:"
    echo "  1. Check logs: flyctl logs"
    echo "  2. Check app status: flyctl status"
    echo "  3. Manual deploy: flyctl deploy"
    exit 1
fi