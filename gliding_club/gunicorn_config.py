# gunicorn_config.py
import multiprocessing

# Binding
bind = "0.0.0.0:8000"  # Change this to the IP and port you want to serve on

# Worker Processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
errorlog = 'logs/gunicorn-error.log'
accesslog = 'logs/gunicorn-access.log'
loglevel = 'info'