#!/bin/bash
set -e

echo "🚀 AI Co-Founder Setup"
echo "======================"

# Check prerequisites
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 is required but not installed."
        exit 1
    fi
    echo "✅ $1 found"
}

echo ""
echo "Checking prerequisites..."
check_command docker
check_command node
check_command python3

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys before starting."
fi

# Create frontend .env.local if it doesn't exist
if [ ! -f "frontend/.env.local" ]; then
    echo ""
    echo "📝 Creating frontend/.env.local from template..."
    cp frontend/.env.local.example frontend/.env.local
    echo "⚠️  Please edit frontend/.env.local and add your Clerk keys."
fi

# Backend setup
echo ""
echo "Setting up backend..."
cd backend
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -e ".[dev]" -q
echo "✅ Backend dependencies installed"
cd ..

# Frontend setup
echo ""
echo "Setting up frontend..."
cd frontend
npm install --legacy-peer-deps -q
echo "✅ Frontend dependencies installed"
cd ..

echo ""
echo "======================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Add your API keys to .env and frontend/.env.local"
echo "2. Run 'docker compose -f docker/docker-compose.yml up' to start services"
echo "3. Or run locally:"
echo "   - Backend: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "   - Frontend: cd frontend && npm run dev"
echo ""
