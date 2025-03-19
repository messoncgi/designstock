import os
import json  # Adicione esta linha
from flask import Flask, render_template, request
import requests
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime

# Configuração para desenvolvimento (REMOVER EM PRODUÇÃO)
# Remove lines 7-8 (dev settings)
# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Modify secret key configuration (line 10)
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret')  # Production-ready

# Configurações
FREEPIK_API_KEY = os.getenv("FREEPIK_API_KEY", "FPSX98a4f1a67e3e4ead80dfc23df6ab8b33")
SCOPES = ['https://www.googleapis.com/auth/drive']  # Escopo completo para acesso ao Drive
SERVICE_ACCOUNT_FILE = 'service-account.json'
# Na linha 19 verifique o FOLDER_ID
FOLDER_ID = '18JkCOexQ7NdzVgmK0WvKyf53AHWKQyyV'  # Confirme se este ID está correto

@app.route('/')
def home():
    return render_template('index.html')



def get_drive_service():
    # Usa a conta de serviço para autenticação
    try:
        # Modificação necessária para produção
        import json
        service_account_info = json.loads(os.environ['SERVICE_ACCOUNT_JSON'])
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        print(f"Erro de autenticação Google Drive: {str(e)}")
        return None

@app.route('/upload', methods=['POST'])
def upload():
    filename = None
    try:
        service = get_drive_service()
        if not service:
            return "<div class='alert alert-danger'>❌ Erro ao conectar com o Google Drive.</div>"

        freepik_link = request.form['freepik_link']
        match = re.search(r'_(\d+)\.htm', freepik_link)
        if not match:
            return "❌ Formato inválido! Exemplo: https://www.freepik.com/photo/12345678.htm"
        
        image_id = match.group(1)
        
        # Fazer requisição à API do Freepik primeiro
        headers = {"x-freepik-api-key": FREEPIK_API_KEY}
        response = requests.get(f"https://api.freepik.com/v1/resources/{image_id}/download", headers=headers)
        response_data = response.json()
        
        if 'data' not in response_data or 'url' not in response_data['data']:
            return "❌ Erro ao obter URL de download do Freepik. Verifique a API."
        
        # Extrair tipo de arquivo da resposta da API
        file_type = response_data['data'].get('type', 'photo')
        file_format = response_data['data'].get('format', '').lower()
        print(f'DEBUG - Tipo de arquivo recebido da API: {file_type}, Formato: {file_format}')

        # Fazer o download primeiro para verificar o tipo real do arquivo
        download_url = response_data['data']['url']
        image_response = requests.get(download_url, stream=True)
        
        # Verificar o Content-Type do header da resposta
        content_type = image_response.headers.get('Content-Type', '').lower()
        print(f'DEBUG - Content-Type do arquivo: {content_type}')
        print(f'DEBUG - Headers completos: {dict(image_response.headers)}')

        # Ler os primeiros bytes do arquivo para verificar a assinatura
        first_bytes = next(image_response.iter_content(8))
        print(f'DEBUG - Primeiros bytes do arquivo: {first_bytes.hex()}')

        # Assinaturas de arquivo conhecidas
        PSD_SIGNATURE = b'8BPS'
        ZIP_SIGNATURES = [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08']
        RAR_SIGNATURE = b'Rar!\x1a\x07\x00'
        
        # Verificar assinatura do arquivo primeiro
        is_archive = False
        for zip_sig in ZIP_SIGNATURES:
            if first_bytes.startswith(zip_sig):
                print('DEBUG - Assinatura ZIP detectada nos primeiros bytes')
                file_extension = 'zip'
                mimetype = 'application/zip'
                is_archive = True
                break
        
        if not is_archive and first_bytes.startswith(RAR_SIGNATURE):
            print('DEBUG - Assinatura RAR detectada nos primeiros bytes')
            file_extension = 'rar'
            mimetype = 'application/x-rar-compressed'
            is_archive = True
        
        if not is_archive:
            if first_bytes.startswith(PSD_SIGNATURE):
                print('DEBUG - Assinatura PSD detectada nos primeiros bytes')
                file_extension = 'psd'
                mimetype = 'image/vnd.adobe.photoshop'
            # Se não for PSD, verificar outras informações
            elif 'photoshop' in content_type or file_format == 'psd' or 'photoshop' in file_type.lower():
                print('DEBUG - Arquivo identificado como PSD através de metadados')
                file_extension = 'psd'
                mimetype = 'image/vnd.adobe.photoshop'
            elif 'svg' in content_type or file_format == 'svg' or 'vector' in file_type.lower():
                file_extension = 'svg'
                mimetype = 'image/svg+xml'
            elif 'png' in content_type or file_format == 'png':
                file_extension = 'png'
                mimetype = 'image/png'
            elif 'jpeg' in content_type or file_format in ['jpg', 'jpeg']:
                file_extension = 'jpg'
                mimetype = 'image/jpeg'
            elif 'application/zip' in content_type or 'application/x-zip-compressed' in content_type:
                print('DEBUG - Arquivo ZIP identificado através do Content-Type')
                file_extension = 'zip'
                mimetype = 'application/zip'
                is_archive = True
            elif 'application/x-rar-compressed' in content_type:
                print('DEBUG - Arquivo RAR identificado através do Content-Type')
                file_extension = 'rar'
                mimetype = 'application/x-rar-compressed'
                is_archive = True
            else:
                # Se não conseguir determinar, usar as informações da API como fallback
                if 'psd' in file_type.lower():
                    file_extension = 'psd'
                    mimetype = 'image/vnd.adobe.photoshop'
                else:
                    file_extension = file_format if file_format else 'jpg'
                    mimetype = content_type if content_type else 'image/jpeg'
        
        print(f'DEBUG - Tipo final determinado: extensão={file_extension}, mimetype={mimetype}')
            
        filename = f"freepik_{image_id}.{file_extension}"
        
        download_url = response_data['data']['url']
        
        # Download e salvamento do arquivo na pasta de arquivos temporários
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arquivos_temporarios')
        # Garantir que a pasta existe
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        temp_file_path = os.path.join(temp_dir, filename)
        image_response = requests.get(download_url)
        with open(temp_file_path, "wb") as f:
            f.write(image_response.content)

        # Preparar metadados do arquivo (incluindo pasta se especificada)
        file_metadata = {'name': filename}
        if FOLDER_ID:
            file_metadata['parents'] = [FOLDER_ID]
        
        # Upload para o Google Drive com gerenciamento adequado do arquivo
        with open(temp_file_path, 'rb'):
            media = MediaFileUpload(temp_file_path, mimetype=mimetype, resumable=True)
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            
            # Adiciona permissão pública para o arquivo
            service.permissions().create(
                fileId=file.get('id'),
                body={
                    'role': 'reader',
                    'type': 'anyone'
                }
            ).execute()
            
            # Fecha explicitamente o descritor de arquivo
            if hasattr(media, '_fd'):
                media._fd.close()

        # Modifica o retorno para incluir HTML formatado
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
        return f'<div class="alert alert-danger">⚠️ Erro: {str(e)}</div>'

    finally:
        # Mecanismo de tentativas para deletar o arquivo temporário
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arquivos_temporarios')
        temp_file_path = os.path.join(temp_dir, filename) if filename else None
        
        if temp_file_path and os.path.exists(temp_file_path):
            import time
            for tentativa in range(3):
                try:
                    time.sleep(0.5)  # Pequeno delay antes de tentar deletar
                    os.remove(temp_file_path)
                    break
                except PermissionError:
                    if tentativa == 2:
                        print(f"Não foi possível deletar o arquivo {temp_file_path} após 3 tentativas")

# Modify the last lines for production
if __name__ == '__main__':
    app.run()