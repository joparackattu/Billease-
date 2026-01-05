"""
Train YOLOv8 Model for Item Detection

This script trains a YOLOv8 model to detect items (tomato, potato, onion, etc.)
for the BILLESE billing system.

Usage:
    python train_model.py

Dataset Structure:
    datasets/
    ├── train/
    │   ├── images/
    │   │   ├── image1.jpg
    │   │   ├── image2.jpg
    │   │   └── ...
    │   └── labels/
    │       ├── image1.txt
    │       ├── image2.txt
    │       └── ...
    ├── val/
    │   ├── images/
    │   └── labels/
    └── data.yaml  # Dataset configuration

Label Format (YOLO):
    Each .txt file contains one line per object:
    class_id center_x center_y width height
    (all values normalized 0-1)
    
Example:
    0 0.5 0.5 0.3 0.3  # class 0 (tomato) at center, 30% width/height
"""

from pathlib import Path
import yaml
import logging

# Try to import ultralytics
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("❌ Error: Ultralytics YOLO not installed!")
    print("Install it with: pip install ultralytics")
    exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_dataset_config(dataset_dir: Path, classes: list) -> Path:
    """
    Create YOLO dataset configuration file (data.yaml).
    
    Args:
        dataset_dir: Path to dataset directory
        classes: List of class names
        
    Returns:
        Path: Path to created data.yaml file
    """
    config_path = dataset_dir / "data.yaml"
    
    config = {
        'path': str(dataset_dir.absolute()),
        'train': 'train/images',
        'val': 'val/images',
        'names': {i: name for i, name in enumerate(classes)}
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    logger.info(f"✅ Created dataset config: {config_path}")
    return config_path


def train_model(
    dataset_path: str = "datasets",
    model_size: str = "n",  # n=nano, s=small, m=medium, l=large, x=xlarge
    epochs: int = 50,
    imgsz: int = 640,
    batch_size: int = 8  # Reduced from 16 to prevent memory issues
):
    """
    Train YOLOv8 model on custom dataset.
    
    Args:
        dataset_path: Path to dataset directory
        model_size: Model size ('n', 's', 'm', 'l', 'x')
        epochs: Number of training epochs
        imgsz: Image size for training
        batch_size: Batch size for training
    """
    dataset_dir = Path(dataset_path)
    
    # Check if dataset exists
    if not dataset_dir.exists():
        logger.error(f"❌ Dataset directory not found: {dataset_dir}")
        logger.info("\n📝 To create a dataset:")
        logger.info("1. Create folder structure:")
        logger.info("   datasets/")
        logger.info("   ├── train/images/")
        logger.info("   ├── train/labels/")
        logger.info("   ├── val/images/")
        logger.info("   └── val/labels/")
        logger.info("\n2. Add your images and labels")
        logger.info("3. Create data.yaml (or run this script to auto-create)")
        return
    
    # Check for data.yaml
    config_path = dataset_dir / "data.yaml"
    if not config_path.exists():
        logger.warning("⚠️  data.yaml not found. Creating default config...")
        # Default classes for BILLESE
        classes = ["tomato", "potato", "onion", "carrot", "cabbage"]
        create_dataset_config(dataset_dir, classes)
    
    # Load dataset config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    logger.info(f"📊 Dataset config loaded:")
    # Handle both dict and list formats for names
    if isinstance(config['names'], dict):
        class_names = list(config['names'].values())
    else:
        class_names = config['names']
    logger.info(f"   Classes: {class_names}")
    logger.info(f"   Train: {config['train']}")
    logger.info(f"   Val: {config.get('val') or config.get('valid')}")
    
    # Initialize model (use pre-trained YOLOv8)
    model_name = f"yolov8{model_size}.pt"
    logger.info(f"🚀 Initializing model: {model_name}")
    model = YOLO(model_name)
    
    # Check for GPU availability
    import torch
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    if device == 'cuda':
        logger.info(f"✅ GPU detected: {torch.cuda.get_device_name(0)}")
    else:
        logger.warning("⚠️  No GPU detected, using CPU (training will be slower)")
    
    # Train the model
    logger.info("🎯 Starting training...")
    logger.info(f"   Device: {device}")
    logger.info(f"   Epochs: {epochs}")
    logger.info(f"   Image size: {imgsz}")
    logger.info(f"   Batch size: {batch_size}")
    logger.info("   (This may take a while...)")
    
    try:
        # Reduce workers to avoid paging file issues on Windows
        # With GPU, fewer workers are needed (GPU is the bottleneck, not data loading)
        workers = 2 if device == 'cuda' else 4
        
        results = model.train(
            data=str(config_path),
            epochs=epochs,
            imgsz=imgsz,
            batch=batch_size,
            device=device,  # Explicitly set device
            workers=workers,  # Reduce workers to prevent memory issues
            name='billese_item_detection',
            project='runs/detect',
            save=True,
            plots=True
        )
        
        logger.info("✅ Training completed!")
        logger.info(f"📁 Model saved to: runs/detect/billese_item_detection/weights/best.pt")
        logger.info("\n💡 Next steps:")
        logger.info("1. Copy the best model:")
        logger.info("   cp runs/detect/billese_item_detection/weights/best.pt models/item_detection.pt")
        logger.info("2. Restart your FastAPI server")
        logger.info("3. Test with: curl http://localhost:8000/test-camera")
        
    except Exception as e:
        logger.error(f"❌ Training failed: {str(e)}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train YOLOv8 model for BILLESE item detection")
    parser.add_argument("--dataset", type=str, default="datasets", help="Path to dataset directory")
    parser.add_argument("--model", type=str, default="n", choices=['n', 's', 'm', 'l', 'x'],
                       help="Model size: n=nano, s=small, m=medium, l=large, x=xlarge")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size for training")
    parser.add_argument("--batch", type=int, default=8, help="Batch size (reduced to prevent memory issues)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("BILLESE - YOLOv8 Model Training")
    print("=" * 60)
    print()
    
    train_model(
        dataset_path=args.dataset,
        model_size=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch_size=args.batch
    )


