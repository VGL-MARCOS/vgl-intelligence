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
@st.cache_data(ttl=300, show_spinner=False)  # cache por 5 minutos
def buscar_equipamentos():
    return get_crti().buscar_equipamentos()

@st.cache_data(ttl=300, show_spinner=False)
def buscar_os(inicio, fim):
    return get_crti().buscar_os_manutencao(data_abertura_de=inicio, data_abertura_ate=fim)

@st.cache_data(ttl=300, show_spinner=False)
def buscar_transferencias(inicio, fim):
    return get_crti().buscar_transferencias(inicio, fim)

@st.cache_data(ttl=300, show_spinner=False)
def buscar_compras(inicio, fim):
    return get_crti().buscar_compras_periodo(inicio, fim)

@st.cache_data(ttl=300, show_spinner=False)
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
    tipo_periodo = st.radio(
        "Tipo",
        ["Mês atual", "Mês anterior", "Últimos 7 dias", "Personalizado"],
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
    else:
        inicio, fim = Periodos.ultimos_7_dias()

    label_periodo = Periodos.formatar_label(inicio, fim)
    st.caption(f"📆 {label_periodo}")

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

    with st.spinner("Carregando dados..."):
        try:
            equipamentos = buscar_equipamentos()
            os_lista     = buscar_os(inicio, fim)
            trf          = buscar_transferencias(inicio, fim)

            res_equip = resumir_equipamentos(equipamentos)
            res_os    = resumir_os_manutencao(os_lista)
            res_trf   = resumir_transferencias(trf)

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

            # ── Alertas ──
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
            st.error(f"Erro ao carregar dados: {e}")


# ─────────────────────────────────────────────
#  PÁGINA 2 — FROTA
# ─────────────────────────────────────────────
elif pagina == "🚜 Frota e Equipamentos":
    st.markdown("""
    <div class="main-header">
        <h1>🚜 Frota e Equipamentos</h1>
        <p>Patrimônio, localização, seguros e horímetros</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Carregando equipamentos..."):
        try:
            equipamentos = buscar_equipamentos()
            res = resumir_equipamentos(equipamentos)

            # KPIs
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: st.markdown(kpi("Total Equip.", res["total_equipamentos"]), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Valor Aquisição", f"R$ {res['valor_aquisicao_total']/1e6:.1f}M"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Depreciação", fmt_pct(res["depreciacao_pct"]),
                                     delta="Alto" if res["depreciacao_pct"] > 60 else "Normal",
                                     delta_type="warn" if res["depreciacao_pct"] > 60 else "up"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Seguros Vencidos", res["seguros_vencidos"],
                                     delta="⚠️ Urgente" if res["seguros_vencidos"] > 0 else "✓ OK",
                                     delta_type="warn" if res["seguros_vencidos"] > 0 else "up"), unsafe_allow_html=True)
            with c5: st.markdown(kpi("De Terceiros", res["de_subempreiteiros"]), unsafe_allow_html=True)

            st.divider()

            col_a, col_b = st.columns(2)

            with col_a:
                st.subheader("Equipamentos por Grupo")
                if res["por_grupo"]:
                    df_grp = pd.DataFrame(list(res["por_grupo"].items()), columns=["Grupo", "Qtde"])
                    df_grp = df_grp.sort_values("Qtde", ascending=False).head(12)
                    fig = px.bar(df_grp, x="Qtde", y="Grupo", orientation="h",
                                 color="Qtde", color_continuous_scale=["#BDD0F0", "#1A3C6E"],
                                 template="plotly_white")
                    fig.update_layout(yaxis=dict(categoryorder="total ascending"),
                                      showlegend=False, margin=dict(t=10, b=10))
                    st.plotly_chart(fig, use_container_width=True)

            with col_b:
                st.subheader("Seguros Vencidos ⚠️")
                if res["lista_seguros_vencidos"]:
                    df_seg = pd.DataFrame(res["lista_seguros_vencidos"])
                    df_seg = df_seg[["descricao", "placa", "vencimento", "valor_cobertura"]].copy()
                    df_seg.columns = ["Equipamento", "Placa", "Vencimento", "Cobertura R$"]
                    df_seg["Cobertura R$"] = df_seg["Cobertura R$"].apply(
                        lambda v: fmt_brl(v) if v else "—"
                    )
                    st.dataframe(df_seg, use_container_width=True, height=300)
                else:
                    st.success("✅ Nenhum seguro vencido!")

            # Tabela completa
            st.subheader("Cadastro de Equipamentos")
            df_equip = pd.DataFrame(equipamentos)
            colunas = ["id", "descricao", "apelido", "placa", "descricaoGrupoEquipamento",
                       "nomeFilialAtual", "ultimoHorometroOdometro", "valorAquisicao",
                       "valorMercado", "vencimentoSeguro", "situacao"]
            colunas_existentes = [c for c in colunas if c in df_equip.columns]
            df_show = df_equip[colunas_existentes].copy()
            df_show.columns = [c.replace("descricaoGrupoEquipamento", "Grupo")
                                 .replace("nomeFilialAtual", "Filial")
                                 .replace("ultimoHorometroOdometro", "Horímetro")
                                 .replace("valorAquisicao", "Vl. Aquisição")
                                 .replace("valorMercado", "Vl. Mercado")
                                 .replace("vencimentoSeguro", "Seguro")
                                 for c in colunas_existentes]

            filtro = st.text_input("🔍 Filtrar por nome ou placa")
            if filtro:
                mask = df_show.apply(lambda row: row.astype(str).str.contains(filtro, case=False).any(), axis=1)
                df_show = df_show[mask]

            st.dataframe(df_show, use_container_width=True, height=400)

        except Exception as e:
            st.error(f"Erro: {e}")


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
            os_lista = buscar_os(inicio, fim)
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
            trf = buscar_transferencias(inicio, fim)
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
        from prompts.prompts import (
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

                if "Frota" in tipo_relatorio and "Patrimônio" not in tipo_relatorio:
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
