"""
Departamento de Edição - Gráfico de Dados Real

O roteiro de vídeo (dp-02, ver VOICE_RULES_ROTEIRO em templates.py) tem uma
regra de voz explícita: "Nunca usa 'como podemos ver no gráfico'. Fala o
dado direto — o slide já mostra o gráfico." Até 05/09/2026 isso não era bem
verdade — o slide só desenhava um ÍCONE decorativo (icons.py), sem nenhum
número real do cliente plotado.

Este módulo resolve isso pros blocos que comparam valores numéricos de
verdade (decisão do analista, 05/09/2026): RESULTADO FINANCEIRO,
COMPARATIVO (Diagnóstico), COMPARATIVO FINANCEIRO e COMPARATIVO DE VENDAS
(Mensalidade) — ver BLOCOS_COM_GRAFICO_REAL em design_config.py. Os demais
blocos (Status, Marketing, Prioridades etc.) continuam com o ícone
temático normal — não têm um número comparável limpo o suficiente pra
virar barra sem forçar a barra.

100% determinístico — nenhuma IA aqui, só desenho a partir de números já
prontos (a mesma regra do resto do pipeline: "nunca inventa dado"). Quem
monta o slide (hoje, os testes; futuro, o app.py que lê
dados_motor['financial'] / dados_motor['comparatives'] direto do motor de
diagnóstico/mensalidade do dp-01) é quem calcula e entrega os valores —
este módulo só recebe e desenha.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import html as html_lib

from .design_config import FINSPOTS_COLORS

# Cinza-azulado neutro pro valor "anterior"/"comparação" — não compete
# visualmente com o laranja (que já é o destaque de marca em toda a peça).
_COR_COMPARACAO_PADRAO = "#5A6B8C"


@dataclass
class BarraGrafico:
    """Uma barra do gráfico: um rótulo + um valor (e, opcionalmente, um valor de comparação ao lado)."""

    rotulo: str
    valor: float
    valor_comparacao: Optional[float] = None  # se vier, desenha o par (ex.: mês atual vs mês anterior)
    cor: Optional[str] = None  # None = laranja padrão (FINSPOTS_COLORS['laranja'])


@dataclass
class DadosGrafico:
    """
    Conteúdo determinístico de um gráfico de barras pro slide de vídeo.
    formato_valor controla só a formatação do número acima de cada barra:
    "moeda" -> "R$ 48.200", "percentual" -> "20%", "numero" -> "4".
    """

    barras: List[BarraGrafico] = field(default_factory=list)
    formato_valor: str = "moeda"  # "moeda" | "percentual" | "numero"
    legenda_atual: str = "Atual"
    legenda_comparacao: str = "Anterior"


def _formatar_valor(valor: float, formato_valor: str) -> str:
    if formato_valor == "percentual":
        return f"{valor:.0f}%"
    if formato_valor == "numero":
        return f"{valor:.0f}".replace(".", ",")
    # moeda — separador de milhar "." e sem casas decimais (valores de slide são sempre arredondados)
    texto = f"{abs(valor):,.0f}".replace(",", "_").replace(".", ",").replace("_", ".")
    sinal = "-" if valor < 0 else ""
    return f"{sinal}R$ {texto}"


def render_grafico_svg(dados: DadosGrafico, largura: int = 460, altura: int = 460) -> str:
    """
    SVG de barras verticais — mesma filosofia de icons.py (SVG inline, sem
    dependência externa tipo matplotlib), no mesmo slot/tamanho onde o
    ícone temático ficava (ver DESIGN_VIDEO['icone'] em design_config.py),
    então não precisa de nenhum CSS novo em slide_template.py.

    Escala automaticamente pelo maior valor absoluto entre todas as barras
    (incluindo os valores de comparação, se houver) — nunca corta barra.
    Se não tiver nenhuma barra, retorna string vazia (quem chama decide o
    fallback, igual ícone customizado ausente cai no SVG interno).
    """
    if not dados.barras:
        return ""

    todos_valores = [b.valor for b in dados.barras] + [
        b.valor_comparacao for b in dados.barras if b.valor_comparacao is not None
    ]
    maior_valor = max([abs(v) for v in todos_valores] or [1]) or 1

    tem_comparacao = any(b.valor_comparacao is not None for b in dados.barras)
    n = len(dados.barras)

    margem_esquerda, margem_direita = 10, 10
    margem_topo = 46  # espaço pra legenda (se tiver) + valor numérico acima da barra
    margem_base = 56  # espaço pro rótulo embaixo da barra
    area_largura = largura - margem_esquerda - margem_direita
    area_altura = altura - margem_topo - margem_base

    grupo_largura = area_largura / n
    largura_barra = grupo_largura * (0.32 if tem_comparacao else 0.5)
    espaco_par = grupo_largura * 0.06

    cor_atual_padrao = FINSPOTS_COLORS["laranja"]
    linha_base_y = margem_topo + area_altura

    def _barra_svg(valor: float, x: float, cor: str) -> str:
        h = max((abs(valor) / maior_valor) * area_altura, 4.0)
        y = linha_base_y - h
        texto_valor = html_lib.escape(_formatar_valor(valor, dados.formato_valor))
        return (
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{largura_barra:.1f}" height="{h:.1f}" rx="6" fill="{cor}"/>'
            f'<text x="{x + largura_barra / 2:.1f}" y="{y - 10:.1f}" text-anchor="middle" '
            f'font-size="20" font-weight="700" fill="#FFFFFF">{texto_valor}</text>'
        )

    partes: List[str] = []
    for i, b in enumerate(dados.barras):
        centro = margem_esquerda + grupo_largura * i + grupo_largura / 2
        cor_barra = b.cor or cor_atual_padrao

        if tem_comparacao:
            x_anterior = centro - largura_barra - espaco_par / 2
            x_atual = centro + espaco_par / 2
            if b.valor_comparacao is not None:
                partes.append(_barra_svg(b.valor_comparacao, x_anterior, _COR_COMPARACAO_PADRAO))
            partes.append(_barra_svg(b.valor, x_atual, cor_barra))
        else:
            partes.append(_barra_svg(b.valor, centro - largura_barra / 2, cor_barra))

        partes.append(
            f'<text x="{centro:.1f}" y="{altura - margem_base + 28:.1f}" text-anchor="middle" '
            f'font-size="19" font-weight="600" fill="#FFFFFF" fill-opacity="0.85">'
            f'{html_lib.escape(b.rotulo)}</text>'
        )

    legenda_svg = ""
    if tem_comparacao:
        legenda_svg = (
            f'<rect x="{largura - 190}" y="8" width="16" height="16" rx="3" fill="{_COR_COMPARACAO_PADRAO}"/>'
            f'<text x="{largura - 168}" y="21" font-size="16" fill="#FFFFFF" fill-opacity="0.85">'
            f'{html_lib.escape(dados.legenda_comparacao)}</text>'
            f'<rect x="{largura - 88}" y="8" width="16" height="16" rx="3" fill="{cor_atual_padrao}"/>'
            f'<text x="{largura - 66}" y="21" font-size="16" fill="#FFFFFF" fill-opacity="0.85">'
            f'{html_lib.escape(dados.legenda_atual)}</text>'
        )

    return (
        f'<svg viewBox="0 0 {largura} {altura}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%">'
        f'<line x1="{margem_esquerda}" y1="{linha_base_y:.1f}" x2="{largura - margem_direita}" y2="{linha_base_y:.1f}" '
        f'stroke="#FFFFFF" stroke-opacity="0.25" stroke-width="2"/>'
        f'{"".join(partes)}'
        f'{legenda_svg}'
        f'</svg>'
    )
