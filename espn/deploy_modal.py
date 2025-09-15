#!/usr/bin/env python3
"""
Modal deployment script for ESPN HAR API
Deploys the ESPN provider as a serverless web API using Modal
"""

import modal
import sys
from pathlib import Path

# Create Modal app
app = modal.App("espn-dynamic-har-api")

# Define the image with all dependencies
image = (
    modal.Image.debian_slim()
    .pip_install([
        "fastapi",
        "uvicorn", 
        "httpx",
        "pydantic"
    ])
    .add_local_dir("espn_provider", remote_path="/root/espn_provider")
    .add_local_file("home_with_scrolling.har", remote_path="/root/home_with_scrolling.har") 
    .add_local_file("top_events_scores.har", remote_path="/root/top_events_scores.har")
    .add_local_file("more_sports_categories_select_one_get_event_details.har", remote_path="/root/more_sports_categories_select_one_get_event_details.har")
)

@app.function(
    image=image,
    scaledown_window=300,  # 5 minutes
    timeout=60
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def espn_har_api():
    """ESPN HAR API FastAPI application"""
    
    # Add the package to Python path  
    sys.path.insert(0, "/root")
    
    from fastapi import FastAPI
    from espn_provider.espn_provider.router import router
    
    # Create FastAPI app
    app = FastAPI(
        title="ESPN Dynamic HAR API",
        description="""
        ESPN API that uses HAR (HTTP Archive) files as a reverse engineering tool
        to dynamically extract data from the ESPN mobile app.
        
        This API provides LLM-friendly endpoints that serve ESPN content including:
        - Home feed with personalized content
        - Live scores and events  
        - Sports categories and navigation
        - Search functionality
        
        Data is extracted in real-time from HAR files captured from the ESPN mobile app.
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Include the ESPN router
    app.include_router(router)
    
    return app

if __name__ == "__main__":
    # Deploy the app
    print("Deploying ESPN HAR API to Modal...")
