"""
=============================================================
  CRTI + CLAUDE — APP WEB
  Interface visual para geração de relatórios e dashboards
  Rode com: streamlit run app.py
=============================================================
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import sys
import os

# Garante que os módulos do projeto são encontrados
sys.path.insert(0, os.path.dirname(__file__))

from modules.crti_client     import CRTIClient
from modules.claude_analyzer import ClaudeAnalyzer
from modules.report_generator import ReportGenerator
from modules.periodos        import Periodos
from modules.resumidor       import (
    resumir_transferencias, resumir_equipamentos,
    resumir_os_manutencao, resumir_materiais, resumir_compras
)

# ─────────────────────────────────────────────
#  CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="CRTI Intelligence | Vogelsanger",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"  # fechado por padrão no celular
)

# ─────────────────────────────────────────────
#  ESTILOS CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* ── MOBILE FIRST ── */
    @media (max-width: 768px) {
        .main-header { padding: 1rem !important; }
        .main-header h1 { font-size: 1.2rem !important; }
        .main-header p  { font-size: 0.8rem !important; }
        .kpi-value { font-size: 1.3rem !important; }
        .kpi-label { font-size: 0.7rem !important; }
        .block-container { padding: 0.5rem !important; }
        .kpi-card { padding: 0.6rem 0.4rem !important; }
    }

    /* Cabeçalho principal */
    .main-header {
        background: linear-gradient(135deg, #1A3C6E 0%, #2C5F9E 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1rem;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.6rem; }
    .main-header p  { color: #BDD0F0; margin: 0.2rem 0 0; font-size: 0.85rem; }

    /* Cards de KPI — compactos no mobile */
    .kpi-card {
        background: white;
        border: 1px solid #E0E8F5;
        border-radius: 10px;
        padding: 0.8rem 0.6rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(26,60,110,0.07);
        height: 100%;
    }
    .kpi-value { font-size: 1.6rem; font-weight: 700; color: #1A3C6E; line-height: 1.2; }
    .kpi-label { font-size: 0.75rem; color: #888; margin-top: 0.2rem; line-height: 1.3; }
    .kpi-delta { font-size: 0.75rem; margin-top: 0.2rem; }
    .kpi-delta.up   { color: #0A6E3F; }
    .kpi-delta.down { color: #C0392B; }
    .kpi-delta.warn { color: #F39C12; }

    /* Alertas */
    .alert-box {
        background: #FDECEA;
        border-left: 4px solid #C0392B;
        padding: 0.7rem 0.8rem;
        border-radius: 0 8px 8px 0;
        margin: 0.4rem 0;
        font-size: 0.9rem;
    }
    .alert-box.warn { background: #FFF3CD; border-left-color: #F39C12; }
    .alert-box.ok   { background: #E8F5EE; border-left-color: #0A6E3F; }

    /* Botões */
    .stButton > button {
        background: #1A3C6E;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-weight: 600;
        width: 100%;
        font-size: 0.9rem;
    }
    .stButton > button:hover { background: #2C5F9E; }

    /* Status */
    .status-ok   { background:#E8F5EE; color:#0A6E3F; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600; }
    .status-warn { background:#FFF3CD; color:#F39C12; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600; }
    .status-err  { background:#FDECEA; color:#C0392B; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600; }

    /* Tabelas — scroll horizontal no mobile */
    .stDataFrame { overflow-x: auto !important; }

    /* Reduz padding geral no mobile */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }

    /* Gráficos responsivos */
    .js-plotly-plot { width: 100% !important; }

    /* Esconde menu e rodapé padrão */
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }

    /* Sidebar mais compacta */
    [data-testid="stSidebar"] { min-width: 240px !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  CACHE DE CONEXÃO
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_crti():
    return CRTIClient()

@st.cache_resource(show_spinner=False)
def get_claude():
    return ClaudeAnalyzer()

@st.cache_resource(show_spinner=False)
def get_pdf():
    return ReportGenerator()


# ─────────────────────────────────────────────
#  CACHE DE DADOS (evita rebuscar a cada clique)
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)  # 1 hora — filiais mudam raramente
def buscar_filiais():
    """Busca lista de filiais via contas correntes (campo filial)."""
    try:
        contas = get_crti().buscar_contas_correntes(apenas_ativas=True)
        filiais = {}
        for c in contas:
            f = c.get("filial") or {}
            fid = f.get("id")
            fnome = f.get("nome", "")
            if fid and fnome:
                filiais[fid] = fnome
        return filiais  # {id: nome}
    except:
        return {}

@st.cache_data(ttl=1800, show_spinner=False)  # 30 min — cadastro muda pouco
def buscar_equipamentos(filial_id=None):
    return get_crti().buscar_equipamentos(filial_atual=filial_id)

@st.cache_data(ttl=600, show_spinner=False)
def buscar_os(inicio, fim, filiais_ids=None):
    return get_crti().buscar_os_manutencao(
        data_abertura_de=inicio, data_abertura_ate=fim,
        filiais_oficina=filiais_ids or None
    )

@st.cache_data(ttl=600, show_spinner=False)
def buscar_transferencias(inicio, fim, filiais_ids=None):
    return get_crti().buscar_transferencias(
        inicio, fim,
        filial_ids=filiais_ids or None
    )

@st.cache_data(ttl=600, show_spinner=False)
def buscar_compras(inicio, fim, filiais_ids=None):
    return get_crti().buscar_compras_periodo(inicio, fim)

@st.cache_data(ttl=600, show_spinner=False)
def buscar_pedidos(inicio, fim, situacao=None, filiais_ids=None):
    return get_crti().buscar_pedidos_material(
        data_inicio=inicio, data_fim=fim,
        situacao=situacao,
        ids_filiais=filiais_ids or None
    )



@st.cache_data(ttl=600, show_spinner=False)
def buscar_orcamentos(inicio, fim):
    try:
        return get_crti().buscar_orcamentos_venda(data_inicio=inicio, data_fim=fim)
    except Exception as e:
        # CRTI pode retornar 500 neste endpoint — retorna lista vazia
        import logging
        logging.getLogger("app").warning(f"Orçamentos indisponível: {e}")
        return []

@st.cache_data(ttl=7200, show_spinner=False)  # 2 horas — análise pesada
def buscar_clientes_inativos_cache(dias=60):
    return get_crti().buscar_clientes_inativos(dias_sem_comprar=dias)

@st.cache_data(ttl=1800, show_spinner=False)  # 30 min
def buscar_materiais():
    return get_crti().buscar_materiais(apenas_ativos=False)

@st.cache_data(ttl=300, show_spinner=False)
def buscar_info_empresa():
    return get_crti().buscar_info_empresa()


# ─────────────────────────────────────────────
#  HELPERS DE FORMATAÇÃO
# ─────────────────────────────────────────────
def fmt_brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ —"

def fmt_pct(v):
    try:
        return f"{float(v):.1f}%"
    except:
        return "—"

def kpi(label, value, delta=None, delta_type="ok"):
    delta_html = ""
    if delta:
        delta_html = f'<div class="kpi-delta {delta_type}">{delta}</div>'
    return f"""
    <div class="kpi-card">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
        {delta_html}
    </div>
    """


# ─────────────────────────────────────────────
#  SIDEBAR — NAVEGAÇÃO E PERÍODO
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 0.5rem 0 1rem;">
        <div style="font-size:2rem;">📊</div>
        <div style="font-weight:700; color:#1A3C6E; font-size:1.1rem;">CRTI Intelligence</div>
        <div style="color:#888; font-size:0.8rem;">Britagem Vogelsanger</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Navegação
    pagina = st.selectbox(
        "📍 Módulo",
        options=[
            "🏠 Painel Geral",
            "🛍️ Vendas",
            "👥 Clientes Inativos",
            "🚜 Frota e Equipamentos",
            "🔧 Manutenção",
            "💳 Financeiro",
            "🛒 Compras",
            "📦 Materiais",
            "🤖 Gerar Relatório com IA",
        ]
    )

    st.divider()

    # Seleção de período
    st.markdown("**📅 Período**")
    tipo_periodo = st.selectbox(
        "Período",
        [
            "Mês atual",
            "Mês anterior",
            "Últimos 7 dias",
            "Últimos 30 dias",
            "Últimos 3 meses",
            "Últimos 6 meses",
            "Ano atual",
            "Personalizado",
        ],
        label_visibility="collapsed"
    )

    if tipo_periodo == "Personalizado":
        col1, col2 = st.columns(2)
        with col1:
            data_ini = st.date_input("Início", value=datetime.now().replace(day=1))
        with col2:
            data_fim = st.date_input("Fim", value=datetime.now())
        inicio = data_ini.strftime("%Y-%m-%d")
        fim    = data_fim.strftime("%Y-%m-%d")
    elif tipo_periodo == "Mês atual":
        inicio, fim = Periodos.mes_atual()
    elif tipo_periodo == "Mês anterior":
        inicio, fim = Periodos.mes_anterior()
    elif tipo_periodo == "Últimos 7 dias":
        inicio, fim = Periodos.ultimos_7_dias()
    elif tipo_periodo == "Últimos 30 dias":
        inicio, fim = Periodos.ultimos_30_dias()
    elif tipo_periodo == "Últimos 3 meses":
        inicio, fim = Periodos.ultimos_n_meses(3)
    elif tipo_periodo == "Últimos 6 meses":
        inicio, fim = Periodos.ultimos_n_meses(6)
    elif tipo_periodo == "Ano atual":
        inicio, fim = Periodos.ano_atual()
    else:
        inicio, fim = Periodos.mes_atual()

    label_periodo = Periodos.formatar_label(inicio, fim)
    st.caption(f"📆 {label_periodo}")

    st.divider()

    # Seletor de filiais
    st.markdown("**🏭 Filial**")
    try:
        filiais_dict = buscar_filiais()
        if filiais_dict:
            filiais_selecionadas = st.multiselect(
                "Filiais",
                options=sorted(filiais_dict.values()),
                default=None,
                placeholder="Todas as filiais",
                label_visibility="collapsed"
            )
            filiais_ids = [k for k,v in filiais_dict.items()
                           if v in filiais_selecionadas] or None
            if filiais_ids:
                st.caption(f"🏭 {len(filiais_ids)} filial(is)")
            else:
                st.caption("🏭 Todas as filiais")
        else:
            filiais_ids = None
    except Exception:
        filiais_ids = None

    st.divider()

    # Status da conexão
    st.markdown("**🔌 Status**")
    try:
        info = buscar_info_empresa()
        empresa = info.get("nomeEmpresa", "Conectado")
        st.markdown(f'<span class="status-ok">✓ {empresa[:25]}</span>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown('<span class="status-err">✗ Sem conexão com CRTI</span>', unsafe_allow_html=True)

    st.caption(f"Atualizado: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Atualizar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ═══════════════════════════════════════════════
#  PÁGINAS
# ═══════════════════════════════════════════════

# ─────────────────────────────────────────────
#  PÁGINA 1 — PAINEL GERAL
# ─────────────────────────────────────────────
if pagina == "🏠 Painel Geral":
    st.markdown("""
    <div class="main-header">
        <h1>📊 Painel Executivo</h1>
        <p>Visão consolidada da operação — Britagem Vogelsanger LTDA</p>
    </div>
    """, unsafe_allow_html=True)

    # Painel carrega em paralelo mostrando cada seção conforme fica pronto
    ph_kpi  = st.empty()
    ph_graf = st.empty()
    ph_alert= st.empty()

    with st.spinner("Carregando equipamentos..."):
        equipamentos = buscar_equipamentos(filial_id=filiais_ids[0] if filiais_ids and len(filiais_ids)==1 else None)
        res_equip    = resumir_equipamentos(equipamentos)

    with st.spinner("Carregando OS e financeiro..."):
        os_lista = buscar_os(inicio, fim, filiais_ids=filiais_ids)
        trf      = buscar_transferencias(inicio, fim, filiais_ids=filiais_ids)
        res_os   = resumir_os_manutencao(os_lista)
        res_trf  = resumir_transferencias(trf)

    with ph_kpi.container():
        try:
            hoje = datetime.now().date().isoformat()

            # ── KPIs — 5 colunas desktop, 2+3 no mobile ──
            col1, col2, col3, col4, col5 = st.columns([1,1,1,1,1])
            with col1:
                st.markdown(kpi("Equipamentos", res_equip["total_equipamentos"]), unsafe_allow_html=True)
            with col2:
                st.markdown(kpi("OS no Período", res_os["total_os"],
                                delta=f"⚠️ {res_os['os_atrasadas']} atrasadas" if res_os['os_atrasadas'] > 0 else "✓ Todas no prazo",
                                delta_type="warn" if res_os['os_atrasadas'] > 0 else "up"),
                            unsafe_allow_html=True)
            with col3:
                st.markdown(kpi("Seguros Vencidos", res_equip["seguros_vencidos"],
                                delta="⚠️ Ação urgente" if res_equip["seguros_vencidos"] > 0 else "✓ OK",
                                delta_type="warn" if res_equip["seguros_vencidos"] > 0 else "up"),
                            unsafe_allow_html=True)
            with col4:
                st.markdown(kpi("Docs Financeiros", res_trf["total_documentos"]), unsafe_allow_html=True)
            with col5:
                st.markdown(kpi("Valor no Período", fmt_brl(res_trf["valor_total_emitido"])), unsafe_allow_html=True)

            st.divider()

            # ── Gráficos ──
            col_a, col_b = st.columns(2)

            with col_a:
                st.subheader("OS por Situação")
                if res_os["por_situacao"]:
                    df_sit = pd.DataFrame(
                        list(res_os["por_situacao"].items()),
                        columns=["Situação", "Quantidade"]
                    )
                    fig = px.bar(df_sit, x="Situação", y="Quantidade",
                                 color="Quantidade",
                                 color_continuous_scale=["#2C5F9E", "#1A3C6E"],
                                 template="plotly_white")
                    fig.update_layout(showlegend=False, margin=dict(t=20, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Nenhuma OS no período selecionado.")

            with col_b:
                st.subheader("Top 10 Fornecedores (Financeiro)")
                if res_trf["top_15_fornecedores"]:
                    df_forn = pd.DataFrame(res_trf["top_15_fornecedores"][:10])
                    df_forn["valor_fmt"] = df_forn["valor"].apply(fmt_brl)
                    fig2 = px.bar(df_forn, x="valor", y="fornecedor",
                                  orientation="h",
                                  color_discrete_sequence=["#1A3C6E"],
                                  template="plotly_white",
                                  text="valor_fmt")
                    fig2.update_layout(yaxis=dict(categoryorder="total ascending"),
                                       margin=dict(t=20, b=20), showlegend=False)
                    fig2.update_traces(textposition="outside")
                    st.plotly_chart(fig2, use_container_width=True)

        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")

    try:
        st.subheader("⚠️ Alertas Ativos")
        alertas = []
        if res_equip["seguros_vencidos"] > 0:
            alertas.append(("err", f"🔴 {res_equip['seguros_vencidos']} equipamento(s) com seguro VENCIDO"))
        if res_os["os_atrasadas"] > 0:
            alertas.append(("warn", f"🟡 {res_os['os_atrasadas']} OS com prazo vencido e não concluída"))
        if res_equip["sem_num_patrimonial"] > 0:
            alertas.append(("warn", f"🟡 {res_equip['sem_num_patrimonial']} equipamento(s) sem número patrimonial"))
        if not alertas:
            alertas.append(("ok", "✅ Nenhum alerta crítico identificado no período"))
        for tipo, msg in alertas:
            st.markdown(f'<div class="alert-box {tipo}">{msg}</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erro ao carregar alertas: {e}")


# ─────────────────────────────────────────────
#  PÁGINA 3 — MANUTENÇÃO
# ─────────────────────────────────────────────
elif pagina == "🔧 Manutenção":
    st.markdown(f"""
    <div class="main-header">
        <h1>🔧 Manutenção</h1>
        <p>Ordens de serviço · {label_periodo}</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Carregando OS..."):
        try:
            os_lista = buscar_os(inicio, fim, filiais_ids=filiais_ids)
            res = resumir_os_manutencao(os_lista)

            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(kpi("Total OS", res["total_os"]), unsafe_allow_html=True)
            with c2: st.markdown(kpi("OS Atrasadas", res["os_atrasadas"],
                                     delta="⚠️ Ação necessária" if res["os_atrasadas"] > 0 else "✓ OK",
                                     delta_type="warn" if res["os_atrasadas"] > 0 else "up"),
                                 unsafe_allow_html=True)
            with c3:
                qtde_equip = len(res["top_10_equipamentos"])
                st.markdown(kpi("Equip. em OS", qtde_equip), unsafe_allow_html=True)
            with c4:
                qtde_def = len(res["top_10_defeitos"])
                st.markdown(kpi("Tipos de Defeito", qtde_def), unsafe_allow_html=True)

            st.divider()

            col_a, col_b = st.columns(2)

            with col_a:
                st.subheader("OS por Situação")
                if res["por_situacao"]:
                    df_sit = pd.DataFrame(list(res["por_situacao"].items()), columns=["Situação", "Qtde"])
                    fig = px.pie(df_sit, values="Qtde", names="Situação",
                                 color_discrete_sequence=px.colors.sequential.Blues_r,
                                 template="plotly_white")
                    fig.update_layout(margin=dict(t=10, b=10))
                    st.plotly_chart(fig, use_container_width=True)

            with col_b:
                st.subheader("Top 10 Defeitos Mais Frequentes")
                if res["top_10_defeitos"]:
                    df_def = pd.DataFrame(list(res["top_10_defeitos"].items()), columns=["Defeito", "Qtde"])
                    df_def = df_def.sort_values("Qtde", ascending=True)
                    fig2 = px.bar(df_def, x="Qtde", y="Defeito", orientation="h",
                                  color_discrete_sequence=["#2C5F9E"],
                                  template="plotly_white")
                    fig2.update_layout(margin=dict(t=10, b=10), showlegend=False)
                    st.plotly_chart(fig2, use_container_width=True)

            # OS Atrasadas
            if res["lista_atrasadas"]:
                st.subheader("⚠️ OS Atrasadas")
                df_atr = pd.DataFrame(res["lista_atrasadas"])
                df_atr.columns = ["ID", "Equipamento", "Defeito", "Prazo", "Situação"]
                st.dataframe(df_atr, use_container_width=True)

            # Tabela completa
            st.subheader("Todas as OS do Período")
            df_os = pd.DataFrame(os_lista)
            if not df_os.empty:
                colunas_os = [c for c in ["id", "dataAbertura", "dataPrevTermino",
                               "situacao", "tipo", "defeito", "causaProvavel"] if c in df_os.columns]
                if "equipamento" in df_os.columns:
                    df_os["equipamento_nome"] = df_os["equipamento"].apply(
                        lambda x: x.get("descricao", "") if isinstance(x, dict) else ""
                    )
                    colunas_os = ["id", "equipamento_nome"] + [c for c in colunas_os if c != "id"]

                filtro_os = st.text_input("🔍 Filtrar OS")
                df_show = df_os[colunas_os].copy()
                if filtro_os:
                    mask = df_show.apply(lambda row: row.astype(str).str.contains(filtro_os, case=False).any(), axis=1)
                    df_show = df_show[mask]
                st.dataframe(df_show, use_container_width=True, height=400)

        except Exception as e:
            st.error(f"Erro: {e}")


# ─────────────────────────────────────────────
#  PÁGINA 4 — FINANCEIRO
# ─────────────────────────────────────────────
elif pagina == "💳 Financeiro":
    st.markdown(f"""
    <div class="main-header">
        <h1>💳 Financeiro</h1>
        <p>Contas a pagar e receber · {label_periodo}</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Carregando transferências..."):
        try:
            trf = buscar_transferencias(inicio, fim, filiais_ids=filiais_ids)
            res = resumir_transferencias(trf)

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: st.markdown(kpi("Documentos", res["total_documentos"]), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Valor Total", fmt_brl(res["valor_total_emitido"])), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Valor Líquido", fmt_brl(res["valor_liquido_total"])), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Total Juros", fmt_brl(res["total_juros"]),
                                     delta="⚠️ Alto" if res["total_juros"] > 10000 else "Normal",
                                     delta_type="warn" if res["total_juros"] > 10000 else "up"),
                                 unsafe_allow_html=True)
            with c5: st.markdown(kpi("Ticket Médio", fmt_brl(res["ticket_medio"])), unsafe_allow_html=True)

            st.divider()

            col_a, col_b = st.columns(2)

            with col_a:
                st.subheader("Top 15 Fornecedores")
                if res["top_15_fornecedores"]:
                    df_forn = pd.DataFrame(res["top_15_fornecedores"])
                    df_forn["valor_fmt"] = df_forn["valor"].apply(fmt_brl)
                    fig = px.bar(df_forn.sort_values("valor"), x="valor", y="fornecedor",
                                 orientation="h", text="valor_fmt",
                                 color_discrete_sequence=["#1A3C6E"],
                                 template="plotly_white")
                    fig.update_layout(showlegend=False, margin=dict(t=10))
                    fig.update_traces(textposition="outside")
                    st.plotly_chart(fig, use_container_width=True)

            with col_b:
                st.subheader("Distribuição por Mês")
                if res["distribuicao_por_mes"]:
                    df_mes = pd.DataFrame(list(res["distribuicao_por_mes"].items()),
                                          columns=["Mês", "Qtde"])
                    df_mes = df_mes.sort_values("Mês")
                    fig2 = px.bar(df_mes, x="Mês", y="Qtde",
                                  color_discrete_sequence=["#2C5F9E"],
                                  template="plotly_white")
                    fig2.update_layout(margin=dict(t=10))
                    st.plotly_chart(fig2, use_container_width=True)

            # Tabela de transferências
            st.subheader("Lançamentos do Período")
            df_trf = pd.DataFrame(res["amostra_documentos"])
            if not df_trf.empty:
                if "fornecedor" in df_trf.columns:
                    df_trf["fornecedor_nome"] = df_trf["fornecedor"].apply(
                        lambda x: x.get("nomeRazao") or x.get("nomeFantasia", "") if isinstance(x, dict) else ""
                    )
                colunas_fin = [c for c in ["id", "fornecedor_nome", "numeroDocumento",
                               "dataEmissao", "valorTotalDocumento", "valorLiquido",
                               "valorJuros", "valorDesconto"] if c in df_trf.columns]
                st.dataframe(df_trf[colunas_fin], use_container_width=True, height=350)

        except Exception as e:
            st.error(f"Erro: {e}")


# ─────────────────────────────────────────────
#  PÁGINA 5 — COMPRAS
# ─────────────────────────────────────────────
elif pagina == "🛒 Compras":
    st.markdown(f"""
    <div class="main-header">
        <h1>🛒 Compras</h1>
        <p>Pipeline de requisições · {label_periodo}</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Carregando dados de compras..."):
        try:
            dados = buscar_compras(inicio, fim)
            res   = resumir_compras(dados)

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: st.markdown(kpi("Requisições", res["total_requisicoes"]), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Ordens de Compra", res["total_ocs"]), unsafe_allow_html=True)
            with c3: st.markdown(kpi("OCs Sem Processo", res["ocs_diretas_sem_req"],
                                     delta="⚠️ Auditar" if res["ocs_diretas_sem_req"] > 0 else "✓ OK",
                                     delta_type="warn" if res["ocs_diretas_sem_req"] > 0 else "up"),
                                 unsafe_allow_html=True)
            with c4: st.markdown(kpi("Valor Total", fmt_brl(res["valor_total_comprado"])), unsafe_allow_html=True)
            with c5: st.markdown(kpi("Frete %", fmt_pct(res["frete_pct"]),
                                     delta="⚠️ Alto" if res["frete_pct"] > 10 else "Normal",
                                     delta_type="warn" if res["frete_pct"] > 10 else "up"),
                                 unsafe_allow_html=True)

            st.divider()

            col_a, col_b = st.columns(2)

            with col_a:
                st.subheader("Top 15 Fornecedores")
                if res["top_15_fornecedores"]:
                    df_f = pd.DataFrame(res["top_15_fornecedores"])
                    df_f["valor_fmt"] = df_f["valor"].apply(fmt_brl)
                    fig = px.bar(df_f.sort_values("valor"), x="valor", y="fornecedor",
                                 orientation="h", text="valor_fmt",
                                 color_discrete_sequence=["#4A235A"],
                                 template="plotly_white")
                    fig.update_layout(showlegend=False, margin=dict(t=10))
                    st.plotly_chart(fig, use_container_width=True)

            with col_b:
                st.subheader("Composição do Valor")
                labels = ["Mercadorias", "Frete", "Desconto"]
                values = [res["valor_mercadorias"], res["valor_frete"],
                          abs(res["valor_desconto"])]
                fig2 = go.Figure(data=[go.Pie(
                    labels=labels, values=values,
                    marker_colors=["#1A3C6E", "#F39C12", "#0A6E3F"],
                    hole=0.4
                )])
                fig2.update_layout(margin=dict(t=10, b=10))
                st.plotly_chart(fig2, use_container_width=True)

            # OCs diretas
            if res["ocs_diretas_lista"]:
                st.subheader("⚠️ OCs Geradas Sem Requisição/Cotação")
                df_ocd = pd.DataFrame([
                    d.get("ordemCompraMestreResumida", d)
                    for d in res["ocs_diretas_lista"]
                ])
                if not df_ocd.empty:
                    if "fornecedorResumido" in df_ocd.columns:
                        df_ocd["fornecedor_nome"] = df_ocd["fornecedorResumido"].apply(
                            lambda x: x.get("nomeRazao", "") if isinstance(x, dict) else ""
                        )
                    colunas_ocd = [c for c in ["id", "fornecedor_nome", "dataOrdemCompra",
                                   "descricaoSituacao", "valorTotalCompras",
                                   "descricaoCondicaoPagamento"] if c in df_ocd.columns]
                    df_ocd_show = df_ocd[colunas_ocd].copy()
                    df_ocd_show = df_ocd_show.loc[:, ~df_ocd_show.columns.duplicated()]
                    st.dataframe(df_ocd_show, use_container_width=True)

        except Exception as e:
            st.error(f"Erro: {e}")


# ─────────────────────────────────────────────
#  PÁGINA 6 — MATERIAIS
# ─────────────────────────────────────────────
elif pagina == "🛍️ Vendas":
    st.markdown(f"""
    <div class="main-header">
        <h1>🛍️ Vendas</h1>
        <p>Pedidos, orçamentos e performance comercial · {label_periodo}</p>
    </div>
    """, unsafe_allow_html=True)

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        carregar_vendas = st.button("🔄 Carregar dados de Vendas", use_container_width=True)
    with col_info:
        st.caption("Clique para buscar os dados do período selecionado.")

    if not carregar_vendas and "vendas_pedidos" not in st.session_state:
        st.info("👆 Clique em **Carregar dados de Vendas** para buscar os pedidos do período.")
        st.stop()

    if carregar_vendas:
        with st.spinner("Buscando pedidos..."):
            st.session_state["vendas_pedidos"]    = buscar_pedidos(inicio, fim, filiais_ids=filiais_ids)
            try:
                st.session_state["vendas_orcamentos"] = buscar_orcamentos(inicio, fim)
            except Exception:
                st.session_state["vendas_orcamentos"] = []
                st.warning("⚠️ Orçamentos indisponíveis no momento — exibindo apenas pedidos.")
            st.session_state["vendas_periodo"]    = label_periodo

    with st.spinner("Processando..."):
        try:
            pedidos    = st.session_state.get("vendas_pedidos", [])
            orcamentos = st.session_state.get("vendas_orcamentos", [])

            from collections import Counter
            valor_total = sum(p.get("valorTotalPedido", 0) or 0 for p in pedidos)
            sit_pedidos = Counter(p.get("situacaoPedido", "?") for p in pedidos)
            sit_orc     = Counter(o.get("situacao", "?") for o in orcamentos)
            orc_aprov   = sit_orc.get("APROVADO", 0) + sit_orc.get("CONCLUIDO", 0)
            taxa_conv   = (orc_aprov / len(orcamentos) * 100) if orcamentos else 0
            if not orcamentos:
                st.info("ℹ️ Orçamentos temporariamente indisponíveis na API do CRTI.")

            # KPIs
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: st.markdown(kpi("Pedidos", len(pedidos)), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Valor Total", fmt_brl(valor_total)), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Ticket Médio", fmt_brl(valor_total/len(pedidos) if pedidos else 0)), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Orçamentos", len(orcamentos)), unsafe_allow_html=True)
            with c5: st.markdown(kpi("Conversão ORC→PED", fmt_pct(taxa_conv),
                                     delta="⚠️ Baixa" if taxa_conv < 30 else "✓ Boa",
                                     delta_type="warn" if taxa_conv < 30 else "up"),
                                 unsafe_allow_html=True)

            st.divider()
            col_a, col_b = st.columns(2)

            with col_a:
                st.subheader("Pedidos por Situação")
                if sit_pedidos:
                    df_sit = pd.DataFrame(list(sit_pedidos.items()), columns=["Situação", "Qtde"])
                    cores = {"CONCLUIDO":"#0A6E3F","APROVADO":"#2C5F9E",
                             "AGUARDANDO_APROVACAO":"#F39C12","CANCELADO":"#C0392B"}
                    fig = px.pie(df_sit, values="Qtde", names="Situação",
                                 color="Situação",
                                 color_discrete_map=cores,
                                 template="plotly_white")
                    fig.update_layout(margin=dict(t=10,b=10))
                    st.plotly_chart(fig, use_container_width=True)

            with col_b:
                st.subheader("Top 10 Clientes por Valor")
                clientes_val = Counter()
                for p in pedidos:
                    cli = (p.get("cliente") or {}).get("nomeRazao", "?")
                    clientes_val[cli] += p.get("valorTotalPedido", 0) or 0
                if clientes_val:
                    df_cli = pd.DataFrame(clientes_val.most_common(10), columns=["Cliente","Valor"])
                    df_cli["Valor_fmt"] = df_cli["Valor"].apply(fmt_brl)
                    fig2 = px.bar(df_cli.sort_values("Valor"), x="Valor", y="Cliente",
                                  orientation="h", text="Valor_fmt",
                                  color_discrete_sequence=["#1A3C6E"],
                                  template="plotly_white")
                    fig2.update_layout(showlegend=False, margin=dict(t=10))
                    st.plotly_chart(fig2, use_container_width=True)

            # Vendedores
            st.subheader("Performance por Vendedor")
            vend_val = Counter()
            for p in pedidos:
                v = (p.get("vendedorPedido") or {}).get("nomeVendedor", "Sem vendedor")
                vend_val[v] += p.get("valorTotalPedido", 0) or 0
            if vend_val:
                df_vend = pd.DataFrame(vend_val.most_common(), columns=["Vendedor","Valor"])
                df_vend["Valor_fmt"] = df_vend["Valor"].apply(fmt_brl)
                df_vend["%"] = (df_vend["Valor"] / df_vend["Valor"].sum() * 100).round(1).astype(str) + "%"
                st.dataframe(df_vend, use_container_width=True, hide_index=True)

            # Tabela de pedidos
            st.subheader("Pedidos do Período")
            if pedidos:
                df_ped = pd.DataFrame(pedidos)
                if "cliente" in df_ped.columns:
                    df_ped["cliente_nome"] = df_ped["cliente"].apply(
                        lambda x: x.get("nomeRazao","") if isinstance(x,dict) else "")
                if "vendedorPedido" in df_ped.columns:
                    df_ped["vendedor"] = df_ped["vendedorPedido"].apply(
                        lambda x: x.get("nomeVendedor","") if isinstance(x,dict) else "")
                cols = [c for c in ["id","cliente_nome","dataPedido","situacaoPedido",
                                    "valorTotalPedido","vendedor","tipoFrete"] if c in df_ped.columns]
                filtro_v = st.text_input("🔍 Filtrar pedidos")
                df_show = df_ped[cols].copy()
                if filtro_v:
                    mask = df_show.apply(lambda r: r.astype(str).str.contains(filtro_v, case=False).any(), axis=1)
                    df_show = df_show[mask]
                st.dataframe(df_show, use_container_width=True, height=350)

        except Exception as e:
            st.error(f"Erro: {e}")


elif pagina == "👥 Clientes Inativos":
    st.markdown("""
    <div class="main-header">
        <h1>👥 Clientes Inativos</h1>
        <p>Clientes que pararam de comprar — análise e estratégia de reativação</p>
    </div>
    """, unsafe_allow_html=True)

    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        dias_inativo = st.slider("Considerar inativo após X dias sem comprar", 30, 180, 60, 10)
    with col_cfg2:
        st.caption(f"Analisando histórico dos últimos 365 dias")

    col_btn2, col_aviso = st.columns([1, 3])
    with col_btn2:
        carregar_inativos = st.button("🔍 Analisar Carteira", use_container_width=True)
    with col_aviso:
        st.caption("⏱️ Esta análise busca 365 dias de histórico — pode levar 30-60 segundos.")

    if not carregar_inativos and "clientes_inativos_data" not in st.session_state:
        st.info("👆 Clique em **Analisar Carteira** para identificar clientes inativos.")
        st.stop()

    if carregar_inativos:
        with st.spinner("Analisando 365 dias de histórico... aguarde..."):
            st.session_state["clientes_inativos_data"] = buscar_clientes_inativos_cache(dias=dias_inativo)

    with st.spinner("Processando..."):
        try:
            dados = st.session_state.get("clientes_inativos_data", {})
            resumo   = dados["resumo"]
            inativos = dados["inativos"]
            ativos   = dados["ativos_recentes"]

            # KPIs
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(kpi("Total Clientes", resumo["total_clientes"]), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Inativos", resumo["inativos"],
                                     delta=f"⚠️ {resumo['pct_inativo']}% da carteira",
                                     delta_type="warn"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Ativos", resumo["ativos"],
                                     delta="✓ Compraram recentemente",
                                     delta_type="up"), unsafe_allow_html=True)
            valor_risco = sum(c.get("total_historico",0) for c in inativos)
            with c4: st.markdown(kpi("Receita em Risco", fmt_brl(valor_risco),
                                     delta="⚠️ Valor histórico inativos",
                                     delta_type="warn"), unsafe_allow_html=True)

            st.divider()

            # Gráfico de inatividade
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Distribuição por Tempo Inativo")
                if inativos:
                    bins = {"60-90 dias":0, "90-120 dias":0, "120-180 dias":0, "+180 dias":0}
                    for c in inativos:
                        d = c["dias_sem_comprar"]
                        if d <= 90:   bins["60-90 dias"] += 1
                        elif d <= 120: bins["90-120 dias"] += 1
                        elif d <= 180: bins["120-180 dias"] += 1
                        else:          bins["+180 dias"] += 1
                    df_bins = pd.DataFrame(list(bins.items()), columns=["Período","Qtde"])
                    fig = px.bar(df_bins, x="Período", y="Qtde",
                                 color="Qtde",
                                 color_continuous_scale=["#FFF3CD","#C0392B"],
                                 template="plotly_white")
                    fig.update_layout(showlegend=False, margin=dict(t=10))
                    st.plotly_chart(fig, use_container_width=True)

            with col_b:
                st.subheader("Valor em Risco por Grupo")
                if inativos:
                    grupos = {"60-90 dias":0,"90-120 dias":0,"120-180 dias":0,"+180 dias":0}
                    for c in inativos:
                        d = c["dias_sem_comprar"]
                        v = c["total_historico"]
                        if d <= 90:    grupos["60-90 dias"] += v
                        elif d <= 120: grupos["90-120 dias"] += v
                        elif d <= 180: grupos["120-180 dias"] += v
                        else:          grupos["+180 dias"] += v
                    df_g = pd.DataFrame(list(grupos.items()), columns=["Grupo","Valor"])
                    fig2 = px.pie(df_g, values="Valor", names="Grupo",
                                  color_discrete_sequence=["#F39C12","#E67E22","#E74C3C","#C0392B"],
                                  template="plotly_white")
                    fig2.update_layout(margin=dict(t=10))
                    st.plotly_chart(fig2, use_container_width=True)

            # Tabela de inativos
            st.subheader("🔴 Lista de Clientes Inativos")
            if inativos:
                df_inat = pd.DataFrame(inativos)
                df_inat["total_historico"] = df_inat["total_historico"].apply(fmt_brl)
                df_inat["ticket_medio"]    = df_inat["ticket_medio"].apply(fmt_brl)
                df_inat.columns = [c.replace("nome","Cliente").replace("ultima_compra","Último Pedido")
                                    .replace("dias_sem_comprar","Dias Inativo")
                                    .replace("total_historico","Total Histórico")
                                    .replace("qtde_pedidos","Qtde Pedidos")
                                    .replace("ticket_medio","Ticket Médio")
                                    for c in df_inat.columns]
                cols_show = [c for c in ["Cliente","Último Pedido","Dias Inativo",
                                          "Total Histórico","Qtde Pedidos","Ticket Médio"]
                             if c in df_inat.columns]
                st.dataframe(df_inat[cols_show], use_container_width=True, height=400)

                # Download
                csv = df_inat[cols_show].to_csv(index=False).encode("utf-8-sig")
                st.download_button("⬇️ Exportar lista para Excel/CSV",
                                   data=csv, file_name="clientes_inativos.csv",
                                   mime="text/csv")

        except Exception as e:
            st.error(f"Erro: {e}")


elif pagina == "📦 Materiais":
    st.markdown("""
    <div class="main-header">
        <h1>📦 Materiais e Suprimentos</h1>
        <p>Cadastro, qualidade de dados e controle de estoque</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Carregando materiais..."):
        try:
            materiais = buscar_materiais()
            res = resumir_materiais(materiais)

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: st.markdown(kpi("Total", res["total_materiais"]), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Ativos", res["ativos"]), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Sem NCM", res["sem_ncm"],
                                     delta="⚠️ Risco fiscal" if res["sem_ncm"] > 0 else "✓ OK",
                                     delta_type="warn" if res["sem_ncm"] > 0 else "up"),
                                 unsafe_allow_html=True)
            with c4: st.markdown(kpi("Sem Preço", res["sem_preco"],
                                     delta="⚠️ Incompleto" if res["sem_preco"] > 0 else "✓ OK",
                                     delta_type="warn" if res["sem_preco"] > 0 else "up"),
                                 unsafe_allow_html=True)
            with c5: st.markdown(kpi("Completude", fmt_pct(res["completude_pct"])), unsafe_allow_html=True)

            st.divider()

            col_a, col_b = st.columns(2)

            with col_a:
                st.subheader("Materiais por Grupo")
                if res["por_grupo"]:
                    df_g = pd.DataFrame(list(res["por_grupo"].items()), columns=["Grupo", "Qtde"])
                    df_g = df_g.sort_values("Qtde", ascending=False).head(10)
                    fig = px.bar(df_g, x="Qtde", y="Grupo", orientation="h",
                                 color_discrete_sequence=["#0A6E3F"],
                                 template="plotly_white")
                    fig.update_layout(yaxis=dict(categoryorder="total ascending"),
                                      showlegend=False, margin=dict(t=10))
                    st.plotly_chart(fig, use_container_width=True)

            with col_b:
                st.subheader("Problemas no Cadastro")
                df_prob = pd.DataFrame({
                    "Problema": ["Sem NCM", "Sem preço", "Sem grupo", "Sem EAN", "Inativos"],
                    "Qtde": [res["sem_ncm"], res["sem_preco"], res["sem_grupo"],
                              res["sem_ean"], res["inativos"]]
                })
                fig2 = px.bar(df_prob, x="Qtde", y="Problema", orientation="h",
                               color="Qtde",
                               color_continuous_scale=["#FFF3CD", "#C0392B"],
                               template="plotly_white")
                fig2.update_layout(showlegend=False, margin=dict(t=10))
                st.plotly_chart(fig2, use_container_width=True)

        except Exception as e:
            st.error(f"Erro: {e}")


# ─────────────────────────────────────────────
#  PÁGINA 7 — GERAR RELATÓRIO COM IA
# ─────────────────────────────────────────────
elif pagina == "🤖 Gerar Relatório com IA":
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Gerar Relatório com IA</h1>
        <p>O Claude analisa os dados e escreve um relatório executivo completo em PDF</p>
    </div>
    """, unsafe_allow_html=True)

    # Seleção do relatório
    col_sel, col_info = st.columns([1, 2])

    with col_sel:
        tipo_relatorio = st.selectbox(
            "Tipo de Relatório",
            options=[
                "🛍️ Análise de Vendas",
                "👥 Clientes Inativos — Estratégia de Reativação",
                "🚜 Auditoria de Frota",
                "🔧 Relatório de Manutenção",
                "📋 Patrimônio da Frota",
                "💳 Auditoria Financeira",
                "💳 Análise Financeira Mensal",
                "🛒 Auditoria de Compras",
                "🛒 Relatório Gerencial de Compras",
                "📦 Auditoria de Materiais",
            ]
        )

        st.caption(f"📅 Período: **{label_periodo}**")

        gerar = st.button("🚀 Gerar Relatório Agora", use_container_width=True)

    with col_info:
        descricoes = {
            "🛍️ Análise de Vendas": "Analisa pedidos e orçamentos do período: volume, top clientes, ranking de vendedores, materiais mais vendidos, taxa de conversão orçamento→pedido.",
            "👥 Clientes Inativos — Estratégia de Reativação": "Identifica clientes que compraram no histórico mas pararam. Classifica por urgência e sugere estratégia de reativação para cada grupo.",
            "🚜 Auditoria de Frota": "Analisa 1.309 equipamentos, OS abertas, transferências e seguros. Detecta seguros vencidos, OS atrasadas, anormalidades em transferências e gera score de saúde da frota.",
            "🔧 Relatório de Manutenção": "Analisa OS do período: taxa de conclusão no prazo, defeitos mais frequentes, equipamentos com mais paradas e eficiência da equipe.",
            "📋 Patrimônio da Frota": "Inventário patrimonial completo: depreciação por grupo, cobertura de seguros, equipamentos próprios vs terceiros, candidatos a baixa.",
            "💳 Auditoria Financeira": "Analisa transferências buscando duplicatas, valores atípicos, concentração de fornecedores e inconsistências. Gera score de risco.",
            "💳 Análise Financeira Mensal": "Visão do CFO: total movimentado, fluxo de caixa, posição bancária, ticket médio e recomendações estratégicas.",
            "🛒 Auditoria de Compras": "Audita o pipeline completo: OCs sem processo, compras diretas sem cotação, favorecimento de fornecedor, materiais não entregues.",
            "🛒 Relatório Gerencial de Compras": "Visão gerencial: volume, top fornecedores, frete %, descontos obtidos, lead times.",
            "📦 Auditoria de Materiais": "Qualidade do cadastro: NCM ausente, sem preço, sem grupo, score de completude e lista dos itens mais incompletos.",
        }
        st.info(descricoes.get(tipo_relatorio, ""))

    st.divider()

    # Gerar relatório
    if gerar:
        from Prompts.prompts import (
            prompt_auditoria_frota, prompt_relatorio_manutencao,
            prompt_relatorio_patrimonio_frota, prompt_auditoria_financeira,
            prompt_analise_financeira_mensal, prompt_auditoria_compras,
            prompt_relatorio_compras_gerencial, prompt_auditoria_materiais
        )

        progresso = st.progress(0)
        status    = st.status("Iniciando...", expanded=True)
        crti_cli  = get_crti()
        claude    = get_claude()
        pdf_gen   = get_pdf()

        try:
            with status:
                # Coleta de dados
                st.write("📡 Buscando dados do CRTI ERP...")
                progresso.progress(15)

                if "Análise de Vendas" in tipo_relatorio:
                    from Prompts.prompts import prompt_analise_vendas
                    pedidos    = get_crti().buscar_pedidos_material(inicio, fim)
                    orcamentos = get_crti().buscar_orcamentos_venda(inicio, fim)
                    prompt     = prompt_analise_vendas(pedidos, orcamentos, label_periodo)
                    tipo_pdf, titulo = "vendas", "Análise de Vendas"
                elif "Clientes Inativos" in tipo_relatorio:
                    from Prompts.prompts import prompt_clientes_inativos
                    dados  = get_crti().buscar_clientes_inativos(dias_sem_comprar=60)
                    prompt = prompt_clientes_inativos(dados)
                    tipo_pdf, titulo = "clientes_inativos", "Clientes Inativos — Estratégia de Reativação"
                elif "Frota" in tipo_relatorio and "Patrimônio" not in tipo_relatorio:
                    dados = crti_cli.buscar_dados_frota_completos(inicio, fim)
                    prompt = prompt_auditoria_frota(dados, label_periodo)
                    tipo_pdf, titulo = "auditoria_frota", "Auditoria de Frota"
                elif "Manutenção" in tipo_relatorio:
                    os_lista = crti_cli.buscar_os_manutencao(data_abertura_de=inicio, data_abertura_ate=fim)
                    prompt = prompt_relatorio_manutencao(os_lista, label_periodo)
                    tipo_pdf, titulo = "manutencao", "Relatório de Manutenção"
                elif "Patrimônio" in tipo_relatorio:
                    equip = crti_cli.buscar_equipamentos()
                    prompt = prompt_relatorio_patrimonio_frota(equip)
                    tipo_pdf, titulo = "patrimonio_frota", "Inventário Patrimonial da Frota"
                elif "Auditoria Financeira" in tipo_relatorio:
                    dados = crti_cli.buscar_dados_auditoria(inicio, fim)
                    prompt = prompt_auditoria_financeira(dados, label_periodo)
                    tipo_pdf, titulo = "auditoria", "Auditoria Financeira"
                elif "Mensal" in tipo_relatorio:
                    dados = crti_cli.buscar_dados_financeiros(inicio, fim)
                    prompt = prompt_analise_financeira_mensal(dados, label_periodo)
                    tipo_pdf, titulo = "mensal", "Análise Financeira Mensal"
                elif "Auditoria de Compras" in tipo_relatorio:
                    dados = crti_cli.buscar_compras_periodo(inicio, fim)
                    prompt = prompt_auditoria_compras(dados, label_periodo)
                    tipo_pdf, titulo = "auditoria_compras", "Auditoria de Compras"
                elif "Gerencial de Compras" in tipo_relatorio:
                    dados = crti_cli.buscar_compras_periodo(inicio, fim)
                    prompt = prompt_relatorio_compras_gerencial(dados, label_periodo)
                    tipo_pdf, titulo = "relatorio_compras", "Relatório Gerencial de Compras"
                elif "Materiais" in tipo_relatorio:
                    mats = crti_cli.buscar_materiais(apenas_ativos=False)
                    prompt = prompt_auditoria_materiais(mats)
                    tipo_pdf, titulo = "materiais", "Auditoria de Materiais"

                progresso.progress(40)
                st.write("🤖 Claude está analisando os dados...")

                analise = claude.analisar(prompt)
                progresso.progress(80)

                st.write("📄 Gerando PDF...")
                caminho = pdf_gen.gerar_pdf(
                    titulo=titulo,
                    analise=analise,
                    tipo=tipo_pdf,
                    subtitulo=f"Período: {label_periodo}"
                )
                progresso.progress(100)
                st.write("✅ Relatório gerado com sucesso!")

            # Resultado
            st.success(f"✅ **{titulo}** gerado com sucesso!")

            col_down, col_prev = st.columns([1, 2])

            with col_down:
                with open(caminho, "rb") as f:
                    st.download_button(
                        label="⬇️ Baixar PDF",
                        data=f.read(),
                        file_name=os.path.basename(caminho),
                        mime="application/pdf",
                        use_container_width=True
                    )

            with col_prev:
                st.subheader("📋 Prévia da Análise")
                st.markdown(analise[:3000] + ("..." if len(analise) > 3000 else ""))

        except Exception as e:
            st.error(f"❌ Erro ao gerar relatório: {e}")
            st.exception(e)
