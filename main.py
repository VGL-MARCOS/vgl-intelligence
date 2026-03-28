"""
=============================================================
  CRTI + CLAUDE INTEGRATION — ORQUESTRADOR PRINCIPAL
  Conecta a API real do CRTI (vogelsanger.crti.com.br)
  com a API do Claude para automação de análises

  COMANDOS:
    python main.py --teste
    python main.py --auditoria
    python main.py --auditoria        --periodo mes
    python main.py --auditoria        --periodo mes-anterior
    python main.py --auditoria        --periodo 2026-03-01,2026-03-31
    python main.py --contas           --periodo semana
    python main.py --mensal           --periodo 2026-02
    python main.py --permutas
    python main.py --materiais
    python main.py --estoque
    python main.py --custos-servicos
    python main.py --compras-auditoria
    python main.py --compras-relatorio
    python main.py --frota-auditoria
    python main.py --frota-manutencao
    python main.py --frota-patrimonio
    python main.py --todos
    python main.py                    → agendador automático

  PERÍODOS DISPONÍVEIS:
    hoje          → somente hoje
    ontem         → somente ontem (padrão)
    semana        → últimos 7 dias
    30dias        → últimos 30 dias
    mes           → mês atual (dia 1 até hoje)
    mes-completo  → mês atual do dia 1 ao último dia
    mes-anterior  → mês anterior completo
    2026-02       → mês específico
    2026-03-01,2026-03-31  → período personalizado
=============================================================
"""

import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

# ── Setup de logging ──
Path("./logs").mkdir(exist_ok=True)
Path("./outputs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"./logs/crti_claude_{datetime.now().strftime('%Y%m')}.log",
            encoding="utf-8"
        )
    ]
)
logger = logging.getLogger("main")

# ── Imports ──
from modules.crti_client      import CRTIClient
from modules.claude_analyzer  import ClaudeAnalyzer
from modules.report_generator import ReportGenerator
from modules.email_sender     import EmailSender
from modules.scheduler        import configurar_agendamentos, iniciar_loop
from modules.periodos         import Periodos
from prompts.prompts          import (
    prompt_auditoria_financeira,
    prompt_analise_contas_pagar_receber,
    prompt_analise_financeira_mensal,
    prompt_relatorio_permutas,
    prompt_auditoria_materiais,
    prompt_relatorio_estoque_critico,
    prompt_analise_servicos_filial,
    prompt_analise_perdas_equipamentos,
    prompt_analise_bmo,
    prompt_auditoria_compras,
    prompt_relatorio_compras_gerencial,
    prompt_auditoria_frota,
    prompt_relatorio_manutencao,
    prompt_relatorio_patrimonio_frota,
)

# ── Serviços ──
crti   = CRTIClient()
claude = ClaudeAnalyzer()
pdf    = ReportGenerator()
email  = EmailSender()


# ─────────────────────────────────────────────
#  HELPER — resolve período e label
# ─────────────────────────────────────────────
def resolver_periodo(periodo_arg: str, padrao: str = "ontem") -> tuple:
    """Retorna (inicio, fim, label) a partir do argumento --periodo."""
    p = periodo_arg or padrao
    inicio, fim = Periodos.resolver(p)
    label = Periodos.formatar_label(inicio, fim)
    return inicio, fim, label


# ─────────────────────────────────────────────
#  TESTE DE CONEXÃO
# ─────────────────────────────────────────────
def job_teste():
    logger.info("🧪 Testando conexões...")
    info = crti.buscar_info_empresa()
    logger.info(f"✅ CRTI conectado — Empresa: {info.get('nomeEmpresa', '?')}")
    logger.info(f"   AppCargas: {info.get('permiteAcessoAppCargas')}")
    logger.info(f"   AppApropriacoes: {info.get('permiteAcessoAppApropriacoes')}")

    inicio, fim = Periodos.ultimos_7_dias()
    transferencias = crti.buscar_transferencias(inicio, fim)
    logger.info(f"✅ Transferências encontradas: {len(transferencias)} ({inicio} → {fim})")

    contas = crti.buscar_contas_correntes()
    logger.info(f"✅ Contas correntes: {len(contas)}")

    resposta = claude.analisar("Responda apenas: API funcionando corretamente.")
    logger.info(f"✅ Claude respondeu: {resposta[:60]}")
    logger.info("\n🎉 Todos os serviços operacionais!")


# ─────────────────────────────────────────────
#  FINANCEIRO
# ─────────────────────────────────────────────
def job_auditoria(periodo_arg=None):
    inicio, fim, label = resolver_periodo(periodo_arg, "ontem")
    logger.info(f"🔍 JOB: Auditoria Financeira — {label}")

    dados = crti.buscar_dados_auditoria(inicio, fim)
    logger.info(f"   Transferências: {len(dados['transferencias'])} | "
                f"Permutas: {len(dados['permutas'])} | Contas: {len(dados['contas_correntes'])}")

    prompt  = prompt_auditoria_financeira(dados, label)
    analise = claude.analisar_auditoria(prompt)

    caminho = pdf.gerar_pdf(
        titulo    = "Auditoria Financeira",
        analise   = analise,
        tipo      = "auditoria",
        subtitulo = f"Período: {label}"
    )
    email.enviar_relatorio(
        assunto    = f"🔍 Auditoria Financeira — {label}",
        corpo_html = EmailSender.corpo_auditoria(analise[:500], label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


def job_contas(periodo_arg=None):
    inicio, fim, label = resolver_periodo(periodo_arg, "semana")
    logger.info(f"💳 JOB: Contas a Pagar/Receber — {label}")

    transferencias = crti.buscar_transferencias(inicio, fim)
    logger.info(f"   {len(transferencias)} transferências")

    prompt  = prompt_analise_contas_pagar_receber(transferencias, label)
    analise = claude.analisar_financeiro(prompt)

    caminho = pdf.gerar_pdf(
        titulo    = "Contas a Pagar e Receber",
        analise   = analise,
        tipo      = "contas",
        subtitulo = f"Período: {label}"
    )
    email.enviar_relatorio(
        assunto    = f"💳 Contas a Pagar/Receber — {label}",
        corpo_html = EmailSender.corpo_operacional(label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


def job_mensal(periodo_arg=None):
    inicio, fim, label = resolver_periodo(periodo_arg, "mes-anterior")
    logger.info(f"📊 JOB: Análise Financeira Mensal — {label}")

    dados   = crti.buscar_dados_financeiros(inicio, fim)
    prompt  = prompt_analise_financeira_mensal(dados, label)
    analise = claude.analisar_financeiro(prompt)

    caminho = pdf.gerar_pdf(
        titulo    = "Análise Financeira Mensal",
        analise   = analise,
        tipo      = "mensal",
        subtitulo = f"Período: {label}"
    )
    email.enviar_relatorio(
        assunto    = f"📊 Análise Financeira — {label}",
        corpo_html = EmailSender.corpo_financeiro(label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


def job_permutas(periodo_arg=None):
    inicio, fim, label = resolver_periodo(periodo_arg, "mes")
    logger.info(f"🔄 JOB: Permutas — {label}")

    permutas = crti.buscar_permutas(inicio, fim)
    logger.info(f"   {len(permutas)} permutas")

    prompt  = prompt_relatorio_permutas(permutas, label)
    analise = claude.analisar(prompt)

    caminho = pdf.gerar_pdf(
        titulo    = "Negociações e Permutas",
        analise   = analise,
        tipo      = "permutas",
        subtitulo = f"Período: {label}"
    )
    email.enviar_relatorio(
        assunto    = f"🔄 Permutas — {label}",
        corpo_html = EmailSender.corpo_operacional(label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


# ─────────────────────────────────────────────
#  SUPRIMENTOS
# ─────────────────────────────────────────────
def job_auditoria_materiais():
    logger.info("📦 JOB: Auditoria de Materiais")
    materiais = crti.buscar_materiais(apenas_ativos=False)
    logger.info(f"   {len(materiais)} materiais")

    prompt  = prompt_auditoria_materiais(materiais)
    analise = claude.analisar_auditoria(prompt)

    label   = datetime.now().strftime("%d/%m/%Y")
    caminho = pdf.gerar_pdf(
        titulo    = "Auditoria de Materiais e Suprimentos",
        analise   = analise,
        tipo      = "materiais",
        subtitulo = f"{len(materiais)} materiais | Referência: {label}"
    )
    email.enviar_relatorio(
        assunto    = f"📦 Auditoria de Materiais — {label}",
        corpo_html = EmailSender.corpo_auditoria(analise[:500], label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


def job_estoque_critico():
    logger.info("⚠️ JOB: Controle de Estoque")
    materiais = crti.buscar_materiais_estoque_critico()
    logger.info(f"   {len(materiais)} materiais com controle de estoque")

    prompt  = prompt_relatorio_estoque_critico(materiais)
    analise = claude.analisar_operacional(prompt)

    label   = datetime.now().strftime("%d/%m/%Y")
    caminho = pdf.gerar_pdf(
        titulo    = "Controle de Estoque",
        analise   = analise,
        tipo      = "estoque",
        subtitulo = f"{len(materiais)} materiais monitorados | {label}"
    )
    email.enviar_relatorio(
        assunto    = f"⚠️ Controle de Estoque — {label}",
        corpo_html = EmailSender.corpo_operacional(label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


# ─────────────────────────────────────────────
#  CUSTOS
# ─────────────────────────────────────────────
def job_custos_servicos(ids_filiais=None):
    logger.info("🔧 JOB: Custos de Serviços por Filial")
    ids_filiais = ids_filiais or [1]
    servicos    = crti.buscar_servicos_todas_filiais(ids_filiais)
    total       = sum(len(v) for v in servicos.values())
    logger.info(f"   {total} serviços em {len(ids_filiais)} filiais")

    prompt  = prompt_analise_servicos_filial(servicos)
    analise = claude.analisar_financeiro(prompt)

    label   = datetime.now().strftime("%d/%m/%Y")
    caminho = pdf.gerar_pdf(
        titulo    = "Custos de Serviços — Realizado vs Contratado",
        analise   = analise,
        tipo      = "custos_servicos",
        subtitulo = f"{total} serviços | {len(ids_filiais)} filiais | {label}"
    )
    email.enviar_relatorio(
        assunto    = f"🔧 Custos de Serviços — {label}",
        corpo_html = EmailSender.corpo_financeiro(label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


def job_custos_perdas_equipamentos(ids_blepdv=None):
    logger.info("📉 JOB: Eficiência de Equipamentos")
    perdas_config = crti.buscar_todas_perdas_e_tipos()
    ids_blepdv    = ids_blepdv or []
    blepdv_lista  = []
    for id_b in ids_blepdv:
        try:
            blepdv_lista.append(crti.buscar_blepdv_por_id(id_b))
        except Exception as e:
            logger.warning(f"   BLE/PDV {id_b}: {e}")

    if not blepdv_lista:
        logger.warning("   Nenhum BLE/PDV — use: job_custos_perdas_equipamentos([1,2,3])")
        return None, None

    prompt  = prompt_analise_perdas_equipamentos(blepdv_lista, perdas_config)
    analise = claude.analisar_operacional(prompt)

    label   = datetime.now().strftime("%d/%m/%Y")
    caminho = pdf.gerar_pdf(
        titulo    = "Eficiência de Equipamentos",
        analise   = analise,
        tipo      = "custos_equipamentos",
        subtitulo = f"{len(blepdv_lista)} BLE/PDVs | {label}"
    )
    email.enviar_relatorio(
        assunto    = f"📉 Eficiência de Equipamentos — {label}",
        corpo_html = EmailSender.corpo_operacional(label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


def job_custos_bmo(ids_bmo=None, periodo_arg=None):
    logger.info("👷 JOB: Análise de BMO")
    _, _, label = resolver_periodo(periodo_arg, "semana")
    ids_bmo     = ids_bmo or []
    bmo_lista   = []
    for id_b in ids_bmo:
        try:
            bmo_lista.append(crti.buscar_bmo_por_id(id_b))
        except Exception as e:
            logger.warning(f"   BMO {id_b}: {e}")

    if not bmo_lista:
        logger.warning("   Nenhum BMO — use: job_custos_bmo([1,2,3])")
        return None, None

    prompt  = prompt_analise_bmo(bmo_lista, label)
    analise = claude.analisar_operacional(prompt)

    caminho = pdf.gerar_pdf(
        titulo    = "Análise de Mão de Obra — BMO",
        analise   = analise,
        tipo      = "custos_bmo",
        subtitulo = f"Período: {label} | {len(bmo_lista)} BMOs"
    )
    email.enviar_relatorio(
        assunto    = f"👷 BMO — {label}",
        corpo_html = EmailSender.corpo_operacional(label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


# ─────────────────────────────────────────────
#  COMPRAS
# ─────────────────────────────────────────────
def job_auditoria_compras(periodo_arg=None):
    inicio, fim, label = resolver_periodo(periodo_arg, "mes")
    logger.info(f"🛒 JOB: Auditoria de Compras — {label}")

    dados   = crti.buscar_compras_periodo(inicio, fim)
    req     = dados.get("solicitacoesMaterialMestre", [])
    oc_dir  = dados.get("ordensCompraMestreSemCotacaoOuSemRequisicao", [])
    logger.info(f"   Requisições: {len(req)} | OCs diretas: {len(oc_dir)}")

    prompt  = prompt_auditoria_compras(dados, label)
    analise = claude.analisar_auditoria(prompt)

    caminho = pdf.gerar_pdf(
        titulo    = "Auditoria de Compras",
        analise   = analise,
        tipo      = "auditoria_compras",
        subtitulo = f"Período: {label} | {len(req)} Requisições · {len(oc_dir)} OCs Diretas"
    )
    email.enviar_relatorio(
        assunto    = f"🛒 Auditoria de Compras — {label}",
        corpo_html = EmailSender.corpo_auditoria(analise[:500], label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


def job_relatorio_compras(periodo_arg=None):
    inicio, fim, label = resolver_periodo(periodo_arg, "mes-anterior")
    logger.info(f"📋 JOB: Relatório de Compras — {label}")

    dados   = crti.buscar_compras_periodo(inicio, fim)
    prompt  = prompt_relatorio_compras_gerencial(dados, label)
    analise = claude.analisar_financeiro(prompt)

    caminho = pdf.gerar_pdf(
        titulo    = "Relatório Gerencial de Compras",
        analise   = analise,
        tipo      = "relatorio_compras",
        subtitulo = f"Período: {label}"
    )
    email.enviar_relatorio(
        assunto    = f"📋 Compras — {label}",
        corpo_html = EmailSender.corpo_operacional(label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


# ─────────────────────────────────────────────
#  FROTA
# ─────────────────────────────────────────────
def job_auditoria_frota(periodo_arg=None):
    inicio, fim, label = resolver_periodo(periodo_arg, "mes")
    logger.info(f"🚜 JOB: Auditoria de Frota — {label}")

    dados  = crti.buscar_dados_frota_completos(inicio, fim)
    equip  = dados["equipamentos"]
    os_m   = dados["os_manutencao"]
    trf    = dados["transferencias"]
    logger.info(f"   Equipamentos: {len(equip)} | OS: {len(os_m)} | Transferências: {len(trf)}")

    prompt  = prompt_auditoria_frota(dados, label)
    analise = claude.analisar_auditoria(prompt)

    caminho = pdf.gerar_pdf(
        titulo    = "Auditoria de Frota e Equipamentos",
        analise   = analise,
        tipo      = "auditoria_frota",
        subtitulo = f"Período: {label} | {len(equip)} equip. · {len(os_m)} OS · {len(trf)} transf."
    )
    email.enviar_relatorio(
        assunto    = f"🚜 Auditoria de Frota — {label}",
        corpo_html = EmailSender.corpo_auditoria(analise[:500], label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


def job_relatorio_manutencao(periodo_arg=None):
    inicio, fim, label = resolver_periodo(periodo_arg, "mes-anterior")
    logger.info(f"🔧 JOB: Manutenção — {label}")

    os_lista = crti.buscar_os_manutencao(
        data_abertura_de=inicio, data_abertura_ate=fim
    )
    logger.info(f"   {len(os_lista)} OS")

    prompt  = prompt_relatorio_manutencao(os_lista, label)
    analise = claude.analisar_operacional(prompt)

    caminho = pdf.gerar_pdf(
        titulo    = "Relatório de Manutenção",
        analise   = analise,
        tipo      = "manutencao",
        subtitulo = f"Período: {label} | {len(os_lista)} OS"
    )
    email.enviar_relatorio(
        assunto    = f"🔧 Manutenção — {label}",
        corpo_html = EmailSender.corpo_operacional(label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


def job_patrimonio_frota():
    logger.info("📋 JOB: Patrimônio da Frota")
    equipamentos = crti.buscar_equipamentos()
    logger.info(f"   {len(equipamentos)} equipamentos")

    prompt  = prompt_relatorio_patrimonio_frota(equipamentos)
    analise = claude.analisar_financeiro(prompt)

    label   = datetime.now().strftime("%d/%m/%Y")
    caminho = pdf.gerar_pdf(
        titulo    = "Inventário Patrimonial da Frota",
        analise   = analise,
        tipo      = "patrimonio_frota",
        subtitulo = f"Referência: {label} | {len(equipamentos)} equipamentos"
    )
    email.enviar_relatorio(
        assunto    = f"📋 Patrimônio da Frota — {label}",
        corpo_html = EmailSender.corpo_financeiro(label),
        pdf_path   = caminho
    )
    logger.info(f"   PDF: {caminho}")
    return caminho, analise


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CRTI + Claude Integration | vogelsanger.crti.com.br",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Jobs
    parser.add_argument("--teste",             action="store_true", help="Testa conexão com CRTI e Claude")
    parser.add_argument("--auditoria",         action="store_true", help="Auditoria financeira")
    parser.add_argument("--contas",            action="store_true", help="Contas a pagar/receber")
    parser.add_argument("--mensal",            action="store_true", help="Análise financeira mensal")
    parser.add_argument("--permutas",          action="store_true", help="Relatório de permutas")
    parser.add_argument("--materiais",         action="store_true", help="Auditoria de materiais")
    parser.add_argument("--estoque",           action="store_true", help="Controle de estoque")
    parser.add_argument("--custos-servicos",   action="store_true", help="Custos realizado vs contratado")
    parser.add_argument("--custos-perdas",     action="store_true", help="Eficiência de equipamentos")
    parser.add_argument("--custos-bmo",        action="store_true", help="Análise de BMO")
    parser.add_argument("--compras-auditoria", action="store_true", help="Auditoria de compras")
    parser.add_argument("--compras-relatorio", action="store_true", help="Relatório gerencial de compras")
    parser.add_argument("--frota-auditoria",   action="store_true", help="Auditoria de frota")
    parser.add_argument("--frota-manutencao",  action="store_true", help="Relatório de manutenção")
    parser.add_argument("--frota-patrimonio",  action="store_true", help="Inventário patrimonial")
    parser.add_argument("--todos",             action="store_true", help="Roda todos os jobs")

    # Controle de período
    parser.add_argument(
        "--periodo",
        type=str,
        default=None,
        metavar="PERIODO",
        help=(
            "Período para o relatório. Opções:\n"
            "  hoje, ontem, semana, 30dias\n"
            "  mes, mes-completo, mes-anterior\n"
            "  2026-02          (mês específico)\n"
            "  2026-03-01,2026-03-31  (período livre)\n"
            "Padrão: cada job usa seu período natural"
        )
    )

    args = parser.parse_args()
    p    = args.periodo  # período opcional passado pelo usuário

    if args.teste:
        job_teste()
    if args.auditoria or args.todos:
        job_auditoria(p)
    if args.contas or args.todos:
        job_contas(p)
    if args.mensal or args.todos:
        job_mensal(p)
    if args.permutas or args.todos:
        job_permutas(p)
    if args.materiais or args.todos:
        job_auditoria_materiais()
    if args.estoque or args.todos:
        job_estoque_critico()
    if getattr(args, "custos_servicos", False) or args.todos:
        job_custos_servicos()
    if getattr(args, "custos_perdas", False):
        job_custos_perdas_equipamentos()
    if getattr(args, "custos_bmo", False):
        job_custos_bmo(periodo_arg=p)
    if getattr(args, "compras_auditoria", False) or args.todos:
        job_auditoria_compras(p)
    if getattr(args, "compras_relatorio", False) or args.todos:
        job_relatorio_compras(p)
    if getattr(args, "frota_auditoria", False) or args.todos:
        job_auditoria_frota(p)
    if getattr(args, "frota_manutencao", False) or args.todos:
        job_relatorio_manutencao(p)
    if getattr(args, "frota_patrimonio", False) or args.todos:
        job_patrimonio_frota()

    # Sem argumento → agendador automático
    if not any([
        args.teste, args.auditoria, args.contas, args.mensal,
        args.permutas, args.materiais, args.estoque,
        getattr(args, "custos_servicos", False),
        getattr(args, "custos_perdas", False),
        getattr(args, "custos_bmo", False),
        getattr(args, "compras_auditoria", False),
        getattr(args, "compras_relatorio", False),
        getattr(args, "frota_auditoria", False),
        getattr(args, "frota_manutencao", False),
        getattr(args, "frota_patrimonio", False),
        args.todos,
    ]):
        logger.info("🕐 Iniciando scheduler automático...")
        configurar_agendamentos(
            fn_auditoria   = job_auditoria,
            fn_operacional = job_contas,
            fn_financeiro  = job_mensal,
            fn_dre_mensal  = lambda: job_relatorio_compras(),
        )
        iniciar_loop()
