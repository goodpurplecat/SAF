"""
Departamento de Tratamento
Orquestra: Extratora → Fiscal de Dados → Limpeza
"""

from .models import *
from .extratora import IAExtratora
from .fiscal_dados import IAFiscalDados
from .limpeza import IALimpeza
import json


class DepartamentoTratamento:
    """Orquestra as 3 IAs de tratamento em sequência"""
    
    def __init__(self):
        self.extratora = IAExtratora()
        self.fiscal = IAFiscalDados()
        self.limpeza = IALimpeza()
    
    def processar_cliente(
        self,
        tipo_produto: TipoProduto,
        respostas_formulario: Dict[str, Any],
        arquivos_info: List[Dict[str, Any]],
        conteudo_arquivos: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """
        Pipeline completo de tratamento:
        1. Extratora: estrutura dados brutos
        2. Fiscal: valida dados
        3. Limpeza: padroniza para engines

        conteudo_arquivos: NOVIDADE (06/09/2026, auditoria "sistema
        digestivo") — Dict[str, str], chave = mesmo "nome" usado em
        `arquivos_info`, valor = conteúdo do arquivo JÁ EM TEXTO (CSV lido
        e virado string, texto extraído do PDF/planilha, etc.). Antes
        desta correção, este parâmetro nem existia aqui — mesmo se quem
        chamasse `processar_cliente()` tivesse o conteúdo real do arquivo
        em mãos, não havia como repassar pra IA Extratora, que só recebia
        `arquivos_info` (nome/formato/tamanho, nunca o conteúdo). Ver
        `extratora.py::_montar_prompt_conteudo_arquivos` — este sistema
        continua sem parser de binário, então a conversão bytes → texto
        precisa acontecer ANTES de chamar isto (no backend/site que vai
        receber o upload).
        """

        print("\n" + "="*60)
        print("🔄 DEPARTAMENTO DE TRATAMENTO")
        print("="*60)

        # Step 1: Extração
        print("\n[1/3] 🔍 IA Extratora: estruturando dados...")
        resultado_extracao = self.extratora.extrair_dados(
            tipo_produto=tipo_produto,
            respostas_formulario=respostas_formulario,
            arquivos_info=arquivos_info,
            conteudo_arquivos=conteudo_arquivos,
        )
        print(f"✅ Extração completa - Status: {resultado_extracao.status_final}")
        
        # Step 2: Fiscal
        print("\n[2/3] ✅ IA Fiscal de Dados: validando...")
        validacao = self.fiscal.validar_extracao(
            resultado_extracao=resultado_extracao,
            dados_originais_formulario=respostas_formulario,
            dados_originais_arquivos=arquivos_info
        )
        
        # CORREÇÃO (auditoria 12/09/2026): chamava `gerar_relatorio_revisao`,
        # método que nunca existiu em IAFiscalDados (só `gerar_relatorio`) —
        # toda vez que a Extratora tivesse sucesso de verdade (GEMINI_API_KEY
        # configurada, como em produção), esta linha derrubava o pipeline
        # inteiro com AttributeError, pra TODO cliente, sempre. Nenhum teste
        # pegava isso porque, sem chave de API neste ambiente, a Extratora já
        # falha antes de chegar aqui.
        relatorio_fiscal = self.fiscal.gerar_relatorio(validacao)
        print(relatorio_fiscal)
        
        # Se tem bloqueadores, parar aqui
        if validacao['status'] == 'BLOQUEADORES':
            print("\n🔴 NÃO FOI POSSÍVEL PROSSEGUIR - Corrigir bloqueadores acima")
            return {
                'status': 'ERRO',
                'etapa': 'FISCAL_DE_DADOS',
                'erro': relatorio_fiscal,
                'resultado_extracao': resultado_extracao.como_json()
            }
        
        # Step 3: Limpeza
        print("\n[3/3] 🧹 IA de Limpeza: padronizando para engines...")
        dados_limpos = self.limpeza.limpar_dados(resultado_extracao)
        print(f"✅ Limpeza completa - Tipo: {tipo_produto.value}")
        
        # Resultado final
        return {
            'status': 'SUCESSO',
            'tipo_produto': tipo_produto.value,
            'cliente': {
                'nome': resultado_extracao.cliente.nome_loja,
                'periodo': resultado_extracao.cliente.periodo_analisado,
            },
            'resultado_extracao': resultado_extracao.como_json(),
            'validacao': validacao,
            'dados_limpos': dados_limpos,
            'timestamp': self._get_timestamp(),
        }
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

def exemplo_uso():
    """Teste rápido do departamento"""
    
    print("\n" + "="*70)
    print("TESTE: DEPARTAMENTO DE TRATAMENTO")
    print("="*70)
    
    # Simular respostas do formulário
    formulario_teste = {
        'q1_nome_loja': 'E-commerce Teste',
        'q12_periodo': 'Abril/2026',
        'q4_nicho': 'Vestuário',
        'q6_tempo': '2 anos',
        'q7_regime': 'Simples Nacional',
        'q8_aliquota': '0.04',
        'q9_canais': ['Mercado Livre', 'Shopify'],
        'q13_receita_bruta': '150000',
        'q14_receita_tipo': 'exato',
        'q15_devolucoes': '7500',
        'q16_cmv': '45000',
        'q17_cmv_tipo': 'exato',
        'q18_custos_var': '22500',
        'q19_custos_fixos': '25000',
        'q20_pro_labore': '5000',
        'q21_num_pedidos': '600',
        'q23_ads_invest': '15000',
        'q24_novos_clientes': '300',
        'q26_pmr': '7',
        'q27_pmp': '15',
    }
    
    arquivos_teste = [
        {
            'nome': 'ML_vendas_abril.csv',
            'formato': 'csv',
            'tamanho': 2.5,
            'data': '2026-04-30',
            'tipo': 'relatorio_mercado_livre',
        },
        {
            'nome': 'Shopify_april.xlsx',
            'formato': 'xlsx',
            'tamanho': 1.8,
            'data': '2026-04-30',
            'tipo': 'relatorio_shopify',
        }
    ]
    
    # Processar
    depto = DepartamentoTratamento()
    resultado = depto.processar_cliente(
        tipo_produto=TipoProduto.DIAGNOSTICO,
        respostas_formulario=formulario_teste,
        arquivos_info=arquivos_teste,
    )
    
    # Mostrar resultado
    if resultado['status'] == 'SUCESSO':
        print("\n" + "="*70)
        print("✅ TRATAMENTO CONCLUÍDO COM SUCESSO")
        print("="*70)
        print(f"\n📋 Cliente: {resultado['cliente']['nome']}")
        print(f"📅 Período: {resultado['cliente']['periodo']}")
        print(f"📊 Tipo: {resultado['tipo_produto']}")
        
        print("\n💰 Dados financeiros extraídos:")
        for k, v in resultado['dados_limpos'].get('input_data', {}).items():
            if isinstance(v, (int, float)):
                print(f"  • {k}: {v:,.2f}")
        
        print("\n✅ Pronto para enviar ao motor de diagnóstico!")
        
        # Salvar resultado como JSON
        with open('/tmp/tratamento_resultado.json', 'w') as f:
            json.dump(resultado, f, indent=2, default=str)
        print("\n📁 Resultado salvo em: /tmp/tratamento_resultado.json")


if __name__ == "__main__":
    exemplo_uso()
