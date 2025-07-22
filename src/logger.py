import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import asyncio

class TradingLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup file handlers
        self.trade_log_file = self.log_dir / "trades.jsonl"
        self.performance_log_file = self.log_dir / "performance.jsonl"
        self.error_log_file = self.log_dir / "errors.log"
        
        # Setup Python logging
        self.logger = logging.getLogger('TradingBot')
        self.logger.setLevel(logging.INFO)
        
        # File handler for errors
        error_handler = logging.FileHandler(self.error_log_file)
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        error_handler.setFormatter(error_formatter)
        self.logger.addHandler(error_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def log_trade(self, token_data: Dict, trade_result: Dict, decision_data: Dict):
        """Log a trade execution"""
        try:
            trade_entry = {
                'timestamp': datetime.now().isoformat(),
                'token': {
                    'address': token_data.get('address', ''),
                    'symbol': token_data.get('symbol', ''),
                    'name': token_data.get('name', '')
                },
                'decision': {
                    'should_trade': decision_data.get('should_trade', False),
                    'confidence': decision_data.get('confidence', 0.0),
                    'risk_score': decision_data.get('risk_score', 0.0),
                    'amount': decision_data.get('amount', 0.0),
                    'reasoning': decision_data.get('reasoning', '')
                },
                'market_data': {
                    'price_usd': token_data.get('price_usd', 0),
                    'volume_24h': token_data.get('volume_24h', 0),
                    'price_change_24h': token_data.get('price_change_24h', 0),
                    'liquidity_usd': token_data.get('liquidity_usd', 0),
                    'market_cap': token_data.get('market_cap', 0)
                },
                'onchain_data': {
                    'holder_count': token_data.get('holder_count', 0),
                    'risk_score': token_data.get('risk_score', 0),
                    'confidence_score': token_data.get('confidence_score', 0)
                },
                'execution': {
                    'success': trade_result.get('success', False),
                    'signature': trade_result.get('signature', ''),
                    'error': trade_result.get('error', ''),
                    'type': trade_result.get('type', 'unknown')
                }
            }
            
            # Write to trade log file
            with open(self.trade_log_file, 'a') as f:
                f.write(json.dumps(trade_entry) + '\n')
            
            # Log to console
            status = "✅ SUCCESS" if trade_result.get('success') else "❌ FAILED"
            self.logger.info(
                f"TRADE {status}: {token_data.get('symbol', 'UNKNOWN')} - "
                f"Confidence: {decision_data.get('confidence', 0):.2f} - "
                f"Amount: {decision_data.get('amount', 0):.4f} SOL"
            )
            
        except Exception as e:
            self.logger.error(f"Error logging trade: {e}")
    
    def log_performance(self, metrics: Dict):
        """Log performance metrics"""
        try:
            performance_entry = {
                'timestamp': datetime.now().isoformat(),
                'metrics': metrics
            }
            
            with open(self.performance_log_file, 'a') as f:
                f.write(json.dumps(performance_entry) + '\n')
            
            self.logger.info(f"Performance logged: {metrics}")
            
        except Exception as e:
            self.logger.error(f"Error logging performance: {e}")
    
    def log_error(self, error_type: str, error_message: str, context: Optional[Dict] = None):
        """Log an error with context"""
        try:
            error_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': error_type,
                'message': error_message,
                'context': context or {}
            }
            
            with open(self.error_log_file, 'a') as f:
                f.write(json.dumps(error_entry) + '\n')
            
            self.logger.error(f"{error_type}: {error_message}")
            
        except Exception as e:
            self.logger.error(f"Error logging error: {e}")
    
    def get_recent_logs(self, count: int = 10) -> List[Dict]:
        """Get recent trade logs"""
        try:
            logs = []
            
            if self.trade_log_file.exists():
                with open(self.trade_log_file, 'r') as f:
                    lines = f.readlines()
                    
                # Get last N lines
                recent_lines = lines[-count:] if len(lines) >= count else lines
                
                for line in recent_lines:
                    try:
                        entry = json.loads(line.strip())
                        logs.append({
                            'timestamp': entry.get('timestamp', ''),
                            'action': 'BUY' if entry.get('decision', {}).get('should_trade') else 'SKIP',
                            'symbol': entry.get('token', {}).get('symbol', ''),
                            'amount': entry.get('decision', {}).get('amount', 0),
                            'result': '✅ Success' if entry.get('execution', {}).get('success') else '❌ Failed',
                            'confidence': entry.get('decision', {}).get('confidence', 0)
                        })
                    except json.JSONDecodeError:
                        continue
            
            return logs
            
        except Exception as e:
            self.logger.error(f"Error getting recent logs: {e}")
            return []
    
    def get_performance_history(self, days: int = 30) -> List[Dict]:
        """Get performance history for specified days"""
        try:
            if not self.performance_log_file.exists():
                return []
            
            cutoff_date = datetime.now() - timedelta(days=days)
            performance_data = []
            
            with open(self.performance_log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_date = datetime.fromisoformat(entry['timestamp'])
                        
                        if entry_date >= cutoff_date:
                            performance_data.append(entry)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
            
            return performance_data
            
        except Exception as e:
            self.logger.error(f"Error getting performance history: {e}")
            return []
    
    def cleanup_old_logs(self, days_to_keep: int = 90):
        """Clean up old log files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Clean trade logs
            if self.trade_log_file.exists():
                self._cleanup_jsonl_file(self.trade_log_file, cutoff_date)
            
            # Clean performance logs
            if self.performance_log_file.exists():
                self._cleanup_jsonl_file(self.performance_log_file, cutoff_date)
            
            self.logger.info(f"Cleaned up logs older than {days_to_keep} days")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up logs: {e}")
    
    def _cleanup_jsonl_file(self, file_path: Path, cutoff_date: datetime):
        """Clean up a JSONL file by removing old entries"""
        try:
            temp_file = file_path.with_suffix('.tmp')
            entries_kept = 0
            
            with open(file_path, 'r') as infile, open(temp_file, 'w') as outfile:
                for line in infile:
                    try:
                        entry = json.loads(line.strip())
                        entry_date = datetime.fromisoformat(entry['timestamp'])
                        
                        if entry_date >= cutoff_date:
                            outfile.write(line)
                            entries_kept += 1
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
            
            # Replace original file with cleaned version
            temp_file.replace(file_path)
            
            self.logger.info(f"Kept {entries_kept} entries in {file_path.name}")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up {file_path}: {e}")
            # Remove temp file if it exists
            if temp_file.exists():
                temp_file.unlink()
    
    def export_logs_json(self, output_file: str, days: int = 30) -> bool:
        """Export logs to JSON file for analysis"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            export_data = {
                'export_date': datetime.now().isoformat(),
                'period_days': days,
                'trades': [],
                'performance': []
            }
            
            # Export trade logs
            if self.trade_log_file.exists():
                with open(self.trade_log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            entry_date = datetime.fromisoformat(entry['timestamp'])
                            
                            if entry_date >= cutoff_date:
                                export_data['trades'].append(entry)
                        except (json.JSONDecodeError, KeyError, ValueError):
                            continue
            
            # Export performance logs
            if self.performance_log_file.exists():
                with open(self.performance_log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            entry_date = datetime.fromisoformat(entry['timestamp'])
                            
                            if entry_date >= cutoff_date:
                                export_data['performance'].append(entry)
                        except (json.JSONDecodeError, KeyError, ValueError):
                            continue
            
            # Write export file
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            self.logger.info(f"Exported {len(export_data['trades'])} trades and {len(export_data['performance'])} performance entries to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting logs: {e}")
            return False