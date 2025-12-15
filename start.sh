#!/bin/bash
# Start script for Render/Railway
# Note: In production, you typically run Web and Worker as separate services.

if [ "$1" == "web" ]; then
    echo "Starting Web Server..."
    uvicorn scholarship_scraper.app.main:app --host 0.0.0.0 --port $PORT
elif [ "$1" == "worker" ]; then
    echo "Starting Celery Worker..."
    celery -A scholarship_scraper.app.tasks.celery_app worker --loglevel=info
elif [ "$1" == "beat" ]; then
    echo "Starting Celery Beat..."
    celery -A scholarship_scraper.app.tasks.celery_app beat --loglevel=info
else
    echo "Usage: ./start.sh [web|worker|beat]"
fi
