FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
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
    libdrm2 \
    libexpat1 \
    libfontconfig1 \
    libglib2.0-0 \
    libharfbuzz0b \
    libnspr4 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]