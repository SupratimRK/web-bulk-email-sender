#!/bin/bash

# Deployment script for Render
echo "🚀 Preparing Bulk Mailer for Render deployment..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
fi

# Add all files
echo "Adding files to git..."
git add .

# Commit changes
echo "Committing changes..."
git commit -m "Deploy to Render with keep-alive service"

# Instructions for user
echo ""
echo "✅ Your app is ready for Render deployment!"
echo ""
echo "📋 Next steps:"
echo "1. Push to GitHub:"
echo "   git remote add origin https://github.com/yourusername/bulk-mailer-app.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "2. Deploy on Render:"
echo "   - Go to https://dashboard.render.com"
echo "   - Create new Blueprint from your GitHub repo"
echo "   - Set environment variables (see RENDER_DEPLOYMENT.md)"
echo ""
echo "3. Required environment variables:"
echo "   - SENDER_EMAIL: your-email@domain.com"
echo "   - PASSWORD: your-app-password"
echo "   - FLASK_SECRET_KEY: random-secret-key"
echo "   - FLASK_ENV: production"
echo ""
echo "📖 Full instructions: See RENDER_DEPLOYMENT.md"
echo ""
