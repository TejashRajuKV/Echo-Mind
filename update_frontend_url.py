#!/usr/bin/env python3
"""
Script to update frontend JavaScript files to use the deployed backend URL
Usage: python update_frontend_url.py <backend_url>
"""

import sys
import os
import re

def update_js_files(backend_url):
    """Update JavaScript files to use the new backend URL"""
    
    # Remove trailing slash if present
    backend_url = backend_url.rstrip('/')
    
    # Files to update
    js_files = [
        'script.js',
        'static/js/script.js'  # In case it's in a static folder
    ]
    
    for js_file in js_files:
        if os.path.exists(js_file):
            print(f"Updating {js_file}...")
            
            with open(js_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace localhost URLs with the deployed URL
            patterns = [
                r'http://localhost:8080',
                r'http://127\.0\.0\.1:8080',
                r'localhost:8080',
                r'127\.0\.0\.1:8080'
            ]
            
            for pattern in patterns:
                content = re.sub(pattern, backend_url, content)
            
            with open(js_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✓ Updated {js_file}")
        else:
            print(f"⚠ File not found: {js_file}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_frontend_url.py <backend_url>")
        print("Example: python update_frontend_url.py https://echo-mind-abc123-uc.a.run.app")
        sys.exit(1)
    
    backend_url = sys.argv[1]
    print(f"Updating frontend to use backend URL: {backend_url}")
    update_js_files(backend_url)
    print("✓ Frontend update complete!")
    print("Don't forget to commit and push the changes to GitHub!")