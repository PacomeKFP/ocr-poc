FROM nexus.orange.cm:4443/digitalisation/python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/ocr_outputs

# Expose API port
EXPOSE 8080

# Set environment variables
ENV PYTHONPATH=/app
ENV MODEL_CACHE_DIR=/app/models

# Start with Gunicorn
CMD ["gunicorn", "--config", "gunicorn.conf.py", "api_server:app"]