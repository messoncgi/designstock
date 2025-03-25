FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    libsoup-3.0-0 \
    libgstreamer-gl1.0-0 \
    libgstreamer-plugins-bad1.0-0 \
    libenchant-2-2 \
    libsecret-1-0 \
    libmanette-0.2-0 \
    libgles2 \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# Instalar Playwright e suas dependências
RUN pip install playwright && playwright install --with-deps

# Copiar o código da aplicação
COPY . .

# Definir o comando de inicialização
CMD ["gunicorn", "app:app"]
