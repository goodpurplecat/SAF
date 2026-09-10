"""
Teste do app.py (orquestrador principal)

Como em test_tratamento.py/test_producao.py/test_edicao.py, dividido em:
1. Testes estruturais/determinísticos (SEM chamada de API) — os helpers de
   conversão (_montar_channel_revenues, _mes_para_enum), o motor de
   Diagnóstico e o motor de Mensalidade rodados de ponta a ponta a partir
   de um `dados_limpos` fabricado à mão (equivalente ao que
   dp-01/tratamento/limpeza.py produziria, mas sem precisar da IA
   Extratora pra gerar) — isso testa exatamente os bugs de integração
   corrigidos ao construir app.py (ver docstring de app.py e os comentários
   "CORREÇÃO (05/09/2026, auditoria app.py)" em limpeza.py), e a montagem
   de dados_graficos reais (com e sem período anterior).
2. Teste do pipeline completo, de ponta a ponta de verdade (formulário →
   PDF/vídeo) — requer GEMINI_API_KEY; sem ela, a falha é ESPERADA e
   capturada explicitamente (mesma limitação ambiental dos outros 3 testes).

Também cobre a config/taxas_canais.json (05/09/2026, pedido do analista:
"como faço pra atualizar a taxa de cada canal") — confirma que editar o
JSON muda de verdade a taxa usada pelo motor, e que o motor não quebra se
o arquivo sumir ou vier corrompido.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import (
    PipelineSAF,
    ResultadoPipeline,
    _mes_para_enum,
    _montar_channel_revenues,
)


def teste_montar_channel_revenues():
    print("\n[1/7] _montar_channel_revenues(): canal conhecido vira enum; canal customizado entra do mesmo jeito...")
    from financial_engine_models import SalesChannel

    convertido, customizados = _montar_channel_revenues({
        "Mercado Livre": 1000.0,
        "Shopify / Loja Própria": 500.0,
        "Loja Que Não Existe": 200.0,
    })
    # CORREÇÃO (05/09/2026, pedido do analista): antes um canal fora da
    # lista conhecida era descartado. Agora ele entra igual, como string —
    # "o público que vou atender é só a galera do e-commerce, então tenho
    # que ter o máximo de opções possível [...] se não for nenhum dos que
    # a gente citou, o próprio cliente tem que declarar".
    assert convertido == {
        SalesChannel.MERCADO_LIVRE: 1000.0,
        SalesChannel.SHOPIFY: 500.0,
        "Loja Que Não Existe": 200.0,
    }, f"Conversão incorreta: {convertido}"
    assert customizados == ["Loja Que Não Existe"], f"Deveria sinalizar só o canal customizado: {customizados}"

    vazio, customizados_vazio = _montar_channel_revenues({})
    assert vazio == {} and customizados_vazio == []
    print("      ✅ Canal conhecido vira enum (taxa de referência automática); canal customizado entra como "
          "texto livre (0% até declarar a taxa real), nada é descartado.")


def teste_mes_para_enum():
    print("\n[2/7] _mes_para_enum(): variações de texto...")
    from monthly_engine_models import Month

    assert _mes_para_enum("Abril") == Month.ABR
    assert _mes_para_enum("abril") == Month.ABR
    assert _mes_para_enum("Abril/2026") == Month.ABR
    assert _mes_para_enum("JANEIRO 2026") == Month.JAN
    assert _mes_para_enum("Dezembro") == Month.DEZ

    try:
        _mes_para_enum("Mêsinventado")
        assert False, "Deveria ter levantado ValueError pra mês não reconhecido"
    except ValueError:
        pass
    print("      ✅ Reconhece nome do mês com/sem acento, caixa, ano ou barra anexados; rejeita o que não bate.")


def _dados_limpos_diagnostico_fake():
    """
    Formato EXATO que dp-01/tratamento/limpeza.py::_limpar_para_diagnostico()
    produz hoje (pós-correção) — fabricado à mão aqui pra não depender da
    IA Extratora/Fiscal (que precisam de GEMINI_API_KEY).
    """
    return {
        "tipo_produto": "DIAGNOSTICO",
        "config": {
            "client_name": "Loja Teste Diagnóstico",
            "analysis_period": "Jan–Jun/2026",
            "business_category": "B",
            "tax_rate": 0.04,
            "tax_regime": "Simples Nacional",
        },
        "input_data": {
            "analysis_period": "Jan–Jun/2026",
            "revenue_gross": 500000.0,
            "returns_cancellations": 25000.0,
            "cmv": 150000.0,
            "variable_costs": 80000.0,
            "fixed_costs": 50000.0,
            "pro_labore": 10000.0,
            "num_orders": 2000,
            "ads_investment": 40000.0,
            "new_customers_ads": 800,
            "avg_collection_period": 15.0,
            "avg_payment_period": 30.0,
            "channel_revenues": {
                "Shopify / Loja Própria": 300000.0,
                "Mercado Livre": 150000.0,
                "Instagram / WhatsApp": 25000.0,
            },
        },
        "status_limpeza": "COMPLETO",
        "timestamp": "2026-09-05T00:00:00",
    }


def _dados_limpos_mensalidade_fake(mes="Abril"):
    return {
        "tipo_produto": "MENSALIDADE",
        "config": {
            "client_name": "Loja Teste Mensalidade",
            "business_category": "B",
            "tax_rate": 0.06,
            "tax_regime": "MEI",
        },
        "monthly_input": {
            "month": mes,
            "data": {
                "revenue_gross": 60000.0,
                "returns_cancellations": 2000.0,
                "cmv": 18000.0,
                "variable_costs": 6000.0,
                "fixed_costs": 9000.0,
                "pro_labore": 4000.0,
                "num_orders": 400,
                "ads_investment": 2500.0,
                "new_customers_ads": 60,
                "avg_collection_period": 10.0,
                "avg_payment_period": 20.0,
                "channel_revenues": {"Mercado Livre": 60000.0},
            },
        },
        "status_limpeza": "COMPLETO",
        "timestamp": "2026-09-05T00:00:00",
    }


def teste_motor_diagnostico_a_partir_da_limpeza():
    """
    Este é o teste que teria pegado o bug original: ConfigParameters(**config)
    quebrava com TypeError por causa da chave 'year' que limpeza.py incluía
    (nenhum teste antes deste instanciava o motor a partir da saída real da
    Limpeza — cada test_*.py forjava ConfigParameters/FinancialInput à mão).
    """
    print("\n[3/7] Motor de Diagnóstico a partir de dados_limpos (formato real da Limpeza)...")
    pipeline = PipelineSAF()
    avisos = []
    dados_motor, categoria = pipeline._rodar_motor_diagnostico(_dados_limpos_diagnostico_fake(), avisos)

    assert dados_motor["client_name"] == "Loja Teste Diagnóstico"
    assert dados_motor["analysis_period"] == "Jan–Jun/2026", "analysis_period deveria vir preenchido (não vazio)"
    assert dados_motor["is_valid"] is True
    assert categoria, "categoria (derivada) não deveria vir vazia"
    nomes_canais = {c["name"] for c in dados_motor["channels"]}
    assert nomes_canais == {"Shopify / Loja Própria", "Mercado Livre", "Instagram / WhatsApp"}, nomes_canais
    assert avisos == [], f"Não deveria gerar aviso com canais todos válidos: {avisos}"
    print(f"      ✅ ConfigParameters/FinancialInput construídos sem erro — categoria derivada: {categoria}, "
          f"{len(nomes_canais)} canal(is) reconhecido(s).")

    print("      Canal fora da lista conhecida entra no cálculo mesmo assim (cliente declarou) + vira aviso...")
    dados_com_canal_novo = _dados_limpos_diagnostico_fake()
    dados_com_canal_novo["input_data"]["channel_revenues"]["Canal Inventado XYZ"] = 999.0
    avisos2 = []
    dados_motor2, _ = pipeline._rodar_motor_diagnostico(dados_com_canal_novo, avisos2)
    assert any("Canal Inventado XYZ" in a for a in avisos2), avisos2
    nomes_canais2 = {c["name"] for c in dados_motor2["channels"]}
    assert "Canal Inventado XYZ" in nomes_canais2, (
        f"Canal customizado deveria aparecer no cálculo de canais (com 0% de taxa), não ser descartado: {nomes_canais2}"
    )
    canal_novo_perf = next(c for c in dados_motor2["channels"] if c["name"] == "Canal Inventado XYZ")
    assert canal_novo_perf["fee_rate"] == 0.0, "Canal sem taxa de referência deveria entrar com 0% até declarar a taxa real"
    print("      ✅ Canal não reconhecido entra no cálculo como texto livre (0% de taxa) + vira aviso informativo.")

    print("      taxas_canais_customizadas: cliente declara a taxa real de um canal fora da lista...")
    avisos2b = []
    dados_motor2b, _ = pipeline._rodar_motor_diagnostico(
        dados_com_canal_novo, avisos2b, taxas_canais_customizadas={"Canal Inventado XYZ": 0.11}
    )
    canal_com_taxa = next(c for c in dados_motor2b["channels"] if c["name"] == "Canal Inventado XYZ")
    assert canal_com_taxa["fee_rate"] == 0.11, canal_com_taxa
    canal_conhecido_ainda_ok = next(c for c in dados_motor2b["channels"] if c["name"] == "Mercado Livre")
    assert canal_conhecido_ainda_ok["fee_rate"] == 0.16, (
        "Declarar a taxa de UM canal customizado não deveria zerar a taxa de referência dos outros (merge, não substituição)"
    )
    print("      ✅ Taxa customizada é aplicada só ao canal declarado — os outros continuam com a taxa de referência (merge).")

    print("      tax_regime inválido também vira aviso, não exceção...")
    dados_regime_ruim = _dados_limpos_diagnostico_fake()
    dados_regime_ruim["config"]["tax_regime"] = "Regime Que Não Existe"
    avisos3 = []
    pipeline._rodar_motor_diagnostico(dados_regime_ruim, avisos3)
    assert any("Regime Que Não Existe" in a for a in avisos3), avisos3
    print("      ✅ tax_regime desconhecido cai no default (Simples Nacional) com aviso, não quebra o motor.")


def teste_motor_mensalidade_a_partir_da_limpeza():
    """
    Confere a segunda correção: devolucoes/novos_clientes_ads/pmr/pmp
    (coletados pela Extratora) agora chegam de fato no MonthlyFinancialInput
    — antes o dicionário monthly_input['data'] parava em 'ads_investment'.
    """
    print("\n[4/7] Motor de Mensalidade a partir de dados_limpos (formato real da Limpeza)...")
    pipeline = PipelineSAF()
    avisos = []
    dados_motor, categoria = pipeline._rodar_motor_mensalidade(_dados_limpos_mensalidade_fake(), None, avisos)

    assert dados_motor["client_name"] == "Loja Teste Mensalidade"
    assert dados_motor["month"] == "Abril"
    assert categoria, "categoria (derivada) não deveria vir vazia"
    # new_customers_ads chegando de verdade -> CAC deveria ser calculável (não None)
    assert dados_motor["marketing"]["cac"] is not None, (
        "CAC deveria ter sido calculado — new_customers_ads=60 estava presente nos dados de entrada "
        "(bug original: esse campo nunca chegava ao motor, CAC saía sempre None)"
    )
    print(f"      ✅ MonthlyFinancialInput construído com todos os campos — categoria: {categoria}, "
          f"CAC calculado: {dados_motor['marketing']['cac']:.2f}")

    print("      Mês por extenso com variações reconhecido (Março, fevereiro, Dezembro/2026)...")
    for mes_texto, mes_esperado in [("Março", "Março"), ("fevereiro", "Fevereiro"), ("Dezembro/2026", "Dezembro")]:
        dm, _ = pipeline._rodar_motor_mensalidade(_dados_limpos_mensalidade_fake(mes=mes_texto), None, [])
        assert dm["month"] == mes_esperado, f"{mes_texto} -> esperava {mes_esperado}, veio {dm['month']}"
    print("      ✅ Todas as variações de texto de mês resolvidas pro Month certo.")

    print("      Com período anterior: comparativos oficiais do motor vêm preenchidos...")
    dados_motor_anterior, _ = pipeline._rodar_motor_mensalidade(_dados_limpos_mensalidade_fake(), None, [])
    dados_motor_atual, _ = pipeline._rodar_motor_mensalidade(
        _dados_limpos_mensalidade_fake(), dados_motor_anterior, []
    )
    comp = dados_motor_atual["comparatives"]["revenue"]
    assert comp["previous"] == dados_motor_anterior["financial"]["revenue_net"], comp
    print(f"      ✅ previous_month_metrics repassado corretamente pro motor (comparativo de receita: {comp}).")


def teste_construir_dados_graficos():
    print("\n[5/7] _construir_dados_graficos(): RESULTADO FINANCEIRO sempre; COMPARATIVO só com período anterior...")
    pipeline = PipelineSAF()

    dados_motor_atual = {"financial": {"revenue_net": 48200.0, "profit_net": {"amount": 9640.0}}}
    ordem = ["BLOCO 1 — RESULTADO FINANCEIRO", "CARD DE TRANSIÇÃO — BLOCO 2", "BLOCO 2 — COMPARATIVO", "BLOCO 3 — PRIORIDADES"]

    graficos_sem_anterior = pipeline._construir_dados_graficos("Diagnóstico", dados_motor_atual, None, ordem)
    assert set(graficos_sem_anterior.keys()) == {"BLOCO 1 — RESULTADO FINANCEIRO"}, graficos_sem_anterior.keys()
    barras = graficos_sem_anterior["BLOCO 1 — RESULTADO FINANCEIRO"].barras
    assert [b.rotulo for b in barras] == ["Receita Líquida", "Lucro Líquido"]
    assert barras[0].valor == 48200.0 and barras[0].valor_comparacao is None
    print("      ✅ Sem período anterior: só RESULTADO FINANCEIRO ganha gráfico (dados do próprio período).")

    dados_motor_anterior = {"financial": {"revenue_net": 40000.0, "profit_net": {"amount": 7000.0}}}
    graficos_com_anterior = pipeline._construir_dados_graficos(
        "Diagnóstico", dados_motor_atual, dados_motor_anterior, ordem
    )
    assert set(graficos_com_anterior.keys()) == {"BLOCO 1 — RESULTADO FINANCEIRO", "BLOCO 2 — COMPARATIVO"}
    barras_comp = graficos_com_anterior["BLOCO 2 — COMPARATIVO"].barras
    receita_bar = next(b for b in barras_comp if b.rotulo == "Receita Líquida")
    assert receita_bar.valor == 48200.0 and receita_bar.valor_comparacao == 40000.0
    print("      ✅ Com período anterior: COMPARATIVO ganha par atual/anterior de verdade.")

    print("      Bloco sem número disponível ou sem correspondência não quebra (cai no ícone)...")
    graficos_incompleto = pipeline._construir_dados_graficos(
        "Diagnóstico", {"financial": {}}, None, ordem
    )
    assert graficos_incompleto == {}, graficos_incompleto
    print("      ✅ dados_motor incompleto não gera gráfico nenhum, mas também não levanta exceção.")


def teste_taxas_canais_configuraveis():
    """
    config/taxas_canais.json: editar o arquivo muda a taxa que o motor usa,
    sem precisar mexer em nenhum .py. Ver comentário em
    dp-01/motores/motor diagnostico/financial_engine_models.py.
    """
    print("\n[6/7] config/taxas_canais.json é a fonte real de ConfigParameters.channel_fees...")
    import json
    import importlib
    import financial_engine_models as fem
    from financial_engine_models import SalesChannel

    caminho = fem._CAMINHO_CONFIG_TAXAS_CANAIS
    assert os.path.exists(caminho), f"Arquivo esperado não existe: {caminho}"

    with open(caminho, "r", encoding="utf-8") as f:
        original = json.load(f)
    assert original["Mercado Livre"] == 0.16, "Valor de referência do teste mudou — ajuste o teste"

    try:
        # Edita o JSON (como o analista faria manualmente) e confirma que o
        # motor pega o valor novo, sem reiniciar processo nem mudar código.
        editado = dict(original)
        editado["Mercado Livre"] = 0.22
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(editado, f, ensure_ascii=False, indent=2)

        config = fem.ConfigParameters(client_name="X", analysis_period="X", business_category="B", tax_rate=0.04)
        assert config.channel_fees[SalesChannel.MERCADO_LIVRE] == 0.22, (
            "Editar o JSON deveria refletir na taxa usada pelo motor"
        )
        assert config.channel_fees[SalesChannel.NUVEMSHOP] == 0.02, "Nuvemshop deveria estar na config"
        print("      ✅ Taxa editada no JSON chega ao motor sem tocar em nenhum .py.")

        # Canal desconhecido no JSON não quebra — só é ignorado com aviso.
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump({**original, "Canal Inventado": 0.5}, f, ensure_ascii=False, indent=2)
        config2 = fem.ConfigParameters(client_name="X", analysis_period="X", business_category="B", tax_rate=0.04)
        assert SalesChannel.MERCADO_LIVRE in config2.channel_fees
        print("      ✅ Nome de canal não reconhecido no JSON é ignorado (aviso), não quebra o motor.")

        # Arquivo corrompido/ausente cai no fallback embutido — motor nunca quebra.
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("{ isso não é JSON válido")
        config3 = fem.ConfigParameters(client_name="X", analysis_period="X", business_category="B", tax_rate=0.04)
        assert config3.channel_fees[SalesChannel.MERCADO_LIVRE] == 0.16, "JSON corrompido deveria cair no fallback"
        print("      ✅ JSON corrompido cai no fallback embutido — motor continua funcionando.")
    finally:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(original, f, ensure_ascii=False, indent=2)


def teste_pipeline_completo_ponta_a_ponta():
    """
    Ambiente sem GEMINI_API_KEY: a falha na IA Extratora (dp-01, 1ª
    chamada de API de todo o pipeline) é ESPERADA — PipelineSAF.processar_cliente()
    captura isso e devolve ResultadoPipeline(status='ERRO', etapa='TRATAMENTO'),
    igual o comportamento já confirmado nos outros 3 testes.
    """
    print("\n[7/7] Pipeline completo (Tratamento → Motor → Produção → Edição) — requer GEMINI_API_KEY...")

    pipeline = PipelineSAF()
    resultado = pipeline.processar_cliente(
        tipo_produto="Diagnóstico",
        respostas_formulario={
            "q1_nome_loja": "E-commerce Teste App",
            "q2_periodo": "Julho/2026",
            "q9_canais": ["Mercado Livre"],
        },
        arquivos_info=[{"nome_arquivo": "vendas.csv", "formato": "csv", "tipo_arquivo": "relatorio_ml"}],
    )

    assert isinstance(resultado, ResultadoPipeline)
    if resultado.status == "SUCESSO":
        print(f"      ✅ Pipeline rodou de ponta a ponta com API real — SUCESSO ({resultado.cliente_nome})")
    else:
        assert resultado.status == "ERRO" and resultado.etapa == "TRATAMENTO", (
            f"Sem API key, esperava ERRO/TRATAMENTO (não uma exceção não tratada); veio "
            f"status={resultado.status!r} etapa={resultado.etapa!r} mensagem={resultado.mensagem!r}"
        )
        print(f"      ⚠️  ERRO/TRATAMENTO — esperado sem GEMINI_API_KEY neste ambiente ({resultado.mensagem})")
        print("      (Isto NÃO é um bug — é a mesma limitação ambiental de test_tratamento.py/test_producao.py.)")

    print("\n      Entrada inválida (tipo_produto desconhecido) é rejeitada sem tocar em nenhum departamento...")
    resultado_invalido = pipeline.processar_cliente(
        tipo_produto="Produto Que Não Existe", respostas_formulario={}, arquivos_info=[],
    )
    assert resultado_invalido.status == "ERRO" and resultado_invalido.etapa == "ENTRADA"
    print("      ✅ Validado antes de chamar qualquer departamento.")


if __name__ == "__main__":
    print("=" * 70)
    print("✅ TESTE: APP.PY (ORQUESTRADOR PRINCIPAL)")
    print("=" * 70)

    teste_montar_channel_revenues()
    teste_mes_para_enum()
    teste_motor_diagnostico_a_partir_da_limpeza()
    teste_motor_mensalidade_a_partir_da_limpeza()
    teste_construir_dados_graficos()
    teste_taxas_canais_configuraveis()
    teste_pipeline_completo_ponta_a_ponta()

    print("\n" + "=" * 70)
    print("✅ TODOS OS TESTES DO APP.PY PASSARAM")
    print("=" * 70)
