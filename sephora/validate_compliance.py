#!/usr/bin/env python3
"""
Validate compliance with UAPI OPENAPI_REQUIREMENTS.md and [EXTERNAL]_PROVIDER_SPEC.md
Especially focusing on the precheck/purchase pattern.
"""

import yaml
import json
import sys

def validate_openapi_compliance():
    """Check OpenAPI spec compliance with UAPI requirements"""
    
    print("=" * 60)
    print("UNIFIED-API COMPLIANCE VALIDATION")
    print("=" * 60)
    
    # Load OpenAPI spec
    with open('openapi.yaml', 'r') as f:
        spec = yaml.safe_load(f)
    
    results = []
    
    # 1. Check OpenAPI version
    print("\n1. OpenAPI Version Check:")
    openapi_version = spec.get('openapi', '')
    if openapi_version.startswith('3.'):
        results.append(("✅", "OpenAPI 3.x version", f"Using {openapi_version}"))
    else:
        results.append(("❌", "OpenAPI version", f"Must be 3.x, found: {openapi_version}"))
    
    # 2. Check info section
    print("\n2. Info Section Check:")
    info = spec.get('info', {})
    if info.get('title'):
        results.append(("✅", "info.title present", info['title']))
    else:
        results.append(("❌", "info.title missing", "Required field"))
    
    if info.get('description'):
        desc_len = len(info['description'])
        if desc_len > 100:
            results.append(("✅", "Rich description", f"{desc_len} characters"))
        else:
            results.append(("⚠️", "Description too short", f"Only {desc_len} chars, should be detailed"))
    else:
        results.append(("❌", "info.description missing", "Required for search"))
    
    # 3. Check service metadata
    print("\n3. Service Metadata Check:")
    services = spec.get('x-services', {})
    if services:
        svc = services.get('sephora', {})
        if svc.get('description'):
            results.append(("✅", "x-services.description", "Present"))
        if svc.get('flow'):
            results.append(("✅", "x-services.flow", svc['flow'][:50] + "..."))
        if svc.get('pricing_model'):
            results.append(("✅", "x-services.pricing_model", svc['pricing_model']))
    else:
        results.append(("⚠️", "x-services missing", "Recommended for meta-tools"))
    
    # 4. Check all endpoints have operationId
    print("\n4. Operation ID Check:")
    paths = spec.get('paths', {})
    missing_op_ids = []
    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ['get', 'post', 'put', 'delete', 'patch']:
                if not details.get('operationId'):
                    missing_op_ids.append(f"{method.upper()} {path}")
    
    if not missing_op_ids:
        results.append(("✅", "All endpoints have operationId", f"{len(paths)} paths checked"))
    else:
        results.append(("❌", "Missing operationIds", ", ".join(missing_op_ids)))
    
    # 5. CRITICAL: Check purchase/precheck pattern
    print("\n5. Purchase Pattern Compliance (CRITICAL):")
    
    purchase_endpoints = []
    precheck_endpoints = []
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ['get', 'post', 'put', 'delete', 'patch']:
                if details.get('x-purchase-endpoint'):
                    purchase_endpoints.append({
                        'path': path,
                        'method': method,
                        'precheck': details.get('x-purchase-precheck'),
                        'amount_path': details.get('x-amount-path'),
                        'transaction_path': details.get('x-transaction-id-path')
                    })
                if details.get('x-purchase-precheckout'):
                    precheck_endpoints.append({
                        'path': path,
                        'method': method,
                        'amount_path': details.get('x-amount-path')
                    })
    
    # Validate purchase endpoints
    for purchase in purchase_endpoints:
        print(f"\n  Purchase Endpoint: {purchase['method'].upper()} {purchase['path']}")
        
        # Must have precheck link
        if purchase['precheck']:
            results.append(("✅", f"Has precheck link", purchase['precheck']))
            
            # Verify precheck endpoint exists
            precheck_exists = any(p['path'] == purchase['precheck'] for p in precheck_endpoints)
            if precheck_exists:
                results.append(("✅", "Precheck endpoint exists", purchase['precheck']))
            else:
                results.append(("❌", "Precheck endpoint missing", f"{purchase['precheck']} not found"))
        else:
            results.append(("❌", "CRITICAL: No precheck link", "Required by UAPI spec"))
        
        # Must have amount path
        if purchase['amount_path']:
            results.append(("✅", "Has amount path", purchase['amount_path']))
        else:
            results.append(("❌", "No amount path", "Required for billing"))
        
        # Should have transaction ID path
        if purchase['transaction_path']:
            results.append(("✅", "Has transaction ID path", purchase['transaction_path']))
        else:
            results.append(("⚠️", "No transaction ID path", "Recommended for idempotency"))
    
    # Validate precheck endpoints
    for precheck in precheck_endpoints:
        print(f"\n  Precheck Endpoint: {precheck['method'].upper()} {precheck['path']}")
        
        if precheck['amount_path']:
            results.append(("✅", "Has amount path", precheck['amount_path']))
        else:
            results.append(("❌", "No amount path", "Required for precheck"))
    
    # 6. Check data formats
    print("\n6. Data Format Compliance:")
    
    # Check if amounts are integers (cents)
    schemas = spec.get('components', {}).get('schemas', {})
    
    # Check CheckoutQuote schema
    quote_schema = schemas.get('CheckoutQuote', {})
    if quote_schema:
        pricing = quote_schema.get('properties', {}).get('pricing', {})
        if pricing:
            total_cents = pricing.get('properties', {}).get('total_cents', {})
            if total_cents.get('type') == 'integer':
                results.append(("✅", "Quote total_cents is integer", "Correct for cents"))
            else:
                results.append(("❌", "Quote total_cents wrong type", f"Should be integer, is {total_cents.get('type')}"))
    
    # Check OrderSubmitResponse schema
    submit_schema = schemas.get('OrderSubmitResponse', {})
    if submit_schema:
        totals = submit_schema.get('properties', {}).get('totals', {})
        if totals:
            total_cents = totals.get('properties', {}).get('total_cents', {})
            if total_cents.get('type') == 'integer':
                results.append(("✅", "Submit total_cents is integer", "Correct for cents"))
            else:
                results.append(("❌", "Submit total_cents wrong type", f"Should be integer, is {total_cents.get('type')}"))
    
    # 7. Final Summary
    print("\n" + "=" * 60)
    print("COMPLIANCE SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r[0] == "✅")
    warnings = sum(1 for r in results if r[0] == "⚠️")
    failed = sum(1 for r in results if r[0] == "❌")
    
    for status, check, detail in results:
        print(f"{status} {check}: {detail}")
    
    print("\n" + "-" * 60)
    print(f"Results: {passed} passed, {warnings} warnings, {failed} failed")
    
    if failed == 0:
        print("\n🎉 FULLY COMPLIANT with UAPI specifications!")
        print("   The precheck/purchase pattern is correctly implemented.")
        print("   The gateway will properly handle credit verification.")
        return 0
    else:
        print("\n⚠️  Some compliance issues found. Please review above.")
        return 1

if __name__ == "__main__":
    sys.exit(validate_openapi_compliance())
