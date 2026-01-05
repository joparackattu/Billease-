# BILLESE - AI-based Smart Billing System

A college project for an AI-powered smart billing system using ESP32 (camera + load cell) and FastAPI backend.

## 📁 Project Structure

```
Billease/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Request/Response data models
│   └── services/
│       ├── __init__.py
│       ├── item_detection.py   # Mock item detection logic
│       └── bill_manager.py     # Bill session management
├── main.py                      # FastAPI application entry point
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Server

```bash
# Option 1: Using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Using Python
python main.py
```

The server will start at: **http://localhost:8000**

### 3. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📡 API Endpoints

### 1. POST `/scan-item`

Scan an item and add it to the bill.

**Request Body:**
```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgAA...",  // Base64 encoded image
  "weight_grams": 500                      // Weight in grams
}
```

**Query Parameters:**
- `session_id` (optional): Session ID for the bill. Defaults to "default"

**Response:**
```json
{
  "detected_item": {
    "name": "tomato",
    "weight_grams": 500,
    "price_per_kg": 80.0,
    "total_price": 40.0
  },
  "current_bill": [
    {
      "item_name": "tomato",
      "weight_grams": 500,
      "price_per_kg": 80.0,
      "total_price": 40.0
    }
  ],
  "bill_total": 40.0
}
```

### 2. GET `/bill/{session_id}`

Get the current bill for a session.

**Response:**
```json
{
  "session_id": "default",
  "items": [
    {
      "item_name": "tomato",
      "weight_grams": 500,
      "price_per_kg": 80.0,
      "total_price": 40.0
    }
  ],
  "total": 40.0
}
```

### 3. DELETE `/bill/{session_id}`

Clear all items from a bill session.

**Response:**
```json
{
  "message": "Bill session default cleared successfully"
}
```

## 📝 Example Usage

### Using cURL

```bash
# Scan an item
curl -X POST "http://localhost:8000/scan-item?session_id=default" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "iVBORw0KGgoAAAANSUhEUgAA...",
    "weight_grams": 500
  }'

# Get current bill
curl "http://localhost:8000/bill/default"

# Clear bill
curl -X DELETE "http://localhost:8000/bill/default"
```

### Using Python

```python
import requests
import base64

# Read image and convert to base64
with open("tomato.jpg", "rb") as image_file:
    image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

# Scan an item
response = requests.post(
    "http://localhost:8000/scan-item",
    params={"session_id": "customer1"},
    json={
        "image": image_base64,
        "weight_grams": 500
    }
)

print(response.json())
```

### Using ESP32 (Arduino/PlatformIO)

```cpp
// Example ESP32 code snippet
#include <WiFi.h>
#include <HTTPClient.h>
#include <base64.h>

void scanItem(String imageBase64, float weightGrams) {
  HTTPClient http;
  http.begin("http://YOUR_PC_IP:8000/scan-item?session_id=default");
  http.addHeader("Content-Type", "application/json");
  
  String jsonPayload = "{\"image\":\"" + imageBase64 + "\",\"weight_grams\":" + String(weightGrams) + "}";
  
  int httpResponseCode = http.POST(jsonPayload);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println(response);
  }
  
  http.end();
}
```

## 💡 How It Works

1. **ESP32 sends data**: Camera captures image → converts to base64 → sends with weight to backend
2. **Backend processes**: Receives image and weight → detects item (currently mock: "tomato") → calculates price
3. **Bill management**: Adds item to session → maintains bill in memory → returns updated bill
4. **Response**: Returns detected item info, calculated price, and complete bill

## 🔧 Current Features (Step 1)

✅ FastAPI backend with clean structure  
✅ POST `/scan-item` endpoint  
✅ Base64 image support  
✅ Weight-based price calculation  
✅ In-memory bill session management  
✅ Mock item detection (always returns "tomato")  
✅ Hardcoded price table  

## 🚧 Future Enhancements

- [ ] Real AI model for item detection
- [ ] Database integration (PostgreSQL/MySQL)
- [ ] WhatsApp integration for bill sharing
- [ ] User authentication
- [ ] Multiple store support
- [ ] Bill history and analytics

## 📚 Learning Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **ESP32 HTTP Client**: https://github.com/espressif/arduino-esp32

## 🎓 For Students

This code is designed to be beginner-friendly with:
- Clear comments explaining each step
- Simple, readable code structure
- Separation of concerns (models, services, main)
- Type hints for better code understanding
- Error handling examples

## 📄 License

This is a college project for educational purposes.










=======
# Billease-
>>>>>>> f85b7a80eba2da79a8728dabe34a37867c3fcb9e
