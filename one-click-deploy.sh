#!/bin/bash

# 🤖 MemeBot One-Click Deployment Script
# Deploy to Fly.io without needing Python/pip locally

set -e

echo "🚀 MemeBot One-Click Deployment to Fly.io"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if flyctl is installed
check_flyctl() {
    print_status "Checking for flyctl CLI..."
    
    if ! command -v flyctl &> /dev/null; then
        print_warning "flyctl not found. Installing..."
        
        # Detect OS and install
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            curl -L https://fly.io/install.sh | sh
            export PATH="$HOME/.fly/bin:$PATH"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            if command -v brew &> /dev/null; then
                brew install flyctl
            else
                curl -L https://fly.io/install.sh | sh
                export PATH="$HOME/.fly/bin:$PATH"
            fi
        elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
            print_error "Please install flyctl for Windows:"
            print_error "Run in PowerShell: iwr https://fly.io/install.ps1 -useb | iex"
            exit 1
        else
            print_error "Unsupported OS: $OSTYPE"
            exit 1
        fi
    fi
    
    print_success "flyctl is available"
}

# Check authentication
check_auth() {
    print_status "Checking Fly.io authentication..."
    
    if ! flyctl auth whoami &> /dev/null; then
        print_warning "Not authenticated with Fly.io"
        print_status "Opening login page..."
        flyctl auth login
    fi
    
    print_success "Authenticated with Fly.io"
}

# Check for existing environment variables or config files
load_existing_config() {
    print_status "Checking for existing configuration..."
    
    # Try to load from .env file
    if [[ -f ".env" ]]; then
        print_success "Found .env file, loading configuration..."
        source .env
        LOADED_FROM_ENV=true
    else
        LOADED_FROM_ENV=false
    fi
    
    # Check for environment variables (from GitHub Actions or manual export)
    if [[ -n "$TELEGRAM_TOKEN" && -n "$OWNER_ID" ]]; then
        print_success "Found configuration in environment variables"
        LOADED_FROM_ENV=true
    fi
    
    # Set defaults from environment if available
    APP_NAME=${FLY_APP_NAME:-${APP_NAME:-memebot-ai}}
    REGION=${FLY_REGION:-${REGION:-fra}}
    TELEGRAM_TOKEN=${TELEGRAM_TOKEN:-}
    OWNER_ID=${OWNER_ID:-}
    SOLANA_PRIVATE_KEY=${SOLANA_PRIVATE_KEY:-}
    REAL_TRADING_ENABLED=${REAL_TRADING_ENABLED:-false}
    WEB_ADMIN_TOKEN=${WEB_ADMIN_TOKEN:-admin123}
    BIRDEYE_API_KEY=${BIRDEYE_API_KEY:-}
    HELIUS_API_KEY=${HELIUS_API_KEY:-}
    DEXSCREENER_API_KEY=${DEXSCREENER_API_KEY:-}
}

# Collect required information (with smart defaults)
collect_info() {
    print_status "Collecting deployment information..."
    echo ""
    
    # Show current config if loaded
    if [[ "$LOADED_FROM_ENV" == "true" ]]; then
        print_success "Using existing configuration:"
        echo "  App Name: $APP_NAME"
        echo "  Region: $REGION"
        echo "  Telegram Token: ${TELEGRAM_TOKEN:0:10}..." 
        echo "  Owner ID: $OWNER_ID"
        echo "  Real Trading: $REAL_TRADING_ENABLED"
        echo ""
        
        read -p "Use this configuration? [Y/n]: " USE_EXISTING
        USE_EXISTING=${USE_EXISTING:-y}
        
        if [[ "$USE_EXISTING" == "y" || "$USE_EXISTING" == "Y" ]]; then
            # Validate required fields
            if [[ -z "$TELEGRAM_TOKEN" || -z "$OWNER_ID" ]]; then
                print_warning "Missing required configuration, will prompt for missing values"
            else
                print_success "Using existing configuration"
                return
            fi
        fi
    fi
    
    # App name
    if [[ -z "$APP_NAME" ]]; then
        read -p "Enter app name (default: memebot-ai): " INPUT_APP_NAME
        APP_NAME=${INPUT_APP_NAME:-memebot-ai}
    fi
    
    # Region  
    if [[ -z "$REGION" ]]; then
        echo "Available regions:"
        echo "  fra - Frankfurt, Germany"
        echo "  iad - Washington D.C., USA" 
        echo "  sin - Singapore"
        echo "  syd - Sydney, Australia"
        read -p "Enter region (default: fra): " INPUT_REGION
        REGION=${INPUT_REGION:-fra}
    fi
    
    # Telegram configuration
    if [[ -z "$TELEGRAM_TOKEN" ]]; then
        echo ""
        print_status "Telegram Bot Configuration"
        echo "Create a bot at: https://t.me/BotFather"
        read -p "Enter your Telegram Bot Token: " TELEGRAM_TOKEN
    fi
    
    if [[ -z "$TELEGRAM_TOKEN" ]]; then
        print_error "Telegram token is required!"
        exit 1
    fi
    
    if [[ -z "$OWNER_ID" ]]; then
        read -p "Enter your Telegram User ID: " OWNER_ID
    fi
    
    if [[ -z "$OWNER_ID" ]]; then
        print_error "Owner ID is required!"
        exit 1
    fi
    
    # Trading configuration
    if [[ -z "$REAL_TRADING_ENABLED" || "$REAL_TRADING_ENABLED" == "false" ]]; then
        echo ""
        print_status "Trading Configuration"
        read -p "Enable real trading? (DANGEROUS - start with 'n') [y/N]: " ENABLE_REAL_TRADING
        ENABLE_REAL_TRADING=${ENABLE_REAL_TRADING:-n}
        
        if [[ "$ENABLE_REAL_TRADING" == "y" || "$ENABLE_REAL_TRADING" == "Y" ]]; then
            print_warning "Real trading enabled! Make sure you understand the risks."
            if [[ -z "$SOLANA_PRIVATE_KEY" ]]; then
                read -p "Enter Solana private key (Base58): " SOLANA_PRIVATE_KEY
            fi
            REAL_TRADING_ENABLED="true"
        else
            print_success "Paper trading mode (safe for testing)"
            SOLANA_PRIVATE_KEY=""
            REAL_TRADING_ENABLED="false"
        fi
    fi
    
    # Web interface
    if [[ "$WEB_ADMIN_TOKEN" == "admin123" ]]; then
        read -p "Enter web admin token (default: admin123): " INPUT_WEB_TOKEN
        WEB_ADMIN_TOKEN=${INPUT_WEB_TOKEN:-admin123}
    fi
    
    echo ""
    print_success "Configuration collected"
}

# Create or get app
setup_app() {
    print_status "Setting up Fly.io app..."
    
    # Check if app exists
    if flyctl apps list | grep -q "$APP_NAME"; then
        print_success "App '$APP_NAME' already exists"
    else
        print_status "Creating app '$APP_NAME'..."
        flyctl apps create "$APP_NAME" --org personal
        print_success "App created"
    fi
    
    # Update fly.toml with app name
    sed -i.bak "s/app = \"memebot-ai\"/app = \"$APP_NAME\"/" fly.toml
    sed -i.bak "s/primary_region = \"fra\"/primary_region = \"$REGION\"/" fly.toml
    
    print_success "App configuration updated"
}

# Create volumes
create_volumes() {
    print_status "Creating persistent volumes..."
    
    # Create volumes with error handling
    flyctl volumes create memebot_models --app "$APP_NAME" --region "$REGION" --size 3 2>/dev/null || print_warning "Models volume might already exist"
    flyctl volumes create memebot_logs --app "$APP_NAME" --region "$REGION" --size 2 2>/dev/null || print_warning "Logs volume might already exist"
    flyctl volumes create memebot_data --app "$APP_NAME" --region "$REGION" --size 1 2>/dev/null || print_warning "Data volume might already exist"
    
    print_success "Volumes created/verified"
}

# Set secrets
set_secrets() {
    print_status "Setting application secrets..."
    
    # Core secrets
    flyctl secrets set \
        TELEGRAM_TOKEN="$TELEGRAM_TOKEN" \
        OWNER_ID="$OWNER_ID" \
        REAL_TRADING_ENABLED="$REAL_TRADING_ENABLED" \
        PAPER_TRADING_ONLY="$([ "$REAL_TRADING_ENABLED" = "true" ] && echo "false" || echo "true")" \
        WEB_ADMIN_TOKEN="$WEB_ADMIN_TOKEN" \
        --app "$APP_NAME"
    
    # Optional secrets
    if [[ -n "$SOLANA_PRIVATE_KEY" ]]; then
        flyctl secrets set SOLANA_PRIVATE_KEY="$SOLANA_PRIVATE_KEY" --app "$APP_NAME"
    fi
    
    if [[ -n "$BIRDEYE_API_KEY" ]]; then
        flyctl secrets set BIRDEYE_API_KEY="$BIRDEYE_API_KEY" --app "$APP_NAME"
    fi
    
    if [[ -n "$HELIUS_API_KEY" ]]; then
        flyctl secrets set HELIUS_API_KEY="$HELIUS_API_KEY" --app "$APP_NAME"
    fi
    
    if [[ -n "$DEXSCREENER_API_KEY" ]]; then
        flyctl secrets set DEXSCREENER_API_KEY="$DEXSCREENER_API_KEY" --app "$APP_NAME"
    fi
    
    # Deployment info
    flyctl secrets set \
        DEPLOYMENT_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        DEPLOYMENT_METHOD="one-click" \
        --app "$APP_NAME"
    
    print_success "Secrets configured"
}

# Deploy application
deploy_app() {
    print_status "Deploying MemeBot to Fly.io..."
    print_status "This may take a few minutes..."
    
    flyctl deploy --app "$APP_NAME" --remote-only
    
    print_success "Deployment completed!"
}

# Health check
verify_deployment() {
    print_status "Verifying deployment..."
    sleep 10
    
    # Get app URL
    APP_URL="https://$(flyctl info --app "$APP_NAME" --json | grep -o '"Hostname":"[^"]*"' | cut -d'"' -f4)"
    
    print_status "App URL: $APP_URL"
    
    # Health check
    for i in {1..5}; do
        print_status "Health check attempt $i/5..."
        if curl -f "$APP_URL/health" &> /dev/null; then
            print_success "✅ Health check passed!"
            break
        else
            if [ $i -eq 5 ]; then
                print_error "❌ Health check failed"
                print_status "Check logs with: flyctl logs --app $APP_NAME"
                exit 1
            fi
            sleep 10
        fi
    done
}

# Show final information
show_completion_info() {
    APP_URL="https://$(flyctl info --app "$APP_NAME" --json | grep -o '"Hostname":"[^"]*"' | cut -d'"' -f4)"
    
    echo ""
    echo "🎉 MemeBot deployed successfully!"
    echo "================================"
    echo ""
    echo "📱 Telegram Bot: Test with /start"
    echo "🌐 Web Dashboard: $APP_URL"
    echo "🔐 Admin Token: $WEB_ADMIN_TOKEN"
    echo ""
    echo "📋 Useful commands:"
    echo "  flyctl logs --app $APP_NAME        # View logs"
    echo "  flyctl status --app $APP_NAME      # Check status"
    echo "  flyctl ssh console --app $APP_NAME # SSH access"
    echo "  flyctl apps restart $APP_NAME      # Restart app"
    echo ""
    echo "🚨 Important:"
    echo "  - Bot is in ${REAL_TRADING_ENABLED} trading mode"
    echo "  - Monitor via web dashboard or Telegram"
    echo "  - Start with small amounts if real trading"
    echo ""
    print_success "Happy trading! 🚀💎"
}

# Main execution
main() {
    print_status "Starting MemeBot deployment process..."
    
    check_flyctl
    check_auth
    load_existing_config
    collect_info
    setup_app
    create_volumes
    set_secrets
    deploy_app
    verify_deployment
    show_completion_info
}

# Handle interruption
trap 'echo ""; print_error "Deployment interrupted"; exit 1' INT

# Run main function
main