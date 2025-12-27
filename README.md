# HeyPico Maps LLM - Code Test 2

A local LLM-powered location finder with Google Maps integration. Users can ask the LLM for place recommendations and view locations on an embedded map with directions.

## 🎯 Project Overview

This project implements a conversational AI system that:
- Runs a local LLM (using Ollama) to understand user queries about places
- Integrates with Google Maps API to fetch location data
- Displays interactive maps with markers and directions
- Provides secure API key management and usage limits

## 📁 Project Structure

```
heytico-maps-llm/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entry
│   │   ├── config.py            # Configuration & environment
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py          # Chat/LLM endpoints
│   │   │   └── maps.py          # Google Maps endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm_service.py   # Ollama LLM integration
│   │   │   └── maps_service.py  # Google Maps service
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   └── rate_limiter.py  # Rate limiting middleware
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── validators.py    # Input validation
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── docker-compose.yml
├── scripts/
│   ├── setup.sh
│   └── start.sh
├── docs/
│   ├── API.md
│   ├── SETUP.md
│   └── ASSUMPTIONS.md
└── README.md
```

## 🚀 Quick Start

### Prerequisites

1. **Docker & Docker Compose** (recommended)
2. **Python 3.10+** (for local development)
3. **Google Cloud Account** with Maps API enabled
4. **Ollama** installed locally

### Setup Instructions

#### 1. Clone and Navigate
```bash
cd heytico-maps-llm
```

#### 2. Google Cloud Setup
1. Create a new Google Cloud project at https://console.cloud.google.com
2. Enable the following APIs:
   - Maps JavaScript API
   - Places API
   - Directions API
   - Geocoding API
3. Create API credentials (API Key)
4. Set up API key restrictions:
   - HTTP referrers (for frontend)
   - IP addresses (for backend)
5. Set usage quotas to prevent unexpected charges

#### 3. Environment Configuration
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys
```

#### 4. Install Ollama and Pull Model
```bash
# Install Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the LLM model (choose one)
ollama pull llama3.2        # Recommended: Good balance
ollama pull mistral         # Alternative: Fast
ollama pull phi3            # Alternative: Lightweight
```

#### 5. Run with Docker Compose
```bash
docker-compose up --build
```

#### 6. Or Run Locally
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
python serve_frontend.py
```

### 7. Access the Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 🔐 Security Best Practices

### API Key Protection
- ✅ API keys stored in environment variables, never in code
- ✅ Backend-only API calls (frontend never exposes keys)
- ✅ API key restrictions configured in Google Cloud Console
- ✅ Rate limiting implemented on all endpoints

### Usage Limits
- ✅ Per-user rate limiting (configurable)
- ✅ Daily quota tracking
- ✅ Request validation and sanitization
- ✅ Error handling for quota exceeded

## 📖 API Documentation

See [docs/API.md](docs/API.md) for complete API documentation.

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message to LLM, get places |
| GET | `/api/places/search` | Search places by query |
| GET | `/api/places/details/{id}` | Get place details |
| GET | `/api/directions` | Get directions between points |
| GET | `/api/health` | Health check endpoint |

## 🧠 LLM Integration

The system uses Ollama to run local LLMs. The LLM is prompted to:
1. Understand user intent (finding places to eat, visit, etc.)
2. Extract relevant search parameters (cuisine, location, etc.)
3. Format responses with place recommendations

### Supported Queries
- "Where can I find good sushi near Times Square?"
- "Best coffee shops in downtown Seattle"
- "Recommend Italian restaurants in Chicago"
- "Find parking near Central Park"

## 🗺️ Google Maps Features

- **Place Search**: Find places by query and location
- **Place Details**: Get address, ratings, hours, photos
- **Embedded Maps**: Interactive map display with markers
- **Directions**: Get routes between locations
- **Street View**: Preview locations (optional)

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

## 📝 Assumptions Made

See [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md) for detailed assumptions.

Key assumptions:
1. User has access to Google Cloud free tier ($200 credit)
2. Ollama is available for local LLM deployment
3. Modern browser with JavaScript enabled
4. Single-user or limited concurrent users for demo

## 🛠️ Technology Stack

- **Backend**: Python 3.10+, FastAPI, Pydantic
- **Frontend**: Vanilla JS, HTML5, CSS3
- **LLM**: Ollama (llama3.2/mistral/phi3)
- **Maps**: Google Maps JavaScript API, Places API
- **Container**: Docker, Docker Compose

## 📜 License

MIT License - See LICENSE file

## 👤 Author

Created for HeyPico.ai Fullstack Developer Assessment
