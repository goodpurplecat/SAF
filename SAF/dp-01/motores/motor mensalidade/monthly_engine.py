"""
Monthly Diagnostic Engine - Main Orchestrator
Motor de Diagnóstico Mensal - Orquestrador Principal

Coordena:
- Cálculos DRE para 12 meses
- Comparativos automáticos
- Inteligência de vendas
- Alertas + Insights
"""

from monthly_engine_models import *
from monthly_engine_calculator import MonthlyCalculator
from monthly_engine_diagnostic import MonthlyDiagnosticEngine, MonthlyInsightGenerator
import json


class MonthlyDiagnosticEngineMain:
    """Motor completo de diagnóstico mensal"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.calculator = MonthlyCalculator(config)
        self.diagnostic_engine = MonthlyDiagnosticEngine(config, self.calculator)
        self.insight_generator = MonthlyInsightGenerator(config)
    
    def run_monthly_diagnostic(
        self,
        reference_month: Month,
        monthly_input: MonthlyFinancialInput,
        sales_intel: SalesIntelligence,
        previous_month_metrics: Optional[Dict[str, float]] = None,
        recurring_pct_history: Optional[List[float]] = None,
        product_breakdown: Optional[List[ProductAggregate]] = None,
    ) -> CompleteMonthlyDiagnostic:
        """
        Executa diagnóstico mensal completo

        Fluxo:
        1. Calcula DRE do mês
        2. Calcula Métricas
        2B. Deriva a Categoria do negócio (A-E) automaticamente, a partir do
            ticket médio e da margem de contribuição do mês (novidade 04/09/2026)
        3. Calcula Comparativos vs mês anterior
        3B. Calcula Fluxo de Caixa do mês (novidade 14/09/2026)
        4. Gera Alertas
        5. Gera Insights
        6. Consolida Resumo

        recurring_pct_history: recurring_pct (fração, ex.: 0.15) dos meses
        anteriores ao mês atual, do mais antigo pro mais recente — usado
        pelo alerta S1 pra distinguir frequência baixa sustentada de uma
        queda pontual de um único mês (novidade 04/09/2026, ver
        monthly_engine_diagnostic.py). Opcional — sem isso, o S1 avalia só
        o mês atual, como antes.

        product_breakdown: detalhamento por produto do mês (ver
        ProductAggregate em monthly_engine_models.py) — normalmente vem de
        sales_intelligence_calculator.calculate_sales_intelligence(),
        junto com o próprio `sales_intel`. NOVIDADE (auditoria 14/09/2026):
        opcional e independente de `sales_intel` de propósito — quem já
        preenche SalesIntelligence à mão (fluxo atual, enquanto o
        formulário/upload de vendas por pedido não existe) pode continuar
        chamando este método exatamente como antes, sem essa lista. Sem
        ela, o relatório mensal continua funcionando normalmente; só o
        ranking anual (annual_engine.py) fica sem dado para aquele mês.
        """

        diagnostic = CompleteMonthlyDiagnostic(
            config=self.config,
            reference_month=reference_month,
            monthly_input=monthly_input,
            sales_intelligence=sales_intel,
            product_breakdown=product_breakdown or [],
        )
        
        # Validar
        if monthly_input.revenue_gross <= 0:
            diagnostic.is_valid = False
            diagnostic.validation_errors.append("Receita bruta deve ser maior que zero")
            return diagnostic
        
        # ========================
        # 1. CALCULAR DRE
        # ========================
        dre = self.calculator.calculate_dre_for_month(monthly_input)
        
        # ========================
        # 2. CALCULAR MÉTRICAS
        # ========================
        metrics = self.calculator.calculate_metrics_for_month(dre, monthly_input)

        # ========================
        # 2B. CATEGORIA DO NEGÓCIO (A-E) — NOVIDADE 04/09/2026
        # ========================
        # Espelha o Motor de Diagnóstico: a Categoria deixou de vir manual
        # do config e passa a ser derivada sozinha, todo mês, a partir do
        # ticket médio e da margem de contribuição do próprio mês. Sem
        # pergunta nova pro cliente. Sobrescreve self.config['business_category']
        # (mesmo dict usado pelo self.diagnostic_engine, então o novo valor
        # já vale pros alertas e insights deste mês). Ver
        # derive_business_category() em monthly_engine_models.py.
        self.config['business_category'] = derive_business_category(
            metrics['avg_ticket'],
            metrics['contribution_margin_pct'],
            self.config.get('mc_minimum_threshold', 0.35),
        )

        # ========================
        # 3. CALCULAR COMPARATIVOS
        # ========================
        comparatives = {}
        if previous_month_metrics:
            comparatives['revenue_net'] = self.calculator.calculate_comparative(
                metrics['revenue_net'],
                previous_month_metrics.get('revenue_net', 0)
            )
            comparatives['contribution_margin_pct'] = self.calculator.calculate_comparative(
                metrics['contribution_margin_pct'],
                previous_month_metrics.get('contribution_margin_pct', 0)
            )
            comparatives['profit_margin_pct'] = self.calculator.calculate_comparative(
                metrics['profit_margin_pct'],
                previous_month_metrics.get('profit_margin_pct', 0)
            )
            comparatives['profit_net'] = self.calculator.calculate_comparative(
                metrics['profit_net'],
                previous_month_metrics.get('profit_net', 0)
            )
            # NOVIDADE (auditoria 14/09/2026): faltavam 5 dos 9 indicadores
            # da EVOLUÇÃO FINANCEIRA planejada (motores.pdf) — breakeven,
            # ticket médio, ROAS, CAC e LTV:CAC já eram calculados todo mês
            # (bloco 2 acima) mas nunca comparados ao mês anterior. Mesmo
            # padrão dos 4 comparativos acima; fica de fora (chave ausente)
            # quando o indicador não existe no mês anterior (ex.: cliente
            # sem investimento em ads), igual ao comportamento de 'roas'/'cac'
            # em calculate_metrics_for_month().
            comparatives['breakeven'] = self.calculator.calculate_comparative(
                metrics['breakeven'],
                previous_month_metrics.get('breakeven', 0)
            )
            comparatives['avg_ticket'] = self.calculator.calculate_comparative(
                metrics['avg_ticket'],
                previous_month_metrics.get('avg_ticket', 0)
            )
            if metrics.get('roas', 0) > 0 or previous_month_metrics.get('roas', 0) > 0:
                comparatives['roas'] = self.calculator.calculate_comparative(
                    metrics.get('roas', 0),
                    previous_month_metrics.get('roas', 0)
                )
            if metrics.get('cac', 0) > 0 or previous_month_metrics.get('cac', 0) > 0:
                comparatives['cac'] = self.calculator.calculate_comparative(
                    metrics.get('cac', 0),
                    previous_month_metrics.get('cac', 0)
                )
            if metrics.get('ltv_cac', 0) > 0 or previous_month_metrics.get('ltv_cac', 0) > 0:
                comparatives['ltv_cac'] = self.calculator.calculate_comparative(
                    metrics.get('ltv_cac', 0),
                    previous_month_metrics.get('ltv_cac', 0)
                )

        # ========================
        # 3B. CALCULAR FLUXO DE CAIXA MENSAL
        # NOVIDADE (auditoria 14/09/2026) — ver calculate_cashflow_for_month()
        # em monthly_engine_calculator.py e MonthlyCashFlowAnalysis em
        # monthly_engine_models.py. Antes desta correção, avg_collection_period
        # e avg_payment_period eram coletados em MonthlyFinancialInput e nunca
        # usados em lugar nenhum do motor mensal.
        # ========================
        cashflow = self.calculator.calculate_cashflow_for_month(monthly_input, dre)

        # ========================
        # 4. CALCULAR METAS
        # ========================
        goals = self.calculator.calculate_goals(metrics, self.config, reference_month)

        # ========================
        # 5. GERAR ALERTAS
        # ========================
        alerts = self.diagnostic_engine.generate_alerts(
            metrics,
            comparatives,
            sales_intel,
            previous_month_metrics,
            recurring_pct_history,
            cashflow,
        )

        # ========================
        # 6. MONTAR RESUMO
        # ========================
        summary = MonthlySummary(month=reference_month)
        summary.client_name = self.config.get('client_name', '')
        summary.category = self.config.get('business_category', '')
        summary.overall_status = self.calculator.get_status_from_metrics(metrics)
        
        # Financeiro
        summary.revenue_net = metrics['revenue_net']
        summary.contribution_margin_pct = metrics['contribution_margin_pct']
        summary.profit_margin_pct = metrics['profit_margin_pct']
        summary.profit_net = metrics['profit_net']
        summary.breakeven_revenue = metrics['breakeven']
        summary.ads_investment = metrics['ads_investment']
        summary.roas = metrics['roas']
        summary.cac = metrics['cac']
        summary.ltv = metrics['ltv']
        summary.ltv_cac = metrics['ltv_cac']
        summary.avg_ticket = metrics['avg_ticket']

        # Fluxo de Caixa (NOVIDADE 14/09/2026)
        summary.cashflow = cashflow

        # Comparativos
        if comparatives:
            summary.revenue_comparative = comparatives.get('revenue_net', MonthlyComparative())
            summary.margin_comparative = comparatives.get('contribution_margin_pct', MonthlyComparative())
            # CORREÇÃO (auditoria 05/09/2026): esse comparativo já era
            # calculado acima (bloco "3. CALCULAR COMPARATIVOS") mas nunca
            # tinha sido guardado no summary — ficava calculado à toa e se
            # perdia, então a Margem Líquida nunca tinha uma variação real
            # disponível pra tabela do bloco COMPARATIVO FINANCEIRO.
            summary.profit_margin_comparative = comparatives.get('profit_margin_pct', MonthlyComparative())
            summary.profit_comparative = comparatives.get('profit_net', MonthlyComparative())
            # NOVIDADE (auditoria 14/09/2026): completa os 9 indicadores da
            # EVOLUÇÃO FINANCEIRA planejada (motores.pdf) — ver bloco "3.
            # CALCULAR COMPARATIVOS" acima.
            summary.breakeven_comparative = comparatives.get('breakeven', MonthlyComparative())
            summary.avg_ticket_comparative = comparatives.get('avg_ticket', MonthlyComparative())
            summary.roas_comparative = comparatives.get('roas', MonthlyComparative())
            summary.cac_comparative = comparatives.get('cac', MonthlyComparative())
            summary.ltv_cac_comparative = comparatives.get('ltv_cac', MonthlyComparative())

        # Inteligência de Vendas
        summary.sales_intel = sales_intel

        # Top 3 alertas
        summary.top_3_alerts = self.diagnostic_engine.get_top_3_priorities(alerts)

        # Insights
        summary.insights = self.insight_generator.generate_all_insights(
            reference_month,
            metrics,
            comparatives,
            sales_intel,
            summary,
            cashflow,
        )
        
        # ========================
        # Consolidar resultado
        # ========================
        diagnostic.monthly_summary = summary
        diagnostic.goals = goals
        diagnostic.alerts = alerts
        diagnostic.is_valid = True
        
        return diagnostic
    
    def export_to_dict(self, diagnostic: CompleteMonthlyDiagnostic) -> Dict[str, Any]:
        """Exporta diagnóstico para dicionário JSON"""
        
        month = diagnostic.reference_month
        summary = diagnostic.monthly_summary
        
        return {
            'client_name': self.config.get('client_name', ''),
            'month': month.get_name(),
            'month_number': month.get_number(),
            'year': self.config.get('year', 2026),
            'generated_at': diagnostic.generated_at.isoformat(),
            
            'overall_status': summary.overall_status,
            
            'financial': {
                'revenue_net': float(summary.revenue_net),
                'contribution_margin_pct': float(summary.contribution_margin_pct),
                'profit_margin_pct': float(summary.profit_margin_pct),
                'profit_net': float(summary.profit_net),
                'breakeven': float(summary.breakeven_revenue),
                # CORREÇÃO (auditoria 13/09/2026): já descontado de profit_net
                # acima — exposto aqui pra coerência com a seção 'marketing'.
                'ads_investment_deducted': float(summary.ads_investment),
            },
            
            'marketing': {
                'roas': float(summary.roas) if summary.roas > 0 else None,
                'cac': float(summary.cac) if summary.cac > 0 else None,
                'ltv': float(summary.ltv) if summary.ltv > 0 else None,
                'ltv_cac': float(summary.ltv_cac) if summary.ltv_cac > 0 else None,
            },

            # NOVIDADE (auditoria 14/09/2026) — ver MonthlyCashFlowAnalysis /
            # calculate_cashflow_for_month(). Antes desta correção, esta
            # chave não existia: PMR/PMP eram coletados e nunca chegavam a
            # lugar nenhum do export.
            'cashflow': {
                'avg_collection_period': float(summary.cashflow.avg_collection_period),
                'avg_payment_period': float(summary.cashflow.avg_payment_period),
                'financial_cycle': float(summary.cashflow.financial_cycle),
                'cycle_status': summary.cashflow.cycle_status,
                'profit_vs_cash_alert': summary.cashflow.profit_vs_cash_alert,
            },

            # CORREÇÃO (auditoria 05/09/2026): esta seção só exportava 2 dos
            # 4 indicadores comparativos que a página/bloco "COMPARATIVO
            # FINANCEIRO" (templates.py) precisa — e o que existia estava
            # com a chave errada ('profit_margin' continha na verdade o
            # comparativo de LUCRO LÍQUIDO em R$, vindo de
            # `profit_comparative`, não o de Margem Líquida em %). Faltava
            # também o comparativo de Margem de Contribuição inteiramente
            # (calculado em `margin_comparative` mas nunca chegava aqui).
            # Agora exporta os 4 indicadores da tabela, cada um com a
            # variação percentual (usada pro [▲/▼] do roteiro).
            'comparatives': {
                'revenue': {
                    'current': float(summary.revenue_comparative.current_month_value),
                    'previous': float(summary.revenue_comparative.previous_month_value),
                    'variation': float(summary.revenue_comparative.variation),
                    'variation_pct': float(summary.revenue_comparative.variation_pct),
                    'status': summary.revenue_comparative.status,
                },
                'contribution_margin_pct': {
                    'current': float(summary.margin_comparative.current_month_value),
                    'previous': float(summary.margin_comparative.previous_month_value),
                    'variation': float(summary.margin_comparative.variation),
                    'variation_pct': float(summary.margin_comparative.variation_pct),
                    'status': summary.margin_comparative.status,
                },
                'profit_margin_pct': {
                    'current': float(summary.profit_margin_comparative.current_month_value),
                    'previous': float(summary.profit_margin_comparative.previous_month_value),
                    'variation': float(summary.profit_margin_comparative.variation),
                    'variation_pct': float(summary.profit_margin_comparative.variation_pct),
                    'status': summary.profit_margin_comparative.status,
                },
                'profit_net': {
                    'current': float(summary.profit_comparative.current_month_value),
                    'previous': float(summary.profit_comparative.previous_month_value),
                    'variation': float(summary.profit_comparative.variation),
                    'variation_pct': float(summary.profit_comparative.variation_pct),
                    'status': summary.profit_comparative.status,
                },
                # NOVIDADE (auditoria 14/09/2026): completa os 9 indicadores
                # da EVOLUÇÃO FINANCEIRA planejada (motores.pdf) — ver
                # MonthlySummary.breakeven_comparative e vizinhos.
                'breakeven': {
                    'current': float(summary.breakeven_comparative.current_month_value),
                    'previous': float(summary.breakeven_comparative.previous_month_value),
                    'variation': float(summary.breakeven_comparative.variation),
                    'variation_pct': float(summary.breakeven_comparative.variation_pct),
                    'status': summary.breakeven_comparative.status,
                },
                'avg_ticket': {
                    'current': float(summary.avg_ticket_comparative.current_month_value),
                    'previous': float(summary.avg_ticket_comparative.previous_month_value),
                    'variation': float(summary.avg_ticket_comparative.variation),
                    'variation_pct': float(summary.avg_ticket_comparative.variation_pct),
                    'status': summary.avg_ticket_comparative.status,
                },
                'roas': {
                    'current': float(summary.roas_comparative.current_month_value),
                    'previous': float(summary.roas_comparative.previous_month_value),
                    'variation': float(summary.roas_comparative.variation),
                    'variation_pct': float(summary.roas_comparative.variation_pct),
                    'status': summary.roas_comparative.status,
                },
                'cac': {
                    'current': float(summary.cac_comparative.current_month_value),
                    'previous': float(summary.cac_comparative.previous_month_value),
                    'variation': float(summary.cac_comparative.variation),
                    'variation_pct': float(summary.cac_comparative.variation_pct),
                    'status': summary.cac_comparative.status,
                },
                'ltv_cac': {
                    'current': float(summary.ltv_cac_comparative.current_month_value),
                    'previous': float(summary.ltv_cac_comparative.previous_month_value),
                    'variation': float(summary.ltv_cac_comparative.variation),
                    'variation_pct': float(summary.ltv_cac_comparative.variation_pct),
                    'status': summary.ltv_cac_comparative.status,
                },
            },
            
            'sales_intelligence': {
                'top_product_1': summary.sales_intel.top_1_product_name,
                'best_channel': summary.sales_intel.best_channel_name,
                'worst_channel': summary.sales_intel.worst_channel_name,
                'recurring_customers_pct': float(summary.sales_intel.recurring_pct),
                'worst_product_margin': float(summary.sales_intel.worst_product_margin_pct),
                'paused_products_count': summary.sales_intel.paused_products_count,
            },
            
            'goals': {
                'contribution_margin': {
                    'goal': float(diagnostic.goals.goal_contribution_margin_pct),
                    'actual': float(diagnostic.goals.actual_contribution_margin_pct),
                    'status': diagnostic.goals.mc_status,
                },
                'profit_margin': {
                    'goal': float(diagnostic.goals.goal_profit_margin_pct),
                    'actual': float(diagnostic.goals.actual_profit_margin_pct),
                    'status': diagnostic.goals.ml_status,
                },
                'profit_net': {
                    'goal': float(diagnostic.goals.goal_profit_net),
                    'actual': float(diagnostic.goals.actual_profit_net),
                    'status': diagnostic.goals.profit_status,
                },
            },
            
            'alerts': [
                {
                    'code': a.code,
                    'rule': a.rule,
                    'impact': a.impact,
                    'urgency': a.urgency,
                    'score': a.score,
                    'action': a.action,
                }
                for a in diagnostic.alerts
            ],
            
            'top_3_priorities': [
                {
                    'code': p.code,
                    'rule': p.rule,
                    'score': p.score,
                    'action': p.action,
                }
                for p in summary.top_3_alerts
            ],
            
            'insights': summary.insights,

            # NOVIDADE (auditoria 14/09/2026): detalhamento completo por
            # produto do mês — não só o Top 3 de 'sales_intelligence' acima.
            # É esta lista, persistida em Relatorio.dados_motor_json
            # (database.py) mês a mês, que annual_engine.py consome pra
            # montar o ranking anual de mais vendidos por ID. Vem vazia
            # ([]) quando o mês foi rodado sem product_breakdown (fluxo
            # atual, com SalesIntelligence preenchido à mão) — não quebra
            # nada, só significa que aquele mês não entra no ranking anual.
            'product_breakdown': [
                {
                    'produto_id': p.produto_id,
                    'produto_nome': p.produto_nome,
                    'receita': float(p.receita),
                    'custo': float(p.custo),
                    'margem_pct': float(p.margem_pct),
                    'pedidos': p.pedidos,
                }
                for p in diagnostic.product_breakdown
            ],
        }


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

def example_usage():
    """Exemplo prático"""
    
    print("=" * 60)
    print("MONTHLY ENGINE - Exemplo de Uso")
    print("=" * 60)
    
    # Config
    config = {
        'client_name': 'E-commerce Mensal',
        'year': 2026,
        'business_category': 'B',  # valor inicial só — o motor deriva sozinho e sobrescreve (04/09/2026)
        'tax_rate': 0.04,
        'mc_critical_threshold': 0.20,
        'mc_minimum_threshold': 0.35,
        'ml_critical_threshold': 0.0,
        'ml_minimum_threshold': 0.10,
        'goal_mc_pct': 0.40,
        'goal_ml_pct': 0.15,
        'goal_profit_net': 5000,
        'repurchase_frequency_per_year': 2.0,  # CORREÇÃO 04/09/2026 (era avg_repurchase_rate)
        'retention_years': 2.0,                 # CORREÇÃO 04/09/2026 (era retention_rate)
    }
    
    # Input de Abril
    april_input = MonthlyFinancialInput(
        revenue_gross=150000,
        returns_cancellations=7500,
        cmv=45000,
        variable_costs=22500,
        fixed_costs=25000,
        pro_labore=5000,
        num_orders=600,
        ads_investment=15000,
        new_customers_ads=300,
    )
    
    # Inteligência de Vendas
    sales_intel = SalesIntelligence(
        top_1_product_name="Produto Premium",
        top_1_product_revenue=45000,
        top_1_product_margin_pct=0.55,
        best_channel_name="Shopify",
        best_channel_revenue=90000,
        best_channel_margin_pct=0.60,
        worst_channel_name="Mercado Livre",
        worst_channel_revenue=35000,
        worst_channel_margin_pct=0.25,
        new_customers_count=300,
        recurring_customers_count=250,
        recurring_pct=0.45,
    )
    
    # Executar
    engine = MonthlyDiagnosticEngineMain(config)
    diagnostic = engine.run_monthly_diagnostic(
        Month.ABR,
        april_input,
        sales_intel,
    )
    
    if diagnostic.is_valid:
        print(f"\n✅ Diagnóstico de {Month.ABR.get_name()}/2026")
        print(f"   Status: {diagnostic.monthly_summary.overall_status}")
        print(f"   Receita: R$ {diagnostic.monthly_summary.revenue_net:,.2f}")
        print(f"   Margem Líquida: {diagnostic.monthly_summary.profit_margin_pct:.1%}")
        print(f"   Lucro: R$ {diagnostic.monthly_summary.profit_net:,.2f}")
        
        print(f"\n📊 Metas:")
        print(f"   MC: {diagnostic.goals.mc_status}")
        print(f"   ML: {diagnostic.goals.ml_status}")
        
        print(f"\n🚨 Alertas:")
        for alert in diagnostic.alerts:
            print(f"   {alert.code}: {alert.rule} (Score: {alert.score})")
        
        print(f"\n💡 Insights (3 principais):")
        for key, value in list(diagnostic.monthly_summary.insights.items())[:3]:
            print(f"   • {key}: {value[:80]}...")
        
        # JSON
        json_output = engine.export_to_dict(diagnostic)
        print(f"\n📄 JSON exportado com sucesso!")


if __name__ == "__main__":
    example_usage()
