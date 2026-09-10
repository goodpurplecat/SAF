"""
IA FISCAL DE PRODUÇÃO — Departamento de Edição

Última barreira do dp-03, antes do PDF e do vídeo finais irem pro cliente.
Compara os DOIS conteúdos já montados (texto que efetivamente foi pros
slides do vídeo e pras páginas do PDF) com os roteiros/relatório aprovados
pela Produção (dp-02) — exatamente o papel da "IA Fiscal de Produção" no
fluxograma do analista (05/09/2026), incluindo o loop pontilhado de volta
pro Intermediador quando reprova.

Dois níveis de checagem, dos mais baratos/objetivos pros mais caros/subjetivos:

1. COMPLETUDE (determinística, sem custo de API): o texto que foi pra cada
   slide/página bate, palavra por palavra, com o texto aprovado pelo dp-02?
   Nenhum bloco sumiu, foi cortado ou trocado de lugar? Isso é fato, não
   opinião — se falhar, é bug no APP Intermediador (edicao.py), não precisa
   de IA pra confirmar, e a revisão já reprova aqui, sem gastar chamada.

2. ESTOURO DE TEXTO (determinístico, medido no render — ver renderer.py):
   igual acima, já vem pronto de fora (edicao.py mede isso ao renderizar) —
   só é incorporado na revisão final.

3. COERÊNCIA (IA, só roda se 1 e 2 passarem): mesmo com o texto certo e sem
   estourar o card, dá pra ter problema que só uma leitura pega — um bloco
   que faz referência a algo que não existe mais fora do contexto do roteiro
   completo (ex.: "veja a tabela abaixo", mas o slide só tem texto+ícone),
   ícone temático que não combina com o conteúdo do bloco, ou o vídeo e o
   PDF "contando histórias" diferentes sobre o mesmo período. Aqui sim entra
   o julgamento de uma IA — mas ela aponta, nunca reescreve, igual a Fiscal
   do dp-02.

Nunca aprova por omissão: erro técnico (API fora, JSON inválido) sempre cai
em NÃO APROVADO, igual ao padrão já usado em fiscal_relatorio.py (dp-02).
"""

from .models import ItemRevisaoFinal, RevisaoFiscalFinal
from google import genai
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class IAFiscalProducaoFinal:
    """Revisa o PDF e o vídeo MONTADOS contra os textos aprovados pelo dp-02."""

    def __init__(self):
        self.client = genai.Client()
        self.model = "gemini-3.6-flash"

    def revisar(
        self,
        tipo_produto: str,
        cliente: Dict[str, Any],
        roteiro_falas_aprovado: Dict[str, str],
        roteiro_falas_montado: Dict[str, str],
        roteiro_cards_aprovado: Dict[str, str],
        roteiro_cards_montado: Dict[str, str],
        relatorio_aprovado: Dict[int, str],
        relatorio_montado: Dict[int, str],
        estouros_detectados: Optional[List[str]] = None,
    ) -> RevisaoFiscalFinal:
        """
        roteiro_falas_*: {nome_do_bloco: fala completa} — o que foi pra IA de
            Áudio (narração). roteiro_cards_*: {nome_do_bloco: texto curto}
            — o que foi pro corpo de texto do slide (decisão do analista,
            05/09/2026: card curto na tela, não a fala inteira). "Aprovado"
            vem do dp-02 (RoteiroTexto.blocos / .blocos_card); "montado" é o
            que a edicao.py efetivamente usou pra cada finalidade.
        relatorio_aprovado / relatorio_montado: {numero_da_pagina: texto}. Mesma
            ideia, pro PDF (RelatorioTexto.paginas vs. o que foi pro pdf_template).
        estouros_detectados: lista de localizações ("Bloco X", "Página N") que
            o renderer já sinalizou como estourando o card fixo (ver
            renderer.render_html_to_png_com_medicao) — checagem 100%
            determinística, feita durante o render, só chega aqui pra virar
            bloqueador formal na revisão final.
        """
        estouros_detectados = estouros_detectados or []

        bloqueadores_deterministicos = (
            self._checar_par("Roteiro (fala)", roteiro_falas_aprovado, roteiro_falas_montado)
            + self._checar_par("Roteiro (card)", roteiro_cards_aprovado, roteiro_cards_montado)
            + self._checar_par("Relatório", relatorio_aprovado, relatorio_montado, rotulo_chave="Página")
        )
        bloqueadores_deterministicos = list(bloqueadores_deterministicos) + [
            ItemRevisaoFinal(
                localizacao=loc,
                problema="O texto ultrapassa a área visível do card/página fixo (estouro detectado no render).",
                sugestao="Card/relatório precisa ser encurtado nesse bloco/página antes de remontar — o layout é fixo e não se ajusta ao tamanho do texto.",
            )
            for loc in estouros_detectados
        ]

        if bloqueadores_deterministicos:
            # Falha objetiva (bug de montagem ou estouro de layout) — nem
            # precisa da IA pra confirmar, e não faz sentido gastar uma
            # chamada revisando coerência de um conteúdo que já sabemos que
            # não pode ir pro cliente como está.
            revisao = RevisaoFiscalFinal(
                bloqueadores=bloqueadores_deterministicos,
                ajustes=[],
                observacoes=[],
                aprovado=False,
            )
            revisao.texto_completo = self._gerar_relatorio_revisao(revisao, motivo_curto="falha determinística (montagem/estouro)")
            return revisao

        try:
            prompt = self._montar_prompt(
                tipo_produto, cliente, roteiro_falas_montado, roteiro_cards_montado, relatorio_montado
            )
            response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(max_output_tokens=3000),
        )
            validacao = self._parsear_json(response.text)
        except Exception as e:
            print(f"[IA FISCAL DE PRODUÇÃO] ❌ Erro: {e}")
            validacao = self._validacao_padrao_em_erro()

        revisao = self._montar_revisao(validacao)
        revisao.texto_completo = self._gerar_relatorio_revisao(revisao, motivo_curto="revisão de coerência (IA)")
        return revisao

    # ------------------------------------------------------------------
    # Nível 1: completude determinística (sem IA)
    # ------------------------------------------------------------------

    def _checar_par(
        self,
        rotulo: str,
        aprovado: Dict[Any, str],
        montado: Dict[Any, str],
        rotulo_chave: str = "Bloco",
    ) -> List[ItemRevisaoFinal]:
        """
        Completude determinística e genérica: usada 3x (fala do roteiro,
        card do roteiro, página do relatório) — cada "montado" precisa ser
        idêntico, chave por chave, ao "aprovado" correspondente.
        """
        achados: List[ItemRevisaoFinal] = []

        def _formatar_localizacao(chave: Any) -> str:
            # Aspas em volta do nome do bloco ajudam a ler ("Bloco 'Resultado
            # Financeiro'"); em números de página só atrapalham ("Página '2'").
            chave_formatada = f"'{chave}'" if isinstance(chave, str) else str(chave)
            return f"{rotulo} / {rotulo_chave} {chave_formatada}"

        for chave, texto_aprovado in aprovado.items():
            texto_usado = montado.get(chave)
            localizacao = _formatar_localizacao(chave)
            if texto_usado is None:
                achados.append(ItemRevisaoFinal(
                    localizacao=localizacao,
                    problema=f"{rotulo_chave} aprovado pela Produção não apareceu no {rotulo.lower()} montado.",
                    sugestao="Verificar o mapeamento no APP Intermediador (edicao.py).",
                ))
            elif texto_usado.strip() != texto_aprovado.strip():
                achados.append(ItemRevisaoFinal(
                    localizacao=localizacao,
                    problema=f"O texto usado em {rotulo.lower()} não é idêntico ao aprovado pela Produção (cortado, resumido ou alterado).",
                    sugestao="Remontar usando o texto exato aprovado — este departamento não tem autorização pra reescrever conteúdo já aprovado.",
                ))

        extras = set(montado) - set(aprovado)
        for chave in extras:
            achados.append(ItemRevisaoFinal(
                localizacao=_formatar_localizacao(chave),
                problema=f"{rotulo} contém um {rotulo_chave.lower()} que não existe no aprovado pela Produção.",
                sugestao="Verificar se o nome/número ficou dessincronizado do conteúdo aprovado.",
            ))

        return achados

    # ------------------------------------------------------------------
    # Nível 2: coerência (IA) — só roda se o nível 1 passar
    # ------------------------------------------------------------------

    def _montar_prompt(
        self,
        tipo_produto: str,
        cliente: Dict[str, Any],
        roteiro_falas_montado: Dict[str, str],
        roteiro_cards_montado: Dict[str, str],
        relatorio_montado: Dict[int, str],
    ) -> str:
        roteiro_formatado = "\n\n".join(
            f"▶ {nome}\nFALA (narração): {fala}\nCARD (texto na tela): {roteiro_cards_montado.get(nome, fala)}"
            for nome, fala in roteiro_falas_montado.items()
        )
        relatorio_formatado = "\n\n".join(f"=== PÁGINA {n} ===\n{t}" for n, t in sorted(relatorio_montado.items()))

        return f"""
Você é a IA FISCAL DE PRODUÇÃO do FinSpots — a última revisão antes do PDF e do vídeo finais irem pro cliente.
O texto de cada bloco/página JÁ foi conferido palavra por palavra contra o aprovado pela Produção (isso não é sua tarefa).
Sua tarefa é achar problemas que só aparecem quando o conteúdo é dividido em cards fixos (1 bloco = 1 slide, mesmo design sempre):

- Um bloco que só faz sentido lido em sequência com outro (ex: "veja a tabela abaixo", "como falamos antes") mas cada slide é isolado (só texto + ícone temático, sem tabelas/imagens extras).
- O CARD (texto curto na tela) contradiz a FALA, ou traz um número que não aparece na fala — o card deve ser sempre um recorte fiel da fala, nunca uma versão diferente da história.
- Vídeo e PDF contando uma história diferente sobre o mesmo período/mês (números ou conclusões que não batem entre os dois).
- Bloco cujo conteúdo claramente não combina com nenhum ícone temático simples (sinal de que o bloco foi classificado errado).

Você APONTA, nunca reescreve.

PRODUTO: {tipo_produto}
CLIENTE: {json.dumps(cliente, ensure_ascii=False)}

ROTEIRO DE VÍDEO MONTADO (1 bloco = 1 slide, na ordem de gravação — fala completa narrada + card curto exibido na tela):
{roteiro_formatado}

RELATÓRIO PDF MONTADO (1 página = 1 seção do PDF):
{relatorio_formatado}

RETORNE APENAS um JSON no formato exato abaixo (sem texto antes ou depois, sem markdown fences):

{{
  "bloqueadores": [{{"localizacao": "...", "problema": "...", "sugestao": "..."}}],
  "ajustes": [{{"localizacao": "...", "problema": "...", "sugestao": "..."}}],
  "observacoes": [{{"localizacao": "...", "problema": "...", "sugestao": "..."}}],
  "status": "APROVADO | APROVADO_COM_OBSERVACOES | NAO_APROVADO"
}}

Regra de status: qualquer bloqueador ou ajuste → "NAO_APROVADO". Só observações → "APROVADO_COM_OBSERVACOES". Nada → "APROVADO".
COMECE!
"""

    def _parsear_json(self, texto: str) -> Dict[str, Any]:
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return self._validacao_padrao_em_erro()

    def _validacao_padrao_em_erro(self) -> Dict[str, Any]:
        """Erro técnico nunca aprova por omissão — mesmo padrão de fiscal_relatorio.py (dp-02)."""
        return {
            "bloqueadores": [{
                "localizacao": "Revisão completa",
                "problema": "A IA Fiscal de Produção não conseguiu revisar o conteúdo final (erro técnico).",
                "sugestao": "Revisar manualmente antes de enviar ao cliente.",
            }],
            "ajustes": [],
            "observacoes": [],
            "status": "NAO_APROVADO",
        }

    def _montar_revisao(self, validacao: Dict[str, Any]) -> RevisaoFiscalFinal:
        def para_itens(lista: List[Dict[str, str]]) -> List[ItemRevisaoFinal]:
            return [
                ItemRevisaoFinal(
                    localizacao=item.get("localizacao", "Não localizado"),
                    problema=item.get("problema", ""),
                    sugestao=item.get("sugestao", ""),
                )
                for item in lista
            ]

        bloqueadores = para_itens(validacao.get("bloqueadores", []))
        ajustes = para_itens(validacao.get("ajustes", []))
        observacoes = para_itens(validacao.get("observacoes", []))
        status = validacao.get("status", "NAO_APROVADO")

        return RevisaoFiscalFinal(
            bloqueadores=bloqueadores,
            ajustes=ajustes,
            observacoes=observacoes,
            aprovado=(status in ("APROVADO", "APROVADO_COM_OBSERVACOES") and not bloqueadores and not ajustes),
        )

    def _gerar_relatorio_revisao(self, revisao: RevisaoFiscalFinal, motivo_curto: str) -> str:
        linhas = [f"IA FISCAL DE PRODUÇÃO — {motivo_curto}", "━" * 30]
        linhas.append(f"🔴 {len(revisao.bloqueadores)} bloqueador(es)")
        for item in revisao.bloqueadores:
            linhas.append(f"  - [{item.localizacao}] {item.problema} → {item.sugestao}")
        linhas.append(f"🟠 {len(revisao.ajustes)} ajuste(s)")
        for item in revisao.ajustes:
            linhas.append(f"  - [{item.localizacao}] {item.problema} → {item.sugestao}")
        linhas.append(f"🟡 {len(revisao.observacoes)} observação(ões)")
        for item in revisao.observacoes:
            linhas.append(f"  - [{item.localizacao}] {item.problema} → {item.sugestao}")
        linhas.append("━" * 30)
        linhas.append("✅ APROVADO — pronto pro cliente" if revisao.aprovado else "❌ NÃO APROVADO — precisa de revisão manual")
        linhas.append(f"Timestamp: {datetime.now().isoformat()}")
        return "\n".join(linhas)
