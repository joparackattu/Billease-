"""Check which GPU is actually being used by PyTorch"""
import torch
import subprocess
import sys

print("=" * 60)
print("GPU Usage Check")
print("=" * 60)

# Check PyTorch CUDA
print("\n1. PyTorch CUDA Status:")
print(f"   CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"   CUDA version: {torch.version.cuda}")
    print(f"   GPU count: {torch.cuda.device_count()}")
    print(f"   Current device: {torch.cuda.current_device()}")
    print(f"   GPU name: {torch.cuda.get_device_name(0)}")
    
    # Check memory usage
    print(f"\n2. GPU Memory:")
    print(f"   Allocated: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
    print(f"   Reserved: {torch.cuda.memory_reserved(0) / 1024**3:.2f} GB")
    print(f"   Total: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    
    # Try to allocate a tensor to see if it works
    try:
        x = torch.randn(1000, 1000).cuda()
        print(f"\n3. GPU Test:")
        print(f"   Successfully allocated tensor on GPU")
        print(f"   Tensor device: {x.device}")
        del x
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"   Error: {e}")

# Check nvidia-smi (more accurate than Task Manager)
print("\n4. NVIDIA-SMI (Real-time GPU usage):")
try:
    result = subprocess.run(['nvidia-smi', '--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader'], 
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        for i, line in enumerate(lines):
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 6:
                print(f"   GPU {parts[0]}: {parts[1]}")
                print(f"      Utilization: {parts[2]}")
                print(f"      Memory: {parts[3]} / {parts[4]}")
                print(f"      Temperature: {parts[5]}")
    else:
        print("   nvidia-smi not available")
except FileNotFoundError:
    print("   nvidia-smi not found in PATH")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 60)
print("Note: Task Manager may show 0% even when GPU is working.")
print("nvidia-smi is more accurate for GPU utilization.")
print("=" * 60)










