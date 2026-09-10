"""
Departamento de Edição - Template do Relatório PDF
"Mini Canva" — mesmo template fixo pra toda página do relatório (Diagnóstico
ou Mensalidade), fundo claro, seguindo o Guia de Marca (Parte 2 - Identidade
Visual: tipografia, cores) e a especificação de header/footer/tipografia de
DESIGN_PDF em design_config.py.
"""

from .design_config import DESIGN_PDF, FINSPOTS_COLORS
from .text_utils import texto_para_paragrafos
from pathlib import Path
from typing import Optional
import base64
import html as html_lib

# Dimensão A4 a 150dpi (bate com renderer.render_html_pages_to_pdf)
PAGE_WIDTH_PX = 1240
PAGE_HEIGHT_PX = 1754

# Logo oficial da Finspots (mesmo PNG usado nos slides de vídeo — ver
# slide_template.LOGO_PADRAO), fornecida pelo analista em 05/09/2026.
# O "Fin" do arquivo original é branco (pensado pra fundo escuro, igual o
# vídeo). Nas páginas de conteúdo do PDF (fundo branco) isso fica invisível,
# então geramos uma segunda versão com o "Fin" recolorido pro azul escuro da
# marca (#020B3B) — só pra uso em fundo claro. O "spots" (laranja) e a mira
# não mudam em nenhuma das duas.
LOGO_PADRAO_FUNDO_ESCURO = Path(__file__).parent / "assets" / "finspots_logo.png"
LOGO_PADRAO_FUNDO_CLARO = Path(__file__).parent / "assets" / "finspots_logo_fundo_claro.png"

# Seletor CSS da área de conteúdo + limite inferior seguro (em px, dentro da
# página de PAGE_HEIGHT_PX px) usados pela IA Fiscal de Produção pra detectar
# estouro de texto pra cima do rodapé — mesma lógica do slide de vídeo.
SELETOR_CONTEUDO = ".pdf-content"
LIMITE_INFERIOR_CONTEUDO_PX = PAGE_HEIGHT_PX - 160


def _logo_header_html(logo_path: Optional[str], altura_px: int = 34, fundo: str = "claro") -> str:
    """
    fundo: "claro" (páginas de conteúdo, fundo branco) ou "escuro" (capa,
    fundo degradê). Só é usado pra escolher a logo padrão quando `logo_path`
    não é passado explicitamente — se vier um `logo_path`, ele manda.
    """
    if logo_path is None:
        padrao = LOGO_PADRAO_FUNDO_CLARO if fundo == "claro" else LOGO_PADRAO_FUNDO_ESCURO
        if padrao.exists():
            logo_path = str(padrao)
    if logo_path:
        caminho = Path(logo_path)
        mime = "image/png" if caminho.suffix.lower() == ".png" else "image/jpeg"
        dados_b64 = base64.b64encode(caminho.read_bytes()).decode("ascii")
        return f'<img src="data:{mime};base64,{dados_b64}" style="height:{altura_px}px;">'
    # Fallback em texto/HTML — só entra em cena se nem o arquivo oficial nem
    # nenhum logo_path explícito estiverem disponíveis.
    cor_fin = DESIGN_PDF['titulo_principal']['cor'] if fundo == "claro" else "#FFFFFF"
    mira = int(altura_px * 0.6)
    return f"""<span style="font-weight:800;font-size:{altura_px}px;line-height:1;">
        <span style="color:{cor_fin}">Fin</span><span style="color:{FINSPOTS_COLORS['laranja']}">sp</span><span style="display:inline-block;width:{mira}px;height:{mira}px;border-radius:50%;background:{FINSPOTS_COLORS['laranja']};position:relative;"><span style="position:absolute;top:32%;left:32%;width:36%;height:36%;border-radius:50%;background:#FFFFFF;"></span></span><span style="color:{FINSPOTS_COLORS['laranja']}">ts</span>
    </span>"""


def build_pdf_capa_html(
    nome_loja: str,
    subtitulo_produto: str,
    periodo_ou_mes: str,
    data_entrega: str,
    logo_path: Optional[str] = None,
) -> str:
    """Página 1 — Capa. Fundo escuro (identidade da marca), única página do PDF nesse tom."""
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    html,body {{ width:{PAGE_WIDTH_PX}px; height:{PAGE_HEIGHT_PX}px; }}
    body {{
        font-family: 'Poppins', 'Arial', sans-serif;
        background: linear-gradient(160deg, #000000 0%, #01184b 100%);
        color: #FFFFFF;
        position: relative;
    }}
    .capa-logo {{ position:absolute; top:120px; left:100px; }}
    .capa-titulo {{ position:absolute; top:720px; left:100px; right:100px; }}
    .capa-titulo h1 {{ font-size:52px; color:{FINSPOTS_COLORS['laranja']}; font-weight:800; margin-bottom:24px; }}
    .capa-titulo h2 {{ font-size:30px; font-weight:400; color:#FFFFFF; }}
    .capa-rodape {{ position:absolute; bottom:100px; left:100px; font-size:18px; color:#B7C0DA; }}
</style></head>
<body>
    <div class="capa-logo">{_logo_header_html(logo_path, altura_px=44, fundo="escuro")}</div>
    <div class="capa-titulo">
        <h1>{html_lib.escape(subtitulo_produto)}</h1>
        <h2>{html_lib.escape(nome_loja)} — {html_lib.escape(periodo_ou_mes)}</h2>
    </div>
    <div class="capa-rodape">Entrega: {html_lib.escape(data_entrega)}</div>
</body></html>"""


def build_pdf_page_html(
    numero_pagina: int,
    titulo_secao: str,
    corpo_texto: str,
    nome_loja: str,
    periodo_ou_mes: str,
    logo_path: Optional[str] = None,
    rodape_final: bool = False,
) -> str:
    """Uma página de conteúdo (2 em diante) — mesmo layout fixo, só o título/corpo mudam."""
    corpo_html = texto_para_paragrafos(corpo_texto)
    header_altura = DESIGN_PDF["header"]["altura_cm"]
    footer_altura = DESIGN_PDF["footer"]["altura_cm"]

    rodape_html = ""
    if rodape_final:
        rodape_html = f"""<div class="pdf-footer-final">{html_lib.escape(DESIGN_PDF['footer']['texto'])}</div>"""

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    html,body {{ width:{PAGE_WIDTH_PX}px; height:{PAGE_HEIGHT_PX}px; }}
    body {{
        font-family: {DESIGN_PDF['font_family_pdf']};
        background: {DESIGN_PDF['fundo_pagina']};
        color: {DESIGN_PDF['corpo']['cor']};
        position: relative;
    }}
    .pdf-header {{
        position: absolute; top:0; left:0; right:0; height:{header_altura}cm;
        display:flex; align-items:center; justify-content:space-between;
        padding: 0 70px;
        border-bottom: {DESIGN_PDF['header']['borda_inferior']};
    }}
    .pdf-header .cliente-info {{ font-size:13pt; color:{DESIGN_PDF['titulo_principal']['cor']}; font-weight:700; }}
    .pdf-content {{ position:absolute; top:calc({header_altura}cm + 60px); left:70px; right:70px; bottom:140px; }}
    .pdf-content h1 {{
        color:{DESIGN_PDF['titulo_secao']['cor']};
        font-size:{DESIGN_PDF['titulo_secao']['font_size_pt']}pt;
        font-weight:{DESIGN_PDF['titulo_secao']['font_weight']};
        margin-bottom:28px;
    }}
    .pdf-content p {{
        font-size:{DESIGN_PDF['corpo']['font_size_pt']}pt;
        line-height:{DESIGN_PDF['corpo']['line_height']};
        margin-bottom:16px;
    }}
    .pdf-footer {{
        position:absolute; bottom:0; left:0; right:0; height:{footer_altura}cm;
        display:flex; align-items:center; justify-content:space-between;
        padding:0 70px; font-size:{DESIGN_PDF['rodape']['font_size_pt']}pt; color:{DESIGN_PDF['rodape']['cor']};
        border-top: 1px solid #EEEEEE;
    }}
    .pdf-footer-final {{
        position:absolute; bottom:150px; left:70px; right:70px;
        font-size:10pt; color:{FINSPOTS_COLORS['azul_escuro']}; font-weight:700; text-align:center;
    }}
</style></head>
<body>
    <div class="pdf-header">
        {_logo_header_html(logo_path, altura_px=26, fundo="claro")}
        <div class="cliente-info">{html_lib.escape(nome_loja)} · {html_lib.escape(periodo_ou_mes)}</div>
    </div>
    <div class="pdf-content">
        <h1>{html_lib.escape(titulo_secao)}</h1>
        {corpo_html}
    </div>
    {rodape_html}
    <div class="pdf-footer">
        <span>Finspots — Inteligência de Vendas e Finanças para E-commerce</span>
        <span>Página {numero_pagina}</span>
    </div>
</body></html>"""
