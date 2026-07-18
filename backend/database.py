# Grocery Item Database and Catalog
import os
import sqlite3
from dotenv import load_dotenv

# Load local .env file
load_dotenv()

GROCERY_ITEMS = {
    "apple": {
        "id": "apple",
        "name": "Honeycrisp Apple",
        "price": 180.00,
        "cost_price": 130.00,
        "stock": 100.0,
        "unit": "kg",
        "category": "Produce",
        "sku": "4011-APP",
        "color": "#FF3B30",
        "icon": "🍎",
        "coco_class": "apple"
    },
    "banana": {
        "id": "banana",
        "name": "Organic Banana",
        "price": 60.00,
        "cost_price": 40.00,
        "stock": 150.0,
        "unit": "kg",
        "category": "Produce",
        "sku": "4011-BAN",
        "color": "#FFCC00",
        "icon": "🍌",
        "coco_class": "banana"
    },
    "orange": {
        "id": "orange",
        "name": "Navel Orange",
        "price": 120.00,
        "cost_price": 85.00,
        "stock": 120.0,
        "unit": "kg",
        "category": "Produce",
        "sku": "3107-ORN",
        "color": "#FF9500",
        "icon": "🍊",
        "coco_class": "orange"
    },
    "broccoli": {
        "id": "broccoli",
        "name": "Crown Broccoli",
        "price": 150.00,
        "cost_price": 100.00,
        "stock": 80.0,
        "unit": "kg",
        "category": "Produce",
        "sku": "4060-BRC",
        "color": "#34C759",
        "icon": "🥦",
        "coco_class": "broccoli"
    },
    "carrot": {
        "id": "carrot",
        "name": "Organic Carrots",
        "price": 50.00,
        "cost_price": 35.00,
        "stock": 200.0,
        "unit": "kg",
        "category": "Produce",
        "sku": "4094-CRT",
        "color": "#FF9500",
        "icon": "🥕",
        "coco_class": "carrot"
    },
    "bottle": {
        "id": "bottle",
        "name": "Spring Water Bottle",
        "price": 20.00,
        "cost_price": 12.00,
        "stock": 250.0,
        "unit": "item",
        "category": "Beverage",
        "sku": "012000000133",
        "color": "#5AC8FA",
        "icon": "💧",
        "coco_class": "bottle"
    },
    "cup": {
        "id": "cup",
        "name": "Artisan Coffee Cup",
        "price": 90.00,
        "cost_price": 30.00,
        "stock": 300.0,
        "unit": "item",
        "category": "Beverage",
        "sku": "073366115933",
        "color": "#AF52DE",
        "icon": "☕",
        "coco_class": "cup"
    },
    "bowl": {
        "id": "bowl",
        "name": "Fresh Salad Bowl",
        "price": 180.00,
        "cost_price": 110.00,
        "stock": 50.0,
        "unit": "item",
        "category": "Deli",
        "sku": "099482419447",
        "color": "#4CD964",
        "icon": "🥗",
        "coco_class": "bowl"
    },
    # Extra items that can be scanned via barcode/manual/OCR
    "milk": {
        "id": "milk",
        "name": "Whole Milk 1L",
        "price": 60.00,
        "cost_price": 48.00,
        "stock": 100.0,
        "unit": "item",
        "category": "Dairy",
        "sku": "078742351866",
        "color": "#E5E5EA",
        "icon": "🥛"
    },
    "bread": {
        "id": "bread",
        "name": "Sliced White Bread",
        "price": 45.00,
        "cost_price": 32.00,
        "stock": 90.0,
        "unit": "item",
        "category": "Bakery",
        "sku": "072250037127",
        "color": "#D1C4E9",
        "icon": "🍞"
    },
    "cereal": {
        "id": "cereal",
        "name": "Honey Nut O's Cereal",
        "price": 160.00,
        "cost_price": 115.00,
        "stock": 60.0,
        "unit": "item",
        "category": "Pantry",
        "sku": "016000123991",
        "color": "#FF8A65",
        "icon": "🥣"
    },
    "cookies": {
        "id": "cookies",
        "name": "Chocolate Chip Cookies",
        "price": 40.00,
        "cost_price": 25.00,
        "stock": 120.0,
        "unit": "item",
        "category": "Bakery",
        "sku": "044000032029",
        "color": "#8D6E63",
        "icon": "🍪"
    }
}

COCO_TO_GROCERY = {item["coco_class"]: item["id"] for item in GROCERY_ITEMS.values() if "coco_class" in item}

# SQLite Database for transactions
# Vercel serverless function environment only allows writing to /tmp/
if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/checkout.db"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "checkout.db")

# Optional Supabase Integration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if SUPABASE_URL:
    # Auto-clean URL trailing paths if copy-pasted incorrectly
    SUPABASE_URL = SUPABASE_URL.strip()
    if SUPABASE_URL.endswith("/rest/v1/"):
        SUPABASE_URL = SUPABASE_URL[:-9]
    elif SUPABASE_URL.endswith("/rest/v1"):
        SUPABASE_URL = SUPABASE_URL[:-8]
    if SUPABASE_URL.endswith("/"):
        SUPABASE_URL = SUPABASE_URL[:-1]

if SUPABASE_KEY:
    SUPABASE_KEY = SUPABASE_KEY.strip()

USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

if USE_SUPABASE:
    try:
        from supabase import create_client, Client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"INFO: database: Supabase Client initialized successfully with URL: {SUPABASE_URL}")
    except Exception as e:
        print(f"ERROR: database: Failed to load Supabase SDK or client: {e}")
        USE_SUPABASE = False

def init_db():
    if USE_SUPABASE:
        try:
            # Check if products already exist
            res = supabase.table("products").select("count", count="exact").limit(1).execute()
            count = res.count if res.count is not None else 0
            if count == 0:
                print("INFO: database: Populating default grocery items to Supabase...")
                payload = []
                for item in GROCERY_ITEMS.values():
                    payload.append({
                        "id": item["id"],
                        "name": item["name"],
                        "price": item["price"],
                        "cost_price": item["cost_price"],
                        "stock": item["stock"],
                        "unit": item["unit"],
                        "category": item["category"],
                        "sku": item["sku"],
                        "color": item["color"],
                        "icon": item["icon"],
                        "coco_class": item.get("coco_class")
                    })
                supabase.table("products").insert(payload).execute()
        except Exception as e:
            print(f"WARNING: database: Supabase init table populating failed/skipped: {e}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            cost_price REAL NOT NULL DEFAULT 0.0,
            stock REAL NOT NULL DEFAULT 100.0,
            unit TEXT NOT NULL,
            category TEXT NOT NULL,
            sku TEXT NOT NULL,
            color TEXT NOT NULL,
            icon TEXT NOT NULL,
            coco_class TEXT
        )
    """)
    
    # 2. Create transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_id TEXT UNIQUE NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            subtotal REAL NOT NULL,
            tax REAL NOT NULL,
            total REAL NOT NULL
        )
    """)
    
    # 3. Create transaction_items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            cost_price REAL NOT NULL DEFAULT 0.0,
            qty INTEGER NOT NULL,
            unit TEXT NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES transactions (id) ON DELETE CASCADE
        )
    """)
    
    # Run migrations for existing databases to add cost_price & stock if missing
    cursor.execute("PRAGMA table_info(products)")
    prod_columns = [col[1] for col in cursor.fetchall()]
    if "cost_price" not in prod_columns:
        cursor.execute("ALTER TABLE products ADD COLUMN cost_price REAL NOT NULL DEFAULT 0.0")
    if "stock" not in prod_columns:
        cursor.execute("ALTER TABLE products ADD COLUMN stock REAL NOT NULL DEFAULT 100.0")
        
    cursor.execute("PRAGMA table_info(transaction_items)")
    item_columns = [col[1] for col in cursor.fetchall()]
    if "cost_price" not in item_columns:
        cursor.execute("ALTER TABLE transaction_items ADD COLUMN cost_price REAL NOT NULL DEFAULT 0.0")
    
    # 4. Check if products table is empty; if so, populate it with default values
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    if count == 0:
        for item in GROCERY_ITEMS.values():
            cursor.execute(
                """INSERT INTO products (id, name, price, cost_price, stock, unit, category, sku, color, icon, coco_class) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item["id"],
                    item["name"],
                    item["price"],
                    item["cost_price"],
                    item["stock"],
                    item["unit"],
                    item["category"],
                    item["sku"],
                    item["color"],
                    item["icon"],
                    item.get("coco_class")
                )
            )
        conn.commit()
        
    conn.commit()
    conn.close()

def get_item_by_id(item_id):
    if USE_SUPABASE:
        try:
            res = supabase.table("products").select("*").eq("id", item_id).execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            print(f"Supabase error getting item: {e}")
            return GROCERY_ITEMS.get(item_id)
            
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error getting product by id: {e}")
        return GROCERY_ITEMS.get(item_id)
    finally:
        if not USE_SUPABASE:
            conn.close()

def get_item_by_coco_class(coco_class):
    if USE_SUPABASE:
        try:
            res = supabase.table("products").select("*").eq("coco_class", coco_class).execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            print(f"Supabase error getting item by coco class: {e}")
            for item in GROCERY_ITEMS.values():
                if item.get("coco_class") == coco_class:
                    return item
            return None
            
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE coco_class = ?", (coco_class,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error getting product by coco_class: {e}")
        for item in GROCERY_ITEMS.values():
            if item.get("coco_class") == coco_class:
                return item
        return None
    finally:
        if not USE_SUPABASE:
            conn.close()

def get_item_by_sku(sku):
    sku_clean = sku.strip().upper()
    if USE_SUPABASE:
        try:
            res = supabase.table("products").select("*").ilike("sku", sku_clean).execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            print(f"Supabase error getting item by sku: {e}")
            for item in GROCERY_ITEMS.values():
                if item["sku"] == sku_clean:
                    return item
            return None
            
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE UPPER(sku) = ?", (sku_clean,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error getting product by sku: {e}")
        for item in GROCERY_ITEMS.values():
            if item["sku"] == sku_clean:
                return item
        return None
    finally:
        if not USE_SUPABASE:
            conn.close()

def get_all_items():
    if USE_SUPABASE:
        try:
            res = supabase.table("products").select("*").execute()
            return res.data or []
        except Exception as e:
            print(f"Supabase error getting all items: {e}")
            return list(GROCERY_ITEMS.values())
            
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products")
        rows = cursor.fetchall()
        if not rows:
            return list(GROCERY_ITEMS.values())
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error getting all products: {e}")
        return list(GROCERY_ITEMS.values())
    finally:
        if not USE_SUPABASE:
            conn.close()

def update_product_details(product_id, price, cost_price, stock):
    if USE_SUPABASE:
        try:
            res = supabase.table("products").update({
                "price": price,
                "cost_price": cost_price,
                "stock": stock
            }).eq("id", product_id).execute()
            return len(res.data) > 0
        except Exception as e:
            print(f"Supabase error updating product details: {e}")
            return False
            
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE products SET price = ?, cost_price = ?, stock = ? WHERE id = ?",
            (price, cost_price, stock, product_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Database error updating product details: {e}")
        return False
    finally:
        if not USE_SUPABASE:
            conn.close()

def save_transaction(tx_id, subtotal, tax, total, items):
    if USE_SUPABASE:
        try:
            # 1. Insert transaction
            tx_res = supabase.table("transactions").insert({
                "tx_id": tx_id,
                "subtotal": subtotal,
                "tax": tax,
                "total": total
            }).execute()
            
            if not tx_res.data:
                return False
                
            transaction_id = tx_res.data[0]["id"]
            
            for item in items:
                # Get the cost price
                prod_res = supabase.table("products").select("cost_price, stock").eq("id", item["id"]).execute()
                cost_price = 0.0
                current_stock = 0.0
                if prod_res.data:
                    cost_price = prod_res.data[0].get("cost_price", 0.0)
                    current_stock = prod_res.data[0].get("stock", 0.0)
                
                # Write transaction item record
                supabase.table("transaction_items").insert({
                    "transaction_id": transaction_id,
                    "item_id": item["id"],
                    "name": item["name"],
                    "price": item["price"],
                    "cost_price": cost_price,
                    "qty": item["qty"],
                    "unit": item["unit"]
                }).execute()
                
                # Deduct stock
                new_stock = max(0.0, current_stock - item["qty"])
                supabase.table("products").update({"stock": new_stock}).eq("id", item["id"]).execute()
                
            return True
        except Exception as e:
            print(f"Supabase error saving transaction: {e}")
            return False

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (tx_id, subtotal, tax, total) VALUES (?, ?, ?, ?)",
            (tx_id, subtotal, tax, total)
        )
        transaction_id = cursor.lastrowid
        
        for item in items:
            # Query the database to get the active cost price
            cursor.execute("SELECT cost_price FROM products WHERE id = ?", (item["id"],))
            db_row = cursor.fetchone()
            cost_price = db_row[0] if db_row else 0.0
            
            # Write transaction item record
            cursor.execute(
                "INSERT INTO transaction_items (transaction_id, item_id, name, price, cost_price, qty, unit) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (transaction_id, item["id"], item["name"], item["price"], cost_price, item["qty"], item["unit"])
            )
            
            # Deduct stock inventory level
            cursor.execute(
                "UPDATE products SET stock = MAX(0.0, stock - ?) WHERE id = ?",
                (item["qty"], item["id"])
            )
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Database error saving transaction: {e}")
        return False
    finally:
        if not USE_SUPABASE:
            conn.close()

def get_all_transactions():
    if USE_SUPABASE:
        try:
            tx_res = supabase.table("transactions").select("*").order("timestamp", desc=True).execute()
            transactions = tx_res.data or []
            
            for tx in transactions:
                # Fetch transaction items
                items_res = supabase.table("transaction_items").select("*").eq("transaction_id", tx["id"]).execute()
                tx["items"] = items_res.data or []
                
            return transactions
        except Exception as e:
            print(f"Supabase error getting transactions: {e}")
            return []

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM transactions ORDER BY timestamp DESC")
        tx_rows = cursor.fetchall()
        
        transactions = []
        for tx in tx_rows:
            tx_dict = dict(tx)
            
            # Fetch items for this transaction
            cursor.execute("SELECT * FROM transaction_items WHERE transaction_id = ?", (tx_dict["id"],))
            item_rows = cursor.fetchall()
            tx_dict["items"] = [dict(item) for item in item_rows]
            
            transactions.append(tx_dict)
            
        return transactions
    except Exception as e:
        print(f"Database error getting transactions: {e}")
        return []
    finally:
        if not USE_SUPABASE:
            conn.close()

def get_financial_summary():
    if USE_SUPABASE:
        try:
            # Fetch revenue
            tx_res = supabase.table("transactions").select("subtotal").execute()
            revenue = sum(row["subtotal"] for row in tx_res.data) if tx_res.data else 0.0
            
            # Fetch cost
            items_res = supabase.table("transaction_items").select("qty, cost_price").execute()
            total_cost = sum(row["qty"] * row["cost_price"] for row in items_res.data) if items_res.data else 0.0
            
            profit = revenue - total_cost
            
            # Count low stock
            low_stock_res = supabase.table("products").select("id", count="exact").lt("stock", 15.0).execute()
            low_stock_count = low_stock_res.count if low_stock_res.count is not None else 0
            
            return {
                "revenue": round(revenue, 2),
                "cost": round(total_cost, 2),
                "profit": round(profit, 2),
                "low_stock_count": low_stock_count
            }
        except Exception as e:
            print(f"Supabase error getting financial summary: {e}")
            return {
                "revenue": 0.0,
                "cost": 0.0,
                "profit": 0.0,
                "low_stock_count": 0
            }

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Total Revenue (Sum of transaction subtotals)
        cursor.execute("SELECT SUM(subtotal) FROM transactions")
        revenue_row = cursor.fetchone()
        revenue = revenue_row[0] if (revenue_row and revenue_row[0]) else 0.0
        
        # 2. Total Cost of Goods Sold (COGS)
        cursor.execute("SELECT SUM(qty * cost_price) FROM transaction_items")
        cost_row = cursor.fetchone()
        total_cost = cost_row[0] if (cost_row and cost_row[0]) else 0.0
        
        # 3. Net Profit
        profit = revenue - total_cost
        
        # 4. Count of low stock items (< 15 units/kgs)
        cursor.execute("SELECT COUNT(*) FROM products WHERE stock < 15.0")
        low_stock_row = cursor.fetchone()
        low_stock_count = low_stock_row[0] if low_stock_row else 0
        
        return {
            "revenue": round(revenue, 2),
            "cost": round(total_cost, 2),
            "profit": round(profit, 2),
            "low_stock_count": low_stock_count
        }
    except Exception as e:
        print(f"Database error computing financial summary: {e}")
        return {
            "revenue": 0.0,
            "cost": 0.0,
            "profit": 0.0,
            "low_stock_count": 0
        }
    finally:
        if not USE_SUPABASE:
            conn.close()
