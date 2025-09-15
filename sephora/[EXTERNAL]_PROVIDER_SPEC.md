────────────────────────────────────────────────────────
UNIFIED-API PROVIDER SPECIFICATION v1 (“UAPS-1”)
────────────────────────────────────────────────────────
This document defines the **mandatory** and **optional** conventions that every
provider package (“plugin”) must follow in order to be auto-discovered,
mounted, documented, and consumed by the Unified-API and, by extension,
unified-metatool-mcp.

The spec is intentionally **service-agnostic**: an airline booking API, a CRM
API, and a weather API can all implement it without change to their business
domain.  Where examples are helpful, they are given with the fictitious
provider “AcmeWeather”.

CONTENTS
0. Terminology
1. Packaging & Discovery
2. Provider Manifest (`provider.yaml`)
3. BaseProvider subclass
4. OpenAPI Document
5. Authentication Contract
6. Request/Response Conventions
7. Error Model
8. Pagination
9. Idempotency & Retries
10. Rate-Limit Signalling
11. Health & Metadata Endpoints (optional)
12. Versioning & Deprecation
13. Testing Contract
14. Directory Layout Checklist
15. Billing & Purchases

────────────────────────────────────────────────────────
0.  TERMINOLOGY
────────────────────────────────────────────────────────
Provider / Plugin   A Python distribution that, when installed, registers
                    itself with Unified-API via an entry-point and exposes an
                    Acme-specific router plus metadata.

Provider ID         Stable, URL-friendly string (e.g. `acmeweather`).
Operation ID       Unique name for one HTTP operation inside a provider
                    (e.g. `getForecast`).

────────────────────────────────────────────────────────
1.  PACKAGING & DISCOVERY
────────────────────────────────────────────────────────
• Package your plugin as a **PEP 517** build (setuptools, poetry, hatch, etc.).  
• Add an *entry-point* inside `pyproject.toml`:

```toml
[project.entry-points."unified_api.providers"]
acmeweather = "acmeweather_plugin.provider:AcmeWeatherProvider"
```

• The runtime will `importlib.metadata.entry_points(group="unified_api.providers")`
  to discover plugins.

────────────────────────────────────────────────────────
2.  PROVIDER MANIFEST (`provider.yaml`)
────────────────────────────────────────────────────────
Placed in the *package root* next to `provider.py`.

```yaml
# provider.yaml  –  AcmeWeather
id: acmeweather          # REQUIRED  (kebab or snake, lowercase)
name: "Acme Weather"     # Human-readable
description: "Global forecasts and climate data"
homepage: "https://developer.acmeweather.com"
auth:
  scheme: apiKey         # one of [apiKey, oauth2, jwt, none, custom]
  in: header             # header | query | cookie   (ignored for oauth2)
  name: "X-Api-Key"      # header/query param name
  scopes:                # oauth2 only
    - "read_forecasts"
    - "write_forecasts"
endpoints: openapi.yaml  # relative path OR '*' = “autodetect from router”
rate_limits:
  default_per_minute: 120
  burst: 30
tags:                    # arbitrary discoverability tags
  - weather
  - climate
  - public
```

Notes  
• If `auth.scheme = custom`, the plugin must override
  `BaseProvider.get_auth_dependency()`.

────────────────────────────────────────────────────────
3.  BASEPROVIDER SUBCLASS
────────────────────────────────────────────────────────
Every plugin exports exactly **one** subclass of
`unified_api.plugins.BaseProvider`.

```python
from unified_api.plugins import BaseProvider, register_provider
from .router import router                  # FastAPI APIRouter you define

@register_provider                           # handles entry-point creation
class AcmeWeatherProvider(BaseProvider):
    manifest_path = Path(__file__).with_name("provider.yaml")
    router = router
```

`BaseProvider` provides defaults for:  
• Auth dependency injection  
• Error mapping → common error model  
• OpenAPI merging helper  
• Health endpoint

Overridable hooks (all optional):  
```python
async def startup(self): ...      # runs once at mount
async def shutdown(self): ...     # runs at app shutdown
def get_auth_dependency(self): ...# custom auth
```

────────────────────────────────────────────────────────
4.  OPENAPI DOCUMENT
────────────────────────────────────────────────────────
• Must be **OpenAPI 3.1** or **3.0.x** YAML or JSON.  
• `info.title` MUST equal `manifest.name`; `info.version`
  equals plugin package version.
• `info.description` SHOULD be rich and detailed - this becomes the service
  description visible in search results. Include key capabilities, use cases,
  and relevant keywords (e.g., "Food delivery service with restaurant search,
  menu browsing, cart management, and order tracking").
• `servers` SHOULD be omitted (Unified-API rewrites servers).  
• MUST provide **operationId** for every path+method; those IDs become MCP
  tool names ("acmeweather_getForecast").
  
• **🔴 CRITICAL for FastAPI providers:** Your function names become MCP tool names!
  
  **STRONGLY RECOMMENDED:** Always explicitly set `operation_id` to match your
  function name. This ensures stable, predictable tool names:
  
  ```python
  @router.get("/forecast", operation_id="get_forecast")  # ✅ BEST PRACTICE
  async def get_forecast(...):
      ...
  ```
  
  **Why this matters:** Without explicit operationIds, FastAPI auto-generates
  names like `get_forecast_forecast_get` which create confusing MCP tool names
  like `acmeweather_get_forecast_forecast_get`. Your clean function name
  (`get_forecast`) should BE the operationId.
  
  **Alternative (if you have many endpoints):** Configure a global generator:
  
  ```python
  from fastapi import FastAPI, APIRouter
  from fastapi.routing import APIRoute

  def use_function_name_as_operation_id(route: APIRoute) -> str:
      # Use the underlying function name directly
      return route.name

  router = APIRouter()

  @router.get("/forecast")  # operationId will be "get_forecast"
  async def get_forecast(...):
      ...

  app = FastAPI(generate_unique_id_function=use_function_name_as_operation_id)
  app.include_router(router)
  ```
  
  **Bottom line:** Your operationIds MUST match your function names for clean
  MCP tool names. Choose explicit `operation_id=` (recommended) or global
  generator (for large codebases).

• Path names **MUST** be relative (`/forecast`, not full URL).  
• All parameters and schemas MUST have `description`.

• **Fast-path onboarding**  
  Providers that already expose a fully-hosted OpenAPI JSON/YAML may skip
  writing a `router.py` entirely and instead build their router at runtime
  with the helper below:

  ```python
  from unified_api.plugins import BaseProvider, register_provider
  from unified_api.plugins.openapi_proxy import build_router_from_remote_spec

  @register_provider(id="acmeweather")
  class AcmeWeatherProvider(BaseProvider):
      def __init__(self) -> None:
          super().__init__(
              id="acmeweather",
              router=build_router_from_remote_spec(
                  "https://api.acme.com/openapi.json",     # spec URL
                  "https://api.acme.com"                   # upstream base URL
              ),
              manifest_path=Path(__file__).with_name("provider.yaml"),
          )
  ```

  This fetches the remote spec at startup, generates a proxy router for every
  path, and automatically merges those paths into Unified-API's Swagger
  document.  Use this shortcut when you need to stand up a proxy quickly and
  don't (yet) require custom request / response logic.

• Providers SHOULD expose an `initializeUser` operation when their upstream
  service requires per-user onboarding (e.g., account creation, profile setup,
  or credential linking). This operation should follow the naming convention
  `initializeUser` and accept user identification parameters as needed.

────────────────────────────────────────────────────────
5.  AUTHENTICATION CONTRACT
────────────────────────────────────────────────────────
Unified-API recognises these schemes:

| scheme   | Description                                             |
|----------|---------------------------------------------------------|
| none     | No auth header produced                                 |
| apiKey   | Static token; plugin receives env var `PROVIDER_{ID}_API_KEY` |
| oauth2   | Client-credentials flow; Unified-API handles token cache|
| jwt      | Downstream expects a JWT signed by Unified-API          |
| custom   | Plugin’s `get_auth_dependency()` builds `HTTPBearer (…)`|

• **No plugin should read environment variables directly**; instead they call
  `self.get_credential()` which yields a typed object matching the scheme.

────────────────────────────────────────────────────────
6.  REQUEST / RESPONSE CONVENTIONS
────────────────────────────────────────────────────────
• **JSON** is the default and strongly preferred.  
• If an endpoint must be non-JSON (e.g., file download), specify
  `content-type` explicitly in OpenAPI and mark `x-binary` in schema.

• Timestamps: **ISO-8601 UTC** (`2024-06-01T15:00:00Z`).  
• Monetary amounts: **string decimal** (`"12.34"`) + `currency` field.

────────────────────────────────────────────────────────
7.  ERROR MODEL
────────────────────────────────────────────────────────
Unified-API translates provider exceptions → common envelope:

```json
{
  "error": {
    "provider_id": "acmeweather",
    "code": "RESOURCE_NOT_FOUND",        // U-API canonical codes
    "status": 404,
    "message": "Station 999 not found",
    "details": { "station_id": "999" }   // provider-specific data
  }
}
```

Canonical `code` values (non-exhaustive):  
• AUTH_FAILED • RATE_LIMITED • VALIDATION_ERROR • RESOURCE_NOT_FOUND  
• CONFLICT • UNAVAILABLE • INTERNAL_ERROR

Plugins SHOULD raise `unified_api.errors.ProviderError(code, status, ...)`
to ensure mapping.

────────────────────────────────────────────────────────
8.  PAGINATION
────────────────────────────────────────────────────────
If an endpoint returns a list, choose exactly one style:

Style A – **Cursor** (preferred)  
```json
{
  "data": [ ... ],
  "next_cursor": "opaque-string"   // absent when at end
}
```

Style B – **Page/limit**  
Same envelope plus `page`, `page_size`, and `total` (optional).

Declare style via OpenAPI `components.schemas.PaginationCursor` or
`PaginationPage`.

────────────────────────────────────────────────────────
9.  IDEMPOTENCY & RETRIES
────────────────────────────────────────────────────────
POST/PUT endpoints that create resources MUST accept the optional header
`Idempotency-Key` (UUIDv4).  Repeating the same key within 24 hours MUST
return the initial success response or an error with `code=IDEmpotencyMismatch`.

────────────────────────────────────────────────────────
10. RATE-LIMIT SIGNALLING
────────────────────────────────────────────────────────
When throttling, respond **429** with headers:

```
RateLimit-Limit: 120
RateLimit-Remaining: 0
RateLimit-Reset: 41   # seconds until reset
```

────────────────────────────────────────────────────────
11. HEALTH & METADATA (optional but strongly encouraged)
────────────────────────────────────────────────────────
Unified-API will mount:

```
GET /{provider_id}/health      → 200 {"ok": true}
GET /{provider_id}/metadata    → provider.yaml contents
```

If additional sub-checks are needed, override `BaseProvider.startup()` to
register them.

────────────────────────────────────────────────────────
11.1  SERVICE METADATA (FLOW, PRICING, ETC.)
────────────────────────────────────────────────────────
Unified-API surfaces **service-level metadata** via a custom OpenAPI extension
`x-services`.

Each provider can expose a JSON object that describes how to use the service
("flow"), typical response times, pricing model, and any additional fields
helpful for front-end guidance or documentation generators.

Two equivalent ways to define the metadata:

• **Python dict** – set `service_metadata` when constructing `BaseProvider`:

```python
SERVICE_METADATA = {
    "flow": "1. Choose utility → 2. Set parameters → 3. Get results",
    "pricing_model": "free tier + premium content (3–5¢)",
    "typical_response_time": "< 100 ms",
    # … any custom keys …
}

@register_provider(id="funapp")
class FunappProvider(BaseProvider):
    def __init__(self):
        super().__init__(
            id="funapp",
            router=build_router_from_remote_spec(...),
            manifest_path=Path(__file__).with_name("provider.yaml"),
            service_metadata=SERVICE_METADATA,
        )
```

• **OpenAPI extension** – embed directly in your spec (useful for remote specs):

```yaml
openapi: 3.1.0
info:
  title: Fun Utilities API
  version: "1.0.0"
x-services:
  funapp:
    flow: "1. Choose utility → 2. Set parameters → 3. Get results"
    pricing_model: "free tier + premium content (3–5¢)"
    typical_response_time: "< 100 ms"
```

The Unified-API gateway automatically injects/merges the metadata into its
root `/openapi.json`.  Meta-tools like **mcp list_tools** read it to enrich the
UI/UX.

**Recommended keys** (free-form – add your own as needed):

• `flow` – A concise, numbered list of typical usage steps.
• `pricing_model` – e.g. "per request", "subscription", or pricing details.
• `typical_response_time` – Human-readable latency expectations.

Providers without metadata still work; the fields will simply be absent.

────────────────────────────────────────────────────────
12. VERSIONING & DEPRECATION
────────────────────────────────────────────────────────
• **SemVer** for plugin package (`2.3.0`).  
• Breaking changes to any endpoint path or schema require either:  
  a) a new path (`/v2/forecast`), **or**  
  b) bumping `info.version` major and setting `deprecated: true`
     on the old operation.

• Deprecation period MUST be ≥90 days unless legal/compliance prevents it.

────────────────────────────────────────────────────────
13. TESTING CONTRACT
────────────────────────────────────────────────────────
Each plugin **MUST** ship `tests/contract_test.py` that imports
`unified_api.testing`:

```python
@pytest.mark.contract
async def test_smoke(acmeweather):
    resp = await acmeweather.get_forecast(lat=0, lon=0)
    assert resp.status_code == 200
```

CI will run all `pytest -m contract` tests in an isolated environment
with credentials injected from GitHub Secrets (pattern:
`PROVIDER_<ID>_*`).

────────────────────────────────────────────────────────
14. DIRECTORY LAYOUT CHECKLIST
────────────────────────────────────────────────────────
```
acmeweather_plugin/
├── acmeweather_plugin/
│   ├── __init__.py
│   ├── provider.py             # BaseProvider subclass
│   ├── provider.yaml           # Manifest (section 2)
│   ├── openapi.yaml            # Full spec (section 4)
│   ├── router.py               # FastAPI router w/ path handlers
│   └── models.py               # (optional) pydantic models
├── tests/
│   └── contract_test.py
├── pyproject.toml
└── README.md                   # Quick-start & examples
```

────────────────────────────────────────────────────────
APPENDIX A – MINIMAL EXAMPLE (`openapi.yaml` snippet)
────────────────────────────────────────────────────────
```yaml
openapi: 3.1.0
info:
  title: Acme Weather
  version: "1.2.0"
paths:
  /forecast:
    get:
      operationId: getForecast
      summary: "7-day forecast for a lat/lon point"
      parameters:
        - in: query
          name: lat
          required: true
          schema: { type: number }
          description: Latitude in decimal degrees
        - in: query
          name: lon
          required: true
          schema: { type: number }
          description: Longitude in decimal degrees
      responses:
        "200":
          description: Success
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ForecastResponse"
components:
  schemas:
    ForecastResponse:
      type: object
      properties:
        data:
          type: array
          items: { $ref: "#/components/schemas/DayForecast" }
      required: [data]
    DayForecast:
      type: object
      properties:
        date: { type: string, format: date }
        high_c: { type: number }
        low_c: { type: number }
        description: { type: string }
      required: [date, high_c, low_c, description]
```

────────────────────────────────────────────────────────
APPENDIX B – INITIALIZEUSER OPERATION EXAMPLE
────────────────────────────────────────────────────────
For providers requiring per-user onboarding, consider this shared schema:

```yaml
  /initialize-user:
    post:
      operationId: initializeUser
      summary: "Initialize user account for provider service"
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/InitializeUserRequest"
      responses:
        "200":
          description: User successfully initialized
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/InitializeUserResponse"

components:
  schemas:
    InitializeUserRequest:
      type: object
      properties:
        email:
          type: string
          format: email
          description: User's email address
        phone:
          type: string
          description: User's phone number (optional)
        name:
          type: string
          description: User's full name (optional)
        preferences:
          type: object
          description: Provider-specific user preferences
      required: [email]
    InitializeUserResponse:
      type: object
      properties:
        user_id:
          type: string
          description: Provider's internal user identifier
        status:
          type: string
          enum: [active, pending_verification, requires_additional_info]
          description: User initialization status
        message:
          type: string
          description: Human-readable status message
      required: [user_id, status]
```

────────────────────────────────────────────────────────
15. BILLING · USAGE FEES · PURCHASES  ✅ QUICK-START FOR PROVIDERS
────────────────────────────────────────────────────────

Unified-API already contains the **entire** billing engine – *you never write any
billing code*.  You only **describe** what should be charged via decorators **or**
OpenAPI extensions.

⚠️  **RULE OF THUMB**  — Every endpoint that deducts credits **MUST** have a
**quote / pre-check** twin so the gateway can block unaffordable calls *before*
reaching your upstream.  CI will reject plugins that mark `x-purchase-endpoint`
without `x-purchase-precheck`.

Below is the exact recipe.

───────────────────────
A) SIMPLE USAGE-FEE ENDPOINT (e.g. 5¢ per request)
───────────────────────
1. Add the `@usage_fee` decorator **or** `x-usage-fee` field.
   ```python
   @router.get("/search")
   @usage_fee(cost_cents=5)   # <-- costs 5¢ every call
   async def search_restaurants(...):
       ...
   ```
   YAML alternative:
   ```yaml
   /search:
     get:
       operationId: search_restaurants
       x-usage-fee: 5   # cents
   ```
2. Nothing else – the gateway automatically deducts the fee when the request
   succeeds (HTTP 2xx).

──────────────────────────────────────────
B) REAL PURCHASE ENDPOINT (e.g. checkout, place order)
──────────────────────────────────────────
You **must** expose *two* endpoints:
• **Pre-check / quote** – returns the final price **before** the purchase
• **Purchase** – executes the transaction

Why?  The gateway calls your pre-check first so that it can block the purchase
with an HTTP 402 *before* hitting your upstream if the user has insufficient
funds.  This avoids needless provider calls and unhappy customers.

Step-by-step:

1. **Pre-check endpoint** – mark with `x-purchase-precheckout: true` and provide
   `x-amount-path` so the gateway knows where to find the price in your JSON.
   ```yaml
   /checkout/quote:
     post:
       operationId: get_checkout_quote
       x-purchase-precheckout: true          # <-- tells gateway this is a quote
       x-amount-path: "$.totals.total_cents" # <-- JSONPath to the price (int)
   ```

2. **Purchase endpoint** – mark with `x-purchase-endpoint: true`, link to the
   pre-check path, and declare the same `x-amount-path`.  ‼️ If your response
   includes a unique order id, also set `x-transaction-id-path` for idempotency.
   ```yaml
   /checkout:
     post:
       operationId: checkout
       x-purchase-endpoint: true
       x-purchase-precheck: "/checkout/quote"   # <-- link!
       x-amount-path: "$.totals.total_cents"
       x-transaction-id-path: "$.order_uuid"
   ```

3. Done – Unified-API will now:
   1. Call `/checkout/quote` → extract price
   2. Ensure the caller has enough balance → *if not* return **HTTP 402**
   3. Proxy the real `/checkout` call
   4. Deduct the amount atomically if purchase succeeds (HTTP 2xx)

──────────────────────────────────────────
POWER USER SHORTCUT – PYTHON DECORATORS
──────────────────────────────────────────
If you own the router code you can skip YAML and use decorators:
```python
@router.post("/checkout/quote")
@purchase_precheckout(amount_path="$.totals.total_cents")
async def get_checkout_quote(...):
    ...

@router.post("/checkout")
@purchase(precheck_endpoint="/checkout/quote",
          amount_path="$.totals.total_cents",
          transaction_id_path="$.order_uuid")
async def checkout(...):
    ...
```

──────────────────────────────────────────
FAQ
──────────────────────────────────────────
• *Do I need to enable a feature flag?* – **No.** Billing is on globally; it is
  toggled by decorators / OpenAPI extensions.
• *What currency?* – Always cents of the smallest unit (USD by default).
• *What if my upstream returns floats (e.g. 1.23)?* – Convert to integer cents
  before returning or round/scale accordingly.
• *What happens on upstream errors?* – Funds are **not** deducted; the user sees
  your upstream error wrapped in Unified-API’s error envelope.

That’s it – no additional SDKs, database calls, or environment variables.

────────────────────────────────────────────────────────
ADOPTION CHECKLIST FOR NEW PROVIDERS
────────────────────────────────────────────────────────
☐ Fill out `provider.yaml`