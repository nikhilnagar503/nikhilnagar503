#!/bin/bash

# DevOps PR Auto-Orchestrator Setup Script

set -e

echo "🚀 Setting up DevOps PR Auto-Orchestrator..."

# Create .env file from example if it doesn't exist
if [ ! -f .env ]; then
    echo "📋 Creating .env file from example..."
    cp config/example.env .env
    echo "✅ Created .env file. Please update it with your configuration."
fi

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
echo "🔍 Checking service health..."
if curl -f http://localhost:8000/healthz > /dev/null 2>&1; then
    echo "✅ Web service is healthy!"
else
    echo "❌ Web service is not responding"
    exit 1
fi

# Show service status
echo "📊 Service Status:"
docker-compose ps

echo "🎉 Setup complete!"
echo ""
echo "📖 Next steps:"
echo "1. Update .env file with your GitHub App credentials"
echo "2. Set up webhook URL pointing to http://your-domain:8000/webhook/github"
echo "3. Install your GitHub App on target repositories"
echo ""
echo "🌐 Access points:"
echo "- API: http://localhost:8000"
echo "- Docs: http://localhost:8000/docs"
echo "- Health: http://localhost:8000/healthz"