# 🤖 MemeBot - AI Solana Trading Bot

Ein vollautomatischer KI-Trading-Bot für Solana Meme Coins mit maschinellem Lernen, Reinforcement Learning und umfassender Onchain-Analyse.

## ✨ Features

### ✅ Was der Bot kann:
- **24/7 Hosting** auf Fly.io (kostenlos)
- **Telegram Integration** mit umfangreichen Befehlen
- **DexScreener API** Integration für neue Token-Erkennung
- **Onchain-Analyse** mit Solscan, Birdeye & Helius APIs
- **KI-Trading** mit Reinforcement Learning (PPO/A2C)
- **Jupiter Aggregator** Integration für optimale Swaps
- **Backtesting** und Monte Carlo Simulationen
- **Performance Monitoring** mit detaillierten Metriken
- **Auto-Restart** System mit Watchdog
- **Umfassendes Logging** für alle Aktivitäten

### 🧠 KI & Machine Learning:
- **Reinforcement Learning** mit stable-baselines3
- **Random Forest** für Preisvorhersagen
- **Risk Assessment** Modelle
- **Adaptive Learning** basierend auf Trade-Erfolg
- **Feature Engineering** mit 20+ Indikatoren

### 🔍 Onchain-Analyse:
- **Holder-Verteilung** und Konzentrations-Analyse
- **Liquidity Tracking** und LP-Lock Detection
- **Dev Wallet** Aktivitäts-Monitoring
- **Social Metrics** Integration
- **Risk Scoring** (0-10 Skala)

## 🚀 Setup

### 1. Projekt klonen
```bash
git clone <your-repo>
cd "MemeBot - Telegram"
```

### 2. Dependencies installieren
```bash
pip install -r requirements.txt
```

### 3. Umgebungsvariablen konfigurieren
```bash
cp .env.example .env
# Bearbeite .env mit deinen echten Werten
```

### 4. Telegram Bot erstellen
1. Gehe zu [@BotFather](https://t.me/BotFather) auf Telegram
2. Erstelle einen neuen Bot: `/newbot`
3. Kopiere den Bot Token in `.env`
4. Finde deine Telegram User ID: [@userinfobot](https://t.me/userinfobot)

### 5. Solana Wallet (optional, für echtes Trading)
```bash
# Generiere ein neues Keypair oder nutze existierendes
# Konvertiere zu Base58 Format für SOLANA_PRIVATE_KEY
```

### 6. Bot starten
```bash
# Mit Watchdog (empfohlen)
python watchdog.py

# Oder direkt
python main.py
```

### 7. Auf Fly.io deployen
```bash
flyctl deploy
```

## 📱 Telegram Befehle

### Basis-Befehle:
- `/start` - Bot-Menü anzeigen
- `/status` - Bot Status und Statistiken
- `/wallet` - Wallet Informationen

### Trading-Kontrolle:
- `/realmode on|off` - Echtes Trading aktivieren/deaktivieren
- `/scan on|off` - Token-Scanning aktivieren/deaktivieren  
- `/setscan <minuten>` - Scan-Intervall setzen
- `/dump` - Notfall-Stop: alle Positionen schließen

### Analyse & Performance:
- `/top5` - Top 5 Trading-Gelegenheiten
- `/performance` - Performance Dashboard
- `/backtest` - Backtest über 30 Tage ausführen
- `/logs` - Aktuelle Trading-Logs

## ⚙️ Konfiguration

### Wichtige Parameter in `.env`:

```bash
# Sicherheit
REAL_TRADING_ENABLED=false          # Auf true setzen für echtes Trading
PAPER_TRADING_ONLY=true             # Paper Trading Modus
MAX_POSITION_SIZE_SOL=1.0           # Max SOL pro Trade
EMERGENCY_STOP_LOSS_PERCENT=50.0    # Notfall Stop-Loss

# KI Einstellungen  
MIN_CONFIDENCE_THRESHOLD=0.6         # Min. KI Vertrauen für Trades
MAX_RISK_THRESHOLD=7.0              # Max. Risk Score für Trades
SCAN_INTERVAL_MINUTES=5             # Scan-Intervall

# Trading
TRADING_FEE=0.0025                  # 0.25% Trading Gebühr
SLIPPAGE_TOLERANCE=0.005            # 0.5% Slippage Toleranz
```

## 🧪 Backtesting

```python
# Führe Backtest aus
from src.backtester import Backtester

backtester = Backtester(initial_balance=100.0)
results = await backtester.run_backtest(days=30)

# Monte Carlo Simulation
monte_carlo = await backtester.run_monte_carlo(num_simulations=1000)
```

## 📊 Performance Monitoring

Der Bot überwacht kontinuierlich:
- **Tägliche/Wöchentliche/Monatliche Performance**
- **Win Rate** und Erfolgsquote
- **Sharpe Ratio** für risikobereinigte Renditen
- **Maximum Drawdown**
- **Volatilität** und Risk-adjusted Returns

## 🔧 Erweiterte Features

### Reinforcement Learning
- **PPO (Proximal Policy Optimization)** für Trading-Entscheidungen
- **Custom Trading Environment** mit 20+ Features
- **Kontinuierliches Learning** basierend auf echten Trades
- **Reward Shaping** für optimale Belohnungsstrukturen

### Onchain-Integration
```python
# Beispiel Onchain-Analyse
from src.onchain_analyzer import OnchainAnalyzer

analyzer = OnchainAnalyzer()
analysis = await analyzer.analyze_token("TOKEN_ADDRESS")

print(f"Risk Score: {analysis['risk_score']}")
print(f"Holder Concentration: {analysis['holder_analysis']['holder_concentration']}")
```

### API Integration
- **DexScreener**: Neue Token-Erkennung
- **Solscan**: Onchain-Daten und Holder-Analyse  
- **Birdeye**: Liquidity und Trading-Daten
- **Jupiter**: Optimierte Swaps

## 🛡️ Sicherheitsfeatures

### Risk Management:
- **Position Size Limits**: Maximale SOL pro Trade
- **Portfolio Limits**: Gesamtportfolio-Begrenzung
- **Emergency Stop**: Sofortiger Verkauf aller Positionen
- **Rate Limiting**: Max. Trades pro Stunde
- **Risk Scoring**: Automatische Risikobewertung

### Monitoring:
- **Watchdog Process**: Auto-Restart bei Crashes
- **Health Checks**: Kontinuierliche System-Überwachung
- **Resource Monitoring**: CPU/Memory/Disk Usage
- **Error Handling**: Umfassendes Error-Logging

## 📁 Projekt-Struktur

```
MemeBot - Telegram/
├── main.py                 # Hauptbot-Datei
├── config.py              # Konfiguration
├── watchdog.py            # Auto-Restart System  
├── requirements.txt       # Python Dependencies
├── fly.toml              # Fly.io Konfiguration
├── .env.example          # Umgebungsvariablen Vorlage
├── src/                  # Quellcode Module
│   ├── scanner.py        # DexScreener Integration
│   ├── onchain_analyzer.py # Onchain-Analyse
│   ├── ai_trader.py      # KI Trading Logic
│   ├── wallet_manager.py # Solana Wallet & Jupiter
│   ├── backtester.py     # Backtesting System
│   ├── logger.py         # Trading Logger
│   └── performance_monitor.py # Performance Tracking
├── models/               # KI Modelle (auto-erstellt)
├── logs/                # Log-Dateien (auto-erstellt)  
└── data/                # Performance Daten (auto-erstellt)
```

## 🚨 Wichtige Hinweise

### ⚠️ Risiko-Warnung:
- **Kryptowährung Trading ist hochriskant**
- **Starte immer mit Paper Trading** (`PAPER_TRADING_ONLY=true`)
- **Teste ausgiebig** bevor du echtes Geld verwendest
- **Nutze nur Geld, das du verlieren kannst**
- **Meme Coins sind extrem volatil** und können zu 100% verloren gehen

### 🔒 Sicherheit:
- **Private Keys niemals teilen** oder committen
- **Environment Variables nutzen** für sensible Daten
- **Regelmäßige Updates** der Dependencies
- **Monitor deine Positionen** kontinuierlich

### 📈 Optimierung:
- **Backtests durchführen** bevor du live gehst
- **Parameter anpassen** basierend auf Performance
- **Monte Carlo Simulationen** für Risikobewertung
- **Logs analysieren** für Verbesserungen

## 🤝 Support

Bei Fragen oder Problemen:
1. Überprüfe die Logs in `/logs/`
2. Teste mit `DEBUG_MODE=true`
3. Führe Backtests durch zur Validierung
4. Nutze Paper Trading zum Testen

## 📜 Lizenz

Dieses Projekt ist nur für Bildungszwecke gedacht. Trading auf eigene Gefahr!

---

**Happy Trading! 🚀💎**

*Denk daran: Die beste Strategie ist oft, nichts zu tun. HODL! 💪*