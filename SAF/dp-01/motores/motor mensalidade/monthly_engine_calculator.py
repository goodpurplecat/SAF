"""
Monthly Diagnostic Engine - Calculator
Motor de Cálculos Mensais - Todas as fórmulas em Python

Calcula:
- DRE para cada mês (12 em paralelo)
- Métricas mensais com semáforos
- Comparativos vs mês anterior
- Metas real vs orçado
"""

from monthly_engine_models import *
from enum import Enum


class MonthlyCalculator:
    """Responsável por todos os cálculos mensais"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tax_rate = config.get('tax_rate', 0.04)
        self.mc_critical = config.get('mc_critical_threshold', 0.20)
        self.mc_minimum = config.get('mc_minimum_threshold', 0.35)
        self.ml_critical = config.get('ml_critical_threshold', 0.0)
        self.ml_minimum = config.get('ml_minimum_threshold', 0.10)
    
    # ========================
    # DRE MENSAL
    # ========================
    
    def calculate_dre_for_month(self, input_data: MonthlyFinancialInput) -> Dict[str, float]:
        """Calcula DRE completa para um mês"""
        
        # Receita
        revenue_gross = input_data.revenue_gross
        returns_cancellations = input_data.returns_cancellations
        revenue_net = revenue_gross - returns_cancellations
        
        # Impostos
        taxes = revenue_net * self.tax_rate
        
        # CMV
        cmv = input_data.cmv
        
        # Lucro Bruto
        profit_gross = revenue_net - taxes - cmv
        
        # Custos Variáveis
        variable_costs = input_data.variable_costs
        
        # Margem Contribuição
        contribution_margin = profit_gross - variable_costs
        
        # Custos Fixos e Pró-labore
        fixed_costs = input_data.fixed_costs
        pro_labore = input_data.pro_labore
        
        # Lucro Líquido
        profit_net = contribution_margin - fixed_costs - pro_labore
        
        # Percentuais
        cm_pct = contribution_margin / revenue_net if revenue_net > 0 else 0
        ml_pct = profit_net / revenue_net if revenue_net > 0 else 0
        
        return {
            'revenue_gross': revenue_gross,
            'returns_cancellations': returns_cancellations,
            'revenue_net': revenue_net,
            'taxes': taxes,
            'cmv': cmv,
            'profit_gross': profit_gross,
            'variable_costs': variable_costs,
            'contribution_margin': contribution_margin,
            'contribution_margin_pct': cm_pct,
            'fixed_costs': fixed_costs,
            'pro_labore': pro_labore,
            'profit_net': profit_net,
            'profit_net_pct': ml_pct,
        }
    
    # ========================
    # MÉTRICAS MENSAIS
    # ========================
    
    def calculate_metrics_for_month(
        self, 
        dre: Dict[str, float], 
        input_data: MonthlyFinancialInput
    ) -> Dict[str, float]:
        """Calcula todas as métricas para um mês"""
        
        revenue_net = dre['revenue_net']
        contribution_margin = dre['contribution_margin']
        profit_net = dre['profit_net']
        
        # Ticket Médio
        num_orders = input_data.num_orders
        avg_ticket = revenue_net / num_orders if num_orders > 0 else 0
        
        # Breakeven
        total_fixed = input_data.fixed_costs + input_data.pro_labore
        breakeven = (total_fixed * revenue_net) / contribution_margin if contribution_margin > 0 else 0
        
        # Marketing
        ads_investment = input_data.ads_investment
        new_customers = input_data.new_customers_ads
        
        roas = revenue_net / ads_investment if ads_investment > 0 else 0
        roas_breakeven = revenue_net / contribution_margin if contribution_margin > 0 else 0
        cac = ads_investment / new_customers if new_customers > 0 else 0
        ads_pct = ads_investment / revenue_net if revenue_net > 0 else 0
        
        # LTV simplificado = Ticket × Frequência de Recompra/Ano × Anos de Retenção
        # (fórmula padrão, alinhada com CONFIG!B41/B42 da planilha — auditoria 04/09/2026;
        # substitui os antigos avg_repurchase_rate × retention_rate, que misturavam uma
        # contagem de recompras com uma probabilidade sem componente de tempo)
        repurchase_frequency_per_year = self.config.get('repurchase_frequency_per_year', 2.0)
        retention_years = self.config.get('retention_years', 2.0)
        ltv = avg_ticket * repurchase_frequency_per_year * retention_years
        ltv_cac = ltv / cac if cac > 0 else 0
        
        return {
            'revenue_net': revenue_net,
            'contribution_margin_pct': dre['contribution_margin_pct'],
            'profit_margin_pct': dre['profit_net_pct'],
            'profit_net': profit_net,
            'breakeven': breakeven,
            'avg_ticket': avg_ticket,
            'roas': roas,
            'roas_breakeven': roas_breakeven,
            'cac': cac,
            'ads_pct': ads_pct,
            'ltv': ltv,
            'ltv_cac': ltv_cac,
        }
    
    # ========================
    # COMPARATIVOS
    # ========================
    
    def calculate_comparative(
        self,
        current_value: float,
        previous_value: float
    ) -> MonthlyComparative:
        """
        Calcula comparativo e determina status
        Status: 🟢 Cresceu > 10% | 🟡 Cresceu | 🟠 Queda Leve | 🔴 Queda Crítica | —
        """
        comp = MonthlyComparative()
        
        if previous_value == 0 and current_value == 0:
            comp.status = "—"
            return comp
        
        if previous_value == 0:
            comp.status = "—"
            comp.current_month_value = current_value
            return comp
        
        comp.current_month_value = current_value
        comp.previous_month_value = previous_value
        comp.variation = current_value - previous_value
        comp.variation_pct = (current_value - previous_value) / abs(previous_value)
        
        # Determinar status
        if current_value >= previous_value * 1.1:
            comp.status = "🟢 Cresceu > 10%"
        elif current_value >= previous_value:
            comp.status = "🟡 Cresceu"
        else:
            # Queda
            threshold_critical = self.config.get('variation_critical_threshold', 0.15)  # 15%
            threshold_attention = self.config.get('variation_attention_threshold', 0.05)  # 5%
            
            pct_variation = abs(comp.variation_pct)
            
            if pct_variation >= threshold_critical:
                comp.status = "🔴 Queda Crítica"
            elif pct_variation >= threshold_attention:
                comp.status = "🟠 Queda Atenção"
            else:
                comp.status = "▼ Queda Leve"
        
        return comp
    
    # ========================
    # METAS
    # ========================
    
    def calculate_goals(
        self,
        metrics: Dict[str, float],
        config: Dict[str, Any],
        month: Month
    ) -> MonthlyGoals:
        """Compara real vs meta"""
        
        goals = MonthlyGoals(month=month)
        
        # Metas do CONFIG
        goals.goal_contribution_margin_pct = config.get('goal_mc_pct', 0.35)
        # CORREÇÃO (04/09/2026): padrão era 0.15, divergindo do padrão de
        # CONFIG!B47 da planilha (12%). Alinhado para 0.12.
        goals.goal_profit_margin_pct = config.get('goal_ml_pct', 0.12)
        goals.goal_profit_net = config.get('goal_profit_net', 5000)
        
        # Real
        goals.actual_contribution_margin_pct = metrics['contribution_margin_pct']
        goals.actual_profit_margin_pct = metrics['profit_margin_pct']
        goals.actual_profit_net = metrics['profit_net']
        
        # Status
        goals.mc_status = "✅ Meta" if goals.actual_contribution_margin_pct >= goals.goal_contribution_margin_pct else "❌ Abaixo"
        goals.ml_status = "✅ Meta" if goals.actual_profit_margin_pct >= goals.goal_profit_margin_pct else "❌ Abaixo"
        goals.profit_status = "✅ Meta" if goals.actual_profit_net >= goals.goal_profit_net else "❌ Abaixo"
        
        return goals
    
    # ========================
    # SEMÁFOROS
    # ========================
    
    def get_status_from_metrics(self, metrics: Dict[str, float]) -> str:
        """Determina status geral do mês"""
        
        profit_margin = metrics['profit_margin_pct']
        
        if profit_margin < self.ml_critical:
            return "🔴 CRÍTICO — Prejuízo"
        elif profit_margin < self.ml_minimum:
            return "🟠 RUIM"
        elif profit_margin < 0.20:
            return "🟡 ATENÇÃO"
        else:
            return "🟢 SAUDÁVEL"
