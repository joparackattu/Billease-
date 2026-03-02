"""
Roboflow Dataset Downloader

This script helps download datasets from Roboflow Universe.
Since Roboflow requires API authentication, this provides instructions
and can download public datasets if URLs are provided.

Usage:
    python scripts/download_roboflow_dataset.py --search "grocery items"
    python scripts/download_roboflow_dataset.py --url <roboflow_export_url>
"""

import argparse
import requests
import zipfile
from pathlib import Path
import json


def search_roboflow_datasets(query: str):
    """Search Roboflow Universe for datasets."""
    print(f"\n🔍 Searching Roboflow Universe for: '{query}'")
    print("\n📋 Manual Steps:")
    print("1. Go to https://universe.roboflow.com")
    print(f"2. Search for: {query}")
    print("3. Browse available datasets")
    print("4. Click on a dataset")
    print("5. Click 'Download' → Select 'YOLOv8' format")
    print("6. Download the zip file")
    print("7. Extract to datasets/ folder")
    print("\n💡 Recommended search terms:")
    print("   - 'grocery items'")
    print("   - 'fruits vegetables'")
    print("   - 'retail products'")
    print("   - 'supermarket'")
    print("   - 'food items'")


def download_roboflow_export(url: str, target_dir: Path = Path("datasets")):
    """Download dataset from Roboflow export URL."""
    print(f"\n📥 Downloading from Roboflow export URL...")
    
    try:
        # Download the dataset
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        # Save to temp file
        zip_path = target_dir / "temp_roboflow_dataset.zip"
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Extract
        print("📦 Extracting dataset...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        
        # Cleanup
        zip_path.unlink()
        
        print(f"✅ Dataset extracted to: {target_dir}")
        print("\n📝 Next steps:")
        print("1. Verify dataset structure (train/images, train/labels)")
        print("2. Update item_detection.py with new items")
        print("3. Retrain model: python train_model.py")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\n💡 Tip: Make sure the URL is a direct download link from Roboflow")


def list_popular_datasets():
    """List popular Roboflow datasets for grocery/retail."""
    print("\n📚 Popular Roboflow Datasets for Grocery/Retail:\n")
    
    datasets = [
        {
            "name": "Grocery Items Detection",
            "search": "grocery items detection",
            "items": ["Various grocery products"],
            "format": "YOLOv8"
        },
        {
            "name": "Fruits and Vegetables",
            "search": "fruits vegetables yolo",
            "items": ["apple", "banana", "orange", "tomato", "potato"],
            "format": "YOLOv8"
        },
        {
            "name": "Retail Products",
            "search": "retail products detection",
            "items": ["bottles", "packages", "boxes"],
            "format": "YOLOv8"
        },
        {
            "name": "Supermarket Items",
            "search": "supermarket items",
            "items": ["Various supermarket products"],
            "format": "YOLOv8"
        }
    ]
    
    for i, dataset in enumerate(datasets, 1):
        print(f"{i}. {dataset['name']}")
        print(f"   Search: '{dataset['search']}'")
        print(f"   Items: {', '.join(dataset['items'][:3])}{'...' if len(dataset['items']) > 3 else ''}")
        print(f"   Format: {dataset['format']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Download datasets from Roboflow Universe")
    parser.add_argument("--search", type=str, help="Search query for Roboflow Universe")
    parser.add_argument("--url", type=str, help="Direct Roboflow export URL")
    parser.add_argument("--list", action="store_true", help="List popular datasets")
    parser.add_argument("--target", type=str, default="datasets", help="Target directory")
    
    args = parser.parse_args()
    
    if args.list:
        list_popular_datasets()
        return
    
    if args.url:
        target_dir = Path(args.target)
        target_dir.mkdir(parents=True, exist_ok=True)
        download_roboflow_export(args.url, target_dir)
        return
    
    if args.search:
        search_roboflow_datasets(args.search)
        return
    
    print("❌ Please provide --search, --url, or use --list")
    print("\nUsage:")
    print("  python scripts/download_roboflow_dataset.py --list")
    print("  python scripts/download_roboflow_dataset.py --search 'grocery items'")
    print("  python scripts/download_roboflow_dataset.py --url <roboflow_export_url>")


if __name__ == "__main__":
    main()















