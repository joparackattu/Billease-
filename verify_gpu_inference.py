"""
Verify that YOLO is actually using GPU for inference.
This script will test the model and show GPU utilization.
"""

import torch
from ultralytics import YOLO
import numpy as np
import cv2
import time

print("=" * 60)
print("GPU VERIFICATION FOR YOLO INFERENCE")
print("=" * 60)

# Check PyTorch CUDA
print("\n1. PyTorch CUDA Check:")
print(f"   CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"   GPU Name: {torch.cuda.get_device_name(0)}")
    print(f"   CUDA Version: {torch.version.cuda}")
    print(f"   GPU Count: {torch.cuda.device_count()}")
    print(f"   Current Device: {torch.cuda.current_device()}")
else:
    print("   ❌ CUDA not available!")
    exit(1)

# Check device
device = 0 if torch.cuda.is_available() else 'cpu'
print(f"\n2. Device Selection: {device}")

# Load model
print("\n3. Loading YOLO Model...")
try:
    model = YOLO('yolov8n.pt')
    print("   ✅ Model loaded")
except Exception as e:
    print(f"   ❌ Error loading model: {e}")
    exit(1)

# Create a test image (640x640 RGB)
print("\n4. Creating test image...")
test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
print("   ✅ Test image created (640x640)")

# Check where model is loaded
print("\n5. Model Device Check:")
try:
    # Get model's device
    model_device = next(model.model.parameters()).device
    print(f"   Model Parameters Device: {model_device}")
    if 'cuda' in str(model_device):
        print("   ✅ Model is on GPU!")
    else:
        print("   ⚠️  Model is on CPU!")
except Exception as e:
    print(f"   ⚠️  Could not check model device: {e}")

# Run inference with explicit device
print("\n6. Running Inference Test...")
print("   Testing with device=0 (GPU) and half=True (FP16)...")

start_time = time.time()
try:
    results = model(
        test_image,
        conf=0.25,
        imgsz=416,
        device=0,  # Explicitly use GPU
        half=True,  # FP16 for faster inference
        verbose=False
    )
    inference_time = time.time() - start_time
    print(f"   ✅ Inference completed in {inference_time:.3f}s")
    
    # Check GPU memory usage
    if torch.cuda.is_available():
        memory_allocated = torch.cuda.memory_allocated(0) / 1024**2  # MB
        memory_reserved = torch.cuda.memory_reserved(0) / 1024**2  # MB
        print(f"   GPU Memory Allocated: {memory_allocated:.2f} MB")
        print(f"   GPU Memory Reserved: {memory_reserved:.2f} MB")
        
        if memory_allocated > 0:
            print("   ✅ GPU memory is being used - GPU is active!")
        else:
            print("   ⚠️  No GPU memory allocated - might be using CPU!")
            
except Exception as e:
    print(f"   ❌ Inference failed: {e}")
    import traceback
    traceback.print_exc()

# Test with CPU for comparison
print("\n7. Running CPU Comparison Test...")
print("   Testing with device='cpu'...")

start_time = time.time()
try:
    results_cpu = model(
        test_image,
        conf=0.25,
        imgsz=416,
        device='cpu',  # Explicitly use CPU
        verbose=False
    )
    cpu_time = time.time() - start_time
    print(f"   ✅ CPU Inference completed in {cpu_time:.3f}s")
    
    if torch.cuda.is_available():
        print(f"\n   Speed Comparison:")
        print(f"   GPU: {inference_time:.3f}s")
        print(f"   CPU: {cpu_time:.3f}s")
        if cpu_time > inference_time:
            speedup = cpu_time / inference_time
            print(f"   ✅ GPU is {speedup:.2f}x faster!")
        else:
            print(f"   ⚠️  GPU is slower - something might be wrong")
            
except Exception as e:
    print(f"   ⚠️  CPU test failed: {e}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
print("\n💡 To verify GPU usage during actual inference:")
print("   1. Run: nvidia-smi (in another terminal)")
print("   2. Run your FastAPI server")
print("   3. Perform a scan")
print("   4. Check nvidia-smi for GPU utilization")














