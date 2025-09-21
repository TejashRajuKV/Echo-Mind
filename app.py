import os
import json
from urllib.parse import urlparse

from flask import Flask, request, jsonify
from flask_cors import CORS

# --- Configuration ---
# Make sure you have authenticated with Google Cloud CLI and set your project:
# 1. gcloud auth application-default login
# 2. gcloud config set project YOUR_PROJECT_ID
#    (IMPORTANT: Replace 'YOUR_PROJECT_ID' with your actual Google Cloud Project ID)

PROJECT_ID = "echo-mind-472808"

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

@app.route('/analyze', methods=['POST'])
def analyze():
    # These globals are used to persist state across requests for this simple demo.
    global user_points, user_badges

    data = request.get_json()
    if not data or 'claim' not in data:
        return jsonify({"error": "Invalid request. 'claim' key is missing."}), 400

    claim_text = data['claim']

    # Call the stateless analysis function, passing in the current server state.
    result = analyze_claim(claim_text, user_points, user_badges)

    # Update the server's state with the new values returned by the analysis function.
    user_points = result.get("gamification", {}).get("points", user_points)
    user_badges = result.get("gamification", {}).get("badges", user_badges)

    return jsonify(result)

if __name__ == '__main__':
    # Use port 8080 for compatibility with cloud environments
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)