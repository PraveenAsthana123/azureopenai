#!/bin/bash
#===============================================================================
# WebLLM Platform - Local Development Setup
#===============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}Setting up local development environment...${NC}"

# Backend setup
echo -e "${BLUE}Setting up backend...${NC}"
cd "$PROJECT_ROOT/backend"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create .env file if not exists
if [ ! -f .env ]; then
    cat > .env << EOF
DEBUG=true
WORKERS=1
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_SSL=false
MLC_LLM_ENDPOINT=http://localhost:8000
EOF
    echo "Created .env file"
fi

# Frontend setup
echo -e "${BLUE}Setting up frontend...${NC}"
cd "$PROJECT_ROOT/frontend"
npm install

# Create .env file if not exists
if [ ! -f .env ]; then
    cat > .env << EOF
VITE_API_URL=http://localhost:8080/api
EOF
    echo "Created .env file"
fi

echo -e "${GREEN}Local development setup completed!${NC}"
echo ""
echo "To start the backend:"
echo "  cd backend && source .venv/bin/activate && uvicorn src.main:app --reload"
echo ""
echo "To start the frontend:"
echo "  cd frontend && npm run dev"
