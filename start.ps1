# ============================================================
# Corgi Insurance Platform — Start Everything
# ============================================================
# Usage: .\start.ps1
#   -setup    First-time setup (install deps, DB, seed data)
#   -api      Start API only
#   -portal   Start Portal only
#   -admin    Start Admin only
#   -docker   Use Docker Compose instead of local processes
# ============================================================

param(
    [switch]$setup,
    [switch]$api,
    [switch]$portal,
    [switch]$admin,
    [switch]$docker
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# Colors
function Write-Step($msg) { Write-Host "`n🔧 $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "  ✅ $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  ⚠️  $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  ❌ $msg" -ForegroundColor Red }

# ────────────────────────────────────────────────────────────
# Dependency checks + auto-install
# ────────────────────────────────────────────────────────────
function Check-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

# Refresh PATH from the registry so newly installed tools are visible
# without requiring the user to open a new shell.
function Refresh-Path {
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath    = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path    = "$machinePath;$userPath"
}

function Install-WithWinget($packageId, $label) {
    if (-not (Check-Command "winget")) {
        Write-Err "winget not found. Install $label manually: https://aka.ms/winget-install"
        exit 1
    }
    Write-Host "  ⬇️  Installing $label via winget..." -ForegroundColor Cyan
    winget install --id $packageId --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Err "winget failed to install $label (exit $LASTEXITCODE). Install it manually and re-run."
        exit 1
    }
    Refresh-Path
}

function Ensure-Node {
    if (-not (Check-Command "node")) {
        Write-Warn "Node.js not found — installing automatically..."
        Install-WithWinget "OpenJS.NodeJS.LTS" "Node.js LTS"
        if (-not (Check-Command "node")) {
            Write-Err "Node.js still not found after install. Open a new terminal and re-run."
            exit 1
        }
        Write-OK "Node.js installed"
    }

    if (-not (Check-Command "pnpm")) {
        Write-Step "Activating pnpm via corepack..."
        corepack enable 2>&1 | Out-Null
        corepack prepare pnpm@9.15.0 --activate 2>&1 | Out-Null
        if (-not (Check-Command "pnpm")) {
            Write-Err "pnpm not available after corepack activation. Run: corepack enable; corepack prepare pnpm@9.15.0 --activate"
            exit 1
        }
        Write-OK "pnpm activated"
    }
}

function Ensure-Python {
    if (Check-Command "python") {
        # pip ships with Python, but is absent on broken/minimal installs.
        # Treat a missing pip the same as a missing Python — reinstall cleanly.
        if (-not (Check-Command "pip")) {
            Write-Warn "pip not found — reinstalling Python to get a clean install with pip..."
            Install-WithWinget "Python.Python.3.12" "Python 3.12"
            Refresh-Path
            if (-not (Check-Command "pip")) {
                Write-Err "pip still not available after reinstall. Check your Python installation."
                exit 1
            }
            Write-OK "Python reinstalled with pip"
        }
        return
    }

    Write-Warn "Python not found — installing automatically..."
    Install-WithWinget "Python.Python.3.12" "Python 3.12"

    # winget installs the 'python3' alias; also check 'python'
    Refresh-Path
    if (-not (Check-Command "python") -and (Check-Command "python3")) {
        # Create a small wrapper so the rest of the script can call 'python'
        $wrapperDir = "$env:LOCALAPPDATA\Programs\PythonWrapper"
        New-Item -ItemType Directory -Force -Path $wrapperDir | Out-Null
        @"
@echo off
python3 %*
"@ | Set-Content "$wrapperDir\python.cmd"
        $env:Path = "$wrapperDir;$env:Path"
    }

    if (-not (Check-Command "python")) {
        Write-Err "Python still not found after install. Open a new terminal and re-run."
        exit 1
    }

    if (-not (Check-Command "pip")) {
        Write-Err "pip still not available after install. Check your Python installation."
        exit 1
    }

    Write-OK "Python + pip installed"
}

function Ensure-Dependencies {
    Write-Step "Checking dependencies..."

    Ensure-Node
    Ensure-Python

    if ($docker -and -not (Check-Command "docker")) {
        Write-Err "Docker is required for -docker mode but was not found."
        Write-Host "  Install Docker Desktop from https://docker.com and re-run." -ForegroundColor Red
        exit 1
    }

    $nodeVer = (node --version) -replace 'v',''
    $pyVer   = python --version 2>&1 | Select-String -Pattern '(\d+\.\d+)' | ForEach-Object { $_.Matches[0].Value }
    Write-OK "Node.js $nodeVer"
    Write-OK "Python $pyVer  (pip $(pip --version | Select-String -Pattern '(\d+\.\d+)' | ForEach-Object { $_.Matches[0].Value }))"
    if (Check-Command "docker") {
        Write-OK "Docker $(docker --version | Select-String -Pattern '(\d+\.\d+\.\d+)' | ForEach-Object { $_.Matches[0].Value })"
    }
}

# ────────────────────────────────────────────────────────────
# Setup (first-time install)
# ────────────────────────────────────────────────────────────
function Run-Setup {
    Write-Step "Installing Portal dependencies..."
    Push-Location "$root\portal"
    pnpm install
    Write-OK "Portal deps installed"
    Pop-Location

    Write-Step "Installing Admin Dashboard dependencies..."
    Push-Location "$root\admin"
    pnpm install
    Write-OK "Admin deps installed"
    Pop-Location

    Write-Step "Setting up API..."
    Push-Location "$root\api"
    
    if (-not (Test-Path "venv")) {
        Write-Step "Creating Python virtual environment..."
        python -m venv venv
        Write-OK "venv created"
    }
    
    # Activate venv
    & "$root\api\venv\Scripts\Activate.ps1"
    
    Write-Step "Installing Python dependencies..."
    pip install -r requirements.txt
    Write-OK "Python deps installed"
    
    Pop-Location

    # Create .env files if they don't exist
    Write-Step "Setting up environment files..."
    
    if (-not (Test-Path "$root\api\.env")) {
        @"
DJANGO_SECRET_KEY=local-dev-secret-key-$(Get-Random -Maximum 999999)
DJANGO_DEBUG=True
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=corgi
DATABASE_USER=corgi_admin
DATABASE_PASSWORD=Corg1Secure2026x
ALLOWED_HOSTS=*
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
JWT_SECRET_KEY=local-dev-jwt-secret-$(Get-Random -Maximum 999999)
CORGI_PORTAL_URL=http://localhost:3000
# REDIS_URL=redis://localhost:6379/0
# STRIPE_SECRET_KEY=
# STRIPE_WEBHOOK_SECRET=
# RESEND_API_KEY=
# S3_ACCESS_KEY_ID=
# S3_SECRET_ACCESS_KEY=
# S3_BUCKET_NAME=
# OPENAI_API_KEY=
# SENTRY_DSN=
# HUBSPOT_ACCESS_TOKEN=
# HUBSPOT_PIPELINE_ID=default
# HUBSPOT_WEBHOOK_SECRET=
"@ | Set-Content "$root\api\.env"
        Write-OK "api/.env created (default creds: corgi_admin / [see .env] / corgi)"
    } else { Write-OK "api/.env exists" }

    if (-not (Test-Path "$root\portal\.env.local")) {
        @"
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STRIPE_KEY=pk_test_xxx
NEXT_PUBLIC_SENTRY_DSN=
"@ | Set-Content "$root\portal\.env.local"
        Write-OK "portal/.env.local created"
    } else { Write-OK "portal/.env.local exists" }

    if (-not (Test-Path "$root\admin\.env")) {
        @"
VITE_API_URL=http://localhost:8000
VITE_SENTRY_DSN=
"@ | Set-Content "$root\admin\.env"
        Write-OK "admin/.env created"
    } else { Write-OK "admin/.env exists" }

    # ── Start PostgreSQL via Docker ──
    Write-Step "Starting PostgreSQL..."
    $dbRunning = docker ps --filter "name=corgi-db" --format "{{.Names}}" 2>$null
    if ($dbRunning -eq "corgi-db") {
        Write-OK "PostgreSQL already running (corgi-db)"
    } else {
        $dbExists = docker ps -a --filter "name=corgi-db" --format "{{.Names}}" 2>$null
        if ($dbExists -eq "corgi-db") {
            docker start corgi-db | Out-Null
            Write-OK "PostgreSQL started (existing container)"
        } else {
            Write-Host "    Pulling image + starting container (first time may take a minute)..." -ForegroundColor DarkGray
            docker run -d --name corgi-db -e POSTGRES_USER=corgi_admin -e POSTGRES_PASSWORD=Corg1Secure2026x -e POSTGRES_DB=corgi -p 5432:5432 postgres:14
            Write-OK "PostgreSQL container created"
            Write-Step "Waiting for PostgreSQL to accept connections..."
            $ready = $false
            for ($i = 0; $i -lt 30; $i++) {
                Start-Sleep -Seconds 2
                try {
                    $result = docker exec corgi-db pg_isready -U corgi_admin 2>&1
                    if ($result -match "accepting connections") { $ready = $true; break }
                } catch {}
                Write-Host "    Waiting... ($($i*2+2)s)" -ForegroundColor DarkGray
            }
            if ($ready) { Write-OK "PostgreSQL is ready" }
            else { Write-Warn "PostgreSQL may still be starting — continuing anyway" }
        }
    }

    # ── Start Redis via Docker ──
    Write-Step "Starting Redis..."
    $redisRunning = docker ps --filter "name=corgi-redis" --format "{{.Names}}" 2>$null
    if ($redisRunning -eq "corgi-redis") {
        Write-OK "Redis already running (corgi-redis)"
    } else {
        $redisExists = docker ps -a --filter "name=corgi-redis" --format "{{.Names}}" 2>$null
        if ($redisExists -eq "corgi-redis") {
            docker start corgi-redis | Out-Null
            Write-OK "Redis started (existing container)"
        } else {
            Write-Host "    Pulling image + starting container..." -ForegroundColor DarkGray
            docker run -d --name corgi-redis -p 6379:6379 redis:7-alpine
            Write-OK "Redis started (new container on :6379)"
        }
    }

    # ── Run migrations ──
    $venvPython = "$root\api\venv\Scripts\python.exe"
    Write-Step "Checking for model changes..."
    Push-Location "$root\api"
    & $venvPython manage.py makemigrations --check 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Model changes detected — generating migrations..."
        & $venvPython manage.py makemigrations
    } else {
        Write-OK "Models up to date"
    }
    Write-Step "Running database migrations..."
    & $venvPython manage.py migrate 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Migrations FAILED (exit code $LASTEXITCODE)"
        Write-Host "    Check your database connection settings in api/.env" -ForegroundColor Red
        Write-Host "    Expected: DATABASE_USER=corgi_admin  DATABASE_PASSWORD=Corg1Secure2026x  DATABASE_NAME=corgi" -ForegroundColor Red
        Write-Host "    Make sure PostgreSQL is running and these credentials match." -ForegroundColor Red
        exit 1
    }
    Write-OK "Migrations complete"

    # ── Seed form data ──
    Write-Step "Seeding form definitions (8 coverage types)..."
    & $venvPython manage.py seed_forms 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Form seeding failed — you may need to run this manually later"
    } else {
        Write-OK "Form data seeded"
    }

    # ── Seed platform config ──
    Write-Step "Seeding platform config (limits, carriers, etc.)..."
    & $venvPython manage.py seed_platform_config 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Platform config seeding failed — run manually: python manage.py seed_platform_config"
    } else {
        Write-OK "Platform config seeded"
    }

    # ── Seed role accounts for quick login ──
    Write-Step "Seeding role accounts (admin, ae, broker, etc.)..."
    & $venvPython manage.py shell -c "exec(open('seed_roles.py').read())" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Role seeding failed — you can run manually: python manage.py shell < seed_roles.py"
    } else {
        Write-OK "Role accounts seeded (password: corgi123)"
    }
    Pop-Location

    # ── Create superuser (interactive) ──
    Write-Step "Create admin superuser"
    $createAdmin = Read-Host "  Create a superuser now? (y/N)"
    if ($createAdmin -eq 'y' -or $createAdmin -eq 'Y') {
        Push-Location "$root\api"
        & $venvPython manage.py createsuperuser
        Pop-Location
    } else {
        Write-Warn "Skipped — run 'cd api && python manage.py createsuperuser' later"
    }

    Write-Host "`n✅ Setup complete! Starting servers...`n" -ForegroundColor Green

    # After setup, start everything — use script scope so main block sees this
    $script:postSetupStartAll = $true
}

# ────────────────────────────────────────────────────────────
# Docker mode
# ────────────────────────────────────────────────────────────
function Start-Docker {
    Write-Step "Starting all services with Docker Compose..."
    Push-Location $root
    docker compose up --build
    Pop-Location
}

# ────────────────────────────────────────────────────────────
# Start individual services
# ────────────────────────────────────────────────────────────
function Start-API {
    Write-Step "Starting API server (http://localhost:8000)..."
    $job = Start-Process powershell -ArgumentList @(
        "-NoProfile", "-Command",
        "Set-Location '$root\api'; & '$root\api\venv\Scripts\python.exe' manage.py runserver 0.0.0.0:8000"
    ) -PassThru -WindowStyle Normal
    Write-OK "API started (PID: $($job.Id))"
    return $job
}

function Start-Portal {
    Write-Step "Starting Portal (http://localhost:3000)..."
    $job = Start-Process powershell -ArgumentList @(
        "-NoProfile", "-Command",
        "Set-Location '$root\portal'; pnpm run dev"
    ) -PassThru -WindowStyle Normal
    Write-OK "Portal started (PID: $($job.Id))"
    return $job
}

function Start-Admin {
    Write-Step "Starting Admin Dashboard (http://localhost:3001)..."
    $job = Start-Process powershell -ArgumentList @(
        "-NoProfile", "-Command",
        "Set-Location '$root\admin'; pnpm run dev -- --port 3001"
    ) -PassThru -WindowStyle Normal
    Write-OK "Admin started (PID: $($job.Id))"
    return $job
}

# ────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────

Write-Host @"

   ██████╗ ██████╗ ██████╗  ██████╗ ██╗
  ██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██║
  ██║     ██║   ██║██████╔╝██║  ███╗██║
  ██║     ██║   ██║██╔══██╗██║   ██║██║
  ╚██████╗╚██████╔╝██║  ██║╚██████╔╝██║
   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝
   Insurance Platform

"@ -ForegroundColor DarkYellow

Ensure-Dependencies

$script:postSetupStartAll = $false

if ($setup) {
    Run-Setup
}

if ($docker) {
    Start-Docker
    exit 0
}

# Ensure DB + Redis are running
if (-not $docker) {
    $dbRunning = docker ps --filter "name=corgi-db" --format "{{.Names}}" 2>$null
    if ($dbRunning -ne "corgi-db") {
        Write-Step "Starting PostgreSQL..."
        $dbExists = docker ps -a --filter "name=corgi-db" --format "{{.Names}}" 2>$null
        if ($dbExists -eq "corgi-db") { docker start corgi-db | Out-Null }
        else { docker run -d --name corgi-db -e POSTGRES_USER=corgi_admin -e POSTGRES_PASSWORD=Corg1Secure2026x -e POSTGRES_DB=corgi -p 5432:5432 postgres:14 | Out-Null }
        Start-Sleep -Seconds 2
        Write-OK "PostgreSQL running"
    }
    $redisRunning = docker ps --filter "name=corgi-redis" --format "{{.Names}}" 2>$null
    if ($redisRunning -ne "corgi-redis") {
        Write-Step "Starting Redis..."
        $redisExists = docker ps -a --filter "name=corgi-redis" --format "{{.Names}}" 2>$null
        if ($redisExists -eq "corgi-redis") { docker start corgi-redis | Out-Null }
        else { docker run -d --name corgi-redis -p 6379:6379 redis:7-alpine | Out-Null }
        Write-OK "Redis running"
    }
}

# Selective start or start all
# If Run-Setup just completed, start everything regardless of flags
$startAll = $script:postSetupStartAll -or -not ($api -or $portal -or $admin)
$jobs = @()

if ($api -or $startAll)    { $jobs += Start-API }
if ($portal -or $startAll) { $jobs += Start-Portal }
if ($admin -or $startAll)  { $jobs += Start-Admin }

Write-Host "`n" -NoNewline
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""
if ($startAll -or $api)    { Write-Host "  🔶 API:    http://localhost:8000" -ForegroundColor Yellow }
if ($startAll -or $api)    { Write-Host "  🔶 Admin:  http://localhost:8000/admin/" -ForegroundColor Yellow }
if ($startAll -or $portal) { Write-Host "  🟠 Portal: http://localhost:3000" -ForegroundColor DarkYellow }
if ($startAll -or $admin)  { Write-Host "  📊 Ops:    http://localhost:3001" -ForegroundColor DarkYellow }
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Press Ctrl+C to stop all services" -ForegroundColor DarkGray
Write-Host ""

# Wait for Ctrl+C
try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    Write-Host "`n🛑 Stopping services..." -ForegroundColor Yellow
    $jobs | ForEach-Object { 
        if (-not $_.HasExited) { 
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            # Also kill child processes
            Get-Process | Where-Object { $_.Parent.Id -eq $_.Id } | Stop-Process -Force -ErrorAction SilentlyContinue
        }
    }
    Write-OK "All services stopped"
}

