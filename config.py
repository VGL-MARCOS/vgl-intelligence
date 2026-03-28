"""
=============================================================
  CRTI + CLAUDE INTEGRATION — CONFIGURAÇÕES CENTRALIZADAS
  Suporta dois modos:
    - LOCAL:  lê do arquivo .env
    - NUVEM:  lê dos Streamlit Secrets (st.secrets)
=============================================================
"""

import os

# ── Tenta carregar Streamlit Secrets (modo nuvem) ──
def _get(chave: str, padrao: str = "") -> str:
    """
    Busca credenciais na seguinte ordem:
    1. Streamlit Secrets (quando rodando na nuvem)
    2. Variáveis de ambiente / .env (quando rodando local)
    3. Valor padrão
    """
    try:
        import streamlit as st
        if chave in st.secrets:
            return st.secrets[chave]
        # Tenta seção aninhada ex: st.secrets["crti"]["CLIENT_ID"]
        secao = chave.split("_")[0].lower()
        campo = "_".join(chave.split("_")[1:])
        if secao in st.secrets and campo in st.secrets[secao]:
            return st.secrets[secao][campo]
    except Exception:
        pass

    # Fallback: variável de ambiente / .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    return os.getenv(chave, padrao)


# ─────────────────────────────────────────────
#  CRTI ERP — Credenciais e Endpoints REAIS
# ─────────────────────────────────────────────
CRTI_CONFIG = {
    "base_url":      _get("CRTI_BASE_URL", "https://vogelsanger.crti.com.br"),

    # X-Api-Key (Chave Única — Credenciais B2B no CRTI) — MÉTODO PRINCIPAL
    "xapi_key":      _get("CRTI_XAPI_KEY", ""),

    # OAuth 2.0 (fallback)
    "client_id":     _get("CRTI_CLIENT_ID",     ""),
    "client_secret": _get("CRTI_CLIENT_SECRET", ""),

    # Usuário/Senha (fallback)
    "username": _get("CRTI_USERNAME", ""),
    "password": _get("CRTI_PASSWORD", ""),

    "timeout": 30,

    "endpoints": {
        "signin":        "/api/v1/auth/signin",
        "refresh_token": "/api/v1/auth/refresh_token",
        "info":          "/api/v1/auth/info",

        "transferencias": "/api/v1/financeiro/trf_pagar_receber",
        "conta_corrente": "/api/v1/financeiro/conta_corrente",
        "permuta":        "/api/v1/financeiro/permuta",
        "boleto_config":  "/api/v1/financeiro/configuracao_boleto",

        "materiais":      "/api/v1/suprimentos/materiais",

        "servicos_por_filial": "/api/v1/custos/servicos_por_filial",
        "perdas":              "/api/v1/custos/perdas",
        "turnos_trabalho":     "/api/v1/custos/turnos_de_trabalho",
        "bmo":                 "/api/v1/custos/bmo",
        "blepdv":              "/api/v1/custos/blepdv",

        "acompanhamento_requisicoes": "/api/v1/compras/acompanhamento_requisicoes",

        "equipamentos":        "/api/v1/equipamentos/equipamentos",
        "os_manutencao":       "/api/v1/equipamentos/ordemservicomanutencao",
        "transferencias_equip":"/api/v1/equipamentos/transferencias",
    }
}

# ─────────────────────────────────────────────
#  CLAUDE API
# ─────────────────────────────────────────────
CLAUDE_CONFIG = {
    "api_key":    _get("ANTHROPIC_API_KEY", ""),
    "model":      "claude-sonnet-4-20250514",
    "max_tokens": 4096,
}

# ─────────────────────────────────────────────
#  EMAIL
# ─────────────────────────────────────────────
EMAIL_CONFIG = {
    "smtp_host":     _get("SMTP_HOST", "smtp.gmail.com"),
    "smtp_port":     587,
    "usuario":       _get("EMAIL_USER", ""),
    "senha":         _get("EMAIL_PASS", ""),
    "remetente":     _get("EMAIL_FROM", ""),
    "destinatarios": _get("EMAIL_TO", "").split(","),
}

# ─────────────────────────────────────────────
#  AGENDAMENTO
# ─────────────────────────────────────────────
SCHEDULE_CONFIG = {
    "auditoria_financeira": {"frequencia": "diaria",  "horario": "07:00", "ativo": True},
    "relatorio_contas":     {"frequencia": "diaria",  "horario": "08:00", "ativo": True},
    "analise_semanal":      {"frequencia": "semanal", "dia_semana": "monday", "horario": "06:30", "ativo": True},
    "relatorio_mensal":     {"frequencia": "mensal",  "dia_mes": 1, "horario": "06:00", "ativo": True},
}

PATHS = {
    "outputs": "./outputs",
    "logs":    "./logs",
}
