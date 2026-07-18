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
    HONEYCRISP APPLE          $1.99
    WHOLE MILK 1GAL           $3.49
    SLICED SOURDOUGH          $2.99
    --------------------------------
    SUBTOTAL                  $8.47
    TAX 8%                    $0.68
    TOTAL                     $9.15
    """
    
    parsed = parse_receipt_text(sample_text)
    print(f"Parsed receipt structured data:\n{parsed}")
    
    assert parsed["merchant"] == "Supermarket Express", f"Expected Supermarket Express, got {parsed['merchant']}"
    assert len(parsed["items"]) == 3, f"Expected 3 items, got {len(parsed['items'])}"
    assert parsed["items"][0]["id"] == "apple", f"First item should resolve to apple, got {parsed['items'][0]['id']}"
    assert parsed["items"][1]["id"] == "milk", f"Second item should resolve to milk, got {parsed['items'][1]['id']}"
    assert parsed["items"][2]["id"] == "bread", f"Third item should resolve to bread, got {parsed['items'][2]['id']}"
    assert parsed["total"] == 9.15, f"Expected total 9.15, got {parsed['total']}"
    print("[PASS] Regex invoice parser passed.")

def main():
    print("==================================================")
    print("   Running Automated Offline Backend Verification ")
    print("==================================================")
    try:
        test_color_heuristic_detector()
        test_ocr_parser_logic()
        print("\n==================================================")
        print("  ALL OFFLINE TESTS PASSED SUCCESSFULLY! [OK]")
        print("==================================================")
    except AssertionError as e:
        print(f"\n[FAIL] Test assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Test run encountered error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
