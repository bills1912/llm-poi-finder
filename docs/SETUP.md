# Setup Guide

This guide will walk you through setting up the HeyPico Maps LLM application from scratch.

## Prerequisites

### Required Software

1. **Python 3.10+**
   ```bash
   python3 --version
   ```

2. **Node.js 18+ (optional, for development)**
   ```bash
   node --version
   ```

3. **Docker & Docker Compose (recommended)**
   ```bash
   docker --version
   docker-compose --version
   ```

4. **Ollama (for local LLM)**
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.com/install.sh | sh
   ```

---

## Step 1: Google Cloud Setup

### 1.1 Create Google Cloud Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Sign up for a new account (get $300 free credit)
3. Create a new project (e.g., "heypico-maps-llm")

### 1.2 Enable Required APIs

Navigate to **APIs & Services > Library** and enable:

- ✅ Maps JavaScript API
- ✅ Places API
- ✅ Directions API
- ✅ Geocoding API

### 1.3 Create API Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > API Key**
3. Create TWO API keys:

**Backend API Key:**
- Name: "Backend Server Key"
- Restrictions:
  - Application restrictions: IP addresses
  - Add your server IP (or `0.0.0.0/0` for development)
  - API restrictions: Places API, Directions API, Geocoding API

**Frontend API Key:**
- Name: "Frontend Web Key"  
- Restrictions:
  - Application restrictions: HTTP referrers
  - Add: `http://localhost:3000/*`, `http://localhost:8080/*`
  - API restrictions: Maps JavaScript API

### 1.4 Set Usage Quotas (Important!)

Go to **APIs & Services > Quotas** and set limits to prevent unexpected charges:

| API | Recommended Daily Limit |
|-----|------------------------|
| Places API | 1,000 requests |
| Directions API | 500 requests |
| Geocoding API | 500 requests |
| Maps JavaScript API | 25,000 loads |

---

## Step 2: Install Ollama and LLM Model

### 2.1 Install Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows
# Download from https://ollama.com/download
```

### 2.2 Start Ollama Service

```bash
# Start the Ollama server
ollama serve
```

### 2.3 Pull a Model

Choose one of these models:

```bash
# Recommended: Good balance of quality and speed
ollama pull llama3.2

# Alternative: Fast and lightweight
ollama pull phi3

# Alternative: Great quality
ollama pull mistral
```

### 2.4 Verify Installation

```bash
# Test the model
ollama run llama3.2 "Hello, how are you?"
```

---

## Step 3: Project Setup

### 3.1 Clone/Download the Project

```bash
cd heytico-maps-llm
```

### 3.2 Configure Environment Variables

```bash
# Copy the example environment file
cp backend/.env.example backend/.env

# Edit with your API keys
nano backend/.env
```

Update these values in `.env`:
```
GOOGLE_MAPS_API_KEY=your_backend_api_key_here
GOOGLE_MAPS_FRONTEND_KEY=your_frontend_api_key_here
LLM_MODEL=llama3.2
```

---

## Step 4: Running the Application

### Option A: Using Docker (Recommended)

```bash
# Set environment variables
export GOOGLE_MAPS_API_KEY=your_backend_key
export GOOGLE_MAPS_FRONTEND_KEY=your_frontend_key

# Build and run
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### Option B: Manual Setup

#### Terminal 1: Start Ollama
```bash
ollama serve
```

#### Terminal 2: Start Backend
```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Terminal 3: Start Frontend
```bash
cd frontend

# Simple Python server
python3 -m http.server 3000

# Or use Node.js
npx serve -l 3000
```

---

## Step 5: Verify Installation

### 5.1 Check Health Endpoint

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
    "status": "healthy",
    "services": {
        "llm": {"status": "up", "model": "llama3.2"},
        "maps": {"status": "configured"}
    }
}
```

### 5.2 Access the Application

Open your browser and navigate to:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

### 5.3 Test a Query

Type in the chat: "Where can I find good coffee nearby?"

---

## Troubleshooting

### LLM Not Available

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
pkill ollama
ollama serve
```

### Google Maps Not Loading

1. Check browser console for errors
2. Verify API key is correct
3. Check API key restrictions match your domain
4. Ensure billing is enabled on Google Cloud

### Rate Limit Exceeded

- Wait for the rate limit window to reset
- Check `Retry-After` header in response
- Consider increasing limits in `.env`

### CORS Errors

Add your frontend URL to `ALLOWED_ORIGINS` in `.env`:
```
ALLOWED_ORIGINS=http://localhost:3000,http://your-domain.com
```

---

## Production Deployment

### Security Checklist

- [ ] Use separate API keys for frontend/backend
- [ ] Set proper API key restrictions in Google Cloud
- [ ] Enable HTTPS
- [ ] Set `DEBUG=false`
- [ ] Configure proper rate limits
- [ ] Set up monitoring and logging
- [ ] Use environment variables for all secrets
- [ ] Regular security updates

### Recommended Hosting

- **Backend**: AWS EC2, Google Cloud Run, DigitalOcean
- **Frontend**: Vercel, Netlify, Cloudflare Pages
- **LLM**: Self-hosted or use cloud LLM API

---

## Getting Help

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Review the API documentation: `/docs`
3. Verify all services are running: `/health`
