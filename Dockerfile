# Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium
# ---> Bloco do Link Simbólico <---
RUN mkdir -p /app/playwright-browsers/chromium-1105/chrome-linux && \
    ln -s /ms-playwright/chromium-1105/chrome-linux/chrome /app/playwright-browsers/chromium-1105/chrome-linux/chrome
COPY . .
EXPOSE 8000
# ---> Comando CMD com --bind <---
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
