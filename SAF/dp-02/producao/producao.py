"""
Departamento de Produção
Orquestra: IA de Relatório e Roteiro → IA Fiscal do Relatório e Roteiro
(com loop de correção quando a Fiscal reprova) → entrega final.

Fluxo (espelha o fluxograma enviado pelo analista):

    dados do motor (Diagnóstico OU Mensalidade)
              │
              ▼
    IA de Relatório e Roteiro  ──────┐  gera texto do PDF + roteiro de vídeo
              │                      │
              ▼                      │ (loop pontilhado: reprovou → volta
    IA Fiscal do Relatório e         │  com o feedback pra gerar de novo)
    Roteiro  ─────────────────────────┘
              │
              ▼
       aprovado? ──não (esgotou tentativas)──> REVISAO_MANUAL_NECESSARIA
              │
             sim
              ▼
           SUCESSO — pronto pra virar PDF/vídeo e ir pro cliente

Unificado pros dois produtos: mesma classe, mesmo loop — a diferença de
estrutura (9 vs 10 páginas, 6-8min vs 7-9min de vídeo, aposta anterior só
na Mensalidade) já está resolvida dentro de templates.py e das próprias
IAs, então quem chama este orquestrador só passa `tipo_produto` e os dados.
"""

from .models import (
    TipoProduto,
    TipoDocumento,
    RelatorioTexto,
    RoteiroTexto,
    RevisaoFiscal,
    ResultadoProducao,
    StatusProducao,
)
from .relatorio_roteiro import IARelatorioRoteiro
from .fiscal_relatorio import IAFiscalRelatorioRoteiro
from datetime import datetime
from typing import Any, Dict, Optional


class DepartamentoProducao:
    """Orquestra as 2 IAs de produção (Relatório e Roteiro → Fiscal) com loop de correção."""

    def __init__(self, max_tentativas: int = 2):
        """
        max_tentativas: quantas vezes a IA de Relatório e Roteiro tenta
        corrigir e regerar depois de uma reprovação da Fiscal, antes de
        desistir e devolver pra revisão manual do analista. Default = 2
        (1ª geração + 1 regeração com o feedback da Fiscal).

        Decisão de design: um documento NUNCA sai como SUCESSO sem estar
        efetivamente aprovado pela Gem Fiscal (nem com bloqueadores, nem
        com ajustes pendentes) — se esgotar as tentativas, o resultado é
        REVISAO_MANUAL_NECESSARIA, igual ao Departamento de Tratamento
        parar quando a Fiscal de Dados encontra bloqueadores. A Produção
        nunca manda algo pro cliente sozinha.
        """
        self.gerador = IARelatorioRoteiro()
        self.fiscal = IAFiscalRelatorioRoteiro()
        self.max_tentativas = max_tentativas

    def processar(
        self,
        tipo_produto: TipoProduto,
        dados_motor: Dict[str, Any],
        cliente: Dict[str, Any],
        periodo_anterior: Optional[Dict[str, Any]] = None,
        diagnostico_periodo_anterior_completo: Optional[Dict[str, Any]] = None,
        percepcoes_cliente: Optional[Dict[str, Any]] = None,
    ) -> ResultadoProducao:
        """
        dados_motor: export_to_dict() do motor (Diagnóstico ou Mensalidade) do PERÍODO ATUAL.
        cliente: {'nome_loja', 'periodo' (Diagnóstico) ou 'mes_ano' (Mensalidade), 'categoria', ...}
        periodo_anterior: recorte simples (financial/comparatives) do período/mês anterior,
            usado na página de comparação — opcional, None se for o primeiro período/mês.
        diagnostico_periodo_anterior_completo: o export_to_dict() INTEIRO do
            período/mês anterior. Só usado pra extrair automaticamente a
            "aposta anterior" (a antiga célula manual CONFIG!B53) da
            Mensalidade — a Prioridade #1 de lá vira a aposta deste mês,
            sem precisar de nenhuma célula preenchida à mão. Ignorado no
            Diagnóstico.
        percepcoes_cliente: NOVIDADE (06/09/2026) — dict vindo de
            PercepcoesCliente (dp-01/tratamento/models.py), as respostas
            subjetivas do cliente sobre o próprio negócio (Seção 6 do
            formulário — só existe no Diagnóstico). Usado pela IA de
            Relatório e Roteiro e pela IA Fiscal pra montar/validar o
            Diagnóstico Comparativo ("o que o cliente acredita" vs "o que
            os dados mostram"). None/vazio = gera normalmente, sem forçar
            nenhuma comparação — nunca é um erro.
        """
        print("\n" + "=" * 60)
        print("🎬 DEPARTAMENTO DE PRODUÇÃO")
        print("=" * 60)

        aposta_anterior = None
        if tipo_produto == TipoProduto.MENSALIDADE:
            aposta_anterior = self._extrair_aposta_anterior(diagnostico_periodo_anterior_completo)

        feedback_relatorio: Optional[RevisaoFiscal] = None
        feedback_roteiro: Optional[RevisaoFiscal] = None
        relatorio: Optional[RelatorioTexto] = None
        roteiro: Optional[RoteiroTexto] = None
        revisao_relatorio: Optional[RevisaoFiscal] = None
        revisao_roteiro: Optional[RevisaoFiscal] = None

        for tentativa in range(1, self.max_tentativas + 1):
            print(f"\n[Tentativa {tentativa}/{self.max_tentativas}]")

            print("  [1/4] ✍️  IA de Relatório e Roteiro: gerando relatório PDF...")
            relatorio = self.gerador.gerar_relatorio(
                tipo_produto, dados_motor, cliente, periodo_anterior, feedback_relatorio, percepcoes_cliente
            )

            print("  [2/4] 🎬 IA de Relatório e Roteiro: gerando roteiro de vídeo...")
            roteiro = self.gerador.gerar_roteiro(
                tipo_produto, dados_motor, cliente, relatorio, periodo_anterior, aposta_anterior,
                feedback_roteiro, percepcoes_cliente,
            )

            print("  [3/4] ✅ IA Fiscal: revisando relatório PDF...")
            revisao_relatorio = self.fiscal.revisar_relatorio(
                tipo_produto, relatorio, dados_motor, cliente, percepcoes_cliente
            )
            print(f"        → {revisao_relatorio.status.value} "
                  f"({len(revisao_relatorio.bloqueadores)} bloqueador(es), "
                  f"{len(revisao_relatorio.ajustes)} ajuste(s))")

            print("  [4/4] ✅ IA Fiscal: revisando roteiro de vídeo...")
            revisao_roteiro = self.fiscal.revisar_roteiro(
                tipo_produto, roteiro, dados_motor, cliente, percepcoes_cliente
            )
            print(f"        → {revisao_roteiro.status.value} "
                  f"({len(revisao_roteiro.bloqueadores)} bloqueador(es), "
                  f"{len(revisao_roteiro.ajustes)} ajuste(s))")

            relatorio_ok = not revisao_relatorio.precisa_correcao
            roteiro_ok = not revisao_roteiro.precisa_correcao

            if relatorio_ok and roteiro_ok:
                print(f"\n✅ APROVADO na tentativa {tentativa} — pronto pro cliente.")
                return ResultadoProducao(
                    status=StatusProducao.SUCESSO,
                    tipo_produto=tipo_produto,
                    cliente_nome=cliente.get("nome_loja", ""),
                    relatorio=relatorio,
                    roteiro=roteiro,
                    revisao_relatorio=revisao_relatorio,
                    revisao_roteiro=revisao_roteiro,
                    tentativas=tentativa,
                    timestamp=datetime.now().isoformat(),
                )

            # Reprovado — prepara feedback pra próxima tentativa (loop pontilhado do fluxograma)
            feedback_relatorio = revisao_relatorio if not relatorio_ok else None
            feedback_roteiro = revisao_roteiro if not roteiro_ok else None
            print(f"\n🔁 Reprovado — {'relatório' if not relatorio_ok else ''}"
                  f"{' e ' if not relatorio_ok and not roteiro_ok else ''}"
                  f"{'roteiro' if not roteiro_ok else ''} precisa(m) de correção.")

        print(f"\n🔴 ESGOTADAS {self.max_tentativas} TENTATIVAS — enviando para revisão manual do analista.")
        return ResultadoProducao(
            status=StatusProducao.REVISAO_MANUAL_NECESSARIA,
            tipo_produto=tipo_produto,
            cliente_nome=cliente.get("nome_loja", ""),
            relatorio=relatorio,
            roteiro=roteiro,
            revisao_relatorio=revisao_relatorio,
            revisao_roteiro=revisao_roteiro,
            tentativas=self.max_tentativas,
            timestamp=datetime.now().isoformat(),
        )

    def _extrair_aposta_anterior(self, diagnostico_anterior: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Deriva automaticamente a "aposta anterior" (antiga célula manual
        CONFIG!B53) a partir da Prioridade #1 do mês passado — nenhuma
        célula pra preencher à mão. Se não houver mês anterior ou ele não
        tiver gerado nenhuma prioridade, retorna None (equivalente a
        B53 vazia nos guias — os textos padrão de "sem aposta" entram em cena).
        """
        if not diagnostico_anterior:
            return None
        prioridades = diagnostico_anterior.get("top_3_priorities") or []
        if not prioridades:
            return None
        prioridade_1 = prioridades[0]
        return {
            "texto": prioridade_1.get("action") or prioridade_1.get("rule", ""),
            "alerta": prioridade_1.get("rule", ""),
            "codigo_alerta": prioridade_1.get("code", ""),
        }


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

def exemplo_uso():
    """
    Demonstra o pipeline completo: Motor de Diagnóstico → Departamento de
    Produção. Sem GEMINI_API_KEY configurada, as chamadas às IAs vão
    falhar — o resultado esperado neste ambiente é REVISAO_MANUAL_NECESSARIA
    (a IA Fiscal nunca aprova por omissão, ver _validacao_padrao_em_erro),
    não um SUCESSO fabricado.
    """
    import os
    import sys

    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..",
    ))
    from financial_engine import FinancialDiagnosticEngine
    from financial_engine_models import ConfigParameters, FinancialInput, BusinessCategory, TaxRegime, SalesChannel

    config = ConfigParameters(
        client_name="E-commerce Teste",
        analysis_period="Jan–Jun/2026",
        business_category=BusinessCategory.B,
        tax_regime=TaxRegime.SIMPLES_NACIONAL,
        tax_rate=0.04,
    )
    input_data = FinancialInput(
        analysis_period="Jan–Jun/2026",
        revenue_gross=500000.0,
        returns_cancellations=25000.0,
        cmv=150000.0,
        variable_costs=80000.0,
        fixed_costs=50000.0,
        pro_labore=10000.0,
        num_orders=2000,
        ads_investment=40000.0,
        new_customers_ads=800,
        primary_ads_channel="Meta Ads",
        avg_collection_period=15.0,
        avg_payment_period=30.0,
        channel_revenues={
            SalesChannel.SHOPIFY: 300000.0,
            SalesChannel.MERCADO_LIVRE: 150000.0,
            SalesChannel.INSTAGRAM: 25000.0,
        },
    )

    engine = FinancialDiagnosticEngine(config)
    diagnostic = engine.run_diagnostic(input_data)
    dados_motor = engine.export_to_dict(diagnostic)

    cliente = {
        "nome_loja": "E-commerce Teste",
        "periodo": "Jan–Jun/2026",
        "categoria": config.business_category.value,
    }

    depto = DepartamentoProducao(max_tentativas=2)
    resultado = depto.processar(TipoProduto.DIAGNOSTICO, dados_motor, cliente)

    print("\n" + "=" * 70)
    print(f"STATUS FINAL: {resultado.status.value}")
    print("=" * 70)
    if resultado.revisao_relatorio:
        print("\n--- Revisão do Relatório ---")
        print(resultado.revisao_relatorio.texto_completo)


if __name__ == "__main__":
    exemplo_uso()
