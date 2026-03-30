"""
=============================================================
  PROMPTS — Templates otimizados para dados reais do CRTI
  Usa resumidor para não ultrapassar limite de tokens do Claude
=============================================================
"""

import json
from datetime import datetime


def _s(dados, limite=80) -> str:
    """Serializa com limite de registros para evitar overflow."""
    if isinstance(dados, list) and len(dados) > limite:
        dados = dados[:limite]
    return json.dumps(dados, ensure_ascii=False, indent=2, default=str)


# ═══════════════════════════════════════════════════════
#  FINANCEIRO
# ═══════════════════════════════════════════════════════

def prompt_auditoria_financeira(dados: dict, periodo: str) -> str:
    from modules.resumidor import resumir_transferencias
    trf   = resumir_transferencias(dados.get("transferencias", []))
    perms = dados.get("permutas", [])[:30]
    contas = dados.get("contas_correntes", [])

    return f"""
Você é um auditor financeiro sênior analisando os dados do ERP CRTI da empresa BRITAGEM VOGELSANGER LTDA.

Período: {periodo}

═══ RESUMO ESTATÍSTICO — TRANSFERÊNCIAS ═══
{_s(trf, 999)}

═══ PERMUTAS/NEGOCIAÇÕES (amostra) ═══
{_s(perms)}

═══ CONTAS CORRENTES ═══
{_s(contas)}

Realize uma auditoria financeira completa:

### 1. DUPLICATAS SUSPEITAS
- Fornecedores com mesmo valor em datas próximas
- Documentos com numeração repetida

### 2. VALORES ATÍPICOS
- Transferências muito acima da média (ticket médio: R$ {trf.get('ticket_medio', 0):,.2f})
- Casos com juros ou descontos excessivos

### 3. ANÁLISE DE FORNECEDORES
- Concentração nos top fornecedores
- Fornecedores com múltiplas transferências sequenciais

### 4. PERMUTAS — SITUAÇÃO
- Permutas pendentes ou bloqueadas sem resolução

### 5. CONTAS BANCÁRIAS
- Contas sem uso ou inativas
- Distribuição entre tipos de conta

### 6. RESUMO EXECUTIVO
- Score de risco: BAIXO / MÉDIO / ALTO
- Top 3 achados mais relevantes
- Ações recomendadas

**Dados do período:** {trf.get('total_documentos',0)} documentos | R$ {trf.get('valor_total_emitido',0):,.2f} total | {len(perms)} permutas | {len(contas)} contas
"""


def prompt_analise_contas_pagar_receber(transferencias: list, periodo: str) -> str:
    from modules.resumidor import resumir_transferencias
    res = resumir_transferencias(transferencias)

    return f"""
Você é um analista financeiro sênior especializado em gestão de fluxo de caixa — BRITAGEM VOGELSANGER LTDA.

Período: {periodo}
Total de documentos: {res['total_documentos']}
Valor total emitido: R$ {res['valor_total_emitido']:,.2f}
Valor líquido total: R$ {res['valor_liquido_total']:,.2f}
Total de juros: R$ {res['total_juros']:,.2f}
Total de descontos: R$ {res['total_descontos']:,.2f}
Ticket médio: R$ {res['ticket_medio']:,.2f}
Total de parcelas: {res['total_parcelas']}
Média parcelas/doc: {res['media_parcelas_por_doc']}

═══ TOP 15 FORNECEDORES POR VALOR ═══
{_s(res['top_15_fornecedores'], 999)}

═══ DISTRIBUIÇÃO POR MÊS ═══
{_s(res['distribuicao_por_mes'], 999)}

═══ AMOSTRA DE DOCUMENTOS ═══
{_s(res['amostra_documentos'], 999)}

Análise de contas a pagar/receber:

### 1. VISÃO GERAL DO PERÍODO
- Performance vs expectativa
- Distribuição por fornecedor e período

### 2. ANÁLISE DE PARCELAS E VENCIMENTOS
- Concentração de vencimentos
- Risco de aperto de caixa

### 3. ANÁLISE POR FORNECEDOR
- Top fornecedores e concentração
- Parcelamentos longos

### 4. JUROS E DESCONTOS
- Impacto no resultado
- Oportunidades de negociação

### 5. ALERTAS E RECOMENDAÇÕES
- Vencimentos críticos
- Oportunidades de melhoria
"""


def prompt_analise_financeira_mensal(dados: dict, periodo: str) -> str:
    from modules.resumidor import resumir_transferencias
    trf = resumir_transferencias(dados.get("transferencias_emissao", []))
    contas = dados.get("contas_correntes", [])

    return f"""
Você é o CFO da BRITAGEM VOGELSANGER LTDA analisando os resultados financeiros do período.

Período: {periodo}

═══ RESUMO FINANCEIRO DO PERÍODO ═══
Total de documentos:     {trf['total_documentos']}
Valor total emitido:     R$ {trf['valor_total_emitido']:,.2f}
Valor líquido total:     R$ {trf['valor_liquido_total']:,.2f}
Total de juros pagos:    R$ {trf['total_juros']:,.2f}
Total de descontos:      R$ {trf['total_descontos']:,.2f}
Ticket médio:            R$ {trf['ticket_medio']:,.2f}
Total de parcelas:       {trf['total_parcelas']}
Média parcelas/doc:      {trf['media_parcelas_por_doc']}
Contas bancárias ativas: {len(contas)}

═══ TOP 15 FORNECEDORES ═══
{_s(trf['top_15_fornecedores'], 999)}

═══ DISTRIBUIÇÃO MENSAL ═══
{_s(trf['distribuicao_por_mes'], 999)}

═══ CONTAS CORRENTES ═══
{_s(contas)}

═══ AMOSTRA DE LANÇAMENTOS ═══
{_s(trf['amostra_documentos'], 999)}

Elabore análise financeira executiva completa:

### 1. RESULTADO DO PERÍODO
- Total movimentado e composição
- Comparativo entre emissões e vencimentos
- Ticket médio e volume

### 2. POSIÇÃO BANCÁRIA
- Contas ativas e distribuição por banco/filial
- Tipos de conta utilizados

### 3. ANÁLISE DE FLUXO
- Concentração de pagamentos
- Picos identificados
- Janelas de folga financeira

### 4. QUALIDADE DOS TÍTULOS
- Impacto de juros e descontos no resultado
- Prazo médio das operações
- Parcelas por documento

### 5. ANÁLISE DE FORNECEDORES
- Concentração (top 15 representam qual % do total?)
- Risco de dependência
- Fornecedores com maior volume

### 6. RECOMENDAÇÕES ESTRATÉGICAS
- 3 ações prioritárias com base nos dados
- Riscos identificados
- Oportunidades de melhoria financeira

Escreva em linguagem executiva para apresentação à diretoria. Use R$ e % em todos os valores.
"""


def prompt_relatorio_permutas(permutas: list, periodo: str) -> str:
    por_situacao = {}
    for p in permutas:
        sit = str(p.get("situacaoPermuta", "?"))
        por_situacao.setdefault(sit, []).append(p)

    return f"""
Você é um analista de negociações comerciais — BRITAGEM VOGELSANGER LTDA.

Período: {periodo}
Total de permutas: {len(permutas)}
Distribuição: {{{', '.join(f'Situação {k}: {len(v)}' for k, v in por_situacao.items())}}}

Situações: 1=Pendente, 2=Liberado, 3=Finalizado, 4=Bloqueado, 5=Cancelado

═══ DADOS DAS PERMUTAS ═══
{_s(permutas)}

### 1. STATUS GERAL
- Resumo por situação com percentuais
- Tempo médio em cada situação

### 2. PERMUTAS QUE EXIGEM ATENÇÃO
- Pendentes sem definição
- Bloqueadas sem resolução

### 3. ANÁLISE POR PARTICIPANTE
- Principais parceiros
- Concentração de negociações

### 4. RECOMENDAÇÕES
- Permutas para resolver com urgência
"""


# ═══════════════════════════════════════════════════════
#  SUPRIMENTOS
# ═══════════════════════════════════════════════════════

def prompt_auditoria_materiais(materiais: list) -> str:
    from modules.resumidor import resumir_materiais
    res = resumir_materiais(materiais)

    return f"""
Você é um auditor de suprimentos — BRITAGEM VOGELSANGER LTDA.

═══ RESUMO DO CADASTRO ═══
Total de materiais: {res['total_materiais']}
Ativos: {res['ativos']} | Inativos: {res['inativos']}
Sem NCM: {res['sem_ncm']} (risco fiscal)
Sem preço: {res['sem_preco']}
Sem grupo: {res['sem_grupo']}
Sem EAN: {res['sem_ean']}
Com controle de estoque: {res['com_controle_estoque']}
Score de completude: {res['completude_pct']}%

═══ DISTRIBUIÇÃO POR GRUPO ═══
{_s(res['por_grupo'], 999)}

═══ TOP 20 MATERIAIS MAIS INCOMPLETOS ═══
{_s(res['top_20_incompletos'], 999)}

═══ AMOSTRA DO CADASTRO ═══
{_s(res['amostra_materiais'], 999)}

Auditoria completa do cadastro de materiais:

### 1. QUALIDADE DO CADASTRO
- Campos críticos em branco (NCM, preço, unidade)
- Materiais com descrição insuficiente

### 2. RISCO FISCAL
- Materiais sem NCM (impedem emissão de NF-e)
- Configurações de CFOP ausentes

### 3. CONTROLE DE ESTOQUE
- Materiais sem ponto de reposição configurado
- Configurações inconsistentes de mínimo/máximo

### 4. PREÇOS E VALORES
- Materiais sem preço cadastrado
- Discrepâncias entre preço comercial e tributário

### 5. RESUMO EXECUTIVO
- Score de qualidade: {res['completude_pct']}% completo
- Principais riscos e ações prioritárias
"""


def prompt_relatorio_estoque_critico(materiais_com_controle: list) -> str:
    total = len(materiais_com_controle)
    alertas = []
    for m in materiais_com_controle:
        for ce in (m.get("materiaisControleEstoque") or []):
            est_min = ce.get("estoqueMinimo", 0) or 0
            est_max = ce.get("estoqueMaximo", 0) or 0
            if est_min == 0:
                alertas.append({"material": m.get("descricao"), "filial": (ce.get("filial") or {}).get("nome"), "problema": "Estoque mínimo zerado"})
            elif est_max > 0 and est_min >= est_max:
                alertas.append({"material": m.get("descricao"), "filial": (ce.get("filial") or {}).get("nome"), "problema": "Mínimo >= Máximo"})

    return f"""
Você é um analista de supply chain — BRITAGEM VOGELSANGER LTDA.

Total de materiais com controle de estoque: {total}
Alertas identificados: {len(alertas)}

═══ ALERTAS DE CONFIGURAÇÃO ═══
{_s(alertas, 999)}

═══ MATERIAIS COM CONTROLE ═══
{_s(materiais_com_controle[:60], 999)}

### 1. VISÃO GERAL
- Total controlado por filial
- Distribuição por grupo

### 2. ALERTAS CRÍTICOS
- Mínimos zerados (sem ponto de reposição)
- Configurações impossíveis (mínimo >= máximo)
- Filiais com configurações incompletas

### 3. RECOMENDAÇÕES
- Materiais para revisão urgente
- Padronização entre filiais
"""


# ═══════════════════════════════════════════════════════
#  CUSTOS
# ═══════════════════════════════════════════════════════

def prompt_analise_servicos_filial(servicos_por_filial: dict) -> str:
    total_realizado = 0
    total_contrato  = 0
    total_servicos  = 0
    for servicos in servicos_por_filial.values():
        for s in servicos:
            total_realizado += s.get("valorTotal", 0) or 0
            total_contrato  += s.get("valorTotalContrato", 0) or 0
            total_servicos  += 1

    desvio = total_realizado - total_contrato
    perc   = (desvio / total_contrato * 100) if total_contrato else 0

    # Top desvios
    todos_servicos = [s for servs in servicos_por_filial.values() for s in servs]
    com_desvio = sorted(
        [s for s in todos_servicos if s.get("valorTotalContrato", 0)],
        key=lambda s: abs((s.get("valorTotal", 0) or 0) - (s.get("valorTotalContrato", 0) or 0)),
        reverse=True
    )[:30]

    return f"""
Você é um controller de custos — BRITAGEM VOGELSANGER LTDA.

Filiais: {len(servicos_por_filial)} | Serviços: {total_servicos}
Realizado: R$ {total_realizado:,.2f} | Contratado: R$ {total_contrato:,.2f}
Desvio: R$ {desvio:,.2f} ({perc:+.1f}%)

═══ TOP 30 SERVIÇOS COM MAIOR DESVIO ═══
{_s(com_desvio, 999)}

═══ TODOS OS SERVIÇOS POR FILIAL (amostra) ═══
{_s({k: v[:20] for k, v in servicos_por_filial.items()}, 999)}

### 1. VISÃO GERAL — REALIZADO VS CONTRATADO
### 2. SERVIÇOS ACIMA DO CONTRATO (top desvios positivos)
### 3. SERVIÇOS ABAIXO DE 80% DO CONTRATO
### 4. ANÁLISE POR FILIAL
### 5. ALERTAS E RECOMENDAÇÕES
"""


def prompt_analise_perdas_equipamentos(blepdv_lista: list, perdas_config: list) -> str:
    total_horas_disp   = sum(b.get("horasDisponiveis", 0) or 0 for b in blepdv_lista)
    total_horas_perdas = sum(p.get("totalHoras", 0) or 0
                             for b in blepdv_lista for p in (b.get("perdas") or []))
    total_horas_serv   = sum(s.get("tempoGastoHoras", 0) or 0
                             for b in blepdv_lista for s in (b.get("servicos") or []))
    efic = (total_horas_serv / total_horas_disp * 100) if total_horas_disp else 0

    return f"""
Você é um analista de eficiência operacional — BRITAGEM VOGELSANGER LTDA.

Registros BLE/PDV: {len(blepdv_lista)}
Horas disponíveis: {total_horas_disp:.1f}h
Horas produtivas:  {total_horas_serv:.1f}h
Horas de perdas:   {total_horas_perdas:.1f}h
Eficiência global: {efic:.1f}%

═══ CONFIGURAÇÃO DE PERDAS ═══
{_s(perdas_config, 999)}

═══ REGISTROS BLE/PDV ═══
{_s(blepdv_lista[:60], 999)}

### 1. EFICIÊNCIA GLOBAL DA FROTA
### 2. ANÁLISE DE PERDAS POR TIPO
### 3. ANÁLISE POR EQUIPAMENTO
### 4. ANÁLISE POR TURNO
### 5. RECOMENDAÇÕES
"""


def prompt_analise_bmo(bmo_lista: list, periodo: str) -> str:
    funcionarios = set()
    total_horas_extra = 0
    for bmo in bmo_lista:
        for srv in (bmo.get("servicos") or []):
            func = srv.get("funcionario", {})
            if func.get("chapa"):
                funcionarios.add(func["chapa"])
            total_horas_extra += srv.get("horaExtra", 0) or 0

    return f"""
Você é um analista de RH e produtividade — BRITAGEM VOGELSANGER LTDA.

Período: {periodo}
BMOs: {len(bmo_lista)} | Funcionários únicos: {len(funcionarios)}
Total horas extras: {total_horas_extra}h

═══ DADOS DOS BMOs ═══
{_s(bmo_lista[:40], 999)}

### 1. HORAS EXTRAS — ANÁLISE E RISCO
### 2. CONFORMIDADE DE JORNADA
### 3. PRODUTIVIDADE POR ENCARREGADO
### 4. PADRÕES SUSPEITOS
### 5. RESUMO EXECUTIVO
"""


# ═══════════════════════════════════════════════════════
#  COMPRAS
# ═══════════════════════════════════════════════════════

def prompt_auditoria_compras(dados_compras: dict, periodo: str) -> str:
    from modules.resumidor import resumir_compras
    import json

    res = resumir_compras(dados_compras)

    # Extrai dados detalhados das OCs diretas para listar individualmente
    ocs_diretas_raw = dados_compras.get("ordensCompraMestreSemCotacaoOuSemRequisicao", [])
    ocs_detalhadas = []
    for d in ocs_diretas_raw:
        oc = d.get("ordemCompraMestreResumida", d)
        forn = (oc.get("fornecedorResumido") or {})
        ocs_detalhadas.append({
            "id":           oc.get("id"),
            "data":         oc.get("dataOrdemCompra"),
            "fornecedor":   forn.get("nomeRazao") or forn.get("nomeFantasia","?"),
            "cnpj":         forn.get("cnpj",""),
            "descricao":    oc.get("descricao",""),
            "valor":        oc.get("valorTotalCompras", 0),
            "situacao":     oc.get("descricaoSituacao",""),
            "entrega":      oc.get("descricaoSituacaoEntrega",""),
            "comprador":    (oc.get("compradorResumido") or {}).get("nomeCompleto",""),
            "prazo_entrega":oc.get("descricaoPrazoEntrega",""),
            "itens": [
                {
                    "material": (i.get("materialResumido") or {}).get("descricao","?"),
                    "qtde":     i.get("quantidade"),
                    "valor":    i.get("valorTotal"),
                }
                for i in (oc.get("itens") or [])
            ]
        })

    # Requisições sem cotação detalhadas
    reqs_sem_cot = []
    for req_wrapper in dados_compras.get("solicitacoesMaterialMestre", []):
        if not req_wrapper.get("cotacaoMestreResumidoList"):
            req = req_wrapper.get("solicitacaoMaterialMestreResumido", {})
            ocs = req_wrapper.get("ordemCompraMestreResumidaList", [])
            valor_oc = sum(o.get("valorTotalCompras",0) or 0 for o in ocs)
            reqs_sem_cot.append({
                "id":          req.get("id"),
                "data":        req.get("dataSolicitacao"),
                "solicitante": (req.get("funcionarioSolicitacao") or {}).get("nome","?"),
                "comprador":   (req.get("comprador") or {}).get("nomeCompleto",""),
                "situacao":    req.get("situacao",""),
                "valor_oc":    valor_oc,
                "materiais": [
                    (i.get("materialResumido") or {}).get("descricao","?")
                    for i in (req.get("listSolicitacaoItens") or [])
                ]
            })

    return f"""
Você é um auditor de compras sênior — BRITAGEM VOGELSANGER LTDA.

Período: {periodo}

═══ RESUMO DO PIPELINE ═══
Requisições:              {res['total_requisicoes']}
Ordens de compra:         {res['total_ocs']}
OCs SEM REQUISIÇÃO:       {res['ocs_diretas_sem_req']} ⚠️
Requisições sem OC:       {res['req_sem_oc']}
Requisições sem cotação:  {res['req_sem_cotacao']}
Valor total comprado:     R$ {res['valor_total_comprado']:,.2f}
  Mercadorias:            R$ {res['valor_mercadorias']:,.2f}
  Frete:                  R$ {res['valor_frete']:,.2f} ({res['frete_pct']}%)
  Descontos:              R$ {res['valor_desconto']:,.2f}
Ticket médio OC:          R$ {res['ticket_medio_oc']:,.2f}

═══ LISTA COMPLETA — OCs SEM REQUISIÇÃO/COTAÇÃO (BYPASS) ═══
Total: {len(ocs_detalhadas)} OCs | Valor: R$ {sum(o['valor'] or 0 for o in ocs_detalhadas):,.2f}
{_s(ocs_detalhadas, 999)}

═══ LISTA COMPLETA — REQUISIÇÕES SEM COTAÇÃO ═══
Total: {len(reqs_sem_cot)} requisições
{_s(reqs_sem_cot, 999)}

═══ TOP 15 FORNECEDORES ═══
{_s(res['top_15_fornecedores'], 999)}

═══ AMOSTRA DE REQUISIÇÕES COM PROCESSO COMPLETO ═══
{_s(res['amostra_requisicoes'][:15], 999)}

### 1. CONFORMIDADE DO PROCESSO — LISTA DETALHADA DE BYPASS

**OCs geradas sem requisição/cotação — liste TODAS em tabela:**
| ID OC | Data | Fornecedor | CNPJ | Materiais | Valor | Comprador | Situação Entrega |

Para cada OC liste os itens comprados.
Agrupe por fornecedor recorrente e identifique padrões.
Destaque as 10 de maior valor com análise de risco.

**Requisições sem cotação — liste TODAS:**
| ID Req | Data | Solicitante | Comprador | Materiais | Valor OC |

Identifique se há concentração em mesmo comprador ou fornecedor.

### 2. ANÁLISE DE RISCO POR FORNECEDOR
- Fornecedores que aparecem repetidamente no bypass
- Valor acumulado por fornecedor no bypass
- Risco de favorecimento

### 3. ANÁLISE DAS ORDENS DE COMPRA REGULARES
- OCs com entrega em atraso
- Materiais pagos e não entregues (sem entrada de NF)
- Lead times médios

### 4. CONCENTRAÇÃO DE FORNECEDORES
- Top fornecedores e % de concentração
- Risco de dependência

### 5. ALERTAS CRÍTICOS
| ID | TIPO DE RISCO | FORNECEDOR | VALOR | COMPRADOR | AÇÃO RECOMENDADA |

### 6. RESUMO EXECUTIVO
- Score de conformidade: X% (calcule: OCs com processo correto / total OCs)
- Valor em risco (bypass): R$ X
- Top 3 riscos com maior impacto financeiro
- Recomendações prioritárias para regularização

Use R$ em todos os valores. Liste IDs reais das OCs — não generalize.
"""


def prompt_relatorio_compras_gerencial(dados_compras: dict, periodo: str) -> str:
    from modules.resumidor import resumir_compras
    res = resumir_compras(dados_compras)

    return f"""
Você é o gerente de suprimentos — BRITAGEM VOGELSANGER LTDA.

Período: {periodo}

═══ RESUMO EXECUTIVO ═══
Requisições: {res['total_requisicoes']} | OCs: {res['total_ocs']}
Valor total: R$ {res['valor_total_comprado']:,.2f}
Mercadorias: R$ {res['valor_mercadorias']:,.2f}
Frete:       R$ {res['valor_frete']:,.2f} ({res['frete_pct']}%)
Descontos:   R$ {res['valor_desconto']:,.2f}
Ticket médio: R$ {res['ticket_medio_oc']:,.2f}

═══ TOP 15 FORNECEDORES ═══
{_s(res['top_15_fornecedores'], 999)}

═══ AMOSTRA DE OCs ═══
{_s(res['amostra_requisicoes'][:20], 999)}

### 1. VOLUME E VALOR DO PERÍODO
### 2. TOP FORNECEDORES
### 3. PERFORMANCE DE COMPRAS (lead times, prazo)
### 4. DESCONTOS OBTIDOS
### 5. RECOMENDAÇÕES
"""


# ═══════════════════════════════════════════════════════
#  FROTA E EQUIPAMENTOS
# ═══════════════════════════════════════════════════════

def prompt_auditoria_frota(dados_frota: dict, periodo: str) -> str:
    from modules.resumidor import resumir_equipamentos, resumir_os_manutencao
    equip = resumir_equipamentos(dados_frota.get("equipamentos", []))
    osm   = resumir_os_manutencao(dados_frota.get("os_manutencao", []))
    trf   = dados_frota.get("transferencias", [])[:30]

    return f"""
Você é o gestor de frota sênior — BRITAGEM VOGELSANGER LTDA.

Período: {periodo}

═══ RESUMO DA FROTA ═══
Total de equipamentos:    {equip['total_equipamentos']}
Valor de aquisição:       R$ {equip['valor_aquisicao_total']:,.2f}
Valor de mercado:         R$ {equip['valor_mercado_total']:,.2f}
Depreciação:              R$ {equip['depreciacao_total']:,.2f} ({equip['depreciacao_pct']}%)
Seguros VENCIDOS:         {equip['seguros_vencidos']} ⚠️
Sem seguro:               {equip['sem_seguro']}
Sem nº patrimonial:       {equip['sem_num_patrimonial']}
De subempreiteiros:       {equip['de_subempreiteiros']}

═══ RESUMO DE MANUTENÇÃO ═══
Total de OS:              {osm['total_os']}
OS atrasadas:             {osm['os_atrasadas']} ⚠️
Por situação:             {osm['por_situacao']}

═══ SEGUROS VENCIDOS ═══
{_s(equip['lista_seguros_vencidos'], 999)}

═══ OS ATRASADAS ═══
{_s(osm['lista_atrasadas'], 999)}

═══ TOP 10 EQUIPAMENTOS EM MANUTENÇÃO ═══
{_s(osm['top_10_equipamentos'], 999)}

═══ TOP 10 DEFEITOS ═══
{_s(osm['top_10_defeitos'], 999)}

═══ TRANSFERÊNCIAS DO PERÍODO ═══
{_s(trf, 999)}

═══ DISTRIBUIÇÃO POR GRUPO ═══
{_s(equip['por_grupo'], 999)}

═══ AMOSTRA DE EQUIPAMENTOS ═══
{_s(equip['amostra_equipamentos'][:30], 999)}

### 1. SEGUROS — RISCO IMEDIATO (liste equipamentos com seguro vencido)
### 2. PATRIMÔNIO E DEPRECIAÇÃO
### 3. MANUTENÇÃO — OS CRÍTICAS
### 4. TRANSFERÊNCIAS — ANORMALIDADES
### 5. ALERTAS CRÍTICOS (tabela: Risco | Equipamento | Placa | Ação)
### 6. RESUMO EXECUTIVO (score de saúde da frota: X/100)
"""


def prompt_relatorio_manutencao(os_lista: list, periodo: str) -> str:
    from modules.resumidor import resumir_os_manutencao
    res = resumir_os_manutencao(os_lista)

    return f"""
Você é o gerente de manutenção — BRITAGEM VOGELSANGER LTDA.

Período: {periodo}
Total de OS: {res['total_os']}
OS atrasadas: {res['os_atrasadas']}
Por situação: {res['por_situacao']}

═══ TOP 10 EQUIPAMENTOS COM MAIS OS ═══
{_s(res['top_10_equipamentos'], 999)}

═══ TOP 10 DEFEITOS ═══
{_s(res['top_10_defeitos'], 999)}

═══ OS ATRASADAS ═══
{_s(res['lista_atrasadas'], 999)}

═══ AMOSTRA DE OS ═══
{_s(res['amostra_os'], 999)}

### 1. VOLUME E STATUS DAS OS
### 2. TOP EQUIPAMENTOS EM MANUTENÇÃO
### 3. ANÁLISE DE DEFEITOS
### 4. EFICIÊNCIA DA EQUIPE
### 5. RECOMENDAÇÕES
"""


def prompt_relatorio_patrimonio_frota(equipamentos: list) -> str:
    from modules.resumidor import resumir_equipamentos
    res = resumir_equipamentos(equipamentos)

    return f"""
Você é o controller patrimonial — BRITAGEM VOGELSANGER LTDA.

═══ RESUMO PATRIMONIAL ═══
Total de equipamentos: {res['total_equipamentos']}
Valor de aquisição:    R$ {res['valor_aquisicao_total']:,.2f}
Valor de mercado:      R$ {res['valor_mercado_total']:,.2f}
Depreciação:           R$ {res['depreciacao_total']:,.2f} ({res['depreciacao_pct']}%)
Receita locação/mês:   R$ {res['valor_locacao_mensal']:,.2f}
De subempreiteiros:    {res['de_subempreiteiros']}
Sem nº patrimonial:    {res['sem_num_patrimonial']}
Seguros vencidos:      {res['seguros_vencidos']}

═══ DISTRIBUIÇÃO POR GRUPO ═══
{_s(res['por_grupo'], 999)}

═══ SEGUROS VENCIDOS ═══
{_s(res['lista_seguros_vencidos'], 999)}

═══ AMOSTRA DO CADASTRO ═══
{_s(res['amostra_equipamentos'], 999)}

### 1. INVENTÁRIO POR GRUPO (tabela: Grupo | Qtde | Valor Aquisição | Valor Mercado | Depreciação %)
### 2. PRÓPRIOS VS TERCEIROS/LOCAÇÃO
### 3. ANÁLISE DE DEPRECIAÇÃO
### 4. SEGUROS — COBERTURA E GAPS
### 5. NUMERAÇÃO PATRIMONIAL
### 6. RECOMENDAÇÕES PARA CONTROLADORIA
"""


# ═══════════════════════════════════════════════════════
#  PROMPTS — MÓDULO VENDAS
# ═══════════════════════════════════════════════════════

def prompt_clientes_inativos(dados: dict) -> str:
    """Análise de clientes inativos com estratégia de reativação."""
    resumo   = dados.get("resumo", {})
    inativos = dados.get("inativos", [])
    ativos   = dados.get("ativos_recentes", [])

    valor_inativos = sum(c.get("total_historico", 0) for c in inativos)
    valor_ativos   = sum(c.get("total_historico", 0) for c in ativos)

    return f"""
Você é um gerente comercial sênior da BRITAGEM VOGELSANGER LTDA analisando a carteira de clientes.

═══ RESUMO DA CARTEIRA ═══
Total de clientes com histórico: {resumo.get('total_clientes', 0)}
Clientes INATIVOS (sem comprar há +{resumo.get('dias_corte', 60)} dias): {resumo.get('inativos', 0)} ({resumo.get('pct_inativo', 0)}%)
Clientes ativos recentes: {resumo.get('ativos', 0)}
Período analisado: últimos {resumo.get('periodo_analise', 365)} dias

Valor histórico dos inativos: R$ {valor_inativos:,.2f}
Valor histórico dos ativos:   R$ {valor_ativos:,.2f}

═══ CLIENTES INATIVOS (ordenados por tempo sem comprar) ═══
{_s(inativos[:50], 999)}

═══ TOP 20 CLIENTES ATIVOS ═══
{_s(ativos[:20], 999)}

Elabore um relatório completo de análise de carteira:

### 1. VISÃO GERAL DA CARTEIRA
- Distribuição ativo/inativo com % e valores
- Receita em risco (valor histórico dos inativos)
- Tempo médio de inatividade

### 2. CLIENTES INATIVOS — PRIORIDADE DE REATIVAÇÃO
Classifique em 3 grupos por prioridade:
- 🔴 **URGENTE** (inativos há 60-120 dias, alto valor histórico)
- 🟡 **ATENÇÃO** (inativos há 120-180 dias)
- ⚫ **PERDIDOS** (inativos há +180 dias)

Para cada grupo liste: Cliente | Último pedido | Dias sem comprar | Valor histórico | Ticket médio

### 3. ANÁLISE DE PADRÃO
- Clientes que compravam regularmente e pararam (frequência alta → zero)
- Clientes sazonais (padrão esperado vs inesperado)
- Mês/período em que ocorreram mais inativos

### 4. ESTRATÉGIA DE REATIVAÇÃO
Para cada grupo de prioridade, sugira ação específica:
- Script de abordagem comercial
- Tipo de oferta/condição especial
- Canal de contato recomendado (visita, ligação, email)

### 5. TOP 10 CLIENTES ATIVOS — PROTEÇÃO
- Clientes mais valiosos que precisam de atenção especial
- Frequência de compra e tendência

### 6. RESUMO EXECUTIVO
- Receita recuperável estimada (% dos inativos que podem voltar)
- Meta de reativação recomendada para o mês
- KPI sugerido: taxa de reativação mensal

Use R$ e % em todos os valores. Tom direto para a equipe comercial.
"""


def prompt_analise_vendas(pedidos: list, orcamentos: list, periodo: str) -> str:
    """Análise completa de vendas: pedidos, orçamentos, conversão."""
    from collections import Counter

    total_pedidos   = len(pedidos)
    total_orc       = len(orcamentos)
    valor_pedidos   = sum(p.get("valorTotalPedido", 0) or 0 for p in pedidos)

    # Por situação
    sit_pedidos = Counter(p.get("situacaoPedido", "?") for p in pedidos)
    sit_orc     = Counter(o.get("situacao", "?") for o in orcamentos)

    # Por cliente
    clientes_pedido = Counter()
    for p in pedidos:
        cli = (p.get("cliente") or {}).get("nomeRazao", "?")
        clientes_pedido[cli] += p.get("valorTotalPedido", 0) or 0

    # Por vendedor
    vendedores = Counter()
    for p in pedidos:
        v = (p.get("vendedorPedido") or {}).get("nomeVendedor", "Sem vendedor")
        vendedores[v] += p.get("valorTotalPedido", 0) or 0

    # Materiais mais vendidos
    materiais = Counter()
    for p in pedidos:
        for m in (p.get("materiaisPedido") or []):
            nome = (m.get("material") or {}).get("descricao", "?")
            materiais[nome] += m.get("quantidade", 0) or 0

    # Taxa de conversão
    orc_aprovados = sit_orc.get("APROVADO", 0) + sit_orc.get("CONCLUIDO", 0)
    taxa_conv = (orc_aprovados / total_orc * 100) if total_orc else 0

    return f"""
Você é o diretor comercial da BRITAGEM VOGELSANGER LTDA apresentando resultados para a diretoria.

Período: {periodo}

═══ RESUMO DE VENDAS ═══
Pedidos no período:     {total_pedidos}
Valor total:            R$ {valor_pedidos:,.2f}
Ticket médio:           R$ {(valor_pedidos/total_pedidos):,.2f if total_pedidos else 0}
Orçamentos emitidos:    {total_orc}
Taxa de conversão ORC→PED: {taxa_conv:.1f}%

Por situação (pedidos): {dict(sit_pedidos)}
Por situação (orçamentos): {dict(sit_orc)}

═══ TOP 15 CLIENTES POR VALOR ═══
{_s(clientes_pedido.most_common(15), 999)}

═══ RANKING DE VENDEDORES ═══
{_s(vendedores.most_common(10), 999)}

═══ TOP 10 MATERIAIS MAIS VENDIDOS (quantidade) ═══
{_s(materiais.most_common(10), 999)}

═══ AMOSTRA DE PEDIDOS ═══
{_s(pedidos[:30], 999)}

═══ AMOSTRA DE ORÇAMENTOS ═══
{_s(orcamentos[:20], 999)}

Elabore relatório gerencial completo de vendas:

### 1. RESULTADO DO PERÍODO
- Volume total e comparativo
- Distribuição por situação (concluído, aprovado, pendente, cancelado)
- Ticket médio e tendência

### 2. ANÁLISE DE CLIENTES
- Top 15 clientes por valor
- Concentração: top 3 representam X% do total
- Clientes novos vs recorrentes (se identificável pela data)

### 3. PERFORMANCE DE VENDEDORES
- Ranking por valor vendido
- Participação % de cada vendedor no total

### 4. PRODUTOS MAIS VENDIDOS
- Top materiais por quantidade e valor
- Mix de produtos por cliente

### 5. PIPELINE DE ORÇAMENTOS
- Orçamentos em aberto (aguardando aprovação)
- Taxa de conversão: orçamento → pedido aprovado
- Valor potencial em orçamentos pendentes (saldo)
- Orçamentos reprovados: principais motivos

### 6. ALERTAS COMERCIAIS
- Pedidos aguardando aprovação há muito tempo
- Orçamentos próximos do vencimento da validade
- Clientes sem pedido no período (possíveis inativos)

### 7. RESUMO EXECUTIVO
- Top 3 conquistas do período
- Top 3 oportunidades identificadas
- Recomendações para o próximo período

Tom executivo para apresentação à diretoria. Use R$ e % em todos os valores.
"""
