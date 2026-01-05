"""
Item Detection Service

This service handles item detection using YOLOv8 AI model.
Falls back to mock detection if model is not available.
"""

from app.models.schemas import ItemInfo
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Try to import model service
try:
    from app.services.model_service import get_model
    MODEL_AVAILABLE = True
except ImportError:
    MODEL_AVAILABLE = False
    logger.warning("Model service not available. Using mock detection.")


def detect_item_from_image(image_base64: str) -> tuple:
    """
    Detect item from image using YOLOv8 AI model.
    
    This function:
    1. Decodes the base64 image
    2. Sends it to YOLOv8 model for detection
    3. Returns the detected item name and confidence
    
    Returns ("unknown", 0.0) if detection fails (no false positives).
    
    Args:
        image_base64: Base64 encoded image string
        
    Returns:
        tuple: (item_name, confidence) - Name of the detected item and confidence score
    """
    if MODEL_AVAILABLE:
        try:
            model = get_model()
            item_name, confidence = model.detect(image_base64)
            
            # Confidence threshold: 0.25 to allow more detections (model already filters at 0.25/0.4)
            # Lower threshold here to catch legitimate detections that might be slightly below 0.3
            if item_name != "unknown" and confidence > 0.25:
                logger.info(f"✅ Detected: {item_name} (confidence: {confidence:.2f})")
                return item_name, confidence
            else:
                logger.warning(f"⚠️  Low confidence or unknown item. Confidence: {confidence:.2f}, Item: {item_name}")
                # Return "unknown" instead of false positive
                return "unknown", confidence
        except Exception as e:
            logger.error(f"❌ Error in model detection: {str(e)}")
            # Return "unknown" instead of false positive
            return "unknown", 0.0
    else:
        # Model not available - return unknown
        logger.warning("Model not available - returning unknown")
        return "unknown", 0.0


# Items that are priced per piece (not by weight)
PER_PIECE_ITEMS = {
    "phone", "mouse", "keyboard", "laptop", "tablet", "pen", "pencil",
    "book", "notebook", "monitor", "eraser", "ruler", "calculator",
    "chair", "desk", "envelope", "filing-cabinet", "luggage", "mug",
    "printer", "scissors", "shelf", "stapler", "wall-clock", "whiteboard"
}

def get_item_info(item_name: str, weight_grams: float, shopkeeper_id: Optional[int] = None) -> ItemInfo:
    """
    Get complete information about an item including price calculation.
    
    This function:
    1. Looks up the price per kg for the item (from shopkeeper's prices or default)
    2. Calculates the total price based on weight
    3. Returns complete item information
    
    Args:
        item_name: Name of the item (e.g., "tomato")
        weight_grams: Weight of the item in grams
        shopkeeper_id: Optional shopkeeper ID to use shop-specific prices
        
    Returns:
        ItemInfo: Complete information about the item including calculated price
    """
    # Get price from database if shopkeeper_id is provided
    if shopkeeper_id:
        try:
            from app.services.database import db
            price_per_kg = db.get_price(shopkeeper_id, item_name)
            if price_per_kg is not None:
                weight_kg = weight_grams / 1000.0
                total_price = price_per_kg * weight_kg
                return ItemInfo(
                    name=item_name,
                    weight_grams=weight_grams,
                    price_per_kg=price_per_kg,
                    total_price=round(total_price, 2)
                )
        except Exception as e:
            logger.warning(f"Error fetching price from database: {e}, using default prices")
    
    # Fallback to default prices if no shopkeeper or database error
    # Hardcoded price table (price per kilogram or per item)
    # Used as fallback or for default shopkeeper
    PRICE_TABLE = {
        # Grocery items (price per kg)
        "tomato": 80.0,      # ₹80 per kg
        "potato": 40.0,      # ₹40 per kg
        "onion": 60.0,       # ₹60 per kg
        "carrot": 50.0,      # ₹50 per kg
        "cabbage": 30.0,     # ₹30 per kg
        "banana": 60.0,      # ₹60 per kg
        "apple": 100.0,      # ₹100 per kg
        "orange": 80.0,      # ₹80 per kg
        "cup": 100.0,        # ₹100 per kg (or per piece - adjust as needed)
        "bottle": 50.0,      # ₹50 per kg
        "bowl": 80.0,        # ₹80 per kg
        # Office/Stationery items (price per item - converted to per kg for calculation)
        "phone": 5000.0,     # ₹5000 per item
        "mouse": 500.0,      # ₹500 per item
        "keyboard": 1500.0,  # ₹1500 per item
        "laptop": 50000.0,  # ₹50000 per item
        "tablet": 20000.0,  # ₹20000 per item
        "pen": 10.0,        # ₹10 per item
        "pencil": 5.0,      # ₹5 per item
        "book": 200.0,      # ₹200 per item
        "notebook": 50.0,   # ₹50 per item
        "monitor": 10000.0, # ₹10000 per item
        "eraser": 5.0,      # ₹5 per item
        "ruler": 20.0,      # ₹20 per item
        "calculator": 300.0, # ₹300 per item
        "chair": 2000.0,    # ₹2000 per item
        "desk": 5000.0,     # ₹5000 per item
        "envelope": 5.0,    # ₹5 per item
        "filing-cabinet": 3000.0, # ₹3000 per item
        "luggage": 2000.0,  # ₹2000 per item
        "mug": 100.0,       # ₹100 per item
        "printer": 5000.0,  # ₹5000 per item
        "scissors": 50.0,   # ₹50 per item
        "shelf": 1500.0,    # ₹1500 per item
        "stapler": 100.0,   # ₹100 per item
        "wall-clock": 500.0, # ₹500 per item
        "whiteboard": 2000.0, # ₹2000 per item
        # Add more items as needed
    }
    
    # Get price per kg (default to 50 if item not found)
    price_per_kg = PRICE_TABLE.get(item_name.lower(), 50.0)
    
    # Check if item is priced per piece
    is_per_piece = item_name.lower() in PER_PIECE_ITEMS
    
    if is_per_piece:
        # For per-piece items, price_per_kg actually represents price per piece
        # Total price is just the price per piece (quantity will be handled in BillItem)
        total_price = price_per_kg
    else:
        # For weight-based items, calculate based on weight
        weight_kg = weight_grams / 1000.0
        total_price = price_per_kg * weight_kg
    
    return ItemInfo(
        name=item_name,
        weight_grams=weight_grams,
        price_per_kg=price_per_kg,
        total_price=round(total_price, 2)  # Round to 2 decimal places
    )

