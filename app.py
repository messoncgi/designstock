import os
import json
import requests
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime
import base64
from collections import defaultdict
import time
from playwright.sync_api import sync_playwright
from flask import Flask, render_template, request, jsonify

# Configurações do Designi
URL_LOGIN = os.getenv('DESIGNI_LOGIN_URL', 'https://designi.com.br/login')
EMAIL = os.getenv('DESIGNI_EMAIL', '')
SENHA = os.getenv('DESIGNI_PASSWORD', '')
CAPTCHA_API_KEY = os.getenv('CAPTCHA_API_KEY', '')

# Arquivo para salvar o estado da sessão
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'designi_session_state.json')

# Função para resolver CAPTCHA
def resolver_captcha(api_key, site_key, url):
    print("[LOG] Enviando CAPTCHA para o 2CAPTCHA...")
    response = requests.post("http://2captcha.com/in.php", data={
        "key": api_key,
        "method": "userrecaptcha",
        "googlekey": site_key,
        "pageurl": url,
        "json": 1
    })
    
    request_result = response.json()
    if request_result["status"] != 1:
        print("[ERRO] Falha ao enviar CAPTCHA.")
        return None
    
    captcha_id = request_result["request"]
    print(f"[LOG] CAPTCHA enviado, ID: {captcha_id}. Aguardando solução...")
    
    for _ in range(30):  # Espera até 150 segundos (30 * 5)
        time.sleep(3)
        result = requests.get(f"http://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}&json=1").json()
        if result["status"] == 1:
            print("[LOG] CAPTCHA resolvido!")
            return result["request"]
    
    print("[ERRO] Tempo limite para resolver CAPTCHA excedido.")
    return None

# Função para realizar login usando sessão salva ou criando uma nova
def login_with_session(p):
    print("[LOG] Iniciando Playwright...")
    browser = p.chromium.launch(headless=True)
    
    # Verifica se existe um estado de sessão salvo
    if os.path.exists(STATE_FILE):
        print("[LOG] Encontrada sessão salva. Tentando restaurar...")
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()
        
        # Testa se a sessão ainda é válida
        page.goto("https://www.designi.com.br")
        time.sleep(1)
        
        if "/login" not in page.url:
            print("[SUCESSO] Sessão restaurada com sucesso!")
            return browser, context, page
        else:
            print("[LOG] Sessão expirada. Realizando novo login...")
            context.close()
    
    # Se não há sessão salva ou ela expirou, faz login normal
    context = browser.new_context()
    page = context.new_page()
    
    print(f"[LOG] Acessando página de login: {URL_LOGIN}")
    page.goto(URL_LOGIN)
    
    if not EMAIL or not SENHA:
        raise ValueError('Credenciais do Designi não configuradas')
    
    print("[LOG] Preenchendo credenciais...")
    page.fill("input[name=email]", EMAIL)
    page.fill("input[name=password]", SENHA)
    
    # Verificar se há CAPTCHA
    captcha_element = page.locator("iframe[src*='recaptcha']")
    if captcha_element.count() > 0:
        print("[LOG] CAPTCHA detectado! Tentando resolver...")
        site_key = page.evaluate('''() => {
            const recaptchaDiv = document.querySelector('.g-recaptcha');
            return recaptchaDiv ? recaptchaDiv.getAttribute('data-sitekey') : null;
        }''')
        if not site_key:
            raise Exception('Não foi possível encontrar a site key do CAPTCHA.')
        token = resolver_captcha(CAPTCHA_API_KEY, site_key, URL_LOGIN)
        if token:
            page.evaluate(f"document.getElementById('g-recaptcha-response').value = '{token}';")
            print("[LOG] CAPTCHA resolvido e inserido!")
            time.sleep(1)
        else:
            raise Exception('Falha ao resolver CAPTCHA.')
    
    # Clicar no botão de login
    print("[LOG] Aguardando botão de login ficar visível...")
    login_button = page.get_by_role("button", name="Fazer login")
    login_button.wait_for(state="visible")
    print("[LOG] Clicando no botão de login...")
    login_button.click()
    
    # Verificar se o login foi bem-sucedido
    print("[LOG] Aguardando redirecionamento após login...")
    time.sleep(2)
    if "/login" in page.url:
        raise Exception("Falha no login. Verifique as credenciais ou se há CAPTCHA.")
    
    # Salvar estado da sessão após login bem-sucedido
    print("[LOG] Salvando estado da sessão...")
    context.storage_state(path=STATE_FILE)
    print("[SUCESSO] Estado da sessão salvo!")
    
    return browser, context, page

# Sistema de armazenamento em memória para ambiente local
class LocalStorage:
    def __init__(self):
        self.data = defaultdict(int)
        self.expiry = {}
    
    def get(self, key):
        if key in self.expiry and time.time() > self.expiry[key]:
            del self.data[key]
            del self.expiry[key]
            return None
        return str(self.data[key]).encode() if key in self.data else None
    
    def set(self, key, value, ex=None):
        self.data[key] = int(value)
        if ex:
            self.expiry[key] = time.time() + ex
    
    def incr(self, key):
        self.data[key] += 1
        return self.data[key]

# Usar Redis em produção e armazenamento local em desenvolvimento
if os.environ.get('REDIS_URL'):
    import redis
    REDIS_URL = os.environ.get('REDIS_URL')
    if 'upstash.io' in REDIS_URL:
        from urllib.parse import urlparse
        parsed_url = urlparse(REDIS_URL)
        redis_client = redis.Redis(
            host=parsed_url.hostname,
            port=parsed_url.port or 6379,
            password=parsed_url.password,
            ssl=True,
            ssl_cert_reqs=None
        )
    else:
        redis_ssl = REDIS_URL.startswith('rediss://') or 'redis.com' in REDIS_URL
        redis_client = redis.from_url(
            REDIS_URL.replace('redis://', 'rediss://') if redis_ssl else REDIS_URL,
            ssl_cert_reqs=None if redis_ssl else None
        )
else:
    redis_client = LocalStorage()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret')

# Configurações
FREEPIK_API_KEY = os.getenv("FREEPIK_API_KEY", "FPSX98a4f1a67e3e4ead80dfc23df6ab8b33")
SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", '18JkCOexQ7NdzVgmK0WvKyf53AHWKQyyV')

# Função para obter o IP real do cliente
def get_client_ip():
    if request.headers.getlist("X-Forwarded-For"):
        client_ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    else:
        client_ip = request.remote_addr or '127.0.0.1'
    return client_ip

def get_drive_service():
    try:
        # Primeiro tenta usar variáveis de ambiente para as credenciais
        service_account_info = None
        
        # Verifica se existe a variável de ambiente com as credenciais codificadas em base64
        encoded_creds = os.environ.get('GOOGLE_CREDENTIALS_BASE64')
        if encoded_creds:
            try:
                json_str = base64.b64decode(encoded_creds).decode('utf-8')
                service_account_info = json.loads(json_str)
                print("Usando credenciais do Google Drive a partir da variável de ambiente GOOGLE_CREDENTIALS_BASE64")
            except Exception as e:
                print(f"Erro ao decodificar credenciais da variável de ambiente: {str(e)}")
        
        # Se não encontrou nas variáveis de ambiente, tenta o arquivo local
        if not service_account_info:
            credentials_path = os.path.join(os.path.dirname(__file__), 'encoded-correct.txt')
            if not os.path.exists(credentials_path):
                print("Erro: Arquivo de credenciais não encontrado e variável de ambiente não configurada")
                return None
                
            with open(credentials_path, 'r') as f:
                encoded_json = f.read().strip()
            
            json_str = base64.b64decode(encoded_json).decode('utf-8')
            service_account_info = json.loads(json_str)
            print("Usando credenciais do Google Drive a partir do arquivo local")
        
        required_fields = ['client_email', 'private_key', 'project_id']
        for field in required_fields:
            if field not in service_account_info:
                print(f"Erro: Campo {field} não encontrado nas credenciais")
                return None
        
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        print(f"Erro de autenticação Google Drive: {str(e)}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/status')
def user_status():
    try:
        client_ip = get_client_ip()
        downloads_key = f"downloads:{client_ip}"
        downloads_hoje = redis_client.get(downloads_key)
        
        if downloads_hoje:
            downloads = int(downloads_hoje)
            downloads_restantes = max(0, 2 - downloads)
            if downloads_restantes > 0:
                return f'<div class="alert alert-info">Você tem {downloads_restantes} downloads restantes hoje.</div>'
            else:
                return '<div class="alert alert-warning">Você atingiu o limite de downloads hoje. Tente novamente amanhã!</div>'
        else:
            return '<div class="alert alert-info">Você tem 2 downloads disponíveis hoje.</div>'
    except Exception as e:
        return f'<div class="alert alert-danger">Erro ao verificar status: {str(e)}</div>'

@app.route('/upload', methods=['POST'])
def upload():
    filename = None
    try:
        client_ip = get_client_ip()
        downloads_key = f"downloads:{client_ip}"
        downloads_hoje = redis_client.get(downloads_key)
        
        if downloads_hoje and int(downloads_hoje) >= 2:
            return "<div class='alert alert-danger'>❌ Você atingiu o limite de downloads hoje. Tente novamente amanhã!</div>"
        
        service = get_drive_service()
        if not service:
            return "<div class='alert alert-danger'>❌ Erro ao conectar com o Google Drive.</div>"

        freepik_link = request.form['freepik_link']
        match = re.search(r'_(\d+)\.htm', freepik_link)
        if not match:
            return "❌ Formato inválido! Exemplo: https://www.freepik.com/photo/12345678.htm"
        
        image_id = match.group(1)
        
        headers = {"x-freepik-api-key": FREEPIK_API_KEY}
        response = requests.get(f"https://api.freepik.com/v1/resources/{image_id}/download", headers=headers)
        response_data = response.json()
        
        if 'data' not in response_data or 'url' not in response_data['data']:
            return "❌ Erro ao obter URL de download do Freepik. Verifique a API."
        
        download_url = response_data['data']['url']
        image_response = requests.get(download_url)
        
        file_extension = 'jpg'
        content_type = image_response.headers.get('Content-Type', '').lower()
        if 'png' in content_type:
            file_extension = 'png'
        elif 'svg' in content_type:
            file_extension = 'svg'
        
        filename = f"freepik_{image_id}.{file_extension}"
        
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arquivos_temporarios')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        temp_file_path = os.path.join(temp_dir, filename)
        with open(temp_file_path, "wb") as f:
            f.write(image_response.content)
            
        # Adiciona um atraso de 3 segundos para liberar o arquivo
        print(f"[LOG] Aguardando 3 segundos para liberar o arquivo: {filename}")
        time.sleep(1)

        file_metadata = {'name': filename}
        if FOLDER_ID:
            file_metadata['parents'] = [FOLDER_ID]
        
        print(f"[LOG] Iniciando upload para o Google Drive: {filename}")
        media = MediaFileUpload(temp_file_path, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,webViewLink'
        ).execute()
        
        # Fechar explicitamente o descritor de arquivo, se existir
        if hasattr(media, '_fd') and media._fd is not None:
            media._fd.close()
            print(f"[LOG] Descritor de arquivo fechado para {filename}")
        
        print(f"[LOG] Upload para o Google Drive concluído com sucesso: {filename} (ID: {file.get('id')})")
        
        print(f"[LOG] Configurando permissões do arquivo no Google Drive...")
        service.permissions().create(
            fileId=file.get('id'),
            body={
                'role': 'reader',
                'type': 'anyone'
            }
        ).execute()
        print(f"[LOG] Permissões configuradas com sucesso para o arquivo: {filename}")
        
        if not downloads_hoje:
            redis_client.set(downloads_key, 1, ex=86400)
        else:
            redis_client.incr(downloads_key)

        success_html = f"""
        <div class="card-body">
            <div class="alert alert-success mb-3">
                ✅ Upload concluído com sucesso!
            </div>
            <div class="mb-2">
                <strong>ID do arquivo:</strong> {file.get('id')}
            </div>
            <div class="mb-3">
                <strong>Link para download:</strong><br>
                <a href="{file.get('webViewLink')}" target="_blank" class="btn btn-sm btn-outline-primary mt-2">
                    <i class="bi bi-download"></i> Baixar do Google Drive
                </a>
            </div>
            <div class="text-muted small">
                {filename} • {datetime.now().strftime('%d/%m/%Y %H:%M')}
            </div>
        </div>
        """
        return success_html

    except Exception as e:
        print(f"DEBUG - Erro no upload: {str(e)}")
        return f'<div class="alert alert-danger">⚠️ Erro: {str(e)}</div>'

    finally:
        # Mecanismo de retry simples para exclusão
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arquivos_temporarios')
        temp_file_path = os.path.join(temp_dir, filename) if filename else None
        
        if temp_file_path and os.path.exists(temp_file_path):
            for tentativa in range(3):
                try:
                    time.sleep(0.5)
                    os.remove(temp_file_path)
                    print(f"[LOG] Arquivo temporário removido: {temp_file_path}")
                    break
                except PermissionError:
                    if tentativa == 2:
                        print(f"[LOG] Não foi possível deletar o arquivo {temp_file_path} após 3 tentativas")
        
        limpar_arquivos_temporarios()

@app.route('/download-designi', methods=['POST'])
def download_designi():
    temp_file_path = None
    try:
        client_ip = get_client_ip()
        downloads_key = f"downloads:{client_ip}"
        downloads_hoje = redis_client.get(downloads_key)
        
        if downloads_hoje and int(downloads_hoje) >= 2:
            return jsonify({
                'success': False,
                'error': 'Você atingiu o limite de downloads hoje. Tente novamente amanhã!'
            })
        
        data = request.json
        url = data.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL não fornecida'})
        
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arquivos_temporarios')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        with sync_playwright() as p:
            browser, context, page = login_with_session(p)
            
            print(f"[LOG] Navegando para a URL do arquivo: {url}")
            page.goto(url)
            page.wait_for_load_state("networkidle")
            
            try:
                download_path = os.path.join(temp_dir, "designi_download")
                context.set_default_timeout(90000)
                
                with page.expect_download() as download_info:
                    print("[LOG] Clicando no botão de download...")
                    page.click("#downButton")
                    print("[LOG] Clique no botão realizado, aguardando popup...")
                    time.sleep(1)
                    
                    thank_you_popup = page.locator("div.modal-content:has-text('Obrigado por baixar meu arquivo!')")
                    if thank_you_popup.count() > 0:
                        print("[LOG] Popup de agradecimento detectado")
                        close_button = page.locator("button[aria-label='Close']")
                        if close_button.count() > 0:
                            print("[LOG] Fechando popup de agradecimento")
                            close_button.click()
                            print("[LOG] Popup fechado")
                        else:
                            print("[LOG] Botão de fechar não encontrado, continuando...")
                    else:
                        print("[LOG] Nenhum popup de agradecimento detectado")
                    
                    print("[LOG] Aguardando download começar...")
                
                download = download_info.value
                temp_file_path = os.path.join(download_path, download.suggested_filename)
                download.save_as(temp_file_path)
                
                print(f"[LOG] Download concluído: {temp_file_path}")
                
                service = get_drive_service()
                if not service:
                    return jsonify({'success': False, 'error': 'Erro ao conectar com o Google Drive'})
                
                filename = os.path.basename(temp_file_path)
                
                file_metadata = {'name': filename}
                if FOLDER_ID:
                    file_metadata['parents'] = [FOLDER_ID]
                
                print(f"[LOG] Iniciando upload para o Google Drive: {filename}")
                media = MediaFileUpload(temp_file_path, resumable=True)
                file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,webViewLink'
                ).execute()
                
                # Fechar explicitamente o descritor de arquivo, se existir
                if hasattr(media, '_fd') and media._fd is not None:
                    media._fd.close()
                    print(f"[LOG] Descritor de arquivo fechado para {filename}")
                
                print(f"[LOG] Upload para o Google Drive concluído com sucesso: {filename} (ID: {file.get('id')})")
                
                print(f"[LOG] Configurando permissões do arquivo no Google Drive...")
                service.permissions().create(
                    fileId=file.get('id'),
                    body={'role': 'reader', 'type': 'anyone'}
                ).execute()
                print(f"[LOG] Permissões configuradas com sucesso para o arquivo: {filename}")
                
                if not downloads_hoje:
                    redis_client.set(downloads_key, 1, ex=86400)
                else:
                    redis_client.incr(downloads_key)
                
                return jsonify({
                    'success': True,
                    'file_id': file.get('id'),
                    'download_link': file.get('webViewLink'),
                    'filename': filename
                })
                
            except Exception as e:
                print(f"[ERRO] Falha no fluxo de download: {str(e)}")
                return jsonify({'success': False, 'error': f"Erro durante o download: {str(e)}"})
                
            finally:
                browser.close()
                print(f"[LOG] Navegador fechado, aguardando 2 segundos para liberar recursos...")
                time.sleep(1)
                
    except Exception as e:
        print(f"[ERRO] Exceção geral: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
        
    finally:
        # Mecanismo de retry simples para exclusão
        if temp_file_path and os.path.exists(temp_file_path) and 'file' in locals() and file.get('id'):
            for tentativa in range(3):
                try:
                    time.sleep(0.5)
                    os.remove(temp_file_path)
                    print(f"[LOG] Arquivo temporário removido: {temp_file_path}")
                    break
                except PermissionError:
                    if tentativa == 2:
                        print(f"[LOG] Não foi possível deletar o arquivo {temp_file_path} após 3 tentativas")
        
        limpar_arquivos_temporarios()

def limpar_arquivos_temporarios(max_idade_horas=24):
    try:
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arquivos_temporarios')
        if not os.path.exists(temp_dir):
            return
            
        tempo_atual = time.time()
        for arquivo in os.listdir(temp_dir):
            caminho_arquivo = os.path.join(temp_dir, arquivo)
            if os.path.isfile(caminho_arquivo):
                idade_arquivo = tempo_atual - os.path.getmtime(caminho_arquivo)
                idade_horas = idade_arquivo / 3600
                
                if idade_horas >= max_idade_horas:
                    for tentativa in range(3):
                        try:
                            time.sleep(0.5)
                            os.remove(caminho_arquivo)
                            print(f"[LOG] Arquivo temporário antigo removido: {arquivo}")
                            break
                        except PermissionError:
                            if tentativa == 2:
                                print(f"[LOG] Não foi possível deletar o arquivo {caminho_arquivo} após 3 tentativas")
    
    except Exception as e:
        print(f"[LOG] Erro ao limpar diretório de arquivos temporários: {str(e)}")

if __name__ == '__main__':
    print("[LOG] Limpando arquivos temporários na inicialização...")
    limpar_arquivos_temporarios()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))