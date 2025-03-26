FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# Instalar dependências do sistema de forma detalhada
RUN apt-get update && apt-get install -y \
    libsoup-3.0-0 \
    libgstreamer-gl1.0-0 \
    libgstreamer-gl1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    libgstcodecparsers-1.0-0 \
    libenchant-2-2 \
    libsecret-1-0 \
    libmanette-0.2-0 \
    libgles2 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Definir variáveis de ambiente para o Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/app/playwright-browsers
ENV PATH="/app/playwright-browsers/chromium-$PLAYWRIGHT_CHROMIUM_VERSION:${PATH}"

# Definir diretório de trabalho
WORKDIR /app

# Copiar requisitos e instalar dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar dependências do Playwright com verificação adicional
RUN playwright install-deps && \
    playwright install chromium

# Copiar o resto do código da aplicação
COPY . .

# Definir o comando padrão
CMD ["gunicorn", "app:app"]
