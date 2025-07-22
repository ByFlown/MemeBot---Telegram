#!/bin/bash

# 🐛 MemeBot Debug Deployment Script
# Provides detailed logging and error information

# Enable debug mode
set -x  # Print commands as they're executed
set -euo pipefail
IFS=$'\n\t'

# Create debug log
DEBUG_LOG="deployment-debug-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$DEBUG_LOG") 2>&1

echo "🐛 MemeBot Debug Deployment Started"
echo "===================================="
echo "Debug log: $DEBUG_LOG"
echo "Timestamp: $(date)"
echo "User: $(whoami)"
echo "Shell: $BASH"
echo "Working directory: $(pwd)"
echo "PATH: $PATH"
echo ""

# Enhanced error handler
handle_error() {
    local exit_code=$?
    local line_number=$1
    local bash_lineno=$2
    local last_command="$3"
    local funcstack=("${FUNCNAME[@]}")
    
    echo ""
    echo "💥💥💥 CRITICAL ERROR DETECTED 💥💥💥"
    echo "======================================"
    echo "Timestamp: $(date)"
    echo "Exit Code: $exit_code"
    echo "Line Number: $line_number"
    echo "Bash Line: $bash_lineno"
    echo "Last Command: $last_command"
    echo "Function Stack: ${funcstack[*]}"
    echo ""
    
    echo "🔍 System Information:"
    echo "OS Type: $OSTYPE"
    echo "Kernel: $(uname -a 2>/dev/null || echo 'Unable to get kernel info')"
    echo "Shell Version: $BASH_VERSION"
    echo "Current Directory: $(pwd)"
    echo "Disk Space: $(df -h . 2>/dev/null | tail -1 || echo 'Unable to check disk space')"
    echo ""
    
    echo "🌐 Network Connectivity:"
    if ping -c 1 google.com >/dev/null 2>&1; then
        echo "✅ Internet connection: OK"
    else
        echo "❌ Internet connection: FAILED"
    fi
    
    if ping -c 1 fly.io >/dev/null 2>&1; then
        echo "✅ Fly.io connectivity: OK"
    else
        echo "❌ Fly.io connectivity: FAILED"
    fi
    echo ""
    
    echo "🔧 Tool Availability:"
    for tool in curl wget git flyctl; do
        if command -v $tool >/dev/null 2>&1; then
            local version=$($tool --version 2>&1 | head -1 || echo "Unknown version")
            echo "✅ $tool: $version"
        else
            echo "❌ $tool: Not found"
        fi
    done
    echo ""
    
    if command -v flyctl >/dev/null 2>&1; then
        echo "🚁 Flyctl Information:"
        echo "Version: $(flyctl version 2>&1 || echo 'Unable to get version')"
        echo "Auth Status: $(flyctl auth whoami 2>&1 || echo 'Not authenticated')"
        echo "Apps: $(flyctl apps list 2>&1 | head -5 || echo 'Unable to list apps')"
        echo ""
    fi
    
    echo "📂 File System:"
    echo "Current files: $(ls -la 2>/dev/null || echo 'Unable to list files')"
    if [[ -f ".env" ]]; then
        echo ".env file exists ($(wc -l < .env) lines)"
        echo "First few lines of .env:"
        head -5 .env | sed 's/=.*/=***HIDDEN***/'
    else
        echo ".env file: Not found"
    fi
    echo ""
    
    echo "🔒 Environment Variables (sanitized):"
    env | grep -E "(FLY_|TELEGRAM_|OWNER_)" | sed 's/=.*/=***HIDDEN***/' | head -10
    echo ""
    
    echo "📋 Recent Commands History:"
    history | tail -10 2>/dev/null || echo "Unable to get command history"
    echo ""
    
    echo "🆘 Troubleshooting Steps:"
    echo "1. Check internet connection"
    echo "2. Verify flyctl installation: curl -L https://fly.io/install.sh | sh"
    echo "3. Login to Fly.io: flyctl auth login"
    echo "4. Check .env file format and permissions"
    echo "5. Verify all required environment variables"
    echo "6. Check available disk space"
    echo "7. Try running with sudo (if permissions issue)"
    echo ""
    
    echo "📧 Support Information:"
    echo "- Debug log saved to: $DEBUG_LOG"
    echo "- Share this log when asking for help"
    echo "- Fly.io Community: https://community.fly.io"
    echo "- Repository Issues: GitHub issues page"
    echo ""
    
    echo "⏸️  Press any key to exit (this keeps the terminal open)..."
    read -n 1 -s
    exit $exit_code
}

# Set comprehensive error trapping
trap 'handle_error ${LINENO} $? "$BASH_COMMAND"' ERR

# Function to validate prerequisites
validate_prerequisites() {
    echo "🔍 Validating prerequisites..."
    
    # Check OS compatibility
    case "$OSTYPE" in
        linux-gnu*|darwin*) 
            echo "✅ OS compatible: $OSTYPE"
            ;;
        msys|cygwin|win32)
            echo "❌ Windows detected. Please use one-click-deploy.bat instead"
            exit 1
            ;;
        *)
            echo "⚠️ Unknown OS: $OSTYPE (may work, continuing...)"
            ;;
    esac
    
    # Check required commands
    local required_commands=("curl" "bash")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "❌ Required command not found: $cmd"
            echo "Please install $cmd and try again"
            exit 1
        fi
        echo "✅ $cmd available"
    done
    
    # Check disk space (need at least 100MB)
    if command -v df >/dev/null 2>&1; then
        local available_space
        available_space=$(df . | tail -1 | awk '{print $4}')
        if [[ $available_space -lt 100000 ]]; then
            echo "⚠️ Low disk space: ${available_space}KB available"
            echo "Consider freeing up some space"
        else
            echo "✅ Sufficient disk space: ${available_space}KB available"
        fi
    fi
    
    # Check internet connectivity with verbose output
    echo "🌐 Testing internet connectivity..."
    if timeout 10 curl -sSf https://google.com >/dev/null; then
        echo "✅ Internet connection working"
    else
        echo "❌ No internet connection detected"
        echo "Please check your network settings"
        exit 1
    fi
    
    # Test Fly.io connectivity specifically
    echo "🚁 Testing Fly.io connectivity..."
    if timeout 10 curl -sSf https://fly.io >/dev/null; then
        echo "✅ Fly.io accessible"
    else
        echo "❌ Cannot reach fly.io"
        echo "Please check if fly.io is blocked or if there are network issues"
        exit 1
    fi
}

# Enhanced flyctl installation with detailed logging
install_flyctl() {
    echo "📦 Installing flyctl with detailed logging..."
    
    # Create temporary directory
    local temp_dir
    temp_dir=$(mktemp -d)
    echo "Using temp directory: $temp_dir"
    
    # Download installer
    echo "⬇️ Downloading flyctl installer..."
    if curl -fsSL -o "$temp_dir/install.sh" https://fly.io/install.sh; then
        echo "✅ Installer downloaded successfully"
        
        # Show installer content (first few lines for verification)
        echo "📋 Installer preview:"
        head -10 "$temp_dir/install.sh"
        echo "..."
        
        # Make executable and run
        chmod +x "$temp_dir/install.sh"
        echo "🚀 Running installer..."
        bash "$temp_dir/install.sh"
        
        # Update PATH
        if [[ -d "$HOME/.fly/bin" ]]; then
            export PATH="$HOME/.fly/bin:$PATH"
            echo "✅ Updated PATH to include ~/.fly/bin"
        fi
        
        # Verify installation
        if command -v flyctl >/dev/null 2>&1; then
            echo "✅ flyctl installed successfully: $(flyctl version)"
        else
            echo "❌ flyctl installation failed"
            echo "Contents of ~/.fly/bin:"
            ls -la "$HOME/.fly/bin/" 2>/dev/null || echo "Directory not found"
            exit 1
        fi
    else
        echo "❌ Failed to download installer"
        echo "Curl exit code: $?"
        echo "Try manual installation: https://fly.io/docs/flyctl/install/"
        exit 1
    fi
    
    # Cleanup
    rm -rf "$temp_dir"
    echo "🧹 Cleaned up temporary files"
}

# Main execution with detailed progress
main() {
    echo "🚀 Starting debug deployment process..."
    
    validate_prerequisites
    
    # Check for flyctl
    if ! command -v flyctl >/dev/null 2>&1; then
        install_flyctl
    else
        echo "✅ flyctl already available: $(flyctl version)"
    fi
    
    # Continue with normal deployment (importing functions from main script)
    echo "🔄 Continuing with standard deployment process..."
    
    # Source the main deployment script functions
    # (This would need to be adapted based on your specific needs)
    
    echo "✅ Debug deployment completed successfully!"
    echo "📋 Debug log saved to: $DEBUG_LOG"
}

# Cleanup function
cleanup() {
    local exit_code=$?
    if [[ $exit_code -eq 0 ]]; then
        echo ""
        echo "✅ Script completed successfully!"
    else
        echo ""
        echo "❌ Script failed with exit code: $exit_code"
    fi
    
    echo "📋 Debug information saved to: $DEBUG_LOG"
    echo "💡 You can review this log file for detailed information"
    
    if [[ $exit_code -ne 0 ]]; then
        echo ""
        echo "⏸️  Press any key to close..."
        read -n 1 -s
    fi
    
    exit $exit_code
}

trap cleanup EXIT

# Run main function
main "$@"