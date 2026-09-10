"""
Departamento de Edição - Renderer
Wrapper fino sobre Playwright/Chromium pra transformar HTML (slide de vídeo
ou página de relatório) em PNG ou PDF. Determinístico — sem IA nenhuma aqui,
é só "tirar um print" do HTML gerado pelos templates.
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
from typing import List, Optional, Tuple, Union


def render_html_to_png(html: str, out_path: Union[str, Path], width: int = 1920, height: int = 1080) -> str:
    """Renderiza um HTML autocontido pra um PNG de dimensão exata (ex: um slide de vídeo)."""
    out_path = str(out_path)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=out_path)
        browser.close()
    return out_path


# JS: acha, dentro de `sel`, a borda superior (top) mais alta e a borda
# inferior (bottom) mais baixa entre os filhos diretos — ou seja, onde o
# conteúdo de verdade começa/termina na tela, independente da altura "de
# design" do container (importante agora que o corpo é centralizado
# verticalmente via flexbox, em vez de fixo no topo — ver slide_template.py).
_JS_MEDIR_LIMITES = """(sel) => {
    const c = document.querySelector(sel);
    if (!c) return null;
    const kids = c.querySelectorAll(':scope > *');
    if (kids.length === 0) {
        const r = c.getBoundingClientRect();
        return {top: r.top, bottom: r.bottom};
    }
    let minT = Infinity, maxB = 0;
    kids.forEach(k => {
        const r = k.getBoundingClientRect();
        minT = Math.min(minT, r.top);
        maxB = Math.max(maxB, r.bottom);
    });
    return {top: minT, bottom: maxB};
}"""


def render_html_to_png_com_medicao(
    html: str,
    out_path: Union[str, Path],
    selector: str,
    limite_bottom_px: float,
    width: int = 1920,
    height: int = 1080,
    limite_top_px: Optional[float] = None,
) -> Tuple[str, bool, Optional[float]]:
    """
    Igual a `render_html_to_png`, mas também mede se o conteúdo de `selector`
    (ex: o corpo de texto de um slide, ou a área de conteúdo de uma página do
    PDF) ultrapassa `limite_bottom_px` — sinal determinístico de estouro de
    texto pra fora do layout fixo (risco real quando se mantém a narração
    completa dentro de um card de tamanho fixo, como pedido pelo analista).

    limite_top_px: opcional — se passado, também reprova quando o conteúdo
    sobe além desse limite (ex: um card centralizado verticalmente com texto
    longo demais pode estourar tanto pra baixo quanto pra cima, em direção
    ao pill do título). Sem isso, só o limite inferior é checado (compatível
    com o comportamento anterior).

    Retorna (out_path, dentro_do_limite, medida_bottom_px). `medida_bottom_px`
    é None se o seletor não existir no HTML (não deveria acontecer com os
    templates oficiais — indica erro de template, não de conteúdo).
    """
    out_path = str(out_path)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=out_path)
        limites = page.evaluate(_JS_MEDIR_LIMITES, selector)
        browser.close()

    if limites is None:
        return out_path, True, None

    dentro_do_limite = limites["bottom"] <= limite_bottom_px
    if limite_top_px is not None:
        dentro_do_limite = dentro_do_limite and limites["top"] >= limite_top_px
    return out_path, dentro_do_limite, limites["bottom"]


def render_html_pages_to_pdf(
    htmls: List[str],
    out_path: Union[str, Path],
    page_width_px: int = 1240,
    page_height_px: int = 1754,
) -> str:
    """
    Renderiza uma lista de HTMLs (uma página do relatório cada) em um único
    PDF multi-página, na ordem dada. Cada item de `htmls` deve ser uma página
    A4 autocontida (ver pdf_template.py).
    """
    out_path = str(out_path)
    # Playwright não concatena páginas nativamente a partir de HTMLs
    # separados — a solução simples e robusta é gerar um PDF por página e
    # depois juntar com pypdf (já usado no restante do projeto via a skill de pdf).
    import tempfile
    from pypdf import PdfWriter

    writer = PdfWriter()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        with tempfile.TemporaryDirectory() as tmp:
            for i, pagina_html in enumerate(htmls):
                page.set_content(pagina_html, wait_until="networkidle")
                pagina_pdf_path = f"{tmp}/pagina_{i:02d}.pdf"
                page.pdf(
                    path=pagina_pdf_path,
                    width=f"{page_width_px}px",
                    height=f"{page_height_px}px",
                    print_background=True,
                    margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                )
                writer.append(pagina_pdf_path)
        browser.close()

    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path
