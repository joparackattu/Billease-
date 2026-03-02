# Monitor GPU usage during training
# Run this in a separate terminal while training

Write-Host "Monitoring RTX 2050 GPU usage..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

while ($true) {
    Clear-Host
    Write-Host "RTX 2050 GPU Status:" -ForegroundColor Cyan
    Write-Host "===================" -ForegroundColor Cyan
    nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader,nounits
    Write-Host ""
    Write-Host "Updated: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Gray
    Start-Sleep -Seconds 2
}














