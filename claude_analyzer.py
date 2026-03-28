"""
=============================================================
  MÓDULO: CLAUDE ANALYZER
  Envia dados para o Claude e retorna análises estruturadas
=============================================================
"""

import anthropic
import logging
from config import CLAUDE_CONFIG

logger = logging.getLogger(__name__)


class ClaudeAnalyzer:
    """
    Interface com a API do Claude (Anthropic).
    Recebe dados do CRTI e prompts, retorna análises em texto.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=CLAUDE_CONFIG["api_key"])
        self.model  = CLAUDE_CONFIG["model"]
        self.max_tokens = CLAUDE_CONFIG["max_tokens"]

    def analisar(self, prompt: str, contexto_sistema: str = None) -> str:
        """
        Envia um prompt ao Claude e retorna o texto da análise.
        
        Args:
            prompt: O prompt completo com dados e instruções
            contexto_sistema: Opcional — personalidade/contexto adicional
        
        Returns:
            Texto da análise gerado pelo Claude
        """
        sistema = contexto_sistema or (
            "Você é um analista financeiro e auditor sênior especializado em ERP. "
            "Suas análises são precisas, baseadas em dados, e escritas em português brasileiro. "
            "Sempre formate bem seus relatórios para fácil leitura por gestores."
        )

        logger.info(f"🤖 Enviando para Claude ({self.model})...")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=sistema,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            resultado = response.content[0].text
            logger.info(f"✅ Claude respondeu — {len(resultado)} caracteres")
            return resultado

        except anthropic.APIError as e:
            logger.error(f"❌ Erro na API do Claude: {e}")
            raise

    def analisar_auditoria(self, prompt: str) -> str:
        return self.analisar(prompt, contexto_sistema=(
            "Você é um auditor contábil sênior com 20 anos de experiência em auditoria de ERP. "
            "Identifique inconsistências, fraudes potenciais e erros operacionais com precisão cirúrgica. "
            "Seja objetivo e baseie cada achado nos dados fornecidos. Responda em português brasileiro."
        ))

    def analisar_financeiro(self, prompt: str) -> str:
        return self.analisar(prompt, contexto_sistema=(
            "Você é um CFO experiente com profundo conhecimento em análise financeira e contabilidade gerencial. "
            "Suas análises conectam os números à estratégia do negócio. Responda em português brasileiro."
        ))

    def analisar_operacional(self, prompt: str) -> str:
        return self.analisar(prompt, contexto_sistema=(
            "Você é um diretor de operações especializado em supply chain, estoque e gestão comercial. "
            "Foca em eficiência operacional e ações práticas de melhoria. Responda em português brasileiro."
        ))
