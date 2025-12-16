FROM python:3.9-slim-bullseye

# Install system dependencies (Tesseract, Playwright deps, ffmpeg for video)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    ffmpeg \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libjbig0 \
    liblcms2-2 \
    libopenjp2-7 \
    libtiff5 \
    libwebp6 \
    libwebpmux3 \
    libxslt1.1 \
    libxml2 \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (huge step, might be cached in layers)
RUN playwright install chromium
RUN playwright install-deps

COPY . .

CMD ["uvicorn", "scholarship_scraper.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
