import streamlit as st

# Ler e aplicar o CSS externo
with open("teste.css", "r", encoding="utf-8") as f:
    css_content = f.read()

# Injetar o CSS na página Streamlit
st.markdown(f"""
    <style>
    {css_content}
    </style>
""", unsafe_allow_html=True)

# Configuração da página
st.set_page_config(page_title="CNAK Vision - Painel", layout="centered")

st.title("🏢 CNAK Vision - Controle de Acesso")
st.write("Bem-vindo ao sistema de gestão inteligente das galerias comerciais.")
st.write("Selecione a ação desejada:")

col1, col2 = st.columns(2)

with col1:
    if st.button("➕ Cadastrar Usuário/Equipamento", use_container_width=True):
        st.success("Abrindo módulo de Cadastro...")

with col2:
    if st.button("🔍 Consultar Acessos", use_container_width=True):
        st.info("Abrindo módulo de Consulta do Banco de Dados...")