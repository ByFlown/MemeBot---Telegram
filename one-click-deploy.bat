@echo off
REM 🤖 MemeBot One-Click Deployment Script for Windows
REM Deploy to Fly.io without needing Python/pip locally

setlocal EnableDelayedExpansion

echo 🚀 MemeBot One-Click Deployment to Fly.io
echo ========================================
echo.

REM Check for PowerShell
where powershell >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ PowerShell not found! This script requires PowerShell.
    echo Please use Windows PowerShell or PowerShell Core.
    pause
    exit /b 1
)

REM Check if flyctl is installed
echo 🔍 Checking for flyctl CLI...
where flyctl >nul 2>nul
if %errorlevel% neq 0 (
    echo ⚠️ flyctl not found. Installing...
    echo.
    echo Please choose installation method:
    echo 1. Automatic installation via PowerShell ^(recommended^)
    echo 2. Manual installation instructions
    echo.
    set /p choice="Enter choice (1 or 2): "
    
    if "!choice!"=="1" (
        echo Installing flyctl via PowerShell...
        powershell -ExecutionPolicy Bypass -Command "iwr https://fly.io/install.ps1 -useb | iex"
        if !errorlevel! neq 0 (
            echo ❌ Installation failed. Please try manual installation.
            goto manual_install
        )
        
        REM Refresh PATH for current session
        call refreshenv >nul 2>nul || echo Note: You may need to restart your terminal for PATH changes to take effect.
        
        REM Check if installation was successful
        where flyctl >nul 2>nul
        if !errorlevel! neq 0 (
            echo ❌ Installation verification failed. Please restart your terminal and try again.
            echo Or install manually: https://github.com/superfly/flyctl/releases
            pause
            exit /b 1
        )
    ) else if "!choice!"=="2" (
        goto manual_install
    ) else (
        echo ❌ Invalid choice. Please run the script again.
        pause
        exit /b 1
    )
)

echo ✅ flyctl is available

REM Check authentication
echo 🔍 Checking Fly.io authentication...
flyctl auth whoami >nul 2>nul
if %errorlevel% neq 0 (
    echo ⚠️ Not authenticated with Fly.io
    echo Opening login page...
    flyctl auth login
    if !errorlevel! neq 0 (
        echo ❌ Login failed. Please try again.
        pause
        exit /b 1
    )
)

echo ✅ Authenticated with Fly.io

REM Validate fly.toml configuration
echo.
echo 🔍 Validating fly.toml configuration...
if not exist "fly.toml" (
    echo ❌ fly.toml not found in current directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Check for common TOML issues
findstr /C:"[mounts]" fly.toml >nul
if %errorlevel% equ 0 (
    echo ⚠️ Found potential TOML syntax issue in fly.toml
    echo Fixing mount sections...
    
    REM Create backup
    copy fly.toml fly.toml.backup >nul
    
    REM Fix mount sections (basic replacement)
    powershell -Command "(Get-Content fly.toml) -replace '^\[mounts\]', '[[mounts]]' | Set-Content fly.toml"
    
    echo ✅ Fixed mount section syntax
)

REM Validate with flyctl if possible
flyctl config validate >nul 2>nul
if %errorlevel% neq 0 (
    echo ⚠️ fly.toml has configuration issues
    echo Running flyctl config validate for details...
    flyctl config validate
    echo.
    set /p continue="Continue anyway? (y/N): "
    if /i "!continue!" neq "y" (
        echo Deployment cancelled
        pause
        exit /b 1
    )
) else (
    echo ✅ fly.toml configuration is valid
)

REM Check for .env file
if exist ".env" (
    echo ✅ Found .env file
    echo Current configuration:
    type .env | findstr /v "^#" | findstr "="
    echo.
    set /p use_env="Use this configuration? (Y/n): "
    if /i "!use_env!"=="n" goto collect_info
    if /i "!use_env!"=="no" goto collect_info
    
    REM Load .env file (simplified - only gets basic values)
    for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
        if "%%a"=="TELEGRAM_TOKEN" set TELEGRAM_TOKEN=%%b
        if "%%a"=="OWNER_ID" set OWNER_ID=%%b
        if "%%a"=="FLY_APP_NAME" set FLY_APP_NAME=%%b
        if "%%a"=="REAL_TRADING_ENABLED" set REAL_TRADING_ENABLED=%%b
        if "%%a"=="WEB_ADMIN_TOKEN" set WEB_ADMIN_TOKEN=%%b
    )
    goto validate_config
) else (
    echo ⚠️ No .env file found. Please configure manually.
)

:collect_info
echo.
echo 📋 Collecting deployment information...
echo.

REM App name with validation
:get_app_name
if "!FLY_APP_NAME!"=="" (
    echo.
    echo 📝 App Name Configuration
    echo App names must be:
    echo   - 3-30 characters long
    echo   - Only lowercase letters, numbers, and hyphens
    echo   - Unique across all Fly.io apps
    echo.
    echo Examples: memebot-ai, my-trading-bot, solana-trader-123
    echo.
    set /p FLY_APP_NAME="Enter app name (default: memebot-ai): "
    if "!FLY_APP_NAME!"=="" set FLY_APP_NAME=memebot-ai
)

REM Validate app name
echo !FLY_APP_NAME! | findstr /R "^[a-z0-9-]*$" >nul
if !errorlevel! neq 0 (
    echo ❌ Invalid app name. Use only lowercase letters, numbers, and hyphens.
    set FLY_APP_NAME=
    goto get_app_name
)

REM Check length
set app_name_length=0
set temp_name=!FLY_APP_NAME!
:count_loop
if defined temp_name (
    set temp_name=!temp_name:~1!
    set /a app_name_length+=1
    goto count_loop
)

if !app_name_length! lss 3 (
    echo ❌ App name must be at least 3 characters long.
    set FLY_APP_NAME=
    goto get_app_name
)

if !app_name_length! gtr 30 (
    echo ❌ App name must be less than 30 characters long.
    set FLY_APP_NAME=
    goto get_app_name
)

REM Check if app name is available
echo 🔍 Checking if app name '!FLY_APP_NAME!' is available...
flyctl apps list | findstr "!FLY_APP_NAME!" >nul
if !errorlevel! equ 0 (
    echo ⚠️ App name '!FLY_APP_NAME!' already exists in your account.
    set /p use_existing="Use existing app '!FLY_APP_NAME!'? (Y/n): "
    if /i "!use_existing!"=="n" (
        echo Please choose a different name.
        set FLY_APP_NAME=
        goto get_app_name
    )
) else (
    echo ✅ App name '!FLY_APP_NAME!' is available!
)

REM Telegram configuration
if "!TELEGRAM_TOKEN!"=="" (
    echo.
    echo 🤖 Telegram Bot Configuration
    echo Create a bot at: https://t.me/BotFather
    set /p TELEGRAM_TOKEN="Enter your Telegram Bot Token: "
)

if "!OWNER_ID!"=="" (
    echo Get your user ID from: https://t.me/userinfobot
    set /p OWNER_ID="Enter your Telegram User ID: "
)

REM Trading configuration
if "!REAL_TRADING_ENABLED!"=="" (
    echo.
    echo ⚠️ Trading Configuration
    set /p enable_real="Enable real trading? (DANGEROUS - start with 'n') [y/N]: "
    if /i "!enable_real!"=="y" (
        echo ⚠️ Real trading enabled! Make sure you understand the risks.
        set /p SOLANA_PRIVATE_KEY="Enter Solana private key (Base58): "
        set REAL_TRADING_ENABLED=true
    ) else (
        echo ✅ Paper trading mode (safe for testing)
        set REAL_TRADING_ENABLED=false
    )
)

REM Web interface
if "!WEB_ADMIN_TOKEN!"=="" (
    set /p WEB_ADMIN_TOKEN="Enter web admin token (default: admin123): "
    if "!WEB_ADMIN_TOKEN!"=="" set WEB_ADMIN_TOKEN=admin123
)

:validate_config
echo.
echo 🔍 Validating configuration...

if "!TELEGRAM_TOKEN!"=="" (
    echo ❌ Telegram token is required!
    pause
    exit /b 1
)

if "!OWNER_ID!"=="" (
    echo ❌ Owner ID is required!
    pause
    exit /b 1
)

if "!FLY_APP_NAME!"=="" set FLY_APP_NAME=memebot-ai
if "!WEB_ADMIN_TOKEN!"=="" set WEB_ADMIN_TOKEN=admin123

echo ✅ Configuration validated

REM Create or verify app
echo.
echo 🏗️ Setting up Fly.io app...
flyctl apps list | findstr "!FLY_APP_NAME!" >nul
if %errorlevel% equ 0 (
    echo ✅ App '!FLY_APP_NAME!' already exists
) else (
    echo 📝 Creating app '!FLY_APP_NAME!'...
    flyctl apps create "!FLY_APP_NAME!" --org personal
    if !errorlevel! neq 0 (
        echo ❌ Failed to create app '!FLY_APP_NAME!'
        echo.
        echo App name might be taken globally. Try these alternatives:
        echo   !FLY_APP_NAME!-%RANDOM%
        echo   !FLY_APP_NAME!-%USERNAME%
        echo   !FLY_APP_NAME!-trading
        echo   !FLY_APP_NAME!-bot
        echo.
        set /p new_name="Enter a different app name: "
        if "!new_name!" neq "" (
            set FLY_APP_NAME=!new_name!
            flyctl apps create "!FLY_APP_NAME!" --org personal
            if !errorlevel! neq 0 (
                echo ❌ Failed to create app with new name
                pause
                exit /b 1
            )
            echo ✅ App '!FLY_APP_NAME!' created!
        ) else (
            echo No alternative name provided
            pause
            exit /b 1
        )
    ) else (
        echo ✅ App '!FLY_APP_NAME!' created successfully!
    )
)

REM Update fly.toml with app name
echo 📝 Updating fly.toml configuration...
copy fly.toml fly.toml.backup >nul

REM Use PowerShell to update the TOML file
powershell -Command "(Get-Content fly.toml) -replace 'app = \".*\"', 'app = \"!FLY_APP_NAME!\"' | Set-Content fly.toml"
powershell -Command "(Get-Content fly.toml) -replace 'primary_region = \".*\"', 'primary_region = \"fra\"' | Set-Content fly.toml"

echo ✅ fly.toml updated with app: !FLY_APP_NAME!

REM Create volumes
echo.
echo 💾 Creating persistent volumes...
flyctl volumes create memebot_models --app "!FLY_APP_NAME!" --region fra --size 3 2>nul || echo Models volume might already exist
flyctl volumes create memebot_logs --app "!FLY_APP_NAME!" --region fra --size 2 2>nul || echo Logs volume might already exist  
flyctl volumes create memebot_data --app "!FLY_APP_NAME!" --region fra --size 1 2>nul || echo Data volume might already exist
echo ✅ Volumes created/verified

REM Set secrets
echo.
echo 🔐 Setting application secrets...
flyctl secrets set TELEGRAM_TOKEN="!TELEGRAM_TOKEN!" OWNER_ID="!OWNER_ID!" REAL_TRADING_ENABLED="!REAL_TRADING_ENABLED!" WEB_ADMIN_TOKEN="!WEB_ADMIN_TOKEN!" --app "!FLY_APP_NAME!"
if %errorlevel% neq 0 (
    echo ❌ Failed to set secrets
    pause
    exit /b 1
)

if not "!SOLANA_PRIVATE_KEY!"=="" (
    flyctl secrets set SOLANA_PRIVATE_KEY="!SOLANA_PRIVATE_KEY!" --app "!FLY_APP_NAME!"
)

echo ✅ Secrets configured

REM Deploy
echo.
echo 🚀 Deploying MemeBot to Fly.io...
echo This may take a few minutes...
flyctl deploy --app "!FLY_APP_NAME!" --remote-only
if %errorlevel% neq 0 (
    echo ❌ Deployment failed! Check the output above for details.
    pause
    exit /b 1
)

echo ✅ Deployment completed!

REM Health check
echo.
echo 🔍 Verifying deployment...
timeout /t 10 /nobreak >nul
flyctl status --app "!FLY_APP_NAME!"

REM Get app URL
for /f "tokens=2" %%i in ('flyctl info --app "!FLY_APP_NAME!" --json 2^>nul ^| findstr "Hostname"') do set APP_URL=%%i
set APP_URL=!APP_URL:"=!
set APP_URL=https://!APP_URL!

echo.
echo 🎉 MemeBot deployed successfully!
echo ================================
echo.
echo 📱 Telegram Bot: Test with /start
echo 🌐 Web Dashboard: !APP_URL!
echo 🔐 Admin Token: !WEB_ADMIN_TOKEN!
echo.
echo 📋 Useful commands:
echo   flyctl logs --app !FLY_APP_NAME!        # View logs
echo   flyctl status --app !FLY_APP_NAME!      # Check status  
echo   flyctl ssh console --app !FLY_APP_NAME! # SSH access
echo   flyctl apps restart !FLY_APP_NAME!      # Restart app
echo.
if "!REAL_TRADING_ENABLED!"=="true" (
    echo ⚠️ IMPORTANT: Real trading is ENABLED!
    echo    Monitor via web dashboard or Telegram
    echo    Start with small amounts
) else (
    echo ✅ Bot is in paper trading mode - safe for testing
)
echo.
echo ✅ Happy trading! 🚀💎

pause
exit /b 0

:manual_install
echo.
echo 📋 Manual Installation Instructions:
echo.
echo 1. Download flyctl from: https://github.com/superfly/flyctl/releases
echo 2. Extract to a folder in your PATH
echo 3. Or install via PowerShell: iwr https://fly.io/install.ps1 -useb ^| iex
echo 4. Or install via Chocolatey: choco install flyctl
echo 5. Or install via Scoop: scoop install flyctl
echo.
echo After installation, restart this script.
pause
exit /b 1