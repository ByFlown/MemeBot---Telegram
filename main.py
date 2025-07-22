import asyncio
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import time
import threading
from aiohttp import web, ClientSession

from config import TELEGRAM_TOKEN, OWNER_ID
from src.scanner import DexScreenerScanner
from src.onchain_analyzer import OnchainAnalyzer
from src.ai_trader import AITrader
from src.wallet_manager import WalletManager
from src.backtester import Backtester
from src.logger import TradingLogger
from src.performance_monitor import PerformanceMonitor
from src.web_interface import WebInterface

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MemeBot:
    def __init__(self):
        self.scanner = DexScreenerScanner()
        self.onchain_analyzer = OnchainAnalyzer()
        self.ai_trader = AITrader()
        self.wallet_manager = WalletManager()
        self.backtester = Backtester()
        self.trading_logger = TradingLogger()
        self.performance_monitor = PerformanceMonitor()
        self.web_interface = WebInterface(self)
        
        self.real_mode = False
        self.scanning_active = True
        self.scan_interval = 300  # 5 minutes default
        
        # Performance tracking
        self.total_trades = 0
        self.successful_trades = 0
        self.total_profit_loss = 0.0
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        try:
            if update.effective_user.id != OWNER_ID:
                await update.message.reply_text("🚫 Unauthorized access!")
                logger.warning(f"Unauthorized access attempt from user {update.effective_user.id}")
                return
                
            await update.message.reply_text(
                "🤖 **MemeBot AI Trading Bot**\n\n"
                "Available commands:\n"
                "/start - Show this menu\n"
                "/status - Bot status and stats\n"
                "/realmode on|off - Toggle real trading\n"
                "/scan on|off - Toggle scanning\n"
                "/setscan <minutes> - Set scan interval\n"
                "/wallet - Wallet information\n"
                "/top5 - Top 5 recent opportunities\n"
                "/performance - Performance dashboard\n"
                "/backtest - Run backtest\n"
                "/logs - Recent trading logs\n"
                "/dump - Emergency stop all positions",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await update.message.reply_text("❌ Error processing command. Please try again.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Status command handler"""
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text("🚫 Unauthorized access!")
            return
        
        uptime = datetime.now() - self.start_time if hasattr(self, 'start_time') else timedelta(0)
        success_rate = (self.successful_trades / max(self.total_trades, 1)) * 100
        
        status_msg = (
            f"📊 **Bot Status**\n\n"
            f"🟢 Online: {uptime}\n"
            f"🔄 Real Mode: {'ON' if self.real_mode else 'OFF (Paper Trading)'}\n"
            f"📡 Scanning: {'ON' if self.scanning_active else 'OFF'}\n"
            f"⏱️ Scan Interval: {self.scan_interval}s\n"
            f"📈 Total Trades: {self.total_trades}\n"
            f"✅ Success Rate: {success_rate:.1f}%\n"
            f"💰 P&L: {self.total_profit_loss:.4f} SOL\n"
            f"💎 Wallet Balance: {await self.wallet_manager.get_sol_balance():.4f} SOL"
        )
        
        await update.message.reply_text(status_msg)
    
    async def realmode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle real trading mode"""
        if update.effective_user.id != OWNER_ID:
            return
            
        if not context.args:
            await update.message.reply_text("Usage: /realmode on|off")
            return
            
        mode = context.args[0].lower()
        if mode == "on":
            if not self.wallet_manager.is_configured():
                await update.message.reply_text("❌ Wallet not configured! Add private key first.")
                return
            self.real_mode = True
            await update.message.reply_text("🚨 **REAL TRADING MODE ACTIVATED** 🚨\nBot will trade with real money!")
        elif mode == "off":
            self.real_mode = False
            await update.message.reply_text("📝 Paper trading mode activated. No real money at risk.")
        else:
            await update.message.reply_text("Usage: /realmode on|off")
    
    async def scan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle scanning"""
        if update.effective_user.id != OWNER_ID:
            return
            
        if not context.args:
            await update.message.reply_text("Usage: /scan on|off")
            return
            
        mode = context.args[0].lower()
        if mode == "on":
            self.scanning_active = True
            await update.message.reply_text("🔍 Token scanning activated!")
        elif mode == "off":
            self.scanning_active = False
            await update.message.reply_text("⏸️ Token scanning paused.")
        else:
            await update.message.reply_text("Usage: /scan on|off")
    
    async def setscan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set scan interval"""
        if update.effective_user.id != OWNER_ID:
            return
            
        if not context.args:
            await update.message.reply_text("Usage: /setscan <minutes>")
            return
            
        try:
            minutes = int(context.args[0])
            if minutes < 1:
                await update.message.reply_text("❌ Interval must be at least 1 minute")
                return
            self.scan_interval = minutes * 60
            await update.message.reply_text(f"⏱️ Scan interval set to {minutes} minutes")
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid number")
    
    async def wallet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show wallet information"""
        if update.effective_user.id != OWNER_ID:
            return
            
        wallet_info = await self.wallet_manager.get_wallet_info()
        await update.message.reply_text(
            f"💎 **Wallet Information**\n\n"
            f"Address: `{wallet_info['address']}`\n"
            f"SOL Balance: {wallet_info['sol_balance']:.4f} SOL\n"
            f"Token Count: {wallet_info['token_count']}\n"
            f"Status: {'🟢 Connected' if wallet_info['connected'] else '🔴 Disconnected'}"
        )
    
    async def top5_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show top 5 recent opportunities"""
        if update.effective_user.id != OWNER_ID:
            return
            
        opportunities = await self.ai_trader.get_top_opportunities()
        msg = "🚀 **Top 5 Recent Opportunities**\n\n"
        
        for i, opp in enumerate(opportunities[:5], 1):
            msg += f"{i}. {opp['symbol']} - Score: {opp['score']:.2f}\n"
            msg += f"   💰 Volume: ${opp['volume']:,.0f}\n"
            msg += f"   📈 Price Change: {opp['price_change']:+.1f}%\n\n"
        
        await update.message.reply_text(msg)
    
    async def performance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show performance dashboard"""
        if update.effective_user.id != OWNER_ID:
            return
            
        metrics = await self.performance_monitor.get_metrics()
        await update.message.reply_text(
            f"📊 **Performance Dashboard**\n\n"
            f"📈 24h Performance: {metrics['daily_performance']:+.2f}%\n"
            f"📅 7d Performance: {metrics['weekly_performance']:+.2f}%\n"
            f"🎯 Win Rate: {metrics['win_rate']:.1f}%\n"
            f"💵 Avg Trade Size: {metrics['avg_trade_size']:.4f} SOL\n"
            f"⏱️ Avg Hold Time: {metrics['avg_hold_time']}\n"
            f"🔥 Best Trade: +{metrics['best_trade']:.2f}%\n"
            f"❄️ Worst Trade: {metrics['worst_trade']:+.2f}%"
        )
    
    async def backtest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Run backtest"""
        if update.effective_user.id != OWNER_ID:
            return
            
        await update.message.reply_text("🧮 Running backtest... This may take a moment.")
        results = await self.backtester.run_backtest(days=30)
        
        await update.message.reply_text(
            f"📊 **30-Day Backtest Results**\n\n"
            f"💰 Total Return: {results['total_return']:+.2f}%\n"
            f"📈 Sharpe Ratio: {results['sharpe_ratio']:.2f}\n"
            f"📉 Max Drawdown: -{results['max_drawdown']:.2f}%\n"
            f"🎯 Win Rate: {results['win_rate']:.1f}%\n"
            f"📊 Total Trades: {results['total_trades']}\n"
            f"💎 Avg Trade: {results['avg_trade_return']:+.2f}%"
        )
    
    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent logs"""
        if update.effective_user.id != OWNER_ID:
            return
            
        logs = self.trading_logger.get_recent_logs(10)
        msg = "📝 **Recent Trading Logs**\n\n"
        
        for log in logs:
            msg += f"🕐 {log['timestamp']}\n"
            msg += f"📊 {log['action']} - {log['symbol']}\n"
            msg += f"💰 {log['amount']:.4f} SOL\n"
            msg += f"📈 Result: {log['result']}\n\n"
        
        await update.message.reply_text(msg[:4000])  # Telegram message limit
    
    async def dump_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Emergency stop - sell all positions"""
        if update.effective_user.id != OWNER_ID:
            return
            
        if not self.real_mode:
            await update.message.reply_text("📝 Paper trading mode - no real positions to close.")
            return
            
        await update.message.reply_text("🚨 EMERGENCY STOP - Closing all positions!")
        closed_positions = await self.wallet_manager.close_all_positions()
        
        await update.message.reply_text(
            f"✅ Emergency stop completed!\n"
            f"Closed {len(closed_positions)} positions\n"
            f"Total recovered: {sum(p['amount'] for p in closed_positions):.4f} SOL"
        )
    
    async def scan_and_trade(self):
        """Main scanning and trading loop"""
        while True:
            try:
                if not self.scanning_active:
                    await asyncio.sleep(60)
                    continue
                
                logger.info("🔍 Scanning for ALL token opportunities (unfiltered)...")
                
                # Get ALL tokens from DexScreener for AI learning
                all_tokens = await self.scanner.scan_new_tokens()
                logger.info(f"Found {len(all_tokens)} tokens for AI analysis")
                
                for token in all_tokens:
                    try:
                        # Enhanced onchain analysis
                        onchain_data = await self.onchain_analyzer.analyze_token(token['address'])
                        
                        # Combine data for AI analysis
                        combined_data = {**token, **onchain_data}
                        
                        # AI decision making
                        trade_decision = await self.ai_trader.should_trade(combined_data)
                        
                        if trade_decision['should_trade']:
                            logger.info(f"🎯 Trading opportunity: {token['symbol']} - Score: {trade_decision['confidence']:.2f}")
                            
                            if self.real_mode:
                                # Execute real trade
                                trade_result = await self.wallet_manager.execute_trade(
                                    token_address=token['address'],
                                    amount_sol=trade_decision['amount'],
                                    action='buy'
                                )
                            else:
                                # Paper trade
                                trade_result = {
                                    'success': True,
                                    'amount': trade_decision['amount'],
                                    'price': token['price'],
                                    'type': 'paper'
                                }
                            
                            # Log trade
                            self.trading_logger.log_trade(token, trade_result, trade_decision)
                            
                            # Update AI model with result (for learning)
                            self.ai_trader.update_model(combined_data, trade_result)
                            
                            # Update stats
                            self.total_trades += 1
                            if trade_result.get('success'):
                                self.successful_trades += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing token {token.get('symbol', 'unknown')}: {e}")
                
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in scan_and_trade loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    def setup_scheduler(self):
        """Setup scheduled tasks"""
        self.scheduler = AsyncIOScheduler()
        
        # Schedule AI model retraining every hour
        self.scheduler.add_job(
            self.ai_trader.retrain_model,
            'interval',
            hours=1,
            id='retrain_model'
        )
        
        # Schedule performance metrics update every 6 hours
        self.scheduler.add_job(
            self.performance_monitor.update_metrics,
            'interval',
            hours=6,
            id='update_metrics'
        )
        
        self.scheduler.start()
    
    async def health_check(self, request):
        """Health check endpoint for monitoring"""
        try:
            # Check if bot is responsive
            status = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'uptime': str(datetime.now() - self.start_time) if hasattr(self, 'start_time') else 'unknown',
                'real_mode': self.real_mode,
                'scanning_active': self.scanning_active,
                'total_trades': self.total_trades,
                'successful_trades': self.successful_trades,
                'scan_interval': self.scan_interval
            }
            return web.json_response(status)
        except Exception as e:
            return web.json_response({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=500)
    
    async def setup_web_interface(self):
        """Setup web interface server"""
        port = int(os.getenv('PORT', 8080))
        await self.web_interface.start_server(port)
    
    async def setup_bot_commands(self, application):
        """Setup bot command menu"""
        try:
            commands = [
                BotCommand("start", "Show bot menu and commands"),
                BotCommand("status", "Show bot status and statistics"),
                BotCommand("realmode", "Toggle real trading mode on/off"),
                BotCommand("scan", "Toggle token scanning on/off"),
                BotCommand("setscan", "Set scanning interval in minutes"),
                BotCommand("wallet", "Show wallet information"),
                BotCommand("top5", "Show top 5 recent opportunities"),
                BotCommand("performance", "Show performance dashboard"),
                BotCommand("backtest", "Run backtesting analysis"),
                BotCommand("logs", "Show recent trading logs"),
                BotCommand("dump", "Emergency stop - close all positions")
            ]
            
            await application.bot.set_my_commands(commands)
            logger.info("✅ Bot commands registered successfully")
            
        except Exception as e:
            logger.error(f"Error setting up bot commands: {e}")

async def main():
    """Main function"""
    try:
        print("🚀 MemeBot starting up...")
        logger.info("🚀 MemeBot starting up...")
        
        # Debug configuration
        print(f"📋 Configuration check:")
        print(f"   TELEGRAM_TOKEN: {'✅ Set' if TELEGRAM_TOKEN != 'DEIN_TELEGRAM_BOT_TOKEN' else '❌ Not set'}")
        print(f"   OWNER_ID: {OWNER_ID}")
        
        # Validate configuration
        if TELEGRAM_TOKEN == 'DEIN_TELEGRAM_BOT_TOKEN':
            logger.error("❌ TELEGRAM_TOKEN not configured! Please set your bot token.")
            print("\n🔧 Configuration Error:")
            print("TELEGRAM_TOKEN is not configured. Using environment variable or fly secrets:")
            print("  fly secrets set TELEGRAM_TOKEN=your_bot_token_here")
            print("  fly secrets set OWNER_ID=your_telegram_user_id")
            print("\n⏳ Continuing in demo mode for 60 seconds...")
            
            # Don't exit immediately - wait a bit to see logs
            await asyncio.sleep(60)
            return
        
        if OWNER_ID == 123456789:
            logger.warning("⚠️ OWNER_ID not configured! Using default value.")
            print("\n⚠️ Configuration Warning:")
            print("Please set your OWNER_ID (your Telegram user ID) in environment variables")
            print("Send a message to @userinfobot to get your Telegram user ID")
        
        bot = MemeBot()
        bot.start_time = datetime.now()
        
        logger.info("🚀 Initializing MemeBot...")
        
        # Initialize Telegram bot
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", bot.start_command))
        application.add_handler(CommandHandler("status", bot.status_command))
        application.add_handler(CommandHandler("realmode", bot.realmode_command))
        application.add_handler(CommandHandler("scan", bot.scan_command))
        application.add_handler(CommandHandler("setscan", bot.setscan_command))
        application.add_handler(CommandHandler("wallet", bot.wallet_command))
        application.add_handler(CommandHandler("top5", bot.top5_command))
        application.add_handler(CommandHandler("performance", bot.performance_command))
        application.add_handler(CommandHandler("backtest", bot.backtest_command))
        application.add_handler(CommandHandler("logs", bot.logs_command))
        application.add_handler(CommandHandler("dump", bot.dump_command))
        
        # Setup scheduler
        bot.setup_scheduler()
        
        # Setup web interface
        await bot.setup_web_interface()
        
        # Start Telegram bot
        await application.initialize()
        await application.start()
        
        # Register bot commands for the command menu
        await bot.setup_bot_commands(application)
        
        # Start polling
        await application.updater.start_polling()
        
        logger.info("✅ MemeBot Telegram bot is running!")
        logger.info(f"📱 Bot username: @{application.bot.username}")
        
        # Start trading loop
        trading_task = asyncio.create_task(bot.scan_and_trade())
        
        try:
            await trading_task
        except KeyboardInterrupt:
            logger.info("🛑 Bot shutting down...")
        finally:
            await application.stop()
            
    except Exception as e:
        logger.error(f"💥 Critical error in main(): {e}")
        print(f"\n💥 Bot crashed with error: {e}")
        print("Check your configuration and try again.")
        
        # In production, keep container running for debugging
        if os.getenv('FLY_APP_NAME'):
            print("🔍 Running on Fly.io - keeping container alive for debugging...")
            logger.error("Keeping container alive for debugging...")
            while True:
                await asyncio.sleep(300)  # Sleep 5 minutes at a time

if __name__ == "__main__":
    print("🚀 Starting MemeBot AI Trading Bot...")
    asyncio.run(main())