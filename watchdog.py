#!/usr/bin/env python3
"""
Watchdog script for MemeBot - Auto restart and error recovery
This script monitors the main bot process and restarts it if it crashes
"""

import subprocess
import time
import logging
import psutil
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import signal

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - WATCHDOG - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/watchdog.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotWatchdog:
    def __init__(self):
        self.bot_process = None
        self.restart_count = 0
        self.last_restart = None
        self.max_restarts_per_hour = 10
        self.bot_script = "main.py"
        self.restart_delay = 30  # seconds between restarts
        self.health_check_interval = 60  # seconds
        
        # Create logs directory
        Path("logs").mkdir(exist_ok=True)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down watchdog...")
        self.running = False
        if self.bot_process:
            self._stop_bot()
    
    def _start_bot(self):
        """Start the bot process"""
        try:
            logger.info("Starting MemeBot...")
            
            # Start the bot process
            self.bot_process = subprocess.Popen([
                sys.executable, self.bot_script
            ], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True
            )
            
            logger.info(f"MemeBot started with PID: {self.bot_process.pid}")
            
            # Update restart tracking
            self.restart_count += 1
            self.last_restart = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to start MemeBot: {e}")
            self.bot_process = None
    
    def _stop_bot(self):
        """Stop the bot process"""
        if self.bot_process:
            try:
                logger.info("Stopping MemeBot...")
                
                # Try graceful shutdown first
                self.bot_process.terminate()
                
                # Wait up to 30 seconds for graceful shutdown
                try:
                    self.bot_process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    logger.warning("Bot didn't shutdown gracefully, force killing...")
                    self.bot_process.kill()
                    self.bot_process.wait()
                
                logger.info("MemeBot stopped")
                
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")
            finally:
                self.bot_process = None
    
    def _is_bot_running(self) -> bool:
        """Check if bot process is running"""
        if not self.bot_process:
            return False
        
        # Check if process is still alive
        poll = self.bot_process.poll()
        return poll is None
    
    def _should_restart(self) -> bool:
        """Check if bot should be restarted"""
        # Don't restart if we're shutting down
        if not self.running:
            return False
        
        # Check restart rate limits
        if self.last_restart:
            hour_ago = datetime.now() - timedelta(hours=1)
            if self.last_restart > hour_ago and self.restart_count >= self.max_restarts_per_hour:
                logger.warning(f"Hit restart limit ({self.max_restarts_per_hour}/hour), waiting...")
                return False
        
        return True
    
    def _check_system_resources(self) -> bool:
        """Check if system has enough resources"""
        try:
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 95:
                logger.warning(f"High memory usage: {memory.percent}%")
                return False
            
            # Check disk space
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                logger.warning(f"High disk usage: {disk.percent}%")
                return False
            
            # Check if Python processes are consuming too much CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 95:
                logger.warning(f"High CPU usage: {cpu_percent}%")
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking system resources: {e}")
            return True  # Assume resources are OK if check fails
    
    def _cleanup_logs(self):
        """Clean up old log files to save disk space"""
        try:
            log_dir = Path("logs")
            if not log_dir.exists():
                return
            
            # Delete log files older than 30 days
            cutoff_time = time.time() - (30 * 24 * 60 * 60)  # 30 days in seconds
            
            for log_file in log_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    logger.info(f"Deleted old log file: {log_file}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up logs: {e}")
    
    def _health_check(self):
        """Perform health check on the bot"""
        try:
            if not self._is_bot_running():
                logger.warning("Bot process not running")
                return False
            
            # Check if bot is responsive (could implement API endpoint check)
            # For now, just check if process exists and is not consuming excessive resources
            
            try:
                process = psutil.Process(self.bot_process.pid)
                
                # Check memory usage of bot process
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                if memory_mb > 1000:  # 1GB memory limit
                    logger.warning(f"Bot using too much memory: {memory_mb:.1f}MB")
                    return False
                
                # Check CPU usage
                cpu_percent = process.cpu_percent()
                if cpu_percent > 50:  # 50% CPU limit
                    logger.warning(f"Bot using too much CPU: {cpu_percent:.1f}%")
                
                return True
                
            except psutil.NoSuchProcess:
                logger.warning("Bot process disappeared")
                return False
                
        except Exception as e:
            logger.error(f"Error during health check: {e}")
            return False
    
    def run(self):
        """Main watchdog loop"""
        logger.info("🐕 MemeBot Watchdog started")
        
        # Initial bot start
        self._start_bot()
        
        last_health_check = time.time()
        last_log_cleanup = time.time()
        
        while self.running:
            try:
                current_time = time.time()
                
                # Health check
                if current_time - last_health_check > self.health_check_interval:
                    if not self._health_check():
                        logger.warning("Health check failed, restarting bot...")
                        self._stop_bot()
                        
                        if self._should_restart():
                            time.sleep(self.restart_delay)
                            self._start_bot()
                        else:
                            logger.info("Restart rate limited, waiting...")
                    
                    last_health_check = current_time
                
                # Check if bot process ended unexpectedly
                if not self._is_bot_running() and self.running:
                    logger.warning("Bot process ended unexpectedly")
                    
                    # Get exit code and output
                    if self.bot_process:
                        exit_code = self.bot_process.poll()
                        logger.error(f"Bot exited with code: {exit_code}")
                        
                        # Log stderr output
                        try:
                            stderr_output = self.bot_process.stderr.read()
                            if stderr_output:
                                logger.error(f"Bot stderr: {stderr_output}")
                        except Exception:
                            pass
                    
                    if self._should_restart():
                        logger.info(f"Restarting bot in {self.restart_delay} seconds...")
                        time.sleep(self.restart_delay)
                        self._start_bot()
                    else:
                        logger.info("Restart rate limited, waiting...")
                
                # Log cleanup (once per day)
                if current_time - last_log_cleanup > 24 * 60 * 60:  # 24 hours
                    self._cleanup_logs()
                    last_log_cleanup = current_time
                
                # Check system resources periodically
                if not self._check_system_resources():
                    logger.warning("System resources low, waiting before restart...")
                    time.sleep(60)  # Wait 1 minute
                
                # Reset restart count every hour
                if self.last_restart and (datetime.now() - self.last_restart).total_seconds() > 3600:
                    self.restart_count = 0
                    self.last_restart = None
                
                time.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in watchdog loop: {e}")
                time.sleep(30)  # Wait before continuing
        
        # Cleanup
        logger.info("Shutting down watchdog...")
        self._stop_bot()
        logger.info("Watchdog stopped")

def main():
    """Main entry point"""
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Start watchdog
    watchdog = BotWatchdog()
    
    try:
        watchdog.run()
    except KeyboardInterrupt:
        logger.info("Watchdog interrupted by user")
    except Exception as e:
        logger.error(f"Watchdog crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()