"""
=============================================================
  MÓDULO: CRTI CLIENT
  Integração real com a API do ERP CRTI (vogelsanger)
  Baseado na documentação OAS 3.0 oficial do CRTI ERP
=============================================================

  ENDPOINTS CONFIRMADOS:
  ├── POST /api/v1/auth/signin              → Login (retorna accessToken + refreshToken)
  ├── POST /api/v1/auth/refresh_token       → Renovar token
  ├── GET  /api/v1/auth/info                → Info da empresa
  ├── GET  /api/v1/financeiro/trf_pagar_receber  → Transferências pagar/receber
  ├── GET  /api/v1/financeiro/conta_corrente     → Contas bancárias
  ├── GET  /api/v1/financeiro/permuta            → Negociações/Permutas
  └── GET  /api/v1/financeiro/configuracao_boleto → Config boletos
"""

import requests
import logging
from datetime import datetime, timedelta
from config import CRTI_CONFIG

logger = logging.getLogger(__name__)

# Limite padrão de itens por página (CRTI suporta paginação)
DEFAULT_LIMIT = 500


class CRTIClient:
    """
    Cliente oficial para a API do CRTI ERP (vogelsanger.crti.com.br).

    Suporta dois modos de autenticação (configurado no .env):
      1. OAuth 2.0 (recomendado) — usa CRTI_CLIENT_ID + CRTI_CLIENT_SECRET
      2. Usuário/Senha            — usa CRTI_USERNAME + CRTI_PASSWORD
    """

    def __init__(self):
        self.base_url      = CRTI_CONFIG["base_url"]
        self.timeout       = CRTI_CONFIG["timeout"]
        self.access_token  = None
        self.refresh_token = None
        self.session       = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

        # Detecta modo de autenticação automaticamente
        self.xapi_key      = CRTI_CONFIG.get("xapi_key")
        self.client_id     = CRTI_CONFIG.get("client_id")
        self.client_secret = CRTI_CONFIG.get("client_secret")
        self.username      = CRTI_CONFIG.get("username")
        self.password      = CRTI_CONFIG.get("password")

        # Prioridade: X-Api-Key → OAuth 2.0 → Usuário/Senha
        if self.xapi_key:
            self._autenticar_xapikey_direto()
        elif self.client_id and self.client_secret:
            self._autenticar_oauth2()
        else:
            self._autenticar()

    # ──────────────────────────────────────────
    #  AUTENTICAÇÃO — OAUTH 2.0 (Client Credentials)
    # ──────────────────────────────────────────
    def _autenticar_oauth2(self):
        """
        OAuth 2.0 Client Credentials Grant.
        Tenta os endpoints mais comuns do CRTI até encontrar o correto.
        """
        logger.info("🔐 Autenticando no CRTI via OAuth 2.0...")

        endpoints_tentar = [
            "/api/v1/auth/oauth/token",
            "/oauth/token",
            "/api/v1/auth/token",
            "/api/oauth/token",
        ]

        # Formatos de requisição a tentar
        payloads = [
            # Formato 1: form-urlencoded (padrão OAuth 2.0)
            {
                "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                "data": {
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }
            },
            # Formato 2: JSON
            {
                "headers": {"Content-Type": "application/json"},
                "json": {
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }
            },
            # Formato 3: Basic Auth
            {
                "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                "auth": (self.client_id, self.client_secret),
                "data": {"grant_type": "client_credentials"}
            },
        ]

        for endpoint in endpoints_tentar:
            for payload in payloads:
                try:
                    url = f"{self.base_url}{endpoint}"
                    headers = {**self.session.headers, **payload.pop("headers", {})}
                    resp = requests.post(url, headers=headers, timeout=self.timeout, **payload)
                    if resp.status_code == 200:
                        dados = resp.json()
                        token = dados.get("access_token") or dados.get("accessToken")
                        if token:
                            self.access_token = token
                            self.session.headers.update({"Authorization": f"Bearer {token}"})
                            logger.info(f"✅ OAuth 2.0 autenticado via {endpoint}")
                            return
                except Exception:
                    continue

        # Se OAuth falhou, tenta também com X-Api-Key direto
        logger.warning("⚠️  Endpoints OAuth não encontrados — tentando X-Api-Key direta...")
        self._autenticar_xapikey()

    def _autenticar_xapikey_direto(self):
        """
        Autenticação direta via CRTI_XAPI_KEY.
        Se falhar, tenta usuário/senha como fallback.
        """
        logger.info("🔑 Autenticando via X-Api-Key direta...")
        self.session.headers.update({"X-Api-Key": self.xapi_key})
        if self.client_id:
            self.session.headers.update({"X-Client-Id": self.client_id})
        try:
            resp = self.session.get(f"{self.base_url}/api/v1/auth/info", timeout=self.timeout)
            if resp.status_code == 200:
                logger.info("✅ Autenticado via X-Api-Key com sucesso!")
                return
            logger.warning(f"⚠️ X-Api-Key retornou {resp.status_code} — tentando usuário/senha...")
        except Exception as e:
            logger.warning(f"⚠️ Erro X-Api-Key: {e} — tentando usuário/senha...")

        # Fallback: usuário/senha (JWT completo — acessa todos os módulos)
        if self.username and self.password:
            # Remove headers da X-Api-Key para usar JWT
            self.session.headers.pop("X-Api-Key", None)
            self.session.headers.pop("X-Client-Id", None)
            self._autenticar()
        else:
            raise Exception("❌ Nenhum método de autenticação funcionou. Verifique os Secrets.")

    def _autenticar_xapikey(self):
        """
        Tenta autenticação via X-Api-Key (chave única).
        Usa o client_secret como chave direta no header.
        """
        logger.info("🔑 Tentando autenticação via X-Api-Key...")
        self.session.headers.update({
            "X-Api-Key": self.client_secret,
            "X-Client-Id": self.client_id,
        })
        try:
            resp = self.session.get(f"{self.base_url}/api/v1/auth/info", timeout=self.timeout)
            if resp.status_code == 200:
                logger.info("✅ Autenticado via X-Api-Key com sucesso!")
                return
        except Exception:
            pass
        raise Exception(
            "❌ Nenhum método de autenticação funcionou.\n"
            "Verifique CRTI_CLIENT_ID e CRTI_CLIENT_SECRET no .env\n"
            "ou consulte o suporte CRTI para o endpoint OAuth correto."
        )

    # ──────────────────────────────────────────
    #  AUTENTICAÇÃO — USUÁRIO/SENHA (fallback)
    # ──────────────────────────────────────────
    def _autenticar(self):
        """
        POST /api/v1/auth/signin
        Body: {"username": "...", "password": "..."}
        """
        url = f"{self.base_url}/api/v1/auth/signin"
        logger.info("🔐 Autenticando no CRTI via usuário/senha...")
        resp = self.session.post(
            url,
            json={"username": self.username, "password": self.password},
            timeout=self.timeout
        )
        resp.raise_for_status()
        dados = resp.json()
        self.access_token  = dados["accessToken"]
        self.refresh_token = dados.get("refreshToken")
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
        logger.info("✅ Autenticado no CRTI com sucesso")

    def _renovar_token(self):
        """
        POST /api/v1/auth/refresh_token
        Body: {"refreshToken": "..."}
        Renova o accessToken automaticamente.
        """
        url = f"{self.base_url}/api/v1/auth/refresh_token"
        logger.info("🔄 Renovando token CRTI...")
        resp = self.session.post(
            url,
            json={"refreshToken": self.refresh_token},
            timeout=self.timeout
        )
        resp.raise_for_status()
        dados = resp.json()
        self.access_token  = dados["accessToken"]
        self.refresh_token = dados["refreshToken"]
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
        logger.info("✅ Token renovado")

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Executa GET com retry automático se token expirar (401)."""
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 401:
                logger.warning("⚠️ Token expirado — renovando...")
                self._renovar_token()
                resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            logger.info(f"✅ GET {endpoint} — {resp.status_code}")
            return resp.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ Erro HTTP {endpoint}: {e} | Response: {e.response.text[:300]}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Sem conexão com CRTI: {url}")
            raise

    def _get_paginado(self, endpoint: str, params: dict = None) -> list:
        """
        Busca todas as páginas automaticamente.
        CRTI retorna: {"data": [...], "totalLength": N, "page": 0, "limit": N}
        """
        params = params or {}
        params.setdefault("limit", DEFAULT_LIMIT)
        params.setdefault("page", 0)

        todos = []
        while True:
            dados = self._get(endpoint, params)
            items = dados.get("data", [])
            todos.extend(items)
            total = dados.get("totalLength", len(items))
            logger.info(f"   Página {params['page']+1} — {len(items)} itens | Total: {total}")
            if len(todos) >= total or len(items) == 0:
                break
            params["page"] += 1

        return todos

    # ──────────────────────────────────────────
    #  INFO DA EMPRESA
    # ──────────────────────────────────────────
    def buscar_info_empresa(self) -> dict:
        """
        GET /api/v1/auth/info
        Retorna: {"nomeEmpresa": "...", "permiteAcessoAppCargas": true, ...}
        """
        return self._get("/api/v1/auth/info")

    # ──────────────────────────────────────────
    #  TRANSFERÊNCIAS (CONTAS A PAGAR / RECEBER)
    # ──────────────────────────────────────────
    def buscar_transferencias(
        self,
        data_inicio: str,
        data_fim: str,
        fornecedor_id: int = None,
        filial_ids: list = None,
    ) -> list:
        """
        GET /api/v1/financeiro/trf_pagar_receber
        
        Parâmetros obrigatórios: dataInicio e dataFim (formato YYYY-MM-DD)
        
        Retorna lista de TransferenciaResponse com:
        - id, fornecedor, numeroDocumento, dataEmissao
        - valorTotalDocumento, valorLiquido, parcelas[], itens[]
        
        Uso: Auditoria de lançamentos financeiros, análise de fluxo de caixa
        """
        logger.info(f"💳 Buscando transferências: {data_inicio} → {data_fim}")
        params = {
            "dataInicio": data_inicio,
            "dataFim":    data_fim,
        }
        if fornecedor_id:
            params["fornecedorId"] = fornecedor_id
        if filial_ids:
            params["filiaisMovimento"] = filial_ids

        return self._get_paginado("/api/v1/financeiro/trf_pagar_receber", params)

    def buscar_transferencia_por_id(self, id: int) -> dict:
        """GET /api/v1/financeiro/trf_pagar_receber/{id}"""
        return self._get(f"/api/v1/financeiro/trf_pagar_receber/{id}")

    def buscar_transferencias_vencimento(
        self, data_inicio_venc: str, data_fim_venc: str
    ) -> list:
        """
        Busca transferências por período de VENCIMENTO.
        Útil para identificar contas vencidas ou a vencer.
        """
        logger.info(f"📅 Buscando transferências p/ vencimento: {data_inicio_venc} → {data_fim_venc}")
        params = {
            "dataInicio":              data_inicio_venc,  # obrigatório
            "dataFim":                 data_fim_venc,
            "inicioPeriodoVencimento": data_inicio_venc,
            "fimPeriodoVencimento":    data_fim_venc,
        }
        return self._get_paginado("/api/v1/financeiro/trf_pagar_receber", params)

    # ──────────────────────────────────────────
    #  CONTAS CORRENTES (SALDO BANCÁRIO)
    # ──────────────────────────────────────────
    def buscar_contas_correntes(self, apenas_ativas: bool = True) -> list:
        """
        GET /api/v1/financeiro/conta_corrente
        
        Tipos de conta: 1=Corrente, 2=Investimento, 3=Poupança,
                        4=Cartão Débito/Crédito, 5=Cartão Crédito Pagamento
        
        Retorna: id, numeroConta, numero, banco, agencia, filial,
                 contaContabil, tipoConta, tipoMoeda, contaAtiva
        """
        logger.info("🏦 Buscando contas correntes...")
        params = {"apenasAtivas": str(apenas_ativas).lower()}
        return self._get_paginado("/api/v1/financeiro/conta_corrente", params)

    def buscar_conta_corrente_por_id(self, id: int) -> dict:
        """GET /api/v1/financeiro/conta_corrente/{id}"""
        return self._get(f"/api/v1/financeiro/conta_corrente/{id}")

    # ──────────────────────────────────────────
    #  PERMUTAS / NEGOCIAÇÕES
    # ──────────────────────────────────────────
    def buscar_permutas(self, data_inicio: str, data_fim: str) -> list:
        """
        GET /api/v1/financeiro/permuta
        
        Parâmetros obrigatórios: dataInicio e dataFim
        Retorna: id, situacaoPermuta, dataPermuta, participantePermuta,
                 filialMovimento, descricaoPermuta
        
        Situações: PENDENTE → LIBERADO → FINALIZADO (ou BLOQUEADO/CANCELADO)
        """
        logger.info(f"🔄 Buscando permutas: {data_inicio} → {data_fim}")
        params = {"dataInicio": data_inicio, "dataFim": data_fim}
        return self._get_paginado("/api/v1/financeiro/permuta", params)

    # ──────────────────────────────────────────
    #  BOLETOS
    # ──────────────────────────────────────────
    def buscar_configuracoes_boleto(self) -> list:
        """
        GET /api/v1/financeiro/configuracao_boleto
        Útil para análise de cobrança e boletos emitidos.
        """
        logger.info("📄 Buscando configurações de boleto...")
        return self._get_paginado("/api/v1/financeiro/configuracao_boleto")

    # ──────────────────────────────────────────
    #  MÉTODOS COMPOSTOS PARA OS RELATÓRIOS
    # ──────────────────────────────────────────
    def buscar_dados_auditoria(self, data_inicio: str, data_fim: str) -> dict:
        """
        Busca todos os dados necessários para auditoria financeira do período.
        Retorna dict consolidado com transferências e contas.
        """
        logger.info(f"🔍 Coletando dados para auditoria: {data_inicio} → {data_fim}")
        return {
            "transferencias": self.buscar_transferencias(data_inicio, data_fim),
            "contas_correntes": self.buscar_contas_correntes(),
            "permutas": self.buscar_permutas(data_inicio, data_fim),
        }

    def buscar_dados_financeiros(self, data_inicio: str, data_fim: str) -> dict:
        logger.info(f"📊 Coletando dados financeiros: {data_inicio} → {data_fim}")
        transferencias = self.buscar_transferencias(data_inicio, data_fim)
        return {
            "transferencias_emissao":    transferencias,
            "transferencias_vencimento": transferencias,
            "contas_correntes":          self.buscar_contas_correntes(),
        }

    # ──────────────────────────────────────────
    #  HELPERS DE PERÍODO
    # ──────────────────────────────────────────
    @staticmethod
    def periodo_ontem() -> tuple:
        ontem = datetime.now() - timedelta(days=1)
        d = ontem.strftime("%Y-%m-%d")
        return d, d

    @staticmethod
    def periodo_ultima_semana() -> tuple:
        hoje   = datetime.now()
        inicio = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
        fim    = hoje.strftime("%Y-%m-%d")
        return inicio, fim

    @staticmethod
    def periodo_mes_atual() -> tuple:
        hoje   = datetime.now()
        inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
        fim    = hoje.strftime("%Y-%m-%d")
        return inicio, fim

    @staticmethod
    def mes_anterior() -> tuple:
        hoje               = datetime.now()
        primeiro_deste_mes = hoje.replace(day=1)
        ultimo_mes_passado = primeiro_deste_mes - timedelta(days=1)
        return ultimo_mes_passado.month, ultimo_mes_passado.year

    @staticmethod
    def periodo_mes_anterior_completo() -> tuple:
        hoje               = datetime.now()
        primeiro_deste_mes = hoje.replace(day=1)
        ultimo_dia_mes_ant = primeiro_deste_mes - timedelta(days=1)
        primeiro_dia_mes_ant = ultimo_dia_mes_ant.replace(day=1)
        return (
            primeiro_dia_mes_ant.strftime("%Y-%m-%d"),
            ultimo_dia_mes_ant.strftime("%Y-%m-%d")
        )


    # ──────────────────────────────────────────
    #  SUPRIMENTOS — MATERIAIS
    #  GET /api/v1/suprimentos/materiais
    # ──────────────────────────────────────────
    def buscar_materiais(
        self,
        apenas_ativos: bool = True,
        id_grupo: int = None,
        id_classe: int = None,
        tipo_item: str = None,
        descricao: str = None,
    ) -> list:
        """
        Lista todos os materiais cadastrados no CRTI.

        Campos retornados por material:
          id, descricao, ativo, unidade, grupo, classes, marca,
          ean, ncm, tipoItem, valorUnitarioCom, valorUnitarioTrib,
          cfopMesmaUf, cfopUfDiferente, aliquotaIcmsInterno,
          codigoIntegracao, dataInclusao,
          materiaisControleEstoque[{filial, estoqueMinimo, estoqueMaximo, localizacao}]

        Filtros disponíveis:
          - apenas_ativos: filtra materiais ativos
          - id_grupo: filtra por grupo de materiais
          - id_classe: filtra por classe
          - tipo_item: filtra por tipo
          - descricao: busca parcial por descrição
        """
        logger.info("📦 Buscando materiais/suprimentos...")
        params = {}
        if apenas_ativos:
            params["ativo"] = True
        if id_grupo:
            params["idGrupo"] = id_grupo
        if id_classe:
            params["idClasse"] = id_classe
        if tipo_item:
            params["tipoItem"] = tipo_item
        if descricao:
            params["descricao"] = descricao

        return self._get_paginado("/api/v1/suprimentos/materiais", params)

    def buscar_material_por_id(self, id: int) -> dict:
        """GET /api/v1/suprimentos/materiais/{id}"""
        return self._get(f"/api/v1/suprimentos/materiais/{id}")

    def buscar_materiais_estoque_critico(self) -> list:
        """
        Busca todos os materiais ativos e filtra os que têm
        controle de estoque configurado (estoqueMinimo > 0).
        Útil para auditoria de estoque e alertas de ruptura.
        """
        logger.info("⚠️ Verificando materiais com controle de estoque...")
        todos = self.buscar_materiais(apenas_ativos=True)
        com_controle = [
            m for m in todos
            if m.get("materiaisControleEstoque")
        ]
        logger.info(f"   {len(com_controle)}/{len(todos)} materiais têm controle de estoque")
        return com_controle


    # ══════════════════════════════════════════
    #  MÓDULO: CUSTOS
    #  /api/v1/custos/*
    # ══════════════════════════════════════════

    # ──────────────────────────────────────────
    #  SERVIÇOS POR FILIAL
    #  Contém: valorTotal, valorTotalContrato, qtdeTotal, ativo
    # ──────────────────────────────────────────
    def buscar_servicos_por_filial(self, id_filial: int) -> list:
        """
        GET /api/v1/custos/servicos_por_filial/{id_filial}

        Campos retornados:
          id, idFilial, nomeFilial, codigo, codigoCompleto,
          descricao, grupoServico, nivel,
          qtdeTotal, valorTotal, valorTotalContrato,
          estoque, abrevUnidadeMedida, ativo

        valorTotal vs valorTotalContrato → margem por serviço
        """
        logger.info(f"🔧 Buscando serviços da filial {id_filial}...")
        return self._get_paginado(
            f"/api/v1/custos/servicos_por_filial/{id_filial}"
        )

    def buscar_servicos_todas_filiais(self, ids_filiais: list) -> dict:
        """
        Busca serviços de múltiplas filiais e retorna agrupado por filial.
        """
        resultado = {}
        for id_filial in ids_filiais:
            resultado[id_filial] = self.buscar_servicos_por_filial(id_filial)
        return resultado

    # ──────────────────────────────────────────
    #  PERDAS
    #  Tipos de perda com percentual de dedução
    # ──────────────────────────────────────────
    def buscar_perdas(self) -> list:
        """
        GET /api/v1/custos/perdas
        Lista categorias de perdas cadastradas.
        Retorna: id, descricao
        """
        logger.info("📉 Buscando categorias de perdas...")
        return self._get_paginado("/api/v1/custos/perdas")

    def buscar_tipos_perda(self, id_perda: int) -> list:
        """
        GET /api/v1/custos/perdas/{idPerda}/tipos
        Lista os tipos de perda de uma categoria.

        Campos: idTipoPerda, descricao, perdaDedutiva,
                percentualDeducao, descricaoCustosPerda
        """
        logger.info(f"📉 Buscando tipos de perda para categoria {id_perda}...")
        return self._get_paginado(f"/api/v1/custos/perdas/{id_perda}/tipos")

    def buscar_todas_perdas_e_tipos(self) -> list:
        """
        Busca todas as categorias de perdas e seus tipos,
        montando uma estrutura hierárquica completa.
        """
        perdas = self.buscar_perdas()
        for perda in perdas:
            perda["tipos"] = self.buscar_tipos_perda(perda["id"])
        return perdas

    # ──────────────────────────────────────────
    #  TURNOS DE TRABALHO
    # ──────────────────────────────────────────
    def buscar_turnos_de_trabalho(self) -> list:
        """
        GET /api/v1/custos/turnos_de_trabalho
        Retorna: id, descricao, ordemDia,
                 inicioServico, terminoServico,
                 inicioRefeicao, terminoRefeicao
        """
        logger.info("⏰ Buscando turnos de trabalho...")
        return self._get_paginado("/api/v1/custos/turnos_de_trabalho")

    # ──────────────────────────────────────────
    #  BMO — BOLETIM DE MEDIÇÃO DE OBRAS
    #  Registro diário: funcionários, serviços, horas, h. extra
    # ──────────────────────────────────────────
    def buscar_bmo_por_id(self, id: int) -> dict:
        """
        GET /api/v1/custos/bmo/{id}

        Campos: id, filialMovimento, data, encarregado,
                turnoDeTrabalho, observacaoMestre, usuarioLancamento,
                servicos[{funcionario, servicoExecutado,
                           horaEntradaServico, horaSaidaServico,
                           inicioHorarioRefeicao, fimHorarioRefeicao,
                           horaExtra, observacaoServ}]
        """
        return self._get(f"/api/v1/custos/bmo/{id}")

    # ──────────────────────────────────────────
    #  BLE/PDV — BOLETIM DE EQUIPAMENTOS
    #  Controle de horímetro, operadores e perdas por turno
    # ──────────────────────────────────────────
    def buscar_blepdv_por_id(self, id: int) -> dict:
        """
        GET /api/v1/custos/blepdv/{id}

        Campos: id, equipamento{descricao, apelido, placa},
                dataBlePdv, turno,
                horometroInicial, horometroFinal, horasDisponiveis,
                operadorPrincipal, operadores[], observacoes,
                servicos[{servico, tempoGastoHoras,
                           estacaKmInicial, estacaKmFinal, volumeArea}],
                perdas[{tipoPerda, totalHoras, compartimento}]
        """
        return self._get(f"/api/v1/custos/blepdv/{id}")


    # ══════════════════════════════════════════
    #  MÓDULO: COMPRAS
    #  /api/v1/compras/*
    # ══════════════════════════════════════════

    def buscar_acompanhamento_requisicoes(
        self,
        data_de: str = None,
        data_ate: str = None,
        ids_filiais: list = None,
        situacao_requisicao: int = 0,
        situacao_ordem_compra: int = 0,
    ) -> dict:
        """
        GET /api/v1/compras/acompanhamento_requisicoes

        Retorna o pipeline COMPLETO de compras em uma única chamada:

        ┌─ SolicitacaoMaterialMestre (Requisições)
        │   ├─ situacao, situacaoCompra, dataSolicitacao, dataUtilMaterial
        │   ├─ funcionarioSolicitacao, comprador, filialMovimento
        │   ├─ listSolicitacaoItens[]
        │   │   ├─ materialResumido, quantidadeSolicitada
        │   │   ├─ equipamentoResumido (vincula ao módulo Custos!)
        │   │   ├─ codigoContaResultadoEconomico (centro de custo)
        │   │   └─ listOrdemCompraItens[]
        │   ├─ cotacaoMestreResumidoList[]
        │   │   ├─ fornecedor, prazoEntrega, condicaoPagamento
        │   │   └─ listCotacaoItem[]: valorProduto, IPI, ICMS-ST, desconto, valorTotal
        │   └─ ordemCompraMestreResumidaList[]
        │       ├─ dataOrdemCompra, dataAprovacao, dataRealEntrega
        │       ├─ valorMercadorias, valorFrete, valorTotalCompras
        │       ├─ descricaoSituacao, descricaoSituacaoEntrega
        │       └─ entradaMercadoriaMestreResumidaList[] (NF de entrada)
        │
        └─ OrdensCompraSemCotacaoOuSemRequisicao
            └─ OCs geradas diretamente (sem processo de requisição/cotação)

        Filtros:
          situacaoRequisicao: 0=todas, outros valores conforme CRTI
          situacaoOrdemCompra: 0=todas, outros valores conforme CRTI
        """
        logger.info(f"🛒 Buscando acompanhamento de requisições: {data_de} → {data_ate}")
        params = {
            "situacaoRequisicao":   situacao_requisicao,
            "situacaoOrdemCompra":  situacao_ordem_compra,
        }
        if data_de:
            params["dataDe"] = data_de
        if data_ate:
            params["dataAte"] = data_ate
        if ids_filiais:
            params["idsFiliaisRequisicao"] = ids_filiais

        dados = self._get("/api/v1/compras/acompanhamento_requisicoes", params)

        requisicoes = dados.get("solicitacoesMaterialMestre", [])
        ocs_diretas = dados.get("ordensCompraMestreSemCotacaoOuSemRequisicao", [])

        logger.info(f"   Requisições: {len(requisicoes)} | OCs diretas: {len(ocs_diretas)}")
        return dados

    def buscar_compras_periodo(self, data_inicio: str, data_fim: str) -> dict:
        """Atalho para buscar todas as compras de um período."""
        return self.buscar_acompanhamento_requisicoes(
            data_de=data_inicio, data_ate=data_fim
        )


    # ══════════════════════════════════════════
    #  MÓDULO: EQUIPAMENTOS / FROTA
    #  /api/v1/equipamentos/*
    # ══════════════════════════════════════════

    # ──────────────────────────────────────────
    #  CADASTRO DE EQUIPAMENTOS
    # ──────────────────────────────────────────
    def buscar_equipamentos(
        self,
        filial_atual: int = None,
        descricao: str = None,
        exibir_acoplados: str = "TODOS",
    ) -> list:
        """
        GET /api/v1/equipamentos/equipamentos

        Campos patrimoniais retornados:
          id, descricao, apelido, placa, situacao,
          marca, grupo, subGrupo, modelo, serie, chassis,
          anoFabricacao, anoModelo, cor,
          potencia, capacidade, altura, largura, comprimento,
          ultimoHorometroOdometro, horometroHodometroAcumulado,
          valorAquisicao, valorMercado, valorLocacao,
          seguradora, apolice, vencimentoSeguro, valorFranquia, valorCobertura,
          idFilialAtual, nomeFilialAtual, dataChegada,
          numeroBemPatrimonial, numeroNfCompra, dataNf, nomeFornecedorNf,
          requerApropriacao, requerPlanoLubrificacao,
          idSubEmpreitero, codigoContratoSubEmpreitadaMestre,
          codigoContratoLocEquipClienteMestre, dataDevolucao
        """
        logger.info("🚜 Buscando equipamentos...")
        params = {"exibirAcoplados": exibir_acoplados}
        if filial_atual:
            params["filialAtual"] = filial_atual
        if descricao:
            params["descricao"] = descricao
        return self._get_paginado("/api/v1/equipamentos/equipamentos", params)

    def buscar_equipamento_por_id(self, id: int) -> dict:
        """GET /api/v1/equipamentos/equipamentos/{id}"""
        return self._get(f"/api/v1/equipamentos/equipamentos/{id}")

    def buscar_acoplados(self, id_mestre: int) -> list:
        """
        GET /api/v1/equipamentos/equipamentos/{idMestre}/acoplados
        Retorna: idEquipamento, idEquipamentoAcoplado,
                 dataAcoplamento, dataDesacoplamento
        """
        return self._get_paginado(f"/api/v1/equipamentos/equipamentos/{id_mestre}/acoplados")

    def buscar_filial_equipamento_na_data(self, id_equipamento: int, data: str = None) -> list:
        """
        GET /api/v1/equipamentos/equipamentos/{idEquipamento}/filiais
        Retorna em qual filial o equipamento estava na data informada.
        Campos: filial{id, nome, cidade}, dataInicio, dataFim
        """
        params = {}
        if data:
            params["data"] = data
        return self._get(
            f"/api/v1/equipamentos/equipamentos/{id_equipamento}/filiais",
            params
        )

    # ──────────────────────────────────────────
    #  ORDENS DE SERVIÇO DE MANUTENÇÃO
    # ──────────────────────────────────────────
    def buscar_os_manutencao(
        self,
        data_abertura_de: str = None,
        data_abertura_ate: str = None,
        id_equipamento: int = None,
        situacoes: list = None,
        filiais_oficina: list = None,
        tipo: int = None,
    ) -> list:
        """
        GET /api/v1/equipamentos/ordemservicomanutencao

        Campos retornados:
          id, equipamento{descricao, apelido, placa},
          dataAbertura, dataPrevTermino, tipo, situacao,
          defeito, causaProvavel, observacoes, dataCancelamento,
          listOSServicos[{servico, descricaoCompartimento,
                           nomeFuncionario, statusExecucao,
                           tipoConsumo, quantidade}]

        Situações típicas: Aberta, Em andamento, Concluída, Cancelada
        Tipos: Corretiva, Preventiva, etc.
        """
        logger.info(f"🔧 Buscando OS de manutenção: {data_abertura_de} → {data_abertura_ate}")
        params = {}
        if data_abertura_de:
            params["dataAberturaDe"] = data_abertura_de
        if data_abertura_ate:
            params["dataAberturaAte"] = data_abertura_ate
        if id_equipamento:
            params["equipamento"] = id_equipamento
        if situacoes:
            params["listSituacoes"] = situacoes
        if filiais_oficina:
            params["listFilialOficina"] = filiais_oficina
        if tipo:
            params["tipo"] = tipo
        return self._get_paginado("/api/v1/equipamentos/ordemservicomanutencao", params)

    def buscar_os_por_id(self, id: int) -> dict:
        """GET /api/v1/equipamentos/ordemservicomanutencao/{id}"""
        return self._get(f"/api/v1/equipamentos/ordemservicomanutencao/{id}")

    # ──────────────────────────────────────────
    #  TRANSFERÊNCIAS DE EQUIPAMENTOS
    # ──────────────────────────────────────────
    def buscar_transferencias_equipamentos(
        self,
        data_de: str = None,
        data_ate: str = None,
        id_equipamento: int = None,
    ) -> list:
        """
        GET /api/v1/equipamentos/transferencias

        Campos retornados:
          id, idEquipamento, descricaoEquipamento, apelidoEquipamento,
          idFilialOrigem, nomeFilialOrigem,
          idFilialDestino, nomeFilialDestino,
          dataSaida, dataChegada, dataChegadaPrevista,
          horometroHodometroSaida, horometroHodometroChegada,
          situacaoEquipamento,
          transportado, motorista,
          anormalidades, acessorios,
          nomeFuncionarioSol, nomeFuncionarioAuto,
          nomeFuncionarioInsp, nomeFuncionarioInspChegada,
          nomeUsuarioAceite, dataAceite,
          concordaAnormalidades, concordaAcessorios
        """
        logger.info(f"🚚 Buscando transferências de equipamentos: {data_de} → {data_ate}")
        params = {}
        if data_de:
            params["dataDe"] = data_de
        if data_ate:
            params["dataAte"] = data_ate
        if id_equipamento:
            params["idEquipamento"] = id_equipamento
        return self._get_paginado("/api/v1/equipamentos/transferencias", params)

    # ──────────────────────────────────────────
    #  MÉTODO COMPOSTO — DADOS COMPLETOS DA FROTA
    # ──────────────────────────────────────────
    def buscar_dados_frota_completos(self, data_inicio: str, data_fim: str) -> dict:
        """
        Coleta todos os dados de frota do período para análise consolidada:
        equipamentos + OS de manutenção + transferências
        """
        logger.info(f"🚜 Coletando dados completos da frota: {data_inicio} → {data_fim}")
        return {
            "equipamentos":    self.buscar_equipamentos(),
            "os_manutencao":   self.buscar_os_manutencao(
                                   data_abertura_de=data_inicio,
                                   data_abertura_ate=data_fim
                               ),
            "transferencias":  self.buscar_transferencias_equipamentos(
                                   data_de=data_inicio, data_ate=data_fim
                               ),
        }


    # ══════════════════════════════════════════
    #  MÓDULO: VENDAS E PRODUÇÃO
    #  /api/v1/vendas_producao/*
    # ══════════════════════════════════════════

    # ──────────────────────────────────────────
    #  PEDIDOS DE MATERIAL (VENDAS)
    # ──────────────────────────────────────────
    def buscar_pedidos_material(
        self,
        data_inicio: str = None,
        data_fim: str = None,
        id_cliente: int = None,
        situacao: str = None,
        ids_filiais: list = None,
        ids_vendedores: list = None,
    ) -> list:
        """
        GET /api/v1/vendas_producao/pedido_material

        Filtro via objeto FiltroPedidoMaterial (passado como query params).

        Campos retornados:
          id, cliente{id,nomeRazao,cnpj}, dataPedido, situacaoPedido,
          valorTotalPedido, tipoPedidoVenda, tipoFrete,
          vendedorPedido, filialMovimento,
          materiaisPedido[{material, quantidade, valorUnitarioCif,
                            valorUnitarioFob, custoTransporte}],
          dataLancamento, dataAprovacao, observacao

        Situações: AGUARDANDO_APROVACAO, APROVADO, CONCLUIDO, CANCELADO
        """
        logger.info(f"🛍️ Buscando pedidos de material: {data_inicio} → {data_fim}")
        params = {}
        if data_inicio:
            params["filtro.dataInicialPedido"] = data_inicio
        if data_fim:
            params["filtro.dataFinalPedido"] = data_fim
        if id_cliente:
            params["filtro.idCliente"] = id_cliente
        if situacao:
            params["filtro.situacaoPedido"] = situacao
        if ids_filiais:
            params["filtro.idsFiliaisMovimento"] = ids_filiais
        if ids_vendedores:
            params["filtro.idsVendedores"] = ids_vendedores

        # Busca primeira página para ter estatísticas rápidas
        params["limit"] = 200
        params["page"]  = 0
        dados = self._get("/api/v1/vendas_producao/pedido_material", params)
        items = dados.get("data", [])
        total = dados.get("totalLength", len(items))
        logger.info(f"   Pedidos: {len(items)}/{total} (primeiros 200)")

        # Filtra localmente por data — a API pode retornar registros antigos
        if data_inicio:
            items = [p for p in items if (p.get("dataPedido") or "")[:10] >= data_inicio]
        if data_fim:
            items = [p for p in items if (p.get("dataPedido") or "")[:10] <= data_fim]
        logger.info(f"   Após filtro local: {len(items)} pedidos no período")
        return items

    # ──────────────────────────────────────────
    #  ORÇAMENTOS DE VENDAS
    # ──────────────────────────────────────────
    def buscar_orcamentos_venda(
        self,
        data_inicio: str = None,
        data_fim: str = None,
        id_cliente: int = None,
        situacao: str = None,
    ) -> list:
        """
        GET /api/v1/vendas_producao/orcamentos_venda

        Campos retornados:
          id, cliente, dataOrcamento, situacao, saldo,
          representante (vendedor), filialMovimento,
          materiaisOrcamento[{material, quantidade,
                               valorUnitarioCif, valorUnitarioFob}],
          dataAprovacao, dataReprovacao, tabelaPreco

        Situações: AGUARDANDO_APROVACAO, APROVADO, CONCLUIDO,
                   CANCELADO, REPROVADO
        """
        logger.info(f"📋 Buscando orçamentos: {data_inicio} → {data_fim}")
        params = {}
        if data_inicio:
            params["dataInicio"] = data_inicio
        if data_fim:
            params["dataFim"] = data_fim
        if id_cliente:
            params["idCliente"] = id_cliente
        if situacao:
            params["situacao"] = situacao
        return self._get_paginado("/api/v1/vendas_producao/orcamentos_venda", params)

    # ──────────────────────────────────────────
    #  TABELA DE PREÇOS
    # ──────────────────────────────────────────
    def buscar_precos_venda(self, apenas_ativos: bool = True) -> list:
        """
        GET /api/v1/vendas_producao/precos_venda

        Campos:
          id, nomeTabela, dataTabela, tipoTabela (PESO/VOLUME/UNIDADES),
          tipoPedidoVenda, ativo, filiais[],
          itensPrecoVenda[{material, tipoFrete,
                            precoMaterialFob, precoFreteKm,
                            criterioCalculoCusto}]
        """
        logger.info("💰 Buscando tabelas de preços...")
        params = {}
        if apenas_ativos:
            params["ativo"] = True
        return self._get_paginado("/api/v1/vendas_producao/precos_venda", params)

    # ──────────────────────────────────────────
    #  ANÁLISE DE CLIENTES INATIVOS
    #  Compara dois períodos para identificar
    #  clientes que pararam de comprar
    # ──────────────────────────────────────────
    def buscar_clientes_inativos(
        self,
        dias_sem_comprar: int = 60,
        periodo_historico_dias: int = 730,
    ) -> dict:
        """
        Identifica clientes que compraram no histórico
        mas não compraram nos últimos N dias.

        Retorna:
          {
            "inativos": [{cliente, ultima_compra, dias_sem_comprar,
                          total_historico, qtde_pedidos}],
            "ativos_recentes": [{cliente, ultima_compra, total_periodo}],
            "resumo": {total_clientes, inativos, ativos, pct_inativo}
          }
        """
        from datetime import datetime, timedelta

        hoje     = datetime.now().date()
        corte    = hoje - timedelta(days=dias_sem_comprar)
        historico= hoje - timedelta(days=periodo_historico_dias)

        logger.info(f"🔍 Buscando clientes inativos "
                    f"(sem comprar há {dias_sem_comprar} dias)...")

        # Busca pedidos do histórico completo
        # Busca com limite maior para ter histórico representativo
        logger.info(f"   Período: {historico} → {hoje}")
        params_hist = {
            "filtro.dataInicialPedido": historico.strftime("%Y-%m-%d"),
            "filtro.dataFinalPedido":   hoje.strftime("%Y-%m-%d"),
            "filtro.situacaoPedido":    "CONCLUIDO",
            "limit": 500,
            "page":  0,
        }
        dados_hist = self._get("/api/v1/vendas_producao/pedido_material", params_hist)
        todos_pedidos = dados_hist.get("data", [])
        total_hist = dados_hist.get("totalLength", len(todos_pedidos))
        logger.info(f"   Histórico: {len(todos_pedidos)}/{total_hist} pedidos carregados")

        logger.info(f"   Total pedidos carregados: {len(todos_pedidos)}")

        # Agrupa por cliente
        clientes = {}
        for p in todos_pedidos:
            cli = p.get("cliente") or {}
            cli_id   = cli.get("id")
            cli_nome = cli.get("nomeRazao") or cli.get("nomeFantasia", f"ID {cli_id}")
            if not cli_id:
                continue

            data_str = p.get("dataPedido", "")
            try:
                data_pedido = datetime.strptime(data_str[:10], "%Y-%m-%d").date()
            except:
                continue

            valor = p.get("valorTotalPedido", 0) or 0

            if cli_id not in clientes:
                clientes[cli_id] = {
                    "id":             cli_id,
                    "nome":           cli_nome,
                    "cnpj":           cli.get("cnpj", ""),
                    "ultima_compra":  data_pedido,
                    "primeira_compra":data_pedido,
                    "total_historico":0,
                    "qtde_pedidos":   0,
                }
            c = clientes[cli_id]
            c["total_historico"] += valor
            c["qtde_pedidos"]    += 1
            if data_pedido > c["ultima_compra"]:
                c["ultima_compra"] = data_pedido
            if data_pedido < c["primeira_compra"]:
                c["primeira_compra"] = data_pedido

        # Classifica inativos vs ativos
        inativos = []
        ativos   = []
        for c in clientes.values():
            dias = (hoje - c["ultima_compra"]).days
            c["dias_sem_comprar"]    = dias
            c["ultima_compra"]       = c["ultima_compra"].isoformat()
            c["primeira_compra"]     = c["primeira_compra"].isoformat()
            c["total_historico"]     = round(c["total_historico"], 2)
            c["ticket_medio"]        = round(
                c["total_historico"] / c["qtde_pedidos"], 2
            ) if c["qtde_pedidos"] else 0

            if c["ultima_compra"] < corte.isoformat():
                inativos.append(c)
            else:
                ativos.append(c)

        inativos.sort(key=lambda x: x["dias_sem_comprar"], reverse=True)
        ativos.sort(key=lambda x: x["total_historico"], reverse=True)

        total = len(clientes)
        logger.info(f"   {len(inativos)} clientes inativos / "
                    f"{len(ativos)} ativos / {total} total")

        return {
            "inativos":        inativos,
            "ativos_recentes": ativos,
            "resumo": {
                "total_clientes":  total,
                "inativos":        len(inativos),
                "ativos":          len(ativos),
                "pct_inativo":     round(len(inativos)/total*100, 1) if total else 0,
                "dias_corte":      dias_sem_comprar,
                "periodo_analise": periodo_historico_dias,
            }
        }
