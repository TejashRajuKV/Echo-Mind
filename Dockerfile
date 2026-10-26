# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# OCR uses the Tesseract executable through pytesseract.
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only runtime code and public frontend assets; never include local .env
# files, databases, logs, or private admin tools in the image.
COPY app.py analysis_engine.py api_decision_engine.py context_memory.py database_helper.py evidence_engine.py incremental_verification.py notification_store.py ocr_support.py verdict_policy.py verification_engine.py ./
COPY claim_evolution.py claim_monitor.py document_analysis.py indian_language_engine.py shareable_report.py transparency_dashboard.py ./
COPY data/claim_family_eval.jsonl ./data/
COPY index.html script.js styles.css ./
COPY assets/ ./assets/

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "app.py"]
