"""
Download Open Source Datasets for Object Detection

This script downloads popular open-source datasets that can be used
to expand the detection capabilities of the BILLESE system.

Supported Sources:
1. Roboflow Universe (grocery/retail datasets)
2. Kaggle datasets
3. GitHub repositories
4. Direct download links

Usage:
    python download_datasets.py --source roboflow --dataset grocery-items
    python download_datasets.py --source kaggle --dataset fruits-vegetables
    python download_datasets.py --list  # List available datasets
"""

import os
import sys
import argparse
import requests
import zipfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict
import json

# Dataset configurations
AVAILABLE_DATASETS = {
    "roboflow": {
        "grocery-items": {
            "name": "Grocery Items Dataset",
            "url": "https://universe.roboflow.com/ds/...",  # Update with actual URL
            "description": "Various grocery items with YOLO labels",
            "items": ["apple", "banana", "orange", "tomato", "potato", "onion", "carrot", "cabbage", "bread", "milk", "egg"]
        },
        "fruits-vegetables": {
            "name": "Fruits and Vegetables Dataset",
            "url": "https://universe.roboflow.com/ds/...",
            "description": "Comprehensive fruits and vegetables dataset",
            "items": ["apple", "banana", "orange", "tomato", "potato", "onion", "carrot", "cucumber", "pepper", "lettuce"]
        },
        "retail-products": {
            "name": "Retail Products Dataset",
            "url": "https://universe.roboflow.com/ds/...",
            "description": "Common retail store products",
            "items": ["bottle", "cup", "bowl", "can", "box", "bag", "package"]
        }
    },
    "kaggle": {
        "fruits-360": {
            "name": "Fruits 360 Dataset",
            "url": "https://www.kaggle.com/datasets/moltean/fruits",
            "description": "Large dataset of fruits (131 classes)",
            "items": ["apple", "banana", "orange", "grape", "mango", "strawberry", "pineapple", "peach", "pear", "cherry"]
        },
        "vegetables": {
            "name": "Vegetables Dataset",
            "url": "https://www.kaggle.com/datasets/...",
            "description": "Vegetable detection dataset",
            "items": ["tomato", "potato", "onion", "carrot", "cabbage", "broccoli", "cauliflower", "pepper", "cucumber"]
        }
    },
    "github": {
        "yolo-grocery": {
            "name": "YOLO Grocery Dataset",
            "url": "https://github.com/.../archive/refs/heads/main.zip",
            "description": "Grocery items in YOLO format",
            "items": ["apple", "banana", "tomato", "potato", "onion"]
        }
    }
}


def download_file(url: str, destination: Path, chunk_size: int = 8192) -> bool:
    """Download a file from URL to destination."""
    try:
        print(f"📥 Downloading from: {url}")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r   Progress: {percent:.1f}%", end='', flush=True)
        
        print(f"\n✅ Downloaded: {destination.name}")
        return True
    except Exception as e:
        print(f"\n❌ Download failed: {str(e)}")
        return False


def extract_zip(zip_path: Path, extract_to: Path) -> bool:
    """Extract zip file to destination."""
    try:
        print(f"📦 Extracting: {zip_path.name}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"✅ Extracted to: {extract_to}")
        return True
    except Exception as e:
        print(f"❌ Extraction failed: {str(e)}")
        return False


def convert_to_yolo_format(source_dir: Path, target_dir: Path, class_mapping: Dict[str, int]) -> bool:
    """
    Convert dataset to YOLO format.
    
    This function handles different dataset formats and converts them to YOLO.
    """
    try:
        # Create target directories
        train_images = target_dir / "train" / "images"
        train_labels = target_dir / "train" / "labels"
        val_images = target_dir / "val" / "images"
        val_labels = target_dir / "val" / "labels"
        
        for d in [train_images, train_labels, val_images, val_labels]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Check if already in YOLO format
        if (source_dir / "train" / "images").exists() and (source_dir / "train" / "labels").exists():
            print("✅ Dataset already in YOLO format")
            # Copy to target
            shutil.copytree(source_dir / "train" / "images", train_images, dirs_exist_ok=True)
            shutil.copytree(source_dir / "train" / "labels", train_labels, dirs_exist_ok=True)
            if (source_dir / "val").exists():
                shutil.copytree(source_dir / "val" / "images", val_images, dirs_exist_ok=True)
                shutil.copytree(source_dir / "val" / "labels", val_labels, dirs_exist_ok=True)
            return True
        
        print("⚠️  Dataset format conversion not yet implemented")
        print("   Please ensure dataset is in YOLO format or use Roboflow export")
        return False
        
    except Exception as e:
        print(f"❌ Conversion failed: {str(e)}")
        return False


def download_roboflow_dataset(dataset_key: str, api_key: Optional[str] = None) -> bool:
    """Download dataset from Roboflow Universe."""
    if dataset_key not in AVAILABLE_DATASETS["roboflow"]:
        print(f"❌ Dataset '{dataset_key}' not found in Roboflow datasets")
        return False
    
    dataset_info = AVAILABLE_DATASETS["roboflow"][dataset_key]
    print(f"\n📦 Downloading: {dataset_info['name']}")
    print(f"   Description: {dataset_info['description']}")
    print(f"   Items: {', '.join(dataset_info['items'])}")
    
    # Note: Roboflow requires API key and specific download format
    print("\n⚠️  Manual Download Required:")
    print("1. Go to https://universe.roboflow.com")
    print("2. Search for grocery/retail datasets")
    print("3. Export in YOLO format")
    print("4. Download and extract to datasets/ folder")
    print("\nRecommended Roboflow datasets:")
    print("  - Grocery Items Detection")
    print("  - Fruits and Vegetables")
    print("  - Retail Products")
    
    return False  # Manual download required


def download_kaggle_dataset(dataset_key: str, kaggle_username: Optional[str] = None, kaggle_key: Optional[str] = None) -> bool:
    """Download dataset from Kaggle."""
    if dataset_key not in AVAILABLE_DATASETS["kaggle"]:
        print(f"❌ Dataset '{dataset_key}' not found in Kaggle datasets")
        return False
    
    dataset_info = AVAILABLE_DATASETS["kaggle"][dataset_key]
    print(f"\n📦 Downloading: {dataset_info['name']}")
    print(f"   Description: {dataset_info['description']}")
    print(f"   Items: {', '.join(dataset_info['items'])}")
    
    print("\n⚠️  Kaggle Download Instructions:")
    print("1. Install Kaggle API: pip install kaggle")
    print("2. Setup credentials: https://www.kaggle.com/settings")
    print("3. Download dataset:")
    print(f"   kaggle datasets download -d {dataset_key}")
    print("4. Extract and convert to YOLO format")
    
    return False  # Requires Kaggle API setup


def list_available_datasets():
    """List all available datasets."""
    print("\n📚 Available Datasets:\n")
    
    for source, datasets in AVAILABLE_DATASETS.items():
        print(f"\n🔹 {source.upper()}:")
        for key, info in datasets.items():
            print(f"   • {key}")
            print(f"     Name: {info['name']}")
            print(f"     Items: {', '.join(info['items'][:5])}{'...' if len(info['items']) > 5 else ''}")
            print(f"     Total Items: {len(info['items'])}")
            print()


def download_from_url(url: str, dataset_name: str, target_dir: Path) -> bool:
    """Download dataset from direct URL."""
    print(f"\n📥 Downloading dataset: {dataset_name}")
    
    # Create temp directory
    temp_dir = target_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Download file
    zip_path = temp_dir / f"{dataset_name}.zip"
    if not download_file(url, zip_path):
        return False
    
    # Extract
    extract_dir = temp_dir / dataset_name
    if not extract_zip(zip_path, temp_dir):
        return False
    
    # Convert to YOLO format
    if convert_to_yolo_format(extract_dir, target_dir, {}):
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\n✅ Dataset '{dataset_name}' downloaded and integrated successfully!")
        return True
    else:
        print(f"\n⚠️  Dataset downloaded but conversion may be needed")
        print(f"   Check: {extract_dir}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download open-source datasets for object detection")
    parser.add_argument("--source", choices=["roboflow", "kaggle", "github", "url"], help="Dataset source")
    parser.add_argument("--dataset", type=str, help="Dataset key or name")
    parser.add_argument("--url", type=str, help="Direct download URL")
    parser.add_argument("--list", action="store_true", help="List all available datasets")
    parser.add_argument("--target", type=str, default="datasets", help="Target directory (default: datasets)")
    parser.add_argument("--api-key", type=str, help="API key for Roboflow/Kaggle")
    
    args = parser.parse_args()
    
    target_dir = Path(args.target)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    if args.list:
        list_available_datasets()
        return
    
    if args.url:
        dataset_name = args.dataset or "downloaded_dataset"
        download_from_url(args.url, dataset_name, target_dir)
        return
    
    if not args.source or not args.dataset:
        print("❌ Error: --source and --dataset are required (or use --url)")
        print("\nUsage examples:")
        print("  python download_datasets.py --list")
        print("  python download_datasets.py --source roboflow --dataset grocery-items")
        print("  python download_datasets.py --url https://example.com/dataset.zip --dataset my-dataset")
        return
    
    if args.source == "roboflow":
        download_roboflow_dataset(args.dataset, args.api_key)
    elif args.source == "kaggle":
        download_kaggle_dataset(args.dataset)
    elif args.source == "github":
        if args.dataset in AVAILABLE_DATASETS["github"]:
            dataset_info = AVAILABLE_DATASETS["github"][args.dataset]
            download_from_url(dataset_info["url"], args.dataset, target_dir)
        else:
            print(f"❌ Dataset '{args.dataset}' not found")
    else:
        print(f"❌ Unknown source: {args.source}")


if __name__ == "__main__":
    main()











