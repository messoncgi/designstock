# Usar a imagem oficial do Playwright que já inclui dependências e navegadores
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# ---> ADICIONE ESTA LINHA <---
# Explicitamente dizer à biblioteca Python onde encontrar os navegadores pré-instalados
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Definir diretório de trabalho
WORKDIR /app

# Copiar o arquivo de requisitos primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar as dependências Python (incluindo Playwright)
RUN pip install --no-cache-dir -r requirements.txt

# ---> MANTENHA ESTA LINHA POR SEGURANÇA <---
# Garante que o Chromium esteja instalado ou linkado onde a lib Python espera
# (Pode ser redundante com a ENV acima, mas não deve prejudicar)
RUN playwright install chromium

# Copiar o resto do código da sua aplicação
COPY . .

# Expor a porta que o Gunicorn vai usar
EXPOSE 8000

# Comando para iniciar a aplicação via Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
