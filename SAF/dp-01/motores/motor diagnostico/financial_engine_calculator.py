"""
Financial Diagnostic Engine - Calculator
Máquina de cálculos - transforma INPUT em diagnóstico completo.

Este módulo implementa toda a lógica de cálculo das planilhas em Python puro.
"""

from financial_engine_models import *
import math


class FinancialCalculator:
    """
    Classe responsável por todos os cálculos do diagnóstico financeiro.
    Segue exatamente a lógica das fórmulas do Excel, mas em Python.
    """
    
    def __init__(self, config: ConfigParameters):
        self.config = config
    
    # ========================
    # VALIDAÇÃO - BASE_TRATADA
    # ========================
    
    def validate_and_sanitize(self, input_data: FinancialInput) -> ValidatedData:
        """
        Valida e sanitiza dados de entrada.
        Equivalente à aba BASE_TRATADA no Excel.
        
        Regra: se é número, usa; se não é, substitui por zero.
        Para texto: se vazio, exibe "Não informado".
        """
        valid_data = ValidatedData()
        valid_data.period = input_data.analysis_period or "Não informado"
        
        # Validação de números - se não for número, vira 0
        valid_data.revenue_gross = input_data.revenue_gross if input_data.revenue_gross > 0 else 0
        valid_data.returns_cancellations = input_data.returns_cancellations if input_data.returns_cancellations >= 0 else 0
        valid_data.cmv = input_data.cmv if input_data.cmv >= 0 else 0
        valid_data.variable_costs = input_data.variable_costs if input_data.variable_costs >= 0 else 0
        valid_data.fixed_costs = input_data.fixed_costs if input_data.fixed_costs >= 0 else 0
        valid_data.pro_labore = input_data.pro_labore if input_data.pro_labore >= 0 else 0
        valid_data.num_orders = input_data.num_orders if input_data.num_orders > 0 else 0
        
        # Marketing
        valid_data.ads_investment = input_data.ads_investment if input_data.ads_investment >= 0 else 0
        valid_data.new_customers_ads = input_data.new_customers_ads if input_data.new_customers_ads >= 0 else 0
        valid_data.primary_ads_channel = input_data.primary_ads_channel or "Não informado"
        
        # Fluxo de caixa
        valid_data.avg_collection_period = input_data.avg_collection_period if input_data.avg_collection_period >= 0 else 0
        valid_data.avg_payment_period = input_data.avg_payment_period if input_data.avg_payment_period >= 0 else 0
        
        # Canais de venda
        valid_data.channel_revenues = input_data.channel_revenues.copy()
        # CORREÇÃO (05/09/2026, pedido do analista): antes, informar
        # channel_fees_custom pra UM canal (ex.: um canal customizado que
        # não está na tabela de referência) substituía a tabela INTEIRA —
        # perdia as taxas de referência de Mercado Livre/Shopee/etc. só por
        # declarar a taxa de um canal novo. Agora é merge: a tabela de
        # referência (config/taxas_canais.json) continua valendo pros
        # canais que não foram informados em channel_fees_custom; só o(s)
        # canal(is) explicitamente informado(s) ali é que sobrescrevem.
        valid_data.channel_fees = {
            **self.config.channel_fees,
            **(input_data.channel_fees_custom or {}),
        }

        # Retenção (novidade 04/09/2026) — mantém None se não informado, pra
        # o alerta R1 não confundir "sem dado" com "0% de recorrência".
        valid_data.recurring_customers_pct = input_data.recurring_customers_pct
        
        # Status de validação
        valid_data.validation_status = {
            'revenue_gross': '✅ OK' if valid_data.revenue_gross > 0 else '⚠️ Vazio',
            'returns_cancellations': '✅ OK' if valid_data.returns_cancellations >= 0 else '⚠️ Vazio',
            'cmv': '✅ OK' if valid_data.cmv >= 0 else '⚠️ Vazio',
            'variable_costs': '✅ OK' if valid_data.variable_costs >= 0 else '⚠️ Vazio',
            'fixed_costs': '✅ OK' if valid_data.fixed_costs >= 0 else '⚠️ Vazio',
            'pro_labore': '✅ OK' if valid_data.pro_labore >= 0 else '⚠️ Vazio',
            'num_orders': '✅ OK' if valid_data.num_orders > 0 else '⚠️ Vazio',
        }
        
        return valid_data
    
    # ========================
    # DRE - Demonstração de Resultados
    # ========================
    
    def calculate_dre(self, valid_data: ValidatedData) -> DREResults:
        """
        Calcula a Demonstração do Resultado do Exercício (DRE).
        Equivalente à aba DRE no Excel.
        
        Estrutura:
        (+) Receita Bruta
        (-) Devoluções
        = RECEITA LÍQUIDA
        (-) Impostos
        (-) CMV
        = LUCRO BRUTO
        (-) Custos Variáveis
        = MARGEM DE CONTRIBUIÇÃO
        (-) Custos Fixos
        (-) Pró-labore
        = LUCRO LÍQUIDO
        """
        dre = DREResults()
        
        # Receita
        dre.revenue_gross = valid_data.revenue_gross
        dre.returns_cancellations = valid_data.returns_cancellations
        dre.revenue_net = dre.revenue_gross - dre.returns_cancellations
        
        # Impostos (sobre receita líquida)
        dre.taxes = dre.revenue_net * self.config.tax_rate
        
        # CMV
        dre.cmv = valid_data.cmv
        
        # Lucro bruto (Receita Líquida - Impostos - CMV)
        dre.profit_gross = dre.revenue_net - dre.taxes - dre.cmv
        
        # Custos Variáveis
        dre.variable_costs = valid_data.variable_costs
        
        # Margem de Contribuição (Lucro Bruto - Custos Variáveis)
        dre.contribution_margin = dre.profit_gross - dre.variable_costs
        
        # Custos Fixos
        dre.fixed_costs = valid_data.fixed_costs
        
        # Pró-labore
        dre.pro_labore = valid_data.pro_labore
        
        # Lucro Líquido
        dre.profit_net = dre.contribution_margin - dre.fixed_costs - dre.pro_labore
        
        # Cálculo de percentuais (se receita líquida > 0)
        if dre.revenue_net > 0:
            dre.tax_pct = dre.taxes / dre.revenue_net
            dre.cmv_pct = dre.cmv / dre.revenue_net
            dre.profit_gross_pct = dre.profit_gross / dre.revenue_net
            dre.variable_costs_pct = dre.variable_costs / dre.revenue_net
            dre.contribution_margin_pct = dre.contribution_margin / dre.revenue_net
            dre.fixed_costs_pct = dre.fixed_costs / dre.revenue_net
            dre.pro_labore_pct = dre.pro_labore / dre.revenue_net
            dre.profit_net_pct = dre.profit_net / dre.revenue_net
        
        return dre
    
    # ========================
    # MARKETING - ROAS, CAC, LTV
    # ========================
    
    def calculate_marketing_metrics(self, valid_data: ValidatedData, dre: DREResults) -> MarketingMetrics:
        """
        Calcula métricas de marketing.
        Equivalente à aba MARKETING no Excel.
        """
        metrics = MarketingMetrics()
        metrics.ads_investment = valid_data.ads_investment
        metrics.revenue_net = dre.revenue_net
        
        # % Ads sobre Receita Líquida
        if dre.revenue_net > 0:
            metrics.ads_pct_revenue = metrics.ads_investment / dre.revenue_net
        
        # ROAS - Return on Ad Spend
        if metrics.ads_investment > 0:
            metrics.roas = dre.revenue_net / metrics.ads_investment
        
        # ROAS de Equilíbrio (mínimo para não ter prejuízo)
        if dre.contribution_margin > 0:
            metrics.roas_breakeven = dre.revenue_net / dre.contribution_margin
        
        # CAC - Custo por Cliente Adquirido
        if valid_data.new_customers_ads > 0:
            metrics.cac = metrics.ads_investment / valid_data.new_customers_ads
        
        # Ticket Médio
        if valid_data.num_orders > 0:
            metrics.avg_ticket = dre.revenue_net / valid_data.num_orders
        
        # LTV Simplificado = Ticket × Frequência de Recompra/Ano × Anos de Retenção
        # (fórmula padrão, alinhada com CONFIG!B41/B42 da planilha — auditoria 04/09/2026)
        metrics.ltv_simplified = (
            metrics.avg_ticket *
            self.config.repurchase_frequency_per_year *
            self.config.retention_years
        )
        
        # LTV:CAC Ratio
        if metrics.cac > 0:
            metrics.ltv_cac_ratio = metrics.ltv_simplified / metrics.cac
        
        metrics.primary_ads_channel = valid_data.primary_ads_channel
        
        # Semáforos
        metrics.roas_traffic_light = self._get_roas_traffic_light(metrics.roas)
        metrics.ads_pct_traffic_light = self._get_ads_pct_traffic_light(metrics.ads_pct_revenue)
        
        return metrics
    
    def _get_roas_traffic_light(self, roas: float) -> TrafficLightStatus:
        """Determina semáforo para ROAS"""
        if roas == 0:
            return TrafficLightStatus.NO_DATA
        elif roas < self.config.roas_critical_threshold:
            return TrafficLightStatus.CRITICAL
        elif roas < self.config.roas_minimum_threshold:
            return TrafficLightStatus.MINIMUM
        elif roas < self.config.roas_good_threshold:
            return TrafficLightStatus.GOOD
        else:
            return TrafficLightStatus.EXCELLENT
    
    def _get_ads_pct_traffic_light(self, ads_pct: float) -> TrafficLightStatus:
        """Determina semáforo para % de Ads (inverso - menor é melhor)"""
        if ads_pct == 0:
            return TrafficLightStatus.NO_DATA
        elif ads_pct > self.config.ads_minimum_threshold:
            return TrafficLightStatus.CRITICAL
        elif ads_pct > self.config.ads_good_threshold:
            return TrafficLightStatus.MINIMUM
        elif ads_pct > self.config.ads_excellent_threshold:
            return TrafficLightStatus.GOOD
        else:
            return TrafficLightStatus.EXCELLENT
    
    # ========================
    # CANAIS - Desempenho por canal
    # ========================
    
    def calculate_channel_performance(self, valid_data: ValidatedData, dre: DREResults) -> list[ChannelPerformance]:
        """
        Calcula margem de contribuição por canal de venda.
        Equivalente à aba CANAIS no Excel.
        
        Fórmula da margem por canal:
        Margem = (Faturamento - Custo Taxa - CMV Proporcional) / Faturamento
        
        CMV é alocado proporcionalmente ao faturamento de cada canal.
        """
        channels = []
        total_revenue = sum(valid_data.channel_revenues.values())
        
        for channel, revenue in valid_data.channel_revenues.items():
            if revenue <= 0:
                continue
            
            perf = ChannelPerformance(channel=channel)
            perf.revenue = revenue
            
            # Taxa do canal (usa taxa customizada se informada, senão usa padrão do config)
            perf.fee_rate = (
                valid_data.channel_fees.get(channel, self.config.channel_fees.get(channel, 0))
            )
            
            # Custo da taxa
            perf.fee_cost = perf.revenue * perf.fee_rate
            
            # CMV proporcional ao canal
            if total_revenue > 0 and dre.revenue_net > 0:
                perf.cmv_proportional = dre.cmv * (revenue / dre.revenue_net)
            
            # Margem (R$)
            perf.margin = perf.revenue - perf.fee_cost - perf.cmv_proportional
            
            # Margem (%)
            if perf.revenue > 0:
                perf.margin_pct = perf.margin / perf.revenue
            
            # Semáforo para margem
            perf.margin_traffic_light = self._get_channel_margin_traffic_light(perf.margin_pct)
            
            channels.append(perf)
        
        return sorted(channels, key=lambda c: c.revenue, reverse=True)
    
    def _get_channel_margin_traffic_light(self, margin_pct: float) -> TrafficLightStatus:
        """Determina semáforo para margem por canal"""
        if margin_pct < 0:
            return TrafficLightStatus.CRITICAL  # Prejuízo
        elif margin_pct < 0.10:
            return TrafficLightStatus.MINIMUM   # < 10%
        elif margin_pct < 0.20:
            return TrafficLightStatus.GOOD      # 10-20%
        else:
            return TrafficLightStatus.EXCELLENT # > 20%
    
    # ========================
    # FLUXO DE CAIXA
    # ========================
    
    def calculate_cashflow(self, valid_data: ValidatedData, dre: DREResults) -> CashFlowAnalysis:
        """
        Calcula ciclo financeiro e risco de caixa.
        Equivalente à aba FLUXO_CAIXA no Excel.
        
        Ciclo Financeiro = PMR (Prazo Médio de Recebimento) - PMP (Prazo Médio de Pagamento)
        Positivo = recebe depois que paga = risco de caixa
        """
        cf = CashFlowAnalysis()
        cf.avg_collection_period = valid_data.avg_collection_period
        cf.avg_payment_period = valid_data.avg_payment_period
        cf.financial_cycle = cf.avg_collection_period - cf.avg_payment_period
        
        # Status do ciclo
        if cf.avg_collection_period == 0 or cf.avg_payment_period == 0:
            cf.cycle_status = "Dados não informados"
            cf.cycle_traffic_light = TrafficLightStatus.NO_DATA
        elif cf.financial_cycle > self.config.cycle_critical_threshold:
            cf.cycle_status = "🔴 Risco de capital de giro"
            cf.cycle_traffic_light = TrafficLightStatus.CRITICAL
        elif cf.financial_cycle > 0:
            cf.cycle_status = "🟠 Atenção"
            cf.cycle_traffic_light = TrafficLightStatus.MINIMUM
        else:
            cf.cycle_status = "🟢 Saudável"
            cf.cycle_traffic_light = TrafficLightStatus.EXCELLENT
        
        # Alerta: Lucro × Caixa
        if (dre.profit_net > 0 and 
            cf.financial_cycle > self.config.cycle_alert_threshold):
            cf.profit_vs_cash_alert = (
                "⚠️ Lucrativo no papel mas com risco de caixa"
            )
        else:
            cf.profit_vs_cash_alert = "✅ Sem conflito identificado"
        
        return cf
    
    # ========================
    # MÉTRICAS - Consolidação com Semáforos
    # ========================
    
    def get_contribution_margin_traffic_light(self, margin_pct: float) -> TrafficLightStatus:
        """Semáforo para Margem de Contribuição"""
        if margin_pct < self.config.mc_critical_threshold:
            return TrafficLightStatus.CRITICAL
        elif margin_pct < self.config.mc_minimum_threshold:
            return TrafficLightStatus.MINIMUM
        elif margin_pct < self.config.mc_good_threshold:
            return TrafficLightStatus.GOOD
        else:
            return TrafficLightStatus.EXCELLENT
    
    def get_profit_margin_traffic_light(self, margin_pct: float) -> TrafficLightStatus:
        """Semáforo para Margem Líquida"""
        if margin_pct < self.config.ml_critical_threshold:
            return TrafficLightStatus.CRITICAL
        elif margin_pct < self.config.ml_minimum_threshold:
            return TrafficLightStatus.MINIMUM
        elif margin_pct < self.config.ml_good_threshold:
            return TrafficLightStatus.GOOD
        else:
            return TrafficLightStatus.EXCELLENT
    
    def calculate_breakeven(self, dre: DREResults) -> float:
        """
        Calcula faturamento mínimo para não ter prejuízo (breakeven).
        
        Fórmula: (Custos Fixos + Pró-labore) × Receita Líquida / Margem de Contribuição
        """
        if dre.contribution_margin <= 0 or dre.revenue_net <= 0:
            return 0
        
        total_fixed = dre.fixed_costs + dre.pro_labore
        breakeven = (total_fixed * dre.revenue_net) / dre.contribution_margin
        return breakeven
