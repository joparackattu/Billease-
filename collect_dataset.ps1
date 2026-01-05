# BILLESE - Dataset Collection Helper Script
# Interactive script to capture images from camera for training dataset

Write-Host "=" * 60 -ForegroundColor Green
Write-Host "BILLESE - Dataset Collection Tool" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green
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

# Get class name
$className = Read-Host "Enter item class name (e.g., tomato, potato, cup)"
if ([string]::IsNullOrWhiteSpace($className)) {
    Write-Host "❌ Class name is required!" -ForegroundColor Red
    exit
}

# Get split
Write-Host ""
Write-Host "Image split:" -ForegroundColor Yellow
Write-Host "  [1] Train (for training - 80% of images)" -ForegroundColor White
Write-Host "  [2] Val (for validation - 20% of images)" -ForegroundColor White
$splitChoice = Read-Host "Choose (1 or 2, default: 1)"
$split = if ($splitChoice -eq "2") { "val" } else { "train" }

# Get number of images to capture
Write-Host ""
$count = Read-Host "How many images to capture? (default: 1)"
if ([string]::IsNullOrWhiteSpace($count) -or -not ($count -match '^\d+$')) {
    $count = 1
} else {
    $count = [int]$count
}

Write-Host ""
Write-Host "📸 Ready to capture $count image(s) for class '$className' ($split split)" -ForegroundColor Cyan
Write-Host "Make sure the item is clearly visible in the camera view!" -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Press Enter to start capturing (or 'q' to quit)"
if ($confirm -eq "q") { exit }

Write-Host ""

$successCount = 0
$failCount = 0

for ($i = 1; $i -le $count; $i++) {
    Write-Host "[$i/$count] Capturing image..." -ForegroundColor Cyan -NoNewline
    
    try {
        $uri = "http://localhost:8000/dataset/capture?class_name=$className&split=$split"
        $response = Invoke-WebRequest -Uri $uri -Method POST -TimeoutSec 10
        $result = $response.Content | ConvertFrom-Json
        
        if ($result.status -eq "success") {
            Write-Host " ✅ Saved!" -ForegroundColor Green
            Write-Host "   Total $className images: $($result.total_images_for_class)" -ForegroundColor Gray
            $successCount++
        } else {
            Write-Host " ❌ Failed: $($result.error)" -ForegroundColor Red
            $failCount++
        }
    } catch {
        Write-Host " ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
        $failCount++
    }
    
    # Wait between captures (except for last one)
    if ($i -lt $count) {
        Start-Sleep -Seconds 1
    }
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Green
Write-Host "Collection Complete!" -ForegroundColor Green
Write-Host "  ✅ Success: $successCount" -ForegroundColor Green
Write-Host "  ❌ Failed: $failCount" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Gray" })
Write-Host ""

# Show dataset stats
Write-Host "Current Dataset Statistics:" -ForegroundColor Yellow
try {
    $statsResponse = Invoke-WebRequest -Uri "http://localhost:8000/dataset/stats" -Method GET
    $stats = $statsResponse.Content | ConvertFrom-Json
    
    Write-Host "  Total images: $($stats.total_images)" -ForegroundColor White
    Write-Host "  Classes: $($stats.classes -join ', ')" -ForegroundColor White
    Write-Host ""
    Write-Host "  Train images:" -ForegroundColor Cyan
    foreach ($class in $stats.classes) {
        $trainCount = $stats.train_images.$class
        if ($trainCount) {
            Write-Host "    - $class : $trainCount images" -ForegroundColor White
        }
    }
    Write-Host ""
    Write-Host "  Val images:" -ForegroundColor Cyan
    foreach ($class in $stats.classes) {
        $valCount = $stats.val_images.$class
        if ($valCount) {
            Write-Host "    - $class : $valCount images" -ForegroundColor White
        }
    }
    Write-Host ""
    
    if ($stats.ready_for_training) {
        Write-Host "  ✅ Ready for training! (all classes have 50+ images)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Need more images (aim for 50+ per class)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Could not fetch stats" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Label images using LabelImg (see datasets/README.md)" -ForegroundColor White
Write-Host "  2. Train model: python train_model.py" -ForegroundColor White
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Green












