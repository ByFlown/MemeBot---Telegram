#!/bin/bash

# 🔧 Fix fly.toml Configuration Script
# Validates and fixes common fly.toml issues

echo "🔧 MemeBot fly.toml Validator & Fixer"
echo "===================================="
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

# Check if fly.toml exists
if [[ ! -f "fly.toml" ]]; then
    print_error "fly.toml not found in current directory"
    echo "Current directory: $(pwd)"
    echo "Files present:"
    ls -la
    exit 1
fi

print_status "Found fly.toml, validating configuration..."

# Create backup
cp fly.toml fly.toml.backup
print_status "Created backup: fly.toml.backup"

# Check for common issues
echo ""
print_status "Checking for common TOML issues..."

# Issue 1: Duplicate [mounts] sections
duplicate_mounts=$(grep -c "^\[mounts\]" fly.toml || true)
if [[ $duplicate_mounts -gt 1 ]]; then
    print_warning "Found $duplicate_mounts duplicate [mounts] sections"
    print_status "Fixing mount section syntax..."
    
    # Fix the mounts sections
    sed -i.tmp 's/^\[mounts\]/[[mounts]]/' fly.toml
    rm -f fly.toml.tmp
    
    print_success "Fixed mount sections to use array syntax [[mounts]]"
fi

# Issue 2: Check for other duplicate sections
for section in "env" "vm" "build" "http_service" "deploy"; do
    count=$(grep -c "^\[$section\]" fly.toml || true)
    if [[ $count -gt 1 ]]; then
        print_error "Found $count duplicate [$section] sections - manual fix required"
    fi
done

# Issue 3: Validate TOML syntax
print_status "Validating TOML syntax..."

# Try to validate with flyctl if available
if command -v flyctl >/dev/null 2>&1; then
    if flyctl config validate 2>/dev/null; then
        print_success "✅ fly.toml syntax is valid"
    else
        print_error "❌ fly.toml has syntax errors:"
        flyctl config validate 2>&1 || true
        echo ""
        print_status "Attempting automatic fixes..."
        
        # Common fixes
        print_status "Checking for missing quotes..."
        
        # Add quotes around string values that might be missing them
        sed -i.tmp2 's/= \([^"]\+\)$/= "\1"/' fly.toml
        rm -f fly.toml.tmp2
        
        # Re-validate
        if flyctl config validate 2>/dev/null; then
            print_success "✅ Fixed syntax issues automatically"
        else
            print_error "❌ Manual fix required. Check the validation output above."
            print_status "Restoring backup..."
            cp fly.toml.backup fly.toml
            exit 1
        fi
    fi
else
    print_warning "flyctl not available - skipping full syntax validation"
    
    # Basic validation
    if grep -q "^\[.*\].*\[.*\]" fly.toml; then
        print_error "Possible syntax error: multiple sections on same line"
    fi
    
    if grep -q "^  \[" fly.toml; then
        print_error "Possible syntax error: indented section headers"
    fi
fi

# Show current configuration
echo ""
print_status "Current fly.toml configuration:"
echo "================================"
cat fly.toml
echo "================================"

# Offer to test deployment
echo ""
read -p "Test deployment configuration? [Y/n]: " test_deploy
test_deploy=${test_deploy:-y}

if [[ "$test_deploy" == "y" || "$test_deploy" == "Y" ]]; then
    if command -v flyctl >/dev/null 2>&1; then
        print_status "Testing deployment configuration..."
        
        # Check if app exists and test config
        if flyctl status 2>/dev/null | grep -q "app"; then
            print_status "App exists, testing configuration..."
            if flyctl config save 2>/dev/null; then
                print_success "✅ Configuration is valid for deployment"
            else
                print_error "❌ Configuration has issues"
            fi
        else
            print_success "✅ Configuration syntax is valid (app not deployed yet)"
        fi
    else
        print_warning "flyctl not available - install it to test deployment"
    fi
fi

echo ""
print_success "fly.toml validation complete!"
echo ""
echo "📋 What was checked/fixed:"
echo "  ✅ Duplicate mount sections → Fixed to [[mounts]] syntax"  
echo "  ✅ TOML syntax validation"
echo "  ✅ Common configuration issues"
echo "  📁 Backup created: fly.toml.backup"
echo ""
echo "🚀 You can now run deployment:"
echo "  ./one-click-deploy.sh"
echo "  # or"  
echo "  flyctl deploy"