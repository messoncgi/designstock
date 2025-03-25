# DesignStock

Aplicativo para baixar e gerenciar imagens do Designi e armazená-las no Google Drive.

## Configuração

### Variáveis de Ambiente

Para executar este aplicativo, você precisa configurar as seguintes variáveis de ambiente:

#### Credenciais do Designi
- `DESIGNI_EMAIL`: Email de login do Designi
- `DESIGNI_PASSWORD`: Senha do Designi
- `DESIGNI_LOGIN_URL`: URL de login do Designi (padrão: https://designi.com.br/login)
- `CAPTCHA_API_KEY`: Chave API do 2Captcha para resolver captchas

#### Configurações do Google Drive
- `GOOGLE_CREDENTIALS_BASE64`: Credenciais de conta de serviço do Google Drive codificadas em base64
- `GOOGLE_DRIVE_FOLDER_ID`: ID da pasta do Google Drive onde as imagens serão armazenadas

#### Configurações do Redis (para produção)
- `REDIS_URL`: URL de conexão do Redis

#### Outras configurações
- `SECRET_KEY`: Chave secreta para a aplicação Flask
- `FREEPIK_API_KEY`: Chave API do Freepik (opcional)

### Configuração no Render

1. Crie um novo Web Service no Render
2. Conecte ao seu repositório GitHub
3. Configure as variáveis de ambiente mencionadas acima
4. Para a variável `GOOGLE_CREDENTIALS_BASE64`, você precisa codificar o arquivo JSON de credenciais do Google em base64:
   ```
   cat service-account.json | base64
   ```
   Ou no Windows:
   ```
   certutil -encode service-account.json temp.b64 && findstr /v /c:- temp.b64 > encoded.b64 && type encoded.b64
   ```
5. Defina o comando de build como `pip install -r requirements.txt`
6. Defina o comando de start como `gunicorn app:app`

## Desenvolvimento Local

1. Clone o repositório
2. Crie um arquivo `.env` na raiz do projeto com as variáveis de ambiente necessárias
3. Instale as dependências: `pip install -r requirements.txt`
4. Execute o aplicativo: `flask run`

## Estrutura do Projeto

- `app.py`: Arquivo principal da aplicação
- `templates/`: Diretório contendo os templates HTML
- `requirements.txt`: Dependências do projeto
- `Procfile`: Configuração para o Render