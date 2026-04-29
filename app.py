"""
CRTI Intelligence v2 — BI Completo
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
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules"))

# ── AUTH via CRTI ──
from auth_crti import requer_autenticacao, usuario_atual, logout
requer_autenticacao()

st.set_page_config(
    page_title="CRTI Intelligence | Vogelsanger",
    page_icon="📊", layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.main-header { background:linear-gradient(135deg,#1A3C6E 0%,#2C5F9E 100%);
    padding:1.2rem 1.5rem;border-radius:12px;color:white;margin-bottom:1rem; }
.main-header h1{color:white;margin:0;font-size:1.5rem;}
.main-header p{color:#BDD0F0;margin:.2rem 0 0;font-size:.85rem;}
.kpi-card{background:white;border:1px solid #E0E8F5;border-radius:10px;
    padding:.8rem .6rem;text-align:center;box-shadow:0 2px 8px rgba(26,60,110,.07);height:100%;}
.kpi-value{font-size:1.5rem;font-weight:700;color:#1A3C6E;line-height:1.2;}
.kpi-label{font-size:.75rem;color:#888;margin-top:.2rem;}
.kpi-delta{font-size:.75rem;margin-top:.2rem;}
.kpi-delta.up{color:#0A6E3F;} .kpi-delta.warn{color:#F39C12;} .kpi-delta.down{color:#C0392B;}
.alert-box{border-left:4px solid #C0392B;background:#FDECEA;
    padding:.7rem .8rem;border-radius:0 8px 8px 0;margin:.3rem 0;font-size:.9rem;}
.alert-box.warn{background:#FFF3CD;border-left-color:#F39C12;}
.alert-box.ok{background:#E8F5EE;border-left-color:#0A6E3F;}
.status-ok{background:#E8F5EE;color:#0A6E3F;padding:2px 8px;border-radius:12px;font-size:.75rem;font-weight:600;}
.status-warn{background:#FFF3CD;color:#F39C12;padding:2px 8px;border-radius:12px;font-size:.75rem;font-weight:600;}
.stButton>button{background:#1A3C6E;color:white;border:none;border-radius:8px;
    padding:.5rem 1rem;font-weight:600;width:100%;}
.stButton>button:hover{background:#2C5F9E;}
.secao-kpi{background:#F5F6F8;border-radius:10px;padding:1rem;margin:.5rem 0;}
#MainMenu{visibility:hidden;} footer{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def fmt_brl(v):
    try:    return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except: return "R$ —"

def fmt_brl_m(v):
    try:
        v = float(v)
        if abs(v) >= 1_000_000: return f"R$ {v/1_000_000:.1f}M"
        if abs(v) >= 1_000:     return f"R$ {v/1_000:.0f}k"
        return fmt_brl(v)
    except: return "R$ —"

def fmt_pct(v):
    try:    return f"{float(v):.1f}%"
    except: return "—"

def fmt_num(v):
    try:    return f"{int(v):,}".replace(",",".")
    except: return "—"

def kpi(label, value, delta=None, delta_type="ok"):
    d = f'<div class="kpi-delta {delta_type}">{delta}</div>' if delta else ""
    return f'<div class="kpi-card"><div class="kpi-value">{value}</div><div class="kpi-label">{label}</div>{d}</div>'

def dias_vencimento(data_venc_str):
    try:
        dv = datetime.strptime(str(data_venc_str)[:10], "%Y-%m-%d").date()
        return (datetime.now().date() - dv).days
    except: return 0

# ─── CONEXÕES ────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_crti():
    from crti_client import CRTIClient
    return CRTIClient()

@st.cache_resource(show_spinner=False)
def get_claude():
    from claude_analyzer import ClaudeAnalyzer
    return ClaudeAnalyzer()

@st.cache_resource(show_spinner=False)
def get_pdf():
    from report_generator import ReportGenerator
    return ReportGenerator()

# ─── CACHE DE DADOS ──────────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def _info_empresa():
    return get_crti().buscar_info_empresa()

@st.cache_data(ttl=3600, show_spinner=False)
def _equipamentos():
    return get_crti().buscar_equipamentos()

@st.cache_data(ttl=1800, show_spinner=False)
def _os_legado(inicio, fim):
    return get_crti().buscar_os_manutencao(data_abertura_de=inicio, data_abertura_ate=fim)

@st.cache_data(ttl=1800, show_spinner=False)
def _transferencias(inicio, fim):
    return get_crti().buscar_transferencias(inicio, fim)

@st.cache_data(ttl=1800, show_spinner=False)
def _compras(inicio, fim):
    return get_crti().buscar_compras_periodo(inicio, fim)

@st.cache_data(ttl=900, show_spinner=False)
def _pedidos(inicio, fim):
    return get_crti().buscar_pedidos_material(data_inicio=inicio, data_fim=fim)

@st.cache_data(ttl=900, show_spinner=False)
def _orcamentos(inicio, fim):
    try:    return get_crti().buscar_orcamentos_venda(data_inicio=inicio, data_fim=fim)
    except: return []

@st.cache_data(ttl=7200, show_spinner=False)
def _materiais():
    return get_crti().buscar_materiais(apenas_ativos=False)

@st.cache_data(ttl=7200, show_spinner=False)
def _clientes_inativos(dias):
    return get_crti().buscar_clientes_inativos(dias_sem_comprar=dias)

# Novos endpoints BI
@st.cache_data(ttl=1800, show_spinner=False)
def _pendencias(tipo, venc_de=None, venc_ate=None):
    return get_crti().bi_pendencias_baixas(tipo, data_venc_de=venc_de, data_venc_ate=venc_ate)

@st.cache_data(ttl=1800, show_spinner=False)
def _recebimentos(inicio, fim):
    return get_crti().bi_recebimentos_efetivados(inicio, fim)

@st.cache_data(ttl=1800, show_spinner=False)
def _pagamentos(inicio, fim):
    return get_crti().bi_pagamentos_efetivados(inicio, fim)

@st.cache_data(ttl=1800, show_spinner=False)
def _fluxo_previsto(de=None, ate=None):
    return get_crti().bi_fluxo_previsto_realizado(data_mes_de=de, data_mes_ate=ate)

@st.cache_data(ttl=1800, show_spinner=False)
def _faturamento(inicio, fim):
    return get_crti().bi_faturamento_geral(inicio, fim)

@st.cache_data(ttl=1800, show_spinner=False)
def _saida_analitico(inicio, fim):
    return get_crti().bi_saida_material_analitico(inicio, fim)

@st.cache_data(ttl=3600, show_spinner=False)
def _custos_filial():
    return get_crti().bi_custos_totais_filial()

@st.cache_data(ttl=1800, show_spinner=False)
def _despesas(inicio, fim):
    return get_crti().bi_despesas_analiticas(inicio, fim)

@st.cache_data(ttl=3600, show_spinner=False)
def _producao():
    return get_crti().bi_producao_previsto_realizado()

@st.cache_data(ttl=3600, show_spinner=False)
def _mao_obra(inicio=None, fim=None):
    return get_crti().bi_histograma_mao_obra(data_inicio=inicio, data_fim=fim)

@st.cache_data(ttl=3600, show_spinner=False)
def _eficiencia():
    return get_crti().bi_eficiencia_equipamentos()

@st.cache_data(ttl=3600, show_spinner=False)
def _combustivel():
    return get_crti().bi_controle_combustivel()

@st.cache_data(ttl=1800, show_spinner=False)
def _oficina(inicio=None, fim=None):
    return get_crti().bi_lancamentos_oficina(data_inicio=inicio, data_fim=fim)

@st.cache_data(ttl=1800, show_spinner=False)
def _os_bi(inicio=None, fim=None):
    return get_crti().bi_os_manutencao(data_inicio=inicio, data_fim=fim)

@st.cache_data(ttl=1800, show_spinner=False)
def _oc_os(inicio=None, fim=None):
    return get_crti().bi_oc_os_analitico(data_inicio=inicio, data_fim=fim)

@st.cache_data(ttl=1800, show_spinner=False)
def _nfe(inicio, fim):
    return get_crti().bi_notas_fiscais_emitidas(inicio, fim)

@st.cache_data(ttl=1800, show_spinner=False)
def _nfse(inicio, fim):
    return get_crti().bi_notas_fiscais_servico(inicio, fim)

# ─── PERÍODO ─────────────────────────────────────────────────────────────────

def resolver_periodo(tipo, ini=None, fim=None):
    from periodos import Periodos
    m = {"Mês atual": Periodos.mes_atual, "Mês anterior": Periodos.mes_anterior,
         "Últimos 7 dias": Periodos.ultimos_7_dias, "Últimos 30 dias": Periodos.ultimos_30_dias,
         "Últimos 3 meses": lambda: Periodos.ultimos_n_meses(3),
         "Últimos 6 meses": lambda: Periodos.ultimos_n_meses(6),
         "Ano atual": Periodos.ano_atual}
    if tipo in m: return m[tipo]()
    if tipo == "Personalizado" and ini and fim:
        return ini.strftime("%Y-%m-%d"), fim.strftime("%Y-%m-%d")
    return Periodos.mes_atual()

def fmt_label(i, f):
    fi = datetime.strptime(i,"%Y-%m-%d").strftime("%d/%m/%Y")
    ff = datetime.strptime(f,"%Y-%m-%d").strftime("%d/%m/%Y")
    return fi if i==f else f"{fi} a {ff}"

# ════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════
def erro_endpoint(endpoint=""):
    st.warning(f"""
⚠️ **Módulo não disponível — sem permissão de acesso**

O endpoint **{endpoint}** retornou erro 403.
Solicite ao TI do CRTI que libere este endpoint.

Os outros módulos continuam funcionando normalmente.
""")

def erro_generico(e):
    msg = str(e)
    if "403" in msg:
        erro_endpoint()
    elif "401" in msg:
        st.error("❌ Sessão expirada. Faça logout e entre novamente.")
        if st.button("🚪 Logout"):
            logout()
    elif "Connection" in type(e).__name__:
        st.error("❌ Sem conexão com o CRTI.")
    else:
        st.error(f"❌ Erro: {str(e)[:200]}")

with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:.5rem 0 1rem;">
        <div style="font-size:2rem;">📊</div>
        <div style="font-weight:700;color:#1A3C6E;font-size:1.1rem;">CRTI Intelligence</div>
        <div style="color:#888;font-size:.8rem;">Britagem Vogelsanger</div>
    </div>""", unsafe_allow_html=True)
    st.divider()

    pagina = st.selectbox("📍 Módulo", [
        # Painel
        "🏠 Painel Executivo",
        # Financeiro
        "💰 Pendências e Aging",
        "📊 Fluxo de Caixa",
        "💳 Pagamentos e Recebimentos",
        # Comercial
        "📈 Faturamento Geral",
        "🛍️ Vendas com Margem",
        "👥 Clientes Inativos",
        # Custos
        "🏗️ Custos por Filial",
        "📋 Produção Previsto/Realizado",
        "👷 Mão de Obra",
        "💸 Despesas Analíticas",
        # Frota
        "⚙️ Eficiência de Equipamentos",
        "⛽ Consumo de Combustível",
        "🔧 Manutenção e Oficina",
        "🚜 Frota — Cadastro",
        # Compras
        "🛒 Compras OC/OS Analítico",
        # Materiais
        "📦 Materiais",
        # KPIs
        "🎯 KPIs e Cruzamentos",
        # IA
        "🤖 Gerar Relatório com IA",
    ])

    st.divider()
    st.markdown("**📅 Período**")
    tipo_p = st.selectbox("Período", [
        "Mês atual","Mês anterior","Últimos 7 dias",
        "Últimos 30 dias","Últimos 3 meses","Últimos 6 meses","Ano atual","Personalizado",
    ], label_visibility="collapsed")
    ini_c = fim_c = None
    if tipo_p == "Personalizado":
        c1,c2 = st.columns(2)
        with c1: ini_c = st.date_input("Início", value=datetime.now().replace(day=1))
        with c2: fim_c = st.date_input("Fim",    value=datetime.now())
    inicio, fim = resolver_periodo(tipo_p, ini_c, fim_c)
    label_periodo = fmt_label(inicio, fim)
    st.caption(f"📆 {label_periodo}")

    st.divider()
    st.markdown("**🔌 Status**")
    try:
        info = _info_empresa()
        emp  = info.get("nomeEmpresa","")[:20]
        st.markdown(f'<span class="status-ok">✓ {emp}</span>', unsafe_allow_html=True)
    except:
        st.markdown('<span class="status-warn">⚠ Conectando...</span>', unsafe_allow_html=True)
    st.caption(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    u = usuario_atual()
    if u:
        st.caption(f"👤 {u}")
    col_a, col_s = st.columns(2)
    with col_a:
        if st.button("🔄", use_container_width=True, help="Atualizar dados"):
            st.cache_data.clear()
            st.session_state.pop("filiais_carregadas", None)
            st.rerun()
    with col_s:
        if st.button("🚪", use_container_width=True, help="Sair"):
            logout()


# ════════════════════════════════════════
#  PAINEL EXECUTIVO CUSTOMIZÁVEL
# ════════════════════════════════════════

# ── Widgets disponíveis ──
WIDGETS_DISPONIVEIS = {
    "kpis_frota":       "🚜 KPIs de Frota (equip., OS, seguros)",
    "kpis_financeiro":  "💰 KPIs Financeiros (docs, valor)",
    "kpis_eficiencia":  "⚙️ KPI Eficiência média da frota",
    "os_situacao":      "🔧 Gráfico: OS por Situação",
    "top_fornecedores": "🏭 Gráfico: Top Fornecedores",
    "alertas":          "⚠️ Painel de Alertas",
    "faturamento_kpi":  "📈 KPI Faturamento do período",
    "eficiencia_graf":  "⚙️ Gráfico: Eficiência por equipamento",
    "combustivel_kpi":  "⛽ KPI Combustível (desvios)",
    "custos_kpi":       "🏗️ KPI Custos por filial",
    "navegacao":        "🗺️ Atalhos de Navegação Rápida",
}

# ── Padrão se nunca configurou ──
WIDGETS_PADRAO = ["kpis_frota","kpis_financeiro","os_situacao",
                   "top_fornecedores","alertas","navegacao"]

# ── Lê preferências salvas (session_state) ──
if "painel_widgets" not in st.session_state:
    st.session_state["painel_widgets"] = WIDGETS_PADRAO.copy()

if pagina == "🏠 Painel Executivo":
    # ── Configuração na sidebar (só quando no painel) ──
    with st.sidebar:
        st.divider()
        with st.expander("⚙️ Configurar Painel"):
            st.caption("Escolha os widgets visíveis:")
            novos = []
            for chave, label in WIDGETS_DISPONIVEIS.items():
                ativo = st.checkbox(label, value=(chave in st.session_state["painel_widgets"]),
                                    key=f"chk_{chave}")
                if ativo:
                    novos.append(chave)
            if st.button("💾 Salvar layout", use_container_width=True):
                st.session_state["painel_widgets"] = novos
                st.success("Layout salvo!")
                st.rerun()
            if st.button("↩️ Restaurar padrão", use_container_width=True):
                st.session_state["painel_widgets"] = WIDGETS_PADRAO.copy()
                st.rerun()

    W = st.session_state["painel_widgets"]

    st.markdown(f'''<div class="main-header">
        <h1>📊 Painel Executivo</h1>
        <p>Visão consolidada · {label_periodo} · <span style="font-size:.8rem;opacity:.7">{len(W)} widgets ativos</span></p></div>''', unsafe_allow_html=True)

    # ── Carrega dados base (sempre) ──
    with st.spinner("Carregando dados..."):
        try:
            from resumidor import resumir_equipamentos, resumir_os_manutencao, resumir_transferencias
            equip = _equipamentos()
            os_l  = _os_legado(inicio, fim)
            trf   = _transferencias(inicio, fim)
            re = resumir_equipamentos(equip)
            ro = resumir_os_manutencao(os_l)
            rt = resumir_transferencias(trf)
            dados_base_ok = True
        except Exception:
            dados_base_ok = False

    # ── KPIs FROTA ──
    if "kpis_frota" in W and dados_base_ok:
        c1,c2,c3 = st.columns(3)
        with c1: st.markdown(kpi("Equipamentos", re["total_equipamentos"]), unsafe_allow_html=True)
        with c2: st.markdown(kpi("OS Período", ro["total_os"],
            delta=f"⚠️ {ro['os_atrasadas']} atrasadas" if ro["os_atrasadas"] else "✓ OK",
            delta_type="warn" if ro["os_atrasadas"] else "up"), unsafe_allow_html=True)
        with c3: st.markdown(kpi("Seguros Vencidos", re["seguros_vencidos"],
            delta="⚠️ Urgente" if re["seguros_vencidos"] else "✓ OK",
            delta_type="warn" if re["seguros_vencidos"] else "up"), unsafe_allow_html=True)

    # ── KPIs FINANCEIRO ──
    if "kpis_financeiro" in W and dados_base_ok:
        c4,c5 = st.columns(2)
        with c4: st.markdown(kpi("Docs Financeiros", rt["total_documentos"]), unsafe_allow_html=True)
        with c5: st.markdown(kpi("Valor Período", fmt_brl_m(rt["valor_total_emitido"])), unsafe_allow_html=True)

    # ── KPI EFICIÊNCIA ──
    if "kpis_eficiencia" in W:
        try:
            ef = _eficiencia()
            if ef:
                ef_med = sum(float(d.get("eficiencia",0) or 0) for d in ef) / len(ef)
                baixa  = sum(1 for d in ef if float(d.get("eficiencia",0) or 0) < 0.75)
                st.markdown(kpi("Eficiência Média Frota", fmt_pct(ef_med*100),
                    delta=f"⚠️ {baixa} equip. abaixo de 75%" if baixa else "✓ OK",
                    delta_type="warn" if baixa else "up"), unsafe_allow_html=True)
        except Exception:
            pass

    # ── KPI FATURAMENTO ──
    if "faturamento_kpi" in W:
        try:
            fat = _faturamento(inicio, fim)
            if fat:
                tot_fat = sum(float(f.get("valorBruto",0) or 0) for f in fat)
                tot_liq = sum(float(f.get("valorLiquido",0) or 0) for f in fat)
                c_f1, c_f2 = st.columns(2)
                with c_f1: st.markdown(kpi("Faturamento Bruto", fmt_brl_m(tot_fat)), unsafe_allow_html=True)
                with c_f2: st.markdown(kpi("Faturamento Líquido", fmt_brl_m(tot_liq)), unsafe_allow_html=True)
        except Exception:
            pass

    # ── KPI COMBUSTÍVEL ──
    if "combustivel_kpi" in W:
        try:
            comb = _combustivel()
            if comb:
                acima = [d for d in comb if d.get("mediaObtida") and d.get("mediaDesejada")
                         and float(d.get("mediaObtida",0)) > float(d.get("mediaDesejada",0)) * 1.15]
                st.markdown(kpi("Equip. Combustível Acima do Padrão", len(acima),
                    delta="⚠️ Consumindo 15%+ acima" if acima else "✓ Todos no padrão",
                    delta_type="warn" if acima else "up"), unsafe_allow_html=True)
        except Exception:
            pass

    # ── KPI CUSTOS ──
    if "custos_kpi" in W:
        try:
            cst = _custos_filial()
            if cst:
                mg_vals = [float(d.get("percentualLucroProposta",0) or 0) for d in cst if d.get("percentualLucroProposta")]
                mg_med  = sum(mg_vals)/len(mg_vals) if mg_vals else 0
                st.markdown(kpi("Margem Média Filiais", fmt_pct(mg_med),
                    delta="⚠️ Abaixo de 5%" if mg_med < 5 else "✓ OK",
                    delta_type="warn" if mg_med < 5 else "up"), unsafe_allow_html=True)
        except Exception:
            pass

    # ── SEPARADOR ──
    if any(w in W for w in ["kpis_frota","kpis_financeiro","kpis_eficiencia","faturamento_kpi","combustivel_kpi","custos_kpi"]):
        st.divider()

    # ── LINHA DE GRÁFICOS ──
    graficos = [w for w in ["os_situacao","top_fornecedores","eficiencia_graf"] if w in W]
    if graficos and dados_base_ok:
        cols_graf = st.columns(min(len(graficos), 2))
        gi = 0

        if "os_situacao" in W and gi < len(cols_graf):
            with cols_graf[gi]:
                st.subheader("🔧 OS por Situação")
                if ro["por_situacao"]:
                    df = pd.DataFrame(list(ro["por_situacao"].items()), columns=["Situação","Qtde"])
                    fig = px.bar(df, x="Situação", y="Qtde", color="Qtde",
                                 color_continuous_scale=["#BDD0F0","#1A3C6E"], template="plotly_white")
                    fig.update_layout(showlegend=False, margin=dict(t=10,b=10))
                    st.plotly_chart(fig, use_container_width=True)
            gi += 1

        if "top_fornecedores" in W and gi < len(cols_graf):
            with cols_graf[gi]:
                st.subheader("🏭 Top Fornecedores")
                if rt["top_15_fornecedores"]:
                    df2 = pd.DataFrame(rt["top_15_fornecedores"][:10])
                    df2["vf"] = df2["valor"].apply(fmt_brl)
                    fig2 = px.bar(df2, x="valor", y="fornecedor", orientation="h",
                                  text="vf", color_discrete_sequence=["#1A3C6E"], template="plotly_white")
                    fig2.update_layout(showlegend=False, margin=dict(t=10))
                    st.plotly_chart(fig2, use_container_width=True)
            gi += 1

        if "eficiencia_graf" in W:
            try:
                ef = _eficiencia()
                if ef:
                    col_ef = st.columns(1)[0]
                    with col_ef:
                        st.subheader("⚙️ Eficiência por Equipamento")
                        df_ef = pd.DataFrame([{
                            "Equipamento": (d.get("equipamentoResumido") or {}).get("descricao","?")[:20],
                            "Eficiência %": float(d.get("eficiencia",0) or 0)*100,
                        } for d in ef]).sort_values("Eficiência %").tail(15)
                        fig_ef = px.bar(df_ef, x="Eficiência %", y="Equipamento", orientation="h",
                                        color="Eficiência %",
                                        color_continuous_scale=["#C0392B","#F39C12","#0A6E3F"],
                                        template="plotly_white")
                        fig_ef.add_vline(x=80, line_dash="dash", line_color="orange")
                        fig_ef.update_layout(showlegend=False)
                        st.plotly_chart(fig_ef, use_container_width=True)
            except Exception:
                pass

    # ── ALERTAS ──
    if "alertas" in W and dados_base_ok:
        st.subheader("⚠️ Alertas")
        alertas = []
        if re["seguros_vencidos"]:    alertas.append(("err",  f"🔴 {re['seguros_vencidos']} seguro(s) vencido(s)"))
        if ro["os_atrasadas"]:        alertas.append(("warn", f"🟡 {ro['os_atrasadas']} OS com prazo vencido"))
        if re["sem_num_patrimonial"]: alertas.append(("warn", f"🟡 {re['sem_num_patrimonial']} equip. sem nº patrimonial"))

        # Alertas dos novos módulos
        try:
            comb = _combustivel()
            acima = [d for d in comb if d.get("mediaObtida") and d.get("mediaDesejada")
                     and float(d.get("mediaObtida",0)) > float(d.get("mediaDesejada",0)) * 1.20]
            if acima: alertas.append(("warn", f"🟡 {len(acima)} equipamento(s) com consumo 20%+ acima do padrão"))
        except Exception: pass

        if not alertas: alertas.append(("ok", "✅ Nenhum alerta crítico"))
        for t, m in alertas:
            st.markdown(f'<div class="alert-box {t}">{m}</div>', unsafe_allow_html=True)

    # ── NAVEGAÇÃO ──
    if "navegacao" in W:
        st.divider()
        st.subheader("🗺️ Navegação Rápida")
        modulos = [
            ("💰","Pendências e Aging","Contas vencidas"),
            ("📊","Fluxo de Caixa","Previsto vs realizado"),
            ("📈","Faturamento Geral","Receita do período"),
            ("🛍️","Vendas com Margem","Margem por ticket"),
            ("🏗️","Custos por Filial","R$/Ton"),
            ("⚙️","Eficiência de Equipamentos","Disponibilidade"),
            ("⛽","Consumo de Combustível","Média vs padrão"),
            ("🎯","KPIs e Cruzamentos","Análises estratégicas"),
        ]
        cols_nav = st.columns(4)
        for idx, (emoji, mod, desc) in enumerate(modulos):
            with cols_nav[idx % 4]:
                st.button(f"{emoji} {mod}", key=f"nav_{mod}", use_container_width=True)
                st.caption(desc)


# ════════════════════════════════════════
#  PENDÊNCIAS E AGING
# ════════════════════════════════════════
elif pagina == "💰 Pendências e Aging":
    st.markdown("""<div class="main-header">
        <h1>💰 Pendências e Aging</h1>
        <p>Contas a pagar e receber — análise por vencimento</p></div>""", unsafe_allow_html=True)

    aba = st.radio("Visualizar", ["A Receber","A Pagar","Comparativo PMR/PMP"],
                   horizontal=True, label_visibility="collapsed")

    hoje_str  = datetime.now().strftime("%Y-%m-%d")
    d60_str   = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

    if aba in ["A Receber", "A Pagar"]:
        tipo = "RECEBER" if aba == "A Receber" else "PAGAR"
        cor_titulo = "#0A6E3F" if tipo == "RECEBER" else "#C0392B"

        col_f1, col_f2 = st.columns(2)
        with col_f1: venc_de = st.date_input("Vencimento de", value=datetime.now().replace(day=1))
        with col_f2: venc_ate = st.date_input("Vencimento até", value=datetime.now() + timedelta(days=60))

        if st.button(f"🔄 Carregar {aba}", use_container_width=False):
            st.session_state[f"pend_{tipo}"] = _pendencias(
                tipo, venc_de=venc_de.strftime("%Y-%m-%d"),
                venc_ate=venc_ate.strftime("%Y-%m-%d")
            )

        dados = st.session_state.get(f"pend_{tipo}", [])
        if not dados:
            st.info(f"👆 Clique em **Carregar {aba}** para buscar os dados.")
        else:
            try:
                df = pd.DataFrame(dados)
                tot_pend   = sum(float(d.get("valorPendenteFinal", d.get("valorPendente",0)) or 0) for d in dados)
                tot_juros  = sum(float(d.get("juros",0) or 0) for d in dados)
                tot_desc   = sum(float(d.get("desconto",0) or 0) for d in dados)
                vencidos   = [d for d in dados if float(d.get("diasVencimento",0) or 0) > 0]
                a_vencer   = [d for d in dados if float(d.get("diasVencimento",0) or 0) <= 0]

                c1,c2,c3,c4 = st.columns(4)
                with c1: st.markdown(kpi("Total Pendente", fmt_brl_m(tot_pend)), unsafe_allow_html=True)
                with c2: st.markdown(kpi("Documentos", len(dados)), unsafe_allow_html=True)
                with c3: st.markdown(kpi("Vencidos", len(vencidos),
                    delta="⚠️ Urgente" if vencidos else "✓ OK",
                    delta_type="warn" if vencidos else "up"), unsafe_allow_html=True)
                with c4: st.markdown(kpi("Juros Acumulados", fmt_brl_m(tot_juros),
                    delta="⚠️ Alto" if tot_juros > 5000 else "Normal",
                    delta_type="warn" if tot_juros > 5000 else "up"), unsafe_allow_html=True)

                st.divider()

                # Aging por faixa
                def faixa(d):
                    dias = float(d.get("diasVencimento",0) or 0)
                    if dias <= 0: return "A vencer"
                    elif dias <= 30: return "1-30 dias"
                    elif dias <= 60: return "31-60 dias"
                    elif dias <= 90: return "61-90 dias"
                    else: return "+90 dias"

                ca, cb = st.columns(2)
                with ca:
                    st.subheader("Aging por Faixa de Vencimento")
                    faixas = Counter(faixa(d) for d in dados)
                    ordem  = ["A vencer","1-30 dias","31-60 dias","61-90 dias","+90 dias"]
                    df_f = pd.DataFrame([(f, faixas.get(f,0)) for f in ordem], columns=["Faixa","Qtde"])
                    cores = {"A vencer":"#0A6E3F","1-30 dias":"#2C5F9E",
                             "31-60 dias":"#F39C12","61-90 dias":"#E67E22","+90 dias":"#C0392B"}
                    fig = px.bar(df_f, x="Faixa", y="Qtde", color="Faixa",
                                 color_discrete_map=cores, template="plotly_white")
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

                with cb:
                    st.subheader("Valor por Faixa (R$)")
                    val_faixa = {}
                    for d in dados:
                        f = faixa(d)
                        val_faixa[f] = val_faixa.get(f, 0) + float(d.get("valorPendenteFinal",d.get("valorPendente",0)) or 0)
                    df_v = pd.DataFrame([(f, val_faixa.get(f,0)) for f in ordem], columns=["Faixa","Valor"])
                    fig2 = px.bar(df_v, x="Faixa", y="Valor", color="Faixa",
                                  color_discrete_map=cores, template="plotly_white")
                    fig2.update_layout(showlegend=False)
                    fig2.update_traces(texttemplate="%{y:,.0f}", textposition="outside")
                    st.plotly_chart(fig2, use_container_width=True)

                # Top fornecedores/clientes
                st.subheader(f"Top {'Clientes' if tipo=='RECEBER' else 'Fornecedores'} por Valor Pendente")
                conc = {}
                for d in dados:
                    nome = d.get("nomeFornecedor","?")
                    conc[nome] = conc.get(nome,0) + float(d.get("valorPendenteFinal",d.get("valorPendente",0)) or 0)
                df_c = pd.DataFrame(sorted(conc.items(), key=lambda x:-x[1])[:15],
                                    columns=["Nome","Valor"])
                df_c["vf"] = df_c["Valor"].apply(fmt_brl)
                fig3 = px.bar(df_c, x="Valor", y="Nome", orientation="h", text="vf",
                              color_discrete_sequence=["#1A3C6E"], template="plotly_white")
                fig3.update_layout(showlegend=False)
                st.plotly_chart(fig3, use_container_width=True)

                # Tabela completa
                st.subheader("Listagem Completa")
                cols_show = ["nomeFornecedor","tipoDocumento","dataVencimento",
                             "valorPrincipal","valorPendenteFinal","juros","desconto","diasVencimento"]
                cols_ok = [c for c in cols_show if c in df.columns]
                flt = st.text_input("🔍 Filtrar")
                dfs = df[cols_ok].copy()
                if flt:
                    mask = dfs.apply(lambda r: r.astype(str).str.contains(flt, case=False).any(), axis=1)
                    dfs = dfs[mask]
                st.dataframe(dfs, use_container_width=True, height=350)
                csv = dfs.to_csv(index=False).encode("utf-8-sig")
                st.download_button("⬇️ Exportar CSV", data=csv,
                                   file_name=f"pendencias_{tipo.lower()}.csv", mime="text/csv")
            except Exception as e:
                st.error(f"Erro: {e}")

    else:  # PMR/PMP
        st.subheader("📊 PMR vs PMP — Gap de Capital de Giro")
        col_b1, col_b2 = st.columns(2)
        with col_b1: carregar_rec = st.button("🔄 Carregar Recebimentos", use_container_width=True)
        with col_b2: carregar_pag = st.button("🔄 Carregar Pagamentos",   use_container_width=True)

        if carregar_rec:
            st.session_state["rec_pmr"] = _recebimentos(inicio, fim)
        if carregar_pag:
            st.session_state["pag_pmp"] = _pagamentos(inicio, fim)

        rec = st.session_state.get("rec_pmr", [])
        pag = st.session_state.get("pag_pmp", [])

        if rec and pag:
            # Calcula PMR
            pmr_list = []
            for r in rec:
                try:
                    emissao = datetime.strptime(str(r.get("dataEmissao",""))[:10], "%Y-%m-%d")
                    baixa   = datetime.strptime(str(r.get("dataBaixa",""))[:10], "%Y-%m-%d")
                    pmr_list.append((baixa - emissao).days)
                except: pass
            pmr = sum(pmr_list)/len(pmr_list) if pmr_list else 0

            # Calcula PMP
            pmp_list = []
            for p in pag:
                try:
                    emissao = datetime.strptime(str(p.get("dataEmissao",""))[:10], "%Y-%m-%d")
                    baixa   = datetime.strptime(str(p.get("dataBaixa",""))[:10], "%Y-%m-%d")
                    pmp_list.append((baixa - emissao).days)
                except: pass
            pmp = sum(pmp_list)/len(pmp_list) if pmp_list else 0

            gap  = pmr - pmp
            tot_rec = sum(float(r.get("valorReceita",0) or 0) for r in rec)
            tot_pag = sum(float(p.get("valorDespesa",0) or 0) for p in pag)

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(kpi("PMR (dias)", f"{pmr:.0f}",
                delta="⚠️ Alto" if pmr > 35 else "✓ OK",
                delta_type="warn" if pmr > 35 else "up"), unsafe_allow_html=True)
            with c2: st.markdown(kpi("PMP (dias)", f"{pmp:.0f}",
                delta="⚠️ Baixo" if pmp < 20 else "✓ OK",
                delta_type="warn" if pmp < 20 else "up"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Gap (PMR-PMP)", f"{gap:.0f} dias",
                delta="⚠️ Precisar financiar" if gap > 0 else "✓ Paga depois de receber",
                delta_type="warn" if gap > 0 else "up"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Saldo Período", fmt_brl_m(tot_rec - tot_pag),
                delta="✓ Positivo" if tot_rec > tot_pag else "⚠️ Negativo",
                delta_type="up" if tot_rec > tot_pag else "warn"), unsafe_allow_html=True)

            fig = go.Figure()
            fig.add_trace(go.Bar(name="PMR — Recebimento", x=["Prazos"], y=[pmr],
                                  marker_color="#0A6E3F"))
            fig.add_trace(go.Bar(name="PMP — Pagamento", x=["Prazos"], y=[pmp],
                                  marker_color="#C0392B"))
            fig.add_annotation(x=0, y=max(pmr,pmp)+2,
                text=f"Gap: {gap:.0f} dias", showarrow=False,
                font=dict(size=14, color="#F39C12" if gap > 0 else "#0A6E3F"))
            fig.update_layout(template="plotly_white", barmode="group",
                title="PMR (Prazo Médio de Recebimento) vs PMP (Prazo Médio de Pagamento)")
            st.plotly_chart(fig, use_container_width=True)

            if gap > 0:
                msg_gap = f"a empresa precisa financiar {abs(gap):.0f} dias de capital de giro."
            else:
                msg_gap = "a empresa paga depois de receber — situação saudável."
            st.info(f"💡 **Interpretação:** Com PMR de {pmr:.0f} dias e PMP de {pmp:.0f} dias, {msg_gap}")
        else:
            st.info("👆 Carregue os dados de recebimentos e pagamentos para calcular PMR e PMP.")


# ════════════════════════════════════════
#  FLUXO DE CAIXA
# ════════════════════════════════════════
elif pagina == "📊 Fluxo de Caixa":
    st.markdown("""<div class="main-header">
        <h1>📊 Fluxo de Caixa</h1>
        <p>Previsto vs. Realizado por conta e filial</p></div>""", unsafe_allow_html=True)

    col_b, col_i = st.columns([1,3])
    with col_b: carregar = st.button("🔄 Carregar Fluxo", use_container_width=True)
    with col_i: st.caption("⚡ Busca previsto vs. realizado por conta de fluxo e filial.")

    if carregar:
        with st.spinner("Carregando fluxo de caixa..."):
            st.session_state["fluxo_dados"] = _fluxo_previsto(de=inicio, ate=fim)

    dados = st.session_state.get("fluxo_dados", [])
    if not dados:
        st.info("👆 Clique em **Carregar Fluxo** para buscar os dados.")
    else:
        try:
            df = pd.DataFrame(dados)
            tot_prev = sum(float(d.get("valorPrevisto",0) or 0) for d in dados)
            tot_real = sum(float(d.get("valorRealizado",0) or 0) for d in dados)
            tot_dif  = tot_real - tot_prev
            pct_real = (tot_real / tot_prev * 100) if tot_prev else 0

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(kpi("Previsto Total", fmt_brl_m(tot_prev)), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Realizado Total", fmt_brl_m(tot_real)), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Desvio", fmt_brl_m(tot_dif),
                delta="⚠️ Abaixo do previsto" if tot_dif < 0 else "✓ Acima do previsto",
                delta_type="warn" if tot_dif < 0 else "up"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Execução %", fmt_pct(pct_real),
                delta="⚠️ Baixo" if pct_real < 80 else "✓ OK",
                delta_type="warn" if pct_real < 80 else "up"), unsafe_allow_html=True)

            st.divider()

            # Agrupa por mês
            if "dataMes" in df.columns:
                df["dataMes"] = pd.to_datetime(df["dataMes"], errors="coerce")
                df["mes"] = df["dataMes"].dt.to_period("M").astype(str)
                df_mes = df.groupby("mes").agg(
                    previsto=("valorPrevisto","sum"),
                    realizado=("valorRealizado","sum")
                ).reset_index().sort_values("mes")

                ca, cb = st.columns(2)
                with ca:
                    st.subheader("Evolução Mensal: Previsto vs. Realizado")
                    fig = go.Figure()
                    fig.add_trace(go.Bar(name="Previsto",  x=df_mes["mes"], y=df_mes["previsto"],  marker_color="#BDD0F0"))
                    fig.add_trace(go.Bar(name="Realizado", x=df_mes["mes"], y=df_mes["realizado"], marker_color="#1A3C6E"))
                    fig.update_layout(template="plotly_white", barmode="group", legend=dict(orientation="h"))
                    st.plotly_chart(fig, use_container_width=True)

                with cb:
                    st.subheader("Desvio por Mês (R$)")
                    df_mes["desvio"] = df_mes["realizado"] - df_mes["previsto"]
                    cores_d = ["#C0392B" if v < 0 else "#0A6E3F" for v in df_mes["desvio"]]
                    fig2 = go.Figure(go.Bar(x=df_mes["mes"], y=df_mes["desvio"],
                                            marker_color=cores_d))
                    fig2.update_layout(template="plotly_white", showlegend=False)
                    fig2.add_hline(y=0, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig2, use_container_width=True)

            # Por filial
            if "filialResumidaDTO" in df.columns or "filial" in df.columns:
                col_filial = "filialResumidaDTO" if "filialResumidaDTO" in df.columns else "filial"
                df["nome_filial"] = df[col_filial].apply(
                    lambda x: x.get("nome","?") if isinstance(x,dict) else str(x))
                df_fil = df.groupby("nome_filial").agg(
                    previsto=("valorPrevisto","sum"),
                    realizado=("valorRealizado","sum")
                ).reset_index()
                df_fil["execucao_pct"] = (df_fil["realizado"]/df_fil["previsto"]*100).round(1)
                st.subheader("Por Filial")
                st.dataframe(df_fil.rename(columns={
                    "nome_filial":"Filial","previsto":"Previsto (R$)",
                    "realizado":"Realizado (R$)","execucao_pct":"Execução %"
                }), use_container_width=True, hide_index=True)

            # Tabela completa
            st.subheader("Detalhe por Conta de Fluxo")
            st.dataframe(df, use_container_width=True, height=350)
        except Exception as e:
            erro_generico(e)


# ════════════════════════════════════════
#  PAGAMENTOS E RECEBIMENTOS
# ════════════════════════════════════════
elif pagina == "💳 Pagamentos e Recebimentos":
    st.markdown(f"""<div class="main-header">
        <h1>💳 Pagamentos e Recebimentos</h1>
        <p>Efetivados no período · {label_periodo}</p></div>""", unsafe_allow_html=True)

    col_b1, col_b2 = st.columns(2)
    with col_b1: c_rec = st.button("🔄 Carregar Recebimentos", use_container_width=True)
    with col_b2: c_pag = st.button("🔄 Carregar Pagamentos",   use_container_width=True)

    if c_rec:
        with st.spinner("Buscando recebimentos..."):
            st.session_state["rec_ef"] = _recebimentos(inicio, fim)
    if c_pag:
        with st.spinner("Buscando pagamentos..."):
            st.session_state["pag_ef"] = _pagamentos(inicio, fim)

    rec = st.session_state.get("rec_ef", [])
    pag = st.session_state.get("pag_ef", [])

    if rec or pag:
        tot_rec = sum(float(r.get("valorReceita",0) or 0) for r in rec)
        tot_pag = sum(float(p.get("valorDespesa",0) or 0) for p in pag)
        saldo   = tot_rec - tot_pag

        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(kpi("Recebido", fmt_brl_m(tot_rec), delta=f"✓ {len(rec)} docs", delta_type="up"), unsafe_allow_html=True)
        with c2: st.markdown(kpi("Pago",     fmt_brl_m(tot_pag), delta=f"{len(pag)} docs"), unsafe_allow_html=True)
        with c3: st.markdown(kpi("Saldo Período", fmt_brl_m(saldo),
            delta="✓ Positivo" if saldo >= 0 else "⚠️ Negativo",
            delta_type="up" if saldo >= 0 else "warn"), unsafe_allow_html=True)
        with c4: st.markdown(kpi("Cobertura", fmt_pct(tot_rec/tot_pag*100 if tot_pag else 0),
            delta="✓ Recebeu mais" if tot_rec > tot_pag else "⚠️ Pagou mais",
            delta_type="up" if tot_rec > tot_pag else "warn"), unsafe_allow_html=True)

        st.divider()
        ca, cb = st.columns(2)
        with ca:
            if rec:
                st.subheader("Recebimentos por Fluxo de Caixa")
                fc = {}
                for r in rec:
                    k = r.get("descricaoFluxo","Outros") or "Outros"
                    fc[k] = fc.get(k,0) + float(r.get("valorReceita",0) or 0)
                df_fc = pd.DataFrame(sorted(fc.items(),key=lambda x:-x[1])[:10],
                                     columns=["Fluxo","Valor"])
                fig = px.bar(df_fc, x="Valor", y="Fluxo", orientation="h",
                             color_discrete_sequence=["#0A6E3F"], template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)

        with cb:
            if pag:
                st.subheader("Pagamentos por Fornecedor (Top 10)")
                fp = {}
                for p in pag:
                    forn = (p.get("fornecedor") or {})
                    nome = forn.get("nomeRazao") or forn.get("nomeFantasia","?") if isinstance(forn,dict) else "?"
                    fp[nome] = fp.get(nome,0) + float(p.get("valorDespesa",0) or 0)
                df_fp = pd.DataFrame(sorted(fp.items(),key=lambda x:-x[1])[:10],
                                     columns=["Fornecedor","Valor"])
                fig2 = px.bar(df_fp, x="Valor", y="Fornecedor", orientation="h",
                              color_discrete_sequence=["#C0392B"], template="plotly_white")
                st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("👆 Carregue os dados para visualizar.")


# ════════════════════════════════════════
#  FATURAMENTO GERAL
# ════════════════════════════════════════
elif pagina == "📈 Faturamento Geral":
    st.markdown(f"""<div class="main-header">
        <h1>📈 Faturamento Geral</h1>
        <p>NFe + NFS-e + Locação · {label_periodo}</p></div>""", unsafe_allow_html=True)

    col_b, _ = st.columns([1,3])
    with col_b: carregar = st.button("🔄 Carregar Faturamento", use_container_width=True)

    if carregar:
        with st.spinner("Carregando faturamento..."):
            st.session_state["fat_dados"]  = _faturamento(inicio, fim)
            st.session_state["nfe_dados"]  = _nfe(inicio, fim)
            st.session_state["nfse_dados"] = _nfse(inicio, fim)

    fat  = st.session_state.get("fat_dados",  [])
    nfe  = st.session_state.get("nfe_dados",  [])
    nfse = st.session_state.get("nfse_dados", [])

    if fat or nfe or nfse:
        try:
            tot_bruto  = sum(float(f.get("valorBruto",0) or 0) for f in fat)
            tot_liq    = sum(float(f.get("valorLiquido",0) or 0) for f in fat)
            tot_retido = sum(float(f.get("valorRetido",0) or 0) for f in fat)
            tot_nfe    = sum(float(n.get("valorTotalNFe",0) or 0) for n in nfe)
            tot_nfse   = sum(float(n.get("valorTotalServicos",0) or 0) for n in nfse)
            tot_iss    = sum(float(n.get("valorIssDevido",0) or 0) for n in nfse)

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.markdown(kpi("Faturamento Bruto", fmt_brl_m(tot_bruto)), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Faturamento Líquido", fmt_brl_m(tot_liq)), unsafe_allow_html=True)
            with c3: st.markdown(kpi("NF Produtos (NFe)", fmt_brl_m(tot_nfe)), unsafe_allow_html=True)
            with c4: st.markdown(kpi("NF Serviços (NFSe)", fmt_brl_m(tot_nfse)), unsafe_allow_html=True)
            with c5: st.markdown(kpi("ISS Devido", fmt_brl_m(tot_iss),
                delta=f"{(tot_iss/tot_nfse*100):.1f}% sobre serviços" if tot_nfse else "—"), unsafe_allow_html=True)

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Faturamento por Tipo de Movimento")
                if fat:
                    tipos = {}
                    for f in fat:
                        tm = (f.get("tipoMovimento") or {})
                        desc = tm.get("descricao","?") if isinstance(tm,dict) else "?"
                        tipos[desc] = tipos.get(desc,0) + float(f.get("valorBruto",0) or 0)
                    df_t = pd.DataFrame(sorted(tipos.items(),key=lambda x:-x[1]),
                                        columns=["Tipo","Valor"])
                    fig = px.pie(df_t, values="Valor", names="Tipo",
                                 color_discrete_sequence=px.colors.sequential.Blues_r,
                                 template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)

            with cb:
                st.subheader("Top Clientes — NFe Emitidas")
                if nfe:
                    cli_fat = {}
                    for n in nfe:
                        dest = n.get("destinatario") or {}
                        nome = dest.get("nomeRazao") or dest.get("nomeFantasia","?") if isinstance(dest,dict) else "?"
                        cli_fat[nome] = cli_fat.get(nome,0) + float(n.get("valorTotalNFe",0) or 0)
                    df_cli = pd.DataFrame(sorted(cli_fat.items(),key=lambda x:-x[1])[:10],
                                          columns=["Cliente","Valor"])
                    df_cli["vf"] = df_cli["Valor"].apply(fmt_brl)
                    fig2 = px.bar(df_cli, x="Valor", y="Cliente", orientation="h",
                                  text="vf", color_discrete_sequence=["#1A3C6E"],
                                  template="plotly_white")
                    fig2.update_layout(showlegend=False)
                    st.plotly_chart(fig2, use_container_width=True)

            # ICMS e DIFAL por UF
            if nfe:
                st.subheader("ICMS e DIFAL por UF de Destino")
                uf_icms = {}
                for n in nfe:
                    uf = n.get("uf","?") or "?"
                    uf_icms[uf] = uf_icms.get(uf,0) + float(n.get("valorICMS",0) or 0)
                df_uf = pd.DataFrame(sorted(uf_icms.items(),key=lambda x:-x[1]),
                                     columns=["UF","ICMS"])
                df_uf["vf"] = df_uf["ICMS"].apply(fmt_brl)
                fig3 = px.bar(df_uf.head(15), x="UF", y="ICMS", text="vf",
                              color_discrete_sequence=["#2C5F9E"], template="plotly_white")
                st.plotly_chart(fig3, use_container_width=True)
        except Exception as e:
            erro_generico(e)
    else:
        st.info("👆 Clique em **Carregar Faturamento** para buscar os dados.")


# ════════════════════════════════════════
#  VENDAS COM MARGEM
# ════════════════════════════════════════
elif pagina == "🛍️ Vendas com Margem":
    st.markdown(f"""<div class="main-header">
        <h1>🛍️ Vendas com Margem</h1>
        <p>Saída analítica — margem por ticket · {label_periodo}</p></div>""", unsafe_allow_html=True)

    col_b, col_i = st.columns([1,3])
    with col_b: carregar = st.button("🔄 Carregar Saídas", use_container_width=True)
    with col_i: st.caption("⚡ Dados de saída analítica com custo unitário e margem real por ticket.")

    if carregar:
        with st.spinner("Carregando saídas analíticas..."):
            st.session_state["saida_dados"] = _saida_analitico(inicio, fim)

    dados = st.session_state.get("saida_dados", [])
    if not dados:
        st.info("👆 Clique em **Carregar Saídas** para buscar os dados.")
    else:
        try:
            # Calcula margem por item
            for d in dados:
                preco = float(d.get("vlrUnitario",0) or 0)
                custo = float(d.get("custoUnitarioSaida",0) or 0)
                d["margem_unitaria"]  = preco - custo
                d["margem_pct"]       = ((preco-custo)/preco*100) if preco else 0
                d["receita_total"]    = float(d.get("valorTotal",0) or 0)
                d["custo_total_calc"] = custo * float(d.get("pesoLiquido",d.get("quantidade",1)) or 1)

            tot_rec  = sum(d["receita_total"] for d in dados)
            tot_peso = sum(float(d.get("pesoLiquido",0) or 0) for d in dados)
            margens  = [d["margem_pct"] for d in dados if d["margem_pct"] != 0]
            mg_media = sum(margens)/len(margens) if margens else 0
            dmt_list = [float(d.get("dmt",0) or 0) for d in dados if d.get("dmt")]
            dmt_med  = sum(dmt_list)/len(dmt_list) if dmt_list else 0

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.markdown(kpi("Tickets", len(dados)), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Receita Total", fmt_brl_m(tot_rec)), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Peso Líquido (t)", f"{tot_peso/1000:,.0f}"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Margem Média", fmt_pct(mg_media),
                delta="⚠️ Baixa" if mg_media < 10 else "✓ OK",
                delta_type="warn" if mg_media < 10 else "up"), unsafe_allow_html=True)
            with c5: st.markdown(kpi("DMT Médio (km)", f"{dmt_med:.1f}"), unsafe_allow_html=True)

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Margem por Material (%)")
                mat_mg = {}
                mat_vol = {}
                for d in dados:
                    mat = d.get("descricaoMaterial","?") or "?"
                    if mat not in mat_mg: mat_mg[mat] = []; mat_vol[mat] = 0
                    mat_mg[mat].append(d["margem_pct"])
                    mat_vol[mat] += float(d.get("pesoLiquido",0) or 0)
                df_mat = pd.DataFrame([
                    {"Material": k, "Margem %": sum(v)/len(v), "Volume (t)": mat_vol[k]/1000}
                    for k,v in mat_mg.items()
                ]).sort_values("Margem %", ascending=False).head(15)
                fig = px.bar(df_mat, x="Margem %", y="Material", orientation="h",
                             color="Margem %",
                             color_continuous_scale=["#C0392B","#F39C12","#0A6E3F"],
                             template="plotly_white")
                fig.add_vline(x=0, line_dash="dash", line_color="gray")
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with cb:
                st.subheader("Receita por Cliente (Top 10)")
                cli_rec = {}
                for d in dados:
                    nome = d.get("nomeRazaoCliente","?") or "?"
                    cli_rec[nome] = cli_rec.get(nome,0) + d["receita_total"]
                df_c = pd.DataFrame(sorted(cli_rec.items(),key=lambda x:-x[1])[:10],
                                    columns=["Cliente","Receita"])
                df_c["vf"] = df_c["Receita"].apply(fmt_brl)
                fig2 = px.bar(df_c, x="Receita", y="Cliente", orientation="h",
                              text="vf", color_discrete_sequence=["#1A3C6E"],
                              template="plotly_white")
                fig2.update_layout(showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

            # Frete vs receita
            st.subheader("Custo de Transporte vs Receita")
            fret_rec = {}
            for d in dados:
                mat = d.get("descricaoMaterial","?") or "?"
                fret_rec.setdefault(mat, {"frete":0,"receita":0})
                fret_rec[mat]["frete"]   += float(d.get("custoTransporteCliente",0) or 0)
                fret_rec[mat]["receita"] += d["receita_total"]
            df_fr = pd.DataFrame([
                {"Material": k, "Frete %": v["frete"]/v["receita"]*100 if v["receita"] else 0}
                for k,v in fret_rec.items()
            ]).sort_values("Frete %", ascending=False).head(12)
            fig3 = px.bar(df_fr, x="Material", y="Frete %",
                          color="Frete %", color_continuous_scale=["#BDD0F0","#F39C12","#C0392B"],
                          template="plotly_white")
            fig3.add_hline(y=12, line_dash="dash", line_color="red",
                           annotation_text="Meta máx 12%")
            st.plotly_chart(fig3, use_container_width=True)

            # Tabela
            st.subheader("Tickets do Período")
            df_tab = pd.DataFrame(dados)
            cols = [c for c in ["numeroTicket","data","nomeRazaoCliente","descricaoMaterial",
                                "nomeFilialMovimento","pesoLiquido","vlrUnitario",
                                "custoUnitarioSaida","margem_pct","receita_total","dmt"] if c in df_tab.columns]
            flt = st.text_input("🔍 Filtrar")
            dfs = df_tab[cols].copy()
            if flt:
                mask = dfs.apply(lambda r: r.astype(str).str.contains(flt,case=False).any(), axis=1)
                dfs = dfs[mask]
            st.dataframe(dfs, use_container_width=True, height=350)
            csv = dfs.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Exportar CSV", data=csv,
                               file_name="saidas_margin.csv", mime="text/csv")
        except Exception as e:
            erro_generico(e)


# ════════════════════════════════════════
#  CUSTOS POR FILIAL
# ════════════════════════════════════════
elif pagina == "🏗️ Custos por Filial":
    st.markdown("""<div class="main-header">
        <h1>🏗️ Custos por Filial</h1>
        <p>Previsto vs. Realizado · Margem · R$/Ton</p></div>""", unsafe_allow_html=True)

    col_b, _ = st.columns([1,3])
    with col_b: carregar = st.button("🔄 Carregar Custos", use_container_width=True)

    if carregar:
        with st.spinner("Carregando custos..."):
            st.session_state["custos_dados"] = _custos_filial()
            try: st.session_state["saida_r"] = _saida_analitico(inicio, fim)
            except: st.session_state["saida_r"] = []

    dados = st.session_state.get("custos_dados", [])
    saidas = st.session_state.get("saida_r", [])

    if not dados:
        st.info("👆 Clique em **Carregar Custos** para buscar os dados.")
    else:
        try:
            tot_desp = sum(float(d.get("valorDespesas",0) or 0) for d in dados)
            tot_fat  = sum(float(d.get("valorFaturamentoRealizado",0) or 0) for d in dados)
            tot_srv  = sum(float(d.get("valorServicosExecutadosRealizado",0) or 0) for d in dados)
            tot_adi  = sum(float(d.get("valorTotalAditivosContrato",0) or 0) for d in dados)
            mg_media = sum(float(d.get("percentualLucroProposta",0) or 0) for d in dados) / len(dados) if dados else 0

            # R$/Ton cruzamento
            tot_ton  = sum(float(d.get("pesoLiquido",0) or 0) for d in saidas) / 1000
            r_por_ton = tot_desp / tot_ton if tot_ton > 0 else 0

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.markdown(kpi("Despesas Totais", fmt_brl_m(tot_desp)), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Faturamento Real.", fmt_brl_m(tot_fat)), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Margem Média %", fmt_pct(mg_media),
                delta="⚠️ Baixa" if mg_media < 5 else "✓ OK",
                delta_type="warn" if mg_media < 5 else "up"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Aditivos Contratos", fmt_brl_m(tot_adi),
                delta="⚠️ Alto" if tot_adi > tot_fat*0.15 else "Normal",
                delta_type="warn" if tot_adi > tot_fat*0.15 else "up"), unsafe_allow_html=True)
            with c5: st.markdown(kpi("R$/Tonelada", f"R$ {r_por_ton:,.2f}" if r_por_ton else "—",
                delta="Custo por ton produzida" if r_por_ton else "Carregar saídas p/ calcular"),
                unsafe_allow_html=True)

            st.divider()

            # Por filial
            filiais = {}
            for d in dados:
                fil = d.get("nomeFilial","?") or "?"
                if fil not in filiais:
                    filiais[fil] = {"despesas":0,"faturamento":0,"servicos":0,"margem_list":[]}
                filiais[fil]["despesas"]    += float(d.get("valorDespesas",0) or 0)
                filiais[fil]["faturamento"] += float(d.get("valorFaturamentoRealizado",0) or 0)
                filiais[fil]["servicos"]    += float(d.get("valorServicosExecutadosRealizado",0) or 0)
                mg = float(d.get("percentualLucroProposta",0) or 0)
                if mg: filiais[fil]["margem_list"].append(mg)

            df_fil = pd.DataFrame([{
                "Filial": k,
                "Despesas (R$)": v["despesas"],
                "Faturamento (R$)": v["faturamento"],
                "Margem %": sum(v["margem_list"])/len(v["margem_list"]) if v["margem_list"] else 0,
            } for k,v in filiais.items()])

            ca, cb = st.columns(2)
            with ca:
                st.subheader("Faturamento vs Despesas por Filial")
                fig = go.Figure()
                fig.add_trace(go.Bar(name="Despesas",    x=df_fil["Filial"], y=df_fil["Despesas (R$)"],  marker_color="#C0392B"))
                fig.add_trace(go.Bar(name="Faturamento", x=df_fil["Filial"], y=df_fil["Faturamento (R$)"],marker_color="#0A6E3F"))
                fig.update_layout(template="plotly_white", barmode="group", legend=dict(orientation="h"))
                st.plotly_chart(fig, use_container_width=True)

            with cb:
                st.subheader("Margem % por Filial")
                fig2 = px.bar(df_fil, x="Filial", y="Margem %",
                              color="Margem %",
                              color_continuous_scale=["#C0392B","#F39C12","#0A6E3F"],
                              template="plotly_white")
                fig2.add_hline(y=5, line_dash="dash", line_color="red",
                               annotation_text="Meta mínima 5%")
                st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Tabela Detalhada por Filial")
            df_fil["Despesas (R$)"]    = df_fil["Despesas (R$)"].apply(fmt_brl)
            df_fil["Faturamento (R$)"] = df_fil["Faturamento (R$)"].apply(fmt_brl)
            df_fil["Margem %"]         = df_fil["Margem %"].apply(fmt_pct)
            st.dataframe(df_fil, use_container_width=True, hide_index=True)
        except Exception as e:
            erro_generico(e)


# ════════════════════════════════════════
#  PRODUÇÃO PREVISTO/REALIZADO
# ════════════════════════════════════════
elif pagina == "📋 Produção Previsto/Realizado":
    st.markdown("""<div class="main-header">
        <h1>📋 Produção Previsto/Realizado</h1>
        <p>Avanço físico-financeiro — Curva S</p></div>""", unsafe_allow_html=True)

    col_b, _ = st.columns([1,3])
    with col_b: carregar = st.button("🔄 Carregar Produção", use_container_width=True)

    if carregar:
        with st.spinner("Carregando produção..."):
            st.session_state["prod_dados"] = _producao()

    dados = st.session_state.get("prod_dados", [])
    if not dados:
        st.info("👆 Clique em **Carregar Produção** para buscar os dados.")
    else:
        try:
            df = pd.DataFrame(dados)
            tot_prev = sum(float(d.get("quantidadePrevista",0) or 0) for d in dados)
            tot_real = sum(float(d.get("quantidadeRealizada",0) or 0) for d in dados)
            val_prev = sum(float(d.get("valorPrevisto",0) or 0) for d in dados)
            val_real = sum(float(d.get("valorRealizado",0) or 0) for d in dados)
            exec_pct = (tot_real/tot_prev*100) if tot_prev else 0

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(kpi("Qtde Prevista", fmt_num(tot_prev)), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Qtde Realizada", fmt_num(tot_real)), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Execução Física %", fmt_pct(exec_pct),
                delta="⚠️ Atrasado" if exec_pct < 90 else "✓ OK",
                delta_type="warn" if exec_pct < 90 else "up"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Valor Real. vs Prev.", fmt_pct((val_real/val_prev*100) if val_prev else 0)), unsafe_allow_html=True)

            st.divider()
            if "data" in df.columns:
                df["data"] = pd.to_datetime(df["data"], errors="coerce")
                df["mes"] = df["data"].dt.to_period("M").astype(str)
                df_m = df.groupby("mes").agg(
                    prevista=("quantidadePrevista","sum"),
                    realizada=("quantidadeRealizada","sum")
                ).reset_index().sort_values("mes")

                ca, cb = st.columns(2)
                with ca:
                    st.subheader("Produção Mensal: Previsto vs Realizado")
                    fig = go.Figure()
                    fig.add_trace(go.Bar(name="Prevista",  x=df_m["mes"], y=df_m["prevista"],  marker_color="#BDD0F0"))
                    fig.add_trace(go.Bar(name="Realizada", x=df_m["mes"], y=df_m["realizada"], marker_color="#1A3C6E"))
                    fig.update_layout(template="plotly_white", barmode="group")
                    st.plotly_chart(fig, use_container_width=True)

                with cb:
                    st.subheader("Curva S — Cumula Realizado vs Previsto")
                    df_m["prev_cum"]  = df_m["prevista"].cumsum()
                    df_m["real_cum"]  = df_m["realizada"].cumsum()
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(name="Previsto Acumulado", x=df_m["mes"],
                                              y=df_m["prev_cum"], mode="lines+markers",
                                              line=dict(color="#BDD0F0", dash="dash")))
                    fig2.add_trace(go.Scatter(name="Realizado Acumulado", x=df_m["mes"],
                                              y=df_m["real_cum"], mode="lines+markers",
                                              line=dict(color="#1A3C6E")))
                    fig2.update_layout(template="plotly_white")
                    st.plotly_chart(fig2, use_container_width=True)

            # Por filial e serviço
            if "filial" in df.columns and "servico" in df.columns:
                st.subheader("Desvio por Serviço")
                df["desvio"] = df["quantidadeRealizada"].fillna(0) - df["quantidadePrevista"].fillna(0)
                df["desvio_pct"] = (df["desvio"]/df["quantidadePrevista"]*100).fillna(0)
                st.dataframe(df[["filial","servico","quantidadePrevista","quantidadeRealizada","desvio_pct"]].rename(columns={
                    "filial":"Filial","servico":"Serviço","quantidadePrevista":"Previsto",
                    "quantidadeRealizada":"Realizado","desvio_pct":"Desvio %"
                }), use_container_width=True, height=350)
        except Exception as e:
            erro_generico(e)


# ════════════════════════════════════════
#  MÃO DE OBRA
# ════════════════════════════════════════
elif pagina == "👷 Mão de Obra":
    st.markdown(f"""<div class="main-header">
        <h1>👷 Mão de Obra</h1>
        <p>Histograma — Previsto vs. Alocado por função · {label_periodo}</p></div>""", unsafe_allow_html=True)

    col_b, _ = st.columns([1,3])
    with col_b: carregar = st.button("🔄 Carregar Mão de Obra", use_container_width=True)

    if carregar:
        with st.spinner("Carregando histograma..."):
            st.session_state["mo_dados"] = _mao_obra(inicio, fim)

    dados = st.session_state.get("mo_dados", [])
    if not dados:
        st.info("👆 Clique em **Carregar Mão de Obra** para buscar os dados.")
    else:
        try:
            df = pd.DataFrame(dados)
            tot_prev = sum(float(d.get("quantidadePrevisto",0) or 0) for d in dados)
            tot_aloc = sum(float(d.get("quantidadeAlocado",0) or 0) for d in dados)
            gap      = tot_prev - tot_aloc
            exec_pct = (tot_aloc/tot_prev*100) if tot_prev else 0

            c1,c2,c3 = st.columns(3)
            with c1: st.markdown(kpi("Previsto (pessoas)", fmt_num(tot_prev)), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Alocado (pessoas)", fmt_num(tot_aloc)), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Gap", f"{gap:+.0f}",
                delta="⚠️ Falta pessoal" if gap > 0 else "✓ Coberto" if gap == 0 else "Excesso",
                delta_type="warn" if gap > 0 else "up"), unsafe_allow_html=True)

            # Por função
            if "funcao" in df.columns:
                df["funcao_nome"] = df["funcao"].apply(
                    lambda x: x.get("descricao","?") if isinstance(x,dict) else str(x))
                df_func = df.groupby("funcao_nome").agg(
                    previsto=("quantidadePrevisto","sum"),
                    alocado=("quantidadeAlocado","sum")
                ).reset_index()
                df_func["gap"] = df_func["previsto"] - df_func["alocado"]

                ca, cb = st.columns(2)
                with ca:
                    st.subheader("Previsto vs. Alocado por Função")
                    fig = go.Figure()
                    fig.add_trace(go.Bar(name="Previsto", x=df_func["funcao_nome"],
                                         y=df_func["previsto"], marker_color="#BDD0F0"))
                    fig.add_trace(go.Bar(name="Alocado",  x=df_func["funcao_nome"],
                                         y=df_func["alocado"],  marker_color="#1A3C6E"))
                    fig.update_layout(template="plotly_white", barmode="group",
                                      xaxis_tickangle=-30)
                    st.plotly_chart(fig, use_container_width=True)

                with cb:
                    st.subheader("Gap por Função (falta/excesso)")
                    cores_g = ["#C0392B" if g > 0 else "#0A6E3F" for g in df_func["gap"]]
                    fig2 = go.Figure(go.Bar(x=df_func["funcao_nome"], y=df_func["gap"],
                                            marker_color=cores_g))
                    fig2.add_hline(y=0, line_dash="dash", line_color="gray")
                    fig2.update_layout(template="plotly_white", showlegend=False,
                                       xaxis_tickangle=-30)
                    st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Dados Completos")
            st.dataframe(df, use_container_width=True, height=350)
        except Exception as e:
            erro_generico(e)


# ════════════════════════════════════════
#  DESPESAS ANALÍTICAS
# ════════════════════════════════════════
elif pagina == "💸 Despesas Analíticas":
    st.markdown(f"""<div class="main-header">
        <h1>💸 Despesas Analíticas</h1>
        <p>Rastreio diário de cada despesa · {label_periodo}</p></div>""", unsafe_allow_html=True)

    col_b, _ = st.columns([1,3])
    with col_b: carregar = st.button("🔄 Carregar Despesas", use_container_width=True)

    if carregar:
        with st.spinner("Carregando despesas..."):
            st.session_state["desp_dados"] = _despesas(inicio, fim)

    dados = st.session_state.get("desp_dados", [])
    if not dados:
        st.info("👆 Clique em **Carregar Despesas** para buscar os dados.")
    else:
        try:
            tot = sum(float(d.get("valor",0) or 0) for d in dados)
            df  = pd.DataFrame(dados)

            c1,c2 = st.columns(2)
            with c1: st.markdown(kpi("Total Despesas", fmt_brl_m(tot)), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Lançamentos", len(dados)), unsafe_allow_html=True)

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Por Conta MOB")
                if "contaMob" in df.columns:
                    df["conta_nome"] = df["contaMob"].apply(
                        lambda x: x.get("descricao","?") if isinstance(x,dict) else "?")
                    cnt = df.groupby("conta_nome")["valor"].sum().reset_index()
                    cnt = cnt.sort_values("valor", ascending=False).head(12)
                    fig = px.bar(cnt, x="valor", y="conta_nome", orientation="h",
                                 color_discrete_sequence=["#2C5F9E"], template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)

            with cb:
                st.subheader("Por Tipo de Movimento")
                if "tipoMovimento" in df.columns:
                    tm = df.groupby("tipoMovimento")["valor"].sum().reset_index()
                    fig2 = px.pie(tm, values="valor", names="tipoMovimento",
                                  template="plotly_white",
                                  color_discrete_sequence=px.colors.sequential.Blues_r)
                    st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Lançamentos Analíticos")
            cols = [c for c in ["data","descricao","valor","origem","tipoMovimento",
                                 "fornecedor"] if c in df.columns]
            flt = st.text_input("🔍 Filtrar")
            dfs = df[cols].copy()
            if flt:
                mask = dfs.apply(lambda r: r.astype(str).str.contains(flt,case=False).any(), axis=1)
                dfs = dfs[mask]
            st.dataframe(dfs, use_container_width=True, height=400)
            csv = dfs.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Exportar CSV", csv, "despesas.csv", "text/csv")
        except Exception as e:
            erro_generico(e)


# ════════════════════════════════════════
#  EFICIÊNCIA DE EQUIPAMENTOS
# ════════════════════════════════════════
elif pagina == "⚙️ Eficiência de Equipamentos":
    st.markdown("""<div class="main-header">
        <h1>⚙️ Eficiência de Equipamentos</h1>
        <p>Disponibilidade · Perdas (1-5) · Situação</p></div>""", unsafe_allow_html=True)

    col_b, _ = st.columns([1,3])
    with col_b: carregar = st.button("🔄 Carregar Eficiência", use_container_width=True)

    if carregar:
        with st.spinner("Carregando eficiência..."):
            st.session_state["efic_dados"] = _eficiencia()

    dados = st.session_state.get("efic_dados", [])
    if not dados:
        st.info("👆 Clique em **Carregar Eficiência** para buscar os dados.")
    else:
        try:
            efics = [float(d.get("eficiencia",0) or 0) for d in dados]
            horas = [float(d.get("horasMes",0) or 0) for d in dados]
            disp  = [float(d.get("horasDisponiveis",0) or 0) for d in dados]
            ef_med = sum(efics)/len(efics) if efics else 0
            tot_h  = sum(horas)
            tot_d  = sum(disp)

            situacoes = Counter(d.get("situacao","?") for d in dados)
            ativos    = situacoes.get("ATIVO",0)

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.markdown(kpi("Equipamentos", len(dados)), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Ativos", ativos), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Eficiência Média", fmt_pct(ef_med),
                delta="⚠️ Baixa" if ef_med < 80 else "✓ OK",
                delta_type="warn" if ef_med < 80 else "up"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Horas Trabalhadas", fmt_num(tot_h)), unsafe_allow_html=True)
            with c5: st.markdown(kpi("Horas Disponíveis", fmt_num(tot_d)), unsafe_allow_html=True)

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Eficiência por Equipamento (Top/Bottom)")
                df_ef = pd.DataFrame([{
                    "Equipamento": (d.get("equipamentoResumido") or {}).get("descricao","?"),
                    "Eficiência %": float(d.get("eficiencia",0) or 0),
                    "Situação": d.get("situacao","?"),
                } for d in dados]).sort_values("Eficiência %", ascending=False)
                fig = px.bar(df_ef.head(20), x="Eficiência %", y="Equipamento",
                             orientation="h", color="Eficiência %",
                             color_continuous_scale=["#C0392B","#F39C12","#0A6E3F"],
                             template="plotly_white")
                fig.add_vline(x=80, line_dash="dash", line_color="orange",
                              annotation_text="Meta 80%")
                st.plotly_chart(fig, use_container_width=True)

            with cb:
                st.subheader("Distribuição de Perdas")
                tot_perdas = {}
                for i in range(1,6):
                    key = f"perda{i}"
                    tot = sum(float(d.get(key,0) or 0) for d in dados)
                    if tot > 0: tot_perdas[f"Perda {i}"] = tot
                if tot_perdas:
                    df_p = pd.DataFrame(list(tot_perdas.items()), columns=["Tipo","Horas"])
                    fig2 = px.pie(df_p, values="Horas", names="Tipo",
                                  template="plotly_white",
                                  color_discrete_sequence=px.colors.sequential.Reds_r)
                    st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Por Situação")
            df_sit = pd.DataFrame(list(situacoes.items()), columns=["Situação","Qtde"])
            fig3 = px.bar(df_sit.sort_values("Qtde",ascending=False), x="Situação", y="Qtde",
                          color_discrete_sequence=["#2C5F9E"], template="plotly_white")
            st.plotly_chart(fig3, use_container_width=True)

            # Tabela
            df_tab = pd.DataFrame([{
                "Equipamento": (d.get("equipamentoResumido") or {}).get("descricao","?"),
                "Placa":       (d.get("equipamentoResumido") or {}).get("placa",""),
                "Eficiência %": float(d.get("eficiencia",0) or 0),
                "Horas Mês":   float(d.get("horasMes",0) or 0),
                "Horas Disp.": float(d.get("horasDisponiveis",0) or 0),
                "Perda 1": float(d.get("perda1",0) or 0),
                "Perda 2": float(d.get("perda2",0) or 0),
                "Situação": d.get("situacao","?"),
            } for d in dados])
            flt = st.text_input("🔍 Filtrar equipamento")
            dfs = df_tab.copy()
            if flt:
                mask = dfs.apply(lambda r: r.astype(str).str.contains(flt,case=False).any(), axis=1)
                dfs = dfs[mask]
            st.dataframe(dfs, use_container_width=True, height=350)
            csv = dfs.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Exportar CSV", csv, "eficiencia.csv", "text/csv")
        except Exception as e:
            erro_generico(e)


# ════════════════════════════════════════
#  COMBUSTÍVEL
# ════════════════════════════════════════
elif pagina == "⛽ Consumo de Combustível":
    st.markdown("""<div class="main-header">
        <h1>⛽ Consumo de Combustível</h1>
        <p>Média obtida vs. desejada por equipamento</p></div>""", unsafe_allow_html=True)

    col_b, _ = st.columns([1,3])
    with col_b: carregar = st.button("🔄 Carregar Combustível", use_container_width=True)

    if carregar:
        with st.spinner("Carregando consumo..."):
            st.session_state["comb_dados"] = _combustivel()

    dados = st.session_state.get("comb_dados", [])
    if not dados:
        st.info("👆 Clique em **Carregar Combustível** para buscar os dados.")
    else:
        try:
            tot_litros   = sum(float(d.get("quantidade",0) or 0) for d in dados)
            medias_obt   = [float(d.get("mediaObtida",0) or 0) for d in dados if d.get("mediaObtida")]
            medias_des   = [float(d.get("mediaDesejada",0) or 0) for d in dados if d.get("mediaDesejada")]
            med_obt_avg  = sum(medias_obt)/len(medias_obt) if medias_obt else 0
            med_des_avg  = sum(medias_des)/len(medias_des) if medias_des else 0
            desvio_pct   = ((med_obt_avg - med_des_avg) / med_des_avg * 100) if med_des_avg else 0

            # Equipamentos acima de 15% do padrão
            acima_padrao = [d for d in dados
                            if d.get("mediaObtida") and d.get("mediaDesejada") and
                            float(d.get("mediaObtida",0)) > float(d.get("mediaDesejada",0)) * 1.15]

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(kpi("Total Litros", f"{tot_litros:,.0f}"), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Média Obtida", f"{med_obt_avg:.1f}"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Média Desejada", f"{med_des_avg:.1f}"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Desvio %", fmt_pct(desvio_pct),
                delta="⚠️ Consome acima do padrão" if desvio_pct > 10 else "✓ OK",
                delta_type="warn" if desvio_pct > 10 else "up"), unsafe_allow_html=True)

            if acima_padrao:
                st.markdown(f'<div class="alert-box warn">⚠️ {len(acima_padrao)} equipamento(s) consumindo 15%+ acima do padrão</div>',
                            unsafe_allow_html=True)

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Média Obtida vs. Desejada por Equipamento")
                df_c = pd.DataFrame([{
                    "Equipamento": (d.get("equipamento") or {}).get("descricao","?")[:25],
                    "Obtida": float(d.get("mediaObtida",0) or 0),
                    "Desejada": float(d.get("mediaDesejada",0) or 0),
                } for d in dados if d.get("mediaObtida")]).sort_values("Obtida", ascending=False).head(20)
                fig = go.Figure()
                fig.add_trace(go.Bar(name="Obtida",   x=df_c["Equipamento"], y=df_c["Obtida"],  marker_color="#F39C12"))
                fig.add_trace(go.Bar(name="Desejada", x=df_c["Equipamento"], y=df_c["Desejada"],marker_color="#1A3C6E"))
                fig.update_layout(template="plotly_white", barmode="group", xaxis_tickangle=-30)
                st.plotly_chart(fig, use_container_width=True)

            with cb:
                st.subheader("⚠️ Equipamentos Acima do Padrão (>115%)")
                if acima_padrao:
                    df_a = pd.DataFrame([{
                        "Equipamento": (d.get("equipamento") or {}).get("descricao","?")[:25],
                        "Obtida": float(d.get("mediaObtida",0) or 0),
                        "Desejada": float(d.get("mediaDesejada",0) or 0),
                        "Desvio %": ((float(d.get("mediaObtida",0))/float(d.get("mediaDesejada",1))-1)*100),
                    } for d in acima_padrao]).sort_values("Desvio %", ascending=False)
                    st.dataframe(df_a, use_container_width=True)
                else:
                    st.success("✅ Nenhum equipamento com desvio acima de 15%")
        except Exception as e:
            erro_generico(e)


# ════════════════════════════════════════
#  MANUTENÇÃO E OFICINA
# ════════════════════════════════════════
elif pagina == "🔧 Manutenção e Oficina":
    st.markdown(f"""<div class="main-header">
        <h1>🔧 Manutenção e Oficina</h1>
        <p>OS · Oficina · MTBF · MTTR · {label_periodo}</p></div>""", unsafe_allow_html=True)

    col_b1, col_b2 = st.columns(2)
    with col_b1: c_os  = st.button("🔄 Carregar OS Manutenção", use_container_width=True)
    with col_b2: c_of  = st.button("🔄 Carregar Oficina",       use_container_width=True)

    if c_os:
        with st.spinner("Carregando OS..."):
            st.session_state["os_bi_dados"] = _os_bi(inicio, fim)
    if c_of:
        with st.spinner("Carregando oficina..."):
            st.session_state["ofic_dados"] = _oficina(inicio, fim)

    os_dados   = st.session_state.get("os_bi_dados", [])
    ofic_dados = st.session_state.get("ofic_dados", [])

    if os_dados or ofic_dados:
        # KPIs
        hoje = datetime.now().date()
        atrasadas = []
        if os_dados:
            for o in os_dados:
                prev = str(o.get("dataPrevisaoConclusao",""))[:10]
                sit  = str(o.get("situacaoOSM","")).lower()
                if prev and prev < str(hoje) and "conclu" not in sit and "cancel" not in sit:
                    atrasadas.append(o)

        por_tipo = Counter(
            (o.get("tipoOSM") or {}).get("descricao","?") if isinstance(o.get("tipoOSM"),dict)
            else str(o.get("tipoOSM","?"))
            for o in os_dados
        )

        # MTTR da oficina
        tempos = []
        for of in ofic_dados:
            try:
                ch = datetime.strptime(str(of.get("dataChegada",""))[:10], "%Y-%m-%d")
                cs = datetime.strptime(str(of.get("dataSaida",""))[:10], "%Y-%m-%d")
                tempos.append((cs-ch).days)
            except: pass
        mttr = sum(tempos)/len(tempos) if tempos else 0

        custo_of = sum(float(of.get("custoSolucao",0) or 0) for of in ofic_dados)

        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: st.markdown(kpi("OS Abertas", len(os_dados)), unsafe_allow_html=True)
        with c2: st.markdown(kpi("Atrasadas", len(atrasadas),
            delta="⚠️ Urgente" if atrasadas else "✓ OK",
            delta_type="warn" if atrasadas else "up"), unsafe_allow_html=True)
        with c3: st.markdown(kpi("MTTR (dias)", f"{mttr:.1f}",
            delta="⚠️ Alto" if mttr > 5 else "✓ OK",
            delta_type="warn" if mttr > 5 else "up"), unsafe_allow_html=True)
        with c4: st.markdown(kpi("Custo Oficina", fmt_brl_m(custo_of)), unsafe_allow_html=True)
        with c5:
            prev_pct = (por_tipo.get("Preventiva",0)+por_tipo.get("PREVENTIVA",0))/len(os_dados)*100 if os_dados else 0
            st.markdown(kpi("% Preventiva", fmt_pct(prev_pct),
                delta="⚠️ Abaixo de 60%" if prev_pct < 60 else "✓ OK",
                delta_type="warn" if prev_pct < 60 else "up"), unsafe_allow_html=True)

        st.divider()
        ca, cb = st.columns(2)
        with ca:
            if os_dados:
                st.subheader("OS por Tipo")
                df_t = pd.DataFrame(list(por_tipo.items()), columns=["Tipo","Qtde"])
                fig = px.pie(df_t, values="Qtde", names="Tipo",
                             color_discrete_sequence=px.colors.sequential.Blues_r,
                             template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)

        with cb:
            if ofic_dados:
                st.subheader("Top Equipamentos por Custo de Oficina")
                eq_custo = {}
                for of in ofic_dados:
                    eq = (of.get("equipamento") or {}).get("descricao","?")[:25]
                    eq_custo[eq] = eq_custo.get(eq,0) + float(of.get("custoSolucao",0) or 0)
                df_eq = pd.DataFrame(sorted(eq_custo.items(),key=lambda x:-x[1])[:10],
                                     columns=["Equipamento","Custo"])
                df_eq["vf"] = df_eq["Custo"].apply(fmt_brl)
                fig2 = px.bar(df_eq, x="Custo", y="Equipamento", orientation="h",
                              text="vf", color_discrete_sequence=["#C0392B"],
                              template="plotly_white")
                fig2.update_layout(showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

        if atrasadas:
            st.subheader("⚠️ OS Atrasadas")
            df_at = pd.DataFrame([{
                "OS": o.get("numeroOSM",""),
                "Equipamento": (o.get("equipamento") or {}).get("descricao","?"),
                "Defeito": o.get("defeitoOSM",""),
                "Prev. Conclusão": o.get("dataPrevisaoConclusao",""),
                "Situação": (o.get("situacaoOSM") or {}).get("descricao","?"),
            } for o in atrasadas])
            st.dataframe(df_at, use_container_width=True)
    else:
        st.info("👆 Carregue OS de Manutenção e/ou dados de Oficina.")


# ════════════════════════════════════════
#  FROTA — CADASTRO (legado melhorado)
# ════════════════════════════════════════
elif pagina == "🚜 Frota — Cadastro":
    st.markdown(f"""<div class="main-header">
        <h1>🚜 Frota — Cadastro</h1>
        <p>Patrimônio · Seguros · Horímetros · {label_periodo}</p></div>""", unsafe_allow_html=True)
    with st.spinner("Carregando equipamentos..."):
        try:
            from resumidor import resumir_equipamentos
            equip = _equipamentos()
            res   = resumir_equipamentos(equip)

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.markdown(kpi("Total",            res["total_equipamentos"]), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Valor Aquisição",  f"R${res['valor_aquisicao_total']/1e6:.1f}M"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Depreciação",       fmt_pct(res["depreciacao_pct"]),
                delta="⚠️ Alto" if res["depreciacao_pct"]>60 else "Normal",
                delta_type="warn" if res["depreciacao_pct"]>60 else "up"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Seguros Vencidos",  res["seguros_vencidos"],
                delta="⚠️ Urgente" if res["seguros_vencidos"] else "✓ OK",
                delta_type="warn" if res["seguros_vencidos"] else "up"), unsafe_allow_html=True)
            with c5: st.markdown(kpi("De Terceiros",      res["de_subempreiteiros"]), unsafe_allow_html=True)

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
                    fig.update_layout(yaxis=dict(categoryorder="total ascending"), showlegend=False)
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
            erro_generico(e)


# ════════════════════════════════════════
#  COMPRAS OC/OS ANALÍTICO
# ════════════════════════════════════════
elif pagina == "🛒 Compras OC/OS Analítico":
    st.markdown(f"""<div class="main-header">
        <h1>🛒 Compras OC/OS Analítico</h1>
        <p>Ordens de Compra · Fornecedores · Lead Time · {label_periodo}</p></div>""", unsafe_allow_html=True)

    col_b, _ = st.columns([1,3])
    with col_b: carregar = st.button("🔄 Carregar Compras", use_container_width=True)

    if carregar:
        with st.spinner("Carregando OC/OS..."):
            st.session_state["oc_dados"] = _oc_os(inicio, fim)

    dados = st.session_state.get("oc_dados", [])
    if not dados:
        st.info("👆 Clique em **Carregar Compras** para buscar os dados.")
    else:
        try:
            tot_bruto = sum(float(d.get("valorTotalBruto",0) or 0) for d in dados)
            tot_desc  = sum(float(d.get("valorDescontoPorItem",0) or 0) for d in dados)
            n_forn    = len(set((d.get("fornecedor") or {}).get("nomeRazao","?") for d in dados if d.get("fornecedor")))

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(kpi("Total OC/OS", len(dados)), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Valor Total", fmt_brl_m(tot_bruto)), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Descontos", fmt_brl_m(tot_desc),
                delta=f"{(tot_desc/tot_bruto*100):.1f}% do total" if tot_bruto else ""), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Fornecedores Únicos", n_forn), unsafe_allow_html=True)

            st.divider()
            ca, cb = st.columns(2)
            with ca:
                st.subheader("Top Fornecedores por Valor")
                forn_v = {}
                for d in dados:
                    f = (d.get("fornecedor") or {})
                    nome = f.get("nomeRazao") or f.get("nomeFantasia","?") if isinstance(f,dict) else "?"
                    forn_v[nome] = forn_v.get(nome,0) + float(d.get("valorTotalBruto",0) or 0)
                df_f = pd.DataFrame(sorted(forn_v.items(),key=lambda x:-x[1])[:12],
                                    columns=["Fornecedor","Valor"])
                df_f["vf"] = df_f["Valor"].apply(fmt_brl)
                fig = px.bar(df_f, x="Valor", y="Fornecedor", orientation="h",
                             text="vf", color_discrete_sequence=["#4A235A"],
                             template="plotly_white")
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with cb:
                st.subheader("Por Grupo de Insumo")
                gi_v = {}
                for d in dados:
                    gi = d.get("grupoInsumo","Sem grupo") or "Sem grupo"
                    gi_v[gi] = gi_v.get(gi,0) + float(d.get("valorTotalBruto",0) or 0)
                df_gi = pd.DataFrame(sorted(gi_v.items(),key=lambda x:-x[1])[:10],
                                     columns=["Grupo","Valor"])
                fig2 = px.pie(df_gi, values="Valor", names="Grupo",
                              template="plotly_white",
                              color_discrete_sequence=px.colors.sequential.Purples_r)
                st.plotly_chart(fig2, use_container_width=True)

            # Concentração de fornecedor
            if forn_v:
                tot_comp = sum(forn_v.values())
                top1_nome = max(forn_v, key=forn_v.get)
                top1_pct  = forn_v[top1_nome]/tot_comp*100 if tot_comp else 0
                if top1_pct > 40:
                    st.markdown(f'<div class="alert-box warn">⚠️ Concentração: <b>{top1_nome}</b> representa {top1_pct:.1f}% das compras — risco de dependência</div>',
                                unsafe_allow_html=True)

            # Tabela
            st.subheader("Listagem OC/OS")
            df_tab = pd.DataFrame([{
                "N° OC/OS":    d.get("numeroOcOs",""),
                "Tipo":        d.get("tipo",""),
                "Fornecedor":  (d.get("fornecedor") or {}).get("nomeRazao","?")[:30],
                "Material":    (d.get("material") or {}).get("descricao","?")[:30],
                "Grupo Insumo":d.get("grupoInsumo",""),
                "Data":        d.get("dataOcOs",""),
                "Valor Bruto": float(d.get("valorTotalBruto",0) or 0),
                "Desconto":    float(d.get("valorDescontoPorItem",0) or 0),
                "Situação":    (d.get("situacao") or {}).get("descricao","?"),
                "Filial Aplic.":(d.get("filialAplicacao") or {}).get("nome","?"),
            } for d in dados])
            flt = st.text_input("🔍 Filtrar")
            dfs = df_tab.copy()
            if flt:
                mask = dfs.apply(lambda r: r.astype(str).str.contains(flt,case=False).any(), axis=1)
                dfs = dfs[mask]
            st.dataframe(dfs, use_container_width=True, height=400)
            csv = dfs.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Exportar CSV", csv, "compras_oc_os.csv", "text/csv")
        except Exception as e:
            erro_generico(e)


# ════════════════════════════════════════
#  KPIs E CRUZAMENTOS
# ════════════════════════════════════════
elif pagina == "🎯 KPIs e Cruzamentos":
    st.markdown(f"""<div class="main-header">
        <h1>🎯 KPIs e Cruzamentos Estratégicos</h1>
        <p>Análises que cruzam múltiplos módulos · {label_periodo}</p></div>""", unsafe_allow_html=True)

    st.info("💡 **Como usar:** Carregue os dados dos módulos individuais primeiro, depois volte aqui para ver os cruzamentos calculados automaticamente.")

    tab1, tab2, tab3 = st.tabs(["💰 Financeiro", "🏗️ Custos e Produção", "🚜 Frota"])

    with tab1:
        st.subheader("PMR vs PMP — Capital de Giro")
        rec = st.session_state.get("rec_ef", st.session_state.get("rec_pmr", []))
        pag = st.session_state.get("pag_ef", st.session_state.get("pag_pmp", []))
        if rec and pag:
            pmr_list, pmp_list = [], []
            for r in rec:
                try:
                    e = datetime.strptime(str(r.get("dataEmissao",""))[:10], "%Y-%m-%d")
                    b = datetime.strptime(str(r.get("dataBaixa",""))[:10], "%Y-%m-%d")
                    pmr_list.append((b-e).days)
                except: pass
            for p in pag:
                try:
                    e = datetime.strptime(str(p.get("dataEmissao",""))[:10], "%Y-%m-%d")
                    b = datetime.strptime(str(p.get("dataBaixa",""))[:10], "%Y-%m-%d")
                    pmp_list.append((b-e).days)
                except: pass
            pmr = sum(pmr_list)/len(pmr_list) if pmr_list else 0
            pmp = sum(pmp_list)/len(pmp_list) if pmp_list else 0
            gap = pmr - pmp
            tot_rec = sum(float(r.get("valorReceita",0) or 0) for r in rec)
            giro_needed = tot_rec * gap / 30 if gap > 0 else 0

            c1,c2,c3 = st.columns(3)
            with c1: st.markdown(kpi("PMR (dias)", f"{pmr:.0f}"), unsafe_allow_html=True)
            with c2: st.markdown(kpi("PMP (dias)", f"{pmp:.0f}"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Capital de Giro Necessário", fmt_brl_m(giro_needed),
                delta=f"Gap de {gap:.0f} dias",
                delta_type="warn" if gap > 0 else "up"), unsafe_allow_html=True)
        else:
            st.warning("⚠️ Carregue Pagamentos e Recebimentos no módulo **💳 Pagamentos e Recebimentos**")

        st.divider()
        st.subheader("Faturamento vs. Inadimplência")
        fat  = st.session_state.get("fat_dados", [])
        pend = st.session_state.get("pend_RECEBER", [])
        if fat and pend:
            tot_fat  = sum(float(f.get("valorBruto",0) or 0) for f in fat)
            tot_inad = sum(float(p.get("valorPendenteFinal",p.get("valorPendente",0)) or 0)
                           for p in pend if float(p.get("diasVencimento",0) or 0) > 30)
            pct_inad = (tot_inad/tot_fat*100) if tot_fat else 0
            c1,c2 = st.columns(2)
            with c1: st.markdown(kpi("Faturamento", fmt_brl_m(tot_fat)), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Inadimplência >30d", fmt_brl_m(tot_inad),
                delta=f"⚠️ {pct_inad:.1f}% do faturamento" if pct_inad > 5 else f"✓ {pct_inad:.1f}%",
                delta_type="warn" if pct_inad > 5 else "up"), unsafe_allow_html=True)
        else:
            st.warning("⚠️ Carregue Faturamento e Pendências para este cruzamento.")

    with tab2:
        st.subheader("🏆 R$/Tonelada por Filial")
        custos = st.session_state.get("custos_dados", [])
        saidas = st.session_state.get("saida_dados", [])
        if custos and saidas:
            # Agrupa custos por filial
            c_fil = {}
            for c in custos:
                fil = c.get("nomeFilial","?") or "?"
                c_fil[fil] = c_fil.get(fil,0) + float(c.get("valorDespesas",0) or 0)

            # Agrupa volume por filial
            v_fil = {}
            for s in saidas:
                fil = s.get("nomeFilialMovimento","?") or "?"
                v_fil[fil] = v_fil.get(fil,0) + float(s.get("pesoLiquido",0) or 0)

            rows = []
            for fil in set(list(c_fil.keys()) + list(v_fil.keys())):
                custo = c_fil.get(fil,0)
                ton   = v_fil.get(fil,0) / 1000
                rpt   = custo/ton if ton > 0 else 0
                rows.append({"Filial":fil,"Custo (R$)":custo,"Volume (ton)":ton,"R$/Ton":rpt})

            df_rpt = pd.DataFrame(rows).sort_values("R$/Ton")
            fig = px.bar(df_rpt, x="Filial", y="R$/Ton", color="R$/Ton",
                         color_continuous_scale=["#0A6E3F","#F39C12","#C0392B"],
                         template="plotly_white", text="R$/Ton")
            fig.update_traces(texttemplate="R$ %{y:.0f}", textposition="outside")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_rpt.assign(**{"Custo (R$)": df_rpt["Custo (R$)"].apply(fmt_brl),
                                          "Volume (ton)": df_rpt["Volume (ton)"].apply(lambda x: f"{x:,.0f}"),
                                          "R$/Ton": df_rpt["R$/Ton"].apply(lambda x: f"R$ {x:,.2f}")}),
                         use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Carregue **Custos por Filial** e **Vendas com Margem** para calcular R$/Ton.")

        st.divider()
        st.subheader("Produção Realizada vs. Faturamento")
        prod = st.session_state.get("prod_dados", [])
        if prod and fat:
            tot_prod_val = sum(float(d.get("valorRealizado",0) or 0) for d in prod)
            tot_fat_val  = sum(float(f.get("valorBruto",0) or 0) for f in fat)
            ratio = (tot_fat_val/tot_prod_val) if tot_prod_val else 0
            c1,c2,c3 = st.columns(3)
            with c1: st.markdown(kpi("Produção Realizada", fmt_brl_m(tot_prod_val)), unsafe_allow_html=True)
            with c2: st.markdown(kpi("Faturamento", fmt_brl_m(tot_fat_val)), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Faturamento/Produção", fmt_pct(ratio*100),
                delta="✓ Fatura mais do que produz" if ratio > 1 else "⚠️ Gap produção→faturamento",
                delta_type="up" if ratio > 1 else "warn"), unsafe_allow_html=True)
        else:
            st.warning("⚠️ Carregue **Produção** e **Faturamento** para este cruzamento.")

    with tab3:
        st.subheader("Eficiência vs. Consumo de Combustível")
        efic = st.session_state.get("efic_dados", [])
        comb = st.session_state.get("comb_dados", [])
        if efic and comb:
            # Indexa eficiência por equipamento ID
            efic_map = {(d.get("equipamentoResumido") or {}).get("id"): d for d in efic if d.get("equipamentoResumido")}
            # Cruza com combustível
            rows = []
            for c in comb:
                eq = c.get("equipamento") or {}
                eq_id = eq.get("id")
                ef_d  = efic_map.get(eq_id,{})
                ef    = float(ef_d.get("eficiencia",0) or 0)
                mo    = float(c.get("mediaObtida",0) or 0)
                md    = float(c.get("mediaDesejada",0) or 0)
                if mo and md:
                    rows.append({
                        "Equipamento": eq.get("descricao","?")[:25],
                        "Eficiência %": ef,
                        "Desvio Combustível %": (mo/md-1)*100,
                        "Consumo Litros": float(c.get("quantidade",0) or 0),
                    })
            if rows:
                df_cr = pd.DataFrame(rows)
                fig = px.scatter(df_cr, x="Eficiência %", y="Desvio Combustível %",
                                 size="Consumo Litros", hover_name="Equipamento",
                                 color="Desvio Combustível %",
                                 color_continuous_scale=["#0A6E3F","#F39C12","#C0392B"],
                                 template="plotly_white")
                fig.add_hline(y=0,  line_dash="dash", line_color="gray")
                fig.add_vline(x=80, line_dash="dash", line_color="orange",
                              annotation_text="Meta efic. 80%")
                fig.update_layout(title="Cada ponto = 1 equipamento | Quadrante ideal: direita-baixo")
                st.plotly_chart(fig, use_container_width=True)
                st.caption("🎯 Ideal: alta eficiência (direita) + baixo desvio de combustível (baixo).")
            else:
                st.info("Não foi possível cruzar os dados por falta de IDs comuns.")
        else:
            st.warning("⚠️ Carregue **Eficiência de Equipamentos** e **Consumo de Combustível**.")

        st.divider()
        st.subheader("Custo de Oficina vs. Horas de Eficiência")
        if efic and ofic_dados:
            ofic_dados = st.session_state.get("ofic_dados", [])
            eq_custo_of = {}
            for of in ofic_dados:
                eq_id = (of.get("equipamento") or {}).get("id")
                eq_nm = (of.get("equipamento") or {}).get("descricao","?")[:25]
                if eq_id:
                    eq_custo_of[eq_id] = eq_custo_of.get(eq_id,{})
                    eq_custo_of[eq_id]["nome"]  = eq_nm
                    eq_custo_of[eq_id]["custo"] = eq_custo_of[eq_id].get("custo",0) + float(of.get("custoSolucao",0) or 0)

            rows = []
            for d in efic:
                eq = d.get("equipamentoResumido") or {}
                eq_id = eq.get("id")
                custo = eq_custo_of.get(eq_id,{}).get("custo",0)
                if custo > 0:
                    rows.append({
                        "Equipamento": eq.get("descricao","?")[:25],
                        "Custo Oficina (R$)": custo,
                        "Eficiência %": float(d.get("eficiencia",0) or 0),
                        "Horas Mês": float(d.get("horasMes",0) or 0),
                    })
            if rows:
                df_oe = pd.DataFrame(rows).sort_values("Custo Oficina (R$)", ascending=False).head(15)
                df_oe["Custo/Hora"] = df_oe["Custo Oficina (R$)"] / df_oe["Horas Mês"].replace(0,1)
                st.dataframe(df_oe.assign(**{
                    "Custo Oficina (R$)": df_oe["Custo Oficina (R$)"].apply(fmt_brl),
                    "Eficiência %": df_oe["Eficiência %"].apply(fmt_pct),
                    "Custo/Hora": df_oe["Custo/Hora"].apply(fmt_brl),
                }), use_container_width=True, hide_index=True)
            else:
                st.info("Dados insuficientes para o cruzamento.")
        else:
            st.warning("⚠️ Carregue **Eficiência** e **Manutenção e Oficina**.")


# ════════════════════════════════════════
#  MÓDULOS LEGADOS
# ════════════════════════════════════════
elif pagina == "👥 Clientes Inativos":
    st.markdown("""<div class="main-header">
        <h1>👥 Clientes Inativos</h1>
        <p>Carteira em risco — estratégia de reativação</p></div>""", unsafe_allow_html=True)

    dias = st.slider("Inativo após X dias sem comprar", 30, 180, 60, 10)
    col_b, _ = st.columns([1,3])
    with col_b: analisar = st.button("🔍 Analisar Carteira", use_container_width=True)

    if st.session_state.get("inat_dias") != dias:
        st.session_state.pop("inat_dados", None)
        st.session_state["inat_dias"] = dias

    if analisar:
        with st.spinner("Buscando histórico..."): st.session_state["inat_dados"] = _clientes_inativos(dias)

    if "inat_dados" not in st.session_state:
        st.info("👆 Clique em **Analisar Carteira**.")
    else:
        try:
            dados    = st.session_state["inat_dados"]
            resumo   = dados.get("resumo", {})
            inativos = dados.get("inativos", [])
            ativos   = dados.get("ativos_recentes", [])
            valor_risco = sum(c.get("total_historico",0) for c in inativos)
            pct = round(len(inativos)/resumo.get("total_clientes",1)*100,1) if resumo.get("total_clientes") else 0

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(kpi("Total Clientes", resumo.get("total_clientes",0)), unsafe_allow_html=True)
            with c2: st.markdown(kpi(f"Inativos +{dias}d", len(inativos),
                delta=f"⚠️ {pct}% da carteira", delta_type="warn"), unsafe_allow_html=True)
            with c3: st.markdown(kpi("Ativos Recentes", resumo.get("ativos",0),
                delta="✓ Compraram recentemente", delta_type="up"), unsafe_allow_html=True)
            with c4: st.markdown(kpi("Receita em Risco", fmt_brl_m(valor_risco),
                delta="⚠️ Valor histórico", delta_type="warn"), unsafe_allow_html=True)

            ca, cb = st.columns(2)
            with ca:
                st.subheader("Por Tempo de Inatividade")
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

            if inativos:
                df3 = pd.DataFrame(inativos)
                df3["total_historico"] = df3["total_historico"].apply(fmt_brl)
                df3["ticket_medio"]    = df3["ticket_medio"].apply(fmt_brl)
                cols = [c for c in ["nome","ultima_compra","dias_sem_comprar",
                                    "total_historico","qtde_pedidos","ticket_medio"] if c in df3.columns]
                st.dataframe(df3[cols], use_container_width=True, height=400)
                csv = df3[cols].to_csv(index=False).encode("utf-8-sig")
                st.download_button("⬇️ Exportar CSV", csv, "clientes_inativos.csv", "text/csv")
        except Exception as e:
            erro_generico(e)


elif pagina == "📦 Materiais":
    st.markdown("""<div class="main-header">
        <h1>📦 Materiais e Suprimentos</h1>
        <p>Cadastro e qualidade de dados</p></div>""", unsafe_allow_html=True)
    with st.spinner("Carregando materiais..."):
        try:
            from resumidor import resumir_materiais
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
            erro_generico(e)


# ════════════════════════════════════════
#  GERAR RELATÓRIO COM IA
# ════════════════════════════════════════
elif pagina == "🤖 Gerar Relatório com IA":
    st.markdown("""<div class="main-header">
        <h1>🤖 Gerar Relatório com IA</h1>
        <p>Claude analisa os dados e escreve um relatório executivo em PDF</p></div>""", unsafe_allow_html=True)

    descricoes = {
        "🛍️ Análise de Vendas":              "Pedidos, orçamentos, top clientes, vendedores, taxa de conversão.",
        "👥 Clientes Inativos":              "Identifica clientes que pararam de comprar. Estratégia de reativação.",
        "🚜 Auditoria de Frota":             "Seguros vencidos, OS atrasadas, anormalidades, score da frota.",
        "🔧 Relatório de Manutenção":        "OS por período, defeitos frequentes, tempo de resolução.",
        "📋 Patrimônio da Frota":            "Depreciação, cobertura, próprios vs. terceiros.",
        "💳 Auditoria Financeira":           "Duplicatas, valores suspeitos, concentração de fornecedores.",
        "💳 Análise Financeira Mensal":      "Fluxo de caixa, posição bancária, ticket médio.",
        "🛒 Auditoria de Compras":           "Bypass de processo, favorecimento de fornecedor.",
        "🛒 Relatório Gerencial de Compras": "Volume, top fornecedores, frete %, descontos.",
        "📦 Auditoria de Materiais":         "NCM ausente, sem preço, score de qualidade do cadastro.",
        "⚙️ Análise de Eficiência da Frota": "Disponibilidade, perdas, equipamentos críticos.",
        "🏗️ Relatório de Custos por Filial": "Margem, desvio orçamentário, R$/Ton por unidade.",
    }

    c1, c2 = st.columns([1,2])
    with c1:
        tipo = st.selectbox("Tipo de Relatório", list(descricoes.keys()))
        st.caption(f"📅 {label_periodo}")
        gerar = st.button("🚀 Gerar Relatório Agora", use_container_width=True)
    with c2:
        st.info(descricoes[tipo])

    if gerar:
        try:
            from prompts import (
                prompt_auditoria_frota, prompt_relatorio_manutencao,
                prompt_relatorio_patrimonio_frota, prompt_auditoria_financeira,
                prompt_analise_financeira_mensal, prompt_auditoria_compras,
                prompt_relatorio_compras_gerencial, prompt_auditoria_materiais,
                prompt_analise_vendas, prompt_clientes_inativos,
            )
        except ImportError:
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
                    os_l = _os_legado(inicio, fim)
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
                elif "Eficiência" in tipo:
                    efic = _eficiencia()
                    comb = _combustivel()
                    import json
                    dados_str = json.dumps({"eficiencia": efic[:30], "combustivel": comb[:30]},
                                           ensure_ascii=False, default=str)[:12000]
                    prompt = (f"Você é um analista de frota sênior. Analise os dados de eficiência "
                              f"e consumo de combustível da frota da Britagem Vogelsanger para {label_periodo}. "
                              f"Identifique os equipamentos com menor disponibilidade, maior desvio de "
                              f"consumo e recomende ações práticas.\n\nDADOS:\n{dados_str}")
                    tipo_pdf, titulo = "eficiencia_frota", "Eficiência da Frota"
                elif "Custos" in tipo:
                    custos = _custos_filial()
                    import json
                    dados_str = json.dumps(custos[:50], ensure_ascii=False, default=str)[:12000]
                    prompt = (f"Você é um CFO especialista em mineração e construção pesada. "
                              f"Analise os custos por filial da Britagem Vogelsanger para {label_periodo}. "
                              f"Identifique desvios orçamentários, compare margens entre filiais e "
                              f"recomende ações de redução de custo.\n\nDADOS:\n{dados_str}")
                    tipo_pdf, titulo = "custos_filial", "Custos por Filial"
                else:
                    st.error("Tipo não reconhecido")
                    st.stop()

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
            st.markdown(analise[:3000] + ("..." if len(analise) > 3000 else ""))

        except Exception as e:
            st.error(f"❌ Erro: {e}")
            st.exception(e)
