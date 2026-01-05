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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(id),
                UNIQUE(shopkeeper_id, item_name)
            )
        """)
        
        # Bills table (completed bills)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shopkeeper_id INTEGER NOT NULL,
                bill_number TEXT NOT NULL,
                total_amount REAL NOT NULL,
                items_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(id)
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shopkeeper_id ON prices(shopkeeper_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_shopkeeper ON bills(shopkeeper_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_created ON bills(created_at)")
        
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
        except Exception as e:
            logger.warning(f"Error during billease_id migration: {e}")
        
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
            float: Price per kg, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT price_per_kg FROM prices
            WHERE shopkeeper_id = ? AND item_name = ?
        """, (shopkeeper_id, item_name.lower()))
        
        row = cursor.fetchone()
        conn.close()
        
        return row["price_per_kg"] if row else None
    
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
    
    def get_all_prices(self, shopkeeper_id: int) -> Dict[str, float]:
        """
        Get all prices for a shopkeeper.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            
        Returns:
            dict: {item_name: price_per_kg}
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT item_name, price_per_kg FROM prices
            WHERE shopkeeper_id = ?
            ORDER BY item_name
        """, (shopkeeper_id,))
        
        prices = {row["item_name"]: row["price_per_kg"] for row in cursor.fetchall()}
        conn.close()
        
        return prices
    
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
    def save_bill(self, shopkeeper_id: int, items: List[Dict], total_amount: float) -> str:
        """
        Save a completed bill to history.
        
        Args:
            shopkeeper_id: Shopkeeper ID
            items: List of bill items
            total_amount: Total bill amount
            
        Returns:
            str: Bill number
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Generate bill number
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        bill_number = f"BILL-{timestamp}-{shopkeeper_id}"
        
        # Convert items to JSON
        items_json = json.dumps(items)
        
        cursor.execute("""
            INSERT INTO bills (shopkeeper_id, bill_number, total_amount, items_json)
            VALUES (?, ?, ?, ?)
        """, (shopkeeper_id, bill_number, total_amount, items_json))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Saved bill {bill_number} for shopkeeper {shopkeeper_id} (Total: ₹{total_amount})")
        return bill_number
    
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


# Global database instance
db = Database()

