FROM python:3.11-slim

# Instalar dependências do sistema necessárias para o Playwright
RUN apt-get update && apt-get install -y \
    # Dependências base do sistema
    wget \
    gnupg \
    unzip \
    ca-certificates \
    # Dependências de sistema gráfico e renderização
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    # Dependências de renderização e gráficos
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    # Dependências específicas do Playwright
    libsoup-3.0-0 \
    libgstreamer-gl1.0-0 \
    libgstreamer-plugins-bad1.0-0 \
    libenchant-2-2 \
    libsecret-1-0 \
    libmanette-0.2-0 \
    libgles2 \
    libgl1 \
    libxshmfence-dev \
    # Dependências para codec e plugin
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-libav \
    && rm -rf /var/lib/apt/lists/*

# Configurar variáveis de ambiente para o Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/app/playwright-browsers
ENV PATH="/app/playwright-browsers/chromium-$PLAYWRIGHT_CHROMIUM_VERSION:${PATH}"

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Playwright e suas dependências
RUN pip install --upgrade pip \
    && pip install playwright \
    && playwright install --with-deps chromium

# Copiar o código da aplicação
COPY . .

# Definir o comando de inicialização
CMD ["gunicorn", "app:app"]
