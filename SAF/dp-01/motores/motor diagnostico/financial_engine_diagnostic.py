"""
Financial Diagnostic Engine - Diagnostic & Alerts
Sistema de diagnóstico automático com 14 regras de alerta (eram 13 até
03/09/2026; R1 de retenção por Categoria adicionado em 04/09/2026).

Equivalente às abas ALERTAS e PRIORIDADES do Excel.
"""

from financial_engine_models import *
from financial_engine_calculator import FinancialCalculator


class DiagnosticEngine:
    """
    Motor de diagnóstico que executa as 14 regras de alerta automáticas.
    Cada alerta tem um código (F1, F2, M1, etc), impacto, urgência e score.
    """
    
    def __init__(self, config: ConfigParameters, calculator: FinancialCalculator):
        self.config = config
        self.calc = calculator
    
    def generate_alerts(
        self,
        valid_data: ValidatedData,
        dre: DREResults,
        marketing: MarketingMetrics,
        channels: list[ChannelPerformance],
        cashflow: CashFlowAnalysis
    ) -> list[Alert]:
        """
        Gera lista de todos os 14 alertas possíveis.
        Retorna apenas os SIM (ativos) com score calculado.
        """
        alerts = []
        
        # ========================
        # ALERTAS FINANCEIROS (F1-F5)
        # ========================
        
        # F1: MC CRÍTICA
        if dre.contribution_margin_pct < self.config.mc_critical_threshold:
            alerts.append(Alert(
                code="F1",
                rule="Margem Contribuição CRÍTICA (< 20%)",
                is_active=True,
                impact=5,
                urgency=5,
                action="Revisar precificação e custos variáveis"
            ))
        
        # F2: MC MÍNIMA
        elif (dre.contribution_margin_pct >= self.config.mc_critical_threshold and
              dre.contribution_margin_pct < self.config.mc_minimum_threshold):
            alerts.append(Alert(
                code="F2",
                rule="Margem Contribuição MÍNIMA (20–35%)",
                is_active=True,
                impact=3,
                urgency=3,
                action="Identificar custos variáveis reduzíveis"
            ))
        
        # F3: ML NEGATIVA (Prejuízo)
        if dre.profit_net_pct < 0:
            alerts.append(Alert(
                code="F3",
                rule="Margem Líquida NEGATIVA — Prejuízo",
                is_active=True,
                impact=5,
                urgency=5,
                action="Ação imediata obrigatória"
            ))
        
        # F4: ML MÍNIMA
        elif (dre.profit_net_pct >= 0 and
              dre.profit_net_pct < self.config.ml_minimum_threshold):
            alerts.append(Alert(
                code="F4",
                rule="Margem Líquida MÍNIMA (0–10%)",
                is_active=True,
                impact=4,
                urgency=4,
                action="Custos fixos ou pró-labore comprometendo"
            ))
        
        # F5: Faturamento abaixo do Breakeven
        breakeven = self.calc.calculate_breakeven(dre)
        if breakeven > 0 and dre.revenue_net < breakeven:
            alerts.append(Alert(
                code="F5",
                rule="Faturamento ABAIXO do Breakeven",
                is_active=True,
                impact=5,
                urgency=5,
                action="Aumentar faturamento ou reduzir custos fixos"
            ))
        
        # ========================
        # ALERTAS DE MARKETING (M1-M5)
        # ========================
        
        # M1: ROAS abaixo do Equilíbrio
        if (marketing.ads_investment > 0 and
            marketing.roas > 0 and
            marketing.roas < marketing.roas_breakeven):
            alerts.append(Alert(
                code="M1",
                rule="ROAS abaixo do Equilíbrio",
                is_active=True,
                impact=4,
                urgency=4,
                action="Ads gerando prejuízo — revisar campanhas"
            ))
        
        # M2: ROAS CRÍTICO
        if (marketing.ads_investment > 0 and
            marketing.roas > 0 and
            marketing.roas < self.config.roas_critical_threshold):
            alerts.append(Alert(
                code="M2",
                rule="ROAS CRÍTICO (< 2x)",
                is_active=True,
                impact=5,
                urgency=5,
                action="Inviável — cada R$1 em ads gera < R$2"
            ))
        
        # M3: % Ads CRÍTICO
        if (marketing.ads_investment > 0 and
            marketing.ads_pct_revenue > self.config.ads_minimum_threshold):
            alerts.append(Alert(
                code="M3",
                rule="% Ads CRÍTICO (> 30% da Receita)",
                is_active=True,
                impact=4,
                urgency=4,
                action="Marketing consome o negócio"
            ))
        
        # M4: LTV:CAC em RISCO
        if (marketing.ltv_cac_ratio > 0 and
            marketing.ltv_cac_ratio < self.config.ltv_cac_minimum_threshold):
            alerts.append(Alert(
                code="M4",
                rule="LTV:CAC em RISCO (< 3x) — ESTIMATIVA",
                is_active=True,
                impact=3,
                urgency=3,
                action="Revisar estratégia de aquisição"
            ))
        
        # M5: LTV:CAC CRÍTICO
        if (marketing.ltv_cac_ratio > 0 and
            marketing.ltv_cac_ratio < self.config.ltv_cac_critical_threshold):
            alerts.append(Alert(
                code="M5",
                rule="LTV:CAC CRÍTICO (< 1x) — ESTIMATIVA",
                is_active=True,
                impact=5,
                urgency=5,
                action="Perde dinheiro em cada cliente"
            ))
        
        # ========================
        # ALERTAS DE CANAIS (C1-C2)
        # ========================
        
        min_margin = min([c.margin_pct for c in channels], default=1.0)
        
        # C1: Canal com margem NEGATIVA
        if any(c.margin_pct < 0 for c in channels):
            alerts.append(Alert(
                code="C1",
                rule="Canal com MARGEM NEGATIVA (Prejuízo)",
                is_active=True,
                impact=4,
                urgency=4,
                action="Avaliar descontinuação ou repricing"
            ))
        
        # C2: Canal com margem MÍNIMA
        elif (max([c.revenue for c in channels], default=0) > 0 and
              min_margin < 0.10):
            alerts.append(Alert(
                code="C2",
                rule="Canal com MARGEM MÍNIMA (< 10%)",
                is_active=True,
                impact=2,
                urgency=3,
                action="Renegociar taxas ou ajustar preço"
            ))
        
        # ========================
        # ALERTA DE RETENÇÃO (R1) — NOVIDADE 04/09/2026
        # ========================
        # Só avalia quando `recurring_customers_pct` foi de fato informado
        # (None = "não informado", não é o mesmo que 0%) — mesmo cuidado já
        # tomado no S1 do Motor de Mensalidade, pra não gerar alerta falso
        # quando o dado simplesmente não foi preenchido. O piso é o mesmo
        # piso por Categoria usado no Motor de Mensalidade (ver
        # CATEGORY_RECURRING_FLOOR em financial_engine_models.py), aplicado
        # aqui sobre o período completo analisado (tipicamente 6 meses),
        # não mês a mês — por isso não há aqui a checagem de "sustentado"
        # que existe no S1.
        if valid_data.recurring_customers_pct is not None:
            recurring_floor = get_recurring_floor(self.config.business_category)
            if valid_data.recurring_customers_pct < recurring_floor:
                alerts.append(Alert(
                    code="R1",
                    rule=f"Clientes Recorrentes BAIXOS (< {recurring_floor:.0%}, piso da Categoria do negócio)",
                    is_active=True,
                    impact=4,
                    urgency=4,
                    action="Revisar estratégia de retenção"
                ))

        # ========================
        # ALERTAS DE FLUXO DE CAIXA (X1)
        # ========================
        
        # X1: Ciclo Financeiro CRÍTICO
        if (cashflow.avg_collection_period > 0 and
            cashflow.avg_payment_period > 0 and
            cashflow.financial_cycle > self.config.cycle_critical_threshold):
            alerts.append(Alert(
                code="X1",
                rule="Ciclo Financeiro CRÍTICO (> 30 dias)",
                is_active=True,
                impact=3,
                urgency=3,
                action="Rever prazo de recebimento"
            ))
        
        # Calcular scores
        for alert in alerts:
            alert.score = alert.impact * alert.urgency
        
        return alerts
    
    def get_top_3_priorities(self, alerts: list[Alert]) -> list[Alert]:
        """
        Rankeia alertas ativos por score (Impacto × Urgência).
        Retorna top 3.
        """
        active_alerts = [a for a in alerts if a.is_active]
        sorted_alerts = sorted(active_alerts, key=lambda a: a.score, reverse=True)
        return sorted_alerts[:3]
    
    def get_overall_status(self, dre: DREResults) -> TrafficLightStatus:
        """
        Determina o status geral do negócio baseado na margem líquida.
        """
        profit_margin = dre.profit_net_pct
        
        if profit_margin < 0:
            return TrafficLightStatus.CRITICAL
        elif profit_margin < self.config.ml_minimum_threshold:
            return TrafficLightStatus.MINIMUM
        elif profit_margin < self.config.ml_good_threshold:
            return TrafficLightStatus.GOOD
        else:
            return TrafficLightStatus.EXCELLENT


class InsightGenerator:
    """
    Gera insights em linguagem natural para o roteiro de vídeo e relatório.
    Equivalente à aba INSIGHTS no Excel.
    """
    
    def __init__(self, config: ConfigParameters, calculator: FinancialCalculator):
        self.config = config
        self.calc = calculator
    
    def generate_all_insights(
        self,
        valid_data: ValidatedData,
        dre: DREResults,
        marketing: MarketingMetrics,
        channels: list[ChannelPerformance],
        cashflow: CashFlowAnalysis,
        summary: DiagnosticSummary
    ) -> Dict[str, str]:
        """Gera todos os 10 blocos de insights"""
        insights = {}
        
        insights['STATUS GERAL'] = self._status_geral(summary)
        insights['LUCRATIVIDADE'] = self._lucratividade(dre)
        insights['MARGEM_CONTRIBUICAO'] = self._margem_contribuicao(dre, summary)
        insights['BREAKEVEN'] = self._breakeven(dre, summary)
        insights['MARKETING'] = self._marketing(marketing, valid_data)
        insights['CANAIS'] = self._canais(channels, summary)
        insights['LTV_CAC'] = self._ltv_cac(marketing)
        insights['CATEGORIA'] = self._categoria_negocio()
        insights['PRIORIDADES'] = self._prioridades(summary)
        insights['FLUXO_CAIXA'] = self._fluxo_caixa(cashflow)
        
        return insights
    
    def _status_geral(self, summary: DiagnosticSummary) -> str:
        """Bloco 1: STATUS GERAL"""
        status_text = summary.overall_status.value.split('—')[0].strip()
        return (
            f"Seu negócio está {status_text} — Receita Líquida de "
            f"R$ {summary.revenue_net:,.2f} no período {summary.analysis_period}."
        )
    
    def _lucratividade(self, dre: DREResults) -> str:
        """Bloco 2: LUCRATIVIDADE"""
        if dre.profit_net >= 0:
            insight = (
                f"Lucro líquido de R$ {dre.profit_net:,.2f} "
                f"({dre.profit_net_pct:.1%} de margem). "
            )
            if dre.profit_net_pct < self.config.ml_good_threshold:
                insight += "Há espaço importante para melhorar a margem."
            else:
                insight += "Boa performance de margem."
        else:
            insight = (
                f"PREJUÍZO de R$ {abs(dre.profit_net):,.2f}. "
                f"O negócio está gastando mais do que fatura. "
                f"Ação imediata necessária."
            )
        
        return insight
    
    def _margem_contribuicao(self, dre: DREResults, summary: DiagnosticSummary) -> str:
        """Bloco 3: MARGEM DE CONTRIBUIÇÃO"""
        # CORREÇÃO (auditoria 04/09/2026): `summary.summary` nunca existiu em
        # DiagnosticSummary (código morto protegido por hasattr, sempre
        # retornava ""). O que o bloco realmente precisa aqui é o semáforo
        # da própria margem de contribuição.
        status = self.calc.get_contribution_margin_traffic_light(dre.contribution_margin_pct).value
        
        insight = (
            f"{status} — {dre.contribution_margin_pct:.1%} de margem de contribuição. "
        )
        
        if dre.contribution_margin_pct < self.config.mc_critical_threshold:
            insight += (
                "Não cobre custos fixos com folga — "
                "revisar precificação e custos variáveis é urgente."
            )
        elif dre.contribution_margin_pct < self.config.mc_minimum_threshold:
            insight += (
                "Existe mas sem gordura — qualquer variação de custo desequilibra o negócio."
            )
        elif dre.contribution_margin_pct < self.config.mc_good_threshold:
            insight += (
                "Margem saudável — permite cobrir fixos com margem líquida real."
            )
        else:
            insight += "Excelente posição — pricing eficiente."
        
        return insight
    
    def _breakeven(self, dre: DREResults, summary: DiagnosticSummary) -> str:
        """Bloco 4: BREAKEVEN"""
        breakeven = summary.breakeven_revenue
        
        if breakeven == 0:
            return "Dados insuficientes para calcular o ponto de equilíbrio."
        
        insight = (
            f"Para não ter prejuízo, o negócio precisa faturar pelo menos "
            f"R$ {breakeven:,.2f} por mês. "
        )
        
        if dre.revenue_net < breakeven:
            insight += "Faturamento atual está ABAIXO desse patamar — situação crítica."
        else:
            insight += "Faturamento atual está ACIMA — breakeven atingido."
        
        return insight
    
    def _marketing(self, marketing: MarketingMetrics, valid_data: ValidatedData) -> str:
        """Bloco 5: MARKETING"""
        if marketing.ads_investment == 0:
            return (
                "Dados de marketing não foram informados. "
                "Recomenda-se coletar ROAS e CAC para a próxima análise."
            )
        
        insight = (
            f"ROAS atual: {marketing.roas:.1f}x | "
            f"ROAS mínimo para não perder: {marketing.roas_breakeven:.1f}x. "
        )
        
        if marketing.roas < marketing.roas_breakeven:
            insight += "Os anúncios estão gerando prejuízo. Revisar campanhas é urgente."
        else:
            insight += "Anúncios acima do ponto de equilíbrio."
            if valid_data.primary_ads_channel == "TikTok Ads":
                insight += (
                    " Atenção: TikTok está em maturação no BR — "
                    "ROAS de 2x pode ser aceitável nesse canal."
                )
        
        return insight
    
    def _canais(self, channels: list[ChannelPerformance], summary: DiagnosticSummary) -> str:
        """Bloco 6: CANAIS"""
        if not channels or max([c.revenue for c in channels], default=0) == 0:
            return "Dados de canais não informados."
        
        top_channel = summary.top_channel_by_revenue
        best_margin_channel = summary.top_channel_by_margin
        worst_channel = summary.worst_channel
        
        insight = (
            f"Canal com maior faturamento: {top_channel} | "
            f"Canal com melhor margem: {best_margin_channel} | "
            f"Canal que mais preocupa: {worst_channel}. "
        )
        
        if any(c.margin_pct < 0 for c in channels):
            insight += (
                "Atenção: há canal com margem NEGATIVA — "
                "avaliar descontinuação ou repricing urgente."
            )
        else:
            insight += "Todos os canais ativos com margem positiva."
        
        return insight
    
    def _ltv_cac(self, marketing: MarketingMetrics) -> str:
        """Bloco 7: LTV:CAC"""
        if marketing.ltv_cac_ratio == 0:
            return "Dados insuficientes para calcular LTV:CAC."
        
        # REMOÇÃO (auditoria 05/09/2026): recomendava "utilize a planilha de
        # Cohort" — esse produto não vai existir (confirmado com o
        # analista). Frase removida em vez de trocada por outra recomendação,
        # já que não há hoje nenhum produto Finspots que cubra esse caso.
        return (
            f"LTV:CAC estimado: {marketing.ltv_cac_ratio:.1f}x. "
            f"⚠️ ATENÇÃO: valor estimado baseado em dados declarados, não em "
            f"acompanhamento individual por cliente ao longo do tempo."
        )
    
    def _categoria_negocio(self) -> str:
        """
        Bloco 8: CATEGORIA DO NEGÓCIO

        ATUALIZAÇÃO (04/09/2026): os pisos de retenção citados abaixo foram
        recalculados a partir de pesquisa de mercado de taxa de recompra por
        ticket médio/nicho (Prax Analytics — 1.000+ e-commerces brasileiros;
        Rivo/Flawless Magazine — benchmarks globais por vertical), e agora
        cobrem as 5 categorias de forma consistente. Antes só C (5%) e D
        (10%) tinham número — A, B e E não tinham nenhum piso citado, e os
        valores de C/D eram de um rascunho muito antigo, bem abaixo do que a
        pesquisa de mercado sugere. Os mesmos números são usados como regra
        de verdade (não só texto) no Motor de Mensalidade — ver
        CATEGORY_RECURRING_FLOOR em monthly_engine_models.py.
        """
        category = self.config.business_category

        if category == BusinessCategory.A:
            return (
                "Negócio Categoria A (ticket alto, frequência baixa) — "
                "foco em ROAS elevado por transação e estratégias de cross-sell. "
                "Retenção abaixo de 12% é alerta real."
            )
        elif category == BusinessCategory.B:
            return (
                "Negócio Categoria B (ticket médio-alto) — "
                "equilibrar margem por pedido com volume consistente. "
                "Retenção abaixo de 20% é alerta real."
            )
        elif category == BusinessCategory.C:
            return (
                "Negócio Categoria C (ticket médio-baixo) — "
                "volume é o motor. Retenção abaixo de 28% é alerta real."
            )
        elif category == BusinessCategory.D:
            return (
                "Negócio Categoria D (ticket baixo, margem alta) — "
                "LTV e retenção são os principais indicadores de saúde. "
                "Retenção abaixo de 35% requer ação."
            )
        else:
            return (
                "Negócio Categoria E (ticket baixo, margem baixa) — "
                "volume e eficiência operacional são essenciais. "
                "Qualquer aumento de custo variável é crítico. "
                "Retenção abaixo de 45% é alerta real."
            )
    
    def _prioridades(self, summary: DiagnosticSummary) -> str:
        """Bloco 9: PRIORIDADES (Top 3)"""
        if not summary.top_3_priorities:
            return "✅ Nenhum alerta crítico identificado."
        
        insight = "Problemas prioritários que exigem ação:\n"
        for i, alert in enumerate(summary.top_3_priorities, 1):
            insight += f"{i}. {alert.rule} (Score: {alert.score}) - {alert.action}\n"
        
        return insight.strip()
    
    def _fluxo_caixa(self, cashflow: CashFlowAnalysis) -> str:
        """Bloco 10: FLUXO DE CAIXA"""
        if (cashflow.avg_collection_period == 0 or
            cashflow.avg_payment_period == 0):
            return "Dados de fluxo de caixa não informados."
        
        insight = (
            f"Ciclo financeiro de {cashflow.financial_cycle:.0f} dias. "
        )
        
        if cashflow.financial_cycle > self.config.cycle_alert_threshold:
            insight += (
                "Risco de caixa: o negócio paga antes de receber. "
                "Lucro no papel não significa dinheiro disponível."
            )
        else:
            insight += "Dentro do saudável."
        
        return insight
