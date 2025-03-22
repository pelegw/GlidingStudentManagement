FROM python:3.13-alpine3.21

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install build dependencies, then install Python packages, then remove build dependencies
COPY requirements.txt /app/

# Add SDL2 and other pygame dependencies
RUN apk add --no-cache --virtual .build-deps \
        gcc \
        g++ \
        musl-dev \
        python3-dev \
        postgresql-dev \
        sdl2-dev \
        sdl2_image-dev \
        sdl2_mixer-dev \
        sdl2_ttf-dev \
        freetype-dev \
        jpeg-dev \
        libpng-dev \
        zlib-dev \
    && apk add --no-cache \
        libpq \
        sdl2 \
        sdl2_image \
        sdl2_mixer \
        sdl2_ttf \
        freetype \
        jpeg \
        libpng \
        mesa-gl \
        libxkbcommon \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps

# Copy project
COPY . /app/

# Create a non-root user and switch to it
# Create a non-root user and switch to it
RUN adduser -D appuser
RUN chown -R appuser:appuser /app
USER appuser

# Run gunicorn
ENTRYPOINT ["/app/entrypoint.sh"]

