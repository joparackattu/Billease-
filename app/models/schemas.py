"""
Request and Response Models (Schemas)

This file defines the data structures for API requests and responses.
Think of these as "contracts" that define what data the API expects and returns.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional


class ScanItemRequest(BaseModel):
    """
    Request model for scanning an item.
    
    This is what the ESP32 will send to the backend:
    - image: Optional base64 encoded image (if not provided, backend captures from RTSP)
    - weight_grams: Weight of the item in grams
    """
    image: Optional[str] = Field(None, description="Optional: Base64 encoded image. If not provided, backend captures from RTSP camera")
    weight_grams: float = Field(..., gt=0, description="Weight of the item in grams (must be > 0)")


class ItemInfo(BaseModel):
    """
    Information about a detected item.
    
    This represents a single item that was detected from the image.
    """
    name: str = Field(..., description="Name of the detected item (e.g., 'tomato')")
    weight_grams: float = Field(..., description="Weight of the item in grams")
    price_per_kg: float = Field(..., description="Price per kilogram")
    total_price: float = Field(..., description="Calculated total price for this item")


class BillItem(BaseModel):
    """
    A single item in the bill.
    
    This represents one line item in the shopping bill.
    """
    item_name: str
    weight_grams: float
    price_per_kg: float
    total_price: float
    quantity: int = 1  # Quantity for per-piece items (default 1)
    pricing_type: str = "weight"  # "weight" or "piece" - indicates if priced by weight or per piece
    gst_rate: float = 0.0  # GST % for this item's category
    gst_amount: float = 0.0  # GST amount (total_price * gst_rate / 100)


class ScanItemResponse(BaseModel):
    """
    Response model for the /scan-item endpoint.
    
    This is what the backend returns after processing an item:
    - detected_item: Information about what was detected
    - current_bill: The complete bill so far (all items scanned in this session)
    - bill_total: Total amount of the current bill
    """
    detected_item: Optional[ItemInfo] = None
    current_bill: list[BillItem] = Field(default_factory=list, description="All items in current bill session")
    bill_total: float = Field(..., description="Total price of all items in the bill")


class BillSession(BaseModel):
    """
    Represents a complete bill session.
    
    This is stored in memory to track all items scanned in a session.
    """
    session_id: str
    items: list[BillItem] = Field(default_factory=list)
    
    def get_subtotal(self) -> float:
        """Sum of item prices before GST."""
        return sum(item.total_price for item in self.items)
    
    def get_gst_total(self) -> float:
        """Sum of GST amounts for all items."""
        return sum(getattr(item, 'gst_amount', 0) for item in self.items)
    
    def get_total(self) -> float:
        """Total amount including GST (subtotal + gst_total)."""
        return self.get_subtotal() + self.get_gst_total()
    
    def add_item(self, item: BillItem):
        """Add an item to the bill."""
        self.items.append(item)


# Authentication schemas
class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., description="Shopkeeper username")
    password: str = Field(..., description="Shopkeeper password")


class LoginResponse(BaseModel):
    """Login response model."""
    token: str = Field(..., description="Session token")
    shopkeeper: dict = Field(..., description="Shopkeeper information")


class RegisterRequest(BaseModel):
    """Registration request model."""
    username: str = Field(..., description="Unique username")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    shop_name: str = Field(..., description="Name of the shop")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    
    @validator('email')
    def validate_email(cls, v):
        if v is None or v.strip() == '':
            return v
        import re
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        if v is None or v.strip() == '':
            return v
        import re
        # Remove spaces, dashes, parentheses, and plus signs
        cleaned = re.sub(r'[\s\-\(\)\+]', '', v)
        # Indian phone: 10 digits starting with 6-9, optionally with country code 91
        phone_pattern = r'^(91)?[6-9]\d{9}$'
        if not re.match(phone_pattern, cleaned) or len(cleaned) < 10 or len(cleaned) > 12:
            raise ValueError('Invalid phone number. Must be 10 digits (Indian format)')
        return v


class UpdateProfileRequest(BaseModel):
    """Update profile request model."""
    shop_name: Optional[str] = Field(None, description="Shop name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    
    @validator('email')
    def validate_email(cls, v):
        if v is None or v.strip() == '':
            return v
        import re
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        if v is None or v.strip() == '':
            return v
        import re
        # Remove spaces, dashes, parentheses, and plus signs
        cleaned = re.sub(r'[\s\-\(\)\+]', '', v)
        # Indian phone: 10 digits starting with 6-9, optionally with country code 91
        phone_pattern = r'^(91)?[6-9]\d{9}$'
        if not re.match(phone_pattern, cleaned) or len(cleaned) < 10 or len(cleaned) > 12:
            raise ValueError('Invalid phone number. Must be 10 digits (Indian format)')
        return v


# Price management schemas
class PriceUpdateRequest(BaseModel):
    """Price update request model."""
    item_name: str = Field(..., description="Item name")
    price_per_kg: float = Field(..., gt=0, description="Price per kilogram")


class ItemUpdateRequest(BaseModel):
    """Item update request model with all fields."""
    item_name: str = Field(..., description="Item name")
    cost_price: Optional[float] = Field(None, ge=0, description="Cost price")
    selling_price: Optional[float] = Field(None, gt=0, description="Selling price")
    pricing_type: Optional[str] = Field(None, description="Pricing type: kg, ltr, or units")


class ItemCreateRequest(BaseModel):
    """Item create request model."""
    item_name: str = Field(..., description="Item name")
    cost_price: Optional[float] = Field(None, ge=0, description="Cost price")
    selling_price: Optional[float] = Field(None, gt=0, description="Selling price")
    pricing_type: str = Field("kg", description="Pricing type: kg, ltr, or units")


class BulkPriceUpdateRequest(BaseModel):
    """Bulk price update request model."""
    prices: dict[str, float] = Field(..., description="Dictionary of {item_name: price_per_kg}")


class PriceResponse(BaseModel):
    """Price response model."""
    item_name: str
    price_per_kg: float


class ItemResponse(BaseModel):
    """Item response model with all fields."""
    item_name: str
    price_per_kg: float
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    pricing_type: str = "kg"


class PricesResponse(BaseModel):
    """All prices response model."""
    prices: dict[str, float] = Field(..., description="Dictionary of {item_name: price_per_kg}")


# Bill history schemas
class BillHistoryItem(BaseModel):
    """Bill history item model."""
    id: int
    bill_number: str
    total_amount: float
    items: list[BillItem]
    created_at: str


class BillHistoryResponse(BaseModel):
    """Bill history response model."""
    bills: list[BillHistoryItem]
    total: int = Field(..., description="Total number of bills")


# Statistics schemas
class EarningsData(BaseModel):
    """Earnings data point."""
    period: str = Field(..., description="Period label (e.g., 'Jan 15' or 'January 2024')")
    amount: float = Field(..., description="Total earnings for this period")
    count: int = Field(..., description="Number of bills in this period")


class MostSoldItem(BaseModel):
    """Most sold item data."""
    item_name: str = Field(..., description="Item name")
    total_quantity: float = Field(..., description="Total quantity sold (units for per-piece items, kg for weight-based items)")
    unit_type: str = Field(..., description="Unit type: 'units' for per-piece items, 'kg' for weight-based items")


class StatisticsResponse(BaseModel):
    """Statistics response model."""
    earnings: list[EarningsData] = Field(..., description="Earnings by period")
    most_sold_items: list[MostSoldItem] = Field(..., description="Most sold items")
    total_earnings: float = Field(..., description="Total earnings across all periods")
    total_bills: int = Field(..., description="Total number of bills")

