# Grocery Item Database and Catalog
import os
import sqlite3

GROCERY_ITEMS = {
    "apple": {
        "id": "apple",
        "name": "Honeycrisp Apple",
        "price": 1.99,
        "unit": "lb",
        "category": "Produce",
        "sku": "4011-APP",
        "color": "#FF3B30",
        "icon": "🍎",
        "coco_class": "apple"
    },
    "banana": {
        "id": "banana",
        "name": "Organic Banana",
        "price": 0.59,
        "unit": "lb",
        "category": "Produce",
        "sku": "4011-BAN",
        "color": "#FFCC00",
        "icon": "🍌",
        "coco_class": "banana"
    },
    "orange": {
        "id": "orange",
        "name": "Navel Orange",
        "price": 1.29,
        "unit": "lb",
        "category": "Produce",
        "sku": "3107-ORN",
        "color": "#FF9500",
        "icon": "🍊",
        "coco_class": "orange"
    },
    "broccoli": {
        "id": "broccoli",
        "name": "Crown Broccoli",
        "price": 2.49,
        "unit": "lb",
        "category": "Produce",
        "sku": "4060-BRC",
        "color": "#34C759",
        "icon": "🥦",
        "coco_class": "broccoli"
    },
    "carrot": {
        "id": "carrot",
        "name": "Organic Carrots",
        "price": 1.89,
        "unit": "lb",
        "category": "Produce",
        "sku": "4094-CRT",
        "color": "#FF9500",
        "icon": "🥕",
        "coco_class": "carrot"
    },
    "bottle": {
        "id": "bottle",
        "name": "Spring Water Bottle",
        "price": 0.99,
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
        "price": 2.49,
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
        "price": 6.99,
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
        "name": "Whole Milk 1Gal",
        "price": 3.49,
        "unit": "item",
        "category": "Dairy",
        "sku": "078742351866",
        "color": "#E5E5EA",
        "icon": "🥛"
    },
    "bread": {
        "id": "bread",
        "name": "Sliced Sourdough",
        "price": 2.99,
        "unit": "item",
        "category": "Bakery",
        "sku": "072250037127",
        "color": "#D1C4E9",
        "icon": "🍞"
    },
    "cereal": {
        "id": "cereal",
        "name": "Honey Nut O's Cereal",
        "price": 4.59,
        "unit": "item",
        "category": "Pantry",
        "sku": "016000123991",
        "color": "#FF8A65",
        "icon": "🥣"
    },
    "cookies": {
        "id": "cookies",
        "name": "Chocolate Chip Cookies",
        "price": 3.89,
        "unit": "item",
        "category": "Bakery",
        "sku": "044000032029",
        "color": "#8D6E63",
        "icon": "🍪"
    }
}

COCO_TO_GROCERY = {item["coco_class"]: item["id"] for item in GROCERY_ITEMS.values() if "coco_class" in item}

def get_item_by_id(item_id):
    return GROCERY_ITEMS.get(item_id)

def get_item_by_coco_class(coco_class):
    item_id = COCO_TO_GROCERY.get(coco_class)
    if item_id:
        return GROCERY_ITEMS.get(item_id)
    return None

def get_item_by_sku(sku):
    sku_clean = sku.strip().upper()
    for item in GROCERY_ITEMS.values():
        if item["sku"] == sku_clean:
            return item
    return None

def get_all_items():
    return list(GROCERY_ITEMS.values())

# SQLite Database for transactions
# Vercel serverless function environment only allows writing to /tmp/
if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/checkout.db"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "checkout.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create transactions table
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
    # Create transaction_items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            qty INTEGER NOT NULL,
            unit TEXT NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES transactions (id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def save_transaction(tx_id, subtotal, tax, total, items):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (tx_id, subtotal, tax, total) VALUES (?, ?, ?, ?)",
            (tx_id, subtotal, tax, total)
        )
        transaction_id = cursor.lastrowid
        
        for item in items:
            cursor.execute(
                "INSERT INTO transaction_items (transaction_id, item_id, name, price, qty, unit) VALUES (?, ?, ?, ?, ?, ?)",
                (transaction_id, item["id"], item["name"], item["price"], item["qty"], item["unit"])
            )
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Database error saving transaction: {e}")
        return False
    finally:
        conn.close()

def get_all_transactions():
    try:
        conn = sqlite3.connect(DB_PATH)
        # return dicts
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
        conn.close()
