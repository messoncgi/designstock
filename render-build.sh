#!/usr/bin/env bash
# Script de build para o Render

# Instala os navegadores do Playwright
echo "Instalando navegadores do Playwright..."
python3 -m playwright install chromium --with-deps

# Exibe mensagem de conclusão
echo "Instalação dos navegadores concluída com sucesso!"