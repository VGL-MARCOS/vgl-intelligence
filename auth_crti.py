"""
auth_crti.py
────────────
Autenticação do CRTI Intelligence via credenciais do CRTI ERP.

Como funciona:
  - Exibe tela de login com usuário/senha
  - Faz POST /api/v1/auth/signin no CRTI
  - Se retornar accessToken, o usuário está autenticado
  - Token e dados ficam em st.session_state pela sessão

Qualquer usuário com acesso ao CRTI pode acessar o BI.
Sem necessidade de cadastro separado ou Streamlit Secrets para auth.
"""

import streamlit as st
import requests
import time
import os
import sys

# Garante que config.py é encontrado
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules"))

def _get_base_url() -> str:
    """Lê a URL base do CRTI dos Secrets ou config."""
    try:
        return st.secrets.get("CRTI_BASE_URL", "https://vogelsanger.crti.com.br")
    except Exception:
        try:
            from config import CRTI_CONFIG
            return CRTI_CONFIG.get("base_url", "https://vogelsanger.crti.com.br")
        except Exception:
            return "https://vogelsanger.crti.com.br"

def _autenticar_crti(usuario: str, senha: str) -> dict | None:
    """
    Tenta autenticar no CRTI ERP.
    Retorna dict com accessToken e info do usuário, ou None se falhar.
    """
    base_url = _get_base_url()
    url = f"{base_url}/api/v1/auth/signin"
    try:
        resp = requests.post(
            url,
            json={"username": usuario, "password": senha},
            timeout=15,
            headers={"Content-Type": "application/json"}
        )
        if resp.status_code == 200:
            dados = resp.json()
            token = dados.get("accessToken") or dados.get("access_token")
            if token:
                return {"token": token, "refresh": dados.get("refreshToken"),
                        "usuario": usuario}
        return None
    except requests.exceptions.ConnectionError:
        return {"erro": "conexao"}
    except Exception:
        return None

def requer_autenticacao():
    """
    Bloqueia o app e exibe tela de login se o usuário não estiver autenticado.
    Chame no TOPO do app.py, antes de qualquer outra lógica.
    """
    if st.session_state.get("crti_autenticado"):
        return  # ✅ Já autenticado

    _tela_login()
    st.stop()

def usuario_atual() -> str:
    """Retorna o nome do usuário logado."""
    return st.session_state.get("crti_usuario", "")

def token_atual() -> str:
    """Retorna o token JWT da sessão."""
    return st.session_state.get("crti_token", "")

def logout():
    """Encerra a sessão."""
    for k in ["crti_autenticado", "crti_usuario", "crti_token", "crti_refresh"]:
        st.session_state.pop(k, None)
    st.rerun()

def _tela_login():
    """Renderiza a tela de login."""
    st.markdown("""
    <style>
    #MainMenu {visibility:hidden;} footer {visibility:hidden;}
    .login-wrap {
        max-width: 420px; margin: 3rem auto;
        background: white; border-radius: 16px;
        padding: 2.5rem; box-shadow: 0 4px 32px rgba(26,60,110,.15);
        border: 1px solid #E0E8F5;
    }
    .login-header { text-align:center; margin-bottom:2rem; }
    .login-header h2 { color:#1A3C6E; margin:.4rem 0 .2rem; font-size:1.5rem; }
    .login-header p  { color:#888; font-size:.85rem; margin:0; }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div class="login-wrap">
            <div class="login-header">
                <div style="font-size:3rem;">📊</div>
                <h2>CRTI Intelligence</h2>
                <p>Britagem Vogelsanger — use seu login do CRTI</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("form_login_crti", clear_on_submit=False):
            usuario = st.text_input("👤 Usuário CRTI", placeholder="seu.usuario")
            senha   = st.text_input("🔒 Senha CRTI",   type="password", placeholder="••••••••")
            entrar  = st.form_submit_button("Entrar", use_container_width=True)

        if entrar:
            if not usuario or not senha:
                st.error("Preencha usuário e senha.")
                return

            with st.spinner("Autenticando no CRTI..."):
                resultado = _autenticar_crti(usuario, senha)

            if resultado is None:
                time.sleep(1)
                st.error("❌ Usuário ou senha inválidos.")
            elif isinstance(resultado, dict) and resultado.get("erro") == "conexao":
                st.error("❌ Não foi possível conectar ao CRTI. Verifique sua conexão.")
            elif resultado and resultado.get("token"):
                st.session_state["crti_autenticado"] = True
                st.session_state["crti_usuario"]     = resultado["usuario"]
                st.session_state["crti_token"]       = resultado["token"]
                st.session_state["crti_refresh"]     = resultado.get("refresh","")
                st.success(f"✅ Bem-vindo, {usuario}!")
                time.sleep(0.4)
                st.rerun()
            else:
                st.error("❌ Falha na autenticação. Verifique suas credenciais.")

        st.caption("🔒 Suas credenciais são enviadas diretamente ao CRTI e não são armazenadas.")
