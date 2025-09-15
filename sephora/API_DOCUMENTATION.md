# Sephora Beauty API Documentation

## Overview

This minimal API emulates key Sephora user journeys for beauty product discovery and shopping. It abstracts the complex internal Sephora systems (1700+ endpoints from HAR analysis) into a clean, RESTful interface focused on user experience.

## Live API Documentation

Once the server is running, access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Key Design Decisions

Based on HAR analysis of 1752 requests, we identified and consolidated:

1. **Authentication**: OAuth2 client credentials flow (similar to Sephora's actual implementation)
2. **Content Management**: Modular homepage system with typed content blocks
3. **Product Catalog**: Unified search/browse with consistent filtering
4. **Shopping Cart**: Stateful cart management with real-time pricing
5. **User Profiles**: Beauty Insider integration with rewards/points
6. **Error Handling**: Consistent error format with 429 rate limiting

## API Endpoints

### Authentication
```
POST /v1/auth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
```

### Homepage Content
```
GET /v1/content/home?ch=iPhoneApp&loc=en-US
```

### Product Search
```
GET /v1/products/search?q=foundation&brand=ILIA&sort=RATING&page=1&size=24
```

### Product Details
```
GET /v1/products/P469211?skuId=2674057
```

### Shopping Cart (Authenticated)
```
GET /v1/cart
POST /v1/cart
  {
    "skuId": "2674057",
    "quantity": 1
  }
PUT /v1/cart/items/{itemId}
  {
    "quantity": 2
  }
DELETE /v1/cart/items/{itemId}
```

### User Profile (Authenticated)
```
GET /v1/users/profile
```

## Testing

### Unit Tests
```bash
python tests/test_golden_paths.py
```

### cURL Examples

Get access token:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" | jq -r .access_token)
```

Add to cart:
```bash
curl -X POST http://localhost:8000/v1/cart \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"skuId": "2674057", "quantity": 1}'
```

## Performance Characteristics

- **Rate Limiting**: 100 requests per hour per identifier
- **Token Expiry**: 1 hour (3600 seconds)
- **Response Time**: < 50ms for all endpoints (in-memory storage)
- **Payload Size**: Optimized for mobile (minimal JSON responses)

## Data Model Highlights

### Product Summary
- Minimal fields for list views
- Includes badges (clean-at-sephora, etc.)
- Rating and review count
- Price with sale support

### Cart
- Real-time tax calculation (NYC rate: 8.875%)
- Free shipping threshold ($50)
- Item-level management
- Promo code support (structure defined)

### User Profile
- Beauty Insider tiers (Insider, VIB, Rouge)
- Points and next tier tracking
- Profile basics

## Security

- Bearer token authentication
- Rate limiting with Retry-After headers
- Input validation via Pydantic models
- HTTPException with consistent error responses

## Production Considerations

For production deployment:
1. Replace in-memory storage with database (PostgreSQL/MongoDB)
2. Implement Redis for token/session management
3. Add API gateway for rate limiting
4. Implement real payment processing
5. Add comprehensive logging and monitoring
6. Deploy with Docker/Kubernetes
7. Implement caching layer (CDN for product images)
8. Add search indexing (Elasticsearch)

## HAR Analysis Insights

From analyzing 1752 requests in the HAR file:
- 1400+ were image/asset requests
- ~100 were core API calls
- Key patterns: OAuth2, modular content, product catalog, user profiles
- Consolidated into 7 core endpoints representing main user journeys

## Compliance Notes

This implementation:
- Uses public product data from HAR file
- Does not include actual Sephora business logic
- Intended for educational/demonstration purposes
- Should not be used to scrape or access Sephora production systems
