#!/bin/bash

# 🎲 MemeBot App Name Generator
# Generate unique app names for Fly.io deployment

echo "🎲 MemeBot App Name Generator"
echo "============================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_info() {
    echo -e "${BLUE}💡${NC} $1"
}

print_suggestion() {
    echo -e "${YELLOW}🎯${NC} $1"
}

# Get current user and date info
USER=$(whoami)
DATE_SHORT=$(date +%m%d)
DATE_LONG=$(date +%Y%m%d)
RANDOM_NUM=$((RANDOM % 9999 + 1000))

echo "Here are some unique app name suggestions:"
echo ""

# Personal names
echo "👤 Personalized Names:"
print_suggestion "memebot-$USER"
print_suggestion "solana-trader-$USER"
print_suggestion "$USER-memebot"
print_suggestion "$USER-trading-ai"
echo ""

# Date-based names
echo "📅 Date-based Names:"
print_suggestion "memebot-$DATE_SHORT"
print_suggestion "trading-bot-$DATE_SHORT"
print_suggestion "solana-ai-$DATE_LONG"
print_suggestion "meme-trader-$DATE_SHORT"
echo ""

# Random/Creative names
echo "🎨 Creative Names:"
print_suggestion "memebot-ai-$RANDOM_NUM"
print_suggestion "solana-moon-bot"
print_suggestion "degen-trader-ai"
print_suggestion "diamond-hands-bot"
print_suggestion "crypto-sniper-ai"
print_suggestion "meme-hunter-bot"
print_suggestion "token-scout-ai"
print_suggestion "profit-seeker-bot"
echo ""

# Descriptive names
echo "📝 Descriptive Names:"
print_suggestion "automated-meme-trader"
print_suggestion "solana-trading-assistant"
print_suggestion "ai-powered-dex-bot"
print_suggestion "smart-contract-trader"
print_suggestion "defi-trading-engine"
echo ""

# Ask user to check availability
echo "🔍 Want to check if a name is available?"
read -p "Enter app name to check (or press Enter to skip): " CHECK_NAME

if [[ -n "$CHECK_NAME" ]]; then
    # Validate format
    if [[ ! "$CHECK_NAME" =~ ^[a-z0-9-]+$ ]]; then
        echo "❌ Invalid format. Use only lowercase letters, numbers, and hyphens."
    elif [[ ${#CHECK_NAME} -lt 3 ]]; then
        echo "❌ Too short. Must be at least 3 characters."
    elif [[ ${#CHECK_NAME} -gt 30 ]]; then
        echo "❌ Too long. Must be less than 30 characters."
    else
        echo "✅ Format looks good!"
        
        # Check with flyctl if available
        if command -v flyctl >/dev/null 2>&1; then
            echo "🔍 Checking availability with Fly.io..."
            
            # Try to get app info (will fail if doesn't exist)
            if flyctl apps list 2>/dev/null | grep -q "^$CHECK_NAME\s"; then
                echo "❌ App name '$CHECK_NAME' is already taken in your account"
                echo "💡 Try one of the suggestions above or add numbers/username"
            else
                echo "✅ App name '$CHECK_NAME' appears to be available!"
                echo "💡 Ready to use in deployment"
                
                # Offer to export
                read -p "Export as environment variable? [Y/n]: " EXPORT_VAR
                if [[ "$EXPORT_VAR" != "n" && "$EXPORT_VAR" != "N" ]]; then
                    export FLY_APP_NAME="$CHECK_NAME"
                    echo "✅ Exported FLY_APP_NAME=$CHECK_NAME"
                    echo "💡 Now run: ./one-click-deploy.sh"
                fi
            fi
        else
            echo "⚠️ flyctl not installed - cannot check availability"
            echo "💡 Install flyctl first or try the name during deployment"
        fi
    fi
fi

echo ""
print_info "💡 Tips for choosing app names:"
echo "   • Use your username for personalization"
echo "   • Include date/numbers for uniqueness"
echo "   • Keep it short but descriptive"
echo "   • Avoid special characters except hyphens"
echo "   • Remember: names are global across all Fly.io users"
echo ""
print_info "🚀 Ready to deploy? Run:"
echo "   ./setup-env.sh        # Configure with chosen name"
echo "   ./one-click-deploy.sh  # Deploy to Fly.io"