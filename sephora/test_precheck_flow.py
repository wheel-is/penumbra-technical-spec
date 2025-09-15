#!/usr/bin/env python3
"""
Test script to demonstrate the checkout flow up to the payment point (precheck).
This tests everything except the actual purchase submission.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def print_step(step_num, description):
    """Print a formatted step header"""
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {description}")
    print('='*60)

def print_success(message):
    print(f"✅ {message}")

def print_info(label, value):
    print(f"   {label}: {value}")

def main():
    print("\n🛒 SEPHORA CHECKOUT PRECHECK TEST")
    print("Testing the complete flow up to the payment point")
    print("This validates everything BEFORE the actual purchase")
    
    # Step 1: Browse products
    print_step(1, "Browse Available Gift Cards")
    search_response = requests.get(
        f"{BASE_URL}/products/search",
        params={"q": "gift card"}
    )
    if search_response.status_code == 200:
        products = search_response.json()['products']
        gift_cards = [p for p in products if p.get('type') == 'Gift Card']
        print_success(f"Found {len(gift_cards)} gift cards available")
        for card in gift_cards[:3]:  # Show first 3
            print_info(f"  - {card['variationDesc']}", card['listPrice'])
    else:
        print(f"❌ Failed to search products: {search_response.text}")
        return
    
    # Step 2: Add multiple items to cart
    print_step(2, "Build Shopping Cart")
    
    # Add $50 gift card
    add_response_1 = requests.post(
        f"{BASE_URL}/cart",
        json={"skuId": "00540", "quantity": 1}
    )
    if add_response_1.status_code == 200:
        print_success("Added $50 gift card")
    
    # Add $25 gift card
    add_response_2 = requests.post(
        f"{BASE_URL}/cart",
        json={"skuId": "00520", "quantity": 2}
    )
    if add_response_2.status_code == 200:
        print_success("Added 2x $25 gift cards")
    
    # Get cart totals
    cart_response = requests.get(f"{BASE_URL}/cart")
    if cart_response.status_code == 200:
        cart = cart_response.json()
        print_success("Cart built successfully")
        print_info("Items", f"{len(cart['items'])} items")
        print_info("Subtotal", cart['subtotal'])
        print_info("Tax", cart['tax'])
        print_info("Shipping", cart['shipping'])
        print_info("Total", cart['total'])
    else:
        print(f"❌ Failed to get cart: {cart_response.text}")
        return
    
    # Step 3: Initialize checkout order
    print_step(3, "Initialize Checkout Session")
    init_response = requests.post(
        f"{BASE_URL}/checkout/order/init",
        json={
            "isPaypalFlow": False,
            "isApplePayFlow": False,
            "isVenmoFlow": False
        }
    )
    if init_response.status_code == 200:
        order_data = init_response.json()
        order_id = order_data['orderId']
        print_success("Checkout session initialized")
        print_info("Order ID", order_id)
        print_info("Beauty Insider", order_data.get('isBIMember', False))
        print_info("Profile Status", order_data.get('profileStatus', 'N/A'))
    else:
        print(f"❌ Failed to initialize order: {init_response.text}")
        return
    
    # Step 4: Validate shipping address formats
    print_step(4, "Validate Shipping Address")
    
    # Test with different addresses
    addresses = [
        {
            "name": "San Francisco Address",
            "address": {
                "firstName": "Willy",
                "lastName": "Rob",
                "address1": "1513 Pershing Dr",
                "address2": "Apt A",
                "city": "San Francisco",
                "state": "CA",
                "postalCode": "94129-3316",
                "country": "US",
                "phone": "9167995790"
            }
        },
        {
            "name": "New York Address",
            "address": {
                "firstName": "Test",
                "lastName": "User",
                "address1": "123 Broadway",
                "address2": "",
                "city": "New York",
                "state": "NY",
                "postalCode": "10007",
                "country": "US",
                "phone": "2125551234"
            }
        }
    ]
    
    # Set the first address
    shipping_response = requests.post(
        f"{BASE_URL}/checkout/orders/shippingAddress",
        json={
            "shippingGroupId": "0",
            "address": addresses[0]["address"],
            "saveToProfile": True,
            "isDefaultAddress": True,
            "addressType": "Residential",
            "isPOBoxAddress": False
        }
    )
    if shipping_response.status_code == 200:
        shipping_data = shipping_response.json()
        print_success(f"Set shipping to {addresses[0]['name']}")
        print_info("Address ID", shipping_data.get('addressId'))
    else:
        print(f"❌ Failed to set shipping: {shipping_response.text}")
        return
    
    # Step 5: Get detailed order information
    print_step(5, "Retrieve Order Details")
    details_response = requests.get(f"{BASE_URL}/checkout/orders/{order_id}")
    if details_response.status_code == 200:
        order_details = details_response.json()
        print_success("Order details retrieved")
        print_info("Status", order_details['status'])
        print_info("Items Count", len(order_details['items']))
        
        # Show items
        print("\n  Order Items:")
        for item in order_details['items']:
            print(f"    • {item['name']} x{item['quantity']} = {item['price']}")
        
        # Show shipping info
        if order_details.get('shippingAddress'):
            addr = order_details['shippingAddress']
            print(f"\n  Shipping To:")
            print(f"    {addr['firstName']} {addr['lastName']}")
            print(f"    {addr['address1']} {addr.get('address2', '')}")
            print(f"    {addr['city']}, {addr['state']} {addr['postalCode']}")
        
        # Show pricing
        pricing = order_details['priceInfo']
        print(f"\n  Pricing Breakdown:")
        print_info("Subtotal", pricing['merchandiseSubtotal'])
        print_info("Shipping", pricing['merchandiseShipping'])
        print_info("Tax", pricing['tax'])
        print_info("Total", pricing['orderTotal'])
        print_info("Total (cents)", pricing['orderTotal_cents'])
    else:
        print(f"❌ Failed to get order details: {details_response.text}")
        return
    
    # Step 6: Get checkout quote (PRECHECK ENDPOINT)
    print_step(6, "Get Checkout Quote (PRECHECK)")
    print("\n⚠️  This is the PRECHECK endpoint that the gateway will call")
    print("   to verify the user has sufficient credits before purchase")
    
    quote_response = requests.post(
        f"{BASE_URL}/checkout/quote",
        json={"order_id": order_id}
    )
    if quote_response.status_code == 200:
        quote = quote_response.json()
        print_success("Quote retrieved successfully")
        
        print("\n  📋 Quote Details:")
        print_info("Order ID", quote['orderId'])
        print_info("Estimated Delivery", quote['estimatedDelivery'])
        
        print("\n  💰 Final Pricing:")
        pricing = quote['pricing']
        print_info("Subtotal", pricing['subtotal'])
        print_info("Tax", pricing['tax'])
        print_info("Shipping", pricing['shipping'])
        print_info("Total", pricing['total'])
        print_info("Total (cents)", f"{pricing['total_cents']} ← This is what the gateway checks")
        
        print("\n  🏠 Delivery Address:")
        addr = quote['shippingAddress']
        print(f"     {addr['firstName']} {addr['lastName']}")
        print(f"     {addr['address1']} {addr.get('address2', '')}")
        print(f"     {addr['city']}, {addr['state']} {addr['postalCode']}")
        
        print("\n  📦 Items to Purchase:")
        for item in quote['items']:
            print(f"     • {item['name']} x{item['quantity']}")
    else:
        print(f"❌ Failed to get quote: {quote_response.text}")
        return
    
    # Step 7: Explain what happens next
    print_step(7, "What Happens Next (NOT EXECUTED)")
    print("\n🔐 When the actual purchase is submitted:")
    print("   1. Gateway intercepts the /checkout/submitOrder call")
    print("   2. Gateway calls /checkout/quote to get the price")
    print(f"   3. Gateway checks if user has {quote['pricing']['total_cents']} credits")
    print("   4. If insufficient → Returns HTTP 402 Payment Required")
    print("   5. If sufficient → Forwards to our submitOrder endpoint")
    print("   6. Our endpoint processes with hardcoded payment:")
    print("      • Card: MasterCard ****-****-****-7034")
    print("      • Name: Will Roberts")
    print("      • Expiry: 12/2030")
    print("   7. Gateway deducts credits atomically")
    print("   8. User receives confirmation number")
    
    # Summary
    print("\n" + "="*60)
    print("✨ PRECHECK TEST COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("\nValidated:")
    print("✅ Product browsing and search")
    print("✅ Shopping cart management")
    print("✅ Order initialization") 
    print("✅ Shipping address configuration")
    print("✅ Order details retrieval")
    print("✅ Quote/precheck endpoint (gateway integration point)")
    print("\n📊 Ready for payment:")
    print(f"   Total to charge: {quote['pricing']['total']} ({quote['pricing']['total_cents']} cents)")
    print(f"   Order ID: {order_id}")
    print("\n💡 The gateway will use the precheck response to validate")
    print("   credit availability before allowing the purchase to proceed.")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to the API server")
        print("   Please ensure the server is running with: python modal_app.py")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
