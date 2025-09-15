#!/usr/bin/env python3
"""
Modal deployment of Sephora Beauty API with LIVE API Integration
Makes REAL API calls to Sephora's servers for live, real-time data
"""

import os
import modal
from modal import App, Image, asgi_app
from fastapi import FastAPI, HTTPException, status, Request, Body
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import time
import yaml
from pathlib import Path
import httpx
import asyncio
import base64
import json
import uuid
from datetime import datetime, timedelta
import random

# Create Modal app with dependencies
app = App("sephora-beauty-api-live")

# Create custom image with dependencies
image = (
    Image.debian_slim()
    .pip_install(
        "fastapi",
        "uvicorn",
        "pyyaml",
        "httpx",  # For making real API calls
        "python-multipart"
    )
)

# Add local files to the image
image = image.add_local_file("openapi.yaml", "/app/openapi.yaml")
image = image.add_local_file("sephora_purchase.har", "/app/sephora_purchase.har")
image = image.add_local_file("sephora_reauth.har", "/app/sephora_reauth.har")
# Add the fresh auth HAR if it exists
if os.path.exists("reauth2.har"):
    image = image.add_local_file("reauth2.har", "/app/reauth2.har")

# Create FastAPI app
fastapi_app = FastAPI(
    title="Sephora Beauty API - LIVE",
    version="2.0.0",
    description="Real-time Sephora API with live data from actual servers"
)

# Add CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers to load freshest auth artifacts from HAR
def _load_refresh_from_har() -> Dict[str, Any]:
    """Parse reauth2.har or sephora_reauth.har to extract fresh tokens."""
    try:
        # Try reauth2.har first (fresher), then sephora_reauth.har
        har_paths = [
            Path("/app/reauth2.har") if Path("/app/reauth2.har").exists() else (Path(__file__).parent / "reauth2.har"),
            Path("/app/sephora_reauth.har") if Path("/app/sephora_reauth.har").exists() else (Path(__file__).parent / "sephora_reauth.har")
        ]
        
        for har_path in har_paths:
            if not har_path.exists():
                continue
                
            with open(har_path, "r") as f:
                har = json.load(f)
            
            # Look for /session endpoint which has the freshest tokens
            for entry in har.get("log", {}).get("entries", []):
                req = entry.get("request", {})
                url = req.get("url", "")
                if "/v1/dotcom/auth/v2/session" in url:
                    resp = entry.get("response", {})
                    content = resp.get("content", {})
                    text = content.get("text")
                    if text:
                        try:
                            data = json.loads(text)
                            if "accessToken" in data:
                                print(f"INFO: Loaded fresh auth from {har_path.name}")
                                return {
                                    "accessToken": data.get("accessToken"),
                                    "refreshToken": data.get("refreshToken"),
                                    "atExp": data.get("atExp"),
                                    "rtExp": data.get("rtExp")
                                }
                        except Exception:
                            pass
            
            # Fallback to refreshToken endpoint
            for entry in har.get("log", {}).get("entries", []):
                req = entry.get("request", {})
                url = req.get("url", "")
                if "/v1/dotcom/auth/v2/refreshToken" in url:
                    resp = entry.get("response", {})
                    content = resp.get("content", {})
                    text = content.get("text")
                    if text:
                        try:
                            data = json.loads(text)
                            if "accessToken" in data:
                                return {
                                    "accessToken": data.get("accessToken"),
                                    "refreshToken": data.get("refreshToken"),
                                    "atExp": data.get("atExp"),
                                    "rtExp": data.get("rtExp")
                                }
                        except Exception:
                            pass
            
            # If we found a HAR file, don't check the next one
            if har_path.exists():
                break
                
        return {}
    except Exception as e:
        print(f"WARNING: Could not load auth from HAR: {e}")
        return {}

HAR_AUTH = _load_refresh_from_har()

# ==================== SESSION MANAGER (FRESH BOOTSTRAP) ====================
class SessionManager:
    """Bootstraps fresh Sephora sessions to eliminate 403/429 errors"""
    def __init__(self):
        # Sephora client credentials (from HAR analysis)
        self.client_id = "a1YNj37xKo1e6uLGAXgG52Bp2qWaueNT"
        self.client_secret = "TT3QfRe0rs4LghAI"
        self.api_key = "a1YNj37xKo1e6uLGAXgG52Bp2qWaueNT"
        
        # Session state
        self.cookies = ""
        self.bearer_token = ""
        # Seed Seph-Access-Token and refresh token from HAR if available
        self.access_token = HAR_AUTH.get("accessToken", "")
        self.refresh_token = HAR_AUTH.get("refreshToken", "")
        at_exp = HAR_AUTH.get("atExp")
        try:
            self.token_expiry = datetime.fromtimestamp(int(at_exp)) if at_exp else datetime.utcnow()
        except Exception:
            self.token_expiry = datetime.utcnow()
        self.session_expiry = datetime.utcnow()
        self.device_id = "BD4DD90A-BCE8-411F-8C24-25292242E2F7"
        
        # HTTP client for auth calls (OAuth endpoints are on api-developer.sephora.com)
        self.client = httpx.AsyncClient(
            base_url="https://api-developer.sephora.com",
            timeout=30.0,
            headers={
                "User-Agent": "Sephora 25.17.1, iOS 18.6.2, iPhone17,2",
                "Accept": "application/json"
            }
        )

    async def bootstrap_session(self):
        """Bootstrap a fresh session with Akamai cookies and OAuth tokens"""
        print("INFO: Bootstrapping fresh Sephora session...")
        
        try:
            # Step 1a: Hit api.sephora.com header/footer to set site cookies (Akamai domain cookies)
            async with httpx.AsyncClient(base_url="https://api.sephora.com", timeout=30.0, headers={
                "User-Agent": "Sephora 25.17.1, iOS 18.6.2, iPhone17,2",
                "Accept": "application/json",
                "x-api-key": self.api_key
            }) as site_client:
                hf_resp = await site_client.get(
                    "/v1/content/globalElements/headerFooter",
                    params={"ch": "iPhoneApp", "loc": "en-US", "zipcode": "20147"}
                )
                hf_resp.raise_for_status()

                site_cookie_parts = [f"{c.name}={c.value}" for c in site_client.cookies.jar]

            # Step 1b: Get util/configuration on developer to set _abck and bm_sz
            cfg_resp = await self.client.get(
                "/v1/dotcom/util/configuration",
                params={"ch": "iPhoneApp"}
            )
            cfg_resp.raise_for_status()
            dev_cookie_parts = [f"{c.name}={c.value}" for c in self.client.cookies.jar]

            # Also hit pageCheckout to finalize checkout cookies
            async with httpx.AsyncClient(base_url="https://api.sephora.com", timeout=30.0, headers={
                "User-Agent": "Sephora 25.17.1, iOS 18.6.2, iPhone17,2",
                "Accept": "application/json",
                "x-api-key": self.api_key
            }) as site_client2:
                pc_resp = await site_client2.get(
                    "/v1/content/checkout/pageCheckout",
                    params={"ch": "iPhoneApp", "loc": "en-US", "zipcode": "20147"}
                )
                pc_resp.raise_for_status()
                page_cookie_parts = [f"{c.name}={c.value}" for c in site_client2.cookies.jar]

            # Merge and add device/site flags
            cookie_parts = site_cookie_parts + dev_cookie_parts + page_cookie_parts + [
                f"ADID={self.device_id}",
                "site_language=en",
                "site_locale=us",
                "ship_country=us",
                "rcps_cc=true",
                "rcps_po=true",
                "rcps_ss=true"
            ]

            # De-duplicate by name keeping last seen
            cookie_map = {}
            for kv in cookie_parts:
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    cookie_map[k.strip()] = v
            self.cookies = "; ".join([f"{k}={v}" for k, v in cookie_map.items()])
            print(f"INFO: Fresh cookies obtained: {len(cookie_map)} unique cookies")
            
            # Step 2: Get OAuth bearer token via client_credentials
            auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            
            token_response = await self.client.post(
                "/v1/oauth2/token",
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Cookie": self.cookies
                },
                data="grant_type=client_credentials"
            )
            token_response.raise_for_status()
            
            token_data = token_response.json()
            self.bearer_token = token_data["access_token"]
            self.token_expiry = datetime.utcnow() + timedelta(seconds=int(token_data["expires_in"]))
            print(f"INFO: OAuth bearer token obtained, expires: {self.token_expiry}")
            
            # Step 3: Use fresh token from HAR if available, otherwise use bearer token
            if HAR_AUTH.get("accessToken") and not self.access_token:
                self.access_token = HAR_AUTH["accessToken"]
                self.refresh_token = HAR_AUTH.get("refreshToken", "")
                at_exp = HAR_AUTH.get("atExp")
                if at_exp:
                    try:
                        self.token_expiry = datetime.fromtimestamp(int(at_exp))
                        print(f"INFO: Using fresh Seph-Access-Token from HAR, expires: {self.token_expiry}")
                    except:
                        pass
            
            if not self.access_token:
                self.access_token = self.bearer_token
                print("INFO: Using bearer token as access token")
            
            # Session is valid for 20 minutes (Akamai cookie lifetime)
            self.session_expiry = datetime.utcnow() + timedelta(minutes=20)
            
            print("INFO: Session bootstrap completed successfully")
            
        except Exception as e:
            print(f"ERROR: Session bootstrap failed: {e}")
            # Set far future expiry to avoid retry loops
            self.session_expiry = datetime.utcnow() + timedelta(hours=1)
            raise

    async def ensure_fresh_session(self):
        """Ensure we have a fresh, valid session"""
        now = datetime.utcnow()
        
        # Add rate limiting to avoid 429s
        if hasattr(self, '_last_request'):
            time_since_last = (now - self._last_request).total_seconds()
            if time_since_last < 2:  # Wait at least 2 seconds between requests
                await asyncio.sleep(2 - time_since_last)
        self._last_request = now
        
        # Check if session needs refresh (within 2 minutes of expiry)
        if now >= self.session_expiry - timedelta(minutes=2):
            await self.bootstrap_session()
        
        # Check if token needs refresh (within 5 minutes of expiry)
        elif now >= self.token_expiry - timedelta(minutes=5):
            await self.refresh_access_token()

    async def refresh_access_token(self):
        """Refresh OAuth token using existing session"""
        if not self.refresh_token:
            # No refresh token available, do full bootstrap
            await self.bootstrap_session()
            return
            
        try:
            print("INFO: Refreshing OAuth token...")
            
            response = await self.client.post(
                "/v1/dotcom/auth/v2/refreshToken",
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                    "Content-Type": "application/json",
                    "Cookie": self.cookies
                },
                json={
                    "refreshToken": self.refresh_token,
                    "ssiToken": "",
                    "accessToken": self.access_token,
                    "email": "dojarob@gmail.com"
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Update tokens
            # Prefer Seph-Access-Token header if present
            sat = response.headers.get("Seph-Access-Token")
            self.access_token = sat or data.get("accessToken", self.access_token)
            self.refresh_token = data["refreshToken"]
            self.token_expiry = datetime.fromtimestamp(int(data["atExp"]))
            
            print(f"INFO: Token refreshed successfully, new expiry: {self.token_expiry}")
            
        except Exception as e:
            print(f"WARNING: Token refresh failed: {e}")
            # Don't bootstrap again - just extend expiry to avoid loops
            self.token_expiry = datetime.utcnow() + timedelta(hours=1)

    def auth_headers(self) -> Dict[str, str]:
        """Get complete auth headers for API requests"""
        return {
            "Cookie": self.cookies,
            "Authorization": f"Bearer {self.bearer_token}",
            "Seph-Access-Token": self.access_token,
            "x-api-key": self.api_key,
            "ADID": self.device_id,
            "IAV": "25.17",
            "Mobile_Efm_Id": self.device_id,
            "x-sephora-channel": "iPhone17,2",
            "User-Agent": "Sephora 25.17.1, iOS 18.6.2, iPhone17,2",
            "Accept-Encoding": "br;q=1.0, gzip;q=0.9, deflate;q=0.8",
            "Accept": "application/json",
            "Accept-Language": "en-US;q=1.0",
            "x-requested-source": "Sephora 25.17.1, iOS 18.6.2, iPhone17,2"
        }

    def checkout_headers(self) -> Dict[str, str]:
        """Headers specifically for checkout calls (mirror HAR exactly: no Authorization)."""
        # From HAR request #93 - checkout/order/init
        return {
            "Cookie": self.cookies,
            "User-Agent": "Sephora 25.17.1, iOS 18.6.2, iPhone17,2",
            "x-requested-source": "Sephora 25.17.1, iOS 18.6.2, iPhone17,2",
            "IAV": "25.17.1",  # Note: 25.17.1 not 25.17
            "Accept-Language": "en-US;q=1.0, zh-Hant-US;q=0.9",
            "Mobile_Efm_Id": self.device_id,
            "Seph-Access-Token": self.access_token,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "x-sephora-channel": "iPhone17,2",
            "Accept-Encoding": "br;q=1.0, gzip;q=0.9, deflate;q=0.8",
            "ADID": self.device_id
        }

    def merge_response_cookies(self, response: httpx.Response) -> None:
        """Merge Set-Cookie from a response into the session cookie header."""
        try:
            cookie_map: Dict[str, str] = {}
            # Start with existing cookies
            for kv in (self.cookies or "").split("; "):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    cookie_map[k] = v
            # Merge from the response client's cookie jar if available
            if hasattr(response, "request") and hasattr(response.request, "extensions"):
                pass  # no-op
            # httpx exposes cookies on Response via .cookies.jar
            try:
                for c in response.cookies.jar:
                    cookie_map[c.name] = c.value
            except Exception:
                pass
            self.cookies = "; ".join([f"{k}={v}" for k, v in cookie_map.items()])
        except Exception:
            return

_session_manager = SessionManager()

# ==================== LIVE API CLIENT ====================
class SephoraLiveAPI:
    """Direct API client for Sephora's real endpoints"""
    
    def __init__(self):
        # Real API configuration from HAR analysis
        self.base_url = "https://api.sephora.com"
        self.api_key = "a1YNj37xKo1e6uLGAXgG52Bp2qWaueNT"  # Real API key from HAR
        
        # Real headers from HAR - exact match from working search request #220
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "br;q=1.0, gzip;q=0.9, deflate;q=0.8",
            "IAV": "25.17",
            "x-api-key": self.api_key,
            "Accept-Language": "en-US;q=1.0, zh-Hant-US;q=0.9",
            "x-sephora-channel": "iPhone17,2",
            "Mobile_Efm_Id": "BD4DD90A-BCE8-411F-8C24-25292242E2F7",
            "User-Agent": "Sephora 25.17, iOS 18.6.1, iPhone17,2",
            "x-requested-source": "Sephora 25.17, iOS 18.6.1, iPhone17,2",
            "Seph-Access-Token": "" # Will be set dynamically
        }
        
        self.client = None
    
    async def ensure_client(self):
        """Ensure HTTP client is initialized with fresh session"""
        await _session_manager.ensure_fresh_session()
        
        # Update headers with fresh session auth
        session_headers = _session_manager.auth_headers()
        self.headers.update(session_headers)

        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=30.0,
                follow_redirects=True
            )
        else:
            # Update headers on existing client
            self.client.headers = self.headers
    
    async def get_home_content(self) -> Dict:
        """Get LIVE homepage content from Sephora API"""
        await self.ensure_client()
        try:
            response = await self.client.get(
                "/v1/content/home",
                params={"ch": "iPhoneApp", "loc": "en-US"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching home content: {e}")
            # Return a structured error response
            return {"error": str(e), "data": {"items": []}}
    
    async def search_products(self, query: str = "", category: str = None, page: int = 1, size: int = 30) -> Dict:
        """Search for products using LIVE Sephora API - EXACT params from working HAR request #220"""
        await self.ensure_client()
        try:
            # EXACT parameters from working search request #220 in sephora_ux_comprehensive.har
            params = {
                "callAdSvc": "true",
                "ch": "iPhoneApp", 
                "constructorClientID": "BD4DD90A-BCE8-411F-8C24-25292242E2F7",
                "constructorSessionID": "1",
                "currentPage": str(page),
                "forcePriceRangeRwd": "true",
                "includeEDD": "true",
                "loc": "en-US",
                "ph": "10000000",
                "pl": "0",
                "sortBy": "",
                "targetSearchEngine": "nlp",
                "type": "keyword"
            }

            if query:
                params["q"] = query
            
            response = await self.client.get(
                "/v2/catalog/search",
                params=params
            )
            print(f"INFO: Calling Sephora search API: {response.url}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error searching products: {e}")
            return {"products": [], "error": str(e)}
    
    async def get_product(self, product_id: str, sku_id: Optional[str] = None) -> Dict:
        """Get LIVE product details from Sephora API"""
        await self.ensure_client()
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
            return None

# Create singleton instance
_live_api = SephoraLiveAPI()

# ==================== IN-MEMORY STORES ====================
# Using real user data from HAR (sephora_purchase.har request #68)
default_user_id = "4321676833524480"  # Real profile ID from HAR
carts_store = {
    default_user_id: {"items": []}
}
users_store = {
    default_user_id: {
        "profileId": default_user_id,
        "email": "dojarob@gmail.com",  # Real email from HAR
        "firstName": "Will",  # Real first name from HAR
        "lastName": "Roberts",  # Real last name from HAR
        "phoneNumber": "9167995790",  # Real phone from HAR
        "beautyInsider": {
            "tier": "BI",  # Real tier from HAR (Beauty Insider base tier)
            "points": 0,  # Real points from HAR
            "pointsToNextTier": 350,  # Real value from HAR
            "vibSpendingForYear": 0,  # Real spending from HAR
            "accountStatus": "ACTIVE"  # Real status from HAR
        }
    }
}

# Order storage
orders_store = {}
order_counter = 735700000000  # Start with Sephora-like order IDs

def get_tax_rate(state: str = "CA", city: str = None) -> float:
    """Get tax rate based on location - using real rates from HAR data"""
    tax_rates = {
        "CA": {"default": 0.08625, "cities": {"San Francisco": 0.08625, "Los Angeles": 0.095}},
        "NY": {"default": 0.08, "cities": {"New York": 0.08875}},
        "TX": {"default": 0.0825},
        "OR": {"default": 0.0},
        "FL": {"default": 0.06}
    }
    
    if state not in tax_rates:
        return 0.0875  # Default rate
    
    state_config = tax_rates[state]
    if isinstance(state_config, dict):
        if city and "cities" in state_config and city in state_config["cities"]:
            return state_config["cities"][city]
        return state_config.get("default", 0.0875)
    return state_config

# ==================== API ENDPOINTS ====================

@fastapi_app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "sephora-beauty-api-live",
        "version": "2.0.0",
        "mode": "LIVE_API",
        "api_endpoint": "https://api.sephora.com",
        "timestamp": datetime.utcnow().isoformat()
    }

@fastapi_app.get("/")
async def root():
    return {"message": "Sephora LIVE API is running"}

@fastapi_app.get("/test-session", operation_id="test_session")
async def test_session():
    """Test session bootstrap"""
    try:
        await _session_manager.ensure_fresh_session()
        headers = _session_manager.checkout_headers()
        return {
            "status": "success",
            "cookies_length": len(_session_manager.cookies),
            "bearer_token_length": len(_session_manager.bearer_token) if _session_manager.bearer_token else 0,
            "headers_count": len(headers),
            "session_expiry": _session_manager.session_expiry.isoformat(),
            "token_expiry": _session_manager.token_expiry.isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

@fastapi_app.get("/home", operation_id="get_home_content")
async def get_home_content(ch: str = "iPhoneApp", loc: str = "en-US"):
    """Get LIVE homepage content directly from Sephora API"""
    
    # Get LIVE data from Sephora
    live_data = await _live_api.get_home_content()
    
    # Transform the response to our format
    content_blocks = []
    items = live_data.get('data', {}).get('items', [])
    
    for item in items:
        item_type = item.get('type')
        
        # Handle ProductList items
        if item_type == 'ProductList' and 'skuList' in item:
            sku_list = item.get('skuList', [])
            if sku_list:
                products = []
                for sku in sku_list[:20]:  # Limit for response size
                    products.append({
                        'productId': sku.get('productId', ''),
                        'skuId': sku.get('skuId', ''),
                        'name': sku.get('productName', ''),
                        'brandName': sku.get('brandName', ''),
                        'listPrice': sku.get('listPrice', '$0.00'),
                        'salePrice': sku.get('salePrice'),
                        'imageUrl': f"https://www.sephora.com/productimages/sku/s{sku.get('skuId', '')}-main-zoom.jpg?imwidth=270",
                        'rating': sku.get('starRatings', 0),
                        'reviewCount': sku.get('reviewsCount', 0),
                        'inStock': True
                    })
                
                if products:
                    content_blocks.append({
                        "type": "ProductCarousel",
                        "title": item.get('title', 'Products'),
                        "products": products
                    })
        
        # Handle Recap items with nested products
        elif item_type == 'Recap':
            recap_items = item.get('items', [])
            for recap_item in recap_items:
                if 'skuList' in recap_item:
                    sku_list = recap_item.get('skuList', [])
                    if sku_list:
                        products = []
                        for sku in sku_list[:8]:
                            products.append({
                                'productId': sku.get('productId', ''),
                                'skuId': sku.get('skuId', ''),
                                'name': sku.get('productName', ''),
                                'brandName': sku.get('brandName', ''),
                                'listPrice': sku.get('listPrice', '$0.00'),
                                'imageUrl': f"https://www.sephora.com/productimages/sku/s{sku.get('skuId', '')}-main-zoom.jpg?imwidth=270",
                                'inStock': True
                            })
                        
                        if products:
                            content_blocks.append({
                                "type": "ProductCarousel",
                                "title": recap_item.get('title', 'Products'),
                                "products": products
                            })
    
    # Add a message about live data
    if content_blocks:
        content_blocks.insert(0, {
            "type": "LiveDataNotice",
            "message": f"LIVE DATA from Sephora API at {datetime.utcnow().isoformat()}",
            "itemCount": len(content_blocks)
        })
    
    return {"content": content_blocks, "isLiveData": True}

@fastapi_app.get("/search", operation_id="search_products")
async def search_products(
    query: Optional[str] = None,
    category: Optional[str] = None,
    minPrice: Optional[float] = None,
    maxPrice: Optional[float] = None,
    brand: Optional[str] = None,
    page: int = 1,
    pageSize: int = 30
):
    """Search products using LIVE Sephora API"""
    
    try:
        # Get LIVE search results
        results = await _live_api.search_products(
            query=query or "",
            category=category,
            page=page,
            size=pageSize
        )
    except Exception as e:
        print(f"ERROR: Search failed with auth error: {e}")
        # Return empty results instead of crashing
        return {
            "products": [],
            "totalProducts": 0,
            "page": page,
            "pageSize": pageSize,
            "isLiveData": False,
            "error": f"Authentication failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Transform Sephora response to our format
    products = []
    for product in results.get('products', []):
        sku = product.get('currentSku', {})
        
        # Apply price filters
        price_str = sku.get('listPrice', '$0').replace('$', '').replace(',', '')
        try:
            price = float(price_str)
            if minPrice and price < minPrice:
                continue
            if maxPrice and price > maxPrice:
                continue
        except:
            pass
        
        # Apply brand filter
        if brand and brand.lower() not in product.get('brandName', '').lower():
            continue
        
        products.append({
            'productId': product.get('productId', ''),
            'skuId': sku.get('skuId', ''),
            'name': product.get('displayName', ''),
            'brandName': product.get('brandName', ''),
            'price': sku.get('listPrice', '$0.00'),
            'salePrice': sku.get('salePrice'),
            'imageUrl': product.get('heroImage', ''),
            'rating': product.get('rating', 0),
            'reviewCount': product.get('reviews', 0),
            'inStock': not sku.get('isOutOfStock', False)
        })
    
    return {
        "products": products,
        "totalProducts": len(products),
        "page": page,
        "pageSize": pageSize,
        "isLiveData": True,
        "timestamp": datetime.utcnow().isoformat()
    }

@fastapi_app.get("/products/{product_id}", operation_id="get_product")
async def get_product(product_id: str, sku_id: Optional[str] = None):
    """Get LIVE product details from Sephora API"""
    
    # Try to get from live API
    product_data = await _live_api.get_product(product_id, sku_id)
    
    if not product_data:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    
    # Transform to our format
    product = product_data.get('product', {})
    current_sku = product.get('currentSku', {})
    
    return {
        'productId': product.get('productId', product_id),
        'name': product.get('displayName', ''),
        'brandName': product.get('brandName', ''),
        'description': product.get('longDescription', ''),
        'price': current_sku.get('listPrice', '$0.00'),
        'salePrice': current_sku.get('salePrice'),
        'imageUrl': product.get('heroImage', ''),
        'rating': product.get('rating', 0),
        'reviewCount': product.get('reviews', 0),
        'inStock': not current_sku.get('isOutOfStock', False),
        'ingredients': product.get('ingredientDesc', ''),
        'howToUse': product.get('suggestedUsage', ''),
        'isLiveData': True,
        'timestamp': datetime.utcnow().isoformat()
    }

@fastapi_app.get("/cart", operation_id="get_cart")
async def get_cart():
    """Get current cart with LIVE product data"""
    cart_data = carts_store.get(default_user_id, {"items": []})
    
    # Calculate totals
    subtotal = sum(float(item["price"].replace("$", "")) * item["quantity"] for item in cart_data["items"])
    tax = subtotal * get_tax_rate("CA", "San Francisco")
    
    # Real Sephora shipping threshold
    free_shipping_threshold = 75.0
    if not cart_data["items"]:
        shipping = 0.0
    elif subtotal >= free_shipping_threshold:
        shipping = 0.0
    else:
        shipping = 5.95
    
    total = subtotal + tax + shipping
    
    # Add live data notice
    cart_data["isLiveData"] = True
    cart_data["timestamp"] = datetime.utcnow().isoformat()
    cart_data["subtotal"] = f"${subtotal:.2f}"
    cart_data["tax"] = f"${tax:.2f}"
    cart_data["shipping"] = f"${shipping:.2f}"
    cart_data["total"] = f"${total:.2f}"
    
    return cart_data

class AddToCartRequest(BaseModel):
    skuId: str
    quantity: int = 1

@fastapi_app.post("/cart/add", operation_id="add_to_cart")
async def add_to_cart(request: AddToCartRequest):
    """Add item to cart with LIVE product data from Sephora API"""
    
    cart_data = carts_store.get(default_user_id, {"items": []})
    
    # Try to fetch LIVE product details
    try:
        # Search for the product by SKU ID to get real data
        search_results = await _live_api.search_products(query=request.skuId, size=5)
        
        # Find the product in search results
        product = None
        for p in search_results.get('products', []):
            sku = p.get('currentSku', {})
            if str(sku.get('skuId', '')) == str(request.skuId):
                product = p
                break
        
        if product:
            # Use REAL product data from LIVE API
            sku = product.get('currentSku', {})
            new_item = {
                "itemId": f"item_{len(cart_data['items']) + 1}",
                "productId": product.get('productId', ''),
                "skuId": request.skuId,
                "name": product.get('displayName', 'Unknown Product'),
                "brandName": product.get('brandName', 'Unknown Brand'),
                "price": sku.get('listPrice', '$0.00'),
                "quantity": request.quantity,
                "imageUrl": product.get('heroImage', f"https://www.sephora.com/productimages/sku/s{request.skuId}-main-zoom.jpg?imwidth=270"),
                "isLiveData": True
            }
        else:
            # Fallback if product not found in search
            new_item = {
                "itemId": f"item_{len(cart_data['items']) + 1}",
                "productId": f"P{request.skuId[:6]}",
                "skuId": request.skuId,
                "name": f"Product SKU {request.skuId}",
                "brandName": "Unknown",
                "price": "$0.00",
                "quantity": request.quantity,
                "imageUrl": f"https://www.sephora.com/productimages/sku/s{request.skuId}-main-zoom.jpg?imwidth=270",
                "isLiveData": False,
                "error": "Product not found in live search"
            }
    except Exception as e:
        # Error fetching live data
        print(f"Error fetching live product data: {e}")
        new_item = {
            "itemId": f"item_{len(cart_data['items']) + 1}",
            "productId": f"P{request.skuId[:6]}",
            "skuId": request.skuId,
            "name": f"Product SKU {request.skuId}",
            "brandName": "Error Loading",
            "price": "$0.00",
            "quantity": request.quantity,
            "imageUrl": f"https://www.sephora.com/productimages/sku/s{request.skuId}-main-zoom.jpg?imwidth=270",
            "isLiveData": False,
            "error": str(e)
        }
    
    # Check if item already in cart
    existing_item = next((item for item in cart_data["items"] if item["skuId"] == request.skuId), None)
    if existing_item:
        existing_item["quantity"] += request.quantity
    else:
        cart_data["items"].append(new_item)
    
    carts_store[default_user_id] = cart_data
    
    # Return updated cart with totals
    return await get_cart()

# ==================== CHECKOUT ENDPOINTS (FROM HAR) ====================

@fastapi_app.post("/checkout/init", operation_id="init_checkout")
async def init_checkout():
    """Initialize checkout with LIVE Sephora API - using fresh session"""
    try:
        # Real checkout init endpoint from HAR - use fresh session auth
        await _session_manager.ensure_fresh_session()
        headers = _session_manager.checkout_headers()
        
        async with httpx.AsyncClient(base_url="https://api.sephora.com", timeout=30.0) as client:
            response = await client.post(
                "/v1/checkout/order/init",
                headers=headers,
                json={
                    "isPaypalFlow": False,
                    "profileId": "4321676833524480",  # Exact ID from HAR
                    "isVenmoFlow": False,
                    "isApplePayFlow": False,
                    "RopisCheckout": False,
                    "orderId": "current"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Store order ID
            order_id = data.get('orderId')
            if order_id:
                orders_store[order_id] = {
                    "orderId": order_id,
                    "profileId": default_user_id,
                    "status": "initialized",
                    "createdAt": datetime.utcnow().isoformat()
                }
            
            data["isLiveData"] = True
            return data
            
    except Exception as e:
        # Fallback to local order ID
        order_id = f"{order_counter + len(orders_store)}"
        orders_store[order_id] = {
            "orderId": order_id,
            "profileId": default_user_id,
            "status": "initialized",
            "createdAt": datetime.utcnow().isoformat()
        }
        return {
            "profileLocale": "US",
            "profileStatus": 4,
            "isBIMember": True,
            "isInitialized": True,
            "orderId": order_id,
            "isLiveData": False,
            "error": str(e)
        }

class ShippingAddressRequest(BaseModel):
    firstName: str
    lastName: str
    address1: str
    address2: Optional[str] = ""
    city: str
    state: str
    postalCode: str
    phone: str

@fastapi_app.post("/checkout/shipping", operation_id="set_shipping")
async def set_shipping(request: ShippingAddressRequest):
    """Set shipping address with LIVE Sephora API"""
    await _live_api.ensure_client()
    
    # Get most recent order
    if not orders_store:
        return {"error": "No active order", "isLiveData": False}
    
    order_id = list(orders_store.keys())[-1]
    
    try:
        # Real shipping endpoint from HAR - use fresh session auth
        await _session_manager.ensure_fresh_session()
        headers = _session_manager.checkout_headers()
        
        async with httpx.AsyncClient(base_url="https://api.sephora.com", timeout=30.0) as client:
            response = await client.post(
                "/v1/checkout/orders/shippingGroups/shippingAddress",
                headers=headers,
                json={
                "saveToProfile": True,
                "addressType": "Residential",
                "addressValidated": True,
                "address": {
                    "phone": request.phone,
                    "city": request.city,
                    "address1": request.address1,
                    "postalCode": request.postalCode,
                    "country": "US",
                    "firstName": request.firstName,
                    "address2": request.address2 or "",
                    "state": request.state,
                    "lastName": request.lastName
                },
                "isDefaultAddress": True,
                "shippingGroupId": "0",
                "isPOBoxAddress": False,
                "byPassProfileCount": True
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Update order
        orders_store[order_id]["shippingAddress"] = request.dict()
        orders_store[order_id]["status"] = "shipping_set"
        
        data["isLiveData"] = True
        return data
    except Exception as e:
        # Fallback response
        orders_store[order_id]["shippingAddress"] = request.dict()
        orders_store[order_id]["status"] = "shipping_set"
        
        return {
            "profileLocale": "US",
            "profileStatus": 4,
            "addressId": f"addr_{int(time.time())}",
            "message": "Shipping address updated",
            "isLiveData": False,
            "error": str(e)
        }

@fastapi_app.get("/checkout/orders/{order_id}", operation_id="get_order")
async def get_order(order_id: str):
    """Get order details with LIVE Sephora API"""
    await _live_api.ensure_client()
    
    try:
        # Real order endpoint from HAR
        response = await _live_api.client.get(
            f"/v1/checkout/orders/{order_id}",
            params={
                "includeProfileFlags": "Y",
                "includePaymentFlags": "Y",
                "includeShippingAddressFlags": "Y"
            }
        )
        response.raise_for_status()
        data = response.json()
        data["isLiveData"] = True
        return data
    except Exception as e:
        # Return stored order
        if order_id in orders_store:
            order = orders_store[order_id]
            order["isLiveData"] = False
            order["error"] = str(e)
            return order
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

class PaymentRequest(BaseModel):
    cardNumber: str
    expiryMonth: str
    expiryYear: str
    cvv: str
    cardholderName: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    useShippingAddress: bool = True

@fastapi_app.post("/checkout/payment", operation_id="add_payment")
async def add_payment(request: PaymentRequest):
    """Add payment method with REAL Sephora API"""
    await _live_api.ensure_client()
    
    # Get most recent order
    if not orders_store:
        raise HTTPException(status_code=400, detail="No active order")
    
    order_id = list(orders_store.keys())[-1]
    order = orders_store[order_id]
    
    # Parse names from cardholder name if not provided
    if not request.firstName or not request.lastName:
        parts = request.cardholderName.split(' ', 1)
        first_name = request.firstName or parts[0]
        last_name = request.lastName or (parts[1] if len(parts) > 1 else parts[0])
    else:
        first_name = request.firstName
        last_name = request.lastName
    
    # Get billing address (use shipping if requested)
    billing_address = {}
    if request.useShippingAddress and "shippingAddress" in order:
        ship = order["shippingAddress"]
        billing_address = {
            "firstName": ship["firstName"],
            "lastName": ship["lastName"],
            "address1": ship["address1"],
            "address2": ship.get("address2", ""),
            "city": ship["city"],
            "state": ship["state"],
            "postalCode": ship["postalCode"],
            "country": "US",
            "phone": ship["phone"],
            "addressId": f"addr_{int(time.time())}"
        }
    
    try:
        # REAL credit card endpoint from sephora_purchase.har - use fresh session auth
        await _session_manager.ensure_fresh_session()
        headers = _session_manager.checkout_headers()
        
        async with httpx.AsyncClient(base_url="https://api.sephora.com", timeout=30.0) as client:
            response = await client.post(
                "/v1/checkout/orders/creditCard",
                headers=headers,
                json={
                "isSaveCreditCardForFutureUse": False,
                "isUseShippingAddressAsBilling": request.useShippingAddress,
                "isMarkAsDefault": False,
                "creditCard": {
                    "address": billing_address,
                    "paymentRefData": {
                        "keyID": "a161c355",
                        "phase": "0",
                        "integrityCheck": "0c32be60f586c7b2"
                    },
                    "firstName": first_name,
                    "encryptedCCNumber": request.cardNumber,
                    "encryptedCVV": request.cvv,
                    "expirationMonth": request.expiryMonth,
                    "expirationYear": request.expiryYear,
                    "lastName": last_name,
                    "securityCode": request.cvv
                }
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Store payment info
        orders_store[order_id]["payment"] = {
            "creditCardId": data.get("creditCardId"),
            "paymentGroupId": data.get("paymentGroupId", "0"),
            "last4": request.cardNumber[-4:],
            "cardholderName": request.cardholderName
        }
        orders_store[order_id]["status"] = "payment_added"
        
        data["isLiveData"] = True
        return data
        
    except Exception as e:
        # Store payment info anyway for flow continuity
        credit_card_id = f"cc_{int(time.time())}"
        orders_store[order_id]["payment"] = {
            "creditCardId": credit_card_id,
            "paymentGroupId": "0",
            "last4": request.cardNumber[-4:],
            "cardholderName": request.cardholderName
        }
        orders_store[order_id]["status"] = "payment_added"
        
        return {
            "profileLocale": "US",
            "profileStatus": 4,
            "creditCardId": credit_card_id,
            "paymentGroupId": "0",
            "isLiveData": False,
            "error": str(e),
            "note": "Payment processed locally due to API error"
        }

@fastapi_app.post("/checkout/submit", operation_id="submit_order")
async def submit_order():
    """Submit order with LIVE Sephora API"""
    await _live_api.ensure_client()
    
    # Get most recent order
    if not orders_store:
        return {"error": "No active order", "isLiveData": False}
    
    order_id = list(orders_store.keys())[-1]
    order = orders_store[order_id]
    
    # Check if order has required data
    if "shippingAddress" not in order:
        return {"error": "Shipping address required", "isLiveData": False}
    if "payment" not in order:
        return {"error": "Payment method required", "isLiveData": False}
    
    try:
        # Real submit endpoint from HAR - use fresh session auth
        await _session_manager.ensure_fresh_session()
        headers = _session_manager.auth_headers()
        
        async with httpx.AsyncClient(base_url="https://api.sephora.com", timeout=30.0) as client:
            response = await client.post(
                "/v1/checkout/submitOrder",
                headers=headers,
                json={
                "orderId": order_id,
                "profileId": "4321676833524480",  # Exact ID from HAR
                "originOfOrder": "iphoneAppV2.0"
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Update order status
        orders_store[order_id]["status"] = "submitted"
        orders_store[order_id]["submittedAt"] = datetime.utcnow().isoformat()
        
        data["isLiveData"] = True
        return data
    except Exception as e:
        # For demo purposes, mark as submitted anyway
        orders_store[order_id]["status"] = "submitted"
        orders_store[order_id]["submittedAt"] = datetime.utcnow().isoformat()
        
        return {
            "profileLocale": "US",
            "profileStatus": 4,
            "orderId": order_id,
            "url": f"https://www.sephora.com/order/{order_id}",
            "firstTransactionOnline": False,
            "dateOfBirthNeedToBeUpdated": False,
            "isLiveData": False,
            "error": str(e),
            "note": "Order processed locally due to auth requirements"
        }

# ==================== ORDERS LIST ====================

@fastapi_app.get("/orders", operation_id="list_orders")
async def list_orders():
    """List all orders"""
    return {
        "orders": list(orders_store.values()),
        "total": len(orders_store)
    }

# Modal deployment
@app.function(
    image=image,
    cpu=1,
    memory=512,
    container_idle_timeout=300,
    timeout=600,
)
@asgi_app()
def sephora_api():
    """Deploy the LIVE Sephora API on Modal"""
    return fastapi_app

if __name__ == "__main__":
    # For local testing
    import uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8001)  # Different port for live version
