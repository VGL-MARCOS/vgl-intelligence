# 🤖 CRTI + Claude AI — Integração de Automação Financeira

Sistema de automação que conecta o ERP **CRTI** com a **API do Claude (Anthropic)** para gerar auditorias, relatórios operacionais e análises financeiras automaticamente.

---

## 📁 Estrutura do Projeto

```
crti-claude-integration/
│
├── main.py                    ← Orquestrador principal (ponto de entrada)
├── config.py                  ← Todas as configurações e credenciais
├── requirements.txt           ← Dependências Python
├── .env.example               ← Template de variáveis de ambiente
│
├── modules/
│   ├── crti_client.py         ← Busca dados do CRTI via API
│   ├── claude_analyzer.py     ← Envia dados ao Claude e recebe análises
│   ├── report_generator.py    ← Gera PDFs profissionais
│   ├── email_sender.py        ← Envia relatórios por email
│   └── scheduler.py           ← Agendamento automático
│
├── prompts/
│   └── prompts.py             ← Templates de prompts para cada análise
│
├── outputs/                   ← PDFs gerados (criado automaticamente)
└── logs/                      ← Logs de execução (criado automaticamente)
```

---

## ⚙️ Instalação

### 1. Requisitos
- Python 3.9+
- Acesso à API do CRTI (token de autenticação)
- Chave da API Anthropic (`sk-ant-...`)

### 2. Clone e instale as dependências
```bash
git clone <seu-repo>
cd crti-claude-integration
pip install -r requirements.txt
```

### 3. Configure as credenciais
```bash
cp .env.example .env
# Edite o .env com suas credenciais reais
```

Ou edite diretamente o `config.py`.

### 4. Adapte os endpoints do CRTI
Abra `config.py` e ajuste os endpoints conforme a documentação da sua versão do CRTI:

```python
"endpoints": {
    "lancamentos":   "/contabil/lancamentos",   # ← verifique no seu CRTI
    "estoque":       "/estoque/movimentacoes",
    ...
}
```

---

## 🚀 Como Usar

### Rodar um relatório manualmente (ideal para testar):
```bash
python main.py --auditoria       # Auditoria de lançamentos
python main.py --operacional     # Estoque, compras e vendas
python main.py --financeiro      # DRE + fluxo de caixa
python main.py --dre             # DRE mensal comparativo
python main.py --todos           # Todos de uma vez
```

### Iniciar o agendador automático:
```bash
python main.py
```

Isso mantém o processo rodando e executa cada relatório no horário configurado.

### Rodar em background (servidor Linux):
```bash
nohup python main.py > logs/scheduler.log 2>&1 &
```

### Ou como serviço systemd (produção):
```ini
# /etc/systemd/system/crti-claude.service
[Unit]
Description=CRTI Claude Integration
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/crti-claude-integration
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable crti-claude
sudo systemctl start crti-claude
sudo systemctl status crti-claude
```

---

## ⏰ Agendamentos Padrão

| Relatório              | Frequência    | Horário       |
|------------------------|---------------|---------------|
| Auditoria Lançamentos  | Diária        | 07:00         |
| Relatório Operacional  | Diária        | 08:00         |
| Análise Financeira     | Semanal (seg) | 06:30         |
| DRE Mensal             | Dia 1 do mês  | 06:00         |

Altere em `config.py` → `SCHEDULE_CONFIG`.

---

## 🔧 Personalização

### Adicionar novo tipo de relatório:
1. Crie o prompt em `prompts/prompts.py`
2. Adicione o método de busca em `modules/crti_client.py`
3. Crie o job em `main.py`
4. Adicione o agendamento em `config.py`

### Alterar destinatários por relatório:
No `main.py`, passe `destinatarios=[...]` no `email.enviar_relatorio(...)`.

---

## 🔑 Onde obter as credenciais

| Credencial           | Onde obter                                      |
|----------------------|-------------------------------------------------|
| `CRTI_TOKEN`         | Painel do CRTI → Configurações → API            |
| `ANTHROPIC_API_KEY`  | https://console.anthropic.com/settings/api-keys |
| `EMAIL_PASS` (Gmail) | Conta Google → Segurança → Senhas de app        |

---

## 💰 Estimativa de Custo (Claude API)

| Uso | Custo/mês estimado |
|-----|-------------------|
| 4 relatórios/dia | ~R$ 30–80 |
| 10 relatórios/dia | ~R$ 80–200 |
| Auditoria de 1000 lançamentos | ~R$ 0,50/execução |

---

## 🛟 Suporte

Se a API do CRTI retornar erro 401: verifique o token e o header `X-Empresa`.  
Se o Claude retornar erro: verifique se a `ANTHROPIC_API_KEY` está correta.  
Logs completos em: `./logs/integration_AAAAMM.log`

---

## 📊 Mapa Completo de Módulos Integrados

| Módulo | Endpoints | Comando |
|---|---|---|
| **Financeiro** | `trf_pagar_receber`, `conta_corrente`, `permuta` | `--auditoria`, `--contas`, `--mensal`, `--permutas` |
| **Suprimentos** | `materiais` | `--materiais`, `--estoque` |
| **Custos** | `servicos_por_filial`, `perdas`, `bmo`, `blepdv` | `--custos-servicos`, `--custos-perdas`, `--custos-bmo` |
| **Compras** | `acompanhamento_requisicoes` | `--compras-auditoria`, `--compras-relatorio` |
| **Equipamentos** | `equipamentos`, `ordemservicomanutencao`, `transferencias` | `--frota-auditoria`, `--frota-manutencao`, `--frota-patrimonio` |

**Total: 17 jobs automáticos cobrindo toda a operação.**
