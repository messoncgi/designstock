# Usar a imagem oficial do Playwright que já inclui dependências e navegadores
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# Definir diretório de trabalho
WORKDIR /app

# Copiar o arquivo de requisitos primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar as dependências Python (incluindo Playwright, para garantir a versão)
# O --no-cache-dir ajuda a manter a imagem menor
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código da sua aplicação
# Faça isso DEPOIS de instalar dependências para melhor cache
COPY . .

# Expor a porta que o Gunicorn vai usar (opcional, mas boa prática)
EXPOSE 8000

# Comando para iniciar a aplicação via Gunicorn
# Certifique-se que 'app:app' está correto (arquivo app.py, variável app do Flask)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
# Adicionei --bind 0.0.0.0:8000 que é comum para containers e esperado pelo Render
