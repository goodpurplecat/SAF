"""
Departamento de Produção - Templates
Especificações página a página (relatório PDF) e bloco a bloco (roteiro de
vídeo), extraídas fielmente dos 4 guias da Gem fornecidos pelo analista:

- GUIA_DO_RELATÓRIO_PDF_DIAGNÓSTICO_FINSPOTS (v1.1, Maio/2026)
- GUIA_DO_RELATÓRIO_PDF_MENSALIDADE_FINSPOTS (v1.1, Maio/2026)
- GUIA_DO_ROTEIRO_DE_VÍDEO_DIAGNÓSTICO_FINSPOTS (v1.1, Maio/2026)
- GUIA_DO_ROTEIRO_DE_VÍDEO_MENSALIDADE_FINSPOTS (v1.1, Maio/2026)

Isso é dado, não prompt solto: a IA de Relatório e Roteiro monta o prompt
final concatenando essas specs com os dados do motor. Como o próprio
analista disse — "as regras são as mesmas o que realmente importa" — a
voz e a lógica de bloco (dado → interpretação → ação) são únicas; só a
estrutura de página/bloco muda entre Diagnóstico e Mensalidade, por isso
está tabelada aqui em vez de duplicada em duas classes de IA.
"""

from typing import Dict, Any, List


# ============================================================================
# REGRAS DE VOZ — COMPARTILHADAS ENTRE OS DOIS PRODUTOS
# ============================================================================

VOICE_RULES_RELATORIO = """
REGRAS DE VOZ FINSPOTS (relatório PDF) — seguir sempre, sem exceção:
- Começa pelo resultado, nunca pelo processo. ("Sua margem está em 18%" — não "calculamos a margem dividindo...")
- Dado concreto → interpretação → ação. Sempre nessa ordem.
- Frases curtas. Parágrafos curtos. Máximo 3 linhas por parágrafo.
- Nunca devolve a decisão pro cliente. Proibido: "faz sentido?", "o que você acha?", "fica à vontade", "se preferir", "você decide".
- Honesta mesmo quando o número dói. Se está ruim, diz que está ruim — com cuidado, mas diz.
- Termina sempre com ação. Cada bloco fecha com o que fazer.
- Nunca usa jargão sem explicar. Primeira vez que aparece um termo técnico (MC, ML, ROAS, CAC, LTV, Breakeven), explica em parênteses ou na frase seguinte.
- Nunca inventa dado. Se um campo estiver vazio/None nos dados recebidos, sinaliza isso explicitamente no texto — não preenche com um número chutado.
- Formatação: valores em R$ como `R$ 1.500,00` (ponto de milhar, vírgula decimal). Percentuais como `18%` (sem espaço antes do símbolo).
""".strip()

VOICE_RULES_ROTEIRO = """
REGRAS DE VOZ FINSPOTS (roteiro de vídeo) — seguir sempre, sem exceção:
- Fala como guia, não como locutor. Tom próximo, direto — como se estivesse explicando pessoalmente para o dono da loja.
- Dado concreto → interpretação → ação. Sempre nessa ordem, em cada bloco.
- Frases curtas para narração. Máximo 2 linhas por frase falada.
- Nunca lê a tabela inteira. Destaca os números mais relevantes e interpreta — não lista tudo.
- Nunca usa "como podemos ver no gráfico" nem cita "o gráfico" de forma genérica. Fala o dado direto.
  Nos blocos que comparam número de verdade (RESULTADO FINANCEIRO, COMPARATIVO, COMPARATIVO
  FINANCEIRO, COMPARATIVO DE VENDAS — decisão do analista, 05/09/2026), o slide de fato mostra um
  gráfico de barras com os números reais (ver dp-03/edicao/graficos.py); nos demais blocos, o slide
  só tem um ícone temático ilustrativo — nunca dizer "veja no gráfico" nesses.
- Nunca devolve decisão pro cliente. Sem "faz sentido?", sem "o que você prefere?".
- Honesta quando o número dói. Se está ruim, diz — com cuidado, mas diz.
- Cada bloco fecha com ação ou direção. Nunca termina descrevendo.
- Nunca inventa dado. Campo ausente = sinalizar, nunca preencher com número chutado.
""".strip()

VOICE_RULES_CARD = """
REGRAS DO TEXTO DO CARD (o que aparece ESCRITO no slide, enquanto a fala completa é narrada) — seguir sempre:
- NÃO é a fala transcrita. É um resumo curto pro card fixo do vídeo (mesmo template/layout sempre): 1 dado principal + 1 frase curta de interpretação ou ação. 2 a 4 linhas curtas no total.
- Contém sempre o número/dado mais importante do bloco (o que a fala destaca primeiro), nunca um número que não esteja também na fala.
- Nunca contradiz a fala. É um recorte dela, não uma versão diferente da história.
- Nunca usa frase incompleta cortada ("Sua margem est..."). Frases curtas e completas.
- Cards de transição (sem narração própria, ex: "BLOCO 1 — COMO ESTÁ SEU NEGÓCIO") usam o mesmo texto curto tanto na fala quanto no card — não têm versão longa separada.
""".strip()

VOICE_RULES_PREDITIVA = """
REGRAS DA CAMADA PREDITIVA — seguir sempre que o bloco pedir projeção/contrafactual:
- Nunca número único. Sempre três cenários: pessimista, realista, otimista.
- Nunca passado como culpa. Sempre futuro como oportunidade — mudar tempo verbal.
  Proibido: "se não tivesse dado desconto, teria lucrado R$20k a mais."
  Correto: "Temos espaço para capturar até R$20k adicionais na próxima campanha ajustando a precificação."
- Sempre ancorar no dado. "Baseado nos últimos X meses/períodos..." — nunca "estimamos que...", nunca prometer.
- Sinalizar incerteza sem perder autoridade. "A tendência aponta para..." / "A zona de aterrissagem é entre X e Y" — não "pode ser que...", não "você vai faturar...".
- Campo/histórico insuficiente = sem projeção. Diagnóstico precisa de pelo menos 2 períodos; Mensalidade precisa de pelo menos 3 meses de histórico. Sem isso, sinalizar a ausência — nunca inventar cenário.
""".strip()

VOICE_RULES_COMPARATIVO = """
REGRAS DO DIAGNÓSTICO COMPARATIVO (NOVIDADE 06/09/2026 — crença do cliente vs. realidade dos dados) — só valem quando "PERCEPÇÕES DO CLIENTE" abaixo tiver algo preenchido; confirmado pelo analista: "isso tem que ser feito com cuidado pra não parecer um sermão, pois o intuito é trazer clareza":
- Objetivo: trazer clareza, nunca corrigir ou repreender. O cliente não errou — ele só não tinha os dados na frente antes de contratar a Finspots. Você está revelando o que os números mostram, não apontando uma falha dele.
- Formato de referência: [o que o cliente acredita, do formulário] → [o que os dados realmente mostram] → [a causa, em uma frase]. Ex.: "Segundo sua resposta no formulário, você acredita que fatura R$X. Os dados mostram que na verdade é R$Y — a diferença vem de Z, que está consumindo parte da sua margem em W."
- Proibido soar como sermão, bronca ou correção de prova: nunca "você errou", "isso mostra que você não tinha controle", "você deveria saber disso". Trocar por tom de descoberta conjunta: "isso é mais comum do que parece", "agora você sabe exatamente onde", "essa clareza já é o primeiro passo".
- Só compare quando a divergência for real e relevante (muda a decisão do cliente). Se a percepção do cliente já bate com os dados, ou a diferença é pequena/irrelevante, não force nenhuma comparação — pode virar um reforço positivo curto ("Sua percepção de que X bate com o que os dados mostram — você já tem clareza aqui.") em vez de procurar defeito onde não há.
- No máximo 1 a 2 percepções por entrega — a mais reveladora pro negócio, nunca todas de uma vez. Comparação demais vira lista de correções, não narrativa de clareza (a mesma regra de "não passar informação excessiva" do Guia de Marca).
- Nunca inventar uma crença que o cliente não declarou — campo ausente/None em "percepcoes_cliente" significa que aquele assunto simplesmente não entra na comparação, não que o cliente "não sabia de nada".
- Aplica a mesma régua de honestidade do resto da voz Finspots ("honesta mesmo quando o número dói") — a diferença aqui é só o EMPACOTAMENTO: em vez de "sua margem está em 8%, que é crítico", fica "você imaginava X, a realidade é 8%, que é crítico — e é exatamente isso que vamos resolver juntos agora".
""".strip()

WHATSAPP_FINSPOTS = "(62) 9 9667-7168"
RODAPE_FINSPOTS = f"Dúvidas? WhatsApp: {WHATSAPP_FINSPOTS} | Finspots — Análise Financeira para E-commerce"


# ============================================================================
# RELATÓRIO PDF — DIAGNÓSTICO (Capa + páginas 2 a 9 = 9 páginas no total)
# ============================================================================

DIAGNOSTICO_PAGINAS: List[Dict[str, Any]] = [
    {
        "numero": 2,
        "titulo": "COMO ESTÁ SEU NEGÓCIO HOJE",
        "fonte": "summary (overall_status, revenue_net, profit_net, contribution_margin_pct, profit_margin_pct) + insights['STATUS GERAL']",
        "instrucoes": [
            "Trazer a frase do insight STATUS GERAL exatamente como está, sem alterar.",
            "Apresentar os 4 números principais em linguagem direta.",
            "Nomear o status geral do negócio com contexto — não só o emoji, mas o que significa pra esse cliente.",
            "Se houver PERCEPÇÕES DO CLIENTE disponíveis (Diagnóstico Comparativo), este é o lugar natural pra plantar a mais reveladora — ver VOICE_RULES_COMPARATIVO. Não force se não houver nenhuma divergência relevante.",
        ],
        "formato": """[NOME DA LOJA] — [PERÍODO]

[Frase do insight STATUS GERAL]

Receita Líquida: R$ ___
Lucro Líquido: R$ ___
Margem de Contribuição: ___% [🔴/🟠/🟡/🟢]
Margem Líquida: ___% [🔴/🟠/🟡/🟢]
Status Geral: [🔴 CRÍTICO / 🟠 RUIM / 🟡 ATENÇÃO / 🟢 SAUDÁVEL]""",
    },
    {
        "numero": 3,
        "titulo": "RESULTADO FINANCEIRO",
        "fonte": "financial (DRE completo) + insights['LUCRATIVIDADE'] + insights['MARGEM_CONTRIBUICAO']",
        "instrucoes": [
            "Comentar o maior custo identificado (CMV, custos variáveis ou fixos) e o que isso significa.",
            "Contextualizar a Margem de Contribuição com a frase do insight correspondente.",
            "Fechar com o Breakeven — se o faturamento ficou acima ou abaixo, e o que isso significa na prática.",
        ],
        "formato": """[Texto introdutório — 2 linhas máximo]

[Frase do insight LUCRATIVIDADE]

[Frase do insight MARGEM_CONTRIBUICAO]

Breakeven: R$ ___
Seu faturamento ficou [ACIMA / ABAIXO] desse valor no período.
[1 frase explicando o que isso significa — ex: "Isso significa que o negócio cobriu os custos fixos e gerou lucro" ou "Isso significa que a operação não se pagou completamente neste período."]""",
    },
    {
        "numero": 4,
        "titulo": "ONDE ESTÁ O PESO",
        "fonte": "financial (composição de custos) + channels + insights['CANAIS']",
        "instrucoes": [
            "Identificar o maior peso de custo e comentar se é esperado para o perfil do negócio (usar a Categoria A-E, disponível em cliente['categoria']).",
            "Apresentar a distribuição de canais em linguagem direta — qual lidera, qual é secundário.",
            "Trazer a frase do insight CANAIS.",
        ],
        "formato": """[1–2 frases sobre composição de custos — identificar o maior peso e contextualizar com a Categoria do negócio]

[Distribuição de canais: "[canal 1] responde por ___% do faturamento, seguido de [canal 2] com ___% e [canal 3] com ___%."]

[Frase do insight CANAIS]""",
    },
    {
        "numero": 5,
        "titulo": "SEUS CANAIS DE VENDA",
        "fonte": "channels (lista completa com margem e semáforo) + insights['CANAIS']",
        "instrucoes": [
            "Destacar o canal com melhor margem e o que isso significa.",
            "Alertar sobre o canal com pior margem — com dado concreto (taxa, margem resultante).",
            "Fechar com ação clara.",
        ],
        "formato": """O canal com melhor margem é [canal] — ___%. [1 frase de contexto].

O canal que mais preocupa é [canal] — margem de ___%.
[1 frase explicando o porquê — ex: "A taxa de ___% da plataforma consome boa parte do faturamento."]

[Ação direta — ex: "Antes de aumentar o volume nesse canal, vale revisar a precificação para garantir margem mínima de ___%."]""",
    },
    {
        "numero": 6,
        "titulo": "MARKETING",
        "fonte": "marketing (roas, roas_breakeven, ads_pct_revenue, cac) + insights['MARKETING']",
        "instrucoes": [
            "Formulário de entrada tem o campo de marketing como OPCIONAL, e o público é leigo — é comum vir incompleto ou "
            "estimado. Tratar 3 estados, nunca inventar o que faltar:",
            "1) ads_investment == 0 (nenhum dado de ads informado) -> formato 'sem dados' abaixo, bloco inteiro.",
            "2) ads_investment > 0 mas new_customers_ads não informado (CAC fica indisponível, embora ROAS/%Ads existam, "
            "porque só o CAC depende do número de novos clientes) -> formato 'parcial': narra ROAS e %Ads normalmente, "
            "e no lugar do CAC usa uma frase curta pedindo o dado que falta — nunca mostra 'R$ 0' nem estima um CAC.",
            "3) Os dois presentes -> formato 'com dados', completo.",
            "Em qualquer estado com ROAS disponível: apresentar o ROAS real vs o ROAS de equilíbrio, com interpretação clara, "
            "e o % de Ads sobre receita com o semáforo correspondente.",
            "Fechar com ação ou recomendação (mesmo no formato parcial).",
        ],
        "formato_com_dados": """[Frase do insight MARKETING]

ROAS: ___x | Mínimo pra não perder: ___x
[1 frase interpretando — ex: "Seu ROAS está acima do equilíbrio — os anúncios estão gerando retorno positivo." ou "Seu ROAS está abaixo do mínimo — cada real investido em ads está gerando prejuízo."]

___% do faturamento vai para anúncios. [Frase do semáforo correspondente].

Custo por cliente (CAC): R$ ___
[1 frase contextualizando — ex: "Cada novo cliente via ads custou R$ ___ pra chegar até você."]

[Ação fechando o bloco]""",
        "formato_parcial_sem_cac": """[Frase do insight MARKETING]

ROAS: ___x | Mínimo pra não perder: ___x
[1 frase interpretando]

___% do faturamento vai para anúncios. [Frase do semáforo correspondente].

Custo por cliente (CAC): não foi possível calcular neste período — falta o número de novos clientes via Ads.
Pra próxima análise, informe esse número e mostramos o CAC real.

[Ação fechando o bloco]""",
        "formato_sem_dados": """Dados de marketing não foram informados neste período.

Para a próxima análise, recomendamos incluir:
— Investimento total em Ads
— Número de novos clientes via Ads

Com esses dados conseguimos calcular o retorno real das campanhas e o custo por cliente adquirido.""",
    },
    {
        "numero": 7,
        "titulo": "A COMPARAÇÃO",
        "fonte": "periodo_anterior (se fornecido) vs dados atuais (revenue_net, contribution_margin_pct, profit_margin_pct, profit_net, roas)",
        "instrucoes": [
            "Se NÃO houver período anterior (primeiro diagnóstico do cliente), usar o texto padrão de primeiro diagnóstico — nunca inventar comparativo.",
            "Se houver período anterior, apresentar o comparativo indicador a indicador e gerar 2-3 frases analíticas sobre a evolução mais relevante.",
            "[CAMADA PREDITIVA] Só ativar o bloco de projeção se houver período anterior disponível (mínimo 2 períodos). Aplicar VOICE_RULES_PREDITIVA. Nunca prometer — sempre ancorar.",
        ],
        "formato_primeiro": """Este é o seu primeiro diagnóstico Finspots.

A partir do acompanhamento mensal você terá a evolução período a período — e aí sim vamos ver claramente o que melhorou, o que manteve e o que ainda precisa de atenção.""",
        "formato_comparativo": """Comparando com o período anterior:

Receita Líquida: R$ ___ → R$ ___ ([▲/▼] ___%)
Margem de Contribuição: ___% → ___%
Margem Líquida: ___% → ___%
Lucro Líquido: R$ ___ → R$ ___ ([▲/▼] ___%)
ROAS: ___x → ___x

[2–3 frases analíticas sobre a evolução mais relevante — o que melhorou, o que piorou e o que o dado significa]

— — —

Projeção para o próximo período — baseada na tendência dos dados disponíveis

Cenário pessimista: R$ ___ (queda de ___% sobre o atual)
Cenário realista: R$ ___ (continuidade da tendência atual)
Cenário otimista: R$ ___ (reversão dos pontos de alerta)

[1 frase ancorada no dado: "A tendência dos dois períodos aponta para X. O que vai definir em qual cenário você aterra é Y."]""",
    },
    {
        "numero": 8,
        "titulo": "O QUE FAZER AGORA",
        "fonte": "top_3_priorities (code, rule, score, action)",
        "instrucoes": [
            "Página mais importante do relatório — nunca suavizar. Se o alerta tem score máximo (🔴), o texto precisa refletir urgência real: 'ação imediata', 'impacto direto no lucro', 'risco real de prejuízo'.",
            "Ordem de urgência: 🔴 Prioridade 1, 🟠 Prioridade 2, 🟡 Prioridade 3 — sempre na ordem de score (maior primeiro), exatamente como top_3_priorities já vem ordenado.",
            "[CAMADA PREDITIVA] Cada prioridade recebe uma linha de 'Impacto estimado' com análise contrafactual simples (ceteris paribus — mantendo volume e tráfego constantes, alterando só a variável da prioridade). Tempo verbal sempre no futuro (oportunidade), nunca no passado (culpa).",
        ],
        "formato": """Suas 3 prioridades — em ordem de urgência

🔴 PRIORIDADE 1 — [nome do alerta]
O que fazer: [ação recomendada]
Por que isso importa: [1–2 frases em linguagem simples, sem jargão, explicando o impacto real no negócio]
Impacto estimado: Corrigindo isso, sua margem sai de ___% para aproximadamente ___% — mantendo o mesmo volume de vendas.

🟠 PRIORIDADE 2 — [nome do alerta]
O que fazer: [ação recomendada]
Por que isso importa: [contexto em linguagem simples]
Impacto estimado: Corrigindo isso, sua margem sai de ___% para aproximadamente ___% — mantendo o mesmo volume de vendas.

🟡 PRIORIDADE 3 — [nome do alerta]
O que fazer: [ação recomendada]
Por que isso importa: [contexto]
Impacto estimado: Corrigindo isso, sua margem sai de ___% para aproximadamente ___% — mantendo o mesmo volume de vendas.""",
    },
    {
        "numero": 9,
        "titulo": "PRÓXIMO PASSO",
        "fonte": "insights['BREAKEVEN'] + insights['PRIORIDADES'] (ou top_3_priorities[0])",
        "instrucoes": [
            "Página de fechamento. Tom: próximo, direto, confiante. Sem enrolação, sem cordialidade excessiva.",
            "Recomendação personalizada conectando a prioridade #1 com o perfil do negócio (categoria, canal principal, maior custo identificado).",
            "Adicionar frase de projeção que planta o gancho para a mensalidade (cenário realista da Página 7, se houver; senão frase genérica de acompanhamento).",
            f"Rodapé fixo: '{RODAPE_FINSPOTS}'",
        ],
        "formato": f"""[Frase do insight BREAKEVEN, formatada como parágrafo]

[Frase do insight PRIORIDADES/PRIORIDADE #1, formatada como parágrafo]

Recomendação: [2–3 linhas personalizadas conectando a prioridade #1 com o perfil do negócio — categoria, canal principal, maior custo identificado]

No ritmo atual, o próximo período aponta para [cenário realista]. Vamos acompanhar juntos se essa projeção se confirma — e o que explica quando ela diverge.

{RODAPE_FINSPOTS}""",
    },
]

DIAGNOSTICO_CHECKLIST_ENTREGA = [
    "Todos os campos numéricos usados vieram dos dados do motor? Nenhum foi inventado?",
    "O status geral bate com os números apresentados?",
    "As prioridades estão em ordem de score (maior primeiro)?",
    "Cada bloco termina com ação — não só com descrição?",
    "Nenhuma frase devolve a decisão pro cliente?",
    "O breakeven foi comparado com o faturamento real?",
    "Se não há dados de marketing, foi usado o texto padrão de ausência?",
    "[PREDITIVO] Se houver diagnóstico anterior: bloco de projeção com três cenários foi adicionado na Página 7?",
    "[PREDITIVO] Cada prioridade na Página 8 tem linha de impacto estimado com contrafactual?",
    "[PREDITIVO] O tempo verbal do contrafactual está no futuro — oportunidade, não culpa?",
    "[PREDITIVO] Frase de gancho plantada na Página 9 para a mensalidade?",
    "[PREDITIVO] Nenhuma projeção usa número único — sempre intervalo com três cenários?",
    "[PREDITIVO] Campos vazios sinalizados — nenhum dado inventado?",
]


# ============================================================================
# RELATÓRIO PDF — MENSALIDADE (Capa + páginas 2 a 10 = 10 páginas no total)
# ============================================================================

MENSALIDADE_PAGINAS: List[Dict[str, Any]] = [
    {
        "numero": 2,
        "titulo": "COMO FOI O MÊS",
        "fonte": "financial (revenue_net, profit_net, contribution_margin_pct, profit_margin_pct, breakeven) + insights['STATUS_DO_MES'] + insights['LUCRATIVIDADE']",
        "instrucoes": [
            "Trazer a frase do insight STATUS_DO_MES exatamente como está.",
            "Apresentar os 5 números principais com semáforo.",
            "Indicar se o faturamento ficou acima ou abaixo do Breakeven.",
        ],
        "formato": """[NOME DA LOJA] — [MÊS/ANO]

[Frase do insight STATUS_DO_MES]

Receita Líquida:          R$ ___   —
Lucro Líquido:            R$ ___   —
Margem de Contribuição:   ___%     [🔴/🟠/🟡/🟢]
Margem Líquida:           ___%     [🔴/🟠/🟡/🟢]
Breakeven:                R$ ___   [ACIMA / ABAIXO]

[Frase do insight LUCRATIVIDADE]""",
    },
    {
        "numero": 3,
        "titulo": "RESULTADO FINANCEIRO DO MÊS",
        "fonte": "financial (DRE do mês) + insights['LUCRATIVIDADE']",
        "instrucoes": [
            "Destacar o maior custo do mês e o que isso representa.",
            "Contextualizar a Margem de Contribuição com a frase do insight.",
            "Fechar com o Breakeven — acima ou abaixo, e o que significa.",
        ],
        "formato": """O que entrou, o que saiu e o que sobrou em [mês].

[1–2 frases sobre o maior custo identificado na DRE — ex: "O CMV representou ___% da receita — o maior peso da operação neste mês."]

[Frase do insight LUCRATIVIDADE]

Breakeven do mês: R$ ___
Seu faturamento ficou [ACIMA / ABAIXO] desse valor.
[1 frase explicando o que isso significa na prática]""",
    },
    {
        "numero": 4,
        "titulo": "SEUS CANAIS NO MÊS",
        "fonte": "sales_intelligence (best_channel_*, worst_channel_*) + insights['CANAIS'] (se disponível)",
        "instrucoes": [
            "Apresentar o canal líder e o canal com pior desempenho.",
            "Comparar com o mês anterior se houver mudança de canal líder.",
            "Trazer a frase do insight CANAIS, se disponível nos dados.",
            "Fechar com ação.",
        ],
        "formato": """Quanto cada canal faturou e qual a margem em [mês].

Canal com melhor desempenho: [canal] — R$ ___ | Margem: ___% [semáforo]
Canal com pior desempenho:   [canal] — R$ ___ | Margem: ___% [semáforo]

[Se o canal líder mudou vs mês anterior: "Atenção: o canal líder mudou — no mês passado era [canal anterior], agora é [canal atual]. Vale investigar o que explica essa mudança."]

[Frase do insight CANAIS, se disponível]

[Ação fechando o bloco]""",
    },
    {
        "numero": 5,
        "titulo": "SEUS PRODUTOS NO MÊS",
        "fonte": "sales_intelligence (top_product_1, worst_product_margin, paused_products_count) + insights['PORTFOLIO']",
        "instrucoes": [
            "Apresentar o Top 3 com receita e margem (usar o que estiver disponível — pode ser só o Top 1 se for o único dado no motor).",
            "Alertar sobre o produto com pior margem — com dado concreto.",
            "Mencionar produtos parados — quantos e o que isso significa.",
            "Trazer a frase do insight PORTFOLIO.",
        ],
        "formato": """O que vendeu, o que preocupa e o que parou em [mês].

🥇 [Produto Top 1] — R$ ___ | Margem: ___%
🥈 [Produto Top 2] — R$ ___ | Margem: ___% (se disponível)
🥉 [Produto Top 3] — R$ ___ | Margem: ___% (se disponível)

⚠️ Produto com pior margem: [produto] — ___%
[1 frase explicando o impacto — ex: "Cada venda desse produto contribui pouco pro resultado — vale revisar o preço ou o custo."]

💤 Produtos sem venda no mês: ___ itens
[1 frase sobre capital parado — ex: "Itens parados representam capital imobilizado no estoque. Vale avaliar queima ou reposicionamento."]

[Frase do insight PORTFOLIO]""",
    },
    {
        "numero": 6,
        "titulo": "CLIENTES E MARKETING",
        "fonte": "sales_intelligence (recurring_customers_pct) + marketing (roas, cac) + insights['CLIENTES_RETENCAO'] + insights['MARKETING']",
        "instrucoes": [
            "Apresentar a base de clientes do mês — novos vs recorrentes — SEMPRE, independente de ter dado de marketing (não depende de ads).",
            "Comentar o % de recorrentes com semáforo (usar o piso da Categoria do negócio — ver get_recurring_floor no motor).",
            "Marketing é opcional no formulário e o público é leigo — trate os mesmos 3 estados do bloco MARKETING do "
            "Diagnóstico: sem nenhum dado de ads -> formato_sem_dados_marketing (troca só a seção de marketing, os "
            "clientes acima continuam normalmente); com ROAS/%Ads mas sem CAC (número de novos clientes via ads não "
            "informado) -> formato_parcial_sem_cac_marketing (narra ROAS/%Ads, sinaliza que falta o CAC, nunca inventa "
            "um valor); com tudo -> formato_com_dados.",
            "Trazer as frases dos insights CLIENTES_RETENCAO e MARKETING (esta última só quando houver algum dado de marketing).",
        ],
        "formato_com_dados": """Quem comprou e quanto custou trazer cada cliente em [mês].

Clientes novos:        ___
Clientes recorrentes:  ___
% recorrentes:         ___% [🔴/🟠/🟡/🟢]

[Frase do insight CLIENTES_RETENCAO]

ROAS:                      ___x [🔴/🟠/🟡/🟢]
% do faturamento em Ads:   ___%  [🔴/🟠/🟡/🟢]
CAC:                       R$ ___

[Frase do insight MARKETING]""",
        "formato_parcial_sem_cac_marketing": """Quem comprou e quanto custou trazer cada cliente em [mês].

Clientes novos:        ___
Clientes recorrentes:  ___
% recorrentes:         ___% [🔴/🟠/🟡/🟢]

[Frase do insight CLIENTES_RETENCAO]

ROAS:                      ___x [🔴/🟠/🟡/🟢]
% do faturamento em Ads:   ___%  [🔴/🟠/🟡/🟢]
CAC:                       não foi possível calcular neste mês — falta o número de novos clientes via Ads.

[Frase do insight MARKETING]""",
        "formato_sem_dados_marketing": "Dados de marketing não informados neste mês. Para calcular ROAS e CAC, incluir investimento em Ads e número de novos clientes via Ads no próximo mês.",
    },
    {
        "numero": 7,
        "titulo": "COMPARATIVO FINANCEIRO",
        "fonte": "comparatives (revenue_net, contribution_margin_pct, profit_margin_pct, profit_net) + insights['COMPARATIVO_FINANCEIRO'] + aposta_anterior (texto + resultado, se houver mês anterior com prioridade #1 registrada)",
        "instrucoes": [
            "Se for o primeiro mês de acompanhamento, usar o texto padrão — nunca inventar comparativo.",
            "Se houver mês anterior E uma 'aposta anterior' (a ação da Prioridade #1 do mês passado, extraída automaticamente do diagnóstico anterior — substitui a antiga célula manual CONFIG!B53), abrir narrando o resultado dessa aposta: ✅ Melhorou / ❌ Não melhorou / ➡️ Manteve, com base na variação do indicador associado.",
            "Se não houver aposta anterior registrada, ignorar o bloco de abertura e iniciar direto no comparativo financeiro.",
            "[CAMADA PREDITIVA] Separar fatores controláveis (ex: política de desconto, mix de produto) de fatores externos (sazonalidade, frete) quando houver desvio relevante vs a aposta.",
        ],
        "formato_primeiro_mes": """Este é o primeiro mês de acompanhamento Finspots.

A partir do próximo mês você terá a comparação mês a mês para acompanhar sua evolução — receita, margem, lucro e ROAS lado a lado, mês após mês.""",
        "formato_comparativo": """[Se houver aposta anterior: "No mês passado, a prioridade era [texto da aposta anterior]. O que aconteceu: [✅ Melhorou / ❌ Não melhorou / ➡️ Manteve]. [1 frase explicando o resultado]" — senão, pular direto para o bloco abaixo]

— — —

Como você estava no mês passado vs agora.

Indicador              Mês Atual   Mês Anterior   Variação
Receita Líquida        R$ ___      R$ ___         [▲/▼] ___%
Margem Contribuição    ___%        ___%           [▲/▼]
Margem Líquida         ___%        ___%           [▲/▼]
Lucro Líquido          R$ ___      R$ ___         [▲/▼] ___%
ROAS                   ___x        ___x           [▲/▼]

[Frase do insight COMPARATIVO_FINANCEIRO]

[1–2 frases analíticas sobre a variação mais relevante — o que explica a mudança e o que significa pra frente]""",
    },
    {
        "numero": 8,
        "titulo": "COMPARATIVO DE VENDAS",
        "fonte": "sales_intelligence atual vs mês anterior (top_product, best_channel, recurring_customers_pct, paused_products_count) + insights['TENDENCIA']",
        "instrucoes": [
            "Comparar top produto e canal líder — manteve ou mudou.",
            "Comparar % recorrentes e produtos parados.",
            "Trazer a frase do insight TENDENCIA.",
        ],
        "formato": """O que mudou nos seus produtos e canais.

                   Mês Atual   Mês Anterior   Mudou?

Top 1 produto          ___         ___            [✅ Manteve / ⚡ Mudou]
Canal líder            ___         ___            [✅ Manteve / ⚡ Mudou]
Clientes recorrentes   ___%        ___%           [▲/▼]
Produtos parados       ___         ___            [▲/▼]

[Se algo mudou — 1 frase contextualizando cada mudança relevante. Ex: "O top produto mudou de [X] pra [Y] — vale verificar se é sazonalidade ou tendência de portfólio."]

[Frase do insight TENDENCIA]""",
    },
    {
        "numero": 9,
        "titulo": "O QUE FAZER AGORA",
        "fonte": "top_3_priorities (code, rule, score, action)",
        "instrucoes": [
            "Mesma lógica do Diagnóstico — página mais importante. Urgência proporcional ao score. Prioridade 🔴 nunca é suavizada.",
        ],
        "formato": """Suas 3 prioridades do mês — em ordem de urgência.

🔴 PRIORIDADE 1 — [nome do alerta]
O que fazer: [ação recomendada]
Por que isso importa: [1–2 frases em linguagem simples, sem jargão, explicando o impacto real no negócio]

🟠 PRIORIDADE 2 — [nome do alerta]
O que fazer: [ação recomendada]
Por que isso importa: [contexto em linguagem simples]

🟡 PRIORIDADE 3 — [nome do alerta]
O que fazer: [ação recomendada]
Por que isso importa: [contexto]""",
    },
    {
        "numero": 10,
        "titulo": "PRÓXIMO PASSO",
        "fonte": "insights['PRIORIDADE'] (Prioridade #1) + contexto do mês (canal que mais variou, custo que pesou, tendência)",
        "instrucoes": [
            "Fechamento do relatório. Tom direto, próximo, confiante.",
            "Recomendação personalizada conectando a prioridade #1 com o que foi observado no mês.",
            f"Rodapé fixo: '{RODAPE_FINSPOTS}'",
        ],
        "formato": f"""[Frase do insight PRIORIDADE, formatada como parágrafo corrido]

Recomendação do mês: [2–3 linhas personalizadas conectando a prioridade #1 com o contexto do mês — canal que mais variou, custo que pesou, tendência de margem ou retenção]

{RODAPE_FINSPOTS}""",
    },
]

MENSALIDADE_CHECKLIST_ENTREGA = [
    "O mês de referência está correto em todos os blocos?",
    "Todos os comparativos mês atual vs anterior estão presentes?",
    "Se for o primeiro mês, os blocos de comparativo foram substituídos pelo texto padrão?",
    "Cada bloco termina com ação — não só com descrição?",
    "As prioridades estão em ordem de score (maior primeiro)?",
    "A Prioridade #1 está com tom de urgência proporcional ao score?",
    "Se não há dados de marketing, foi usado o texto padrão de ausência?",
    "Se o canal líder ou top produto mudou, foi mencionado e contextualizado?",
    "A recomendação final é personalizada — não genérica?",
    "Nenhuma frase devolve decisão pro cliente?",
    "[PREDITIVO] A aposta anterior (se houver) foi lida antes de gerar a Página 7?",
    "[PREDITIVO] Se não houver aposta anterior, o bloco de abertura foi ignorado?",
    "[PREDITIVO] O resultado da prioridade anterior foi classificado como ✅ / ❌ / ➡️?",
]


# ============================================================================
# ROTEIRO DE VÍDEO — DIAGNÓSTICO (6-8 minutos)
# ============================================================================

DIAGNOSTICO_ESPECIFICACOES_VIDEO = {
    "tempo_estimado": "6-8 minutos",
    "musica": "Lofi business baixinha durante todo o vídeo — fade out na última fala",
    "volume_musica": "15-20% — não pode cobrir a voz",
    "cards_transicao": "Clipe de cor sólida azul escuro #020B3B, texto branco centralizado, 2 segundos",
    "fade": "Fade in no início + fade out no final — 1 segundo cada",
}

DIAGNOSTICO_BLOCOS_VIDEO: List[Dict[str, Any]] = [
    {
        "nome": "INTRO",
        "duracao": "20 segundos",
        "slide": "[CARD: Logo Finspots centralizada, fundo azul escuro #020B3B]",
        "instrucoes": ["Saudar pelo nome do cliente, apresentar a Finspots, nomear o período analisado, convidar a seguir."],
        "formato": """"Olá, [nome do cliente]. Aqui é a Finspots — análise financeira para e-commerce.

Esse é o seu diagnóstico financeiro referente ao período [período].

Vou te guiar pelos números do seu negócio de forma clara e direta — e no final você vai saber exatamente o que fazer primeiro.

Vamos lá."​""",
    },
    {"nome": "CARD DE TRANSIÇÃO — BLOCO 1", "duracao": "2 segundos", "slide": "[CARD]", "instrucoes": [], "formato": "BLOCO 1 — COMO ESTÁ SEU NEGÓCIO"},
    {
        "nome": "BLOCO 1 — STATUS GERAL",
        "duracao": "30 segundos",
        "slide": "[SLIDE: Página 2 do PDF]",
        "instrucoes": [
            "Narrar o panorama geral. Não ler a tabela número por número — apresentar o cenário e nomear o status com contexto.",
            "Se houver PERCEPÇÕES DO CLIENTE disponíveis (Diagnóstico Comparativo), este é o lugar natural pra plantar a mais reveladora — ver VOICE_RULES_COMPARATIVO. Não force se não houver nenhuma divergência relevante.",
        ],
        "formato": """"Vou começar com o panorama geral.

No período analisado, sua receita líquida foi de [valor] e seu lucro líquido foi de [valor].

Sua margem líquida ficou em [%] — [frase curta do semáforo].

O status geral do seu negócio neste período é [🟡 ATENÇÃO / 🟠 RUIM / 🟢 SAUDÁVEL / 🔴 CRÍTICO].

Vou te explicar o que está por trás desse número agora."​""",
    },
    {
        "nome": "BLOCO 1 — RESULTADO FINANCEIRO",
        "duracao": "90 segundos",
        "slide": "[SLIDE: Página 3 do PDF — DRE]",
        "instrucoes": ["Narrar a DRE de forma fluida, não linha por linha. Destacar CMV, Margem de Contribuição, Lucro Líquido e Breakeven. Usar insights LUCRATIVIDADE e MARGEM_CONTRIBUICAO."],
        "formato": """"Agora vamos olhar pra dentro.

Sua receita bruta foi de [valor]. Depois das devoluções, chegamos a uma receita líquida de [valor] — essa é a base real de todos os percentuais que vou mostrar agora.

O custo das mercadorias representou [%] da receita.

Depois de impostos e CMV, seu lucro bruto ficou em [%] de margem.

Os custos variáveis consumiram mais [%]. Isso nos deixa com uma Margem de Contribuição de [%]. [Frase do insight MARGEM_CONTRIBUICAO].

Depois de custos fixos e pró-labore, seu lucro líquido foi de [valor] — [%] de margem líquida. [Frase do insight LUCRATIVIDADE].

Um ponto importante: pra não ter prejuízo, seu negócio precisa faturar pelo menos [breakeven] por mês.

Neste período, seu faturamento ficou [ACIMA / ABAIXO] desse valor."​""",
    },
    {
        "nome": "BLOCO 1 — CUSTOS E CANAIS",
        "duracao": "60 segundos",
        "slide": "[SLIDE: Página 4 do PDF]",
        "instrucoes": ["Comentar o maior custo, contextualizando com a Categoria do negócio. Apresentar distribuição de canais."],
        "formato": """"Olhando pra composição dos custos, o maior peso na sua operação é [maior custo] — [%] da receita.

[1 frase contextualizando com a Categoria do negócio].

Sobre os canais de venda: [canal principal] responde por [%] do seu faturamento total, seguido de [canal 2] com [%] e [canal 3] com [%].

Mas faturamento não é tudo — agora vamos olhar a margem de cada canal."​""",
    },
    {
        "nome": "BLOCO 1 — CANAIS DE VENDA",
        "duracao": "45 segundos",
        "slide": "[SLIDE: Página 5 do PDF]",
        "instrucoes": ["Destacar melhor e pior canal por margem. Usar insight CANAIS. Fechar com ação direta."],
        "formato": """"O canal com melhor margem é [canal] — [%]. [1 frase de contexto positivo].

O canal que mais preocupa é [canal] — margem de [%]. [Frase do insight CANAIS].

Isso é importante porque vender muito num canal de margem baixa pode estar prejudicando seu resultado sem você perceber.

[Ação direta]"​""",
    },
    {
        "nome": "BLOCO 1 — MARKETING",
        "duracao": "45 segundos",
        "slide": "[SLIDE: Página 6 do PDF]",
        "instrucoes": [
            "Marketing é opcional no formulário e o público é leigo — trate os mesmos 3 estados da Página 6 do PDF "
            "(ver templates de relatório, bloco MARKETING): sem nenhum dado de ads -> formato_sem_dados; com ROAS/%Ads "
            "mas sem CAC (número de novos clientes não informado) -> formato_parcial_sem_cac (narra ROAS normalmente, "
            "sinaliza que falta o CAC, nunca inventa um valor); com tudo -> formato_com_dados.",
        ],
        "formato_com_dados": """"Agora os anúncios.

Você investiu [valor] em ads neste período. Seu ROAS foi de [x] — o mínimo pra não perder dinheiro nesse negócio é [ROAS de equilíbrio].

[Frase do insight MARKETING].

O custo por cliente adquirido via ads foi de [CAC] — cada novo cliente custou [valor] pra chegar até você.

[Ação fechando]"​""",
        "formato_parcial_sem_cac": """"Agora os anúncios.

Você investiu [valor] em ads neste período. Seu ROAS foi de [x] — o mínimo pra não perder dinheiro nesse negócio é [ROAS de equilíbrio].

[Frase do insight MARKETING].

Não deu pra calcular o custo por cliente esse período — faltou o número de novos clientes via ads. Na próxima, me manda esse número que eu calculo certinho.

[Ação fechando]"​""",
        "formato_sem_dados": """"Dados de marketing não foram informados neste período.

Pra próxima análise, recomendo incluir o investimento em ads e o número de novos clientes.

Com esses dados conseguimos calcular o retorno real das campanhas e o custo por cliente adquirido."​""",
    },
    {"nome": "CARD DE TRANSIÇÃO — BLOCO 2", "duracao": "2 segundos", "slide": "[CARD]", "instrucoes": ["Pular direto pro Bloco 3 se for o primeiro diagnóstico."], "formato": "BLOCO 2 — A COMPARAÇÃO"},
    {
        "nome": "BLOCO 2 — COMPARATIVO",
        "duracao": "60 segundos",
        "slide": "[SLIDE: Página 7 do PDF]",
        "instrucoes": ["Se primeiro diagnóstico, texto padrão. Senão, narrar evolução + projeção com três cenários (VOICE_RULES_PREDITIVA)."],
        "formato_primeiro": """"Este é o seu primeiro diagnóstico Finspots.

A partir do acompanhamento mensal você terá a evolução período a período — e aí sim vamos ver claramente o que melhorou e o que ainda precisa de atenção."​""",
        "formato_comparativo": """"Comparando com o período anterior:

Sua receita [subiu / caiu] [%] — de [valor anterior] pra [valor atual].

A margem líquida [melhorou de ___% pra ___% / caiu de ___% pra ___%].

O lucro [subiu / caiu] [%].

[1–2 frases analíticas sobre a mudança mais relevante]

Agora, com base na tendência desses dois períodos, veja pra onde o negócio está caminhando.

No cenário pessimista, o próximo período aponta pra [valor].
No cenário realista, a tendência indica [valor].
E se as ações prioritárias forem implementadas, o cenário otimista é de [valor].

O que vai definir em qual cenário você aterra é [fator decisivo]."​""",
    },
    {"nome": "CARD DE TRANSIÇÃO — BLOCO 3", "duracao": "2 segundos", "slide": "[CARD]", "instrucoes": [], "formato": "BLOCO 3 — O QUE FAZER AGORA"},
    {
        "nome": "BLOCO 3 — PRIORIDADES",
        "duracao": "90 segundos",
        "slide": "[SLIDE: Página 8 do PDF]",
        "instrucoes": ["Parte mais importante do vídeo. Urgência proporcional ao score. 🔴 nunca é suavizada. Impacto estimado sempre no futuro."],
        "formato": """"Agora o mais importante — o que você precisa fazer primeiro.

Prioridade número 1: [nome do alerta].
[Ação recomendada].
[Por que isso importa — 1–2 frases]
Corrigindo isso, sua margem sai de [%] pra aproximadamente [%] — mantendo o mesmo volume de vendas.

Prioridade número 2: [nome do alerta].
[Ação recomendada].
[Contexto]
Corrigindo isso, sua margem sai de [%] pra aproximadamente [%] — mantendo o mesmo volume de vendas.

Prioridade número 3: [nome do alerta].
[Ação recomendada].
[Contexto]
Corrigindo isso, sua margem sai de [%] pra aproximadamente [%] — mantendo o mesmo volume de vendas.

Essas três ações, se implementadas agora, têm o maior potencial de impacto no seu resultado."​""",
    },
    {
        "nome": "BLOCO 3 — ENCERRAMENTO",
        "duracao": "40 segundos",
        "slide": "[SLIDE: Página 9 do PDF]",
        "instrucoes": [f"Frase da Prioridade #1 adaptada pra fala + recomendação personalizada + gancho pra mensalidade + WhatsApp {WHATSAPP_FINSPOTS}."],
        "formato": f""""[Frase do insight PRIORIDADES, adaptada pra fala]

[Recomendação personalizada de 1–2 frases]

No ritmo atual, o próximo período aponta pra [cenário realista]. Vamos acompanhar juntos se essa projeção se confirma — e o que explica quando ela diverge.

Qualquer dúvida, é só me chamar no WhatsApp. O número está no relatório PDF que você recebeu junto com esse vídeo.

Obrigada por confiar na Finspots. Até o próximo."​""",
    },
    {"nome": "CARD FINAL", "duracao": "-", "slide": "[CARD: Logo Finspots + WhatsApp — fundo azul escuro][Música fade out]", "instrucoes": [], "formato": "(sem fala — apenas card visual de encerramento)"},
]

DIAGNOSTICO_CHECKLIST_ROTEIRO = [
    "O nome do cliente aparece na intro e está correto?",
    "O período analisado está correto?",
    "Nenhum bloco lê a tabela inteira — só destaca o relevante?",
    "Cada bloco fecha com ação ou direção?",
    "A Prioridade #1 está com tom de urgência proporcional ao score?",
    "Se não há dados de marketing, foi usado o texto padrão?",
    "Se é o primeiro diagnóstico, o Bloco 2 foi substituído pelo texto padrão?",
    "O encerramento tem recomendação personalizada — não genérica?",
    "Nenhuma frase devolve decisão pro cliente?",
    "[PREDITIVO] Se houver diagnóstico anterior: projeção com três cenários foi narrada no Bloco 2?",
    "[PREDITIVO] O fator decisivo foi identificado e narrado?",
    "[PREDITIVO] Cada prioridade tem impacto estimado narrado — sempre no futuro?",
    "[PREDITIVO] Frase de gancho para mensalidade está no encerramento?",
    "[PREDITIVO] Nenhuma projeção usou número único — sempre três cenários?",
]


# ============================================================================
# ROTEIRO DE VÍDEO — MENSALIDADE (7-9 minutos)
# ============================================================================

MENSALIDADE_ESPECIFICACOES_VIDEO = {
    "tempo_estimado": "7-9 minutos",
    "musica": "Lofi business baixinha durante todo o vídeo — fade out na última fala",
    "volume_musica": "15-20% — não pode cobrir a voz",
    "cards_transicao": "Clipe de cor sólida azul escuro #020B3B, texto branco centralizado, 2 segundos",
    "fade": "Fade in no início + fade out no final — 1 segundo cada",
}

MENSALIDADE_BLOCOS_VIDEO: List[Dict[str, Any]] = [
    {
        "nome": "INTRO",
        "duracao": "25 segundos",
        "slide": "[CARD: Logo Finspots centralizada, fundo azul escuro #020B3B]",
        "instrucoes": ["Se houver aposta anterior registrada, abrir com o resultado dela antes de apresentar o mês. Senão, intro padrão."],
        "formato_com_aposta_anterior": """"Olá, [nome do cliente]. Aqui é a Finspots.

No mês passado, nossa aposta era [texto da aposta anterior].

Essa aposta [✅ se confirmou / ❌ não se confirmou / ➡️ ficou neutra].

[1 frase explicando o resultado]

Agora vamos ver como foi [mês/ano] completo."​""",
        "formato_sem_aposta_anterior": """"Olá, [nome do cliente]. Aqui é a Finspots.

Esse é o seu acompanhamento mensal de [mês/ano].

Vou te mostrar como foi o mês, comparar com o mês anterior e te dizer o que fazer primeiro.

Vamos lá."​""",
    },
    {"nome": "CARD DE TRANSIÇÃO — BLOCO 1", "duracao": "2 segundos", "slide": "[CARD]", "instrucoes": [], "formato": "BLOCO 1 — COMO FOI O MÊS"},
    {
        "nome": "BLOCO 1 — STATUS DO MÊS",
        "duracao": "30 segundos",
        "slide": "[SLIDE: Página 2 do PDF]",
        "instrucoes": ["Abrir com a frase do insight STATUS_DO_MES. Destacar receita, lucro e margem líquida com contexto rápido."],
        "formato": """"[Frase do insight STATUS_DO_MES]

Receita líquida de [valor], lucro de [valor] e margem líquida de [%].

[1 frase do semáforo]

Vou detalhar cada parte agora."​""",
    },
    {
        "nome": "BLOCO 1 — RESULTADO FINANCEIRO",
        "duracao": "75 segundos",
        "slide": "[SLIDE: Página 3 do PDF]",
        "instrucoes": ["Narrar DRE fluida. CMV, MC, Lucro Líquido, Breakeven. Usar insight LUCRATIVIDADE."],
        "formato": """"No financeiro do mês: receita líquida de [valor].

A margem de contribuição ficou em [%] — [frase do semáforo].

O lucro líquido foi de [valor] — [%] de margem líquida.

[Frase do insight LUCRATIVIDADE]

Olhando a composição dos custos, o maior peso foi [maior custo] — [%] da receita. [1 frase contextualizando]

O breakeven do mês foi de [valor] — seu faturamento ficou [ACIMA / ABAIXO] desse valor."​""",
    },
    {
        "nome": "BLOCO 1 — CANAIS DO MÊS",
        "duracao": "60 segundos",
        "slide": "[SLIDE: Página 4 do PDF]",
        "instrucoes": ["Canal líder + pior desempenho. Mencionar se mudou vs mês anterior. Usar insight CANAIS."],
        "formato": """"Nos canais de venda, [canal principal] liderou o faturamento com [valor] — [%] do total.

O canal com melhor margem foi [canal] — [%].

O canal que mais preocupa é [canal] — [frase do insight CANAIS].

[Se o canal líder mudou: 'Atenção: o canal líder mudou em relação ao mês passado — antes era [canal anterior], agora é [canal atual].']

[Ação fechando]"​""",
    },
    {
        "nome": "BLOCO 1 — PRODUTOS DO MÊS",
        "duracao": "75 segundos",
        "slide": "[SLIDE: Página 5 do PDF]",
        "instrucoes": ["Top 3, produto de pior margem, produtos parados. Usar insight PORTFOLIO. Nunca listar todos os produtos."],
        "formato": """"Nos produtos, os três mais vendidos esse mês foram [Top 1], [Top 2] e [Top 3].

[Top 1] liderou com [valor] em receita e margem de [%].

O produto que mais preocupa em margem é [produto pior margem] — [%]. [Frase do insight PORTFOLIO].

Este mês tivemos [número] produtos sem nenhuma venda — capital parado no estoque.

[Se o número aumentou vs mês anterior: 'Esse número cresceu em relação ao mês passado — vale revisar esses itens antes que o problema aumente.']"​""",
    },
    {
        "nome": "BLOCO 1 — CLIENTES E MARKETING",
        "duracao": "60 segundos",
        "slide": "[SLIDE: Página 6 do PDF]",
        "instrucoes": [
            "Base de clientes com % recorrentes — sempre narra, independente de ter dado de marketing.",
            "Marketing é opcional no formulário e o público é leigo — 3 estados: sem nenhum dado de ads -> "
            "formato_sem_dados_marketing; com ROAS/%Ads mas sem CAC (sem número de novos clientes via ads) -> "
            "formato_parcial_sem_cac_marketing (narra ROAS, sinaliza que falta o CAC, nunca inventa um valor); "
            "com tudo -> formato_com_dados. Usar insights CLIENTES_RETENCAO e MARKETING (esta só quando houver dado de marketing).",
        ],
        "formato_com_dados": """"Na base de clientes: [número] novos e [número] recorrentes — [%] do total voltou pra comprar de novo.

[Frase do insight CLIENTES_RETENCAO]

No marketing: ROAS de [x] — [frase do semáforo].

O CAC ficou em [valor] por cliente.

[Frase do insight MARKETING]"​""",
        "formato_parcial_sem_cac_marketing": """"Na base de clientes: [número] novos e [número] recorrentes — [%] do total voltou pra comprar de novo.

[Frase do insight CLIENTES_RETENCAO]

No marketing: ROAS de [x] — [frase do semáforo].

Não deu pra calcular o CAC esse mês — faltou o número de novos clientes via Ads. Manda esse número no próximo mês que eu calculo certinho.

[Frase do insight MARKETING]"​""",
        "formato_sem_dados_marketing": """"Na base de clientes: [número] novos e [número] recorrentes — [%] voltou pra comprar de novo.

[Frase do insight CLIENTES_RETENCAO]

Dados de marketing não foram informados neste mês. Pra calcular ROAS e CAC no próximo mês, incluir o investimento em Ads e o número de novos clientes via Ads."​""",
    },
    {
        "nome": "CARD DE TRANSIÇÃO — BLOCO 2",
        "duracao": "2 segundos",
        "slide": "[CARD]",
        "instrucoes": ["Se primeiro mês, substituir este card e o Bloco 2 pelo texto padrão e ir direto pro Bloco 3."],
        "formato": "BLOCO 2 — A COMPARAÇÃO",
        "formato_primeiro_mes": """"Este é o primeiro mês do seu acompanhamento Finspots.

A partir do próximo mês você terá a comparação mês a mês — e vamos acompanhar juntos sua evolução."​""",
    },
    {
        "nome": "BLOCO 2 — COMPARATIVO FINANCEIRO",
        "duracao": "75 segundos",
        "slide": "[SLIDE: Página 7 do PDF]",
        "instrucoes": ["Evolução dos indicadores. Se houver aposta anterior, narrar diagnóstico de desvio (fatores controláveis vs externos). Fechar com projeção de três cenários."],
        "formato": """"Comparando com [mês anterior]:

Sua receita [subiu / caiu] [%] — de [valor anterior] pra [valor atual].

A margem líquida [melhorou de ___% pra ___% / caiu de ___% pra ___%].

O lucro [subiu / caiu] [%].

[Frase do insight COMPARATIVO_FINANCEIRO]

[Se houver desvio em relação à aposta anterior: 'O que explica essa variação: [fator controlável] teve impacto de R$___ no resultado. [Fator externo] respondeu pelo restante.']

Agora, com base nos últimos três meses, a projeção pra [mês seguinte]:

No cenário pessimista: [valor].
No cenário realista: [valor].
No cenário otimista: [valor].

O que vai definir em qual cenário você aterra é [fator decisivo]."​""",
    },
    {
        "nome": "BLOCO 2 — COMPARATIVO DE VENDAS",
        "duracao": "60 segundos",
        "slide": "[SLIDE: Página 8 do PDF]",
        "instrucoes": ["Top produto, canal líder, % recorrentes, produtos parados. Classificar mudanças como sazonalidade/tendência/evento. Usar insight TENDENCIA."],
        "formato": """"Nos produtos: o top 1 [manteve / mudou] — [se mudou: 'no mês passado era [X], agora é [Y].']

O canal líder [manteve / mudou]. [Se mudou: 'Antes era [canal anterior], agora é [canal atual].']

[Se top produto ou canal mudou: 'Essa mudança parece ser [sazonalidade esperada / uma tendência que já aparece pelo segundo mês / um evento pontual]. [Ação correspondente]']

Os clientes recorrentes [subiram / caíram] — de [%] pra [%].

[Frase do insight TENDENCIA]"​""",
    },
    {"nome": "CARD DE TRANSIÇÃO — BLOCO 3", "duracao": "2 segundos", "slide": "[CARD]", "instrucoes": [], "formato": "BLOCO 3 — O QUE FAZER AGORA"},
    {
        "nome": "BLOCO 3 — PRIORIDADES DO MÊS",
        "duracao": "90 segundos",
        "slide": "[SLIDE: Página 9 do PDF]",
        "instrucoes": ["3 prioridades do mês em ordem de score. 🔴 nunca suavizada. Impacto estimado sempre no futuro."],
        "formato": """"Agora o mais importante do mês.

Prioridade número 1: [nome do alerta].
[Ação recomendada].
[Por que importa agora — conectando com o que foi visto no vídeo]
Corrigindo isso, sua margem sai de [%] pra aproximadamente [%] — mantendo o mesmo volume de vendas.

Prioridade número 2: [nome do alerta].
[Ação recomendada].
[Contexto]
Corrigindo isso, sua margem sai de [%] pra aproximadamente [%] — mantendo o mesmo volume de vendas.

Prioridade número 3: [nome do alerta].
[Ação recomendada].
[Contexto]
Corrigindo isso, sua margem sai de [%] pra aproximadamente [%] — mantendo o mesmo volume de vendas.

Essas três ações têm o maior impacto no resultado do próximo mês."​""",
    },
    {
        "nome": "BLOCO 3 — ENCERRAMENTO",
        "duracao": "40 segundos",
        "slide": "[SLIDE: Página 10 do PDF]",
        "instrucoes": ["Frase da Prioridade #1 adaptada + recomendação personalizada + 'aposta do mês' como gancho de série pro próximo mês."],
        "formato": """"[Frase do insight PRIORIDADE, adaptada pra fala]

[Recomendação personalizada de 1–2 frases]

A aposta deste mês: [ação prioritária].
A hipótese é que [impacto esperado em % ou R$] — mantendo o volume atual.

No mês que vem, a gente abre o vídeo vendo se ganhamos ou perdemos essa aposta.

Qualquer dúvida é só me chamar no WhatsApp.

Até o mês que vem."​""",
    },
    {"nome": "CARD FINAL", "duracao": "-", "slide": "[CARD: Logo Finspots + WhatsApp — fundo azul escuro][Música fade out]", "instrucoes": [], "formato": "(sem fala — apenas card visual de encerramento)"},
]

MENSALIDADE_CHECKLIST_ROTEIRO = [
    "O nome do cliente e o mês estão corretos em todos os blocos?",
    "Cada número relevante vem com o comparativo vs mês anterior?",
    "Se for o primeiro mês, o Bloco 2 foi substituído pelo texto padrão?",
    "Cada bloco fecha com ação ou direção — nunca só com descrição?",
    "A Prioridade #1 está com tom de urgência proporcional ao score?",
    "Se o canal líder ou top produto mudou, foi mencionado e classificado?",
    "Se não há dados de marketing, foi usado o texto padrão de ausência?",
    "A recomendação final está personalizada com o contexto do mês?",
    "Nenhum bloco lê a tabela inteira — só o relevante?",
    "Nenhuma frase devolve decisão pro cliente?",
    "[PREDITIVO] A aposta anterior (se houver) foi narrada na intro?",
    "[PREDITIVO] Bloco 2: diagnóstico de desvio separou fatores controláveis de externos?",
    "[PREDITIVO] Bloco 2: projeção com três cenários foi narrada?",
    "[PREDITIVO] Bloco 2: mudança de top produto/canal foi classificada?",
    "[PREDITIVO] Bloco 3: cada prioridade tem impacto estimado narrado no futuro?",
    "[PREDITIVO] Encerramento: aposta do mês formulada como gancho de série?",
    "[PREDITIVO] Nenhuma projeção usou número único — sempre três cenários?",
]


# ============================================================================
# GEM FISCAL — CHECKLIST DE REVISÃO (7 blocos)
# Bloco 6 (Identidade Visual) só se aplica ao Relatório, não ao Roteiro.
# ============================================================================

FISCAL_BLOCO_1_DADOS_NUMEROS = """
BLOCO 1 — DADOS E NÚMEROS (o mais crítico — número errado é erro grave):
- Todos os valores em R$ batem com os dados do motor (Receita Bruta/Líquida, Lucro Líquido, Breakeven, CMV, Custos Variáveis/Fixos, Pró-labore, CAC)? → erro = 🔴 Bloqueador
- Todos os percentuais batem (MC%, ML%, %Ads, %Recorrentes, variações ▲▼)? → erro = 🔴 Bloqueador
- ROAS e ROAS de Equilíbrio corretos? → erro = 🔴 Bloqueador
- Variações ▲▼ com sinal e percentual corretos vs os dados de comparação? → erro = 🔴 Bloqueador
- Breakeven comparado corretamente com o faturamento (ACIMA/ABAIXO)? → erro = 🔴 Bloqueador
- Semáforos batem com os thresholds usados pelo motor? → erro = 🟠 Ajuste
- Prioridades em ordem de score (maior primeiro)? → erro = 🟠 Ajuste
- Dados de marketing ausentes usaram o texto padrão de ausência (não zero/vazio sem contexto)? → erro = 🟠 Ajuste
""".strip()

FISCAL_BLOCO_2_IDENTIFICACAO_CLIENTE = """
BLOCO 2 — IDENTIFICAÇÃO DO CLIENTE:
- Nome da loja correto em todas as ocorrências (capa, cabeçalhos, intro do roteiro)? → erro = 🔴 Bloqueador
- Nome escrito de forma consistente (mesma grafia em todo o documento)? → erro = 🟠 Ajuste
- Período analisado correto? → erro = 🔴 Bloqueador
- (Mensalidade) Mês de referência correto? → erro = 🔴 Bloqueador
- Categoria do negócio usada nos benchmarks bate com a categoria derivada pelo motor? → erro = 🟠 Ajuste
""".strip()

FISCAL_BLOCO_3_COMPLETUDE = """
BLOCO 3 — COMPLETUDE DO DOCUMENTO:
- Todas as páginas/blocos previstos estão presentes? (Diagnóstico: 9 páginas / Mensalidade: 10 páginas / Roteiro: todos os blocos da spec) → faltando = 🔴 Bloqueador
- Nenhum texto placeholder foi esquecido (campos como [nome do alerta], [valor], ___, [mês], [canal] ainda sem preencher)? → erro = 🔴 Bloqueador
- Nenhum bloco está vazio ou só com o título? → erro = 🔴 Bloqueador
- A página/bloco de Prioridades tem as 3 prioridades completas (nome + ação + por que importa)? → faltando = 🟠 Ajuste
- A recomendação final é específica do negócio, não genérica? → genérica = 🟠 Ajuste
- O bloco de comparativo está presente quando deveria (não é o primeiro período/mês)? Se é o primeiro, o texto padrão foi usado? → erro = 🟠 Ajuste
""".strip()

FISCAL_BLOCO_4_VOZ_ESCRITA = """
BLOCO 4 — VOZ E ESCRITA FINSPOTS (inclui camada preditiva):
- Alguma frase devolve a decisão pro cliente ("faz sentido?", "o que você acha?", "fica à vontade", "se preferir", "você decide")? → encontrou = 🟠 Ajuste
- Algum bloco termina sem ação ou direção? → encontrou = 🟠 Ajuste
- Algum número aparece sem interpretação? → encontrou = 🟠 Ajuste
- Alguma prioridade 🔴 foi suavizada? → encontrou = 🟠 Ajuste
- Algum jargão (MC, ML, ROAS, CAC, LTV, Breakeven) aparece sem explicação na primeira vez? → encontrou = 🟡 Observação
- O tom está consistente com a marca (direto, honesto, acessível, confiante)? → desvio = 🟡 Observação
- [PREDITIVO] Alguma projeção usa número único em vez de três cenários? → encontrou = 🟠 Ajuste
- [PREDITIVO] Algum contrafactual está no passado em vez do futuro? → encontrou = 🟠 Ajuste
- [PREDITIVO] Alguma projeção foi gerada sem dado suficiente (menos de 2 períodos no Diagnóstico ou 3 meses na Mensalidade)? → projeção sem base = 🔴 Bloqueador
- [DIAGNÓSTICO COMPARATIVO] Se houver comparação com percepção do cliente, o tom soa como correção/sermão ("você errou", "você não sabia", "isso mostra que você não tinha controle") em vez de trazer clareza? → encontrou = 🟠 Ajuste
- [DIAGNÓSTICO COMPARATIVO] O texto cita uma "crença do cliente" que não está em PERCEPÇÕES DECLARADAS PELO CLIENTE, ou compara com um número que não é o de DADOS DO MOTOR? → inventou percepção/comparação = 🔴 Bloqueador
""".strip()

FISCAL_BLOCO_5_ORTOGRAFIA = """
BLOCO 5 — ORTOGRAFIA E PORTUGUÊS:
- Erros de ortografia? → 🟠 Ajuste
- Erros de concordância verbal/nominal? → 🟠 Ajuste
- Erros de acentuação? → 🟠 Ajuste
- Palavras repetidas próximas sem intenção ("o negócio do negócio", "que que")? → 🟠 Ajuste
- Frases truncadas/incompletas? → 🔴 Bloqueador
- Pontuação correta (especialmente nas listas de prioridades)? → 🟡 Observação
- Valores em R$ formatados como `R$ 1.500,00`? → erro de formato = 🟠 Ajuste
- Percentuais formatados como `18%` (sem espaço)? → erro de formato = 🟡 Observação
""".strip()

FISCAL_BLOCO_6_IDENTIDADE_VISUAL = """
BLOCO 6 — IDENTIDADE VISUAL (apenas Relatório PDF, não se aplica ao Roteiro):
- Logo Finspots presente na capa? → faltando = 🔴 Bloqueador
- Semáforos usando os emojis corretos (🔴🟠🟡🟢)? → errado = 🟠 Ajuste
- Prioridades usando os emojis corretos (🔴 P1 / 🟠 P2 / 🟡 P3)? → errado = 🟠 Ajuste
- Rodapé da última página presente (WhatsApp + assinatura Finspots)? → faltando = 🟠 Ajuste
""".strip()

FISCAL_BLOCO_7_ESPECIFICO_DIAGNOSTICO = """
BLOCO 7 — ESPECÍFICO DO DIAGNÓSTICO:
- Se houver diagnóstico anterior: bloco de projeção com três cenários presente na Página 7? → faltando = 🟠 Ajuste
- Cada prioridade na Página 8 tem impacto estimado com contrafactual no futuro? → faltando = 🟠 Ajuste
- Frase de gancho para a mensalidade presente na Página 9? → faltando = 🟡 Observação
""".strip()

FISCAL_BLOCO_7_ESPECIFICO_MENSALIDADE = """
BLOCO 7 — ESPECÍFICO DA MENSALIDADE:
- Mês atual e mês anterior corretos em todos os comparativos?
- Variações ▲▼ com o sinal certo (subiu = ▲, caiu = ▼)?
- Se primeiro mês: texto padrão usado em todos os blocos de comparativo? → erro = 🔴 Bloqueador
- Aposta anterior (quando houver) foi lida — resultado está na Página 7? → faltando = 🟠 Ajuste
- Diagnóstico de desvio separou fatores controláveis de externos na Página 7? → faltando = 🟠 Ajuste
- Projeção do próximo mês com três cenários está na Página 7? → faltando = 🟠 Ajuste
- Mudança de top produto/canal classificada como sazonalidade/tendência/evento na Página 8? → faltando = 🟡 Observação
- Aposta do mês com hipótese testável está na Página 10? → faltando = 🟠 Ajuste
""".strip()

FISCAL_BLOCO_7_ESPECIFICO_ROTEIRO = """
BLOCO 7 — ESPECÍFICO DO ROTEIRO DE VÍDEO:
- Cards de transição presentes e na ordem certa?
- Intro com nome do cliente e período/mês corretos?
- Encerramento com o número do WhatsApp?
- Nenhum bloco lê a tabela inteira — só destaca o relevante?
- Todo bloco tem um texto de CARD curto (2-4 linhas), com o dado principal da fala, sem contradizer nem inventar número que não esteja na fala?
- [PREDITIVO — Mensalidade] Aposta anterior (se houver) narrada na intro?
- [PREDITIVO — Mensalidade] Aposta do mês no encerramento como gancho de série?
- [PREDITIVO — Diagnóstico] Projeção com três cenários narrada no Bloco 2 (se houver diagnóstico anterior)?
- [PREDITIVO — Diagnóstico] Impacto estimado de cada prioridade narrado no Bloco 3?
→ erro em qualquer item acima = 🟠 Ajuste
""".strip()

FISCAL_FORMATO_RELATORIO_REVISAO = """
REVISÃO FINSPOTS — [NOME DO CLIENTE] — [PRODUTO] — [DATA]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 BLOQUEADORES — [N encontrados]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Número]. [Localização — ex: Página 3 / Bloco Resultado Financeiro]
Problema: [descrição clara do erro]
Sugestão: [como corrigir]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟠 AJUSTES — [N encontrados]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Número]. [Localização]
Problema: [descrição]
Sugestão: [como corrigir]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟡 OBSERVAÇÕES — [N encontradas]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Número]. [Localização]
Observação: [descrição]
Sugestão: [opcional]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESULTADO FINAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 [N] bloqueador(es) — corrigir antes de enviar
🟠 [N] ajuste(s) — corrigir antes de enviar
🟡 [N] observação(ões) — opcional, recomendado

[STATUS FINAL:
❌ NÃO APROVADO — corrigir os bloqueadores e ajustes antes de enviar
✅ APROVADO COM OBSERVAÇÕES — pode enviar, considerar as observações
✅ APROVADO — pode enviar pro cliente]
""".strip()


def paginas_do_produto(tipo_produto_value: str) -> List[Dict[str, Any]]:
    """tipo_produto_value: 'Diagnóstico' ou 'Mensalidade'."""
    return DIAGNOSTICO_PAGINAS if tipo_produto_value == "Diagnóstico" else MENSALIDADE_PAGINAS


def blocos_video_do_produto(tipo_produto_value: str) -> List[Dict[str, Any]]:
    return DIAGNOSTICO_BLOCOS_VIDEO if tipo_produto_value == "Diagnóstico" else MENSALIDADE_BLOCOS_VIDEO


def checklist_entrega_do_produto(tipo_produto_value: str) -> List[str]:
    return DIAGNOSTICO_CHECKLIST_ENTREGA if tipo_produto_value == "Diagnóstico" else MENSALIDADE_CHECKLIST_ENTREGA


def checklist_roteiro_do_produto(tipo_produto_value: str) -> List[str]:
    return DIAGNOSTICO_CHECKLIST_ROTEIRO if tipo_produto_value == "Diagnóstico" else MENSALIDADE_CHECKLIST_ROTEIRO


def especificacoes_video_do_produto(tipo_produto_value: str) -> Dict[str, str]:
    return DIAGNOSTICO_ESPECIFICACOES_VIDEO if tipo_produto_value == "Diagnóstico" else MENSALIDADE_ESPECIFICACOES_VIDEO


def fiscal_bloco_7_do_produto(tipo_produto_value: str) -> str:
    return FISCAL_BLOCO_7_ESPECIFICO_DIAGNOSTICO if tipo_produto_value == "Diagnóstico" else FISCAL_BLOCO_7_ESPECIFICO_MENSALIDADE
