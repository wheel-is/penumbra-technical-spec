#!/usr/bin/env python3
"""
Load real Sephora data from HAR-extracted JSON files
Fails loudly if data is not available
"""

import json
from pathlib import Path

def load_data():
    """Load real data from JSON files - required, no fallbacks"""
    # Check if we're running in Modal (files are in /app)
    if Path('/app/home_content_real.json').exists():
        base_path = Path('/app')
    else:
        base_path = Path(__file__).parent
    
    # Load home content data
    home_file = base_path / 'home_content_real.json'
    if not home_file.exists():
        raise FileNotFoundError(f"FATAL: Required file {home_file} not found")
    
    with open(home_file, 'r') as f:
        HOME_CONTENT_DATA = json.load(f)
    
    # Load product search data
    search_file = base_path / 'product_search_real.json'
    if not search_file.exists():
        raise FileNotFoundError(f"FATAL: Required file {search_file} not found")
    
    with open(search_file, 'r') as f:
        PRODUCT_SEARCH_DATA = json.load(f)
    
    # Build products cache from data
    products_cache = {}
    
    # Add products from search data
    for product in PRODUCT_SEARCH_DATA.get('products', []):
        sku = product.get('currentSku', {})
        sku_id = sku.get('skuId')
        if sku_id:
            products_cache[sku_id] = {
                'productId': product.get('productId', ''),
                'skuId': sku_id,
                'name': product.get('displayName', ''),
                'brandName': product.get('brandName', ''),
                'listPrice': sku.get('listPrice', '$0.00'),
                'salePrice': sku.get('salePrice'),
                'imageUrl': product.get('heroImage', ''),
                'rating': product.get('rating', 0),
                'reviewCount': product.get('reviews', 0),
                'type': 'Standard',
                'typeDisplayName': 'Standard',
                'variationDesc': sku.get('variationDesc', ''),
                'isNew': sku.get('isNew', False),
                'isLimitedEdition': sku.get('isLimitedEdition', False),
                'targetUrl': product.get('targetUrl', ''),
                'inStock': not sku.get('isOutOfStock', False)
            }
    
    # Add products from home content (both direct skuList and nested in items)
    items = HOME_CONTENT_DATA.get('data', {}).get('items', [])
    for item in items:
        # Direct skuList (ProductList items)
        if 'skuList' in item:
            for sku in item['skuList']:
                sku_id = sku.get('skuId')
                if sku_id and sku_id not in products_cache:
                    products_cache[sku_id] = {
                        'productId': sku.get('productId', ''),
                        'skuId': sku_id,
                        'name': sku.get('productName', ''),
                        'brandName': sku.get('brandName', ''),
                        'listPrice': sku.get('listPrice', '$0.00'),
                        'salePrice': sku.get('salePrice'),
                        'imageUrl': f"https://www.sephora.com/productimages/sku/s{sku_id}-main-zoom.jpg?imwidth=270",
                        'rating': sku.get('starRatings', 0),
                        'reviewCount': sku.get('reviewsCount', 0),
                        'type': 'Standard',
                        'typeDisplayName': 'Standard',
                        'variationDesc': sku.get('variationDesc', sku.get('variationValue', '')),
                        'isNew': sku.get('isNew', False),
                        'isLimitedEdition': sku.get('isLimitedEdition', False),
                        'targetUrl': sku.get('targetUrl', ''),
                        'inStock': True
                    }
        
        # Nested items (Recap items)
        if 'items' in item:
            for nested_item in item['items']:
                if 'skuList' in nested_item:
                    for sku in nested_item['skuList']:
                        sku_id = sku.get('skuId')
                        if sku_id and sku_id not in products_cache:
                            products_cache[sku_id] = {
                                'productId': sku.get('productId', ''),
                                'skuId': sku_id,
                                'name': sku.get('productName', ''),
                                'brandName': sku.get('brandName', ''),
                                'listPrice': sku.get('listPrice', '$0.00'),
                                'salePrice': sku.get('salePrice'),
                                'imageUrl': f"https://www.sephora.com/productimages/sku/s{sku_id}-main-zoom.jpg?imwidth=270",
                                'rating': sku.get('starRatings', 0),
                                'reviewCount': sku.get('reviewsCount', 0),
                                'type': 'Standard',
                                'typeDisplayName': 'Standard',
                                'variationDesc': sku.get('variationDesc', sku.get('variationValue', '')),
                                'isNew': sku.get('isNew', False),
                                'isLimitedEdition': sku.get('isLimitedEdition', False),
                                'targetUrl': sku.get('targetUrl', ''),
                                'inStock': True
                            }
    
    REAL_PRODUCTS = list(products_cache.values())
    
    if not REAL_PRODUCTS:
        raise RuntimeError("FATAL: No product data could be extracted from JSON files")
    
    return HOME_CONTENT_DATA, PRODUCT_SEARCH_DATA, REAL_PRODUCTS

# Load data when module is imported
HOME_CONTENT_DATA, PRODUCT_SEARCH_DATA, REAL_PRODUCTS = load_data()
print(f"Real data loaded with {len(REAL_PRODUCTS)} products")
