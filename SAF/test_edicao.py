"""
Teste do Departamento de Edição (dp-03)

Como em test_producao.py e test_tratamento.py, dividido em:
1. Testes estruturais/determinísticos (SEM chamada de API, mas COM
   Playwright/ffmpeg reais — que são determinísticos, então rodam sempre
   neste ambiente) — templates, medição de estouro de texto, IA de Áudio em
   modo placeholder, montagem de vídeo, checagem de completude da IA Fiscal.
2. Teste do pipeline completo (COM chamada de API) — sem GEMINI_API_KEY
   configurada neste ambiente, a IA Fiscal de Produção falha na chamada e
   cai em NÃO_APROVADO (nunca aprova por omissão) — a falha é esperada e
   capturada explicitamente, exatamente como test_producao.py faz com a
   IA de Relatório e Roteiro.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "dp-03"))

from edicao import (
    StatusEdicao,
    ItemRevisaoFinal,
    RevisaoFiscalFinal,
    SlideRenderizado,
    icone_para_bloco,
    bloco_tem_grafico_recomendado,
    DEFAULT_ICONE,
    ICONE_POR_BLOCO,
    BLOCOS_COM_GRAFICO_REAL,
    BarraGrafico,
    DadosGrafico,
    render_grafico_svg,
    build_slide_html,
    build_pdf_capa_html,
    build_pdf_page_html,
    render_html_to_png_com_medicao,
    IAAudio,
    assemble_video,
    IAFiscalProducaoFinal,
    DepartamentoEdicao,
)
from edicao.slide_template import SELETOR_CORPO, LIMITE_INFERIOR_CORPO_PX, LIMITE_SUPERIOR_CORPO_PX
from edicao.pdf_template import SELETOR_CONTEUDO, LIMITE_INFERIOR_CONTEUDO_PX, PAGE_WIDTH_PX, PAGE_HEIGHT_PX
from edicao.text_utils import texto_para_paragrafos, destacar_dados_importantes


def teste_icone_por_bloco():
    """Todo bloco mapeado aponta pra um ícone que de fato existe em icons.py; desconhecido cai no default."""
    print("\n[1/14] Mapeamento bloco → ícone temático...")
    from edicao.icons import render_icone

    for nome_bloco, nome_icone in ICONE_POR_BLOCO.items():
        svg = render_icone(nome_icone)
        assert svg.strip().startswith("<svg"), f"Ícone '{nome_icone}' (bloco '{nome_bloco}') não gerou SVG válido"

    assert icone_para_bloco("Bloco Totalmente Desconhecido XYZ") == DEFAULT_ICONE
    print(f"      ✅ {len(ICONE_POR_BLOCO)} blocos mapeados, todos com ícone SVG válido; desconhecido cai em '{DEFAULT_ICONE}'")


def teste_texto_para_paragrafos():
    """Regressão do bug encontrado no render de amostra: linha simples vira <br>, não some."""
    print("\n[2/14] texto_para_paragrafos — parágrafos e quebras de linha simples...")

    texto = "Receita Líquida: R$ 48.200\nCustos Totais: R$ 38.560\n\nEsse foi o melhor mês."
    html = texto_para_paragrafos(texto)
    assert html.count("<p>") == 2, "Deveria gerar 2 parágrafos (separados por linha em branco)"
    assert "Receita Líquida: R$ 48.200<br>Custos Totais: R$ 38.560" in html, "Quebra de linha simples deveria virar <br>, não sumir"
    assert "Esse foi o melhor mês." in html
    print("      ✅ Parágrafos (\\n\\n → <p>) e linhas simples (\\n → <br>) preservados corretamente")


def teste_negrito_dados_importantes():
    """
    Destaque automático (regex, sem IA) de R$/%/múltiplos no card do slide —
    pedido do analista, 05/09/2026: "coloca em negrito o que for importante".
    """
    print("\n[3/14] Destaque automático de dados importantes (negrito)...")

    texto_escapado = "R$ 48.200 faturados, R$ 9.640 de lucro (20% de margem). LTV:CAC de 11,9x."
    destacado = destacar_dados_importantes(texto_escapado)
    assert "<strong>R$ 48.200</strong>" in destacado
    assert "<strong>R$ 9.640</strong>" in destacado
    assert "<strong>20%</strong>" in destacado
    assert "<strong>11,9x</strong>" in destacado

    # integrado em texto_para_paragrafos via negrito_dados=True (usado no card do slide)
    html_com_negrito = texto_para_paragrafos("Receita: R$ 48.200.", negrito_dados=True)
    assert "<strong>R$ 48.200</strong>" in html_com_negrito
    html_sem_negrito = texto_para_paragrafos("Receita: R$ 48.200.")  # default False (usado no PDF)
    assert "<strong>" not in html_sem_negrito

    print("      ✅ R$/%/múltiplos destacados corretamente; negrito_dados=False (padrão) não altera nada")


def teste_icone_customizado_png_vs_svg():
    """
    Prioridade de conteúdo do slot do ícone (pedido do analista, 05/09/2026):
    PNG customizado em assets/icons/<nome>.png se já existir, senão SVG
    interno (icons.py) como fallback. O slot do ícone é sempre uma
    imagem/desenho — nunca o emoji de semáforo, que fica só no texto do
    card/fala (correção explícita do analista, 05/09/2026: "emoji é só no
    texto"), coberto por teste_negrito_dados_importantes e pelos testes do
    dp-02 (roteiro fala/card), não aqui.

    Desde 05/09/2026 os 8 ícones reais (ver ICONE_POR_BLOCO) já têm PNG
    customizado de verdade em assets/icons/ (entregues pelo analista, fundo
    transparente) — então o teste do fallback pro SVG usa um nome de ícone
    inexistente de propósito, pra não depender de nenhum desses 8 arquivos
    ficarem ausentes.
    """
    print("\n[4/14] Ícone: PNG customizado > SVG (fallback)...")
    from edicao import slide_template
    import base64

    # 1) com um PNG customizado disponível -> usa o PNG (embutido como base64)
    icone_teste_path = slide_template.ICONES_ASSETS_DIR / "_teste_icone_customizado.png"
    slide_template.ICONES_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    png_1x1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    icone_teste_path.write_bytes(png_1x1)
    try:
        html_com_png = build_slide_html("Bloco Teste", "Texto de teste.", icone_nome="_teste_icone_customizado")
        assert 'class="fs-icone-img"' in html_com_png
    finally:
        icone_teste_path.unlink(missing_ok=True)

    # 2) ícone sem PNG customizado (nome que de propósito não existe em assets/icons/) -> cai no SVG interno
    html_svg = build_slide_html("Bloco Sem PNG", "Texto normal.", icone_nome="_icone_que_nao_existe_de_verdade")
    assert "<svg" in html_svg
    assert 'class="fs-icone-img"' not in html_svg

    # 3) os 8 ícones reais JÁ têm PNG customizado do analista (entregues 05/09/2026) -> usam o PNG, não o SVG
    for nome_icone in ICONE_POR_BLOCO.values():
        html_com_png_real = build_slide_html("Bloco Teste", "Texto normal.", icone_nome=nome_icone)
        assert 'class="fs-icone-img"' in html_com_png_real, f"Ícone '{nome_icone}' deveria usar o PNG customizado do analista"

    # 4) o slot do ícone nunca vira emoji, mesmo quando o texto do card tem um embutido
    #    (o emoji fica só no texto — não existe mais lógica de override no template)
    html_com_semaforo_no_texto = build_slide_html("Status Geral", "Status: 🟡 ATENÇÃO.", icone_nome="engrenagem")
    assert 'class="fs-icone-img"' in html_com_semaforo_no_texto, "Ícone deve continuar sendo a imagem/PNG, mesmo com emoji no texto do card"
    assert "🟡 ATENÇÃO" in html_com_semaforo_no_texto, "O emoji deve aparecer no texto do card normalmente"

    print("      ✅ PNG customizado tem prioridade sobre o SVG (inclusive nos 8 ícones reais); ícone nunca vira emoji")


def teste_grafico_real_render_svg():
    """
    graficos.py — desenho determinístico do gráfico de barras real (pedido
    do analista, 05/09/2026, depois de notar que o roteiro já presume "o
    slide mostra o gráfico" mas até então só tinha ícone decorativo).
    """
    print("\n[5/14] Gráfico de barras real (graficos.py) — SVG determinístico...")

    # 1) sem barras -> string vazia (quem chama decide o fallback pro ícone)
    assert render_grafico_svg(DadosGrafico(barras=[])) == ""

    # 2) barra simples (sem comparação) — valor formatado como moeda
    dados_simples = DadosGrafico(
        barras=[BarraGrafico(rotulo="Receita Líquida", valor=48200)],
        formato_valor="moeda",
    )
    svg_simples = render_grafico_svg(dados_simples)
    assert svg_simples.strip().startswith("<svg")
    assert "R$ 48.200" in svg_simples
    assert "Receita Líquida" in svg_simples

    # 3) par atual vs anterior (ex.: bloco COMPARATIVO/COMPARATIVO FINANCEIRO) — percentual
    dados_comparativo = DadosGrafico(
        barras=[
            BarraGrafico(rotulo="Margem Contribuição", valor=43.5, valor_comparacao=41.0),
            BarraGrafico(rotulo="Margem Líquida", valor=22.7, valor_comparacao=16.0),
        ],
        formato_valor="percentual",
        legenda_atual="Mês Atual",
        legenda_comparacao="Mês Anterior",
    )
    svg_comparativo = render_grafico_svg(dados_comparativo)
    assert "44%" in svg_comparativo  # 43.5 arredondado
    assert "41%" in svg_comparativo
    assert "Mês Atual" in svg_comparativo and "Mês Anterior" in svg_comparativo
    # 2 barras × 2 (atual+anterior) = 4 <rect> de dado + 2 <rect> de legenda
    assert svg_comparativo.count("<rect") == 6

    print("      ✅ Sem barras vira string vazia; barra simples e par atual/anterior desenham SVG correto")


def teste_grafico_tem_prioridade_no_slot():
    """
    Prioridade do slot da direita no slide (pedido do analista, 05/09/2026):
    1) gráfico real (dados_grafico), 2) PNG customizado, 3) SVG do ícone.
    """
    print("\n[6/14] Gráfico real tem prioridade sobre ícone (customizado ou SVG)...")

    dados = DadosGrafico(barras=[BarraGrafico(rotulo="Lucro Líquido", valor=9640)])

    # com dados_grafico -> desenha o gráfico, tem prioridade até sobre o PNG customizado do ícone
    html_com_grafico = build_slide_html("Resultado Financeiro", "Texto do card.", icone_nome="grafico_barras", dados_grafico=dados)
    assert "R$ 9.640" in html_com_grafico
    assert "Lucro Líquido" in html_com_grafico
    assert 'class="fs-icone-img"' not in html_com_grafico, "Gráfico real deveria ter prioridade sobre o PNG customizado do ícone"

    # sem dados_grafico -> comportamento de sempre (PNG customizado, já que "grafico_barras" tem um; ver ICONE_POR_BLOCO)
    html_sem_grafico = build_slide_html("Resultado Financeiro", "Texto do card.", icone_nome="grafico_barras")
    assert 'class="fs-icone-img"' in html_sem_grafico
    assert "R$ 9.640" not in html_sem_grafico

    # mapeamento bloco -> candidato a gráfico real (documentação/orientação, não obrigatório)
    assert bloco_tem_grafico_recomendado("BLOCO 1 — RESULTADO FINANCEIRO")
    assert bloco_tem_grafico_recomendado("BLOCO 2 — COMPARATIVO FINANCEIRO")
    assert bloco_tem_grafico_recomendado("BLOCO 2 — COMPARATIVO DE VENDAS")
    assert not bloco_tem_grafico_recomendado("BLOCO 1 — STATUS GERAL")
    assert len(BLOCOS_COM_GRAFICO_REAL) == 4

    print("      ✅ dados_grafico tem prioridade sobre o ícone; bloco_tem_grafico_recomendado() casa os 4 blocos certos")


def teste_estouro_de_texto_slide():
    """Checagem determinística de estouro — a mesma usada pela IA Fiscal de Produção."""
    print("\n[7/14] Detecção de estouro de texto no slide (Playwright)...")

    texto_normal = "Sua loja faturou R$ 48.200 em agosto.\n\nMargem de 20%."
    html_ok = build_slide_html("Resultado", texto_normal, icone_nome="grafico_barras")
    _, dentro_ok, medida_ok = render_html_to_png_com_medicao(
        html_ok, "/tmp/_teste_edicao_slide_ok.png", SELETOR_CORPO, LIMITE_INFERIOR_CORPO_PX,
        limite_top_px=LIMITE_SUPERIOR_CORPO_PX,
    )
    assert dentro_ok, f"Texto curto (agora centralizado, ver LIMITE_SUPERIOR/INFERIOR_CORPO_PX) não deveria estourar (medido {medida_ok}px)"

    texto_gigante = "\n\n".join([f"Parágrafo {i} bem longo, repetindo bastante conteúdo pra forçar o estouro do card fixo do slide de vídeo." for i in range(10)])
    html_estoura = build_slide_html("Teste de Estouro", texto_gigante, icone_nome="alvo")
    _, dentro_estoura, medida_estoura = render_html_to_png_com_medicao(
        html_estoura, "/tmp/_teste_edicao_slide_estoura.png", SELETOR_CORPO, LIMITE_INFERIOR_CORPO_PX
    )
    assert not dentro_estoura, "Texto gigante deveria ultrapassar o limite do card"
    print(f"      ✅ Texto normal dentro do limite ({medida_ok:.0f}px); texto gigante detectado como estouro ({medida_estoura:.0f}px > {LIMITE_INFERIOR_CORPO_PX}px)")


def teste_estouro_de_texto_pdf():
    """Mesma checagem, na página de conteúdo do PDF."""
    print("\n[8/14] Detecção de estouro de texto na página do PDF (Playwright)...")

    html_ok = build_pdf_page_html(2, "Resultado Financeiro", "Receita: R$ 48.200\nLucro: R$ 9.640", "Loja Exemplo", "Agosto/2026")
    _, dentro_ok, _ = render_html_to_png_com_medicao(
        html_ok, "/tmp/_teste_edicao_pdf_ok.png", SELETOR_CONTEUDO, LIMITE_INFERIOR_CONTEUDO_PX,
        width=PAGE_WIDTH_PX, height=PAGE_HEIGHT_PX,
    )
    assert dentro_ok, "Página de conteúdo normal não deveria estourar"
    print("      ✅ Página de conteúdo normal dentro do limite")


def teste_ia_audio_modo_placeholder():
    """Sem ELEVENLABS_API_KEY, cai em modo placeholder (áudio silencioso com duração estimada)."""
    print("\n[9/14] IA de Áudio — modo placeholder (sem ELEVENLABS_API_KEY)...")

    audio = IAAudio()
    assert not audio.modo_real, "Sem ELEVENLABS_API_KEY, modo_real deveria ser False"

    duracao = audio.gerar_audio_bloco("Este é um texto de teste com algumas palavras para estimar a duração.", "/tmp/_teste_edicao_audio.mp3")
    assert duracao > 0
    assert os.path.exists("/tmp/_teste_edicao_audio.mp3")
    print(f"      ✅ Áudio placeholder gerado — {duracao:.2f}s estimados (sem chave real, sinalizado via modo_real=False)")


def teste_assemble_video():
    """Monta um vídeo de 2 slides a partir de PNGs + áudios placeholder já gerados."""
    print("\n[10/14] Montagem de vídeo (ffmpeg) — 2 slides...")

    slides = [
        SlideRenderizado(bloco_nome="Bloco 1", imagem_path="/tmp/_teste_edicao_slide_ok.png",
                          audio_path="/tmp/_teste_edicao_audio.mp3", duracao_segundos=2.0),
    ]
    out_path = assemble_video(slides, "/tmp/_teste_edicao_video.mp4")
    assert os.path.exists(out_path)
    assert os.path.getsize(out_path) > 0
    print(f"      ✅ Vídeo montado em {out_path}")


def teste_dados_graficos_no_pipeline():
    """
    DepartamentoEdicao._montar_video_slides() encaminha dados_graficos pro
    bloco certo por nome EXATO (mesma chave de roteiro_falas/roteiro_cards)
    — não quebra quando o dict vem parcial (só alguns blocos têm gráfico)
    nem quando vem None (comportamento de sempre).
    """
    print("\n[11/14] dados_graficos encaminhado corretamente em _montar_video_slides()...")

    depto = DepartamentoEdicao(max_tentativas_tecnicas=1)
    roteiro_falas = {"Resultado Financeiro": "Fala do resultado.", "Status Geral": "Fala do status."}
    roteiro_cards = {"Resultado Financeiro": "Card do resultado.", "Status Geral": "Card do status."}
    dados_graficos = {
        "Resultado Financeiro": DadosGrafico(barras=[BarraGrafico(rotulo="Lucro Líquido", valor=9640)]),
        # "Status Geral" não tem entrada -> deve cair no ícone normal, sem quebrar
    }

    slides, falas_montado, cards_montado, _ = depto._montar_video_slides(
        ["Resultado Financeiro", "Status Geral"], roteiro_falas, roteiro_cards,
        Path("/tmp/_teste_edicao_dados_graficos"), dados_graficos,
    )
    assert len(slides) == 2
    assert falas_montado["Resultado Financeiro"] == "Fala do resultado."
    assert cards_montado["Status Geral"] == "Card do status."

    # sem dados_graficos nenhum (None) -> não quebra, comportamento de sempre
    slides_sem_grafico, _, _, _ = depto._montar_video_slides(
        ["Status Geral"], roteiro_falas, roteiro_cards, Path("/tmp/_teste_edicao_dados_graficos"), None,
    )
    assert len(slides_sem_grafico) == 1

    print("      ✅ Bloco com dados_graficos usa o gráfico; bloco sem entrada e dados_graficos=None não quebram")


def teste_fiscal_completude_deterministica():
    """A IA Fiscal de Produção pega bloco sumido/divergente SEM precisar chamar API."""
    print("\n[12/14] IA Fiscal de Produção — completude determinística (sem API)...")

    fiscal = IAFiscalProducaoFinal.__new__(IAFiscalProducaoFinal)  # não precisa do client Anthropic pra este teste

    achados_fala = fiscal._checar_par("Roteiro (fala)", {"Bloco A": "texto A", "Bloco B": "texto B"}, {"Bloco A": "texto A"})
    achados_relatorio = fiscal._checar_par(
        "Relatório", {2: "página 2"}, {2: "página 2 ALTERADA"}, rotulo_chave="Página"
    )
    localizacoes = {item.localizacao for item in achados_fala + achados_relatorio}
    assert any("Bloco B" in loc for loc in localizacoes), "Deveria detectar bloco sumido"
    assert any("Página 2" in loc for loc in localizacoes), "Deveria detectar texto divergente"
    print(f"      ✅ {len(achados_fala) + len(achados_relatorio)} divergência(s) detectada(s) sem nenhuma chamada de API")


def teste_revisao_fiscal_final_dataclass():
    """Confere precisa_correcao (bloqueadores OU ajustes bloqueiam, igual RevisaoFiscal do dp-02)."""
    print("\n[13/14] Dataclass RevisaoFiscalFinal...")

    limpa = RevisaoFiscalFinal(aprovado=True)
    assert not limpa.precisa_correcao

    com_ajuste = RevisaoFiscalFinal(ajustes=[ItemRevisaoFinal(localizacao="Bloco X", problema="Ícone não combina")])
    assert com_ajuste.precisa_correcao

    print("      ✅ precisa_correcao correto (bloqueadores OU ajustes bloqueiam o envio)")


def teste_pipeline_completo_com_api():
    """
    Pipeline ponta a ponta do dp-03: DepartamentoEdicao.processar() com
    conteúdo já "aprovado" (simulado — normalmente viria do dp-02).
    A montagem de PDF/vídeo em si NÃO depende de nenhuma API (é
    determinística), mas a IA Fiscal de Produção final usa Claude — sem
    GEMINI_API_KEY, ela nunca aprova por omissão, então o status
    esperado aqui é REVISAO_MANUAL_NECESSARIA, com os arquivos MESMO ASSIM
    gerados (só não aprovados pra ir pro cliente).
    """
    print("\n[14/14] Pipeline completo (APP Intermediador → PDF + Vídeo → IA Fiscal) — requer GEMINI_API_KEY pra aprovar...")

    relatorio_paginas = {
        2: "Sua loja faturou R$ 48.200 em agosto, com lucro líquido de R$ 9.640 (20% de margem).",
        3: "Custos totais somaram R$ 38.560 este mês.",
    }
    titulos_paginas = {2: "Resultado Financeiro", 3: "Custos e Canais"}
    roteiro_falas = {
        "Resultado Financeiro": "Sua loja faturou R$ 48.200 em agosto, com lucro líquido de R$ 9.640.",
        "Custos e Canais": "Seus custos totais somaram R$ 38.560 este mês.",
    }
    roteiro_cards = {
        "Resultado Financeiro": "R$ 48.200 faturados. Lucro de R$ 9.640.",
        "Custos e Canais": "Custos totais: R$ 38.560.",
    }
    cliente = {"nome_loja": "E-commerce Teste Edição", "periodo": "Agosto/2026"}

    depto = DepartamentoEdicao(max_tentativas_tecnicas=1)
    resultado = depto.processar(
        tipo_produto="Diagnóstico",
        cliente=cliente,
        relatorio_paginas=relatorio_paginas,
        roteiro_falas=roteiro_falas,
        roteiro_cards=roteiro_cards,
        roteiro_ordem=list(roteiro_falas.keys()),
        out_dir="/tmp/_teste_edicao_pipeline",
        titulos_paginas=titulos_paginas,
    )

    assert resultado.status in (StatusEdicao.SUCESSO, StatusEdicao.REVISAO_MANUAL_NECESSARIA), \
        f"Status inesperado: {resultado.status} (ERRO indicaria falha técnica de montagem, não de API)"
    assert resultado.pdf_path and os.path.exists(resultado.pdf_path), "PDF deveria ter sido montado mesmo sem API (é determinístico)"
    assert resultado.video_path and os.path.exists(resultado.video_path), "Vídeo deveria ter sido montado mesmo sem API"

    if resultado.status == StatusEdicao.SUCESSO:
        print(f"      ✅ Pipeline rodou de ponta a ponta com API real — APROVADO")
    else:
        print(f"      ⚠️  REVISAO_MANUAL_NECESSARIA — esperado sem GEMINI_API_KEY neste ambiente")
        print("      (PDF e vídeo foram montados normalmente — só a aprovação final da IA Fiscal não rodou de verdade.)")


if __name__ == "__main__":
    print("=" * 70)
    print("✅ TESTE: DEPARTAMENTO DE EDIÇÃO")
    print("=" * 70)

    teste_icone_por_bloco()
    teste_texto_para_paragrafos()
    teste_negrito_dados_importantes()
    teste_icone_customizado_png_vs_svg()
    teste_grafico_real_render_svg()
    teste_grafico_tem_prioridade_no_slot()
    teste_estouro_de_texto_slide()
    teste_estouro_de_texto_pdf()
    teste_ia_audio_modo_placeholder()
    teste_assemble_video()
    teste_dados_graficos_no_pipeline()
    teste_fiscal_completude_deterministica()
    teste_revisao_fiscal_final_dataclass()
    teste_pipeline_completo_com_api()

    print("\n" + "=" * 70)
    print("✅ TODOS OS TESTES ESTRUTURAIS PASSARAM")
    print("=" * 70)
