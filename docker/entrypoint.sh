#!/bin/bash

# FitGirl Updater Docker Entrypoint Script

echo "🐳 Starting FitGirl Updater Docker Container..."

# Set display for headless Chrome
export DISPLAY=:99

# Start Xvfb for headless browser support
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
XVFB_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "🛑 Stopping services..."
    kill $XVFB_PID 2>/dev/null
    exit 0
}

# Trap signals for graceful shutdown
trap cleanup SIGTERM SIGINT

# Wait a moment for Xvfb to start
sleep 2

echo "✅ Virtual display started"
echo "🚀 Starting FitGirl Updater Web Application..."
echo "📱 Application will be available at: http://localhost:2121"
echo "⏹️  Use Ctrl+C or docker stop to shutdown"
echo ""

# Start the Flask application
python start_web.py

# If we reach here, the app has stopped
cleanup 