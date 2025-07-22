# 🛠️ Deployment Troubleshooting Guide

Having issues with the one-click deployment? This guide will help you identify and fix common problems.

## 🚨 Terminal Crashes Instantly?

### Problem: Script crashes and terminal closes before you can read the error

### Solution: Use the Enhanced Scripts

We've created multiple deployment options with better error handling:

#### **Option 1: Enhanced One-Click Script (Recommended)**
```bash
# The updated script now prevents terminal from closing
./one-click-deploy.sh
# ✅ Shows detailed error messages
# ✅ Waits for keypress before closing
# ✅ Provides diagnostic information
```

#### **Option 2: Debug Script (For Complex Issues)**
```bash
# Provides maximum detail and logging
./debug-deploy.sh
# ✅ Creates detailed log file
# ✅ Shows system information
# ✅ Tests connectivity
# ✅ Validates prerequisites
```

#### **Option 3: Windows Batch Script**
```batch
REM For Windows users
one-click-deploy.bat
REM ✅ Windows-native error handling
REM ✅ Detailed progress messages
REM ✅ Automatic flyctl installation
```

## 🔧 Common Issues & Solutions

### 1. **flyctl Not Found**
```
Error: flyctl: command not found
```

**Solutions:**
```bash
# Linux/Mac - Automatic installation
curl -L https://fly.io/install.sh | sh
export PATH="$HOME/.fly/bin:$PATH"

# Windows - PowerShell
iwr https://fly.io/install.ps1 -useb | iex

# Or install via package managers
brew install flyctl        # macOS
choco install flyctl        # Windows (Chocolatey)
scoop install flyctl        # Windows (Scoop)
```

### 2. **Not Authenticated with Fly.io**
```
Error: not authenticated
```

**Solutions:**
```bash
# Login to fly.io
flyctl auth login

# Verify authentication
flyctl auth whoami

# If login fails, try:
flyctl auth logout
flyctl auth login
```

### 3. **Missing Environment Variables**
```
Error: TELEGRAM_TOKEN is required
```

**Solutions:**

**Method A: Use setup script**
```bash
./setup-env.sh           # Interactive setup
./one-click-deploy.sh    # Deploy with saved config
```

**Method B: Manual environment variables**
```bash
export TELEGRAM_TOKEN="your_bot_token"
export OWNER_ID="your_telegram_user_id"
./one-click-deploy.sh
```

**Method C: Create .env file**
```bash
# Create .env file
cat > .env << 'EOF'
TELEGRAM_TOKEN=your_bot_token
OWNER_ID=your_telegram_user_id
REAL_TRADING_ENABLED=false
WEB_ADMIN_TOKEN=admin123
EOF

./one-click-deploy.sh
```

### 4. **Network/Connectivity Issues**
```
Error: curl failed / cannot reach fly.io
```

**Solutions:**
```bash
# Test internet connectivity
ping google.com

# Test Fly.io specifically
curl -I https://fly.io

# Check if behind corporate firewall/proxy
export HTTP_PROXY="your_proxy:port"
export HTTPS_PROXY="your_proxy:port"

# Use debug script for detailed connectivity tests
./debug-deploy.sh
```

### 5. **App Already Exists**
```
Error: app name already taken
```

**Solutions:**
```bash
# Use different app name
export FLY_APP_NAME="memebot-yourname-$(date +%s)"
./one-click-deploy.sh

# Or specify in setup
./setup-env.sh  # Choose unique app name
```

### 6. **Volume Creation Failed**
```
Error: failed to create volume
```

**Solutions:**
```bash
# Check available regions
flyctl platform regions

# Try different region
export FLY_REGION="iad"  # US East
# or
export FLY_REGION="fra"  # Frankfurt (default)

# Manual volume creation
flyctl volumes create memebot_models --size 3 --region fra
flyctl volumes create memebot_logs --size 2 --region fra
flyctl volumes create memebot_data --size 1 --region fra
```

### 7. **Deployment Failed**
```
Error: deployment failed
```

**Solutions:**
```bash
# Check deployment logs
flyctl logs --app your-app-name

# Check app status
flyctl status --app your-app-name

# Try manual deployment
flyctl deploy --app your-app-name

# Check resource limits
flyctl scale show --app your-app-name
```

### 8. **Permission Denied**
```
Error: permission denied
```

**Solutions:**
```bash
# Check file permissions
ls -la one-click-deploy.sh

# Make executable
chmod +x one-click-deploy.sh
chmod +x setup-env.sh
chmod +x debug-deploy.sh

# For Windows
# Run as Administrator or use PowerShell script
```

## 🐛 Advanced Debugging

### Step 1: Use Debug Script
```bash
./debug-deploy.sh
```
This creates a detailed log file with:
- System information
- Network connectivity tests
- Tool availability checks
- Environment variable validation
- File system status

### Step 2: Manual Step-by-Step
If scripts still fail, try manual deployment:

```bash
# 1. Verify flyctl
flyctl version

# 2. Login
flyctl auth login

# 3. Create app
flyctl apps create memebot-test

# 4. Set secrets manually
flyctl secrets set TELEGRAM_TOKEN="your_token" --app memebot-test

# 5. Deploy
flyctl deploy --app memebot-test
```

### Step 3: Check Logs
```bash
# Deployment logs
flyctl logs --app your-app-name

# Build logs
flyctl logs --app your-app-name | grep -i error

# Live logs
flyctl logs --follow --app your-app-name
```

## 📞 Getting Help

### When Asking for Help, Include:

1. **Operating System**: Windows/Mac/Linux
2. **Error Message**: Full error text
3. **Debug Log**: From `debug-deploy.sh`
4. **Steps Taken**: What you tried
5. **Network Environment**: Corporate/Home/VPN

### Debug Log File
The debug script creates: `deployment-debug-YYYYMMDD-HHMMSS.log`
Include this file when asking for help.

### Example Help Request:
```
Subject: Deployment failing on Windows 10

OS: Windows 10 Pro
Error: flyctl command not found
Steps tried: 
1. Ran one-click-deploy.bat
2. Tried manual PowerShell installation
3. Restarted terminal

Debug log attached: deployment-debug-20241222-143022.log

Network: Corporate network with proxy
```

## 🔄 Alternative Deployment Methods

If one-click scripts don't work, try:

### 1. **GitHub Actions** (Zero Local Setup)
- Fork repository
- Set GitHub secrets
- Push to main branch
- Automatic deployment

### 2. **Manual Deployment**
```bash
git clone https://github.com/your-repo/MemeBot.git
cd MemeBot

# Install flyctl manually
curl -L https://fly.io/install.sh | sh

# Configure manually
cp .env.example .env
# Edit .env with your values

# Deploy step by step
flyctl auth login
flyctl apps create your-app-name
flyctl secrets set TELEGRAM_TOKEN="your_token"
flyctl deploy
```

### 3. **Docker Deployment**
```bash
# Build and deploy with Docker
docker build -t memebot .
flyctl deploy --dockerfile Dockerfile
```

## ✅ Success Checklist

After successful deployment, verify:

- [ ] App status: `flyctl status --app your-app-name`
- [ ] Health check: `curl https://your-app.fly.dev/health`
- [ ] Telegram bot responds to `/start`
- [ ] Web dashboard accessible
- [ ] Logs are clean: `flyctl logs --app your-app-name`

## 🎯 Prevention Tips

1. **Always test locally first** with paper trading
2. **Keep your .env file** for future deployments
3. **Use unique app names** to avoid conflicts
4. **Check Fly.io status** at https://status.fly.io
5. **Monitor resource usage** after deployment

---

**Need more help? Create an issue with your debug log and detailed error information!** 🆘