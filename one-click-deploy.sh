#!/bin/bash

# 🤖 MemeBot One-Click Deployment Script
# Deploy to Fly.io without needing Python/pip locally

# Enhanced error handling
set -euo pipefail  # Exit on error, undefined vars, pipe failures
IFS=$'\n\t'       # Secure Internal Field Separator

# Error handler function
handle_error() {
    local exit_code=$?
    local line_number=$1
    
    echo ""
    print_error "💥 DEPLOYMENT FAILED!"
    echo ""
    print_error "Error occurred on line $line_number (exit code: $exit_code)"
    print_error "Last command: ${BASH_COMMAND}"
    echo ""
    
    # Show some diagnostic information
    print_status "🔍 Diagnostic Information:"
    echo "  Script: $0"
    echo "  Working directory: $(pwd)"
    echo "  User: $(whoami)"
    echo "  Shell: $SHELL"
    echo "  Date: $(date)"
    
    # Check if flyctl is available
    if command -v flyctl &> /dev/null; then
        echo "  flyctl version: $(flyctl version 2>/dev/null || echo 'Unable to get version')"
        echo "  flyctl auth: $(flyctl auth whoami 2>/dev/null || echo 'Not authenticated')"
    else
        echo "  flyctl: Not installed"
    fi
    
    echo ""
    print_error "Common solutions:"
    echo "  1. Check your internet connection"
    echo "  2. Ensure flyctl is installed: curl -L https://fly.io/install.sh | sh"
    echo "  3. Login to fly.io: flyctl auth login"
    echo "  4. Check if .env file exists and has correct format"
    echo "  5. Verify all required environment variables are set"
    echo ""
    print_warning "Press any key to exit..."
    read -n 1 -s
    exit $exit_code
}

# Set error trap
trap 'handle_error ${LINENO}' ERR

# Also trap EXIT to prevent terminal from closing immediately
cleanup_and_exit() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo ""
        print_error "Script exited with error code: $exit_code"
        print_warning "Press any key to close terminal..."
        read -n 1 -s
    fi
    exit $exit_code
}
trap cleanup_and_exit EXIT

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
        
        # Create temp directory for installation
        local temp_dir
        temp_dir=$(mktemp -d 2>/dev/null || mktemp -d -t 'flyctl_install')
        
        # Detect OS and install
        if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
            print_status "Downloading flyctl installer..."
            if curl -fsSL https://fly.io/install.sh -o "$temp_dir/install.sh"; then
                print_status "Running installer..."
                bash "$temp_dir/install.sh"
                
                # Add to PATH for this session
                if [[ -d "$HOME/.fly/bin" ]]; then
                    export PATH="$HOME/.fly/bin:$PATH"
                fi
                
                # Verify installation
                if ! command -v flyctl &> /dev/null; then
                    print_error "Installation failed. Please install manually:"
                    if [[ "$OSTYPE" == "darwin"* ]]; then
                        print_error "brew install flyctl"
                    fi
                    print_error "Or visit: https://fly.io/docs/flyctl/install/"
                    exit 1
                fi
            else
                print_error "Failed to download installer. Please check your internet connection."
                print_error "Or install manually: https://fly.io/docs/flyctl/install/"
                exit 1
            fi
        elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
            print_error "Windows detected. Please install flyctl manually:"
            print_error "Run in PowerShell: iwr https://fly.io/install.ps1 -useb | iex"
            print_error "Or download from: https://github.com/superfly/flyctl/releases"
            exit 1
        else
            print_error "Unsupported OS: $OSTYPE"
            print_error "Please install flyctl manually: https://fly.io/docs/flyctl/install/"
            exit 1
        fi
        
        # Cleanup
        rm -rf "$temp_dir"
    fi
    
    # Verify flyctl works
    local flyctl_version
    if flyctl_version=$(flyctl version 2>&1); then
        print_success "flyctl is available: $flyctl_version"
    else
        print_error "flyctl is installed but not working properly"
        print_error "Try reinstalling: curl -L https://fly.io/install.sh | sh"
        exit 1
    fi
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
    
    # App name with validation
    while [[ -z "$APP_NAME" ]]; do
        read -p "Enter app name (default: memebot-ai): " INPUT_APP_NAME
        APP_NAME=${INPUT_APP_NAME:-memebot-ai}
        
        # Validate app name (Fly.io requirements)
        if [[ ! "$APP_NAME" =~ ^[a-z0-9-]+$ ]]; then
            print_error "Invalid app name. Use only lowercase letters, numbers, and hyphens."
            print_status "Examples: memebot-ai, my-trading-bot, solana-trader-123"
            APP_NAME=""
            continue
        fi
        
        if [[ ${#APP_NAME} -lt 3 ]]; then
            print_error "App name must be at least 3 characters long."
            APP_NAME=""
            continue
        fi
        
        if [[ ${#APP_NAME} -gt 30 ]]; then
            print_error "App name must be less than 30 characters long."
            APP_NAME=""
            continue
        fi
        
        # Check if name is available
        if command -v flyctl >/dev/null 2>&1; then
            print_status "Checking if app name '$APP_NAME' is available..."
            if flyctl apps list 2>/dev/null | grep -q "^$APP_NAME\s"; then
                print_warning "App name '$APP_NAME' already exists in your account."
                read -p "Use existing app '$APP_NAME'? [y/N]: " use_existing
                if [[ "$use_existing" != "y" && "$use_existing" != "Y" ]]; then
                    print_status "Please choose a different name."
                    APP_NAME=""
                    continue
                fi
            else
                print_success "App name '$APP_NAME' is available!"
            fi
        fi
        
        break
    done
    
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
        
        # Try to create app with error handling
        if flyctl apps create "$APP_NAME" --org personal; then
            print_success "App '$APP_NAME' created successfully!"
        else
            print_error "Failed to create app '$APP_NAME'"
            
            # Suggest alternative names
            print_status "App name might be taken globally. Try these alternatives:"
            echo "  ${APP_NAME}-$(date +%m%d)"
            echo "  ${APP_NAME}-$(whoami)"
            echo "  ${APP_NAME}-trading"
            echo "  ${APP_NAME}-bot"
            echo ""
            
            read -p "Enter a different app name: " NEW_APP_NAME
            if [[ -n "$NEW_APP_NAME" ]]; then
                APP_NAME="$NEW_APP_NAME"
                flyctl apps create "$APP_NAME" --org personal
                print_success "App '$APP_NAME' created!"
            else
                exit 1
            fi
        fi
    fi
    
    # Update fly.toml with app name and region
    print_status "Updating fly.toml configuration..."
    
    # Create backup
    cp fly.toml fly.toml.bak
    
    # Update app name and region
    sed -i.tmp "s/app = \".*\"/app = \"$APP_NAME\"/" fly.toml
    sed -i.tmp "s/primary_region = \".*\"/primary_region = \"$REGION\"/" fly.toml
    
    # Clean up temp files
    rm -f fly.toml.tmp fly.toml.bak
    
    print_success "fly.toml updated with app: $APP_NAME, region: $REGION"
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