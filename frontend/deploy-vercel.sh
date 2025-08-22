#!/bin/bash
# VoiceAI Frontend - Vercel Deployment Script

echo "🚀 Deploying VoiceAI Frontend to Vercel..."

# Check if we're in the frontend directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Run this script from the frontend directory"
    exit 1
fi

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "📦 Installing Vercel CLI..."
    npm install -g vercel
fi

# Build the project first to check for errors
echo "🔨 Building project..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Build failed. Please fix errors before deploying."
    exit 1
fi

echo "✅ Build successful!"

# Deploy to Vercel
echo "🌐 Deploying to Vercel..."
vercel --prod

echo "🎉 Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Set environment variables in Vercel dashboard:"
echo "   - REACT_APP_API_URL=https://your-railway-app.railway.app"
echo "   - REACT_APP_ENVIRONMENT=production"
echo ""
echo "2. Update Railway CORS settings to include your Vercel URL"
echo ""
echo "3. Test the deployment by visiting your Vercel URL"
echo ""
echo "🔗 Useful links:"
echo "- Vercel Dashboard: https://vercel.com/dashboard"
echo "- Railway Dashboard: https://railway.app/dashboard"