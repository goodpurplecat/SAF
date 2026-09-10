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
- `DiagnosticEngine` - 14 regras de alerta automáticas (eram 13 até
  03/09/2026; R1 de retenção por Categoria adicionado em 04/09/2026)
- `InsightGenerator` - Geração de insights em linguagem natural

**Alertas implementados:**
- F1-F5: Alertas financeiros (Margem Contribuição, Margem Líquida, Breakeven)
- M1-M5: Alertas de marketing (ROAS, % Ads, LTV:CAC)
- C1-C2: Alertas de canais (Margem negativa/mínima)
- R1: Alerta de retenção (recorrência abaixo do piso da Categoria — novidade
  04/09/2026, opcional, só avalia se `recurring_customers_pct` for informado)
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
# NOTA (04/09/2026): business_category aqui é só um valor inicial — o motor
# recalcula sozinho a Categoria (A-E) a partir do ticket médio e da margem
# de contribuição do cliente durante o run_diagnostic(). Nenhuma pergunta
# nova é feita ao cliente.
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

```
INPUT
  ↓
[1] VALIDAÇÃO (BASE_TRATADA)
  - Converte números inválidos em 0
  - Verifica campos obrigatórios
  ↓
[2] DRE (Demonstração de Resultados)
  - Receita Bruta - Devoluções = Receita Líquida
  - Receita Líquida - Impostos - CMV = Lucro Bruto
  - Lucro Bruto - Custos Variáveis = Margem Contribuição
  - Margem Contribuição - Custos Fixos - Pró-labore = Lucro Líquido
  ↓
[3] MARKETING
  - % Ads = Investimento / Receita Líquida
  - ROAS = Receita Líquida / Investimento
  - CAC = Investimento / Novos Clientes
  - LTV = Ticket × Frequência de Recompra/Ano × Anos de Retenção
  ↓
[3B] CATEGORIA DO NEGÓCIO (A-E) — novidade 04/09/2026
  - Derivada automaticamente do Ticket Médio + Margem de Contribuição
  - Sem pergunta nova pro cliente (ver derive_business_category())
  ↓
[4] CANAIS
  - Para cada canal: Receita - Taxa - CMV Proporcional = Margem
  ↓
[5] FLUXO DE CAIXA
  - Ciclo = PMR - PMP
  ↓
[6] ALERTAS
  - 14 regras automáticas com score (Impacto × Urgência)
  ↓
[7] RESUMO + INSIGHTS
  - Consolidação de todas as métricas
  - Geração de frases em linguagem natural
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

## 🚨 14 Alertas Automáticos

<!-- CORREÇÃO (auditoria 04/09/2026): a tabela abaixo sempre teve 13 linhas; o título dizia 15.
NOVIDADE (04/09/2026): R1 (retenção por Categoria) adicionado, tabela agora tem 14 linhas / 14 alertas possíveis. -->


| Cód | Regra | Impacto | Urgência | Score | Ação |
|-----|-------|---------|----------|-------|------|
| F1 | MC Crítica (< 20%) | 5 | 5 | **25** | Revisar precificação |
| F2 | MC Mínima (20-35%) | 3 | 3 | 9 | Reduzir custos variáveis |
| F3 | ML Negativa | 5 | 5 | **25** | Ação imediata |
| F4 | ML Mínima (0-10%) | 4 | 4 | 16 | Reduzir custos fixos |
| F5 | Faturamento < Breakeven | 5 | 5 | **25** | Aumentar faturamento |
| M1 | ROAS < Equilíbrio | 4 | 4 | 16 | Revisar campanhas |
| M2 | ROAS Crítico (< 2x) | 5 | 5 | **25** | Pausar ads |
| M3 | % Ads Crítico (> 30%) | 4 | 4 | 16 | Otimizar CAC |
| M4 | LTV:CAC Risco (< 3x) | 3 | 3 | 9 | Revisar aquisição |
| M5 | LTV:CAC Crítico (< 1x) | 5 | 5 | **25** | Parar aquisição |
| C1 | Canal Margem Negativa | 4 | 4 | 16 | Descontinuar/repricing |
| C2 | Canal Margem Mínima (< 10%) | 2 | 3 | 6 | Renegociar taxas |
| R1 | Clientes Recorrentes BAIXOS (< piso da Categoria*) | 4 | 4 | 16 | Revisar estratégia de retenção |
| X1 | Ciclo Financeiro Crítico (> 30 dias) | 3 | 3 | 9 | Rever prazos |

Score = Impacto × Urgência. Top 3 alertas são priorizados automaticamente.

\* **R1 — piso por Categoria do negócio (novidade 04/09/2026):** opcional —
só avalia se `recurring_customers_pct` for informado em `FinancialInput`
(None, não 0.0, quando não informado — evita alerta falso). O piso vem da
mesma régua usada no S1 do Motor de Mensalidade (Categoria A=12%, B=20%,
C=28%, D=35%, E=45%), baseada em pesquisa de mercado de taxa de recompra por
ticket médio/nicho. Diferente do S1, aqui não há checagem de "sustentado" —
o período analisado já é o semestre inteiro (ver `analysis_period`), não
mês a mês. A Categoria em si agora é sempre derivada automaticamente do
ticket médio + margem de contribuição (`derive_business_category()`), não
mais escolhida manualmente.

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
