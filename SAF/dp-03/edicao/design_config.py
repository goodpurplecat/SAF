"""
Departamento de Edição - Design Config
Fonte da verdade visual do PDF e do vídeo, alinhada ao Guia de Marca Finspots
v3.1 (Maio/2026) e ao exemplo de slide aprovado pelo analista em 04-05/09/2026.

Este arquivo substitui o design_config.py de uma versão anterior do projeto
(mantido como referência técnica — resolução, timings, especificação de
ffmpeg) com os ajustes confirmados pelo analista:
- Fundo do vídeo: degradê preto → #01184b (não #020B3B como na versão
  anterior — correção explícita do analista).
- Card de título: pill laranja com texto escuro (estilo do exemplo
  aprovado), não o "card branco com borda esquerda" da versão anterior.
- Ícone temático por bloco mantido (engrenagem, gráfico, balança, etc.),
  mas renderizado sólido (100% opacidade), não em 25% de opacidade atrás
  do texto como na versão anterior.
"""

# ==================== PALETA FINSPOTS OFICIAL (Guia de Marca v3.1) ====================

FINSPOTS_COLORS = {
    "laranja": "#FF5500",       # Cor principal — destaques, CTAs, pill de título
    "azul_escuro": "#020B3B",   # Cor de apoio — fundos claros/PDF, seriedade
    "quase_preto": "#00031B",   # Textos, contraste máximo
    "branco": "#FFFFFF",        # Textos sobre fundo escuro

    # Semáforos (status de saúde) — mesmos valores usados nos motores
    "critico": "#E74C3C",
    "ruim": "#E67E22",
    "atencao": "#F39C12",
    "saudavel": "#27AE60",
}

FONT_FAMILY = "'Poppins', 'Montserrat', 'Arial', sans-serif"  # Poppins confirmada instalada no ambiente de render

# ==================== DESIGN DO VÍDEO (slides) ====================
# Fundo escuro em degradê + pill laranja de título + corpo branco + ícone sólido.

DESIGN_VIDEO = {
    "gradiente": {
        "inicio": "#000000",
        "fim": "#01184b",         # CORREÇÃO do analista (04/09/2026) — não é #020B3B
        "angulo_graus": 135,      # diagonal, escuro no topo-esquerdo → azul no canto inferior-direito
    },
    "pill_titulo": {
        # AJUSTE do analista (05/09/2026): antes usava FINSPOTS_COLORS['laranja']
        # (#FF5500, de propósito um pouco mais escuro que o ícone, pra
        # "equilíbrio visual" — ver comentário antigo em icone.cor). O
        # analista pediu o oposto agora: mesmo tom do ícone (#FF7A00) pra
        # ficar uniforme no card.
        "fundo": "#FF7A00",
        "texto_cor": FINSPOTS_COLORS["azul_escuro"],
        "formato": "flag",        # bleed à esquerda, arredondado só do lado direito (ver slide_template.py)
        "font_size_px": 46,
        "font_weight": 700,
    },
    "corpo": {
        "cor": FINSPOTS_COLORS["branco"],
        "font_size_px": 36,
        "font_weight": 400,
        "line_height": 1.45,
        "max_largura_pct": 56,    # % da largura do frame
    },
    "numero_destaque": {
        "cor": FINSPOTS_COLORS["laranja"],
        "font_weight": 700,
    },
    "icone": {
        "cor": "#FF7A00",         # mesmo tom do pill_titulo (ver acima) — uniforme no card, pedido do analista (05/09/2026)
        "opacidade": 1.0,         # CORREÇÃO do analista — sólido, não 25%
        "largura_px": 460,        # AJUSTE do analista — ícone maior
        "posicao": {"x_pct": 78, "y_pct": 50},  # AJUSTE do analista — centralizado verticalmente no lado direito do card
    },
    "logo": {
        "posicao": "inferior_direita",
        "altura_px": 42,
        "margem_px": 56,
    },
}

# ==================== DESIGN DO RELATÓRIO PDF ====================
# PDF formal — fundo branco, texto escuro, acentos laranja/azul (Guia de Marca, regra prática:
# "fundo padrão é escuro" vale pra vídeo/site; o PDF interno usa Arial/fundo claro por legibilidade impressa).

DESIGN_PDF = {
    "fundo_pagina": "#FFFFFF",
    "texto_corpo": FINSPOTS_COLORS["quase_preto"],
    "titulo_principal": {"cor": FINSPOTS_COLORS["azul_escuro"], "font_size_pt": 24, "font_weight": 700},
    "titulo_secao": {"cor": FINSPOTS_COLORS["laranja"], "font_size_pt": 16, "font_weight": 700},
    "corpo": {"cor": FINSPOTS_COLORS["quase_preto"], "font_size_pt": 11, "font_weight": 400, "line_height": 1.5},
    "rodape": {"cor": "#999999", "font_size_pt": 9},
    "fundo_card": "#F8F9FA",
    "acento": FINSPOTS_COLORS["laranja"],
    "header": {
        "altura_cm": 2,
        "borda_inferior": f"2px solid {FINSPOTS_COLORS['laranja']}",
    },
    "footer": {
        "altura_cm": 1.5,
        "texto": "Dúvidas? WhatsApp: (62) 9 9667-7168 | Finspots — Análise Financeira para E-commerce",
    },
    "font_family_pdf": "'Arial', 'Poppins', sans-serif",  # Arial como padrão em PDFs gerados internamente (Guia de Marca)
}

# ==================== SEMÁFOROS ====================

# Usado pelo dp-02 (IA de Relatório e Roteiro) no placeholder "[🟡 ATENÇÃO /
# 🟠 RUIM / 🟢 SAUDÁVEL / 🔴 CRÍTICO]" — o emoji real do status do cliente
# entra direto no texto do card/fala aprovado. Confirmado pelo analista
# (05/09/2026): fica só no texto — o slot do ícone do slide continua sendo
# sempre uma imagem/desenho (PNG customizado ou SVG interno, nunca o emoji).
SEMAFORO_EMOJI = {
    "critico": "🔴",
    "ruim": "🟠",
    "atencao": "🟡",
    "saudavel": "🟢",
}

# ==================== ÍCONE TEMÁTICO POR BLOCO ====================
# Mantido da versão anterior (design_config.py) — mapeia cada bloco do
# roteiro/relatório a um ícone temático. Ver icons.py pros SVGs sólidos.

ICONE_POR_BLOCO = {
    # Diagnóstico
    "STATUS GERAL": "engrenagem",
    "RESULTADO FINANCEIRO": "grafico_barras",
    "CUSTOS E CANAIS": "balanca",
    "CANAIS DE VENDA": "distribuicao",
    "MARKETING": "alvo",
    "COMPARATIVO": "grafico_linha",
    "PRIORIDADES": "foguete",
    "ENCERRAMENTO": "mira",
    "INTRO": "mira",
    # Mensalidade
    "STATUS DO MÊS": "engrenagem",
    "CANAIS DO MÊS": "distribuicao",
    "PRODUTOS DO MÊS": "grafico_barras",
    "CLIENTES E MARKETING": "alvo",
    "COMPARATIVO FINANCEIRO": "grafico_linha",
    "COMPARATIVO DE VENDAS": "grafico_linha",
    "PRIORIDADES DO MÊS": "foguete",
}

DEFAULT_ICONE = "grafico_barras"

# ==================== BLOCOS COM GRÁFICO REAL ====================
# Blocos que comparam número de verdade (decisão do analista, 05/09/2026,
# depois de notar que o roteiro já presume "o slide mostra o gráfico" — ver
# VOICE_RULES_ROTEIRO no dp-02): aqui entra um gráfico de barras desenhado
# a partir dos dados do motor (ver graficos.py), não o ícone decorativo.
# Os demais blocos (Status, Marketing, Prioridades etc.) continuam com o
# ícone temático normal — não têm um número comparável limpo o suficiente
# pra virar barra sem forçar. Isto é só documentação/orientação pra quem
# monta os dados do slide (hoje os testes, no futuro o app.py) — o
# slide_template.py em si não obriga nada: se vier `dados_grafico`
# preenchido pra qualquer bloco, ele desenha; se não vier, cai no ícone.
BLOCOS_COM_GRAFICO_REAL = {
    "RESULTADO FINANCEIRO",
    "COMPARATIVO",
    "COMPARATIVO FINANCEIRO",
    "COMPARATIVO DE VENDAS",
}


def bloco_tem_grafico_recomendado(nome_bloco: str) -> bool:
    """Mesma lógica de casamento de icone_para_bloco(), mas pra saber se o bloco é candidato a gráfico real."""
    nome_upper = nome_bloco.upper()
    return any(chave in nome_upper for chave in BLOCOS_COM_GRAFICO_REAL)


def icone_para_bloco(nome_bloco: str) -> str:
    """Casa o nome do bloco (pode ter sufixo tipo 'BLOCO 1 — ') com o mapeamento acima."""
    nome_upper = nome_bloco.upper()
    for chave, icone in ICONE_POR_BLOCO.items():
        if chave in nome_upper:
            return icone
    return DEFAULT_ICONE


# ==================== ESPECIFICAÇÃO DO VÍDEO FINAL ====================

VIDEO_SPEC = {
    "resolucao": (1920, 1080),
    "framerate": 30,
    "codec_video": "libx264",
    "codec_audio": "aac",
    "bitrate_video": "5000k",
    "bitrate_audio": "128k",
    "formato_saida": "mp4",
}

TRANSICOES = {
    "tipo": "fade",
    "duracao_slide_s": 0.5,   # fade in/out entre slides
    "duracao_geral_s": 1.0,   # fade in do início / fade out do final do vídeo inteiro
}

AUDIO_CONFIG = {
    "narracao": {"idioma": "pt-BR", "volume_db": 0},
    "musica_background": {
        "volume_pct": 17,     # 15-20%, ponto médio
        "fade_in_s": 2,
        "fade_out_s": 3,
    },
}
