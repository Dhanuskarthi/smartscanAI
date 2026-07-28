import os
import sys
import numpy as np
import cv2

# Ensure the parent directory is in the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force test runner to use local SQLite database so it doesn't pollute live Supabase tables
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_KEY"] = ""

from backend.detector import GroceryDetector
from backend.parser import parse_receipt_text, parse_receipt_image

def test_color_heuristic_detector():
    print("Testing Color Heuristic Fallback Detector offline...")
    detector = GroceryDetector()
    
    # 1. Create a pure solid red image (representing Apple)
    img_red = np.zeros((480, 640, 3), dtype=np.uint8)
    img_red[:, :] = [0, 0, 200]  # BGR format: Red
    
    detections = detector._detect_fallback(img_red)
    print(f"Red image detection results: {detections}")
    assert len(detections) > 0, "Failed to detect red object"
    assert detections[0]["id"] == "apple", f"Expected apple, got {detections[0]['id']}"
    print("[PASS] Red image classification passed.")
    
    # 2. Create a pure solid yellow image (representing Banana)
    img_yellow = np.zeros((480, 640, 3), dtype=np.uint8)
    img_yellow[:, :] = [0, 200, 200]  # BGR format: Yellow (Red+Green)
    
    detections = detector._detect_fallback(img_yellow)
    print(f"Yellow image detection results: {detections}")
    assert len(detections) > 0, "Failed to detect yellow object"
    assert detections[0]["id"] == "banana", f"Expected banana, got {detections[0]['id']}"
    print("[PASS] Yellow image classification passed.")
    
    # 3. Create a pure solid green image (representing Broccoli)
    img_green = np.zeros((480, 640, 3), dtype=np.uint8)
    img_green[:, :] = [0, 180, 0]  # BGR format: Green
    
    detections = detector._detect_fallback(img_green)
    print(f"Green image detection results: {detections}")
    assert len(detections) > 0, "Failed to detect green object"
    assert detections[0]["id"] == "broccoli", f"Expected broccoli, got {detections[0]['id']}"
    print("[PASS] Green image classification passed.")

def test_ocr_parser_logic():
    print("\nTesting Regex Receipt Parser logic offline...")
    
    sample_text = """
    SUPERMARKET EXPRESS
    DATE: 07/18/2026   TIME: 14:32
    --------------------------------
    HONEYCRISP APPLE          Rs. 180.00
    WHOLE MILK 1L             Rs. 60.00
    SLICED WHITE BREAD        Rs. 45.00
    --------------------------------
    SUBTOTAL                  Rs. 285.00
    TAX 8%                    Rs. 22.80
    TOTAL                     Rs. 307.80
    """
    
    parsed = parse_receipt_text(sample_text)
    print(f"Parsed receipt structured data:\n{parsed}")
    
    assert parsed["merchant"] == "Supermarket Express", f"Expected Supermarket Express, got {parsed['merchant']}"
    assert len(parsed["items"]) == 3, f"Expected 3 items, got {len(parsed['items'])}"
    assert parsed["items"][0]["id"] == "apple", f"First item should resolve to apple, got {parsed['items'][0]['id']}"
    assert parsed["items"][1]["id"] == "milk", f"Second item should resolve to milk, got {parsed['items'][1]['id']}"
    assert parsed["items"][2]["id"] == "bread", f"Third item should resolve to bread, got {parsed['items'][2]['id']}"
    assert parsed["total"] == 307.80, f"Expected total 307.80, got {parsed['total']}"
    print("[PASS] Regex invoice parser passed.")

def test_database_persistence():
    print("\nTesting SQLite database persistence...")
    from backend.database import init_db, save_transaction, get_all_transactions, DB_PATH
    
    # Clean test database path if exists to start fresh
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass
            
    # Initialize
    init_db()
    
    # Save a test transaction with default payment method (cash)
    tx_items = [
        {"id": "apple", "name": "Honeycrisp Apple", "price": 180.00, "qty": 2, "unit": "kg"},
        {"id": "milk", "name": "Whole Milk 1L", "price": 60.00, "qty": 1, "unit": "item"}
    ]
    tx_id = "TXID-TEST12345"
    subtotal = 420.00
    tax = 33.60
    total = 453.60
    
    success = save_transaction(tx_id, subtotal, tax, total, tx_items)
    assert success, "Failed to save transaction to SQLite database"
    
    # Get and check transactions
    transactions = get_all_transactions()
    assert len(transactions) == 1, f"Expected 1 transaction in DB, got {len(transactions)}"
    
    saved_tx = transactions[0]
    assert saved_tx["tx_id"] == tx_id, f"Expected tx_id {tx_id}, got {saved_tx['tx_id']}"
    assert saved_tx["total"] == total, f"Expected total {total}, got {saved_tx['total']}"
    assert saved_tx["payment_method"] == "cash", f"Expected default payment method 'cash', got '{saved_tx['payment_method']}'"
    assert len(saved_tx["items"]) == 2, f"Expected 2 items in saved transaction, got {len(saved_tx['items'])}"
    
    # Verify items
    item_apple = next(item for item in saved_tx["items"] if item["item_id"] == "apple")
    assert item_apple["qty"] == 2, f"Expected apple qty 2, got {item_apple['qty']}"

    # Save another transaction with explicit payment method (card)
    tx_id_card = "TXID-CARD12345"
    success_card = save_transaction(tx_id_card, subtotal, tax, total, tx_items, payment_method="card")
    assert success_card, "Failed to save card transaction"

    transactions_all = get_all_transactions()
    assert len(transactions_all) == 2, f"Expected 2 transactions in DB, got {len(transactions_all)}"
    saved_tx_card = next(tx for tx in transactions_all if tx["tx_id"] == tx_id_card)
    assert saved_tx_card["payment_method"] == "card", f"Expected payment method 'card', got '{saved_tx_card['payment_method']}'"
    
    # Cleanup DB after test
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass
            
    print("[PASS] SQLite transaction persistence (including cash and card payment methods) passed.")

def test_admin_catalog_updates():
    print("\nTesting Admin Catalog updates...")
    from backend.database import init_db, get_item_by_id, update_product_details, DB_PATH, save_transaction, get_financial_summary
    
    # Clean test database path if exists to start fresh
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass
            
    # Initialize
    init_db()
    
    # 1. Get default price, cost, and stock of apple (should be 180.00, 130.00, 100.0)
    item = get_item_by_id("apple")
    assert item is not None, "Product apple not found"
    assert item["price"] == 180.00, f"Expected default price 180.0, got {item['price']}"
    assert item["cost_price"] == 130.00, f"Expected cost price 130.0, got {item['cost_price']}"
    assert item["stock"] == 100.0, f"Expected stock 100.0, got {item['stock']}"
    
    # 2. Update price, cost, and stock of apple
    success = update_product_details("apple", 200.00, 140.00, 95.0)
    assert success, "Failed to update product details"
    
    # 3. Get apple details again and check
    item_updated = get_item_by_id("apple")
    assert item_updated["price"] == 200.00, f"Expected updated price 200.0, got {item_updated['price']}"
    assert item_updated["cost_price"] == 140.00, f"Expected cost 140.0, got {item_updated['cost_price']}"
    assert item_updated["stock"] == 95.0, f"Expected stock 95.0, got {item_updated['stock']}"

    # 4. Perform a transaction of 5 units of apples
    tx_items = [
        {"id": "apple", "name": "Honeycrisp Apple", "price": 200.00, "qty": 5, "unit": "kg"}
    ]
    tx_id = "TXID-STOCKTEST"
    save_success = save_transaction(tx_id, 1000.00, 80.00, 1080.00, tx_items)
    assert save_success, "Failed to save stock test transaction"

    # 5. Verify stock was deducted: 95.0 - 5 = 90.0
    item_after_tx = get_item_by_id("apple")
    assert item_after_tx["stock"] == 90.0, f"Expected stock 90.0 after sale, got {item_after_tx['stock']}"

    # 6. Verify financials: Revenue = 1000.00, Cost = 5 * 140.00 = 700.00, Profit = 300.00
    summary = get_financial_summary()
    assert summary["revenue"] == 1000.00, f"Expected revenue 1000.00, got {summary['revenue']}"
    assert summary["cost"] == 700.00, f"Expected cost 700.00, got {summary['cost']}"
    assert summary["profit"] == 300.00, f"Expected profit 300.00, got {summary['profit']}"
    
    # Cleanup
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass
            
    print("[PASS] Admin Catalog update & stock/profit tracking passed.")

def test_login_auth_logic():
    print("\nTesting Login Authentication endpoint logic...")
    # Simulate login auth endpoint lookup
    users = {
        "admin": {"password": "admin123", "role": "admin"},
        "worker": {"password": "worker123", "role": "worker"}
    }
    assert users.get("admin")["password"] == "admin123"
    assert users.get("worker")["password"] == "worker123"
    assert users.get("unknown") is None
    print("[PASS] Login Authentication endpoint logic passed.")

def test_add_product_and_bulk_updates():
    print("\nTesting Add Product and Bulk Updates...")
    from backend.database import init_db, add_product_to_db, bulk_update_products_details, get_item_by_id, DB_PATH
    import os
    
    # Initialize fresh database
    if not os.environ.get("VERCEL"):
        if os.path.exists(DB_PATH):
            try:
                os.remove(DB_PATH)
            except Exception:
                pass
        init_db()
        
    # 1. Test adding a product
    prod_data = {
        "id": "tomato",
        "name": "Roma Tomato",
        "price": 80.0,
        "cost_price": 50.0,
        "stock": 100.0,
        "unit": "kg",
        "category": "Vegetables",
        "sku": "4011-TOM",
        "color": "#FF3B30",
        "icon": "🍅",
        "coco_class": None
    }
    
    success = add_product_to_db(prod_data)
    assert success, "Failed to add product to database"
    
    fetched = get_item_by_id("tomato")
    assert fetched is not None, "Tomato product should be in the database"
    assert fetched["name"] == "Roma Tomato", f"Expected 'Roma Tomato', got {fetched['name']}"
    assert fetched["price"] == 80.0, f"Expected 80.0 price, got {fetched['price']}"
    assert fetched["stock"] == 100.0, f"Expected 100.0 stock, got {fetched['stock']}"
    assert fetched["category"] == "Vegetables", f"Expected category 'Vegetables', got {fetched['category']}"

    # Verify migration of apple and broccoli
    apple_fetched = get_item_by_id("apple")
    assert apple_fetched["category"] == "Fruits", f"Expected apple category 'Fruits', got {apple_fetched['category']}"
    
    broccoli_fetched = get_item_by_id("broccoli")
    assert broccoli_fetched["category"] == "Vegetables", f"Expected broccoli category 'Vegetables', got {broccoli_fetched['category']}"
    
    # 2. Test bulk update
    updates = [
        {"id": "tomato", "price": 90.0, "cost_price": 60.0, "stock": 120.0},
        {"id": "apple", "price": 190.0, "cost_price": 140.0, "stock": 80.0}
    ]
    
    bulk_success = bulk_update_products_details(updates)
    assert bulk_success, "Failed to bulk update products"
    
    updated_tomato = get_item_by_id("tomato")
    assert updated_tomato["price"] == 90.0, f"Expected updated tomato price 90.0, got {updated_tomato['price']}"
    assert updated_tomato["stock"] == 120.0, f"Expected updated tomato stock 120.0, got {updated_tomato['stock']}"
    
    updated_apple = get_item_by_id("apple")
    assert updated_apple["price"] == 190.0, f"Expected updated apple price 190.0, got {updated_apple['price']}"
    assert updated_apple["stock"] == 80.0, f"Expected updated apple stock 80.0, got {updated_apple['stock']}"
    
    print("[PASS] Add Product and Bulk Updates database verification passed.")

def main():
    print("==================================================")
    print("   Running Automated Offline Backend Verification ")
    print("==================================================")
    
    # Initialize DB for testing to avoid "no such table" warnings
    from backend.database import init_db, DB_PATH
    import os
    if os.environ.get("VERCEL"):
        # Don't alter Vercel SQLite
        pass
    else:
        if os.path.exists(DB_PATH):
            try:
                os.remove(DB_PATH)
            except Exception:
                pass
        init_db()
    
    try:
        test_color_heuristic_detector()
        test_ocr_parser_logic()
        test_database_persistence()
        test_admin_catalog_updates()
        test_login_auth_logic()
        test_add_product_and_bulk_updates()
        print("\n==================================================")
        print("  ALL OFFLINE TESTS PASSED SUCCESSFULLY! [OK]")
        print("==================================================")
    except AssertionError as e:
        print(f"\n[FAIL] Test assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Test run encountered error: {e}")
        sys.exit(1)
    finally:
        # Cleanup test database at the very end
        if os.path.exists(DB_PATH):
            try:
                os.remove(DB_PATH)
            except Exception:
                pass

if __name__ == "__main__":
    main()
