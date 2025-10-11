# Tag Sense AI - Launch Script
# This script starts both the Python backend and Tauri frontend

Write-Host "🚀 Starting Tag Sense AI..." -ForegroundColor Green
Write-Host "=" * 50

# Check if we're in the correct directory
if (-not (Test-Path "Sources\Backend\tagging_api.py")) {
    Write-Host "❌ Error: Please run this script from the Tag-Sense-AI root directory" -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    exit 1
}

# Check and activate virtual environment if it exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "🐍 Activating Python virtual environment..." -ForegroundColor Blue
    & .\.venv\Scripts\Activate.ps1
    
    # Install backend dependencies if requirements.txt exists
    if (Test-Path "Sources\Backend\requirements.txt") {
        Write-Host "📦 Checking Python dependencies..." -ForegroundColor Blue
        
        # Check if Flask is installed (key dependency)
        $flaskCheck = & python -c "import flask; print('Flask installed')" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Installing missing Python dependencies..." -ForegroundColor Yellow
            pip install -r Sources\Backend\requirements.txt
            if ($LASTEXITCODE -ne 0) {
                Write-Host "❌ Failed to install Python dependencies" -ForegroundColor Red
                exit 1
            }
            Write-Host "✅ Python dependencies installed!" -ForegroundColor Green
        } else {
            Write-Host "✅ Python dependencies already installed!" -ForegroundColor Green
        }
    }
} elseif (Test-Path ".venv\Scripts\activate.bat") {
    Write-Host "🐍 Activating Python virtual environment..." -ForegroundColor Blue
    & .\.venv\Scripts\activate.bat
    
    # Install backend dependencies if requirements.txt exists
    if (Test-Path "Sources\Backend\requirements.txt") {
        Write-Host "📦 Installing Python dependencies..." -ForegroundColor Blue
        pip install -r Sources\Backend\requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Failed to install Python dependencies" -ForegroundColor Red
            exit 1
        }
        Write-Host "✅ Python dependencies installed!" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  No virtual environment found. Using system Python..." -ForegroundColor Yellow
}

# Function to check if a port is in use
function Test-Port {
    param([int]$Port)
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("127.0.0.1", $Port)
        $connection.Close()
        return $true
    }
    catch {
        return $false
    }
}

# Check if Python backend is already running
if (Test-Port 5000) {
    Write-Host "⚠️  Python backend appears to be already running on port 5000" -ForegroundColor Yellow
    $response = Read-Host "Do you want to continue anyway? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Exiting..." -ForegroundColor Yellow
        exit 0
    }
}

# Check if Tauri dev server port is in use
if (Test-Port 1420) {
    Write-Host "⚠️  Tauri dev server appears to be already running on port 1420" -ForegroundColor Yellow
    $response = Read-Host "Do you want to continue anyway? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Exiting..." -ForegroundColor Yellow
        exit 0
    }
}

Write-Host ""
Write-Host "🐍 Starting Python Backend..." -ForegroundColor Blue
Write-Host "Backend will run on: http://127.0.0.1:5000" -ForegroundColor Cyan

# Start Python backend in a new PowerShell window
$backendPath = Join-Path $PWD "Sources\Backend"
if (Test-Path ".venv\Scripts\Activate.ps1") {
    $backendScript = "cd '$backendPath'; & '$PWD\.venv\Scripts\Activate.ps1'; python tagging_api.py"
} else {
    $backendScript = "cd '$backendPath'; python tagging_api.py"
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript -WindowStyle Normal

# Wait a moment for backend to start
Write-Host "⏳ Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "✅ Python backend should be running on http://127.0.0.1:5000" -ForegroundColor Green

Write-Host ""
Write-Host "🦀 Starting Tauri Frontend..." -ForegroundColor Blue
Write-Host "Frontend will run on: http://localhost:1420" -ForegroundColor Cyan

# Navigate to frontend directory and start Tauri
$frontendPath = Join-Path $PWD "Sources\Frontend\tauri-app"

try {
    Set-Location $frontendPath
    
    # Check if node_modules exists
    if (-not (Test-Path "node_modules")) {
        Write-Host "📦 Installing npm dependencies..." -ForegroundColor Yellow
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Failed to install npm dependencies" -ForegroundColor Red
            Set-Location $PWD
            exit 1
        }
    }
    
    Write-Host "🎯 Launching Tauri app..." -ForegroundColor Green
    Write-Host ""
    Write-Host "🔗 Services will be available at:" -ForegroundColor Cyan
    Write-Host "   Backend API: http://127.0.0.1:5000" -ForegroundColor White
    Write-Host "   Frontend:    http://localhost:1420" -ForegroundColor White
    Write-Host ""
    Write-Host "📝 To stop the services:" -ForegroundColor Yellow
    Write-Host "   - Close this window to stop the frontend" -ForegroundColor White
    Write-Host "   - Close the Python backend window" -ForegroundColor White
    Write-Host ""
    
    # Start Tauri (this will block until the app is closed)
    npm run tauri dev
    
}
catch {
    Write-Host "❌ Error starting frontend: $_" -ForegroundColor Red
}
finally {
    # Return to original directory
    Set-Location $PWD
}

Write-Host ""
Write-Host "👋 Tag Sense AI stopped. Goodbye!" -ForegroundColor Green