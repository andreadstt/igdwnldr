#!/usr/bin/env python3
"""
Development server runner for IG Downloader webapp
"""
import os
from app import create_app

# Create Flask app
app = create_app('development')

if __name__ == '__main__':
    print("=" * 60)
    print("  Instagram Downloader - Web Application")
    print("=" * 60)
    print(f"\nStarting development server...")
    print(f"Downloads folder: {app.config['DOWNLOAD_FOLDER']}")
    print(f"🔗 Open in browser: http://127.0.0.1:5000")
    print("\nPress CTRL+C to stop\n")
    
    # Run development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )
