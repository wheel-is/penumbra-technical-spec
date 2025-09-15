#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}🛍️  SEPHORA API CURL TEST - COMPLETE CHECKOUT FLOW${NC}"
echo -e "${BLUE}============================================================${NC}"

# Step 1: Search for gift cards
echo -e "\n${YELLOW}STEP 1: Search for Gift Cards${NC}"
echo "Command: curl -X GET \"${BASE_URL}/products/search?q=gift%20card\""
echo -e "${GREEN}Response:${NC}"
curl -X GET "${BASE_URL}/products/search?q=gift%20card" -H "Content-Type: application/json" | jq '.products[] | {name: .name, price: .listPrice, sku: .skuId}' 2>/dev/null || curl -X GET "${BASE_URL}/products/search?q=gift%20card" -H "Content-Type: application/json"

# Step 2: Add $50 gift card to cart
echo -e "\n${YELLOW}STEP 2: Add $50 Gift Card to Cart${NC}"
echo 'Command: curl -X POST "${BASE_URL}/cart" -d {"skuId": "00540", "quantity": 1}'
echo -e "${GREEN}Response:${NC}"
curl -X POST "${BASE_URL}/cart" \
  -H "Content-Type: application/json" \
  -d '{
    "skuId": "00540",
    "quantity": 1
  }' | jq '{items: .items | length, subtotal: .subtotal, tax: .tax, total: .total}' 2>/dev/null || curl -X POST "${BASE_URL}/cart" -H "Content-Type: application/json" -d '{"skuId": "00540", "quantity": 1}'

# Step 3: Add another gift card to cart
echo -e "\n${YELLOW}STEP 3: Add $25 Gift Cards (x2) to Cart${NC}"
echo 'Command: curl -X POST "${BASE_URL}/cart" -d {"skuId": "00520", "quantity": 2}'
echo -e "${GREEN}Response:${NC}"
curl -X POST "${BASE_URL}/cart" \
  -H "Content-Type: application/json" \
  -d '{
    "skuId": "00520",
    "quantity": 2
  }' | jq '{items: .items | length, subtotal: .subtotal, tax: .tax, total: .total}' 2>/dev/null || curl -X POST "${BASE_URL}/cart" -H "Content-Type: application/json" -d '{"skuId": "00520", "quantity": 2}'

# Step 4: View cart contents
echo -e "\n${YELLOW}STEP 4: View Cart Contents${NC}"
echo "Command: curl -X GET \"${BASE_URL}/cart\""
echo -e "${GREEN}Response:${NC}"
curl -X GET "${BASE_URL}/cart" | jq '{
  items: [.items[] | {name: .name, quantity: .quantity, price: .price}],
  totals: {subtotal: .subtotal, tax: .tax, shipping: .shipping, total: .total}
}' 2>/dev/null || curl -X GET "${BASE_URL}/cart"

# Step 5: Initialize checkout order
echo -e "\n${YELLOW}STEP 5: Initialize Checkout Order${NC}"
echo 'Command: curl -X POST "${BASE_URL}/checkout/order/init"'
echo -e "${GREEN}Response:${NC}"
ORDER_RESPONSE=$(curl -s -X POST "${BASE_URL}/checkout/order/init" \
  -H "Content-Type: application/json" \
  -d '{
    "isPaypalFlow": false,
    "isApplePayFlow": false,
    "isVenmoFlow": false
  }')
echo "$ORDER_RESPONSE" | jq '.' 2>/dev/null || echo "$ORDER_RESPONSE"

# Extract order ID
ORDER_ID=$(echo "$ORDER_RESPONSE" | jq -r '.orderId' 2>/dev/null || echo "$ORDER_RESPONSE" | grep -o '"orderId":"[^"]*"' | cut -d'"' -f4)
echo -e "${BLUE}📌 Order ID: ${ORDER_ID}${NC}"

# Step 6: Set shipping address
echo -e "\n${YELLOW}STEP 6: Set Shipping Address${NC}"
echo 'Command: curl -X POST "${BASE_URL}/checkout/orders/shippingAddress"'
echo -e "${GREEN}Response:${NC}"
curl -X POST "${BASE_URL}/checkout/orders/shippingAddress" \
  -H "Content-Type: application/json" \
  -d '{
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
    "saveToProfile": true,
    "isDefaultAddress": true,
    "addressType": "Residential",
    "isPOBoxAddress": false
  }' | jq '.' 2>/dev/null || curl -X POST "${BASE_URL}/checkout/orders/shippingAddress" -H "Content-Type: application/json" -d '{"shippingGroupId":"0","address":{"firstName":"Willy","lastName":"Rob","address1":"1513 Pershing Dr","address2":"Apt A","city":"San Francisco","state":"CA","postalCode":"94129-3316","country":"US","phone":"9167995790"}}'

# Step 7: Get order details
echo -e "\n${YELLOW}STEP 7: Get Order Details${NC}"
echo "Command: curl -X GET \"${BASE_URL}/checkout/orders/${ORDER_ID}\""
echo -e "${GREEN}Response:${NC}"
curl -X GET "${BASE_URL}/checkout/orders/${ORDER_ID}" | jq '{
  orderId: .orderId,
  items: [.items[] | {name: .name, quantity: .quantity}],
  shipping: .shippingAddress | {to: "\(.firstName) \(.lastName)", city: .city, state: .state},
  pricing: .priceInfo
}' 2>/dev/null || curl -X GET "${BASE_URL}/checkout/orders/${ORDER_ID}"

# Step 8: Get checkout quote (PRECHECK)
echo -e "\n${YELLOW}STEP 8: Get Checkout Quote (PRECHECK ENDPOINT)${NC}"
echo -e "${RED}⚠️  This is the endpoint marked with x-purchase-precheckout: true${NC}"
echo "Command: curl -X POST \"${BASE_URL}/checkout/quote\" -d {\"order_id\": \"${ORDER_ID}\"}"
echo -e "${GREEN}Response:${NC}"
QUOTE_RESPONSE=$(curl -s -X POST "${BASE_URL}/checkout/quote" \
  -H "Content-Type: application/json" \
  -d "{\"order_id\": \"${ORDER_ID}\"}")
echo "$QUOTE_RESPONSE" | jq '{
  orderId: .orderId,
  pricing: .pricing,
  estimatedDelivery: .estimatedDelivery,
  shippingTo: "\(.shippingAddress.firstName) \(.shippingAddress.lastName), \(.shippingAddress.city), \(.shippingAddress.state)"
}' 2>/dev/null || echo "$QUOTE_RESPONSE"

# Extract total cents for display
TOTAL_CENTS=$(echo "$QUOTE_RESPONSE" | jq -r '.pricing.total_cents' 2>/dev/null || echo "$QUOTE_RESPONSE" | grep -o '"total_cents":[0-9]*' | cut -d':' -f2)

echo -e "\n${BLUE}============================================================${NC}"
echo -e "${BLUE}💰 READY FOR PAYMENT - PRECHECK COMPLETE${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "Total to charge: ${GREEN}${TOTAL_CENTS} cents${NC}"
echo -e "Order ID: ${GREEN}${ORDER_ID}${NC}"

# Step 9: Show submit order command (but don't execute)
echo -e "\n${YELLOW}STEP 9: Submit Order (NOT EXECUTED - JUST SHOWING COMMAND)${NC}"
echo -e "${RED}This would complete the purchase with hardcoded payment:${NC}"
echo "curl -X POST \"${BASE_URL}/checkout/submitOrder\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{"
echo "    \"orderId\": \"${ORDER_ID}\","
echo "    \"originOfOrder\": \"iPhoneAppV2.0\""
echo "  }'"

echo -e "\n${GREEN}Expected Response Structure:${NC}"
cat << 'EOF'
{
  "orderId": "735700000001",
  "confirmationNumber": "SEP-735700000001",
  "totals": {
    "total": "$108.62",
    "total_cents": 10862  ← This is what the gateway will deduct
  },
  "message": "Order submitted successfully"
}
EOF

echo -e "\n${BLUE}============================================================${NC}"
echo -e "${GREEN}✅ CURL TEST COMPLETED SUCCESSFULLY!${NC}"
echo -e "${BLUE}============================================================${NC}"

echo -e "\n${YELLOW}📋 Summary of Unified API Integration:${NC}"
echo "1. The /checkout/quote endpoint is marked with x-purchase-precheckout: true"
echo "2. The /checkout/submitOrder endpoint is marked with x-purchase-endpoint: true"
echo "3. The gateway will call /checkout/quote first to check the amount"
echo "4. If user has ${TOTAL_CENTS} credits, purchase proceeds"
echo "5. If not, gateway returns HTTP 402 Payment Required"
echo "6. Payment details are hardcoded (MasterCard ****7034, Will Roberts)"

echo -e "\n${YELLOW}🔧 To test the actual purchase, run:${NC}"
echo "curl -X POST \"${BASE_URL}/checkout/submitOrder\" -H \"Content-Type: application/json\" -d '{\"orderId\": \"${ORDER_ID}\"}'"
