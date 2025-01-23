FROM python:3.10-slim

# Instala dependências essenciais
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
    libharfbuzz0b \
    # Corrige caminho do chromedriver
    && ln -s /usr/lib/chromium/chromedriver /usr/bin/chromedriver

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]