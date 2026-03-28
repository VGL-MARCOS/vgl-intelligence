"""
=============================================================
  MÓDULO: RESUMIDOR DE DADOS
  Transforma listas grandes em resumos estatísticos
  para não ultrapassar o limite de tokens do Claude.

  Regra: nunca enviar mais de ~150 registros completos.
  Para listas maiores, envia estatísticas + amostra.
=============================================================
"""

import json
from collections import Counter
from datetime import datetime


def _fmt(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def resumir_transferencias(transferencias: list) -> dict:
    """
    Condensa lista de transferências em estatísticas + amostra.
    Evita overflow de tokens para listas grandes.
    """
    total = len(transferencias)
    if total == 0:
        return {"total": 0, "dados": [], "resumo": "Nenhuma transferência no período."}

    valor_total  = sum(t.get("valorTotalDocumento", 0) or 0 for t in transferencias)
    valor_liq    = sum(t.get("valorLiquido", 0) or 0 for t in transferencias)
    valor_juros  = sum(t.get("valorJuros", 0) or 0 for t in transferencias)
    valor_desc   = sum(t.get("valorDesconto", 0) or 0 for t in transferencias)

    # Top fornecedores
    fornecedores = Counter()
    for t in transferencias:
        f = t.get("fornecedor") or {}
        nome = f.get("nomeRazao") or f.get("nomeFantasia") or f"ID {f.get('id','?')}"
        fornecedores[nome] += t.get("valorTotalDocumento", 0) or 0
    top_forn = [{"fornecedor": k, "valor": round(v, 2)}
                for k, v in fornecedores.most_common(15)]

    # Distribuição por mês/data
    por_data = Counter()
    for t in transferencias:
        data = (t.get("dataEmissao") or "")[:7]
        if data:
            por_data[data] += 1

    # Parcelas
    total_parcelas = sum(len(t.get("parcelas") or []) for t in transferencias)
    com_duplicata  = sum(1 for t in transferencias if t.get("itens"))
    sem_historico  = sum(1 for t in transferencias if not t.get("complemento") and not (t.get("itens")))

    # Amostra representativa (primeiros 30 + últimos 10)
    amostra = transferencias[:30] + (transferencias[-10:] if total > 30 else [])

    return {
        "total_documentos":      total,
        "valor_total_emitido":   round(valor_total, 2),
        "valor_liquido_total":   round(valor_liq, 2),
        "total_juros":           round(valor_juros, 2),
        "total_descontos":       round(valor_desc, 2),
        "ticket_medio":          round(valor_total / total, 2) if total else 0,
        "total_parcelas":        total_parcelas,
        "media_parcelas_por_doc": round(total_parcelas / total, 1) if total else 0,
        "com_duplicata":         com_duplicata,
        "sem_complemento":       sem_historico,
        "top_15_fornecedores":   top_forn,
        "distribuicao_por_mes":  dict(por_data.most_common(12)),
        "amostra_documentos":    amostra,
    }


def resumir_equipamentos(equipamentos: list) -> dict:
    """Condensa cadastro de equipamentos em estatísticas."""
    total = len(equipamentos)
    if total == 0:
        return {"total": 0, "dados": []}

    from datetime import date
    hoje = date.today().isoformat()

    valor_aq   = sum(e.get("valorAquisicao", 0) or 0 for e in equipamentos)
    valor_merc = sum(e.get("valorMercado", 0) or 0 for e in equipamentos)
    valor_loc  = sum(e.get("valorLocacao", 0) or 0 for e in equipamentos)

    # Seguros
    seguros_vencidos = [e for e in equipamentos
                        if e.get("vencimentoSeguro") and e["vencimentoSeguro"] < hoje]
    sem_seguro       = [e for e in equipamentos if not e.get("vencimentoSeguro")]

    # Por grupo
    por_grupo = Counter(e.get("descricaoGrupoEquipamento", "Sem grupo") for e in equipamentos)

    # Sem patrimônio
    sem_patrimonio = [e for e in equipamentos if not e.get("numeroBemPatrimonial")]

    # Subempreiteiros
    de_terceiros = [e for e in equipamentos if e.get("idSubEmpreitero")]

    # Amostra
    amostra = equipamentos[:50]

    return {
        "total_equipamentos":   total,
        "valor_aquisicao_total": round(valor_aq, 2),
        "valor_mercado_total":  round(valor_merc, 2),
        "depreciacao_total":    round(valor_aq - valor_merc, 2),
        "depreciacao_pct":      round((valor_aq - valor_merc) / valor_aq * 100, 1) if valor_aq else 0,
        "valor_locacao_mensal": round(valor_loc, 2),
        "seguros_vencidos":     len(seguros_vencidos),
        "sem_seguro":           len(sem_seguro),
        "sem_num_patrimonial":  len(sem_patrimonio),
        "de_subempreiteiros":   len(de_terceiros),
        "por_grupo":            dict(por_grupo.most_common(15)),
        "lista_seguros_vencidos": [
            {"id": e.get("id"), "descricao": e.get("descricao"),
             "placa": e.get("placa"), "vencimento": e.get("vencimentoSeguro"),
             "valor_cobertura": e.get("valorCobertura")}
            for e in seguros_vencidos[:20]
        ],
        "amostra_equipamentos": amostra,
    }


def resumir_os_manutencao(os_lista: list) -> dict:
    """Condensa OS de manutenção em estatísticas."""
    total = len(os_lista)
    if total == 0:
        return {"total": 0, "dados": []}

    from datetime import date
    hoje = date.today().isoformat()

    por_situacao   = Counter(str(o.get("situacao", "?")) for o in os_lista)
    por_equipamento = Counter(
        (o.get("equipamento") or {}).get("descricao", "?") for o in os_lista
    )

    # OS atrasadas
    atrasadas = [o for o in os_lista
                 if o.get("dataPrevTermino") and o["dataPrevTermino"] < hoje
                 and "conclu" not in str(o.get("situacao","")).lower()
                 and "cancel" not in str(o.get("situacao","")).lower()]

    # Defeitos mais comuns
    defeitos = Counter(o.get("defeito", "") for o in os_lista if o.get("defeito"))

    return {
        "total_os":             total,
        "por_situacao":         dict(por_situacao.most_common()),
        "os_atrasadas":         len(atrasadas),
        "top_10_equipamentos":  dict(por_equipamento.most_common(10)),
        "top_10_defeitos":      dict(defeitos.most_common(10)),
        "lista_atrasadas":      [
            {"id": o.get("id"), "equipamento": (o.get("equipamento") or {}).get("descricao"),
             "defeito": o.get("defeito"), "dataPrevTermino": o.get("dataPrevTermino"),
             "situacao": o.get("situacao")}
            for o in atrasadas[:20]
        ],
        "amostra_os":           os_lista[:40],
    }


def resumir_materiais(materiais: list) -> dict:
    """Condensa cadastro de materiais em estatísticas."""
    total = len(materiais)
    if total == 0:
        return {"total": 0, "dados": []}

    sem_ncm      = [m for m in materiais if not m.get("ncm")]
    sem_preco    = [m for m in materiais if not m.get("valorUnitarioCom")]
    sem_grupo    = [m for m in materiais if not m.get("grupo")]
    sem_ean      = [m for m in materiais if not m.get("ean")]
    inativos     = [m for m in materiais if not m.get("ativo")]
    com_estoque  = [m for m in materiais if m.get("materiaisControleEstoque")]

    por_grupo    = Counter(
        (m.get("grupo") or {}).get("descricao", "Sem grupo") for m in materiais
    )

    # Top 20 materiais com mais campos em branco
    def score_incompleto(m):
        campos = ["ncm", "ean", "grupo", "classes", "marca",
                  "valorUnitarioCom", "unidade", "codigoIntegracao"]
        return sum(1 for c in campos if not m.get(c))

    top_incompletos = sorted(materiais, key=score_incompleto, reverse=True)[:20]

    return {
        "total_materiais":      total,
        "ativos":               total - len(inativos),
        "inativos":             len(inativos),
        "sem_ncm":              len(sem_ncm),
        "sem_preco":            len(sem_preco),
        "sem_grupo":            len(sem_grupo),
        "sem_ean":              len(sem_ean),
        "com_controle_estoque": len(com_estoque),
        "completude_pct":       round((total - len(sem_ncm) - len(sem_preco)) / total * 100, 1) if total else 0,
        "por_grupo":            dict(por_grupo.most_common(15)),
        "top_20_incompletos":   top_incompletos,
        "amostra_materiais":    materiais[:50],
    }


def resumir_compras(dados: dict) -> dict:
    """Condensa dados de compras em estatísticas."""
    requisicoes = dados.get("solicitacoesMaterialMestre", [])
    ocs_diretas = dados.get("ordensCompraMestreSemCotacaoOuSemRequisicao", [])

    todas_ocs = [oc for req in requisicoes
                 for oc in req.get("ordemCompraMestreResumidaList", [])]

    valor_total = sum(oc.get("valorTotalCompras", 0) or 0 for oc in todas_ocs)
    valor_frete = sum(oc.get("valorFrete", 0) or 0 for oc in todas_ocs)
    valor_merc  = sum(oc.get("valorMercadorias", 0) or 0 for oc in todas_ocs)
    valor_desc  = sum(oc.get("valorDesconto", 0) or 0 for oc in todas_ocs)

    # Top fornecedores
    forn_counter = Counter()
    for oc in todas_ocs:
        f = (oc.get("fornecedorResumido") or {})
        nome = f.get("nomeRazao") or f.get("nomeFantasia") or f"ID {f.get('id','?')}"
        forn_counter[nome] += oc.get("valorTotalCompras", 0) or 0

    # Req sem OC
    req_sem_oc = [r for r in requisicoes
                  if not r.get("ordemCompraMestreResumidaList")]

    # OCs sem cotação
    req_sem_cot = [r for r in requisicoes
                   if not r.get("cotacaoMestreResumidoList")]

    return {
        "total_requisicoes":    len(requisicoes),
        "total_ocs":            len(todas_ocs),
        "ocs_diretas_sem_req":  len(ocs_diretas),
        "req_sem_oc":           len(req_sem_oc),
        "req_sem_cotacao":      len(req_sem_cot),
        "valor_total_comprado": round(valor_total, 2),
        "valor_mercadorias":    round(valor_merc, 2),
        "valor_frete":          round(valor_frete, 2),
        "frete_pct":            round(valor_frete / valor_merc * 100, 1) if valor_merc else 0,
        "valor_desconto":       round(valor_desc, 2),
        "ticket_medio_oc":      round(valor_total / len(todas_ocs), 2) if todas_ocs else 0,
        "top_15_fornecedores":  [{"fornecedor": k, "valor": round(v, 2)}
                                  for k, v in forn_counter.most_common(15)],
        "amostra_requisicoes":  requisicoes[:30],
        "ocs_diretas_lista":    ocs_diretas[:20],
    }


def serializar_seguro(dados, limite=100) -> str:
    """Serializa com limite de registros."""
    if isinstance(dados, list) and len(dados) > limite:
        dados = dados[:limite]
    return json.dumps(dados, ensure_ascii=False, indent=2, default=str)
