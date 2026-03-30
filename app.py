"""
CRTI Intelligence — App Web
Britagem Vogelsanger LTDA
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from collections import Counter
import sys, os, logging

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="CRTI Intelligence | Vogelsanger",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #1A3C6E 0%, #2C5F9E 100%);
    padding: 1.2rem 1.5rem; border-radius: 12px; color: white; margin-bottom: 1rem;
}
.main-header h1 { color: white; margin: 0; font-size: 1.5rem; }
.main-header p  { color: #BDD0F0; margin: 0.2rem 0 0; font-size: 0.85rem; }
.kpi-card {
    background: white; border: 1px solid #E0E8F5; border-radius: 10px;
    padding: 0.8rem 0.6rem; text-align: center;
    box-shadow: 0 2px 8px rgba(26,60,110,0.07); height: 100%;
}
.kpi-value { font-size: 1.5rem; font-weight: 700; color: #1A3C6E; line-height: 1.2; }
.kpi-label { font-size: 0.75rem; color: #888; margin-top: 0.2rem; }
.kpi-delta { font-size: 0.75rem; margin-top: 0.2rem; }
.kpi-delta.up   { color: #0A6E3F; }
.kpi-delta.warn { color: #F39C12; }
.kpi-delta.down { color: #C0392B; }
.alert-box { border-left: 4px solid #C0392B; background: #FDECEA;
    padding: 0.7rem 0.8rem; border-radius: 0 8px 8px 0; margin: 0.3rem 0; font-size: 0.9rem; }
.alert-box.warn { background: #FFF3CD; border-left-color: #F39C12; }
.alert-box.ok   { background: #E8F5EE; border-left-color: #0A6E3F; }
.status-ok   { background:#E8F5EE; color:#0A6E3F; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600; }
.status-warn { background:#FFF3CD; color:#F39C12; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600; }
.status-err  { background:#FDECEA; color:#C0392B; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600; }
.stButton > button { background:#1A3C6E; color:white; border:none; border-radius:8px;
    padding:0.5rem 1rem; font-weight:600; width:100%; }
.stButton > button:hover { background:#2C5F9E; }
#MainMenu { visibility: hidden; } footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ──
def fmt_brl(v):
    try:    return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except: return "R$ —"

def fmt_pct(v):
    try:    return f"{float(v):.1f}%"
    except: return "—"

def kpi(label, value, delta=None, delta_type="ok"):
    d = f'<div class="kpi-delta {delta_type}">{delta}</div>' if delta else ""
    return f'<div class="kpi-card"><div class="kpi-value">{value}</div><div class="kpi-label">{label}</div>{d}</div>'

# ── Conexões (singleton) ──
@st.cache_resource(show_spinner=False)
def get_crti():
    from modules.crti_client import CRTIClient
    return CRTIClient()

@st.cache_resource(show_spinner=False)
def get_claude():
    from modules.claude_analyzer import ClaudeAnalyzer
    return ClaudeAnalyzer()

@st.cache_resource(show_spinner=False)
def get_pdf():
    from modules.report_generator import ReportGenerator
    return ReportGenerator()

# ── Cache de dados ──
@st.cache_data(ttl=300, show_spinner=False)
def _info_empresa():
    return get_crti().buscar_info_empresa()

@st.cache_data(ttl=1800, show_spinner=False)
def _equipamentos():
    return get_crti().buscar_equipamentos()

@st.cache_data(ttl=600, show_spinner=False)
def _os(inicio, fim):
    return get_crti().buscar_os_manutencao(data_abertura_de=inicio, data_abertura_ate=fim)

@st.cache_data(ttl=600, show_spinner=False)
def _transferencias(inicio, fim):
    return get_crti().buscar_transferencias(inicio, fim)

@st.cache_data(ttl=600, show_spinner=False)
def _compras(inicio, fim):
    return get_crti().buscar_compras_periodo(inicio, fim)

@st.cache_data(ttl=300, show_spinner=False)  # 5 min - dados limitados a 200
def _pedidos(inicio, fim):
    return get_crti().buscar_pedidos_material(data_inicio=inicio, data_fim=fim)

@st.cache_data(ttl=600, show_spinner=False)
def _orcamentos(inicio, fim):
    try:    return get_crti().buscar_orcamentos_venda(data_inicio=inicio, data_fim=fim)
    except: return []

@st.cache_data(ttl=1800, show_spinner=False)
def _materiais():
    return get_crti().buscar_materiais(apenas_ativos=False)

@st.cache_data(ttl=3600, show_spinner=False)  # 1 hora - busca pesada
def _clientes_inativos(dias):
    return get_crti().buscar_clientes_inativos(dias_sem_comprar=dias)

# ── Períodos ──
def resolver_periodo(tipo, data_ini=None, data_fim=None):
    from modules.periodos import Periodos
    hoje = datetime.now()
    if tipo == "Mês atual":        return Periodos.mes_atual()
    if tipo == "Mês anterior":     return Periodos.mes_anterior()
    if tipo == "Últimos 7 dias":   return Periodos.ultimos_7_dias()
    if tipo == "Últimos 30 dias":  return Periodos.ultimos_30_dias()
    if tipo == "Últimos 3 meses":  return Periodos.ultimos_n_meses(3)
    if tipo == "Últimos 6 meses":  return Periodos.ultimos_n_meses(6)
    if tipo == "Ano atual":        return Periodos.ano_atual()
    if tipo == "Personalizado" and data_ini and data_fim:
        return data_ini.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d")
    return Periodos.mes_atual()

def fmt_label(inicio, fim):
    fi = datetime.strptime(inicio, "%Y-%m-%d").strftime("%d/%m/%Y")
    ff = datetime.strptime(fim,    "%Y-%m-%d").strftime("%d/%m/%Y")
    return fi if inicio == fim else f"{fi} a {ff}"

# ════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:0.5rem 0 1rem;">
        <div style="font-size:2rem;">📊</div>
        <div style="font-weight:700;color:#1A3C6E;font-size:1.1rem;">CRTI Intelligence</div>
        <div style="color:#888;font-size:0.8rem;">Britagem Vogelsanger</div>
    </div>""", unsafe_allow_html=True)

    st.divider()

    pagina = st.selectbox("📍 Módulo", [
        "🏠 Painel Geral",
        "🛍️ Vendas",
        "👥 Clientes Inativos",
        "🚜 Frota e Equipamentos",
        "🔧 Manutenção",
        "💳 Financeiro",
        "🛒 Compras",
        "📦 Materiais",
        "🤖 Gerar Relatório com IA",
    ])

    st.divider()

    # Período
    st.markdown("**📅 Período**")
    tipo_periodo = st.selectbox("Período", [
        "Mês atual", "Mês anterior", "Últimos 7 dias",
        "Últimos 30 dias", "Últimos 3 meses",
        "Últimos 6 meses", "Ano atual", "Personalizado",
    ], label_visibility="collapsed")

    data_ini_custom = data_fim_custom = None
    if tipo_periodo == "Personalizado":
        c1, c2 = st.columns(2)
        with c1: data_ini_custom = st.date_input("Início", value=datetime.now().replace(day=1))
        with c2: data_fim_custom = st.date_input("Fim",    value=datetime.now())

    inicio, fim = resolver_periodo(tipo_periodo, data_ini_custom, data_fim_custom)
    label_periodo = fmt_label(inicio, fim)
    st.caption(f"📆 {label_periodo}")

    st.divider()

    # Filial — carrega APENAS quando o usuário expandir
    with st.expander("🏭 Filtrar por Filial"):
        filiais_ids = None
        if st.button("Carregar filiais", key="btn_filiais"):
            st.session_state["filiais_carregadas"] = True

        if st.session_state.get("filiais_carregadas"):
            try:
                equip = _equipamentos()
                fd = {}
                for e in equip:
                    fid = e.get("idFilialAtual")
                    fnome = e.get("nomeFilialAtual","")
                    if fid and fnome: fd[fid] = fnome
                fd = dict(sorted(fd.items(), key=lambda x: x[1]))

                if fd:
                    sel = st.multiselect("Filiais", sorted(fd.values()),
                                         placeholder="Todas", label_visibility="collapsed")
                    filiais_ids = [k for k,v in fd.items() if v in sel] or None
                    if filiais_ids:
                        st.caption(f"🏭 {len(filiais_ids)} filial(is)")
            except Exception as ex:
                st.caption(f"Erro: {ex}")
        else:
            st.caption("Clique para carregar filiais")

    st.divider()

    # Status
    st.markdown("**🔌 Status**")
    try:
        info = _info_empresa()
        emp  = info.get("nomeEmpresa","")[:20]
        st.markdown(f'<span class="status-ok">✓ {emp}</span>', unsafe_allow_html=True)
    except:
        st.markdown('<span class="status-warn">⚠ Conectando...</span>', unsafe_allow_html=True)

    st.caption(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.session_state.pop("filiais_carregadas", None)
        st.rerun()


# ════════════════════════════════════════
#  PAINEL GERAL
# ════════════════════════════════════════
if pagina == "🏠 Painel Geral":
    st.markdown(f"""<div class="main-header">
        <h1>📊 Painel Executivo</h1>
        <p>Visão consolidada · {label_periodo}</p></div>""", unsafe_allow_html=True)

    with st.spinner("Carregando dados..."):
        try:
            from modules.resumidor import resumir_equipamentos, resumir_os_manutencao, resumir_transferencias
            equip = _equipamentos()
            os_l  = _os(inicio, fim)
            trf   = _transferencias(inicio, fim)
            re    = resumir_equipamentos(equip)
            ro    = resumir_os_manutencao(os_l)
            rt    = resumir_transferencias(trf)

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.markdown(kpi("Equipamentos", re["total_equipamentos"]), unsafe_allow_html=True)
            with c2: st.markdown(kpi("OS no Período", ro["total_os"],
                delta=f"⚠️ {ro['os_atrasadas']} atrasadas" if ro["os_atrasadas"] else "✓ OK",
                delta_type="warn" if ro["os_atrasadas"] else "up"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Seguros Vencidos", re["seguros_vencidos"],
                delta="⚠️ Urgente" if re["seguros_vencidos"] else "✓ OK",
                delta_type="warn" if re["seguros_vencidos"] else "up"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Docs Financeiros", rt["total_documentos"]), unsafe_allow_html=True)
            with c5: st.markdown(kpi("Valor Período", fmt_brl(rt["valor_total_emitido"])), unsafe_allow_html=True)

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("OS por Situação")
                if ro["por_situacao"]:
                    df = pd.DataFrame(list(ro["por_situacao"].items()), columns=["Situação","Qtde"])
                    fig = px.bar(df, x="Situação", y="Qtde", color="Qtde",
                                 color_continuous_scale=["#BDD0F0","#1A3C6E"], template="plotly_white")
                    fig.update_layout(showlegend=False, margin=dict(t=10,b=10))
                    st.plotly_chart(fig, use_container_width=True)
            with cb:
                st.subheader("Top 10 Fornecedores")
                if rt["top_15_fornecedores"]:
                    df2 = pd.DataFrame(rt["top_15_fornecedores"][:10])
                    df2["vf"] = df2["valor"].apply(fmt_brl)
                    fig2 = px.bar(df2, x="valor", y="fornecedor", orientation="h",
                                  text="vf", color_discrete_sequence=["#1A3C6E"], template="plotly_white")
                    fig2.update_layout(showlegend=False, margin=dict(t=10))
                    st.plotly_chart(fig2, use_container_width=True)

            st.subheader("⚠️ Alertas")
            alertas = []
            if re["seguros_vencidos"]:   alertas.append(("err",  f"🔴 {re['seguros_vencidos']} seguro(s) vencido(s)"))
            if ro["os_atrasadas"]:       alertas.append(("warn", f"🟡 {ro['os_atrasadas']} OS com prazo vencido"))
            if re["sem_num_patrimonial"]:alertas.append(("warn", f"🟡 {re['sem_num_patrimonial']} equip. sem nº patrimonial"))
            if not alertas:              alertas.append(("ok",   "✅ Nenhum alerta crítico"))
            for t, m in alertas:
                st.markdown(f'<div class="alert-box {t}">{m}</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Erro: {e}")


# ════════════════════════════════════════
#  VENDAS
# ════════════════════════════════════════
elif pagina == "🛍️ Vendas":
    st.markdown(f"""<div class="main-header">
        <h1>🛍️ Vendas</h1>
        <p>Pedidos e orçamentos · {label_periodo} · máx 200 registros</p></div>""", unsafe_allow_html=True)

    c_btn, c_info = st.columns([1,3])
    with c_btn:
        carregar = st.button("🔄 Carregar Vendas", use_container_width=True)
    with c_info:
        st.caption("⚡ Carrega até 200 pedidos mais recentes do período.")

    if carregar or "v_pedidos" in st.session_state:
        if carregar:
            with st.spinner("Buscando pedidos..."):
                st.session_state["v_pedidos"] = _pedidos(inicio, fim)
            with st.spinner("Buscando orçamentos..."):
                st.session_state["v_orc"] = _orcamentos(inicio, fim)
            st.session_state["v_periodo"] = label_periodo
    else:
        st.info("👆 Clique em **Carregar Vendas** para buscar os dados.")
        st.stop()

    if "v_pedidos" in st.session_state:
        try:
            pedidos    = st.session_state["v_pedidos"]
            orcamentos = st.session_state["v_orc"]
            valor_total= sum(p.get("valorTotalPedido",0) or 0 for p in pedidos)
            sit_p = Counter(p.get("situacaoPedido","?") for p in pedidos)
            sit_o = Counter(o.get("situacao","?") for o in orcamentos)
            orc_ok= sit_o.get("APROVADO",0)+sit_o.get("CONCLUIDO",0)
            conv  = (orc_ok/len(orcamentos)*100) if orcamentos else 0

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.markdown(kpi("Pedidos", len(pedidos)), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Valor Total", fmt_brl(valor_total)), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Ticket Médio", fmt_brl(valor_total/len(pedidos) if pedidos else 0)), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Orçamentos", len(orcamentos)), unsafe_allow_html=True)
            with c5: st.markdown(kpi("Conversão", fmt_pct(conv),
                delta="⚠️ Baixa" if conv < 30 else "✓ Boa",
                delta_type="warn" if conv < 30 else "up"), unsafe_allow_html=True)

            if not orcamentos:
                st.warning("⚠️ Orçamentos indisponíveis no CRTI no momento.")

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Pedidos por Situação")
                if sit_p:
                    df = pd.DataFrame(list(sit_p.items()), columns=["Situação","Qtde"])
                    cores = {"CONCLUIDO":"#0A6E3F","APROVADO":"#2C5F9E",
                             "AGUARDANDO_APROVACAO":"#F39C12","CANCELADO":"#C0392B"}
                    fig = px.pie(df, values="Qtde", names="Situação",
                                 color="Situação", color_discrete_map=cores, template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)
            with cb:
                st.subheader("Top 10 Clientes")
                cv = Counter()
                for p in pedidos:
                    cli = (p.get("cliente") or {}).get("nomeRazao","?")
                    cv[cli] += p.get("valorTotalPedido",0) or 0
                if cv:
                    df2 = pd.DataFrame(cv.most_common(10), columns=["Cliente","Valor"])
                    df2["vf"] = df2["Valor"].apply(fmt_brl)
                    fig2 = px.bar(df2.sort_values("Valor"), x="Valor", y="Cliente",
                                  orientation="h", text="vf",
                                  color_discrete_sequence=["#1A3C6E"], template="plotly_white")
                    fig2.update_layout(showlegend=False)
                    st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Ranking de Vendedores")
            vv = Counter()
            for p in pedidos:
                v = (p.get("vendedorPedido") or {}).get("nomeVendedor","Sem vendedor")
                vv[v] += p.get("valorTotalPedido",0) or 0
            if vv:
                df3 = pd.DataFrame(vv.most_common(), columns=["Vendedor","Valor"])
                df3["Valor_fmt"] = df3["Valor"].apply(fmt_brl)
                df3["%"] = (df3["Valor"]/df3["Valor"].sum()*100).round(1).astype(str)+"%"
                st.dataframe(df3[["Vendedor","Valor_fmt","%"]], use_container_width=True, hide_index=True)

            st.subheader("Pedidos do Período")
            if pedidos:
                df4 = pd.DataFrame(pedidos)
                if "cliente" in df4.columns:
                    df4["cliente_nome"] = df4["cliente"].apply(lambda x: x.get("nomeRazao","") if isinstance(x,dict) else "")
                if "vendedorPedido" in df4.columns:
                    df4["vendedor"] = df4["vendedorPedido"].apply(lambda x: x.get("nomeVendedor","") if isinstance(x,dict) else "")
                cols = [c for c in ["id","cliente_nome","dataPedido","situacaoPedido","valorTotalPedido","vendedor"] if c in df4.columns]
                flt = st.text_input("🔍 Filtrar")
                df_s = df4[cols].copy()
                if flt:
                    mask = df_s.apply(lambda r: r.astype(str).str.contains(flt,case=False).any(), axis=1)
                    df_s = df_s[mask]
                st.dataframe(df_s, use_container_width=True, height=350)
        except Exception as e:
            st.error(f"Erro: {e}")


# ════════════════════════════════════════
#  CLIENTES INATIVOS
# ════════════════════════════════════════
elif pagina == "👥 Clientes Inativos":
    st.markdown("""<div class="main-header">
        <h1>👥 Clientes Inativos</h1>
        <p>Clientes que pararam de comprar — estratégia de reativação</p></div>""", unsafe_allow_html=True)

    dias = st.slider("Considerar inativo após X dias sem comprar", 30, 180, 60, 10)

    c1, c2 = st.columns([1,3])
    with c1:
        analisar = st.button("🔍 Analisar Carteira", use_container_width=True)
    with c2:
        st.caption("⚡ Busca até 500 pedidos do histórico para identificar inativos.")

    # Invalida cache se mudou o critério de dias
    if st.session_state.get("inat_dias") != dias:
        st.session_state.pop("inat_dados", None)
        st.session_state["inat_dias"] = dias

    if analisar:
        ph = st.empty()
        ph.info("⏳ Buscando histórico de pedidos... aguarde.")
        st.session_state["inat_dados"] = _clientes_inativos(dias)
        ph.empty()

    if "inat_dados" not in st.session_state:
        st.info("👆 Clique em **Analisar Carteira** para identificar clientes inativos.")
    else:
        try:
            dados    = st.session_state["inat_dados"]
            resumo   = dados.get("resumo", {})
            inativos_todos = dados.get("inativos", [])
            ativos         = dados.get("ativos_recentes", [])

            # Lê filtros do session_state
            dias_min = st.session_state.get("inat_dias_min", 30)
            dias_max = st.session_state.get("inat_dias_max", 180)

            # Filtra pelo range de dias selecionado
            inativos = [
                c for c in inativos_todos
                if dias_min <= c.get("dias_sem_comprar", 0) <= dias_max
            ]

            valor_risco = sum(c.get("total_historico",0) for c in inativos)
            pct = round(len(inativos)/resumo.get("total_clientes",1)*100, 1) if resumo.get("total_clientes") else 0

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(kpi("Total Clientes", resumo.get("total_clientes",0)), unsafe_allow_html=True)
            with c2: st.markdown(kpi(f"Inativos ({dias_min}-{dias_max}d)", len(inativos),
                delta=f"⚠️ {pct}% da carteira", delta_type="warn"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Ativos Recentes", resumo.get("ativos",0),
                delta="✓ Compraram recentemente", delta_type="up"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Receita em Risco", fmt_brl(valor_risco),
                delta="⚠️ Valor histórico", delta_type="warn"), unsafe_allow_html=True)

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Por Tempo de Inatividade")
                if inativos:
                    bins = {"60-90d":0,"90-120d":0,"120-180d":0,"+180d":0}
                    for c in inativos:
                        d = c["dias_sem_comprar"]
                        if d<=90: bins["60-90d"]+=1
                        elif d<=120: bins["90-120d"]+=1
                        elif d<=180: bins["120-180d"]+=1
                        else: bins["+180d"]+=1
                    df = pd.DataFrame(list(bins.items()), columns=["Grupo","Qtde"])
                    fig = px.bar(df, x="Grupo", y="Qtde", color="Qtde",
                                 color_continuous_scale=["#FFF3CD","#C0392B"], template="plotly_white")
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            with cb:
                st.subheader("Valor em Risco por Grupo")
                if inativos:
                    gv = {"60-90d":0,"90-120d":0,"120-180d":0,"+180d":0}
                    for c in inativos:
                        d,v = c["dias_sem_comprar"], c["total_historico"]
                        if d<=90: gv["60-90d"]+=v
                        elif d<=120: gv["90-120d"]+=v
                        elif d<=180: gv["120-180d"]+=v
                        else: gv["+180d"]+=v
                    df2 = pd.DataFrame(list(gv.items()), columns=["Grupo","Valor"])
                    fig2 = px.pie(df2, values="Valor", names="Grupo",
                                  color_discrete_sequence=["#F39C12","#E67E22","#E74C3C","#C0392B"],
                                  template="plotly_white")
                    st.plotly_chart(fig2, use_container_width=True)

            st.subheader("🔴 Lista de Clientes Inativos")
            if inativos:
                df3 = pd.DataFrame(inativos)
                df3["total_historico"] = df3["total_historico"].apply(fmt_brl)
                df3["ticket_medio"]    = df3["ticket_medio"].apply(fmt_brl)
                cols = [c for c in ["nome","ultima_compra","dias_sem_comprar",
                                    "total_historico","qtde_pedidos","ticket_medio"] if c in df3.columns]
                st.dataframe(df3[cols], use_container_width=True, height=400)
                csv = df3[cols].to_csv(index=False).encode("utf-8-sig")
                st.download_button("⬇️ Exportar CSV", data=csv,
                                   file_name="clientes_inativos.csv", mime="text/csv")
        except Exception as e:
            st.error(f"Erro: {e}")


# ════════════════════════════════════════
#  FROTA
# ════════════════════════════════════════
elif pagina == "🚜 Frota e Equipamentos":
    st.markdown(f"""<div class="main-header">
        <h1>🚜 Frota e Equipamentos</h1>
        <p>Patrimônio, seguros e horímetros · {label_periodo}</p></div>""", unsafe_allow_html=True)

    with st.spinner("Carregando equipamentos..."):
        try:
            from modules.resumidor import resumir_equipamentos
            equip = _equipamentos()
            res   = resumir_equipamentos(equip)

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.markdown(kpi("Total", res["total_equipamentos"]), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Valor Aquisição", f"R${res['valor_aquisicao_total']/1e6:.1f}M"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Depreciação", fmt_pct(res["depreciacao_pct"]),
                delta="⚠️ Alto" if res["depreciacao_pct"]>60 else "Normal",
                delta_type="warn" if res["depreciacao_pct"]>60 else "up"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Seguros Vencidos", res["seguros_vencidos"],
                delta="⚠️ Urgente" if res["seguros_vencidos"] else "✓ OK",
                delta_type="warn" if res["seguros_vencidos"] else "up"), unsafe_allow_html=True)
            with c5: st.markdown(kpi("De Terceiros", res["de_subempreiteiros"]), unsafe_allow_html=True)

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Por Grupo")
                if res["por_grupo"]:
                    df = pd.DataFrame(list(res["por_grupo"].items()), columns=["Grupo","Qtde"])
                    df = df.sort_values("Qtde", ascending=False).head(12)
                    fig = px.bar(df, x="Qtde", y="Grupo", orientation="h",
                                 color="Qtde", color_continuous_scale=["#BDD0F0","#1A3C6E"],
                                 template="plotly_white")
                    fig.update_layout(yaxis=dict(categoryorder="total ascending"),
                                      showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            with cb:
                st.subheader("⚠️ Seguros Vencidos")
                if res["lista_seguros_vencidos"]:
                    df2 = pd.DataFrame(res["lista_seguros_vencidos"])
                    df2 = df2[["descricao","placa","vencimento","valor_cobertura"]].copy()
                    df2.columns = ["Equipamento","Placa","Vencimento","Cobertura"]
                    df2["Cobertura"] = df2["Cobertura"].apply(lambda v: fmt_brl(v) if v else "—")
                    st.dataframe(df2, use_container_width=True, height=300)
                else:
                    st.success("✅ Nenhum seguro vencido!")

            st.subheader("Cadastro Completo")
            df3 = pd.DataFrame(equip)
            cols = [c for c in ["id","descricao","placa","descricaoGrupoEquipamento",
                                 "nomeFilialAtual","ultimoHorometroOdometro",
                                 "valorAquisicao","valorMercado","vencimentoSeguro"] if c in df3.columns]
            flt = st.text_input("🔍 Filtrar equipamento")
            dfs = df3[cols].copy()
            if flt:
                mask = dfs.apply(lambda r: r.astype(str).str.contains(flt,case=False).any(), axis=1)
                dfs = dfs[mask]
            st.dataframe(dfs, use_container_width=True, height=400)
        except Exception as e:
            st.error(f"Erro: {e}")


# ════════════════════════════════════════
#  MANUTENÇÃO
# ════════════════════════════════════════
elif pagina == "🔧 Manutenção":
    st.markdown(f"""<div class="main-header">
        <h1>🔧 Manutenção</h1>
        <p>Ordens de serviço · {label_periodo}</p></div>""", unsafe_allow_html=True)

    with st.spinner("Carregando OS..."):
        try:
            from modules.resumidor import resumir_os_manutencao
            os_l = _os(inicio, fim)
            res  = resumir_os_manutencao(os_l)

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(kpi("Total OS", res["total_os"]), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Atrasadas", res["os_atrasadas"],
                delta="⚠️ Ação" if res["os_atrasadas"] else "✓ OK",
                delta_type="warn" if res["os_atrasadas"] else "up"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Equip. em OS", len(res["top_10_equipamentos"])), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Tipos Defeito", len(res["top_10_defeitos"])), unsafe_allow_html=True)

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("OS por Situação")
                if res["por_situacao"]:
                    df = pd.DataFrame(list(res["por_situacao"].items()), columns=["Situação","Qtde"])
                    fig = px.pie(df, values="Qtde", names="Situação",
                                 color_discrete_sequence=px.colors.sequential.Blues_r,
                                 template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)
            with cb:
                st.subheader("Top Defeitos")
                if res["top_10_defeitos"]:
                    df2 = pd.DataFrame(list(res["top_10_defeitos"].items()), columns=["Defeito","Qtde"])
                    fig2 = px.bar(df2.sort_values("Qtde"), x="Qtde", y="Defeito",
                                  orientation="h", color_discrete_sequence=["#2C5F9E"],
                                  template="plotly_white")
                    st.plotly_chart(fig2, use_container_width=True)

            if res["lista_atrasadas"]:
                st.subheader("⚠️ OS Atrasadas")
                st.dataframe(pd.DataFrame(res["lista_atrasadas"]), use_container_width=True)

            st.subheader("Todas as OS")
            df3 = pd.DataFrame(os_l)
            if not df3.empty:
                if "equipamento" in df3.columns:
                    df3["equip_nome"] = df3["equipamento"].apply(lambda x: x.get("descricao","") if isinstance(x,dict) else "")
                cols = [c for c in ["id","equip_nome","dataAbertura","dataPrevTermino",
                                    "situacao","tipo","defeito"] if c in df3.columns]
                flt = st.text_input("🔍 Filtrar OS")
                dfs = df3[cols].copy()
                if flt:
                    mask = dfs.apply(lambda r: r.astype(str).str.contains(flt,case=False).any(), axis=1)
                    dfs = dfs[mask]
                st.dataframe(dfs, use_container_width=True, height=400)
        except Exception as e:
            st.error(f"Erro: {e}")


# ════════════════════════════════════════
#  FINANCEIRO
# ════════════════════════════════════════
elif pagina == "💳 Financeiro":
    st.markdown(f"""<div class="main-header">
        <h1>💳 Financeiro</h1>
        <p>Contas a pagar e receber · {label_periodo}</p></div>""", unsafe_allow_html=True)

    with st.spinner("Carregando transferências..."):
        try:
            from modules.resumidor import resumir_transferencias
            trf = _transferencias(inicio, fim)
            res = resumir_transferencias(trf)

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.markdown(kpi("Documentos", res["total_documentos"]), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Valor Total", fmt_brl(res["valor_total_emitido"])), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Valor Líquido", fmt_brl(res["valor_liquido_total"])), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Juros", fmt_brl(res["total_juros"]),
                delta="⚠️ Alto" if res["total_juros"]>10000 else "Normal",
                delta_type="warn" if res["total_juros"]>10000 else "up"), unsafe_allow_html=True)
            with c5: st.markdown(kpi("Ticket Médio", fmt_brl(res["ticket_medio"])), unsafe_allow_html=True)

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Top 15 Fornecedores")
                if res["top_15_fornecedores"]:
                    df = pd.DataFrame(res["top_15_fornecedores"])
                    df["vf"] = df["valor"].apply(fmt_brl)
                    fig = px.bar(df.sort_values("valor"), x="valor", y="fornecedor",
                                 orientation="h", text="vf",
                                 color_discrete_sequence=["#1A3C6E"], template="plotly_white")
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            with cb:
                st.subheader("Por Mês")
                if res["distribuicao_por_mes"]:
                    df2 = pd.DataFrame(list(res["distribuicao_por_mes"].items()), columns=["Mês","Qtde"])
                    fig2 = px.bar(df2.sort_values("Mês"), x="Mês", y="Qtde",
                                  color_discrete_sequence=["#2C5F9E"], template="plotly_white")
                    st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Lançamentos")
            df3 = pd.DataFrame(res["amostra_documentos"])
            if not df3.empty:
                if "fornecedor" in df3.columns:
                    df3["forn_nome"] = df3["fornecedor"].apply(lambda x: x.get("nomeRazao","") if isinstance(x,dict) else "")
                cols = [c for c in ["id","forn_nome","numeroDocumento","dataEmissao",
                                    "valorTotalDocumento","valorLiquido"] if c in df3.columns]
                st.dataframe(df3[cols], use_container_width=True, height=350)
        except Exception as e:
            st.error(f"Erro: {e}")


# ════════════════════════════════════════
#  COMPRAS
# ════════════════════════════════════════
elif pagina == "🛒 Compras":
    st.markdown(f"""<div class="main-header">
        <h1>🛒 Compras</h1>
        <p>Pipeline de requisições · {label_periodo}</p></div>""", unsafe_allow_html=True)

    with st.spinner("Carregando compras..."):
        try:
            from modules.resumidor import resumir_compras
            dados = _compras(inicio, fim)
            res   = resumir_compras(dados)

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.markdown(kpi("Requisições", res["total_requisicoes"]), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Ordens Compra", res["total_ocs"]), unsafe_allow_html=True)
            with c3: st.markdown(kpi("OCs Sem Processo", res["ocs_diretas_sem_req"],
                delta="⚠️ Auditar" if res["ocs_diretas_sem_req"] else "✓ OK",
                delta_type="warn" if res["ocs_diretas_sem_req"] else "up"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Valor Total", fmt_brl(res["valor_total_comprado"])), unsafe_allow_html=True)
            with c5: st.markdown(kpi("Frete %", fmt_pct(res["frete_pct"]),
                delta="⚠️ Alto" if res["frete_pct"]>10 else "Normal",
                delta_type="warn" if res["frete_pct"]>10 else "up"), unsafe_allow_html=True)

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Top Fornecedores")
                if res["top_15_fornecedores"]:
                    df = pd.DataFrame(res["top_15_fornecedores"])
                    df["vf"] = df["valor"].apply(fmt_brl)
                    fig = px.bar(df.sort_values("valor"), x="valor", y="fornecedor",
                                 orientation="h", text="vf",
                                 color_discrete_sequence=["#4A235A"], template="plotly_white")
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            with cb:
                st.subheader("Composição do Valor")
                df2 = pd.DataFrame({
                    "Tipo": ["Mercadorias","Frete","Desconto"],
                    "Valor": [res["valor_mercadorias"], res["valor_frete"], abs(res["valor_desconto"])]
                })
                fig2 = go.Figure(go.Pie(
                    labels=df2["Tipo"], values=df2["Valor"],
                    marker_colors=["#1A3C6E","#F39C12","#0A6E3F"], hole=0.4))
                st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")


# ════════════════════════════════════════
#  MATERIAIS
# ════════════════════════════════════════
elif pagina == "📦 Materiais":
    st.markdown("""<div class="main-header">
        <h1>📦 Materiais e Suprimentos</h1>
        <p>Cadastro e qualidade de dados</p></div>""", unsafe_allow_html=True)

    with st.spinner("Carregando materiais..."):
        try:
            from modules.resumidor import resumir_materiais
            mats = _materiais()
            res  = resumir_materiais(mats)

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.markdown(kpi("Total", res["total_materiais"]), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Ativos", res["ativos"]), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Sem NCM", res["sem_ncm"],
                delta="⚠️ Risco fiscal" if res["sem_ncm"] else "✓ OK",
                delta_type="warn" if res["sem_ncm"] else "up"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Sem Preço", res["sem_preco"],
                delta="⚠️" if res["sem_preco"] else "✓ OK",
                delta_type="warn" if res["sem_preco"] else "up"), unsafe_allow_html=True)
            with c5: st.markdown(kpi("Completude", fmt_pct(res["completude_pct"])), unsafe_allow_html=True)

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Por Grupo")
                if res["por_grupo"]:
                    df = pd.DataFrame(list(res["por_grupo"].items()), columns=["Grupo","Qtde"])
                    df = df.sort_values("Qtde", ascending=False).head(10)
                    fig = px.bar(df, x="Qtde", y="Grupo", orientation="h",
                                 color_discrete_sequence=["#0A6E3F"], template="plotly_white")
                    fig.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            with cb:
                st.subheader("Problemas no Cadastro")
                df2 = pd.DataFrame({
                    "Problema": ["Sem NCM","Sem preço","Sem grupo","Sem EAN","Inativos"],
                    "Qtde": [res["sem_ncm"],res["sem_preco"],res["sem_grupo"],res["sem_ean"],res["inativos"]]
                })
                fig2 = px.bar(df2, x="Qtde", y="Problema", orientation="h",
                              color="Qtde", color_continuous_scale=["#FFF3CD","#C0392B"],
                              template="plotly_white")
                fig2.update_layout(showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")


# ════════════════════════════════════════
#  GERAR RELATÓRIO COM IA
# ════════════════════════════════════════
elif pagina == "🤖 Gerar Relatório com IA":
    st.markdown("""<div class="main-header">
        <h1>🤖 Gerar Relatório com IA</h1>
        <p>Claude analisa os dados e escreve um relatório executivo em PDF</p></div>""", unsafe_allow_html=True)

    descricoes = {
        "🛍️ Análise de Vendas":           "Pedidos, orçamentos, top clientes, vendedores, taxa de conversão.",
        "👥 Clientes Inativos":            "Identifica clientes que pararam de comprar. Estratégia de reativação por grupo de urgência.",
        "🚜 Auditoria de Frota":           "Seguros vencidos, OS atrasadas, anormalidades, score de saúde da frota.",
        "🔧 Relatório de Manutenção":      "OS por período, defeitos frequentes, tempo de resolução, equipe.",
        "📋 Patrimônio da Frota":          "Depreciação, cobertura de seguros, próprios vs terceiros.",
        "💳 Auditoria Financeira":         "Duplicatas, valores suspeitos, concentração de fornecedores.",
        "💳 Análise Financeira Mensal":    "Fluxo de caixa, posição bancária, ticket médio, recomendações.",
        "🛒 Auditoria de Compras":         "Bypass de processo, favorecimento de fornecedor, OCs sem entrega.",
        "🛒 Relatório Gerencial de Compras":"Volume, top fornecedores, frete %, descontos, lead times.",
        "📦 Auditoria de Materiais":       "NCM ausente, sem preço, score de qualidade do cadastro.",
    }

    c1, c2 = st.columns([1,2])
    with c1:
        tipo = st.selectbox("Tipo de Relatório", list(descricoes.keys()))
        st.caption(f"📅 {label_periodo}")
        gerar = st.button("🚀 Gerar Relatório Agora", use_container_width=True)
    with c2:
        st.info(descricoes[tipo])

    if gerar:
        from Prompts.prompts import (
            prompt_auditoria_frota, prompt_relatorio_manutencao,
            prompt_relatorio_patrimonio_frota, prompt_auditoria_financeira,
            prompt_analise_financeira_mensal, prompt_auditoria_compras,
            prompt_relatorio_compras_gerencial, prompt_auditoria_materiais,
            prompt_analise_vendas, prompt_clientes_inativos,
        )
        prog = st.progress(0)
        stat = st.status("Iniciando...", expanded=True)
        try:
            with stat:
                st.write("📡 Buscando dados do CRTI...")
                prog.progress(20)

                crti_cli = get_crti()
                if "Análise de Vendas" in tipo:
                    ped = _pedidos(inicio, fim); orc = _orcamentos(inicio, fim)
                    prompt = prompt_analise_vendas(ped, orc, label_periodo)
                    tipo_pdf, titulo = "vendas", "Análise de Vendas"
                elif "Clientes Inativos" in tipo:
                    dados = _clientes_inativos(60)
                    prompt = prompt_clientes_inativos(dados)
                    tipo_pdf, titulo = "clientes_inativos", "Clientes Inativos"
                elif "Auditoria de Frota" in tipo:
                    dados = crti_cli.buscar_dados_frota_completos(inicio, fim)
                    prompt = prompt_auditoria_frota(dados, label_periodo)
                    tipo_pdf, titulo = "auditoria_frota", "Auditoria de Frota"
                elif "Manutenção" in tipo:
                    os_l = _os(inicio, fim)
                    prompt = prompt_relatorio_manutencao(os_l, label_periodo)
                    tipo_pdf, titulo = "manutencao", "Relatório de Manutenção"
                elif "Patrimônio" in tipo:
                    equip = _equipamentos()
                    prompt = prompt_relatorio_patrimonio_frota(equip)
                    tipo_pdf, titulo = "patrimonio", "Patrimônio da Frota"
                elif "Auditoria Financeira" in tipo:
                    dados = crti_cli.buscar_dados_auditoria(inicio, fim)
                    prompt = prompt_auditoria_financeira(dados, label_periodo)
                    tipo_pdf, titulo = "auditoria", "Auditoria Financeira"
                elif "Mensal" in tipo:
                    dados = crti_cli.buscar_dados_financeiros(inicio, fim)
                    prompt = prompt_analise_financeira_mensal(dados, label_periodo)
                    tipo_pdf, titulo = "mensal", "Análise Financeira Mensal"
                elif "Auditoria de Compras" in tipo:
                    dados = _compras(inicio, fim)
                    prompt = prompt_auditoria_compras(dados, label_periodo)
                    tipo_pdf, titulo = "auditoria_compras", "Auditoria de Compras"
                elif "Gerencial de Compras" in tipo:
                    dados = _compras(inicio, fim)
                    prompt = prompt_relatorio_compras_gerencial(dados, label_periodo)
                    tipo_pdf, titulo = "relatorio_compras", "Relatório de Compras"
                elif "Materiais" in tipo:
                    mats = _materiais()
                    prompt = prompt_auditoria_materiais(mats)
                    tipo_pdf, titulo = "materiais", "Auditoria de Materiais"

                prog.progress(50)
                st.write("🤖 Claude analisando...")
                analise = get_claude().analisar(prompt)

                prog.progress(80)
                st.write("📄 Gerando PDF...")
                caminho = get_pdf().gerar_pdf(
                    titulo=titulo, analise=analise,
                    tipo=tipo_pdf, subtitulo=f"Período: {label_periodo}"
                )
                prog.progress(100)
                st.write("✅ Pronto!")

            st.success(f"✅ **{titulo}** gerado!")
            with open(caminho, "rb") as f:
                st.download_button("⬇️ Baixar PDF", data=f.read(),
                                   file_name=os.path.basename(caminho),
                                   mime="application/pdf", use_container_width=True)

            st.subheader("📋 Prévia")
            st.markdown(analise[:3000] + ("..." if len(analise)>3000 else ""))

        except Exception as e:
            st.error(f"❌ Erro: {e}")
            st.exception(e)
