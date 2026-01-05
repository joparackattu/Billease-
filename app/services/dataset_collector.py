"""
Dataset Collection Service

This service helps collect images from the RTSP camera for training dataset.
Captures images and saves them to the dataset folder structure.
"""

import os
import base64
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DatasetCollector:
    """
    Service to collect images from camera for dataset creation.
    
    Helps organize images by class name for easy labeling later.
    """
    
    def __init__(self, dataset_root: str = "datasets"):
        """
        Initialize dataset collector.
        
        Args:
            dataset_root: Root directory for datasets
        """
        self.dataset_root = Path(dataset_root)
        self.train_images_dir = self.dataset_root / "train" / "images"
        self.train_labels_dir = self.dataset_root / "train" / "labels"
        self.val_images_dir = self.dataset_root / "val" / "images"
        self.val_labels_dir = self.dataset_root / "val" / "labels"
        
        # Create directories if they don't exist
        self._create_directories()
    
    def _create_directories(self):
        """Create dataset directory structure if it doesn't exist."""
        self.train_images_dir.mkdir(parents=True, exist_ok=True)
        self.train_labels_dir.mkdir(parents=True, exist_ok=True)
        self.val_images_dir.mkdir(parents=True, exist_ok=True)
        self.val_labels_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Dataset directories ready at: {self.dataset_root}")
    
    def save_image(self, image_base64: str, class_name: str, split: str = "train") -> dict:
        """
        Save captured image to dataset folder.
        
        Args:
            image_base64: Base64 encoded image
            class_name: Name of the class/item (e.g., "tomato", "potato")
            split: "train" or "val" (default: "train")
        
        Returns:
            dict: Information about saved image
        """
        try:
            # Validate split
            if split not in ["train", "val"]:
                split = "train"
            
            # Get target directory
            if split == "train":
                target_dir = self.train_images_dir
            else:
                target_dir = self.val_images_dir
            
            # Create class subdirectory
            class_dir = target_dir / class_name
            class_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{class_name}_{timestamp}.jpg"
            filepath = class_dir / filename
            
            # Decode and save image
            image_bytes = base64.b64decode(image_base64)
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            # Count images for this class
            image_count = len(list(class_dir.glob("*.jpg")))
            
            result = {
                "status": "success",
                "message": f"Image saved successfully",
                "filepath": str(filepath),
                "filename": filename,
                "class": class_name,
                "split": split,
                "total_images_for_class": image_count,
                "full_path": str(filepath.absolute())
            }
            
            logger.info(f"✅ Saved image: {filename} for class '{class_name}' ({split})")
            return result
            
        except Exception as e:
            logger.error(f"Error saving image: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_dataset_stats(self) -> dict:
        """
        Get statistics about the current dataset.
        
        Returns:
            dict: Dataset statistics
        """
        stats = {
            "train": {},
            "val": {},
            "total_images": 0,
            "classes": []
        }
        
        # Count train images
        if self.train_images_dir.exists():
            for class_dir in self.train_images_dir.iterdir():
                if class_dir.is_dir():
                    class_name = class_dir.name
                    image_count = len(list(class_dir.glob("*.jpg")))
                    stats["train"][class_name] = image_count
                    stats["total_images"] += image_count
                    if class_name not in stats["classes"]:
                        stats["classes"].append(class_name)
        
        # Count val images
        if self.val_images_dir.exists():
            for class_dir in self.val_images_dir.iterdir():
                if class_dir.is_dir():
                    class_name = class_dir.name
                    image_count = len(list(class_dir.glob("*.jpg")))
                    stats["val"][class_name] = image_count
                    stats["total_images"] += image_count
                    if class_name not in stats["classes"]:
                        stats["classes"].append(class_name)
        
        return stats
    
    def list_classes(self) -> list:
        """
        List all classes in the dataset.
        
        Returns:
            list: List of class names
        """
        classes = set()
        
        # Get classes from train
        if self.train_images_dir.exists():
            for class_dir in self.train_images_dir.iterdir():
                if class_dir.is_dir():
                    classes.add(class_dir.name)
        
        # Get classes from val
        if self.val_images_dir.exists():
            for class_dir in self.val_images_dir.iterdir():
                if class_dir.is_dir():
                    classes.add(class_dir.name)
        
        return sorted(list(classes))


# Global dataset collector instance
dataset_collector = DatasetCollector()












