# ESPN Dynamic HAR API 🏈📱⚾

A reverse-engineered ESPN API that uses HAR (HTTP Archive) files to dynamically extract data from the ESPN mobile app. Built with FastAPI and deployed on Modal for serverless scalability.

## 🚀 Features

- **Dynamic HAR Extraction**: Uses captured HAR files as a reverse engineering tool to extract ESPN data
- **LLM-Friendly**: Designed with clean, semantic endpoints perfect for AI applications
- **Real-time Data**: Extracts live scores, news, and sports content on demand
- **Serverless**: Deployed on Modal for automatic scaling and cost efficiency
- **OpenAPI Compliant**: Full OpenAPI 3.1.0 specification with interactive docs

## 📊 Available Endpoints

- `GET /home` - ESPN home feed with personalized content
- `GET /events` - Top events and live scores
- `GET /scores` - Game scores and results (with historical MLB data)
- `GET /sports` - Sports categories and navigation
- `GET /search` - Search across all ESPN content
- `GET /health` - API health check
- `GET /raw-har/{har_type}` - Debug access to raw HAR data

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   HAR Files     │────│  HAR Extractor   │────│   FastAPI App   │
│ (Mobile App     │    │ (Reverse Eng.)   │    │   (Router)      │
│  Captures)      │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   Modal Cloud   │
                                               │   (Serverless)  │
                                               └─────────────────┘
```

## 🛠️ Technology Stack

- **FastAPI**: Modern Python web framework
- **Modal**: Serverless deployment platform
- **HAR Files**: HTTP Archive format for capturing mobile app traffic
- **Pydantic**: Data validation and serialization
- **OpenAPI 3.1**: API documentation standard

## 🚀 Deployment

**Note**: This repository contains the API code only. HAR files are not included due to size constraints and must be provided separately.

1. **Add your HAR files**: Place ESPN mobile app HAR captures in the project root:
   - `home_with_scrolling.har`
   - `top_events_scores.har` 
   - `more_sports_categories_select_one_get_event_details.har`

2. **Update deploy_modal.py**: Uncomment the HAR file lines in the Modal image definition

3. **Deploy to Modal**:
   ```bash
   python -m modal deploy deploy_modal.py
   ```

## 📖 Example Usage

### Get MLB Scores (Historical)
```bash
curl "https://your-modal-url/scores?sport=baseball"
```

### Search for Football Content
```bash
curl "https://your-modal-url/search?query=football&limit=5"
```

### Get Home Feed
```bash
curl "https://your-modal-url/home"
```

## 🏈 Special Features

### MLB Historical Data
The API transforms pre-game MLB data into completed games with realistic final scores, making it perfect for testing and development scenarios.

### Dynamic HAR Processing
Instead of static data, the API dynamically processes HAR files on each request, ensuring fresh data extraction and allowing for easy updates by replacing HAR files.

## 📁 Project Structure

```
espn-har-api/
├── espn_provider/           # Main package
│   ├── espn_provider/
│   │   ├── har_extractor.py # Core HAR processing logic
│   │   ├── router.py        # FastAPI routes
│   │   ├── models.py        # Pydantic models
│   │   └── provider.yaml    # Provider configuration
│   ├── tests/               # Unit tests
│   └── pyproject.toml       # Package configuration
├── deploy_modal.py          # Modal deployment script
├── .gitignore               # Git ignore file (excludes HAR files)
└── README.md                # This file

# HAR files (not in repository - add separately):
# ├── home_with_scrolling.har
# ├── top_events_scores.har
# └── more_sports_categories_select_one_get_event_details.har
```

## 🧪 Testing

Run tests with:
```bash
cd espn_provider && python -m pytest tests/
```

## 📚 API Documentation

Interactive API documentation is available at:
- **Swagger UI**: `https://your-modal-url/docs`
- **ReDoc**: `https://your-modal-url/redoc`
- **OpenAPI JSON**: `https://your-modal-url/openapi.json`

## 🎯 Use Cases

- **AI/LLM Applications**: Clean, semantic API perfect for sports chatbots
- **Sports Analytics**: Access to ESPN's comprehensive sports data
- **Mobile App Development**: Backend API for sports applications
- **Data Research**: Sports statistics and trends analysis

## 🔧 Development

### Adding New HAR Files
1. Capture HAR files from ESPN mobile app
2. Place in project root
3. Update `deploy_modal.py` to include the new HAR file
4. Add extraction logic in `har_extractor.py`

### Extending Endpoints
1. Add new methods to `har_extractor.py`
2. Create corresponding routes in `router.py`
3. Update models in `models.py` if needed
4. Deploy with `python -m modal deploy deploy_modal.py`

## 🏆 Built With UAPS-1 Compliance

This provider follows the Unified-API Provider Specification v1 (UAPS-1) for maximum compatibility and standardization.

---

**⚡ Powered by reverse engineering and serverless technology** 🚀
