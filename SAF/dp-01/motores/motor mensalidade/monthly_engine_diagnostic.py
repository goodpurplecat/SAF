"""
Monthly Diagnostic Engine - Diagnostic & Alerts
Sistema de Alertas Mensal com 16 regras:
- F1-F6: Alertas Financeiros Absolutos
- M4-M5: Alertas de LTV:CAC (adicionado na auditoria de 04/09/2026,
  para paridade com o Motor de Diagnóstico)
- V1-V3: Alertas de Variação Financeira
- S1-S4: Alertas de Inteligência de Vendas
- X1: Alerta de Fluxo de Caixa (NOVIDADE 14/09/2026 — paridade com o X1
  do Motor de Diagnóstico, agora que calculate_cashflow_for_month() existe)
"""

from monthly_engine_models import *
from monthly_engine_calculator import MonthlyCalculator


class MonthlyDiagnosticEngine:
    """Motor de diagnóstico com 15 alertas mensais (F1-F6, M4-M5, V1-V3, S1-S4)"""
    
    def __init__(self, config: Dict[str, Any], calculator: MonthlyCalculator):
        self.config = config
        self.calc = calculator
    
    # Quantos meses seguidos abaixo do piso da Categoria são exigidos pra
    # considerar a frequência baixa "sustentada" (e não só um mês ruim
    # pontual). Inclui o mês atual — ex.: 3 = mês atual + 2 meses anteriores.
    # Usa o mesmo horizonte de "últimos 3 meses" já assumido no insight de
    # TENDÊNCIA (ver generate_all_insights, bloco 10) — ajustável aqui se
    # quiser um horizonte diferente.
    SUSTAINED_LOW_FREQUENCY_MONTHS = 3

    def generate_alerts(
        self,
        metrics: Dict[str, float],
        comparative: Dict[str, MonthlyComparative],
        sales_intel: SalesIntelligence,
        previous_metrics: Optional[Dict[str, float]] = None,
        recurring_pct_history: Optional[List[float]] = None,
        cashflow: Optional[MonthlyCashFlowAnalysis] = None,
    ) -> List[MonthlyAlert]:
        """Gera 16 alertas possíveis para o mês"""
        
        alerts = []
        
        # ========================
        # GRUPO F: Alertas Financeiros Absolutos (F1-F6)
        # ========================
        
        cm_pct = metrics['contribution_margin_pct']
        ml_pct = metrics['profit_margin_pct']
        revenue_net = metrics['revenue_net']
        profit_net = metrics['profit_net']
        breakeven = metrics['breakeven']
        roas = metrics['roas']
        roas_breakeven = metrics['roas_breakeven']
        
        # F1: MC CRÍTICA
        if cm_pct < self.calc.mc_critical:
            alerts.append(MonthlyAlert(
                code="F1",
                rule="Margem Contribuição CRÍTICA (< 20%)",
                is_active=True,
                impact=5,
                urgency=5,
                action="Revisar precificação e custos variáveis com urgência"
            ))
        
        # F2: MC MÍNIMA
        elif cm_pct < self.calc.mc_minimum:
            alerts.append(MonthlyAlert(
                code="F2",
                rule="Margem Contribuição MÍNIMA (20–35%)",
                is_active=True,
                impact=3,
                urgency=3,
                action="Identificar custos variáveis reduzíveis"
            ))
        
        # F3: ML NEGATIVA
        if ml_pct < 0:
            alerts.append(MonthlyAlert(
                code="F3",
                rule="Margem Líquida NEGATIVA — Prejuízo",
                is_active=True,
                impact=5,
                urgency=5,
                action="Prejuízo no mês — ação imediata obrigatória"
            ))
        
        # F4: ML MÍNIMA
        elif ml_pct < self.calc.ml_minimum:
            alerts.append(MonthlyAlert(
                code="F4",
                rule="Margem Líquida MÍNIMA (0–10%)",
                is_active=True,
                impact=4,
                urgency=4,
                action="Custos comprometendo o resultado"
            ))
        
        # F5: Faturamento < Breakeven
        if breakeven > 0 and revenue_net < breakeven:
            alerts.append(MonthlyAlert(
                code="F5",
                rule="Faturamento ABAIXO do Breakeven",
                is_active=True,
                impact=5,
                urgency=5,
                action="Aumentar faturamento ou reduzir custos fixos"
            ))
        
        # F6: ROAS < Equilíbrio
        if metrics.get('ads_pct', 0) > 0 and roas > 0 and roas < roas_breakeven:
            alerts.append(MonthlyAlert(
                code="F6",
                rule="ROAS abaixo do Equilíbrio",
                is_active=True,
                impact=4,
                urgency=4,
                action="Ads gerando prejuízo — revisar campanhas"
            ))

        # ========================
        # GRUPO M: Alertas de LTV:CAC (M4-M5)
        # CORREÇÃO (auditoria 04/09/2026): o motor mensal já calculava
        # metrics['ltv_cac'] (ver monthly_engine_calculator.py) mas nunca o
        # comparava a nenhum limite — não existia nenhum alerta equivalente
        # ao M4/M5 do Motor de Diagnóstico (financial_engine_diagnostic.py),
        # então um risco real de LTV:CAC nunca era sinalizado no relatório
        # mensal. Os dois blocos abaixo replicam exatamente a mesma regra e
        # os mesmos limites (ltv_cac_minimum_threshold=3x,
        # ltv_cac_critical_threshold=1x) do Motor de Diagnóstico, para
        # manter paridade entre os dois motores.
        # ========================

        ltv_cac = metrics.get('ltv_cac', 0)
        ltv_cac_minimum = self.config.get('ltv_cac_minimum_threshold', 3.0)
        ltv_cac_critical = self.config.get('ltv_cac_critical_threshold', 1.0)

        # M4: LTV:CAC em RISCO
        if ltv_cac > 0 and ltv_cac < ltv_cac_minimum:
            alerts.append(MonthlyAlert(
                code="M4",
                rule="LTV:CAC em RISCO (< 3x) — ESTIMATIVA",
                is_active=True,
                impact=3,
                urgency=3,
                action="Revisar estratégia de aquisição"
            ))

        # M5: LTV:CAC CRÍTICO
        if ltv_cac > 0 and ltv_cac < ltv_cac_critical:
            alerts.append(MonthlyAlert(
                code="M5",
                rule="LTV:CAC CRÍTICO (< 1x) — ESTIMATIVA",
                is_active=True,
                impact=5,
                urgency=5,
                action="Perde dinheiro em cada cliente adquirido"
            ))

        # ========================
        # GRUPO V: Alertas de Variação Financeira (V1-V3)
        # ========================
        
        if previous_metrics:
            # V1: Receita caiu
            if 'revenue_net' in comparative:
                rev_comp = comparative['revenue_net']
                if rev_comp.current_month_value > 0 and rev_comp.current_month_value < rev_comp.previous_month_value * 0.95:
                    alerts.append(MonthlyAlert(
                        code="V1",
                        rule="Receita Líquida CAIU vs mês anterior",
                        is_active=True,
                        impact=4,
                        urgency=4,
                        action="Investigar causa da queda de faturamento"
                    ))
            
            # V2: Lucro caiu significativamente
            if 'profit_net' in comparative:
                profit_comp = comparative['profit_net']
                if profit_comp.variation_pct < -0.20:  # Queda > 20%
                    alerts.append(MonthlyAlert(
                        code="V2",
                        rule="Lucro Líquido CAIU significativamente",
                        is_active=True,
                        impact=5,
                        urgency=5,
                        action="Identificar gargalo principal"
                    ))
            
            # V3: Margem Líquida caiu
            if 'profit_margin_pct' in comparative:
                ml_comp = comparative['profit_margin_pct']
                if ml_comp.current_month_value < ml_comp.previous_month_value * 0.90:  # Queda 10%
                    alerts.append(MonthlyAlert(
                        code="V3",
                        rule="Margem Líquida CAIU",
                        is_active=True,
                        impact=4,
                        urgency=5,
                        action="Analisar variação de custos"
                    ))
        
        # ========================
        # GRUPO S: Alertas de Inteligência de Vendas (S1-S4)
        # ========================
        
        # S1: Clientes recorrentes caíram
        # CORREÇÃO (auditoria 04/09/2026): antes disparava sempre que a
        # "Inteligência de Vendas" não era preenchida (recurring_pct fica em
        # 0.0 por padrão em SalesIntelligence, que é < 0.30), tratando
        # "sem dados" como "0% de recorrência" — um falso positivo. Agora só
        # avalia quando há evidência de que a base de clientes foi
        # realmente informada (mesmo padrão já usado nos alertas de
        # marketing, que exigem ads_investment > 0).
        #
        # NOVIDADE (04/09/2026): o piso de 30% deixou de ser fixo pra todo
        # mundo. Cada Categoria de negócio (A-E) tem seu próprio piso de
        # recorrência esperado — ver CATEGORY_RECURRING_FLOOR em
        # monthly_engine_models.py para a régua completa e as fontes de
        # mercado usadas. Um negócio Categoria A (ticket alto) é saudável
        # com bem menos recorrência que um Categoria E (ticket baixo,
        # precisa de volume pra se sustentar).
        #
        # NOVIDADE (04/09/2026): o alerta agora distingue frequência baixa
        # "sustentada" (SUSTAINED_LOW_FREQUENCY_MONTHS meses seguidos abaixo
        # do piso) de uma queda pontual de um único mês. Se o chamador
        # fornecer `recurring_pct_history` com meses suficientes, exige que
        # o mês atual E os anteriores estejam todos abaixo do piso. Sem
        # histórico suficiente (cliente novo, poucos meses de dados), cai no
        # comportamento anterior — avalia só o mês atual, pra não deixar um
        # problema real de fora só por falta de histórico.
        recurring_floor = get_recurring_floor(self.config.get('business_category', 'C'))
        current_below_floor = sales_intel.recurring_pct < recurring_floor

        months_needed_before_current = self.SUSTAINED_LOW_FREQUENCY_MONTHS - 1
        has_enough_history = (
            recurring_pct_history is not None
            and len(recurring_pct_history) >= months_needed_before_current
        )

        if has_enough_history:
            previous_months_below_floor = all(
                v < recurring_floor
                for v in recurring_pct_history[-months_needed_before_current:]
            )
            is_sustained_low_frequency = current_below_floor and previous_months_below_floor
            s1_rule_text = (
                f"Clientes Recorrentes BAIXOS há {self.SUSTAINED_LOW_FREQUENCY_MONTHS}+ meses "
                f"(< {recurring_floor:.0%}, piso da Categoria do negócio)"
            )
        else:
            is_sustained_low_frequency = current_below_floor
            s1_rule_text = (
                f"Clientes Recorrentes BAIXOS (< {recurring_floor:.0%}, piso da Categoria do "
                f"negócio — histórico insuficiente pra confirmar tendência)"
            )

        if (sales_intel.new_customers_count + sales_intel.recurring_customers_count) > 0 and \
                is_sustained_low_frequency:
            alerts.append(MonthlyAlert(
                code="S1",
                rule=s1_rule_text,
                is_active=True,
                impact=4,
                urgency=4,
                action="Revisar estratégia de retenção"
            ))
        
        # S2: Pior margem é crítica
        if sales_intel.worst_product_margin_pct < 0:
            alerts.append(MonthlyAlert(
                code="S2",
                rule="Produto com Margem NEGATIVA",
                is_active=True,
                impact=4,
                urgency=3,
                action="Descontinuar ou repricing do produto"
            ))
        
        # S3: Muitos produtos parados
        if sales_intel.paused_products_count > 10:
            alerts.append(MonthlyAlert(
                code="S3",
                rule="Produtos Parados AUMENTARAM (> 10)",
                is_active=True,
                impact=3,
                urgency=3,
                action="Risco de estoque parado e capital preso"
            ))
        
        # S4: Canal principal com margem baixa
        # CORREÇÃO (auditoria 04/09/2026): mesmo problema do S1 — sem essa
        # checagem, o alerta disparava por padrão quando o canal líder não
        # era informado (best_channel_margin_pct = 0.0 por padrão).
        if sales_intel.best_channel_revenue > 0 and sales_intel.best_channel_margin_pct < 0.10:
            alerts.append(MonthlyAlert(
                code="S4",
                rule="Canal Líder com Margem MÍNIMA (< 10%)",
                is_active=True,
                impact=3,
                urgency=3,
                action="Renegociar taxas ou ajustar preço"
            ))
        
        # ========================
        # ALERTA DE FLUXO DE CAIXA (X1)
        # NOVIDADE (auditoria 14/09/2026) — espelha X1 do Motor de
        # Diagnóstico, agora que calculate_cashflow_for_month() existe.
        # ========================

        if (cashflow is not None
                and cashflow.avg_collection_period > 0
                and cashflow.avg_payment_period > 0
                and cashflow.financial_cycle > self.config.get('cycle_critical_threshold', 30)):
            alerts.append(MonthlyAlert(
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
    
    def get_top_3_priorities(self, alerts: List[MonthlyAlert]) -> List[MonthlyAlert]:
        """Rankeia alertas por score"""
        active_alerts = [a for a in alerts if a.is_active]
        sorted_alerts = sorted(active_alerts, key=lambda a: a.score, reverse=True)
        return sorted_alerts[:3]


class MonthlyInsightGenerator:
    """Gera insights em linguagem natural para relatório e vídeo"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def generate_all_insights(
        self,
        month: Month,
        metrics: Dict[str, float],
        comparative: Dict[str, MonthlyComparative],
        sales_intel: SalesIntelligence,
        summary: MonthlySummary,
        cashflow: Optional[MonthlyCashFlowAnalysis] = None,
    ) -> Dict[str, str]:
        """Gera 11 blocos de insights (10 originais + FLUXO_CAIXA, novidade 14/09/2026)"""
        
        insights = {}
        
        month_name = month.get_name()
        
        # 1. STATUS DO MÊS
        status = summary.overall_status.split('—')[0].strip() if summary.overall_status else "—"
        insights['STATUS_DO_MES'] = (
            f"Em {month_name}, seu negócio estava {status} — "
            f"Receita Líquida de R$ {metrics['revenue_net']:,.2f}."
        )
        
        # 2. LUCRATIVIDADE
        # CORREÇÃO (auditoria 13/09/2026): metrics['profit_net'] já desconta
        # o investimento em ads (mesmo ajuste do motor de Diagnóstico) — nota
        # explícita no texto quando existe ads, pra não ficar incoerente com
        # o que é dito sobre ROAS em outro bloco.
        nota_ads = (
            f" (já descontado o investimento de R$ {metrics['ads_investment']:,.2f} em anúncios)"
            if metrics.get('ads_investment', 0) > 0 else ""
        )
        if metrics['profit_net'] >= 0:
            insights['LUCRATIVIDADE'] = (
                f"Lucro líquido de R$ {metrics['profit_net']:,.2f} "
                f"({metrics['profit_margin_pct']:.1%} de margem){nota_ads}. "
                f"{'Ótimo resultado!' if metrics['profit_margin_pct'] > 0.20 else 'Há espaço para melhorar.'}"
            )
        else:
            insights['LUCRATIVIDADE'] = (
                f"PREJUÍZO de R$ {abs(metrics['profit_net']):,.2f}{nota_ads}. "
                f"Ação imediata necessária."
            )
        
        # 3. COMPARATIVO FINANCEIRO
        if comparative:
            rev_var = comparative.get('revenue_net', MonthlyComparative())
            insights['COMPARATIVO_FINANCEIRO'] = (
                f"vs mês anterior: Receita {rev_var.status} "
                f"(variação: R$ {rev_var.variation:,.0f})"
            )
        else:
            insights['COMPARATIVO_FINANCEIRO'] = "Primeiro mês registrado — sem comparativo disponível."
        
        # 4. INTELIGÊNCIA DE VENDAS
        insights['INTELIGENCIA_VENDAS'] = (
            f"Top produto: {sales_intel.top_1_product_name} "
            f"(R$ {sales_intel.top_1_product_revenue:,.0f}). "
            f"Canal líder: {sales_intel.best_channel_name}. "
            f"Canal preocupante: {sales_intel.worst_channel_name}."
        )
        
        # 5. CLIENTES E RETENÇÃO
        # NOVIDADE (04/09/2026): "retenção saudável" agora é relativo ao piso
        # da Categoria do negócio (ver CATEGORY_RECURRING_FLOOR em
        # monthly_engine_models.py), não mais um corte fixo de 30% pra todo
        # mundo.
        recurring_floor = get_recurring_floor(self.config.get('business_category', 'C'))
        insights['CLIENTES_RETENCAO'] = (
            f"Clientes recorrentes: {sales_intel.recurring_pct:.0%} do total. "
            f"Novos clientes: {sales_intel.new_customers_count}. "
            f"{'Retenção saudável para o perfil deste negócio.' if sales_intel.recurring_pct >= recurring_floor else 'Retenção baixa para o perfil deste negócio — revisar estratégia.'}"
        )
        
        # 6. PORTFÓLIO
        insights['PORTFOLIO'] = (
            f"Produto com pior margem: {sales_intel.worst_product_name} "
            f"({sales_intel.worst_product_margin_pct:.1%}). "
            f"Produtos parados: {sales_intel.paused_products_count}. "
            f"{'Portfólio com bom giro.' if sales_intel.paused_products_count == 0 else 'Capital preso em estoque.'}"
        )
        
        # 7. BREAKEVEN
        if metrics['breakeven'] > 0:
            status_be = "atingido" if metrics['revenue_net'] >= metrics['breakeven'] else "NÃO atingido"
            insights['BREAKEVEN'] = (
                f"Breakeven: R$ {metrics['breakeven']:,.2f}/mês. "
                f"Status: {status_be}."
            )
        else:
            insights['BREAKEVEN'] = "Dados insuficientes para calcular breakeven."
        
        # 8. PRIORIDADE #1
        if summary.top_3_alerts:
            priority = summary.top_3_alerts[0]
            insights['PRIORIDADE'] = (
                f"Problema mais urgente: {priority.rule} "
                f"(Score: {priority.score}). "
                f"Ação: {priority.action}"
            )
        else:
            insights['PRIORIDADE'] = "Sem alertas críticos este mês."
        
        # 9. MARKETING (se houver dados)
        if metrics.get('roas', 0) > 0:
            insights['MARKETING'] = (
                f"ROAS: {metrics['roas']:.1f}x. "
                f"CAC: R$ {metrics['cac']:.2f}. "
                f"Ads representam {metrics['ads_pct']:.1%} da receita."
            )
        else:
            insights['MARKETING'] = "Sem dados de marketing registrados."
        
        # 10. TENDÊNCIA (últimos 3 meses)
        insights['TENDENCIA'] = (
            f"Mês de {month_name} foi um {summary.overall_status.lower()} "
            "— continue monitorando os indicadores nos próximos meses."
        )

        # 11. FLUXO DE CAIXA (NOVIDADE 14/09/2026 — espelha o bloco 10 do
        # Motor de Diagnóstico, ver _fluxo_caixa() em
        # financial_engine_diagnostic.py; antes não existia porque o motor
        # mensal não calculava fluxo de caixa nenhum)
        if cashflow is None or cashflow.avg_collection_period == 0 or cashflow.avg_payment_period == 0:
            insights['FLUXO_CAIXA'] = "Dados de fluxo de caixa não informados."
        else:
            texto = f"Ciclo financeiro de {cashflow.financial_cycle:.0f} dias. "
            if cashflow.financial_cycle > self.config.get('cycle_alert_threshold', 60):
                texto += (
                    "Risco de caixa: o negócio paga antes de receber. "
                    "Lucro no papel não significa dinheiro disponível."
                )
            elif cashflow.financial_cycle > 0:
                texto += "Atenção: prazo de recebimento maior que o de pagamento."
            else:
                texto += "Ciclo financeiro saudável."
            insights['FLUXO_CAIXA'] = texto

        return insights
