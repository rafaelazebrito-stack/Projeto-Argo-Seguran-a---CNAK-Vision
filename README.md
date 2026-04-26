# Projeto Argo Segurança - CNAK-Vision
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import time
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import base64
from datetime import datetime, timedelta
import random
import json

# ==============================================================================
# 0. CONFIGURAÇÃO DE AMBIENTE E VARIÁVEIS GLOBAIS
# ==============================================================================

# Definição de diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RELATORIOS_DIR = os.path.join(BASE_DIR, 'relatorios')
CADASTROS_DIR = os.path.join(BASE_DIR, 'cadastros_usuarios')
FOTO_DIR = os.path.join(BASE_DIR, 'photos')
DB_FILE = os.path.join(CADASTROS_DIR, 'db_vision_final.csv')
COLUNAS = ['Nome', 'Documento', 'Email', 'Telefone', 'Tipo', 'Sexo', 'Endereco', 'Origem', 'Data_Cad', 'Foto']

# NOVO: Arquivo para persistência dos IDs de login
LOGIN_DB_FILE = os.path.join(CADASTROS_DIR, 'login_users.json')

# Criar diretórios se não existirem
for dir_path in [RELATORIOS_DIR, CADASTROS_DIR, FOTO_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Configuração da Páginast.set_page_config(page_title="CNAK Vision - Smart Hub", page_icon="💠", layout="wide")

# ==============================================================================
# 1. CLASSE DE UTILIDADES E MANIPULAÇÃO DE DADOS (DatabaseHandler & Utils)
# ==============================================================================

class Utils:
    """Funções de utilidade geral e formatação."""
    
    @staticmethod
    def formatar_cpf(numero):
        """Formata string de CPF para o padrão 000.000.000-00."""
        texto = str(numero).zfill(11)
        return f"{texto[:3]}.{texto[3:6]}.{texto[6:9]}-{texto[9:]}"
    
    @staticmethod
    def gerar_foto_ficticia(seed):
        """Gera URL de foto fictícia para seeds."""
        return f"https://picsum.photos/seed/{seed}/320/320"
    
    @staticmethod
    def gerar_usuario_ficticio(seed):
        """Gera um dicionário de usuário fictício."""
        nomes = ["Mariana Silva", "Tiago Almeida", "Beatriz Costa", "Lucas Pereira", "Fernanda Rocha", "Gabriel Santos", "Juliana Andrade", "Rafael Oliveira", "Paula Mendes", "Felipe Cardoso", "Ana Sousa", "Bruno Ferreira"]
        enderecos = ["Rua das Laranjeiras, 540", "Av. da Liberdade, 1200", "Rua Piratini, 75", "Alameda dos Anjos, 350", "Av. Paulista, 2001", "Rua do Comércio, 88", "Largo das Flores, 14", "Praça Central, 220"]
        origens = ["CNAK Vision", "Lojista", "Operacional", "Portal", "Auditoria"]
        tipos = ["Diretoria", "Operacional", "Lojista", "Visitante"]
        sexos = ["Masculino", "Feminino", "Não Informado"]
        
        nome = nomes[seed % len(nomes)]
        documento = Utils.formatar_cpf(seed * 3 + 17)
        email = nome.lower().replace(" ", ".") + f"{seed % 10}@cnakvision.com"
        telefone = f"(11) 9{seed % 10}{(seed * 7) % 10000:04d}-{(seed * 13) % 10000:04d}"
        tipo = tipos[seed % len(tipos)]
        sexo = sexos[seed % len(sexos)]
        endereco = f"{enderecos[seed % len(enderecos)]}, Sala {seed % 50 + 1}"
        origem = origens[seed % len(origens)]
        data_cad = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        foto = Utils.gerar_foto_ficticia(seed)
        
        return dict(zip(COLUNAS, [nome, documento, email, telefone, tipo, sexo, endereco, origem, data_cad, foto]))
    
class DatabaseHandler:
    """Gerencia a persistência de dados (atualmente via CSV)."""
    
    def __init__(self, db_file, colunas):
        self.db_file = db_file
        self.colunas = colunas
        self._load_db()
    
    def _load_db(self):
        """Carrega ou inicializa o DataFrame no session_state."""
        if 'db' not in st.session_state:
            if not os.path.exists(self.db_file):
                pd.DataFrame(columns=self.colunas).to_csv(self.db_file, index=False)
            df = pd.read_csv(self.db_file)
            for col in self.colunas:
                if col not in df.columns:
                    df[col] = 'N/A'
            st.session_state.db = df
            
            if st.session_state.db.empty and not st.session_state.get('seeded_random_users', False):
                self.seed_random_users(10)
                
    def get_all_users(self):
        """Retorna o DataFrame de usuários."""
        return st.session_state.db
    
    def save_user(self, user_data):
        """Adiciona um novo usuário ao DB e persiste."""
        novo = pd.DataFrame([user_data], columns=self.colunas)
        st.session_state.db = pd.concat([st.session_state.db, novo], ignore_index=True)
        self._persist_db()
        return True
    
    def delete_users(self, documents_list):
        """Exclui usuários com base na lista de documentos e persiste."""
        st.session_state.db = st.session_state.db[~st.session_state.db['Documento'].isin(documents_list)]
        self._persist_db()
    
    def _persist_db(self):
        """Salva o DataFrame de volta ao CSV."""
        st.session_state.db.to_csv(self.db_file, index=False)
    
    def is_duplicate(self, nome, document, email):
        """Verifica se Nome, CPF ou Email já estão cadastrados."""
        df = st.session_state.db.copy()
        
        # 1. Check Document (CPF) - removing formatting for safe comparison
        target_document = document.replace('.', '').replace('-', '')
        db_documents = df['Documento'].astype(str).str.replace('.', '', regex=False).str.replace('-', '', regex=False)
        if target_document in db_documents.values:
            return 'CPF'
        
        # 2. Check Name (Case-insensitive)
        if nome.lower() in df['Nome'].astype(str).str.lower().values:
            return 'Nome'
        
        # 3. Check Email (Case-insensitive, skip check if email is 'N/A' or empty)
        if email and email.lower() != 'n/a' and email.lower() in df['Email'].astype(str).str.lower().values:
            return 'Email'
        
        return None # No duplicate found
    
    # Mantida para compatibilidade com o seed_random_users
    def is_document_duplicate(self, document):
        """Verifica se um documento já está cadastrado."""
        db_documents = st.session_state.db['Documento'].astype(str).str.replace('.', '', regex=False).str.replace('-', '', regex=False)
        target_document = document.replace('.', '').replace('-', '')
        return target_document in db_documents.values
    
    def seed_random_users(self, count=10):
        """Adiciona usuários fictícios ao banco de dados."""
        usuarios = []
        base = int(time.time())
        for i in range(count):
            usuario = Utils.gerar_usuario_ficticio(base + i)
            if not self.is_document_duplicate(usuario['Documento']):
                usuarios.append(usuario)
        if usuarios:
            st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame(usuarios)], ignore_index=True)
            self._persist_db()
            st.session_state.seeded_random_users = True
        return len(usuarios)

# Inicializa o handler de banco de dados
db_handler = DatabaseHandler(DB_FILE, COLUNAS)

# ==============================================================================
# 1.5 FUNÇÕES DE PERSISTÊNCIA DE LOGIN
# ==============================================================================

USUARIOS_CADASTRO_DEFAULT = {
    "rafaelazebrito@gmail.com": {"id": "rafael61739386", "chave": "123456789", "nome": "Rafael Brito", "nivel": "Admin"},
    "operacional": {"id": "op1", "chave": "senha123", "nome": "Operacional", "nivel": "Operacional"},
    "lojista": {"id": "lojista", "chave": "loja123", "nome": "Lojista Hub", "nivel": "Lojista"},
}

def load_login_users():
    """Carrega as credenciais de login do JSON, ou inicializa com padrão."""
    if os.path.exists(LOGIN_DB_FILE):
        try:
            with open(LOGIN_DB_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Em caso de arquivo corrompido, retorna defaults
            print("Warning: login_users.json corrupted. Using default users.")
            return USUARIOS_CADASTRO_DEFAULT.copy()
    else:
        # Se o arquivo não existir, salva os defaults e retorna
        save_login_users(USUARIOS_CADASTRO_DEFAULT)
        return USUARIOS_CADASTRO_DEFAULT.copy()

def save_login_users(users_dict):
    """Salva as credenciais de login no arquivo JSON."""
    os.makedirs(os.path.dirname(LOGIN_DB_FILE), exist_ok=True)
    with open(LOGIN_DB_FILE, 'w') as f:
        json.dump(users_dict, f, indent=4)

# Inicializa o estado de login lendo do arquivo persistente
if 'USUARIOS_CADASTRO_STATE' not in st.session_state:
    st.session_state.USUARIOS_CADASTRO_STATE = load_login_users()

# ==============================================================================
# 2. DESIGN E ESTILIZAÇÃO
# ==============================================================================

def aplicar_design():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500&display=swap');
        .stApp { background: radial-gradient(circle at top, rgba(26, 18, 4, 0.96) 0%, #0a0803 90%); color: #fff8e7; }
        .stApp::before {
            content: '';
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: radial-gradient(circle at top left, rgba(255, 215, 0, 0.16), transparent 16%),
                        radial-gradient(circle at top right, rgba(218, 165, 32, 0.12), transparent 14%),
                        radial-gradient(circle at bottom, rgba(255, 193, 7, 0.08), transparent 20%);
            pointer-events: none; z-index: 0;
        }
        .neon-title {
            font-family: 'Orbitron', sans-serif; color: #ffd700; text-align: center;
            padding: 22px 18px; border: 1px solid rgba(255, 215, 0, 0.28);
            background: rgba(0, 0, 0, 0.38); border-radius: 16px;
            text-transform: uppercase; letter-spacing: 4px; margin-bottom: 30px;
            text-shadow: 0 0 12px rgba(255, 215, 0, 0.8), 0 0 25px rgba(255, 215, 0, 0.3);
            animation: neonPulse 1.8s ease-in-out infinite alternate;
            position: relative; z-index: 1;
        }
        .stButton button {
            background: linear-gradient(135deg, #ffd700, #b8860b) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            color: #1a1204 !important; font-family: 'Orbitron', sans-serif;
            box-shadow: 0 0 18px rgba(255, 215, 0, 0.36);
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }
        .stButton button:hover {
            transform: scale(1.02); box-shadow: 0 0 32px rgba(255, 215, 0, 0.55);
        }
        .section-card {
            background: rgba(28, 20, 7, 0.88); border: 1px solid rgba(255, 215, 0, 0.18);
            border-radius: 18px; padding: 22px; margin-bottom: 24px;
            box-shadow: 0 0 32px rgba(255, 215, 0, 0.08);
        }
        .stSidebar {
            background: rgba(14, 10, 4, 0.95) !important;
            border-right: 1px solid rgba(255, 215, 0, 0.12);
        }
        .stTextInput>div>div>input, .stSelectbox>div>div>div>div, .stFileUploader>div {
            background: rgba(255,255,255,0.05) !important; border: 1px solid rgba(255, 215, 0, 0.18) !important;
            color: #fff8e7 !important;
        }
        .neon-box {
            background: rgba(28, 20, 7, 0.92); border: 1px solid rgba(255, 215, 0, 0.26);
            border-radius: 18px; padding: 18px; margin-bottom: 20px;
            box-shadow: 0 0 30px rgba(255, 215, 0, 0.18);
            position: relative;
        }
        .dashboard-card {
            background: rgba(28, 20, 7, 0.94); border: 1px solid rgba(255, 193, 7, 0.22);
            border-radius: 20px; padding: 24px; margin-bottom: 24px;
            box-shadow: 0 0 40px rgba(255, 193, 7, 0.14);
        }
        .glow-text {
            color: #ffd700; text-shadow: 0 0 12px rgba(255, 215, 0, 0.8), 0 0 24px rgba(255, 215, 0, 0.35);
        }
        </style>
    """, unsafe_allow_html=True)

def ativar_sonorizacao():
    components.html("""
        <audio id='clickSound'><source src='https://www.soundjay.com/buttons/sounds/button-16.mp3' type='audio/mpeg'></audio>
        <script>
            const clickAudio = document.getElementById('clickSound');
            document.addEventListener('click', function(e) {
                if (e.target.closest('button')) {
                    clickAudio.currentTime = 0;
                    clickAudio.play().catch(() => {});
                }
            }, true);
        </script>
    """, height=0)

aplicar_design()
ativar_sonorizacao()

# ==============================================================================
# 3. FUNÇÕES DE ARQUIVO E CÂMERA
# ==============================================================================

def salvar_foto(foto, documento, foto_base64=None):
    """Salva a foto (upload ou base64) e retorna o caminho."""
    if foto_base64 and foto_base64.startswith('data:image'):
        # Salvar foto capturada pela câmera
        header, encoded = foto_base64.split(',', 1)
        nome_arquivo = f"{documento}_camera_{int(time.time())}.png".replace(' ', '_')
        caminho = os.path.join(FOTO_DIR, nome_arquivo)
        with open(caminho, 'wb') as f:
            f.write(base64.b64decode(encoded))
        return caminho
    elif foto is None:
        return 'N/A'
    else:
        # Salvar foto por upload
        nome_arquivo = f"{documento}_{foto.name}".replace(' ', '_')
        caminho = os.path.join(FOTO_DIR, nome_arquivo)
        with open(caminho, 'wb') as f:
            f.write(foto.getbuffer())
        return caminho

# Componente de Câmera Original (Restaurado)
def capturar_foto_camera(key_suffix):
    """Implementação ORIGINAL do componente de câmera Streamlit (HTML/JS)"""
    st.markdown(f'<h4 class="glow-text">📷 Captura de Identificação Facial (Original)</h4>', unsafe_allow_html=True)
    
    components.html(f"""
        <div class='camera-container' style='text-align: center;'>
            <video id='video_{key_suffix}' autoplay playsinline style='width: 100%; max-width: 400px; border-radius: 12px; border: 2px solid rgba(255, 215, 0, 0.4);'></video>
            <canvas id='canvas_{key_suffix}' style='display: none;'></canvas>
            <br><br>
            <button id='captureBtn_{key_suffix}' class='camera-btn' style='margin: 5px;'>📸 Capturar Foto</button>
            <button id='retakeBtn_{key_suffix}' class='camera-btn' style='margin: 5px; display: none;'>🔄 Tirar Novamente</button>
            <input type='hidden' id='photoData_{key_suffix}' name='photoData' value=''>
        </div>
        <script>
            const video = document.getElementById('video_{key_suffix}');
            const canvas = document.getElementById('canvas_{key_suffix}');
            const captureBtn = document.getElementById('captureBtn_{key_suffix}');
            const retakeBtn = document.getElementById('retakeBtn_{key_suffix}');
            const photoData = document.getElementById('photoData_{key_suffix}');

            async function startCamera() {{
                try {{
                    const stream = await navigator.mediaDevices.getUserMedia({{ 
                          video: {{ facingMode: 'user', width: 320, height: 240 }} 
                      }});
                    video.srcObject = stream;
                }} catch (err) {{
                    console.error('Erro ao acessar câmera:', err);
                }}
            }}
            
            captureBtn.addEventListener('click', function() {{
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0);
                const dataURL = canvas.toDataURL('image/png');
                
                photoData.value = dataURL;
                
                video.style.display = 'none';
                captureBtn.style.display = 'none';
                retakeBtn.style.display = 'inline-block';
                
                const img = document.createElement('img');
                img.src = dataURL;
                img.style.cssText = 'width: 100%; max-width: 400px; border-radius: 12px; border: 2px solid rgba(255, 215, 0, 0.4); margin-top: 10px;';
                img.id = 'capturedImage';
                const container = video.parentElement;
                const existingImg = document.getElementById('capturedImage');
                if (existingImg) existingImg.remove();
                container.appendChild(img);
                
                // Tenta injetar o DataURL no campo de texto de Streamlit
                const st_input = parent.document.querySelector('input[aria-label="URL Base64 da Foto Capturada"]');
                if (st_input) {{
                    st_input.value = dataURL;
                    st_input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }} else {{
                    // O usuário deve copiar manualmente o valor do console ou do elemento photoData se a injeção falhar
                }}
                            
            }});

            retakeBtn.addEventListener('click', function() {{
                video.style.display = 'block';
                captureBtn.style.display = 'inline-block';
                retakeBtn.style.display = 'none';
                const existingImg = document.getElementById('capturedImage');
                if (existingImg) existingImg.remove();
                photoData.value = '';
            }});

            startCamera();
        </script>
    """, height=400, scrolling=False)
    
    # Campo de texto que recebe o Data URL (necessário para Streamlit ler o valor)
    return st.text_input("URL Base64 da Foto Capturada", type="default", key=f"foto_base64_data_{key_suffix}", help="Aperte 'Capturar Foto' e cole o Data URL que aparece no console ou use o Data URL injetado automaticamente.")

# ==============================================================================
# 4. AUTENTICAÇÃO (Melhorada e Mantida)
# ==============================================================================

# Funções de gestão de login foram movidas para o bloco 1.5 para melhor organização

def login_form():
    """Exibe o formulário de login e gerencia o estado de sessão."""
    st.markdown('<div class="neon-title">💠 CNAK VISION - HUB DE ACESSO</div>', unsafe_allow_html=True)
    
    _, col_login, _ = st.columns([1, 0.8, 1])
    with col_login:
        u = st.text_input("ID Operador")
        p = st.text_input("Chave", type="password")

        if st.button("ACESSAR HUB"):
            auth_success = False
            user_data = None
            
            # Usa o estado da sessão (carregado do JSON) para autenticação
            for user_key, data in st.session_state.USUARIOS_CADASTRO_STATE.items():
                if data['id'] == u and data['chave'] == p:
                    auth_success = True
                    user_data = data
                    break

            if auth_success:
                st.session_state.logged_in = True
                st.session_state.user_info = user_data
                st.rerun()
            else:
                st.error("ID ou Chave inválidos.")

    if not st.session_state.get('logged_in', False):
        st.stop()

# ==============================================================================
# 5. FUNÇÕES DE RELATÓRIO E BI (Mantidas)
# ==============================================================================

def gerar_relatorio_auditoria():
    df_db = db_handler.get_all_users()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_arquivo = f"relatorio_auditoria_{timestamp}.txt"
    caminho_arquivo = os.path.join(RELATORIOS_DIR, nome_arquivo)
    
    conteudo = f"""================================================================================
                    RELATÓRIO DE AUDITORIA - CNAK VISION
================================================================================
Data de Geração: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Operador: {st.session_state.user_info.get('nome', 'Desconhecido')}
================================================================================

RESUMO DO SISTEMA:
- Total de Usuários Cadastrados: {len(df_db)}
- Diretório de Cadastros: {CADASTROS_DIR}
- Diretório de Relatórios: {RELATORIOS_DIR}
- Diretório de Fotos: {FOTO_DIR}

================================================================================
LISTA COMPLETA DE USUÁRIOS:
================================================================================\n"""
    
    for idx, row in df_db.iterrows():
        

        conteudo += f"{idx + 1}. {row['Nome']} | CPF: {row['Documento']} | Email: {row['Email']} | Tipo: {row['Tipo']} | Origem: {row['Origem']} | Data de Cadastro: {row['Data_Cad']}\n"
    
    conteudo += f"""================================================================================
ESTATÍSTICAS:
================================================================================\n"""
    
    if not df_db.empty:
        estatisticas = df_db.groupby(['Tipo', 'Origem']).size().reset_index(name='Quantidade')
        for _, row in estatisticas.iterrows():
            conteudo += f"- {row['Tipo']} / {row['Origem']}: {row['Quantidade']} registros\n"
            
    conteudo += f"""================================================================================
FIM DO RELATÓRIO
================================================================================"""

    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    return caminho_arquivo, nome_arquivo, conteudo

def gerar_relatorio_acessos():
    # Código de geração de relatório de acessos (simulado)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_arquivo = f"relatorio_acessos_{timestamp}.txt"
    caminho_arquivo = os.path.join(RELATORIOS_DIR, nome_arquivo)
    
    conteudo = f"""================================================================================
              RELATÓRIO DE ACESSOS - CNAK VISION
================================================================================
Data de Geração: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Operador: {st.session_state.user_info.get('nome', 'Desconhecido')}
================================================================================

HISTÓRICO DE ACESSOS:
"""
    
    access_logs = [
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')} - Acesso autorizado: {st.session_state.user_info.get('nome')}",
        f"{(datetime.now() - timedelta(minutes=10)).strftime('%d/%m/%Y %H:%M')} - Acesso ao BI",
        f"{(datetime.now() - timedelta(hours=1)).strftime('%d/%m/%Y %H:%M')} - Operador 1 - Tentativa falhada",
        f"{(datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y %H:%M')} - Lojista A - Cadastro realizado"
    ]
    
    for log in access_logs:
        conteudo += f"• {log}\n"
            
    conteudo += f"""\n================================================================================
FIM DO RELATÓRIO
================================================================================"""
    
    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    return caminho_arquivo, nome_arquivo, conteudo

# Funções de BI (mantidas)
def gerar_dados_simulados_bi():
    np.random.seed(42)
    datas = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30, 0, -1)]
    fluxo_diario = np.random.randint(3500, 6500, size=30).tolist()
    tipos = ['Diretoria', 'Operacional', 'Lojista', 'Visitante']
    dados_tipo = {tipo: np.random.randint(100, 800, size=30).tolist() for tipo in tipos}
    origens = ['CNAK Vision', 'Lojista', 'Operacional', 'Portal', 'Auditoria']
    dados_origem = {origem: np.random.randint(50, 500, size=30).tolist() for origem in origens}
    andares = ['Piso 1', 'Piso 2', 'Piso 3']
    dados_andar = {andar: np.random.randint(800, 2000, size=30).tolist() for andar in andares}
    periodos = ['Manhã (6h-12h)', 'Tarde (12h-18h)', 'Noite (18h-24h)']
    dados_periodo = {periodo: np.random.randint(1000, 3000, size=30).tolist() for periodo in periodos}
    return {'datas': datas, 'fluxo_diario': fluxo_diario, 'dados_tipo': dados_tipo, 'dados_origem': dados_origem, 'dados_andar': dados_andar, 'dados_periodo': dados_periodo}

# Funções de Gráfico (Apenas a chamada principal é mostrada para brevidade)
def criar_grafico_animado(dados):
    fig = go.Figure()
    cores = {'Diretoria': '#ffd700', 'Operacional': '#b8860b', 'Lojista': '#daa520', 'Visitante': '#ffa500'}
    for tipo, valores in dados['dados_tipo'].items():
        fig.add_trace(go.Scatter(x=dados['datas'], y=valores, mode='lines+markers', name=tipo, line=dict(color=cores.get(tipo, '#ffd700'), width=2), marker=dict(size=6)))
    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(28, 20, 7, 0.5)', font=dict(color='#ffd700'), height=400)
    return fig

def criar_grafico_fluxo_tempo_real(dados):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dados['datas'], y=dados['fluxo_diario'], mode='lines+markers', name='Fluxo Total', line=dict(color='#ffd700', width=3), fill='tozeroy', fillcolor='rgba(255, 215, 0, 0.2)'))
    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(28, 20, 7, 0.5)', font=dict(color='#ffd700'), title='Fluxo Diário de Visitantes', height=350)
    return fig

def criar_grafico_andares(dados):
    fig = go.Figure()
    for andar, valores in dados['dados_andar'].items():
        fig.add_trace(go.Bar(name=andar, x=dados['datas'][-7:], y=valores[-7:], marker=dict(color='#ffd700' if 'Piso 1' in andar else '#b8860b' if 'Piso 2' in andar else '#daa520')))
    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(28, 20, 7, 0.5)', font=dict(color='#ffd700'), title='Fluxo por Andar (Últimos 7 dias)', barmode='group', height=350)
    return fig

def gerar_dados_simulados_heatmap():
    np.random.seed(123)
    zonas = ['Entrada Principal', 'Praça de Alimentação', 'Lojas Premium', 'Estacionamento']
    andares = ['Piso 1', 'Piso 2', 'Piso 3']
    matriz_calor = {}
    for zona in zonas:
        matriz_calor[zona] = {}
        for andar in andares:
            matriz_calor[zona][andar] = np.random.randint(20, 100)
    horas = list(range(6, 24))
    fluxo_hora = np.random.randint(200, 800, size=len(horas)).tolist()
    fluxo_hora[11:14] = [f + 300 for f in fluxo_hora[11:14]]
    fluxo_hora[17:20] = [f + 400 for f in fluxo_hora[17:20]]
    return {'matriz_calor': matriz_calor, 'zonas': zonas, 'andares': andares, 'horas': horas, 'fluxo_hora': fluxo_hora}

def criar_mapa_calor_interativo(dados):
    matriz = dados['matriz_calor']
    zonas = dados['zonas']
    andares = dados['andares']
    z_data = [[matriz[zona][andar] for andar in andares] for zona in zonas]
    fig = go.Figure(data=go.Heatmap(z=z_data, x=andares, y=zonas, colorscale='Ylorrd', showscale=True, text=[[str(v) for v in row] for row in z_data], texttemplate='%{text}', textfont=dict(size=14, color='black')))
    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(28, 20, 7, 0.5)', font=dict(color='#ffd700'), title='Mapa de Calor - Densidade por Zona e Andar', height=400)
    return fig

def criar_grafico_horas(heatmap_dados):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=heatmap_dados['horas'], y=heatmap_dados['fluxo_hora'], mode='lines+markers', name='Fluxo por Hora', line=dict(color='#ffd700', width=3), fill='tozeroy', fillcolor='rgba(255, 215, 0, 0.3)'))
    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(28, 20, 7, 0.5)', font=dict(color='#ffd700'), title='Fluxo de Visitantes por Hora do Dia', height=350)
    return fig

# ==============================================================================
# 6. ESTRUTURA MODULAR DAS PÁGINAS
# ==============================================================================

def page_cadastro_geral():
    """Módulo: Cadastro Geral (Com validações de duplicidade aprimoradas)."""
    st.subheader("Registro Central")
    
    with st.form("form_geral", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome Completo *")
        doc = c1.text_input("CPF *", placeholder="000.000.000-00")
        email = c1.text_input("Email *", placeholder="exemplo@dominio.com")
        
        sexo = c2.selectbox("Sexo", ["Masculino", "Feminino", "Não Informado"])
        tipo = c2.selectbox("Tipo de Acesso", ["Diretoria", "Operacional", "Lojista", "Visitante"])
        endereco = c2.text_input("Endereço Completo", placeholder="Rua, Número, Bairro, Cidade")
        
        foto_base64 = capturar_foto_camera("cadastro")
        foto_upload = c2.file_uploader("Ou faça upload de foto", type=['png', 'jpg', 'jpeg'])

        if st.form_submit_button("REGISTRAR NO SISTEMA"):
            doc_formatado = Utils.formatar_cpf(doc)
            
            if nome and doc and email:
                duplicidade = db_handler.is_duplicate(nome, doc_formatado, email)
                
                if duplicidade:
                    st.error(f"ERRO: Cadastro duplicado detectado pelo campo '{duplicidade}'. Não é permitido Nome, CPF ou E-mail repetido.")
                else:
                    foto_path = 'N/A'
                    if foto_base64 and foto_base64.startswith('data:image'):
                        foto_path = salvar_foto(None, doc_formatado, foto_base64)
                        st.success("Foto capturada e salva com sucesso!")
                    elif foto_upload:
                        foto_path = salvar_foto(foto_upload, doc_formatado)
                        st.success("Foto de upload salva com sucesso!")
                        
                    novo_usuario = {
                        'Nome': nome, 'Documento': doc_formatado, 'Email': email, 'Telefone': "N/A", 
                        'Tipo': tipo, 'Sexo': sexo, 'Endereco': endereco, 'Origem': "CNAK Vision", 
                        'Data_Cad': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'Foto': foto_path
                    }
                    db_handler.save_user(novo_usuario)
                    st.success(f"Sucesso: {nome} cadastrado.")
                    st.rerun()

            else:
                st.warning("Preencha os campos obrigatórios (Nome, CPF e Email).")

    if st.button("GERAR CADASTROS FICTÍCIOS"):
        total = db_handler.seed_random_users(8)
        if total > 0:
            st.success(f"{total} usuários fictícios adicionados.")
            st.rerun()

    st.markdown("---")
    st.markdown('<h3 class="glow-text">👥 Galeria de Perfis Cadastrados</h3>', unsafe_allow_html=True)
    df_db = db_handler.get_all_users()
    
    if not df_db.empty:
        filtro_tipo = st.selectbox("Filtrar por Tipo de Acesso", ["Todos"] + list(df_db['Tipo'].unique()))
        filtro_origem = st.selectbox("Filtrar por Origem", ["Todas"] + list(df_db['Origem'].unique()))

        df_filtrado = df_db.copy()
        if filtro_tipo != "Todos": df_filtrado = df_filtrado[df_filtrado['Tipo'] == filtro_tipo]
        if filtro_origem != "Todas": df_filtrado = df_filtrado[df_filtrado['Origem'] == filtro_origem]
        
        st.markdown(f"**Total de registros: {len(df_filtrado)}**")

        cols = st.columns(4)
        for idx, (_, user) in enumerate(df_filtrado.iterrows()): 
            with cols[idx % 4]:
                st.markdown(f"""
                    <div class='neon-box' style='text-align: center; padding: 20px; min-height: 480px; display: flex; flex-direction: column; justify-content: space-between;'>
                        <div>
                            <img src='{user['Foto']}' style='width: 100%; height: 200px; border-radius: 12px; border: 2px solid rgba(255, 215, 0, 0.4); object-fit: cover; margin-bottom: 12px;' />
                            <h4 class='glow-text' style='margin: 8px 0;'>{user['Nome']}</h4>
                            <p style='color: #ffd700; font-weight: bold; margin: 4px 0;'>{user['Tipo']}</p>
                            <p style='color: #ffe4b5; font-size: 12px; margin: 4px 0;'>{user['Origem']}</p>
                        </div>
                        <div style='border-top: 1px solid rgba(255, 215, 0, 0.2); padding-top: 12px; font-size: 11px; color: #ffe4b5;'>
                            <div style='margin: 4px 0;'><strong>Email:</strong></div>
                            <div style='word-break: break-word; margin-bottom: 8px;'>{user['Email']}</div>
                            <div style='margin: 4px 0;'><strong>Tel:</strong></div>
                            <div>{user['Telefone']}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Nenhum usuário cadastrado.")

def page_portal_lojista():
    """Módulo: Portal do Lojista (Com validações de duplicidade aprimoradas)."""
    st.subheader("Entrada de Visitantes")

    with st.form("form_lojista", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome *")
        d = c1.text_input("CPF *", placeholder="000.000.000-00")
        email_visitante = c1.text_input("Email *", placeholder="visitante@email.com")
        sex = c1.radio("Sexo", ["Masculino", "Feminino"], horizontal=True, key="sexo_visitante")

        foto_base64 = capturar_foto_camera("lojista")
        foto_upload = c2.file_uploader("Ou faça upload de foto", type=['png', 'jpg', 'jpeg'], key="foto_upload_visitante")

        tel = c2.text_input("Telefone *", placeholder="(00) 00000-0000")
        end = c2.text_input("Endereço Completo *")

        if st.form_submit_button("AUTORIZAR ENTRADA"):
            doc_formatado = Utils.formatar_cpf(d)
            
            if n and d and email_visitante and end:
                duplicidade = db_handler.is_duplicate(n, doc_formatado, email_visitante)
                
                if duplicidade:
                    st.error(f"ERRO: Cadastro duplicado detectado pelo campo '{duplicidade}'. Não é permitido Nome, CPF ou E-mail repetido.")
                else:
                    foto_path = 'N/A'
                    if foto_base64 and foto_base64.startswith('data:image'):
                        foto_path = salvar_foto(None, doc_formatado, foto_base64)
                    elif foto_upload:
                        foto_path = salvar_foto(foto_upload, doc_formatado)
                        
                    novo = {'Nome': n, 'Documento': doc_formatado, 'Email': email_visitante, 'Telefone': tel, 
                            'Tipo': "Visitante", 'Sexo': sex, 'Endereco': end, 'Origem': "Lojista", 
                            'Data_Cad': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'Foto': foto_path}
                        
                    db_handler.save_user(novo)
                    st.success("Acesso Liberado.")
                    st.rerun()
            else:
                st.warning("Preencha todos os campos obrigatórios (Nome, CPF, Email e Endereço).")

def page_bi_analytics():
    """Módulo: BI & Analytics."""
    st.subheader("CNAK Vision - Painel de BI")
    st.markdown("#### 4 prédios, 3 andares por prédio, 50 lojas por prédio e fluxo diário estimado de 5.000 pessoas.")

    dados_bi = gerar_dados_simulados_bi()

    st.markdown("""
        <div class='dashboard-card'>
            <div class='sparkle-row'>
                <div class='sparkle-pill'><strong class='glow-text'>Prédios</strong><br><span style='font-size:28px;'>4</span></div>
                <div class='sparkle-pill'><strong class='glow-text'>Andares</strong><br><span style='font-size:28px;'>3</span></div>
                <div class='sparkle-pill'><strong class='glow-text'>Lojas</strong><br><span style='font-size:28px;'>50</span></div>
                <div class='sparkle-pill'><strong class='glow-text'>Fluxo Diário</strong><br><span style='font-size:28px;'>5.000</span></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.markdown(f"""
        <div class='neon-box'>
            <h3 class='glow-text'>Total de Cadastros</h3>
            <p style='font-size:32px; margin:0;'>{len(db_handler.get_all_users())}</p>
        </div>
    """, unsafe_allow_html=True)
    c2.markdown("""
        <div class='neon-box'>
            <h3 class='glow-text'>Visitantes Ativos</h3>
            <p style='font-size:32px; margin:0;'>5.000</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""<div class='dashboard-card'><h3 class='glow-text'>📊 Dashboard Animado - Fluxo por Tipo de Acesso</h3></div>""", unsafe_allow_html=True)
    fig_animado = criar_grafico_animado(dados_bi)
    st.plotly_chart(fig_animado, use_container_width=True)

    st.markdown("""<div class='dashboard-card'><h3 class="glow-text">📈 Fluxo Diário em Tempo Real</h3></div>""", unsafe_allow_html=True)
    fig_fluxo = criar_grafico_fluxo_tempo_real(dados_bi)
    st.plotly_chart(fig_fluxo, use_container_width=True)

    st.markdown("""<div class='dashboard-card'><h3 class="glow-text">🏢 Fluxo por Andar</h3></div>""", unsafe_allow_html=True)
    fig_andares = criar_grafico_andares(dados_bi)
    st.plotly_chart(fig_andares, use_container_width=True)

    df_db = db_handler.get_all_users()
    if not df_db.empty:
        df_grouped = df_db.groupby(['Tipo', 'Origem']).size().reset_index(name='Quantidade')
        fig_real = px.bar(df_grouped, x='Tipo', y='Quantidade', color='Origem', title="Perfil de Acesso por Origem (Dados Reais)", template="plotly_dark")
        fig_real.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(28, 20, 7, 0.5)', font=dict(color='#ffd700'))
        
        st.markdown("""<div class='dashboard-card'><h3 class="glow-text">Dados Reais do Sistema</h3></div>""", unsafe_allow_html=True)
        st.plotly_chart(fig_real, use_container_width=True)
        st.markdown("""<div class='dashboard-card'><h3 class="glow-text">Relação de Usuários por Origem e Tipo</h3></div>""", unsafe_allow_html=True)
        st.dataframe(df_grouped, use_container_width=True)
    else:
        st.info("Nenhum registro disponível para análise de BI.")

# Dados de simulação para o Marketplace
DADOS_CONTRATO = {
    "PACOTE ESSENTIAL BI": {
        "melhor_horario": "Tardes (14h às 17h)", 
        "melhor_local": "Piso 2, próximo à Praça de Alimentação",
        "beneficios": ["Relatório Semanal de Fluxo", "Perfil por Gênero"]
    },
    "PACOTE HEATMAP PRO": {
        "melhor_horario": "Finais de semana (10h às 18h)", 
        "melhor_local": "Entrada Principal e Lojas Premium",
        "beneficios": ["Mapa de Calor em Tempo Real", "Taxa de Permanência"]
    },
    "PACOTE VISION AI": {
        "melhor_horario": "Noites de Quinta-feira (18h às 21h)", 
        "melhor_local": "Todos os andares com foco no Piso 3",
        "beneficios": ["IA Preditiva de Vendas", "BI + Mapa de Calor Completo"]
    }}

if 'contrato_ativo' not in st.session_state:
    st.session_state.contrato_ativo = None

def page_contrato_ativo(pacote):
    """Exibe os detalhes do pacote contratado (Item 3)."""
    st.subheader(f"Contrato Ativo: {pacote}")
    data = DADOS_CONTRATO.get(pacote, {})

    st.markdown("""<div class='dashboard-card'><h3 class="glow-text">Detalhes da Oferta Contratada</h3></div>""", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown(f"""
            <div class='neon-box'>
                <h4 class="glow-text">Melhor Período para Ofertas:</h4>
                <p style='font-size: 24px; color: #fff; text-shadow: 0 0 5px #ffd700;'>{data.get('melhor_horario', 'N/A')}</p>
                <p>Baseado na análise de fluxo dos últimos 30 dias, este é o pico de audiência para seu segmento.</p>
            </div>
        """, unsafe_allow_html=True)
    
    with c2:
        st.markdown(f"""
            <div class='neon-box'>
                <h4 class="glow-text">Melhor Localização para Ações Promocionais:</h4>
                <p style='font-size: 24px; color: #fff; text-shadow: 0 0 5px #ffd700;'>{data.get('melhor_local', 'N/A')}</p>
                <p>Maior concentração de público-alvo com perfil compatível ao seu produto/serviço.</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown('<h3 class="glow-text">Serviços Inclusos</h3>', unsafe_allow_html=True)
    
    for item in data.get('beneficios', []):
        st.markdown(f"• **{item}**", unsafe_allow_html=True)

    if st.button("Cancelar Contrato"):
        st.session_state.contrato_ativo = None
        st.success(f"Contrato {pacote} cancelado.")
        st.rerun()

def page_marketplace_dados():
    """Módulo: Marketplace de Dados (Item 3)."""
    
    if st.session_state.contrato_ativo:
        page_contrato_ativo(st.session_state.contrato_ativo)
        return

    st.subheader("Ofertas Exclusivas para Lojistas")
    col1, col2, col3 = st.columns(3)
        
    with col1:
        st.info("📊 **PACOTE ESSENTIAL BI**")
        st.write("- Relatório Semanal de Fluxo\n- Perfil por Gênero")
        st.markdown("### R$ 200,00 /mês")
        if st.button("ASSINAR ESSENTIAL"): 
            st.session_state.contrato_ativo = "PACOTE ESSENTIAL BI"
            st.success("Pacote contratado com sucesso!")
            st.rerun()
    with col2:
        st.success("🔥 **PACOTE HEATMAP PRO**")
        st.write("- Mapa de Calor em Tempo Real\n- Taxa de Permanência")
        st.markdown("### R$ 650,00 /mês")
        if st.button("ASSINAR HEATMAP"): 
            st.session_state.contrato_ativo = "PACOTE HEATMAP PRO"
            st.success("Pacote contratado com sucesso!")
            st.rerun()
    with col3:
        st.warning("🚀 **PACOTE VISION AI**")
        st.write("- IA Preditiva de Vendas\n- BI + Mapa de Calor Completo")
        st.markdown("### R$ 1.000,00 /mês")
        if st.button("ASSINAR VISION AI"): 
            st.session_state.contrato_ativo = "PACOTE VISION AI"
            st.success("Pacote contratado com sucesso!")
            st.rerun()

def page_gerenciamento_auditoria():
    """Módulo: Gerenciamento e Auditoria (Com atualização de vídeo)."""
    tab_users, tab_security = st.tabs(["👥 Gestão de Usuários", "🎥 Monitoramento Vídeo"])
    
    with tab_users:
        st.subheader("Gestão de Usuários")
        df_db = db_handler.get_all_users().sort_values(['Origem', 'Tipo', 'Nome'])

        if not df_db.empty:
            st.markdown("### Relação completa de usuários")
            st.dataframe(df_db, use_container_width=True)

            st.markdown("### Exclusão de registros")
            df_with_select = df_db.copy()
            df_with_select.insert(0, 'Selecionar', False)

            edited_df = st.data_editor(
                df_with_select,
                hide_index=True,
                column_config={'Selecionar': st.column_config.CheckboxColumn('Excluir?')},
                use_container_width=True
            )

            to_delete = edited_df[edited_df['Selecionar'] == True]['Documento'].tolist()

            if to_delete:
                st.warning(f'Atenção: {len(to_delete)} registro(s) serão apagados para sempre. Confirme para prosseguir.')
                if st.button('❌ EXCLUIR SELECIONADOS DEFINITIVAMENTE', key="confirm_delete"):
                    db_handler.delete_users(to_delete)
                    st.success('Dados removidos do servidor.')
                    st.rerun()
            else:
                st.info('Nenhum item selecionado para exclusão.')
            
            st.markdown("---")
            st.markdown('<div class="neon-box"><h4>Relatório de Auditoria</h4><p>Gere relatórios detalhados para fiscalização e compliance.</p></div>', unsafe_allow_html=True)
            if st.button("Gerar Relatório de Auditoria"):
                caminho, nome_arq, conteudo = gerar_relatorio_auditoria()
                st.success(f"Relatório gerado! Salvo em: {RELATORIOS_DIR}")
                st.download_button(label="📥 Baixar Relatório", data=conteudo, file_name=nome_arq, mime='text/plain')
        else:
            st.info('Banco de dados vazio.')

    with tab_security:
        st.subheader('CNAK VISION - Monitoramento de Câmeras')
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("<div class='video-container'>", unsafe_allow_html=True)
            st.write('🚗 **Controle de Estacionamento** (Vigilância Noturna)') # Título corrigido
            st.video('https://assets.mixkit.co/videos/download/mixkit-car-parking-lot-night-action-1305.mp4')
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='video-container'>", unsafe_allow_html=True)
            st.write('🛍️ **Câmera com IA em Shopping** (Fluxo de Pessoas)') # Título corrigido
            st.video('https://assets.mixkit.co/videos/download/mixkit-people-walking-in-shopping-mall-1110.mp4')
            st.markdown('</div>', unsafe_allow_html=True)

def page_relatorios_alertas():
    st.subheader("CNAK Vision - Relatórios e Alertas")
    st.markdown("""<div class='dashboard-card'><h3 class="glow-text">Painel de Relatórios Avançados</h3><p style='color: #ffe4b5;'>Monitore performance em tempo real com alertas inteligentes e relatórios automatizados.</p></div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
            <div class='neon-box'>
                <h4 class="glow-text">Relatórios Diários</h4>
                <p>Fluxo de visitantes, vendas por loja, alertas de segurança.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Gerar Relatório Diário"): 
            st.info("Relatório Diário simulado gerado com sucesso!")

    with col2:
        st.markdown("""
            <div class='neon-box'>
                <h4 class="glow-text">Alertas em Tempo Real</h4>
                <p>Notificações para picos de fluxo, acessos não autorizados.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Configurar Alertas"):
            st.info("Configurações de Alertas salvas.")

    st.markdown("""<div class='dashboard-card'><h3 class="glow-text">Análise Preditiva</h3><p style='color: #c8e9ff;'>Use IA para prever tendências de fluxo e otimizar operações.</p></div>""", unsafe_allow_html=True)
    if st.button("Executar Análise Preditiva"):
        st.success("Análise concluída! Tendência de aumento de 15% no fluxo para amanhã.")

def page_configuracoes_controle():
    """Módulo: Configurações e Controle (Com cadastro de usuário)."""
    tab_config, tab_access, tab_monitor, tab_heatmap = st.tabs(["⚙️ Configurações", "🔐 Controle de Acesso", "📡 Monitoramento", "🌡️ Mapa de Calor"])
    
    with tab_config:
        st.subheader("Configurações do Sistema")
        st.markdown("""<div class='dashboard-card'><h3 class="glow-text">Parâmetros Gerais</h3><p style='color: #c8e9ff;'>Ajuste configurações globais do sistema CNAK Vision.</p></div>""", unsafe_allow_html=True)
        st.slider("Limite de Visitantes por Dia", 1000, 10000, 5000)
        st.selectbox("Tema Visual", ["Neon Dark", "Classic", "Minimal"], index=0)
        if st.button("Salvar Configurações"):
            st.success("Configurações salvas com sucesso!")

    with tab_access:
        st.subheader("Controle de Acesso dos Usuários")
        
        # Cadastro de Nova Senha de Acesso
        st.markdown("---")
        st.markdown('<div class="dashboard-card"><h3 class="glow-text">🔑 Cadastro de Novo Acesso</h3></div>', unsafe_allow_html=True)
        
        with st.form("form_novo_acesso", clear_on_submit=True):
            novo_nome = st.text_input("Nome do Novo Operador *")
            novo_id = st.text_input("ID de Login * (Ex: user001)")
            novo_email_key = st.text_input("Email/Key de Identificação *")
            nova_chave = st.text_input("Senha de Acesso * (Mín. 8 caracteres)", type="password")
            confirmar_chave = st.text_input("Confirmar Senha *", type="password")
            novo_nivel = st.selectbox("Nível de Permissão", ["Operacional", "Lojista", "Admin"])
            
            if st.form_submit_button("CADASTRAR NOVO ACESSO"):
                if nova_chave != confirmar_chave:
                    st.error("As senhas digitadas não coincidem.")
                elif len(nova_chave) < 8:
                    st.error("A senha deve ter no mínimo 8 caracteres.")
                elif not (novo_id and novo_email_key and novo_nome and nova_chave):
                    st.error("Preencha todos os campos obrigatórios.")
                elif novo_id in [u['id'] for u in st.session_state.USUARIOS_CADASTRO_STATE.values()]:
                    st.error(f"O ID de Login '{novo_id}' já está em uso. Escolha outro.")
                else:
                    st.session_state.USUARIOS_CADASTRO_STATE[novo_email_key] = {
                        "id": novo_id,
                        "chave": nova_chave,
                        "nome": novo_nome,
                        "nivel": novo_nivel
                    }
                    # CORREÇÃO: Salva o novo usuário no arquivo JSON para persistência
                    save_login_users(st.session_state.USUARIOS_CADASTRO_STATE) 
                    
                    st.success(f"Novo acesso criado para **{novo_nome}** (Nível: {novo_nivel}) com sucesso! Eles podem logar imediatamente.")
        
        st.markdown("#### Histórico de Acessos")
        # Usando a função de relatório de acesso
        access_logs = [
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')} - {st.session_state.user_info.get('nome')} - Acesso ao BI",
            "17/04/2026 09:45 - Operador 1 - Tentativa falhada",
            "17/04/2026 08:20 - Lojista A - Cadastro realizado"
        ]
        for log in access_logs:
            st.write(f"• {log}")
            
        if st.button("Gerar Relatório de Acesso"):
            caminho, nome_arq, conteudo = gerar_relatorio_acessos()
            st.success(f"Relatório gerado! Salvo em: {RELATORIOS_DIR}")
            st.download_button(label="📥 Baixar Relatório", data=conteudo, file_name=nome_arq, mime='text/plain')

    with tab_monitor:
        st.subheader("Monitoramento em Tempo Real")
        st.markdown("""<div class='dashboard-card'><h3 class="glow-text">Status do Sistema</h3></div>""", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Servidores Ativos", "4/4", delta="+0")
        col2.metric("Câmeras Online", "12/12", delta="+0")
        col3.metric("Fluxo Atual", "1.250", delta="+5%")
        col4.metric("Alertas Ativos", "2", delta="-1")
        st.progress(0.75, text="Uso de Recursos: 75%")

        st.markdown("""<div class='neon-box'><h4>Logs de Atividade Recente</h4></div>""", unsafe_allow_html=True)
        logs = [
            f"{datetime.now().strftime('%H:%M')} - Acesso autorizado: {st.session_state.user_info.get('nome')}",
            "10:42 - Câmera 5: Movimento detectado",
            "10:40 - Alerta: Fluxo alto no Piso 2",
            "10:35 - Backup automático concluído"
        ]
        for log in logs:
            st.write(f"• {log}")

        if st.button("Verificar Status Detalhado"):
            st.info("Sistema operacional. Última verificação: " + datetime.now().strftime("%H:%M:%S"))
            st.success("Nenhum problema crítico detectado!")

    with tab_heatmap:
        st.subheader("Mapa de Calor de Fluxo")
        dados_heatmap = gerar_dados_simulados_heatmap()
        
        st.markdown("""<div class='dashboard-card'><h3 class="glow-text">🗺️ Mapa de Calor - Densidade por Zona</h3></div>""", unsafe_allow_html=True)
        fig_heatmap = criar_mapa_calor_interativo(dados_heatmap)
        st.plotly_chart(fig_heatmap, use_container_width=True)

        st.markdown("""<div class='dashboard-card'><h3 class="glow-text">⏰ Fluxo por Horário</h3></div>""", unsafe_allow_html=True)
        fig_horas = criar_grafico_horas(dados_heatmap)
        st.plotly_chart(fig_horas, use_container_width=True)

# ==============================================================================
# 7. LÓGICA PRINCIPAL DO APLICATIVO
# ==============================================================================

def logout():
    """Função para deslogar e reverter o estado para o formulário de login."""
    st.session_state.logged_in = False
    st.session_state.user_info = {}
    st.rerun()

def main_app():
    """Gerencia a navegação principal após o login."""
    
    user_name = st.session_state.user_info.get('nome', 'Usuário')
    st.sidebar.markdown(f"## 🛡️ OPERADOR: {user_name.upper()}")

    # NOVO: Botão de Logout na sidebar
    if st.sidebar.button("LOGOUT (Sair)"):
        logout()
        
    menu_options = [
        "📝 Cadastro Geral", "🛍️ Portal do Lojista", "📊 BI & Analytics", 
        "💎 Marketplace de Dados", "⚙️ Gerenciamento e Auditoria", 
        "📈 Relatórios e Alertas", "🔧 Configurações e Controle"
    ]

    menu = st.sidebar.radio("Módulos:", menu_options)

    st.markdown(f'<div class="neon-title">💠 {menu}</div>', unsafe_allow_html=True)

    if menu == "📝 Cadastro Geral":
        page_cadastro_geral()
    elif menu == "🛍️ Portal do Lojista":
        page_portal_lojista()
    elif menu == "📊 BI & Analytics":
        page_bi_analytics()
    elif menu == "💎 Marketplace de Dados":
        page_marketplace_dados()
    elif menu == "⚙️ Gerenciamento e Auditoria":
        page_gerenciamento_auditoria()
    elif menu == "📈 Relatórios e Alertas":
        page_relatorios_alertas()
    elif menu == "🔧 Configurações e Controle":
        page_configuracoes_controle()


# ==============================================================================
# 8. PONTO DE ENTRADA
# ==============================================================================

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_form()
else:
    main_app()
