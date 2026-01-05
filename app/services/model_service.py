"""
AI Model Service for Object Detection

This service handles loading and using the YOLOv8 model for detecting items.
Uses Ultralytics YOLOv8 which is easy to use and perfect for college projects.
"""

import cv2
import numpy as np
import base64
from typing import Optional, Tuple, List
import os
from pathlib import Path
import logging
import time

logger = logging.getLogger(__name__)

# Try to import ultralytics, but handle gracefully if not installed
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("Ultralytics YOLO not installed. Install with: pip install ultralytics")


class ObjectDetectionModel:
    """
    YOLOv8 Object Detection Model wrapper with dual-model support.
    
    Uses:
    - Trained model for office items (Book, Calculator, Mouse, etc.)
    - COCO pre-trained model for fruits/vegetables (banana, apple, etc.)
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize with both trained and COCO models.
        
        Args:
            model_path: Path to trained YOLO model (.pt file)
                       If None, uses default path
        """
        if not YOLO_AVAILABLE:
            raise ImportError(
                "Ultralytics YOLO is not installed. "
                "Install it with: pip install ultralytics"
            )
        
        self.trained_model = None
        self.coco_model = None
        self.model = None  # Keep for backward compatibility
        self.model_path = model_path or self._get_default_model_path()
        self.confidence_threshold = 0.5
        
        # Check GPU availability and half precision support
        import torch
        self.use_gpu = torch.cuda.is_available()
        self.use_half = self.use_gpu  # Use half precision only if GPU available
        self.device = 0 if self.use_gpu else 'cpu'
        
        # Load both models
        self._load_models()
    
    def _get_default_model_path(self) -> str:
        """Get default path for model file."""
        # Create models directory if it doesn't exist
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)
        return str(models_dir / "item_detection.pt")
    
    def _load_models(self):
        """Load both trained model (office items) and COCO model (fruits/vegetables)."""
        # Load trained model (for office items)
        try:
            if os.path.exists(self.model_path):
                logger.info(f"Loading trained model from: {self.model_path}")
                self.trained_model = YOLO(self.model_path)
                self.model = self.trained_model  # For backward compatibility
                logger.info("✅ Trained model loaded successfully!")
                # Log what classes the trained model knows
                if hasattr(self.trained_model, 'names'):
                    classes = list(self.trained_model.names.values())
                    logger.info(f"   Trained model classes: {len(classes)} items")
            else:
                logger.warning(f"Trained model not found at {self.model_path}")
                logger.info("Will use COCO model only for now.")
        except Exception as e:
            logger.error(f"Error loading trained model: {str(e)}")
            self.trained_model = None
        
        # Always load COCO model (for fruits/vegetables)
        try:
            logger.info("Loading COCO pre-trained model...")
            self.coco_model = YOLO('yolov8n.pt')
            logger.info("✅ COCO model loaded successfully!")
            if not self.trained_model:
                self.model = self.coco_model  # Use COCO as primary if no trained model
            
            # Verify GPU is available and will be used
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"✅ GPU detected: {gpu_name} - Will use for inference")
                logger.info(f"   Device: {self.device} (0 = GPU)")
                logger.info(f"   Half Precision (FP16): {self.use_half}")
                
                # Warm up GPU with a dummy inference to reduce first-inference latency
                logger.info("🔥 Warming up GPU with dummy inference...")
                try:
                    import numpy as np
                    dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
                    warmup_start = time.time()
                    _ = self.coco_model(
                        dummy_image,
                        conf=0.25,
                        imgsz=640,
                        device=self.device,
                        half=self.use_half,
                        verbose=False
                    )
                    warmup_time = time.time() - warmup_start
                    
                    # Check GPU memory after warmup
                    memory_mb = torch.cuda.memory_allocated(0) / 1024**2
                    logger.info(f"✅ GPU warmup complete in {warmup_time:.3f}s")
                    logger.info(f"   GPU Memory Allocated: {memory_mb:.2f} MB")
                    if memory_mb > 0:
                        logger.info("   ✅ GPU is active and ready for inference!")
                    else:
                        logger.warning("   ⚠️  No GPU memory allocated - check device parameter")
                except Exception as e:
                    logger.warning(f"GPU warmup failed (non-critical): {e}")
            else:
                logger.warning("⚠️  No GPU detected - inference will be slower on CPU")
        except Exception as e:
            logger.error(f"Error loading COCO model: {str(e)}")
            self.coco_model = None
    
    def preprocess_image(self, image_base64: str, target_size: int = 640) -> np.ndarray:
        """
        Convert base64 image to numpy array, resize, and apply simple preprocessing.
        
        Preprocessing includes:
        - Resizing to target_size (maintains aspect ratio)
        - Normalization (0-1 range)
        - Simple contrast enhancement (CLAHE)
        
        Args:
            image_base64: Base64 encoded image string
            target_size: Target size for resizing (default: 640 for better accuracy)
            
        Returns:
            np.ndarray: Preprocessed image as numpy array (BGR format for OpenCV)
        """
        try:
            # Decode base64 to bytes
            image_bytes = base64.b64decode(image_base64)
            
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            
            # Decode image (OpenCV uses BGR format)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Failed to decode image from base64")
            
            # Resize image (maintains aspect ratio)
            h, w = image.shape[:2]
            if max(h, w) > target_size:
                # Calculate scaling factor
                scale = target_size / max(h, w)
                new_w = int(w * scale)
                new_h = int(h * scale)
                # Resize using INTER_LINEAR for speed
                image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                logger.debug(f"Resized image from {w}x{h} to {new_w}x{new_h}")
            
            # Simple preprocessing: Contrast enhancement using CLAHE
            # Convert to LAB color space for better contrast enhancement
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l)
            
            # Merge channels and convert back to BGR
            lab_enhanced = cv2.merge([l_enhanced, a, b])
            image = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
            
            # Normalize to 0-1 range (YOLO expects 0-255, but normalization helps)
            # Note: YOLO will handle this, but we keep image in 0-255 range for now
            # The normalization happens internally in YOLO
            
            return image
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            raise
    
    def detect(self, image_base64: str) -> Tuple[str, float]:
        """
        Detect item using both models on the same frame.
        
        Strategy:
        1. Run both COCO and trained models on the same frame (single scan cycle)
        2. Collect all detections from both models
        3. Merge detections by confidence score and class priority
        4. Return best result based on merged detections
        
        Args:
            image_base64: Base64 encoded image string
            
        Returns:
            tuple: (item_name, confidence_score)
        """
        if not YOLO_AVAILABLE:
            logger.warning("YOLO not available, returning mock detection")
            return "tomato", 0.0
        
        try:
            start_time = time.time()
            
            # Preprocess image with aspect ratio maintained (target_size=640)
            image = self.preprocess_image(image_base64, target_size=640)
            preprocess_time = time.time() - start_time
            
            # Office items from trained model
            office_items = [
                "book", "calculator", "chair", "keyboard", "monitor", 
                "mouse", "desk", "envelope", "filing-cabinet", "laptop",
                "luggage", "mug", "pen", "printer", "scissors",
                "shelf", "stapler", "wall-clock", "whiteboard"
            ]
            
            # Fruits/vegetables from COCO
            coco_items = ["apple", "banana", "orange", "bottle", "cup", "bowl"]
            
            # Run BOTH models on the same frame in a single scan cycle
            coco_results = None
            trained_results = None
            
            # Get ROI area for bounding box filtering
            # Import camera_service dynamically to avoid circular imports
            try:
                from app.services.camera_service import camera_service
                roi_region = camera_service.get_crop_region()
                if roi_region:
                    roi_area = roi_region["width"] * roi_region["height"]
                else:
                    # If no ROI, use full image area
                    h, w = image.shape[:2]
                    roi_area = w * h
            except Exception as e:
                # Fallback: use full image area if camera_service not available
                logger.warning(f"Could not get ROI region: {e}, using full image area")
                h, w = image.shape[:2]
                roi_area = w * h
            
            # Run COCO model
            if self.coco_model:
                try:
                    coco_results = self.coco_model(
                        image, 
                        conf=0.5,  # Global minimum threshold of 0.5
                        imgsz=640,  # Use 640 for both models
                        device=self.device,
                        half=self.use_half,
                        verbose=False
                    )
                except Exception as e:
                    logger.warning(f"COCO model detection failed: {e}")
            
            # Run trained model (always run, both models process same frame)
            if self.trained_model:
                try:
                    trained_results = self.trained_model(
                        image, 
                        conf=0.5,  # Global minimum threshold of 0.5
                        imgsz=640,  # Use 640 for both models
                        device=self.device,
                        half=self.use_half,
                        verbose=False
                    )
                except Exception as e:
                    logger.warning(f"Trained model detection failed: {e}")
            
            # Collect all detections from both models
            all_detections = []
            
            # Process COCO model detections
            if coco_results and len(coco_results) > 0 and len(coco_results[0].boxes) > 0:
                boxes = coco_results[0].boxes
                logger.info(f"[COCO] Found {len(boxes)} raw detections")
                print(f"[COCO] Found {len(boxes)} raw detections")
                
                for box in boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = self.coco_model.names[class_id]
                    item_name = self._map_class_to_item(class_name)
                    
                    # Get bounding box coordinates
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])
                    box_width = x2 - x1
                    box_height = y2 - y1
                    box_area = box_width * box_height
                    
                    logger.info(f"[COCO] Raw: '{class_name}' -> Mapped: '{item_name}' (conf: {confidence:.2f}, area: {box_area:.0f})")
                    print(f"[COCO] Raw: '{class_name}' -> Mapped: '{item_name}' (conf: {confidence:.2f}, area: {box_area:.0f})")
                    
                    # Global confidence threshold: reject below 0.5
                    if confidence < 0.5:
                        logger.info(f"[COCO] ❌ Rejected: '{item_name}' (conf: {confidence:.2f} < 0.5 global threshold)")
                        continue
                    
                    # Bounding box area filtering: reject if box area > 60% of ROI area
                    box_area_percentage = (box_area / roi_area) * 100 if roi_area > 0 else 0
                    if box_area_percentage > 60:
                        logger.info(f"[COCO] ❌ Rejected: '{item_name}' (box area {box_area_percentage:.1f}% > 60% of ROI - likely background)")
                        print(f"[COCO] ❌ Rejected: '{item_name}' (box area {box_area_percentage:.1f}% > 60% of ROI)")
                        continue
                    
                    # Only consider known COCO items
                    if item_name in coco_items and item_name != "unknown":
                        all_detections.append({
                            "item_name": item_name,
                            "confidence": confidence,
                            "source": "coco",
                            "class_name": class_name,
                            "priority": 1,  # COCO items (fruits) have priority 1
                            "box_area": box_area,
                            "box_area_percentage": box_area_percentage
                        })
            
            # Process trained model detections
            if trained_results and len(trained_results) > 0 and len(trained_results[0].boxes) > 0:
                boxes = trained_results[0].boxes
                logger.info(f"[Trained] Found {len(boxes)} raw detections")
                print(f"[Trained] Found {len(boxes)} raw detections")
                
                for box in boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = self.trained_model.names[class_id]
                    item_name = self._map_class_to_item(class_name)
                    
                    # Get bounding box coordinates
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])
                    box_width = x2 - x1
                    box_height = y2 - y1
                    box_area = box_width * box_height
                    
                    logger.info(f"[Trained] Raw: '{class_name}' -> Mapped: '{item_name}' (conf: {confidence:.2f}, area: {box_area:.0f})")
                    print(f"[Trained] Raw: '{class_name}' -> Mapped: '{item_name}' (conf: {confidence:.2f}, area: {box_area:.0f})")
                    
                    # Global confidence threshold: reject below 0.5
                    if confidence < 0.5:
                        logger.info(f"[Trained] ❌ Rejected: '{item_name}' (conf: {confidence:.2f} < 0.5 global threshold)")
                        continue
                    
                    # Bounding box area filtering: reject if box area > 60% of ROI area
                    box_area_percentage = (box_area / roi_area) * 100 if roi_area > 0 else 0
                    if box_area_percentage > 60:
                        logger.info(f"[Trained] ❌ Rejected: '{item_name}' (box area {box_area_percentage:.1f}% > 60% of ROI - likely background)")
                        print(f"[Trained] ❌ Rejected: '{item_name}' (box area {box_area_percentage:.1f}% > 60% of ROI)")
                        continue
                    
                    # Only consider known office items
                    if item_name in office_items and item_name != "unknown":
                        # Determine priority based on item type
                        # Mouse has lower priority (2) to prevent false positives
                        # Other office items have higher priority (1)
                        priority = 2 if item_name == "mouse" else 1
                        
                        all_detections.append({
                            "item_name": item_name,
                            "confidence": confidence,
                            "source": "trained",
                            "class_name": class_name,
                            "priority": priority,
                            "box_area": box_area,
                            "box_area_percentage": box_area_percentage
                        })
            
            # Merge detections by confidence score and class priority
            if not all_detections:
                logger.warning("No known items detected in image")
                print("❌ No known items detected in image")
                return "unknown", 0.0
            
            # Apply class-specific confidence thresholds
            filtered_detections = []
            for det in all_detections:
                item_name = det["item_name"]
                confidence = det["confidence"]
                
                # Apply item-specific thresholds (higher for small items)
                if item_name == "mouse":
                    min_confidence = 0.7  # High threshold (0.6-0.8 range) for mouse
                elif item_name == "pen":
                    min_confidence = 0.65  # High threshold (0.6-0.8 range) for pen
                elif item_name in coco_items:
                    min_confidence = 0.5  # Global minimum for fruits
                else:
                    min_confidence = 0.5  # Global minimum for other office items
                
                if confidence >= min_confidence:
                    filtered_detections.append(det)
                    logger.info(f"[{det['source'].upper()}] ✅ Valid: '{item_name}' (conf: {confidence:.2f} >= {min_confidence}, area: {det.get('box_area_percentage', 0):.1f}%)")
                else:
                    logger.info(f"[{det['source'].upper()}] ❌ Rejected: '{item_name}' (conf: {confidence:.2f} < {min_confidence})")
            
            if not filtered_detections:
                logger.warning("No detections passed confidence thresholds")
                print("❌ No detections passed confidence thresholds")
                return "unknown", 0.0
            
            # Merge strategy: Sort by priority first (lower is better), then by confidence (higher is better)
            # Priority 1 items (fruits, office items) are preferred over priority 2 (mouse)
            # Within same priority, higher confidence wins
            # Sort key: (priority, -confidence) means:
            #   - Lower priority number wins (1 < 2)
            #   - Within same priority, higher confidence wins (negative for descending sort)
            filtered_detections.sort(key=lambda x: (x["priority"], -x["confidence"]))
            
            # Log all valid detections for debugging
            if len(filtered_detections) > 1:
                logger.info(f"Merged {len(filtered_detections)} valid detections:")
                for i, det in enumerate(filtered_detections[:5]):  # Show top 5
                    logger.info(f"  {i+1}. {det['item_name']} (conf: {det['confidence']:.2f}, priority: {det['priority']}, source: {det['source']})")
            
            best_detection = filtered_detections[0]
            best_item = best_detection["item_name"]
            best_confidence = best_detection["confidence"]
            best_source = best_detection["source"]
            
            total_time = time.time() - start_time
            
            logger.info(f"✅ Best detection: '{best_item}' (confidence: {best_confidence:.2f}, source: {best_source}, priority: {best_detection['priority']}, time: {total_time:.3f}s)")
            print(f"✅ Best detection: '{best_item}' (confidence: {best_confidence:.2f}, source: {best_source}, time: {total_time:.3f}s)")
            print(f"⚡ Detection speed: {total_time:.3f}s (preprocess: {preprocess_time:.3f}s)")
            
            return best_item, best_confidence
                
        except Exception as e:
            logger.error(f"Error during detection: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return "unknown", 0.0
    
    def detect_all(self, image_base64: str) -> List[dict]:
        """
        Detect all objects using both models and return combined results.
        
        Useful for debugging to see what the models actually detect.
        
        Args:
            image_base64: Base64 encoded image string
            
        Returns:
            List of dicts with detection info including source model
        """
        if not YOLO_AVAILABLE:
            return []
        
        all_detections = []
        
        try:
            image = self.preprocess_image(image_base64, target_size=640)
            
            # Try trained model
            if self.trained_model:
                try:
                    results = self.trained_model(
                        image, 
                        conf=0.25, 
                        imgsz=640,
                        device=self.device,
                        half=self.use_half,
                        verbose=False
                    )
                    if len(results) > 0 and len(results[0].boxes) > 0:
                        boxes = results[0].boxes
                        for box in boxes:
                            class_id = int(box.cls[0])
                            confidence = float(box.conf[0])
                            class_name = self.trained_model.names[class_id]
                            mapped_name = self._map_class_to_item(class_name)
                            
                            all_detections.append({
                                "class": class_name,
                                "confidence": round(confidence, 3),
                                "mapped": mapped_name,
                                "is_known": mapped_name != "unknown",
                                "source": "trained"
                            })
                except Exception as e:
                    logger.warning(f"Trained model detect_all failed: {e}")
            
            # Try COCO model
            if self.coco_model:
                try:
                    results = self.coco_model(
                        image, 
                        conf=0.25, 
                        imgsz=640,
                        device=self.device,
                        half=self.use_half,
                        verbose=False
                    )
                    if len(results) > 0 and len(results[0].boxes) > 0:
                        boxes = results[0].boxes
                        for box in boxes:
                            class_id = int(box.cls[0])
                            confidence = float(box.conf[0])
                            class_name = self.coco_model.names[class_id]
                            mapped_name = self._map_class_to_item(class_name)
                            
                            all_detections.append({
                                "class": class_name,
                                "confidence": round(confidence, 3),
                                "mapped": mapped_name,
                                "is_known": mapped_name != "unknown",
                                "source": "coco"
                            })
                except Exception as e:
                    logger.warning(f"COCO model detect_all failed: {e}")
            
            return all_detections
        except Exception as e:
            logger.error(f"Error in detect_all: {str(e)}")
            return []
    
    def detect_with_boxes(self, image_base64: str) -> Tuple[np.ndarray, List[dict]]:
        """
        Detect objects and return image with bounding boxes drawn, plus detection info.
        
        Args:
            image_base64: Base64 encoded image string
            
        Returns:
            Tuple of (annotated_image, detections_list)
            - annotated_image: numpy array with bounding boxes drawn
            - detections_list: List of dicts with detection info including box coordinates
        """
        if not YOLO_AVAILABLE:
            # Return original image if YOLO not available
            image = self.preprocess_image(image_base64, target_size=640)
            return image, []
        
        try:
            # Decode original image first to get original dimensions
            image_bytes = base64.b64decode(image_base64)
            nparr = np.frombuffer(image_bytes, np.uint8)
            original_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if original_image is None:
                raise ValueError("Failed to decode image from base64")
            
            original_h, original_w = original_image.shape[:2]
            
            # Preprocess for detection (resize to 640)
            detection_image = self.preprocess_image(image_base64, target_size=640)
            detection_h, detection_w = detection_image.shape[:2]
            
            # Calculate scale factors
            scale_x = original_w / detection_w
            scale_y = original_h / detection_h
            
            # Use original image for drawing (better visibility)
            image = original_image.copy()
            
            all_detections = []
            
            # Run both models
            coco_results = None
            trained_results = None
            
            if self.coco_model:
                try:
                    coco_results = self.coco_model(
                        detection_image,
                        conf=0.1,
                        imgsz=640,
                        device=self.device,
                        half=self.use_half,
                        verbose=False
                    )
                except Exception as e:
                    logger.warning(f"COCO model detection failed: {e}")
            
            if self.trained_model:
                try:
                    trained_results = self.trained_model(
                        detection_image,
                        conf=0.25,
                        imgsz=640,
                        device=self.device,
                        half=self.use_half,
                        verbose=False
                    )
                except Exception as e:
                    logger.warning(f"Trained model detection failed: {e}")
            
            # Draw boxes from COCO model
            if coco_results and len(coco_results) > 0 and len(coco_results[0].boxes) > 0:
                boxes = coco_results[0].boxes
                for box in boxes:
                    # Get box coordinates (xyxy format: x1, y1, x2, y2) from detection image
                    xyxy = box.xyxy[0].cpu().numpy()
                    # Scale coordinates back to original image size
                    x1 = int(xyxy[0] * scale_x)
                    y1 = int(xyxy[1] * scale_y)
                    x2 = int(xyxy[2] * scale_x)
                    y2 = int(xyxy[3] * scale_y)
                    
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = self.coco_model.names[class_id]
                    mapped_name = self._map_class_to_item(class_name)
                    
                    # Draw bounding box (green for COCO)
                    color = (0, 255, 0)  # Green
                    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                    
                    # Draw label
                    label = f"{mapped_name} ({class_name}) {confidence:.2f}"
                    label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(image, (x1, y1 - label_size[1] - 10), 
                                (x1 + label_size[0], y1), color, -1)
                    cv2.putText(image, label, (x1, y1 - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                    
                    all_detections.append({
                        "class": class_name,
                        "mapped": mapped_name,
                        "confidence": round(confidence, 3),
                        "source": "coco",
                        "box": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)}
                    })
            
            # Draw boxes from trained model
            if trained_results and len(trained_results) > 0 and len(trained_results[0].boxes) > 0:
                boxes = trained_results[0].boxes
                for box in boxes:
                    # Get box coordinates from detection image
                    xyxy = box.xyxy[0].cpu().numpy()
                    # Scale coordinates back to original image size
                    x1 = int(xyxy[0] * scale_x)
                    y1 = int(xyxy[1] * scale_y)
                    x2 = int(xyxy[2] * scale_x)
                    y2 = int(xyxy[3] * scale_y)
                    
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = self.trained_model.names[class_id]
                    mapped_name = self._map_class_to_item(class_name)
                    
                    # Draw bounding box (blue for trained model)
                    color = (255, 0, 0)  # Blue
                    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                    
                    # Draw label
                    label = f"{mapped_name} ({class_name}) {confidence:.2f}"
                    label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(image, (x1, y1 - label_size[1] - 10), 
                                (x1 + label_size[0], y1), color, -1)
                    cv2.putText(image, label, (x1, y1 - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    all_detections.append({
                        "class": class_name,
                        "mapped": mapped_name,
                        "confidence": round(confidence, 3),
                        "source": "trained",
                        "box": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)}
                    })
            
            return image, all_detections
        except Exception as e:
            logger.error(f"Error in detect_with_boxes: {str(e)}")
            # Return original image on error
            try:
                image = self.preprocess_image(image_base64, target_size=640)
                return image, []
            except Exception as e2:
                logger.error(f"Error preprocessing image in exception handler: {str(e2)}")
                # Return a black image as fallback
                return np.zeros((480, 640, 3), dtype=np.uint8), []
    
    def _map_class_to_item(self, class_name: str) -> str:
        """
        Map dataset class names to our item names.
        
        Handles both:
        - Trained model classes (office items with capital letters and hyphens)
        - COCO dataset classes (fruits/vegetables)
        
        Args:
            class_name: Class name from YOLO model
            
        Returns:
            str: Mapped item name
        """
        # Normalize to lowercase for matching
        normalized = class_name.lower().strip()
        
        # Complete mapping for all items
        # Office items from trained model (handles both "Book" and "book", "Computer-mouse" and "computer-mouse")
        class_mapping = {
            # Office items from trained model (Roboflow dataset)
            "book": "book",
            "calculator": "calculator",
            "chair": "chair",
            "computer-keyboard": "keyboard",
            "computerkeyboard": "keyboard",
            "keyboard": "keyboard",
            "computer-monitor": "monitor",
            "computermonitor": "monitor",
            "monitor": "monitor",
            "computer-mouse": "mouse",
            "computermouse": "mouse",
            "mouse": "mouse",
            "desk": "desk",
            "envelope": "envelope",
            "filing-cabinet": "filing-cabinet",
            "filingcabinet": "filing-cabinet",
            "laptop": "laptop",
            "luggage-and-bags": "luggage",
            "luggageandbags": "luggage",
            "luggage": "luggage",
            "mug": "mug",
            "pen": "pen",
            "printer": "printer",
            "scissors": "scissors",
            "shelf": "shelf",
            "stapler": "stapler",
            "wall-clock": "wall-clock",
            "wallclock": "wall-clock",
            "whiteboard": "whiteboard",
            
            # Fruits and vegetables (from COCO)
            "apple": "apple",
            "banana": "banana",
            "orange": "orange",
            
            # Common items (from COCO)
            "bottle": "bottle",
            "cup": "cup",
            "bowl": "bowl",
            
            # Additional items
            "pencil": "pencil",
            "phone": "phone",
            "tablet": "tablet",
            "notebook": "notebook",
            "eraser": "eraser",
            "ruler": "ruler",
        }
        
        # Try exact match first
        mapped = class_mapping.get(normalized)
        
        # Try without hyphens if not found
        if not mapped:
            no_hyphen = normalized.replace("-", "").replace("_", "")
            mapped = class_mapping.get(no_hyphen)
        
        # Try partial match for compound names
        if not mapped:
            for key, value in class_mapping.items():
                if key in normalized or normalized in key:
                    mapped = value
                    break
        
        # If still not found, return lowercase version if it's a known item
        if not mapped:
            mapped = normalized
        
        # List of all known items we support
        known_items = [
            # Office items
            "book", "calculator", "chair", "keyboard", "monitor", "mouse",
            "desk", "envelope", "filing-cabinet", "laptop", "luggage",
            "mug", "pen", "printer", "scissors", "shelf", "stapler",
            "wall-clock", "whiteboard",
            # Grocery items
            "tomato", "potato", "onion", "carrot", "cabbage",
            "apple", "banana", "orange", "bottle", "cup", "bowl",
            # Additional items
            "phone", "tablet", "pencil", "notebook", "eraser", "ruler"
        ]
        
        # Check if mapped item is in our known items list
        if mapped not in known_items:
            # Try to find a close match
            for known in known_items:
                if known in mapped or mapped in known:
                    return known
            return "unknown"
        
        return mapped


# Global model instance (lazy loading)
_model_instance: Optional[ObjectDetectionModel] = None


def get_model() -> ObjectDetectionModel:
    """
    Get or create the global model instance (singleton pattern).
    
    Returns:
        ObjectDetectionModel: The model instance
    """
    global _model_instance
    if _model_instance is None:
        _model_instance = ObjectDetectionModel()
    return _model_instance


def reset_model():
    """
    Reset the global model instance (useful after model updates).
    """
    global _model_instance
    _model_instance = None
    logger.info("Model instance reset. Will reload on next get_model() call.")

