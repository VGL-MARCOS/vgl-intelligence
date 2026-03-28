"""
=============================================================
  MÓDULO: EMAIL SENDER
  Envia relatórios por email automaticamente
=============================================================
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from datetime import datetime
from config import EMAIL_CONFIG

logger = logging.getLogger(__name__)


class EmailSender:
    """
    Envia emails com PDFs anexados para os destinatários configurados.
    """

    def __init__(self):
        self.cfg = EMAIL_CONFIG

    def enviar_relatorio(
        self,
        assunto: str,
        corpo_html: str,
        pdf_path: str,
        destinatarios: list = None
    ) -> bool:
        """
        Envia email com relatório PDF anexado.
        
        Args:
            assunto: Assunto do email
            corpo_html: Corpo do email em HTML
            pdf_path: Caminho do arquivo PDF a anexar
            destinatarios: Lista de emails (usa config padrão se None)
        
        Returns:
            True se enviado com sucesso
        """
        destinatarios = destinatarios or self.cfg["destinatarios"]
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"]    = self.cfg["remetente"]
        msg["To"]      = ", ".join(destinatarios)

        # Corpo HTML
        msg.attach(MIMEText(corpo_html, "html", "utf-8"))

        # Anexo PDF
        pdf_file = Path(pdf_path)
        if pdf_file.exists():
            with open(pdf_file, "rb") as f:
                parte = MIMEApplication(f.read(), _subtype="pdf")
                parte.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=pdf_file.name
                )
                msg.attach(parte)
        else:
            logger.warning(f"⚠️ PDF não encontrado: {pdf_path}")

        try:
            with smtplib.SMTP(self.cfg["smtp_host"], self.cfg["smtp_port"]) as server:
                server.ehlo()
                server.starttls()
                server.login(self.cfg["usuario"], self.cfg["senha"])
                server.sendmail(self.cfg["remetente"], destinatarios, msg.as_string())
            logger.info(f"✉️ Email enviado para: {destinatarios}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao enviar email: {e}")
            return False

    @staticmethod
    def corpo_auditoria(analise_resumo: str, data: str) -> str:
        return f"""
        <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto">
          <div style="background:#1A3C6E;padding:24px;border-radius:8px 8px 0 0">
            <h2 style="color:white;margin:0">🔍 Relatório de Auditoria</h2>
            <p style="color:#aac;margin:4px 0">Período: {data}</p>
          </div>
          <div style="border:1px solid #ddd;border-top:none;padding:24px;border-radius:0 0 8px 8px">
            <p>Prezados,</p>
            <p>O sistema de auditoria automática concluiu a análise dos lançamentos do período.</p>
            <div style="background:#f5f8ff;border-left:4px solid #1A3C6E;padding:16px;margin:16px 0;border-radius:4px">
              <strong>Resumo:</strong><br>
              <pre style="white-space:pre-wrap;font-size:13px">{analise_resumo[:600]}...</pre>
            </div>
            <p>O relatório completo está em anexo (PDF).</p>
            <hr style="border:none;border-top:1px solid #eee">
            <p style="font-size:12px;color:#888">
              Enviado automaticamente pela integração CRTI + Claude AI
            </p>
          </div>
        </body></html>
        """

    @staticmethod
    def corpo_operacional(periodo: str) -> str:
        data_hora = datetime.now().strftime("%d/%m/%Y às %H:%M")
        return f"""
        <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto">
          <div style="background:#0F7B3E;padding:24px;border-radius:8px 8px 0 0">
            <h2 style="color:white;margin:0">📦 Relatório Operacional</h2>
            <p style="color:#ace;margin:4px 0">Período: {periodo} | Gerado em: {data_hora}</p>
          </div>
          <div style="border:1px solid #ddd;border-top:none;padding:24px;border-radius:0 0 8px 8px">
            <p>Prezados,</p>
            <p>O relatório operacional automático foi gerado e está disponível em anexo.</p>
            <p>Ele contém análises de <strong>estoque, compras e vendas</strong> do período com alertas e recomendações.</p>
            <hr style="border:none;border-top:1px solid #eee">
            <p style="font-size:12px;color:#888">Enviado automaticamente pela integração CRTI + Claude AI</p>
          </div>
        </body></html>
        """

    @staticmethod
    def corpo_financeiro(periodo: str) -> str:
        data_hora = datetime.now().strftime("%d/%m/%Y às %H:%M")
        return f"""
        <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto">
          <div style="background:#6B21A8;padding:24px;border-radius:8px 8px 0 0">
            <h2 style="color:white;margin:0">📊 Análise Financeira</h2>
            <p style="color:#dac;margin:4px 0">Período: {periodo} | Gerado em: {data_hora}</p>
          </div>
          <div style="border:1px solid #ddd;border-top:none;padding:24px;border-radius:0 0 8px 8px">
            <p>Prezados,</p>
            <p>A análise financeira automática foi concluída. O relatório inclui <strong>DRE, fluxo de caixa e KPIs</strong>.</p>
            <p>O documento completo está em anexo.</p>
            <hr style="border:none;border-top:1px solid #eee">
            <p style="font-size:12px;color:#888">Enviado automaticamente pela integração CRTI + Claude AI</p>
          </div>
        </body></html>
        """
