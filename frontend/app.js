// Global State
let cart = {};
let databaseItems = [];
let selectedMode = 'camera'; // 'camera', 'simulation', 'upload'
let activeTab = 'cart'; // 'cart', 'ocr'
let scannerInterval = null;
let webcamStream = null;
let currentDetectorEngine = "Heuristic Simulator";
let scanCooldowns = {}; // item_id -> timestamp

// Canvas elements for simulation
let simCanvas = document.getElementById('simulation-canvas');
let simCtx = simCanvas.getContext('2d');
let simulatedObject = null; // { name, emoji, color, x, y, size }

// Initialize Web Audio context for synthesizer beep
let audioCtx = null;
function playBeep(freq = 1000, duration = 0.12) {
    try {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);
        
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    } catch (e) {
        console.warn("Audio beep failed: ", e);
    }
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(amount);
}

// Fetch database items on load
async function fetchItems() {
    try {
        const response = await fetch('/api/items');
        databaseItems = await response.json();
        console.log("Loaded product database:", databaseItems);
    } catch (error) {
        console.error("Failed to fetch product catalog:", error);
    }
}

// Update clock in header
function updateClock() {
    const clockEl = document.getElementById('live-time');
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString();
}
setInterval(updateClock, 1000);

// Tab switching
document.querySelectorAll('.tab-btn').forEach(button => {
    button.addEventListener('click', () => {
        const tab = button.dataset.tab;
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        button.classList.add('active');
        document.getElementById(`tab-${tab}`).classList.add('active');
        activeTab = tab;
        
        if (tab === 'history') {
            fetchTransactions();
        } else if (tab === 'admin') {
            fetchAdminCatalog();
        }
    });
});

// Mode switching
document.querySelectorAll('.mode-btn').forEach(button => {
    button.addEventListener('click', () => {
        const mode = button.dataset.mode;
        document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.viewport-content').forEach(vp => vp.classList.remove('active'));
        
        button.classList.add('active');
        document.getElementById(`viewport-${mode}`).classList.add('active');
        selectedMode = mode;
        
        stopScanner();
        
        if (mode === 'camera') {
            initWebcam();
        } else if (mode === 'simulation') {
            initSimulation();
        } else if (mode === 'upload') {
            initUploadMode();
        }
    });
});

// WEBCAM SCANNER
async function initWebcam() {
    const video = document.getElementById('webcam');
    const placeholder = document.getElementById('camera-placeholder');
    const overlay = document.getElementById('camera-overlay');
    
    // Reset video & stream
    video.srcObject = null;
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
    }
    
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, facingMode: 'environment' }
        });
        video.srcObject = webcamStream;
        placeholder.style.display = 'none';
        
        // Wait for video to metadata load to set overlay dimensions
        video.onloadedmetadata = () => {
            overlay.width = video.videoWidth;
            overlay.height = video.videoHeight;
            startScannerLoop();
        };
    } catch (err) {
        console.error("Camera access denied:", err);
        placeholder.style.display = 'flex';
        placeholder.querySelector('p').textContent = "Camera Access Denied or Unavailable";
    }
}

function startScannerLoop() {
    stopScanner();
    const video = document.getElementById('webcam');
    const overlay = document.getElementById('camera-overlay');
    const ctx = overlay.getContext('2d');
    
    // Offscreen canvas to capture frames
    const captureCanvas = document.createElement('canvas');
    
    scannerInterval = setInterval(async () => {
        if (selectedMode !== 'camera' || video.paused || video.ended) return;
        
        captureCanvas.width = video.videoWidth;
        captureCanvas.height = video.videoHeight;
        const capCtx = captureCanvas.getContext('2d');
        capCtx.drawImage(video, 0, 0, video.videoWidth, video.videoHeight);
        
        const base64Img = captureCanvas.toDataURL('image/jpeg', 0.6);
        const result = await sendScanFrame(base64Img, false);
        
        // Draw detections
        ctx.clearRect(0, 0, overlay.width, overlay.height);
        if (result && result.detections) {
            drawDetections(ctx, result.detections, overlay.width, overlay.height);
            processScannedDetections(result.detections);
        }
        
        if (result && result.engine) {
            updateDetectorEngineBadge(result.engine);
        }
    }, 400); // Scan every 400ms to balance performance
}

// SIMULATION SCANNER
function initSimulation() {
    // Setup canvas dimension
    simCanvas.width = simCanvas.parentElement.clientWidth || 500;
    simCanvas.height = 250;
    
    simulatedObject = null;
    drawSimulationScene();
    startSimulationLoop();
}

function drawSimulationScene() {
    // Draw scanner plate
    simCtx.fillStyle = '#080c14';
    simCtx.fillRect(0, 0, simCanvas.width, simCanvas.height);
    
    // Draw scale plate lines (metallic grid effect)
    simCtx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    simCtx.lineWidth = 2;
    for (let i = 0; i < simCanvas.width; i += 40) {
        simCtx.beginPath();
        simCtx.moveTo(i, 0);
        simCtx.lineTo(i, simCanvas.height);
        simCtx.stroke();
    }
    
    // Draw scanning laser window in the middle
    const sw = 140;
    const sh = 100;
    const sx = (simCanvas.width - sw) / 2;
    const sy = (simCanvas.height - sh) / 2;
    
    simCtx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    simCtx.fillRect(sx, sy, sw, sh);
    simCtx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    simCtx.strokeRect(sx, sy, sw, sh);
    
    // Red laser glowing glass borders
    simCtx.strokeStyle = 'rgba(233, 30, 99, 0.4)';
    simCtx.lineWidth = 1;
    simCtx.strokeRect(sx - 2, sy - 2, sw + 4, sh + 4);
    
    // Draw simulated item
    if (simulatedObject) {
        simCtx.save();
        
        // Draw backing color splash (so the color heuristic logic in the backend works!)
        simCtx.beginPath();
        simCtx.arc(simulatedObject.x, simulatedObject.y, simulatedObject.size / 2, 0, Math.PI * 2);
        simCtx.fillStyle = simulatedObject.color;
        simCtx.fill();
        
        // Draw emoji icon in center
        simCtx.fillStyle = '#ffffff';
        simCtx.font = `${simulatedObject.size * 0.7}px sans-serif`;
        simCtx.textAlign = 'center';
        simCtx.textBaseline = 'middle';
        simCtx.fillText(simulatedObject.emoji, simulatedObject.x, simulatedObject.y);
        
        simCtx.restore();
    }
}

function startSimulationLoop() {
    stopScanner();
    
    scannerInterval = setInterval(async () => {
        if (selectedMode !== 'simulation') return;
        
        // Send simulated scene frame to API
        const base64Img = simCanvas.toDataURL('image/jpeg', 0.6);
        const result = await sendScanFrame(base64Img, true); // Force simulation mode logic
        
        drawSimulationScene();
        
        // Render bounding boxes over simulated item
        if (result && result.detections && result.detections.length > 0) {
            drawDetections(simCtx, result.detections, simCanvas.width, simCanvas.height);
            processScannedDetections(result.detections);
        }
        
        if (result && result.engine) {
            updateDetectorEngineBadge(result.engine);
        }
    }, 500);
}

// Register simulation button listeners
document.querySelectorAll('.sim-item-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const itemType = btn.dataset.item;
        const color = btn.style.getPropertyValue('--color');
        
        let emoji = '🍎';
        let name = 'apple';
        
        if (itemType === 'banana') { emoji = '🍌'; name = 'banana'; }
        else if (itemType === 'orange') { emoji = '🍊'; name = 'orange'; }
        else if (itemType === 'broccoli') { emoji = '🥦'; name = 'broccoli'; }
        else if (itemType === 'bottle') { emoji = '💧'; name = 'bottle'; }
        else if (itemType === 'cup') { emoji = '☕'; name = 'cup'; }
        
        // Set coordinates in center scanner plate
        simulatedObject = {
            name: name,
            emoji: emoji,
            color: color,
            x: simCanvas.width / 2,
            y: simCanvas.height / 2,
            size: 60
        };
        playBeep(440, 0.05); // Place click feedback
        drawSimulationScene();
    });
});

document.getElementById('btn-clear-sim').addEventListener('click', () => {
    simulatedObject = null;
    drawSimulationScene();
});

// UPLOAD MODE
function initUploadMode() {
    const dropzone = document.getElementById('frame-dropzone');
    const input = document.getElementById('frame-file-input');
    const previewWrapper = document.getElementById('frame-preview-wrapper');
    const previewImg = document.getElementById('frame-preview-img');
    
    dropzone.onclick = () => input.click();
    
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (file) handleUploadFrame(file);
    };
    
    // Drag-and-drop
    dropzone.ondragover = (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--secondary)';
    };
    
    dropzone.ondragleave = () => {
        dropzone.style.borderColor = 'rgba(255,255,255,0.12)';
    };
    
    dropzone.ondrop = (e) => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file) handleUploadFrame(file);
    };
}

function handleUploadFrame(file) {
    const reader = new FileReader();
    const dropzone = document.getElementById('frame-dropzone');
    const previewWrapper = document.getElementById('frame-preview-wrapper');
    const previewImg = document.getElementById('frame-preview-img');
    const overlay = document.getElementById('upload-overlay');
    const ctx = overlay.getContext('2d');
    
    reader.onload = function(event) {
        previewImg.src = event.target.result;
        dropzone.style.display = 'none';
        previewWrapper.style.display = 'block';
        
        previewImg.onload = async () => {
            overlay.width = previewImg.clientWidth;
            overlay.height = previewImg.clientHeight;
            
            // Draw on dynamic canvas to convert and size properly
            const canvas = document.createElement('canvas');
            canvas.width = previewImg.naturalWidth;
            canvas.height = previewImg.naturalHeight;
            const tempCtx = canvas.getContext('2d');
            tempCtx.drawImage(previewImg, 0, 0);
            
            const base64Img = canvas.toDataURL('image/jpeg', 0.6);
            
            // Scan uploaded image
            const result = await sendScanFrame(base64Img, false);
            
            ctx.clearRect(0, 0, overlay.width, overlay.height);
            if (result && result.detections) {
                drawDetections(ctx, result.detections, overlay.width, overlay.height);
                processScannedDetections(result.detections);
                
                if (result.detections.length === 0) {
                    document.getElementById('scanner-tip').textContent = "No grocery items detected in frame.";
                }
            }
            if (result && result.engine) {
                updateDetectorEngineBadge(result.engine);
            }
        };
    };
    reader.readAsDataURL(file);
}

document.getElementById('btn-reset-upload').onclick = () => {
    document.getElementById('frame-dropzone').style.display = 'flex';
    document.getElementById('frame-preview-wrapper').style.display = 'none';
    document.getElementById('frame-file-input').value = '';
    const overlay = document.getElementById('upload-overlay');
    overlay.getContext('2d').clearRect(0, 0, overlay.width, overlay.height);
};

// GLOBAL API COMMUNICATORS
async function sendScanFrame(base64Image, simulate) {
    try {
        const response = await fetch('/api/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: base64Image, simulate: simulate })
        });
        return await response.json();
    } catch (e) {
        console.error("Frame scan api error:", e);
        return null;
    }
}

function stopScanner() {
    if (scannerInterval) {
        clearInterval(scannerInterval);
        scannerInterval = null;
    }
}

// Bounding boxes drawer
function drawDetections(ctx, detections, width, height) {
    detections.forEach(det => {
        const [x, y, w, h] = det.box;
        const color = det.color || '#FF3B30';
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.strokeRect(x, y, w, h);
        
        // Box background fill
        ctx.fillStyle = `${color}15`;
        ctx.fillRect(x, y, w, h);
        
        // Draw text label on box top
        ctx.fillStyle = color;
        ctx.font = 'bold 12px Outfit';
        const labelText = `${det.name} (${Math.round(det.confidence * 100)}%)`;
        const textWidth = ctx.measureText(labelText).width;
        
        ctx.fillRect(x - 1, y - 22, textWidth + 12, 22);
        
        ctx.fillStyle = '#ffffff';
        ctx.fillText(labelText, x + 6, y - 6);
    });
}

function updateDetectorEngineBadge(engine) {
    const badge = document.getElementById('detector-badge');
    badge.textContent = `Engine: ${engine}`;
}

// Checkout Scanned Item Processor
function processScannedDetections(detections) {
    const now = Date.now();
    
    detections.forEach(det => {
        const item_id = det.id;
        const confidence = det.confidence;
        
        // Threshold check: allow scanning with >= 60% confidence to handle typical uploads/scans safely
        if (confidence >= 0.60) {
            const lastScan = scanCooldowns[item_id] || 0;
            if (now - lastScan > 2200) {
                // Perform Scan Add!
                scanCooldowns[item_id] = now;
                addToCart(det);
                
                // Scan tip info
                document.getElementById('scanner-tip').textContent = `Scanned successfully: ${det.name}`;
            }
        }
    });
}

// CART MANAGEMENTS
function addToCart(item, quantity = 1) {
    if (cart[item.id]) {
        cart[item.id].qty += quantity;
    } else {
        cart[item.id] = {
            id: item.id,
            name: item.name,
            price: item.price,
            unit: item.unit,
            icon: item.icon,
            sku: item.sku,
            qty: quantity
        };
    }
    
    playBeep(880, 0.1); // High cash register beep
    renderCart();
}

function updateQty(item_id, delta) {
    if (cart[item_id]) {
        cart[item_id].qty += delta;
        if (cart[item_id].qty <= 0) {
            delete cart[item_id];
        }
        playBeep(600, 0.05);
        renderCart();
    }
}

function renderCart() {
    const listEl = document.getElementById('cart-items-list');
    const emptyMsgEl = document.getElementById('empty-cart-msg');
    
    listEl.innerHTML = '';
    const items = Object.values(cart);
    
    if (items.length === 0) {
        listEl.style.display = 'none';
        emptyMsgEl.style.display = 'flex';
        updateCartTotals(0);
        return;
    }
    
    listEl.style.display = 'flex';
    emptyMsgEl.style.display = 'none';
    
    let subtotal = 0;
    
    items.forEach(item => {
        const itemTotal = item.price * item.qty;
        subtotal += itemTotal;
        
        const row = document.createElement('div');
        row.className = 'cart-item';
        row.innerHTML = `
            <div class="item-info-col">
                <div class="item-icon">${item.icon}</div>
                <div class="item-details">
                    <h4>${item.name}</h4>
                    <span>SKU: ${item.sku} | Unit Price: ${formatCurrency(item.price)}/${item.unit}</span>
                </div>
            </div>
            <div class="item-qty-price">
                <div class="qty-counter">
                    <button class="qty-btn" onclick="updateQty('${item.id}', -1)">-</button>
                    <span class="qty-val">${item.qty} ${item.unit}</span>
                    <button class="qty-btn" onclick="updateQty('${item.id}', 1)">+</button>
                </div>
                <span class="item-total-price">${formatCurrency(itemTotal)}</span>
            </div>
        `;
        listEl.appendChild(row);
    });
    
    updateCartTotals(subtotal);
}

function updateCartTotals(subtotal) {
    const tax = subtotal * 0.08;
    const total = subtotal + tax;
    
    document.getElementById('cart-subtotal').textContent = formatCurrency(subtotal);
    document.getElementById('cart-tax').textContent = formatCurrency(tax);
    document.getElementById('cart-total').textContent = formatCurrency(total);
}

// Void Cart buttons
document.getElementById('btn-clear-cart').onclick = () => {
    cart = {};
    renderCart();
    playBeep(300, 0.2); // Void low sound
    document.getElementById('scanner-tip').textContent = "Cart voided. Register cleared.";
};

// OCR RECEIPT BACKUP PARSER
function initOCRMode() {
    const ocrDropzone = document.getElementById('ocr-dropzone');
    const ocrInput = document.getElementById('ocr-file-input');
    
    document.getElementById('btn-select-receipt').onclick = () => ocrInput.click();
    
    ocrInput.onchange = (e) => {
        const file = e.target.files[0];
        if (file) uploadReceipt(file);
    };
    
    ocrDropzone.ondragover = (e) => {
        e.preventDefault();
        ocrDropzone.style.borderColor = 'var(--secondary)';
    };
    ocrDropzone.ondragleave = () => {
        ocrDropzone.style.borderColor = 'rgba(255, 255, 255, 0.12)';
    };
    ocrDropzone.ondrop = (e) => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file) uploadReceipt(file);
    };

    // Quick mock samples
    document.querySelectorAll('.btn-sample').forEach(btn => {
        btn.onclick = async (e) => {
            e.stopPropagation();
            const filename = btn.dataset.sample;
            
            // Try fetching sample receipt image from the test directory
            try {
                showOCRProgress();
                
                // Simulate progressive scanning steps
                updateProgressStep(10, "Fetching mock receipt image...", "Reading sample assets...");
                const response = await fetch(`/test_receipts/${filename}`);
                if (!response.ok) {
                    throw new Error("Local sample file not found, sending direct placeholder requests");
                }
                const blob = await response.blob();
                
                updateProgressStep(30, "Analyzing pixels...", "Reading grayscale matrices...");
                const file = new File([blob], filename, { type: "image/png" });
                
                await executeOCRUpload(file);
            } catch (err) {
                console.warn(err);
                // Direct fallback: if file fetch fails, generate a simulated submit using standard File name
                // The server parser detects the filename and serves mock data directly!
                const file = new File(["mock_data"], filename, { type: "image/png" });
                await executeOCRUpload(file);
            }
        };
    });
}

function showOCRProgress() {
    document.getElementById('ocr-dropzone').style.display = 'none';
    document.getElementById('ocr-processing').style.display = 'flex';
    document.getElementById('ocr-result').style.display = 'none';
}

function updateProgressStep(percentage, title, desc) {
    document.getElementById('ocr-progress-fill').style.width = `${percentage}%`;
    document.getElementById('ocr-step-title').textContent = title;
    document.getElementById('ocr-step-desc').textContent = desc;
}

async function uploadReceipt(file) {
    showOCRProgress();
    updateProgressStep(15, "Uploading receipt invoice...", "Transferring file metadata...");
    await executeOCRUpload(file);
}

// Global cached parsed OCR items to import later
let parsedOCRResult = null;

async function executeOCRUpload(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        updateProgressStep(40, "Running OCR Reader...", "Executing Tesseract line scanning...");
        
        const response = await fetch('/api/parse-receipt', {
            method: 'POST',
            body: formData
        });
        
        updateProgressStep(75, "Structuring syntax tree...", "Extracting itemized keys and pricing...");
        
        const data = await response.json();
        
        updateProgressStep(95, "Completing data frames...", "Rounding float totals...");
        
        setTimeout(() => {
            renderOCRResult(data);
        }, 600);
        
    } catch (e) {
        console.error("Receipt parse error:", e);
        updateProgressStep(100, "Error parsing invoice", "Could not connect to OCR pipeline.");
        setTimeout(() => {
            resetOCRView();
        }, 2000);
    }
}

function renderOCRResult(data) {
    document.getElementById('ocr-processing').style.display = 'none';
    document.getElementById('ocr-result').style.display = 'flex';
    
    // Load text
    document.getElementById('ocr-raw-text').textContent = data.text;
    
    const parsed = data.parsed;
    parsedOCRResult = parsed; // Cache it
    
    document.getElementById('ocr-merchant').textContent = parsed.merchant;
    document.getElementById('ocr-date').textContent = parsed.date;
    
    // Line items table
    const listEl = document.getElementById('ocr-items-list');
    listEl.innerHTML = '';
    
    parsed.items.forEach(item => {
        const row = document.createElement('div');
        row.className = 'ocr-invoice-item';
        row.innerHTML = `
            <span>${item.qty}x ${item.name}</span>
            <span class="ocr-item-price">${formatCurrency(item.price)}</span>
        `;
        listEl.appendChild(row);
    });
    
    document.getElementById('ocr-subtotal').textContent = formatCurrency(parsed.subtotal);
    document.getElementById('ocr-tax').textContent = formatCurrency(parsed.tax);
    document.getElementById('ocr-total').textContent = formatCurrency(parsed.total);
    
    playBeep(980, 0.15); // Completion double beeps
}

document.getElementById('btn-import-ocr').onclick = () => {
    if (!parsedOCRResult || !parsedOCRResult.items) return;
    
    parsedOCRResult.items.forEach(ocrItem => {
        // Resolve target catalog details if matched to local catalog IDs
        // Otherwise create item dynamically
        let itemInfo = databaseItems.find(i => i.id === ocrItem.id);
        
        if (!itemInfo) {
            // Default generic item properties
            itemInfo = {
                id: ocrItem.id || `ocr_${Math.random().toString(36).substr(2, 5)}`,
                name: ocrItem.name,
                price: ocrItem.price,
                unit: 'item',
                icon: '📦',
                sku: 'OCR-IMPORT'
            };
        }
        
        addToCart(itemInfo, ocrItem.qty);
    });
    
    // Return to Cart view
    document.querySelector('[data-tab="cart"]').click();
    document.getElementById('scanner-tip').textContent = "Imported OCR items into register cart.";
};

function resetOCRView() {
    document.getElementById('ocr-dropzone').style.display = 'flex';
    document.getElementById('ocr-processing').style.display = 'none';
    document.getElementById('ocr-result').style.display = 'none';
    document.getElementById('ocr-file-input').value = '';
    parsedOCRResult = null;
}

document.getElementById('btn-reset-ocr').onclick = resetOCRView;

// CHECKOUT ACTIONS & PRINTER ANIMATOR
document.getElementById('btn-checkout').onclick = async () => {
    const items = Object.values(cart);
    if (items.length === 0) {
        alert("Cart is empty! Scan items to checkout.");
        return;
    }
    
    const transactionId = Math.floor(100000 + Math.random() * 900000);
    const txIdStr = `TXID-${transactionId}`;
    const now = new Date();
    
    let subtotal = 0;
    items.forEach(item => {
        subtotal += item.price * item.qty;
    });
    const tax = subtotal * 0.08;
    const total = subtotal + tax;

    // Send payload to SQLite database backend
    try {
        const response = await fetch('/api/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tx_id: txIdStr,
                subtotal: parseFloat(subtotal.toFixed(2)),
                tax: parseFloat(tax.toFixed(2)),
                total: parseFloat(total.toFixed(2)),
                items: items.map(i => ({
                    id: i.id,
                    name: i.name,
                    price: parseFloat(i.price),
                    qty: parseInt(i.qty),
                    unit: i.unit || 'item'
                }))
            })
        });

        if (!response.ok) {
            throw new Error("Failed to write to database on the backend");
        }

        const data = await response.json();
        console.log("Transaction saved successfully:", data);
    } catch (err) {
        console.error("Checkout database save failed:", err);
        alert("Checkout database save failed. Checkout cancelled.");
        return;
    }
    
    playBeep(1200, 0.2); // Beep register close
    
    // Fill paper receipt representation
    const receiptEl = document.getElementById('paper-receipt');
    let itemsRows = '';
    
    items.forEach(item => {
        const rowTotal = item.price * item.qty;
        itemsRows += `
            <div class="r-line">
                <span>${item.qty} ${item.unit} ${item.name.substring(0, 16)}</span>
                <span>${formatCurrency(rowTotal)}</span>
            </div>
        `;
    });
    
    receiptEl.innerHTML = `
        <h4>SMART SCAN REGISTER</h4>
        <div class="r-line"><span>Reg: #04</span><span>TXID: ${transactionId}</span></div>
        <div class="r-line"><span>Date: ${now.toLocaleDateString()}</span><span>Time: ${now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span></div>
        <div class="r-divider"></div>
        ${itemsRows}
        <div class="r-divider"></div>
        <div class="r-line"><span>SUBTOTAL</span><span>${formatCurrency(subtotal)}</span></div>
        <div class="r-line"><span>TAX 8%</span><span>${formatCurrency(tax)}</span></div>
        <div class="r-line" style="font-weight: bold;"><span>TOTAL</span><span>${formatCurrency(total)}</span></div>
        <div class="r-divider"></div>
        <div class="r-line" style="justify-content: center;"><span>PAID VIA SMART WALLET</span></div>
        <div class="r-barcode">|||||||| |||| |||||</div>
        <div class="r-line" style="justify-content: center; font-size: 9px; margin-top: 4px;"><span>* THANK YOU FOR SCANNING *</span></div>
    `;
    
    // Show Modal
    const modal = document.getElementById('checkout-modal');
    modal.classList.add('active');
    
    // Simulate register receipt print ticking noise
    let tickCount = 0;
    const tickInterval = setInterval(() => {
        if (tickCount < 6) {
            playBeep(2000, 0.03); // Quick sharp printer ticks
            tickCount++;
        } else {
            clearInterval(tickInterval);
        }
    }, 200);

    // Refresh history panel quietly in background
    fetchTransactions();
};

document.getElementById('btn-close-modal').onclick = () => {
    document.getElementById('checkout-modal').classList.remove('active');
    // Clear and reset checkout
    cart = {};
    renderCart();
    document.getElementById('scanner-tip').textContent = "Ready to scan next customer.";
};

// SQLite Database History helpers
async function fetchTransactions() {
    const listEl = document.getElementById('history-list');
    const emptyMsgEl = document.getElementById('empty-history-msg');
    
    try {
        const response = await fetch('/api/transactions');
        const transactions = await response.json();
        renderTransactions(transactions);
    } catch (error) {
        console.error("Failed to fetch transactions:", error);
        listEl.style.display = 'none';
        emptyMsgEl.style.display = 'flex';
        emptyMsgEl.querySelector('p').textContent = "Could not load transaction history.";
    }
}

function renderTransactions(transactions) {
    const listEl = document.getElementById('history-list');
    const emptyMsgEl = document.getElementById('empty-history-msg');
    
    listEl.innerHTML = '';
    
    if (!transactions || transactions.length === 0) {
        listEl.style.display = 'none';
        emptyMsgEl.style.display = 'flex';
        return;
    }
    
    listEl.style.display = 'flex';
    emptyMsgEl.style.display = 'none';
    
    transactions.forEach(tx => {
        const itemEl = document.createElement('div');
        itemEl.className = 'history-item';
        
        // Format ISO UTC timestamp to local string
        const txDate = new Date(tx.timestamp + 'Z'); // Add 'Z' so JS Date handles SQLite UTC timestamp correctly
        const timeString = txDate.toLocaleString();
        
        // Create tags for products
        const productsHtml = tx.items.map(item => 
            `<span class="history-product-tag">${item.qty} ${item.unit} ${item.name}</span>`
        ).join('');
        
        itemEl.innerHTML = `
            <div class="history-item-header">
                <span class="history-item-id">${tx.tx_id}</span>
                <span class="history-item-time">${timeString}</span>
            </div>
            <div class="history-item-details">
                <span class="history-item-summary">${tx.items.length} items purchased</span>
                <span class="history-item-total">${formatCurrency(tx.total)}</span>
            </div>
            <div class="history-item-products">
                ${productsHtml}
            </div>
        `;
        listEl.appendChild(itemEl);
    });
}

document.getElementById('btn-refresh-history').onclick = () => {
    playBeep(440, 0.05);
    fetchTransactions();
};

// Admin Panel catalog management
async function fetchAdminCatalog() {
    const listEl = document.getElementById('admin-items-list');
    listEl.innerHTML = '<div style="text-align: center; padding: 20px;"><div class="spinner" style="margin: 0 auto 10px auto;"></div>Loading catalog...</div>';
    
    // Quietly load financial summary
    fetchFinancialSummary();
    
    try {
        const response = await fetch('/api/items');
        const items = await response.json();
        // Keep our global databaseItems cached updated as well!
        databaseItems = items;
        renderAdminCatalog(items);
    } catch (error) {
        console.error("Failed to fetch admin catalog:", error);
        listEl.innerHTML = '<div style="color: var(--accent); text-align: center; padding: 20px;">Could not load product catalog.</div>';
    }
}

async function fetchFinancialSummary() {
    try {
        const response = await fetch('/api/admin/finances');
        const summary = await response.json();
        
        document.getElementById('db-revenue').textContent = formatCurrency(summary.revenue);
        
        const profitEl = document.getElementById('db-profit');
        profitEl.textContent = formatCurrency(summary.profit);
        if (summary.profit >= 0) {
            profitEl.style.color = "var(--primary)";
        } else {
            profitEl.style.color = "var(--accent)";
        }
        
        const stockAlertEl = document.getElementById('db-low-stock');
        stockAlertEl.textContent = summary.low_stock_count;
        if (summary.low_stock_count > 0) {
            stockAlertEl.style.color = "#FF9500";
        } else {
            stockAlertEl.style.color = "";
        }
    } catch (error) {
        console.error("Error fetching financial summary:", error);
    }
}

function renderAdminCatalog(items) {
    const listEl = document.getElementById('admin-items-list');
    listEl.innerHTML = '';
    
    if (!items || items.length === 0) {
        listEl.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">No products found in database.</div>';
        return;
    }
    
    items.forEach(item => {
        const isLow = item.stock < 15.0;
        const stockText = isLow ? `Low Stock (${item.stock} ${item.unit})` : `In Stock (${item.stock} ${item.unit})`;
        const stockClass = isLow ? 'low-stock' : 'in-stock';
        
        const row = document.createElement('div');
        row.className = 'admin-product-row';
        row.innerHTML = `
            <div class="admin-product-info">
                <div class="admin-product-icon">${item.icon}</div>
                <div class="admin-product-details">
                    <h4>${item.name}</h4>
                    <span>SKU: ${item.sku} | Unit: ${item.unit} | Category: ${item.category}</span>
                    <div class="admin-product-meta">
                        <span class="stock-tag ${stockClass}">${stockText}</span>
                    </div>
                </div>
            </div>
            <div class="admin-price-update-form" data-id="${item.id}">
                <div class="admin-input-group">
                    <span class="admin-input-label">Cost</span>
                    <div class="admin-price-input-wrapper">
                        <span class="admin-currency-prefix">₹</span>
                        <input type="number" class="admin-price-input admin-cost-input-field" step="0.01" min="0" value="${(item.cost_price || 0).toFixed(2)}">
                    </div>
                </div>
                <div class="admin-input-group">
                    <span class="admin-input-label">Price</span>
                    <div class="admin-price-input-wrapper">
                        <span class="admin-currency-prefix">₹</span>
                        <input type="number" class="admin-price-input admin-selling-input-field" step="0.01" min="0" value="${item.price.toFixed(2)}">
                    </div>
                </div>
                <div class="admin-input-group">
                    <span class="admin-input-label">Stock (${item.unit})</span>
                    <input type="number" class="admin-stock-input admin-stock-input-field" step="0.1" min="0" value="${item.stock}">
                </div>
                <button class="btn btn-primary admin-save-btn" onclick="saveProductDetails('${item.id}', this)">Save</button>
            </div>
        `;
        listEl.appendChild(row);
    });
}

async function saveProductDetails(id, buttonEl) {
    const rowEl = buttonEl.closest('.admin-price-update-form');
    const costInput = rowEl.querySelector('.admin-cost-input-field');
    const sellingInput = rowEl.querySelector('.admin-selling-input-field');
    const stockInput = rowEl.querySelector('.admin-stock-input-field');
    
    const cost = parseFloat(costInput.value);
    const price = parseFloat(sellingInput.value);
    const stock = parseFloat(stockInput.value);
    
    if (isNaN(cost) || cost < 0 || isNaN(price) || price < 0 || isNaN(stock) || stock < 0) {
        alert("Please enter valid positive values for cost, price, and stock levels.");
        return;
    }
    
    // Disable inputs during save
    costInput.disabled = true;
    sellingInput.disabled = true;
    stockInput.disabled = true;
    buttonEl.disabled = true;
    const originalText = buttonEl.textContent;
    buttonEl.textContent = "Saving...";
    
    try {
        const response = await fetch('/api/admin/update-product', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id, price: price, cost_price: cost, stock: stock })
        });
        
        if (!response.ok) {
            throw new Error("Update product API failed");
        }
        
        playBeep(880, 0.05);
        buttonEl.textContent = "Saved ✓";
        buttonEl.style.backgroundColor = "var(--primary)";
        buttonEl.style.color = "#004D20";
        
        // Refresh local cache and list after a short delay
        setTimeout(async () => {
            buttonEl.style.backgroundColor = "";
            buttonEl.style.color = "";
            buttonEl.textContent = originalText;
            costInput.disabled = false;
            sellingInput.disabled = false;
            stockInput.disabled = false;
            buttonEl.disabled = false;
            // Fetch database items again so scan and cart logic uses the new prices immediately!
            await fetchItems();
            fetchAdminCatalog();
        }, 1200);
        
    } catch (error) {
        console.error("Error updating product details:", error);
        alert("Failed to update product details in the database.");
        costInput.disabled = false;
        sellingInput.disabled = false;
        stockInput.disabled = false;
        buttonEl.disabled = false;
        buttonEl.textContent = originalText;
    }
}

// Make globally accessible
window.saveProductDetails = saveProductDetails;

document.getElementById('btn-refresh-admin').onclick = () => {
    playBeep(440, 0.05);
    fetchAdminCatalog();
};

// Authentication & Role-Based Access Control
function checkAuth() {
    const role = localStorage.getItem('user_role');
    const name = localStorage.getItem('user_name');
    
    const overlay = document.getElementById('login-overlay');
    const userBadge = document.getElementById('user-badge');
    const roleNameEl = document.getElementById('user-role-name');
    
    // Find the Admin Panel tab button
    const adminTabBtn = document.querySelector('.tab-btn[data-tab="admin"]');
    
    if (role && name) {
        overlay.classList.remove('active');
        userBadge.style.display = 'flex';
        roleNameEl.textContent = `${name} (${role})`;
        
        if (role === 'admin') {
            if (adminTabBtn) adminTabBtn.style.display = '';
        } else {
            if (adminTabBtn) adminTabBtn.style.display = 'none';
        }
    } else {
        overlay.classList.add('active');
        userBadge.style.display = 'none';
        if (adminTabBtn) adminTabBtn.style.display = 'none';
        
        // If current tab is admin, switch to cart
        if (activeTab === 'admin') {
            switchTab('cart');
        }
    }
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        if (btn.dataset.tab === tabId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    document.querySelectorAll('.tab-content').forEach(content => {
        if (content.id === `tab-${tabId}`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
    
    activeTab = tabId;
}

async function handleLogin(event) {
    event.preventDefault();
    const usernameEl = document.getElementById('login-username');
    const passwordEl = document.getElementById('login-password');
    const errorEl = document.getElementById('login-error-msg');
    const submitBtn = document.getElementById('btn-login-submit');
    
    errorEl.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Verifying...';
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: usernameEl.value, password: passwordEl.value })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Login failed');
        }
        
        const data = await response.json();
        playBeep(880, 0.05);
        setTimeout(() => playBeep(1200, 0.08), 60);
        
        localStorage.setItem('user_role', data.role);
        localStorage.setItem('user_name', data.username);
        
        usernameEl.value = '';
        passwordEl.value = '';
        checkAuth();
        
        // Refresh catalog if admin
        if (data.role === 'admin') {
            fetchAdminCatalog();
        }
    } catch (error) {
        console.error("Login failure:", error);
        errorEl.textContent = error.message;
        errorEl.style.display = 'block';
        playBeep(220, 0.25);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Sign In';
    }
}

function handleLogout() {
    playBeep(440, 0.1);
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_name');
    checkAuth();
}

// Attach event listeners for login & logout
document.getElementById('login-form').onsubmit = handleLogin;
document.getElementById('btn-logout').onclick = handleLogout;

// Initialize
window.onload = async () => {
    await fetchItems();
    initWebcam();
    initSimulation();
    initOCRMode();
    fetchTransactions(); // Initial quiet load of history
    checkAuth();         // Verify login state
};
