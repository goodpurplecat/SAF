"""
Departamento de Edição - Template do Slide de Vídeo
Layout fixo único (aprovado pelo analista em 04-05/09/2026): degradê
preto→#01184b, pill laranja de título (formato "flag", bleed à esquerda),
corpo em branco, ícone temático sólido à direita, logo Finspots no rodapé.

Mesmo HTML/CSS pra todo bloco do roteiro (Diagnóstico ou Mensalidade) — só
o título, o corpo e o ícone mudam, exatamente como pedido: "mesmo design,
só muda o texto".
"""

from .design_config import DESIGN_VIDEO, FINSPOTS_COLORS, FONT_FAMILY
from .graficos import DadosGrafico, render_grafico_svg
from .icons import render_icone
from .text_utils import texto_para_paragrafos
from pathlib import Path
from typing import Optional
import base64
import html as html_lib

# Logo oficial da Finspots (PNG com fundo transparente, fornecido pelo
# analista em 05/09/2026) — usada como marca d'água padrão em todo slide.
# Ainda dá pra sobrescrever passando `logo_path=` explicitamente se precisar.
LOGO_PADRAO = Path(__file__).parent / "assets" / "finspots_logo.png"

# Ícones temáticos customizados (PNG com fundo transparente, fornecidos pelo
# analista) ficam aqui, um arquivo por ícone: assets/icons/<nome_icone>.png
# (ex: "assets/icons/grafico_barras.png"). Se o arquivo existir, ele é usado
# no lugar do SVG gerado em icons.py — sem precisar mudar nenhum código,
# só soltar o PNG na pasta com o nome certo. Enquanto não vier, o SVG
# continua sendo o fallback (nunca quebra o pipeline por falta de um ícone).
ICONES_ASSETS_DIR = Path(__file__).parent / "assets" / "icons"


def _icone_imagem_path(nome_icone: str) -> Optional[Path]:
    caminho = ICONES_ASSETS_DIR / f"{nome_icone}.png"
    return caminho if caminho.exists() else None

# Seletor CSS do corpo de texto + limites seguros (em px, dentro do frame de
# 1080px) usados pela IA Fiscal de Produção pra detectar estouro de texto.
# O corpo agora fica dentro de uma faixa vertical centralizada (top 260px a
# bottom 220px, ver .fs-corpo-wrap) em vez de fixo no topo — como o card
# passou a ser curto (decisão do analista, 05/09/2026), ele fica centralizado
# nessa faixa em vez de "grudado" perto do pill do título. Os dois limites
# (superior e inferior) existem porque texto centralizado que ultrapassa a
# faixa estoura pros dois lados: pra cima (em direção ao pill) e pra baixo
# (em direção à logo).
SELETOR_CORPO = ".fs-corpo"
LIMITE_SUPERIOR_CORPO_PX = 260
LIMITE_INFERIOR_CORPO_PX = 860


def _logo_html_texto(altura_px: int = 42) -> str:
    """
    Fallback: logo Finspots reconstruída em HTML/CSS — 'Fin' branco + 'sp'
    laranja + símbolo de mira no lugar do 'o' + 'ts' laranja (regra exata do
    Guia de Marca, Parte 2 - Identidade Visual). Usada só enquanto o arquivo
    de logo oficial (JPG/PNG) não é fornecido — ver build_slide_html(logo_path=...).
    """
    mira_tamanho = int(altura_px * 0.62)
    return f"""
    <div class="fs-logo" style="height:{altura_px}px;">
        <span class="fs-logo-fin">Fin</span><span class="fs-logo-orange">sp</span><span class="fs-logo-mira" style="width:{mira_tamanho}px;height:{mira_tamanho}px;"></span><span class="fs-logo-orange">ts</span>
    </div>
    """


def _logo_html_imagem(logo_path: str, altura_px: int = 42) -> str:
    """Logo oficial (arquivo JPG/PNG do analista) embutida como marca d'água, via data URI."""
    caminho = Path(logo_path)
    mime = "image/png" if caminho.suffix.lower() == ".png" else "image/jpeg"
    dados_b64 = base64.b64encode(caminho.read_bytes()).decode("ascii")
    return f'<img class="fs-logo-img" src="data:{mime};base64,{dados_b64}" style="height:{altura_px}px;">'


def build_slide_html(
    titulo: str,
    corpo_texto: str,
    icone_nome: str = "grafico_barras",
    largura: int = 1920,
    altura: int = 1080,
    logo_path: Optional[str] = None,
    dados_grafico: Optional[DadosGrafico] = None,
) -> str:
    """
    titulo: texto curto que vai dentro do pill (ex: "Resultado Financeiro").
    corpo_texto: texto do slide (parágrafos separados por linha em branco).
    icone_nome: chave de icons.py (ver design_config.ICONE_POR_BLOCO).
    logo_path: caminho do arquivo de logo oficial (PNG/JPG). Se None, usa a
        logo oficial padrão em assets/finspots_logo.png (fornecida pelo
        analista em 05/09/2026); se esse arquivo também não existir, cai na
        reconstrução em HTML/CSS como último recurso.
    dados_grafico: gráfico de barras real (graficos.DadosGrafico), pros
        blocos que comparam número de verdade (ver
        design_config.BLOCOS_COM_GRAFICO_REAL) — decisão do analista,
        05/09/2026. Quando fornecido, ocupa o MESMO slot visual do ícone
        (à direita) e tem prioridade sobre ele; None (padrão) mantém o
        comportamento de sempre (ícone customizado ou SVG).
    """
    if logo_path is None and LOGO_PADRAO.exists():
        logo_path = str(LOGO_PADRAO)
    grad = DESIGN_VIDEO["gradiente"]
    pill = DESIGN_VIDEO["pill_titulo"]
    corpo_cfg = DESIGN_VIDEO["corpo"]
    icone_cfg = DESIGN_VIDEO["icone"]

    # negrito_dados=True: destaca R$/%/múltiplos automaticamente (pedido do
    # analista, 05/09/2026) — faz mais sentido agora que o texto é o card
    # curto, não a fala inteira: o dado principal deve saltar aos olhos.
    corpo_html = texto_para_paragrafos(corpo_texto, negrito_dados=True)
    titulo_escapado = html_lib.escape(titulo)

    # O slot da direita nunca é o emoji — o emoji de semáforo (quando o
    # bloco fala de status) fica só no texto do card/fala, como já vem do
    # dp-02 (confirmado pelo analista, 05/09/2026: "emoji é só no texto").
    # Prioridade aqui: 1) gráfico real, se dados_grafico foi passado (o
    # bloco compara número de verdade — ver BLOCOS_COM_GRAFICO_REAL);
    # 2) PNG customizado do analista, se já existir em
    # assets/icons/<nome>.png; 3) SVG interno (icons.py) como fallback.
    grafico_svg = render_grafico_svg(dados_grafico) if dados_grafico else ""
    if grafico_svg:
        icone_conteudo = grafico_svg
    else:
        caminho_icone_imagem = _icone_imagem_path(icone_nome)
        if caminho_icone_imagem:
            dados_b64 = base64.b64encode(caminho_icone_imagem.read_bytes()).decode("ascii")
            icone_conteudo = f'<img class="fs-icone-img" src="data:image/png;base64,{dados_b64}">'
        else:
            icone_conteudo = render_icone(icone_nome)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{ width: {largura}px; height: {altura}px; overflow: hidden; }}
    body {{
        font-family: {FONT_FAMILY};
        background: linear-gradient({grad['angulo_graus']}deg, {grad['inicio']} 0%, {grad['fim']} 100%);
        position: relative;
        width: {largura}px;
        height: {altura}px;
    }}
    .fs-pill {{
        position: absolute;
        top: 90px;
        left: 0;
        background: {pill['fundo']};
        color: {pill['texto_cor']};
        font-size: {pill['font_size_px']}px;
        font-weight: {pill['font_weight']};
        padding: 26px 70px 26px 80px;
        border-radius: 0 999px 999px 0;
        max-width: 68%;
        line-height: 1.15;
    }}
    .fs-corpo-wrap {{
        position: absolute;
        top: {LIMITE_SUPERIOR_CORPO_PX}px;
        bottom: {altura - LIMITE_INFERIOR_CORPO_PX}px;
        left: 80px;
        width: {corpo_cfg['max_largura_pct']}%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}
    .fs-corpo {{
        color: {corpo_cfg['cor']};
        font-size: {corpo_cfg['font_size_px']}px;
        font-weight: {corpo_cfg['font_weight']};
        line-height: {corpo_cfg['line_height']};
    }}
    .fs-corpo p {{ margin-bottom: 28px; }}
    .fs-corpo p:last-child {{ margin-bottom: 0; }}
    .fs-corpo strong {{ font-weight: 700; }}
    .fs-icone {{
        position: absolute;
        left: {icone_cfg['posicao']['x_pct']}%;
        top: {icone_cfg['posicao']['y_pct']}%;
        width: {icone_cfg['largura_px']}px;
        height: {icone_cfg['largura_px']}px;
        opacity: {icone_cfg['opacidade']};
        transform: translate(-50%, -50%);
    }}
    .fs-icone-img {{
        width: 100%;
        height: 100%;
        object-fit: contain;
    }}
    .fs-logo {{
        position: absolute;
        right: 56px;
        bottom: 48px;
        display: flex;
        align-items: center;
        font-weight: 800;
        font-size: 34px;
        line-height: 1;
        white-space: nowrap;
    }}
    .fs-logo-fin {{ color: {FINSPOTS_COLORS['branco']}; }}
    .fs-logo-orange {{ color: {FINSPOTS_COLORS['laranja']}; }}
    .fs-logo-mira {{
        display: inline-block;
        border-radius: 50%;
        background: {FINSPOTS_COLORS['laranja']};
        position: relative;
        margin: 0 1px;
    }}
    .fs-logo-mira::after {{
        content: "";
        position: absolute;
        top: 32%; left: 32%; width: 36%; height: 36%;
        border-radius: 50%;
        background: {DESIGN_VIDEO['gradiente']['fim']};
    }}
    .fs-logo-img {{
        position: absolute;
        right: 56px;
        bottom: 48px;
    }}
</style>
</head>
<body>
    <div class="fs-pill">{titulo_escapado}</div>
    <div class="fs-corpo-wrap"><div class="fs-corpo">{corpo_html}</div></div>
    <div class="fs-icone">{icone_conteudo}</div>
    {_logo_html_imagem(logo_path) if logo_path else _logo_html_texto()}
</body>
</html>"""
