# Usar uma imagem base com Python
FROM python:3.11-slim

# Instalar as dependências do sistema necessárias
RUN apt-get update && apt-get install -y \
    libsoup-3.0-0 \
    libgstreamer-gl1.0-0 \
    libgstreamer-plugins-bad1.0-0 \
    libenchant-2-2 \
    libsecret-1-0 \
    libmanette-0.2-0 \
    libgles2 \
    && rm -rf /var/lib/apt/lists/*

# Copiar o arquivo requirements.txt e instalar as dependências Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# Instalar o Playwright e seus binários
RUN playwright install

# Copiar o restante do código da aplicação
COPY . .

# Definir o comando de inicialização (ajuste conforme sua aplicação)
CMD ["gunicorn", "app:app"]
