"""
IA de Limpeza - Departamento de Tratamento
Padroniza dados validados para o formato exato que os engines (financial_engine + monthly_engine) esperam
"""

from .models import *
from anthropic import Anthropic
from dataclasses import asdict


class IALimpeza:
    """
    Recebe dados validados e limpos
    Padroniza estrutura, tipos, valores, formato de data
    Retorna JSON estruturado pronto para enviar aos motores de diagnóstico
    """
    
    def __init__(self):
        self.client = Anthropic()
        # CORREÇÃO (auditoria 04/09/2026): modelo antigo (2024) atualizado.
        self.model = "claude-sonnet-5"
    
    def limpar_dados(
        self,
        resultado_validado: ResultadoTratamento
    ) -> Dict[str, Any]:
        """
        Recebe resultado já validado (do fiscal de dados)
        Retorna dados no formato EXATO que financial_engine.py + monthly_engine.py esperam
        
        Para Diagnóstico: formato do financial_engine_models.FinancialInput
        Para Mensalidade: formato do monthly_engine_models.MonthlyFinancialInput
        """

        if resultado_validado.tipo_produto == TipoProduto.DIAGNOSTICO:
            return self._limpar_para_diagnostico(resultado_validado)
        elif resultado_validado.tipo_produto == TipoProduto.MENSALIDADE:
            return self._limpar_para_mensalidade(resultado_validado)
    
    def _limpar_para_diagnostico(self, resultado: ResultadoTratamento) -> Dict[str, Any]:
        """
        Formata para FinancialDiagnosticEngine
        Retorna JSON que pode ser usado direto:
        
        {
            'config': {...},
            'input_data': {...}
        }
        """
        
        dados = resultado.dados_financeiros
        cliente = resultado.cliente
        
        # Converter CampeTratado → valor
        def get_valor(campo: CampoTratado, default=0.0):
            return float(campo.valor) if campo.valor is not None else default
        
        config = {
            'client_name': cliente.nome_loja,
            # CORREÇÃO (05/09/2026, auditoria app.py): faltava aqui, e
            # ConfigParameters.analysis_period é obrigatório (sem default) —
            # sem isso, ConfigParameters(**config) nem construía.
            'analysis_period': cliente.periodo_analisado,
            # LIMPEZA (04/09/2026): cliente.categoria_negocio hoje é sempre
            # None (a Extratora parou de pedir isso a Claude). Esse 'B' é só
            # um valor inicial — os motores derivam a Categoria de verdade
            # sozinhos e sobrescrevem este valor logo no início do cálculo.
            'business_category': cliente.categoria_negocio or 'B',
            'tax_rate': cliente.aliquota_impostos,
            # CORREÇÃO (05/09/2026): cliente.regime_tributario já existe em
            # DadosCliente mas nunca era repassado — o motor ficava sempre
            # no default (Simples Nacional), mesmo pra clientes MEI/Lucro
            # Presumido. Hoje isso não entra em nenhum cálculo (tax_rate,
            # o número, é quem entra), só no rótulo do regime nos relatórios
            # — mas o rótulo errado também é bug. app.py converte esta
            # string pro enum TaxRegime (com fallback seguro).
            'tax_regime': cliente.regime_tributario,
            # CORREÇÃO (05/09/2026): 'year' não existe como campo em
            # ConfigParameters — isso quebrava ConfigParameters(**config)
            # com TypeError assim que algo tentasse de fato instanciar o
            # motor com esta config (descoberto ao construir o app.py).
        }

        input_data = {
            # CORREÇÃO (05/09/2026, auditoria app.py): faltava aqui — sem
            # isso FinancialInput.analysis_period ficava "" (default), e
            # diagnostic.validated_data.period (usado no export_to_dict())
            # saía vazio mesmo com o período correto disponível em cliente.
            'analysis_period': cliente.periodo_analisado,
            'revenue_gross': get_valor(dados.receita_bruta),
            'returns_cancellations': get_valor(dados.devolucoes),
            'cmv': get_valor(dados.cmv),
            'variable_costs': get_valor(dados.custos_variaveis),
            'fixed_costs': get_valor(dados.custos_fixos),
            'pro_labore': get_valor(dados.pro_labore),
            'num_orders': int(get_valor(dados.num_pedidos)),
            'ads_investment': get_valor(dados.ads_investment),
            'new_customers_ads': int(get_valor(dados.novos_clientes_ads)),
            'avg_collection_period': get_valor(dados.pmr),
            'avg_payment_period': get_valor(dados.pmp),
            # Nomes de canal em texto livre (ex.: "Mercado Livre"). O
            # app.py é quem converte pro enum SalesChannel exigido por
            # FinancialInput.channel_revenues, ignorando com segurança
            # qualquer nome que não bata com nenhum canal conhecido — aqui
            # em limpeza.py o formato continua sendo JSON puro de propósito
            # (como o resto deste dicionário e como como_json() em
            # models.py), sem depender dos enums do motor.
            'channel_revenues': {
                canal: get_valor(campo)
                for canal, campo in dados.faturamento_por_canal.items()
            },
            # NOVIDADE (05/09/2026, pedido do analista): taxa de canal que
            # o PRÓPRIO CLIENTE declarou no formulário (canal fora da
            # nossa lista conhecida — ver taxas_canais_declaradas em
            # DadosFinanceirosTratados, models.py). Flui sozinho até o
            # motor via app.py — pipeline automático/assíncrono, ninguém
            # precisa digitar isso na mão por cliente. Fica {} (não falta
            # nada) quando não há canal customizado ou o cliente não sabia
            # a taxa — nesse caso o motor usa 0% até alguém informar.
            'channel_fees_customizadas': {
                canal: get_valor(campo)
                for canal, campo in dados.taxas_canais_declaradas.items()
            },
        }

        return {
            'tipo_produto': 'DIAGNOSTICO',
            'config': config,
            'input_data': input_data,
            # NOVIDADE (06/09/2026, confirmado pelo analista): percepções
            # subjetivas do cliente (Seção 6 do formulário) — DE PROPÓSITO
            # fora de 'input_data' (que é só o que o motor consome) e como
            # dict simples, não CampoTratado. Só serve pra app.py repassar
            # pra Produção (dp-02) montar o Diagnóstico Comparativo — o
            # motor de cálculo nunca vê esta chave. Vem vazio (todos os
            # valores None) quando o cliente não respondeu a Seção 6, o
            # que não é erro nenhum.
            'percepcoes_cliente': asdict(resultado.percepcoes_cliente),
            'status_limpeza': 'COMPLETO',
            'timestamp': self._get_timestamp(),
        }
    
    def _limpar_para_mensalidade(self, resultado: ResultadoTratamento) -> Dict[str, Any]:
        """
        Formata para MonthlyDiagnosticEngine
        Para mensalidade, esperamos 12 meses de dados
        """
        
        # Para Mensalidade, o resultado estaria com dados estruturados por mês
        # Este é um exemplo simplificado
        
        dados = resultado.dados_financeiros
        cliente = resultado.cliente
        
        def get_valor(campo: CampoTratado, default=0.0):
            return float(campo.valor) if campo.valor is not None else default
        
        config = {
            'client_name': cliente.nome_loja,
            # LIMPEZA (04/09/2026): cliente.categoria_negocio hoje é sempre
            # None (a Extratora parou de pedir isso a Claude). Esse 'B' é só
            # um valor inicial — os motores derivam a Categoria de verdade
            # sozinhos e sobrescrevem este valor logo no início do cálculo.
            'business_category': cliente.categoria_negocio or 'B',
            'tax_rate': cliente.aliquota_impostos,
            'tax_regime': cliente.regime_tributario,
            # CORREÇÃO (05/09/2026): 'year' removido — MonthlyDiagnosticEngineMain
            # recebe um Dict[str, Any] livre (não é dataclass estrito como
            # ConfigParameters), então isso nunca quebrou nada, mas também
            # não é lido em lugar nenhum do motor mensal — era um campo morto.
        }

        # Estrutura para 1 mês. app.py monta o Month (enum) e o
        # MonthlyFinancialInput a partir deste dicionário; o histórico dos
        # outros 11 meses do ano (quando existir) é responsabilidade da
        # futura "ficha" por cliente — ver README, seção "Planejado".
        monthly_inputs = {
            'month': resultado.cliente.periodo_analisado,  # Ex: "Abril"
            'data': {
                'revenue_gross': get_valor(dados.receita_bruta),
                # CORREÇÃO (05/09/2026, auditoria app.py): estes 4 campos
                # eram coletados pela Extratora (fazem parte de
                # DadosFinanceirosTratados, os mesmos usados no Diagnóstico)
                # mas nunca chegavam ao motor mensal — o dicionário parava
                # em 'ads_investment'. Na prática isso zerava sempre
                # devoluções (inflando a receita líquida) e zerava sempre
                # novos_clientes_ads (a Mensalidade nunca calculava CAC/LTV
                # de verdade, mesmo quando o cliente informava esse dado).
                'returns_cancellations': get_valor(dados.devolucoes),
                'cmv': get_valor(dados.cmv),
                'variable_costs': get_valor(dados.custos_variaveis),
                'fixed_costs': get_valor(dados.custos_fixos),
                'pro_labore': get_valor(dados.pro_labore),
                'num_orders': int(get_valor(dados.num_pedidos)),
                'ads_investment': get_valor(dados.ads_investment),
                'new_customers_ads': int(get_valor(dados.novos_clientes_ads)),
                'avg_collection_period': get_valor(dados.pmr),
                'avg_payment_period': get_valor(dados.pmp),
                'channel_revenues': {
                    canal: get_valor(campo)
                    for canal, campo in dados.faturamento_por_canal.items()
                },
            }
        }
        
        return {
            'tipo_produto': 'MENSALIDADE',
            'config': config,
            'monthly_input': monthly_inputs,
            'status_limpeza': 'COMPLETO',
            'timestamp': self._get_timestamp(),
        }
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
