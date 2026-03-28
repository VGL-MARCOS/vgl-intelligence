"""
=============================================================
  MÓDULO: SCHEDULER
  Agendamento automático de todos os relatórios
=============================================================
"""

import schedule
import time
import logging
from datetime import datetime
from config import SCHEDULE_CONFIG

logger = logging.getLogger(__name__)


def executar_com_log(nome: str, funcao):
    """Wrapper que loga início, fim e erros de cada execução."""
    def wrapper():
        logger.info(f"\n{'='*50}")
        logger.info(f"▶️  INICIANDO: {nome} — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        try:
            funcao()
            logger.info(f"✅ CONCLUÍDO: {nome}")
        except Exception as e:
            logger.error(f"❌ ERRO em {nome}: {e}", exc_info=True)
        logger.info(f"{'='*50}\n")
    return wrapper


def configurar_agendamentos(
    fn_auditoria,
    fn_operacional,
    fn_financeiro,
    fn_dre_mensal
):
    """
    Registra todos os jobs no scheduler com base no config.py.
    
    Parâmetros são as funções a executar para cada relatório.
    """

    cfg = SCHEDULE_CONFIG

    # ── Auditoria de lançamentos ──
    if cfg["auditoria_lancamentos"]["ativo"]:
        horario = cfg["auditoria_lancamentos"]["horario"]
        schedule.every().day.at(horario).do(
            executar_com_log("Auditoria de Lançamentos", fn_auditoria)
        )
        logger.info(f"📅 Auditoria agendada — todos os dias às {horario}")

    # ── Relatório operacional ──
    if cfg["relatorio_operacional"]["ativo"]:
        horario = cfg["relatorio_operacional"]["horario"]
        schedule.every().day.at(horario).do(
            executar_com_log("Relatório Operacional", fn_operacional)
        )
        logger.info(f"📅 Operacional agendado — todos os dias às {horario}")

    # ── Análise financeira semanal ──
    if cfg["analise_financeira"]["ativo"]:
        horario = cfg["analise_financeira"]["horario"]
        dia     = cfg["analise_financeira"]["dia_semana"]
        getattr(schedule.every(), dia).at(horario).do(
            executar_com_log("Análise Financeira Semanal", fn_financeiro)
        )
        logger.info(f"📅 Financeiro agendado — toda {dia} às {horario}")

    # ── DRE mensal ──
    if cfg["dre_mensal"]["ativo"]:
        horario  = cfg["dre_mensal"]["horario"]
        dia_mes  = cfg["dre_mensal"]["dia_mes"]
        # schedule não suporta dia_mes diretamente — usamos verificação manual
        def verificar_e_executar_dre():
            if datetime.now().day == dia_mes:
                executar_com_log("DRE Mensal", fn_dre_mensal)()
        schedule.every().day.at(horario).do(verificar_e_executar_dre)
        logger.info(f"📅 DRE Mensal agendado — dia {dia_mes} de cada mês às {horario}")


def iniciar_loop():
    """
    Inicia o loop infinito do scheduler.
    Mantém o processo rodando e executa os jobs nos horários definidos.
    """
    logger.info("\n🚀 Scheduler iniciado! Aguardando próximos jobs...\n")
    while True:
        schedule.run_pending()
        time.sleep(30)  # verifica a cada 30 segundos
