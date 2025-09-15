#!/usr/bin/env python3
"""
Generate validation scripts from HAR file to test API conformance.
Uses har_preview.py to extract key requests that map to our API endpoints.
"""

import subprocess
import json

# Key HAR entries that map to our API endpoints
KEY_ENTRIES = {
    "auth_token": [81],  # OAuth token request
    "homepage": [9, 74],  # Homepage content requests
    "product_search": [82],  # Product search/browse
    "global_config": [17],  # Configuration
}

def generate_replay_for_entries(entries, output_file):
    """Generate Python replay code for specific HAR entries"""
    entries_str = ",".join(str(e) for e in entries)
    cmd = [
        "python", "har_preview.py", 
        "sephora_ux_comprehensive.har",
        "--generate-python", output_file,
        "--python-requests", entries_str
    ]
    
    print(f"Generating replay code for entries {entries_str}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"  ✓ Generated {output_file}")
    else:
        print(f"  ✗ Failed to generate {output_file}")
        print(f"    Error: {result.stderr}")
    
    return result.returncode == 0

def main():
    """Generate validation scripts for each API category"""
    print("=" * 50)
    print("Generating Validation Scripts from HAR")
    print("=" * 50)
    
    for category, entries in KEY_ENTRIES.items():
        output_file = f"tests/validate_{category}.py"
        generate_replay_for_entries(entries, output_file)
    
    print("\n" + "=" * 50)
    print("Validation Script Generation Complete")
    print("=" * 50)
    print("\nThese scripts can be used to:")
    print("1. Validate our API responses against real Sephora responses")
    print("2. Understand the exact request/response format")
    print("3. Test our normalization and abstraction layer")
    
    print("\nWARNING: Do not execute these scripts against production Sephora APIs")
    print("without permission. They are for reference and local testing only.")

if __name__ == "__main__":
    main()
