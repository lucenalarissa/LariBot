import streamlit as st
from openai import OpenAI
import logging
from typing import Dict, Any, List
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class ChatInterface:
    def __init__(self):
        # Configuração inicial do Streamlit
        st.set_page_config(page_title="Lari Bot", page_icon="🤖", layout="wide")
        
        # Inicialização do histórico de chat
        if 'messages' not in st.session_state:
            st.session_state.messages = []

    def setup_sidebar(self):
        """Configura a barra lateral com as opções"""
        with st.sidebar:
            # Botão para limpar conversa
            if st.button("Limpar Conversa"):
                self.clear_conversation()
            
            # Verifica se existe API key no ambiente
            if not os.getenv('OPENAI_API_KEY'):
                st.error("Por favor, configure a API key no arquivo .env")
                return False
            return "gpt-4"

    def clear_conversation(self):
        """Limpa a conversa"""
        st.session_state.messages = []

    def get_messages(self) -> List[Dict]:
        """Retorna as mensagens da conversa"""
        return st.session_state.messages

    def display_chat_history(self):
        """Mostra o histórico do chat"""
        for message in self.get_messages():
            with st.chat_message(message["role"]):
                if message.get("type") == "image":
                    st.image(message["content"])
                elif message.get("type") == "code":
                    st.code(message["content"], language=message.get("language", ""))
                else:
                    st.markdown(message["content"])

    def append_chat_message(self, role: str, content: str, msg_type: str = "text", language: str = None):
        """Adiciona uma mensagem ao histórico da conversa"""
        message = {
            "role": role,
            "content": content,
            "type": msg_type
        }
        if language:
            message["language"] = language
        st.session_state.messages.append(message)

class Chatbot:
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.logger = logging.getLogger(__name__)

    def detect_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """Detecta blocos de código no texto"""
        blocks = []
        lines = text.split('\n')
        in_code_block = False
        current_block = []
        current_language = ""
        
        for line in lines:
            if line.startswith('```'):
                if in_code_block:
                    blocks.append({
                        "type": "code",
                        "content": '\n'.join(current_block),
                        "language": current_language
                    })
                    current_block = []
                    in_code_block = False
                else:
                    language = line[3:].strip()
                    current_language = language if language else ""
                    in_code_block = True
            elif in_code_block:
                current_block.append(line)
            else:
                if line.strip():
                    blocks.append({
                        "type": "text",
                        "content": line
                    })
        
        return blocks

    def generate_image(self, prompt: str) -> str:
        """Gera uma imagem usando DALL-E 3"""
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            return response.data[0].url
            
        except Exception as e:
            self.logger.error(f"Erro na geração de imagem: {str(e)}")
            return None

    def process_message(self, message: str, history: List[Dict], model: str = "gpt-4") -> List[Dict[str, Any]]:
        """
        Processa a mensagem do usuário e retorna uma resposta
        """
        try:
            responses = []
            
            # Verifica se é um pedido de geração de imagem
            if message.lower().startswith(('/imagem', '/img', '/gerar imagem', '/criar imagem')):
                image_prompt = message.split(' ', 1)[1]
                image_url = self.generate_image(image_prompt)
                if image_url:
                    responses.append({
                        "tipo": "imagem",
                        "conteudo": image_url
                    })
                    return responses
            
            # Prepara o histórico para o GPT
            messages = [
                {"role": "system", "content": """Você é um assistente prestativo e amigável.
                 Você fornece respostas claras e úteis, mantendo um tom profissional e amigável.
                 Quando fornecendo exemplos de código, use blocos de código markdown com a linguagem especificada."""}
            ]
            
            # Adiciona histórico recente
            for msg in history[-5:]:  # Últimas 5 mensagens
                if msg['type'] in ['text', 'code']:
                    messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })
            
            # Adiciona mensagem atual
            messages.append({"role": "user", "content": message})
            
            # Gera resposta
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7
            )
            
            # Processa a resposta para identificar blocos de código
            blocks = self.detect_code_blocks(response.choices[0].message.content)
            
            # Retorna os blocos processados
            return [{
                "tipo": block["type"],
                "conteudo": block["content"],
                "linguagem": block.get("language", "") if block["type"] == "code" else None
            } for block in blocks]
                
        except Exception as e:
            self.logger.error(f"Erro no processamento: {str(e)}")
            return [{
                "tipo": "texto",
                "conteudo": f"Desculpe, ocorreu um erro: {str(e)}"
            }]

def main():
    """Função principal da interface"""
    # Inicializa a interface
    interface = ChatInterface()
    
    # Configura a sidebar e verifica API key
    model = interface.setup_sidebar()
    if not model:
        return
    
    # Título da aplicação
    st.title("🤖 Lari Bot")
    
    # Inicializa o bot se ainda não foi inicializado
    if 'bot' not in st.session_state:
        st.session_state.bot = Chatbot(os.getenv('OPENAI_API_KEY'))
    
    # Mostra o histórico do chat
    interface.display_chat_history()
    
    # Campo de input do usuário
    if prompt := st.chat_input("Digite sua mensagem... (Use /imagem para gerar imagens)"):
        # Adiciona a mensagem do usuário ao histórico
        interface.append_chat_message("user", prompt)
        
        # Mostra a mensagem do usuário
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Processa a mensagem com contexto
        historico = interface.get_messages()
        
        # Gera e mostra a resposta
        with st.chat_message("assistant"):
            responses = st.session_state.bot.process_message(prompt, historico, model)
            
            for response in responses:
                if response["tipo"] == "imagem":
                    st.image(response["conteudo"])
                    interface.append_chat_message("assistant", response["conteudo"], "image")
                elif response["tipo"] == "code":
                    st.code(response["conteudo"], language=response.get("linguagem", ""))
                    interface.append_chat_message("assistant", response["conteudo"], "code", response.get("linguagem"))
                else:
                    st.markdown(response["conteudo"])
                    interface.append_chat_message("assistant", response["conteudo"])

if __name__ == "__main__":
    main()