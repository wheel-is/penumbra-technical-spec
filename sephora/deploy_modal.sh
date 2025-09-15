#!/bin/bash

# Deploy Sephora Beauty API to Modal
# Ensures compliance with Unified API (uapi) OpenAPI specifications

echo "========================================="
echo "Deploying Sephora Beauty API to Modal"
echo "========================================="

# Check if Modal is installed
if ! command -v modal &> /dev/null; then
    echo "❌ Modal CLI not found. Installing..."
    pip install modal
fi

# Check if authenticated
echo "Checking Modal authentication..."
modal token set --token-from-env 2>/dev/null || {
    echo "📝 Please authenticate with Modal:"
    modal setup
}

# Deploy the app
echo ""
echo "🚀 Deploying to Modal..."
echo ""

python -m modal deploy modal_app.py

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Your API is now available at the Modal-provided URL."
echo ""
echo "Key endpoints:"
echo "  • GET  /docs          - Interactive API documentation"
echo "  • GET  /openapi.json  - OpenAPI specification (JSON)"
echo "  • GET  /openapi.yaml  - OpenAPI specification (YAML)"
echo "  • POST /auth/token    - Get authentication token"
echo "  • GET  /content/home  - Homepage content"
echo "  • GET  /products/search - Search products"
echo ""
echo "Test the API:"
echo "  curl <MODAL_URL>/health"
echo ""
echo "Get access token:"
echo "  curl -X POST <MODAL_URL>/auth/token \\"
echo "    -H 'Content-Type: application/x-www-form-urlencoded' \\"
echo "    -d 'grant_type=client_credentials'"
echo ""
