"""Simple GPU check that handles loading issues"""
import os
import sys

print("Checking PyTorch installation...")
print(f"Python: {sys.executable}")

try:
    # Try importing torch with timeout handling
    print("\nAttempting to import torch...")
    import torch
    print(f"PyTorch version: {torch.__version__}")
    
    print("\nChecking CUDA...")
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")
    
    if cuda_available:
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU name: {torch.cuda.get_device_name(0)}")
        print(f"GPU count: {torch.cuda.device_count()}")
        print("\n[SUCCESS] GPU is ready for training!")
    else:
        print("\n[WARNING] CUDA not available")
        print("Possible reasons:")
        print("1. CUDA toolkit not installed")
        print("2. PyTorch CPU-only version installed")
        print("3. GPU drivers not up to date")
        
except ImportError as e:
    print(f"[ERROR] PyTorch not installed: {e}")
except Exception as e:
    print(f"[ERROR] Error loading PyTorch: {e}")
    print("\nTroubleshooting:")
    print("1. Check if CUDA toolkit is installed")
    print("2. Try: pip uninstall torch torchvision")
    print("3. Then: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")

