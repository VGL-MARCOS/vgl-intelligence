"""
=============================================================
  MÓDULO: PERÍODOS
  Controle centralizado de datas para todos os relatórios
  
  Como usar no main.py ou linha de comando:
    python main.py --auditoria                         → ontem (padrão)
    python main.py --auditoria --periodo hoje
    python main.py --auditoria --periodo semana
    python main.py --auditoria --periodo mes
    python main.py --auditoria --periodo mes-anterior
    python main.py --auditoria --periodo 2026-03-01,2026-03-31
    python main.py --mensal    --periodo 2026-02
=============================================================
"""

from datetime import datetime, timedelta
import calendar


class Periodos:
    """
    Centraliza toda a lógica de períodos de data.
    Retorna sempre tupla (data_inicio: str, data_fim: str) no formato YYYY-MM-DD.
    """

    @staticmethod
    def hoje() -> tuple:
        d = datetime.now().strftime("%Y-%m-%d")
        return d, d

    @staticmethod
    def ontem() -> tuple:
        d = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        return d, d

    @staticmethod
    def ultimos_7_dias() -> tuple:
        hoje  = datetime.now()
        inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
        fim   = hoje.strftime("%Y-%m-%d")
        return inicio, fim

    @staticmethod
    def ultimos_30_dias() -> tuple:
        hoje  = datetime.now()
        inicio = (hoje - timedelta(days=30)).strftime("%Y-%m-%d")
        fim   = hoje.strftime("%Y-%m-%d")
        return inicio, fim

    @staticmethod
    def mes_atual() -> tuple:
        hoje  = datetime.now()
        inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
        fim   = hoje.strftime("%Y-%m-%d")
        return inicio, fim

    @staticmethod
    def mes_atual_completo() -> tuple:
        hoje  = datetime.now()
        inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
        ultimo = calendar.monthrange(hoje.year, hoje.month)[1]
        fim   = hoje.replace(day=ultimo).strftime("%Y-%m-%d")
        return inicio, fim

    @staticmethod
    def mes_anterior() -> tuple:
        hoje              = datetime.now()
        primeiro_deste    = hoje.replace(day=1)
        ultimo_ant        = primeiro_deste - timedelta(days=1)
        primeiro_ant      = ultimo_ant.replace(day=1)
        return primeiro_ant.strftime("%Y-%m-%d"), ultimo_ant.strftime("%Y-%m-%d")

    @staticmethod
    def mes_especifico(ano_mes: str) -> tuple:
        """
        Recebe '2026-02' e retorna (2026-02-01, 2026-02-28).
        """
        ano, mes = int(ano_mes[:4]), int(ano_mes[5:7])
        ultimo   = calendar.monthrange(ano, mes)[1]
        return f"{ano:04d}-{mes:02d}-01", f"{ano:04d}-{mes:02d}-{ultimo:02d}"

    @staticmethod
    def personalizado(periodo_str: str) -> tuple:
        """
        Recebe '2026-03-01,2026-03-31' e retorna a tupla.
        """
        partes = periodo_str.split(",")
        return partes[0].strip(), partes[1].strip()

    @classmethod
    def resolver(cls, periodo: str = None) -> tuple:
        """
        Resolve qualquer string de período para (inicio, fim).
        
        Aceita:
          None ou 'ontem'       → ontem
          'hoje'                → hoje
          'semana'              → últimos 7 dias
          '30dias'              → últimos 30 dias
          'mes'                 → mês atual (do dia 1 até hoje)
          'mes-completo'        → mês atual completo (1 ao último dia)
          'mes-anterior'        → mês anterior completo
          '2026-02'             → mês específico
          '2026-03-01,2026-03-31' → período personalizado
        """
        if not periodo or periodo == "ontem":
            return cls.ontem()
        if periodo == "hoje":
            return cls.hoje()
        if periodo in ("semana", "7dias"):
            return cls.ultimos_7_dias()
        if periodo == "30dias":
            return cls.ultimos_30_dias()
        if periodo == "mes":
            return cls.mes_atual()
        if periodo == "mes-completo":
            return cls.mes_atual_completo()
        if periodo == "mes-anterior":
            return cls.mes_anterior()
        if len(periodo) == 7 and periodo[4] == "-":
            return cls.mes_especifico(periodo)
        if "," in periodo:
            return cls.personalizado(periodo)

        raise ValueError(
            f"Período '{periodo}' não reconhecido.\n"
            f"Use: hoje, ontem, semana, mes, mes-anterior, 2026-02, ou 2026-03-01,2026-03-31"
        )

    @staticmethod
    def formatar_label(inicio: str, fim: str) -> str:
        """Formata datas para exibição nos relatórios."""
        fmt = lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
        if inicio == fim:
            return fmt(inicio)
        return f"{fmt(inicio)} a {fmt(fim)}"

    @staticmethod
    def ultimos_n_meses(n: int) -> tuple:
        hoje  = datetime.now()
        fim   = hoje.strftime("%Y-%m-%d")
        mes   = hoje.month - n
        ano   = hoje.year
        while mes <= 0:
            mes += 12
            ano -= 1
        inicio = datetime(ano, mes, 1).strftime("%Y-%m-%d")
        return inicio, fim

    @staticmethod
    def ano_atual() -> tuple:
        hoje   = datetime.now()
        inicio = hoje.replace(month=1, day=1).strftime("%Y-%m-%d")
        fim    = hoje.strftime("%Y-%m-%d")
        return inicio, fim

