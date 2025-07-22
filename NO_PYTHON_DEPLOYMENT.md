# 🚀 Zero-Local-Dependencies Deployment

Deploy MemeBot to Fly.io **without installing Python, pip, or any local dependencies!**

## 🎯 Quick Start (One-Click Deployment)

### Option 1: One-Click Script (Smart Config Detection)
```bash
# Method A: With configuration setup
git clone https://github.com/your-repo/MemeBot.git
cd MemeBot
./setup-env.sh        # Configure once
./one-click-deploy.sh  # Deploy (uses saved config)

# Method B: Direct deployment (auto-detects .env)
./one-click-deploy.sh  # Prompts only for missing values

# Method C: With environment variables
export TELEGRAM_TOKEN="your_token"
export OWNER_ID="your_user_id" 
./one-click-deploy.sh  # No prompts needed!
```

### Option 2: GitHub Actions (Recommended)
1. **Fork this repository** on GitHub
2. **Set up secrets** in repository settings
3. **Push to main branch** or trigger workflow manually
4. **Done!** Your bot runs 24/7 on Fly.io

---

## 🔧 Setup Methods

### Method 1: GitHub Actions (Zero Local Setup)

#### Step 1: Fork Repository
- Go to this repository on GitHub
- Click "Fork" to create your copy

#### Step 2: Configure GitHub Secrets
Go to your forked repo → Settings → Secrets and variables → Actions

**Required Secrets:**
```
FLY_API_TOKEN=your_fly_io_api_token
TELEGRAM_TOKEN=your_telegram_bot_token
OWNER_ID=your_telegram_user_id
```

**Optional Secrets:**
```
FLY_APP_NAME=your-custom-app-name
SOLANA_PRIVATE_KEY=your_base58_private_key
REAL_TRADING_ENABLED=false
BIRDEYE_API_KEY=your_birdeye_api_key
HELIUS_API_KEY=your_helius_api_key
```

#### Step 3: Get Fly.io API Token
```bash
# Install flyctl locally (one time)
curl -L https://fly.io/install.sh | sh

# Login and get token
flyctl auth login
flyctl auth token
```

#### Step 4: Deploy
- Push any commit to `main` branch
- Or go to Actions → Deploy MemeBot → Run workflow
- Bot will be deployed automatically!

### Method 2: One-Click Script

#### Requirements
- **Only flyctl CLI** (no Python needed)
- Terminal access (Linux/Mac/WSL)

#### Installation
```bash
# Download repository
git clone https://github.com/your-repo/MemeBot.git
cd MemeBot

# Run one-click deployment
./one-click-deploy.sh
```

The script will:
1. ✅ Check/install flyctl
2. ✅ Login to Fly.io
3. ✅ Collect your configuration
4. ✅ Create app and volumes
5. ✅ Set secrets
6. ✅ Deploy everything
7. ✅ Verify deployment

### Method 3: Manual Fly.io Commands

If you prefer manual control:

```bash
# 1. Create app
flyctl apps create memebot-ai

# 2. Create volumes
flyctl volumes create memebot_models --size 3 --region fra
flyctl volumes create memebot_logs --size 2 --region fra  
flyctl volumes create memebot_data --size 1 --region fra

# 3. Set secrets
flyctl secrets set \
  TELEGRAM_TOKEN="your_token" \
  OWNER_ID="your_user_id" \
  PAPER_TRADING_ONLY="true"

# 4. Deploy
flyctl deploy
```

---

## 🌐 Web Dashboard Access

Your bot includes a **beautiful web dashboard** accessible at:
```
https://your-app-name.fly.dev
```

**Features:**
- 📊 Real-time performance metrics
- 🎮 Trading controls (start/stop/emergency)
- 📈 Interactive charts
- 📝 Live activity logs
- 💎 Wallet information
- 🧮 Run backtests
- 📱 Mobile-responsive design

**Default Login:**
- Token: `admin123` (change via `WEB_ADMIN_TOKEN` secret)

---

## 📱 Bot Management

### Via Telegram:
```
/start     - Show command menu
/status    - Bot status and performance
/realmode on|off - Toggle real trading
/wallet    - Wallet information
/backtest  - Run 30-day backtest
/dump      - Emergency stop all positions
```

### Via Web Dashboard:
- Real-time monitoring
- Trading controls
- Performance analytics
- Configuration management

### Via Fly.io CLI:
```bash
flyctl status              # App status
flyctl logs               # View logs
flyctl ssh console        # SSH access
flyctl apps restart       # Restart bot
flyctl secrets list       # List secrets
```

---

## 🔧 Configuration

### Environment Variables (GitHub Secrets or flyctl secrets)

#### Core Configuration:
```bash
TELEGRAM_TOKEN=your_bot_token           # Required
OWNER_ID=your_telegram_user_id          # Required
PAPER_TRADING_ONLY=true                 # Safe default
REAL_TRADING_ENABLED=false              # Start safe
WEB_ADMIN_TOKEN=your_admin_password     # Web dashboard
```

#### Trading Configuration:
```bash
SOLANA_PRIVATE_KEY=base58_private_key   # For real trading
MAX_POSITION_SIZE_SOL=1.0               # Max per trade
MAX_TOTAL_PORTFOLIO_SOL=10.0            # Portfolio limit
MIN_CONFIDENCE_THRESHOLD=0.6            # AI confidence
SCAN_INTERVAL_MINUTES=5                 # Scan frequency
```

#### API Keys (Optional):
```bash
BIRDEYE_API_KEY=your_birdeye_key       # Enhanced data
HELIUS_API_KEY=your_helius_key         # RPC access
DEXSCREENER_API_KEY=your_dex_key       # Premium features
```

---

## 💰 Fly.io Costs

### Free Tier Includes:
- ✅ **2,340 CPU hours/month** (more than 24/7)
- ✅ **3GB persistent storage** (free)
- ✅ **160GB bandwidth/month**
- ✅ **SSL certificates**
- ✅ **Global CDN**

### MemeBot Usage:
- **CPU**: ~720 hours/month (24/7) ✅ **FREE**
- **Memory**: 1GB RAM ✅ **FREE**  
- **Storage**: 6GB volumes = ~$0.90/month
- **Bandwidth**: Minimal usage ✅ **FREE**

**Total Cost: ~$1/month for professional 24/7 hosting!** 🎯

---

## 🚀 Deployment Advantages

### vs Local Hosting:
- ✅ **No local Python/dependencies**
- ✅ **99.9% uptime** (professional infrastructure)
- ✅ **Auto-scaling and recovery**
- ✅ **Global CDN** for web dashboard
- ✅ **SSL certificates** included
- ✅ **Professional monitoring**
- ✅ **Version control** integration
- ✅ **Zero maintenance**

### vs Other Cloud Providers:
- ✅ **Simpler setup** than AWS/GCP
- ✅ **Better pricing** than Heroku
- ✅ **More features** than VPS hosting
- ✅ **Built-in CI/CD** with GitHub Actions
- ✅ **Better performance** than serverless

---

## 🔒 Security Features

### Built-in Security:
- 🔐 **Encrypted secrets** management
- 🛡️ **Container isolation**
- 🌐 **HTTPS everywhere**
- 🔒 **Private networks**
- 👤 **Non-root execution**
- 🔑 **Token-based authentication**

### Best Practices:
- 🔄 **Regular secret rotation**
- 📊 **Comprehensive monitoring**
- 🚨 **Emergency controls**
- 💾 **Automated backups**
- 📝 **Audit logging**

---

## 🛠️ Maintenance & Updates

### Automatic Updates:
```bash
# Push to main branch = automatic deployment
git add .
git commit -m "Update trading parameters"  
git push origin main
# Bot updates automatically via GitHub Actions!
```

### Manual Updates:
```bash
# Update secrets
flyctl secrets set NEW_SETTING="new_value"

# Restart bot
flyctl apps restart your-app-name

# Check status
flyctl status
```

### Monitoring:
```bash
# Live logs
flyctl logs --follow

# Performance metrics
curl https://your-app.fly.dev/health

# Web dashboard
open https://your-app.fly.dev
```

---

## 🆘 Troubleshooting

### Common Issues:

#### Bot not starting:
```bash
flyctl logs --lines=50
# Check for configuration errors
```

#### Can't access web dashboard:
```bash
# Check if app is running
flyctl status

# Test health endpoint
curl https://your-app.fly.dev/health
```

#### Trading not working:
```bash
# Check wallet configuration
flyctl ssh console
# Inside container:
python -c "from src.wallet_manager import WalletManager; print(WalletManager().is_configured())"
```

#### Out of memory:
```bash
# Increase memory in fly.toml
[vm]
  memory_mb = 2048

# Redeploy
flyctl deploy
```

### Support:
- 📖 **Fly.io Docs**: https://fly.io/docs/
- 💬 **Community**: https://community.fly.io
- 🐛 **Issues**: GitHub repository issues
- 📊 **Status**: https://status.fly.io

---

## 🎉 Success Checklist

- [ ] Repository forked/cloned
- [ ] GitHub secrets configured (if using Actions)
- [ ] Telegram bot created (@BotFather)
- [ ] Fly.io account created
- [ ] flyctl installed and authenticated
- [ ] Deployment completed successfully
- [ ] Bot responds to `/start` in Telegram
- [ ] Web dashboard accessible
- [ ] Health check passes: `curl https://your-app.fly.dev/health`
- [ ] Logs are clean: `flyctl logs`

**Your MemeBot is now running 24/7 on professional infrastructure!** 🚀💎

---

## 📊 What Runs in the Cloud

**Everything runs on Fly.io - no local dependencies needed:**

- 🤖 **Telegram Bot** - Command interface
- 🧠 **AI Trading Engine** - RL models + ML predictions  
- 🔍 **Token Scanner** - DexScreener integration
- ⛓️ **Onchain Analyzer** - Solscan/Birdeye/Helius
- 💎 **Wallet Manager** - Jupiter swaps
- 📊 **Backtester** - Monte Carlo simulations
- 📈 **Performance Monitor** - Real-time metrics
- 🌐 **Web Dashboard** - Beautiful UI
- 📝 **Logging System** - Comprehensive tracking
- 🔄 **Auto-restart** - Reliability system

**All data persists in professional-grade volumes. All models train and learn continuously. Zero local setup required!**