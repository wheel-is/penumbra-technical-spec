# Sephora Beauty API

A minimal FastAPI implementation that emulates key Sephora user journeys for beauty product discovery and shopping.

## Features

- **OAuth2 Authentication**: Client credentials flow with Bearer tokens
- **Homepage Content**: Modular content blocks (banners, product carousels, category links)
- **Product Catalog**: Search and browse products with filters and pagination
- **Product Details**: Detailed product information with reviews and recommendations
- **Gift Cards**: Full catalog of Sephora gift cards ($10-$100)
- **Shopping Cart**: Add, update, and remove items with real-time totals
- **Checkout Flow**: Complete purchase flow with order initialization, shipping, and payment
- **Billing Integration**: Unified API precheck pattern for purchase validation
- **User Profiles**: Beauty Insider rewards and points system
- **Rate Limiting**: 429 responses with Retry-After headers
- **Error Handling**: Consistent error response format

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python app/main.py
```

3. View API documentation:
```
http://localhost:8000/docs
```

## Authentication Flow

1. Get an access token:
```bash
curl -X POST http://localhost:8000/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials"
```

2. Use the token for authenticated requests:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/v1/users/profile
```

## Checkout Flow

The API implements a complete checkout flow following the Sephora purchase pattern:

1. **Add items to cart** - Add products/gift cards to shopping cart
2. **Initialize order** - Create an order from cart contents
3. **Set shipping address** - Configure delivery information  
4. **Get checkout quote** - Calculate final pricing (precheck endpoint)
5. **Submit order** - Complete purchase with hardcoded payment

### Purchase Pattern (Unified API Compliance)

The checkout implements the Unified API billing precheck pattern:
- `/checkout/quote` is marked with `x-purchase-precheckout: true`
- `/checkout/submitOrder` is marked with `x-purchase-endpoint: true`
- The gateway calls the quote endpoint first to verify user has sufficient credits
- If successful, the purchase endpoint is called to complete the transaction
- Payment details are hardcoded (MasterCard ending in 7034, Will Roberts, 12/2030)

### Testing the Checkout Flow

Run the included test script to see the complete flow:
```bash
python test_checkout_flow.py
```

## Key Endpoints

### Authentication & Content
- `POST /v1/auth/token` - Get access token
- `GET /v1/content/home` - Homepage content

### Products & Cart
- `GET /v1/products/search` - Search products
- `GET /v1/products/{id}` - Product details
- `GET /v1/cart` - Shopping cart
- `POST /v1/cart` - Add to cart

### Checkout Flow
- `POST /checkout/order/init` - Initialize order
- `POST /checkout/orders/shippingAddress` - Set shipping address
- `GET /checkout/orders/{orderId}` - Get order details
- `POST /checkout/quote` - Get pricing quote (precheck)
- `POST /checkout/submitOrder` - Submit order (purchase)
- `GET /v1/users/profile` - User profile

## Sample Golden Path

1. Get homepage content
2. Search for "foundation" products
3. View product details
4. Get access token
5. Add product to cart
6. View cart totals
7. Check user profile and points

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

Run individual test scenarios:
```bash
python tests/test_golden_paths.py
```

## Design Principles

- **Token Efficient**: Minimal payload sizes with essential data
- **UX-Focused**: Endpoints designed around user journeys, not internal systems
- **Consistent**: Standardized error handling, pagination, and response formats
- **RESTful**: Predictable resource naming and HTTP status codes

The API abstracts away Sephora's complex internal systems while preserving the core user experience patterns identified in the HAR analysis.
