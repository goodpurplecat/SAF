"""Helpers de texto compartilhados entre o template do slide e o do PDF."""

import html as html_lib
import re

# Destaque automático de dado importante (pedido do analista, 05/09/2026:
# "coloca em negrito o que for importante" no card do slide). Determinístico
# — regex, não IA — então continua no espírito do dp-03 de não reescrever
# nada, só formata o que já está no texto aprovado. Cobre os 3 formatos de
# número que carregam o "dado concreto" da voz Finspots: moeda, percentual
# e múltiplo (ex: LTV:CAC "11,9x").
_PADRAO_MOEDA = r"R\$\s?\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?"
_PADRAO_PERCENTUAL = r"\d{1,3}(?:,\d{1,2})?%"
_PADRAO_MULTIPLICADOR = r"\d+(?:,\d+)?x\b"
_REGEX_DESTAQUE = re.compile(f"({_PADRAO_MOEDA}|{_PADRAO_PERCENTUAL}|{_PADRAO_MULTIPLICADOR})")


def destacar_dados_importantes(texto_escapado: str) -> str:
    """
    Envolve valores em R$, percentuais e múltiplos (ex: "11,9x") em
    <strong>. Espera texto JÁ escapado (html.escape) — os caracteres desses
    padrões (dígitos, R$, %, x, . ,) não são afetados pelo escape, então é
    seguro rodar depois, sem risco de quebrar tag nem escapar duas vezes.
    """
    return _REGEX_DESTAQUE.sub(r"<strong>\1</strong>", texto_escapado)


def texto_para_paragrafos(texto: str, tag: str = "p", negrito_dados: bool = False) -> str:
    """
    Converte texto em tags HTML, escapando o conteúdo:
    - Parágrafos separados por linha em branco (\n\n) viram tags <tag> separadas.
    - Quebras de linha simples dentro de um parágrafo (comuns nos formatos
      "Receita Líquida: R$ ___" / "Lucro Líquido: R$ ___" linha a linha dos
      guias) viram <br>, preservando o formato original em vez de colapsar
      tudo numa linha só.
    - negrito_dados: se True, destaca automaticamente R$/%/múltiplos em
      negrito (ver destacar_dados_importantes) — usado no card do slide,
      onde o texto é curto e o dado principal deve saltar aos olhos.
    """
    blocos = [b.strip("\n") for b in texto.strip().split("\n\n") if b.strip()]
    if not blocos:
        blocos = [texto.strip()]

    partes = []
    for bloco in blocos:
        linhas = [html_lib.escape(linha) for linha in bloco.split("\n")]
        if negrito_dados:
            linhas = [destacar_dados_importantes(linha) for linha in linhas]
        conteudo = "<br>".join(linhas)
        partes.append(f"<{tag}>{conteudo}</{tag}>")
    return "\n".join(partes)
