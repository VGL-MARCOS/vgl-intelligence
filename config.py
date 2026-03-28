"""
=============================================================
  CRTI + CLAUDE INTEGRATION — CONFIGURAÇÕES CENTRALIZADAS
  Atualizado com endpoints reais da API CRTI (OAS 3.0)
=============================================================
  Edite este arquivo com suas credenciais antes de rodar.
"""

import os
from dotenv import load_dotenv
load_dotenv()  # carrega o .env ANTES de qualquer os.getenv()

# ─────────────────────────────────────────────
#  CRTI ERP — Credenciais e Endpoints REAIS
#  URL base confirmada: https://vogelsanger.crti.com.br
# ─────────────────────────────────────────────
CRTI_CONFIG = {
    "base_url":  os.getenv("CRTI_BASE_URL", "https://vogelsanger.crti.com.br"),

    # OAuth 2.0 (recomendado — gerado em Credenciais B2B no CRTI)
    "client_id":     os.getenv("CRTI_CLIENT_ID", ""),
    "client_secret": os.getenv("CRTI_CLIENT_SECRET", ""),

    # Usuário/Senha (fallback)
    "username":  os.getenv("CRTI_USERNAME", ""),
    "password":  os.getenv("CRTI_PASSWORD", "SUA_SENHA_CRTI"),

    "timeout": 30,  # segundos

    # Endpoints 100% confirmados pelo OpenAPI spec do CRTI
    "endpoints": {
        # Autenticação
        "signin":         "/api/v1/auth/signin",
        "refresh_token":  "/api/v1/auth/refresh_token",
        "info":           "/api/v1/auth/info",

        # Financeiro (módulo confirmado)
        "transferencias": "/api/v1/financeiro/trf_pagar_receber",
        "conta_corrente": "/api/v1/financeiro/conta_corrente",
        "permuta":        "/api/v1/financeiro/permuta",
        "boleto_config":  "/api/v1/financeiro/configuracao_boleto",

        # Suprimentos (confirmado)
        "materiais":      "/api/v1/suprimentos/materiais",

        # Módulos adicionais — adicione quando explorar outras URLs
        # Custos (confirmado)
        "servicos_por_filial": "/api/v1/custos/servicos_por_filial",
        "perdas":              "/api/v1/custos/perdas",
        "turnos_trabalho":     "/api/v1/custos/turnos_de_trabalho",
        "bmo":                 "/api/v1/custos/bmo",
        "blepdv":              "/api/v1/custos/blepdv",

        # Compras (confirmado)
        "acompanhamento_requisicoes": "/api/v1/compras/acompanhamento_requisicoes",

        # Equipamentos / Frota (confirmado)
        "equipamentos":            "/api/v1/equipamentos/equipamentos",
        "os_manutencao":            "/api/v1/equipamentos/ordemservicomanutencao",
        "transferencias_equip":     "/api/v1/equipamentos/transferencias",

        # Ainda a explorar
        # "cargas":       "/api/v1/cargas/...",
        # "apropriacoes": "/api/v1/apropriacoes/...",
    }
}

# ─────────────────────────────────────────────
#  CLAUDE API — Configurações
# ─────────────────────────────────────────────
CLAUDE_CONFIG = {
    "api_key":    os.getenv("ANTHROPIC_API_KEY", "SUA_CHAVE_ANTHROPIC_AQUI"),
    "model":      "claude-sonnet-4-20250514",
    "max_tokens": 4096,
}

# ─────────────────────────────────────────────
#  EMAIL — Para envio automático dos relatórios
# ─────────────────────────────────────────────
EMAIL_CONFIG = {
    "smtp_host":     os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "smtp_port":     587,
    "usuario":       os.getenv("EMAIL_USER", "seu@email.com"),
    "senha":         os.getenv("EMAIL_PASS", "sua_senha_app"),
    "remetente":     os.getenv("EMAIL_FROM", "relatorios@suaempresa.com.br"),
    "destinatarios": os.getenv("EMAIL_TO", "diretoria@suaempresa.com.br").split(","),
}

# ─────────────────────────────────────────────
#  AGENDAMENTO — Frequência de cada relatório
# ─────────────────────────────────────────────
SCHEDULE_CONFIG = {
    "auditoria_financeira": {
        "frequencia":  "diaria",
        "horario":     "07:00",
        "ativo":       True,
    },
    "relatorio_contas": {
        "frequencia":  "diaria",
        "horario":     "08:00",
        "ativo":       True,
    },
    "analise_semanal": {
        "frequencia":  "semanal",
        "dia_semana":  "monday",
        "horario":     "06:30",
        "ativo":       True,
    },
    "relatorio_mensal": {
        "frequencia":  "mensal",
        "dia_mes":     1,
        "horario":     "06:00",
        "ativo":       True,
    },
}

# ─────────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────────
PATHS = {
    "outputs": "./outputs",
    "logs":    "./logs",
}

# ─────────────────────────────────────────────
#  SUPRIMENTOS — adicionado após mapeamento da API
# ─────────────────────────────────────────────
# Adicione ao bloco "endpoints" dentro de CRTI_CONFIG:
#   "materiais": "/api/v1/suprimentos/materiais",
