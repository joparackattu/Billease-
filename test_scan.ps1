# BILLESE - Quick Scan Test Script (PowerShell)
# Run this script to test the scanning feature

Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green
Write-Host "BILLESE - Scan Test" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green
Write-Host ""

# Check if server is running
Write-Host "Checking if server is running..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/" -Method GET -TimeoutSec 2
    Write-Host "✅ Server is running!" -ForegroundColor Green
} catch {
    Write-Host "❌ Server is NOT running!" -ForegroundColor Red
    Write-Host "Please start the server first:" -ForegroundColor Yellow
    Write-Host "  uvicorn main:app --reload" -ForegroundColor Cyan
    exit
}

Write-Host ""

# Get weight from user
$weight = Read-Host "Enter weight in grams (e.g., 200)"
if ([string]::IsNullOrWhiteSpace($weight)) {
    $weight = 200
    Write-Host "Using default weight: 200g" -ForegroundColor Yellow
}

# Get session ID
$sessionId = Read-Host "Enter session ID (press Enter for 'test')"
if ([string]::IsNullOrWhiteSpace($sessionId)) {
    $sessionId = "test"
}

Write-Host ""
Write-Host "📸 Capturing image from camera and detecting item..." -ForegroundColor Cyan
Write-Host ""

# Prepare request
$body = @{
    weight_grams = [float]$weight
} | ConvertTo-Json

$uri = "http://localhost:8000/scan-item?session_id=$sessionId"

try {
    # Make the request
    $response = Invoke-WebRequest -Uri $uri -Method POST -Body $body -ContentType "application/json"
    
    # Parse response
    $result = $response.Content | ConvertFrom-Json
    
    Write-Host "✅ Scan successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Detected Item:" -ForegroundColor Yellow
    Write-Host "  Name: $($result.detected_item.name)" -ForegroundColor White
    Write-Host "  Weight: $($result.detected_item.weight_grams) grams" -ForegroundColor White
    Write-Host "  Price per kg: ₹$($result.detected_item.price_per_kg)" -ForegroundColor White
    Write-Host "  Total Price: ₹$($result.detected_item.total_price)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Current Bill:" -ForegroundColor Yellow
    Write-Host "  Items: $($result.current_bill.Count)" -ForegroundColor White
    Write-Host "  Total: ₹$($result.bill_total)" -ForegroundColor Green
    Write-Host ""
    
    if ($result.current_bill.Count -gt 0) {
        Write-Host "Bill Items:" -ForegroundColor Yellow
        foreach ($item in $result.current_bill) {
            Write-Host "  - $($item.item_name): $($item.weight_grams)g = ₹$($item.total_price)" -ForegroundColor White
        }
    }
    
} catch {
    Write-Host "❌ Error occurred!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=" * 50 -ForegroundColor Green

