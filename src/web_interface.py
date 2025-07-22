"""
Web interface for MemeBot management and monitoring
Accessible via Fly.io deployment without local Python
"""

import asyncio
import logging
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional
from aiohttp import web, ClientSession
from aiohttp_jinja2 import setup as jinja2_setup, template
import jinja2
import aiofiles
import base64

logger = logging.getLogger(__name__)

class WebInterface:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.app = web.Application()
        self.setup_routes()
        self.setup_templates()
        
        # Authentication
        self.admin_token = os.getenv('WEB_ADMIN_TOKEN', 'admin123')
    
    def setup_templates(self):
        """Setup Jinja2 templates"""
        jinja2_setup(
            self.app,
            loader=jinja2.DictLoader({
                'dashboard.html': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 MemeBot Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff; padding: 20px; min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { 
            background: rgba(255,255,255,0.1); backdrop-filter: blur(10px);
            padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.2);
        }
        .card h3 { color: #ffd700; margin-bottom: 15px; font-size: 1.3em; }
        .stat { display: flex; justify-content: space-between; margin-bottom: 10px; }
        .stat-value { font-weight: bold; color: #90ee90; }
        .controls { margin-bottom: 30px; }
        .btn { 
            background: #ff6b6b; color: white; border: none; padding: 12px 24px;
            border-radius: 8px; cursor: pointer; margin: 5px; font-size: 1em;
            transition: all 0.3s ease;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .btn.success { background: #51cf66; }
        .btn.warning { background: #ffd43b; color: #000; }
        .btn.danger { background: #ff6b6b; }
        .logs { 
            background: rgba(0,0,0,0.7); padding: 20px; border-radius: 10px;
            font-family: 'Courier New', monospace; font-size: 0.9em;
            max-height: 400px; overflow-y: auto;
        }
        .trading-controls { display: flex; gap: 10px; margin-bottom: 20px; }
        .performance-chart { background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; }
        @media (max-width: 768px) {
            .status-grid { grid-template-columns: 1fr; }
            .trading-controls { flex-direction: column; }
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 MemeBot Control Panel</h1>
            <p>Autonomous Solana Meme Coin Trading Bot</p>
        </div>

        <div class="status-grid">
            <div class="card">
                <h3>🏃‍♂️ Bot Status</h3>
                <div class="stat">
                    <span>Status:</span>
                    <span class="stat-value">{{ status.status|upper }}</span>
                </div>
                <div class="stat">
                    <span>Uptime:</span>
                    <span class="stat-value">{{ status.uptime }}</span>
                </div>
                <div class="stat">
                    <span>Mode:</span>
                    <span class="stat-value">{{ "🚨 REAL" if status.real_mode else "📝 PAPER" }}</span>
                </div>
                <div class="stat">
                    <span>Scanning:</span>
                    <span class="stat-value">{{ "🟢 ON" if status.scanning_active else "🔴 OFF" }}</span>
                </div>
            </div>

            <div class="card">
                <h3>📊 Performance</h3>
                <div class="stat">
                    <span>Total Trades:</span>
                    <span class="stat-value">{{ performance.total_trades }}</span>
                </div>
                <div class="stat">
                    <span>Win Rate:</span>
                    <span class="stat-value">{{ "%.1f"|format(performance.win_rate) }}%</span>
                </div>
                <div class="stat">
                    <span>24h Return:</span>
                    <span class="stat-value">{{ "%+.2f"|format(performance.daily_performance) }}%</span>
                </div>
                <div class="stat">
                    <span>Best Trade:</span>
                    <span class="stat-value">+{{ "%.2f"|format(performance.best_trade) }}%</span>
                </div>
            </div>

            <div class="card">
                <h3>💎 Wallet</h3>
                <div class="stat">
                    <span>SOL Balance:</span>
                    <span class="stat-value">{{ "%.4f"|format(wallet.sol_balance) }} SOL</span>
                </div>
                <div class="stat">
                    <span>Active Positions:</span>
                    <span class="stat-value">{{ wallet.active_positions }}</span>
                </div>
                <div class="stat">
                    <span>Status:</span>
                    <span class="stat-value">{{ "🟢 Connected" if wallet.connected else "🔴 Disconnected" }}</span>
                </div>
            </div>
        </div>

        <div class="controls">
            <h3>🎮 Trading Controls</h3>
            <div class="trading-controls">
                <button class="btn {{ 'danger' if status.real_mode else 'success' }}" onclick="toggleRealMode()">
                    {{ "🚨 Disable Real Trading" if status.real_mode else "💰 Enable Real Trading" }}
                </button>
                <button class="btn {{ 'warning' if status.scanning_active else 'success' }}" onclick="toggleScanning()">
                    {{ "⏸️ Pause Scanning" if status.scanning_active else "▶️ Resume Scanning" }}
                </button>
                <button class="btn danger" onclick="emergencyStop()">🛑 Emergency Stop</button>
                <button class="btn success" onclick="runBacktest()">📊 Run Backtest</button>
            </div>
        </div>

        <div class="card">
            <h3>📈 Performance Chart</h3>
            <canvas id="performanceChart" width="400" height="200"></canvas>
        </div>

        <div class="card">
            <h3>📝 Recent Activity</h3>
            <div class="logs" id="logs">
                {% for log in recent_logs %}
                <div>{{ log.timestamp }} - {{ log.action }} {{ log.symbol }} - {{ log.result }}</div>
                {% endfor %}
            </div>
        </div>
    </div>

    <script>
        // Chart setup
        const ctx = document.getElementById('performanceChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: {{ chart_labels|safe }},
                datasets: [{
                    label: 'Portfolio Value (%)',
                    data: {{ chart_data|safe }},
                    borderColor: '#90ee90',
                    backgroundColor: 'rgba(144, 238, 144, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { labels: { color: '#fff' } } },
                scales: {
                    x: { ticks: { color: '#fff' } },
                    y: { ticks: { color: '#fff' } }
                }
            }
        });

        // Control functions
        async function toggleRealMode() {
            const response = await fetch('/api/toggle-real-mode', { method: 'POST' });
            if (response.ok) location.reload();
        }

        async function toggleScanning() {
            const response = await fetch('/api/toggle-scanning', { method: 'POST' });
            if (response.ok) location.reload();
        }

        async function emergencyStop() {
            if (confirm('🚨 Emergency stop will close all positions! Continue?')) {
                const response = await fetch('/api/emergency-stop', { method: 'POST' });
                if (response.ok) {
                    alert('✅ Emergency stop executed!');
                    location.reload();
                }
            }
        }

        async function runBacktest() {
            document.querySelector('[onclick="runBacktest()"]').innerHTML = '⏳ Running...';
            const response = await fetch('/api/run-backtest', { method: 'POST' });
            const result = await response.json();
            alert(`📊 Backtest Complete!\\n30-day return: ${result.total_return.toFixed(2)}%`);
            location.reload();
        }

        // Auto-refresh every 30 seconds
        setInterval(() => location.reload(), 30000);
    </script>
</body>
</html>
                ''',
                
                'login.html': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 MemeBot Login</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; margin: 0;
        }
        .login-container { 
            background: rgba(255,255,255,0.1); backdrop-filter: blur(10px);
            padding: 40px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.2);
            text-align: center; color: white; min-width: 300px;
        }
        .login-container h1 { margin-bottom: 30px; font-size: 2em; }
        input { 
            width: 100%; padding: 15px; margin: 10px 0; border: none;
            border-radius: 10px; font-size: 1em; background: rgba(255,255,255,0.9);
        }
        button { 
            width: 100%; padding: 15px; background: #ff6b6b; color: white;
            border: none; border-radius: 10px; font-size: 1.1em; cursor: pointer;
            margin-top: 20px; transition: all 0.3s ease;
        }
        button:hover { transform: translateY(-2px); }
        .error { color: #ff6b6b; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🤖 MemeBot</h1>
        <p>Enter admin token to access dashboard</p>
        <form method="post">
            <input type="password" name="token" placeholder="Admin Token" required>
            <button type="submit">🚀 Login</button>
        </form>
        {% if error %}
        <div class="error">❌ {{ error }}</div>
        {% endif %}
    </div>
</body>
</html>
                '''
            })
        )
    
    def setup_routes(self):
        """Setup web routes"""
        self.app.router.add_get('/', self.dashboard)
        self.app.router.add_get('/login', self.login_page)
        self.app.router.add_post('/login', self.login_submit)
        self.app.router.add_get('/health', self.health_check)
        
        # API endpoints
        self.app.router.add_post('/api/toggle-real-mode', self.api_toggle_real_mode)
        self.app.router.add_post('/api/toggle-scanning', self.api_toggle_scanning)
        self.app.router.add_post('/api/emergency-stop', self.api_emergency_stop)
        self.app.router.add_post('/api/run-backtest', self.api_run_backtest)
        
        # Static content (if needed)
        self.app.router.add_static('/static/', path='static', name='static')
    
    def check_auth(self, request):
        """Check if user is authenticated"""
        token = request.cookies.get('admin_token')
        return token == self.admin_token
    
    @template('login.html')
    async def login_page(self, request):
        """Login page"""
        return {'error': request.query.get('error')}
    
    async def login_submit(self, request):
        """Handle login form submission"""
        try:
            data = await request.post()
            token = data.get('token')
            
            if token == self.admin_token:
                # Set secure cookie
                response = web.HTTPFound('/')
                response.set_cookie(
                    'admin_token', 
                    token, 
                    max_age=86400,  # 24 hours
                    httponly=True,
                    secure=True
                )
                return response
            else:
                return web.HTTPFound('/login?error=Invalid token')
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return web.HTTPFound('/login?error=Login failed')
    
    @template('dashboard.html')
    async def dashboard(self, request):
        """Main dashboard"""
        # Check authentication
        if not self.check_auth(request):
            return web.HTTPFound('/login')
        
        try:
            # Gather bot status data
            status = {
                'status': 'running',
                'uptime': str(datetime.now() - self.bot.start_time) if hasattr(self.bot, 'start_time') else 'Unknown',
                'real_mode': self.bot.real_mode,
                'scanning_active': self.bot.scanning_active
            }
            
            # Get performance metrics
            performance = await self.bot.performance_monitor.get_metrics()
            
            # Get wallet info
            wallet = await self.bot.wallet_manager.get_wallet_info()
            
            # Get recent logs
            recent_logs = self.bot.trading_logger.get_recent_logs(10)
            
            # Generate chart data (mock for now)
            chart_labels = [f"Day {i}" for i in range(1, 8)]
            chart_data = [0, 2.5, -1.2, 4.1, 3.8, -0.5, 2.3]
            
            return {
                'status': status,
                'performance': performance,
                'wallet': wallet,
                'recent_logs': recent_logs,
                'chart_labels': json.dumps(chart_labels),
                'chart_data': json.dumps(chart_data)
            }
            
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return {'error': str(e)}
    
    async def health_check(self, request):
        """Health check endpoint"""
        try:
            status = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'uptime': str(datetime.now() - self.bot.start_time) if hasattr(self.bot, 'start_time') else 'unknown',
                'real_mode': self.bot.real_mode,
                'scanning_active': self.bot.scanning_active,
                'total_trades': self.bot.total_trades,
                'successful_trades': self.bot.successful_trades
            }
            return web.json_response(status)
        except Exception as e:
            return web.json_response({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=500)
    
    async def api_toggle_real_mode(self, request):
        """Toggle real trading mode"""
        if not self.check_auth(request):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        try:
            if not self.bot.wallet_manager.is_configured():
                return web.json_response({'error': 'Wallet not configured'}, status=400)
            
            self.bot.real_mode = not self.bot.real_mode
            return web.json_response({
                'success': True,
                'real_mode': self.bot.real_mode,
                'message': f"Real trading {'enabled' if self.bot.real_mode else 'disabled'}"
            })
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def api_toggle_scanning(self, request):
        """Toggle token scanning"""
        if not self.check_auth(request):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        try:
            self.bot.scanning_active = not self.bot.scanning_active
            return web.json_response({
                'success': True,
                'scanning_active': self.bot.scanning_active,
                'message': f"Scanning {'enabled' if self.bot.scanning_active else 'disabled'}"
            })
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def api_emergency_stop(self, request):
        """Emergency stop all positions"""
        if not self.check_auth(request):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        try:
            if not self.bot.real_mode:
                return web.json_response({
                    'success': True,
                    'message': 'Paper trading mode - no real positions to close'
                })
            
            closed_positions = await self.bot.wallet_manager.close_all_positions()
            return web.json_response({
                'success': True,
                'positions_closed': len(closed_positions),
                'message': f'Emergency stop completed. Closed {len(closed_positions)} positions.'
            })
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def api_run_backtest(self, request):
        """Run backtest"""
        if not self.check_auth(request):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        try:
            results = await self.bot.backtester.run_backtest(days=30)
            return web.json_response({
                'success': True,
                'results': results
            })
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def start_server(self, port=8080):
        """Start the web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"Web interface started on port {port}")
        return runner