"""
BILLESE - AI-based Smart Billing System
Main FastAPI Application

This is the entry point of the backend application.
It sets up the FastAPI server and defines all API endpoints.

To run this application:
    uvicorn main:app --reload

The server will start at: http://localhost:8000
API documentation will be available at: http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, Query, Depends, Header, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import cv2
import base64
import time
import logging
import os
import asyncio
import sqlite3
from io import BytesIO
from typing import Optional, List
from datetime import datetime
from pathlib import Path
from app.models.schemas import (
    ScanItemRequest, ScanItemResponse, BillItem,
    LoginRequest, LoginResponse, RegisterRequest, UpdateProfileRequest,
    PriceUpdateRequest, BulkPriceUpdateRequest, PricesResponse,
    ItemUpdateRequest, ItemCreateRequest, ItemResponse,
    BillHistoryResponse, BillHistoryItem,
    StatisticsResponse
)
from app.services.item_detection import detect_item_from_image, get_item_info
from app.services.bill_manager import bill_manager
from app.services.camera_service import RTSPCameraService
from app.services.dataset_collector import dataset_collector
from app.services.detection_state import detection_state
from app.services.auth_service import auth_service
from app.services.database import db

logger = logging.getLogger(__name__)

# RTSP URL for TP-Link Tapo C210
# Format: rtsp://username:password@ip:port/path
# Working format discovered: /stream1
RTSP_URL = os.getenv(
    "RTSP_URL", 
    "rtsp://Billease:12344321@172.20.10.13:554/stream1"
)

# Initialize camera service
camera_service = RTSPCameraService(RTSP_URL)

# Security
security = HTTPBearer(auto_error=False)

# Create FastAPI application instance
app = FastAPI(
    title="BILLESE API",
    description="AI-based Smart Billing System - Backend API",
    version="1.0.0"
)

# Add CORS middleware to allow requests from ESP32 and frontend
# CORS (Cross-Origin Resource Sharing) allows the ESP32 to make requests
# from a different origin (different IP address/port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Authentication dependency
async def get_current_shopkeeper(
    authorization: Optional[str] = Header(None)
) -> Optional[dict]:
    """
    Get current shopkeeper from authorization token.
    Returns None if not authenticated (for optional auth endpoints).
    """
    if not authorization:
        return None
    
    # Extract token from "Bearer <token>" format
    try:
        token = authorization.replace("Bearer ", "").strip()
        session = auth_service.validate_token(token)
        return session
    except Exception:
        return None


async def require_auth(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> dict:
    """
    Require authentication. Raises HTTPException if not authenticated.
    """
    if not authorization:
        logger.warning("Authentication required but no authorization header provided")
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Handle both "Bearer <token>" and just "<token>" formats
        token = authorization.replace("Bearer ", "").replace("bearer ", "").strip()
        if not token:
            logger.warning("Authorization header provided but token is empty")
            raise HTTPException(status_code=401, detail="Invalid token format")
        
        session = auth_service.validate_token(token)
        if not session:
            logger.warning(f"Token validation failed for token: {token[:8]}...")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        logger.debug(f"Authentication successful for shopkeeper ID: {session['shopkeeper_id']}")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """
    Initialize services when server starts.
    
    - Sets default ROI (Region of Interest) permanently
    - Starts RTSP camera reader (runs continuously in background)
    - Tests RTSP connection (non-blocking)
    """
    print("🚀 Starting BILLESE services...")
    
    # Set default ROI (Region of Interest) permanently
    # This crops the camera feed to focus on the platform area
    DEFAULT_ROI_X = 450
    DEFAULT_ROI_Y = 20
    DEFAULT_ROI_WIDTH = 950
    DEFAULT_ROI_HEIGHT = 900
    
    print("📐 Setting default ROI (Region of Interest)...")
    try:
        camera_service.set_crop_region(DEFAULT_ROI_X, DEFAULT_ROI_Y, DEFAULT_ROI_WIDTH, DEFAULT_ROI_HEIGHT)
        print(f"✅ Default ROI set permanently: x={DEFAULT_ROI_X}, y={DEFAULT_ROI_Y}, width={DEFAULT_ROI_WIDTH}, height={DEFAULT_ROI_HEIGHT}")
        logger.info(f"Default ROI set permanently: x={DEFAULT_ROI_X}, y={DEFAULT_ROI_Y}, width={DEFAULT_ROI_WIDTH}, height={DEFAULT_ROI_HEIGHT}")
    except Exception as e:
        print(f"⚠️  Warning: Could not set default ROI: {e}")
        logger.warning(f"Could not set default ROI: {e}")
    
    # Start RTSP reader ONCE at startup (runs continuously in background)
    print("📹 Starting RTSP camera reader...")
    try:
        camera_service.start_rtsp_reader()
        print("✅ RTSP reader thread started (will run continuously)")
    except Exception as e:
        print(f"⚠️  Failed to start RTSP reader: {e}")
        print("   Server will continue, but camera may not work")
    
    # Test RTSP connection (non-blocking, just for verification)
    print("🔍 Testing RTSP camera connection...")
    try:
        # Run test in executor to avoid blocking startup
        loop = asyncio.get_event_loop()
        success, working_url = await loop.run_in_executor(
            None,
            lambda: camera_service.test_connection(try_alternatives=False, quick_test=True)
        )
        
        if success:
            print(f"✅ RTSP camera connection successful!")
            if working_url and working_url != RTSP_URL:
                from urllib.parse import urlparse
                parsed_working = urlparse(working_url)
                print(f"   Using URL path: {parsed_working.path}{parsed_working.query}")
        else:
            print("⚠️  Quick camera test failed (camera may be offline or URL incorrect).")
            print("   RTSP reader will keep trying to connect in background.")
            print("   To test manually: curl http://localhost:8000/test-camera")
    except Exception as e:
        print(f"⚠️  Camera test error: {str(e)}")
        print("   RTSP reader will keep trying to connect in background.")
    
    print("✅ Application startup complete.")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when server shuts down."""
    print("🛑 Shutting down BILLESE services...")
    try:
        camera_service.stop_rtsp_reader()
        print("✅ RTSP reader stopped")
    except Exception as e:
        print(f"⚠️  Error stopping RTSP reader: {e}")
    print("✅ Shutdown complete.")


@app.get("/")
async def root():
    """
    Root endpoint - Welcome message.
    
    This is a simple endpoint to check if the server is running.
    """
    return {
        "message": "Welcome to BILLESE API",
        "version": "1.0.0",
        "endpoints": {
            "auth": {
                "register": "POST /auth/register",
                "login": "POST /auth/login",
                "logout": "POST /auth/logout"
            },
            "prices": {
                "get_all": "GET /prices",
                "update": "PUT /prices/{item_name}",
                "bulk_update": "PUT /prices"
            },
            "bills": {
                "history": "GET /bills/history",
                "save": "POST /bills/save"
            },
            "scan_item": "POST /scan-item",
            "test_camera": "GET /test-camera",
            "camera_view": "GET /camera/view - View camera feed in browser",
            "camera_frame": "GET /camera/frame - Get single frame as image",
            "detect_debug": "GET /detect/debug - See what model detects",
            "detect_capabilities": "GET /detect/capabilities - List all detectable items",
            "dataset_capture": "POST /dataset/capture - Capture image for training dataset",
            "dataset_stats": "GET /dataset/stats - View dataset statistics",
            "camera_crop_set": "POST /camera/crop/set - Set crop region",
            "camera_crop_get": "GET /camera/crop - Get current crop settings",
            "camera_crop_clear": "POST /camera/crop/clear - Clear crop (use full frame)",
            "camera_crop_view": "GET /camera/crop/view - Visual crop selector",
            "docs": "GET /docs"
        }
    }


# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/auth/register", response_model=dict)
async def register(request: RegisterRequest):
    """
    Register a new shopkeeper account.
    """
    try:
        shopkeeper_id = db.create_shopkeeper(
            username=request.username,
            password=request.password,
            shop_name=request.shop_name,
            email=request.email,
            phone=request.phone
        )
        
        # Get the created shopkeeper data (including billease_id)
        shopkeeper = db.get_shopkeeper(shopkeeper_id)
        if not shopkeeper:
            raise HTTPException(status_code=500, detail="Failed to retrieve created shopkeeper")
        
        return {
            "message": "Shopkeeper registered successfully",
            "shopkeeper_id": shopkeeper_id,
            "shopkeeper": shopkeeper
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login and get session token.
    """
    try:
        result = auth_service.login(request.username, request.password)
        if not result:
            logger.warning(f"Login failed for username: {request.username}")
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Validate response structure
        if "token" not in result or "shopkeeper" not in result:
            logger.error(f"Invalid login response structure: {result}")
            raise HTTPException(status_code=500, detail="Internal server error during login")
        
        return LoginResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")


@app.get("/auth/validate")
async def validate_token(session: dict = Depends(get_current_shopkeeper)):
    """
    Validate current token and return session info.
    
    Returns 200 if token is valid, 401 if invalid/expired.
    """
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {
        "valid": True,
        "shopkeeper_id": session["shopkeeper_id"],
        "username": session["username"],
        "shop_name": session.get("shop_name", "")
    }


@app.get("/auth/profile", response_model=dict)
async def get_profile(session: dict = Depends(require_auth)):
    """
    Get current shopkeeper profile information.
    """
    try:
        shopkeeper_id = session["shopkeeper_id"]
        
        # First, ensure billease_id column exists
        try:
            conn = db._get_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(shopkeepers)")
            columns = [column[1] for column in cursor.fetchall()]
            has_billease_id = 'billease_id' in columns
            
            if not has_billease_id:
                # Add column if it doesn't exist (without UNIQUE constraint first)
                try:
                    cursor.execute("ALTER TABLE shopkeepers ADD COLUMN billease_id TEXT")
                    conn.commit()
                    logger.info("Added billease_id column to shopkeepers table")
                    # Create unique index
                    try:
                        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_shopkeepers_billease_id ON shopkeepers(billease_id)")
                        conn.commit()
                        logger.info("Created unique index on billease_id")
                    except sqlite3.OperationalError as idx_error:
                        logger.debug(f"Index may already exist: {idx_error}")
                except sqlite3.OperationalError as e:
                    if "duplicate column" not in str(e).lower():
                        logger.warning(f"Error adding billease_id column: {e}")
            
            conn.close()
        except Exception as e:
            logger.warning(f"Error checking/adding billease_id column: {e}")
        
        # Get shopkeeper data
        shopkeeper = db.get_shopkeeper(shopkeeper_id)
        if not shopkeeper:
            raise HTTPException(status_code=404, detail="Shopkeeper not found")
        
        # Ensure billease_id exists (generate if missing)
        if not shopkeeper.get("billease_id"):
            try:
                billease_id = db._generate_billease_id()
                conn = db._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE shopkeepers 
                    SET billease_id = ? 
                    WHERE id = ?
                """, (billease_id, shopkeeper_id))
                conn.commit()
                conn.close()
                shopkeeper["billease_id"] = billease_id
                logger.info(f"✅ Generated Billease ID {billease_id} for shopkeeper {shopkeeper_id}")
            except Exception as e:
                logger.error(f"Error generating billease_id: {e}", exc_info=True)
        
        return {"shopkeeper": shopkeeper}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")


@app.post("/auth/logout")
async def logout(session: dict = Depends(require_auth)):
    """
    Logout and invalidate session.
    """
    # Token extraction would be needed here, but for now this is a placeholder
    return {"message": "Logout successful"}


@app.put("/auth/profile", response_model=dict)
async def update_profile(
    request: UpdateProfileRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    session: dict = Depends(require_auth)
):
    """
    Update shopkeeper profile information.
    """
    try:
        shopkeeper_id = session["shopkeeper_id"]
        
        # Update profile
        success = db.update_shopkeeper(
            shopkeeper_id=shopkeeper_id,
            shop_name=request.shop_name,
            email=request.email,
            phone=request.phone
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Get updated shopkeeper data
        updated_shopkeeper = db.get_shopkeeper(shopkeeper_id)
        if not updated_shopkeeper:
            raise HTTPException(status_code=404, detail="Shopkeeper not found")
        
        # Update session with new shop name if changed
        if request.shop_name and authorization:
            try:
                token = authorization.replace("Bearer ", "").replace("bearer ", "").strip()
                if token and token in auth_service.sessions:
                    auth_service.sessions[token]["shop_name"] = request.shop_name
            except:
                pass
        
        return {
            "message": "Profile updated successfully",
            "shopkeeper": updated_shopkeeper
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


# ==================== PRICE MANAGEMENT ENDPOINTS ====================

@app.get("/prices", response_model=PricesResponse)
async def get_prices(session: dict = Depends(require_auth)):
    """
    Get all prices for the current shopkeeper (backward compatible).
    """
    shopkeeper_id = session["shopkeeper_id"]
    prices = db.get_all_prices(shopkeeper_id)
    return PricesResponse(prices=prices)


@app.get("/prices/items", response_model=List[ItemResponse])
async def get_all_items(session: dict = Depends(require_auth)):
    """
    Get all items with complete details (cost price, selling price, pricing type).
    """
    shopkeeper_id = session["shopkeeper_id"]
    items = db.get_all_items(shopkeeper_id)
    return [ItemResponse(**item) for item in items]


@app.put("/prices/{item_name}", response_model=dict)
async def update_price(
    item_name: str,
    request: PriceUpdateRequest,
    session: dict = Depends(require_auth)
):
    """
    Update price for a specific item (backward compatible).
    """
    shopkeeper_id = session["shopkeeper_id"]
    db.set_price(shopkeeper_id, item_name, request.price_per_kg)
    return {
        "message": f"Price updated for {item_name}",
        "item_name": item_name,
        "price_per_kg": request.price_per_kg
    }


@app.put("/prices/{item_name}/details", response_model=ItemResponse)
async def update_item_details(
    item_name: str,
    request: ItemUpdateRequest,
    session: dict = Depends(require_auth)
):
    """
    Update item details including cost price, selling price, and pricing type.
    """
    shopkeeper_id = session["shopkeeper_id"]
    db.update_item(
        shopkeeper_id=shopkeeper_id,
        item_name=item_name,
        cost_price=request.cost_price,
        selling_price=request.selling_price,
        pricing_type=request.pricing_type
    )
    item = db.get_item_details(shopkeeper_id, item_name)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse(**item)


@app.post("/prices/items", response_model=ItemResponse)
async def create_item(
    request: ItemCreateRequest,
    session: dict = Depends(require_auth)
):
    """
    Create a new item with cost price, selling price, and pricing type.
    """
    shopkeeper_id = session["shopkeeper_id"]
    db.create_item(
        shopkeeper_id=shopkeeper_id,
        item_name=request.item_name,
        cost_price=request.cost_price,
        selling_price=request.selling_price,
        pricing_type=request.pricing_type
    )
    item = db.get_item_details(shopkeeper_id, request.item_name)
    if not item:
        raise HTTPException(status_code=500, detail="Failed to create item")
    return ItemResponse(**item)


@app.put("/prices", response_model=dict)
async def bulk_update_prices(
    request: BulkPriceUpdateRequest,
    session: dict = Depends(require_auth)
):
    """
    Update multiple prices at once.
    """
    shopkeeper_id = session["shopkeeper_id"]
    db.update_prices_bulk(shopkeeper_id, request.prices)
    return {
        "message": f"Updated {len(request.prices)} prices",
        "updated_count": len(request.prices)
    }


# ==================== BILL HISTORY ENDPOINTS ====================

@app.get("/bills/history", response_model=BillHistoryResponse)
async def get_bill_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: dict = Depends(require_auth)
):
    """
    Get bill history for the current shopkeeper.
    """
    shopkeeper_id = session["shopkeeper_id"]
    bills = db.get_bill_history(shopkeeper_id, limit=limit, offset=offset)
    
    bill_items = [
        BillHistoryItem(
            id=bill["id"],
            bill_number=bill["bill_number"],
            total_amount=bill["total_amount"],
            items=[BillItem(**item) for item in bill["items"]],
            created_at=bill["created_at"]
        )
        for bill in bills
    ]
    
    return BillHistoryResponse(bills=bill_items, total=len(bill_items))


@app.post("/bills/save", response_model=dict)
async def save_bill(
    request: dict = Body(...),
    session_id: str = Query(...),
    session: dict = Depends(require_auth)
):
    """
    Save current bill to history.
    """
    shopkeeper_id = session["shopkeeper_id"]
    bill_session = bill_manager.get_session(session_id)
    
    if not bill_session.items:
        raise HTTPException(status_code=400, detail="Bill is empty")
    
    # Get unpaid parameters from request body
    is_unpaid = request.get("is_unpaid", False)
    customer_name = request.get("customer_name")
    customer_phone = request.get("customer_phone")
    
    # Validate unpaid requirements
    if is_unpaid:
        if not customer_name or not customer_name.strip():
            raise HTTPException(status_code=400, detail="Customer name is required for unpaid bills")
        # Phone is optional - will be looked up from customer name if not provided
    # Note: For paid bills, customer_name and customer_phone are optional but will create customer if both provided
    
    # Convert BillItems to dicts (include pricing_type, quantity, gst_rate, gst_amount)
    items = [
        {
            "item_name": item.item_name,
            "weight_grams": item.weight_grams,
            "price_per_kg": item.price_per_kg,
            "total_price": item.total_price,
            "quantity": getattr(item, 'quantity', 1),
            "pricing_type": getattr(item, 'pricing_type', 'weight'),
            "gst_rate": getattr(item, 'gst_rate', 0),
            "gst_amount": getattr(item, 'gst_amount', 0),
        }
        for item in bill_session.items
    ]
    
    try:
        bill_number = db.save_bill(
            shopkeeper_id=shopkeeper_id,
            items=items,
            total_amount=bill_session.get_total(),
            is_unpaid=is_unpaid,
            customer_name=customer_name.strip() if customer_name else None,
            customer_phone=customer_phone.strip() if customer_phone else None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Clear the session after saving
    bill_manager.clear_session(session_id)
    
    return {
        "message": "Bill saved successfully",
        "bill_number": bill_number,
        "total_amount": bill_session.get_total()
    }


# ==================== CUSTOMERS & ACCOUNTS ENDPOINTS ====================

@app.get("/accounts/customers", response_model=dict)
async def get_customers_with_pending(
    session: dict = Depends(require_auth)
):
    """
    Get all customers with pending (unpaid) bills and their total pending amount.
    """
    shopkeeper_id = session["shopkeeper_id"]
    customers = db.get_customers_with_pending(shopkeeper_id)
    
    return {
        "customers": customers,
        "total": len(customers)
    }


@app.get("/accounts/customers/{customer_id}/bills", response_model=dict)
async def get_customer_unpaid_bills(
    customer_id: int,
    session: dict = Depends(require_auth)
):
    """
    Get all unpaid bills for a specific customer.
    """
    shopkeeper_id = session["shopkeeper_id"]
    bills = db.get_customer_unpaid_bills(shopkeeper_id, customer_id)
    
    return {
        "bills": bills,
        "total": len(bills)
    }


@app.get("/customers", response_model=dict)
async def get_all_customers(
    session: dict = Depends(require_auth)
):
    """
    Get all customers for the authenticated shopkeeper.
    """
    shopkeeper_id = session["shopkeeper_id"]
    customers = db.get_all_customers(shopkeeper_id)
    
    return {
        "customers": customers,
        "total": len(customers)
    }


@app.post("/customers", response_model=dict)
async def create_customer(
    request: dict = Body(...),
    session: dict = Depends(require_auth)
):
    """
    Create a new customer.
    """
    shopkeeper_id = session["shopkeeper_id"]
    name = request.get("name", "").strip()
    phone = request.get("phone", "").strip()
    
    if not name:
        raise HTTPException(status_code=400, detail="Customer name is required")
    
    if not phone:
        raise HTTPException(status_code=400, detail="Customer phone is required")
    
    try:
        customer_id = db.create_customer(shopkeeper_id, name, phone)
        customer = db.get_customer_by_name(shopkeeper_id, name)
        
        return {
            "message": "Customer created successfully",
            "customer_id": customer_id,
            "customer": customer
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/customers/{customer_id}", response_model=dict)
async def delete_customer(
    customer_id: int,
    session: dict = Depends(require_auth)
):
    """
    Delete a customer (only if they have no unpaid bills).
    """
    shopkeeper_id = session["shopkeeper_id"]
    
    try:
        success = db.delete_customer(shopkeeper_id, customer_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        return {
            "message": "Customer deleted successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== LOGISTICS / STOCK ENDPOINTS ====================

@app.get("/logistics/stock", response_model=dict)
async def get_stock_list(session: dict = Depends(require_auth)):
    """
    Get all stock items (inventory) for the current shopkeeper.
    Quantities are deducted automatically when bills are saved.
    """
    shopkeeper_id = session["shopkeeper_id"]
    items = db.get_stock_list(shopkeeper_id)
    return {"stock": items}


@app.post("/logistics/stock", response_model=dict)
async def add_or_update_stock(
    request: dict = Body(...),
    session: dict = Depends(require_auth)
):
    """
    Add quantity to stock. If item exists, adds to current quantity.
    If item is new, creates it with the given quantity.
    Body: { "item_name": "...", "quantity": number, "unit": "kg" | "unit" | "ltr" }
    """
    shopkeeper_id = session["shopkeeper_id"]
    item_name = (request.get("item_name") or "").strip()
    quantity = request.get("quantity")
    unit = (request.get("unit") or "kg").strip().lower() or "kg"
    if not item_name:
        raise HTTPException(status_code=400, detail="Item name is required")
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Quantity must be a number")
    if quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")
    try:
        # Add to existing stock if item exists, else create new
        row = db.adjust_stock_quantity(shopkeeper_id, item_name, quantity)
        if row is None:
            row = db.add_or_update_stock(shopkeeper_id, item_name, quantity, unit=unit)
        return {"message": "Stock updated successfully", "stock": row}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/logistics/stock/{item_name:path}", response_model=dict)
async def update_stock_quantity(
    item_name: str,
    request: dict = Body(...),
    session: dict = Depends(require_auth)
):
    """
    Update quantity/unit for an existing stock item.
    Body: { "quantity": number, "unit": "kg" | "unit" | "ltr" (optional) }
    """
    shopkeeper_id = session["shopkeeper_id"]
    quantity = request.get("quantity")
    unit = (request.get("unit") or "kg").strip().lower() or "kg"
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Quantity must be a number")
    if quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")
    try:
        row = db.add_or_update_stock(shopkeeper_id, item_name.strip(), quantity, unit=unit)
        return {"message": "Stock updated successfully", "stock": row}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/logistics/stock/{item_name:path}", response_model=dict)
async def delete_stock_item(
    item_name: str,
    session: dict = Depends(require_auth)
):
    """Remove an item from stock."""
    shopkeeper_id = session["shopkeeper_id"]
    deleted = db.delete_stock_item(shopkeeper_id, item_name.strip())
    if not deleted:
        raise HTTPException(status_code=404, detail="Stock item not found")
    return {"message": "Stock item removed"}


@app.post("/accounts/bills/{bill_id}/mark-paid", response_model=dict)
async def mark_bill_as_paid(
    bill_id: int,
    session: dict = Depends(require_auth)
):
    """
    Mark a bill as paid (set is_unpaid to 0).
    """
    shopkeeper_id = session["shopkeeper_id"]
    success = db.mark_bill_as_paid(shopkeeper_id, bill_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Bill not found or already paid")
    
    return {
        "message": "Bill marked as paid successfully",
        "bill_id": bill_id
    }


# ==================== STATISTICS, ANALYTICS & GST ENDPOINTS ====================

@app.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    period: str = Query("days", regex="^(days|months)$"),
    session: dict = Depends(require_auth),
):
    """Get business statistics for the current shopkeeper (quick overview)."""
    shopkeeper_id = session["shopkeeper_id"]
    stats = db.get_statistics(shopkeeper_id, period=period)
    return StatisticsResponse(**stats)


@app.get("/analytics", response_model=dict)
async def get_analytics(session: dict = Depends(require_auth)):
    """
    Deeper analytics for the Analytics page: summary, top items by revenue,
    bills by day of week, low stock.
    """
    shopkeeper_id = session["shopkeeper_id"]
    return db.get_analytics(shopkeeper_id)


@app.get("/gst/settings", response_model=dict)
async def get_gst_settings(session: dict = Depends(require_auth)):
    """
    Get GST category settings for the current shopkeeper.
    Rates are fixed by government slabs (read-only).
    """
    shopkeeper_id = session["shopkeeper_id"]
    settings = db.get_gst_settings(shopkeeper_id)
    return {"categories": settings}


@app.get("/gst/analytics", response_model=dict)
async def get_gst_analytics(session: dict = Depends(require_auth)):
    """
    Get GST analytics: total GST collected, this month, last month, today.
    Helps shopkeeper understand how much GST is paid to the government.
    """
    shopkeeper_id = session["shopkeeper_id"]
    return db.get_gst_analytics(shopkeeper_id)


@app.put("/gst/settings/{category_key}", response_model=dict)
async def update_gst_setting(
    category_key: str,
    request: dict = Body(...),
    session: dict = Depends(require_auth),
):
    """
    Update GST rate for a category.
    Body: { "rate": number }
    """
    shopkeeper_id = session["shopkeeper_id"]
    rate = request.get("rate")
    try:
        rate = float(rate)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="GST rate must be a number")
    if rate < 0:
        raise HTTPException(status_code=400, detail="GST rate cannot be negative")
    updated = db.update_gst_rate(shopkeeper_id, category_key, rate)
    return {"message": "GST rate updated", "category": updated}


@app.get("/test-camera")
async def test_camera():
    """
    Test RTSP camera connection and capture.
    
    Useful for debugging camera connection issues.
    Returns detailed information about the connection attempt.
    """
    import socket
    from urllib.parse import urlparse
    
    result = {
        "rtsp_url": RTSP_URL.split('@')[0] + "@...",  # Hide password
        "status": "unknown"
    }
    
    # Parse RTSP URL to get IP and port
    try:
        parsed = urlparse(RTSP_URL)
        camera_ip = parsed.hostname
        camera_port = parsed.port or 554
        
        # Test basic network connectivity
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            connection_result = sock.connect_ex((camera_ip, camera_port))
            sock.close()
            
            if connection_result == 0:
                result["network_test"] = "success"
                result["camera_reachable"] = True
            else:
                result["network_test"] = "failed"
                result["camera_reachable"] = False
                result["error"] = f"Cannot reach {camera_ip}:{camera_port}"
        except Exception as e:
            result["network_test"] = "error"
            result["error"] = str(e)
    except Exception as e:
        result["url_parse_error"] = str(e)
    
    # Test RTSP connection (try alternatives)
    success, working_url = camera_service.test_connection(try_alternatives=True)
    if success:
        result["rtsp_connection"] = "success"
        if working_url:
            from urllib.parse import urlparse
            parsed = urlparse(working_url)
            result["working_url"] = working_url.split('@')[0] + "@..."  # Hide password
            result["working_url_path"] = f"{parsed.path}{parsed.query}"  # Show path for reference
            if working_url != RTSP_URL:
                result["note"] = "Using different URL format than configured"
                result["suggestion"] = f"Update RTSP_URL in main.py to: rtsp://TAPOC210:nav123een123@192.168.20.4:554{parsed.path}{parsed.query}"
        
        frame = camera_service.capture_frame()
        if frame:
            result["status"] = "success"
            result["message"] = "Camera working!"
            result["frame_size_bytes"] = len(frame)
            result["frame_capture"] = "success"
        else:
            result["status"] = "partial"
            result["message"] = "RTSP connection OK but failed to capture frame"
            result["frame_capture"] = "failed"
    else:
        result["status"] = "error"
        result["message"] = "Failed to connect to RTSP camera (tried multiple URL formats)"
        result["rtsp_connection"] = "failed"
        result["suggestions"] = [
            "Check RTSP is enabled in Tapo app",
            "Try: rtsp://user:pass@ip:554/stream1",
            "Try: rtsp://user:pass@ip:554/cam/realmonitor?channel=1&subtype=0",
            "Verify camera IP is correct and accessible"
        ]
    
    return result


@app.get("/camera/status")
async def camera_status():
    """
    Quick check of camera connection status.
    
    Returns simple status information about the camera.
    """
    success, working_url = camera_service.test_connection(try_alternatives=False)
    
    status = {
        "connected": success,
        "rtsp_url": RTSP_URL.split('@')[0] + "@...",
        "timestamp": time.time()
    }
    
    if success:
        status["message"] = "Camera is connected and working"
        # Try to capture a frame to verify it's actually working (async)
        loop = asyncio.get_event_loop()
        try:
            frame = await asyncio.wait_for(
                loop.run_in_executor(None, camera_service.capture_frame, 0, True, 1280),
                timeout=3.0
            )
        except asyncio.TimeoutError:
            frame = None
        
        if frame:
            status["frame_capture"] = "success"
            status["frame_size_bytes"] = len(frame)
        else:
            status["frame_capture"] = "failed"
            status["message"] = "Camera connected but frame capture failed"
    else:
        status["message"] = "Camera is not connected"
        status["frame_capture"] = "not_attempted"
    
    return status


def _make_camera_placeholder_jpeg(width: int = 640, height: int = 360) -> bytes:
    """Generate a placeholder JPEG when camera is offline (gray image with text)."""
    import numpy as np
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (60, 60, 60)  # Dark gray
    # Draw "Camera offline" text
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = "Camera offline"
    font_scale = min(width, height) / 400.0
    thickness = max(1, int(font_scale * 2))
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    x = (width - tw) // 2
    y = (height + th) // 2
    cv2.putText(img, text, (x, y), font, font_scale, (200, 200, 200), thickness, cv2.LINE_AA)
    _, buffer = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    return buffer.tobytes()


@app.get("/camera/frame")
async def camera_frame(max_width: int = 1280):
    """
    Get a single frame from the camera as a JPEG image (ZERO-LAG).
    
    Returns the latest cached frame from memory (never touches RTSP).
    When camera is offline, returns a placeholder image so the UI always has something to show.
    
    Args:
        max_width: Maximum width in pixels (default: 1280). Use 640 for faster/low-res.
    """
    try:
        # ZERO-LAG: capture_frame reads from memory only (no RTSP access)
        loop = asyncio.get_event_loop()
        frame_base64 = await loop.run_in_executor(
            None,
            camera_service.capture_frame,
            0,
            True,
            max_width,
        )
        
        if frame_base64:
            image_bytes = base64.b64decode(frame_base64)
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Content-Type-Options": "nosniff",
                "X-Camera-Status": "live",
            }
        else:
            # Camera offline: return placeholder so frontend always gets a valid image
            height = int(360 * max_width / 640) if max_width else 360
            image_bytes = _make_camera_placeholder_jpeg(max_width or 640, height)
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Content-Type-Options": "nosniff",
                "X-Camera-Status": "offline",
            }
        
        return Response(
            content=image_bytes,
            media_type="image/jpeg",
            headers=headers,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Camera frame capture timeout"
        )
    except Exception as e:
        logger.error(f"Error in camera_frame: {str(e)}")
        # Still return placeholder on error so UI doesn't break
        try:
            image_bytes = _make_camera_placeholder_jpeg(min(max_width, 640), 360)
            return Response(
                content=image_bytes,
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "X-Camera-Status": "offline",
                },
            )
        except Exception:
            raise HTTPException(
                status_code=500,
                detail=f"Error capturing frame: {str(e)}"
            )


@app.post("/camera/set-roi")
async def set_camera_roi(
    x: int = Query(..., description="X coordinate of top-left corner"),
    y: int = Query(..., description="Y coordinate of top-left corner"),
    width: int = Query(..., description="Width of ROI region"),
    height: int = Query(..., description="Height of ROI region")
):
    """
    Set Region of Interest (ROI) for camera feed.
    
    This crops the camera feed to focus on the white platform area.
    Only the cropped region will be used for detection.
    
    Args:
        x: X coordinate of top-left corner (pixels)
        y: Y coordinate of top-left corner (pixels)
        width: Width of ROI region (pixels)
        height: Height of ROI region (pixels)
    
    Returns:
        dict: Success message and current ROI settings
    """
    try:
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            raise HTTPException(status_code=400, detail="Invalid ROI coordinates. All values must be positive.")
        
        camera_service.set_crop_region(x, y, width, height)
        
        return {
            "message": "ROI set successfully",
            "roi": {
                "x": x,
                "y": y,
                "width": width,
                "height": height
            },
            "note": "Camera feed is now cropped to this region. Detection will only use this area."
        }
    except Exception as e:
        logger.error(f"Error setting ROI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error setting ROI: {str(e)}")


@app.get("/camera/get-roi")
async def get_camera_roi():
    """
    Get current Region of Interest (ROI) settings.
    
    Returns:
        dict: Current ROI settings or None if no ROI is set
    """
    try:
        roi = camera_service.get_crop_region()
        if roi:
            return {
                "roi": roi,
                "message": "ROI is active - camera feed is cropped"
            }
        else:
            return {
                "roi": None,
                "message": "No ROI set - using full frame"
            }
    except Exception as e:
        logger.error(f"Error getting ROI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting ROI: {str(e)}")


@app.post("/camera/clear-roi")
async def clear_camera_roi():
    """
    Clear Region of Interest (ROI) - use full frame.
    
    Returns:
        dict: Success message
    """
    try:
        camera_service.clear_crop_region()
        return {
            "message": "ROI cleared - using full frame for detection"
        }
    except Exception as e:
        logger.error(f"Error clearing ROI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing ROI: {str(e)}")


@app.post("/camera/detect-white-platform")
async def detect_white_platform():
    """
    Automatically detect white platform region in the camera feed.
    
    Uses color thresholding to find the white rectangular platform.
    Sets the ROI to the detected platform region.
    
    Returns:
        dict: Detected platform region and ROI settings
    """
    try:
        import cv2
        import numpy as np
        
        # Get current frame
        loop = asyncio.get_event_loop()
        frame_base64 = await loop.run_in_executor(
            None,
            camera_service.capture_frame,
            0,
            True,
            1280
        )
        
        if not frame_base64:
            raise HTTPException(status_code=500, detail="Failed to capture frame")
        
        # Decode frame
        image_bytes = base64.b64decode(frame_base64)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=500, detail="Failed to decode frame")
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Define white color range in HSV
        # White has low saturation and high value
        lower_white = np.array([0, 0, 200])  # Lower bound for white
        upper_white = np.array([180, 30, 255])  # Upper bound for white
        
        # Create mask for white regions
        mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Apply morphological operations to clean up the mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            raise HTTPException(
                status_code=404,
                detail="White platform not detected. Make sure the platform is visible and well-lit."
            )
        
        # Find the largest contour (likely the platform)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Add some padding (10% on each side)
        padding_x = int(w * 0.1)
        padding_y = int(h * 0.1)
        x = max(0, x - padding_x)
        y = max(0, y - padding_y)
        w = min(frame.shape[1] - x, w + 2 * padding_x)
        h = min(frame.shape[0] - y, h + 2 * padding_y)
        
        # Set ROI
        camera_service.set_crop_region(x, y, w, h)
        
        return {
            "message": "White platform detected and ROI set",
            "detected_region": {
                "x": x,
                "y": y,
                "width": w,
                "height": h
            },
            "roi": camera_service.get_crop_region(),
            "note": "ROI has been set to the detected platform region"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting white platform: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error detecting white platform: {str(e)}"
        )


@app.get("/camera/view", response_class=HTMLResponse)
async def camera_view():
    """
    View camera feed in browser with auto-refresh.
    
    Opens a simple HTML page that shows the camera feed and refreshes every 2 seconds.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BILLESE Camera View</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                background-color: #1a1a1a;
                color: white;
                margin: 0;
                padding: 20px;
            }
            .container {
                max-width: 1280px;
                margin: 0 auto;
            }
            h1 {
                color: #4CAF50;
            }
            .status {
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
                background-color: #333;
            }
            .status.connected {
                background-color: #4CAF50;
            }
            .status.disconnected {
                background-color: #f44336;
            }
            img {
                max-width: 100%;
                height: auto;
                border: 3px solid #4CAF50;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            }
            .info {
                margin-top: 20px;
                padding: 15px;
                background-color: #2a2a2a;
                border-radius: 5px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                margin: 10px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #45a049;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1> BILLESE Camera Feed</h1>
            <div id="status" class="status">Checking connection...</div>
            <img id="cameraImage" src="/camera/frame?max_width=1280" alt="Camera Feed" 
                 style="max-width: 1280px; max-height: 720px;"
                 onerror="handleError()" onload="handleSuccess()" loading="lazy" />
            <div class="info">
                <p><strong>Camera Status:</strong> <span id="statusText">Loading...</span></p>
                <p><strong>Last Update:</strong> <span id="lastUpdate">-</span></p>
                <p><strong>ROI:</strong> <span id="roiStatus">Checking...</span></p>
                <button onclick="refreshFrame()"> Refresh Now</button>
                <button onclick="location.reload()"> Reload Page</button>
                <button onclick="detectPlatform()"> Auto-Detect Platform</button>
                <button onclick="clearROI()"> Clear ROI</button>
            </div>
            <div class="info" style="margin-top: 20px;">
                <h3>Set ROI Manually</h3>
                <p>Enter coordinates to crop the camera feed to the white platform region:</p>
                <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center; justify-content: center;">
                    <label>X: <input type="number" id="roiX" placeholder="x" style="width: 80px; padding: 5px; color: black;"></label>
                    <label>Y: <input type="number" id="roiY" placeholder="y" style="width: 80px; padding: 5px; color: black;"></label>
                    <label>Width: <input type="number" id="roiW" placeholder="width" style="width: 80px; padding: 5px; color: black;"></label>
                    <label>Height: <input type="number" id="roiH" placeholder="height" style="width: 80px; padding: 5px; color: black;"></label>
                    <button onclick="setROI()"> Set ROI</button>
                </div>
                <p style="font-size: 12px; color: #aaa; margin-top: 10px;">
                     Tip: Right-click the image → Inspect → Hover to see pixel coordinates, or use Auto-Detect
                </p>
            </div>
        </div>
        
        <script>
            let updateCount = 0;
            let lastError = null;
            
            function updateTime() {
                const now = new Date();
                document.getElementById('lastUpdate').textContent = now.toLocaleTimeString();
            }
            
            function handleSuccess() {
                document.getElementById('status').className = 'status connected';
                document.getElementById('statusText').textContent = ' Connected';
                updateTime();
                updateCount++;
            }
            
            function handleError() {
                document.getElementById('status').className = 'status disconnected';
                document.getElementById('statusText').textContent = ' Connection Failed';
                lastError = new Date();
            }
            
            // Load ROI status
            async function loadROIStatus() {
                try {
                    const response = await fetch('/camera/get-roi');
                    const data = await response.json();
                    if (data.roi) {
                        document.getElementById('roiStatus').textContent = 
                            `Active: x=${data.roi.x}, y=${data.roi.y}, w=${data.roi.width}, h=${data.roi.height}`;
                        document.getElementById('roiStatus').style.color = '#4CAF50';
                        // Fill in the input fields
                        document.getElementById('roiX').value = data.roi.x;
                        document.getElementById('roiY').value = data.roi.y;
                        document.getElementById('roiW').value = data.roi.width;
                        document.getElementById('roiH').value = data.roi.height;
                    } else {
                        document.getElementById('roiStatus').textContent = 'Not set (using full frame)';
                        document.getElementById('roiStatus').style.color = '#ff9800';
                    }
                } catch (e) {
                    document.getElementById('roiStatus').textContent = 'Error loading ROI';
                    document.getElementById('roiStatus').style.color = '#f44336';
                }
            }
            
            // Set ROI manually
            async function setROI() {
                const xVal = document.getElementById('roiX').value;
                const yVal = document.getElementById('roiY').value;
                const wVal = document.getElementById('roiW').value;
                const hVal = document.getElementById('roiH').value;
                
                if (!xVal || !yVal || !wVal || !hVal) {
                    alert('Please enter all coordinates (X, Y, Width, Height)');
                    return;
                }
                
                const x = parseInt(xVal);
                const y = parseInt(yVal);
                const w = parseInt(wVal);
                const h = parseInt(hVal);
                
                if (isNaN(x) || isNaN(y) || isNaN(w) || isNaN(h) || x < 0 || y < 0 || w <= 0 || h <= 0) {
                    alert('Please enter valid positive numbers for all coordinates');
                    return;
                }
                
                try {
                    const response = await fetch(`/camera/set-roi?x=${x}&y=${y}&width=${w}&height=${h}`, {
                        method: 'POST'
                    });
                    
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to set ROI');
                    }
                    
                    const data = await response.json();
                    alert(' ROI set successfully! Detection will now use only this region.');
                    loadROIStatus();
                } catch (e) {
                    alert(' Error setting ROI: ' + (e.message || e));
                }
            }
            
            // Auto-detect platform
            async function detectPlatform() {
                if (!confirm('This will automatically detect the white platform and set the ROI. Continue?')) {
                    return;
                }
                try {
                    const response = await fetch('/camera/detect-white-platform', { method: 'POST' });
                    const data = await response.json();
                    if (data.detected_region) {
                        document.getElementById('roiX').value = data.detected_region.x;
                        document.getElementById('roiY').value = data.detected_region.y;
                        document.getElementById('roiW').value = data.detected_region.width;
                        document.getElementById('roiH').value = data.detected_region.height;
                        alert(' Platform detected! ROI coordinates filled in. Click "Set ROI" to apply.');
                        loadROIStatus();
                    }
                } catch (e) {
                    const errorText = await e.response?.json() || { detail: e.message };
                    alert(' Error detecting platform: ' + (errorText.detail || e.message));
                }
            }
            
            // Clear ROI
            async function clearROI() {
                if (!confirm('Clear ROI and use full frame for detection?')) {
                    return;
                }
                try {
                    await fetch('/camera/clear-roi', { method: 'POST' });
                    document.getElementById('roiX').value = '';
                    document.getElementById('roiY').value = '';
                    document.getElementById('roiW').value = '';
                    document.getElementById('roiH').value = '';
                    alert(' ROI cleared! Using full frame for detection.');
                    loadROIStatus();
                } catch (e) {
                    alert(' Error clearing ROI: ' + e.message);
                }
            }
            
            // Load ROI status on page load
            loadROIStatus();
            setInterval(loadROIStatus, 5000); // Refresh ROI status every 5 seconds
            
            // Auto-refresh with loading protection to prevent lag
            let isLoading = false;
            function refreshFrame() {
                if (isLoading) {
                    console.log('Skipping refresh - image still loading');
                    return; // Skip if already loading
                }
                isLoading = true;
                const img = document.getElementById('cameraImage');
                const timestamp = new Date().getTime();
                
                // Set up load handlers before changing src
                img.onload = function() {
                    isLoading = false;
                    handleSuccess();
                };
                img.onerror = function() {
                    isLoading = false;
                    handleError();
                };
                
                // Change src to trigger load (use max_width for faster loading)
                img.src = '/camera/frame?max_width=1280&t=' + timestamp;
            }
            
            // Auto-refresh every 3 seconds (reduced from 2s for less lag)
            setInterval(refreshFrame, 3000);
            updateTime();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/camera/detection-view", response_class=HTMLResponse)
async def detection_view():
    """
    Testing window to view camera feed with detection boxes drawn.
    
    This is a separate testing window (not part of main UI) to see how the system detects items.
    Shows bounding boxes around detected objects in real-time.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BILLESE - Detection Testing View</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                background-color: #1a1a1a;
                color: white;
                margin: 0;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            h1 {
                color: #4CAF50;
            }
            .status {
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
                background-color: #333;
            }
            .status.connected {
                background-color: #4CAF50;
            }
            .status.disconnected {
                background-color: #f44336;
            }
            img {
                max-width: 100%;
                height: auto;
                border: 3px solid #4CAF50;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            }
            .info {
                margin-top: 20px;
                padding: 15px;
                background-color: #2a2a2a;
                border-radius: 5px;
                text-align: left;
            }
            .detection-info {
                margin-top: 10px;
                padding: 10px;
                background-color: #333;
                border-radius: 5px;
                font-size: 12px;
            }
            .detection-item {
                margin: 5px 0;
                padding: 5px;
                background-color: #444;
                border-radius: 3px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                margin: 10px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #45a049;
            }
            .legend {
                margin-top: 20px;
                padding: 15px;
                background-color: #2a2a2a;
                border-radius: 5px;
            }
            .legend-item {
                display: inline-block;
                margin: 5px 15px;
                padding: 5px 10px;
                border-radius: 3px;
            }
            .legend-coco {
                background-color: rgba(0, 255, 0, 0.3);
                border: 2px solid #00ff00;
            }
            .legend-trained {
                background-color: rgba(0, 0, 255, 0.3);
                border: 2px solid #0000ff;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1> BILLESE - Detection Testing View</h1>
            <p style="color: #aaa;">This is a testing window to see how the system detects items with bounding boxes.</p>
            
            <div id="status" class="status">Checking connection...</div>
            
            <img id="cameraImage" src="/camera/detection-frame" alt="Detection View" 
                 style="max-width: 1280px; max-height: 720px;"
                 onerror="handleError()" onload="handleSuccess()" loading="lazy" />
            
            <div class="legend">
                <h3>Legend</h3>
                <div class="legend-item legend-coco"> Green Boxes = COCO Model (fruits/vegetables)</div>
                <div class="legend-item legend-trained"> Blue Boxes = Trained Model (office items)</div>
            </div>
            
            <div class="info">
                <h3>Detection Information</h3>
                <p><strong>Status:</strong> <span id="statusText">Loading...</span></p>
                <p><strong>Last Update:</strong> <span id="lastUpdate">-</span></p>
                <p><strong>Total Detections:</strong> <span id="totalDetections">0</span></p>
                <div id="detectionsList" class="detection-info">
                    <p>No detections yet...</p>
                </div>
            </div>
            
            <div style="margin-top: 20px;">
                <button onclick="refreshFrame()"> Refresh Now</button>
                <button onclick="location.reload()"> Reload Page</button>
                <button onclick="toggleAutoRefresh()"> Pause Auto-Refresh</button>
            </div>
        </div>
        
        <script>
            let updateCount = 0;
            let autoRefreshEnabled = true;
            let autoRefreshInterval = null;
            
            function updateTime() {
                const now = new Date();
                document.getElementById('lastUpdate').textContent = now.toLocaleTimeString();
            }
            
            function handleSuccess() {
                document.getElementById('status').className = 'status connected';
                document.getElementById('statusText').textContent = ' Connected';
                updateTime();
                updateCount++;
            }
            
            function handleError() {
                document.getElementById('status').className = 'status disconnected';
                document.getElementById('statusText').textContent = ' Connection Failed';
            }
            
            function updateDetections() {
                // Fetch detection info from the frame endpoint
                fetch('/camera/detection-info')
                    .then(response => response.json())
                    .then(data => {
                        if (data.detections && data.detections.length > 0) {
                            document.getElementById('totalDetections').textContent = data.detections.length;
                            
                            let html = '';
                            data.detections.forEach((det, index) => {
                                const color = det.source === 'coco' ? '#00ff00' : '#0000ff';
                                html += `<div class="detection-item" style="border-left: 4px solid ${color};">
                                    <strong>${det.mapped}</strong> (${det.class}) - ${(det.confidence * 100).toFixed(1)}% 
                                    [${det.source}] - Box: (${det.box.x1}, ${det.box.y1}) to (${det.box.x2}, ${det.box.y2})
                                </div>`;
                            });
                            document.getElementById('detectionsList').innerHTML = html;
                        } else {
                            document.getElementById('totalDetections').textContent = '0';
                            document.getElementById('detectionsList').innerHTML = '<p>No detections found</p>';
                        }
                    })
                    .catch(err => {
                        console.error('Error fetching detection info:', err);
                    });
            }
            
            function refreshFrame() {
                const img = document.getElementById('cameraImage');
                const timestamp = new Date().getTime();
                img.src = '/camera/detection-frame?t=' + timestamp;
                updateDetections();
            }
            
            function toggleAutoRefresh() {
                autoRefreshEnabled = !autoRefreshEnabled;
                const button = event.target;
                if (autoRefreshEnabled) {
                    button.textContent = ' Pause Auto-Refresh';
                    startAutoRefresh();
                } else {
                    button.textContent = ' Resume Auto-Refresh';
                    stopAutoRefresh();
                }
            }
            
            function startAutoRefresh() {
                if (autoRefreshInterval) clearInterval(autoRefreshInterval);
                autoRefreshInterval = setInterval(refreshFrame, 2000); // Refresh every 2 seconds
            }
            
            function stopAutoRefresh() {
                if (autoRefreshInterval) {
                    clearInterval(autoRefreshInterval);
                    autoRefreshInterval = null;
                }
            }
            
            // Initialize
            updateTime();
            startAutoRefresh();
            refreshFrame();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/camera/detection-frame")
async def detection_frame(max_width: int = 1280):
    """
    Get camera frame with detection boxes drawn on it.
    
    This endpoint captures a frame, runs detection, draws bounding boxes,
    and returns the annotated image.
    
    Args:
        max_width: Maximum width in pixels (default: 1280)
    """
    try:
        from app.services.model_service import get_model
        
        # Capture frame
        loop = asyncio.get_event_loop()
        frame_base64 = await loop.run_in_executor(
            None,
            camera_service.capture_frame,
            0,
            True,
            max_width
        )
        
        if not frame_base64:
            raise HTTPException(
                status_code=503,
                detail="Failed to capture frame from camera"
            )
        
        # Run detection with boxes
        model = get_model()
        annotated_image, detections = await loop.run_in_executor(
            None,
            model.detect_with_boxes,
            frame_base64
        )
        
        # Encode annotated image to JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        _, buffer = cv2.imencode('.jpg', annotated_image, encode_param)
        image_bytes = buffer.tobytes()
        
        return Response(
            content=image_bytes,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    except Exception as e:
        logger.error(f"Error in detection_frame: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating detection frame: {str(e)}"
        )


@app.get("/camera/detection-info")
async def detection_info():
    """
    Get detection information (without image) for the current frame.
    
    Returns JSON with detection details.
    """
    try:
        from app.services.model_service import get_model
        
        # Capture frame
        loop = asyncio.get_event_loop()
        frame_base64 = await loop.run_in_executor(
            None,
            camera_service.capture_frame,
            0,
            True,
            1280
        )
        
        if not frame_base64:
            return {"detections": [], "error": "Failed to capture frame"}
        
        # Run detection with boxes (we only need the detections list)
        model = get_model()
        _, detections = await loop.run_in_executor(
            None,
            model.detect_with_boxes,
            frame_base64
        )
        
        return {
            "detections": detections,
            "total": len(detections)
        }
    except Exception as e:
        logger.error(f"Error in detection_info: {str(e)}")
        return {"detections": [], "error": str(e)}


@app.post("/camera/crop/set")
async def set_crop_region(x: int, y: int, width: int, height: int):
    """
    Set crop region (ROI) for camera feed.
    
    This allows you to focus on a specific area of the camera view.
    Useful for focusing on the scale platform or item placement area.
    
    Args:
        x: X coordinate of top-left corner (pixels)
        y: Y coordinate of top-left corner (pixels)
        width: Width of crop region (pixels)
        height: Height of crop region (pixels)
    
    Example:
        POST /camera/crop/set?x=100&y=100&width=640&height=480
    """
    try:
        camera_service.set_crop_region(x, y, width, height)
        return {
            "status": "success",
            "message": f"Crop region set: {x},{y} {width}x{height}",
            "crop_region": {
                "x": x,
                "y": y,
                "width": width,
                "height": height
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting crop: {str(e)}")


@app.get("/camera/crop")
async def get_crop_region():
    """
    Get current crop region settings.
    
    Returns:
        dict: Current crop region or None if no crop is set
    """
    crop = camera_service.get_crop_region()
    return {
        "crop_enabled": crop is not None,
        "crop_region": crop,
        "message": "Crop region active" if crop else "No crop (using full frame)"
    }


@app.post("/camera/crop/clear")
async def clear_crop_region():
    """
    Clear crop region (use full frame).
    
    Returns:
        dict: Confirmation message
    """
    camera_service.clear_crop_region()
    return {
        "status": "success",
        "message": "Crop region cleared - using full frame"
    }


@app.get("/camera/crop/view", response_class=HTMLResponse)
async def crop_viewer():
    """
    Visual crop selector - Interactive page to select crop region.
    
    Opens a page where you can:
    1. See the camera feed
    2. Draw a rectangle to select crop region
    3. Set the crop region
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BILLESE - Crop Region Selector</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #1a1a1a;
                color: white;
                margin: 0;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            h1 {
                color: #4CAF50;
            }
            .controls {
                background-color: #2a2a2a;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }
            .control-group {
                margin: 15px 0;
            }
            label {
                display: inline-block;
                width: 120px;
                color: #4CAF50;
            }
            input[type="number"] {
                width: 100px;
                padding: 8px;
                background-color: #333;
                color: white;
                border: 2px solid #4CAF50;
                border-radius: 5px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 24px;
                margin: 5px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #45a049;
            }
            button.danger {
                background-color: #f44336;
            }
            button.danger:hover {
                background-color: #da190b;
            }
            #cameraCanvas {
                border: 3px solid #4CAF50;
                border-radius: 10px;
                cursor: crosshair;
                display: block;
                margin: 20px auto;
                max-width: 100%;
            }
            .info {
                background-color: #2a2a2a;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }
            .status {
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
                background-color: #333;
            }
            .status.success {
                background-color: #4CAF50;
            }
            .status.info {
                background-color: #2196F3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1> BILLESE - Crop Region Selector</h1>
            
            <div class="status info">
                <strong>Instructions:</strong> Draw a rectangle on the camera feed to select the crop region, 
                or enter coordinates manually below.
            </div>
            
            <div class="controls">
                <h3>Manual Crop Settings</h3>
                <div class="control-group">
                    <label>X (left):</label>
                    <input type="number" id="cropX" value="0" min="0">
                    <label style="width: auto; margin-left: 20px;">Y (top):</label>
                    <input type="number" id="cropY" value="0" min="0">
                </div>
                <div class="control-group">
                    <label>Width:</label>
                    <input type="number" id="cropWidth" value="640" min="1">
                    <label style="width: auto; margin-left: 20px;">Height:</label>
                    <input type="number" id="cropHeight" value="480" min="1">
                </div>
                <div class="control-group">
                    <button onclick="setCrop()"> Set Crop Region</button>
                    <button onclick="clearCrop()" class="danger">❌ Clear Crop</button>
                    <button onclick="loadCurrentCrop()"> Load Current Settings</button>
                    <button onclick="previewCrop()"> Preview Crop</button>
                </div>
            </div>
            
            <canvas id="cameraCanvas"></canvas>
            
            <div id="status" class="status"></div>
            
            <div class="info">
                <h3>Current Crop Settings</h3>
                <div id="currentCrop">Loading...</div>
            </div>
        </div>
        
        <script>
            const canvas = document.getElementById('cameraCanvas');
            const ctx = canvas.getContext('2d');
            let isDrawing = false;
            let startX = 0;
            let startY = 0;
            let currentCrop = null;
            
            // Load camera feed
            function loadFrame() {
                const img = new Image();
                img.crossOrigin = 'anonymous';
                img.onload = function() {
                    canvas.width = img.width;
                    canvas.height = img.height;
                    ctx.drawImage(img, 0, 0);
                    
                    // Draw existing crop if any
                    if (currentCrop) {
                        drawCropRect(currentCrop.x, currentCrop.y, currentCrop.width, currentCrop.height);
                    }
                };
                img.src = '/camera/frame?t=' + new Date().getTime();
            }
            
            // Draw crop rectangle
            function drawCropRect(x, y, width, height) {
                ctx.strokeStyle = '#4CAF50';
                ctx.lineWidth = 3;
                ctx.setLineDash([5, 5]);
                ctx.strokeRect(x, y, width, height);
                ctx.setLineDash([]);
                
                // Draw corner markers
                const markerSize = 10;
                ctx.fillStyle = '#4CAF50';
                ctx.fillRect(x - markerSize/2, y - markerSize/2, markerSize, markerSize);
                ctx.fillRect(x + width - markerSize/2, y - markerSize/2, markerSize, markerSize);
                ctx.fillRect(x - markerSize/2, y + height - markerSize/2, markerSize, markerSize);
                ctx.fillRect(x + width - markerSize/2, y + height - markerSize/2, markerSize, markerSize);
            }
            
            // Mouse events for drawing crop
            canvas.addEventListener('mousedown', (e) => {
                isDrawing = true;
                const rect = canvas.getBoundingClientRect();
                startX = e.clientX - rect.left;
                startY = e.clientY - rect.top;
            });
            
            canvas.addEventListener('mousemove', (e) => {
                if (!isDrawing) return;
                
                const rect = canvas.getBoundingClientRect();
                const currentX = e.clientX - rect.left;
                const currentY = e.clientY - rect.top;
                
                // Redraw frame
                loadFrame();
                
                // Draw selection rectangle
                const width = currentX - startX;
                const height = currentY - startY;
                drawCropRect(startX, startY, width, height);
                
                // Update input fields
                document.getElementById('cropX').value = Math.min(startX, currentX);
                document.getElementById('cropY').value = Math.min(startY, currentY);
                document.getElementById('cropWidth').value = Math.abs(width);
                document.getElementById('cropHeight').value = Math.abs(height);
            });
            
            canvas.addEventListener('mouseup', () => {
                isDrawing = false;
            });
            
            // Set crop region
            async function setCrop() {
                const x = parseInt(document.getElementById('cropX').value);
                const y = parseInt(document.getElementById('cropY').value);
                const width = parseInt(document.getElementById('cropWidth').value);
                const height = parseInt(document.getElementById('cropHeight').value);
                
                try {
                    const response = await fetch(`/camera/crop/set?x=${x}&y=${y}&width=${width}&height=${height}`, {
                        method: 'POST'
                    });
                    const result = await response.json();
                    
                    document.getElementById('status').className = 'status success';
                    document.getElementById('status').textContent = ' ' + result.message;
                    
                    loadCurrentCrop();
                    loadFrame();
                } catch (error) {
                    document.getElementById('status').className = 'status';
                    document.getElementById('status').textContent = ' Error: ' + error.message;
                }
            }
            
            // Clear crop
            async function clearCrop() {
                try {
                    const response = await fetch('/camera/crop/clear', { method: 'POST' });
                    const result = await response.json();
                    
                    document.getElementById('status').className = 'status success';
                    document.getElementById('status').textContent = ' ' + result.message;
                    
                    currentCrop = null;
                    loadCurrentCrop();
                    loadFrame();
                } catch (error) {
                    document.getElementById('status').className = 'status';
                    document.getElementById('status').textContent = ' Error: ' + error.message;
                }
            }
            
            // Load current crop settings
            async function loadCurrentCrop() {
                try {
                    const response = await fetch('/camera/crop');
                    const result = await response.json();
                    
                    if (result.crop_enabled) {
                        currentCrop = result.crop_region;
                        document.getElementById('cropX').value = currentCrop.x;
                        document.getElementById('cropY').value = currentCrop.y;
                        document.getElementById('cropWidth').value = currentCrop.width;
                        document.getElementById('cropHeight').value = currentCrop.height;
                        document.getElementById('currentCrop').innerHTML = 
                            ` Active: x=${currentCrop.x}, y=${currentCrop.y}, width=${currentCrop.width}, height=${currentCrop.height}`;
                    } else {
                        currentCrop = null;
                        document.getElementById('currentCrop').innerHTML = ' No crop set (using full frame)';
                    }
                } catch (error) {
                    document.getElementById('currentCrop').innerHTML = 'Error loading crop settings';
                }
            }
            
            // Preview crop
            async function previewCrop() {
                const x = parseInt(document.getElementById('cropX').value);
                const y = parseInt(document.getElementById('cropY').value);
                const width = parseInt(document.getElementById('cropWidth').value);
                const height = parseInt(document.getElementById('cropHeight').value);
                
                // Draw preview
                loadFrame();
                setTimeout(() => {
                    drawCropRect(x, y, width, height);
                }, 100);
            }
            
            // Initialize
            loadFrame();
            loadCurrentCrop();
            
            // Auto-refresh frame every 2 seconds
            setInterval(loadFrame, 2000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/detect/debug")
async def debug_detection():
    """
    Debug endpoint to see what the model detects in the current camera frame.
    
    This helps troubleshoot detection issues by showing:
    - All detected objects
    - Their confidence scores
    - Whether they map to known items
    """
    try:
        from app.services.model_service import get_model
        
        # Capture current frame (async)
        loop = asyncio.get_event_loop()
        frame_base64 = await loop.run_in_executor(
            None,  # Use default executor
            camera_service.capture_frame,
            0,  # max_retries (ignored)
            True,  # use_cache (ignored)
            1280  # max_width
        )
        if not frame_base64:
            return {"error": "Failed to capture frame from camera"}
        
        # Get all detections (async)
        model = get_model()
        detections = await loop.run_in_executor(
            None,
            model.detect_all,
            frame_base64
        )
        
        return {
            "status": "success",
            "detections": detections,
            "total_detections": len(detections),
            "known_items": [d for d in detections if d["is_known"]],
            "unknown_items": [d for d in detections if not d["is_known"]],
            "message": "Check 'detections' array to see what model found"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Make sure ultralytics is installed: pip install ultralytics"
        }


@app.get("/gpu/status")
async def gpu_status():
    """
    Check GPU status and verify YOLO is using GPU for inference.
    
    Returns:
        dict: GPU information including CUDA availability, device name, memory usage
    """
    try:
        import torch
        from app.services.model_service import get_model
        
        gpu_available = torch.cuda.is_available()
        status = {
            "cuda_available": gpu_available,
            "device_configured": None,
            "gpu_name": None,
            "cuda_version": None,
            "gpu_memory_allocated_mb": None,
            "gpu_memory_reserved_mb": None,
            "model_device": None,
            "half_precision_enabled": None,
            "status": "unknown"
        }
        
        if gpu_available:
            status["gpu_name"] = torch.cuda.get_device_name(0)
            status["cuda_version"] = torch.version.cuda
            status["gpu_memory_allocated_mb"] = round(torch.cuda.memory_allocated(0) / 1024**2, 2)
            status["gpu_memory_reserved_mb"] = round(torch.cuda.memory_reserved(0) / 1024**2, 2)
            
            # Check model configuration
            try:
                model = get_model()
                status["device_configured"] = str(model.device)
                status["half_precision_enabled"] = model.use_half
                
                # Check if model is actually using GPU (by checking memory)
                if status["gpu_memory_allocated_mb"] > 0:
                    status["model_device"] = "GPU (active)"
                    status["status"] = "✅ GPU is active and being used for inference"
                else:
                    status["model_device"] = "CPU (no GPU memory allocated)"
                    status["status"] = "⚠️  GPU available but not being used"
            except Exception as e:
                status["status"] = f"⚠️  Error checking model: {str(e)}"
        else:
            status["status"] = "❌ No GPU detected - using CPU"
        
        return status
    except Exception as e:
        return {
            "status": f"❌ Error checking GPU status: {str(e)}",
            "error": str(e)
        }


@app.get("/detect/capabilities")
async def detection_capabilities():
    """
    Get list of all objects the system can detect.
    
    Returns:
    - COCO classes (80 classes from pre-trained model)
    - Mapped items (items we use in billing)
    - Items requiring custom training
    """
    try:
        from app.services.model_service import get_model
        from app.services.item_detection import get_item_info
        
        model = get_model()
        
        # Get all COCO class names
        coco_classes = []
        if model.model and hasattr(model.model, 'names'):
            coco_classes = list(model.model.names.values())
        
        # Known items in our system
        known_items = [
            # Grocery items
            "tomato", "potato", "onion", "carrot", "cabbage",
            "apple", "banana", "orange", "bottle", "cup", "bowl",
            # Office/Stationery items
            "phone", "mouse", "keyboard", "laptop", "tablet",
            "pen", "pencil", "book", "notebook", "monitor",
            "eraser", "ruler"
        ]
        
        # Items from COCO that we can use
        coco_mapped = ["cup", "bottle", "bowl", "apple", "banana", "orange"]
        
        # Items needing custom training
        custom_items = ["tomato", "potato", "onion", "carrot", "cabbage"]
        
        return {
            "model_type": "YOLOv8 (Pre-trained on COCO dataset)",
            "total_coco_classes": len(coco_classes),
            "coco_classes": coco_classes,
            "system_capabilities": {
                "currently_detectable": {
                    "items": coco_mapped,
                    "count": len(coco_mapped),
                    "note": "These are from COCO dataset and work immediately"
                },
                "requires_training": {
                    "items": custom_items,
                    "count": len(custom_items),
                    "note": "Need custom model training (see TRAINING_GUIDE.md)"
                },
                "all_known_items": known_items
            },
            "detection_threshold": 0.3,
            "model_confidence_threshold": 0.25,
            "documentation": "See DETECTION_CAPABILITIES.md for full details"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Model not available. Install: pip install ultralytics"
        }


@app.post("/dataset/capture")
async def capture_for_dataset(class_name: str, split: str = "train"):
    """
    Capture an image from the camera and save it to the dataset.
    
    This endpoint helps you collect images for training:
    1. Captures current frame from RTSP camera
    2. Saves it to datasets/train/images/{class_name}/ or datasets/val/images/{class_name}/
    3. Returns information about saved image
    
    Args:
        class_name: Name of the item class (e.g., "tomato", "potato", "cup")
        split: "train" or "val" (default: "train")
              - Use "train" for training images
              - Use "val" for validation images (20% of total)
    
    Returns:
        dict: Information about saved image
    
    Example:
        POST /dataset/capture?class_name=tomato&split=train
    """
    try:
        from app.services.dataset_collector import dataset_collector
        
        # Validate class name
        if not class_name or not class_name.strip():
            raise HTTPException(status_code=400, detail="class_name is required")
        
        class_name = class_name.strip().lower()
        
        # Validate split
        if split not in ["train", "val"]:
            split = "train"
        
        # Capture image from camera (async)
        loop = asyncio.get_event_loop()
        frame_base64 = await loop.run_in_executor(
            None,  # Use default executor
            camera_service.capture_frame,
            0,  # max_retries (ignored)
            True,  # use_cache (ignored)
            1280  # max_width
        )
        if not frame_base64:
            raise HTTPException(
                status_code=500,
                detail="Failed to capture image from camera. Check camera connection."
            )
        
        # Save to dataset
        result = dataset_collector.save_image(frame_base64, class_name, split)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to save image"))
        
        return {
            **result,
            "message": f"✅ Image saved! Total {class_name} images: {result['total_images_for_class']}",
            "next_steps": [
                f"1. Capture more images for '{class_name}' (aim for 50-100 images)",
                "2. Label images using LabelImg (see datasets/README.md)",
                "3. Train model: python train_model.py"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error capturing image: {str(e)}"
        )


@app.get("/dataset/stats")
async def dataset_statistics():
    """
    Get statistics about the collected dataset.
    
    Shows:
    - Number of images per class
    - Total images
    - Classes in dataset
    - Train/Val split
    """
    try:
        from app.services.dataset_collector import dataset_collector
        
        stats = dataset_collector.get_dataset_stats()
        classes = dataset_collector.list_classes()
        
        return {
            "dataset_path": str(dataset_collector.dataset_root.absolute()),
            "total_images": stats["total_images"],
            "classes": classes,
            "train_images": stats["train"],
            "val_images": stats["val"],
            "recommendations": {
                "minimum_per_class": 50,
                "recommended_per_class": 100,
                "validation_split": "20% of total images should be in 'val' folder"
            },
            "ready_for_training": all(
                (stats["train"].get(cls, 0) + stats["val"].get(cls, 0)) >= 50
                for cls in classes
            ) if classes else False
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.post("/teach-item", response_model=dict)
async def teach_item(
    request: dict = Body(...),
    session: dict = Depends(require_auth)
):
    """
    Save an image with an item name for later model training.
    Place the item on the platform, then call with item_name.
    If image (base64) is not provided, the current camera frame is captured and saved.
    Images are stored under datasets/taught/<item_name>/.
    Collect many images (e.g. 20–50+ per item) then run YOLO training to teach the model.
    """
    import re
    image_b64 = request.get("image")
    item_name = (request.get("item_name") or "").strip()
    if not item_name:
        raise HTTPException(status_code=400, detail="item_name is required")
    if image_b64:
        try:
            image_bytes = base64.b64decode(image_b64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image: {e}")
    else:
        loop = asyncio.get_event_loop()
        image_b64 = await loop.run_in_executor(
            None,
            camera_service.capture_frame,
            0,
            True,
            640,
        )
        if not image_b64:
            raise HTTPException(status_code=503, detail="Could not capture camera frame. Is the camera on?")
        image_bytes = base64.b64decode(image_b64)
    safe_name = re.sub(r"[^\w\-]", "_", item_name).strip("_") or "item"
    taught_dir = Path("datasets") / "taught" / safe_name
    taught_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = taught_dir / f"IMG_{ts}.jpg"
    path.write_bytes(image_bytes)
    logger.info(f"Taught image saved: {path} for item '{item_name}'")
    return {
        "message": "Image saved for training",
        "item_name": item_name,
        "path": str(path),
        "hint": "Collect 20–50+ images per item, then run YOLO training to add this class to the model.",
    }


@app.post("/scan-item", response_model=ScanItemResponse)
async def scan_item(
    request: ScanItemRequest,
    session_id: str = "default",
    add_to_bill: bool = True,
    session: Optional[dict] = Depends(get_current_shopkeeper)
):
    """
    Scan an item and optionally add it to the bill.
    
    This endpoint:
    1. Receives weight from ESP32 (and optionally image)
    2. If image not provided, captures from RTSP camera automatically
    3. Detects the item from the image
    4. Calculates the price based on weight and price-per-kg (uses shopkeeper's prices if authenticated)
    5. Optionally adds the item to the current bill session (if add_to_bill=True)
    6. Returns the detected item info and updated bill
    
    Args:
        request: ScanItemRequest containing weight_grams and optional image
        session_id: Optional session ID. Defaults to "default" if not provided.
        add_to_bill: If True, adds item to bill. If False, only detects and returns item info.
        session: Optional shopkeeper session (from authentication)
    
    Returns:
        ScanItemResponse: Contains detected item info, current bill, and total
    """
    try:
        # Step 1: Get image - either from request or capture from RTSP
        if request.image:
            # Use provided image (if ESP32 sends it)
            image_base64 = request.image
            print("📸 Using image from request")
        else:
            # Fetch latest cached frame (ZERO-LAG, never touches RTSP)
            print("📸 Fetching latest cached frame...")
            loop = asyncio.get_event_loop()
            # capture_frame reads from memory only (background thread handles RTSP)
            image_base64 = await loop.run_in_executor(
                None,  # Use default executor
                camera_service.capture_frame,
                0,  # max_retries (ignored)
                True,  # use_cache (always uses latest cached frame)
                640  # max_width - smaller for faster YOLO processing
            )
            if not image_base64:
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to get frame from camera. Camera may be offline or still connecting."
                )
            print("✅ Latest cached frame fetched (zero-lag)")
        
        # Step 2: Validate weight
        if request.weight_grams <= 0:
            raise HTTPException(status_code=400, detail="Weight must be greater than 0")
        
        # Step 2.5: Check if detection should proceed (weight threshold check)
        if not detection_state.should_detect(request.weight_grams):
            # Weight too low - process as invalid detection
            # Time-based removal will handle state transition ITEM_PRESENT -> EMPTY
            # if enough time has passed since last_seen_time
            state_changed, _ = detection_state.process_detection("unknown", request.weight_grams, 0.0)
            if state_changed:
                logger.info("State changed due to time-based removal (low weight triggered check)")
            session = bill_manager.get_session(session_id)
            return ScanItemResponse(
                detected_item=None,  # No detection
                current_bill=session.items,
                bill_total=round(session.get_total(), 2)
            )
        
        # Step 3: Run YOLO detection ONCE (only when scan is triggered)
        print("🔍 Running YOLO detection (single inference, not continuous)...")
        print(f"   Weight: {request.weight_grams}g")
        print(f"   Current State: {detection_state.get_state().value.upper()}")
        if detection_state.get_current_item():
            item_name, item_weight = detection_state.get_current_item()
            print(f"   Current Item: {item_name} ({item_weight}g)")
        
        loop = asyncio.get_event_loop()
        detection_result = await loop.run_in_executor(
            None,  # Use default executor
            detect_item_from_image,
            image_base64
        )
        
        # Unpack detection result (item_name, confidence)
        if isinstance(detection_result, tuple):
            detected_item_name, detection_confidence = detection_result
        else:
            # Backward compatibility if function returns just string
            detected_item_name = detection_result
            detection_confidence = 0.0
        
        print(f"📊 YOLO Result: item='{detected_item_name}', confidence={detection_confidence:.3f}")
        
        # Step 4: If unknown but user provided item_name, use it (teach / override for this scan)
        user_item_name = (getattr(request, "item_name", None) or "").strip()
        if detected_item_name.lower() == "unknown" and user_item_name:
            detected_item_name = user_item_name.lower()
            detection_confidence = 0.9  # Treat as confident so billing continues
            logger.info(f"✅ Using user-provided item name: '{detected_item_name}' (model did not recognize)")
            print(f"✅ Using user-provided item name: '{detected_item_name}'")
        elif detected_item_name.lower() == "unknown":
            logger.info(f"🚫 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Unknown item detected - not adding to bill")
            print(f"🚫 Unknown item detected - not adding to bill")
            bill_session = bill_manager.get_session(session_id)
            detection_state.process_detection(detected_item_name, request.weight_grams, detection_confidence)
            return ScanItemResponse(
                detected_item=None,
                current_bill=bill_session.items,
                bill_total=round(bill_session.get_total(), 2)
            )
        
        # Step 5: Reject low confidence detections - only add if confidence >= 50%
        if detection_confidence < 0.5:
            logger.info(f"🚫 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Low confidence detection ({detection_confidence*100:.1f}% < 50%) - not adding to bill")
            print(f"🚫 Low confidence detection ({detection_confidence*100:.1f}% < 50%) - not adding to bill")
            bill_session = bill_manager.get_session(session_id)
            # Still process through state machine to update state, but don't bill
            detection_state.process_detection(detected_item_name, request.weight_grams, detection_confidence)
            return ScanItemResponse(
                detected_item=None,  # No new detection to add to bill
                current_bill=bill_session.items,
                bill_total=round(bill_session.get_total(), 2)
            )
        
        # Step 6: Get current bill to check for duplicates
        bill_session = bill_manager.get_session(session_id)
        
        # Step 7: Check if item already exists in bill (duplicate prevention by class name)
        # This check happens BEFORE state machine to allow new items even if state is ITEM_PRESENT
        item_already_in_bill = any(
            item.item_name.lower() == detected_item_name.lower() 
            for item in bill_session.items
        )
        
        if item_already_in_bill:
            # Item already in bill - prevent duplicate
            logger.info(f"🚫 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Item '{detected_item_name}' already in bill - duplicate prevented")
            print(f"🚫 Item '{detected_item_name}' already exists in bill - not adding duplicate")
            # Still process through state machine to update state, but don't bill
            detection_state.process_detection(detected_item_name, request.weight_grams, detection_confidence)
            return ScanItemResponse(
                detected_item=None,  # No new detection to add to bill
                current_bill=bill_session.items,
                bill_total=round(bill_session.get_total(), 2)
            )
        
        # Step 8: Process detection through state machine
        # Returns (state_changed, should_add_to_bill)
        # should_add_to_bill is True when transitioning from EMPTY to ITEM_PRESENT or item changed
        state_changed, should_add_to_bill = detection_state.process_detection(
            detected_item_name, 
            request.weight_grams, 
            detection_confidence
        )
        
        # Step 9: Get item information and calculate price
        shopkeeper_id = session["shopkeeper_id"] if session else None
        item_info = get_item_info(detected_item_name, request.weight_grams, shopkeeper_id=shopkeeper_id)
        
        # Step 10: If state machine says no billing, but item is not in bill, allow it anyway
        # This handles the case where a new item is placed but state is still ITEM_PRESENT
        if not should_add_to_bill:
            # Check if this is a different item than what's currently tracked
            current_item = detection_state.get_current_item()
            if current_item:
                current_name, _ = current_item
                if detected_item_name.lower() != current_name.lower():
                    # Different item detected - allow billing even if state machine says no
                    logger.info(f"✅ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Different item detected ({current_name} -> {detected_item_name}) - allowing billing")
                    print(f"✅ Different item detected: {current_name} -> {detected_item_name} - Allowing billing")
                    should_add_to_bill = True
                else:
                    # Same item - no billing needed
                    logger.debug(f"Same item '{detected_item_name}' still present - no billing")
                    return ScanItemResponse(
                        detected_item=None,  # No new detection to add to bill
                        current_bill=bill_session.items,
                        bill_total=round(bill_session.get_total(), 2)
                    )
            else:
                # No current item but state machine says no billing - return early
                return ScanItemResponse(
                    detected_item=None,  # No new detection to add to bill
                    current_bill=bill_session.items,
                    bill_total=round(bill_session.get_total(), 2)
                )
        
        # Step 11: Final safety check - never add "unknown" or low confidence items
        if detected_item_name.lower() == "unknown" or detection_confidence < 0.5:
            logger.warning(f"🚫 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Safety check: Blocked '{detected_item_name}' (confidence: {detection_confidence*100:.1f}%) from being added to bill")
            print(f"🚫 Safety check: Blocked '{detected_item_name}' from being added to bill")
            return ScanItemResponse(
                detected_item=None,
                current_bill=bill_session.items,
                bill_total=round(bill_session.get_total(), 2)
            )
        
        # Step 12: Add item to bill (only if not already present and passes all checks)
        if add_to_bill:
            # Determine if item is per-piece or weight-based
            from app.services.item_detection import PER_PIECE_ITEMS
            is_per_piece = item_info.name.lower() in PER_PIECE_ITEMS
            pricing_type = "piece" if is_per_piece else "weight"
            
            # For per-piece items, total_price is price per piece * quantity (quantity starts at 1)
            # For weight-based items, total_price is already calculated
            if is_per_piece:
                # price_per_kg actually represents price per piece for these items
                total_price = item_info.price_per_kg * 1  # Start with quantity 1
            else:
                total_price = item_info.total_price
            
            # GST: get rate for this item's category (when shopkeeper is known)
            shopkeeper_id = session["shopkeeper_id"] if session else 0
            gst_rate = float(db.get_gst_rate_for_item(shopkeeper_id, item_info.name)) if shopkeeper_id else 0.0
            gst_amount = round(total_price * gst_rate / 100.0, 2) if gst_rate else 0.0

            # Create a BillItem to add to the session
            bill_item = BillItem(
                item_name=item_info.name,
                weight_grams=item_info.weight_grams,
                price_per_kg=item_info.price_per_kg,
                total_price=round(total_price, 2),
                quantity=1,
                pricing_type=pricing_type,
                gst_rate=gst_rate,
                gst_amount=gst_amount,
            )
            
            # Add item to the bill session
            bill_manager.add_item_to_session(session_id, bill_item)
            
            # Log successful detection with details
            confidence_pct = detection_confidence * 100
            print(f"\n{'='*60}")
            print(f"✅ ITEM DETECTED AND ADDED TO BILL")
            print(f"{'='*60}")
            print(f"Item Name: {detected_item_name.upper()}")
            print(f"Platform State: {detection_state.get_state().value.upper()}")
            print(f"Confidence: {confidence_pct:.1f}%")
            print(f"Weight: {request.weight_grams:.1f}g")
            print(f"Price: ₹{item_info.total_price:.2f}")
            print(f"{'='*60}\n")
            logger.info(f"✅ Item '{detected_item_name}' added to bill (confidence: {detection_confidence:.2f}, weight: {request.weight_grams}g)")
        
        # Step 8: Get the current bill session
        bill_session = bill_manager.get_session(session_id)
        
        # Step 9: Prepare response
        response = ScanItemResponse(
            detected_item=item_info,
            current_bill=bill_session.items,
            bill_total=round(bill_session.get_total(), 2)
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (like validation errors)
        raise
    except Exception as e:
        # Catch any unexpected errors and return a 500 error
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/bill/{session_id}")
async def get_bill(session_id: str):
    """
    Get the current bill for a session.
    
    This endpoint allows you to retrieve the current bill
    without scanning a new item.
    
    Args:
        session_id: The session ID to get the bill for
    
    Returns:
        dict: Current bill information (subtotal, gst_total, total, items)
    """
    session = bill_manager.get_session(session_id)
    return {
        "session_id": session.session_id,
        "items": session.items,
        "subtotal": round(session.get_subtotal(), 2),
        "gst_total": round(session.get_gst_total(), 2),
        "total": round(session.get_total(), 2),
    }


@app.delete("/bill/{session_id}")
async def clear_bill(session_id: str):
    """
    Clear all items from a bill session.
    
    This endpoint resets the bill for a session,
    removing all items but keeping the session active.
    
    Args:
        session_id: The session ID to clear
    """
    bill_manager.clear_session(session_id)
    return {"message": f"Bill session {session_id} cleared successfully"}


@app.delete("/bill/{session_id}/item/{item_index}")
async def remove_bill_item(session_id: str, item_index: int):
    """
    Remove an item from the bill by index.
    
    Args:
        session_id: The session ID
        item_index: Index of item to remove (0-based)
    
    Returns:
        dict: Updated bill information
    """
    success = bill_manager.remove_item_from_session(session_id, item_index)
    if not success:
        raise HTTPException(status_code=404, detail="Item index not found")
    
    session = bill_manager.get_session(session_id)
    return {
        "message": "Item removed successfully",
        "session_id": session.session_id,
        "items": session.items,
        "subtotal": round(session.get_subtotal(), 2),
        "gst_total": round(session.get_gst_total(), 2),
        "total": round(session.get_total(), 2),
    }


@app.post("/detection/reset")
async def reset_detection_state():
    """
    Reset detection state machine to EMPTY state.
    
    Call this when starting a new scanning session to clear previous detections.
    """
    detection_state.reset()
    return {
        "message": "Detection state machine reset to EMPTY",
        "state": detection_state.get_state().value
    }


@app.get("/detection/state")
async def get_detection_state():
    """
    Get current detection state machine status.
    
    Returns:
        dict: Current state, current item (if any), time-based tracking info
    """
    import time
    current_item = detection_state.get_current_item()
    current_time = time.time()
    
    state_info = {
        "state": detection_state.get_state().value,
        "item_removal_delay": detection_state.ITEM_REMOVAL_DELAY,
        "last_seen_time": detection_state.last_seen_time,
        "time_since_last_seen": current_time - detection_state.last_seen_time if detection_state.last_seen_time > 0 else None,
        "current_item": None
    }
    
    if current_item:
        item_name, item_weight = current_item
        state_info["current_item"] = {
            "name": item_name,
            "weight_grams": item_weight
        }
    
    return state_info


@app.post("/bill/{session_id}/add-item")
async def add_item_directly(
    session_id: str,
    item_name: str = Query(...),
    weight_grams: float = Query(...),
    price_per_kg: float = Query(None),
    pricing_type: str = Query(None),
    session: Optional[dict] = Depends(get_current_shopkeeper),
):
    """
    Directly add an item to the bill without detection.
    
    This endpoint is used when an item has already been detected
    and we just want to add it to the bill.
    
    Args:
        session_id: The session ID
        item_name: Name of the item
        weight_grams: Weight in grams
        price_per_kg: Optional price per kg (will be calculated if not provided)
        pricing_type: Optional pricing type ('kg', 'units', 'ltr', 'weight', 'piece')
    
    Returns:
        dict: Updated bill information
    """
    if weight_grams <= 0:
        raise HTTPException(status_code=400, detail="Weight must be greater than 0")
    
    # Determine pricing type - use provided pricing_type or fall back to detection
    if pricing_type:
        # Map database pricing types to bill pricing types
        if pricing_type in ['units']:
            pricing_type_bill = "piece"
        else:
            pricing_type_bill = "weight"
    else:
        # Fall back to detection-based logic
        from app.services.item_detection import PER_PIECE_ITEMS
        is_per_piece = item_name.lower() in PER_PIECE_ITEMS
        pricing_type_bill = "piece" if is_per_piece else "weight"
    
    # Get item info (calculates price if not provided)
    if price_per_kg is None:
        item_info = get_item_info(item_name, weight_grams)
        price_per_kg = item_info.price_per_kg
        # For per-piece items, total_price is price per piece (quantity starts at 1)
        if pricing_type_bill == "piece":
            total_price = price_per_kg * 1  # Start with quantity 1
        else:
            total_price = item_info.total_price
    else:
        # Calculate total price based on pricing type
        if pricing_type_bill == "piece":
            total_price = price_per_kg * 1  # Per piece, quantity starts at 1
        else:
            weight_kg = weight_grams / 1000.0
            total_price = price_per_kg * weight_kg
    
    # GST: get rate for this item's category when shopkeeper is known
    shopkeeper_id = session["shopkeeper_id"] if session else 0
    gst_rate = float(db.get_gst_rate_for_item(shopkeeper_id, item_name)) if shopkeeper_id else 0.0
    gst_amount = round(total_price * gst_rate / 100.0, 2) if gst_rate else 0.0

    # Create bill item
    bill_item = BillItem(
        item_name=item_name,
        weight_grams=weight_grams,
        price_per_kg=price_per_kg,
        total_price=round(total_price, 2),
        quantity=1,
        pricing_type=pricing_type_bill,
        gst_rate=gst_rate,
        gst_amount=gst_amount,
    )
    
    # Add to session
    bill_manager.add_item_to_session(session_id, bill_item)
    
    # Note: This endpoint bypasses the state machine (manual entry)
    # The state machine will handle automatic detection separately
    
    # Get updated session
    sess = bill_manager.get_session(session_id)
    return {
        "message": "Item added successfully",
        "session_id": sess.session_id,
        "items": sess.items,
        "subtotal": round(sess.get_subtotal(), 2),
        "gst_total": round(sess.get_gst_total(), 2),
        "total": round(sess.get_total(), 2),
    }


@app.put("/bill/{session_id}/item/{item_index}")
async def update_bill_item(session_id: str, item_index: int, weight_grams: float = None, quantity: int = None):
    """
    Update an item's weight or quantity in the bill and recalculate price.
    
    Args:
        session_id: The session ID
        item_index: Index of item to update (0-based)
        weight_grams: New weight in grams (for weight-based items)
        quantity: New quantity (for per-piece items)
    
    Returns:
        dict: Updated bill information
    """
    session = bill_manager.get_session(session_id)
    if item_index < 0 or item_index >= len(session.items):
        raise HTTPException(status_code=404, detail="Item index not found")
    
    item = session.items[item_index]
    
    if quantity is not None:
        # Update quantity for per-piece items
        if quantity < 1:
            raise HTTPException(status_code=400, detail="Quantity must be at least 1")
        item.quantity = quantity
        # Recalculate total price: price_per_kg is actually price per piece for per-piece items
        item.total_price = round(item.price_per_kg * quantity, 2)
    elif weight_grams is not None:
        # Update weight for weight-based items
        if weight_grams <= 0:
            raise HTTPException(status_code=400, detail="Weight must be greater than 0")
        item.weight_grams = weight_grams
        # Recalculate total price based on weight
        weight_kg = weight_grams / 1000.0
        item.total_price = round(item.price_per_kg * weight_kg, 2)
    else:
        raise HTTPException(status_code=400, detail="Either weight_grams or quantity must be provided")

    # Recalculate GST amount when price changes
    gst_rate = getattr(item, "gst_rate", 0) or 0
    item.gst_amount = round(item.total_price * gst_rate / 100.0, 2)
    
    return {
        "message": "Item updated successfully",
        "session_id": session.session_id,
        "items": session.items,
        "subtotal": round(session.get_subtotal(), 2),
        "gst_total": round(session.get_gst_total(), 2),
        "total": round(session.get_total(), 2),
    }


if __name__ == "__main__":
    import uvicorn
    # Run the server
    # host="0.0.0.0" allows connections from any IP (useful for ESP32)
    # port=8000 is the default FastAPI port
    uvicorn.run(app, host="0.0.0.0", port=8000)

