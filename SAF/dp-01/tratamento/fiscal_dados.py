"""
IA FISCAL DE DADOS COM CLAUDE - Departamento de Tratamento (COMPLETO)
Valida dados extraídos usando Claude com checklist 🔴🟠🟡
"""

from .models import *
from google import genai
import json
import re
from datetime import datetime


class IAFiscalDados:
    """
    IA Fiscal que usa CLAUDE para validar dados com 9-point checklist
    """
    
    def __init__(self):
        self.client = genai.Client()
        # CORREÇÃO (auditoria 04/09/2026): modelo antigo (2024) atualizado.
        self.model = "gemini-2.5-flash"
    
    def validar_extracao(
        self,
        resultado_extracao: ResultadoTratamento,
        dados_originais_formulario: Dict[str, Any] = None,
        dados_originais_arquivos: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Usa CLAUDE para validar dados com 9-point checklist
        Retorna: bloqueadores 🔴, ajustes 🟠, observações 🟡

        CORREÇÃO CRÍTICA (06/09/2026, auditoria "sistema digestivo"): esta
        assinatura só aceitava `resultado_extracao`, mas
        `DepartamentoTratamento.processar_cliente()` (tratamento/__init__.py)
        SEMPRE chama este método passando também
        `dados_originais_formulario=` e `dados_originais_arquivos=` —
        argumentos que este método simplesmente não existia pra receber.
        Ou seja: toda vez que a IA Extratora tivesse sucesso de verdade
        (com ANTHROPIC_API_KEY configurada), a chamada seguinte — Etapa
        2/3, IA Fiscal de Dados — quebraria imediatamente com
        `TypeError: validar_extracao() got an unexpected keyword argument
        'dados_originais_formulario'`, derrubando o pipeline inteiro antes
        da Limpeza. Nenhum teste pegava isso porque, sem chave de API
        configurada neste ambiente, a Extratora já falha ANTES desta
        chamada ser alcançada (ver test_tratamento.py::teste_completo) —
        o bug só se manifestaria em produção, com a chave configurada.
        Corrigido aceitando os dois parâmetros — e, já que o propósito da
        IA Fiscal de Dados é justamente comparar o extraído com o
        original, eles agora são de fato usados no prompt (ver
        `_montar_prompt_validacao`), o que também resolve uma limitação
        anterior: o prompt só mostrava o resultado já extraído, sem nunca
        mostrar o formulário/arquivos originais pra comparar contra —
        tornando o checklist (ex.: item 4 "nome da loja consistente?",
        item 6 "canais sem arquivo sinalizados?") impossível de aplicar
        de verdade.
        """

        print("[IA FISCAL] ✅ Iniciando validação com Claude...")

        prompt = self._montar_prompt_validacao(
            resultado_extracao, dados_originais_formulario, dados_originais_arquivos
        )
        
        try:
            response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(max_output_tokens=3000),
        )
            
            resultado_texto = response.text
            print("[IA FISCAL] ✅ Claude validou")
            
            # Parsear JSON
            match = re.search(r'\{.*\}', resultado_texto, re.DOTALL)
            if match:
                validacao = json.loads(match.group(0))
            else:
                validacao = self._validacao_padrao()
            
            return validacao
            
        except Exception as e:
            print(f"[IA FISCAL] ❌ Erro: {e}")
            return self._validacao_padrao()
    
    def _truncar_com_aviso(self, texto: str, limite: int) -> str:
        """
        CORREÇÃO (06/09/2026, auditoria "sistema digestivo"): antes disso,
        o prompt cortava o JSON com `[:N]` cru — se o corte caísse no meio
        de um valor, o texto simplesmente sumia sem nenhum aviso, e Claude
        não tinha como saber que faltava conteúdo. Agora, quando há corte,
        isso fica explícito no próprio texto enviado, pra Claude tratar o
        que ficou de fora como incerto em vez de simplesmente ignorar.
        """
        if len(texto) <= limite:
            return texto
        cortados = len(texto) - limite
        return (
            texto[:limite]
            + f"\n... [TRUNCADO — {cortados} caractere(s) a mais não enviados por limite de tamanho]"
        )

    def _montar_prompt_validacao(
        self,
        resultado: ResultadoTratamento,
        dados_originais_formulario: Dict[str, Any] = None,
        dados_originais_arquivos: List[Dict[str, Any]] = None,
    ) -> str:
        """
        Monta prompt para validação.

        CORREÇÃO (06/09/2026, auditoria "sistema digestivo"): antes desta
        correção, o prompt só mostrava `resultado.como_json()` — os dados
        JÁ EXTRAÍDOS — sem nunca incluir o formulário/arquivos ORIGINAIS
        que o cliente de fato enviou. Isso tornava boa parte do checklist
        (nome da loja consistente? período correto? canal sem arquivo
        sinalizado?) impossível de checar de verdade, porque não havia
        nada pra comparar. Agora os originais entram no prompt como fonte
        de comparação.
        """
        originais_formulario_texto = (
            self._truncar_com_aviso(json.dumps(dados_originais_formulario, ensure_ascii=False, indent=2, default=str), 3000)
            if dados_originais_formulario else "Não informado."
        )
        originais_arquivos_texto = (
            self._truncar_com_aviso(json.dumps(dados_originais_arquivos, ensure_ascii=False, indent=2, default=str), 1500)
            if dados_originais_arquivos else "Nenhum arquivo enviado."
        )

        return f"""
Você é a IA FISCAL de Dados do FinSpots.

TAREFA: Validar dados extraídos com 9-point checklist.

FORMULÁRIO ORIGINAL (o que o cliente de fato respondeu — use pra checar se a extração é fiel a isto):
{originais_formulario_texto}

ARQUIVOS ORIGINAIS ENVIADOS (metadados — use pra checar se todo canal declarado tem arquivo, item 6):
{originais_arquivos_texto}

DADOS A VALIDAR (o que a IA Extratora estruturou a partir do formulário/arquivos acima):
{self._truncar_com_aviso(json.dumps(resultado.como_json(), indent=2, default=str), 3000)}

APLICAR CHECKLIST (9 PONTOS):

1. Receita Bruta coerente? (>5% divergência = 🔴)
2. CMV coerente? (>5% divergência = 🟠)
3. Campos obrigatórios preenchidos? (vazio = 🔴)
4. Nome da loja consistente? (diferente = 🔴)
5. Período correto? (diferente = 🔴)
6. Canais sem arquivo sinalizados? (não = 🟠)
7. Qualidade marcada? (não = 🟡)
8. Fonte declarada? (não = 🟡)
9. Sem placeholders [xxx]? ([xxx] = 🔴)

RETORNAR JSON (preenchido TOTALMENTE):

{{
  "bloqueadores": [
    {{"localizacao": "...", "problema": "...", "sugestao": "..."}}
  ],
  "ajustes": [
    {{"localizacao": "...", "problema": "...", "sugestao": "..."}}
  ],
  "observacoes": [
    {{"localizacao": "...", "observacao": "..."}}
  ],
  "confianca": 0.85,
  "status": "APROVADO"
}}

COMECE!
"""
    
    def _validacao_padrao(self) -> Dict[str, Any]:
        """Retorna validação padrão se Claude falhar"""
        return {
            'bloqueadores': [],
            'ajustes': [],
            'observacoes': [],
            'confianca': 0.5,
            'status': 'AGUARDANDO',
            'timestamp': datetime.now().isoformat()
        }
    
    def gerar_relatorio(self, validacao: Dict[str, Any]) -> str:
        """Gera relatório formatado com 🔴🟠🟡"""
        
        output = "╔" + "═" * 58 + "╗\n"
        output += "║ 🔍 REVISÃO DE DADOS — DEPARTAMENTO DE TRATAMENTO  ║\n"
        output += "╚" + "═" * 58 + "╝\n\n"
        
        # Bloqueadores
        bloqueadores = validacao.get('bloqueadores', [])
        output += "🔴 BLOQUEADORES — " + str(len(bloqueadores)) + "\n"
        output += "─" * 60 + "\n"
        if bloqueadores:
            for i, item in enumerate(bloqueadores, 1):
                output += f"{i}. {item.get('localizacao', 'Desconhecido')}\n"
                output += f"   Problema: {item.get('problema', 'N/A')}\n"
                output += f"   Sugestão: {item.get('sugestao', 'N/A')}\n\n"
        else:
            output += "Nenhum bloqueador encontrado ✅\n\n"
        
        # Ajustes
        ajustes = validacao.get('ajustes', [])
        output += "\n🟠 AJUSTES — " + str(len(ajustes)) + "\n"
        output += "─" * 60 + "\n"
        if ajustes:
            for i, item in enumerate(ajustes, 1):
                output += f"{i}. {item.get('localizacao', 'Desconhecido')}\n"
                output += f"   Problema: {item.get('problema', 'N/A')}\n"
                output += f"   Sugestão: {item.get('sugestao', 'N/A')}\n\n"
        else:
            output += "Nenhum ajuste necessário ✅\n\n"
        
        # Observações
        observacoes = validacao.get('observacoes', [])
        output += "\n🟡 OBSERVAÇÕES — " + str(len(observacoes)) + "\n"
        output += "─" * 60 + "\n"
        if observacoes:
            for i, item in enumerate(observacoes, 1):
                output += f"{i}. {item.get('localizacao', 'Desconhecido')}\n"
                output += f"   Observação: {item.get('observacao', 'N/A')}\n\n"
        else:
            output += "Nenhuma observação ✅\n\n"
        
        # Status
        output += "\n" + "═" * 60 + "\n"
        output += "STATUS FINAL\n"
        output += "═" * 60 + "\n\n"
        
        status = validacao.get('status', 'DESCONHECIDO')
        if status == 'BLOQUEADORES':
            output += "❌ NÃO APROVADO\n"
            output += "Corrigir bloqueadores antes de prosseguir.\n"
        elif status == 'AJUSTES_NECESSARIOS' or status == 'AJUSTES':
            output += "⚠️  APROVADO COM AJUSTES\n"
            output += "Considerar ajustes antes de enviar.\n"
        elif status == 'APROVADO':
            output += "✅ APROVADO\n"
            output += "Dados prontos para limpeza.\n"
        else:
            output += f"❓ STATUS: {status}\n"
        
        confianca = validacao.get('confianca', 0.5)
        output += f"\nConfiança: {confianca:.0%}\n"
        output += f"Timestamp: {validacao.get('timestamp', 'N/A')}\n"
        
        return output

      
        
      
      Stop Claude
    
