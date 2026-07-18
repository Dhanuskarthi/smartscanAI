import os
from PIL import Image, ImageDraw, ImageFont

# Get test receipts directory inside frontend so they can be served statically
RECEIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "test_receipts")
os.makedirs(RECEIPTS_DIR, exist_ok=True)

RECEIPTS_TEXTS = {
    "organic_fresh.png": [
        "   ORGANIC FRESH MARKET",
        "     123 HEALTHY WAY",
        "      (555) 019-2831",
        "",
        "DATE: 07/18/2026   TIME: 14:32",
        "CASHIER: SARAH      ST#: 04",
        "--------------------------------",
        "ORGANIC BANANA (1.5 kg)   Rs. 90.00",
        "HONEYCRISP APPLE          Rs. 180.00",
        "WHOLE MILK 1L             Rs. 60.00",
        "SLICED WHITE BREAD        Rs. 45.00",
        "HONEY NUT O'S CEREAL      Rs. 160.00",
        "--------------------------------",
        "SUBTOTAL                  Rs. 535.00",
        "TAX 8%                    Rs. 42.80",
        "TOTAL                     Rs. 577.80",
        "--------------------------------",
        "CARD: ************4321    Rs. 577.80",
        "        THANK YOU!",
        "      PLEASE VISIT US",
        "   WWW.ORGANICFRESH.COM"
    ],
    "quick_mart.png": [
        "      QUICK MART #8421",
        "      456 EXPRESS BLVD",
        "      TEL: 555-987-6543",
        "",
        "18-07-2026  18:15:02  REG 02",
        "--------------------------------",
        "SPRING WATER BOTTLE       Rs. 20.00",
        "CHOCOLATE CHIP COOKIES    Rs. 40.00",
        "ARTISAN COFFEE CUP        Rs. 90.00",
        "--------------------------------",
        "SUBTOTAL                  Rs. 150.00",
        "TAX                       Rs. 7.50",
        "TOTAL                     Rs. 157.50",
        "--------------------------------",
        "CASH                      Rs. 200.00",
        "CHANGE                    Rs. 42.50",
        "    HAVE A GREAT DAY!"
    ]
}

def generate_receipt_image(filename, text_lines):
    # Dimensions of the receipt image
    width, height = 450, 600
    
    # Create white canvas
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    
    # Draw simple border
    draw.rectangle([10, 10, width-10, height-10], outline="#E0E0E0", width=2)
    
    # We will try to use a default monospaced font, falling back to basic font
    font = None
    try:
        # Try finding standard system monospaced fonts on Windows
        font_paths = [
            "lucon.ttf",       # Lucida Console
            "cour.ttf",        # Courier New
            "consola.ttf"      # Consolas
        ]
        for fp in font_paths:
            try:
                font = ImageFont.truetype(fp, 16)
                break
            except:
                continue
    except:
        pass
        
    # If font is not found, pillow will fall back to default
    y_text = 30
    for line in text_lines:
        if font:
            draw.text((35, y_text), line, font=font, fill="black")
            y_text += 24
        else:
            # Basic fallback drawing (default font is very small, so we add more spacing)
            draw.text((35, y_text), line, fill="black")
            y_text += 20
            
    # Save the receipt image
    file_path = os.path.join(RECEIPTS_DIR, filename)
    img.save(file_path)
    print(f"Generated mock receipt image: {file_path}")

def main():
    print("Generating sample receipts...")
    for filename, text_lines in RECEIPTS_TEXTS.items():
        generate_receipt_image(filename, text_lines)
    print("All sample receipts generated successfully.")

if __name__ == "__main__":
    main()
