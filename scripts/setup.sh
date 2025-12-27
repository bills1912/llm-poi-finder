#!/bin/bash

# HeyPico Maps LLM - Setup Script
# This script helps set up the development environment

set -e

echo "=========================================="
echo "  HeyPico Maps LLM - Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check Python
echo "Checking prerequisites..."
echo ""

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_status "Python found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    print_status "pip3 found"
else
    print_warning "pip3 not found. Installing..."
    python3 -m ensurepip --upgrade
fi

# Check Docker (optional)
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    print_status "Docker found: $DOCKER_VERSION"
else
    print_warning "Docker not found (optional)"
fi

# Check Ollama
echo ""
echo "Checking Ollama installation..."

if command -v ollama &> /dev/null; then
    print_status "Ollama found"
    
    # Check if Ollama is running
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        print_status "Ollama is running"
        
        # Check for models
        MODELS=$(curl -s http://localhost:11434/api/tags | python3 -c "import sys, json; print(', '.join([m['name'] for m in json.load(sys.stdin).get('models', [])]))" 2>/dev/null || echo "")
        if [ -n "$MODELS" ]; then
            print_status "Available models: $MODELS"
        else
            print_warning "No models found. Run: ollama pull llama3.2"
        fi
    else
        print_warning "Ollama is not running. Start with: ollama serve"
    fi
else
    print_warning "Ollama not found. Install from: https://ollama.com/download"
fi

# Set up backend
echo ""
echo "Setting up backend..."

cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    print_status "Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt --quiet
print_status "Python dependencies installed"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_warning "Created .env file from template. Please edit with your API keys."
else
    print_status ".env file exists"
fi

# Deactivate virtual environment
deactivate

cd ..

# Summary
echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your Google Maps API keys:"
echo "   Edit backend/.env"
echo ""
echo "2. Ensure Ollama is running:"
echo "   ollama serve"
echo ""
echo "3. Pull an LLM model (if not done):"
echo "   ollama pull llama3.2"
echo ""
echo "4. Start the application:"
echo "   ./scripts/start.sh"
echo ""
echo "   Or manually:"
echo "   - Terminal 1: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "   - Terminal 2: cd frontend && python3 -m http.server 3000"
echo ""
echo "5. Open in browser:"
echo "   http://localhost:3000"
echo ""
