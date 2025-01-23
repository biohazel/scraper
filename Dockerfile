# Start with a lightweight Python image
FROM python:3.10-slim

# Install Debian packages needed for headless Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium-browser \
    libnss3 \
    libx11-6 \
    libgbm1 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    libxss1 \
    fonts-liberation \
    xdg-utils \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Set a working directory
WORKDIR /app

# Copy your requirements
COPY requirements.txt /app/requirements.txt

# Install python dependencies (fastapi, uvicorn, requests, bs4, cloudscraper, selenium, webdriver-manager, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code (main.py, etc.)
COPY . /app

# Expose port 8000 (optional, if you want to map externally)
EXPOSE 8000

# Default command: start the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
