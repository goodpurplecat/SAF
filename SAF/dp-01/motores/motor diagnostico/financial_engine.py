"""
Financial Diagnostic Engine - Main Orchestrator
Motor de Diagnóstico Financeiro - Orquestrador Principal

Este é o ponto de entrada. Coordena todo o fluxo de dados:
INPUT → VALIDAÇÃO → DRE → MARKETING → CANAIS → ALERTAS → DIAGNÓSTICO FINAL
"""

from financial_engine_models import *
from financial_engine_calculator import FinancialCalculator
from financial_engine_diagnostic import DiagnosticEngine, InsightGenerator


class FinancialDiagnosticEngine:
    """
    Motor completo de diagnóstico financeiro.
    Orquestra todos os módulos para transformar dados brutos em diagnóstico.
    """
    
    def __init__(self, config: ConfigParameters):
        """
        Inicializa o motor com configuração do cliente.
        
        Args:
            config: ConfigParameters com calibrações do cliente
        """
        self.config = config
        self.calculator = FinancialCalculator(config)
        self.diagnostic_engine = DiagnosticEngine(config, self.calculator)
        self.insight_generator = InsightGenerator(config, self.calculator)
    
    def run_diagnostic(self, input_data: FinancialInput) -> CompleteDiagnostic:
        """
        Executa diagnóstico completo.
        
        Fluxo:
        1. Validação de dados (BASE_TRATADA)
        2. Cálculo DRE (Demonstração de Resultados)
        3. Cálculo de Marketing (ROAS, CAC, LTV)
        3B. Derivação automática da Categoria do negócio (A-E), a partir do
            ticket médio e da margem de contribuição (novidade 04/09/2026)
        4. Análise de Canais (Margem por canal)
        5. Análise de Fluxo de Caixa
        6. Geração de Alertas (14 regras automáticas, incl. R1 de retenção)
        7. Ranking de Prioridades (Top 3 por score)
        8. Geração de Insights (linguagem natural)
        9. Montagem do Resumo Executivo
        
        Args:
            input_data: FinancialInput com dados brutos do cliente
        
        Returns:
            CompleteDiagnostic: Diagnóstico completo pronto para IA/PDF/Vídeo
        """
        
        diagnostic = CompleteDiagnostic(
            config=self.config,
            input_data=input_data
        )
        
        # Validação inicial
        is_valid, errors = input_data.validate()
        if not is_valid:
            diagnostic.is_valid = False
            diagnostic.validation_errors = errors
            return diagnostic
        
        # ========================
        # PASSO 1: VALIDAÇÃO (BASE_TRATADA)
        # ========================
        diagnostic.validated_data = self.calculator.validate_and_sanitize(input_data)
        
        # ========================
        # PASSO 2: DRE (Demonstração de Resultados)
        # ========================
        diagnostic.dre = self.calculator.calculate_dre(diagnostic.validated_data)
        
        # ========================
        # PASSO 3: MARKETING
        # ========================
        diagnostic.marketing = self.calculator.calculate_marketing_metrics(
            diagnostic.validated_data,
            diagnostic.dre
        )

        # ========================
        # PASSO 3B: CATEGORIA DO NEGÓCIO (A-E) — NOVIDADE 04/09/2026
        # ========================
        # Antes era um campo que o analista escolhia manualmente em
        # ConfigParameters.business_category. Agora é calculada sozinha a
        # partir do ticket médio e da margem de contribuição do próprio
        # cliente — nenhuma pergunta nova pro cliente, nada "na cara" no
        # formulário. Sobrescreve o valor de config (que continua existindo
        # só como valor inicial/fallback antes deste passo rodar). Ver
        # derive_business_category() em financial_engine_models.py.
        self.config.business_category = derive_business_category(
            diagnostic.marketing.avg_ticket,
            diagnostic.dre.contribution_margin_pct,
            self.config.mc_minimum_threshold,
        )

        # ========================
        # PASSO 4: CANAIS
        # ========================
        diagnostic.channels = self.calculator.calculate_channel_performance(
            diagnostic.validated_data,
            diagnostic.dre
        )
        
        # ========================
        # PASSO 5: FLUXO DE CAIXA
        # ========================
        diagnostic.cashflow = self.calculator.calculate_cashflow(
            diagnostic.validated_data,
            diagnostic.dre
        )
        
        # ========================
        # PASSO 6: ALERTAS
        # ========================
        diagnostic.alerts = self.diagnostic_engine.generate_alerts(
            diagnostic.validated_data,
            diagnostic.dre,
            diagnostic.marketing,
            diagnostic.channels,
            diagnostic.cashflow
        )
        
        # ========================
        # PASSO 7: RESUMO EXECUTIVO + INSIGHTS
        # ========================
        diagnostic.summary = self._build_summary(diagnostic)
        diagnostic.summary.top_3_priorities = self.diagnostic_engine.get_top_3_priorities(
            diagnostic.alerts
        )
        
        # Gerar insights
        diagnostic.summary.insights = self.insight_generator.generate_all_insights(
            diagnostic.validated_data,
            diagnostic.dre,
            diagnostic.marketing,
            diagnostic.channels,
            diagnostic.cashflow,
            diagnostic.summary
        )
        
        # Status final
        diagnostic.is_valid = True
        
        return diagnostic
    
    def _build_summary(self, diagnostic: CompleteDiagnostic) -> DiagnosticSummary:
        """Constrói o resumo executivo a partir dos cálculos"""
        summary = DiagnosticSummary()
        
        # Identificação
        summary.client_name = self.config.client_name
        summary.analysis_period = diagnostic.validated_data.period
        summary.business_category = self.config.business_category.value
        
        # Status geral
        summary.overall_status = self.diagnostic_engine.get_overall_status(diagnostic.dre)
        
        # Financeiro
        summary.revenue_net = diagnostic.dre.revenue_net
        summary.contribution_margin_pct = diagnostic.dre.contribution_margin_pct
        summary.profit_margin_pct = diagnostic.dre.profit_net_pct
        summary.profit_net = diagnostic.dre.profit_net
        summary.breakeven_revenue = self.calculator.calculate_breakeven(diagnostic.dre)
        
        # Marketing
        summary.roas = diagnostic.marketing.roas
        summary.roas_breakeven = diagnostic.marketing.roas_breakeven
        summary.cac = diagnostic.marketing.cac
        
        # Canais
        if diagnostic.channels:
            # CORREÇÃO (05/09/2026, pedido do analista: canal customizado
            # que o cliente declara mesmo fora da nossa lista) — `.channel`
            # pode ser um SalesChannel OU uma string livre agora; `.value`
            # direto quebraria (AttributeError) num canal customizado.
            # nome_canal() trata os dois casos. Ver ChannelPerformance em
            # financial_engine_models.py.
            summary.top_channel_by_revenue = nome_canal(diagnostic.channels[0].channel)

            # Canal com melhor margem
            best_channel = max(
                diagnostic.channels,
                key=lambda c: c.margin_pct,
                default=None
            )
            if best_channel:
                summary.top_channel_by_margin = nome_canal(best_channel.channel)

            # Canal que mais preocupa (pior margem)
            worst_channel = min(
                diagnostic.channels,
                key=lambda c: c.margin_pct,
                default=None
            )
            if worst_channel:
                summary.worst_channel = nome_canal(worst_channel.channel)
        
        # Fluxo de caixa
        summary.financial_cycle_days = diagnostic.cashflow.financial_cycle
        
        return summary
    
    def export_to_dict(self, diagnostic: CompleteDiagnostic) -> Dict[str, Any]:
        """
        Exporta diagnóstico completo para dicionário.
        Útil para converter para JSON para APIs/agentes IA.
        """
        return {
            'client_name': diagnostic.config.client_name,
            'analysis_period': diagnostic.validated_data.period,
            'generated_at': diagnostic.generated_at.isoformat(),
            'is_valid': diagnostic.is_valid,
            
            'overall_status': diagnostic.summary.overall_status.value,
            
            'financial': {
                'revenue_net': float(diagnostic.dre.revenue_net),
                'cmv': float(diagnostic.dre.cmv),
                'contribution_margin': {
                    'amount': float(diagnostic.dre.contribution_margin),
                    'percentage': float(diagnostic.dre.contribution_margin_pct),
                    # CORREÇÃO (auditoria 04/09/2026): `summary.summary` nunca
                    # existiu (código morto protegido por hasattr, sempre
                    # retornava ""). O campo correto aqui é o semáforo da
                    # própria margem de contribuição.
                    'status': self.calculator.get_contribution_margin_traffic_light(diagnostic.dre.contribution_margin_pct).value
                },
                'profit_net': {
                    'amount': float(diagnostic.dre.profit_net),
                    'percentage': float(diagnostic.dre.profit_net_pct),
                    'status': diagnostic.summary.overall_status.value
                },
                'breakeven_revenue': float(diagnostic.summary.breakeven_revenue),
            },
            
            'marketing': {
                'ads_investment': float(diagnostic.marketing.ads_investment),
                'ads_pct_revenue': float(diagnostic.marketing.ads_pct_revenue),
                'roas': float(diagnostic.marketing.roas) if diagnostic.marketing.roas > 0 else None,
                'roas_breakeven': float(diagnostic.marketing.roas_breakeven),
                'cac': float(diagnostic.marketing.cac) if diagnostic.marketing.cac > 0 else None,
                'avg_ticket': float(diagnostic.marketing.avg_ticket),
                'ltv_cac_ratio': float(diagnostic.marketing.ltv_cac_ratio) if diagnostic.marketing.ltv_cac_ratio > 0 else None,
                'primary_channel': diagnostic.marketing.primary_ads_channel,
            },
            
            'channels': [
                {
                    'name': nome_canal(c.channel),
                    'revenue': float(c.revenue),
                    'fee_rate': float(c.fee_rate),
                    'margin': {
                        'amount': float(c.margin),
                        'percentage': float(c.margin_pct),
                        'status': c.margin_traffic_light.value
                    }
                }
                for c in diagnostic.channels
            ],
            
            'cashflow': {
                'avg_collection_period': float(diagnostic.cashflow.avg_collection_period),
                'avg_payment_period': float(diagnostic.cashflow.avg_payment_period),
                'financial_cycle_days': float(diagnostic.cashflow.financial_cycle),
                'status': diagnostic.cashflow.cycle_status,
                'profit_vs_cash_alert': diagnostic.cashflow.profit_vs_cash_alert,
            },
            
            'alerts': [
                {
                    'code': a.code,
                    'rule': a.rule,
                    'impact': a.impact,
                    'urgency': a.urgency,
                    'score': a.score,
                    'action': a.action
                }
                for a in diagnostic.alerts
            ],
            
            'top_3_priorities': [
                {
                    'code': p.code,
                    'rule': p.rule,
                    'score': p.score,
                    'action': p.action
                }
                for p in diagnostic.summary.top_3_priorities
            ],
            
            'insights': diagnostic.summary.insights,
        }


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

def example_usage():
    """
    Exemplo de como usar o motor de diagnóstico.
    Este é um padrão que você pode integrar com seus agentes de IA.
    """
    
    # 1. Criar configuração do cliente
    # NOTA (04/09/2026): business_category aqui é só um valor inicial —
    # o motor recalcula sozinho a Categoria (A-E) a partir do ticket médio
    # e da margem de contribuição do cliente durante o run_diagnostic().
    config = ConfigParameters(
        client_name="E-commerce XYZ",
        analysis_period="Jan–Jun/2025",
        business_category=BusinessCategory.B,
        tax_regime=TaxRegime.SIMPLES_NACIONAL,
        tax_rate=0.04,
    )
    
    # 2. Criar dados de entrada do cliente
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
            SalesChannel.INSTAGRAM: 25000.0,
        },
        # Opcional (novidade 04/09/2026) — se você já tiver esse dado pro
        # período, informe aqui pra ativar o alerta R1. Sem esse campo,
        # nenhum alerta de retenção é gerado (fica None, não 0%).
        # recurring_customers_pct=0.25,
    )
    
    # 3. Instanciar o motor
    engine = FinancialDiagnosticEngine(config)
    
    # 4. Executar diagnóstico
    diagnostic = engine.run_diagnostic(input_data)
    
    # 5. Usar os resultados
    if diagnostic.is_valid:
        print(f"✅ Diagnóstico gerado para {diagnostic.config.client_name}")
        print(f"Status: {diagnostic.summary.overall_status.value}")
        print(f"Margem Líquida: {diagnostic.dre.profit_net_pct:.1%}")
        print(f"ROAS: {diagnostic.marketing.roas:.1f}x")
        print(f"\nTop 3 Prioridades:")
        for i, alert in enumerate(diagnostic.summary.top_3_priorities, 1):
            print(f"  {i}. {alert.rule} (Score: {alert.score})")
        
        # 6. Exportar para JSON (para APIs, agentes IA, etc)
        import json
        diagnosis_json = engine.export_to_dict(diagnostic)
        print("\n📄 JSON completo:")
        print(json.dumps(diagnosis_json, indent=2, ensure_ascii=False))
    else:
        print(f"❌ Erros na validação:")
        for error in diagnostic.validation_errors:
            print(f"  - {error}")


if __name__ == "__main__":
    example_usage()
