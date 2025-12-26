# Start Auto-Tagger
# This script starts both the backend API and the auto-tagger

Write-Host "Starting Tag Sense AI Auto-Tagger..." -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
$venvPath = ".venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & $venvPath
} else {
    Write-Host "Virtual environment not found. Creating one..." -ForegroundColor Yellow
    python -m venv .venv
    & $venvPath
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r Sources\Backend\requirements.txt
}

Write-Host ""
Write-Host "Checking backend status..." -ForegroundColor Yellow

# Check if backend is already running
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✓ Backend is already running" -ForegroundColor Green
} catch {
    Write-Host "Backend not running. Starting it now..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "IMPORTANT: Keep this window open!" -ForegroundColor Red
    Write-Host "  - Backend API will run in this window" -ForegroundColor White
    Write-Host "  - Auto-tagger will start after backend is ready" -ForegroundColor White
    Write-Host ""
    
    # Start backend in background job
    Start-Job -ScriptBlock {
        Set-Location (Join-Path $using:PWD "Sources\Backend")
        python tagging_api.py
    } | Out-Null
    
    # Wait for backend to be ready
    Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
    $maxAttempts = 10
    $attempt = 0
    $backendReady = $false
    
    while ($attempt -lt $maxAttempts -and -not $backendReady) {
        Start-Sleep -Seconds 1
        $attempt++
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/health" -TimeoutSec 2 -ErrorAction Stop
            $backendReady = $true
            Write-Host "✓ Backend is ready!" -ForegroundColor Green
        } catch {
            Write-Host "  Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
        }
    }
    
    if (-not $backendReady) {
        Write-Host "✗ Failed to start backend" -ForegroundColor Red
        Write-Host "Please start it manually: python Sources\Backend\tagging_api.py" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 58) -ForegroundColor Cyan
Write-Host " Starting Auto-Tagger " -ForegroundColor White -BackgroundColor DarkCyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 58) -ForegroundColor Cyan
Write-Host ""
Write-Host "Drop files into TestTagging folder to process them automatically" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start auto-tagger
Set-Location Sources\Backend
python auto_tagger.py
