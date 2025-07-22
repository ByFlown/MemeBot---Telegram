#!/bin/bash

# 🔧 Fix Fly.io Volume Configuration
# Removes old volumes and creates single volume setup

echo "🔧 MemeBot Volume Fixer"
echo "======================="
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
    exit 1
fi

# Get app name from fly.toml
APP_NAME=$(grep "^app" fly.toml | cut -d'"' -f2)
if [[ -z "$APP_NAME" ]]; then
    print_error "Could not find app name in fly.toml"
    exit 1
fi

print_status "Working with app: $APP_NAME"

# List existing volumes
print_status "Checking existing volumes..."
VOLUMES=$(flyctl volumes list 2>/dev/null || echo "")

if [[ -n "$VOLUMES" ]] && echo "$VOLUMES" | grep -q "vol_"; then
    print_warning "Found existing volumes:"
    echo "$VOLUMES"
    echo ""
    
    # Ask user if they want to delete old volumes
    print_warning "⚠️  The old volume structure is incompatible!"
    print_status "Fly.io only supports 1 volume per machine."
    echo ""
    read -p "Delete all existing volumes and start fresh? [y/N]: " DELETE_VOLUMES
    
    if [[ "$DELETE_VOLUMES" =~ ^[Yy]$ ]]; then
        print_status "Deleting existing volumes..."
        
        # Get volume IDs and delete them
        VOLUME_IDS=$(echo "$VOLUMES" | grep "vol_" | awk '{print $1}')
        for vol_id in $VOLUME_IDS; do
            if flyctl volumes destroy "$vol_id" --yes 2>/dev/null; then
                print_success "✅ Deleted volume: $vol_id"
            else
                print_warning "⚠️  Could not delete volume: $vol_id (may not exist)"
            fi
        done
    else
        print_error "Cannot proceed with existing incompatible volumes"
        print_status "Please delete them manually with: flyctl volumes destroy <volume_id>"
        exit 1
    fi
else
    print_status "No existing volumes found"
fi

# Create new single volume
print_status "Creating new storage volume..."
REGION=$(grep "^primary_region" fly.toml | cut -d'"' -f2)
if [[ -z "$REGION" ]]; then
    REGION="fra"  # default
fi

if flyctl volumes create memebot_storage --size=3 --region "$REGION"; then
    print_success "✅ Created volume: memebot_storage (3GB)"
else
    print_error "❌ Failed to create volume"
    exit 1
fi

print_status "Volume configuration complete!"
echo ""

# Deploy with new configuration
print_status "Deploying with new volume configuration..."

if flyctl deploy; then
    print_success "✅ Deployment successful!"
    echo ""
    
    print_status "Checking app status..."
    flyctl status
    
    echo ""
    print_status "Recent logs:"
    echo "=============================="
    flyctl logs --lines=15
    echo "=============================="
    
    print_success "🎉 Volume fix complete!"
    echo ""
    print_status "📁 New storage structure:"
    echo "  /app/storage/    <- Single mounted volume"
    echo "  /app/models/     <- Symlink to storage/models/"
    echo "  /app/logs/       <- Symlink to storage/logs/"
    echo "  /app/data/       <- Symlink to storage/data/"
    
else
    print_error "❌ Deployment failed"
    echo ""
    print_status "Check logs for details:"
    echo "  flyctl logs"
    exit 1
fi

echo ""
print_success "✅ All done! Your bot should now be running properly."
print_status "Test it by sending /start to your Telegram bot."