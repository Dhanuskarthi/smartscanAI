import os
import urllib.request
import numpy as np
import cv2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("detector")

MODEL_URL = "https://huggingface.co/SpotLab/YOLOv8Detection/resolve/main/yolov8n.onnx"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "yolov8n.onnx")

# COCO Classes mapping to index
# 39: bottle, 41: cup, 45: bowl, 46: banana, 47: apple, 49: orange, 50: broccoli, 51: carrot
COCO_CLASSES = {
    39: "bottle",
    41: "cup",
    45: "bowl",
    46: "banana",
    47: "apple",
    49: "orange",
    50: "broccoli",
    51: "carrot"
}

class GroceryDetector:
    def __init__(self):
        self.session = None
        self.use_fallback = True
        self.downloading = False
        self.attempt_load_model()

    def attempt_load_model(self):
        try:
            import onnxruntime as ort
            
            # Download model if not exists
            if not os.path.exists(MODEL_PATH):
                logger.info("YOLOv8 ONNX model not found. Attempting download...")
                self.download_model()
            
            if os.path.exists(MODEL_PATH):
                # Load ONNX model
                logger.info(f"Loading YOLOv8 model from {MODEL_PATH}...")
                self.session = ort.InferenceSession(MODEL_PATH, providers=['CPUExecutionProvider'])
                self.use_fallback = False
                logger.info("YOLOv8 model loaded successfully using ONNX Runtime.")
            else:
                logger.warning("YOLOv8 model file missing. Running in Fallback/Simulation mode.")
                self.use_fallback = True
        except Exception as e:
            logger.warning(f"Failed to load ONNX Runtime or model: {e}. Running in Fallback/Simulation mode.")
            self.use_fallback = True

    def download_model(self):
        self.downloading = True
        import shutil
        
        candidates = [
            "https://huggingface.co/SpotLab/YOLOv8Detection/resolve/main/yolov8n.onnx",
            "https://huggingface.co/unity/inference-engine-yolo/resolve/main/yolov8n.onnx",
            "https://huggingface.co/Kalray/yolov8/resolve/main/yolov8n.onnx",
            "https://github.com/djl-ai/resources/raw/master/ml-models/object_detection/yolo/yolov8n.onnx"
        ]
        
        success = False
        for url in candidates:
            try:
                logger.info(f"Attempting to download YOLOv8 ONNX model from: {url}")
                req = urllib.request.Request(
                    url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                with urllib.request.urlopen(req, timeout=20) as response:
                    with open(MODEL_PATH, 'wb') as out_file:
                        shutil.copyfileobj(response, out_file)
                logger.info("Model download complete and saved successfully.")
                success = True
                break
            except Exception as e:
                logger.warning(f"Download failed from {url}: {e}")
                
        if not success:
            logger.error("Failed to download YOLOv8 model from all sources. Falling back to simulation.")
        self.downloading = False

    def detect(self, image_np, conf_threshold=0.35, nms_threshold=0.45):
        """
        Runs object detection on the numpy image (BGR format).
        Returns a list of dicts: [{"id": "apple", "box": [x, y, w, h], "confidence": 0.85}]
        """
        if self.use_fallback or self.session is None:
            return self._detect_fallback(image_np)

        try:
            h, w = image_np.shape[:2]
            
            # Prepare image for YOLOv8 (640x640, RGB, scale to 0-1)
            blob = cv2.resize(image_np, (640, 640))
            blob = cv2.cvtColor(blob, cv2.COLOR_BGR2RGB)
            blob = blob.astype(np.float32) / 255.0
            blob = np.transpose(blob, (2, 0, 1))  # HWC to CHW
            blob = np.expand_dims(blob, axis=0)   # CHW to BCHW

            # Run inference
            input_name = self.session.get_inputs()[0].name
            outputs = self.session.run(None, {input_name: blob})
            predictions = np.squeeze(outputs[0])  # Shape: (84, 8400)

            # Post-process detections
            # Transpose to shape (8400, 84)
            predictions = predictions.T
            
            boxes = []
            confidences = []
            class_ids = []

            for pred in predictions:
                # pred contains: x_center, y_center, width, height, class0_conf, class1_conf, ...
                xc, yc, bw, bh = pred[:4]
                classes_scores = pred[4:]
                
                class_id = np.argmax(classes_scores)
                confidence = classes_scores[class_id]
                
                if confidence > conf_threshold and class_id in COCO_CLASSES:
                    # Map 640x640 coords back to original image coords
                    x = int((xc - bw / 2) * w / 640.0)
                    y = int((yc - bh / 2) * h / 640.0)
                    box_w = int(bw * w / 640.0)
                    box_h = int(bh * h / 640.0)
                    
                    boxes.append([x, y, box_w, box_h])
                    confidences.append(float(confidence))
                    class_ids.append(int(class_id))

            # Apply NMS
            indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)
            
            results = []
            if len(indices) > 0:
                # indices can be a flat list or nested
                flat_indices = indices.flatten() if hasattr(indices, 'flatten') else indices
                for idx in flat_indices:
                    coco_class_name = COCO_CLASSES[class_ids[idx]]
                    results.append({
                        "id": coco_class_name,
                        "box": boxes[idx],
                        "confidence": confidences[idx]
                    })
            return results

        except Exception as e:
            logger.error(f"Error in YOLOv8 inference: {e}. Falling back to simulation.")
            return self._detect_fallback(image_np)

    def _detect_fallback(self, image_np):
        """
        Color-based heuristic simulation mode:
        Analyses the center region of the frame to spot a dominant color and simulates detection.
        This provides a fun, responsive interaction when YOLO isn't loaded!
        """
        h, w = image_np.shape[:2]
        
        # Crop center region (where items are placed)
        cy, cx = h // 2, w // 2
        dy, dx = h // 6, w // 6
        center_region = image_np[cy-dy:cy+dy, cx-dx:cx+dx]
        
        if center_region.size == 0:
            return []

        # Convert to RGB and calculate mean color
        center_rgb = cv2.cvtColor(center_region, cv2.COLOR_BGR2RGB)
        mean_color = np.mean(center_rgb, axis=(0, 1))  # [R, G, B]
        r, g, b = mean_color

        detected_id = None
        confidence = 0.90
        
        # Simple color classification rules
        # Red dominant (Apple)
        if r > 130 and g < 110 and b < 110:
            detected_id = "apple"
        # Yellow dominant (Banana)
        elif r > 140 and g > 130 and b < 90:
            detected_id = "banana"
        # Orange dominant (Orange or Carrot)
        elif r > 160 and 90 < g < 150 and b < 80:
            detected_id = "orange"
        # Green dominant (Broccoli)
        elif g > 100 and r < 120 and b < 110:
            detected_id = "broccoli"
        # Blue / Transparent plastic (Water Bottle)
        elif b > 140 and r < 150 and g < 150:
            detected_id = "bottle"
        # White/Gray cup (Cup)
        elif r > 150 and g > 150 and b > 150 and abs(r-g) < 20 and abs(g-b) < 20:
            # Let's say cup if it's white/light
            detected_id = "cup"

        if detected_id:
            # Create a box around the center region
            box_x = int(cx - dx)
            box_y = int(cy - dy)
            box_w = int(dx * 2)
            box_h = int(dy * 2)
            
            return [{
                "id": detected_id,
                "box": [box_x, box_y, box_w, box_h],
                "confidence": confidence,
                "is_simulated": True
            }]
            
        return []
