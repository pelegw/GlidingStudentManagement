FROM python:3.13-alpine3.21

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Copy requirements file first for better caching
COPY gliding_club/requirements.txt /app/

# Install dependencies
RUN apk add --no-cache --virtual .build-deps \
        gcc \
        # ... other build dependencies ...
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps

# Copy only the application code (not the venv)
COPY gliding_club/ /app/
RUN chmod 755 /app/entrypoint.sh
# Create a non-root user and switch to it
RUN adduser -D appuser
RUN chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=35s --start-period=30s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8000/ || exit 1

# Run gunicorn
ENTRYPOINT ["/app/entrypoint.sh"]