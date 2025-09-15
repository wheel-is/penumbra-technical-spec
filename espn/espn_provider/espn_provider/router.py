"""FastAPI router for ESPN API endpoints using dynamic HAR extraction."""

from fastapi import APIRouter, Query, HTTPException, Path
from fastapi.routing import APIRoute
from typing import Optional, List, Dict, Any
from datetime import datetime

from .models import (
    ClubhouseResponse,
    HomeFeedResponse,
    TopEventsResponse,
    SportsListResponse,
    EventDetailsResponse,
    Event
)

from .har_extractor import ESPNHARExtractor

# Generate clean operation IDs based on function names
def gen_operation_id(route: APIRoute) -> str:
    return route.name

# Create router with custom operation ID generator
router = APIRouter(generate_unique_id_function=gen_operation_id)

# Initialize HAR extractor
har_extractor = ESPNHARExtractor()


@router.get("/", tags=["API Info"])
async def root():
    """Root endpoint with API information and available endpoints."""
    return {
        "message": "ESPN Dynamic HAR API",
        "description": "Reverse engineered ESPN mobile app using HAR files", 
        "version": "1.0.0",
        "endpoints": {
            "home": "/home",
            "events": "/events", 
            "sports": "/sports",
            "search": "/search",
            "scores": "/scores",
            "health": "/health",
            "documentation": "/docs"
        },
        "data_source": "ESPN Mobile App HAR Files"
    }


@router.get("/home")
async def get_home_feed(
    lang: str = Query("en", description="Language code"),
    region: str = Query("US", description="Region code"),
    platform: str = Query("ios", description="Platform"),
    personalized: bool = Query(True, description="Enable personalization"),
    limit: int = Query(20, description="Number of items to return", ge=1, le=100)
) -> Dict[str, Any]:
    """Get the ESPN home feed using dynamic HAR extraction.
    
    Returns personalized home feed with news, scores, videos, and featured content
    extracted directly from ESPN mobile app HAR files.
    """
    try:
        return har_extractor.extract_home_feed()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract home feed: {str(e)}")


@router.get("/events")
async def get_top_events(
    competition_id: Optional[str] = Query(None, description="Competition ID", alias="ceId"),
    limit: int = Query(20, description="Number of events to return", ge=1, le=100),
    offset: int = Query(0, description="Offset for pagination", ge=0),
    sport: Optional[str] = Query(None, description="Filter by sport")
) -> Dict[str, Any]:
    """Get top live events and scores using dynamic HAR extraction.
    
    Returns live scores, game details, and trending events extracted from
    ESPN mobile app HAR files with real betting odds and game data.
    """
    try:
        return har_extractor.extract_top_events()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract events: {str(e)}")


@router.get("/sports")
async def get_sports_categories(
    profile: str = Query("sports-card", description="Profile type"),
    lang: str = Query("en", description="Language code"),
    region: str = Query("US", description="Region code"),
    category: Optional[str] = Query(None, description="Filter by category")
) -> Dict[str, Any]:
    """Get sports categories and league navigation using dynamic HAR extraction.
    
    Returns hierarchical sports navigation structure with leagues, teams, and
    competition data extracted from ESPN mobile app HAR files.
    """
    try:
        return har_extractor.extract_sports_categories()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract sports categories: {str(e)}")


@router.get("/search")
async def search_content(
    query: str = Query(..., description="Search query"),
    type: str = Query("all", description="Content type to search (all, teams, players, news, events)"),
    limit: int = Query(20, description="Number of results", ge=1, le=100)
) -> Dict[str, Any]:
    """Search across all ESPN content using dynamic HAR extraction.
    
    Searches through home feed, events, and sports data extracted from HAR files
    to find relevant content matching the query.
    """
    try:
        return har_extractor.search_content(query, type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/scores")
async def get_scores(
    lang: str = Query("en", description="Language code"),
    region: str = Query("US", description="Region code"),
    sport: Optional[str] = Query(None, description="Filter by sport"),
    date: Optional[str] = Query(None, description="Date in YYYYMMDD format"),
    live_only: bool = Query(False, description="Only show live games")
) -> Dict[str, Any]:
    """Get current scores and game results.
    
    Alias for /events endpoint focused on score data.
    """
    try:
        # Use the new extract_scores method
        scores_data = har_extractor.extract_scores()
        
        # Filter by sport if specified
        if sport and scores_data.get('data', {}).get('games'):
            games = scores_data['data']['games']
            filtered_games = [
                game for game in games 
                if sport.lower() in game.get('sport', '').lower()
            ]
            scores_data['data']['games'] = filtered_games
            scores_data['data']['total_games'] = len(filtered_games)
        
        return scores_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract scores: {str(e)}")


@router.get("/event/{event_id}")
async def get_event_details(
    event_id: str = Path(..., description="Event ID"),
    sport: Optional[str] = Query(None, description="Sport identifier"),
    include_betting: bool = Query(True, description="Include betting odds"),
    include_stats: bool = Query(True, description="Include game statistics")
) -> Dict[str, Any]:
    """Get detailed information about a specific event.
    
    Extracts detailed event information from HAR files including game stats,
    betting odds, team info, and live updates.
    """
    try:
        # Search through HAR data for specific event
        events_data = har_extractor.extract_top_events()
        
        if events_data.get('status') == 'success':
            events = events_data.get('data', {}).get('events', [])
            
            # Find matching event
            for event in events:
                if str(event.get('id')) == str(event_id):
                    return {
                        "status": "success",
                        "event": event,
                        "details": {
                            "betting_included": include_betting,
                            "stats_included": include_stats,
                            "source": "ESPN Mobile App HAR"
                        }
                    }
        
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get event details: {str(e)}")


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint to verify HAR extractor is working."""
    try:
        # Test each HAR file can be loaded
        status = {}
        
        for har_type in ['home', 'events', 'sports']:
            try:
                entries = har_extractor.load_har_file(har_type)
                status[har_type] = {
                    "status": "ok",
                    "requests_count": len(entries)
                }
            except Exception as e:
                status[har_type] = {
                    "status": "error", 
                    "error": str(e)
                }
        
        overall_status = "ok" if all(s["status"] == "ok" for s in status.values()) else "degraded"
        
        return {
            "status": overall_status,
            "har_files": status,
            "extractor": "ESPNHARExtractor",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

