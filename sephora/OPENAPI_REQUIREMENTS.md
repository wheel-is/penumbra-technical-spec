────────────────────────────────────────────────────────
UNIFIED-API OPENAPI SPECIFICATION REQUIREMENTS
────────────────────────────────────────────────────────
This document extracts and consolidates all OpenAPI-specific requirements 
for providers integrating with the Unified-API gateway.

────────────────────────────────────────────────────────
1. OPENAPI VERSION & STRUCTURE
────────────────────────────────────────────────────────
• **REQUIRED**: OpenAPI 3.1 or 3.0.x (YAML or JSON)
• **REQUIRED**: Place in provider package root (e.g., `openapi.yaml`)
• **OPTIONAL**: Can be dynamically generated from remote spec

────────────────────────────────────────────────────────
2. REQUIRED FIELDS
────────────────────────────────────────────────────────
## Info Section
• `info.title` **MUST** equal `manifest.name`
• `info.version` **MUST** equal plugin package version
• `info.description` **SHOULD** be rich and detailed
  - This becomes the service description visible in search results
  - Include key capabilities, use cases, and relevant keywords
  - Example: "Food delivery service with restaurant search, menu browsing, 
    cart management, and order tracking"

## Servers
• `servers` **SHOULD** be omitted (Unified-API rewrites servers)

## Paths
• Path names **MUST** be relative (`/forecast`, not full URL)
• Every path+method **MUST** have an `operationId`
• All parameters and schemas **MUST** have `description`

────────────────────────────────────────────────────────
3. OPERATION ID BEST PRACTICES 🔴 CRITICAL
────────────────────────────────────────────────────────
Your function names become MCP tool names! The final tool name will be:
`{provider_id}_{operationId}`

**STRONGLY RECOMMENDED**: Always explicitly set `operation_id` to match your 
function name:

```python
@router.get("/forecast", operation_id="get_forecast")  # ✅ BEST PRACTICE
async def get_forecast(...):
    ...
```

**Why this matters**: Without explicit operationIds, FastAPI auto-generates 
names like `get_forecast_forecast_get` which create confusing MCP tool names 
like `acmeweather_get_forecast_forecast_get`.

**Alternative for large codebases**: Configure a global generator:

```python
from fastapi import FastAPI, APIRouter
from fastapi.routing import APIRoute

def use_function_name_as_operation_id(route: APIRoute) -> str:
    return route.name  # Use the underlying function name directly

router = APIRouter()

@router.get("/forecast")  # operationId will be "get_forecast"
async def get_forecast(...):
    ...

app = FastAPI(generate_unique_id_function=use_function_name_as_operation_id)
app.include_router(router)
```

────────────────────────────────────────────────────────
4. SERVICE METADATA EXTENSION (x-services)
────────────────────────────────────────────────────────
Unified-API surfaces service-level metadata via a custom OpenAPI extension.

## In Your OpenAPI Spec
```yaml
openapi: 3.1.0
info:
  title: Fun Utilities API
  version: "1.0.0"
x-services:
  funapp:
    description: "Collection of utilities and entertainment tools"
    flow: "1. Choose utility → 2. Set parameters → 3. Get results"
    pricing_model: "free tier + premium content (3–5¢)"
    typical_response_time: "< 100 ms"
    # ... any custom fields ...
```

## Recommended Metadata Fields
• `description` - Rich service description for search
• `flow` - Concise, numbered list of typical usage steps
• `pricing_model` - e.g., "per request", "subscription"
• `typical_response_time` - Human-readable latency expectations

────────────────────────────────────────────────────────
5. BILLING EXTENSIONS
────────────────────────────────────────────────────────
Mark endpoints that handle real-world transactions or usage fees.

## Purchase Endpoints with Precheck Pattern (RECOMMENDED)
For real transactions with price verification:

```yaml
paths:
  # Step 1: Precheck endpoint returns pricing estimate
  /checkout/quote:
    post:
      operationId: get_checkout_quote
      x-purchase-precheckout: true              # Mark as precheck
      x-amount-path: "$.pricing.total_cents"    # JSONPath to estimate
      
  # Step 2: Purchase endpoint linked to precheck
  /checkout:
    post:
      operationId: checkout
      x-purchase-endpoint: true                 # Required
      x-purchase-precheck: "/checkout/quote"    # Link to precheck
      x-amount-path: "$.totals.total_cents"     # JSONPath to cents
      x-transaction-id-path: "$.order_uuid"     # JSONPath to unique ID
      x-currency-path: "$.totals.currency"      # Optional, defaults to USD
```

## Simple Purchase Endpoints (without precheck)
For transactions where price is known upfront:

```yaml
paths:
  /checkout:
    post:
      operationId: checkout
      x-purchase-endpoint: true          # Required
      x-amount-path: "$.totals.total_cents"    # JSONPath to cents
      x-transaction-id-path: "$.order_uuid"    # JSONPath to unique ID
      x-currency-path: "$.totals.currency"     # Optional, defaults to USD
```

## Usage Fee Endpoints
For per-request charges:

```yaml
paths:
  /search:
    get:
      operationId: search_restaurants
      x-usage-fee: 5  # Charge 5 cents per request
```

**IMPORTANT**: All amounts **MUST** be in cents (or smallest currency unit) as integers

────────────────────────────────────────────────────────
6. SPECIAL OPERATIONS
────────────────────────────────────────────────────────
## Initialize User Operation
For providers requiring per-user onboarding:

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
    responses:
      "200":
        description: User successfully initialized
        content:
          application/json:
            schema:
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
7. CONTENT TYPE & DATA FORMATS
────────────────────────────────────────────────────────
• **Default**: JSON (strongly preferred)
• **Non-JSON**: Specify `content-type` explicitly and mark `x-binary` in schema
• **Timestamps**: ISO-8601 UTC (`2024-06-01T15:00:00Z`)
• **Monetary amounts**: String decimal (`"12.34"`) + `currency` field

────────────────────────────────────────────────────────
8. REMOTE SPEC PROXY PATTERN
────────────────────────────────────────────────────────
For providers with existing hosted OpenAPI specs:

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

This fetches the remote spec at startup and generates a proxy router 
automatically.

────────────────────────────────────────────────────────
9. MINIMAL COMPLETE EXAMPLE
────────────────────────────────────────────────────────
```yaml
openapi: 3.1.0
info:
  title: Acme Weather
  version: "1.2.0"
  description: "Global weather forecasts and climate data with 7-day predictions, 
    historical data, and real-time alerts for any location worldwide"
x-services:
  acmeweather:
    description: "Global weather forecasts and climate data service"
    flow: "1. Provide location → 2. Select forecast type → 3. Get weather data"
    pricing_model: "free tier (100 requests/day) + premium ($0.01/request)"
    typical_response_time: "< 500ms"
paths:
  /forecast:
    get:
      operationId: get_forecast
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
                type: object
                properties:
                  data:
                    type: array
                    items:
                      type: object
                      properties:
                        date: 
                          type: string
                          format: date
                          description: Forecast date
                        high_c: 
                          type: number
                          description: High temperature in Celsius
                        low_c: 
                          type: number
                          description: Low temperature in Celsius
                        description: 
                          type: string
                          description: Weather conditions description
                      required: [date, high_c, low_c, description]
                required: [data]
```

────────────────────────────────────────────────────────
10. VALIDATION CHECKLIST
────────────────────────────────────────────────────────
☐ OpenAPI 3.0+ version specified
☐ info.title matches provider name
☐ info.description is rich and searchable
☐ Every endpoint has an explicit operationId
☐ operationId matches function name (no auto-generated suffixes)
☐ All parameters have descriptions
☐ All schema properties have descriptions
☐ Paths use relative URLs
☐ x-services metadata included (if applicable)
☐ Purchase endpoints marked with x-purchase-endpoint
☐ Precheck endpoints marked with x-purchase-precheckout (if applicable)
☐ Purchase endpoints linked to prechecks via x-purchase-precheck (recommended)
☐ Usage fees specified with x-usage-fee (if applicable)
☐ Amounts are in cents as integers
☐ Timestamps use ISO-8601 format
☐ initializeUser operation included (if needed)

────────────────────────────────────────────────────────
11. COMMON PITFALLS TO AVOID
────────────────────────────────────────────────────────
❌ DON'T let FastAPI auto-generate operationIds
❌ DON'T use full URLs in paths
❌ DON'T omit descriptions on parameters/schemas
❌ DON'T use float for monetary amounts
❌ DON'T forget to specify operation_id explicitly
❌ DON'T use generic service descriptions
❌ DON'T express amounts in dollars (use cents)

✅ DO set explicit operation_id matching function names
✅ DO write rich, searchable descriptions
✅ DO include service metadata in x-services
✅ DO use cents for all monetary values
✅ DO include usage flow in metadata
✅ DO validate your spec with tools before deployment

## Payment / Purchase QUICK CHECKLIST  ✅
If your provider charges users you must implement **the pre-check pattern** – every paid endpoint **MUST** have a linked quote/estimate endpoint.  Unified-API blocks the purchase with HTTP 402 if the caller lacks credits.

1. **Usage-fee endpoint** – fixed cost per request
   • Add `x-usage-fee: <cents>`  **OR** `@usage_fee(cost_cents=<cents>)`

2. **Purchase endpoint** – *always* paired with a precheck
   a. Create *quote* endpoint and mark with:
      ```yaml
      x-purchase-precheckout: true
      x-amount-path: "$.price_cents"   # integer cents
      ```
   b. Link the real purchase endpoint:
      ```yaml
      x-purchase-endpoint: true
      x-purchase-precheck: "/quote/path"   # required
      x-amount-path: "$.price_cents"
      x-transaction-id-path: "$.order_id"   # recommended
      ```

Unified-API will: call quote → verify balance → execute purchase → deduct/rollback.  **Never** expose a paid endpoint without a precheck – CI validation will fail.
