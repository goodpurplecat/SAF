"""
SAF-V4 — Orquestrador Principal (app.py)

Ponto de entrada único do pipeline completo. Liga os 3 departamentos que
até agora só existiam testados isoladamente (cada test_*.py monta os dados
de entrada do departamento seguinte "na mão"), na ordem do fluxograma geral
do analista:

    formulário + arquivos do cliente
              │
              ▼
    dp-01 TRATAMENTO (IA Extratora → IA Fiscal de Dados → IA Limpeza)
              │  dados_limpos (JSON puro, pronto pro motor)
              ▼
    MOTOR (Diagnóstico OU Mensalidade, dp-01/motores/)
              │  dados_motor = engine.export_to_dict(...)
              ▼
    dp-02 PRODUÇÃO (IA de Relatório e Roteiro ↔ IA Fiscal do Relatório e Roteiro)
              │  RelatorioTexto + RoteiroTexto aprovados
              ▼
    dp-03 EDIÇÃO (App de Formatação + IA de Áudio/Slides/Editora → IA Fiscal de Produção Final)
              │
              ▼
    PDF final + vídeo MP4 final, prontos pro cliente

Princípio de design herdado dos 3 departamentos (mantido aqui): o
pipeline PARA no primeiro status que não for SUCESSO e devolve exatamente
em que etapa parou — nunca inventa dado nem finge sucesso. Nenhum
departamento é reimplementado aqui; app.py só importa e liga os três,
adaptando o formato de saída de cada um pro formato de entrada do próximo
(essa "tradução de fronteira" é o único código novo deste arquivo).

BUGS ENCONTRADOS E CORRIGIDOS AO CONSTRUIR ESTE ARQUIVO (05/09/2026):
já eram bugs pré-existentes em dp-01/tratamento/limpeza.py, nunca
detectados porque nenhum teste até então instanciava de fato o motor a
partir da saída da Limpeza (cada test_*.py usava dados forjados à mão).
Ver comentários "CORREÇÃO (05/09/2026, auditoria app.py)" em limpeza.py:
  1. config['year'] não é campo de ConfigParameters — ConfigParameters(**config)
     quebrava com TypeError pra QUALQUER cliente Diagnóstico. Removido.
  2. ConfigParameters.analysis_period (obrigatório) nunca era preenchido. Corrigido.
  3. FinancialInput.analysis_period nunca era preenchido. Corrigido.
  4. cliente.regime_tributario nunca chegava ao motor (ficava sempre no
     default Simples Nacional, mesmo pra MEI/Lucro Presumido). Corrigido.
  5. Mensalidade: 4 campos coletados pela Extratora (devoluções, novos
     clientes via ads, PMR, PMP) nunca chegavam ao monthly_input — receita
     líquida e CAC/LTV da Mensalidade sempre calculados como se esses
     campos fossem zero. Corrigido.
  6. FinancialInput.channel_revenues exige Dict[SalesChannel, float]
     (chaves enum), mas a Limpeza produz Dict[str, float] (nomes livres) —
     quem usar direto ConfigParameters(**config)/FinancialInput(**input_data)
     sem converter quebra ou (pior, silencioso) nunca bate com
     config.channel_fees. Resolvido aqui em _montar_channel_revenues().
"""

import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_ROOT = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------
# sys.path — mesma técnica usada em test_tratamento.py/test_producao.py/
# test_edicao.py e nos shims financial_engine.py/monthly_engine.py da raiz:
# "dp-01", "dp-02", "dp-03" viram pacotes Python importáveis (sem hífen no
# nome do módulo de fato importado); as pastas dos motores têm espaço no
# nome ("motor diagnostico"/"motor mensalidade") e por isso não podem virar
# pacote — entram no sys.path e seus módulos internos são importados soltos.
# ----------------------------------------------------------------------
# CORREÇÃO (05/09/2026, auditoria app.py): usar append() em vez de
# insert(0, ...) dentro do loop — insert(0, ...) inverte a ordem a cada
# iteração (o último item do loop acaba primeiro no sys.path). Isso só não
# tinha quebrado nada até agora porque nada no repositório botava as duas
# pastas de motor no sys.path ao mesmo tempo; foi assim que este trabalho
# descobriu que "motor mensalidade/" tinha uma cópia órfã e desatualizada
# de financial_engine*.py (pré-fix de 04/09/2026, sem a derivação de
# Categoria) — sem nome de pasta com espaço pra impedir o shadowing, ela
# ficava na frente de "motor diagnostico/" e o motor de Diagnóstico
# silenciosamente rodava a versão errada. Os arquivos órfãos foram
# removidos (não eram importados por nada em monthly_engine*.py — só
# citados em comentários) e o append() aqui evita que o próximo módulo
# duplicado por engano volte a causar o mesmo tipo de bug silencioso.
for _sub in (
    os.path.join(_ROOT, "dp-01"),
    os.path.join(_ROOT, "dp-01", "motores", "motor diagnostico"),
    os.path.join(_ROOT, "dp-01", "motores", "motor mensalidade"),
    os.path.join(_ROOT, "dp-02"),
    os.path.join(_ROOT, "dp-03"),
):
    if _sub not in sys.path:
        sys.path.append(_sub)

from tratamento import DepartamentoTratamento  # dp-01
from tratamento.models import TipoProduto as _TipoProdutoTratamento

from financial_engine_models import (  # motor diagnóstico
    ConfigParameters,
    FinancialInput,
    SalesChannel,
    TaxRegime,
)
from financial_engine import FinancialDiagnosticEngine

from monthly_engine_models import (  # motor mensalidade
    Month,
    MonthlyFinancialInput,
    OrderLine,
    ProductAggregate,
    SalesIntelligence,
)
from monthly_engine import MonthlyDiagnosticEngineMain
from sales_intelligence_calculator import calculate_sales_intelligence

# PENDÊNCIA 1 (handoff 15/09/2026): IAExtratoraVendas (pedido por pedido,
# dp-01/tratamento/extratora_vendas.py) e calculate_sales_intelligence()
# (acima) já existiam prontos e testados, mas nenhum dos dois era chamado
# de lugar nenhum do pipeline — DepartamentoTratamento (dp-01) só conhece
# IAExtratora (dados agregados, mesmo formato do Diagnóstico), então
# `sales_intel` sempre chegava em run_monthly_diagnostic() como um
# SalesIntelligence() vazio, não importa o que o cliente tivesse
# realmente vendido. Import direto do pacote `tratamento` (não repassado
# por DepartamentoTratamento.processar_cliente(), que segue servindo só o
# fluxo agregado/financeiro) porque a extração de vendas por pedido é
# deliberadamente um fluxo à parte — ver docstring de extratora_vendas.py.
from tratamento.extratora_vendas import ErroExtracaoVendas, IAExtratoraVendas

from producao import DepartamentoProducao, ResultadoProducao  # dp-02
from producao.models import TipoProduto as _TipoProdutoProducao
from producao import templates as _producao_templates

from edicao import DepartamentoEdicao, BarraGrafico, DadosGrafico  # dp-03
from edicao.models import ResultadoEdicao
from edicao.design_config import bloco_tem_grafico_recomendado


PRODUTOS_VALIDOS = {"Diagnóstico", "Mensalidade"}


@dataclass
class ResultadoPipeline:
    """Resultado consolidado do pipeline completo, para 1 cliente."""

    status: str  # "SUCESSO" | "REVISAO_MANUAL_NECESSARIA" | "ERRO"
    etapa: str  # "TRATAMENTO" | "MOTOR" | "PRODUCAO" | "EDICAO" | "" (SUCESSO)
    tipo_produto: str
    cliente_nome: str
    timestamp: str
    mensagem: str = ""
    resultado_tratamento: Optional[Dict[str, Any]] = None
    dados_motor: Optional[Dict[str, Any]] = None
    resultado_producao: Optional[ResultadoProducao] = None
    resultado_edicao: Optional[ResultadoEdicao] = None
    avisos: List[str] = field(default_factory=list)
    # PENDÊNCIA 3 (handoff 15/09/2026): todo cliente_id visto nos pedidos
    # deste mês (só preenchido pra Mensalidade, quando conteudo_arquivos_vendas
    # foi passado) — quem chama processar_cliente() persiste isto (ver
    # database.py::Relatorio) pra virar known_customer_ids do MÊS SEGUINTE
    # (novo x recorrente). Sem isso persistido em algum lugar, a
    # recorrência nunca teria como ser calculada de verdade mês a mês.
    clientes_ids_mes: List[str] = field(default_factory=list)

    def como_json(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "etapa": self.etapa,
            "tipo_produto": self.tipo_produto,
            "cliente_nome": self.cliente_nome,
            "timestamp": self.timestamp,
            "mensagem": self.mensagem,
            "avisos": self.avisos,
            "dados_motor": self.dados_motor,
            "producao": self.resultado_producao.como_json() if self.resultado_producao else None,
            "edicao": self.resultado_edicao.como_json() if self.resultado_edicao else None,
        }


class PipelineSAF:
    """
    Orquestrador único: dp-01 (Tratamento + Motor) → dp-02 (Produção) →
    dp-03 (Edição). Uma instância pode processar vários clientes (os 3
    departamentos internos não guardam estado entre chamadas).
    """

    def __init__(
        self,
        max_tentativas_producao: int = 2,
        max_tentativas_tecnicas_edicao: int = 2,
        musica_path: Optional[str] = None,
        logo_path: Optional[str] = None,
    ):
        self.tratamento = DepartamentoTratamento()
        self.producao = DepartamentoProducao(max_tentativas=max_tentativas_producao)
        self.edicao = DepartamentoEdicao(
            max_tentativas_tecnicas=max_tentativas_tecnicas_edicao,
            musica_path=musica_path,
            logo_path=logo_path,
        )

    # ------------------------------------------------------------------
    # Entrada pública
    # ------------------------------------------------------------------

    def processar_cliente(
        self,
        tipo_produto: str,
        respostas_formulario: Dict[str, Any],
        arquivos_info: List[Dict[str, Any]],
        conteudo_arquivos: Optional[Dict[str, str]] = None,
        out_dir: Optional[str] = None,
        cliente_extra: Optional[Dict[str, Any]] = None,
        dados_motor_periodo_anterior: Optional[Dict[str, Any]] = None,
        periodo_anterior_recorte: Optional[Dict[str, Any]] = None,
        taxas_canais_customizadas: Optional[Dict[str, float]] = None,
        conteudo_arquivos_vendas: Optional[Dict[str, str]] = None,
        canal_arquivos_vendas: Optional[Dict[str, str]] = None,
        previous_month_product_ids: Optional[Set[str]] = None,
        known_customer_ids: Optional[Set[str]] = None,
        recurring_pct_history: Optional[List[float]] = None,
    ) -> ResultadoPipeline:
        """
        tipo_produto: "Diagnóstico" ou "Mensalidade".
        respostas_formulario / arquivos_info: exatamente o que
            DepartamentoTratamento.processar_cliente() já espera hoje.
        conteudo_arquivos: NOVIDADE (06/09/2026, auditoria "sistema
            digestivo") — {'nome do arquivo (igual ao usado em
            arquivos_info)': 'conteúdo do arquivo já em texto'}. Antes
            desta correção, não existia NENHUM jeito de o conteúdo real de
            um arquivo (extrato, planilha) chegar até a IA Extratora — só
            o nome/formato/tamanho (`arquivos_info`) chegava. Opcional:
            sem isto, a extração usa só o formulário, como sempre. Este
            pipeline não lê binário (.xlsx/.pdf/.csv brutos) — quem
            receber o upload no site precisa converter pra texto antes de
            chamar `processar_cliente()`.
        out_dir: pasta onde o PDF/vídeo finais (dp-03) são escritos —
            default: "saidas/<slug do cliente>_<timestamp>/" na raiz do repo.
        cliente_extra: sobrescreve/adiciona chaves no dicionário `cliente`
            repassado a dp-02/dp-03 (ex.: {'subtitulo_produto': ..., 'data_entrega': ...}).
        dados_motor_periodo_anterior: o export_to_dict() COMPLETO do
            período/mês anterior deste MESMO cliente, se você já tiver
            (hoje ninguém persiste isso ainda — ver README, seção
            "Planejado: histórico de 12 meses + Análise Anual" — então o
            padrão são runs de 1º período/mês, sem comparativo). Quando
            fornecido: (a) para Mensalidade, vira `previous_month_metrics`
            de verdade pro motor calcular os comparativos oficiais; (b)
            para Diagnóstico (que não tem conceito de "mês anterior" no
            motor), é usado só aqui em app.py pra montar o gráfico real do
            bloco COMPARATIVO. Sem isso, os blocos de comparação caem no
            texto/ícone de "primeiro diagnóstico/mês", como sempre
            funcionou.
        periodo_anterior_recorte: repassado direto pro parâmetro
            `periodo_anterior` de DepartamentoProducao.processar() (recorte
            simples pra página de comparação do PDF) — normalmente dá pra
            derivar de dados_motor_periodo_anterior; exposto à parte só
            porque a assinatura de dp-02 já separa os dois.
        taxas_canais_customizadas: {'nome do canal': taxa em fração}, só
            pro Diagnóstico (o Motor de Mensalidade não calcula margem por
            canal hoje). AJUSTE MANUAL, opcional — o caminho automático já
            existe: quando o cliente usa um canal fora da lista conhecida
            (SalesChannel, financial_engine_models.py) e informa a própria
            taxa no formulário, isso é extraído sozinho pela IA Extratora
            (campo `taxas_canais_declaradas`, ver models.py) e chega até
            aqui via `dados_limpos['input_data']['channel_fees_customizadas']`
            — pipeline automático/assíncrono não depende de ninguém passar
            este parâmetro. Use `taxas_canais_customizadas` só pra corrigir
            depois (ex.: o analista revisou e a taxa que o cliente disse
            estava errada) ou pra sobrescrever, pra ESTE cliente, a taxa de
            um canal já conhecido (negociação especial com o Mercado
            Livre, por exemplo) — tem prioridade sobre o que veio do
            formulário se os dois declararem o mesmo canal. Faz merge com
            a tabela de referência (config/taxas_canais.json) e com o que
            veio do formulário — só o(s) canal(is) aqui é(são)
            sobrescrito(s), os outros continuam normalmente (ver correção
            em financial_engine_calculator.py::validate_input).
        conteudo_arquivos_vendas: SÓ MENSALIDADE (handoff 15/09/2026,
            Pendência 1) — {'nome do arquivo de vendas': 'conteúdo já em
            texto'}, os arquivos que o cliente sobe na área "Vendas do
            mês" (pedido por pedido — export de canal ou planilha
            própria), DIFERENTES dos arquivos financeiros agregados que
            vão em `conteudo_arquivos`/`arquivos_info`. Quando fornecido,
            cada arquivo passa por IAExtratoraVendas.extrair_pedidos()
            (dp-01/tratamento/extratora_vendas.py) e o resultado
            (OrderLine) alimenta calculate_sales_intelligence()
            (sales_intelligence_calculator.py) — as 8 Perguntas de
            Negócio deixam de ser um SalesIntelligence() vazio. Sem isto
            (fluxo antigo), o comportamento não muda: sales_intel continua
            vazio, como sempre foi.
        canal_arquivos_vendas: {'nome do arquivo': 'nome do canal'} —
            repassado como `canal_default` pra cada arquivo de
            `conteudo_arquivos_vendas` (ver extrair_pedidos()), útil
            quando um export inteiro é de um único canal que não repete
            essa informação em cada linha (ex.: export nativo do Mercado
            Livre). Opcional; arquivo ausente aqui usa canal_default=None
            (linha sem canal próprio vira "Não informado").
        previous_month_product_ids: IDs de produto (ver ProductAggregate)
            que venderam no(s) mês(es) anterior(es) deste cliente — repassado
            direto pra calculate_sales_intelligence() pra achar "produtos
            parados". Quem chama normalmente lê isso do
            `product_breakdown` do último Relatorio de Mensalidade
            persistido (ver database.py) — sem isso, paused_products_count
            sai sempre 0 (conservador, nunca inventa "parou" sem saber
            quem vendia antes).
        known_customer_ids: todo cliente_id já visto em meses anteriores
            deste cliente — repassado direto pra
            calculate_sales_intelligence() pra separar cliente novo x
            recorrente. Quem chama normalmente é a UNIÃO de
            `ResultadoPipeline.clientes_ids_mes` de todos os relatórios de
            Mensalidade anteriores já persistidos. Sem isso, todo cliente
            do mês conta como novo.
        recurring_pct_history: recurring_pct (fração) dos meses anteriores
            deste cliente, do mais antigo pro mais recente — repassado
            direto pra run_monthly_diagnostic() (alerta S1, ver
            monthly_engine_diagnostic.py). Opcional.
        """
        timestamp = datetime.now().isoformat()

        if tipo_produto not in PRODUTOS_VALIDOS:
            return ResultadoPipeline(
                status="ERRO", etapa="ENTRADA", tipo_produto=tipo_produto, cliente_nome="",
                timestamp=timestamp,
                mensagem=f"tipo_produto inválido: {tipo_produto!r} (esperado {sorted(PRODUTOS_VALIDOS)})",
            )

        avisos: List[str] = []

        # ================================================================
        # ETAPA 1 — TRATAMENTO (dp-01: Extratora → Fiscal de Dados → Limpeza)
        # ================================================================
        print("\n" + "#" * 70)
        print("# PIPELINE SAF-V4 — INÍCIO")
        print("#" * 70)

        try:
            resultado_tratamento = self.tratamento.processar_cliente(
                tipo_produto=_TipoProdutoTratamento(tipo_produto),
                respostas_formulario=respostas_formulario,
                arquivos_info=arquivos_info,
                conteudo_arquivos=conteudo_arquivos,
            )
        except Exception as e:
            # A IA Extratora (dp-01) chama a API de verdade e NÃO engole o
            # erro (ver extratora.py / test_tratamento.py) — sem
            # GEMINI_API_KEY configurada, isso é esperado; capturamos
            # aqui pra devolver o mesmo formato ResultadoPipeline de
            # qualquer outra parada de pipeline, em vez de propagar um
            # traceback cru pra quem chamou app.py.
            return ResultadoPipeline(
                status="ERRO", etapa="TRATAMENTO", tipo_produto=tipo_produto, cliente_nome="",
                timestamp=timestamp, mensagem=f"{type(e).__name__}: {e}",
            )

        if resultado_tratamento.get("status") != "SUCESSO":
            return ResultadoPipeline(
                status="ERRO",
                etapa="TRATAMENTO",
                tipo_produto=tipo_produto,
                cliente_nome=(resultado_tratamento.get("cliente") or {}).get("nome", ""),
                timestamp=timestamp,
                mensagem=resultado_tratamento.get("erro", "Tratamento não retornou SUCESSO."),
                resultado_tratamento=resultado_tratamento,
            )

        nome_loja = resultado_tratamento["cliente"]["nome"]
        periodo_ou_mes = resultado_tratamento["cliente"]["periodo"]
        dados_limpos = resultado_tratamento["dados_limpos"]
        # NOVIDADE (06/09/2026): percepções do cliente (Seção 6 do
        # formulário — só existe no Diagnóstico, ver limpeza.py) seguem
        # direto pra Produção (dp-02), NUNCA pro motor — dados_limpos só
        # empresta a chave, o motor lê só 'input_data' (ver
        # _rodar_motor_diagnostico). Mensalidade não tem essa chave
        # (limpeza.py só a inclui em _limpar_para_diagnostico), .get()
        # cobre esse caso com None sem precisar de um if a mais aqui.
        percepcoes_cliente = dados_limpos.get("percepcoes_cliente") if tipo_produto == "Diagnóstico" else None

        # ================================================================
        # ETAPA 2 — MOTOR (Diagnóstico OU Mensalidade)
        # ================================================================
        clientes_ids_mes: List[str] = []
        try:
            if tipo_produto == "Diagnóstico":
                dados_motor, categoria = self._rodar_motor_diagnostico(
                    dados_limpos, avisos, taxas_canais_customizadas
                )
            else:
                dados_motor, categoria, clientes_ids_mes = self._rodar_motor_mensalidade(
                    dados_limpos,
                    dados_motor_periodo_anterior,
                    avisos,
                    conteudo_arquivos_vendas=conteudo_arquivos_vendas,
                    canal_arquivos_vendas=canal_arquivos_vendas,
                    previous_month_product_ids=previous_month_product_ids,
                    known_customer_ids=known_customer_ids,
                    recurring_pct_history=recurring_pct_history,
                )
        except Exception as e:
            # ErroExtracaoVendas (Pendência 1) cai aqui também — mesmo
            # padrão de "nunca falhar em silêncio" do resto do pipeline:
            # um bloco de vendas que não pôde ser extraído para a etapa
            # MOTOR inteira, em vez de seguir com dado incompleto.
            return ResultadoPipeline(
                status="ERRO", etapa="MOTOR", tipo_produto=tipo_produto, cliente_nome=nome_loja,
                timestamp=timestamp, mensagem=f"{type(e).__name__}: {e}",
                resultado_tratamento=resultado_tratamento, avisos=avisos,
            )

        # cliente comum pra dp-02 e dp-03 (nomes de chave exigidos por eles,
        # diferentes do que dp-01 devolve — ver producao.py/edicao.py)
        cliente: Dict[str, Any] = {"nome_loja": nome_loja, "categoria": categoria}
        if tipo_produto == "Diagnóstico":
            cliente["periodo"] = periodo_ou_mes
        else:
            cliente["mes_ano"] = periodo_ou_mes
        if cliente_extra:
            cliente.update(cliente_extra)

        # ================================================================
        # ETAPA 3 — PRODUÇÃO (dp-02: IA de Relatório e Roteiro ↔ Fiscal)
        # ================================================================
        diagnostico_periodo_anterior_completo = (
            dados_motor_periodo_anterior if tipo_produto == "Mensalidade" else None
        )
        try:
            resultado_producao = self.producao.processar(
                tipo_produto=_TipoProdutoProducao(tipo_produto),
                dados_motor=dados_motor,
                cliente=cliente,
                periodo_anterior=periodo_anterior_recorte,
                diagnostico_periodo_anterior_completo=diagnostico_periodo_anterior_completo,
                percepcoes_cliente=percepcoes_cliente,
            )
        except Exception as e:
            # A IA de Relatório e Roteiro (dp-02) também chama a API de
            # verdade e não engole o erro (ver relatorio_roteiro.py /
            # test_producao.py) — mesma lógica da etapa de Tratamento acima.
            return ResultadoPipeline(
                status="ERRO", etapa="PRODUCAO", tipo_produto=tipo_produto, cliente_nome=nome_loja,
                timestamp=timestamp, mensagem=f"{type(e).__name__}: {e}",
                resultado_tratamento=resultado_tratamento, dados_motor=dados_motor, avisos=avisos,
                clientes_ids_mes=clientes_ids_mes,
            )

        if resultado_producao.status.value != "SUCESSO":
            return ResultadoPipeline(
                status=resultado_producao.status.value,
                etapa="PRODUCAO",
                tipo_produto=tipo_produto,
                cliente_nome=nome_loja,
                timestamp=timestamp,
                mensagem="Produção não aprovou o relatório/roteiro (ver resultado_producao).",
                resultado_tratamento=resultado_tratamento,
                dados_motor=dados_motor,
                resultado_producao=resultado_producao,
                avisos=avisos,
                clientes_ids_mes=clientes_ids_mes,
            )

        # ================================================================
        # ETAPA 4 — EDIÇÃO (dp-03: montagem determinística + Fiscal Final)
        # ================================================================
        relatorio = resultado_producao.relatorio
        roteiro = resultado_producao.roteiro

        titulos_paginas = {
            p["numero"]: p["titulo"]
            for p in _producao_templates.paginas_do_produto(tipo_produto)
        }
        dados_graficos = self._construir_dados_graficos(
            tipo_produto, dados_motor, dados_motor_periodo_anterior, roteiro.ordem_blocos
        )

        if out_dir is None:
            slug = "".join(c if c.isalnum() else "_" for c in nome_loja).strip("_") or "cliente"
            out_dir = os.path.join(_ROOT, "saidas", f"{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        resultado_edicao = self.edicao.processar(
            tipo_produto=tipo_produto,
            cliente=cliente,
            relatorio_paginas=relatorio.paginas,
            roteiro_falas=roteiro.blocos,
            roteiro_cards=roteiro.blocos_card,
            roteiro_ordem=roteiro.ordem_blocos,
            out_dir=out_dir,
            titulos_paginas=titulos_paginas,
            dados_graficos=dados_graficos,
        )

        status_final = resultado_edicao.status.value
        mensagem = {
            "SUCESSO": "Pipeline completo — PDF e vídeo prontos pro cliente.",
            "REVISAO_MANUAL_NECESSARIA": "Edição reprovada pela IA Fiscal de Produção Final — revisão manual necessária.",
            "ERRO": "Falha técnica na montagem (Playwright/ffmpeg) — ver logs.",
        }.get(status_final, status_final)

        print("\n" + "#" * 70)
        print(f"# PIPELINE SAF-V4 — FIM: {status_final}")
        print("#" * 70)

        return ResultadoPipeline(
            status=status_final,
            etapa="" if status_final == "SUCESSO" else "EDICAO",
            tipo_produto=tipo_produto,
            cliente_nome=nome_loja,
            timestamp=timestamp,
            mensagem=mensagem,
            resultado_tratamento=resultado_tratamento,
            dados_motor=dados_motor,
            resultado_producao=resultado_producao,
            resultado_edicao=resultado_edicao,
            avisos=avisos,
            clientes_ids_mes=clientes_ids_mes,
        )

    # ------------------------------------------------------------------
    # Motor de Diagnóstico — tradução dados_limpos -> ConfigParameters/FinancialInput
    # ------------------------------------------------------------------

    def _rodar_motor_diagnostico(
        self,
        dados_limpos: Dict[str, Any],
        avisos: List[str],
        taxas_canais_customizadas: Optional[Dict[str, float]] = None,
    ) -> Tuple[Dict[str, Any], str]:
        config_raw = dict(dados_limpos["config"])

        tax_regime_raw = config_raw.pop("tax_regime", None)
        if tax_regime_raw:
            try:
                config_raw["tax_regime"] = TaxRegime(tax_regime_raw)
            except ValueError:
                avisos.append(
                    f"tax_regime {tax_regime_raw!r} não reconhecido — usando default "
                    f"({TaxRegime.SIMPLES_NACIONAL.value})."
                )
        config = ConfigParameters(**config_raw)

        input_raw = dict(dados_limpos["input_data"])
        channel_revenues_raw = input_raw.pop("channel_revenues", {}) or {}
        channel_revenues, canais_customizados = _montar_channel_revenues(channel_revenues_raw)
        if canais_customizados:
            avisos.append(
                f"Canal(is) fora da lista conhecida, incluído(s) no cálculo mesmo assim, sem taxa de "
                f"referência (considerado 0% até informar a taxa real via channel_fees_custom): "
                f"{canais_customizados}"
            )
        input_raw["channel_revenues"] = channel_revenues
        # analysis_period também precisa bater no FinancialInput (ver
        # correção em limpeza.py); se por algum motivo não vier, cai no
        # mesmo period do config, nunca fica dessincronizado.
        input_raw.setdefault("analysis_period", config.analysis_period)

        # NOVIDADE (05/09/2026, pedido do analista): a taxa de um canal
        # customizado agora chega SOZINHA aqui, vinda do que o próprio
        # cliente declarou no formulário (ver limpeza.py — chave
        # 'channel_fees_customizadas', preenchida a partir de
        # DadosFinanceirosTratados.taxas_canais_declaradas) — pipeline
        # automático/assíncrono não pode depender de alguém lembrar de
        # passar `taxas_canais_customizadas` na mão pra cada cliente.
        # `taxas_canais_customizadas` (parâmetro de processar_cliente)
        # continua existindo como ajuste manual — ex.: o analista corrige
        # depois de ver o relatório — e tem prioridade sobre o que veio do
        # formulário se os dois declararem o mesmo canal.
        taxas_do_formulario_raw = input_raw.pop("channel_fees_customizadas", {}) or {}
        taxas_finais_raw = {**taxas_do_formulario_raw, **(taxas_canais_customizadas or {})}
        if taxas_finais_raw:
            # Reaproveita _montar_channel_revenues() só pela conversão de
            # chave (nome -> SalesChannel se reconhecido, senão string
            # livre) — a lógica é idêntica pra revenue ou fee, o segundo
            # valor de retorno (canais não reconhecidos) não interessa
            # aqui, porque declarar a taxa de um canal customizado É o
            # próprio propósito deste parâmetro, não um problema a avisar.
            taxas_convertidas, _ = _montar_channel_revenues(taxas_finais_raw)
            input_raw["channel_fees_custom"] = taxas_convertidas

        input_data = FinancialInput(**input_raw)

        engine = FinancialDiagnosticEngine(config)
        diagnostic = engine.run_diagnostic(input_data)
        dados_motor = engine.export_to_dict(diagnostic)

        # NOTA: config.business_category já foi sobrescrito dentro de
        # run_diagnostic() (derive_business_category) — é o valor real,
        # não o placeholder que veio da Limpeza. Ver financial_engine.py.
        categoria = config.business_category.value
        return dados_motor, categoria

    # ------------------------------------------------------------------
    # Motor de Mensalidade — tradução dados_limpos -> config dict/MonthlyFinancialInput
    # ------------------------------------------------------------------

    def _rodar_motor_mensalidade(
        self,
        dados_limpos: Dict[str, Any],
        dados_motor_periodo_anterior: Optional[Dict[str, Any]],
        avisos: List[str],
        conteudo_arquivos_vendas: Optional[Dict[str, str]] = None,
        canal_arquivos_vendas: Optional[Dict[str, str]] = None,
        previous_month_product_ids: Optional[Set[str]] = None,
        known_customer_ids: Optional[Set[str]] = None,
        recurring_pct_history: Optional[List[float]] = None,
    ) -> Tuple[Dict[str, Any], str, List[str]]:
        config = dict(dados_limpos["config"])  # Dict[str, Any] tolerante — motor usa .get()
        monthly_input_raw = dados_limpos["monthly_input"]

        mes_enum = _mes_para_enum(monthly_input_raw["month"])

        # CORREÇÃO (auditoria 15/09/2026, handoff Pendência 3): 'year'
        # nunca era preenchido em lugar nenhum — um comentário antigo em
        # limpeza.py ("campo morto, não é lido em lugar nenhum do motor
        # mensal") ficou desatualizado assim que monthly_engine.py passou
        # a exportar 'year' em export_to_dict() (config.get('year', 2026)).
        # Sem isso, TODO relatório de Mensalidade, de qualquer cliente, em
        # qualquer ano, saía com year=2026 fixo — o que quebraria
        # silenciosamente qualquer busca de histórico entre anos
        # diferentes (ex.: comparar Janeiro/2027 com Dezembro/2026).
        # Deriva do próprio texto do período quando ele trouxer um ano
        # (ex.: "Abril/2026"); sem isso, cai no ano corrente.
        config.setdefault("year", _ano_do_periodo(monthly_input_raw["month"]))

        monthly_data = dict(monthly_input_raw["data"])
        monthly_data.setdefault("channel_revenues", {})
        monthly_data.setdefault("channel_fees", {})
        monthly_input = MonthlyFinancialInput(**monthly_data)

        previous_month_metrics = None
        if dados_motor_periodo_anterior:
            previous_month_metrics = dados_motor_periodo_anterior.get("financial")
            if not previous_month_metrics:
                avisos.append(
                    "dados_motor_periodo_anterior fornecido sem chave 'financial' — "
                    "comparativo mês a mês ignorado."
                )

        # ================================================================
        # PENDÊNCIA 1 (handoff 15/09/2026): IA Extratora de Vendas + Sales
        # Intelligence — antes desta correção, `sales_intel` chegava aqui
        # SEMPRE como um SalesIntelligence() vazio (nenhum código no
        # pipeline calculava as 8 Perguntas de Negócio a partir de dado
        # real). conteudo_arquivos_vendas é opcional de propósito: sem ele
        # (fluxo antigo/testes), o comportamento não muda em nada.
        # ================================================================
        sales_intel = SalesIntelligence()
        product_breakdown: List[ProductAggregate] = []
        clientes_ids_mes: List[str] = []

        if conteudo_arquivos_vendas:
            extratora_vendas = IAExtratoraVendas()
            canal_arquivos_vendas = canal_arquivos_vendas or {}
            order_lines: List[OrderLine] = []
            for nome_arquivo, conteudo in conteudo_arquivos_vendas.items():
                # ErroExtracaoVendas sobe direto pra quem chamou
                # processar_cliente() (etapa MOTOR) — nunca seguimos com
                # inteligência de vendas incompleta/inventada.
                order_lines.extend(
                    extratora_vendas.extrair_pedidos(
                        conteudo_arquivo=conteudo,
                        nome_arquivo=nome_arquivo,
                        canal_default=canal_arquivos_vendas.get(nome_arquivo),
                    )
                )

            if order_lines:
                resultado_vendas = calculate_sales_intelligence(
                    order_lines,
                    previous_month_product_ids=previous_month_product_ids,
                    known_customer_ids=known_customer_ids,
                )
                sales_intel = resultado_vendas.sales_intelligence
                product_breakdown = resultado_vendas.product_breakdown
                # Quem chama processar_cliente() (api.py) persiste isto —
                # é o known_customer_ids do MÊS SEGUINTE deste cliente.
                clientes_ids_mes = sorted({
                    linha.cliente_id for linha in order_lines if linha.cliente_id
                })
            else:
                avisos.append(
                    "conteudo_arquivos_vendas foi passado, mas nenhuma linha de pedido válida "
                    "foi extraída (produto_id/cliente_id ausentes em todas) — sales_intelligence "
                    "seguiu vazio, como no fluxo antigo."
                )

        engine = MonthlyDiagnosticEngineMain(config)
        diagnostic = engine.run_monthly_diagnostic(
            reference_month=mes_enum,
            monthly_input=monthly_input,
            sales_intel=sales_intel,
            previous_month_metrics=previous_month_metrics,
            recurring_pct_history=recurring_pct_history,
            product_breakdown=product_breakdown,
        )

        if not diagnostic.is_valid:
            raise ValueError(
                "Motor de Mensalidade recusou os dados: " + "; ".join(diagnostic.validation_errors)
            )

        dados_motor = engine.export_to_dict(diagnostic)

        # Espelha o Diagnóstico: business_category já foi sobrescrito
        # dentro de run_monthly_diagnostic() (derive_business_category),
        # mas aqui já vem como string curta ("A".."E"), não enum.
        categoria = config.get("business_category", "")
        return dados_motor, categoria, clientes_ids_mes

    # ------------------------------------------------------------------
    # Gráficos reais (dp-03) — só pros blocos/dados que já temos de verdade
    # ------------------------------------------------------------------

    def _construir_dados_graficos(
        self,
        tipo_produto: str,
        dados_motor: Dict[str, Any],
        dados_motor_periodo_anterior: Optional[Dict[str, Any]],
        ordem_blocos: List[str],
    ) -> Dict[str, "DadosGrafico"]:
        """
        Monta o dict {nome do bloco -> DadosGrafico} exigido por
        DepartamentoEdicao.processar() (ver graficos.py e design_config.py).
        Casamento por nome EXATO do bloco (mesma chave usada em
        roteiro.blocos), então percorremos `ordem_blocos` (os nomes reais
        que a IA de Relatório e Roteiro gerou) e testamos cada um com
        bloco_tem_grafico_recomendado() — a mesma função que o dp-03 usa
        pra decidir "este bloco merece um número plotado" — em vez de
        adivinhar os nomes exatos aqui.

        Escopo desta primeira versão (documentado, não uma limitação
        escondida): sem uma "ficha" persistida por cliente (ver README,
        "Planejado: histórico de 12 meses + Análise Anual"), este
        orquestrador normalmente roda sem período/mês anterior — nesse
        caso só o bloco RESULTADO FINANCEIRO ganha gráfico real (dados do
        próprio período, sem comparação). Os blocos de COMPARATIVO só
        ganham gráfico quando quem chama processar_cliente() já tem o
        export_to_dict() do período anterior à mão (dados_motor_periodo_anterior)
        — sem isso, caem no ícone temático normal (nada quebra).
        """
        dados_graficos: Dict[str, DadosGrafico] = {}
        financial = dados_motor.get("financial") or {}

        def _valor_lucro_liquido() -> Optional[float]:
            pn = financial.get("profit_net")
            if isinstance(pn, dict):  # Diagnóstico: {'amount', 'percentage', 'status'}
                return pn.get("amount")
            return pn  # Mensalidade: float direto

        def _valor_receita_liquida() -> Optional[float]:
            return financial.get("revenue_net")

        for nome_bloco in ordem_blocos:
            if not bloco_tem_grafico_recomendado(nome_bloco):
                continue
            nome_upper = nome_bloco.upper()

            if "RESULTADO FINANCEIRO" in nome_upper:
                receita = _valor_receita_liquida()
                lucro = _valor_lucro_liquido()
                if receita is None or lucro is None:
                    continue
                dados_graficos[nome_bloco] = DadosGrafico(
                    barras=[
                        BarraGrafico(rotulo="Receita Líquida", valor=receita),
                        BarraGrafico(rotulo="Lucro Líquido", valor=lucro),
                    ],
                    formato_valor="moeda",
                )
                continue

            # Blocos de COMPARATIVO (Diagnóstico: "COMPARATIVO"; Mensalidade:
            # "COMPARATIVO FINANCEIRO"/"COMPARATIVO DE VENDAS") — só com
            # período/mês anterior de verdade em mãos.
            if not dados_motor_periodo_anterior:
                continue
            financial_anterior = dados_motor_periodo_anterior.get("financial") or {}

            if "COMPARATIVO DE VENDAS" in nome_upper:
                # Inteligência de vendas (top produtos) não tem hoje um par
                # numérico limpo pra virar barra sem forçar — fica de fora
                # por enquanto, cai no ícone temático (nada quebra).
                continue

            if "COMPARATIVO" in nome_upper:
                receita_atual = _valor_receita_liquida()
                receita_anterior = financial_anterior.get("revenue_net")
                if receita_atual is None or receita_anterior is None:
                    continue
                barras = [BarraGrafico(rotulo="Receita Líquida", valor=receita_atual, valor_comparacao=receita_anterior)]

                lucro_atual = _valor_lucro_liquido()
                lucro_anterior = financial_anterior.get("profit_net")
                if isinstance(lucro_anterior, dict):
                    lucro_anterior = lucro_anterior.get("amount")
                if lucro_atual is not None and lucro_anterior is not None:
                    barras.append(BarraGrafico(rotulo="Lucro Líquido", valor=lucro_atual, valor_comparacao=lucro_anterior))

                dados_graficos[nome_bloco] = DadosGrafico(
                    barras=barras, formato_valor="moeda",
                    legenda_atual="Atual", legenda_comparacao="Anterior",
                )

        return dados_graficos


# ============================================================================
# Helpers de conversão (módulo, não instância — não dependem de estado)
# ============================================================================


def _montar_channel_revenues(canais_raw: Dict[str, float]) -> Tuple[Dict[Any, float], List[str]]:
    """
    Converte {'Mercado Livre': 1000.0, ...} (nomes livres, como a Limpeza
    produz) para as chaves que FinancialInput.channel_revenues espera.
    Canal conhecido (bate com algum SalesChannel) vira o enum — ganha a
    taxa de referência automática de config/taxas_canais.json. Canal NÃO
    reconhecido (o cliente vende num canal que ainda não está na nossa
    lista) NÃO é descartado — pedido do analista (05/09/2026): "o público
    que vou atender é só a galera do e-commerce, então tenho que ter o
    máximo de opções possível [...] se não for nenhum dos que a gente
    citou, o próprio cliente tem que declarar". Ele entra no cálculo do
    jeito que o cliente escreveu (string livre — ver nome_canal() e o
    comentário em ChannelPerformance, financial_engine_models.py), só que
    sem taxa de referência (considerado 0% até alguém informar a taxa real
    via FinancialInput.channel_fees_custom, que hoje já faz merge com a
    tabela de referência em vez de substituí-la — ver financial_engine_calculator.py).
    `avisados` volta só pra virar um aviso informativo (não é erro).
    """
    convertido: Dict[Any, float] = {}
    avisados: List[str] = []
    for nome, valor in canais_raw.items():
        try:
            convertido[SalesChannel(nome)] = valor
        except ValueError:
            convertido[nome] = valor  # canal customizado — entra do mesmo jeito, como texto livre
            avisados.append(nome)
    return convertido, avisados


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


_MESES_PT = {_sem_acento(m.get_name().lower()): m for m in Month}


def _mes_para_enum(texto_mes: str) -> Month:
    """
    'Abril', 'abril', 'Abril/2026', 'ABRIL 2026', 'Marco/2026' (sem cedilha)
    -> Month.ABR/Month.MAR. Usa correspondência por substring (o texto pode
    vir com ano/barra anexados, como cliente.periodo_analisado normalmente
    traz) em vez de igualdade exata.

    CORREÇÃO (auditoria 12/09/2026): a comparação era feita com o nome do
    mês acentuado ("março"), então qualquer texto sem acento (comum em
    extração de IA, formulários digitados sem acento, ou encoding perdido
    em algum ponto do pipeline) falhava a detectar meses com acento
    (março, é o único caso real em pt-BR) e derrubava a Mensalidade inteira
    com "Mês não reconhecido". Normalizando os dois lados (removendo
    acento) antes de comparar.
    """
    texto_norm = _sem_acento((texto_mes or "").strip().lower())
    for nome_mes, m in _MESES_PT.items():
        if nome_mes in texto_norm:
            return m
    raise ValueError(f"Mês não reconhecido em periodo_analisado: {texto_mes!r}")


def _ano_do_periodo(texto_mes: str) -> int:
    """
    NOVIDADE (auditoria 15/09/2026, handoff Pendência 3): extrai o ano de
    um texto tipo 'Abril/2026' ou 'ABRIL 2026' (mesmo texto que
    _mes_para_enum já recebe) — usado só pra preencher config['year'] do
    Motor de Mensalidade antes de export_to_dict(), pra 'year' no export
    não ficar sempre fixo em 2026 (ver comentário na chamada, em
    _rodar_motor_mensalidade). Sem 4 dígitos reconhecíveis no texto, cai
    no ano corrente — nunca inventa um ano que não veio do dado.
    """
    match = re.search(r"(19|20)\d{2}", texto_mes or "")
    return int(match.group(0)) if match else datetime.now().year


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

def exemplo_uso():
    """
    Demonstra o pipeline INTEIRO de ponta a ponta (dp-01 → motor → dp-02 →
    dp-03) a partir de formulário + arquivos brutos, como um cliente real
    enviaria. Sem GEMINI_API_KEY configurada neste ambiente, a IA
    Extratora (dp-01) falha na primeira chamada de API — comportamento
    ESPERADO aqui, igual test_tratamento.py/test_producao.py/test_edicao.py.
    """
    respostas_formulario = {
        "q1_nome_loja": "E-commerce Teste",
        "q2_periodo": "Julho/2026",
        "q9_canais": ["Mercado Livre", "Shopify"],
    }
    arquivos_info = [
        {"nome_arquivo": "vendas_ml.csv", "formato": "csv", "tipo_arquivo": "relatorio_ml"},
    ]

    pipeline = PipelineSAF()
    resultado = pipeline.processar_cliente(
        tipo_produto="Diagnóstico",
        respostas_formulario=respostas_formulario,
        arquivos_info=arquivos_info,
    )

    print("\n" + "=" * 70)
    print(f"STATUS FINAL DO PIPELINE: {resultado.status} (etapa: {resultado.etapa or '—'})")
    print(f"Mensagem: {resultado.mensagem}")
    print("=" * 70)


if __name__ == "__main__":
    exemplo_uso()
