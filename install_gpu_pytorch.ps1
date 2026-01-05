# Install PyTorch with CUDA support for RTX 2050

Write-Host "Installing PyTorch with CUDA support..." -ForegroundColor Green

# Uninstall CPU-only version if exists
pip uninstall torch torchvision torchaudio -y

# Install PyTorch with CUDA 11.8 (compatible with RTX 2050)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

Write-Host "`nVerifying GPU support..." -ForegroundColor Green
python -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"

Write-Host "`nDone! If CUDA shows True, GPU training is ready." -ForegroundColor Green

