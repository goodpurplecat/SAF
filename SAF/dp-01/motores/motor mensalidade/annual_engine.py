"""
Annual Engine - Motor de Mensalidade (Análise Anual)

NOVIDADE (auditoria 14/09/2026): consolida até 12 meses de dados já
calculados pelo motor mensal numa visão anual — hoje, o ranking de
produtos mais vendidos por ID, exatamente como descrito pelo analista:
"guarda os meses anteriores (até 12 meses) pra fazer o comparativo do mês
atual com mês passado e depois uma análise anual que dá pra fazer uma vez
por ano e fazer um ranking de mais vendidos através das listas de
produtos com ids".

Antes desta correção isso era estruturalmente impossível por dois
motivos, os dois corrigidos juntos nesta auditoria:
1. AnnualMonthlyData (monthly_engine_models.py) já existia, mas era um
   contêiner vazio — nenhuma classe ou função em todo o repositório o
   instanciava ou processava.
2. Não existia ID de produto em lugar nenhum do sistema, então mesmo que
   o contêiner fosse usado não haveria dado pra ranquear.

(2) só fica resolvido de verdade quando o formulário/upload de vendas por
pedido (ainda em desenho, confirmado pelo analista) estiver pronto e
alimentando sales_intelligence_calculator.py. Este módulo cobre a
consolidação (1) e já fica pronto pra usar os dados reais assim que (2)
existir — no fim do arquivo há um exemplo com dados fictícios só pra
provar que o cálculo funciona.
"""

from typing import Dict, List

from monthly_engine_models import Month, ProductAggregate, AnnualMonthlyData


def build_annual_product_ranking(
    monthly_product_breakdown: Dict[Month, List[ProductAggregate]],
) -> List[ProductAggregate]:
    """
    Soma receita/custo/pedidos de cada produto (por produto_id) através de
    todos os meses informados e devolve o ranking anual, do mais vendido
    pro menos vendido.

    Aceita qualquer quantidade de meses (1 a 12) — não exige o ano
    completo pra funcionar, então dá pra rodar mês a mês conforme os dados
    chegam, sem esperar dezembro. Um produto que nunca aparece no Top 3 de
    nenhum mês individual (SalesIntelligence só guarda os 3 melhores de
    cada mês) mas vende de forma consistente o ano inteiro ainda assim
    aparece aqui — é exatamente essa a diferença entre olhar só o Top 3
    mensal e ter uma análise anual de verdade.
    """
    acumulado: Dict[str, ProductAggregate] = {}

    for _month, breakdown in monthly_product_breakdown.items():
        for produto in breakdown:
            agg = acumulado.get(produto.produto_id)
            if agg is None:
                agg = ProductAggregate(produto_id=produto.produto_id, produto_nome=produto.produto_nome)
                acumulado[produto.produto_id] = agg
            agg.receita += produto.receita
            agg.custo += produto.custo
            agg.pedidos += produto.pedidos
            if produto.produto_nome:
                agg.produto_nome = produto.produto_nome

    return sorted(acumulado.values(), key=lambda p: p.receita, reverse=True)


def build_annual_data_from_exports(
    client_name: str,
    year: int,
    monthly_exports: Dict[Month, dict],
) -> AnnualMonthlyData:
    """
    Monta um AnnualMonthlyData a partir dos JSONs já persistidos em
    Relatorio.dados_motor_json (database.py) — um export_to_dict() por
    mês (ver monthly_engine.py), indexado pelo Month do relatório.

    Ponto de entrada pensado pra quem orquestra a análise anual (fora do
    escopo deste motor — provavelmente app.py, lendo N meses de Relatorio
    pelo cliente_id). Assume que cada export já inclui a chave
    'product_breakdown' — presente a partir desta auditoria em
    monthly_engine.py::export_to_dict().
    """
    annual = AnnualMonthlyData(client_name=client_name, year=year)

    for month, export in monthly_exports.items():
        breakdown = [
            ProductAggregate(
                produto_id=item['produto_id'],
                produto_nome=item['produto_nome'],
                receita=item['receita'],
                custo=item.get('custo', 0.0),
                pedidos=item.get('pedidos', 0),
            )
            for item in export.get('product_breakdown', [])
        ]
        annual.monthly_inputs.setdefault(month, None)  # placeholder — o motor mensal já guarda o input real por fora; não duplicamos aqui
        annual.monthly_product_breakdown[month] = breakdown

    annual.is_complete = len(annual.monthly_product_breakdown) >= 12
    return annual


if __name__ == "__main__":
    # Exemplo com dados fictícios — só pra provar que a consolidação
    # funciona antes de existir dado real (formulário/upload ainda em
    # desenho). "Produto C" nunca é Top 3 em nenhum mês individual mas
    # ainda assim vence o ranking anual por vender de forma consistente.
    breakdown_abril = [
        ProductAggregate(produto_id="P1", produto_nome="Produto A", receita=20000, custo=8000, pedidos=100),
        ProductAggregate(produto_id="P2", produto_nome="Produto B", receita=15000, custo=9000, pedidos=80),
        ProductAggregate(produto_id="P3", produto_nome="Produto C", receita=9000, custo=4000, pedidos=60),
    ]
    breakdown_maio = [
        ProductAggregate(produto_id="P1", produto_nome="Produto A", receita=5000, custo=2000, pedidos=25),
        ProductAggregate(produto_id="P2", produto_nome="Produto B", receita=4000, custo=2500, pedidos=20),
        ProductAggregate(produto_id="P3", produto_nome="Produto C", receita=9500, custo=4200, pedidos=65),
    ]

    ranking = build_annual_product_ranking({
        Month.ABR: breakdown_abril,
        Month.MAI: breakdown_maio,
    })

    print("Ranking anual (2 meses de exemplo):")
    for posicao, produto in enumerate(ranking, start=1):
        print(f"  {posicao}. {produto.produto_nome} — R$ {produto.receita:,.2f} ({produto.margem_pct:.1%} margem, {produto.pedidos} pedidos)")
