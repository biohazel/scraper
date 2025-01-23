FROM python:3.10-slim

# Instala dependências do Chrome e do sistema
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
    libxss1 \  # Corrigido: "libxssl" para "libxss1"
    fonts-liberation \
    xdg-utils \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*  # Limpa o cache para reduzir o tamanho da imagem

# Configura o ChromeDriver (com substituição forçada)
RUN ln -sf /usr/lib/chromium/chromedriver /usr/bin/chromedriver

# Configura o diretório de trabalho e instala dependências Python
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código após instalar dependências (para aproveitar o cache)
COPY . .

# Expõe a porta e inicia a aplicação
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]  # Corrigido: "@.0.0.0" → "0.0.0.0" e "@000" → "8000"