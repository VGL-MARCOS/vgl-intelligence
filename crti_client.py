"""
=============================================================
  CRTI Intelligence — Cliente API v2
  Britagem Vogelsanger LTDA
  Todos os endpoints do Swagger BI mapeados
=============================================================
"""

import requests
import logging
from datetime import datetime, timedelta
from config import CRTI_CONFIG

logger = logging.getLogger(__name__)
DEFAULT_LIMIT = 500


class CRTIClient:
    def __init__(self):
        self.base_url      = CRTI_CONFIG["base_url"]
        self.timeout       = CRTI_CONFIG["timeout"]
        self.access_token  = None
        self.refresh_token = None
        self.session       = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

        self.xapi_key      = CRTI_CONFIG.get("xapi_key")
        self.client_id     = CRTI_CONFIG.get("client_id")
        self.client_secret = CRTI_CONFIG.get("client_secret")
        self.username      = CRTI_CONFIG.get("username")
        self.password      = CRTI_CONFIG.get("password")

        if self.xapi_key:
            self._autenticar_xapikey_direto()
        elif self.client_id and self.client_secret:
            self._autenticar_oauth2()
        else:
            self._autenticar()

    # ─── AUTENTICAÇÃO ────────────────────────────────────────────────────────

    def _autenticar_oauth2(self):
        logger.info("🔐 Autenticando via OAuth 2.0...")
        endpoints = ["/api/v1/auth/oauth/token", "/oauth/token", "/api/v1/auth/token"]
        for ep in endpoints:
            try:
                resp = requests.post(
                    f"{self.base_url}{ep}",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data={"grant_type": "client_credentials",
                          "client_id": self.client_id,
                          "client_secret": self.client_secret},
                    timeout=self.timeout
                )
                if resp.status_code == 200:
                    token = resp.json().get("access_token") or resp.json().get("accessToken")
                    if token:
                        self.access_token = token
                        self.session.headers.update({"Authorization": f"Bearer {token}"})
                        logger.info(f"✅ OAuth 2.0 via {ep}")
                        return
            except Exception:
                continue
        logger.warning("⚠️ OAuth falhou — tentando X-Api-Key...")
        self._autenticar_xapikey()

    def _autenticar_xapikey_direto(self):
        logger.info("🔑 Autenticando via X-Api-Key...")
        self.session.headers.update({"X-Api-Key": self.xapi_key})
        if self.client_id:
            self.session.headers.update({"X-Client-Id": self.client_id})
        try:
            resp = self.session.get(f"{self.base_url}/api/v1/auth/info", timeout=self.timeout)
            if resp.status_code == 200:
                logger.info("✅ Autenticado via X-Api-Key")
                return
        except Exception as e:
            logger.warning(f"⚠️ X-Api-Key erro: {e}")
        if self.username and self.password:
            self.session.headers.pop("X-Api-Key", None)
            self.session.headers.pop("X-Client-Id", None)
            self._autenticar()
        else:
            raise Exception("❌ Nenhum método de autenticação funcionou.")

    def _autenticar_xapikey(self):
        logger.info("🔑 Tentando X-Api-Key via client_secret...")
        self.session.headers.update({"X-Api-Key": self.client_secret, "X-Client-Id": self.client_id})
        try:
            resp = self.session.get(f"{self.base_url}/api/v1/auth/info", timeout=self.timeout)
            if resp.status_code == 200:
                logger.info("✅ Autenticado via X-Api-Key")
                return
        except Exception:
            pass
        raise Exception("❌ Nenhum método de autenticação funcionou.")

    def _autenticar(self):
        logger.info("🔐 Autenticando via usuário/senha...")
        resp = self.session.post(
            f"{self.base_url}/api/v1/auth/signin",
            json={"username": self.username, "password": self.password},
            timeout=self.timeout
        )
        resp.raise_for_status()
        dados = resp.json()
        self.access_token  = dados["accessToken"]
        self.refresh_token = dados.get("refreshToken")
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
        logger.info("✅ Autenticado via usuário/senha")

    def _renovar_token(self):
        resp = self.session.post(
            f"{self.base_url}/api/v1/auth/refresh_token",
            json={"refreshToken": self.refresh_token},
            timeout=self.timeout
        )
        resp.raise_for_status()
        dados = resp.json()
        self.access_token  = dados["accessToken"]
        self.refresh_token = dados["refreshToken"]
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    def _get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 401 and self.refresh_token:
                self._renovar_token()
                resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP {endpoint}: {e}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Sem conexão: {url}")
            raise

    def _get_paginado(self, endpoint: str, params: dict = None) -> list:
        params = params or {}
        params.setdefault("limit", DEFAULT_LIMIT)
        params.setdefault("page", 0)
        todos = []
        while True:
            dados = self._get(endpoint, params)
            items = dados.get("data", dados if isinstance(dados, list) else [])
            if isinstance(dados, list):
                return dados
            todos.extend(items)
            total = dados.get("totalLength", len(items))
            if len(todos) >= total or len(items) == 0:
                break
            params["page"] += 1
        return todos

    # ─── INFO EMPRESA ────────────────────────────────────────────────────────

    def buscar_info_empresa(self) -> dict:
        return self._get("/api/v1/auth/info")

    # ─── FINANCEIRO — ENDPOINTS LEGADOS ─────────────────────────────────────

    def buscar_transferencias(self, data_inicio: str, data_fim: str,
                               fornecedor_id: int = None, filial_ids: list = None) -> list:
        params = {"dataInicio": data_inicio, "dataFim": data_fim}
        if fornecedor_id: params["fornecedorId"] = fornecedor_id
        if filial_ids:    params["filiaisMovimento"] = filial_ids
        return self._get_paginado("/api/v1/financeiro/trf_pagar_receber", params)

    def buscar_contas_correntes(self, apenas_ativas: bool = True) -> list:
        return self._get_paginado("/api/v1/financeiro/conta_corrente",
                                   {"apenasAtivas": str(apenas_ativas).lower()})

    def buscar_permutas(self, data_inicio: str, data_fim: str) -> list:
        return self._get_paginado("/api/v1/financeiro/permuta",
                                   {"dataInicio": data_inicio, "dataFim": data_fim})

    # ─── FINANCEIRO — ENDPOINTS BI (SWAGGER) ─────────────────────────────────

    def bi_pendencias_baixas(self, tipo_conta: str, data_venc_de: str = None,
                              data_venc_ate: str = None, data_emissao_de: str = None,
                              data_emissao_ate: str = None, ids_filiais: list = None,
                              considerar_previsoes: bool = False) -> list:
        """
        GET /api/v1/bi/financeiro/pendencias_baixas
        tipo_conta: "PAGAR" ou "RECEBER"
        Retorna: idFornecedor, nomeFornecedor, dataVencimento, valorPrincipal,
                 valorPendente, valorPendenteFinal, juros, desconto,
                 diasVencimento, origemPagamento, contaContabil
        """
        params = {"tipo_conta": tipo_conta, "considerar_previsoes": considerar_previsoes}
        if data_venc_de:    params["data_vencimento_de"] = data_venc_de
        if data_venc_ate:   params["data_vencimento_ate"] = data_venc_ate
        if data_emissao_de: params["data_emissao_de"] = data_emissao_de
        if data_emissao_ate:params["data_emissao_ate"] = data_emissao_ate
        if ids_filiais:     params["ids_filiais_movimento"] = ids_filiais
        dados = self._get("/api/v1/bi/financeiro/pendencias_baixas", params)
        return dados if isinstance(dados, list) else dados.get("data", [])

    def bi_recebimentos_efetivados(self, data_inicio: str, data_fim: str,
                                    id_filial: int = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/financeiro/recebimentos_efetivados
        Retorna: dataRecebimento, cliente, filialRecebimento, codigoFluxo,
                 dataEmissao, dataVencimento, dataBaixa, valorReceita
        """
        params = {"dataInicio": data_inicio, "dataFim": data_fim, "limit": limit}
        if id_filial: params["idFilial"] = id_filial
        return self._get_paginado("/api/v1/bi/financeiro/recebimentos_efetivados", params)

    def bi_pagamentos_efetivados(self, data_inicio: str, data_fim: str,
                                  id_filial: int = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/financeiro/pagamentos_efetivados
        Retorna: dataPagamento, fornecedor, filialPagamento, contaFluxo,
                 dataEmissao, dataVencimento, dataBaixa, valorDespesa
        """
        params = {"dataInicio": data_inicio, "dataFim": data_fim, "limit": limit}
        if id_filial: params["idFilial"] = id_filial
        return self._get_paginado("/api/v1/bi/financeiro/pagamentos_efetivados", params)

    def bi_movimentacoes_conta_corrente(self, data_inicio: str, data_fim: str,
                                         limit: int = 500) -> list:
        """
        GET /api/v1/bi/financeiro/movimentacoes_conta_corrente
        Retorna: tipoMovimento, fornecedor, dataMovimento, valorDocumento,
                 debitoCredito, filialMovimento, contaFluxoCaixa, numeroConta
        """
        return self._get_paginado("/api/v1/bi/financeiro/movimentacoes_conta_corrente",
                                   {"dataInicio": data_inicio, "dataFim": data_fim, "limit": limit})

    def bi_fluxo_previsto_realizado(self, data_mes_de: str = None, data_mes_ate: str = None,
                                     id_filial: str = None, exibir_acumulado: str = "false",
                                     limit: int = 500) -> list:
        """
        GET /api/v1/bi/financeiro/fluxos_caixa_previsto_realizado
        Retorna: filial, contaFluxoCaixa, debitoCredito, dataMes,
                 valorPrevisto, valorRealizado, diferenca,
                 valorPrevistoAcumulado, valorRealizadoAcumulado
        """
        params = {"exibirAcumulado": exibir_acumulado, "limit": limit}
        if data_mes_de:  params["dataMesDe"] = data_mes_de
        if data_mes_ate: params["dataMesAte"] = data_mes_ate
        if id_filial:    params["idFilialMovimento"] = id_filial
        return self._get_paginado("/api/v1/bi/financeiro/fluxos_caixa_previsto_realizado", params)

    def bi_log_fluxo_caixa(self, ids_filiais: list = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/financeiro/log_fluxo_caixa
        Retorna: descricaoFluxoCaixa, origemMovimento, data, nomeFornecedor,
                 debitoCredito, valorDebito, valorCredito, valorPrevisto, filialMovimento
        """
        params = {"limit": limit}
        if ids_filiais: params["idsFiliais"] = ids_filiais
        return self._get_paginado("/api/v1/bi/financeiro/log_fluxo_caixa", params)

    def bi_faturamento_geral(self, data_inicio: str, data_fim: str,
                              id_filial: int = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/financeiro/faturamento_geral
        Retorna: tipoMovimento, dataEmissao, situacao, destinatario,
                 naturezaOperacao, filial, valorLiquido, valorRetido, valorBruto
        """
        params = {"dataEmissaoInicio": data_inicio, "dataEmissaoFim": data_fim, "limit": limit}
        if id_filial: params["idFilial"] = id_filial
        return self._get_paginado("/api/v1/bi/financeiro/faturamento_geral", params)

    def bi_movimentacoes_baixas(self, data_inicio: str, data_fim: str,
                                 ids_filiais: list = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/movimentacoes/baixas
        Retorna: fornecedor, dataMovimento, valorRealizado, debitoCredito,
                 filialMovimento, contaContabilDebito, contaFluxoCaixa
        """
        params = {"dataInicio": data_inicio, "dataFim": data_fim, "limit": limit}
        if ids_filiais: params["idsFiliais"] = ids_filiais
        return self._get_paginado("/api/v1/bi/movimentacoes/baixas", params)

    # ─── VENDAS — BI ENDPOINTS ────────────────────────────────────────────────

    def bi_saida_material_analitico(self, data_inicio: str, data_fim: str,
                                     ids_filiais: list = None, ids_clientes: list = None,
                                     ids_materiais: list = None) -> list:
        """
        GET /api/v1/bi/vendas/saida_material/analitico
        Retorna: numeroTicket, data, idCliente, nomeRazaoCliente, idObra, nomeObra,
                 idMaterial, descricaoMaterial, placa, nomeMotorista, pesoLiquido,
                 quantidade, vlrUnitario, custoUnitarioSaida, custoUnitarioMaterial,
                 custoTransporte, custoTransporteCliente, dmt, valorTotal,
                 valorTotalComFreteBomba, valorMedioSFreteLiq, tempoPermanencia,
                 nomeVendedor, nomeFilialMovimento, tipoOperacao
        """
        params = {"data_inicio": data_inicio, "data_fim": data_fim}
        if ids_filiais:  params["ids_filiais"] = ids_filiais
        if ids_clientes: params["ids_clientes"] = ids_clientes
        if ids_materiais:params["ids_materiais"] = ids_materiais
        dados = self._get("/api/v1/bi/vendas/saida_material/analitico", params)
        return dados if isinstance(dados, list) else dados.get("data", [])

    def bi_notas_fiscais_emitidas(self, data_inicio: str, data_fim: str,
                                   id_filial: int = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/nfe/notas_fiscais_emitidas
        Retorna: dataEmissao, numeroNfe, emitente, destinatario, uf, produto,
                 quantidade, valorUnitario, valorItem, numCFOP, valorTotalNFe,
                 valorFrete, valorICMS, aliquotaICMS, valorDIFAL, condicaoPagamento
        """
        params = {"dataInicio": data_inicio, "dataFim": data_fim, "limit": limit}
        if id_filial: params["idFilial"] = id_filial
        return self._get_paginado("/api/v1/bi/nfe/notas_fiscais_emitidas", params)

    def bi_notas_fiscais_servico(self, data_inicio: str, data_fim: str,
                                  id_filial: int = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/nfse/notas_fiscais_servico
        Retorna: numeroNfse, tomador, dataEmissao, valorTotalServicos,
                 valorIssDevido, valorIssRetido, valorPis, valorCofins,
                 valorCsll, valorInss, valorIr, valorLiquido, filialMovimento
        """
        params = {"dataInicio": data_inicio, "dataFim": data_fim, "limit": limit}
        if id_filial: params["idFilial"] = id_filial
        return self._get_paginado("/api/v1/bi/nfse/notas_fiscais_servico", params)

    # ─── CUSTOS — BI ENDPOINTS ────────────────────────────────────────────────

    def bi_custos_totais_filial(self, ids_filiais: list = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/custos/custos_totais_por_filial
        Retorna: nomeFilial, data, valorDespesas, valorFaturamentoRealizado,
                 valorServicosExecutadosRealizado, valorDespesasPrevisto,
                 faturamentoPrevisto, percentualLucroProposta, precoInicialContrato,
                 valorTotalAditivosContrato, valorFaturamentoDireto,
                 valorVendasMateriais, valorTotalReajustes
        """
        params = {"limit": limit}
        if ids_filiais: params["idsFiliais"] = ids_filiais
        return self._get_paginado("/api/v1/bi/custos/custos_totais_por_filial", params)

    def bi_despesas_analiticas(self, data_inicio: str, data_fim: str,
                                id_filial: int = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/custos/despesas_analiticas
        Retorna: data, descricao, valor, origem, quantidade, tipoMovimento,
                 filialMovimento, filialAplicacao, aplicacao, contaMob, fornecedor
        """
        params = {"dataInicio": data_inicio, "dataFim": data_fim, "limit": limit}
        if id_filial: params["idFilial"] = id_filial
        return self._get_paginado("/api/v1/bi/custos/despesas_analiticas", params)

    def bi_despesas_por_contas(self, ids_filiais: list = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/custos/custos_despesas_por_contas
        Retorna: filial, contaMob, valorPrevisto, valorRealizado
        """
        params = {"limit": limit}
        if ids_filiais: params["idsFiliais"] = ids_filiais
        return self._get_paginado("/api/v1/bi/custos/custos_despesas_por_contas", params)

    def bi_resultado_economico(self, id_filial: int = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/custos/serv_exec_resultado_economico
        Retorna: filial, periodo (mes/ano), tipoServico,
                 valorManual, valorAutomatico, valorTotal
        """
        params = {"limit": limit}
        if id_filial: params["idFilial"] = id_filial
        return self._get_paginado("/api/v1/bi/custos/serv_exec_resultado_economico", params)

    def bi_producao_previsto_realizado(self, id_filial: int = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/custos/prod_serv_prev_realizado
        Retorna: nomeEmpresa, filial, data, servico, equipeProducao,
                 quantidadePrevista, quantidadeRealizada,
                 valorPrevisto, valorPrevistoContrato, valorRealizado
        """
        params = {"limit": limit}
        if id_filial: params["idFilial"] = id_filial
        return self._get_paginado("/api/v1/bi/custos/prod_serv_prev_realizado", params)

    def bi_histograma_mao_obra(self, data_inicio: str = None, data_fim: str = None,
                                limit: int = 500) -> list:
        """
        GET /api/v1/bi/custos/medicoes_histograma_mao_de_obra
        Retorna: data, filial, funcao, quantidadePrevisto, quantidadeAlocado
        """
        params = {"limit": limit}
        if data_inicio: params["dataInicio"] = data_inicio
        if data_fim:    params["dataFim"] = data_fim
        return self._get_paginado("/api/v1/bi/custos/medicoes_histograma_mao_de_obra", params)

    # ─── EQUIPAMENTOS / FROTA — BI ENDPOINTS ─────────────────────────────────

    def bi_eficiencia_equipamentos(self, ids_filiais: list = None,
                                    id_grupo: int = None, id_equipamento: int = None,
                                    limit: int = 500) -> list:
        """
        GET /api/v1/bi/apropriacoes/eficiencia_equipamentos
        Retorna: equipamento, horoHodoInicial, horoHodoFinal, horasMes,
                 horasAcumulado, horasDisponiveis, eficiencia,
                 perda1, perda2, perda3, perda4, perda5,
                 horasOperadores, operadorMaquina, situacao
        """
        params = {"limit": limit}
        if ids_filiais:    params["idsFiliais"] = ids_filiais
        if id_grupo:       params["idGrupoEquipamento"] = id_grupo
        if id_equipamento: params["idEquipamento"] = id_equipamento
        return self._get_paginado("/api/v1/bi/apropriacoes/eficiencia_equipamentos", params)

    def bi_controle_combustivel(self, id_filial: int = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/equipamentos/controle_consumo_combustivel
        Retorna: material, equipamento, filialAtualEquipamento, dataConsumo,
                 tipoCalculoMedia, horometroInicial, horometroFinal,
                 horasTrabalhadas, quantidade, mediaDesejada, mediaObtida
        """
        params = {"limit": limit}
        if id_filial: params["idFilial"] = id_filial
        return self._get_paginado("/api/v1/bi/equipamentos/controle_consumo_combustivel", params)

    def bi_lancamentos_oficina(self, data_inicio: str = None, data_fim: str = None,
                                limit: int = 500) -> list:
        """
        GET /api/v1/bi/equipamentos/lancamentos_oficina
        Retorna: dataChegada, dataSaida, horometroEntrada, horometroSaida,
                 codigoOsCorretiva, equipamento, tipoOficina, fornecedor,
                 situacaoOficina, defeitoOficina, solucaoOficina,
                 causaProvavel, custoSolucao, responsavel
        """
        params = {"limit": limit}
        if data_inicio: params["dataInicio"] = data_inicio
        if data_fim:    params["dataFim"] = data_fim
        return self._get_paginado("/api/v1/bi/equipamentos/lancamentos_oficina", params)

    def bi_consumo_analitico(self, id_equipamento: int = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/equipamentos/equipamentos_consumo_analitico
        Retorna: equipamento, descricaoTipoConsumo, dataConsumo, quantidade,
                 valorTotal, fornecedor, horometroConsumo, filialAplicacao
        """
        params = {"limit": limit}
        if id_equipamento: params["idEquipamento"] = id_equipamento
        return self._get_paginado("/api/v1/bi/equipamentos/equipamentos_consumo_analitico", params)

    def bi_os_manutencao(self, data_inicio: str = None, data_fim: str = None,
                          id_filial: int = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/gestao_frota_equipamentos/ordem_servico_manutencao
        Retorna: numeroOSM, tipoOSM, dataAbertura, dataPrevisaoConclusao,
                 situacaoOSM, statusOSMOficina, decorrenteMauUso,
                 defeitoOSM, servicoOSM, equipamento
        """
        params = {"limit": limit}
        if data_inicio: params["dataInicio"] = data_inicio
        if data_fim:    params["dataFim"] = data_fim
        if id_filial:   params["idFilial"] = id_filial
        return self._get_paginado("/api/v1/bi/gestao_frota_equipamentos/ordem_servico_manutencao", params)

    # ─── COMPRAS — BI ENDPOINTS ───────────────────────────────────────────────

    def bi_oc_os_analitico(self, data_inicio: str = None, data_fim: str = None,
                            situacao: int = None, limit: int = 500) -> list:
        """
        GET /api/v1/bi/compras/oc_os_analitico
        Retorna: numeroOcOs, tipo, fornecedor, filialRequisicao, filialEntrega,
                 dataOcOs, comprador, material, quantidade, valorTotalBruto,
                 valorDescontoPorItem, grupoInsumo, classeInsumo,
                 filialAplicacao, tipoAplicacao, situacao
        """
        params = {"limit": limit}
        if data_inicio: params["dataInicio"] = data_inicio
        if data_fim:    params["dataFim"] = data_fim
        if situacao is not None: params["situacao"] = situacao
        return self._get_paginado("/api/v1/bi/compras/oc_os_analitico", params)

    # ─── MÉTODOS LEGADOS (manter compatibilidade) ─────────────────────────────

    def buscar_materiais(self, apenas_ativos: bool = True, id_grupo: int = None,
                          descricao: str = None) -> list:
        params = {}
        if apenas_ativos: params["ativo"] = True
        if id_grupo:      params["idGrupo"] = id_grupo
        if descricao:     params["descricao"] = descricao
        return self._get_paginado("/api/v1/suprimentos/materiais", params)

    def buscar_equipamentos(self, filial_atual: int = None) -> list:
        params = {"exibirAcoplados": "TODOS"}
        if filial_atual: params["filialAtual"] = filial_atual
        return self._get_paginado("/api/v1/equipamentos/equipamentos", params)

    def buscar_os_manutencao(self, data_abertura_de: str = None,
                              data_abertura_ate: str = None) -> list:
        params = {}
        if data_abertura_de:  params["dataAberturaDe"] = data_abertura_de
        if data_abertura_ate: params["dataAberturaAte"] = data_abertura_ate
        return self._get_paginado("/api/v1/equipamentos/ordemservicomanutencao", params)

    def buscar_acompanhamento_requisicoes(self, data_de: str = None,
                                           data_ate: str = None) -> dict:
        params = {"situacaoRequisicao": 0, "situacaoOrdemCompra": 0}
        if data_de:  params["dataDe"] = data_de
        if data_ate: params["dataAte"] = data_ate
        return self._get("/api/v1/compras/acompanhamento_requisicoes", params)

    def buscar_compras_periodo(self, data_inicio: str, data_fim: str) -> dict:
        return self.buscar_acompanhamento_requisicoes(data_de=data_inicio, data_ate=data_fim)

    def buscar_pedidos_material(self, data_inicio: str = None,
                                 data_fim: str = None) -> list:
        params = {"sortField": "dataPedido", "sortDir": "desc", "limit": 500, "page": 0}
        if data_inicio: params["filtro.dataInicialPedido"] = data_inicio
        if data_fim:    params["filtro.dataFinalPedido"] = data_fim
        dados = self._get("/api/v1/vendas_producao/pedido_material", params)
        items = dados.get("data", [])
        if data_inicio: items = [p for p in items if (p.get("dataPedido") or "")[:10] >= data_inicio]
        if data_fim:    items = [p for p in items if (p.get("dataPedido") or "")[:10] <= data_fim]
        return items[:200]

    def buscar_orcamentos_venda(self, data_inicio: str = None, data_fim: str = None) -> list:
        params = {}
        if data_inicio: params["dataInicio"] = data_inicio
        if data_fim:    params["dataFim"] = data_fim
        return self._get_paginado("/api/v1/vendas_producao/orcamentos_venda", params)

    def buscar_dados_auditoria(self, data_inicio: str, data_fim: str) -> dict:
        return {
            "transferencias": self.buscar_transferencias(data_inicio, data_fim),
            "contas_correntes": self.buscar_contas_correntes(),
            "permutas": self.buscar_permutas(data_inicio, data_fim),
        }

    def buscar_dados_financeiros(self, data_inicio: str, data_fim: str) -> dict:
        trf = self.buscar_transferencias(data_inicio, data_fim)
        return {"transferencias_emissao": trf, "transferencias_vencimento": trf,
                "contas_correntes": self.buscar_contas_correntes()}

    def buscar_dados_frota_completos(self, data_inicio: str, data_fim: str) -> dict:
        return {
            "equipamentos":   self.buscar_equipamentos(),
            "os_manutencao":  self.buscar_os_manutencao(data_abertura_de=data_inicio,
                                                          data_abertura_ate=data_fim),
        }

    def buscar_clientes_inativos(self, dias_sem_comprar: int = 60,
                                  periodo_historico_dias: int = 730) -> dict:
        hoje      = datetime.now().date()
        corte     = hoje - timedelta(days=dias_sem_comprar)
        historico = hoje - timedelta(days=periodo_historico_dias)
        params = {
            "filtro.dataInicialPedido": historico.strftime("%Y-%m-%d"),
            "filtro.dataFinalPedido":   hoje.strftime("%Y-%m-%d"),
            "filtro.situacaoPedido": "CONCLUIDO", "limit": 500, "page": 0,
        }
        dados = self._get("/api/v1/vendas_producao/pedido_material", params)
        todos = dados.get("data", [])
        clientes = {}
        for p in todos:
            cli = p.get("cliente") or {}
            cli_id = cli.get("id")
            if not cli_id: continue
            try:
                data_pedido = datetime.strptime((p.get("dataPedido",""))[:10], "%Y-%m-%d").date()
            except: continue
            valor = p.get("valorTotalPedido", 0) or 0
            if cli_id not in clientes:
                clientes[cli_id] = {"id": cli_id,
                    "nome": cli.get("nomeRazao", f"ID {cli_id}"),
                    "cnpj": cli.get("cnpj", ""),
                    "ultima_compra": data_pedido, "primeira_compra": data_pedido,
                    "total_historico": 0, "qtde_pedidos": 0}
            c = clientes[cli_id]
            c["total_historico"] += valor
            c["qtde_pedidos"] += 1
            if data_pedido > c["ultima_compra"]:  c["ultima_compra"] = data_pedido
            if data_pedido < c["primeira_compra"]: c["primeira_compra"] = data_pedido
        inativos, ativos = [], []
        for c in clientes.values():
            dias = (hoje - c["ultima_compra"]).days
            c["dias_sem_comprar"]  = dias
            c["ultima_compra"]     = c["ultima_compra"].isoformat()
            c["primeira_compra"]   = c["primeira_compra"].isoformat()
            c["total_historico"]   = round(c["total_historico"], 2)
            c["ticket_medio"]      = round(c["total_historico"] / c["qtde_pedidos"], 2) if c["qtde_pedidos"] else 0
            if c["ultima_compra"] < corte.isoformat(): inativos.append(c)
            else: ativos.append(c)
        inativos.sort(key=lambda x: x["dias_sem_comprar"], reverse=True)
        ativos.sort(key=lambda x: x["total_historico"], reverse=True)
        total = len(clientes)
        return {"inativos": inativos, "ativos_recentes": ativos,
                "resumo": {"total_clientes": total, "inativos": len(inativos),
                           "ativos": len(ativos),
                           "pct_inativo": round(len(inativos)/total*100,1) if total else 0,
                           "dias_corte": dias_sem_comprar}}
