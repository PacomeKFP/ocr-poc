# Gunicorn configuration for ID Card OCR
import multiprocessing

# Server socket
bind = "0.0.0.0:8080"
backlog = 2048

# Worker processes
workers = 1  # Single worker to avoid OCR model reloading
worker_class = "sync"
worker_connections = 1000
timeout = 300  # 5 minutes pour OCR long
keepalive = 2

# Memory management
max_requests = 100
max_requests_jitter = 10
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'id-card-ocr'

# Graceful timeout
graceful_timeout = 30

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190