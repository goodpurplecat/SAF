"""
IA FISCAL DO RELATÓRIO E ROTEIRO — Departamento de Produção

Última barreira antes do cliente. Não reescreve — aponta. Segue o checklist
de 7 blocos do GUIA_DA_GEM_FISCAL_REVISÃO_DE_RELATÓRIO_E_ROTEIRO (ver
templates.py), separando achados em 🔴 Bloqueadores / 🟠 Ajustes / 🟡 Observações.

Roda uma vez sobre o relatório PDF e uma vez sobre o roteiro de vídeo —
o Bloco 6 (Identidade Visual) só entra na revisão do relatório.
"""

from .models import TipoProduto, TipoDocumento, RelatorioTexto, RoteiroTexto, RevisaoFiscal, ItemRevisao, StatusRevisao
from . import templates as tpl
from google import genai
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class IAFiscalRelatorioRoteiro:
    """Revisa o relatório PDF ou o roteiro de vídeo já gerados pela IA de Relatório e Roteiro."""

    def __init__(self):
        self.client = genai.Client()
        self.model = "gemini-3.6-flash"

    def revisar_relatorio(
        self,
        tipo_produto: TipoProduto,
        relatorio: RelatorioTexto,
        dados_motor: Dict[str, Any],
        cliente: Dict[str, Any],
        percepcoes_cliente: Optional[Dict[str, Any]] = None,
    ) -> RevisaoFiscal:
        checklist = self._checklist_completo(tipo_produto, TipoDocumento.RELATORIO)
        texto_documento = relatorio.como_texto_unico()
        return self._revisar(
            TipoDocumento.RELATORIO, tipo_produto, texto_documento, checklist, dados_motor, cliente, percepcoes_cliente
        )

    def revisar_roteiro(
        self,
        tipo_produto: TipoProduto,
        roteiro: RoteiroTexto,
        dados_motor: Dict[str, Any],
        cliente: Dict[str, Any],
        percepcoes_cliente: Optional[Dict[str, Any]] = None,
    ) -> RevisaoFiscal:
        checklist = self._checklist_completo(tipo_produto, TipoDocumento.ROTEIRO)
        texto_documento = roteiro.como_texto_unico()
        return self._revisar(
            TipoDocumento.ROTEIRO, tipo_produto, texto_documento, checklist, dados_motor, cliente, percepcoes_cliente
        )

    # ------------------------------------------------------------------

    def _checklist_completo(self, tipo_produto: TipoProduto, tipo_documento: TipoDocumento) -> str:
        blocos = [
            tpl.FISCAL_BLOCO_1_DADOS_NUMEROS,
            tpl.FISCAL_BLOCO_2_IDENTIFICACAO_CLIENTE,
            tpl.FISCAL_BLOCO_3_COMPLETUDE,
            tpl.FISCAL_BLOCO_4_VOZ_ESCRITA,
            tpl.FISCAL_BLOCO_5_ORTOGRAFIA,
        ]
        if tipo_documento == TipoDocumento.RELATORIO:
            blocos.append(tpl.FISCAL_BLOCO_6_IDENTIDADE_VISUAL)
            blocos.append(tpl.fiscal_bloco_7_do_produto(tipo_produto.value))
        else:
            blocos.append(tpl.FISCAL_BLOCO_7_ESPECIFICO_ROTEIRO)
        return "\n\n".join(blocos)

    def _revisar(
        self,
        tipo_documento: TipoDocumento,
        tipo_produto: TipoProduto,
        texto_documento: str,
        checklist: str,
        dados_motor: Dict[str, Any],
        cliente: Dict[str, Any],
        percepcoes_cliente: Optional[Dict[str, Any]] = None,
    ) -> RevisaoFiscal:
        prompt = self._montar_prompt(
            tipo_documento, tipo_produto, texto_documento, checklist, dados_motor, cliente, percepcoes_cliente
        )

        try:
            response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(max_output_tokens=4000),
        )
            resultado_texto = response.text
            validacao = self._parsear_json(resultado_texto)
        except Exception as e:
            print(f"[IA FISCAL RELATÓRIO E ROTEIRO] ❌ Erro: {e}")
            validacao = self._validacao_padrao_em_erro()

        return self._montar_revisao_fiscal(tipo_documento, validacao)

    def _montar_prompt(
        self,
        tipo_documento: TipoDocumento,
        tipo_produto: TipoProduto,
        texto_documento: str,
        checklist: str,
        dados_motor: Dict[str, Any],
        cliente: Dict[str, Any],
        percepcoes_cliente: Optional[Dict[str, Any]] = None,
    ) -> str:
        percepcoes_texto = (
            json.dumps(percepcoes_cliente, ensure_ascii=False, indent=2)
            if percepcoes_cliente else "Nenhuma — cliente não declarou percepções (Seção 6 do formulário)."
        )
        return f"""
Você é a GEM FISCAL DO RELATÓRIO E ROTEIRO do FinSpots — a última barreira antes do cliente.
Você APONTA problemas, nunca reescreve. Localiza com precisão (página ou bloco). Não inventa erro — se está correto, não aponta.

PRODUTO: {tipo_produto.value}
DOCUMENTO EM REVISÃO: {tipo_documento.value}

DADOS DO CLIENTE (fonte da verdade para nome, período, categoria):
{json.dumps(cliente, ensure_ascii=False, indent=2)}

DADOS DO MOTOR (fonte da verdade para TODOS os números calculados — confira cada valor do documento contra isto):
{json.dumps(dados_motor, ensure_ascii=False, indent=2, default=str)}

PERCEPÇÕES DECLARADAS PELO CLIENTE (fonte da verdade para as CRENÇAS dele, usadas no Diagnóstico Comparativo — NÃO é erro o documento citar um valor daqui que diverge de DADOS DO MOTOR: essa divergência é o propósito da seção. Só seria erro se o documento citasse uma crença que NÃO está aqui, comparasse com um número que não é o de DADOS DO MOTOR, ou usasse tom de correção/sermão em vez de trazer clareza — ver VOICE_RULES_COMPARATIVO):
{percepcoes_texto}

CHECKLIST COMPLETO DE REVISÃO:
{checklist}

DOCUMENTO A REVISAR:
{texto_documento}

RETORNE APENAS um JSON no formato exato abaixo (sem texto antes ou depois, sem markdown fences):

{{
  "bloqueadores": [
    {{"localizacao": "Página 3 / Bloco Resultado Financeiro", "problema": "...", "sugestao": "..."}}
  ],
  "ajustes": [
    {{"localizacao": "...", "problema": "...", "sugestao": "..."}}
  ],
  "observacoes": [
    {{"localizacao": "...", "problema": "...", "sugestao": "..."}}
  ],
  "status": "APROVADO | APROVADO_COM_OBSERVACOES | NAO_APROVADO"
}}

Regra de status: se houver qualquer bloqueador OU ajuste, status é "NAO_APROVADO". Se só houver observações, status é "APROVADO_COM_OBSERVACOES". Se não houver nada, status é "APROVADO".
COMECE!
"""

    def _parsear_json(self, texto: str) -> Dict[str, Any]:
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return self._validacao_padrao_em_erro()

    def _validacao_padrao_em_erro(self) -> Dict[str, Any]:
        """
        Se a Gem Fiscal falhar tecnicamente (erro de API, JSON inválido),
        NUNCA aprova por omissão — cai em NAO_APROVADO com um bloqueador
        explicando o problema, pra sempre exigir revisão manual em vez de
        deixar passar um documento sem revisão pro cliente.
        """
        return {
            "bloqueadores": [{
                "localizacao": "Revisão completa",
                "problema": "A IA Fiscal não conseguiu revisar este documento (erro técnico).",
                "sugestao": "Revisar manualmente antes de enviar ao cliente.",
            }],
            "ajustes": [],
            "observacoes": [],
            "status": "NAO_APROVADO",
        }

    def _montar_revisao_fiscal(self, tipo_documento: TipoDocumento, validacao: Dict[str, Any]) -> RevisaoFiscal:
        def para_itens(lista: List[Dict[str, str]]) -> List[ItemRevisao]:
            return [
                ItemRevisao(
                    localizacao=item.get("localizacao", "Não localizado"),
                    problema=item.get("problema", item.get("observacao", "")),
                    sugestao=item.get("sugestao", ""),
                )
                for item in lista
            ]

        bloqueadores = para_itens(validacao.get("bloqueadores", []))
        ajustes = para_itens(validacao.get("ajustes", []))
        observacoes = para_itens(validacao.get("observacoes", []))

        status_bruto = validacao.get("status", "NAO_APROVADO")
        try:
            status = StatusRevisao(status_bruto)
        except ValueError:
            status = StatusRevisao.NAO_APROVADO if (bloqueadores or ajustes) else StatusRevisao.APROVADO_COM_OBSERVACOES

        revisao = RevisaoFiscal(
            tipo_documento=tipo_documento,
            bloqueadores=bloqueadores,
            ajustes=ajustes,
            observacoes=observacoes,
            status=status,
        )
        revisao.texto_completo = self.gerar_relatorio_revisao(revisao)
        return revisao

    def gerar_relatorio_revisao(self, revisao: RevisaoFiscal) -> str:
        """Formata a revisão no padrão exato do Guia da Gem Fiscal (para log/humano)."""
        linhas = []
        linhas.append("━" * 30)
        linhas.append(f"🔴 BLOQUEADORES — {len(revisao.bloqueadores)} encontrados")
        linhas.append("━" * 30)
        if revisao.bloqueadores:
            for i, item in enumerate(revisao.bloqueadores, 1):
                linhas.append(f"{i}. {item.localizacao}\nProblema: {item.problema}\nSugestão: {item.sugestao}\n")
        else:
            linhas.append("Nenhum bloqueador encontrado ✅\n")

        linhas.append("━" * 30)
        linhas.append(f"🟠 AJUSTES — {len(revisao.ajustes)} encontrados")
        linhas.append("━" * 30)
        if revisao.ajustes:
            for i, item in enumerate(revisao.ajustes, 1):
                linhas.append(f"{i}. {item.localizacao}\nProblema: {item.problema}\nSugestão: {item.sugestao}\n")
        else:
            linhas.append("Nenhum ajuste necessário ✅\n")

        linhas.append("━" * 30)
        linhas.append(f"🟡 OBSERVAÇÕES — {len(revisao.observacoes)} encontradas")
        linhas.append("━" * 30)
        if revisao.observacoes:
            for i, item in enumerate(revisao.observacoes, 1):
                linhas.append(f"{i}. {item.localizacao}\nObservação: {item.problema}\nSugestão: {item.sugestao}\n")
        else:
            linhas.append("Nenhuma observação ✅\n")

        linhas.append("━" * 30)
        linhas.append("RESULTADO FINAL")
        linhas.append("━" * 30)
        linhas.append(f"🔴 {len(revisao.bloqueadores)} bloqueador(es)")
        linhas.append(f"🟠 {len(revisao.ajustes)} ajuste(s)")
        linhas.append(f"🟡 {len(revisao.observacoes)} observação(ões)")

        if revisao.status == StatusRevisao.NAO_APROVADO:
            linhas.append("\n❌ NÃO APROVADO — corrigir os bloqueadores e ajustes antes de enviar")
        elif revisao.status == StatusRevisao.APROVADO_COM_OBSERVACOES:
            linhas.append("\n✅ APROVADO COM OBSERVAÇÕES — pode enviar, considerar as observações")
        else:
            linhas.append("\n✅ APROVADO — pode enviar pro cliente")

        linhas.append(f"\nTimestamp: {datetime.now().isoformat()}")
        return "\n".join(linhas)
