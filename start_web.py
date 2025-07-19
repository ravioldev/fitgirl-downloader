#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Startup script for FitGirl Downloader Web
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    print("🚀 Starting FitGirl Downloader Web...")
    print("⏹️  Press Ctrl+C to stop the server")
    print()
    
    # Import and run the Flask application with SocketIO
    from app import app, socketio
    
    # Configure for Docker environment
    import os
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    # Load configuration from config.yaml
    from backend.settings_manager import SettingsManager
    settings_manager = SettingsManager()
    settings_manager.load_settings()
    
    # Use configuration from settings
    host = settings_manager.settings.web_host
    port = settings_manager.settings.web_port
    debug = settings_manager.settings.debug_mode
    
    print(f"📱 Open your browser at: http://localhost:{port}")
    
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True) 