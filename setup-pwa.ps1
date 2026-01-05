# BILLESE - PWA Setup Script
# This script helps set up the app as a Progressive Web App for iPhone

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  BILLESE - PWA Setup for iPhone" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "frontend")) {
    Write-Host "Error: frontend directory not found!" -ForegroundColor Red
    Write-Host "Please run this script from the project root directory." -ForegroundColor Yellow
    exit 1
}

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
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*"
    } | Select-Object -First 1).IPAddress
}

if (-not $ip) {
    Write-Host "Could not determine IP address automatically" -ForegroundColor Yellow
    Write-Host "Please enter your computer's IP address:" -ForegroundColor Yellow
    $ip = Read-Host "IP Address"
}

Write-Host ""
Write-Host "Detected IP Address: $ip" -ForegroundColor Green
Write-Host ""

# Check if icons exist
$icon192 = "frontend/public/pwa-192x192.png"
$icon512 = "frontend/public/pwa-512x512.png"
$appleIcon = "frontend/public/apple-touch-icon.png"

$iconsMissing = $false
if (-not (Test-Path $icon192)) {
    Write-Host "Missing: $icon192" -ForegroundColor Yellow
    $iconsMissing = $true
}
if (-not (Test-Path $icon512)) {
    Write-Host "Missing: $icon512" -ForegroundColor Yellow
    $iconsMissing = $true
}
if (-not (Test-Path $appleIcon)) {
    Write-Host "Missing: $appleIcon" -ForegroundColor Yellow
    $iconsMissing = $true
}

if ($iconsMissing) {
    Write-Host ""
    Write-Host "Icons are missing! You need to generate them first." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option 1: Use the icon generator" -ForegroundColor Cyan
    Write-Host "  1. Start dev server: cd frontend; npm run dev" -ForegroundColor White
    Write-Host "  2. Open: http://localhost:3000/generate-icons.html" -ForegroundColor White
    Write-Host "  3. Click Generate All Icons" -ForegroundColor White
    Write-Host "  4. Move downloaded icons to frontend/public/" -ForegroundColor White
    Write-Host ""
    Write-Host "Option 2: Create custom icons with sizes 192x192, 512x512, 180x180" -ForegroundColor Cyan
    Write-Host "  Place them in frontend/public/ folder" -ForegroundColor White
    Write-Host ""
    
    $continue = Read-Host "Have you generated the icons? (y/n)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        Write-Host "Please generate icons first, then run this script again." -ForegroundColor Yellow
        exit 1
    }
}

# Update .env file with IP
$envFile = "frontend\.env"
$envContent = "VITE_API_URL=http://$ip:8000"

if (Test-Path $envFile) {
    $existing = Get-Content $envFile -Raw
    if ($existing -match "VITE_API_URL") {
        $existing = $existing -replace "VITE_API_URL=.*", $envContent
        Set-Content $envFile $existing
    } else {
        Add-Content $envFile "`n$envContent"
    }
} else {
    Set-Content $envFile $envContent
}

Write-Host "Updated frontend/.env file" -ForegroundColor Green
Write-Host ""

# Build the app
Write-Host "Building app for production..." -ForegroundColor Yellow
cd frontend
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed! Please check the errors above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Build completed!" -ForegroundColor Green
Write-Host ""

# Instructions
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Start the backend server:" -ForegroundColor Yellow
Write-Host "   uvicorn main:app --host 0.0.0.0 --port 8000" -ForegroundColor White
Write-Host ""
Write-Host "2. Start the preview server (in another terminal):" -ForegroundColor Yellow
Write-Host "   cd frontend" -ForegroundColor White
Write-Host "   npm run preview -- --host" -ForegroundColor White
Write-Host ""
Write-Host "3. On your iPhone (Safari browser):" -ForegroundColor Yellow
Write-Host "   - Connect to the same Wi-Fi network" -ForegroundColor White
Write-Host "   - Open Safari and go to: http://$ip:4173" -ForegroundColor Cyan
Write-Host "   - Tap Share button, then Add to Home Screen" -ForegroundColor White
Write-Host "   - Tap Add" -ForegroundColor White
Write-Host ""
Write-Host "4. The app will appear on your home screen!" -ForegroundColor Green
Write-Host ""
Write-Host "For detailed instructions, see: INSTALL_AS_APP.md" -ForegroundColor Cyan
Write-Host ""
