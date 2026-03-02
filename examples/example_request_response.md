# Example Request & Response

This document shows example requests and responses for the BILLESE API.

## Example 1: Scan First Item

### Request

**Endpoint:** `POST http://localhost:8000/scan-item?session_id=customer1`

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "weight_grams": 500
}
```

**Note:** The image value above is a minimal base64-encoded 1x1 pixel image. In production, you'll send the actual product image from the ESP32 camera.

### Response

**Status Code:** `200 OK`

**Body:**
```json
{
  "detected_item": {
    "name": "tomato",
    "weight_grams": 500.0,
    "price_per_kg": 80.0,
    "total_price": 40.0
  },
  "current_bill": [
    {
      "item_name": "tomato",
      "weight_grams": 500.0,
      "price_per_kg": 80.0,
      "total_price": 40.0
    }
  ],
  "bill_total": 40.0
}
```

**Explanation:**
- Detected item: "tomato" (mock detection)
- Weight: 500 grams = 0.5 kg
- Price per kg: ₹80
- Total price: 0.5 × 80 = ₹40
- Bill total: ₹40 (only one item so far)

---

## Example 2: Scan Second Item (Same Session)

### Request

**Endpoint:** `POST http://localhost:8000/scan-item?session_id=customer1`

**Body:**
```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "weight_grams": 750
}
```

### Response

**Status Code:** `200 OK`

**Body:**
```json
{
  "detected_item": {
    "name": "tomato",
    "weight_grams": 750.0,
    "price_per_kg": 80.0,
    "total_price": 60.0
  },
  "current_bill": [
    {
      "item_name": "tomato",
      "weight_grams": 500.0,
      "price_per_kg": 80.0,
      "total_price": 40.0
    },
    {
      "item_name": "tomato",
      "weight_grams": 750.0,
      "price_per_kg": 80.0,
      "total_price": 60.0
    }
  ],
  "bill_total": 100.0
}
```

**Explanation:**
- Second item added: 750g tomato = ₹60
- Bill now contains 2 items
- Total: ₹40 + ₹60 = ₹100

---

## Example 3: Get Current Bill

### Request

**Endpoint:** `GET http://localhost:8000/bill/customer1`

### Response

**Status Code:** `200 OK`

**Body:**
```json
{
  "session_id": "customer1",
  "items": [
    {
      "item_name": "tomato",
      "weight_grams": 500.0,
      "price_per_kg": 80.0,
      "total_price": 40.0
    },
    {
      "item_name": "tomato",
      "weight_grams": 750.0,
      "price_per_kg": 80.0,
      "total_price": 60.0
    }
  ],
  "total": 100.0
}
```

---

## Example 4: Clear Bill

### Request

**Endpoint:** `DELETE http://localhost:8000/bill/customer1`

### Response

**Status Code:** `200 OK`

**Body:**
```json
{
  "message": "Bill session customer1 cleared successfully"
}
```

---

## Example 5: Error - Invalid Weight

### Request

**Endpoint:** `POST http://localhost:8000/scan-item`

**Body:**
```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "weight_grams": -100
}
```

### Response

**Status Code:** `400 Bad Request`

**Body:**
```json
{
  "detail": "Weight must be greater than 0"
}
```

---

## Example 6: Error - Missing Image

### Request

**Endpoint:** `POST http://localhost:8000/scan-item`

**Body:**
```json
{
  "weight_grams": 500
}
```

### Response

**Status Code:** `422 Unprocessable Entity`

**Body:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "image"],
      "msg": "Field required",
      "input": {"weight_grams": 500}
    }
  ]
}
```

---

## Testing with cURL

### Scan Item
```bash
curl -X POST "http://localhost:8000/scan-item?session_id=test" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "weight_grams": 500
  }'
```

### Get Bill
```bash
curl "http://localhost:8000/bill/test"
```

### Clear Bill
```bash
curl -X DELETE "http://localhost:8000/bill/test"
```

---

## Testing with Python

```python
import requests
import base64

# Read and encode image
with open("product_image.jpg", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode('utf-8')

# Scan item
response = requests.post(
    "http://localhost:8000/scan-item",
    params={"session_id": "customer1"},
    json={
        "image": image_base64,
        "weight_grams": 500
    }
)

print("Status Code:", response.status_code)
print("Response:", response.json())
```

---

## Price Table Reference

Current hardcoded prices (per kilogram):

| Item    | Price (₹/kg) |
|---------|--------------|
| tomato  | 80.0         |
| potato  | 40.0         |
| onion   | 60.0         |
| carrot  | 50.0         |
| cabbage | 30.0         |
| default | 50.0         |

*Note: Currently, all items are detected as "tomato" (mock detection).*
















