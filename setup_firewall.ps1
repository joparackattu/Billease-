# BILLESE - Firewall Setup Script
# Run this script as Administrator to allow network access

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  BILLESE - Firewall Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click PowerShell and select 'Run as Administrator', then run this script again." -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

Write-Host "✅ Running as Administrator" -ForegroundColor Green
Write-Host ""

# Add firewall rule for Vite dev server (port 3000)
Write-Host "Adding firewall rule for port 3000 (Vite Dev Server)..." -ForegroundColor Yellow
try {
    $existingRule = netsh advfirewall firewall show rule name="Vite Dev Server Port 3000" 2>$null
    if ($existingRule) {
        Write-Host "⚠️  Firewall rule already exists for port 3000" -ForegroundColor Yellow
    } else {
        netsh advfirewall firewall add rule name="Vite Dev Server Port 3000" dir=in action=allow protocol=TCP localport=3000
        Write-Host "✅ Added firewall rule for port 3000" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Failed to add firewall rule: $_" -ForegroundColor Red
}

# Add firewall rule for FastAPI backend (port 8000)
Write-Host "Adding firewall rule for port 8000 (FastAPI Backend)..." -ForegroundColor Yellow
try {
    $existingRule = netsh advfirewall firewall show rule name="FastAPI Backend Port 8000" 2>$null
    if ($existingRule) {
        Write-Host "⚠️  Firewall rule already exists for port 8000" -ForegroundColor Yellow
    } else {
        netsh advfirewall firewall add rule name="FastAPI Backend Port 8000" dir=in action=allow protocol=TCP localport=8000
        Write-Host "✅ Added firewall rule for port 8000" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Failed to add firewall rule: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Firewall Setup Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now access the app from Safari on your phone!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run start_for_phone.ps1 to start the servers" -ForegroundColor White
Write-Host "2. Find your IP address (shown in the script output)" -ForegroundColor White
Write-Host "3. Open Safari on your phone and go to: http://YOUR_IP:3000" -ForegroundColor White
Write-Host ""
pause







