from fastapi import FastAPI, HTTPException, Depends, Security, status, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any
import secrets
import time
from datetime import datetime, timedelta
import uvicorn

app = FastAPI(
    title="Sephora Beauty API",
    description="Minimal API for beauty product discovery and shopping",
    version="1.0.0"
)

security = HTTPBearer()

# In-memory storage (replace with database in production)
tokens_store = {}
carts_store = {}
users_store = {
    "user1": {
        "profileId": "user1",
        "email": "user@example.com",
        "firstName": "Beauty",
        "beautyInsider": {
            "tier": "VIB",
            "points": 850,
            "pointsToNextTier": 350
        }
    }
}

# Data Models
class TokenResponse(BaseModel):
    access_token: str
    expires_in: str
    scope: str = ""

class ProductSummary(BaseModel):
    productId: str
    skuId: str
    name: str
    brandName: str
    listPrice: str
    salePrice: Optional[str] = None
    imageUrl: str
    rating: float
    reviewCount: int
    badge: Optional[str] = None
    variationDesc: Optional[str] = None

class CartItem(BaseModel):
    itemId: str
    productId: str
    skuId: str
    name: str
    brandName: str
    variationDesc: Optional[str]
    price: str
    quantity: int
    imageUrl: str

class Cart(BaseModel):
    items: List[CartItem]
    subtotal: str
    tax: str
    shipping: str
    total: str
    promoCode: Optional[str] = None
    promoDiscount: Optional[str] = None

class AddToCartRequest(BaseModel):
    skuId: str
    quantity: int

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[List[str]] = None

# Sample Data
SAMPLE_PRODUCTS = [
    {
        "productId": "P469211",
        "skuId": "2674057", 
        "name": "ILIA Super Serum Skin Tint SPF 40 Foundation",
        "brandName": "ILIA",
        "listPrice": "$48.00",
        "imageUrl": "https://www.sephora.com/productimages/sku/s2674057-main-zoom.jpg",
        "rating": 4.4,
        "reviewCount": 2006,
        "badge": "clean-at-sephora",
        "variationDesc": "light medium with neutral undertones"
    },
    {
        "productId": "P505327",
        "skuId": "2674133",
        "name": "DreamBeam Silicone-Free Mineral Sunscreen SPF 40", 
        "brandName": "Kosas",
        "listPrice": "$40.00",
        "imageUrl": "https://www.sephora.com/productimages/sku/s2674133-main-zoom.jpg",
        "rating": 3.8,
        "reviewCount": 1486,
        "badge": "clean-at-sephora"
    },
    {
        "productId": "P505694",
        "skuId": "2681799", 
        "name": "Wet Stick Moisturizing Shiny Sheer Lipstick",
        "brandName": "Kosas",
        "listPrice": "$24.00",
        "imageUrl": "https://www.sephora.com/productimages/sku/s2681799-main-zoom.jpg",
        "rating": 4.3,
        "reviewCount": 706,
        "badge": "clean-at-sephora",
        "variationDesc": "cool mauvey pink"
    }
]

# Authentication helpers
def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if token not in tokens_store:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    token_data = tokens_store[token]
    if datetime.now() > token_data["expires_at"]:
        del tokens_store[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    
    return token_data["user_id"]

# Rate limiting
rate_limit_store = {}

def check_rate_limit(identifier: str, limit: int = 100, window: int = 3600):
    now = time.time()
    if identifier not in rate_limit_store:
        rate_limit_store[identifier] = []
    
    # Clean old requests
    rate_limit_store[identifier] = [
        req_time for req_time in rate_limit_store[identifier] 
        if now - req_time < window
    ]
    
    if len(rate_limit_store[identifier]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": "3600"}
        )
    
    rate_limit_store[identifier].append(now)

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "details": []
        },
        headers=getattr(exc, 'headers', None)
    )

# Endpoints
@app.post("/v1/auth/token", response_model=TokenResponse)
async def get_token(grant_type: str = Form(...)):
    """Get access token using client credentials flow"""
    if grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="Invalid grant type")
    
    # Generate token
    access_token = secrets.token_urlsafe(32)
    expires_in = 3600  # 1 hour
    expires_at = datetime.now() + timedelta(seconds=expires_in)
    
    # Store token
    tokens_store[access_token] = {
        "user_id": "user1",  # Default user for demo
        "expires_at": expires_at
    }
    
    return TokenResponse(
        access_token=access_token,
        expires_in=str(expires_in)
    )

@app.get("/v1/content/home")
async def get_home_content(ch: str = "iPhoneApp", loc: str = "en-US"):
    """Get homepage content with featured products and banners"""
    check_rate_limit(f"home_{ch}_{loc}")
    
    return {
        "content": [
            {
                "type": "Banner",
                "title": "Up to 50% off select beauty",
                "text": "Limited time sale on bestsellers",
                "imageUrl": "https://www.sephora.com/contentimages/2025-08-sale-banner.jpg",
                "actionUrl": "/sale"
            },
            {
                "type": "ProductCarousel",
                "title": "Just Dropped",
                "products": SAMPLE_PRODUCTS
            },
            {
                "type": "CategoryLinks",
                "title": "Shop by Category",
                "links": [
                    {"label": "Makeup", "slug": "makeup-cosmetics", "imageUrl": "https://www.sephora.com/contentimages/makeup-icon.jpg"},
                    {"label": "Skincare", "slug": "skincare", "imageUrl": "https://www.sephora.com/contentimages/skincare-icon.jpg"},
                    {"label": "Fragrance", "slug": "fragrance", "imageUrl": "https://www.sephora.com/contentimages/fragrance-icon.jpg"}
                ]
            }
        ]
    }

@app.get("/v1/products/search")
async def search_products(
    q: Optional[str] = None,
    category: Optional[str] = None, 
    brand: Optional[str] = None,
    page: int = 1,
    size: int = 24,
    sort: Optional[str] = None
):
    """Search products with filters and pagination"""
    check_rate_limit(f"search_{q or 'all'}")
    
    # Filter products based on query
    filtered_products = SAMPLE_PRODUCTS.copy()
    
    if q:
        filtered_products = [
            p for p in filtered_products 
            if q.lower() in p["name"].lower() or q.lower() in p["brandName"].lower()
        ]
    
    if brand:
        filtered_products = [p for p in filtered_products if p["brandName"].lower() == brand.lower()]
    
    # Pagination
    start = (page - 1) * size
    end = start + size
    page_products = filtered_products[start:end]
    
    return {
        "products": page_products,
        "pagination": {
            "page": page,
            "size": size,
            "totalPages": (len(filtered_products) + size - 1) // size,
            "totalItems": len(filtered_products)
        },
        "filters": {
            "brands": ["ILIA", "Kosas", "Fenty Beauty"],
            "categories": ["Foundation", "Sunscreen", "Lipstick"],
            "priceRanges": ["$0-$25", "$25-$50", "$50-$100"]
        }
    }

@app.get("/v1/products/{product_id}")
async def get_product_detail(product_id: str, skuId: Optional[str] = None):
    """Get detailed product information"""
    check_rate_limit(f"product_{product_id}")
    
    # Find product
    product = next((p for p in SAMPLE_PRODUCTS if p["productId"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Return detailed view
    return {
        "productId": product["productId"],
        "name": product["name"],
        "brandName": product["brandName"],
        "description": "A revolutionary product that delivers exceptional results.",
        "skus": [
            {
                "skuId": product["skuId"],
                "listPrice": product["listPrice"],
                "salePrice": product.get("salePrice"),
                "variationValue": product.get("variationDesc", "Default"),
                "variationDesc": product.get("variationDesc"),
                "inStock": True
            }
        ],
        "images": [product["imageUrl"]],
        "rating": product["rating"],
        "reviewCount": product["reviewCount"],
        "reviews": [
            {
                "reviewId": "r1",
                "rating": 5,
                "title": "Amazing product!",
                "text": "Love this product, works perfectly for my skin.",
                "author": "BeautyLover123",
                "date": "2025-08-29",
                "verified": True
            }
        ],
        "recommendations": [p for p in SAMPLE_PRODUCTS if p["productId"] != product_id][:3]
    }

@app.get("/v1/cart", response_model=Cart)
async def get_cart(user_id: str = Depends(verify_token)):
    """Get current shopping cart contents"""
    cart_data = carts_store.get(user_id, {"items": []})
    
    # Calculate totals
    subtotal = sum(float(item["price"].replace("$", "")) * item["quantity"] for item in cart_data["items"])
    tax = subtotal * 0.08875  # NYC tax rate
    shipping = 0.0 if subtotal > 50 else 5.95
    total = subtotal + tax + shipping
    
    return Cart(
        items=[CartItem(**item) for item in cart_data["items"]],
        subtotal=f"${subtotal:.2f}",
        tax=f"${tax:.2f}", 
        shipping=f"${shipping:.2f}",
        total=f"${total:.2f}"
    )

@app.post("/v1/cart", response_model=Cart)
async def add_to_cart(request: AddToCartRequest, user_id: str = Depends(verify_token)):
    """Add item to shopping cart"""
    # Find product by SKU
    product = next((p for p in SAMPLE_PRODUCTS if p["skuId"] == request.skuId), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if user_id not in carts_store:
        carts_store[user_id] = {"items": []}
    
    # Check if item already in cart
    existing_item = next((item for item in carts_store[user_id]["items"] if item["skuId"] == request.skuId), None)
    
    if existing_item:
        existing_item["quantity"] += request.quantity
    else:
        new_item = {
            "itemId": f"item_{len(carts_store[user_id]['items']) + 1}",
            "productId": product["productId"],
            "skuId": product["skuId"],
            "name": product["name"],
            "brandName": product["brandName"],
            "variationDesc": product.get("variationDesc"),
            "price": product["listPrice"],
            "quantity": request.quantity,
            "imageUrl": product["imageUrl"]
        }
        carts_store[user_id]["items"].append(new_item)
    
    return await get_cart(user_id)

class UpdateCartItemRequest(BaseModel):
    quantity: int

@app.put("/v1/cart/items/{item_id}", response_model=Cart)
async def update_cart_item(item_id: str, request: UpdateCartItemRequest, user_id: str = Depends(verify_token)):
    """Update cart item quantity"""
    if user_id not in carts_store:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    item = next((item for item in carts_store[user_id]["items"] if item["itemId"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if request.quantity <= 0:
        carts_store[user_id]["items"].remove(item)
    else:
        item["quantity"] = request.quantity
    
    return await get_cart(user_id)

@app.delete("/v1/cart/items/{item_id}")
async def remove_cart_item(item_id: str, user_id: str = Depends(verify_token)):
    """Remove item from cart"""
    if user_id not in carts_store:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    item = next((item for item in carts_store[user_id]["items"] if item["itemId"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    carts_store[user_id]["items"].remove(item)
    return {"message": "Item removed"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
