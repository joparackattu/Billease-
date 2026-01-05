"""
Download Office/Stationery Items Dataset

This script downloads datasets for detecting office items like:
- Phone, Mouse, Keyboard
- Pencil, Pen
- Books, Notebooks
- Laptop, Tablet
- etc.

Usage:
    python download_office_items_dataset.py
    python download_office_items_dataset.py --source roboflow
    python download_office_items_dataset.py --source kaggle
"""

import os
import sys
import requests
import zipfile
import shutil
from pathlib import Path
import argparse

# Office items datasets
OFFICE_ITEMS_DATASETS = {
    "roboflow": {
        "office-objects": {
            "name": "Office Objects Detection",
            "search": "office objects detection",
            "items": ["phone", "mouse", "keyboard", "laptop", "pen", "pencil", "book", "notebook"],
            "url": "https://universe.roboflow.com",
            "instructions": "Search for 'office objects' or 'stationery items' on Roboflow Universe"
        },
        "stationery-items": {
            "name": "Stationery Items Dataset",
            "search": "stationery items yolo",
            "items": ["pen", "pencil", "book", "notebook", "eraser", "ruler"],
            "url": "https://universe.roboflow.com",
            "instructions": "Search for 'stationery items' on Roboflow Universe"
        },
        "electronic-devices": {
            "name": "Electronic Devices Detection",
            "search": "electronic devices detection",
            "items": ["phone", "mouse", "keyboard", "laptop", "tablet", "monitor"],
            "url": "https://universe.roboflow.com",
            "instructions": "Search for 'electronic devices' on Roboflow Universe"
        }
    },
    "kaggle": {
        "office-objects": {
            "name": "Office Objects Dataset",
            "url": "https://www.kaggle.com/datasets",
            "search": "office objects detection",
            "items": ["phone", "mouse", "keyboard", "pen", "pencil", "book"]
        }
    },
    "github": {
        "yolo-office": {
            "name": "YOLO Office Items",
            "url": "https://github.com",
            "search": "yolo office items dataset",
            "items": ["phone", "mouse", "keyboard", "laptop", "pen", "pencil"]
        }
    }
}


def download_from_roboflow():
    """Instructions for downloading from Roboflow."""
    print("\n" + "="*60)
    print("📦 DOWNLOADING FROM ROBOFLOAT UNIVERSE")
    print("="*60)
    print("\n🔗 Go to: https://universe.roboflow.com")
    print("\n🔍 Search for these datasets:")
    print("   1. 'office objects detection'")
    print("   2. 'stationery items yolo'")
    print("   3. 'electronic devices detection'")
    print("   4. 'desk objects detection'")
    print("\n📥 Download Steps:")
    print("   1. Click on a dataset")
    print("   2. Click 'Download' button")
    print("   3. Select 'YOLOv8' format")
    print("   4. Click 'Download'")
    print("   5. Extract zip to 'datasets/' folder")
    print("\n✅ Recommended Datasets:")
    print("   • Office Objects Detection (if available)")
    print("   • Stationery Items Dataset")
    print("   • Electronic Devices Detection")
    print("\n💡 Tip: Create a free Roboflow account for easier downloads")


def download_from_kaggle():
    """Instructions for downloading from Kaggle."""
    print("\n" + "="*60)
    print("📦 DOWNLOADING FROM KAGGLE")
    print("="*60)
    print("\n📋 Setup Instructions:")
    print("   1. Install Kaggle API:")
    print("      pip install kaggle")
    print("\n   2. Get API credentials:")
    print("      - Go to https://www.kaggle.com/settings")
    print("      - Click 'Create New API Token'")
    print("      - Save kaggle.json to ~/.kaggle/")
    print("\n   3. Search for datasets:")
    print("      kaggle datasets list -s 'office objects'")
    print("      kaggle datasets list -s 'stationery'")
    print("      kaggle datasets list -s 'electronic devices'")
    print("\n   4. Download dataset:")
    print("      kaggle datasets download -d <dataset-name>")
    print("\n⚠️  Note: Most Kaggle datasets need conversion to YOLO format")


def download_sample_dataset():
    """Download a sample/pre-configured dataset if available."""
    print("\n" + "="*60)
    print("📥 DOWNLOADING SAMPLE DATASET")
    print("="*60)
    
    # Common public dataset URLs (update with actual working URLs)
    sample_urls = [
        # Add actual working dataset URLs here
        # Example: "https://example.com/office-items-dataset.zip"
    ]
    
    if not sample_urls:
        print("\n⚠️  No pre-configured sample datasets available.")
        print("   Please use Roboflow or Kaggle to download datasets.")
        return False
    
    target_dir = Path("datasets")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for url in sample_urls:
        try:
            print(f"\n📥 Downloading from: {url}")
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            zip_path = target_dir / "office_items_dataset.zip"
            with open(zip_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            
            print("📦 Extracting...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            
            zip_path.unlink()
            print("✅ Dataset downloaded and extracted!")
            return True
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            continue
    
    return False


def create_office_items_config():
    """Create configuration for office items."""
    print("\n" + "="*60)
    print("⚙️  CREATING OFFICE ITEMS CONFIGURATION")
    print("="*60)
    
    # Office items to add
    office_items = {
        "phone": 5000.0,      # ₹5000 per item (or per kg if sold by weight)
        "mouse": 500.0,       # ₹500 per item
        "keyboard": 1500.0,   # ₹1500 per item
        "laptop": 50000.0,   # ₹50000 per item
        "tablet": 20000.0,   # ₹20000 per item
        "pen": 10.0,         # ₹10 per item
        "pencil": 5.0,       # ₹5 per item
        "book": 200.0,       # ₹200 per item
        "notebook": 50.0,    # ₹50 per item
        "monitor": 10000.0,  # ₹10000 per item
        "eraser": 5.0,       # ₹5 per item
        "ruler": 20.0,       # ₹20 per item
    }
    
    config_file = Path("office_items_config.json")
    with open(config_file, 'w') as f:
        import json
        json.dump(office_items, f, indent=2)
    
    print(f"\n✅ Configuration saved to: {config_file}")
    print("\n📋 Items to add to system:")
    for item, price in office_items.items():
        print(f"   • {item}: ₹{price}")
    
    print("\n📝 Next steps:")
    print("   1. Update app/services/item_detection.py PRICE_TABLE")
    print("   2. Update app/services/model_service.py known_items list")
    print("   3. Update main.py detection_capabilities endpoint")
    
    return office_items


def update_system_files(office_items: dict):
    """Update system files to include office items."""
    print("\n" + "="*60)
    print("🔄 UPDATING SYSTEM FILES")
    print("="*60)
    
    # Read item_detection.py
    item_detection_file = Path("app/services/item_detection.py")
    if item_detection_file.exists():
        content = item_detection_file.read_text(encoding='utf-8')
        
        # Find PRICE_TABLE and add office items
        if "PRICE_TABLE = {" in content:
            # Add office items to PRICE_TABLE
            for item, price in office_items.items():
                if f'"{item}":' not in content:
                    # Find the closing brace of PRICE_TABLE
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'PRICE_TABLE = {' in line:
                            # Find the last item before closing brace
                            for j in range(i+1, len(lines)):
                                if lines[j].strip() == '}':
                                    # Insert before closing brace
                                    indent = '    '  # 4 spaces
                                    price_line = f'{indent}"{item}": {price},      # ₹{price} per item'
                                    lines.insert(j, price_line)
                                    break
                            break
                    content = '\n'.join(lines)
            
            item_detection_file.write_text(content, encoding='utf-8')
            print("✅ Updated app/services/item_detection.py")
        else:
            print("⚠️  Could not find PRICE_TABLE in item_detection.py")
    else:
        print("⚠️  item_detection.py not found")
    
    # Update model_service.py
    model_service_file = Path("app/services/model_service.py")
    if model_service_file.exists():
        content = model_service_file.read_text(encoding='utf-8')
        
        # Find known_items list and add office items
        if 'known_items = [' in content:
            for item in office_items.keys():
                if f'"{item}"' not in content and f"'{item}'" not in content:
                    # Add to known_items list
                    content = content.replace(
                        'known_items = [',
                        f'known_items = [\n        "{item}",'
                    )
            
            model_service_file.write_text(content, encoding='utf-8')
            print("✅ Updated app/services/model_service.py")
        else:
            print("⚠️  Could not find known_items in model_service.py")
    else:
        print("⚠️  model_service.py not found")


def main():
    import sys
    import io
    # Fix Windows encoding issues
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    parser = argparse.ArgumentParser(description="Download office/stationery items datasets")
    parser.add_argument("--source", choices=["roboflow", "kaggle", "auto"], default="auto",
                       help="Dataset source (default: auto)")
    parser.add_argument("--update-config", action="store_true",
                       help="Update system configuration files")
    parser.add_argument("--skip-download", action="store_true",
                       help="Skip download, only update configuration")
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("OFFICE/STATIONERY ITEMS DATASET DOWNLOADER")
    print("="*60)
    print("\n🎯 Target Items:")
    print("   • Phone, Mouse, Keyboard")
    print("   • Pen, Pencil")
    print("   • Books, Notebooks")
    print("   • Laptop, Tablet, Monitor")
    print("   • Eraser, Ruler")
    
    if not args.skip_download:
        if args.source == "roboflow" or args.source == "auto":
            download_from_roboflow()
        
        if args.source == "kaggle" or args.source == "auto":
            download_from_kaggle()
        
        if args.source == "auto":
            print("\n" + "="*60)
            print("💡 RECOMMENDED: Use Roboflow Universe")
            print("="*60)
            print("\n   1. Go to https://universe.roboflow.com")
            print("   2. Search: 'office objects detection'")
            print("   3. Download in YOLOv8 format")
            print("   4. Extract to datasets/ folder")
    
    # Create configuration
    office_items = create_office_items_config()
    
    # Update system files if requested
    if args.update_config:
        update_system_files(office_items)
        print("\n✅ System files updated!")
        print("\n📝 Next steps:")
        print("   1. Download dataset from Roboflow")
        print("   2. Extract to datasets/ folder")
        print("   3. Retrain model: python train_model.py")
    else:
        print("\n💡 To auto-update system files, run:")
        print("   python download_office_items_dataset.py --update-config")
    
    print("\n" + "="*60)
    print("✅ SETUP COMPLETE!")
    print("="*60)


if __name__ == "__main__":
    main()

