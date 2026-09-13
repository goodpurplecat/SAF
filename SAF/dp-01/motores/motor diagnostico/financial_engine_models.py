"""
Financial Diagnostic Engine - Data Models
Motor de Diagnóstico Financeiro para E-commerce

Estrutura de classes que replicam as abas da planilha Diagnostico.xlsx
de forma independente do Google Sheets.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime


class TrafficLightStatus(Enum):
    """Enumeração para semáforos (traffic lights)"""
    CRITICAL = "🔴 Crítico"
    MINIMUM = "🟠 Mínimo"
    GOOD = "🟡 Bom"
    EXCELLENT = "🟢 Muito Bom"
    NO_DATA = "Sem dados"


class TaxRegime(Enum):
    """Regime tributário brasileiro"""
    SIMPLES_NACIONAL = "Simples Nacional"
    MEI = "MEI"
    LUCRO_PRESUMIDO = "Lucro Presumido"


class BusinessCategory(Enum):
    """Categorias de negócio por ticket e frequência"""
    A = "A - Ticket alto, frequência baixa"
    B = "B - Ticket médio-alto, frequência média/baixa"
    C = "C - Ticket médio-baixo, frequência média"
    D = "D - Ticket baixo, margem alta"
    E = "E - Ticket baixo, margem baixa"


# ============================================================================
# CATEGORIA DE NEGÓCIO (A-E) — DERIVAÇÃO AUTOMÁTICA E PISO DE RECORRÊNCIA
# ============================================================================
# NOVIDADE (04/09/2026): a Categoria deixou de ser um campo que o analista
# escolhia manualmente (o padrão em ConfigParameters.business_category
# continua existindo só como fallback). Agora ela é calculada sozinha a
# partir dos próprios números do cliente (ticket médio + margem de
# contribuição, ambos já coletados pro DRE) — sem nenhuma pergunta nova no
# formulário, então o cliente nunca vê nada relacionado a "categoria".
# Ver `derive_business_category()` abaixo e o uso em financial_engine.py.
#
# Os pisos de recorrência por categoria (mesma lógica e mesmos números do
# Motor de Mensalidade, ver CATEGORY_RECURRING_FLOOR em
# monthly_engine_models.py) vêm da mesma pesquisa de mercado de taxa de
# recompra por ticket médio/nicho (Prax Analytics — 1.000+ e-commerces
# brasileiros; Rivo/Flawless Magazine — benchmarks globais por vertical).
CATEGORY_RECURRING_FLOOR: Dict[str, float] = {
    "A": 0.12,  # Ticket alto / frequência baixa — eletrônicos, móveis, alto luxo
    "B": 0.20,  # Ticket médio-alto — moda, vestuário
    "C": 0.28,  # Ticket médio — média geral do e-commerce
    "D": 0.35,  # Ticket baixo, margem alta — beleza, cosméticos
    "E": 0.45,  # Ticket baixo, precisa de volume — alimentos, pet, consumíveis
}
DEFAULT_RECURRING_FLOOR = CATEGORY_RECURRING_FLOOR["C"]  # fallback se a categoria não vier preenchida

# Faixas de ticket médio (R$) usadas pra derivar a categoria automaticamente.
# Baseadas na mesma pesquisa de mercado (ticket médio por nicho — Prax
# Analytics): móveis/eletrônicos R$1.950-2.782 (A); moda/vestuário na faixa
# intermediária (B); "média geral" do e-commerce (C); cosméticos/alimentos
# R$173-182 (ticket baixo — D ou E, desempatado pela margem de contribuição,
# já que a diferença entre D e E é justamente "margem alta" x "margem
# baixa", não o ticket). Ajustável a qualquer momento.
CATEGORY_TICKET_BAND_A = 800.0   # ticket médio >= R$800 -> Categoria A
CATEGORY_TICKET_BAND_B = 400.0   # R$400 a R$800 -> Categoria B
CATEGORY_TICKET_BAND_C = 200.0   # R$200 a R$400 -> Categoria C
# abaixo de R$200 -> Categoria D (margem >= mc_minimum_threshold) ou E (margem menor)


def derive_business_category(
    avg_ticket: float,
    contribution_margin_pct: float,
    mc_minimum_threshold: float = 0.35,
) -> "BusinessCategory":
    """
    Deriva a Categoria de negócio (A-E) automaticamente a partir do ticket
    médio e da margem de contribuição do próprio cliente — sem depender de
    nenhuma pergunta feita a ele. Ticket alto -> A; ticket baixo se separa
    entre D (margem alta, reaproveita o mesmo piso de margem de contribuição
    já usado nos semáforos MC) e E (margem baixa).
    """
    if avg_ticket >= CATEGORY_TICKET_BAND_A:
        return BusinessCategory.A
    if avg_ticket >= CATEGORY_TICKET_BAND_B:
        return BusinessCategory.B
    if avg_ticket >= CATEGORY_TICKET_BAND_C:
        return BusinessCategory.C
    return BusinessCategory.D if contribution_margin_pct >= mc_minimum_threshold else BusinessCategory.E


def get_recurring_floor(business_category: Any) -> float:
    """
    Retorna o piso mínimo de recorrência (fração, ex.: 0.12 = 12%) para a
    Categoria informada. Aceita BusinessCategory (usa .name) ou string
    ('A'..'E'). Categoria ausente/não reconhecida cai no piso da Categoria C.
    """
    key = getattr(business_category, "name", business_category)
    if isinstance(key, str):
        key = key.strip().upper()
    return CATEGORY_RECURRING_FLOOR.get(key, DEFAULT_RECURRING_FLOOR)


class SalesChannel(Enum):
    """
    Canais de venda conhecidos — lista ampliada (05/09/2026, pedido do
    analista: "o público que vou atender é só a galera do e-commerce, então
    tenho que ter o máximo de opções possível") pra cobrir os marketplaces e
    plataformas mais comuns entre lojistas brasileiros.

    Ter um canal aqui SÓ dá acesso à taxa de referência automática (ver
    config/taxas_canais.json) — não ter um canal aqui NÃO impede o cliente
    de usá-lo: desde 05/09/2026, um canal que o cliente declara mas não
    está nesta lista passa a entrar no cálculo mesmo assim, como texto livre
    (ver nome_canal() logo abaixo e FinancialInput.channel_revenues) —
    só entra sem taxa de referência (considerado 0% até alguém informar a
    taxa real via channel_fees_custom). Ou seja: adicionar um canal AQUI é
    só uma conveniência (taxa automática) — nunca um bloqueio.

    Ainda assim, adicionar aqui os canais mais comuns entre nossos clientes
    vale a pena, porque poupa o analista de digitar a taxa manualmente toda
    vez. Pra adicionar: uma linha aqui + uma linha em
    config/taxas_canais.json (ver _carregar_taxas_canais_config() abaixo).
    """
    MERCADO_LIVRE = "Mercado Livre"
    SHOPEE = "Shopee"
    AMAZON = "Amazon"
    SHOPIFY = "Shopify / Loja Própria"
    NUVEMSHOP = "Nuvemshop"
    TIKTOK_SHOP = "TikTok Shop"
    INSTAGRAM = "Instagram / WhatsApp"
    MAGALU = "Magazine Luiza (Magalu)"
    AMERICANAS = "Americanas"
    CASAS_BAHIA = "Casas Bahia"
    SHEIN = "Shein (Marketplace)"
    ALIEXPRESS = "AliExpress"
    CARREFOUR = "Carrefour Marketplace"
    DAFITI = "Dafiti"
    KABUM = "Kabum"
    NETSHOES = "Netshoes"
    ELO7 = "Elo7"
    ENJOEI = "Enjoei"
    OLX = "OLX"
    VTEX = "Loja Própria (VTEX)"
    TRAY = "Tray"
    LOJA_INTEGRADA = "Loja Integrada"
    WOOCOMMERCE = "WooCommerce"
    WIX = "Wix"


def nome_canal(canal: Any) -> str:
    """
    Nome em texto de um canal, seja ele um SalesChannel conhecido (usa
    `.value`) ou um canal customizado declarado pelo cliente/analista (já é
    uma string, devolve como está). Use esta função em vez de `.value`
    direto sempre que precisar do nome do canal em texto (relatórios,
    export_to_dict) — `.value` direto quebra (AttributeError) se o canal
    for uma string customizada.
    """
    return canal.value if isinstance(canal, SalesChannel) else str(canal)


# ============================================================================
# TAXAS DE CANAL — CARREGADAS DE config/taxas_canais.json
# ============================================================================
# NOVIDADE (05/09/2026): antes as taxas de cada canal (Mercado Livre 16%,
# Shopee 14%, etc.) eram um dicionário Python fixo, direto no default de
# ConfigParameters.channel_fees — atualizar uma taxa exigia editar este
# arquivo .py. Isso incomoda porque essas taxas mudam "de tempos em tempos"
# (pedido do analista, 05/09/2026) e quem faz essa atualização não precisa
# necessariamente saber mexer em Python. Agora elas moram em
# config/taxas_canais.json (na raiz do repositório) — editar o número lá e
# salvar já vale na próxima vez que ConfigParameters() for criado. Sem
# argumento explícito de channel_fees, é sempre isso que roda; passar
# channel_fees=... ou usar FinancialInput.channel_fees_custom (por
# cliente) continua funcionando normalmente, por cima deste default.
_CAMINHO_CONFIG_TAXAS_CANAIS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
    "config", "taxas_canais.json",
)

# Fallback se o JSON não existir/estiver corrompido — mesmos valores que já
# eram o default antes desta mudança, então nada quebra mesmo sem o arquivo.
_TAXAS_CANAIS_FALLBACK: Dict[str, float] = {
    "Mercado Livre": 0.16,
    "Shopee": 0.14,
    "Amazon": 0.12,
    "Shopify / Loja Própria": 0.03,
    "Nuvemshop": 0.02,
    "TikTok Shop": 0.06,
    "Instagram / WhatsApp": 0.0,
    "Magazine Luiza (Magalu)": 0.17,
    "Americanas": 0.15,
    "Casas Bahia": 0.20,
    "Shein (Marketplace)": 0.16,
    "AliExpress": 0.06,
    "Carrefour Marketplace": 0.16,
    "Dafiti": 0.27,
    "Kabum": 0.18,
    "Netshoes": 0.20,
    "Elo7": 0.18,
    "Enjoei": 0.20,
    "OLX": 0.0,
    "Loja Própria (VTEX)": 0.03,
    "Tray": 0.03,
    "Loja Integrada": 0.03,
    "WooCommerce": 0.03,
    "Wix": 0.03,
}


def _carregar_taxas_canais_config() -> Dict["SalesChannel", float]:
    """
    Lê config/taxas_canais.json e converte os nomes (texto) pra SalesChannel
    (enum). Um canal no JSON que não bate com nenhum SalesChannel conhecido
    (nome digitado errado, ou um canal novo que ainda não foi adicionado ao
    enum — ver comentário em SalesChannel) é ignorado com um aviso no
    console, não trava o motor. Se o arquivo inteiro não puder ser lido, cai
    no fallback embutido acima — o motor sempre sobe, na pior das hipóteses
    com taxas desatualizadas, nunca quebrado.
    """
    try:
        with open(_CAMINHO_CONFIG_TAXAS_CANAIS, "r", encoding="utf-8") as f:
            bruto = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        print(f"[financial_engine_models] ⚠️  Não foi possível ler config/taxas_canais.json "
              f"({type(e).__name__}) — usando taxas padrão embutidas.")
        bruto = _TAXAS_CANAIS_FALLBACK

    taxas: Dict["SalesChannel", float] = {}
    for nome, taxa in bruto.items():
        if nome.startswith("_"):  # "_comentario" e afins — não é canal
            continue
        try:
            taxas[SalesChannel(nome)] = float(taxa)
        except ValueError:
            print(f"[financial_engine_models] ⚠️  Canal '{nome}' em config/taxas_canais.json "
                  f"não é reconhecido (ver SalesChannel em financial_engine_models.py) — ignorado.")
    return taxas


@dataclass
class ConfigParameters:
    """
    Configuração do cliente - equivalente à aba CONFIG.
    Define todos os thresholds, parâmetros tributários e de semáforo.
    """
    # Identificação
    client_name: str = ""
    analysis_period: str = ""
    business_category: BusinessCategory = BusinessCategory.B
    
    # Tributário
    tax_regime: TaxRegime = TaxRegime.SIMPLES_NACIONAL
    tax_rate: float = 0.04  # 4% para Simples Nacional Anexo I
    
    # Semáforos - Margem de Contribuição (MC)
    mc_critical_threshold: float = 0.20      # < 20%
    mc_minimum_threshold: float = 0.35       # 20-35%
    mc_good_threshold: float = 0.45          # 35-45%
    # > 45% é excellent
    
    # Semáforos - Margem Líquida (ML)
    ml_critical_threshold: float = 0.0       # < 0%
    ml_minimum_threshold: float = 0.10       # 0-10%
    ml_good_threshold: float = 0.20          # 10-20%
    # > 20% é excellent
    
    # Semáforos - ROAS
    roas_critical_threshold: float = 2.0     # < 2x
    roas_minimum_threshold: float = 3.0      # 2-3x
    roas_good_threshold: float = 5.0         # 3-5x
    # > 5x é excellent
    
    # Semáforos - % Ads (inverso - menor é melhor)
    ads_excellent_threshold: float = 0.10    # < 10%
    ads_good_threshold: float = 0.20         # 10-20%
    ads_minimum_threshold: float = 0.30      # 20-30%
    # > 30% é crítico
    
    # Semáforos - LTV:CAC
    ltv_cac_critical_threshold: float = 1.0  # < 1x
    ltv_cac_minimum_threshold: float = 3.0   # 1-3x (risco)
    ltv_cac_good_threshold: float = 5.0      # 3-5x
    # > 5x é excellent
    
    # Parâmetros de LTV — alinhados com CONFIG!B41/B42 da planilha de referência
    # CORREÇÃO (04/09/2026): campos antigos (avg_repurchase_rate × retention_rate
    # como fração) misturavam uma contagem de recompras com uma probabilidade,
    # sem nenhum componente de tempo — não formavam um "valor vitalício" de
    # verdade. Trocado pela fórmula padrão de LTV simplificado (Ticket ×
    # Frequência de recompra/ano × Anos de retenção), igual à planilha.
    repurchase_frequency_per_year: float = 2.0   # Quantas vezes o cliente compra por ano
    retention_years: float = 2.0                  # Por quantos anos o cliente costuma comprar
    
    # Fluxo de caixa
    cycle_critical_threshold: int = 30       # > 30 dias é crítico
    cycle_alert_threshold: int = 60          # Para alerta lucro vs caixa
    
    # Canais de venda com taxas padrão — lidas de config/taxas_canais.json
    # (ver _carregar_taxas_canais_config() acima). Passar channel_fees=...
    # explicitamente aqui continua funcionando normalmente (sobrescreve o
    # arquivo por completo, não faz merge) — é só o default que mudou.
    channel_fees: Dict[SalesChannel, float] = field(default_factory=_carregar_taxas_canais_config)


@dataclass
class FinancialInput:
    """
    Dados de entrada brutos do cliente - equivalente à aba INPUT.
    O analista preenche apenas esses campos.
    """
    # Obrigatório - Financeiro
    analysis_period: str = ""
    revenue_gross: float = 0.0              # Receita bruta
    returns_cancellations: float = 0.0      # Devoluções e cancelamentos
    cmv: float = 0.0                        # Custo das mercadorias vendidas
    variable_costs: float = 0.0             # Custos variáveis (taxas, frete, embalagem)
    fixed_costs: float = 0.0                # Custos fixos (aluguel, funcionários)
    pro_labore: float = 0.0                 # Salário do sócio
    num_orders: float = 0.0                 # Número de pedidos
    
    # Opcional - Marketing
    ads_investment: float = 0.0             # Investimento em anúncios
    new_customers_ads: float = 0.0          # Novos clientes via ads
    primary_ads_channel: str = ""           # Canal principal de ads
    
    # Opcional - Fluxo de Caixa
    avg_collection_period: float = 0.0      # PMR - Prazo médio de recebimento
    avg_payment_period: float = 0.0         # PMP - Prazo médio de pagamento
    
    # Opcional - Canais de venda (faturamento por canal)
    channel_revenues: Dict[SalesChannel, float] = field(default_factory=dict)
    channel_fees_custom: Dict[SalesChannel, float] = field(default_factory=dict)

    # Opcional - Retenção (novidade 04/09/2026)
    # % de clientes recorrentes no período analisado (fração, ex.: 0.25 =
    # 25%). Optional/None (não 0.0) de propósito — permite diferenciar "não
    # informado" de "informado como zero", pra não gerar alerta falso quando
    # esse dado simplesmente não foi preenchido (mesmo cuidado já tomado no
    # alerta S1 do Motor de Mensalidade). Ver alerta R1 em
    # financial_engine_diagnostic.py.
    recurring_customers_pct: Optional[float] = None

    def validate(self) -> tuple[bool, list[str]]:
        """Valida se dados obrigatórios foram preenchidos"""
        errors = []
        
        if self.revenue_gross <= 0:
            errors.append("Receita bruta deve ser maior que zero")
        if self.num_orders <= 0:
            errors.append("Número de pedidos deve ser maior que zero")
        if self.cmv < 0:
            errors.append("CMV não pode ser negativo")
        if self.variable_costs < 0:
            errors.append("Custos variáveis não podem ser negativos")
        if self.fixed_costs < 0:
            errors.append("Custos fixos não podem ser negativos")
        
        return len(errors) == 0, errors


@dataclass
class ValidatedData:
    """
    Dados validados e sanitizados - equivalente à aba BASE_TRATADA.
    Garante que nenhum valor vazio ou inválido quebre os cálculos.
    """
    period: str = ""
    revenue_gross: float = 0.0
    returns_cancellations: float = 0.0
    cmv: float = 0.0
    variable_costs: float = 0.0
    fixed_costs: float = 0.0
    pro_labore: float = 0.0
    num_orders: float = 0.0
    ads_investment: float = 0.0
    new_customers_ads: float = 0.0
    primary_ads_channel: str = "Não informado"
    avg_collection_period: float = 0.0
    avg_payment_period: float = 0.0
    channel_revenues: Dict[SalesChannel, float] = field(default_factory=dict)
    channel_fees: Dict[SalesChannel, float] = field(default_factory=dict)
    recurring_customers_pct: Optional[float] = None

    validation_status: Dict[str, str] = field(default_factory=dict)


@dataclass
class DREResults:
    """
    Demonstração do Resultado do Exercício (DRE) - equivalente à aba DRE.
    Estrutura contábil completa.
    """
    revenue_gross: float = 0.0
    returns_cancellations: float = 0.0
    revenue_net: float = 0.0
    
    taxes: float = 0.0
    cmv: float = 0.0
    profit_gross: float = 0.0
    
    variable_costs: float = 0.0
    contribution_margin: float = 0.0
    
    fixed_costs: float = 0.0
    pro_labore: float = 0.0
    # CORREÇÃO (auditoria 13/09/2026, confirmado pela analista contra a
    # planilha Diagnostico.xlsx original): investimento em ads é dinheiro de
    # verdade saindo do caixa do cliente — quando ele existe, tem que
    # descontar do Lucro Líquido. Fica de fora da Margem de Contribuição de
    # propósito (ela é definida só com os custos variáveis operacionais —
    # plataforma+frete+embalagem+comissões — nunca incluiu ads, nem na
    # planilha original) e entra como uma linha própria, igual custos
    # fixos/pró-labore, só na conta final.
    ads_investment: float = 0.0
    profit_net: float = 0.0

    # Percentuais
    tax_pct: float = 0.0
    cmv_pct: float = 0.0
    profit_gross_pct: float = 0.0
    variable_costs_pct: float = 0.0
    contribution_margin_pct: float = 0.0
    fixed_costs_pct: float = 0.0
    pro_labore_pct: float = 0.0
    ads_investment_pct: float = 0.0
    profit_net_pct: float = 0.0


@dataclass
class MarketingMetrics:
    """Métricas de marketing - equivalente à aba MARKETING"""
    ads_investment: float = 0.0
    revenue_net: float = 0.0
    ads_pct_revenue: float = 0.0
    
    roas: float = 0.0                       # Return on Ad Spend
    roas_breakeven: float = 0.0             # ROAS mínimo para não ter prejuízo
    
    cac: float = 0.0                        # Custo por cliente adquirido
    avg_ticket: float = 0.0                 # Ticket médio
    
    ltv_simplified: float = 0.0             # LTV estimado
    ltv_cac_ratio: float = 0.0              # LTV:CAC estimado
    
    primary_ads_channel: str = ""
    
    roas_traffic_light: TrafficLightStatus = TrafficLightStatus.NO_DATA
    ads_pct_traffic_light: TrafficLightStatus = TrafficLightStatus.NO_DATA


@dataclass
class ChannelPerformance:
    """
    Desempenho de um canal de venda.

    NOVIDADE (05/09/2026, pedido do analista): `channel` aceita tanto um
    SalesChannel (canal conhecido, com taxa de referência em
    config/taxas_canais.json) quanto uma string livre (canal que o cliente
    usa mas não está na nossa lista — o próprio cliente/analista declara o
    nome). O type hint continua SalesChannel só de referência/autocomplete;
    Python não impõe isso em runtime, e é exatamente o que permite um canal
    customizado passar sem quebrar. Ver nome_canal() logo abaixo — todo
    código que precisa do NOME em texto (relatórios, export_to_dict) deve
    usar essa função em vez de `.value` direto, porque uma string simples
    não tem `.value`.
    """
    channel: SalesChannel
    revenue: float = 0.0
    fee_rate: float = 0.0
    fee_cost: float = 0.0
    cmv_proportional: float = 0.0
    margin: float = 0.0
    margin_pct: float = 0.0
    margin_traffic_light: TrafficLightStatus = TrafficLightStatus.NO_DATA


@dataclass
class CashFlowAnalysis:
    """Análise de fluxo de caixa - equivalente à aba FLUXO_CAIXA"""
    avg_collection_period: float = 0.0      # PMR
    avg_payment_period: float = 0.0         # PMP
    financial_cycle: float = 0.0            # Ciclo financeiro (PMR - PMP)
    
    cycle_status: str = ""
    cycle_traffic_light: TrafficLightStatus = TrafficLightStatus.NO_DATA
    
    profit_vs_cash_alert: str = ""


@dataclass
class Alert:
    """Um alerta individual no sistema de diagnóstico"""
    code: str                               # F1, F2, M1, etc
    rule: str                               # Descrição da regra
    is_active: bool = False                 # SIM/NÃO
    impact: int = 0                         # 1-5
    urgency: int = 0                        # 1-5
    score: int = 0                          # Impact × Urgency
    action: str = ""                        # Ação recomendada


@dataclass
class DiagnosticSummary:
    """Resumo executivo final - equivalente às abas RESUMO_EXECUTIVO + INSIGHTS"""
    # Identificação
    client_name: str = ""
    analysis_period: str = ""
    business_category: str = ""
    
    # Status geral
    overall_status: TrafficLightStatus = TrafficLightStatus.NO_DATA
    
    # Financeiro
    revenue_net: float = 0.0
    contribution_margin_pct: float = 0.0
    profit_margin_pct: float = 0.0
    profit_net: float = 0.0
    breakeven_revenue: float = 0.0
    
    # Marketing
    roas: float = 0.0
    roas_breakeven: float = 0.0
    cac: float = 0.0
    
    # Canais
    top_channel_by_revenue: str = ""
    top_channel_by_margin: str = ""
    worst_channel: str = ""
    
    # Fluxo de caixa
    financial_cycle_days: float = 0.0
    
    # Top 3 prioridades
    top_3_priorities: list[Alert] = field(default_factory=list)
    
    # Insights em linguagem natural
    insights: Dict[str, str] = field(default_factory=dict)


@dataclass
class CompleteDiagnostic:
    """
    Diagnóstico completo - agrupa todas as abas em um objeto.
    Este é o resultado final que alimenta os agentes de IA.
    """
    config: ConfigParameters
    input_data: FinancialInput
    validated_data: ValidatedData = field(default_factory=ValidatedData)
    dre: DREResults = field(default_factory=DREResults)
    marketing: MarketingMetrics = field(default_factory=MarketingMetrics)
    channels: list[ChannelPerformance] = field(default_factory=list)
    cashflow: CashFlowAnalysis = field(default_factory=CashFlowAnalysis)
    alerts: list[Alert] = field(default_factory=list)
    summary: DiagnosticSummary = field(default_factory=DiagnosticSummary)
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    is_valid: bool = False
    validation_errors: list[str] = field(default_factory=list)
