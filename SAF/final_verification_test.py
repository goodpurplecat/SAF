"""
Reverificação final pós-correções (auditoria 04/09/2026).
Roda o mesmo caso de teste do briefing ("Loja Premium Test", Abril/2026)
contra os DOIS motores (Diagnóstico e Mensalidade), a partir da raiz do
repositório, exatamente como um usuário seguindo o README faria.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("TESTE 1: MOTOR DE DIAGNÓSTICO (import a partir da raiz)")
print("=" * 70)

from financial_engine import FinancialDiagnosticEngine
from financial_engine_models import FinancialInput, ConfigParameters, BusinessCategory

config = ConfigParameters(
    client_name="Loja Premium Test",
    business_category=BusinessCategory.B,
    tax_rate=0.04,
)

input_data = FinancialInput(
    revenue_gross=500000,
    returns_cancellations=25000,
    cmv=150000,
    variable_costs=80000,
    fixed_costs=50000,
    pro_labore=10000,
    num_orders=2000,
    ads_investment=40000,
    new_customers_ads=500,
    avg_collection_period=7,
    avg_payment_period=30,
)

engine = FinancialDiagnosticEngine(config)
diagnostic = engine.run_diagnostic(input_data)

print(f"Receita Líquida: R$ {diagnostic.dre.revenue_net:,.2f}")
print(f"MC%: {diagnostic.dre.contribution_margin_pct:.2%}")
print(f"ML%: {diagnostic.dre.profit_net_pct:.2%}")
print(f"Lucro Líquido: R$ {diagnostic.dre.profit_net:,.2f}")
print(f"ROAS: {diagnostic.marketing.roas:.2f}x")
print(f"CAC: R$ {diagnostic.marketing.cac:.2f}")
print(f"LTV: R$ {diagnostic.marketing.ltv_simplified:.2f}")
print(f"LTV:CAC: {diagnostic.marketing.ltv_cac_ratio:.2f}x")
print(f"Total de alertas: {len(diagnostic.alerts)}")
for a in diagnostic.alerts:
    print(f"  - {a.code}: {a.rule} (score {a.score})")

# export_to_dict deve funcionar sem erro e sem depender de summary.summary morto
export = diagnostic.export_to_dict() if hasattr(diagnostic, "export_to_dict") else engine.export_to_dict(diagnostic)
assert export is not None
print("export_to_dict() executado sem erro. ✅")

print()
print("=" * 70)
print("TESTE 2: MOTOR DE MENSALIDADE (import a partir da raiz)")
print("=" * 70)

from monthly_engine import MonthlyDiagnosticEngineMain
from monthly_engine_models import Month, MonthlyFinancialInput, SalesIntelligence

config_m = {
    "client_name": "Loja Premium Test",
    "year": 2026,
    "business_category": "B",  # valor inicial só — o motor deriva sozinho e sobrescreve (04/09/2026)
    "tax_rate": 0.04,
}

monthly_input = MonthlyFinancialInput(
    revenue_gross=500000,
    returns_cancellations=25000,
    cmv=150000,
    variable_costs=80000,
    fixed_costs=50000,
    pro_labore=10000,
    num_orders=2000,
    ads_investment=40000,
    new_customers_ads=500,
    avg_collection_period=7,
    avg_payment_period=30,
)

sales_intel = SalesIntelligence(
    top_1_product_name="Produto Premium",
    top_1_product_revenue=150000,
    top_1_product_margin_pct=0.55,
    best_channel_name="Shopify",
    best_channel_revenue=300000,
    best_channel_margin_pct=0.60,
    worst_channel_name="Mercado Livre",
    worst_channel_revenue=150000,
    worst_channel_margin_pct=0.25,
    new_customers_count=400,
    recurring_customers_count=350,
    recurring_pct=0.45,
    paused_products_count=3,
)

engine_m = MonthlyDiagnosticEngineMain(config_m)
diagnostic_m = engine_m.run_monthly_diagnostic(Month.ABR, monthly_input, sales_intel)

print(f"Receita Líquida: R$ {diagnostic_m.monthly_summary.revenue_net:,.2f}")
print(f"MC%: {diagnostic_m.monthly_summary.contribution_margin_pct:.2%}")
print(f"ML%: {diagnostic_m.monthly_summary.profit_margin_pct:.2%}")
print(f"Lucro Líquido: R$ {diagnostic_m.monthly_summary.profit_net:,.2f}")
print(f"Total de alertas: {len(diagnostic_m.alerts)}")
for a in diagnostic_m.alerts:
    print(f"  - {a.code}: {a.rule} (score {a.score})")

m4_m5 = [a for a in diagnostic_m.alerts if a.code in ("M4", "M5")]
print()
if m4_m5:
    print(f"✅ Alerta(s) de LTV:CAC disparado(s) no motor Mensal: {[(a.code, a.score) for a in m4_m5]}")
else:
    print("⚠️  Nenhum alerta M4/M5 disparado no motor Mensal.")

print()
print("=" * 70)
print("TESTE 3: COERÊNCIA ENTRE OS DOIS MOTORES")
print("=" * 70)
diag_codes = {a.code for a in diagnostic.alerts}
mensal_codes = {a.code for a in diagnostic_m.alerts if a.code in ("M4", "M5")}
print(f"Alertas M4/M5 no Diagnóstico: {sorted(diag_codes & {'M4', 'M5'})}")
print(f"Alertas M4/M5 na Mensalidade: {sorted(mensal_codes)}")
if (diag_codes & {"M4", "M5"}) == mensal_codes:
    print("✅ Paridade M4/M5 entre os dois motores confirmada.")
else:
    print("❌ Divergência entre os motores!")

print()
print("=" * 70)
print("TESTE 4: REGRESSÃO — SalesIntelligence vazia não deve gerar falso S1/S4")
print("=" * 70)
sales_vazio = SalesIntelligence(
    top_1_product_name="",
    top_1_product_revenue=0,
    top_1_product_margin_pct=0,
    best_channel_name="",
    best_channel_revenue=0,
    best_channel_margin_pct=0,
    worst_channel_name="",
    worst_channel_revenue=0,
    worst_channel_margin_pct=0,
    new_customers_count=0,
    recurring_customers_count=0,
    recurring_pct=0.0,
    paused_products_count=0,
)
diagnostic_vazio = engine_m.run_monthly_diagnostic(Month.ABR, monthly_input, sales_vazio)
s_codes = [a.code for a in diagnostic_vazio.alerts if a.code in ("S1", "S4")]
if not s_codes:
    print("✅ Nenhum falso S1/S4 disparado com SalesIntelligence vazia.")
else:
    print(f"❌ Falso positivo: {s_codes}")

print()
print("=" * 70)
print("TESTE 5: CATEGORIA DE NEGÓCIO MODULA O PISO DO ALERTA S1 (04/09/2026)")
print("=" * 70)
sales_intel_15pct = SalesIntelligence(
    top_1_product_name="Produto Premium",
    top_1_product_revenue=45000,
    top_1_product_margin_pct=0.55,
    best_channel_name="Shopify",
    best_channel_revenue=90000,
    best_channel_margin_pct=0.60,
    worst_channel_name="Mercado Livre",
    worst_channel_revenue=35000,
    worst_channel_margin_pct=0.25,
    new_customers_count=340,
    recurring_customers_count=60,
    recurring_pct=0.15,  # 15%: acima do piso da Categoria A (12%), abaixo do piso da Categoria E (45%)
    paused_products_count=3,
)

# NOVIDADE (04/09/2026): business_category não é mais forçado no config —
# a Categoria agora é derivada sozinha, todo mês, a partir do ticket médio +
# margem do próprio mês (mesma lógica do Motor de Diagnóstico). Pra testar
# categorias diferentes, usamos inputs mensais com ticket médio diferente.
monthly_input_ticket_alto = MonthlyFinancialInput(
    revenue_gross=100000, returns_cancellations=0, cmv=20000,
    variable_costs=10000, fixed_costs=20000, pro_labore=5000, num_orders=100,
)  # avg_ticket = R$1.000 -> Categoria A (piso 12%)

monthly_input_ticket_baixo = MonthlyFinancialInput(
    revenue_gross=20000, returns_cancellations=0, cmv=15000,
    variable_costs=3000, fixed_costs=0, pro_labore=0, num_orders=150,
)  # avg_ticket = R$133,33, margem baixa -> Categoria E (piso 45%)

diagnostic_a = MonthlyDiagnosticEngineMain(dict(config_m)).run_monthly_diagnostic(
    Month.ABR, monthly_input_ticket_alto, sales_intel_15pct
)
s1_a = [a for a in diagnostic_a.alerts if a.code == "S1"]
cat_a = diagnostic_a.monthly_summary.category

diagnostic_e = MonthlyDiagnosticEngineMain(dict(config_m)).run_monthly_diagnostic(
    Month.ABR, monthly_input_ticket_baixo, sales_intel_15pct
)
s1_e = [a for a in diagnostic_e.alerts if a.code == "S1"]
cat_e = diagnostic_e.monthly_summary.category

print(f"Ticket alto (Categoria derivada: {cat_a}), recorrência 15%: S1 {'disparou ❌ (esperado: NÃO disparar)' if s1_a else 'não disparou ✅ (esperado)'}")
print(f"Ticket baixo/margem baixa (Categoria derivada: {cat_e}), recorrência 15%: S1 {'disparou ✅ (esperado)' if s1_e else 'não disparou ❌ (esperado: disparar)'}")
if cat_a == "A" and cat_e == "E" and (not s1_a) and s1_e:
    print("✅ Categoria automática + piso de recorrência no Motor de Mensalidade funcionando como esperado.")
else:
    print("❌ Categoria automática + piso de recorrência no Motor de Mensalidade NÃO está funcionando como esperado!")

print()
print("=" * 70)
print("TESTE 5B: FREQUÊNCIA BAIXA SUSTENTADA (3+ meses) x QUEDA PONTUAL (04/09/2026)")
print("=" * 70)
# monthly_input (Loja Premium Test, avg_ticket R$237,50) deriva Categoria C,
# piso 28%. Mês atual com 15% (abaixo do piso).

# Caso 1: sem histórico informado -> mantém o comportamento antigo (avalia só o mês atual)
diag_sem_historico = MonthlyDiagnosticEngineMain(dict(config_m)).run_monthly_diagnostic(
    Month.ABR, monthly_input, sales_intel_15pct
)
s1_sem_historico = [a for a in diag_sem_historico.alerts if a.code == "S1"]

# Caso 2: queda pontual -- os 2 meses anteriores estavam SAUDÁVEIS (acima do piso de 28%)
diag_pontual = MonthlyDiagnosticEngineMain(dict(config_m)).run_monthly_diagnostic(
    Month.ABR, monthly_input, sales_intel_15pct, recurring_pct_history=[0.35, 0.30]
)
s1_pontual = [a for a in diag_pontual.alerts if a.code == "S1"]

# Caso 3: sustentado -- os 2 meses anteriores também estavam abaixo do piso de 28%
diag_sustentado = MonthlyDiagnosticEngineMain(dict(config_m)).run_monthly_diagnostic(
    Month.ABR, monthly_input, sales_intel_15pct, recurring_pct_history=[0.18, 0.16]
)
s1_sustentado = [a for a in diag_sustentado.alerts if a.code == "S1"]

print(f"Sem histórico informado: S1 {'disparou ✅ (esperado — comportamento antigo mantido)' if s1_sem_historico else 'não disparou ❌'}")
print(f"Queda pontual (2 meses anteriores saudáveis): S1 {'não disparou ✅ (esperado)' if not s1_pontual else 'disparou ❌ (esperado: NÃO disparar)'}")
print(f"Sustentado (3 meses seguidos abaixo do piso): S1 {'disparou ✅ (esperado)' if s1_sustentado else 'não disparou ❌ (esperado: disparar)'}")
if s1_sem_historico and (not s1_pontual) and s1_sustentado:
    print("✅ Distinção sustentado x pontual funcionando como esperado.")
else:
    print("❌ Distinção sustentado x pontual NÃO está funcionando como esperado!")

print()
print("=" * 70)
print("TESTE 7: MOTOR DE DIAGNÓSTICO — CATEGORIA AUTOMÁTICA E ALERTA R1 (04/09/2026)")
print("=" * 70)

# 7.1: a Loja Premium Test (ticket médio R$237,50) deve derivar Categoria C
# automaticamente, mesmo com BusinessCategory.B configurado manualmente.
print(f"Ticket médio do caso de teste: R$ {diagnostic.marketing.avg_ticket:.2f}")
print(f"Categoria configurada manualmente: B | Categoria derivada automaticamente: {config.business_category.name}")
if config.business_category == BusinessCategory.C:
    print("✅ Categoria derivada automaticamente como esperado (ticket médio entre R$200 e R$400 -> C).")
else:
    print("❌ Categoria derivada não bateu com o esperado (C)!")

# 7.2: negócio de ticket alto (Categoria A, piso 12%) com 15% de recorrência -> sem alerta R1
config_alto_ticket = ConfigParameters(client_name="Ticket Alto Teste", tax_rate=0.04)
input_alto_ticket = FinancialInput(
    revenue_gross=100000, cmv=20000, variable_costs=10000,
    fixed_costs=20000, pro_labore=5000, num_orders=100,
    recurring_customers_pct=0.15,
)
diag_alto = FinancialDiagnosticEngine(config_alto_ticket).run_diagnostic(input_alto_ticket)
r1_alto = [a for a in diag_alto.alerts if a.code == "R1"]
print(f"\nTicket alto (R$ {diag_alto.marketing.avg_ticket:.2f}, Categoria {config_alto_ticket.business_category.name}), recorrência 15%: "
      f"R1 {'disparou ❌ (esperado: NÃO disparar)' if r1_alto else 'não disparou ✅ (esperado)'}")

# 7.3: negócio de ticket baixo e margem baixa (Categoria E, piso 45%) com 15% de recorrência -> dispara R1
config_baixo_ticket = ConfigParameters(client_name="Ticket Baixo Teste", tax_rate=0.04)
input_baixo_ticket = FinancialInput(
    revenue_gross=20000, cmv=15000, variable_costs=3000,
    fixed_costs=0, pro_labore=0, num_orders=150,
    recurring_customers_pct=0.15,
)
diag_baixo = FinancialDiagnosticEngine(config_baixo_ticket).run_diagnostic(input_baixo_ticket)
r1_baixo = [a for a in diag_baixo.alerts if a.code == "R1"]
print(f"Ticket baixo/margem baixa (R$ {diag_baixo.marketing.avg_ticket:.2f}, MC {diag_baixo.dre.contribution_margin_pct:.1%}, "
      f"Categoria {config_baixo_ticket.business_category.name}), recorrência 15%: "
      f"R1 {'disparou ✅ (esperado)' if r1_baixo else 'não disparou ❌ (esperado: disparar)'}")

# 7.4: sem recurring_customers_pct informado -> nenhum R1 (nem falso positivo)
input_sem_dado = FinancialInput(
    revenue_gross=20000, cmv=15000, variable_costs=3000,
    fixed_costs=0, pro_labore=0, num_orders=150,
)
diag_sem_dado = FinancialDiagnosticEngine(ConfigParameters(client_name="Sem Dado Teste")).run_diagnostic(input_sem_dado)
r1_sem_dado = [a for a in diag_sem_dado.alerts if a.code == "R1"]
print(f"Mesmo perfil, sem recurring_customers_pct informado: R1 {'não disparou ✅ (esperado)' if not r1_sem_dado else 'disparou ❌ (esperado: NÃO disparar)'}")

if (config.business_category == BusinessCategory.C) and (not r1_alto) and r1_baixo and (not r1_sem_dado):
    print("\n✅ Categoria automática + alerta R1 do Motor de Diagnóstico funcionando como esperado.")
else:
    print("\n❌ Categoria automática + alerta R1 do Motor de Diagnóstico NÃO está funcionando como esperado!")

print()
print("=" * 70)
print("TESTE 8: test_tratamento.py (import path)")
print("=" * 70)
import subprocess
result = subprocess.run(
    [sys.executable, "test_tratamento.py"],
    cwd=os.path.dirname(os.path.abspath(__file__)),
    capture_output=True,
    text=True,
    timeout=30,
)
print(f"exit code: {result.returncode}")
print(result.stdout[-1500:])
if result.stderr:
    print("STDERR (últimas linhas):")
    print(result.stderr[-1500:])

print()
print("=" * 70)
print("RESUMO FINAL")
print("=" * 70)
print("Todos os testes acima devem mostrar ✅. Revisar qualquer ⚠️ ou ❌.")
