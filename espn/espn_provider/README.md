# ESPN Provider for Unified-API

Access comprehensive sports data from ESPN including live scores, news, event details, and sports statistics.

## Features

- **Live Scores & Events**: Real-time scores and game updates from all major sports
- **Sports News**: Latest news articles and highlights by sport
- **Event Details**: Comprehensive game information including stats and play-by-play
- **Sports Categories**: Browse all available sports and leagues
- **Team & Player Data**: Detailed information about teams and players
- **Personalized Content**: Support for user favorites and preferences

## Supported Sports

- NFL (National Football League)
- NBA (National Basketball Association)
- MLB (Major League Baseball)
- NHL (National Hockey League)
- Soccer (Premier League, MLS, La Liga, etc.)
- Tennis (ATP, WTA, Grand Slams)
- Golf (PGA Tour)
- College Sports (NCAA Football, Basketball)
- And many more...

## Installation

```bash
pip install espn-provider
```

## Quick Start

### Get Home Feed
```python
# Get the main home feed with news and scores
GET /home?region=US&lang=en
```

### Get Live Scores
```python
# Get current scores across all sports
GET /scores

# Get scores for specific sport
GET /scores?sport=nfl

# Get scores for specific date
GET /scores?date=20250826
```

### Get Top Events
```python
# Get top trending live events
GET /events?limit=10
```

### Get Sports List
```python
# Get all available sports and leagues
GET /sports
```

### Get Event Details
```python
# Get detailed information about a specific event
GET /event/401547432?sport=nfl
```

### Search Content
```python
# Search for teams, players, or news
GET /search?query=Lakers&type=teams
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/home` | Get home feed with news and featured content |
| `/scores` | Get current scores and live events |
| `/events/top` | Get top trending events |
| `/sports` | Get list of all sports and leagues |
| `/sports/{sport}/events` | Get events for specific sport |
| `/event/{event_id}` | Get detailed event information |
| `/favorites` | Get user favorites management |
| `/search` | Search for content |
| `/news/{sport}` | Get news for specific sport |

## Response Examples

### Home Feed Response
```json
{
  "clubhouse": {
    "content": [...]
  },
  "feed": {
    "content": [
      {
        "id": "46081223",
        "type": "now",
        "publishedDate": "2025-08-26T19:04:48Z",
        "headline": "Breaking News",
        "items": [...]
      }
    ]
  }
}
```

### Event Response
```json
{
  "id": "401547432",
  "sportName": "Football",
  "eventName": "Chiefs vs Bills",
  "gameState": "in",
  "gameDate": "2025-08-26T20:00:00Z",
  "leagueName": "NFL",
  "statusText": "3rd Quarter",
  "teams": [
    {
      "name": "Kansas City Chiefs",
      "abbreviation": "KC",
      "score": "21",
      "winner": false
    },
    {
      "name": "Buffalo Bills",
      "abbreviation": "BUF",
      "score": "17",
      "winner": false
    }
  ]
}
```

## Rate Limits

- Default: 60 requests per minute
- Burst: 20 requests

## Error Handling

The provider returns standard Unified-API error responses:

```json
{
  "error": {
    "provider_id": "espn",
    "code": "RESOURCE_NOT_FOUND",
    "status": 404,
    "message": "Event not found",
    "details": {}
  }
}
```

## Notes

- ESPN's public APIs are used which don't require authentication
- Some endpoints may return cached data for performance
- Live event data is updated in near real-time
- Personalization features require user initialization

## Support

For issues or questions, please open an issue on the GitHub repository.
