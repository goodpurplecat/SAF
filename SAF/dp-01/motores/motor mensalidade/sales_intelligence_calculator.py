"""
Sales Intelligence Calculator - Motor de Mensalidade

NOVIDADE (auditoria 14/09/2026): calcula as "8 Perguntas de Negócio"
(SalesIntelligence, em monthly_engine_models.py) automaticamente, a partir
de dados brutos de pedido — exatamente como o plano original (motores.pdf)
sempre descreveu: "respondidas AUTOMATICAMENTE... usando MAX, MIN, AVERAGE
e outras regras de comparação... cruzando IDs de produto e de cliente".

Antes desta correção, SalesIntelligence era preenchido 100% à mão — não
existia, em lugar nenhum do sistema (banco, extração por IA, motores), um
único campo de ID de produto ou de cliente (ver Parte 4 / achado 3 da
auditoria "Promessa x Código"). Este módulo resolve o CÁLCULO. Ele não
resolve, sozinho, a ENTRADA de dado: confirmado pelo analista em
14/09/2026, o cliente vai subir arquivo (planilha própria ou export
baixado de canais como Mercado Livre) através de um formulário/upload que
ainda está sendo desenhado. Enquanto esse desenho não existir, não dá pra
saber o formato exato de cada arquivo bruto (colunas, nomes, se vem em
BRL ou centavos, etc.) — e inventar esse formato aqui seria o mesmo erro
que este sistema evita em todo o resto do código (ver
dp-01/tratamento/extratora.py: "Nunca inventar dados").

O que ESTE módulo assume, e é o único contrato que importa pra ele
funcionar: os dados brutos, seja qual for a origem, já chegam como uma
lista de OrderLine (ver monthly_engine_models.py) — uma linha por item
vendido, com produto_id/cliente_id/canal/receita já identificados. Quando
o formulário/upload for desenhado, o trabalho que falta é escrever um
adaptador por canal (Mercado Livre, Shopee, planilha própria...) que leia
o arquivo bruto de verdade e produza essa lista — este módulo já fica
pronto pra consumi-la assim que existir.
"""

from typing import Dict, List, Optional, Set

from monthly_engine_models import OrderLine, ProductAggregate, SalesIntelligence


class SalesIntelligenceResult:
    """
    Saída completa do cálculo: o SalesIntelligence pronto pra entrar direto
    em MonthlyDiagnosticEngineMain.run_monthly_diagnostic() (mesmo
    parâmetro `sales_intel` de sempre — nada no motor mensal precisa mudar
    pra consumir isso) + o detalhamento completo por produto, usado pra
    persistir a série histórica que alimenta o ranking anual.
    """
    def __init__(self, sales_intelligence: SalesIntelligence, product_breakdown: List[ProductAggregate]):
        self.sales_intelligence = sales_intelligence
        self.product_breakdown = product_breakdown


def calculate_sales_intelligence(
    order_lines: List[OrderLine],
    previous_month_product_ids: Optional[Set[str]] = None,
    known_customer_ids: Optional[Set[str]] = None,
) -> SalesIntelligenceResult:
    """
    Calcula as 8 Perguntas de Negócio por fórmula determinística
    (MAX/MIN/soma/contagem agrupada por produto_id/cliente_id/canal) —
    nunca por estimativa ou IA. Espelha, em Python, exatamente o tipo de
    fórmula que uma aba de planilha (INPUT_VENDAS) faria com
    PROCV/SOMASE/MÁXIMO/MÍNIMO, só que operando sobre pedidos individuais
    em vez de totais já prontos.

    order_lines: pedidos do mês corrente, já normalizados (ver OrderLine).
        Lista vazia devolve um SalesIntelligence zerado (mesmo default de
        sempre) — nunca inventa produto/cliente que não veio nos dados.

    previous_month_product_ids: IDs de produto que venderam no(s) mês(es)
        anterior(es) — usado só para achar "produtos parados" (vendiam
        antes, zero pedidos este mês). Sem isso, paused_products_count sai
        0 (não dá pra saber quem "parou" sem saber quem vendia antes —
        mesmo princípio conservador usado no resto do sistema quando falta
        histórico, ex.: S1 em monthly_engine_diagnostic.py).

    known_customer_ids: todo cliente_id já visto em meses anteriores —
        usado pra separar cliente novo x recorrente. Sem isso, todo
        cliente do mês conta como "novo" (mesma lógica conservadora).
    """
    if not order_lines:
        return SalesIntelligenceResult(SalesIntelligence(), [])

    previous_month_product_ids = previous_month_product_ids or set()
    known_customer_ids = known_customer_ids or set()

    # ------------------------------------------------------------------
    # Agregação por produto (produto_id) — base do Top 3, Pior Margem e
    # Produtos Parados.
    # ------------------------------------------------------------------
    produtos: Dict[str, ProductAggregate] = {}
    for line in order_lines:
        agg = produtos.get(line.produto_id)
        if agg is None:
            agg = ProductAggregate(produto_id=line.produto_id, produto_nome=line.produto_nome)
            produtos[line.produto_id] = agg
        agg.receita += line.receita
        agg.custo += line.custo
        agg.pedidos += 1
        if line.produto_nome:
            agg.produto_nome = line.produto_nome  # nome mais recente, caso o anúncio tenha sido renomeado

    product_breakdown = sorted(produtos.values(), key=lambda p: p.receita, reverse=True)

    # Top 3 por receita (MAX)
    top3 = product_breakdown[:3]

    # Pior margem (MIN) — entre os produtos com venda este mês
    worst_product = min(product_breakdown, key=lambda p: p.margem_pct) if product_breakdown else None

    # Parados: tinham venda no(s) mês(es) anterior(es), zero pedidos este mês
    current_product_ids = set(produtos.keys())
    paused_ids = sorted(previous_month_product_ids - current_product_ids)

    # ------------------------------------------------------------------
    # Agregação por canal — melhor/pior canal (perguntas 6-7).
    # ------------------------------------------------------------------
    canais: Dict[str, ProductAggregate] = {}
    for line in order_lines:
        agg = canais.get(line.canal)
        if agg is None:
            agg = ProductAggregate(produto_id=line.canal, produto_nome=line.canal)
            canais[line.canal] = agg
        agg.receita += line.receita
        agg.custo += line.custo
        agg.pedidos += 1

    canais_por_receita = sorted(canais.values(), key=lambda c: c.receita, reverse=True)
    best_channel = canais_por_receita[0] if canais_por_receita else None
    worst_channel = min(canais_por_receita, key=lambda c: c.margem_pct) if canais_por_receita else None

    # ------------------------------------------------------------------
    # Clientes: novo x recorrente (pergunta 8) — via cliente_id, não estimativa.
    # ------------------------------------------------------------------
    clientes_do_mes = {line.cliente_id for line in order_lines if line.cliente_id}
    recorrentes = clientes_do_mes & known_customer_ids
    novos = clientes_do_mes - known_customer_ids
    total_clientes = len(clientes_do_mes)
    recurring_pct = (len(recorrentes) / total_clientes) if total_clientes > 0 else 0.0

    sales_intel = SalesIntelligence(
        top_1_product_name=top3[0].produto_nome if len(top3) > 0 else "",
        top_1_product_revenue=top3[0].receita if len(top3) > 0 else 0.0,
        top_1_product_margin_pct=top3[0].margem_pct if len(top3) > 0 else 0.0,

        top_2_product_name=top3[1].produto_nome if len(top3) > 1 else "",
        top_2_product_revenue=top3[1].receita if len(top3) > 1 else 0.0,
        top_2_product_margin_pct=top3[1].margem_pct if len(top3) > 1 else 0.0,

        top_3_product_name=top3[2].produto_nome if len(top3) > 2 else "",
        top_3_product_revenue=top3[2].receita if len(top3) > 2 else 0.0,
        top_3_product_margin_pct=top3[2].margem_pct if len(top3) > 2 else 0.0,

        worst_product_name=worst_product.produto_nome if worst_product else "",
        worst_product_margin_pct=worst_product.margem_pct if worst_product else 0.0,

        paused_products_name=", ".join(paused_ids),
        paused_products_count=len(paused_ids),

        best_channel_name=best_channel.produto_nome if best_channel else "",
        best_channel_revenue=best_channel.receita if best_channel else 0.0,
        best_channel_margin_pct=best_channel.margem_pct if best_channel else 0.0,

        worst_channel_name=worst_channel.produto_nome if worst_channel else "",
        worst_channel_revenue=worst_channel.receita if worst_channel else 0.0,
        worst_channel_margin_pct=worst_channel.margem_pct if worst_channel else 0.0,

        new_customers_count=len(novos),
        recurring_customers_count=len(recorrentes),
        recurring_pct=recurring_pct,

        # biggest_supplier_* fica de fora de propósito: fornecedor não é
        # algo derivável de um pedido de venda (produto/cliente/canal) —
        # continua sendo um dado à parte, fora do escopo deste cálculo.
    )

    return SalesIntelligenceResult(sales_intel, product_breakdown)
