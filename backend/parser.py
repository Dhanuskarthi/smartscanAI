import re
import os
import logging
from PIL import Image
from backend.database import get_item_by_sku, get_item_by_id, get_all_items

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parser")

# Set pytesseract path if it exists in common Windows installation paths
import pytesseract
TESSERACT_CMD_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\dhanu\AppData\Local\Tesseract-OCR\tesseract.exe",
]
for candidate in TESSERACT_CMD_CANDIDATES:
    if os.path.exists(candidate):
        pytesseract.pytesseract.tesseract_cmd = candidate
        logger.info(f"Tesseract OCR executable found at: {candidate}")
        break

# Predefined mock receipts with raw text and expected outputs
# This ensures that even if Tesseract is not installed, the user can upload these mock files and get a fully working OCR experience!
MOCK_RECEIPTS = {
    "organic_fresh.png": {
        "text": """
      ORGANIC FRESH MARKET
       123 HEALTHY WAY
        (555) 019-2831
        
DATE: 07/18/2026   TIME: 14:32
CASHIER: SARAH      ST#: 04
--------------------------------
ORGANIC BANANA (1.5 lb)   $0.89
HONEYCRISP APPLE          $1.99
WHOLE MILK 1GAL           $3.49
SLICED SOURDOUGH          $2.99
HONEY NUT O'S CEREAL      $4.59
--------------------------------
SUBTOTAL                  $13.95
TAX 8%                    $1.12
TOTAL                     $15.07
--------------------------------
CARD: ************4321    $15.07
          THANK YOU!
        PLEASE VISIT US
     WWW.ORGANICFRESH.COM
""",
        "parsed": {
            "merchant": "Organic Fresh Market",
            "date": "07/18/2026 14:32",
            "items": [
                {"name": "Organic Banana", "qty": 1, "price": 0.89, "id": "banana"},
                {"name": "Honeycrisp Apple", "qty": 1, "price": 1.99, "id": "apple"},
                {"name": "Whole Milk 1Gal", "qty": 1, "price": 3.49, "id": "milk"},
                {"name": "Sliced Sourdough", "qty": 1, "price": 2.99, "id": "bread"},
                {"name": "Honey Nut O's Cereal", "qty": 1, "price": 4.59, "id": "cereal"}
            ],
            "subtotal": 13.95,
            "tax": 1.12,
            "total": 15.07,
            "is_simulated": True
        }
    },
    "quick_mart.png": {
        "text": """
        QUICK MART #8421
        456 EXPRESS BLVD
        TEL: 555-987-6543
        
18-07-2026  18:15:02  REG 02
--------------------------------
SPRING WATER BOTTLE       $0.99
CHOCOLATE CHIP COOKIES    $3.89
ARTISAN COFFEE CUP        $2.49
--------------------------------
SUBTOTAL                  $7.37
TAX                       $0.59
TOTAL                     $7.96
--------------------------------
CASH                      $10.00
CHANGE                    $2.04
      HAVE A GREAT DAY!
""",
        "parsed": {
            "merchant": "Quick Mart #8421",
            "date": "18-07-2026 18:15:02",
            "items": [
                {"name": "Spring Water Bottle", "qty": 1, "price": 0.99, "id": "bottle"},
                {"name": "Chocolate Chip Cookies", "qty": 1, "price": 3.89, "id": "cookies"},
                {"name": "Artisan Coffee Cup", "qty": 1, "price": 2.49, "id": "cup"}
            ],
            "subtotal": 7.37,
            "tax": 0.59,
            "total": 7.96,
            "is_simulated": True
        }
    }
}

def clean_ocr_text(text):
    """Clean up OCR artifacts like double spacing, random chars."""
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join([line for line in lines if line])

def parse_receipt_text(text):
    """
    Parses raw receipt text using regex.
    """
    text = text.upper()
    lines = text.split("\n")
    
    merchant = "Unknown Grocery Store"
    date_str = "Unknown Date"
    items = []
    subtotal = 0.0
    tax = 0.0
    total = 0.0
    
    # 1. Parse Merchant (Usually the first non-empty lines)
    for line in lines[:3]:
        cleaned = re.sub(r'[^A-Z0-9\s#\-]', '', line).strip()
        if len(cleaned) > 5 and not any(k in cleaned for k in ["DATE", "TIME", "WELCOME", "TEL", "PHONE", "CASHIER"]):
            merchant = cleaned.title()
            break

    # 2. Parse Date/Time
    date_match = re.search(r'(\d{2}[/\-]\d{2}[/\-]\d{4}|\d{4}[/\-]\d{2}[/\-]\d{2})', text)
    if date_match:
        date_str = date_match.group(1)
        time_match = re.search(r'(\d{2}:\d{2}(:\d{2})?)', text)
        if time_match:
            date_str += " " + time_match.group(1)

    # 3. Parse Subtotal, Tax, Total
    subtotal_match = re.search(r'SUBTOTAL\s+\$?(\d+\.\d{2})', text)
    if subtotal_match:
        subtotal = float(subtotal_match.group(1))
        
    tax_match = re.search(r'(?:TAX|VAT).*?\$?(\d+\.\d{2})', text)
    if tax_match:
        tax = float(tax_match.group(1))

    total_match = re.search(r'\bTOTAL\s+\$?(\d+\.\d{2})', text)
    if total_match:
        total = float(total_match.group(1))

    # 4. Parse Items
    # Look for patterns: ITEM NAME followed by spaces and a price (e.g. MILK  3.49)
    # Exclude receipt sections like subtotal/tax/totals
    skip_keywords = ["SUBTOTAL", "TAX", "TOTAL", "CASH", "CHANGE", "CARD", "VISA", "MC", "ST#", "STREET", "TEL", "PHONE", "WELCOME", "STORES"]
    
    for line in lines:
        if any(keyword in line for keyword in skip_keywords):
            continue
        
        # Pattern matches: ITEM_NAME  [maybe QTY]  [maybe $] PRICE
        # Example: HONEYCRISP APPLE $1.99 or MILK 1GAL 3.49
        item_match = re.search(r'^([A-Z0-9\s\-&/\(\)\.]+?)\s+\$?(\d+\.\d{2})', line)
        if item_match:
            item_name = item_match.group(1).strip()
            price = float(item_match.group(2))
            
            # Filter out very short names or dates/times
            if len(item_name) < 3 or re.search(r'\d{2}:\d{2}', item_name):
                continue
                
            # Attempt to resolve the item to our database
            matched_id = None
            
            # Check by matching keywords in database
            item_name_lower = item_name.lower()
            for db_item in get_all_items():
                # Direct check or substring match
                if db_item["id"] in item_name_lower or db_item["name"].lower() in item_name_lower or item_name_lower in db_item["name"].lower():
                    matched_id = db_item["id"]
                    break
                    
            items.append({
                "name": item_name.title(),
                "qty": 1,
                "price": price,
                "id": matched_id
            })

    # If subtotal or total was not found, calculate subtotal from items
    if subtotal == 0.0 and items:
        subtotal = sum(i["price"] for i in items)
    if total == 0.0:
        total = subtotal + tax

    return {
        "merchant": merchant,
        "date": date_str,
        "items": items,
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
        "is_simulated": False
    }

def parse_receipt_image(file_path):
    """
    Given a receipt image path, attempts OCR via pytesseract.
    If OCR fails or tesseract is not available:
    - Checks if the file name matches a predefined mock receipt.
    - Otherwise, returns a clean mock receipt with a warning.
    """
    file_name = os.path.basename(file_path).lower()
    
    # Check if this is one of our predefined mocks (by file name matching)
    for mock_name, data in MOCK_RECEIPTS.items():
        if mock_name in file_name:
            logger.info(f"Serving predefined mock data for {file_name}")
            return {
                "text": data["text"],
                "parsed": data["parsed"]
            }

    # Try running Tesseract
    raw_text = ""
    try:
        image = Image.open(file_path)
        # Convert image to grayscale for better OCR accuracy
        gray_image = image.convert('L')
        raw_text = pytesseract.image_to_string(gray_image)
        logger.info("Successfully ran Tesseract OCR on the image.")
    except Exception as e:
        logger.warning(f"Tesseract OCR failed or not installed: {e}")
        # Fall back to a default mock receipt if it's not a known file
        # We'll use the Organic Fresh mock receipt as default fallback
        default_mock = MOCK_RECEIPTS["organic_fresh.png"]
        return {
            "text": default_mock["text"],
            "parsed": default_mock["parsed"],
            "warning": "Tesseract OCR binary not found in PATH or failed to parse. Displaying simulated result."
        }

    if not raw_text.strip():
        # Empty text fallback
        default_mock = MOCK_RECEIPTS["organic_fresh.png"]
        return {
            "text": default_mock["text"],
            "parsed": default_mock["parsed"],
            "warning": "OCR extracted no text. Displaying simulated result."
        }

    cleaned_text = clean_ocr_text(raw_text)
    parsed_data = parse_receipt_text(cleaned_text)
    
    return {
        "text": cleaned_text,
        "parsed": parsed_data
    }
