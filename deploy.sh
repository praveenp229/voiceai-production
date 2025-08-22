#!/bin/bash
# VoiceAI Cloud Deployment Script

set -e

echo "🚀 VoiceAI Cloud Deployment Starting..."

# Check if required environment variables are set
required_vars=("OPENAI_API_KEY" "JWT_SECRET" "DB_PASSWORD")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: $var is not set"
        exit 1
    fi
done

# Build and deploy with Docker Compose
echo "📦 Building application containers..."
docker-compose build --no-cache

echo "🗄️ Setting up database..."
docker-compose up -d db
sleep 10

echo "🔧 Running database migrations..."
# Add your database migration commands here if needed

echo "🚀 Starting all services..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 30

# Health check
echo "🏥 Running health checks..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed"
    docker-compose logs backend
    exit 1
fi

if curl -f http://localhost:80 > /dev/null 2>&1; then
    echo "✅ Frontend is healthy"
else
    echo "❌ Frontend health check failed"
    docker-compose logs frontend
    exit 1
fi

echo "🎉 VoiceAI deployment completed successfully!"
echo "🌐 Frontend: http://localhost"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"

# Show running containers
echo "📋 Running containers:"
docker-compose ps