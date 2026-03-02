"""
Database Service for BILLESE

Handles all database operations for shopkeepers, shops, prices, and bills.
Uses SQLite for simplicity (can be upgraded to PostgreSQL later).
"""

import sqlite3
import json
from typing import Optional, List, Dict
from datetime import datetime
from pathlib import Path
import logging
import hashlib
import secrets
import string

logger = logging.getLogger(__name__)

DB_PATH = Path("billease.db")


class Database:
    """
    Database service for managing shopkeepers, shops, prices, and bills.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file (default: billease.db)
        """
        self.db_path = db_path or str(DB_PATH)
        self._init_database()
    
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        return conn
    
    def _init_database(self):
        """Initialize database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Shopkeepers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopkeepers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                shop_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                billease_id TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Prices table (per shopkeeper)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shopkeeper_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                price_per_kg REAL NOT NULL,
                cost_price REAL,
                selling_price REAL,
                pricing_type TEXT DEFAULT 'kg',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(id),
                UNIQUE(shopkeeper_id, item_name)
            )
        """)
        
        # Migrate prices table to add new columns if they don't exist
        self._migrate_prices_table()
        
        # Bills table (completed bills)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shopkeeper_id INTEGER NOT NULL,
                bill_number TEXT NOT NULL,
                total_amount REAL NOT NULL,
                items_json TEXT NOT NULL,
                is_unpaid BOOLEAN DEFAULT 0,
                customer_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)
        
        # Customers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shopkeeper_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(id),
                UNIQUE(shopkeeper_id, phone)
            )
        """)
        
        # Stock/inventory table (per shopkeeper: item name, quantity, unit kg/unit)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shopkeeper_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 0,
                unit TEXT NOT NULL DEFAULT 'kg',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(id),
                UNIQUE(shopkeeper_id, item_name)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_shopkeeper ON stock(shopkeeper_id)")

        # GST settings per shopkeeper (category-level GST rates)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gst_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shopkeeper_id INTEGER NOT NULL,
                category_key TEXT NOT NULL,
                display_name TEXT NOT NULL,
                rate REAL NOT NULL,
                FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(id),
                UNIQUE(shopkeeper_id, category_key)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gst_shopkeeper ON gst_settings(shopkeeper_id)")

        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shopkeeper_id ON prices(shopkeeper_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_shopkeeper ON bills(shopkeeper_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_created ON bills(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_shopkeeper ON customers(shopkeeper_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone)")
        
        # Add billease_id column if it doesn't exist (for existing databases)
        # Note: We add without UNIQUE first, then create unique index after migration
        try:
            cursor.execute("ALTER TABLE shopkeepers ADD COLUMN billease_id TEXT")
            logger.info("Added billease_id column to shopkeepers table")
            # Create unique index after adding column
            try:
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_shopkeepers_billease_id ON shopkeepers(billease_id)")
                logger.info("Created unique index on billease_id")
            except sqlite3.OperationalError as idx_error:
                logger.debug(f"Index may already exist: {idx_error}")
        except sqlite3.OperationalError as e:
            # Column already exists or other error
            if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                logger.debug(f"Column billease_id may already exist: {e}")
            # Ensure unique index exists even if column already exists
            try:
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_shopkeepers_billease_id ON shopkeepers(billease_id)")
            except sqlite3.OperationalError:
                pass  # Index may already exist
        
        conn.commit()
        conn.close()
        
        # Run migrations (after all tables are created and committed)
        # Note: _migrate_billease_ids will be called, but we also ensure column exists first
        try:
            self._migrate_billease_ids()
            self._migrate_bills_table()
            self._migrate_stock_add_unit(None)
        except Exception as e:
            logger.warning(f"Error during migration: {e}")
        
        self._migrate_bills_to_new_format()
        
        logger.info("Database initialized successfully")
    
    # Shopkeeper operations
    def create_shopkeeper(self, username: str, password: str, shop_name: str, 
                         email: str = None, phone: str = None) -> int:
        """
        Create a new shopkeeper account.
        
        Args:
            username: Unique username
            password: Plain text password (will be hashed)
            shop_name: Name of the shop
            email: Optional email
            phone: Optional phone number
            
        Returns:
            int: Shopkeeper ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Check if billease_id column exists
        cursor.execute("PRAGMA table_info(shopkeepers)")
        columns = [column[1] for column in cursor.fetchall()]
        has_billease_id = 'billease_id' in columns
        
        # Generate unique Billease ID if column exists
        billease_id = None
        if has_billease_id:
            billease_id = self._generate_billease_id()
        
        try:
            if has_billease_id:
                cursor.execute("""
                    INSERT INTO shopkeepers (username, password_hash, shop_name, email, phone, billease_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username, password_hash, shop_name, email, phone, billease_id))
            else:
                cursor.execute("""
                    INSERT INTO shopkeepers (username, password_hash, shop_name, email, phone)
                    VALUES (?, ?, ?, ?, ?)
                """, (username, password_hash, shop_name, email, phone))
            
            shopkeeper_id = cursor.lastrowid
            conn.commit()
            
            # Initialize default prices for this shopkeeper
            self._initialize_default_prices(shopkeeper_id)
            
            logger.info(f"Created shopkeeper: {username} (ID: {shopkeeper_id})")
            return shopkeeper_id
        except sqlite3.IntegrityError:
            conn.close()
            raise ValueError(f"Username '{username}' already exists")
        finally:
            conn.close()
    
    def authenticate_shopkeeper(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate a shopkeeper.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            dict: Shopkeeper info if authenticated, None otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Check if billease_id column exists
            cursor.execute("PRAGMA table_info(shopkeepers)")
            columns = [column[1] for column in cursor.fetchall()]
            has_billease_id = 'billease_id' in columns
            
            # Build query based on column existence
            if has_billease_id:
                cursor.execute("""
                    SELECT id, username, shop_name, email, phone, billease_id, created_at
                    FROM shopkeepers
                    WHERE username = ? AND password_hash = ? AND is_active = 1
                """, (username, password_hash))
            else:
                cursor.execute("""
                    SELECT id, username, shop_name, email, phone, created_at
                    FROM shopkeepers
                    WHERE username = ? AND password_hash = ? AND is_active = 1
                """, (username, password_hash))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                result = {
                    "id": row["id"],
                    "username": row["username"],
                    "shop_name": row["shop_name"],
                    "email": row["email"],
                    "phone": row["phone"],
                    "created_at": row["created_at"]
                }
                # Add billease_id if column exists
                if has_billease_id:
                    billease_id = row["billease_id"]
                    # If billease_id is missing, generate one now
                    if not billease_id or billease_id == '':
                        try:
                            billease_id = self._generate_billease_id()
                            # Update the shopkeeper with the new billease_id
                            update_conn = self._get_connection()
                            update_cursor = update_conn.cursor()
                            update_cursor.execute("""
                                UPDATE shopkeepers 
                                SET billease_id = ? 
                                WHERE id = ?
                            """, (billease_id, row["id"]))
                            update_conn.commit()
                            update_conn.close()
                            logger.info(f"Generated Billease ID {billease_id} for shopkeeper {row['id']}")
                        except Exception as e:
                            logger.warning(f"Error generating billease_id for shopkeeper {row['id']}: {e}")
                            billease_id = None
                    result["billease_id"] = billease_id
                return result
            return None
        except Exception as e:
            logger.error(f"Error authenticating shopkeeper: {str(e)}", exc_info=True)
            return None
    
    def get_shopkeeper(self, shopkeeper_id: int) -> Optional[Dict]:
        """Get shopkeeper by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if billease_id column exists
        cursor.execute("PRAGMA table_info(shopkeepers)")
        columns = [column[1] for column in cursor.fetchall()]
        has_billease_id = 'billease_id' in columns
        
        # Build query based on column existence
        if has_billease_id:
            cursor.execute("""
                SELECT id, username, shop_name, email, phone, billease_id, created_at
                FROM shopkeepers
                WHERE id = ? AND is_active = 1
            """, (shopkeeper_id,))
        else:
            cursor.execute("""
                SELECT id, username, shop_name, email, phone, created_at
                FROM shopkeepers
                WHERE id = ? AND is_active = 1
            """, (shopkeeper_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = {
                "id": row["id"],
                "username": row["username"],
                "shop_name": row["shop_name"],
                "email": row["email"],
                "phone": row["phone"],
                "created_at": row["created_at"]
            }
            # Add billease_id if column exists
            if has_billease_id:
                billease_id = row["billease_id"]
                # If billease_id is missing, generate one now
                if not billease_id or billease_id == '':
                    try:
                        billease_id = self._generate_billease_id()
                        # Update the shopkeeper with the new billease_id
                        update_conn = self._get_connection()
                        update_cursor = update_conn.cursor()
                        update_cursor.execute("""
                            UPDATE shopkeepers 
                            SET billease_id = ? 
                            WHERE id = ?
                        """, (billease_id, row["id"]))
                        update_conn.commit()
                        update_conn.close()
                        logger.info(f"Generated Billease ID {billease_id} for shopkeeper {row['id']}")
                    except Exception as e:
                        logger.warning(f"Error generating billease_id for shopkeeper {row['id']}: {e}")
                        billease_id = None
                result["billease_id"] = billease_id
            return result
        return None
    
    def update_shopkeeper(self, shopkeeper_id: int, shop_name: str = None, 
                          email: str = None, phone: str = None) -> bool:
        """
        Update shopkeeper profile information.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            shop_name: New shop name (optional)
            email: New email (optional)
            phone: New phone (optional)
            
        Returns:
            bool: True if updated successfully
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Build update query dynamically based on provided fields
        updates = []
        params = []
        
        if shop_name is not None:
            updates.append("shop_name = ?")
            params.append(shop_name)
        
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        
        if phone is not None:
            updates.append("phone = ?")
            params.append(phone)
        
        if not updates:
            conn.close()
            return False
        
        params.append(shopkeeper_id)
        
        query = f"""
            UPDATE shopkeepers
            SET {', '.join(updates)}
            WHERE id = ? AND is_active = 1
        """
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        logger.info(f"Updated shopkeeper profile: ID {shopkeeper_id}")
        return True
    
    # Price operations
    def _initialize_default_prices(self, shopkeeper_id: int):
        """Initialize default prices for a new shopkeeper."""
        default_prices = {
            "tomato": 80.0, "potato": 40.0, "onion": 60.0, "carrot": 50.0,
            "cabbage": 30.0, "banana": 60.0, "apple": 100.0, "orange": 80.0,
            "cup": 100.0, "bottle": 50.0, "bowl": 80.0,
            "phone": 5000.0, "mouse": 500.0, "keyboard": 1500.0, "laptop": 50000.0,
            "tablet": 20000.0, "pen": 10.0, "pencil": 5.0, "book": 200.0,
            "notebook": 50.0, "monitor": 10000.0, "eraser": 5.0, "ruler": 20.0,
            "calculator": 300.0, "chair": 2000.0, "desk": 5000.0, "envelope": 5.0,
            "filing-cabinet": 3000.0, "luggage": 2000.0, "mug": 100.0,
            "printer": 5000.0, "scissors": 50.0, "shelf": 1500.0, "stapler": 100.0,
            "wall-clock": 500.0, "whiteboard": 2000.0
        }
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for item_name, price in default_prices.items():
            cursor.execute("""
                INSERT INTO prices (shopkeeper_id, item_name, price_per_kg)
                VALUES (?, ?, ?)
            """, (shopkeeper_id, item_name, price))
        
        conn.commit()
        conn.close()
        logger.info(f"Initialized default prices for shopkeeper {shopkeeper_id}")
    
    def get_price(self, shopkeeper_id: int, item_name: str) -> Optional[float]:
        """
        Get price for an item for a specific shopkeeper.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            item_name: Item name
            
        Returns:
            float: Price per kg (or selling_price if available), or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COALESCE(selling_price, price_per_kg) as price FROM prices
            WHERE shopkeeper_id = ? AND item_name = ?
        """, (shopkeeper_id, item_name.lower()))
        
        row = cursor.fetchone()
        conn.close()
        
        return row["price"] if row else None
    
    def get_item_details(self, shopkeeper_id: int, item_name: str) -> Optional[Dict]:
        """
        Get complete item details including cost price, selling price, and pricing type.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            item_name: Item name
            
        Returns:
            dict: Item details with cost_price, selling_price, pricing_type, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT item_name, price_per_kg, cost_price, selling_price, pricing_type
            FROM prices
            WHERE shopkeeper_id = ? AND item_name = ?
        """, (shopkeeper_id, item_name.lower()))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "item_name": row["item_name"],
                "price_per_kg": row["price_per_kg"],
                "cost_price": row["cost_price"],
                "selling_price": row["selling_price"] or row["price_per_kg"],
                "pricing_type": row["pricing_type"] or "kg"
            }
        return None
    
    def set_price(self, shopkeeper_id: int, item_name: str, price_per_kg: float):
        """
        Set or update price for an item.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            item_name: Item name
            price_per_kg: Price per kilogram
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO prices (shopkeeper_id, item_name, price_per_kg)
            VALUES (?, ?, ?)
            ON CONFLICT(shopkeeper_id, item_name) 
            DO UPDATE SET price_per_kg = ?, updated_at = CURRENT_TIMESTAMP
        """, (shopkeeper_id, item_name.lower(), price_per_kg, price_per_kg))
        
        conn.commit()
        conn.close()
        logger.info(f"Updated price for {item_name}: ₹{price_per_kg}/kg (shopkeeper: {shopkeeper_id})")
    
    def update_item(self, shopkeeper_id: int, item_name: str, cost_price: float = None, 
                    selling_price: float = None, pricing_type: str = None):
        """
        Update item details including cost price, selling price, and pricing type.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            item_name: Item name
            cost_price: Cost price (optional)
            selling_price: Selling price (optional)
            pricing_type: Pricing type - 'kg', 'ltr', or 'units' (optional)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Build update query dynamically based on provided fields
        updates = []
        params = []
        
        if cost_price is not None:
            updates.append("cost_price = ?")
            params.append(cost_price)
        
        if selling_price is not None:
            updates.append("selling_price = ?")
            params.append(selling_price)
            # Also update price_per_kg for backward compatibility
            updates.append("price_per_kg = ?")
            params.append(selling_price)
        
        if pricing_type is not None:
            if pricing_type not in ['kg', 'ltr', 'units']:
                raise ValueError("pricing_type must be 'kg', 'ltr', or 'units'")
            updates.append("pricing_type = ?")
            params.append(pricing_type)
        
        if not updates:
            conn.close()
            return
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([shopkeeper_id, item_name.lower()])
        
        query = f"""
            UPDATE prices 
            SET {', '.join(updates)}
            WHERE shopkeeper_id = ? AND item_name = ?
        """
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        logger.info(f"Updated item {item_name} for shopkeeper {shopkeeper_id}")
    
    def create_item(self, shopkeeper_id: int, item_name: str, cost_price: float = None,
                    selling_price: float = None, pricing_type: str = 'kg'):
        """
        Create a new item in the prices table.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            item_name: Item name
            cost_price: Cost price (optional)
            selling_price: Selling price (required if cost_price not provided)
            pricing_type: Pricing type - 'kg', 'ltr', or 'units' (default: 'kg')
        """
        if selling_price is None and cost_price is None:
            raise ValueError("Either selling_price or cost_price must be provided")
        
        if selling_price is None:
            selling_price = cost_price  # Default selling price to cost price if not provided
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO prices (shopkeeper_id, item_name, price_per_kg, cost_price, selling_price, pricing_type)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(shopkeeper_id, item_name) 
            DO UPDATE SET 
                price_per_kg = ?,
                cost_price = COALESCE(?, cost_price),
                selling_price = COALESCE(?, selling_price),
                pricing_type = COALESCE(?, pricing_type),
                updated_at = CURRENT_TIMESTAMP
        """, (shopkeeper_id, item_name.lower(), selling_price, cost_price, selling_price, pricing_type,
              selling_price, cost_price, selling_price, pricing_type))
        
        conn.commit()
        conn.close()
        logger.info(f"Created/updated item {item_name} for shopkeeper {shopkeeper_id}")
    
    def get_all_prices(self, shopkeeper_id: int) -> Dict[str, float]:
        """
        Get all prices for a shopkeeper (backward compatibility).
        
        Args:
            shopkeeper_id: Shopkeeper ID
            
        Returns:
            dict: {item_name: price_per_kg}
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT item_name, COALESCE(selling_price, price_per_kg) as price FROM prices
            WHERE shopkeeper_id = ?
            ORDER BY item_name
        """, (shopkeeper_id,))
        
        prices = {row["item_name"]: row["price"] for row in cursor.fetchall()}
        conn.close()
        
        return prices
    
    def get_all_items(self, shopkeeper_id: int) -> List[Dict]:
        """
        Get all items with complete details for a shopkeeper.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            
        Returns:
            list: List of dicts with item_name, cost_price, selling_price, pricing_type
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT item_name, price_per_kg, cost_price, selling_price, pricing_type
            FROM prices
            WHERE shopkeeper_id = ?
            ORDER BY item_name
        """, (shopkeeper_id,))
        
        items = []
        for row in cursor.fetchall():
            items.append({
                "item_name": row["item_name"],
                "price_per_kg": row["price_per_kg"],
                "cost_price": row["cost_price"],
                "selling_price": row["selling_price"] or row["price_per_kg"],
                "pricing_type": row["pricing_type"] or "kg"
            })
        
        conn.close()
        return items
    
    def update_prices_bulk(self, shopkeeper_id: int, prices: Dict[str, float]):
        """
        Update multiple prices at once.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            prices: Dictionary of {item_name: price_per_kg}
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for item_name, price_per_kg in prices.items():
            cursor.execute("""
                INSERT INTO prices (shopkeeper_id, item_name, price_per_kg)
                VALUES (?, ?, ?)
                ON CONFLICT(shopkeeper_id, item_name) 
                DO UPDATE SET price_per_kg = ?, updated_at = CURRENT_TIMESTAMP
            """, (shopkeeper_id, item_name.lower(), price_per_kg, price_per_kg))
        
        conn.commit()
        conn.close()
        logger.info(f"Updated {len(prices)} prices for shopkeeper {shopkeeper_id}")
    
    # Bill operations
    def save_bill(self, shopkeeper_id: int, items: List[Dict], total_amount: float, 
                  is_unpaid: bool = False, customer_name: Optional[str] = None, 
                  customer_phone: Optional[str] = None) -> str:
        """
        Save a completed bill to history.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            items: List of bill items
            total_amount: Total bill amount
            is_unpaid: Whether the bill is unpaid
            customer_name: Customer name (required if is_unpaid is True)
            customer_phone: Customer phone (required if is_unpaid is True)
            
        Returns:
            str: Bill number
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Generate bill number using current timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        bill_number = f"BILL-{timestamp}-{shopkeeper_id}"
        
        # Get current timestamp in ISO format for created_at
        # Use local timezone explicitly - format as ISO 8601 for better JavaScript compatibility
        now = datetime.now()
        created_at = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Convert items to JSON
        items_json = json.dumps(items)
        
        customer_id = None
        # Create customer if name is provided (for both paid and unpaid bills)
        if customer_name and customer_name.strip():
            # If phone is not provided, try to get it from existing customer by name
            if not customer_phone or not customer_phone.strip():
                existing_customer = self.get_customer_by_name(shopkeeper_id, customer_name)
                if existing_customer:
                    customer_phone = existing_customer["phone"]
                else:
                    # Create customer without phone if not found
                    customer_phone = None
            
            # Get or create customer (phone can be None/empty)
            customer_id = self._get_or_create_customer(shopkeeper_id, customer_name, customer_phone or "", cursor)
        
        cursor.execute("""
            INSERT INTO bills (shopkeeper_id, bill_number, total_amount, items_json, is_unpaid, customer_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (shopkeeper_id, bill_number, total_amount, items_json, 1 if is_unpaid else 0, customer_id, created_at))
        
        # Deduct sold quantities from stock
        self._deduct_stock_for_bill(shopkeeper_id, items, cursor)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Saved bill {bill_number} for shopkeeper {shopkeeper_id} (Total: ₹{total_amount}, Unpaid: {is_unpaid}) at {created_at}")
        return bill_number
    
    def get_customer_by_name(self, shopkeeper_id: int, name: str) -> Optional[Dict]:
        """
        Get customer by name for a shopkeeper.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            name: Customer name
            
        Returns:
            dict: Customer info (id, name, phone) or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, phone FROM customers
            WHERE shopkeeper_id = ? AND LOWER(name) = LOWER(?)
        """, (shopkeeper_id, name.strip()))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row["id"],
                "name": row["name"],
                "phone": row["phone"]
            }
        return None
    
    def _get_or_create_customer(self, shopkeeper_id: int, name: str, phone: str = None, cursor = None) -> int:
        """
        Get existing customer or create a new one.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            name: Customer name
            phone: Customer phone number (optional)
            cursor: Database cursor (must be from an open connection)
            
        Returns:
            int: Customer ID
        """
        if cursor is None:
            conn = self._get_connection()
            cursor = conn.cursor()
            should_close = True
        else:
            should_close = False
        
        # Normalize phone - use empty string if None or empty
        phone = phone.strip() if phone and phone.strip() else ""
        
        # Try to get existing customer by phone first (if phone provided)
        if phone:
            cursor.execute("""
                SELECT id FROM customers
                WHERE shopkeeper_id = ? AND phone = ?
            """, (shopkeeper_id, phone))
            
            row = cursor.fetchone()
            if row:
                if should_close:
                    conn.close()
                return row["id"]
        
        # Try to get existing customer by name
        cursor.execute("""
            SELECT id FROM customers
            WHERE shopkeeper_id = ? AND LOWER(name) = LOWER(?)
        """, (shopkeeper_id, name.strip()))
        
        row = cursor.fetchone()
        if row:
            # Update phone number if provided and different
            if phone:
                cursor.execute("""
                    UPDATE customers SET phone = ? WHERE id = ?
                """, (phone, row["id"]))
            if should_close:
                conn.commit()
                conn.close()
            return row["id"]
        
        # Create new customer
        cursor.execute("""
            INSERT INTO customers (shopkeeper_id, name, phone)
            VALUES (?, ?, ?)
        """, (shopkeeper_id, name.strip(), phone))
        
        customer_id = cursor.lastrowid
        if should_close:
            conn.commit()
            conn.close()
        
        return customer_id
    
    # Stock / inventory operations
    def get_stock_list(self, shopkeeper_id: int) -> List[Dict]:
        """
        Get all stock items for a shopkeeper (item_name, quantity, unit).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, item_name, quantity, updated_at,
                   COALESCE(unit, 'kg') AS unit
            FROM stock
            WHERE shopkeeper_id = ?
            ORDER BY item_name
        """, (shopkeeper_id,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": row["id"],
                "item_name": row["item_name"],
                "quantity": float(row["quantity"]),
                "unit": ((row["unit"] or "kg") if "unit" in row.keys() else "kg").lower(),
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def add_or_update_stock(self, shopkeeper_id: int, item_name: str, quantity: float, unit: str = "kg") -> Dict:
        """
        Add a new stock item or update quantity/unit for existing item.
        Unit: 'kg', 'unit', or 'ltr'. Stock is per shopkeeper.
        Returns the stock row.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        item_name_norm = item_name.strip()
        if not item_name_norm:
            conn.close()
            raise ValueError("Item name cannot be empty")
        if quantity < 0:
            conn.close()
            raise ValueError("Quantity cannot be negative")
        unit_norm = (unit or "kg").strip().lower()
        if unit_norm not in ("kg", "unit", "ltr", "units"):
            unit_norm = "kg"
        if unit_norm == "units":
            unit_norm = "unit"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "SELECT id FROM stock WHERE shopkeeper_id = ? AND item_name = ?",
            (shopkeeper_id, item_name_norm),
        )
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                "UPDATE stock SET quantity = ?, unit = ?, updated_at = ? WHERE id = ?",
                (quantity, unit_norm, now, existing["id"]),
            )
        else:
            cursor.execute(
                "INSERT INTO stock (shopkeeper_id, item_name, quantity, unit, updated_at) VALUES (?, ?, ?, ?, ?)",
                (shopkeeper_id, item_name_norm, quantity, unit_norm, now),
            )
        cursor.execute(
            "SELECT id, item_name, quantity, updated_at, COALESCE(unit, 'kg') AS unit FROM stock WHERE shopkeeper_id = ? AND item_name = ?",
            (shopkeeper_id, item_name_norm),
        )
        row = cursor.fetchone()
        conn.commit()
        conn.close()
        return {
            "id": row["id"],
            "item_name": row["item_name"],
            "quantity": float(row["quantity"]),
            "unit": (row["unit"] or "kg").lower(),
            "updated_at": row["updated_at"],
        }
    
    def adjust_stock_quantity(self, shopkeeper_id: int, item_name: str, delta: float) -> Optional[Dict]:
        """
        Adjust stock by a delta (positive = add, negative = deduct).
        Returns updated row or None if item not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        item_name_norm = item_name.strip()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "UPDATE stock SET quantity = quantity + ?, updated_at = ? WHERE shopkeeper_id = ? AND item_name = ?",
            (delta, now, shopkeeper_id, item_name_norm),
        )
        if cursor.rowcount == 0:
            conn.close()
            return None
        cursor.execute(
            "SELECT id, item_name, quantity, updated_at, COALESCE(unit, 'kg') AS unit FROM stock WHERE shopkeeper_id = ? AND item_name = ?",
            (shopkeeper_id, item_name_norm),
        )
        row = cursor.fetchone()
        conn.commit()
        conn.close()
        return {
            "id": row["id"],
            "item_name": row["item_name"],
            "quantity": float(row["quantity"]),
            "unit": (row["unit"] or "kg").lower(),
            "updated_at": row["updated_at"],
        }
    
    def delete_stock_item(self, shopkeeper_id: int, item_name: str) -> bool:
        """Remove a stock item. Returns True if deleted."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stock WHERE shopkeeper_id = ? AND item_name = ?", (shopkeeper_id, item_name.strip()))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    def _deduct_stock_for_bill(self, shopkeeper_id: int, items: List[Dict], cursor) -> None:
        """
        Deduct quantities from stock for each bill item.
        - For piece/unit items: deduct item quantity.
        - For weight/kg items: deduct weight_grams/1000 (stock in kg).
        Uses the given cursor (same transaction as save_bill).
        """
        for item in items:
            item_name = (item.get("item_name") or "").strip()
            if not item_name:
                continue
            pricing_type = (item.get("pricing_type") or "weight").lower()
            weight_grams = float(item.get("weight_grams") or 0)
            quantity = float(item.get("quantity") or 1)
            if pricing_type in ("kg", "weight", "ltr"):
                deduct = weight_grams / 1000.0
            else:
                deduct = quantity
            if deduct <= 0:
                continue
            cursor.execute("""
                UPDATE stock SET quantity = quantity - ?, updated_at = ?
                WHERE shopkeeper_id = ? AND item_name = ?
            """, (deduct, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), shopkeeper_id, item_name))
            if cursor.rowcount > 0:
                # Prevent negative stock
                cursor.execute("UPDATE stock SET quantity = 0 WHERE shopkeeper_id = ? AND item_name = ? AND quantity < 0", (shopkeeper_id, item_name))
    
    def get_customers_with_pending(self, shopkeeper_id: int) -> List[Dict]:
        """
        Get all customers with pending (unpaid) bills and their total pending amount.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            
        Returns:
            list: List of customer dictionaries with pending amount
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if is_unpaid column exists
        cursor.execute("PRAGMA table_info(bills)")
        columns = [column[1] for column in cursor.fetchall()]
        has_is_unpaid = 'is_unpaid' in columns
        has_customer_id = 'customer_id' in columns
        
        if not has_is_unpaid or not has_customer_id:
            logger.warning("Bills table missing is_unpaid or customer_id columns")
            conn.close()
            return []
        
        cursor.execute("""
            SELECT 
                c.id,
                c.name,
                c.phone,
                SUM(b.total_amount) as pending_amount,
                COUNT(b.id) as pending_bills_count
            FROM customers c
            INNER JOIN bills b ON c.id = b.customer_id
            WHERE c.shopkeeper_id = ? AND b.is_unpaid = 1
            GROUP BY c.id, c.name, c.phone
            ORDER BY pending_amount DESC
        """, (shopkeeper_id,))
        
        customers = []
        for row in cursor.fetchall():
            customers.append({
                "id": row["id"],
                "name": row["name"],
                "phone": row["phone"],
                "pending_amount": row["pending_amount"],
                "pending_bills_count": row["pending_bills_count"]
            })
        
        conn.close()
        return customers
    
    def get_customer_unpaid_bills(self, shopkeeper_id: int, customer_id: int) -> List[Dict]:
        """
        Get all unpaid bills for a specific customer.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            customer_id: Customer ID
            
        Returns:
            list: List of unpaid bill dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, bill_number, total_amount, items_json, created_at
            FROM bills
            WHERE shopkeeper_id = ? AND customer_id = ? AND is_unpaid = 1
            ORDER BY created_at DESC
        """, (shopkeeper_id, customer_id))
        
        bills = []
        for row in cursor.fetchall():
            bills.append({
                "id": row["id"],
                "bill_number": row["bill_number"],
                "total_amount": row["total_amount"],
                "items": json.loads(row["items_json"]),
                "created_at": row["created_at"]
            })
        
        conn.close()
        return bills
    
    def get_all_customers(self, shopkeeper_id: int) -> List[Dict]:
        """
        Get all customers for a shopkeeper.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            
        Returns:
            list: List of customer dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, phone
            FROM customers
            WHERE shopkeeper_id = ?
            ORDER BY name ASC
        """, (shopkeeper_id,))
        
        customers = []
        for row in cursor.fetchall():
            customers.append({
                "id": row["id"],
                "name": row["name"],
                "phone": row["phone"]
            })
        
        conn.close()
        return customers
    
    def create_customer(self, shopkeeper_id: int, name: str, phone: str) -> int:
        """
        Create a new customer.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            name: Customer name
            phone: Customer phone number
            
        Returns:
            int: Customer ID
            
        Raises:
            ValueError: If customer with same name or phone already exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if customer with same phone exists
        cursor.execute("""
            SELECT id FROM customers
            WHERE shopkeeper_id = ? AND phone = ?
        """, (shopkeeper_id, phone))
        
        if cursor.fetchone():
            conn.close()
            raise ValueError(f"Customer with phone {phone} already exists")
        
        # Check if customer with same name exists
        cursor.execute("""
            SELECT id FROM customers
            WHERE shopkeeper_id = ? AND LOWER(name) = LOWER(?)
        """, (shopkeeper_id, name.strip()))
        
        existing = cursor.fetchone()
        if existing:
            conn.close()
            raise ValueError(f"Customer with name '{name}' already exists")
        
        # Create new customer
        cursor.execute("""
            INSERT INTO customers (shopkeeper_id, name, phone)
            VALUES (?, ?, ?)
        """, (shopkeeper_id, name.strip(), phone))
        
        customer_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return customer_id
    
    def delete_customer(self, shopkeeper_id: int, customer_id: int) -> bool:
        """
        Delete a customer (only if they have no unpaid bills).
        
        Args:
            shopkeeper_id: Shopkeeper ID (for security)
            customer_id: Customer ID to delete
            
        Returns:
            bool: True if customer was deleted, False otherwise
            
        Raises:
            ValueError: If customer has unpaid bills
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if customer exists and belongs to shopkeeper
        cursor.execute("""
            SELECT id FROM customers
            WHERE id = ? AND shopkeeper_id = ?
        """, (customer_id, shopkeeper_id))
        
        if not cursor.fetchone():
            conn.close()
            return False
        
        # Check if customer has unpaid bills
        cursor.execute("""
            SELECT COUNT(*) FROM bills
            WHERE customer_id = ? AND is_unpaid = 1
        """, (customer_id,))
        
        unpaid_count = cursor.fetchone()[0]
        if unpaid_count > 0:
            conn.close()
            raise ValueError(f"Cannot delete customer with {unpaid_count} unpaid bill(s)")
        
        # Delete customer
        cursor.execute("""
            DELETE FROM customers
            WHERE id = ? AND shopkeeper_id = ?
        """, (customer_id, shopkeeper_id))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return deleted
    
    def mark_bill_as_paid(self, shopkeeper_id: int, bill_id: int) -> bool:
        """
        Mark a bill as paid by setting is_unpaid to 0.
        
        Args:
            shopkeeper_id: Shopkeeper ID (for security)
            bill_id: Bill ID to mark as paid
            
        Returns:
            bool: True if bill was found and updated, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if is_unpaid column exists
        cursor.execute("PRAGMA table_info(bills)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'is_unpaid' not in columns:
            conn.close()
            logger.warning("is_unpaid column does not exist in bills table")
            return False
        
        # First check if bill exists and belongs to this shopkeeper
        cursor.execute("""
            SELECT id, is_unpaid FROM bills
            WHERE id = ? AND shopkeeper_id = ?
        """, (bill_id, shopkeeper_id))
        
        bill = cursor.fetchone()
        if not bill:
            logger.warning(f"Bill {bill_id} not found for shopkeeper {shopkeeper_id}")
            conn.close()
            return False
        
        # Check if already paid (SQLite stores booleans as 0/1)
        is_unpaid = bill['is_unpaid']
        if is_unpaid == 0 or is_unpaid is False:
            logger.info(f"Bill {bill_id} is already paid (is_unpaid={is_unpaid})")
            conn.close()
            return False
        
        # Update the bill
        cursor.execute("""
            UPDATE bills
            SET is_unpaid = 0
            WHERE id = ? AND shopkeeper_id = ? AND is_unpaid = 1
        """, (bill_id, shopkeeper_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            logger.info(f"Marked bill {bill_id} as paid for shopkeeper {shopkeeper_id}")
        else:
            logger.warning(f"Failed to mark bill {bill_id} as paid (rowcount: {cursor.rowcount})")
        
        return success
    
    def get_bill_history(self, shopkeeper_id: int, limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        Get bill history for a shopkeeper.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            limit: Maximum number of bills to return
            offset: Offset for pagination
            
        Returns:
            list: List of bill dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, bill_number, total_amount, items_json, created_at
            FROM bills
            WHERE shopkeeper_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (shopkeeper_id, limit, offset))
        
        bills = []
        for row in cursor.fetchall():
            bills.append({
                "id": row["id"],
                "bill_number": row["bill_number"],
                "total_amount": row["total_amount"],
                "items": json.loads(row["items_json"]),
                "created_at": row["created_at"]
            })
        
        conn.close()
        return bills
    
    def get_bill(self, bill_id: int, shopkeeper_id: int) -> Optional[Dict]:
        """
        Get a specific bill by ID.
        
        Args:
            bill_id: Bill ID
            shopkeeper_id: Shopkeeper ID (for security)
            
        Returns:
            dict: Bill information or None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, bill_number, total_amount, items_json, created_at
            FROM bills
            WHERE id = ? AND shopkeeper_id = ?
        """, (bill_id, shopkeeper_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row["id"],
                "bill_number": row["bill_number"],
                "total_amount": row["total_amount"],
                "items": json.loads(row["items_json"]),
                "created_at": row["created_at"]
            }
        return None
    
    def get_statistics(self, shopkeeper_id: int, period: str = "days") -> Dict:
        """
        Get statistics for a shopkeeper.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            period: "days" or "months" for grouping
            
        Returns:
            dict: Statistics including earnings by period and most sold items
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get all bills for this shopkeeper
        cursor.execute("""
            SELECT total_amount, items_json, created_at
            FROM bills
            WHERE shopkeeper_id = ?
            ORDER BY created_at DESC
        """, (shopkeeper_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Process bills for earnings by period
        earnings_by_period = {}
        item_counts = {}
        
        for row in rows:
            total_amount = row["total_amount"]
            items_json = row["items_json"]
            created_at = row["created_at"]
            
            # Parse date
            try:
                if 'T' in created_at:
                    date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    date_obj = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
            except:
                continue
            
            if period == "days":
                period_key = date_obj.strftime('%Y-%m-%d')
                period_label = date_obj.strftime('%d')  # Just day number for X-axis
                month_label = date_obj.strftime('%B %Y')  # Month and year for top
            else:  # months
                period_key = date_obj.strftime('%Y-%m')
                period_label = date_obj.strftime('%B')  # Just month name for X-axis
                month_label = date_obj.strftime('%Y')  # Year for top
            
            # Aggregate earnings
            if period_key not in earnings_by_period:
                earnings_by_period[period_key] = {
                    "label": period_label,
                    "month_label": month_label,
                    "amount": 0.0,
                    "count": 0
                }
            earnings_by_period[period_key]["amount"] += total_amount
            earnings_by_period[period_key]["count"] += 1
            
            # Count items (track units for per-piece items, kg for weight-based items)
            try:
                items = json.loads(items_json)
                for item in items:
                    item_name = item.get("item_name", "").lower()
                    if item_name:
                        # Get pricing type (default to "weight" for old bills)
                        pricing_type = item.get("pricing_type", "weight")
                        quantity = item.get("quantity", 1)
                        weight_grams = item.get("weight_grams", 0)
                        
                        # Initialize item tracking if not exists
                        if item_name not in item_counts:
                            item_counts[item_name] = {
                                "units": 0,
                                "kg": 0.0,
                                "pricing_type": pricing_type
                            }
                        
                        # Track based on pricing type
                        if pricing_type == "piece":
                            # For per-piece items, track units
                            item_counts[item_name]["units"] += quantity
                            item_counts[item_name]["pricing_type"] = "piece"
                        else:
                            # For weight-based items, track kg
                            weight_kg = weight_grams / 1000.0
                            item_counts[item_name]["kg"] += weight_kg
                            item_counts[item_name]["pricing_type"] = "weight"
            except:
                pass
        
        # Sort earnings by period key (chronological)
        sorted_earnings = sorted(earnings_by_period.items())
        
        # Fill in missing periods with zeros
        if period == "days":
            # Always show all days in the current month
            from datetime import timedelta
            from calendar import monthrange
            
            today = datetime.now()
            current_month = today.replace(day=1)
            # Get the last day of the current month
            last_day = monthrange(current_month.year, current_month.month)[1]
            
            # If we have data, use the month from the data, otherwise use current month
            if sorted_earnings:
                # Use the month from the most recent data
                last_date = datetime.strptime(sorted_earnings[-1][0], '%Y-%m-%d')
                current_month = last_date.replace(day=1)
                last_day = monthrange(current_month.year, current_month.month)[1]
            
            # Generate all days in the month
            filled_data = []
            for day in range(1, last_day + 1):
                current_date = current_month.replace(day=day)
                date_key = current_date.strftime('%Y-%m-%d')
                day_label = current_date.strftime('%d')
                month_label = current_date.strftime('%B %Y')
                
                if date_key in earnings_by_period:
                    filled_data.append({
                        "period": earnings_by_period[date_key]["label"],
                        "month_label": earnings_by_period[date_key]["month_label"],
                        "amount": earnings_by_period[date_key]["amount"],
                        "count": earnings_by_period[date_key]["count"]
                    })
                else:
                    filled_data.append({
                        "period": day_label,
                        "month_label": month_label,
                        "amount": 0.0,
                        "count": 0
                    })
            earnings_data = filled_data
        else:  # months
            # Always show all 12 months in the current year
            today = datetime.now()
            current_year = today.year
            
            # If we have data, use the year from the data, otherwise use current year
            if sorted_earnings:
                # Use the year from the most recent data
                last_month = datetime.strptime(sorted_earnings[-1][0] + '-01', '%Y-%m-%d')
                current_year = last_month.year
            
            # Generate all 12 months
            filled_data = []
            for month_num in range(1, 13):
                current_month = datetime(current_year, month_num, 1)
                month_key = current_month.strftime('%Y-%m')
                month_label = current_month.strftime('%B')
                year_label = current_month.strftime('%Y')
                
                if month_key in earnings_by_period:
                    filled_data.append({
                        "period": earnings_by_period[month_key]["label"],
                        "month_label": earnings_by_period[month_key]["month_label"],
                        "amount": earnings_by_period[month_key]["amount"],
                        "count": earnings_by_period[month_key]["count"]
                    })
                else:
                    filled_data.append({
                        "period": month_label,
                        "month_label": year_label,
                        "amount": 0.0,
                        "count": 0
                    })
            earnings_data = filled_data
        
        # Get most sold items (top 10)
        # Sort by total quantity (units for per-piece, kg for weight-based)
        def get_sort_key(item_data):
            if isinstance(item_data, dict):
                if item_data.get("pricing_type") == "piece":
                    return item_data.get("units", 0)
                else:
                    return item_data.get("kg", 0.0)
            else:
                # Old format (just count)
                return item_data
        
        sorted_items = sorted(
            item_counts.items(), 
            key=lambda x: get_sort_key(x[1]), 
            reverse=True
        )[:10]
        
        # Format most sold items
        most_sold_items = []
        for name, data in sorted_items:
            if isinstance(data, dict):
                pricing_type = data.get("pricing_type", "weight")
                if pricing_type == "piece":
                    most_sold_items.append({
                        "item_name": name,
                        "total_quantity": data.get("units", 0),
                        "unit_type": "units"
                    })
                else:
                    most_sold_items.append({
                        "item_name": name,
                        "total_quantity": round(data.get("kg", 0.0), 2),
                        "unit_type": "kg"
                    })
            else:
                # Old format - assume weight-based
                most_sold_items.append({
                    "item_name": name,
                    "total_quantity": data,
                    "unit_type": "kg"
                })
        
        return {
            "earnings": earnings_data,
            "most_sold_items": most_sold_items,
            "total_earnings": sum(e["amount"] for e in earnings_data),
            "total_bills": len(rows)
        }

    def get_analytics(self, shopkeeper_id: int) -> Dict:
        """
        Deeper analytics for the Analytics page: revenue & profit summary,
        comparisons, trends by day/month, top items, bills by day of week,
        and low stock.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Load all bills for this shopkeeper
        cursor.execute("""
            SELECT total_amount, items_json, created_at
            FROM bills
            WHERE shopkeeper_id = ?
            ORDER BY created_at DESC
        """, (shopkeeper_id,))
        rows = cursor.fetchall()

        # Load latest item pricing (including cost) for profit calculations
        cursor.execute("""
            SELECT item_name, cost_price, selling_price, pricing_type, price_per_kg
            FROM prices
            WHERE shopkeeper_id = ?
        """, (shopkeeper_id,))
        price_rows = cursor.fetchall()
        price_map: Dict[str, Dict] = {}
        for r in price_rows:
            name = (r["item_name"] or "").strip().lower()
            if not name:
                continue
            selling = r["selling_price"] if r["selling_price"] is not None else r["price_per_kg"]
            price_map[name] = {
                "cost_price": r["cost_price"],
                "selling_price": selling,
                "pricing_type": (r["pricing_type"] or "kg").lower(),
            }

        today = datetime.now().date()
        this_month_start = today.replace(day=1)
        if this_month_start.month == 1:
            last_month_start = this_month_start.replace(year=today.year - 1, month=12)
        else:
            last_month_start = this_month_start.replace(month=this_month_start.month - 1)
        from calendar import monthrange
        _, last_month_days = monthrange(last_month_start.year, last_month_start.month)
        last_month_end = last_month_start.replace(day=last_month_days)

        total_revenue = 0.0
        total_profit = 0.0
        total_bills = 0
        this_month_revenue = 0.0
        this_month_profit = 0.0
        last_month_revenue = 0.0
        last_month_profit = 0.0
        today_revenue = 0.0
        today_profit = 0.0
        item_revenue: Dict[str, float] = {}
        item_profit: Dict[str, float] = {}
        bills_by_weekday = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}

        # Trends
        revenue_by_day: Dict[str, Dict] = {}
        revenue_by_month: Dict[str, Dict] = {}

        for row in rows:
            total_amount = float(row["total_amount"] or 0)
            items_json = row["items_json"]
            created_at = row["created_at"]

            # Parse date
            try:
                if "T" in created_at:
                    date_obj = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                else:
                    date_obj = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            except Exception:
                # Skip rows with invalid timestamps
                continue

            d = date_obj.date()
            weekday = date_obj.weekday()
            bills_by_weekday[weekday] = bills_by_weekday.get(weekday, 0) + 1

            total_bills += 1
            total_revenue += total_amount

            # Compute profit for this bill by looking at each item
            bill_profit = 0.0
            try:
                items = json.loads(items_json)
            except Exception:
                items = []

            for item in items:
                name = (item.get("item_name") or "").strip()
                if not name:
                    continue
                name_lower = name.lower()
                revenue_item = float(item.get("total_price") or 0.0)

                # Look up cost price info
                price_info = price_map.get(name_lower)
                cost_price = price_info.get("cost_price") if price_info else None

                # If we don't know cost price, we can't estimate profit – treat as zero profit
                if cost_price is None:
                    profit_item = 0.0
                else:
                    pricing_type = (item.get("pricing_type") or "weight").lower()
                    quantity = float(item.get("quantity") or 1.0)
                    weight_grams = float(item.get("weight_grams") or 0.0)

                    if pricing_type in ("kg", "weight", "ltr"):
                        # Cost price is per kg/litre, convert grams to kg
                        weight_kg = weight_grams / 1000.0
                        cost_item = cost_price * weight_kg
                    else:
                        # Per-piece items – cost per unit * quantity
                        cost_item = cost_price * quantity

                    profit_item = max(revenue_item - cost_item, 0.0)

                bill_profit += profit_item

                # Aggregate item-level revenue and profit
                item_revenue[name] = item_revenue.get(name, 0.0) + revenue_item
                item_profit[name] = item_profit.get(name, 0.0) + profit_item

            total_profit += bill_profit

            # Month and day buckets
            if d >= this_month_start:
                this_month_revenue += total_amount
                this_month_profit += bill_profit
            elif last_month_start <= d <= last_month_end:
                last_month_revenue += total_amount
                last_month_profit += bill_profit

            if d == today:
                today_revenue += total_amount
                today_profit += bill_profit

            # Daily trend bucket
            day_key = d.isoformat()
            if day_key not in revenue_by_day:
                revenue_by_day[day_key] = {
                    "date": day_key,
                    "day_label": d.strftime("%d %b"),
                    "revenue": 0.0,
                    "profit": 0.0,
                    "bills": 0,
                }
            revenue_by_day[day_key]["revenue"] += total_amount
            revenue_by_day[day_key]["profit"] += bill_profit
            revenue_by_day[day_key]["bills"] += 1

            # Monthly trend bucket (YYYY-MM)
            month_key = f"{d.year}-{d.month:02d}"
            if month_key not in revenue_by_month:
                revenue_by_month[month_key] = {
                    "month": month_key,
                    "month_label": d.strftime("%b %Y"),
                    "revenue": 0.0,
                    "profit": 0.0,
                    "bills": 0,
                }
            revenue_by_month[month_key]["revenue"] += total_amount
            revenue_by_month[month_key]["profit"] += bill_profit
            revenue_by_month[month_key]["bills"] += 1

        # Month-on-month change (revenue & profit)
        revenue_change_pct = None
        profit_change_pct = None
        if last_month_revenue and last_month_revenue > 0:
            revenue_change_pct = round(
                (this_month_revenue - last_month_revenue) / last_month_revenue * 100, 1
            )
        if last_month_profit and last_month_profit > 0:
            profit_change_pct = round(
                (this_month_profit - last_month_profit) / last_month_profit * 100, 1
            )

        # Top items by revenue and profit
        top_items_by_revenue = sorted(
            [{"item_name": k, "revenue": round(v, 2)} for k, v in item_revenue.items()],
            key=lambda x: x["revenue"],
            reverse=True,
        )[:15]

        top_items_by_profit = []
        for name, profit in item_profit.items():
            revenue_val = item_revenue.get(name, 0.0)
            margin_pct = round((profit / revenue_val) * 100, 1) if revenue_val > 0 else None
            top_items_by_profit.append({
                "item_name": name,
                "profit": round(profit, 2),
                "revenue": round(revenue_val, 2),
                "margin_percent": margin_pct,
            })
        top_items_by_profit.sort(key=lambda x: x["profit"], reverse=True)
        top_items_by_profit = top_items_by_profit[:15]

        # Bills by weekday
        weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        bills_by_day = [
            {"day": weekday_names[i], "count": bills_by_weekday.get(i, 0)}
            for i in range(7)
        ]

        # Low stock (reuse existing logic)
        low_stock = []
        try:
            stock_list = self.get_stock_list(shopkeeper_id)
            for s in stock_list:
                if float(s.get("quantity", 0)) <= 5:
                    low_stock.append({
                        "item_name": s["item_name"],
                        "quantity": s["quantity"],
                        "unit": s.get("unit") or "kg",
                    })
        except Exception:
            pass

        conn.close()

        # Sort trends chronologically
        daily_trend = [
            revenue_by_day[k] for k in sorted(revenue_by_day.keys())
        ]
        monthly_trend = [
            revenue_by_month[k] for k in sorted(revenue_by_month.keys())
        ]

        # Optionally limit daily trend to the last 90 days for readability
        if len(daily_trend) > 90:
            daily_trend = daily_trend[-90:]

        return {
            "summary": {
                "total_revenue": round(total_revenue, 2),
                "total_profit": round(total_profit, 2),
                "total_bills": total_bills,
                "avg_bill_value": round(total_revenue / total_bills, 2) if total_bills else 0,
                "avg_profit_per_bill": round(total_profit / total_bills, 2) if total_bills else 0,
                "today_revenue": round(today_revenue, 2),
                "today_profit": round(today_profit, 2),
                "this_month_revenue": round(this_month_revenue, 2),
                "this_month_profit": round(this_month_profit, 2),
                "last_month_revenue": round(last_month_revenue, 2),
                "last_month_profit": round(last_month_profit, 2),
                "revenue_change_percent": revenue_change_pct,
                "profit_change_percent": profit_change_pct,
            },
            "revenue_by_day": daily_trend,
            "revenue_by_month": monthly_trend,
            "top_items_by_revenue": top_items_by_revenue,
            "top_items_by_profit": top_items_by_profit,
            "bills_by_day_of_week": bills_by_day,
            "low_stock_items": low_stock,
        }

    def _generate_billease_id(self) -> str:
        """
        Generate a unique Billease ID.
        Format: BIL-XXXXXX where XXXXXX is a 6-character alphanumeric code.
        
        Returns:
            str: Unique Billease ID
        """
        # First check if billease_id column exists
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(shopkeepers)")
            columns = [column[1] for column in cursor.fetchall()]
            has_billease_id = 'billease_id' in columns
        except Exception as e:
            logger.warning(f"Error checking for billease_id column: {e}")
            has_billease_id = False
        finally:
            conn.close()
        
        if not has_billease_id:
            # Column doesn't exist, just generate an ID without checking
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            return f"BIL-{code}"
        
        while True:
            # Generate 6-character alphanumeric code
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            billease_id = f"BIL-{code}"
            
            # Check if ID already exists
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT id FROM shopkeepers WHERE billease_id = ?", (billease_id,))
                exists = cursor.fetchone()
            except sqlite3.OperationalError as e:
                # Column might not exist yet
                logger.warning(f"Error checking billease_id uniqueness: {e}")
                exists = None
            finally:
                conn.close()
            
            if not exists:
                return billease_id
    
    def _migrate_billease_ids(self):
        """
        Migrate existing shopkeepers to have billease_id.
        Generates unique Billease IDs for accounts that don't have one.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if billease_id column exists
        try:
            cursor.execute("PRAGMA table_info(shopkeepers)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'billease_id' not in columns:
                logger.info("billease_id column does not exist yet, will be added on next table creation")
                conn.close()
                return
        except Exception as e:
            logger.warning(f"Error checking for billease_id column: {e}")
            conn.close()
            return
        
        # Get all shopkeepers without billease_id
        try:
            cursor.execute("SELECT id FROM shopkeepers WHERE billease_id IS NULL OR billease_id = ''")
            rows = cursor.fetchall()
        except sqlite3.OperationalError as e:
            logger.warning(f"Error querying billease_id: {e}")
            conn.close()
            return
        
        updated_count = 0
        for row in rows:
            try:
                billease_id = self._generate_billease_id()
                cursor.execute("""
                    UPDATE shopkeepers 
                    SET billease_id = ? 
                    WHERE id = ?
                """, (billease_id, row["id"]))
                updated_count += 1
            except Exception as e:
                logger.warning(f"Error migrating billease_id for shopkeeper {row['id']}: {e}")
                continue
        
        if updated_count > 0:
            conn.commit()
            logger.info(f"✅ Migrated {updated_count} shopkeepers with Billease IDs")
        else:
            logger.info("All shopkeepers already have Billease IDs")
        
        conn.close()
    
    def _migrate_stock_add_unit(self, cursor=None):
        """Add unit column to stock table if missing (for existing DBs)."""
        conn = None
        if cursor is None:
            conn = self._get_connection()
            cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(stock)")
            columns = [row[1] for row in cursor.fetchall()]
            if "unit" not in columns:
                cursor.execute("ALTER TABLE stock ADD COLUMN unit TEXT NOT NULL DEFAULT 'kg'")
                if conn:
                    conn.commit()
                logger.info("Added unit column to stock table")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                logger.warning(f"Stock unit migration: {e}")
        finally:
            if conn:
                conn.close()

    # ==================== GST SETTINGS ====================

    def _ensure_default_gst_settings(self, shopkeeper_id: int):
        """
        Ensure default GST settings exist for a shopkeeper.
        
        Categories (editable later):
        - vegetables: 0%
        - fruits: 0%
        - stationery: 12%
        - fruit_juice: 12%
        - toothpaste: 18%
        - processed_food: 5%
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM gst_settings WHERE shopkeeper_id = ?
            """, (shopkeeper_id,))
            row = cursor.fetchone()
            if row and row["cnt"] > 0:
                conn.close()
                return
            defaults = [
                ("vegetables", "Vegetables (fresh)", 0.0),
                ("fruits", "Fruits (fresh)", 0.0),
                ("stationery", "Stationery & office", 12.0),
                ("fruit_juice", "Fruit juice / drinks", 12.0),
                ("toothpaste", "Toothpaste & oral care", 18.0),
                ("processed_food", "Processed / packaged food", 5.0),
            ]
            for key, label, rate in defaults:
                cursor.execute("""
                    INSERT OR IGNORE INTO gst_settings (shopkeeper_id, category_key, display_name, rate)
                    VALUES (?, ?, ?, ?)
                """, (shopkeeper_id, key, label, rate))
            conn.commit()
        finally:
            conn.close()

    def get_gst_settings(self, shopkeeper_id: int) -> List[Dict]:
        """Get GST settings for a shopkeeper (ensures defaults exist)."""
        self._ensure_default_gst_settings(shopkeeper_id)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category_key, display_name, rate
            FROM gst_settings
            WHERE shopkeeper_id = ?
            ORDER BY display_name
        """, (shopkeeper_id,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "category_key": row["category_key"],
                "display_name": row["display_name"],
                "rate": float(row["rate"]),
            }
            for row in rows
        ]

    def update_gst_rate(self, shopkeeper_id: int, category_key: str, rate: float) -> Dict:
        """Update GST rate for a specific category (creates defaults if needed)."""
        if rate < 0:
            raise ValueError("GST rate cannot be negative")
        self._ensure_default_gst_settings(shopkeeper_id)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE gst_settings SET rate = ?
            WHERE shopkeeper_id = ? AND category_key = ?
        """, (rate, shopkeeper_id, category_key))
        if cursor.rowcount == 0:
            # If category key was not part of defaults for some reason, insert it
            cursor.execute("""
                INSERT INTO gst_settings (shopkeeper_id, category_key, display_name, rate)
                VALUES (?, ?, ?, ?)
            """, (shopkeeper_id, category_key, category_key.title(), rate))
        cursor.execute("""
            SELECT category_key, display_name, rate
            FROM gst_settings
            WHERE shopkeeper_id = ? AND category_key = ?
        """, (shopkeeper_id, category_key))
        row = cursor.fetchone()
        conn.commit()
        conn.close()
        return {
            "category_key": row["category_key"],
            "display_name": row["display_name"],
            "rate": float(row["rate"]),
        }

    # Item name -> GST category (for rate lookup)
    ITEM_GST_CATEGORY = {
        "vegetables": ["tomato", "potato", "onion", "carrot", "cabbage"],
        "fruits": ["apple", "banana", "orange"],
        "stationery": [
            "pen", "pencil", "book", "notebook", "eraser", "ruler", "calculator",
            "mouse", "keyboard", "monitor", "desk", "chair", "scissors", "stapler",
            "envelope", "filing-cabinet", "luggage", "mug", "printer", "shelf",
            "wall-clock", "whiteboard", "phone", "tablet", "laptop"
        ],
        "fruit_juice": ["bottle", "cup", "bowl"],
        "toothpaste": ["toothpaste", "soap", "shampoo", "detergent"],
        "processed_food": [],  # default below
    }

    def get_gst_rate_for_item(self, shopkeeper_id: int, item_name: str) -> float:
        """
        Get GST rate % for an item based on its category.
        Returns 0 if shopkeeper_id is 0 or category not found.
        """
        if not shopkeeper_id:
            return 0.0
        name = (item_name or "").strip().lower()
        if not name:
            return 0.0
        category_key = "processed_food"
        for cat, items in self.ITEM_GST_CATEGORY.items():
            if name in items:
                category_key = cat
                break
        self._ensure_default_gst_settings(shopkeeper_id)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT rate FROM gst_settings WHERE shopkeeper_id = ? AND category_key = ?",
            (shopkeeper_id, category_key),
        )
        row = cursor.fetchone()
        conn.close()
        return float(row["rate"]) if row else 0.0

    def _migrate_bills_to_new_format(self):
        """
        Migrate old bills to include pricing_type and quantity fields.
        This function updates all existing bills that don't have these fields.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get all bills
        cursor.execute("SELECT id, items_json FROM bills")
        rows = cursor.fetchall()
        
        updated_count = 0
        for row in rows:
            try:
                items = json.loads(row["items_json"])
                updated = False
                
                # Check if any item needs migration
                for item in items:
                    # If pricing_type or quantity is missing, add them
                    if "pricing_type" not in item or "quantity" not in item:
                        updated = True
                        item_name_lower = item.get("item_name", "").lower()
                        
                        # Import PER_PIECE_ITEMS from item_detection
                        from app.services.item_detection import PER_PIECE_ITEMS
                        
                        # Determine pricing type
                        if item_name_lower in PER_PIECE_ITEMS:
                            item["pricing_type"] = "piece"
                            # For per-piece items, quantity defaults to 1 if not set
                            if "quantity" not in item:
                                item["quantity"] = 1
                        else:
                            item["pricing_type"] = "weight"
                            # For weight-based items, quantity is always 1
                            item["quantity"] = 1
                
                # Update the bill if any items were modified
                if updated:
                    updated_items_json = json.dumps(items)
                    cursor.execute("""
                        UPDATE bills 
                        SET items_json = ? 
                        WHERE id = ?
                    """, (updated_items_json, row["id"]))
                    updated_count += 1
                    
            except Exception as e:
                logger.warning(f"Error migrating bill {row['id']}: {e}")
                continue
        
        if updated_count > 0:
            conn.commit()
            logger.info(f"✅ Migrated {updated_count} bills to new format (added pricing_type and quantity)")
        
        conn.close()
    
    def _migrate_prices_table(self):
        """
        Migrate prices table to add new columns: cost_price, selling_price, pricing_type.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Check existing columns
            cursor.execute("PRAGMA table_info(prices)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add cost_price if it doesn't exist
            if 'cost_price' not in columns:
                cursor.execute("ALTER TABLE prices ADD COLUMN cost_price REAL")
                logger.info("Added cost_price column to prices table")
            
            # Add selling_price if it doesn't exist
            if 'selling_price' not in columns:
                cursor.execute("ALTER TABLE prices ADD COLUMN selling_price REAL")
                logger.info("Added selling_price column to prices table")
            
            # Add pricing_type if it doesn't exist
            if 'pricing_type' not in columns:
                cursor.execute("ALTER TABLE prices ADD COLUMN pricing_type TEXT DEFAULT 'kg'")
                # Update existing rows to have 'kg' as default
                cursor.execute("UPDATE prices SET pricing_type = 'kg' WHERE pricing_type IS NULL")
                logger.info("Added pricing_type column to prices table")
            
            # Migrate existing data: set selling_price = price_per_kg if selling_price is NULL
            cursor.execute("""
                UPDATE prices 
                SET selling_price = price_per_kg 
                WHERE selling_price IS NULL
            """)
            
            conn.commit()
        except Exception as e:
            logger.warning(f"Error migrating prices table: {e}")
        finally:
            conn.close()
    
    def _migrate_bills_table(self):
        """Migrate bills table to add is_unpaid and customer_id columns."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if columns exist
            cursor.execute("PRAGMA table_info(bills)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add is_unpaid column if it doesn't exist
            if 'is_unpaid' not in columns:
                try:
                    cursor.execute("ALTER TABLE bills ADD COLUMN is_unpaid BOOLEAN DEFAULT 0")
                    logger.info("Added is_unpaid column to bills table")
                except sqlite3.OperationalError as e:
                    if "duplicate column" not in str(e).lower():
                        logger.warning(f"Error adding is_unpaid column: {e}")
            
            # Add customer_id column if it doesn't exist
            if 'customer_id' not in columns:
                try:
                    cursor.execute("ALTER TABLE bills ADD COLUMN customer_id INTEGER")
                    logger.info("Added customer_id column to bills table")
                except sqlite3.OperationalError as e:
                    if "duplicate column" not in str(e).lower():
                        logger.warning(f"Error adding customer_id column: {e}")
            
            # Re-check columns after potential additions
            cursor.execute("PRAGMA table_info(bills)")
            columns_after = [column[1] for column in cursor.fetchall()]
            
            # Create indexes only if columns exist
            if 'customer_id' in columns_after:
                try:
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_customer ON bills(customer_id)")
                except sqlite3.OperationalError as e:
                    logger.debug(f"Error creating customer_id index: {e}")
            
            if 'is_unpaid' in columns_after:
                try:
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_unpaid ON bills(is_unpaid)")
                except sqlite3.OperationalError as e:
                    logger.debug(f"Error creating is_unpaid index: {e}")
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Error migrating bills table: {e}")


# Global database instance
db = Database()

