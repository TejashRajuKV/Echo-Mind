import os
import json
import time
from urllib.parse import urlparse
import secrets
from functools import wraps

from flask import Flask, request, jsonify
from flask_cors import CORS

# --- Configuration ---
# Make sure you have authenticated with Google Cloud CLI and set your project:
# 1. gcloud auth application-default login
# 2. gcloud config set project YOUR_PROJECT_ID
#    (IMPORTANT: Replace 'YOUR_PROJECT_ID' with your actual Google Cloud Project ID)

PROJECT_ID = "echo-mind-472808"

# API Key for authentication (you can change this to any secure key)
API_KEY = os.environ.get('ECHO_MIND_API_KEY', 'gdo4N6BnLrvu9MOaH25Ml5M8msPjVf9tsez24Dq8eRI')

# Rate limiting (simple in-memory counter)
request_counts = {}
MAX_REQUESTS_PER_HOUR = 100

LOCATION = "us-central1"
# --- Centralized Analysis Logic ---
# The core logic is now imported from analysis_engine.py to avoid code duplication.
# Make sure you have renamed 'google_hackathonipynb (1).py' to 'analysis_engine.py'.
try:
    from analysis_engine import analyze_claim
except ImportError:
    raise RuntimeError("Could not import 'analyze_claim'. Please rename 'google_hackathonipynb (1).py' to 'analysis_engine.py'.")

# --- Server State Management ---
# For this demo, we store user progress in memory.
# In a real application, this should be in a database (e.g., Firestore, SQL)
# and tied to a user session or account.
user_points = 0
user_badges = []

# --- Flask Web Server ---

app = Flask(__name__)
CORS(app) # Allows your website to talk to this server

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API key in header or query parameter
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key or api_key != API_KEY:
            return jsonify({
                'error': 'Invalid or missing API key',
                'message': 'Please provide a valid API key in X-API-Key header or api_key parameter'
            }), 401
        
        # Simple rate limiting
        client_ip = request.remote_addr
        current_hour = int(time.time() // 3600)
        key = f"{client_ip}_{current_hour}"
        
        if key in request_counts:
            request_counts[key] += 1
        else:
            request_counts[key] = 1
            
        if request_counts[key] > MAX_REQUESTS_PER_HOUR:
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': f'Maximum {MAX_REQUESTS_PER_HOUR} requests per hour allowed'
            }), 429
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/analyze', methods=['POST'])
@require_api_key
def analyze():
    # These globals are used to persist state across requests for this simple demo.
    global user_points, user_badges

    data = request.get_json()
    if not data or 'claim' not in data:
        return jsonify({"error": "Invalid request. 'claim' key is missing."}), 400

    claim_text = data['claim']

    # Call the stateless analysis function, passing in the current server state.
    # The function will automatically save new analysis to database
    result = analyze_claim(claim_text, user_points, user_badges)

    # Update the server's state with the new values returned by the analysis function.
    user_points = result.get("gamification", {}).get("points", user_points)
    user_badges = result.get("gamification", {}).get("badges", user_badges)

    return jsonify(result)

@app.route('/stats', methods=['GET'])
@require_api_key
def get_database_stats():
    """Get statistics about the learning database"""
    try:
        from database_helper import get_database_stats
        stats = get_database_stats()
        return jsonify({
            "status": "success",
            "data": stats
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Could not retrieve database stats: {str(e)}"
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Public health check endpoint - no authentication required"""
    return jsonify({
        "status": "healthy",
        "service": "Echo Mind AI Fact Checker",
        "message": "Service is running. Authentication required for analysis endpoints.",
        "endpoints": {
            "/analyze": "POST - AI fact checking (requires API key)",
            "/stats": "GET - Database statistics (requires API key)",
            "/health": "GET - Health check (public)"
        }
    })

if __name__ == '__main__':
    # Initialize database with sample data if empty
    try:
        from database_helper import get_database_stats, initialize_sample_data
        stats = get_database_stats()
        if stats.get('total_claims', 0) == 0:
            print("🔄 Initializing database with sample data...")
            initialize_sample_data()
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")
    
    # Use port 8080 for compatibility with cloud environments
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)
