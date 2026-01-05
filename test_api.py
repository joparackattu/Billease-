"""
Simple test script for BILLESE API

This script helps you test the API endpoints.
Run it after starting the server with: python main.py
"""

import requests
import base64
import json

# Server URL
BASE_URL = "http://localhost:8000"

def create_test_image_base64():
    """
    Create a minimal test image in base64 format.
    In production, you'll use actual images from the ESP32 camera.
    """
    # This is a 1x1 pixel red PNG image in base64
    # In real usage, you'll get this from the ESP32 camera
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


def test_scan_item(session_id="test", weight_grams=500):
    """
    Test the /scan-item endpoint.
    
    Args:
        session_id: Session ID for the bill
        weight_grams: Weight of the item in grams
    """
    print(f"\n{'='*50}")
    print(f"Testing: POST /scan-item")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/scan-item"
    payload = {
        "image": create_test_image_base64(),
        "weight_grams": weight_grams
    }
    params = {"session_id": session_id}
    
    try:
        response = requests.post(url, json=payload, params=params)
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None


def test_get_bill(session_id="test"):
    """
    Test the GET /bill/{session_id} endpoint.
    """
    print(f"\n{'='*50}")
    print(f"Testing: GET /bill/{session_id}")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/bill/{session_id}"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None


def test_clear_bill(session_id="test"):
    """
    Test the DELETE /bill/{session_id} endpoint.
    """
    print(f"\n{'='*50}")
    print(f"Testing: DELETE /bill/{session_id}")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/bill/{session_id}"
    
    try:
        response = requests.delete(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None


def test_root():
    """
    Test the root endpoint.
    """
    print(f"\n{'='*50}")
    print(f"Testing: GET /")
    print(f"{'='*50}")
    
    url = f"{BASE_URL}/"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    print("="*50)
    print("BILLESE API Test Script")
    print("="*50)
    print("\nMake sure the server is running at http://localhost:8000")
    print("Start the server with: uvicorn main:app --reload")
    print("\nPress Enter to start testing...")
    input()
    
    # Test root endpoint
    test_root()
    
    # Test scanning items
    print("\n\n>>> Scanning first item (500g)")
    test_scan_item("customer1", 500)
    
    print("\n\n>>> Scanning second item (750g)")
    test_scan_item("customer1", 750)
    
    print("\n\n>>> Scanning third item (1000g)")
    test_scan_item("customer1", 1000)
    
    # Get current bill
    print("\n\n>>> Getting current bill")
    test_get_bill("customer1")
    
    # Clear bill
    print("\n\n>>> Clearing bill")
    test_clear_bill("customer1")
    
    # Verify bill is cleared
    print("\n\n>>> Verifying bill is cleared")
    test_get_bill("customer1")
    
    print("\n\n" + "="*50)
    print("Testing Complete!")
    print("="*50)












