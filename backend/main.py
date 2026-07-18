import os
import shutil
import base64
import numpy as np
import cv2
import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.database import get_item_by_id, get_item_by_coco_class, get_all_items, init_db, save_transaction, get_all_transactions, update_product_price
from backend.detector import GroceryDetector
from backend.parser import parse_receipt_image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="Smart Checkout Counter API")

@app.on_event("startup")
def startup_event():
    logger.info("Initializing database...")
    init_db()

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global detector
detector = GroceryDetector()

class ScanRequest(BaseModel):
    image: str  # Base64 data URL
    simulate: bool = False

class CheckoutItem(BaseModel):
    id: str
    name: str
    price: float
    qty: int
    unit: str

class CheckoutRequest(BaseModel):
    tx_id: str
    subtotal: float
    tax: float
    total: float
    items: list[CheckoutItem]

class UpdatePriceRequest(BaseModel):
    id: str
    price: float

@app.get("/api/items")
def get_items():
    """Retrieve the grocery items database catalog."""
    return get_all_items()

@app.post("/api/admin/update-price")
def update_price(request: UpdatePriceRequest):
    """
    Updates the price of a specific product in the SQLite catalog.
    """
    try:
        success = update_product_price(request.id, request.price)
        if not success:
            raise HTTPException(status_code=404, detail="Product not found or update failed")
        return {"success": True, "id": request.id, "new_price": request.price}
    except Exception as e:
        logger.error(f"Error updating product price: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/checkout")
def checkout_transaction(request: CheckoutRequest):
    """
    Saves a completed checkout transaction to the SQLite database.
    """
    try:
        success = save_transaction(
            tx_id=request.tx_id,
            subtotal=request.subtotal,
            tax=request.tax,
            total=request.total,
            items=[item.dict() for item in request.items]
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save transaction to database")
        return {"success": True, "tx_id": request.tx_id}
    except Exception as e:
        logger.error(f"Error during checkout database write: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transactions")
def get_transactions():
    """
    Retrieves all checkout transactions stored in the SQLite database.
    """
    try:
        transactions = get_all_transactions()
        return transactions
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scan")
def scan_frame(request: ScanRequest):
    """
    Receives a camera frame as a base64 string, runs object detection,
    and returns enriched detections with prices and metadata.
    """
    try:
        # Decode base64 image
        image_data = request.image
        if "," in image_data:
            image_data = image_data.split(",")[1]
        
        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data")

        # Run detection
        if request.simulate:
            # Force simulation detection
            detections = detector._detect_fallback(img)
        else:
            detections = detector.detect(img)

        # Enrich detections with database catalog info
        enriched_detections = []
        for det in detections:
            item_id = det["id"]
            # Look up items in database (using either ID or COCO class name)
            item_info = get_item_by_id(item_id) or get_item_by_coco_class(item_id)
            
            if item_info:
                enriched_detections.append({
                    "id": item_info["id"],
                    "name": item_info["name"],
                    "price": item_info["price"],
                    "unit": item_info["unit"],
                    "category": item_info["category"],
                    "color": item_info["color"],
                    "icon": item_info["icon"],
                    "sku": item_info["sku"],
                    "box": det["box"],
                    "confidence": round(float(det["confidence"]), 2),
                    "is_simulated": det.get("is_simulated", False)
                })
        
        return {
            "success": True,
            "detections": enriched_detections,
            "engine": "Fallback Heuristic Simulator" if (detector.use_fallback or request.simulate) else "YOLOv8-ONNX"
        }
    except Exception as e:
        logger.error(f"Error processing scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/parse-receipt")
async def parse_receipt(file: UploadFile = File(...)):
    """
    Receives an uploaded receipt image, runs OCR (via pytesseract with fallback),
    and structures the items and pricing details.
    """
    # Create temp directory if not exists
    temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_path = os.path.join(temp_dir, file.filename)
    try:
        # Save uploaded file
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Parse receipt
        logger.info(f"Received receipt upload: {file.filename}")
        result = parse_receipt_image(temp_path)
        return result

    except Exception as e:
        logger.error(f"Error parsing receipt: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

# Serve Frontend Static Files
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    logger.info(f"Serving frontend static files from: {frontend_dir}")
else:
    logger.warning(f"Frontend directory not found at {frontend_dir}. API runs without UI serving.")
