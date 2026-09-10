"""
Departamento de Edição
Transforma o texto aprovado pela Produção (relatório + roteiro) em arquivos
finais de verdade: o PDF pronto e o vídeo MP4 pronto, na identidade visual
Finspots.
"""

from .models import (
    StatusEdicao,
    SlideRenderizado,
    ItemRevisaoFinal,
    RevisaoFiscalFinal,
    ResultadoEdicao,
)
from .design_config import (
    FINSPOTS_COLORS,
    FONT_FAMILY,
    DESIGN_VIDEO,
    DESIGN_PDF,
    SEMAFORO_EMOJI,
    ICONE_POR_BLOCO,
    DEFAULT_ICONE,
    BLOCOS_COM_GRAFICO_REAL,
    VIDEO_SPEC,
    TRANSICOES,
    AUDIO_CONFIG,
    icone_para_bloco,
    bloco_tem_grafico_recomendado,
)
from .icons import render_icone
from .graficos import BarraGrafico, DadosGrafico, render_grafico_svg
from .slide_template import build_slide_html
from .pdf_template import build_pdf_capa_html, build_pdf_page_html
from .renderer import render_html_to_png, render_html_to_png_com_medicao, render_html_pages_to_pdf
from .audio_generator import IAAudio
from .video_assembler import assemble_video
from .fiscal_producao_final import IAFiscalProducaoFinal
from .edicao import DepartamentoEdicao

__all__ = [
    "StatusEdicao",
    "SlideRenderizado",
    "ItemRevisaoFinal",
    "RevisaoFiscalFinal",
    "ResultadoEdicao",
    "FINSPOTS_COLORS",
    "FONT_FAMILY",
    "DESIGN_VIDEO",
    "DESIGN_PDF",
    "SEMAFORO_EMOJI",
    "ICONE_POR_BLOCO",
    "DEFAULT_ICONE",
    "BLOCOS_COM_GRAFICO_REAL",
    "VIDEO_SPEC",
    "TRANSICOES",
    "AUDIO_CONFIG",
    "icone_para_bloco",
    "bloco_tem_grafico_recomendado",
    "render_icone",
    "BarraGrafico",
    "DadosGrafico",
    "render_grafico_svg",
    "build_slide_html",
    "build_pdf_capa_html",
    "build_pdf_page_html",
    "render_html_to_png",
    "render_html_to_png_com_medicao",
    "render_html_pages_to_pdf",
    "IAAudio",
    "assemble_video",
    "IAFiscalProducaoFinal",
    "DepartamentoEdicao",
]
