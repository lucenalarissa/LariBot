# Lari Bot

## Configuração

Acesse o diretório do projeto e configure o ambiente virtual:
```
cd /LariBot
python3 -m venv venv
source venv/bin/activate
```

Instale as dependências:
```
pip install --upgrade pip
pip install -r requirements.txt
```

Configure as variáveis de ambiente:
```
echo 'OPENAI_API_KEY="sua_api_key_aqui"' > .env
```

## Execução

Execute a aplicação:
```
streamlit run app.py
```
