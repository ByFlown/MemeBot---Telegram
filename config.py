# Configuration file for MemeBot
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'DEIN_TELEGRAM_BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', '123456789'))  # Your Telegram User ID

# Solana Configuration
SOLANA_PRIVATE_KEY = os.getenv('SOLANA_PRIVATE_KEY', '')  # Base58 encoded private key
SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')

# Trading Configuration
REAL_TRADING_ENABLED = os.getenv('REAL_TRADING_ENABLED', 'false').lower() == 'true'
MAX_POSITION_SIZE_SOL = float(os.getenv('MAX_POSITION_SIZE_SOL', '1.0'))  # Max SOL per trade
MAX_TOTAL_PORTFOLIO_SOL = float(os.getenv('MAX_TOTAL_PORTFOLIO_SOL', '10.0'))  # Max total portfolio
TRADING_FEE = float(os.getenv('TRADING_FEE', '0.0025'))  # 0.25% default fee
SLIPPAGE_TOLERANCE = float(os.getenv('SLIPPAGE_TOLERANCE', '0.005'))  # 0.5% slippage

# AI Trading Configuration
MIN_CONFIDENCE_THRESHOLD = float(os.getenv('MIN_CONFIDENCE_THRESHOLD', '0.6'))
MAX_RISK_THRESHOLD = float(os.getenv('MAX_RISK_THRESHOLD', '7.0'))
SCAN_INTERVAL_MINUTES = int(os.getenv('SCAN_INTERVAL_MINUTES', '5'))

# API Keys (optional, for enhanced features)
DEXSCREENER_API_KEY = os.getenv('DEXSCREENER_API_KEY', '')
BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY', '')
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY', '')

# Model Configuration
MODEL_RETRAIN_INTERVAL_HOURS = int(os.getenv('MODEL_RETRAIN_INTERVAL_HOURS', '6'))
BACKTEST_DAYS = int(os.getenv('BACKTEST_DAYS', '30'))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_RETENTION_DAYS = int(os.getenv('LOG_RETENTION_DAYS', '30'))

# Performance Monitoring
PERFORMANCE_UPDATE_INTERVAL_MINUTES = int(os.getenv('PERFORMANCE_UPDATE_INTERVAL_MINUTES', '15'))

# Safety Configuration
EMERGENCY_STOP_LOSS_PERCENT = float(os.getenv('EMERGENCY_STOP_LOSS_PERCENT', '50.0'))  # Emergency stop at 50% loss
MAX_TRADES_PER_HOUR = int(os.getenv('MAX_TRADES_PER_HOUR', '10'))

# Webhook Configuration (optional)
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')

# Development/Testing
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
PAPER_TRADING_ONLY = os.getenv('PAPER_TRADING_ONLY', 'true').lower() == 'true'

# Paper Trading Configuration
PAPER_TRADING_INITIAL_BALANCE = float(os.getenv('PAPER_TRADING_INITIAL_BALANCE', '100.0'))  # Starting SOL for paper trading
PAPER_TRADING_MAX_TRADE_PCT = float(os.getenv('PAPER_TRADING_MAX_TRADE_PCT', '0.10'))  # Max 10% per trade

# Only print configuration in local development, not in production
if not os.getenv('FLY_APP_NAME'):  # Only print locally, not on Fly.io
    print(f"✅ Configuration loaded:")
    print(f"   - Telegram Token: {'✅ Set' if TELEGRAM_TOKEN != 'DEIN_TELEGRAM_BOT_TOKEN' else '❌ Not set'}")
    print(f"   - Owner ID: {OWNER_ID}")
    print(f"   - Real Trading: {'🚨 ENABLED' if REAL_TRADING_ENABLED else '📝 Paper only'}")
    print(f"   - Wallet: {'✅ Configured' if SOLANA_PRIVATE_KEY else '❌ Not configured'}")
    print(f"   - Debug Mode: {'ON' if DEBUG_MODE else 'OFF'}")