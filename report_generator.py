"""
=============================================================
  MÓDULO: REPORT GENERATOR
  Geração de PDFs profissionais com layout corporativo
  Fonte: Inter/Helvetica | Cores: Azul corporativo + cinza
=============================================================
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, Image, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.flowables import KeepTogether

logger = logging.getLogger(__name__)

# ── Paleta de cores corporativa ──
AZUL_ESCURO  = colors.HexColor("#1A3C6E")
AZUL_MEDIO   = colors.HexColor("#2C5F9E")
AZUL_CLARO   = colors.HexColor("#E8F0FB")
AZUL_LINHA   = colors.HexColor("#D0DFF5")
CINZA_ESCURO = colors.HexColor("#333333")
CINZA_MEDIO  = colors.HexColor("#666666")
CINZA_CLARO  = colors.HexColor("#F5F6F8")
CINZA_LINHA  = colors.HexColor("#E0E0E0")
VERDE        = colors.HexColor("#0A6E3F")
VERDE_CLARO  = colors.HexColor("#E8F5EE")
VERMELHO     = colors.HexColor("#C0392B")
VERMELHO_CL  = colors.HexColor("#FDECEA")
AMARELO      = colors.HexColor("#F39C12")
AMARELO_CL   = colors.HexColor("#FEF9E7")
BRANCO       = colors.white
PRETO        = colors.black

# ── Margens da página ──
MARGEM_ESQ  = 2.0 * cm
MARGEM_DIR  = 1.8 * cm
MARGEM_TOPO = 2.5 * cm
MARGEM_INF  = 2.0 * cm
LARGURA_PAG, ALTURA_PAG = A4
LARGURA_UTIL = LARGURA_PAG - MARGEM_ESQ - MARGEM_DIR


class ReportGenerator:
    """
    Gera PDFs profissionais a partir do texto de análise do Claude.
    Layout: cabeçalho corporativo, seções com ícones, tabelas, rodapé.
    """

    def __init__(self, output_dir: str = "./outputs"):
        Path(output_dir).mkdir(exist_ok=True)
        self.output_dir = output_dir
        self._estilos = self._criar_estilos()

    # ─────────────────────────────────────────
    #  ESTILOS DE TEXTO
    # ─────────────────────────────────────────
    def _criar_estilos(self) -> dict:
        base = getSampleStyleSheet()
        fonte = "Helvetica"

        return {
            "titulo_capa": ParagraphStyle(
                "titulo_capa", fontName=f"{fonte}-Bold",
                fontSize=26, leading=32,
                textColor=BRANCO, alignment=TA_CENTER,
                spaceAfter=6,
            ),
            "subtitulo_capa": ParagraphStyle(
                "subtitulo_capa", fontName=fonte,
                fontSize=13, leading=18,
                textColor=colors.HexColor("#BDD0F0"), alignment=TA_CENTER,
                spaceAfter=4,
            ),
            "meta_capa": ParagraphStyle(
                "meta_capa", fontName=fonte,
                fontSize=10, leading=14,
                textColor=colors.HexColor("#90AFD8"), alignment=TA_CENTER,
            ),
            "h1": ParagraphStyle(
                "h1", fontName=f"{fonte}-Bold",
                fontSize=14, leading=18,
                textColor=AZUL_ESCURO,
                spaceBefore=18, spaceAfter=6,
                borderPad=0,
            ),
            "h2": ParagraphStyle(
                "h2", fontName=f"{fonte}-Bold",
                fontSize=11, leading=15,
                textColor=AZUL_MEDIO,
                spaceBefore=12, spaceAfter=4,
            ),
            "h3": ParagraphStyle(
                "h3", fontName=f"{fonte}-Bold",
                fontSize=10, leading=14,
                textColor=CINZA_ESCURO,
                spaceBefore=8, spaceAfter=3,
            ),
            "corpo": ParagraphStyle(
                "corpo", fontName=fonte,
                fontSize=9.5, leading=14,
                textColor=CINZA_ESCURO, alignment=TA_JUSTIFY,
                spaceAfter=5,
            ),
            "bullet": ParagraphStyle(
                "bullet", fontName=fonte,
                fontSize=9.5, leading=14,
                textColor=CINZA_ESCURO,
                leftIndent=14, firstLineIndent=-8,
                spaceAfter=3,
            ),
            "tabela_header": ParagraphStyle(
                "tabela_header", fontName=f"{fonte}-Bold",
                fontSize=8.5, leading=12,
                textColor=BRANCO, alignment=TA_CENTER,
            ),
            "tabela_cel": ParagraphStyle(
                "tabela_cel", fontName=fonte,
                fontSize=8.5, leading=12,
                textColor=CINZA_ESCURO,
            ),
            "alerta": ParagraphStyle(
                "alerta", fontName=f"{fonte}-Bold",
                fontSize=9, leading=13,
                textColor=VERMELHO, spaceAfter=4,
            ),
            "rodape": ParagraphStyle(
                "rodape", fontName=fonte,
                fontSize=7.5, leading=10,
                textColor=CINZA_MEDIO, alignment=TA_CENTER,
            ),
            "destaque": ParagraphStyle(
                "destaque", fontName=f"{fonte}-Bold",
                fontSize=10, leading=14,
                textColor=VERDE, spaceAfter=4,
            ),
        }

    # ─────────────────────────────────────────
    #  CABEÇALHO E RODAPÉ DAS PÁGINAS
    # ─────────────────────────────────────────
    def _cabecalho_rodape(self, canvas, doc, titulo: str, subtitulo: str):
        canvas.saveState()
        w, h = A4

        # ── Faixa superior ──
        canvas.setFillColor(AZUL_ESCURO)
        canvas.rect(0, h - 1.4*cm, w, 1.4*cm, fill=1, stroke=0)
        canvas.setFillColor(BRANCO)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(MARGEM_ESQ, h - 0.95*cm, titulo.upper())
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - MARGEM_DIR, h - 0.95*cm, subtitulo)

        # ── Linha decorativa ──
        canvas.setStrokeColor(AZUL_MEDIO)
        canvas.setLineWidth(0.5)
        canvas.line(MARGEM_ESQ, h - 1.5*cm, w - MARGEM_DIR, h - 1.5*cm)

        # ── Rodapé ──
        canvas.setFillColor(CINZA_CLARO)
        canvas.rect(0, 0, w, 1.1*cm, fill=1, stroke=0)
        canvas.setStrokeColor(CINZA_LINHA)
        canvas.setLineWidth(0.5)
        canvas.line(0, 1.1*cm, w, 1.1*cm)

        canvas.setFillColor(CINZA_MEDIO)
        canvas.setFont("Helvetica", 7.5)
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        canvas.drawString(MARGEM_ESQ, 0.4*cm, f"BRITAGEM VOGELSANGER LTDA  ·  Gerado em {now}")
        canvas.drawRightString(w - MARGEM_DIR, 0.4*cm,
                               f"Página {doc.page}")

        canvas.restoreState()

    def _capa_page(self, canvas, doc, titulo: str, subtitulo: str, tipo: str):
        """Página de capa com fundo gradiente azul."""
        canvas.saveState()
        w, h = A4

        # Fundo azul escuro
        canvas.setFillColor(AZUL_ESCURO)
        canvas.rect(0, 0, w, h, fill=1, stroke=0)

        # Faixa decorativa
        canvas.setFillColor(AZUL_MEDIO)
        canvas.rect(0, h * 0.38, w, h * 0.02, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#0F2A52"))
        canvas.rect(0, 0, w, h * 0.18, fill=1, stroke=0)

        # Linha decorativa lateral
        canvas.setFillColor(colors.HexColor("#4A8FD4"))
        canvas.rect(0, 0, 0.6*cm, h, fill=1, stroke=0)

        # Ícone do tipo de relatório
        icones = {
            "auditoria":           "🔍",
            "contas":              "💳",
            "mensal":              "📊",
            "permutas":            "🔄",
            "materiais":           "📦",
            "estoque":             "⚠️",
            "custos_servicos":     "🔧",
            "custos_equipamentos": "📉",
            "custos_bmo":          "👷",
            "auditoria_compras":   "🛒",
            "relatorio_compras":   "📋",
            "auditoria_frota":     "🚜",
            "manutencao":          "🔨",
            "patrimonio_frota":    "📋",
        }
        icone = icones.get(tipo, "📄")

        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(colors.HexColor("#90AFD8"))
        canvas.drawCentredString(w/2, h * 0.72,
                                 f"BRITAGEM VOGELSANGER LTDA")

        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#6090C0"))
        canvas.drawCentredString(w/2, h * 0.69,
                                 f"Sistema de Inteligência Operacional — Powered by Claude AI")

        # Linha separadora
        canvas.setStrokeColor(colors.HexColor("#4A8FD4"))
        canvas.setLineWidth(1)
        canvas.line(w*0.2, h*0.67, w*0.8, h*0.67)

        # Título principal
        canvas.setFont("Helvetica-Bold", 28)
        canvas.setFillColor(BRANCO)
        # Quebra título longo
        palavras = titulo.upper().split()
        if len(palavras) > 3:
            mid = len(palavras) // 2
            linha1 = " ".join(palavras[:mid])
            linha2 = " ".join(palavras[mid:])
            canvas.drawCentredString(w/2, h * 0.59, linha1)
            canvas.drawCentredString(w/2, h * 0.53, linha2)
            y_sub = h * 0.48
        else:
            canvas.drawCentredString(w/2, h * 0.56, titulo.upper())
            y_sub = h * 0.50

        # Subtítulo
        canvas.setFont("Helvetica", 12)
        canvas.setFillColor(colors.HexColor("#BDD0F0"))
        canvas.drawCentredString(w/2, y_sub - 0.5*cm, subtitulo)

        # Data e hora
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#6090C0"))
        now = datetime.now().strftime("%d de %B de %Y  ·  %H:%M")
        canvas.drawCentredString(w/2, h * 0.08,
                                 f"Relatório gerado em {now}")
        canvas.drawCentredString(w/2, h * 0.06,
                                 "Análise automatizada por Inteligência Artificial")

        canvas.restoreState()

    # ─────────────────────────────────────────
    #  PARSER DO TEXTO DO CLAUDE
    # ─────────────────────────────────────────
    def _parse_markdown(self, texto: str) -> list:
        """
        Converte o markdown retornado pelo Claude em flowables do ReportLab.
        Suporta: ### h1/h2/h3, - bullets, | tabelas |, texto livre, **negrito**
        """
        estilos = self._estilos
        flowables = []
        linhas = texto.split("\n")
        i = 0
        tabela_buffer = []

        while i < len(linhas):
            linha = linhas[i].rstrip()

            # ── Tabela markdown ──
            if "|" in linha and linha.strip().startswith("|"):
                tabela_buffer.append(linha)
                i += 1
                continue
            else:
                if tabela_buffer:
                    fl = self._tabela_md(tabela_buffer)
                    if fl:
                        flowables.append(Spacer(1, 4))
                        flowables.append(fl)
                        flowables.append(Spacer(1, 6))
                    tabela_buffer = []

            # ── Linha em branco ──
            if not linha.strip():
                flowables.append(Spacer(1, 4))
                i += 1
                continue

            # ── H1 (### ou #) ──
            if linha.startswith("### "):
                txt = linha[4:].strip()
                flowables.append(Spacer(1, 8))
                flowables.append(HRFlowable(
                    width="100%", thickness=2,
                    color=AZUL_ESCURO, spaceAfter=4
                ))
                flowables.append(Paragraph(
                    self._md_inline(txt), estilos["h1"]
                ))
                i += 1
                continue

            # ── H2 (## ou ####) ──
            if linha.startswith("## ") or linha.startswith("#### "):
                txt = re.sub(r"^#{2,6}\s+", "", linha).strip()
                flowables.append(Paragraph(
                    self._md_inline(txt), estilos["h2"]
                ))
                i += 1
                continue

            # ── H3 (#####) ──
            if linha.startswith("# ") or linha.startswith("##### "):
                txt = re.sub(r"^#{1,6}\s+", "", linha).strip()
                flowables.append(Paragraph(
                    self._md_inline(txt), estilos["h3"]
                ))
                i += 1
                continue

            # ── Bullet (- ou * ou •) ──
            if re.match(r"^[\-\*•]\s+", linha):
                txt = re.sub(r"^[\-\*•]\s+", "", linha).strip()
                flowables.append(Paragraph(
                    f"• &nbsp; {self._md_inline(txt)}", estilos["bullet"]
                ))
                i += 1
                continue

            # ── Bullet numerado (1. 2. etc) ──
            m = re.match(r"^(\d+)\.\s+(.+)", linha)
            if m:
                flowables.append(Paragraph(
                    f"<b>{m.group(1)}.</b> &nbsp; {self._md_inline(m.group(2))}",
                    estilos["bullet"]
                ))
                i += 1
                continue

            # ── Linha de separação ──
            if re.match(r"^[-=_]{3,}$", linha.strip()):
                flowables.append(HRFlowable(
                    width="100%", thickness=0.5,
                    color=CINZA_LINHA, spaceAfter=4
                ))
                i += 1
                continue

            # ── Texto normal ──
            if linha.strip():
                flowables.append(Paragraph(
                    self._md_inline(linha), estilos["corpo"]
                ))

            i += 1

        # Flush tabela pendente
        if tabela_buffer:
            fl = self._tabela_md(tabela_buffer)
            if fl:
                flowables.append(fl)

        return flowables

    def _md_inline(self, txt: str) -> str:
        """Converte **negrito**, *itálico* e `code` para tags ReportLab."""
        txt = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", txt)
        txt = re.sub(r"\*(.+?)\*",     r"<i>\1</i>", txt)
        txt = re.sub(r"`(.+?)`",        r"<font name='Courier'>\1</font>", txt)
        # Escapa & que não sejam entidades
        txt = re.sub(r"&(?!amp;|lt;|gt;|nbsp;|#)", "&amp;", txt)
        return txt

    def _tabela_md(self, linhas: list):
        """Converte tabela markdown em Table do ReportLab."""
        linhas = [l for l in linhas if not re.match(r"^\|[-:| ]+\|$", l.strip())]
        if len(linhas) < 2:
            return None

        dados = []
        for linha in linhas:
            celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
            dados.append(celulas)

        if not dados:
            return None

        n_cols = max(len(r) for r in dados)
        for row in dados:
            while len(row) < n_cols:
                row.append("")

        col_width = LARGURA_UTIL / n_cols
        estilos = self._estilos

        # Formata células
        dados_fmt = []
        for i, row in enumerate(dados):
            estilo = estilos["tabela_header"] if i == 0 else estilos["tabela_cel"]
            dados_fmt.append([Paragraph(self._md_inline(c), estilo) for c in row])

        t = Table(dados_fmt, colWidths=[col_width] * n_cols, repeatRows=1)
        t.setStyle(TableStyle([
            # Header
            ("BACKGROUND",    (0, 0), (-1, 0),  AZUL_ESCURO),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  BRANCO),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0),  8.5),
            ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, 0),  6),
            ("BOTTOMPADDING", (0, 0), (-1, 0),  6),
            # Dados
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
            ("TOPPADDING",    (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            # Zebra
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BRANCO, CINZA_CLARO]),
            # Grid
            ("GRID",           (0, 0), (-1, -1), 0.5, CINZA_LINHA),
            ("LINEBELOW",      (0, 0), (-1, 0),  1.5, AZUL_MEDIO),
            ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return t

    # ─────────────────────────────────────────
    #  CAIXA DE RESUMO EXECUTIVO
    # ─────────────────────────────────────────
    def _caixa_resumo(self, linhas_texto: list, cor_fundo, cor_borda) -> Table:
        paragrafos = [Paragraph(self._md_inline(l), self._estilos["corpo"]) for l in linhas_texto if l.strip()]
        t = Table([[paragrafos]], colWidths=[LARGURA_UTIL])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), cor_fundo),
            ("LINEBEFOREBEFORE", (0, 0), (0, -1), 4, cor_borda),
            ("LINEBEFORE",    (0, 0), (0, -1),  4, cor_borda),
            ("LINEABOVE",     (0, 0), (-1, 0),  0.5, cor_borda),
            ("LINEBELOW",     (0, -1), (-1, -1), 0.5, cor_borda),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 14),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ]))
        return t

    # ─────────────────────────────────────────
    #  MÉTODO PRINCIPAL — GERAR PDF
    # ─────────────────────────────────────────
    def gerar_pdf(
        self,
        titulo: str,
        analise: str,
        tipo: str = "relatorio",
        subtitulo: str = "",
    ) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"{tipo}_{timestamp}.pdf"
        caminho = os.path.join(self.output_dir, nome_arquivo)

        # ── Configura documento ──
        doc = BaseDocTemplate(
            caminho,
            pagesize=A4,
            leftMargin=MARGEM_ESQ,
            rightMargin=MARGEM_DIR,
            topMargin=MARGEM_TOPO,
            bottomMargin=MARGEM_INF,
        )

        # ── Templates de página ──
        frame_capa = Frame(0, 0, LARGURA_PAG, ALTURA_PAG, id="capa")
        frame_corpo = Frame(
            MARGEM_ESQ, MARGEM_INF,
            LARGURA_UTIL, ALTURA_PAG - MARGEM_TOPO - MARGEM_INF - 0.5*cm,
            id="corpo"
        )

        def capa_fn(canvas, doc):
            self._capa_page(canvas, doc, titulo, subtitulo, tipo)

        def corpo_fn(canvas, doc):
            self._cabecalho_rodape(canvas, doc, titulo, subtitulo)

        doc.addPageTemplates([
            PageTemplate(id="Capa",  frames=[frame_capa],  onPage=capa_fn),
            PageTemplate(id="Corpo", frames=[frame_corpo], onPage=corpo_fn),
        ])

        # ── Constrói conteúdo ──
        story = []

        # Capa (página em branco — o desenho é feito no onPage)
        story.append(NextPageTemplate("Corpo"))
        story.append(PageBreak())

        # Título da seção de conteúdo
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(titulo, self._estilos["h1"]))
        if subtitulo:
            story.append(Paragraph(subtitulo, self._estilos["h2"]))
        story.append(HRFlowable(
            width="100%", thickness=2,
            color=AZUL_ESCURO, spaceAfter=8
        ))
        story.append(Spacer(1, 0.3*cm))

        # Conteúdo da análise
        flowables = self._parse_markdown(analise)
        story.extend(flowables)

        # Rodapé final
        story.append(Spacer(1, 1*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=CINZA_LINHA))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(
            f"Análise gerada automaticamente por Claude AI (Anthropic) · "
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')} · "
            f"BRITAGEM VOGELSANGER LTDA",
            self._estilos["rodape"]
        ))

        doc.build(story)
        logger.info(f"✅ PDF gerado: {caminho}")
        return caminho