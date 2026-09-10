"""
Departamento de Edição - Ícones
SVGs sólidos (100% opacidade, cor laranja Finspots) para o ícone temático de
cada bloco do slide de vídeo — ver ICONE_POR_BLOCO em design_config.py.

Estilo: geométrico, poucos traços, mesma linguagem visual do ícone de
gráfico-com-seta do exemplo aprovado pelo analista (barras + seta ascendente).
"""

from .design_config import FINSPOTS_COLORS

_LARANJA = FINSPOTS_COLORS["laranja"]


def _svg(viewbox: str, body: str, cor: str = _LARANJA) -> str:
    return f'<svg viewBox="{viewbox}" fill="none" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%">{body.replace("{cor}", cor)}</svg>'


def icone_grafico_barras(cor: str = _LARANJA) -> str:
    """Barras ascendentes + seta — o ícone do exemplo aprovado (Resultado Financeiro)."""
    return _svg(
        "0 0 200 200",
        """
        <rect x="20" y="120" width="28" height="60" rx="4" fill="{cor}"/>
        <rect x="70" y="90" width="28" height="90" rx="4" fill="{cor}"/>
        <rect x="120" y="55" width="28" height="125" rx="4" fill="{cor}"/>
        <path d="M15 100 L90 45 L120 65 L185 10" stroke="{cor}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M155 10 L185 10 L185 40" stroke="{cor}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        """,
        cor,
    )


def icone_engrenagem(cor: str = _LARANJA) -> str:
    return _svg(
        "0 0 200 200",
        """
        <path fill="{cor}" d="M100 60a40 40 0 100 80 40 40 0 000-80zm0 60a20 20 0 110-40 20 20 0 010 40z"/>
        <path fill="{cor}" d="M100 20l10 20-10 8-10-8zM100 180l-10-20 10-8 10 8zM20 100l20-10 8 10-8 10zM180 100l-20 10-8-10 8-10zM45 45l22 4 -2 12-22-4zM155 155l-22-4 2-12 22 4zM45 155l22-4 -2-12-22 4zM155 45l-22 4 2 12 22-4z"/>
        """,
        cor,
    )


def icone_balanca(cor: str = _LARANJA) -> str:
    return _svg(
        "0 0 200 200",
        """
        <rect x="94" y="20" width="12" height="130" fill="{cor}"/>
        <rect x="40" y="150" width="120" height="12" rx="4" fill="{cor}"/>
        <path d="M40 55 L60 55" stroke="{cor}" stroke-width="8"/>
        <path d="M140 55 L160 55" stroke="{cor}" stroke-width="8"/>
        <path d="M20 55 L180 55" stroke="{cor}" stroke-width="8" stroke-linecap="round"/>
        <path d="M20 55 L8 90a24 20 0 0024 20 24 20 0 0024-20z" fill="{cor}" opacity="0.85"/>
        <path d="M180 55 L168 90a24 20 0 0024 20 24 20 0 0024-20z" fill="{cor}" opacity="0.85"/>
        <circle cx="100" cy="20" r="10" fill="{cor}"/>
        """,
        cor,
    )


def icone_distribuicao(cor: str = _LARANJA) -> str:
    """Rede/distribuição — nós conectados (canais)."""
    return _svg(
        "0 0 200 200",
        """
        <circle cx="100" cy="30" r="18" fill="{cor}"/>
        <circle cx="30" cy="160" r="18" fill="{cor}"/>
        <circle cx="170" cy="160" r="18" fill="{cor}"/>
        <path d="M100 48 L30 142" stroke="{cor}" stroke-width="8"/>
        <path d="M100 48 L170 142" stroke="{cor}" stroke-width="8"/>
        <path d="M48 160 L152 160" stroke="{cor}" stroke-width="8"/>
        """,
        cor,
    )


def icone_alvo(cor: str = _LARANJA) -> str:
    """Bullseye — marketing/mira (também usado como padrão da marca)."""
    return _svg(
        "0 0 200 200",
        """
        <circle cx="100" cy="100" r="85" fill="none" stroke="{cor}" stroke-width="14"/>
        <circle cx="100" cy="100" r="50" fill="none" stroke="{cor}" stroke-width="14"/>
        <circle cx="100" cy="100" r="18" fill="{cor}"/>
        """,
        cor,
    )


def icone_grafico_linha(cor: str = _LARANJA) -> str:
    return _svg(
        "0 0 200 200",
        """
        <path d="M15 160 L15 30" stroke="{cor}" stroke-width="8" stroke-linecap="round"/>
        <path d="M15 160 L185 160" stroke="{cor}" stroke-width="8" stroke-linecap="round"/>
        <path d="M25 130 L70 90 L105 115 L180 40" stroke="{cor}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <circle cx="70" cy="90" r="9" fill="{cor}"/>
        <circle cx="105" cy="115" r="9" fill="{cor}"/>
        <circle cx="180" cy="40" r="9" fill="{cor}"/>
        """,
        cor,
    )


def icone_foguete(cor: str = _LARANJA) -> str:
    return _svg(
        "0 0 200 200",
        """
        <path d="M100 15c25 20 35 55 35 90 0 15-6 30-14 42l-42 0c-8-12-14-27-14-42 0-35 10-70 35-90z" fill="{cor}"/>
        <circle cx="100" cy="85" r="14" fill="#01184b"/>
        <path d="M65 120 L35 160 L65 150z" fill="{cor}"/>
        <path d="M135 120 L165 160 L135 150z" fill="{cor}"/>
        <path d="M90 165 L110 165 L100 190z" fill="{cor}" opacity="0.85"/>
        """,
        cor,
    )


def icone_mira(cor: str = _LARANJA) -> str:
    """Símbolo de mira da marca — usado na intro/encerramento (favicon Finspots)."""
    return _svg(
        "0 0 200 200",
        """
        <circle cx="100" cy="100" r="90" fill="{cor}"/>
        <circle cx="100" cy="100" r="34" fill="#01184b"/>
        """,
        cor,
    )


_ICONES = {
    "grafico_barras": icone_grafico_barras,
    "engrenagem": icone_engrenagem,
    "balanca": icone_balanca,
    "distribuicao": icone_distribuicao,
    "alvo": icone_alvo,
    "grafico_linha": icone_grafico_linha,
    "foguete": icone_foguete,
    "mira": icone_mira,
}


def render_icone(nome_icone: str, cor: str = _LARANJA) -> str:
    fn = _ICONES.get(nome_icone, icone_grafico_barras)
    return fn(cor)
