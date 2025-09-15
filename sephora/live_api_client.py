#!/usr/bin/env python3
"""
Live Sephora API Client - Makes REAL API calls to Sephora's servers
Reverse engineered from HAR files
"""

import httpx
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

class SephoraLiveAPI:
    """Direct API client for Sephora's real endpoints"""
    
    def __init__(self):
        # Real API configuration from HAR analysis
        self.base_url = "https://api.sephora.com"
        self.api_key = "a1YNj37xKo1e6uLGAXgG52Bp2qWaueNT"  # Real API key from HAR
        
        # Real headers from HAR
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "br;q=1.0, gzip;q=0.9, deflate;q=0.8",
            "x-api-key": self.api_key,
            "Accept-Language": "en-US;q=1.0",
            "x-sephora-channel": "iPhone17,2",
            "User-Agent": "Sephora 25.17, iOS 18.6.1, iPhone17,2",
            "x-requested-source": "Sephora 25.17, iOS 18.6.1, iPhone17,2",
        }
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0,
            follow_redirects=True
        )
    
    async def get_home_content(self) -> Dict:
        """Get LIVE homepage content from Sephora API"""
        try:
            response = await self.client.get(
                "/v1/content/home",
                params={"ch": "iPhoneApp", "loc": "en-US"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching home content: {e}")
            raise
    
    async def search_products(self, query: str, page: int = 1, size: int = 30) -> Dict:
        """Search for products using LIVE Sephora API"""
        try:
            response = await self.client.get(
                "/v3/catalog/search",
                params={
                    "q": query,
                    "currentPage": page,
                    "pageSize": size,
                    "content": "true",
                    "ch": "iPhoneApp",
                    "loc": "en-US"
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error searching products: {e}")
            raise
    
    async def get_product(self, product_id: str, sku_id: Optional[str] = None) -> Dict:
        """Get LIVE product details from Sephora API"""
        try:
            url = f"/v3/catalog/products/{product_id}"
            params = {"ch": "iPhoneApp", "loc": "en-US"}
            if sku_id:
                params["preferedSku"] = sku_id
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching product {product_id}: {e}")
            raise
    
    async def get_category_products(self, category_id: str, page: int = 1) -> Dict:
        """Get LIVE products from a category"""
        try:
            response = await self.client.get(
                f"/v1/catalog/categories/{category_id}",
                params={
                    "currentPage": page,
                    "pageSize": 30,
                    "content": "true",
                    "includeRegionsMap": "false",
                    "ch": "iPhoneApp",
                    "loc": "en-US"
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching category {category_id}: {e}")
            raise
    
    async def get_new_arrivals(self) -> Dict:
        """Get LIVE new arrivals from Sephora"""
        try:
            # New arrivals category ID from HAR analysis
            return await self.get_category_products("cat150006")
        except Exception as e:
            print(f"Error fetching new arrivals: {e}")
            raise
    
    async def get_bestsellers(self) -> Dict:
        """Get LIVE bestsellers from Sephora"""
        try:
            response = await self.client.get(
                "/v3/catalog/search",
                params={
                    "q": "",
                    "sortBy": "P_BEST_SELLING:-1",
                    "currentPage": 1,
                    "pageSize": 30,
                    "content": "true",
                    "ch": "iPhoneApp",
                    "loc": "en-US"
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching bestsellers: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Singleton instance
_api_client: Optional[SephoraLiveAPI] = None

def get_live_client() -> SephoraLiveAPI:
    """Get or create the live API client"""
    global _api_client
    if _api_client is None:
        _api_client = SephoraLiveAPI()
    return _api_client


# Test the live API
async def test_live_api():
    """Test that we can make real API calls"""
    client = get_live_client()
    
    print("Testing LIVE Sephora API...")
    print("-" * 50)
    
    # Test home content
    print("\n1. Fetching LIVE home content...")
    try:
        home = await client.get_home_content()
        items = home.get('data', {}).get('items', [])
        print(f"   ✓ Got {len(items)} content blocks from LIVE API")
        
        # Show some real content
        for item in items[:3]:
            item_type = item.get('type', 'Unknown')
            print(f"   - {item_type}: {item.get('title', 'N/A')}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test product search
    print("\n2. Searching for 'foundation' (LIVE)...")
    try:
        results = await client.search_products("foundation")
        products = results.get('products', [])
        print(f"   ✓ Found {len(products)} products from LIVE search")
        
        # Show first few products
        for p in products[:3]:
            sku = p.get('currentSku', {})
            name = p.get('displayName', 'Unknown')
            price = sku.get('listPrice', 'N/A')
            print(f"   - {name}: {price}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test bestsellers
    print("\n3. Fetching LIVE bestsellers...")
    try:
        bestsellers = await client.get_bestsellers()
        products = bestsellers.get('products', [])
        print(f"   ✓ Got {len(products)} bestsellers from LIVE API")
        
        for p in products[:3]:
            sku = p.get('currentSku', {})
            name = p.get('displayName', 'Unknown')
            brand = p.get('brandName', 'Unknown')
            print(f"   - {brand} - {name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    await client.close()
    print("\n" + "=" * 50)
    print("LIVE API TEST COMPLETE!")


if __name__ == "__main__":
    asyncio.run(test_live_api())
