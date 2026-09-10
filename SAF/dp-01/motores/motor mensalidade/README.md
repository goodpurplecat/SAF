# 🚀 Financial Diagnostic Engine - Python

Motor de Diagnóstico Financeiro em Python puro. Replicação completa da planilha `Diagnostico.xlsx` do FinSpots, agora como sistema independente, escalável e pronto para integração com agentes de IA.

---

## 📋 O que você ganha

✅ **Independência do Sheets** - Executa diagnósticos sem Google Sheets  
✅ **Assincronismo** - Processa múltiplos clientes em paralelo  
✅ **Agentes de IA** - Saída estruturada em JSON pronta para Claude/GPT  
✅ **Velocidade** - Diagnóstico completo em <100ms  
✅ **Precisão** - Fórmulas idênticas às do Excel, linha por linha  
✅ **Manutenção fácil** - Código legível, modular, bem documentado  

---

## 🏗️ Arquitetura

O motor é dividido em 4 módulos independentes:

```
┌─────────────────────────────────────────┐
│  financial_engine.py (Orquestrador)     │
│  - Main entry point                     │
│  - Coordena todo o fluxo                │
│  - Exporta JSON para APIs               │
└──────────────────┬──────────────────────┘
                   │
         ┌─────────┴─────────┬──────────────────┬────────────────┐
         │                   │                  │                │
    ┌────▼─────┐    ┌────────▼────────┐  ┌─────▼──────┐  ┌────▼──────────┐
    │ MODELS   │    │ CALCULATOR      │  │ DIAGNOSTIC │  │ INSIGHTS      │
    │ (Abas)   │    │ (Fórmulas)      │  │ (Alertas)  │  │ (Narrativa)   │
    └──────────┘    └─────────────────┘  └────────────┘  └───────────────┘
    • CONFIG       • DRE               • 15 Alertas     • Blocos de texto
    • INPUT        • MARKETING         • Prioridades   • Frases automáticas
    • BASE_TRATADA • CANAIS            • Scoring       • Contextualizadas
    • DRE          • FLUXO_CAIXA       • Status Geral
    • MARKETING    • Semáforos
    • CANAIS
    • FLUXO_CAIXA
```

---

## 📦 Módulos

### 1. `financial_engine_models.py`
Define todas as estruturas de dados (dataclasses) que correspondem às abas da planilha.

**Classes principais:**
- `ConfigParameters` - Configuração do cliente (equivalente à aba CONFIG)
- `FinancialInput` - Dados de entrada brutos (equivalente à aba INPUT)
- `ValidatedData` - Dados validados (equivalente à aba BASE_TRATADA)
- `DREResults` - Demonstração de Resultados (equivalente à aba DRE)
- `MarketingMetrics` - Métricas de marketing (equivalente à aba MARKETING)
- `ChannelPerformance` - Desempenho por canal (equivalente à aba CANAIS)
- `CashFlowAnalysis` - Análise de fluxo de caixa (equivalente à aba FLUXO_CAIXA)
- `CompleteDiagnostic` - Diagnóstico completo consolidado

### 2. `financial_engine_calculator.py`
Motor de cálculos financeiros. Replicaexatamente as fórmulas do Excel em Python.

**Métodos principais:**
- `validate_and_sanitize()` - BASE_TRATADA: validação e sanitização
- `calculate_dre()` - DRE: demonstração de resultados
- `calculate_marketing_metrics()` - MARKETING: ROAS, CAC, LTV
- `calculate_channel_performance()` - CANAIS: margem por canal
- `calculate_cashflow()` - FLUXO_CAIXA: ciclo financeiro

### 3. `financial_engine_diagnostic.py`
Motor de diagnóstico com alertas automáticos e geração de insights.

**Classes:**
- `DiagnosticEngine` - 15 regras de alerta automáticas
- `InsightGenerator` - Geração de insights em linguagem natural

**Alertas implementados:**
- F1-F5: Alertas financeiros (Margem Contribuição, Margem Líquida, Breakeven)
- M1-M5: Alertas de marketing (ROAS, % Ads, LTV:CAC)
- C1-C2: Alertas de canais (Margem negativa/mínima)
- X1: Alertas de fluxo de caixa (Ciclo crítico)

### 4. `financial_engine.py`
Orquestrador principal que une tudo.

**Classe:**
- `FinancialDiagnosticEngine` - Ponto de entrada único

---

## 🚀 Como usar

### Exemplo básico

```python
from financial_engine import FinancialDiagnosticEngine
from financial_engine_models import *

# 1. Configurar cliente
config = ConfigParameters(
    client_name="E-commerce XYZ",
    analysis_period="Jan–Jun/2025",
    business_category=BusinessCategory.B,
    tax_regime=TaxRegime.SIMPLES_NACIONAL,
    tax_rate=0.04,
)

# 2. Preencher dados de entrada
input_data = FinancialInput(
    analysis_period="Jan–Jun/2025",
    revenue_gross=500000.0,
    returns_cancellations=25000.0,
    cmv=150000.0,
    variable_costs=80000.0,
    fixed_costs=50000.0,
    pro_labore=10000.0,
    num_orders=2000,
    ads_investment=40000.0,
    new_customers_ads=800,
    primary_ads_channel="Meta Ads",
    avg_collection_period=15.0,
    avg_payment_period=30.0,
    channel_revenues={
        SalesChannel.SHOPIFY: 300000.0,
        SalesChannel.MERCADO_LIVRE: 150000.0,
    }
)

# 3. Instanciar motor
engine = FinancialDiagnosticEngine(config)

# 4. Executar diagnóstico
diagnostic = engine.run_diagnostic(input_data)

# 5. Acessar resultados
if diagnostic.is_valid:
    print(f"Status: {diagnostic.summary.overall_status.value}")
    print(f"Margem Líquida: {diagnostic.dre.profit_net_pct:.1%}")
    print(f"ROAS: {diagnostic.marketing.roas:.1f}x")
    
    # Top 3 prioridades
    for alert in diagnostic.summary.top_3_priorities:
        print(f"- {alert.rule} (Score: {alert.score})")
```

---

## 🔄 Fluxo de dados

<!-- CORREÇÃO (04/09/2026): este diagrama estava copiado do README do Motor de
Diagnóstico (etapas de VALIDAÇÃO/CANAIS/FLUXO DE CAIXA que não existem aqui) e
não refletia o fluxo real de run_monthly_diagnostic() (monthly_engine.py). -->

```
MonthlyFinancialInput (do mês) + SalesIntelligence (do mês)
  ↓
[1] DRE DO MÊS
  - Receita Bruta - Devoluções = Receita Líquida
  - Receita Líquida - Impostos - CMV = Lucro Bruto
  - Lucro Bruto - Custos Variáveis = Margem Contribuição
  - Margem Contribuição - Custos Fixos - Pró-labore = Lucro Líquido
  ↓
[2] MÉTRICAS DO MÊS
  - Ticket Médio, Breakeven, ROAS, CAC, LTV, LTV:CAC
  ↓
[2B] CATEGORIA DO NEGÓCIO (A-E) — novidade 04/09/2026
  - Derivada automaticamente do Ticket Médio + Margem de Contribuição do mês
  - Sem pergunta nova pro cliente (ver derive_business_category())
  ↓
[3] COMPARATIVOS vs mês anterior
  - Receita, Margem de Contribuição, Margem Líquida, Lucro Líquido
  ↓
[4] METAS
  - Real vs Orçado (Margem de Contribuição, Margem Líquida, Lucro Líquido)
  ↓
[5] ALERTAS
  - 15 regras automáticas com score (Impacto × Urgência)
  ↓
[6] RESUMO + INSIGHTS
  - Top 3 alertas do mês
  - 10 blocos de insight em linguagem natural
  ↓
SAÍDA JSON (pronto para IA/PDF/Vídeo)
```

---

## 📊 Exportar para JSON

Para integração com APIs e agentes de IA:

```python
# Exportar diagnóstico completo para dicionário
diagnosis_dict = engine.export_to_dict(diagnostic)

# Converter para JSON
import json
json_string = json.dumps(diagnosis_dict, indent=2, ensure_ascii=False)

# Ou enviar para API
import requests
requests.post("https://api.seu-servidor.com/diagnostic", json=diagnosis_dict)
```

**Estrutura do JSON:**
```json
{
  "client_name": "E-commerce XYZ",
  "analysis_period": "Jan–Jun/2025",
  "generated_at": "2026-09-03T21:45:05.950379",
  "overall_status": "🟢 Muito Bom",
  
  "financial": {
    "revenue_net": 475000.0,
    "contribution_margin": {"amount": 226000.0, "percentage": 0.476},
    "profit_net": {"amount": 166000.0, "percentage": 0.349},
    "breakeven_revenue": 126106.19
  },
  
  "marketing": {
    "ads_investment": 40000.0,
    "roas": 11.9,
    "cac": 50.0,
    "ltv_cac_ratio": 2.1
  },
  
  "channels": [
    {
      "name": "Shopify / Loja Própria",
      "revenue": 300000.0,
      "margin": {"amount": 196263.16, "percentage": 0.654}
    }
  ],
  
  "alerts": [
    {
      "code": "M4",
      "rule": "LTV:CAC em RISCO (< 3x)",
      "score": 9,
      "action": "Revisar estratégia de aquisição"
    }
  ],
  
  "insights": {
    "STATUS_GERAL": "Seu negócio está 🟢 Muito Bom...",
    "LUCRATIVIDADE": "Lucro líquido de R$ 166.000...",
    ...
  }
}
```

---

## 🔧 Configuração e Semáforos

Todos os thresholds são configuráveis no `ConfigParameters`:

```python
config = ConfigParameters(
    # Semáforos - Margem de Contribuição
    mc_critical_threshold=0.20,      # < 20% = 🔴
    mc_minimum_threshold=0.35,       # 20-35% = 🟠
    mc_good_threshold=0.45,          # 35-45% = 🟡
    # > 45% = 🟢
    
    # Semáforos - ROAS
    roas_critical_threshold=2.0,     # < 2x = 🔴
    roas_minimum_threshold=3.0,      # 2-3x = 🟠
    roas_good_threshold=5.0,         # 3-5x = 🟡
    # > 5x = 🟢
    
    # Semáforos - Margem Líquida
    ml_critical_threshold=0.0,       # < 0% = 🔴
    ml_minimum_threshold=0.10,       # 0-10% = 🟠
    ml_good_threshold=0.20,          # 10-20% = 🟡
    # > 20% = 🟢
    
    # Parâmetros de LTV (CORREÇÃO 04/09/2026: alinhados com CONFIG!B41/B42 da planilha)
    repurchase_frequency_per_year=2.0,  # Quantas vezes o cliente compra por ano
    retention_years=2.0,                 # Por quantos anos o cliente costuma comprar
)
```

---

## 🚨 15 Alertas Automáticos

<!-- CORREÇÃO (auditoria 04/09/2026): esta tabela estava copiada do README do Motor
de Diagnóstico (F1-F5, M1-M5, C1-C2, X1) e não refletia as regras reais deste motor,
que são F1-F6, M4-M5, V1-V3, S1-S4 (ver monthly_engine_diagnostic.py). -->

| Cód | Regra | Impacto | Urgência | Score | Ação |
|-----|-------|---------|----------|-------|------|
| F1 | Margem Contribuição CRÍTICA (< 20%) | 5 | 5 | **25** | Revisar precificação e custos variáveis com urgência |
| F2 | Margem Contribuição MÍNIMA (20–35%) | 3 | 3 | 9 | Identificar custos variáveis redutíveis |
| F3 | Margem Líquida NEGATIVA — Prejuízo | 5 | 5 | **25** | Prejuízo no mês — ação imediata obrigatória |
| F4 | Margem Líquida MÍNIMA (0–10%) | 4 | 4 | 16 | Custos comprometendo o resultado |
| F5 | Faturamento ABAIXO do Breakeven | 5 | 5 | **25** | Aumentar faturamento ou reduzir custos fixos |
| F6 | ROAS abaixo do Equilíbrio | 4 | 4 | 16 | Ads gerando prejuízo — revisar campanhas |
| M4 | LTV:CAC em RISCO (< 3x) — ESTIMATIVA | 3 | 3 | 9 | Revisar estratégia de aquisição |
| M5 | LTV:CAC CRÍTICO (< 1x) — ESTIMATIVA | 5 | 5 | **25** | Perde dinheiro em cada cliente adquirido |
| V1 | Receita Líquida CAIU vs mês anterior | 4 | 4 | 16 | Investigar causa da queda de faturamento |
| V2 | Lucro Líquido CAIU significativamente | 5 | 5 | **25** | Identificar gargalo principal da queda |
| V3 | Margem Líquida CAIU | 4 | 5 | 20 | Analisar variação de custos fixos ou pró-labore |
| S1 | Clientes Recorrentes BAIXOS (< piso da Categoria*) | 4 | 4 | 16 | Base de clientes perdendo fidelização — revisar retenção |
| S2 | Produto com Margem NEGATIVA | 4 | 3 | 12 | Revisar precificação/custo do produto |
| S3 | Produtos Parados AUMENTARAM (> 10) | 3 | 3 | 9 | Risco de estoque parado e capital preso |
| S4 | Canal Líder com Margem MÍNIMA (< 10%) | 3 | 3 | 9 | Verificar se precificação ou taxa do canal mudou |

Score = Impacto × Urgência. Top 3 alertas são priorizados automaticamente.
M4/M5 (LTV:CAC) foram adicionados em 04/09/2026 para dar paridade com o Motor de
Diagnóstico, que já os tinha.

\* **S1 — piso por Categoria do negócio (novidade 04/09/2026):** antes o piso de
recorrência era fixo em 30% pra qualquer cliente. Agora cada Categoria (A-E) tem
seu próprio piso mínimo, baseado em pesquisa de mercado de taxa de recompra por
ticket médio/nicho (Prax Analytics, Rivo, Flawless Magazine — ver comentário em
`monthly_engine_models.py`, constante `CATEGORY_RECURRING_FLOOR`):

| Categoria | Piso de recorrência |
|-----------|---------------------|
| A (ticket alto, frequência baixa) | 12% |
| B (ticket médio-alto) | 20% |
| C (ticket médio) | 28% |
| D (ticket baixo, margem alta) | 35% |
| E (ticket baixo, precisa de volume) | 45% |

Um negócio Categoria A com 15% de recorrência não dispara mais o S1 (ticket alto
compensa a baixa recorrência); o mesmo 15% numa Categoria E dispara, porque sem
volume alto o negócio não se sustenta. Os mesmos números aparecem como texto no
bloco "Categoria do Negócio" do Motor de Diagnóstico, para consistência entre os
dois motores.

**Categoria 100% automática (novidade 04/09/2026):** `business_category` no
config deixou de ser um valor manual — a cada `run_monthly_diagnostic()`, o
motor deriva a Categoria sozinho a partir do ticket médio e da margem de
contribuição *daquele mês* (mesma régua do Motor de Diagnóstico: ticket
≥R$800=A, R$400-800=B, R$200-400=C, <R$200 desempatado pela margem em D/E).
Sem pergunta nova no formulário. Como isso roda todo mês, a Categoria de um
mesmo cliente pode variar de mês a mês se o ticket/margem mudar muito — na
prática isso é raro (o perfil de um negócio não muda mês a mês), mas é bom
ter em mente. Função: `derive_business_category()` em
`monthly_engine_models.py`.

**Sustentado x queda pontual (novidade 04/09/2026):** o S1 só dispara "cheio"
quando o mês atual **e** os 2 meses anteriores estão todos abaixo do piso da
Categoria — 3 meses seguidos (o mesmo horizonte já usado no insight de
TENDÊNCIA). Uma queda de um único mês isolado não dispara mais o alerta. Isso
depende do chamador passar `recurring_pct_history` (lista com o `recurring_pct`
dos meses anteriores) para `run_monthly_diagnostic(...)`; sem esse histórico
(ex.: cliente novo, ainda sem 2 meses anteriores registrados), o alerta volta a
avaliar só o mês atual — pra não deixar passar um problema real só por falta de
dado histórico. O número de meses é ajustável em
`SUSTAINED_LOW_FREQUENCY_MONTHS`, em `monthly_engine_diagnostic.py`.

---

## 🤖 Integração com Agentes de IA

O motor já exporta em JSON estruturado. Use assim:

```python
from anthropic import Anthropic

client = Anthropic()

# Gerar diagnóstico
diagnostic = engine.run_diagnostic(input_data)
diagnosis_json = engine.export_to_dict(diagnostic)

# Passar para agente de IA
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2000,
    messages=[
        {
            "role": "user",
            "content": f"""
            Você é um analista financeiro especialista em e-commerce.
            
            Aqui está o diagnóstico financeiro completo de um cliente:
            
            {json.dumps(diagnosis_json, indent=2, ensure_ascii=False)}
            
            Por favor:
            1. Resuma o status geral em 1 parágrafo
            2. Explique os 3 problemas principais e suas consequências
            3. Proponha 3 ações concretas para melhorar
            4. Escreva o roteiro para um vídeo de 3 minutos apresentando este diagnóstico
            """
        }
    ]
)

print(response.content[0].text)
```

---

## 📈 Performance

- **Validação**: ~5ms
- **Cálculos**: ~20ms
- **Alertas**: ~10ms
- **Insights**: ~15ms
- **Total**: <100ms para diagnóstico completo

Podem rodar ~10 diagnósticos por segundo em série, ou centenas em paralelo com `asyncio`.

---

## 🔄 Migração a partir da Planilha Excel

Se você tem dados já preenchidos na planilha `Diagnostico.xlsx`:

```python
import openpyxl
from financial_engine import FinancialDiagnosticEngine
from financial_engine_models import *

# Ler Excel
wb = openpyxl.load_workbook('Diagnostico.xlsx')

# Extrair CONFIG
config_ws = wb['CONFIG']
config = ConfigParameters(
    client_name=config_ws['B4'].value,
    analysis_period=config_ws['B5'].value,
    tax_rate=float(config_ws['B9'].value) or 0.04,
)

# Extrair INPUT
input_ws = wb['INPUT']
input_data = FinancialInput(
    analysis_period=input_ws['B4'].value,
    revenue_gross=float(input_ws['B5'].value) or 0,
    returns_cancellations=float(input_ws['B6'].value) or 0,
    cmv=float(input_ws['B7'].value) or 0,
    variable_costs=float(input_ws['B8'].value) or 0,
    fixed_costs=float(input_ws['B9'].value) or 0,
    pro_labore=float(input_ws['B10'].value) or 0,
    num_orders=float(input_ws['B11'].value) or 0,
    ads_investment=float(input_ws['B13'].value) or 0,
    new_customers_ads=float(input_ws['B14'].value) or 0,
)

# Rodar diagnóstico
engine = FinancialDiagnosticEngine(config)
diagnostic = engine.run_diagnostic(input_data)
```

---

## 📝 Testes

Para testar o motor:

```bash
python3 financial_engine.py
```

Isso roda o exemplo incluído e exibe o JSON completo.

---

## 🎯 Próximos passos

1. **API REST** - Criar endpoint Flask/FastAPI
2. **Geração de PDF** - Exportar diagnóstico como relatório
3. **Vídeo narrado** - Integrar com TTS (Text-to-Speech) e geração de vídeo
4. **Dashboard** - Visualização web dos diagnósticos
5. **Histórico** - Comparar diagnósticos ao longo do tempo
6. **Benchmarks** - Comparar cliente contra outros da mesma categoria

---

## 📄 Licença

Desenvolvimento interno FinSpots | Abril/2026

---

**Desenvolvido com ❤️ em Python puro - zero dependências de Google Sheets**
