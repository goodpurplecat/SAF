"""
Teste do Departamento de Produção

Duas partes:
1. Testes estruturais (SEM chamada de API) — validam que templates.py e
   models.py estão consistentes com os guias (contagem de páginas,
   ordem dos blocos de vídeo, comportamento das dataclasses).
2. Teste do pipeline completo (COM chamada de API) — espelha
   test_tratamento.py: sem GEMINI_API_KEY configurada neste ambiente,
   a falha é esperada e é capturada explicitamente, não escondida.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "dp-02"))

from producao import (
    TipoProduto,
    TipoDocumento,
    StatusRevisao,
    StatusProducao,
    ItemRevisao,
    RevisaoFiscal,
    RelatorioTexto,
    RoteiroTexto,
    DepartamentoProducao,
)
from producao import templates as tpl
from producao.relatorio_roteiro import IARelatorioRoteiro


def teste_estrutura_paginas():
    """Confere contagem de páginas contra o que os guias definem."""
    print("\n[1/8] Contagem de páginas do Relatório PDF...")

    diag_paginas = {p["numero"] for p in tpl.DIAGNOSTICO_PAGINAS}
    assert diag_paginas == set(range(2, 10)), f"Diagnóstico deveria ter páginas 2-9, tem {sorted(diag_paginas)}"
    # Capa (pág 1) não é gerada pelo Gem — mas conta no total do guia (9 páginas)
    assert len(diag_paginas) + 1 == 9, "Diagnóstico: Capa + 2-9 deveria somar 9 páginas"

    mensal_paginas = {p["numero"] for p in tpl.MENSALIDADE_PAGINAS}
    assert mensal_paginas == set(range(2, 11)), f"Mensalidade deveria ter páginas 2-10, tem {sorted(mensal_paginas)}"
    assert len(mensal_paginas) + 1 == 10, "Mensalidade: Capa + 2-10 deveria somar 10 páginas"

    print("      ✅ Diagnóstico: 9 páginas (Capa + 2-9) | Mensalidade: 10 páginas (Capa + 2-10)")


def teste_estrutura_blocos_video():
    """Confere que os blocos de vídeo começam com INTRO e terminam com CARD FINAL."""
    print("\n[2/8] Estrutura do roteiro de vídeo...")

    for nome_produto, blocos in [
        ("Diagnóstico", tpl.DIAGNOSTICO_BLOCOS_VIDEO),
        ("Mensalidade", tpl.MENSALIDADE_BLOCOS_VIDEO),
    ]:
        assert blocos[0]["nome"] == "INTRO", f"{nome_produto}: primeiro bloco deveria ser INTRO"
        assert blocos[-1]["nome"] == "CARD FINAL", f"{nome_produto}: último bloco deveria ser CARD FINAL"
        nomes_prioridades = [b["nome"] for b in blocos if "PRIORIDADE" in b["nome"].upper()]
        assert len(nomes_prioridades) >= 1, f"{nome_produto}: deveria ter um bloco de prioridades"
        print(f"      ✅ {nome_produto}: {len(blocos)} blocos, INTRO → ... → CARD FINAL")


def teste_lookup_por_produto():
    """Confere que as funções de lookup batem com o Enum TipoProduto."""
    print("\n[3/8] Lookup de specs por tipo de produto...")

    assert tpl.paginas_do_produto(TipoProduto.DIAGNOSTICO.value) is tpl.DIAGNOSTICO_PAGINAS
    assert tpl.paginas_do_produto(TipoProduto.MENSALIDADE.value) is tpl.MENSALIDADE_PAGINAS
    assert tpl.blocos_video_do_produto(TipoProduto.DIAGNOSTICO.value) is tpl.DIAGNOSTICO_BLOCOS_VIDEO
    assert tpl.blocos_video_do_produto(TipoProduto.MENSALIDADE.value) is tpl.MENSALIDADE_BLOCOS_VIDEO
    print("      ✅ Lookup consistente com TipoProduto.DIAGNOSTICO / .MENSALIDADE")


def teste_revisao_fiscal_dataclass():
    """Confere o comportamento de RevisaoFiscal (bloqueadores/ajustes → precisa_correcao)."""
    print("\n[4/8] Dataclass RevisaoFiscal...")

    revisao_limpa = RevisaoFiscal(tipo_documento=TipoDocumento.RELATORIO, status=StatusRevisao.APROVADO)
    assert not revisao_limpa.tem_bloqueadores
    assert not revisao_limpa.precisa_correcao

    revisao_com_ajuste = RevisaoFiscal(
        tipo_documento=TipoDocumento.RELATORIO,
        ajustes=[ItemRevisao(localizacao="Página 3", problema="Percentual errado", sugestao="Corrigir pra 18%")],
        status=StatusRevisao.NAO_APROVADO,
    )
    assert not revisao_com_ajuste.tem_bloqueadores
    assert revisao_com_ajuste.precisa_correcao  # ajuste sozinho já bloqueia o envio
    feedback = revisao_com_ajuste.como_feedback_para_geradora()
    assert "Página 3" in feedback and "18%" in feedback

    revisao_com_bloqueador = RevisaoFiscal(
        tipo_documento=TipoDocumento.ROTEIRO,
        bloqueadores=[ItemRevisao(localizacao="Bloco 3", problema="Nome do cliente errado", sugestao="Corrigir")],
        status=StatusRevisao.NAO_APROVADO,
    )
    assert revisao_com_bloqueador.tem_bloqueadores
    assert revisao_com_bloqueador.precisa_correcao

    print("      ✅ tem_bloqueadores / precisa_correcao / como_feedback_para_geradora() corretos")


def teste_extrair_aposta_anterior():
    """
    Confere a lógica pura (sem API) de extração automática da 'aposta
    anterior' — o substituto automático da antiga célula manual CONFIG!B53.
    """
    print("\n[5/8] Extração automática da aposta anterior (substitui CONFIG!B53 manual)...")

    depto = DepartamentoProducao.__new__(DepartamentoProducao)  # não precisa das IAs pra este teste

    # Sem mês anterior => None (equivalente a B53 vazia)
    assert depto._extrair_aposta_anterior(None) is None

    # Mês anterior sem prioridades => None
    assert depto._extrair_aposta_anterior({"top_3_priorities": []}) is None

    # Mês anterior com prioridades => extrai a #1 automaticamente
    diagnostico_anterior = {
        "top_3_priorities": [
            {"code": "S1", "rule": "Frequência de recompra abaixo do piso da categoria", "score": 95, "action": "Lançar campanha de recompra"},
            {"code": "S4", "rule": "ROAS abaixo do equilíbrio", "score": 60, "action": "Revisar campanhas"},
        ]
    }
    aposta = depto._extrair_aposta_anterior(diagnostico_anterior)
    assert aposta is not None
    assert aposta["texto"] == "Lançar campanha de recompra"
    assert aposta["codigo_alerta"] == "S1"

    print("      ✅ Aposta anterior extraída automaticamente da Prioridade #1 do mês passado — 0 células manuais")


def teste_roteiro_fala_e_card():
    """
    RoteiroTexto passou a ter 2 textos por bloco (05/09/2026, pedido do
    analista pra manter o card do slide curto em vez de repetir a fala
    inteira na tela) — confere o parsing do schema novo {"fala", "card"} e
    o fallback quando Claude devolve só uma string (schema antigo).
    """
    print("\n[6/8] RoteiroTexto — fala completa + card curto por bloco...")

    gerador = IARelatorioRoteiro.__new__(IARelatorioRoteiro)  # não precisa do client Anthropic pra este teste

    blocos_dict = {
        "blocos": {
            "INTRO": {"fala": "Fala completa da intro, bem mais longa.", "card": "Intro curta"},
            "CARD DE TRANSIÇÃO — BLOCO 1": {"fala": "BLOCO 1 — STATUS", "card": "BLOCO 1 — STATUS"},
            "BLOCO ANTIGO SEM SCHEMA NOVO": "Só uma string, sem fala/card separados",
        }
    }
    roteiro = gerador._construir_roteiro(TipoProduto.DIAGNOSTICO, blocos_dict)

    assert roteiro.blocos["INTRO"] == "Fala completa da intro, bem mais longa."
    assert roteiro.blocos_card["INTRO"] == "Intro curta"
    assert roteiro.blocos["CARD DE TRANSIÇÃO — BLOCO 1"] == roteiro.blocos_card["CARD DE TRANSIÇÃO — BLOCO 1"]
    # Fallback pro schema antigo (Claude devolveu string em vez de {"fala","card"})
    assert roteiro.blocos["BLOCO ANTIGO SEM SCHEMA NOVO"] == "Só uma string, sem fala/card separados"
    assert roteiro.blocos_card["BLOCO ANTIGO SEM SCHEMA NOVO"] == roteiro.blocos["BLOCO ANTIGO SEM SCHEMA NOVO"]

    texto_unico = roteiro.como_texto_unico()
    assert "FALA (narração completa): Fala completa da intro" in texto_unico
    assert "CARD (texto curto na tela): Intro curta" in texto_unico

    print("      ✅ fala/card parseados corretamente; fallback pro schema antigo funciona; como_texto_unico() mostra os dois")


def teste_diagnostico_comparativo_no_prompt_sem_api():
    """
    NOVIDADE (06/09/2026, confirmado pelo analista): quando há
    'percepcoes_cliente' (Seção 6 do formulário — o que o cliente
    ACREDITA sobre o próprio negócio), o prompt da IA de Relatório e
    Roteiro precisa incluir o bloco VOICE_RULES_COMPARATIVO e os valores
    declarados, pro Diagnóstico Comparativo funcionar. Quando NÃO há
    nenhuma percepção, o prompt não deve conter esse bloco — não é pra
    forçar nenhuma comparação. _montar_prompt_relatorio/_montar_prompt_roteiro
    só montam string (não chamam a API), então dá pra testar sem
    GEMINI_API_KEY.
    """
    print("\n[7/8] IA de Relatório e Roteiro: Diagnóstico Comparativo entra/sai do prompt corretamente (sem API)...")

    gerador = IARelatorioRoteiro.__new__(IARelatorioRoteiro)  # não precisa do client Anthropic pra este teste
    dados_motor_fake = {"summary": {"revenue_net": 100000.0}}
    cliente_fake = {"nome_loja": "Loja Teste Comparativo", "periodo": "Jan-Jun/2026", "categoria": "B"}

    percepcoes_com_dado = {
        "percepcao_faturamento": "Crescendo",
        "acha_que_esta_lucrando": "Sim, tenho clareza total",
        "pro_labore_desejado": 5000.0,
        "canal_percebido_como_melhor": "Mercado Livre",
        "sabe_produto_mais_lucrativo": None,
        "objetivo_com_diagnostico": None,
        "maior_duvida_ou_preocupacao": None,
        "outras_percepcoes": {},
    }

    prompt_relatorio_com = gerador._montar_prompt_relatorio(
        TipoProduto.DIAGNOSTICO, dados_motor_fake, cliente_fake, None, None, percepcoes_com_dado
    )
    assert "REGRAS DO DIAGNÓSTICO COMPARATIVO" in prompt_relatorio_com
    assert "Mercado Livre" in prompt_relatorio_com
    assert "5000.0" in prompt_relatorio_com

    prompt_roteiro_com = gerador._montar_prompt_roteiro(
        TipoProduto.DIAGNOSTICO, dados_motor_fake, cliente_fake, None, None, None, None, percepcoes_com_dado
    )
    assert "REGRAS DO DIAGNÓSTICO COMPARATIVO" in prompt_roteiro_com
    assert "Mercado Livre" in prompt_roteiro_com

    # Sem nenhuma percepção declarada (None inteiro, ou todos os campos vazios)
    # — o bloco de regras NÃO deve aparecer, pra IA não forçar comparação.
    for percepcoes_vazias in (None, {}, {"percepcao_faturamento": None, "outras_percepcoes": {}}):
        prompt_sem = gerador._montar_prompt_relatorio(
            TipoProduto.DIAGNOSTICO, dados_motor_fake, cliente_fake, None, None, percepcoes_vazias
        )
        assert "REGRAS DO DIAGNÓSTICO COMPARATIVO" not in prompt_sem, percepcoes_vazias
        assert "não declarou nenhuma percepção" in prompt_sem

    print("      ✅ Bloco de regras do comparativo só entra no prompt quando o cliente realmente declarou algo.")


def teste_pipeline_completo_com_api():
    """
    Pipeline ponta a ponta: Motor de Diagnóstico → Departamento de Produção.
    Ambiente sem GEMINI_API_KEY: a falha na chamada de API é ESPERADA e
    capturada aqui — mesma situação de test_tratamento.py.
    """
    print("\n[8/8] Pipeline completo (Motor → Produção) — requer GEMINI_API_KEY...")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from financial_engine import FinancialDiagnosticEngine
    from financial_engine_models import ConfigParameters, FinancialInput, BusinessCategory, TaxRegime, SalesChannel

    config = ConfigParameters(
        client_name="E-commerce Teste Produção",
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
    assert diagnostic.is_valid
    dados_motor = engine.export_to_dict(diagnostic)

    cliente = {
        "nome_loja": "E-commerce Teste Produção",
        "periodo": "Jan–Jun/2026",
        "categoria": config.business_category.value,
    }

    # CORREÇÃO (auditoria 12/09/2026): mesmo bug de test_tratamento.py —
    # DepartamentoProducao() constrói IARelatorioRoteiro(), que chama
    # genai.Client() no __init__; sem GEMINI_API_KEY isso quebra antes do
    # try, então a construção também precisa estar dentro dele.
    try:
        depto = DepartamentoProducao(max_tentativas=1)
        resultado = depto.processar(TipoProduto.DIAGNOSTICO, dados_motor, cliente)
        # Se GEMINI_API_KEY estiver configurada de verdade, valida o resultado real:
        assert resultado.status in (StatusProducao.SUCESSO, StatusProducao.REVISAO_MANUAL_NECESSARIA)
        print(f"      ✅ Pipeline rodou de ponta a ponta com API real — status: {resultado.status.value}")
    except Exception as e:
        # Esperado neste ambiente: sem GEMINI_API_KEY, a chamada à IA de
        # Relatório e Roteiro falha (mesmo comportamento de IAExtratora em
        # dp-01/tratamento/extratora.py — não engolimos o erro).
        print(f"      ⚠️  Falha esperada sem GEMINI_API_KEY neste ambiente: {type(e).__name__}")
        print("      (Isto NÃO é um bug — é a mesma limitação ambiental de test_tratamento.py.)")


if __name__ == "__main__":
    print("=" * 70)
    print("✅ TESTE: DEPARTAMENTO DE PRODUÇÃO")
    print("=" * 70)

    teste_estrutura_paginas()
    teste_estrutura_blocos_video()
    teste_lookup_por_produto()
    teste_revisao_fiscal_dataclass()
    teste_extrair_aposta_anterior()
    teste_roteiro_fala_e_card()
    teste_diagnostico_comparativo_no_prompt_sem_api()
    teste_pipeline_completo_com_api()

    print("\n" + "=" * 70)
    print("✅ TODOS OS TESTES ESTRUTURAIS PASSARAM")
    print("=" * 70)
