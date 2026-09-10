"""
IA DE RELATÓRIO E ROTEIRO — Departamento de Produção

Recebe o JSON exportado por um dos dois motores (financial_engine.export_to_dict()
ou monthly_engine.export_to_dict() — o equivalente Python à "planilha
preenchida" dos guias originais) e gera o texto de cada página do relatório
PDF e o roteiro de vídeo narrado, na voz da Finspots, seguindo fielmente os
4 guias da Gem (ver templates.py).

Unificada pros dois produtos (Diagnóstico e Mensalidade) porque a voz e a
lógica de bloco são as mesmas — só a estrutura de página/bloco muda, e essa
diferença já está tabelada em templates.py.
"""

from .models import TipoProduto, TipoDocumento, RelatorioTexto, RoteiroTexto, RevisaoFiscal
from . import templates as tpl
from google import genai
import json
import re
from typing import Any, Dict, List, Optional


class IARelatorioRoteiro:
    """Gera o texto do relatório PDF e do roteiro de vídeo a partir do output do motor."""

    def __init__(self):
        self.client = genai.Client()
        self.model = "gemini-3.6-flash"

    # ------------------------------------------------------------------
    # RELATÓRIO PDF
    # ------------------------------------------------------------------

    def gerar_relatorio(
        self,
        tipo_produto: TipoProduto,
        dados_motor: Dict[str, Any],
        cliente: Dict[str, Any],
        periodo_anterior: Optional[Dict[str, Any]] = None,
        feedback_fiscal: Optional[RevisaoFiscal] = None,
        percepcoes_cliente: Optional[Dict[str, Any]] = None,
    ) -> RelatorioTexto:
        """
        dados_motor: dict retornado por FinancialDiagnosticEngine.export_to_dict()
            ou MonthlyDiagnosticEngineMain.export_to_dict().
        cliente: {'nome_loja': str, 'periodo' ou 'mes_ano': str, 'categoria': str,
                  'whatsapp': str (opcional, usa o padrão Finspots se ausente)}
        periodo_anterior: dados do período/mês anterior (mesmo formato de
            'financial'/'comparatives'), só pra Página 7 do Diagnóstico ou
            pro comparativo de Mensalidade (que já vem embutido em
            dados_motor['comparatives'] quando o motor recebeu
            previous_month_metrics — aqui é usado só como contexto extra).
        feedback_fiscal: quando a Gem Fiscal reprovou uma tentativa anterior,
            os bloqueadores/ajustes dela entram como instrução de correção.
        percepcoes_cliente: NOVIDADE (06/09/2026) — o que o cliente
            declarou acreditar sobre o próprio negócio (Seção 6 do
            formulário, só no Diagnóstico). Usado pro Diagnóstico
            Comparativo (ver VOICE_RULES_COMPARATIVO em templates.py).
            None/vazio = gera normalmente, sem forçar comparação nenhuma.
        """
        prompt = self._montar_prompt_relatorio(
            tipo_produto, dados_motor, cliente, periodo_anterior, feedback_fiscal, percepcoes_cliente
        )
        resposta = self._chamar_claude(prompt, max_tokens=8000)
        paginas_dict = self._parsear_json(resposta)

        relatorio = RelatorioTexto(tipo_produto=tipo_produto)
        for numero_str, texto in paginas_dict.get("paginas", {}).items():
            try:
                relatorio.paginas[int(numero_str)] = texto
            except (TypeError, ValueError):
                continue
        return relatorio

    def _montar_prompt_relatorio(
        self,
        tipo_produto: TipoProduto,
        dados_motor: Dict[str, Any],
        cliente: Dict[str, Any],
        periodo_anterior: Optional[Dict[str, Any]],
        feedback_fiscal: Optional[RevisaoFiscal],
        percepcoes_cliente: Optional[Dict[str, Any]] = None,
    ) -> str:
        paginas = tpl.paginas_do_produto(tipo_produto.value)
        specs_texto = self._formatar_specs_paginas(paginas)

        correcao_texto = ""
        if feedback_fiscal is not None:
            correcao_texto = f"""
ATENÇÃO — TENTATIVA ANTERIOR FOI REPROVADA PELA GEM FISCAL. Corrija tudo abaixo antes de gerar de novo:
{feedback_fiscal.como_feedback_para_geradora()}
"""

        periodo_anterior_texto = (
            json.dumps(periodo_anterior, ensure_ascii=False, indent=2)
            if periodo_anterior
            else "Não há período anterior — este é o primeiro diagnóstico/mês do cliente."
        )

        percepcoes_bruto = self._formatar_percepcoes(percepcoes_cliente)
        bloco_comparativo = f"\n{tpl.VOICE_RULES_COMPARATIVO}\n" if percepcoes_bruto else ""
        percepcoes_texto = percepcoes_bruto or (
            "Cliente não declarou nenhuma percepção/expectativa (Seção 6 do formulário vazia ou ausente) "
            "— gere o texto normalmente, sem incluir nenhuma comparação forçada."
        )

        return f"""
Você é a IA DE RELATÓRIO E ROTEIRO do FinSpots — Departamento de Produção.

TAREFA: gerar o texto de CADA PÁGINA do relatório PDF de {tipo_produto.value}, pronto para colar no Canva.
Você recebe os dados já calculados pelo motor (equivalente à planilha preenchida) — não recalcule nada, apenas interprete e escreva.

{tpl.VOICE_RULES_RELATORIO}

{tpl.VOICE_RULES_PREDITIVA}
{bloco_comparativo}
DADOS DO CLIENTE:
{json.dumps(cliente, ensure_ascii=False, indent=2)}

DADOS DO MOTOR (diagnóstico já calculado — esta é sua única fonte de números, não invente nada fora daqui):
{json.dumps(dados_motor, ensure_ascii=False, indent=2, default=str)}

PERÍODO/MÊS ANTERIOR (para a página de comparação, se aplicável):
{periodo_anterior_texto}

PERCEPÇÕES DO CLIENTE — O QUE ELE ACREDITA (Diagnóstico Comparativo, ver regras acima):
{percepcoes_texto}

ESTRUTURA PÁGINA A PÁGINA (siga o formato de saída de cada página o mais fielmente possível, substituindo os campos entre colchetes pelos dados reais; use a Página 2 — abertura — como lugar natural pra plantar o gancho do Diagnóstico Comparativo, quando houver percepção relevante disponível):
{specs_texto}
{correcao_texto}
RETORNE APENAS um JSON no formato exato abaixo (sem texto antes ou depois, sem markdown fences), com o texto de cada página já pronto:

{{
  "paginas": {{
    "2": "texto completo da página 2...",
    "3": "texto completo da página 3...",
    "...": "..."
  }}
}}

A Página 1 (Capa) NÃO entra aqui — ela é montada manualmente pelo analista no Canva.
COMECE!
"""

    # ------------------------------------------------------------------
    # ROTEIRO DE VÍDEO
    # ------------------------------------------------------------------

    def gerar_roteiro(
        self,
        tipo_produto: TipoProduto,
        dados_motor: Dict[str, Any],
        cliente: Dict[str, Any],
        relatorio: Optional[RelatorioTexto] = None,
        periodo_anterior: Optional[Dict[str, Any]] = None,
        aposta_anterior: Optional[Dict[str, Any]] = None,
        feedback_fiscal: Optional[RevisaoFiscal] = None,
        percepcoes_cliente: Optional[Dict[str, Any]] = None,
    ) -> RoteiroTexto:
        """
        aposta_anterior: {'texto': str, 'resultado': 'MELHOROU'|'NAO_MELHOROU'|'MANTEVE'}
            — equivalente automático à antiga célula manual CONFIG!B53, só
            usado pela Mensalidade. Ver DepartamentoProducao._extrair_aposta_anterior.
        percepcoes_cliente: ver gerar_relatorio() acima — mesmo uso aqui,
            pro Diagnóstico Comparativo no roteiro de vídeo.
        """
        prompt = self._montar_prompt_roteiro(
            tipo_produto, dados_motor, cliente, relatorio, periodo_anterior, aposta_anterior,
            feedback_fiscal, percepcoes_cliente,
        )
        resposta = self._chamar_claude(prompt, max_tokens=8000)
        blocos_dict = self._parsear_json(resposta)
        return self._construir_roteiro(tipo_produto, blocos_dict)

    def _construir_roteiro(self, tipo_produto: TipoProduto, blocos_dict: Dict[str, Any]) -> RoteiroTexto:
        """
        Separado de gerar_roteiro() só pra ser testável sem chamada de API
        (ver test_producao.py) — monta o RoteiroTexto (fala + card por
        bloco) a partir do JSON já parseado.
        """
        roteiro = RoteiroTexto(tipo_produto=tipo_produto)
        ordem = []
        for nome, valor in blocos_dict.get("blocos", {}).items():
            if isinstance(valor, dict):
                fala = valor.get("fala", "")
                card = valor.get("card", fala)
            else:
                # Claude não seguiu o schema novo (fala/card) e devolveu só uma
                # string — não trava o pipeline por isso, mas os dois campos
                # ficam iguais (equivalente ao comportamento antigo, antes do
                # card curto existir).
                fala = str(valor)
                card = fala
            roteiro.blocos[nome] = fala
            roteiro.blocos_card[nome] = card
            ordem.append(nome)
        roteiro.ordem_blocos = ordem
        return roteiro

    def _montar_prompt_roteiro(
        self,
        tipo_produto: TipoProduto,
        dados_motor: Dict[str, Any],
        cliente: Dict[str, Any],
        relatorio: Optional[RelatorioTexto],
        periodo_anterior: Optional[Dict[str, Any]],
        aposta_anterior: Optional[Dict[str, Any]],
        feedback_fiscal: Optional[RevisaoFiscal],
        percepcoes_cliente: Optional[Dict[str, Any]] = None,
    ) -> str:
        blocos = tpl.blocos_video_do_produto(tipo_produto.value)
        specs_texto = self._formatar_specs_blocos(blocos)
        especificacoes = tpl.especificacoes_video_do_produto(tipo_produto.value)

        correcao_texto = ""
        if feedback_fiscal is not None:
            correcao_texto = f"""
ATENÇÃO — TENTATIVA ANTERIOR FOI REPROVADA PELA GEM FISCAL. Corrija tudo abaixo antes de gerar de novo:
{feedback_fiscal.como_feedback_para_geradora()}
"""

        relatorio_texto = relatorio.como_texto_unico() if relatorio else "(relatório PDF ainda não disponível — use os dados do motor diretamente)"
        periodo_anterior_texto = (
            json.dumps(periodo_anterior, ensure_ascii=False, indent=2) if periodo_anterior else "Não há período anterior."
        )
        aposta_anterior_texto = (
            json.dumps(aposta_anterior, ensure_ascii=False, indent=2)
            if aposta_anterior
            else "Não há aposta anterior registrada (primeiro mês ou o motor não gerou prioridade #1 no mês passado)."
        )
        percepcoes_bruto = self._formatar_percepcoes(percepcoes_cliente)
        bloco_comparativo = f"\n{tpl.VOICE_RULES_COMPARATIVO}\n" if percepcoes_bruto else ""
        percepcoes_texto = percepcoes_bruto or (
            "Cliente não declarou nenhuma percepção/expectativa (Seção 6 do formulário vazia ou ausente) "
            "— gere o texto normalmente, sem incluir nenhuma comparação forçada."
        )

        return f"""
Você é a IA DE RELATÓRIO E ROTEIRO do FinSpots — Departamento de Produção.

TAREFA: gerar o ROTEIRO DE VÍDEO NARRADO completo de {tipo_produto.value}, bloco a bloco, pronto para gravar.

ESPECIFICAÇÕES TÉCNICAS DO VÍDEO:
{json.dumps(especificacoes, ensure_ascii=False, indent=2)}

{tpl.VOICE_RULES_ROTEIRO}

{tpl.VOICE_RULES_CARD}

{tpl.VOICE_RULES_PREDITIVA}
{bloco_comparativo}
DADOS DO CLIENTE:
{json.dumps(cliente, ensure_ascii=False, indent=2)}

DADOS DO MOTOR (diagnóstico já calculado — esta é sua única fonte de números):
{json.dumps(dados_motor, ensure_ascii=False, indent=2, default=str)}

TEXTO DO RELATÓRIO PDF JÁ MONTADO (para saber a ordem exata das páginas e reaproveitar interpretações já validadas):
{relatorio_texto}

PERÍODO/MÊS ANTERIOR:
{periodo_anterior_texto}

APOSTA ANTERIOR (Prioridade #1 do período/mês passado — só relevante pra Mensalidade):
{aposta_anterior_texto}

PERCEPÇÕES DO CLIENTE — O QUE ELE ACREDITA (Diagnóstico Comparativo, ver regras acima):
{percepcoes_texto}

ROTEIRO BLOCO A BLOCO (siga o formato de saída de cada bloco o mais fielmente possível, substituindo os campos entre colchetes pelos dados reais; use o bloco INTRO ou o primeiro bloco de status como lugar natural pro gancho do Diagnóstico Comparativo, quando houver percepção relevante disponível):
{specs_texto}
{correcao_texto}
RETORNE APENAS um JSON no formato exato abaixo (sem texto antes ou depois, sem markdown fences), na ordem de gravação. Cada bloco tem DOIS textos — "fala" (narração completa, o que o dublador realmente fala) e "card" (texto curto que aparece escrito no slide, ver REGRAS DO TEXTO DO CARD acima). Cards de transição sem narração própria usam o mesmo texto curto nos dois campos:

{{
  "blocos": {{
    "INTRO": {{"fala": "fala completa da intro...", "card": "versão curta da intro pro card..."}},
    "CARD DE TRANSIÇÃO — BLOCO 1": {{"fala": "BLOCO 1 — ...", "card": "BLOCO 1 — ..."}},
    "...": {{"fala": "...", "card": "..."}}
  }}
}}

COMECE!
"""

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _formatar_percepcoes(self, percepcoes_cliente: Optional[Dict[str, Any]]) -> str:
        """
        NOVIDADE (06/09/2026): formata PercepcoesCliente (ver
        dp-01/tratamento/models.py) pro prompt — retorna string vazia
        quando não há NENHUMA percepção declarada (percepcoes_cliente é
        None, {} ou todos os valores são None/vazio), sinal pra quem
        chama não incluir o bloco VOICE_RULES_COMPARATIVO. Isso evita a
        IA forçar uma comparação quando o cliente simplesmente não
        respondeu a Seção 6 do formulário — não é um erro, é o normal
        pra qualquer cliente que já veio de uma versão anterior do
        formulário ou pulou essas perguntas.
        """
        if not percepcoes_cliente:
            return ""
        outras = percepcoes_cliente.get("outras_percepcoes") or {}
        campos_com_valor = {
            chave: valor for chave, valor in percepcoes_cliente.items()
            if chave != "outras_percepcoes" and valor not in (None, "")
        }
        if not campos_com_valor and not outras:
            return ""
        if outras:
            campos_com_valor["outras_percepcoes"] = outras
        return json.dumps(campos_com_valor, ensure_ascii=False, indent=2)

    def _formatar_specs_paginas(self, paginas: List[Dict[str, Any]]) -> str:
        blocos = []
        for pagina in paginas:
            partes = [f"--- PÁGINA {pagina['numero']} — {pagina['titulo']} ---", f"Fonte: {pagina['fonte']}"]
            for instrucao in pagina.get("instrucoes", []):
                partes.append(f"- {instrucao}")
            if "formato" in pagina:
                partes.append(f"Formato de saída:\n{pagina['formato']}")
            for chave in ("formato_com_dados", "formato_sem_dados", "formato_primeiro", "formato_comparativo",
                          "formato_primeiro_mes", "formato_sem_dados_marketing"):
                if chave in pagina:
                    partes.append(f"Formato ({chave}):\n{pagina[chave]}")
            blocos.append("\n".join(partes))
        return "\n\n".join(blocos)

    def _formatar_specs_blocos(self, blocos: List[Dict[str, Any]]) -> str:
        partes_totais = []
        for bloco in blocos:
            partes = [
                f"--- {bloco['nome']} ({bloco.get('duracao', '')}) ---",
                f"Slide: {bloco.get('slide', '')}",
            ]
            for instrucao in bloco.get("instrucoes", []):
                partes.append(f"- {instrucao}")
            for chave, valor in bloco.items():
                if chave.startswith("formato"):
                    partes.append(f"Formato ({chave}):\n{valor}")
            partes_totais.append("\n".join(partes))
        return "\n\n".join(partes_totais)

    def _chamar_claude(self, prompt: str, max_tokens: int = 8000) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(max_output_tokens=max_tokens),
        )
        return response.text

    def _parsear_json(self, texto: str) -> Dict[str, Any]:
        """Extrai o primeiro objeto JSON válido da resposta (mesmo padrão usado no Departamento de Tratamento)."""
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if not match:
            raise ValueError("A IA de Relatório e Roteiro não retornou JSON válido.")
        return json.loads(match.group(0))
