#!/usr/bin/env python3
"""
Golden path tests for the Sephora Beauty API.
Tests key user journeys through the API endpoints.
"""

import httpx
import json
import sys
import time
from typing import Optional

BASE_URL = "http://localhost:8000/v1"
TOKEN: Optional[str] = None

def test_endpoint(method: str, path: str, data=None, headers=None, expected_status=200):
    """Test an API endpoint and print results"""
    url = f"{BASE_URL}{path}"
    
    try:
        if method == "GET":
            response = httpx.get(url, headers=headers)
        elif method == "POST":
            # Handle form data vs JSON
            if isinstance(data, str):
                response = httpx.post(url, data=data, headers=headers)
            else:
                response = httpx.post(url, json=data, headers=headers)
        elif method == "PUT":
            response = httpx.put(url, json=data, headers=headers)
        elif method == "DELETE":
            response = httpx.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        status_match = response.status_code == expected_status
        status_icon = "✓" if status_match else "✗"
        
        print(f"{status_icon} {method} {path} - Status: {response.status_code}")
        
        if not status_match:
            print(f"  Expected: {expected_status}, Got: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
        
        return response
        
    except Exception as e:
        print(f"✗ {method} {path} - Error: {e}")
        return None

def get_token():
    """Get authentication token"""
    global TOKEN
    print("\n=== Authentication Flow ===")
    response = test_endpoint("POST", "/auth/token", 
                           data="grant_type=client_credentials",
                           headers={"Content-Type": "application/x-www-form-urlencoded"})
    if response and response.status_code == 200:
        TOKEN = response.json()["access_token"]
        print(f"  Token acquired: {TOKEN[:20]}...")
        return TOKEN
    return None

def test_homepage_to_purchase():
    """Test the homepage to purchase journey"""
    print("\n=== Homepage to Purchase Journey ===")
    
    # 1. Get homepage content
    response = test_endpoint("GET", "/content/home")
    if response and response.status_code == 200:
        content = response.json()
        print(f"  Found {len(content.get('content', []))} content blocks")
    
    # 2. Search for foundation
    response = test_endpoint("GET", "/products/search?q=foundation")
    if response and response.status_code == 200:
        data = response.json()
        products = data.get("products", [])
        print(f"  Found {len(products)} foundation products")
        
        if products:
            # 3. View first product details
            product_id = products[0]["productId"]
            response = test_endpoint("GET", f"/products/{product_id}")
            if response and response.status_code == 200:
                product = response.json()
                print(f"  Product: {product['name']}")
                
                # 4. Get auth token if not already have one
                if not TOKEN:
                    get_token()
                
                if TOKEN:
                    # 5. Add to cart
                    sku_id = product["skus"][0]["skuId"]
                    headers = {"Authorization": f"Bearer {TOKEN}"}
                    response = test_endpoint("POST", "/cart", 
                                          data={"skuId": sku_id, "quantity": 1},
                                          headers=headers)
                    
                    # 6. View cart
                    response = test_endpoint("GET", "/cart", headers=headers)
                    if response and response.status_code == 200:
                        cart = response.json()
                        print(f"  Cart total: {cart['total']}")

def test_user_profile_and_rewards():
    """Test user profile and rewards journey"""
    print("\n=== User Profile and Rewards Journey ===")
    
    # Get token if needed
    if not TOKEN:
        get_token()
    
    if TOKEN:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        
        # Get user profile
        response = test_endpoint("GET", "/users/profile", headers=headers)
        if response and response.status_code == 200:
            profile = response.json()
            print(f"  User: {profile['firstName']}")
            print(f"  Beauty Insider Tier: {profile['beautyInsider']['tier']}")
            print(f"  Points: {profile['beautyInsider']['points']}")

def test_product_discovery_flow():
    """Test product discovery flow"""
    print("\n=== Product Discovery Flow ===")
    
    # 1. Get homepage
    test_endpoint("GET", "/content/home")
    
    # 2. Search by brand
    response = test_endpoint("GET", "/products/search?brand=Kosas")
    if response and response.status_code == 200:
        data = response.json()
        print(f"  Found {len(data.get('products', []))} Kosas products")
    
    # 3. Search by category with sorting
    response = test_endpoint("GET", "/products/search?category=makeup&sort=RATING")
    if response and response.status_code == 200:
        data = response.json()
        products = data.get("products", [])
        if products:
            print(f"  Top rated: {products[0]['name']} ({products[0]['rating']} stars)")

def test_cart_management():
    """Test cart management operations"""
    print("\n=== Cart Management Flow ===")
    
    # Get token if needed
    if not TOKEN:
        get_token()
    
    if TOKEN:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        
        # Add multiple items
        for product in ["2674057", "2674133"]:
            response = test_endpoint("POST", "/cart",
                                   data={"skuId": product, "quantity": 1},
                                   headers=headers)
        
        # Get cart
        response = test_endpoint("GET", "/cart", headers=headers)
        if response and response.status_code == 200:
            cart = response.json()
            print(f"  Cart has {len(cart['items'])} items")
            print(f"  Subtotal: {cart['subtotal']}")
            
            # Update quantity of first item
            if cart['items']:
                item_id = cart['items'][0]['itemId']
                response = test_endpoint("PUT", f"/cart/items/{item_id}",
                                       data={"quantity": 2},
                                       headers=headers)
                
                # Remove second item if exists
                if len(cart['items']) > 1:
                    item_id = cart['items'][1]['itemId']
                    test_endpoint("DELETE", f"/cart/items/{item_id}", headers=headers)
        
        # Final cart state
        response = test_endpoint("GET", "/cart", headers=headers)
        if response and response.status_code == 200:
            cart = response.json()
            print(f"  Final cart: {len(cart['items'])} items, Total: {cart['total']}")

def test_rate_limiting():
    """Test rate limiting behavior"""
    print("\n=== Rate Limiting Test ===")
    
    # Make rapid requests to trigger rate limit
    endpoint = "/content/home"
    for i in range(5):
        response = httpx.get(f"{BASE_URL}{endpoint}")
        if response.status_code == 429:
            print(f"  Rate limit triggered after {i+1} requests")
            retry_after = response.headers.get("Retry-After", "Unknown")
            print(f"  Retry-After: {retry_after} seconds")
            break
        time.sleep(0.1)  # Small delay to avoid overwhelming
    else:
        print("  Rate limit not triggered (limit may be higher)")

def main():
    """Run all test scenarios"""
    print("=" * 50)
    print("Sephora Beauty API - Golden Path Tests")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = httpx.get(f"{BASE_URL}/content/home")
        print("✓ Server is running")
    except:
        print("✗ Server is not running. Please start with: python app/main.py")
        sys.exit(1)
    
    # Run test scenarios
    test_homepage_to_purchase()
    test_user_profile_and_rewards()
    test_product_discovery_flow()
    test_cart_management()
    test_rate_limiting()
    
    print("\n" + "=" * 50)
    print("Testing Complete")
    print("=" * 50)

if __name__ == "__main__":
    main()
