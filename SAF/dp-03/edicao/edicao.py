"""
Departamento de Edição
"APP Intermediador" do fluxograma do analista (04-05/09/2026): pega o
relatório + roteiro já aprovados pela Produção (dp-02) e monta os dois
entregáveis de verdade — o PDF pronto e o vídeo MP4 pronto — na identidade
visual fixa da Finspots, depois manda pra IA Fiscal de Produção conferir a
montagem antes de considerar pronto pro cliente.

Fluxo (espelha o fluxograma enviado pelo analista):

    relatório + roteiro APROVADOS pela Produção (dp-02)
                    │
                    ▼
         APP Intermediador (esta classe)
         separa o conteúdo pra edição
           │                        │
           ▼                        ▼
    App de Formatação        IA de Áudio → App de Slides → IA Editora
    (PDF, mini Canva)         (vídeo: narração + card + música + fades)
           │                        │
           └───────────┬────────────┘
                        ▼
             IA Fiscal de Produção
             compara os dois conteúdos MONTADOS com os roteiros aprovados
                        │
              aprovado? ──não──> REVISAO_MANUAL_NECESSARIA
                        │
                       sim
                        ▼
                    SUCESSO

Decisão de design importante (documentada porque não é óbvia): ao contrário
do dp-02, este departamento NÃO tenta corrigir-e-regerar quando a IA Fiscal
reprova. O texto já foi aprovado pela Produção — este departamento não tem
autorização pra reescrever nada. A montagem (render HTML→PNG/PDF, ffmpeg) é
100% determinística: rodar de novo com o mesmo texto dá o mesmo resultado.
Então, se a Fiscal reprova por completude/estouro/coerência, isso é sempre
REVISAO_MANUAL_NECESSARIA — a única coisa que este departamento tenta de
novo automaticamente são FALHAS TÉCNICAS transitórias (Playwright/ffmpeg
travando, subprocess derrubado) via `max_tentativas_tecnicas`; se isso
esgotar, o status é ERRO (falha de infraestrutura, não de conteúdo).
"""

import re
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .audio_generator import IAAudio
from .design_config import icone_para_bloco
from .fiscal_producao_final import IAFiscalProducaoFinal
from .graficos import DadosGrafico
from .models import ResultadoEdicao, SlideRenderizado, StatusEdicao
from .pdf_template import (
    LIMITE_INFERIOR_CONTEUDO_PX,
    PAGE_HEIGHT_PX,
    PAGE_WIDTH_PX,
    SELETOR_CONTEUDO,
    build_pdf_capa_html,
    build_pdf_page_html,
)
from .slide_template import LIMITE_INFERIOR_CORPO_PX, LIMITE_SUPERIOR_CORPO_PX, SELETOR_CORPO, build_slide_html
from .video_assembler import assemble_video
from . import renderer


def _slug(texto: str) -> str:
    """'Resultado Financeiro' -> 'resultado_financeiro' (nomes de arquivo previsíveis)."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_") or "bloco"


class DepartamentoEdicao:
    """Orquestra o App de Formatação (PDF) + a IA de Áudio/Slides/Editora (vídeo) + a IA Fiscal de Produção."""

    def __init__(
        self,
        max_tentativas_tecnicas: int = 2,
        musica_path: Optional[str] = None,
        logo_path: Optional[str] = None,
    ):
        """
        musica_path / logo_path: se None, usam os padrões já configurados
        (ver design_config.AUDIO_CONFIG e slide_template.LOGO_PADRAO /
        pdf_template.LOGO_PADRAO_*) — passar aqui só pra sobrescrever.
        """
        self.audio = IAAudio()
        self.fiscal = IAFiscalProducaoFinal()
        self.max_tentativas_tecnicas = max_tentativas_tecnicas
        self.musica_path = musica_path
        self.logo_path = logo_path

    def processar(
        self,
        tipo_produto: str,
        cliente: Dict[str, Any],
        relatorio_paginas: Dict[int, str],
        roteiro_falas: Dict[str, str],
        roteiro_cards: Dict[str, str],
        roteiro_ordem: Optional[List[str]],
        out_dir: str,
        titulos_paginas: Optional[Dict[int, str]] = None,
        dados_graficos: Optional[Dict[str, DadosGrafico]] = None,
    ) -> ResultadoEdicao:
        """
        tipo_produto: "Diagnóstico" ou "Mensalidade" (mesmo texto usado no dp-02).
        cliente: precisa de 'nome_loja' e 'periodo' (Diagnóstico) ou 'mes_ano'
            (Mensalidade); opcionalmente 'subtitulo_produto' e 'data_entrega'.
        relatorio_paginas: RelatorioTexto.paginas aprovado pelo dp-02 (número → texto do corpo).
        roteiro_falas: RoteiroTexto.blocos aprovado pelo dp-02 (nome do bloco →
            FALA completa) — vai pra IA de Áudio (narração/duração do slide).
        roteiro_cards: RoteiroTexto.blocos_card aprovado pelo dp-02 (nome do
            bloco → texto CURTO do card) — vai pro corpo de texto do slide
            (decisão do analista, 05/09/2026: card curto na tela em vez de
            repetir a fala inteira, pra não sobrecarregar visualmente um
            template de tamanho fixo).
        roteiro_ordem: RoteiroTexto.ordem_blocos aprovado; se None, usa a ordem de roteiro_falas.
        out_dir: pasta onde tudo é escrito (slides/, audio/, pdf/, video/).
        titulos_paginas: {número → título da seção}, vindo da spec de páginas
            do dp-02 (`producao.templates.paginas_do_produto(tipo_produto)`,
            campo 'titulo') — o texto aprovado é só o corpo, o título da
            página vive na spec, não no texto gerado. Este departamento não
            importa o dp-02 diretamente (fica desacoplado, mesmo padrão de
            fronteira usado entre dp-01/dp-02/motor), então quem chama passa
            os títulos prontos; se não vier, cai num fallback best-effort
            (ver _extrair_titulo_secao) — só pra este departamento continuar
            testável sozinho.
        dados_graficos: {nome do bloco → graficos.DadosGrafico}, opcional —
            gráfico de barras REAL (números do motor, não texto) pros
            blocos que comparam valor de verdade (ver
            design_config.BLOCOS_COM_GRAFICO_REAL: RESULTADO FINANCEIRO,
            COMPARATIVO, COMPARATIVO FINANCEIRO, COMPARATIVO DE VENDAS —
            decisão do analista, 05/09/2026). Este departamento não calcula
            os números sozinho (não tem acesso ao motor do dp-01, mesma
            fronteira de sempre) — quem chama monta o DadosGrafico a partir
            de dados_motor['financial']/['comparatives'] e passa pronto
            aqui. Bloco sem entrada neste dict cai no ícone temático normal
            (icone_para_bloco) — nada quebra se vier None ou incompleto.
        """
        print("\n" + "=" * 60)
        print("🎬 DEPARTAMENTO DE EDIÇÃO")
        print("=" * 60)

        ordem = roteiro_ordem or list(roteiro_falas.keys())
        out = Path(out_dir)

        for tentativa in range(1, self.max_tentativas_tecnicas + 1):
            print(f"\n[Tentativa técnica {tentativa}/{self.max_tentativas_tecnicas}]")
            try:
                slides, falas_montado, cards_montado, estouros_video = self._montar_video_slides(
                    ordem, roteiro_falas, roteiro_cards, out, dados_graficos
                )
                video_path = self._montar_video_final(slides, out)
                paginas_html, relatorio_montado, estouros_pdf = self._montar_pdf_paginas(
                    tipo_produto, cliente, relatorio_paginas, out, titulos_paginas
                )
                pdf_path = self._montar_pdf_final(paginas_html, out)
                break
            except Exception as e:
                print(f"  ⚠️  Falha técnica na montagem: {e}")
                if tentativa == self.max_tentativas_tecnicas:
                    print(f"\n🔴 ESGOTADAS {self.max_tentativas_tecnicas} TENTATIVAS TÉCNICAS — erro de infraestrutura.")
                    return ResultadoEdicao(
                        status=StatusEdicao.ERRO,
                        tipo_produto=tipo_produto,
                        cliente_nome=cliente.get("nome_loja", ""),
                        tentativas=tentativa,
                        timestamp=datetime.now().isoformat(),
                    )
                print("  🔁 Tentando montar de novo (falha parece transitória)...")

        estouros = estouros_video + estouros_pdf
        print(f"\n✅ Montagem concluída — {len(slides)} slide(s), {len(paginas_html)} página(s) de PDF"
              f"{f', {len(estouros)} estouro(s) de texto detectado(s)' if estouros else ''}.")

        print("\n🔍 IA Fiscal de Produção: comparando conteúdo montado com o aprovado...")
        revisao = self.fiscal.revisar(
            tipo_produto=tipo_produto,
            cliente=cliente,
            roteiro_falas_aprovado=roteiro_falas,
            roteiro_falas_montado=falas_montado,
            roteiro_cards_aprovado=roteiro_cards,
            roteiro_cards_montado=cards_montado,
            relatorio_aprovado=relatorio_paginas,
            relatorio_montado=relatorio_montado,
            estouros_detectados=estouros,
        )
        print(f"   → {'APROVADO' if revisao.aprovado else 'NÃO APROVADO'} "
              f"({len(revisao.bloqueadores)} bloqueador(es), {len(revisao.ajustes)} ajuste(s)))")

        if revisao.aprovado:
            print("\n✅ PDF e vídeo finais aprovados — prontos pro cliente.")
            return ResultadoEdicao(
                status=StatusEdicao.SUCESSO,
                tipo_produto=tipo_produto,
                cliente_nome=cliente.get("nome_loja", ""),
                pdf_path=pdf_path,
                video_path=video_path,
                slides=slides,
                revisao_fiscal_final=revisao,
                tentativas=tentativa,
                timestamp=datetime.now().isoformat(),
            )

        print("\n🔴 REPROVADO pela IA Fiscal de Produção — revisão manual necessária "
              "(conteúdo já aprovado pelo dp-02; este departamento não reescreve).")
        return ResultadoEdicao(
            status=StatusEdicao.REVISAO_MANUAL_NECESSARIA,
            tipo_produto=tipo_produto,
            cliente_nome=cliente.get("nome_loja", ""),
            pdf_path=pdf_path,
            video_path=video_path,
            slides=slides,
            revisao_fiscal_final=revisao,
            tentativas=tentativa,
            timestamp=datetime.now().isoformat(),
        )

    # ------------------------------------------------------------------
    # Vídeo: App de Slides + IA de Áudio + IA Editora
    # ------------------------------------------------------------------

    def _montar_video_slides(
        self,
        ordem: List[str],
        roteiro_falas: Dict[str, str],
        roteiro_cards: Dict[str, str],
        out: Path,
        dados_graficos: Optional[Dict[str, DadosGrafico]] = None,
    ) -> "tuple[List[SlideRenderizado], Dict[str, str], Dict[str, str], List[str]]":
        """
        Dois textos por bloco: a FALA completa vai pra IA de Áudio (narração
        + duração do slide); o CARD curto vai pro corpo de texto do slide
        (ver processar()). Se um bloco não tiver card explícito (não deveria
        acontecer com o dp-02 novo, mas evita quebrar o pipeline), cai na
        fala completa como último recurso — a detecção de estouro pega o
        resto.

        dados_graficos: casamento por nome EXATO do bloco (mesma chave de
        roteiro_falas/roteiro_cards) — ao contrário de icone_para_bloco()
        (que casa por substring pra aceitar prefixo tipo "BLOCO 1 — "),
        aqui é exato porque quem monta dados_graficos já está iterando os
        mesmos nomes de roteiro_falas, então não tem ambiguidade a resolver.
        """
        dir_slides = out / "slides"
        dir_audio = out / "audio"
        dir_slides.mkdir(parents=True, exist_ok=True)
        dir_audio.mkdir(parents=True, exist_ok=True)

        slides: List[SlideRenderizado] = []
        falas_montado: Dict[str, str] = {}
        cards_montado: Dict[str, str] = {}
        estouros: List[str] = []

        for i, nome_bloco in enumerate(ordem):
            fala = roteiro_falas.get(nome_bloco, "")
            texto_card = roteiro_cards.get(nome_bloco) or fala
            falas_montado[nome_bloco] = fala
            cards_montado[nome_bloco] = texto_card
            slug = f"{i:02d}_{_slug(nome_bloco)}"

            icone = icone_para_bloco(nome_bloco)
            grafico = (dados_graficos or {}).get(nome_bloco)
            html = build_slide_html(
                titulo=nome_bloco, corpo_texto=texto_card, icone_nome=icone,
                logo_path=self.logo_path, dados_grafico=grafico,
            )

            imagem_path = dir_slides / f"{slug}.png"
            _, dentro_do_limite, _ = renderer.render_html_to_png_com_medicao(
                html, imagem_path, SELETOR_CORPO, LIMITE_INFERIOR_CORPO_PX,
                limite_top_px=LIMITE_SUPERIOR_CORPO_PX,
            )
            if not dentro_do_limite:
                estouros.append(f"Bloco '{nome_bloco}' (slide de vídeo)")

            audio_path = dir_audio / f"{slug}.mp3"
            duracao = self.audio.gerar_audio_bloco(fala, str(audio_path))

            slides.append(SlideRenderizado(
                bloco_nome=nome_bloco,
                imagem_path=str(imagem_path),
                audio_path=str(audio_path),
                duracao_segundos=duracao,
            ))

        return slides, falas_montado, cards_montado, estouros

    def _montar_video_final(self, slides: List[SlideRenderizado], out: Path) -> str:
        dir_video = out / "video"
        dir_video.mkdir(parents=True, exist_ok=True)
        return assemble_video(slides, str(dir_video / "video_final.mp4"), musica_path=self.musica_path)

    # ------------------------------------------------------------------
    # PDF: App de Formatação
    # ------------------------------------------------------------------

    def _montar_pdf_paginas(
        self,
        tipo_produto: str,
        cliente: Dict[str, Any],
        relatorio_paginas: Dict[int, str],
        out: Path,
        titulos_paginas: Optional[Dict[int, str]] = None,
    ) -> "tuple[List[str], Dict[int, str], List[str]]":
        dir_pdf = out / "pdf"
        dir_pdf.mkdir(parents=True, exist_ok=True)

        nome_loja = cliente.get("nome_loja", "")
        periodo_ou_mes = cliente.get("periodo") or cliente.get("mes_ano", "")
        subtitulo_produto = cliente.get("subtitulo_produto") or f"{tipo_produto} Financeiro"
        data_entrega = cliente.get("data_entrega") or datetime.now().strftime("%d/%m/%Y")

        capa_html = build_pdf_capa_html(
            nome_loja=nome_loja,
            subtitulo_produto=subtitulo_produto,
            periodo_ou_mes=periodo_ou_mes,
            data_entrega=data_entrega,
            logo_path=self.logo_path,
        )
        paginas_html = [capa_html]
        relatorio_montado: Dict[int, str] = {}
        estouros: List[str] = []

        numeros_ordenados = sorted(relatorio_paginas.keys())
        ultima_pagina = numeros_ordenados[-1] if numeros_ordenados else None

        with tempfile.TemporaryDirectory() as tmp_checagem:
            for numero in numeros_ordenados:
                texto = relatorio_paginas[numero]
                relatorio_montado[numero] = texto
                titulo_secao = (titulos_paginas or {}).get(numero) or self._extrair_titulo_secao(texto, numero)

                pagina_html = build_pdf_page_html(
                    numero_pagina=numero,
                    titulo_secao=titulo_secao,
                    corpo_texto=texto,
                    nome_loja=nome_loja,
                    periodo_ou_mes=periodo_ou_mes,
                    logo_path=self.logo_path,
                    rodape_final=(numero == ultima_pagina),
                )
                paginas_html.append(pagina_html)

                # PNG só pra medir estouro de texto (checagem determinística
                # da IA Fiscal) — não faz parte do entregável, fica no tmp.
                _, dentro_do_limite, _ = renderer.render_html_to_png_com_medicao(
                    pagina_html, f"{tmp_checagem}/pagina_{numero:02d}.png",
                    SELETOR_CONTEUDO, LIMITE_INFERIOR_CONTEUDO_PX,
                    width=PAGE_WIDTH_PX, height=PAGE_HEIGHT_PX,
                )
                if not dentro_do_limite:
                    estouros.append(f"Página {numero} (relatório PDF)")

        return paginas_html, relatorio_montado, estouros

    def _montar_pdf_final(self, paginas_html: List[str], out: Path) -> str:
        dir_pdf = out / "pdf"
        dir_pdf.mkdir(parents=True, exist_ok=True)
        return renderer.render_html_pages_to_pdf(
            paginas_html, str(dir_pdf / "relatorio_final.pdf"),
            page_width_px=PAGE_WIDTH_PX, page_height_px=PAGE_HEIGHT_PX,
        )

    def _extrair_titulo_secao(self, texto: str, numero: int) -> str:
        """
        O texto aprovado pelo dp-02 não separa 'título' de 'corpo' — é um
        bloco de texto corrido por página. Usa a primeira linha não vazia
        como título da seção (padrão observado nos guias do dp-02, que
        sempre abrem a página com o nome do bloco em caixa alta/título).
        Se a primeira linha for longa demais pra um título (indício de que
        já é corpo de texto), cai num rótulo genérico em vez de forçar.
        """
        primeira_linha = next((l.strip() for l in texto.split("\n") if l.strip()), "")
        if primeira_linha and len(primeira_linha) <= 60:
            return primeira_linha
        return f"Página {numero}"
