"""Quick script to check GPU availability"""
import sys

try:
    import torch
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU name: {torch.cuda.get_device_name(0)}")
        print(f"GPU count: {torch.cuda.device_count()}")
    else:
        print("❌ CUDA not available - PyTorch is CPU-only")
        print("\nTo enable GPU:")
        print("1. Uninstall current PyTorch: pip uninstall torch torchvision")
        print("2. Install CUDA version: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
except ImportError:
    print("PyTorch not installed")















