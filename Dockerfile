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

# Generate gRPC files
COPY ocr_service.proto .
RUN python -m grpc_tools.protoc --python_out=. --grpc_python_out=. --proto_path=. ocr_service.proto

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/ocr_outputs

# Expose gRPC port
EXPOSE 50051
EXPOSE 8080

# Set environment variables
ENV PYTHONPATH=/app
ENV MODEL_CACHE_DIR=/app/models

# Start the gRPC server
CMD ["python", "start_services.py"]