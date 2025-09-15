#!/usr/bin/env python3
"""
Test script to demonstrate the complete Sephora checkout flow for purchasing a gift card.
This follows the same flow as observed in the HAR file analysis.
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

def main():
    print("\n🛍️  SEPHORA GIFT CARD PURCHASE FLOW DEMONSTRATION")
    print("This script demonstrates the complete checkout flow for purchasing a $50 gift card")
    
    # Step 1: Add gift card to cart
    print_step(1, "Add $50 Gift Card to Cart")
    add_to_cart_response = requests.post(
        f"{BASE_URL}/cart",
        json={
            "skuId": "00540",  # $50 gift card
            "quantity": 1
        }
    )
    if add_to_cart_response.status_code == 200:
        cart = add_to_cart_response.json()
        print(f"✅ Gift card added to cart")
        print(f"   Subtotal: {cart['subtotal']}")
        print(f"   Tax: {cart['tax']}")
        print(f"   Total: {cart['total']}")
    else:
        print(f"❌ Failed to add to cart: {add_to_cart_response.text}")
        return
    
    # Step 2: Initialize order
    print_step(2, "Initialize Checkout Order")
    init_order_response = requests.post(
        f"{BASE_URL}/checkout/order/init",
        json={
            "isPaypalFlow": False,
            "isApplePayFlow": False,
            "isVenmoFlow": False
        }
    )
    if init_order_response.status_code == 200:
        order_data = init_order_response.json()
        order_id = order_data['orderId']
        print(f"✅ Order initialized")
        print(f"   Order ID: {order_id}")
        print(f"   BI Member: {order_data.get('isBIMember', False)}")
    else:
        print(f"❌ Failed to initialize order: {init_order_response.text}")
        return
    
    # Step 3: Set shipping address
    print_step(3, "Set Shipping Address")
    shipping_response = requests.post(
        f"{BASE_URL}/checkout/orders/shippingAddress",
        json={
            "shippingGroupId": "0",
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
            },
            "saveToProfile": True,
            "isDefaultAddress": True,
            "addressType": "Residential",
            "isPOBoxAddress": False
        }
    )
    if shipping_response.status_code == 200:
        shipping_data = shipping_response.json()
        print(f"✅ Shipping address set")
        print(f"   Address ID: {shipping_data.get('addressId')}")
        print(f"   Shipping to: Willy Rob, San Francisco, CA")
    else:
        print(f"❌ Failed to set shipping address: {shipping_response.text}")
        return
    
    # Step 4: Get order details
    print_step(4, "Get Order Details")
    order_details_response = requests.get(f"{BASE_URL}/checkout/orders/{order_id}")
    if order_details_response.status_code == 200:
        order_details = order_details_response.json()
        print(f"✅ Order details retrieved")
        print(f"   Items: {len(order_details['items'])} item(s)")
        print(f"   Shipping: {order_details['priceInfo']['merchandiseShipping']}")
        print(f"   Subtotal: {order_details['priceInfo']['merchandiseSubtotal']}")
        print(f"   Tax: {order_details['priceInfo']['tax']}")
        print(f"   Total: {order_details['priceInfo']['orderTotal']}")
    else:
        print(f"❌ Failed to get order details: {order_details_response.text}")
    
    # Step 5: Get checkout quote (precheck)
    print_step(5, "Get Checkout Quote (Precheck)")
    quote_response = requests.post(
        f"{BASE_URL}/checkout/quote",
        json={"order_id": order_id}
    )
    if quote_response.status_code == 200:
        quote = quote_response.json()
        print(f"✅ Quote retrieved (this is the precheck endpoint)")
        print(f"   Subtotal: {quote['pricing']['subtotal']}")
        print(f"   Tax: {quote['pricing']['tax']}")
        print(f"   Shipping: {quote['pricing']['shipping']}")
        print(f"   Total: {quote['pricing']['total']}")
        print(f"   Total (cents): {quote['pricing']['total_cents']}")
        print(f"   Estimated Delivery: {quote['estimatedDelivery']}")
    else:
        print(f"❌ Failed to get quote: {quote_response.text}")
        return
    
    # Step 6: Submit order (purchase)
    print_step(6, "Submit Order (Purchase)")
    print("📝 Note: Payment is hardcoded as MasterCard ending in 7034")
    submit_response = requests.post(
        f"{BASE_URL}/checkout/submitOrder",
        json={
            "orderId": order_id,
            "originOfOrder": "iPhoneAppV2.0"
        }
    )
    if submit_response.status_code == 200:
        confirmation = submit_response.json()
        print(f"✅ ORDER SUBMITTED SUCCESSFULLY!")
        print(f"   Confirmation Number: {confirmation['confirmationNumber']}")
        print(f"   Order ID: {confirmation['orderId']}")
        print(f"   Total Charged: {confirmation['totals']['total']}")
        print(f"   Total (cents): {confirmation['totals']['total_cents']}")
        print(f"   Message: {confirmation['message']}")
        print(f"\n💳 Payment Method (Hardcoded):")
        print(f"   Card: MasterCard ****-****-****-7034")
        print(f"   Name: Will Roberts")
        print(f"   Expiry: 12/2030")
    else:
        print(f"❌ Failed to submit order: {submit_response.text}")
        return
    
    print("\n" + "="*60)
    print("✨ CHECKOUT FLOW COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("\nSummary:")
    print("- Added $50 Sephora gift card to cart")
    print("- Initialized order session")
    print("- Set shipping address to San Francisco, CA")
    print("- Retrieved pricing quote (precheck)")
    print("- Submitted order with hardcoded payment")
    print(f"- Confirmation: {confirmation['confirmationNumber']}")
    print("\n📌 Note: This flow follows the Unified API purchase pattern:")
    print("  - /checkout/quote is marked as x-purchase-precheckout")
    print("  - /checkout/submitOrder is marked as x-purchase-endpoint")
    print("  - The gateway uses the quote to verify user has sufficient credits")
    print("  - Payment details are hardcoded from the original HAR file")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to the API server")
        print("   Please ensure the server is running with: python modal_app.py")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
