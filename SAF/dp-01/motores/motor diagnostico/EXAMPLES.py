"""
Financial Diagnostic Engine - Exemplos Práticos
Copie e cole esses exemplos no seu projeto!
"""

from financial_engine import FinancialDiagnosticEngine
from financial_engine_models import *
import json


# =============================================================================
# EXEMPLO 1: Diagnóstico Básico
# =============================================================================

def example_1_basic_diagnostic():
    """Exemplo mais simples possível"""
    
    print("=" * 60)
    print("EXEMPLO 1: Diagnóstico Básico")
    print("=" * 60)
    
    # Configurar
    config = ConfigParameters(
        client_name="Loja Virtual ABC",
        analysis_period="Setembro/2025",
        business_category=BusinessCategory.B,
    )
    
    # Dados
    input_data = FinancialInput(
        revenue_gross=100000,
        returns_cancellations=5000,
        cmv=30000,
        variable_costs=15000,
        fixed_costs=20000,
        pro_labore=5000,
        num_orders=500,
    )
    
    # Executar
    engine = FinancialDiagnosticEngine(config)
    diagnostic = engine.run_diagnostic(input_data)
    
    # Exibir resultados
    if diagnostic.is_valid:
        print(f"\n✅ Cliente: {diagnostic.config.client_name}")
        print(f"   Status: {diagnostic.summary.overall_status.value}")
        print(f"   Receita Líquida: R$ {diagnostic.dre.revenue_net:,.2f}")
        print(f"   Margem Líquida: {diagnostic.dre.profit_net_pct:.1%}")
        print(f"   Lucro Líquido: R$ {diagnostic.dre.profit_net:,.2f}")
    else:
        print(f"❌ Erros: {diagnostic.validation_errors}")


# =============================================================================
# EXEMPLO 2: Diagnóstico Completo com Marketing & Canais
# =============================================================================

def example_2_complete_diagnostic():
    """Exemplo com todas as funcionalidades"""
    
    print("\n" + "=" * 60)
    print("EXEMPLO 2: Diagnóstico Completo")
    print("=" * 60)
    
    # Configurar com valores customizados
    config = ConfigParameters(
        client_name="E-commerce Fashion XYZ",
        analysis_period="Jul-Set/2025",
        business_category=BusinessCategory.A,  # Ticket alto
        tax_regime=TaxRegime.SIMPLES_NACIONAL,
        tax_rate=0.04,
        mc_critical_threshold=0.25,  # Customizar semáforo
        mc_good_threshold=0.50,
    )
    
    # Dados completos
    input_data = FinancialInput(
        analysis_period="Jul-Set/2025",
        revenue_gross=750000,
        returns_cancellations=30000,
        cmv=200000,
        variable_costs=120000,
        fixed_costs=80000,
        pro_labore=15000,
        num_orders=1500,
        # Marketing
        ads_investment=60000,
        new_customers_ads=1200,
        primary_ads_channel="Meta Ads",
        # Fluxo de Caixa
        avg_collection_period=10,
        avg_payment_period=45,
        # Canais de venda
        channel_revenues={
            SalesChannel.SHOPIFY: 450000,
            SalesChannel.MERCADO_LIVRE: 180000,
            SalesChannel.INSTAGRAM: 120000,
        },
    )
    
    # Executar
    engine = FinancialDiagnosticEngine(config)
    diagnostic = engine.run_diagnostic(input_data)
    
    if diagnostic.is_valid:
        print(f"\n📊 Financeiro:")
        print(f"   Receita Líquida: R$ {diagnostic.dre.revenue_net:,.2f}")
        print(f"   Margem Contribuição: {diagnostic.dre.contribution_margin_pct:.1%}")
        print(f"   Margem Líquida: {diagnostic.dre.profit_net_pct:.1%}")
        print(f"   Breakeven: R$ {diagnostic.summary.breakeven_revenue:,.2f}/mês")
        
        print(f"\n📢 Marketing:")
        print(f"   ROAS: {diagnostic.marketing.roas:.1f}x")
        print(f"   CAC: R$ {diagnostic.marketing.cac:.2f}")
        print(f"   LTV:CAC: {diagnostic.marketing.ltv_cac_ratio:.1f}x")
        
        print(f"\n🏪 Canais:")
        for channel in diagnostic.channels:
            print(f"   {nome_canal(channel.channel)}: {channel.margin_pct:.1%} de margem")
        
        print(f"\n💸 Fluxo de Caixa:")
        print(f"   Ciclo Financeiro: {diagnostic.cashflow.financial_cycle:.0f} dias")
        print(f"   Status: {diagnostic.cashflow.cycle_status}")
        
        print(f"\n🚨 Alertas Ativos:")
        if diagnostic.alerts:
            for alert in diagnostic.alerts:
                print(f"   {alert.code}: {alert.rule} (Score: {alert.score})")
        else:
            print("   ✅ Nenhum alerta crítico!")
        
        print(f"\n🎯 Top 3 Prioridades:")
        for i, priority in enumerate(diagnostic.summary.top_3_priorities, 1):
            print(f"   {i}. {priority.rule}")
            print(f"      → {priority.action}")


# =============================================================================
# EXEMPLO 3: Exportar para JSON
# =============================================================================

def example_3_export_json():
    """Exportar diagnóstico completo para JSON"""
    
    print("\n" + "=" * 60)
    print("EXEMPLO 3: Exportar para JSON")
    print("=" * 60)
    
    config = ConfigParameters(
        client_name="Teste JSON",
        analysis_period="Out/2025",
    )
    
    input_data = FinancialInput(
        revenue_gross=200000,
        returns_cancellations=10000,
        cmv=60000,
        variable_costs=30000,
        fixed_costs=40000,
        pro_labore=8000,
        num_orders=800,
        ads_investment=25000,
        new_customers_ads=500,
    )
    
    # Executar
    engine = FinancialDiagnosticEngine(config)
    diagnostic = engine.run_diagnostic(input_data)
    
    # Exportar para JSON
    diagnosis_dict = engine.export_to_dict(diagnostic)
    
    # Salvar em arquivo
    with open("diagnostic_output.json", "w", encoding="utf-8") as f:
        json.dump(diagnosis_dict, f, indent=2, ensure_ascii=False)
    
    print("\n✅ JSON salvo em: diagnostic_output.json")
    print("\n📄 Primeiras linhas do JSON:")
    print(json.dumps({
        k: diagnosis_dict[k] 
        for k in list(diagnosis_dict.keys())[:3]
    }, indent=2, ensure_ascii=False))


# =============================================================================
# EXEMPLO 4: Processar Múltiplos Clientes
# =============================================================================

def example_4_multiple_clients():
    """Processar vários clientes em lote"""
    
    print("\n" + "=" * 60)
    print("EXEMPLO 4: Múltiplos Clientes")
    print("=" * 60)
    
    # Lista de clientes para processar
    clients = [
        {
            "name": "Loja A - Premium",
            "period": "Set/2025",
            "revenue": 500000,
            "cmv": 150000,
            "variable_costs": 80000,
            "fixed_costs": 50000,
            "pro_labore": 10000,
            "orders": 2000,
        },
        {
            "name": "Loja B - Econômica",
            "period": "Set/2025",
            "revenue": 200000,
            "cmv": 80000,
            "variable_costs": 40000,
            "fixed_costs": 30000,
            "pro_labore": 5000,
            "orders": 5000,
        },
        {
            "name": "Loja C - Crescimento",
            "period": "Set/2025",
            "revenue": 100000,
            "cmv": 40000,
            "variable_costs": 20000,
            "fixed_costs": 20000,
            "pro_labore": 3000,
            "orders": 800,
        },
    ]
    
    results = []
    
    for client_data in clients:
        config = ConfigParameters(
            client_name=client_data["name"],
            analysis_period=client_data["period"],
        )
        
        input_data = FinancialInput(
            revenue_gross=client_data["revenue"],
            cmv=client_data["cmv"],
            variable_costs=client_data["variable_costs"],
            fixed_costs=client_data["fixed_costs"],
            pro_labore=client_data["pro_labore"],
            num_orders=client_data["orders"],
        )
        
        engine = FinancialDiagnosticEngine(config)
        diagnostic = engine.run_diagnostic(input_data)
        
        results.append({
            "client": client_data["name"],
            "status": diagnostic.summary.overall_status.value,
            "profit_margin": f"{diagnostic.dre.profit_net_pct:.1%}",
            "alerts": len(diagnostic.alerts),
        })
    
    print("\n📊 Resumo de Todos os Clientes:")
    print(f"{'Cliente':<30} {'Status':<15} {'Margem':<10} {'Alertas':<8}")
    print("-" * 63)
    for r in results:
        print(f"{r['client']:<30} {r['status']:<15} {r['profit_margin']:<10} {r['alerts']:<8}")


# =============================================================================
# EXEMPLO 5: Integração com Agentes de IA
# =============================================================================

def example_5_ai_integration():
    """Exemplo de integração com Claude (comentado por questões de API key)"""
    
    print("\n" + "=" * 60)
    print("EXEMPLO 5: Integração com Claude API")
    print("=" * 60)
    
    print("""
    # Descomente e adicione sua ANTHROPIC_API_KEY para testar
    
    from anthropic import Anthropic
    
    # Gerar diagnóstico
    config = ConfigParameters(client_name="Teste IA")
    input_data = FinancialInput(revenue_gross=300000, ...)
    engine = FinancialDiagnosticEngine(config)
    diagnostic = engine.run_diagnostic(input_data)
    
    # Passar para Claude
    client = Anthropic()
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f\"\"\"
                Você é um consultor financeiro para e-commerce.
                Aqui está o diagnóstico de um cliente:
                
                {json.dumps(engine.export_to_dict(diagnostic), indent=2)}
                
                Por favor:
                1. Resuma o status em 1 parágrafo
                2. Explique os 3 principais problemas
                3. Proponha 3 ações concretas
            \"\"\"
        }]
    )
    
    print(response.content[0].text)
    """)


# =============================================================================
# EXEMPLO 6: Validação de Dados
# =============================================================================

def example_6_validation():
    """Exemplo de validação de dados"""
    
    print("\n" + "=" * 60)
    print("EXEMPLO 6: Validação de Dados")
    print("=" * 60)
    
    # Dados inválidos
    input_data = FinancialInput(
        revenue_gross=0,  # ❌ Inválido
        cmv=-5000,        # ❌ Negativo
        num_orders=0,     # ❌ Inválido
    )
    
    # Validar
    is_valid, errors = input_data.validate()
    
    if not is_valid:
        print("\n❌ Erros encontrados:")
        for error in errors:
            print(f"   • {error}")
    
    # Dados válidos
    input_data2 = FinancialInput(
        revenue_gross=100000,
        cmv=30000,
        num_orders=500,
        variable_costs=20000,
        fixed_costs=15000,
        pro_labore=5000,
    )
    
    is_valid2, errors2 = input_data2.validate()
    
    if is_valid2:
        print("\n✅ Dados válidos! Pode executar run_diagnostic()")


# =============================================================================
# EXEMPLO 7: Comparar Dois Cenários
# =============================================================================

def example_7_scenario_comparison():
    """Comparar diagnóstico do cenário atual vs melhorado"""
    
    print("\n" + "=" * 60)
    print("EXEMPLO 7: Comparação de Cenários")
    print("=" * 60)
    
    config = ConfigParameters(
        client_name="Análise de Cenários",
        analysis_period="Out/2025",
    )
    
    # Cenário 1: Atual
    current = FinancialInput(
        revenue_gross=200000,
        returns_cancellations=15000,
        cmv=70000,
        variable_costs=40000,
        fixed_costs=35000,
        pro_labore=8000,
        num_orders=1000,
        ads_investment=20000,
        new_customers_ads=400,
    )
    
    # Cenário 2: Se corrigirmos os problemas
    improved = FinancialInput(
        revenue_gross=250000,      # +25% de receita
        returns_cancellations=10000, # -5k devoluções
        cmv=70000,                  # CMV igual
        variable_costs=35000,       # -5k custos variáveis
        fixed_costs=35000,          # Fixos iguais
        pro_labore=8000,            # Pro-labore igual
        num_orders=1250,            # +250 pedidos
        ads_investment=15000,       # -25% em ads
        new_customers_ads=250,      # Menos clientes, mais eficientes
    )
    
    engine = FinancialDiagnosticEngine(config)
    
    diag_current = engine.run_diagnostic(current)
    diag_improved = engine.run_diagnostic(improved)
    
    print("\n📊 Comparação de Cenários:")
    print(f"\n{'Métrica':<30} {'Atual':<15} {'Melhorado':<15} {'Diferença':<15}")
    print("-" * 75)
    
    revenue_diff = diag_improved.dre.profit_net - diag_current.dre.profit_net
    margin_diff = diag_improved.dre.profit_net_pct - diag_current.dre.profit_net_pct
    roas_diff = diag_improved.marketing.roas - diag_current.marketing.roas
    
    print(f"{'Lucro Líquido':<30} R$ {diag_current.dre.profit_net:>12,.0f} R$ {diag_improved.dre.profit_net:>12,.0f} R$ {revenue_diff:>12,.0f}")
    print(f"{'Margem Líquida':<30} {diag_current.dre.profit_net_pct:>13.1%} {diag_improved.dre.profit_net_pct:>13.1%} {margin_diff:>13.1%}")
    print(f"{'ROAS':<30} {diag_current.marketing.roas:>13.1f}x {diag_improved.marketing.roas:>13.1f}x {roas_diff:>13.1f}x")


# =============================================================================
# Main - Rodar todos os exemplos
# =============================================================================

if __name__ == "__main__":
    try:
        example_1_basic_diagnostic()
        example_2_complete_diagnostic()
        example_3_export_json()
        example_4_multiple_clients()
        example_5_ai_integration()
        example_6_validation()
        example_7_scenario_comparison()
        
        print("\n" + "=" * 60)
        print("✅ Todos os exemplos executados com sucesso!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
