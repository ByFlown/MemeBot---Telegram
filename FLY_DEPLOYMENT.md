# 🚀 Fly.io Deployment Guide for MemeBot

Dieses Guide erklärt, wie du deinen MemeBot vollständig auf Fly.io hostest, inklusive aller KI-Modelle und Datenbank.

## ✅ Voraussetzungen

1. **Fly.io Account**: Registriere dich auf [fly.io](https://fly.io)
2. **flyctl CLI**: Installiere das Fly.io CLI Tool
3. **Telegram Bot**: Erstelle einen Bot über [@BotFather](https://t.me/BotFather)

## 📦 Installation von flyctl

### Windows (PowerShell):
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

### Linux/WSL:
```bash
curl -L https://fly.io/install.sh | sh
```

### macOS:
```bash
brew install flyctl
```

## 🔐 Fly.io Setup

### 1. Login
```bash
flyctl auth login
```

### 2. App erstellen (automatisch durch deploy.py)
```bash
flyctl apps create memebot-ai
```

## ⚙️ Konfiguration

### 1. Environment Variables konfigurieren
```bash
# Kopiere die Beispiel-Konfiguration
cp .env.example .env

# Bearbeite .env mit deinen echten Werten
nano .env
```

**Wichtige Variablen:**
```bash
TELEGRAM_TOKEN=your_bot_token_here
OWNER_ID=your_telegram_user_id
SOLANA_PRIVATE_KEY=your_base58_private_key  # Für echtes Trading
REAL_TRADING_ENABLED=false                  # Auf true für echtes Trading
PAPER_TRADING_ONLY=true                     # Auf false für echtes Trading
```

### 2. Fly.io Volumes (Persistente Speicherung)

Der Bot erstellt automatisch Volumes für:
- **Models**: KI-Modelle und Training-Daten (2GB)
- **Logs**: Trading-Logs und Performance-Daten (1GB)  
- **Data**: Allgemeine Daten und Cache (1GB)

## 🚀 Deployment

### Automatisches Deployment (Empfohlen):
```bash
python deploy.py
```

### Manuelles Deployment:

1. **Volumes erstellen:**
```bash
flyctl volumes create memebot_models --size 2
flyctl volumes create memebot_logs --size 1
flyctl volumes create memebot_data --size 1
```

2. **Secrets setzen:**
```bash
flyctl secrets set TELEGRAM_TOKEN="your_token_here"
flyctl secrets set OWNER_ID="your_telegram_id"
flyctl secrets set SOLANA_PRIVATE_KEY="your_private_key"
# ... weitere Secrets aus .env
```

3. **App deployen:**
```bash
flyctl deploy
```

## 📊 Monitoring & Verwaltung

### Status prüfen:
```bash
flyctl status
```

### Logs anzeigen:
```bash
# Aktuelle Logs
flyctl logs

# Live Logs verfolgen  
flyctl logs --follow

# Nur Fehler anzeigen
flyctl logs --level=error
```

### Health Check:
```bash
# Bot Status über HTTP
curl https://your-app.fly.dev/health
```

### SSH Zugang:
```bash
flyctl ssh console
```

## 💰 Kosten auf Fly.io

### Free Tier Limits:
- **2,340 Shared CPU hours/Monat** (kostenlos)
- **160GB Bandbreite/Monat**
- **3GB Persistente Volumes** (kostenlos)

### Für MemeBot:
- **Bot läuft 24/7**: ~720 Stunden/Monat ✅ **Kostenlos**
- **Memory**: 1GB RAM ✅ **Kostenlos**
- **Storage**: 4GB Volumes ✅ **Kostenlos** (3GB Free + 1GB ca. $0.15/Monat)
- **Bandbreite**: Minimal ✅ **Kostenlos**

**Total: ~$0-2/Monat** für vollständiges 24/7 Hosting!

## 🔧 Performance Optimierung

### 1. Resource Limits anpassen
```toml
# In fly.toml
[vm]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 1024  # Mehr Memory für große ML-Modelle
```

### 2. Regionale Verteilung
```toml
# Näher zu Solana RPC Endpoints
primary_region = "iad"  # US East für bessere Solana-Latenz
```

### 3. Auto-Scaling deaktivieren
```toml
[http_service]
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1
```

## 🛠️ Wartung & Updates

### 1. App Update deployen:
```bash
# Code-Änderungen deployen
flyctl deploy

# Neustart erzwingen
flyctl apps restart
```

### 2. Secrets aktualisieren:
```bash
flyctl secrets set NEW_SECRET="value"
flyctl secrets unset OLD_SECRET
```

### 3. Volumes verwalten:
```bash
# Volume Status
flyctl volumes list

# Volume erweitern
flyctl volumes extend <volume_id> --size 5
```

### 4. Backups:
```bash
# Volume Snapshots erstellen
flyctl volumes snapshots create <volume_id>

# Snapshots auflisten
flyctl volumes snapshots list
```

## 🐛 Troubleshooting

### Bot startet nicht:
```bash
# Logs prüfen
flyctl logs --level=error

# App Status prüfen
flyctl status

# Ins System einloggen
flyctl ssh console
```

### Memory/CPU Probleme:
```bash
# Resource Usage prüfen
flyctl ssh console
htop  # oder top

# Memory erhöhen in fly.toml
memory_mb = 2048
flyctl deploy
```

### Volume/Storage Probleme:
```bash
# Volume Status prüfen
flyctl volumes list

# SSH und Disk Space prüfen
flyctl ssh console
df -h
```

### Networking Issues:
```bash
# DNS/Connectivity testen
flyctl ssh console
ping api.mainnet-beta.solana.com
curl -I https://api.dexscreener.com
```

## 🔒 Sicherheit auf Fly.io

### 1. Secrets Management:
- **Niemals** Private Keys oder Tokens im Code
- Nutze `flyctl secrets` für sensible Daten
- Regelmäßig Secrets rotieren

### 2. Network Security:
- Bot läuft in isolierter VM
- Nur notwendige Ports offen (8080 für Health Check)
- HTTPS erzwungen

### 3. Resource Limits:
- Memory/CPU Limits gesetzt
- Volume-Größe begrenzt
- Auto-scaling kontrolliert

## 📈 Skalierung

### Horizontal Scaling:
```bash
# Mehr Instanzen (nur bei Bedarf)
flyctl scale count 2

# Zurück zu einer Instanz
flyctl scale count 1
```

### Vertical Scaling:
```bash
# Mehr CPU/Memory
flyctl scale vm performance-1x  # Dedicated CPU
flyctl scale memory 2048        # 2GB Memory
```

## 🎯 Best Practices

### 1. **Monitoring Setup:**
```bash
# Health Check überwachen
curl https://your-app.fly.dev/health

# Logs regelmäßig prüfen
flyctl logs --since=1h
```

### 2. **Resource Management:**
- KI-Modelle regelmäßig bereinigen
- Logs rotieren (automatisch implementiert)
- Unused Volumes löschen

### 3. **Development Workflow:**
```bash
# Local testen
python main.py

# Staging deployen
flyctl deploy

# Production überwachen
flyctl logs --follow
```

### 4. **Backup Strategy:**
- Volume Snapshots täglich
- Config in Git versioniert
- Secrets dokumentiert (sicher)

## 🆘 Support

### Fly.io Community:
- [Fly.io Community](https://community.fly.io)
- [Fly.io Documentation](https://fly.io/docs/)
- [Status Page](https://status.fly.io)

### Bot-spezifische Hilfe:
```bash
# Bot Status im Telegram: /status
# Bot Logs im Telegram: /logs  
# Health Check: https://your-app.fly.dev/health
```

---

## 🎉 Deployment Checklist

- [ ] flyctl installiert und eingeloggt
- [ ] .env mit echten Werten konfiguriert
- [ ] Telegram Bot erstellt und Token gesetzt
- [ ] Volumes erstellt (automatisch durch deploy.py)
- [ ] Secrets gesetzt (automatisch durch deploy.py)
- [ ] App deployed: `python deploy.py`
- [ ] Health Check funktioniert: `curl https://your-app.fly.dev/health`
- [ ] Bot antwortet auf `/start` in Telegram
- [ ] Logs sind sauber: `flyctl logs`

**Dein MemeBot läuft jetzt 24/7 auf Fly.io! 🚀💎**