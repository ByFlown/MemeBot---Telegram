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
from src.ai_logger import ai_trader_logger
from src.self_learning_trader import SelfLearningTrader

# Load environment variables
load_dotenv()

# Apply Solana client proxy fix for Fly.io
try:
    from src.solana_client_fix import patch_async_client, patch_async_client_init
    
    # Try both patching approaches for maximum compatibility
    patch_success = patch_async_client()
    if not patch_success:
        print("Main patch failed, trying alternative approach...")
        patch_async_client_init()
    
    print("✅ Solana client proxy fix applied successfully")
except Exception as e:
    print(f"⚠️ Warning: Could not apply Solana client proxy fix: {e}")
    print("The bot will continue but may encounter proxy-related errors.")

# Setup logging with debug for scanner
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Enable debug for scanner specifically  
logging.getLogger('src.scanner').setLevel(logging.DEBUG)

# Enable AI system logging
logging.getLogger('ai.trader').setLevel(logging.INFO)
logging.getLogger('ai.scanner').setLevel(logging.INFO)
logging.getLogger('ai.analyzer').setLevel(logging.INFO)
logging.getLogger('ai.model').setLevel(logging.INFO)

logger = logging.getLogger(__name__)

class MemeBot:
    def __init__(self):
        self.scanner = DexScreenerScanner()
        self.onchain_analyzer = OnchainAnalyzer()
        self.ai_trader = AITrader()  # Keep old system for comparison
        self.self_learning_trader = SelfLearningTrader()  # NEW: Self-learning system
        self.wallet_manager = WalletManager()
        self.backtester = Backtester()
        self.trading_logger = TradingLogger()
        self.performance_monitor = PerformanceMonitor()
        self.web_interface = WebInterface(self)
        
        self.real_mode = False
        self.scanning_active = True
        self.scan_interval = 300  # 5 minutes default
        
        # Set paper trading mode on wallet manager
        self.wallet_manager.set_paper_mode(not self.real_mode)
        
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
                "/mlstats - ML model statistics\n"
                "/retrain - Force model retraining\n"
                "/quickstart - Generate training data\n"
                "/clearmodel - Clear model for fresh training\n"
                "/dump - Emergency stop all positions\n"
                "/addfunds <amount> - Add SOL to paper trading account\n"
                "/resetaccount - Reset paper trading account\n"
                "/portfolio - Show detailed portfolio summary",
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
            self.wallet_manager.set_paper_mode(False)  # Disable paper mode
            await update.message.reply_text("🚨 **REAL TRADING MODE ACTIVATED** 🚨\nBot will trade with real money!")
        elif mode == "off":
            self.real_mode = False
            self.wallet_manager.set_paper_mode(True)  # Enable paper mode
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
        
        if wallet_info.get('paper_mode', False):
            # Paper trading wallet info
            msg = (
                f"💎 **Paper Trading Wallet**\n\n"
                f"Mode: 📝 Paper Trading\n"
                f"SOL Balance: {wallet_info['sol_balance']:.4f} SOL\n"
                f"Active Positions: {wallet_info['active_positions']}\n"
                f"Starting Balance: {wallet_info.get('starting_balance', 100):.4f} SOL\n"
                f"Total Invested: {wallet_info.get('total_invested', 0):.4f} SOL\n"
                f"P&L: {wallet_info.get('total_profit_loss', 0):+.4f} SOL\n"
                f"Performance: {wallet_info.get('performance_pct', 0):+.2f}%\n"
                f"Status: {'🟢 Active' if wallet_info['connected'] else '🔴 Inactive'}"
            )
        else:
            # Real wallet info
            msg = (
                f"💎 **Real Wallet Information**\n\n"
                f"Address: `{wallet_info['address']}`\n"
                f"SOL Balance: {wallet_info['sol_balance']:.4f} SOL\n"
                f"Token Count: {wallet_info['token_count']}\n"
                f"Active Positions: {wallet_info.get('active_positions', 0)}\n"
                f"Status: {'🟢 Connected' if wallet_info['connected'] else '🔴 Disconnected'}"
            )
        
        await update.message.reply_text(msg)
    
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
    
    async def ml_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """🧠 Show profit-based ML learning statistics"""
        if update.effective_user.id != OWNER_ID:
            return
        
        try:
            stats = self.self_learning_trader.get_training_stats()
            
            msg = "🧠 **Profit-Based ML Learning Statistics**\n\n"
            
            # Trading Overview
            msg += f"📊 **Trading Overview:**\n"
            msg += f"• Total Positions: {stats.get('total_positions', 0)}\n"  
            msg += f"• Completed Trades: {stats.get('completed_trades', 0)}\n"
            msg += f"• Active Positions: {stats.get('active_positions', 0)}\n\n"
            
            # Profit Statistics (All Time)
            msg += f"💰 **Profit Statistics (All Time):**\n"
            if stats.get('completed_trades', 0) > 0:
                msg += f"• Average Profit: {stats.get('avg_profit_pct', 0)*100:+.2f}%\n"
                msg += f"• Best Trade: {stats.get('max_profit_pct', 0)*100:+.2f}%\n"
                msg += f"• Worst Trade: {stats.get('min_profit_pct', 0)*100:+.2f}%\n"
                msg += f"• Total Profit: {stats.get('total_profit_sol', 0):.4f} SOL\n"
                msg += f"• Avg Reward Score: {stats.get('avg_reward_score', 0):.3f}\n"
            else:
                msg += f"• No completed trades yet\n"
            
            # Performance (Last 7 Days)  
            msg += f"\n🎯 **Performance (Last 7 Days):**\n"
            if stats.get('recent_trade_count', 0) > 0:
                msg += f"• Trades: {stats.get('recent_trade_count', 0)}\n"
                msg += f"• Win Rate: {stats.get('win_rate_pct', 0):.1f}%\n"
                msg += f"• Profitable Trades: {stats.get('profitable_trades_7d', 0)}\n"
                msg += f"• Avg Profit: {stats.get('recent_avg_profit_pct', 0)*100:+.2f}%\n"
                msg += f"• Avg Hold Time: {stats.get('avg_holding_duration_min', 0):.1f} min\n"
            else:
                msg += f"• No recent trades\n"
            
            # Exit Strategy Analysis
            exit_reasons = stats.get('exit_reasons', {})
            if exit_reasons:
                msg += f"\n🚪 **Exit Strategy Analysis (7d):**\n"
                for reason, count in sorted(exit_reasons.items(), key=lambda x: x[1], reverse=True):
                    reason_display = reason.replace('_', ' ').title()
                    msg += f"• {reason_display}: {count}\n"
            
            # Model Status
            msg += f"\n📈 **Model Status:**\n"
            msg += f"• Model Trained: {'✅ Yes' if stats.get('model_trained', False) else '❌ No'}\n"
            
            model_perf = stats.get('model_performance', {})
            if model_perf:
                msg += f"• Model Type: {model_perf.get('model_type', 'Unknown')}\n"
                msg += f"• Features Used: {model_perf.get('features_count', 19)}\n"
                msg += f"• Profit Threshold: {model_perf.get('profit_threshold', 0.02)*100:+.1f}%\n"
                msg += f"• Confidence Threshold: {model_perf.get('confidence_threshold', 0.6)*100:.0f}%\n"
                msg += f"• Max Hold Time: {model_perf.get('max_position_age_hours', 48):.0f}h\n"
                msg += f"• Stop Loss: {model_perf.get('stop_loss_threshold', -0.15)*100:+.0f}%\n"
                msg += f"• Online Learning: {'✅' if model_perf.get('online_learning_enabled', False) else '❌'}\n"
                msg += f"• Performance Score: {model_perf.get('current_performance_score', 0)*100:+.2f}%\n"
            
            # Confidence Analysis
            if stats.get('avg_confidence', 0) > 0:
                msg += f"\n🎯 **Confidence Analysis (7d):**\n"
                msg += f"• Average Confidence: {stats.get('avg_confidence', 0)*100:.1f}%\n"
                if stats.get('avg_confidence_profitable', 0) > 0:
                    msg += f"• Avg Confidence (Profitable): {stats.get('avg_confidence_profitable', 0)*100:.1f}%\n"
                if stats.get('avg_confidence_losses', 0) > 0:
                    msg += f"• Avg Confidence (Losses): {stats.get('avg_confidence_losses', 0)*100:.1f}%\n"
            
            # Boosted/Trending Token Analysis
            if stats.get('boosted_trades', 0) > 0 or stats.get('trending_trades', 0) > 0:
                msg += f"\n⭐ **Market Status Analysis (7d):**\n"
                if stats.get('boosted_trades', 0) > 0:
                    msg += f"• Boosted Tokens: {stats.get('boosted_trades', 0)} trades\n"
                    msg += f"  - Win Rate: {stats.get('boosted_win_rate', 0):.1f}%\n"
                    msg += f"  - Avg Profit: {stats.get('boosted_avg_profit', 0)*100:+.2f}%\n"
                if stats.get('trending_trades', 0) > 0:
                    msg += f"• Trending Tokens: {stats.get('trending_trades', 0)} trades\n"
                    msg += f"  - Win Rate: {stats.get('trending_win_rate', 0):.1f}%\n"
                    msg += f"  - Avg Profit: {stats.get('trending_avg_profit', 0)*100:+.2f}%\n"
            
            # Recent Activity
            trade_history = stats.get('trading_history', {})
            if trade_history:
                msg += f"\n📝 **Recent Activity:**\n"
                msg += f"• Recent Trades: {trade_history.get('recent_trades_count', 0)}\n"
                msg += f"• Avg Recent Profit: {trade_history.get('avg_recent_profit', 0)*100:+.2f}%\n"
                msg += f"• Avg Recent Reward: {trade_history.get('avg_recent_reward', 0):.3f}\n"
                msg += f"• Avg Recent Duration: {trade_history.get('avg_recent_duration', 0):.1f} min\n"
            
            if not stats.get('model_trained', False):
                msg += f"\n⏳ **Status:** Model not yet trained\n"
                
                # Check if we should trigger initial training
                labeled_count = stats.get('labeled_samples', 0)
                if labeled_count == 0:
                    msg += f"🔥 **Triggering initial training data generation...**\n"
                    await update.message.reply_text(msg)
                    
                    # Trigger initial data generation and training
                    await self.self_learning_trader._generate_initial_training_data()
                    
                    # Get updated stats
                    updated_stats = self.self_learning_trader.get_training_stats()
                    follow_up_msg = f"\n✅ **Update:** Generated {updated_stats.get('labeled_samples', 0)} training samples\n"
                    
                    if updated_stats.get('model_trained', False):
                        follow_up_msg += f"🎯 **Model trained and ready for live trading!**"
                    else:
                        follow_up_msg += f"⏳ Waiting for more data to complete training..."
                    
                    await update.message.reply_text(follow_up_msg)
                    return
                    
                elif labeled_count < 50:
                    msg += f"Need {50 - labeled_count} more samples for initial training."
                else:
                    msg += f"Ready for training - use /retrain to train model"
            else:
                msg += f"\n🤖 **Status:** Active learning and live trading!"
                msg += f"\nModel continuously learns from new price data every {stats.get('learning_window_minutes', 20)} minutes."
            
            await update.message.reply_text(msg)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting ML stats: {e}")
    
    async def retrain_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """🔄 Force ML model retraining"""
        if update.effective_user.id != OWNER_ID:
            return
        
        try:
            await update.message.reply_text("🧠 Starting ML model retraining...")
            
            # Force retrain
            await self.self_learning_trader.train_model()
            
            stats = self.self_learning_trader.get_training_stats()
            await update.message.reply_text(
                f"✅ **Model Retrained Successfully!**\n\n"
                f"📊 Trained on {stats.get('labeled_samples', 0)} samples\n"
                f"🎯 Model Status: {'Active' if stats.get('model_trained') else 'Not Ready'}"
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Retraining failed: {e}")
    
    async def quickstart_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """⚡ Generate immediate training data for instant ML training"""
        if update.effective_user.id != OWNER_ID:
            return
        
        try:
            await update.message.reply_text("⚡ **Quick Start - Generating immediate training data...**\n\nThis will fetch historical token data and create hundreds of training samples instantly!")
            
            # Force immediate data generation
            from src.historical_data_generator import HistoricalDataGenerator
            generator = HistoricalDataGenerator(self.self_learning_trader)
            
            samples_generated = await generator.generate_immediate_training_data(batch_size=500)
            
            stats = self.self_learning_trader.get_training_stats()
            
            await update.message.reply_text(
                f"🚀 **Quick Start Complete!**\n\n"
                f"✅ Generated: {samples_generated} training samples\n"
                f"📊 Total Samples: {stats.get('labeled_samples', 0)}\n"
                f"🧠 Model Status: {'✅ Trained & Ready!' if stats.get('model_trained') else '⏳ Training...'}\n\n"
                f"**The AI system is now ready for immediate trading decisions!**"
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Quick start failed: {e}")
    
    async def clearmodel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """🗑️ Clear ML model and training data for fresh 80/20 training"""
        if update.effective_user.id != OWNER_ID:
            return
        
        try:
            await update.message.reply_text("🗑️ **Clearing ML model and training data...**\n\n⚠️ This will delete all trained models and start fresh!")
            
            # Clear the model from memory and files
            cleared = await self.self_learning_trader.clear_model()
            
            if cleared:
                await update.message.reply_text(
                    "✅ **Model Cleared Successfully!**\n\n"
                    f"🧠 All trained models deleted\n"
                    f"📊 Training data cleared\n"
                    f"🔄 System reset to fresh state\n\n"
                    f"**Use /mlstats to trigger fresh 80/20 training!**"
                )
            else:
                await update.message.reply_text("❌ Failed to clear model - check logs for details")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Clear model failed: {e}")
    
    async def addfunds_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add funds to paper trading account"""
        if update.effective_user.id != OWNER_ID:
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /addfunds <amount>\nExample: /addfunds 50")
            return
        
        try:
            amount = float(context.args[0])
            if amount <= 0:
                await update.message.reply_text("❌ Amount must be greater than 0")
                return
            
            if self.wallet_manager.paper_mode:
                self.wallet_manager.paper_trading.add_funds(amount, "Manual deposit via Telegram")
                new_balance = self.wallet_manager.paper_trading.get_balance()
                await update.message.reply_text(
                    f"✅ **Added {amount:.4f} SOL to paper trading account**\n\n"
                    f"New Balance: {new_balance:.4f} SOL"
                )
            else:
                await update.message.reply_text("❌ This command only works in paper trading mode")
                
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid number")
        except Exception as e:
            await update.message.reply_text(f"❌ Error adding funds: {e}")
    
    async def resetaccount_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reset paper trading account"""
        if update.effective_user.id != OWNER_ID:
            return
        
        if self.wallet_manager.paper_mode:
            # Get optional new balance from args
            new_balance = None
            if context.args:
                try:
                    new_balance = float(context.args[0])
                    if new_balance <= 0:
                        await update.message.reply_text("❌ Initial balance must be greater than 0")
                        return
                except ValueError:
                    await update.message.reply_text("❌ Please provide a valid number for initial balance")
                    return
            
            self.wallet_manager.paper_trading.reset_account(new_balance)
            balance = self.wallet_manager.paper_trading.get_balance()
            
            await update.message.reply_text(
                f"✅ **Paper trading account reset**\n\n"
                f"New Balance: {balance:.4f} SOL\n"
                f"All positions closed\n"
                f"Trade history cleared"
            )
        else:
            await update.message.reply_text("❌ This command only works in paper trading mode")
    
    async def portfolio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed portfolio summary"""
        if update.effective_user.id != OWNER_ID:
            return
        
        if self.wallet_manager.paper_mode:
            summary = self.wallet_manager.paper_trading.get_portfolio_summary()
            positions = self.wallet_manager.paper_trading.get_all_positions()
            
            msg = f"📊 **Paper Trading Portfolio**\n\n"
            msg += f"💰 **Balance**: {summary['current_balance']:.4f} SOL\n"
            msg += f"📈 **Performance**: {summary['performance_percentage']:+.2f}%\n"
            msg += f"💎 **Total P&L**: {summary['total_profit_loss']:+.4f} SOL\n"
            msg += f"📊 **Invested**: {summary['total_invested']:.4f} SOL\n"
            msg += f"🏦 **Portfolio Value**: {summary['total_portfolio_value']:.4f} SOL\n"
            msg += f"📈 **Total Trades**: {summary['total_trades']}\n\n"
            
            if positions:
                msg += f"🎯 **Active Positions** ({len(positions)}):\n"
                for i, (token_addr, pos) in enumerate(positions.items(), 1):
                    if i > 5:  # Limit to 5 positions for readability
                        msg += f"... and {len(positions) - 5} more\n"
                        break
                    symbol = pos.get('token_symbol', 'UNKNOWN')[:8]
                    invested = pos.get('entry_amount_sol', 0)
                    entry_price = pos.get('entry_price', 0)
                    msg += f"{i}. {symbol}: {invested:.3f} SOL @ ${entry_price:.6f}\n"
            else:
                msg += f"📝 No active positions\n"
            
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("❌ Portfolio summary only available in paper trading mode")
    
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
                        
                        # 🧠 NEW: Profit-Based Unsupervised Learning System
                        # Evaluate trading opportunity with flexible profit tracking
                        ml_decision = await self.self_learning_trader.evaluate_trade_opportunity(combined_data)
                        
                        if ml_decision['should_trade']:
                            logger.info(f"🤖 ML Trading opportunity: {token['symbol']} - Expected Profit: {ml_decision['expected_profit']:.1%} - Confidence: {ml_decision['confidence']:.2f}")
                            
                            # Log AI trade execution decision
                            ai_trader_logger.trade_execution(
                                action='buy',
                                token_address=token['address'],
                                amount=0.01,  # Fixed 1% position size for now
                                ai_confidence=ml_decision['confidence'],
                                reasoning=[ml_decision['reason']],
                                expected_outcome=f"expected_profit_{ml_decision['expected_profit']:.2%}"
                            )
                            
                            # Execute trade (real or paper mode handled by wallet manager)
                            trade_result = await self.wallet_manager.execute_trade(
                                token_address=token['address'],
                                amount_sol=0.01,  # Fixed 1% position
                                action='buy',
                                token_price=token.get('price_usd', 0),
                                token_symbol=token.get('symbol', 'UNKNOWN')
                            )
                            
                            # Log trade
                            self.trading_logger.log_trade(token, trade_result, ml_decision)
                            
                            # Note: No manual model update needed - the self-learning system
                            # automatically learns from price movements via price tracking!
                            
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
                BotCommand("mlstats", "Show ML model statistics and training status"),
                BotCommand("retrain", "Force ML model retraining"),
                BotCommand("quickstart", "Generate immediate training data"),
                BotCommand("clearmodel", "Clear ML model for fresh 80/20 training"),
                BotCommand("dump", "Emergency stop - close all positions"),
                BotCommand("addfunds", "Add SOL to paper trading account"),
                BotCommand("resetaccount", "Reset paper trading account"),
                BotCommand("portfolio", "Show detailed portfolio summary")
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
        application.add_handler(CommandHandler("mlstats", bot.ml_stats_command))
        application.add_handler(CommandHandler("retrain", bot.retrain_command))
        application.add_handler(CommandHandler("quickstart", bot.quickstart_command))
        application.add_handler(CommandHandler("clearmodel", bot.clearmodel_command))
        application.add_handler(CommandHandler("addfunds", bot.addfunds_command))
        application.add_handler(CommandHandler("resetaccount", bot.resetaccount_command))
        application.add_handler(CommandHandler("portfolio", bot.portfolio_command))
        
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