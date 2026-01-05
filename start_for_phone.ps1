# BILLESE - Start for Phone Testing
# This script starts both backend and frontend servers configured for phone access

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  BILLESE - Phone Testing Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get local IP address
$ip = $null
$adapters = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    ($_.InterfaceAlias -like "*Wi-Fi*" -or 
     $_.InterfaceAlias -like "*Ethernet*" -or 
     $_.InterfaceAlias -like "*Wireless*") -and
    $_.IPAddress -notlike "127.*" -and
    $_.IPAddress -notlike "169.254.*"
} | Select-Object -First 1

if ($adapters) {
    $ip = $adapters.IPAddress
} else {
    # Fallback: try to get any non-localhost IP
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*"
    } | Select-Object -First 1).IPAddress
}

if (-not $ip) {
    Write-Host "❌ Could not determine your IP address!" -ForegroundColor Red
    Write-Host "Please find your IP manually and update the .env file." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Run: ipconfig" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Detected IP Address: $ip" -ForegroundColor Green
Write-Host ""
Write-Host "📱 Access the app from your phone at:" -ForegroundColor Yellow
Write-Host "   http://$ip:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔧 Backend API will be at:" -ForegroundColor Yellow
Write-Host "   http://$ip:8000" -ForegroundColor Cyan
Write-Host ""

# Create/Update frontend .env file
$envFile = "frontend\.env"
$envContent = "VITE_API_URL=http://$ip:8000"

if (Test-Path $envFile) {
    $existing = Get-Content $envFile -Raw
    if ($existing -match "VITE_API_URL") {
        # Update existing
        $existing = $existing -replace "VITE_API_URL=.*", $envContent
        Set-Content $envFile $existing
        Write-Host "✅ Updated frontend/.env file" -ForegroundColor Green
    } else {
        # Append
        Add-Content $envFile "`n$envContent"
        Write-Host "✅ Added VITE_API_URL to frontend/.env file" -ForegroundColor Green
    }
} else {
    # Create new
    Set-Content $envFile $envContent
    Write-Host "✅ Created frontend/.env file" -ForegroundColor Green
}

Write-Host ""
Write-Host "🚀 Starting servers..." -ForegroundColor Yellow
Write-Host ""

# Start backend in a new window
Write-Host "Starting backend server (port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; Write-Host 'Backend Server (Port 8000)' -ForegroundColor Cyan; Write-Host 'Accessible at: http://$ip:8000' -ForegroundColor Green; Write-Host ''; uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

# Wait for backend to start
Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Start frontend
Write-Host "Starting frontend server (port 3000)..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Frontend Dev Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📱 Open on your phone: http://$ip:3000" -ForegroundColor Green
Write-Host "💻 Or on this computer: http://localhost:3000" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  If you can't access from Safari:" -ForegroundColor Yellow
Write-Host "   1. Make sure Windows Firewall allows port 3000" -ForegroundColor White
Write-Host "   2. Run setup_firewall.ps1 as Administrator" -ForegroundColor White
Write-Host "   3. Ensure phone and computer are on same Wi-Fi network" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the servers" -ForegroundColor Yellow
Write-Host ""

cd frontend

# Set environment variable to ensure host binding
$env:VITE_HOST = "0.0.0.0"

# Start Vite with explicit host binding
npm run dev -- --host 0.0.0.0

