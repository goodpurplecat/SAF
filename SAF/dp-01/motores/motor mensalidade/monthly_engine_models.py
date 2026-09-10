"""
Monthly Diagnostic Engine - Data Models
Motor de Diagnóstico Mensal - Estruturas de Dados

Estrutura para acompanhamento contínuo mês a mês com:
- 12 meses em paralelo
- Comparativo automático vs mês anterior
- 8 perguntas de inteligência de vendas
- Metas real vs orçado
- Alertas de variação + alertas absolutos
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class Month(Enum):
    """Meses do ano"""
    JAN = (1, "Janeiro")
    FEV = (2, "Fevereiro")
    MAR = (3, "Março")
    ABR = (4, "Abril")
    MAI = (5, "Maio")
    JUN = (6, "Junho")
    JUL = (7, "Julho")
    AGO = (8, "Agosto")
    SET = (9, "Setembro")
    OUT = (10, "Outubro")
    NOV = (11, "Novembro")
    DEZ = (12, "Dezembro")
    
    def get_number(self):
        return self.value[0]

    def get_name(self):
        return self.value[1]


# ============================================================================
# CATEGORIA DE NEGÓCIO (A-E) — PISO DE RECORRÊNCIA
# ============================================================================
# NOVIDADE (04/09/2026): antes o alerta S1 usava um piso único de 30% de
# clientes recorrentes pra qualquer cliente. Isso não fazia sentido — um
# negócio de ticket alto (Categoria A) é saudável com recorrência bem menor
# porque o valor da venda compensa; um negócio de ticket baixo (Categoria E)
# depende de volume/recorrência alta pra se sustentar. Os números antigos
# encontrados no código (Categoria C=5%, D=10%, escritos só como texto,
# nunca usados como regra) eram de um rascunho muito antigo e não foram
# usados aqui — os valores abaixo vêm de pesquisa de mercado de taxa de
# recompra por ticket médio/nicho:
#   - Prax Analytics (1.000+ e-commerces brasileiros, ticket médio x taxa de
#     recompra por nicho): móveis/eletrônicos (ticket alto) ~10-18%; moda
#     20-30%; casa/decoração 44%; alimentos/bebidas 48%; pet shop 74%.
#   - Rivo / Flawless Magazine (benchmarks globais por vertical): luxo/
#     joalheria ~10-22%; eletrônicos ~18%; beleza 30-50%; consumíveis/FMCG
#     35-70%+; média geral de e-commerce 25-30%.
# Cada categoria tem seu próprio piso mínimo de recorrência considerado
# sustentável — abaixo dele é um problema real; acima está dentro do
# esperado pra aquele tipo de negócio, mesmo que pareça baixo em termos
# absolutos. Ajustável a qualquer momento — não depende de nenhuma
# assinatura/pesquisa paga, só editar os valores abaixo.
CATEGORY_RECURRING_FLOOR: Dict[str, float] = {
    "A": 0.12,  # Ticket alto / frequência baixa — eletrônicos, móveis, alto luxo
    "B": 0.20,  # Ticket médio-alto — moda, vestuário
    "C": 0.28,  # Ticket médio — média geral do e-commerce (perto do piso único de 30% usado antes)
    "D": 0.35,  # Ticket baixo, margem alta — beleza, cosméticos
    "E": 0.45,  # Ticket baixo, precisa de volume — alimentos, pet, consumíveis
}
DEFAULT_RECURRING_FLOOR = CATEGORY_RECURRING_FLOOR["C"]  # fallback se a categoria não vier preenchida


# Faixas de ticket médio (R$) usadas pra derivar a Categoria automaticamente
# — mesma régua e mesma fonte usadas no Motor de Diagnóstico (ver
# derive_business_category() em financial_engine_models.py). Abaixo de
# CATEGORY_TICKET_BAND_C, o desempate entre D e E usa a margem de
# contribuição do próprio mês.
CATEGORY_TICKET_BAND_A = 800.0   # ticket médio >= R$800 -> Categoria A
CATEGORY_TICKET_BAND_B = 400.0   # R$400 a R$800 -> Categoria B
CATEGORY_TICKET_BAND_C = 200.0   # R$200 a R$400 -> Categoria C
# abaixo de R$200 -> Categoria D (margem >= mc_minimum_threshold) ou E


def derive_business_category(
    avg_ticket: float,
    contribution_margin_pct: float,
    mc_minimum_threshold: float = 0.35,
) -> str:
    """
    Deriva a Categoria de negócio (A-E, como string) automaticamente a
    partir do ticket médio e da margem de contribuição do próprio mês —
    sem depender de nenhuma pergunta feita ao cliente. Espelha
    derive_business_category() do Motor de Diagnóstico (mesmos limites),
    só que retorna string em vez de BusinessCategory, pra bater com o
    formato usado no config do Motor de Mensalidade (dict simples).
    """
    if avg_ticket >= CATEGORY_TICKET_BAND_A:
        return "A"
    if avg_ticket >= CATEGORY_TICKET_BAND_B:
        return "B"
    if avg_ticket >= CATEGORY_TICKET_BAND_C:
        return "C"
    return "D" if contribution_margin_pct >= mc_minimum_threshold else "E"


def get_recurring_floor(business_category: Any) -> float:
    """
    Retorna o piso mínimo de recorrência (fração, ex.: 0.12 = 12%) para a
    Categoria de negócio informada. Aceita string ('A'..'E', maiúscula ou
    minúscula) ou um Enum com atributo .name compatível (ex.: BusinessCategory.A).
    Categoria ausente ou não reconhecida cai no piso da Categoria C (padrão
    "neutro", igual ao piso único usado antes desta correção).
    """
    key = getattr(business_category, "name", business_category)
    if isinstance(key, str):
        key = key.strip().upper()
    return CATEGORY_RECURRING_FLOOR.get(key, DEFAULT_RECURRING_FLOOR)


@dataclass
class MonthlyFinancialInput:
    """Dados financeiros para um mês específico"""
    revenue_gross: float = 0.0
    returns_cancellations: float = 0.0
    cmv: float = 0.0
    variable_costs: float = 0.0
    fixed_costs: float = 0.0
    pro_labore: float = 0.0
    num_orders: float = 0.0
    ads_investment: float = 0.0
    new_customers_ads: float = 0.0
    avg_collection_period: float = 0.0
    avg_payment_period: float = 0.0
    channel_revenues: Dict[str, float] = field(default_factory=dict)
    channel_fees: Dict[str, float] = field(default_factory=dict)


@dataclass
class SalesIntelligence:
    """As 8 perguntas de inteligência de vendas para um mês"""
    # Top Produtos
    top_1_product_name: str = ""
    top_1_product_revenue: float = 0.0
    top_1_product_margin_pct: float = 0.0
    
    top_2_product_name: str = ""
    top_2_product_revenue: float = 0.0
    top_2_product_margin_pct: float = 0.0
    
    top_3_product_name: str = ""
    top_3_product_revenue: float = 0.0
    top_3_product_margin_pct: float = 0.0
    
    # Pior Margem
    worst_product_name: str = ""
    worst_product_margin_pct: float = 0.0
    
    # Parados
    paused_products_name: str = ""
    paused_products_count: int = 0
    
    # Canais
    best_channel_name: str = ""
    best_channel_revenue: float = 0.0
    best_channel_margin_pct: float = 0.0
    
    worst_channel_name: str = ""
    worst_channel_revenue: float = 0.0
    worst_channel_margin_pct: float = 0.0
    
    # Clientes
    new_customers_count: int = 0
    recurring_customers_count: int = 0
    recurring_pct: float = 0.0
    
    # Fornecedor
    biggest_supplier_name: str = ""
    biggest_supplier_cost: float = 0.0


@dataclass
class MonthlyComparative:
    """Comparativo de um indicador: mês atual vs mês anterior"""
    current_month_value: float = 0.0
    previous_month_value: float = 0.0
    variation: float = 0.0  # Diferença absoluta
    variation_pct: float = 0.0  # Variação percentual
    status: str = ""  # 🟢 Cresceu > 10% | 🟡 Cresceu | 🟠 Queda Leve | 🔴 Queda Crítica | —


@dataclass
class MonthlyAlert:
    """Um alerta mensal com status e score"""
    code: str  # F1, V1, S1, etc
    rule: str
    is_active: bool = False
    impact: int = 0
    urgency: int = 0
    score: int = 0
    action: str = ""


@dataclass
class MonthlySummary:
    """Resumo executivo de um mês específico"""
    month: Month = Month.JAN
    client_name: str = ""
    category: str = ""
    
    # Status geral
    overall_status: str = ""
    
    # Financeiro
    revenue_net: float = 0.0
    contribution_margin_pct: float = 0.0
    profit_margin_pct: float = 0.0
    profit_net: float = 0.0
    breakeven_revenue: float = 0.0
    
    # Marketing
    roas: float = 0.0
    cac: float = 0.0
    
    # Comparativos financeiros
    # CORREÇÃO (auditoria 05/09/2026): faltava o comparativo de Margem
    # Líquida (%) — só existia o cálculo bruto em `comparatives` (ver
    # monthly_engine.py) mas nunca era guardado no summary nem exportado,
    # então a linha "Margem Líquida" da tabela do bloco COMPARATIVO
    # FINANCEIRO (templates.py) nunca tinha um valor real de variação pra
    # usar — só os 3 outros indicadores (receita, margem de contribuição,
    # lucro líquido) chegavam até a IA de Relatório e Roteiro.
    revenue_comparative: MonthlyComparative = field(default_factory=MonthlyComparative)
    margin_comparative: MonthlyComparative = field(default_factory=MonthlyComparative)          # Margem de Contribuição (%)
    profit_margin_comparative: MonthlyComparative = field(default_factory=MonthlyComparative)   # Margem Líquida (%)
    profit_comparative: MonthlyComparative = field(default_factory=MonthlyComparative)          # Lucro Líquido (R$)
    
    # Inteligência de Vendas
    sales_intel: SalesIntelligence = field(default_factory=SalesIntelligence)
    
    # Alertas
    top_3_alerts: List[MonthlyAlert] = field(default_factory=list)
    
    # Insights
    insights: Dict[str, str] = field(default_factory=dict)


@dataclass
class MonthlyGoals:
    """Metas para o mês: Real vs Orçado"""
    month: Month = Month.JAN
    
    # Metas (do CONFIG)
    goal_contribution_margin_pct: float = 0.0
    goal_profit_margin_pct: float = 0.0
    goal_profit_net: float = 0.0
    
    # Realizado (de METRICAS_MENSAL)
    actual_contribution_margin_pct: float = 0.0
    actual_profit_margin_pct: float = 0.0
    actual_profit_net: float = 0.0
    
    # Status (✅ Meta | ❌ Abaixo | —)
    mc_status: str = ""
    ml_status: str = ""
    profit_status: str = ""


@dataclass
class CompleteMonthlyDiagnostic:
    """
    Diagnóstico mensal completo para um mês específico
    Combina financeiro + vendas + metas + alertas
    """
    config: Dict[str, Any]  # Parâmetros do cliente
    reference_month: Month  # Qual mês está sendo analisado
    
    # Dados brutos
    monthly_input: MonthlyFinancialInput = field(default_factory=MonthlyFinancialInput)
    sales_intelligence: SalesIntelligence = field(default_factory=SalesIntelligence)
    
    # Cálculos financeiros
    monthly_summary: MonthlySummary = field(default_factory=MonthlySummary)
    goals: MonthlyGoals = field(default_factory=MonthlyGoals)
    
    # Alertas
    alerts: List[MonthlyAlert] = field(default_factory=list)
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class AnnualMonthlyData:
    """
    Dados de 12 meses em paralelo (para a visão anual)
    Contém todos os meses preenchidos e seus cálculos
    """
    client_name: str = ""
    year: int = 2026
    
    # Dados brutos (12 meses)
    monthly_inputs: Dict[Month, MonthlyFinancialInput] = field(default_factory=dict)
    monthly_sales_intel: Dict[Month, SalesIntelligence] = field(default_factory=dict)
    
    # Cálculos financeiros (12 meses)
    monthly_summaries: Dict[Month, MonthlySummary] = field(default_factory=dict)
    
    # Metas (12 meses)
    monthly_goals: Dict[Month, MonthlyGoals] = field(default_factory=dict)
    
    # Alertas (12 meses)
    monthly_alerts: Dict[Month, List[MonthlyAlert]] = field(default_factory=dict)
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    is_complete: bool = False  # True se todos os 12 meses foram preenchidos
