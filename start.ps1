# AI Novel Studio - One-Click Startup
# Usage: .\start.ps1
# Or:    powershell -ExecutionPolicy Bypass -File start.ps1

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

function Test-PortInUse {
    param([int]$Port)
    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
        return $null -ne $connection
    } catch {
        return $false
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI Novel Studio - Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ---------- Check Python venv ----------
$venvPython = Join-Path $ROOT ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Python venv not found" -ForegroundColor Red
    Write-Host "[FIX] Run: python -m venv .venv" -ForegroundColor Yellow
    Write-Host "[FIX] Then: .venv\Scripts\pip.exe install fastapi uvicorn sqlalchemy httpx pydantic python-dotenv" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Python: $( & $venvPython --version )" -ForegroundColor Green

# ---------- Check Node.js ----------
$nodeVersion = & { node --version 2>$null }
if (-not $nodeVersion) {
    Write-Host "[ERROR] Node.js not found" -ForegroundColor Red
    Write-Host "[FIX] Install from https://nodejs.org/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Node.js $nodeVersion" -ForegroundColor Green

# ---------- Check .env ----------
$envFile = Join-Path $ROOT ".env"
if (-not (Test-Path $envFile)) {
    @"
MODEL_PROVIDER=deepseek
MODEL_API_KEY=sk-your-key-here
MODEL_BASE_URL=https://api.deepseek.com/v1
MODEL_FLASH=deepseek-v4-flash
MODEL_PRO=deepseek-v4-pro
MODEL_TIMEOUT_SECONDS=60
DATABASE_URL=sqlite:///./ai_novel_studio.db
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
REACT_APP_API_BASE_URL=http://localhost:8000
"@ | Out-File -FilePath $envFile -Encoding ascii
    Write-Host "[WARN] Created .env - edit it to set MODEL_API_KEY" -ForegroundColor Yellow
}

$envContent = Get-Content $envFile -Raw
if ($envContent -match "MODEL_API_KEY=sk-your-key-here" -or $envContent -notmatch "MODEL_API_KEY=") {
    Write-Host "[WARN] MODEL_API_KEY is not configured. The app will start, but AI generation will fail until you set it." -ForegroundColor Yellow
}

# ---------- Install Python deps if needed ----------
& $venvPython -c "import fastapi, uvicorn, sqlalchemy, httpx, pydantic" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Installing Python dependencies..." -ForegroundColor Yellow
    $venvPip = Join-Path $ROOT ".venv\Scripts\pip.exe"
    & $venvPip install fastapi "uvicorn[standard]" sqlalchemy httpx pydantic python-dotenv 2>&1 | Out-Null
}
Write-Host "[OK] Python dependencies ready" -ForegroundColor Green

# ---------- Install npm deps if needed ----------
$webDir = Join-Path $ROOT "apps\web"
if (-not (Test-Path (Join-Path $webDir "node_modules"))) {
    Write-Host "[INFO] Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $webDir
    npm install 2>&1 | Out-Null
    Pop-Location
}
Write-Host "[OK] Frontend dependencies ready" -ForegroundColor Green

# ---------- Check ports ----------
if (Test-PortInUse 8000) {
    Write-Host "[WARN] Port 8000 is already in use. Backend may already be running or startup may fail." -ForegroundColor Yellow
}
if (Test-PortInUse 3000) {
    Write-Host "[WARN] Port 3000 is already in use. React may ask to use another port." -ForegroundColor Yellow
}

# ---------- Start Backend ----------
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Backend: http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$backendCmd = "cd `"$ROOT`"; & `"$venvPython`" -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host '=== AI Novel Studio Backend ===' -ForegroundColor Green; $backendCmd"

Write-Host "[INFO] Waiting for backend to start (3s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# ---------- Start Frontend ----------
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$frontendCmd = "cd `"$webDir`"; npm start"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host '=== AI Novel Studio Frontend ===' -ForegroundColor Green; $frontendCmd"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Start-Process "http://localhost:3000"
Read-Host "Press Enter to close this window (services keep running)"
