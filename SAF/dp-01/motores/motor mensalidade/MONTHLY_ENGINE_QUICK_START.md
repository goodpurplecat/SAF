# 🚀 Monthly Diagnostic Engine - Quick Start

Motor de Diagnóstico Mensal em Python - Acompanhamento contínuo mês a mês com comparativos automáticos.

## 📦 O que você recebeu

3 módulos Python:
- `monthly_engine_models.py` - Estruturas de dados (com suporte a 12 meses)
- `monthly_engine_calculator.py` - Motor de cálculos mensais
- `monthly_engine_diagnostic.py` - Sistema de 13 alertas (F1-F6, V1-V3, S1-S4)
- `monthly_engine.py` - Orquestrador principal

## ⚡ Teste rápido

```bash
python3 monthly_engine.py
```

Você verá um diagnóstico mensal completo com:
- DRE do mês
- Comparativos vs mês anterior
- 8 perguntas de inteligência de vendas
- Metas real vs orçado
- 13 alertas automáticos com scoring
- Insights em linguagem natural

## 💻 Como usar

```python
from monthly_engine import MonthlyDiagnosticEngineMain
from monthly_engine_models import *

# Config
config = {
    'client_name': 'Meu Cliente',
    'business_category': 'B',
    'tax_rate': 0.04,
    'goal_mc_pct': 0.40,
    'goal_ml_pct': 0.15,
    'goal_profit_net': 5000,
}

# Dados de Abril
april_input = MonthlyFinancialInput(
    revenue_gross=150000,
    cmv=45000,
    variable_costs=22500,
    fixed_costs=25000,
    pro_labore=5000,
    num_orders=600,
    ads_investment=15000,
    new_customers_ads=300,
)

# Inteligência de Vendas (8 perguntas)
sales_intel = SalesIntelligence(
    top_1_product_name="Produto Premium",
    top_1_product_revenue=45000,
    best_channel_name="Shopify",
    recurring_pct=0.45,
    paused_products_count=0,
)

# Executar
engine = MonthlyDiagnosticEngineMain(config)
diagnostic = engine.run_monthly_diagnostic(
    Month.ABR,
    april_input,
    sales_intel,
)

# Resultado
print(diagnostic.monthly_summary.overall_status)
print(diagnostic.monthly_summary.insights)
```

## 📊 13 Alertas Automáticos

### Grupo F: Financeiros Absolutos (F1-F6)
- F1: MC Crítica (< 20%) → Score 25
- F2: MC Mínima (20-35%) → Score 9
- F3: ML Negativa (Prejuízo) → Score 25
- F4: ML Mínima (0-10%) → Score 16
- F5: Faturamento < Breakeven → Score 25
- F6: ROAS < Equilíbrio → Score 16

### Grupo V: Variação Financeira (V1-V3)
- V1: Receita caiu vs mês anterior → Score 16
- V2: Lucro caiu significativamente (> 20%) → Score 25
- V3: Margem líquida caiu → Score 20

### Grupo S: Inteligência de Vendas (S1-S4)
- S1: Clientes recorrentes baixos (< 30%) → Score 16
- S2: Produto com margem negativa → Score 12
- S3: Muitos produtos parados (> 10) → Score 9
- S4: Canal líder com margem mínima (< 10%) → Score 9

## 🎯 O que é diferente do Diagnóstico

| Aspecto | Diagnóstico | Mensalidade |
|---------|-------------|-------------|
| Periodicidade | Pontual (uma vez) | Contínua (12 meses) |
| Comparativo | Não tem | Automático vs mês anterior |
| Inteligência Vendas | Não tem | 8 perguntas mensais |
| Metas | Não tem | Real vs orçado |
| Alertas de variação | Não tem | 3 novos tipos (V1-V3) |

## 💡 8 Perguntas de Negócio

A aba INPUT_VENDAS responde:
1. Top 3 produtos mais vendidos (nome, receita, margem)
2. Produto com pior margem
3. Produtos parados no mês
4. Canal com melhor desempenho
5. Canal com pior desempenho
6. Clientes novos vs recorrentes
7. Quantidade de produtos sem venda
8. Fornecedor com maior custo

## 🔄 Fluxo de Dados

```
INPUT_FINANCEIRO (12 meses)
      ↓
BASE_TRATADA_FIN (validação)
      ↓
DRE_MENSAL (cada mês)
      ↓
METRICAS_MENSAL (indicadores)
      ↓
COMPARATIVO_VENDAS (mês vs mês anterior)
      ↓
EVOLUCAO_FINANCEIRA (variações)
      ↓
ALERTAS_MENSAL (13 regras)
      ↓
JSON ESTRUTURADO (para IA/PDF/Vídeo)
```

## 📈 Exemplo de Saída

```json
{
  "client_name": "E-commerce Mensal",
  "month": "Abril",
  "overall_status": "🟢 SAUDÁVEL",
  "financial": {
    "revenue_net": 142500.0,
    "profit_margin_pct": 0.276,
    "profit_net": 39300.0
  },
  "goals": {
    "contribution_margin": {
      "goal": 0.40,
      "actual": 0.38,
      "status": "❌ Abaixo"
    }
  },
  "insights": {
    "STATUS_DO_MES": "Em Abril, seu negócio estava 🟢 SAUDÁVEL...",
    "COMPARATIVO_FINANCEIRO": "vs mês anterior: Receita 🟢 Cresceu > 10%..."
  }
}
```

## 🚀 Próximos Passos

1. Integrate com seu DB de clientes
2. Processaos 12 meses em paralelo
3. Gere PDF com insights
4. Crie vídeo narrado com TTS
5. Integre com agentes de IA

**Tudo pronto! Comece agora! 🎉**
