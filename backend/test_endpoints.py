import os
import sys
import numpy as np
import cv2

# Ensure the parent directory is in the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
    
    # Save a test transaction
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
    assert len(saved_tx["items"]) == 2, f"Expected 2 items in saved transaction, got {len(saved_tx['items'])}"
    
    # Verify items
    item_apple = next(item for item in saved_tx["items"] if item["item_id"] == "apple")
    assert item_apple["qty"] == 2, f"Expected apple qty 2, got {item_apple['qty']}"
    
    # Cleanup DB after test
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass
            
    print("[PASS] SQLite transaction persistence passed.")

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

def main():
    print("==================================================")
    print("   Running Automated Offline Backend Verification ")
    print("==================================================")
    
    # Initialize DB for testing to avoid "no such table" warnings
    from backend.database import init_db, DB_PATH
    import os
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
