# 🚀 FINSPOTS - SAF-V4 (ATUALIZADO)

Sistema de diagnóstico financeiro para e-commerce.

## 📦 Estrutura

> **Nota (auditoria 04/09/2026):** esta seção estava desatualizada — descrevia
> uma estrutura plana (`departamento/tratamento/`, módulos de apoio na raiz)
> que não corresponde ao repositório real. A estrutura abaixo reflete o que
> realmente existe hoje. `financial_engine.py` e `monthly_engine.py` na raiz
> agora resolvem o caminho automaticamente (via `sys.path`) para os módulos
> de apoio dentro de `dp-01/motores/`, então o "Uso Rápido" abaixo volta a
> funcionar a partir da raiz.

```
SAF-V4/
├── app.py                           (Orquestrador principal — novo, 05/09/2026: liga dp-01 → motor → dp-02 → dp-03)
├── test_app.py                      (Testes do app.py)
├── financial_engine.py              (Motor de Diagnóstico — shim de raiz)
├── monthly_engine.py                (Motor de Mensalidade — shim de raiz)
├── test_tratamento.py               (Testes do Departamento de Tratamento)
├── test_producao.py                 (Testes do Departamento de Produção)
├── test_edicao.py                   (Testes do Departamento de Edição)
├── requirements.txt                 (Dependências)
├── .env.example                     (Template de variáveis)
├── .gitignore
├── README.md
├── config/
│   └── taxas_canais.json            (Taxa de cada canal — editável sem código, novo 05/09/2026)
└── dp-01/
    ├── motores/
    │   ├── motor diagnostico/       (implementação real do Motor de Diagnóstico)
    │   │   ├── financial_engine.py
    │   │   ├── financial_engine_models.py
    │   │   ├── financial_engine_calculator.py
    │   │   └── financial_engine_diagnostic.py
    │   └── motor mensalidade/       (implementação real do Motor de Mensalidade)
    │       ├── monthly_engine.py
    │       ├── monthly_engine_models.py
    │       ├── monthly_engine_calculator.py
    │       └── monthly_engine_diagnostic.py
    └── tratamento/
        ├── models.py                (Estruturas de dados)
        ├── extratora.py             (IA Extratora - COM CLAUDE)
        ├── fiscal_dados.py          (IA Fiscal - COM CLAUDE)
        ├── limpeza.py               (IA Limpeza)
        └── __init__.py              (Orquestrador: DepartamentoTratamento)
└── dp-02/
    └── producao/                    (Departamento de Produção — novo, 04/09/2026)
        ├── models.py                (Estruturas: RelatorioTexto, RoteiroTexto, RevisaoFiscal, ...)
        ├── templates.py             (Specs página a página / bloco a bloco dos 4 guias)
        ├── relatorio_roteiro.py     (IA de Relatório e Roteiro - COM CLAUDE)
        ├── fiscal_relatorio.py      (IA Fiscal do Relatório e Roteiro - COM CLAUDE)
        └── producao.py              (Orquestrador: DepartamentoProducao)
└── dp-03/
    └── edicao/                      (Departamento de Edição — novo, 05/09/2026)
        ├── models.py                (Estruturas: SlideRenderizado, RevisaoFiscalFinal, ResultadoEdicao, ...)
        ├── design_config.py         (Design fixo: cores, tipografia, ícone por bloco, specs de vídeo/PDF)
        ├── icons.py                 (Ícones SVG temáticos, sólidos, laranja)
        ├── text_utils.py            (Texto → HTML: parágrafos e quebras de linha)
        ├── slide_template.py        (HTML do slide de vídeo — mesmo template fixo sempre)
        ├── pdf_template.py          (HTML da capa + páginas do relatório PDF)
        ├── renderer.py              (HTML → PNG/PDF via Playwright, com medição de estouro de texto)
        ├── audio_generator.py       (IA de Áudio — narração via ElevenLabs, com placeholder)
        ├── video_assembler.py       (IA Editora — montagem determinística via ffmpeg)
        ├── fiscal_producao_final.py (IA Fiscal de Produção - COM CLAUDE)
        ├── edicao.py                (Orquestrador/"APP Intermediador": DepartamentoEdicao)
        └── assets/                  (Logo oficial Finspots — fundo escuro e variante fundo claro)
```

## 🚀 Instalação

```bash
# 1. Instalar dependência
pip install anthropic

# 2. Configurar API Key
export ANTHROPIC_API_KEY="sk-ant-seu-token-aqui"

# 3. Rodar testes
python3 test_tratamento.py
python3 test_producao.py
python3 test_edicao.py
python3 test_app.py
```

## ✨ O que mudou?

✅ **extratora.py** → Agora com Claude integrado
✅ **fiscal_dados.py** → Agora com Claude integrado
⚠️ **financial_engine.py** (raiz) → corrigido em 04/09/2026: agora resolve
sozinho o caminho para `dp-01/motores/motor diagnostico/`
⚠️ **monthly_engine.py** (raiz) → corrigido em 04/09/2026: agora resolve
sozinho o caminho para `dp-01/motores/motor mensalidade/`; motor ganhou os
alertas M4/M5 de LTV:CAC
⚠️ **LTV Simplificado** → corrigido em 04/09/2026: fórmula alinhada com a
planilha (`Ticket × Frequência de Recompra/Ano × Anos de Retenção`); campos
`avg_repurchase_rate`/`retention_rate` viraram
`repurchase_frequency_per_year`/`retention_years`
🆕 **Piso de recorrência por Categoria (A-E)** → o alerta S1 (Motor de
Mensalidade) e o novo alerta R1 (Motor de Diagnóstico) agora usam um piso de
recorrência diferente por categoria (12% a 45%, ver `CATEGORY_RECURRING_FLOOR`
em `monthly_engine_models.py`/`financial_engine_models.py`), em vez de um
corte fixo de 30% pra qualquer cliente — um negócio de ticket alto (Categoria
A) é saudável com bem menos recorrência que um de ticket baixo (Categoria E).
No Motor de Mensalidade, o S1 também distingue frequência baixa **sustentada**
(3+ meses seguidos) de uma queda pontual de um único mês.
🆕 **Categoria do negócio (A-E) automática nos dois motores** → deixou de
ser um campo escolhido manualmente e passou a ser calculada sozinha a
partir do ticket médio e da margem de contribuição do próprio cliente —
nenhuma pergunta nova aparece pro cliente. No Diagnóstico é calculada uma
vez por período; na Mensalidade, todo mês. Ver `derive_business_category()`
em `financial_engine_models.py` / `monthly_engine_models.py`.
🆕 **Departamento de Tratamento limpo** → IA Extratora parou de pedir
Categoria a Claude (não era mais usada) e corrigido um bug latente de
nomes de campo no JSON de extração (`periodo`/`aliquota` →
`periodo_analisado`/`aliquota_impostos`). Campo `nicho_produto` removido
(ideia descartada em favor da Categoria automática).

Ver a seção **Correções da auditoria (04/09/2026)** no final deste README
para a lista completa de bugs corrigidos.

## 📊 Motores

### Financial Engine (Diagnóstico)
- DRE completa
- 14 alertas automáticos (F1–F5, M1–M5, C1–C2, R1, X1) — R1 (retenção por
  Categoria) adicionado em 04/09/2026
- Categoria do negócio (A-E) derivada automaticamente (ticket médio + margem)
- Insights em linguagem natural
- JSON estruturado

### Monthly Engine (Mensalidade)
- 12 meses em paralelo
- Comparativos automáticos
- 15 alertas (F1–F6, M4–M5, V1–V3, S1–S4) — os alertas M4/M5 de LTV:CAC
  foram adicionados em 04/09/2026 para dar paridade com o Motor de
  Diagnóstico, que já os tinha
- Metas real vs orçado

### Departamento de Tratamento
- IA Extratora (extrai dados)
- IA Fiscal de Dados (valida)
- IA Limpeza (normaliza)

### Departamento de Produção (novo, 04/09/2026)
Entra depois do Motor (Diagnóstico ou Mensalidade) já ter rodado — pega o
`export_to_dict()` do motor (o equivalente Python à planilha preenchida nos
guias originais da Gem) e transforma em texto pronto pro relatório PDF e
pro roteiro de vídeo, revisados antes de ir pro cliente:
- **IA de Relatório e Roteiro** — gera o texto de cada página do PDF +
  o roteiro narrado do vídeo, na voz Finspots (dado → interpretação → ação),
  seguindo fielmente os 4 guias fornecidos (Relatório PDF e Roteiro de
  Vídeo, um de cada pro Diagnóstico e um pra Mensalidade).
- **IA Fiscal do Relatório e Roteiro** — última barreira antes do cliente.
  Aponta (nunca reescreve) usando o checklist de 7 blocos do Guia da Gem
  Fiscal, separando achados em 🔴 Bloqueadores / 🟠 Ajustes / 🟡 Observações.
- **Loop de correção automático** — se a Fiscal reprovar (bloqueador OU
  ajuste pendente), o feedback estruturado volta pra IA de Relatório e
  Roteiro regerar (até 2 tentativas por padrão). Só sai como `SUCESSO` se
  a Fiscal aprovar de verdade — sem aprovação, o resultado é
  `REVISAO_MANUAL_NECESSARIA` (a Produção nunca manda nada pro cliente
  sozinha, igual ao Departamento de Tratamento parar diante de
  bloqueadores).
- **Unificado pros dois produtos.** Mesmas 2 classes de IA e o mesmo
  orquestrador (`DepartamentoProducao`) atendem Diagnóstico e Mensalidade —
  a voz e a lógica de bloco são as mesmas nos dois guias; só a estrutura de
  página/bloco muda (9 vs. 10 páginas, vídeo de 6-8min vs. 7-9min), e essa
  diferença está tabelada em `templates.py`, não duplicada em código.
- **Marketing opcional e tolerante a dado parcial (reforçado 05/09/2026).**
  O campo de marketing é opcional no formulário e o público é leigo — é
  comum vir incompleto (ex: sabe quanto investiu em Ads mas não anotou
  quantos clientes novos vieram de lá). O bloco MARKETING/CLIENTES E
  MARKETING (relatório e roteiro, Diagnóstico e Mensalidade) trata 3
  estados em `templates.py`: sem nenhum dado de ads (`formato_sem_dados`);
  ROAS/%Ads presentes mas sem CAC (`formato_parcial_*`, narra o que tem e
  sinaliza o que falta — nunca mostra "R$ 0" nem estima); e tudo presente
  (`formato_com_dados`). O motor (`financial_engine_calculator.py` /
  `monthly_engine_calculator.py`) já calculava ROAS e CAC de forma
  independente (CAC só existe se `new_customers_ads > 0`), mas o texto
  gerado antes tratava "falta o CAC" como "falta tudo" — corrigido.
- **"Aposta anterior" automática (Mensalidade).** A antiga célula manual
  `CONFIG!B53` (a prioridade #1 combinada no mês passado, pra narrar se
  "ganhou ou perdeu a aposta") deixou de existir — o orquestrador extrai
  sozinho a Prioridade #1 do `export_to_dict()` do mês anterior. Zero
  células pra preencher à mão.

Ver `test_producao.py` para os testes (estrutura de páginas/blocos roda sem
API; o pipeline ponta a ponta precisa de `ANTHROPIC_API_KEY`).

### Departamento de Edição (novo, 05/09/2026)
Último departamento do pipeline — pega o relatório + roteiro já **aprovados**
pela Produção (dp-02) e monta os dois entregáveis de verdade: o PDF pronto
(mini Canva) e o vídeo MP4 pronto (narração + card + música + fades),
seguindo à risca a identidade visual do Guia de Marca (v3.1) e o design fixo
combinado com o analista (mesmo template e layout em todo vídeo/relatório
produzido — só o texto e o ícone temático do bloco mudam):

- **App de Formatação (PDF)** e **App de Slides (vídeo)** — `pdf_template.py`
  e `slide_template.py` geram HTML autocontido (degradê preto→#01184b nos
  slides e na capa do PDF, pill laranja de título em formato "flag", ícone
  temático sólido em `#FF7A00`, logo oficial Finspots como marca d'água),
  renderizado de forma 100% determinística em PNG/PDF via Playwright/Chromium
  (`renderer.py`) — nenhuma IA decide layout, só "tira um print" do HTML.
- **2 textos por bloco do roteiro (decisão do analista, 05/09/2026).** A
  fala narrada completa (vai pro ElevenLabs) e um texto curto de card (2-4
  linhas, dado principal + interpretação) são gerados **juntos** pela IA de
  Relatório e Roteiro do dp-02 (`RoteiroTexto.blocos` / `.blocos_card`) — o
  card nunca é a fala transcrita na tela, é um recorte dela. Isso mantém o
  slide visualmente limpo mesmo com narrações longas, e reduz bastante o
  risco de estouro de texto no template fixo. O dp-03 continua 100%
  determinístico: só usa o campo certo pra cada finalidade (fala → áudio,
  card → slide), sem nenhuma IA nova nesse departamento.
- **Card centralizado verticalmente + dado em negrito (ajuste do analista,
  05/09/2026).** Como o card agora é curto, o corpo de texto do slide ficou
  centralizado numa faixa vertical (em vez de fixo perto do título) —
  `slide_template.py` usa flexbox pra isso, então funciona pra 1 linha ou 4
  sem precisar recalcular nada manualmente. R$, % e múltiplos (ex: "11,9x")
  são destacados em negrito automaticamente via regex determinística
  (`text_utils.destacar_dados_importantes`) — sem IA, é só formatação do
  texto já aprovado.
- **Cor uniforme no card (ajuste do analista, 05/09/2026).** A pill do
  título dos slides passou a usar o mesmo laranja do ícone (`#FF7A00`, em
  vez do `#FF5500` da marca) — antes eram tons de propósito diferentes
  ("equilíbrio visual"), agora é uniforme no card, por pedido do analista.
  Só o slide de vídeo mudou; logo e PDF continuam com `#FF5500` (marca).
- **IA de Áudio** (`audio_generator.py`) — narra cada bloco do roteiro via
  ElevenLabs; sem `ELEVENLABS_API_KEY` configurada (ainda não é o caso),
  cai automaticamente em modo placeholder (áudio silencioso com duração
  estimada por contagem de palavras), pra o resto do pipeline continuar
  testável de ponta a ponta sem travar esperando a chave — nunca é entregue
  ao cliente nesse modo.
- **IA Editora** (`video_assembler.py`) — na prática não é uma IA: é
  montagem mecânica via ffmpeg, exatamente o "sanduíche" descrito pelo
  analista — imagem do slide na tela pelo tempo da narração + música de
  fundo num volume pré-determinado + fade in/out entre slides e no vídeo
  todo.
- **Gráfico real nos blocos que comparam número (novo, 05/09/2026).** O
  roteiro de vídeo tem uma regra de voz que presume "o slide já mostra o
  gráfico" — mas até então o slide só desenhava um ícone decorativo. Agora,
  nos blocos que de fato comparam valores (RESULTADO FINANCEIRO,
  COMPARATIVO, COMPARATIVO FINANCEIRO, COMPARATIVO DE VENDAS — ver
  `design_config.BLOCOS_COM_GRAFICO_REAL`), o slide desenha um gráfico de
  barras de verdade (`graficos.py`, SVG determinístico, sem IA e sem
  matplotlib) a partir dos números reais do cliente — passado via
  `DepartamentoEdicao.processar(..., dados_graficos={"Nome do Bloco":
  DadosGrafico(...)})`. Ocupa o mesmo slot visual do ícone e tem prioridade
  sobre ele; nos demais blocos (Status, Marketing, Prioridades etc.),
  continua o ícone temático normal — não têm número comparável limpo o
  suficiente pra virar barra. Este departamento não calcula os números
  sozinho (mesma fronteira de sempre) — quem chama monta o `DadosGrafico` a
  partir de `dados_motor['financial']`/`['comparatives']` (dp-01) e passa
  pronto.
- **Ícones customizáveis (novo, 05/09/2026).** Cada ícone temático pode ser
  substituído por um PNG de fundo transparente em
  `dp-03/edicao/assets/icons/<nome_icone>.png` — sem mudar código, só soltar
  o arquivo com o nome certo. Enquanto não vier, usa o SVG interno
  (`icons.py`). Cor padrão dos ícones: `#FF7A00`.
- **Detecção de estouro de texto (determinística).** Como o slide/página
  mantém a narração completa dentro de um card de tamanho fixo, todo render
  é medido (via Playwright, `renderer.render_html_to_png_com_medicao`) pra
  garantir que o texto não ultrapassa a área visível — sem precisar de IA
  pra flagrar isso, é geometria.
- **IA Fiscal de Produção** (`fiscal_producao_final.py`) — última barreira
  antes do cliente. Primeiro roda checagens 100% determinísticas e sem custo
  de API (o texto que foi pra cada slide/página bate, palavra por palavra,
  com o aprovado pelo dp-02? Estourou o card?) — se alguma falhar, nem chama
  a IA, já reprova. Só se essas passarem, chama Claude pra revisar coerência
  (bloco que só faz sentido em sequência, vídeo e PDF "contando histórias"
  diferentes, ícone que não combina com o conteúdo) — aponta, nunca
  reescreve, mesmo padrão da IA Fiscal do dp-02. Nunca aprova por omissão:
  erro técnico de API sempre cai em `NÃO_APROVADO`.
- **Sem loop de correção automático (decisão de design, diferente do dp-02).**
  O texto já foi aprovado pela Produção — este departamento não tem
  autorização pra reescrever nada, e a montagem é determinística (rodar de
  novo com o mesmo texto dá o mesmo resultado). Então uma reprovação da IA
  Fiscal de Produção vai direto pra `REVISAO_MANUAL_NECESSARIA`. O único
  retry automático (`max_tentativas_tecnicas`) é pra falha técnica
  transitória (Playwright/ffmpeg travando) — se esgotar, o status é `ERRO`
  (infraestrutura), não `REVISAO_MANUAL_NECESSARIA` (conteúdo).

Ver `test_edicao.py` para os testes (templates/render/ffmpeg/completude
determinística rodam sempre, sem nenhuma chave de API; só a aprovação final
da IA Fiscal precisa de `ANTHROPIC_API_KEY` de verdade).

### `app.py` — Orquestrador Principal (novo, 05/09/2026)

Ponto de entrada único do pipeline inteiro — a peça que faltava depois que
os 3 departamentos ficaram prontos. `PipelineSAF.processar_cliente(...)`
liga, na ordem do fluxograma geral:

```
formulário + arquivos do cliente
  → dp-01 Tratamento (Extratora → Fiscal de Dados → Limpeza)
  → Motor (Diagnóstico ou Mensalidade, conforme tipo_produto)
  → dp-02 Produção (Relatório + Roteiro ↔ Fiscal, com loop de correção)
  → dp-03 Edição (PDF + Vídeo montados ↔ Fiscal de Produção Final)
  → PDF final + vídeo MP4 final, prontos pro cliente
```

Mesmo princípio de design dos 3 departamentos: o pipeline **para** no
primeiro status que não for SUCESSO e devolve exatamente em que etapa
parou (`ResultadoPipeline.status`/`.etapa`) — nunca inventa dado nem finge
sucesso. Nenhum departamento foi reimplementado aqui; `app.py` só importa
e liga os três, e o único código novo é a "tradução de fronteira" entre a
saída de um e a entrada do próximo (ex.: `dados_limpos['config']` da
Limpeza → `ConfigParameters` do motor).

Duas responsabilidades específicas de `app.py`, documentadas porque não
são óbvias:

- **Gráfico real (dp-03) construído a partir de `dados_motor`.** O
  gráfico de barras do bloco RESULTADO FINANCEIRO (Receita Líquida ×
  Lucro Líquido do próprio período) é montado sempre; o gráfico
  comparativo do bloco COMPARATIVO/COMPARATIVO FINANCEIRO só é montado
  quando quem chama `processar_cliente()` já tem em mãos o
  `export_to_dict()` do período/mês anterior (parâmetro
  `dados_motor_periodo_anterior`) — sem isso (o caso normal hoje, sem
  nenhuma "ficha" persistida ainda, ver seção seguinte), esses blocos
  caem no ícone temático normal, sem quebrar nada.
- **`previous_month_metrics`/`periodo_anterior` são só "slots" prontos,
  não uma implementação de histórico.** `app.py` sabe passar esses dados
  pra frente se alguém já os tiver — não sabe (ainda) buscá-los sozinho
  de nenhum lugar. Isso é intencional: é exatamente o ponto onde a futura
  "ficha" por cliente (seção abaixo) vai se encaixar, sem precisar mexer
  em `app.py` de novo.

Ver `test_app.py` para os testes — inclui os casos que expuseram os bugs
de integração listados na correção nº 18 (auditoria abaixo), rodando o
motor de verdade a partir do formato real que `limpeza.py` produz, em vez
de dados forjados à mão.

## 🗓️ Planejado: histórico de 12 meses + Análise Anual (não implementado ainda)

Conversa com o analista (05/09/2026): na concepção original, a Mensalidade
era uma "ficha" por cliente — uma cópia de planilha que ia acumulando os
diagnósticos mês a mês ao longo de um ano. Ao completar os 12 meses, o
cliente poderia comprar uma **Análise Anual**: um retrospecto de como foi o
desempenho do ano inteiro (não só mês contra mês anterior, como o
comparativo atual já faz, mas os 12 meses juntos).

Sem a planilha física, a ideia (confirmada com o analista, 05/09/2026) é
que a "ficha" continue existindo, só que como um registro no banco — uma
ficha por cliente, vinculada ao ID dele no Supabase, que vai acumulando o
resultado de cada mês processado. Quando for gerar o próximo mês (ou a
Análise Anual), o histórico daquele cliente é puxado pela ficha dele, pelo
ID. Isso é trabalho de infraestrutura/app.py, não deste repositório, então
**nada disso foi implementado ainda** — só documentando aqui pra não
perder o raciocínio. O que já existe hoje que ajuda quando essa hora
chegar:

- **O motor de Mensalidade já tem uma estrutura pronta pra isso, só não
  usada ainda.** `AnnualMonthlyData` (`monthly_engine_models.py`) já é um
  dataclass com `Dict[Month, ...]` pra inputs, resumos, metas e alertas dos
  12 meses — foi deixado como esqueleto mas nenhum código hoje popula ou lê
  esse objeto. É um bom ponto de partida quando a Análise Anual for
  desenhada de verdade.
- **O encaixe do histórico no dp-02 já existe.** `DepartamentoProducao.processar()`
  já aceita `periodo_anterior` e `diagnostico_periodo_anterior_completo`
  como parâmetros opcionais — é exatamente o "slot" onde o mês anterior
  (vindo de onde quer que o histórico esteja guardado) entra hoje pro
  comparativo mês a mês. Só falta alguém buscar esse dado de um banco de
  verdade e passar pra dentro; a lógica de uso já está pronta e testada.
- **O gráfico real do dp-03 já suporta série de vários pontos, não só par
  atual/anterior.** `graficos.DadosGrafico`/`BarraGrafico`
  (`dp-03/edicao/graficos.py`) aceita qualquer número de barras — hoje é
  usado com 1 barra (Resultado Financeiro) ou pares atual/anterior
  (Comparativo), mas o mesmo código já desenharia um gráfico de 12 pontos
  (receita mês a mês do ano, por exemplo) sem nenhuma mudança, se um dia a
  Análise Anual precisar disso.
- **O que ainda falta desenhar de verdade** (só quando o Supabase existir e
  fizer sentido priorizar): o formato da ficha em si — provavelmente uma
  linha por cliente-mês, indexada pelo ID do cliente, guardando um resumo
  do `export_to_dict()` daquele mês (não precisa o JSON inteiro); a lógica
  de "cliente completou 12 fichas de mês, liberar a oferta da Análise
  Anual" (fica no app.py/painel, não no SAF-V4); e os templates de
  relatório/roteiro da própria Análise Anual (que são conteúdo novo, no
  mesmo padrão do dp-02 — precisam ser escritos do zero, não existe guia
  da Gem pra esse produto ainda).

## 💬 Uso Rápido

### Pipeline completo (recomendado — `app.py`)

```python
from app import PipelineSAF

pipeline = PipelineSAF()
resultado = pipeline.processar_cliente(
    tipo_produto="Diagnóstico",  # ou "Mensalidade"
    respostas_formulario={...},   # respostas do formulário do cliente
    arquivos_info=[...],          # metadados dos arquivos enviados (ML, Shopee, extrato, etc.)
)

print(resultado.status)   # "SUCESSO" | "REVISAO_MANUAL_NECESSARIA" | "ERRO"
print(resultado.etapa)    # onde parou, se não foi SUCESSO: "TRATAMENTO" | "MOTOR" | "PRODUCAO" | "EDICAO"
if resultado.status == "SUCESSO":
    print(resultado.resultado_edicao.pdf_path, resultado.resultado_edicao.video_path)
```

### Só o motor, isolado (uso avançado/depuração)

```python
from financial_engine import FinancialDiagnosticEngine
from financial_engine_models import FinancialInput, ConfigParameters, BusinessCategory

config = ConfigParameters(
    client_name="Minha Loja",
    analysis_period="Jan–Jun/2026",
    business_category=BusinessCategory.B,
    tax_rate=0.04
)

input_data = FinancialInput(
    analysis_period="Jan–Jun/2026",
    revenue_gross=500000,
    cmv=150000,
    # ... mais campos
)

engine = FinancialDiagnosticEngine(config)
diagnostic = engine.run_diagnostic(input_data)
print(diagnostic.summary.overall_status)
```

## 🔐 Configuração

### .env.example → .env
```bash
cp .env.example .env
# Editar .env com sua ANTHROPIC_API_KEY
```

### .gitignore
Não commitar .env!

### Taxa de cada canal de venda (Mercado Livre, Shopee, Nuvemshop, ...)

Essas taxas mudam de tempos em tempos (os marketplaces reajustam a
comissão) — **atualizar não exige mexer em código**. Elas ficam em
[`config/taxas_canais.json`](config/taxas_canais.json), na raiz do
repositório, já com uma lista ampliada (05/09/2026) cobrindo os canais mais
comuns entre lojistas de e-commerce no Brasil:

```json
{
  "Mercado Livre": 0.16,
  "Shopee": 0.14,
  "Amazon": 0.12,
  "Shopify / Loja Própria": 0.03,
  "Nuvemshop": 0.02,
  "TikTok Shop": 0.06,
  "Instagram / WhatsApp": 0.0,
  "Magazine Luiza (Magalu)": 0.17,
  "Americanas": 0.15,
  "Casas Bahia": 0.20,
  "Shein (Marketplace)": 0.16,
  "AliExpress": 0.06,
  "Carrefour Marketplace": 0.16,
  "Dafiti": 0.27,
  "Kabum": 0.18,
  "Netshoes": 0.20,
  "Elo7": 0.18,
  "Enjoei": 0.20,
  "OLX": 0.0,
  "Loja Própria (VTEX)": 0.03,
  "Tray": 0.03,
  "Loja Integrada": 0.03,
  "WooCommerce": 0.03,
  "Wix": 0.03
}
```

Pra atualizar uma taxa: abra o arquivo, troque o número (é uma fração —
16% = `0.16`) e salve. Já vale no próximo diagnóstico rodado, sem reiniciar
nada nem precisar de mim. Isso vale só pro **Motor de Diagnóstico**, que é
quem calcula margem por canal; o Motor de Mensalidade hoje não tem essa
análise por canal. Muitas dessas taxas variam por categoria de produto e
volume de vendas — os números acima são o ponto médio de faixas de
pesquisa, um ponto de partida, não a taxa exata garantida de nenhum canal;
sempre vale confirmar a tabela oficial/atual antes de fechar um
diagnóstico real.

**Canal que o cliente usa mas não está nesta lista?** Desde 05/09/2026 o
cliente pode declarar qualquer canal, mesmo que a gente nunca tenha
cadastrado (pedido do analista: "o público que vou atender é só a galera
do e-commerce, então tenho que ter o máximo de opções possível [...] se
não for nenhum dos que a gente citou, o próprio cliente tem que
declarar") — o motor **nunca descarta** um canal desconhecido, ele entra
no cálculo exatamente com o nome que o cliente usou, só que sem taxa de
referência automática (considerado 0% até alguém informar a taxa real).

**Isso é 100% automático — ninguém digita nada na mão por cliente.**
Pipeline é assíncrono e de alto volume (correção 05/09/2026, pedido
explícito do analista: "é q ta é td automatico e assincrono, quando tiver
uma alta demanda como é q eu vou configurar manualmente?"), então a fonte
da taxa de um canal customizado é **o próprio formulário do cliente**, não
um parâmetro que o analista preenche depois. O fluxo completo:

1. O **formulário do cliente** (fora deste repositório — quem construir a
   tela do formulário precisa seguir este contrato de chaves) manda:
   - `q9_canais`: lista dos canais que o cliente marcou (conhecidos ou
     não);
   - `q9_faturamento_por_canal`: quanto cada canal de `q9_canais` faturou
     no período — **obrigatório pra cada canal marcado**, é o que permite
     calcular margem por canal;
   - `q9_canais_outros` (opcional): lista de canais fora da nossa lista
     conhecida, cada um como `{"nome": "...", "faturamento": ...,
     "taxa": ...}` — `taxa` é opcional, porque o cliente pode não saber a
     comissão exata do canal dele.
2. A **IA Extratora** (`dp-01/tratamento/extratora.py`) lê essas respostas
   e preenche `faturamento_por_canal` (todo canal, sempre) e
   `taxas_canais_declaradas` (só os canais em que o cliente informou a
   taxa — nunca inventa um número que não veio do formulário).
3. A **IA de Limpeza** (`dp-01/tratamento/limpeza.py`) repassa isso pronto
   em `dados_limpos['input_data']['channel_fees_customizadas']`.
4. O **`app.py`** (`_rodar_motor_diagnostico`) pega esse dicionário
   automaticamente e faz o *merge* com `config/taxas_canais.json` — só o(s)
   canal(is) declarado(s) pelo cliente é(são) sobrescrito(s), os outros
   continuam na taxa de referência normal. Nenhum humano participa desse
   passo.

Isso substitui o parâmetro manual `taxas_canais_customizadas` de
`PipelineSAF.processar_cliente()` como caminho **principal** — ele continua
existindo, mas agora serve só como **correção pontual** (ex.: uma
negociação especial de taxa com o Mercado Livre pra um cliente específico,
decidida por um humano depois, não algo que escale por cliente):

```python
resultado = pipeline.processar_cliente(
    tipo_produto="Diagnóstico",
    respostas_formulario={...},  # já traz q9_canais / q9_faturamento_por_canal / q9_canais_outros
    arquivos_info=[...],
    taxas_canais_customizadas={"Mercado Livre": 0.11},  # opcional — só pra correção manual pontual
)
```

Os dois caminhos fazem *merge* entre si — se o `taxas_canais_customizadas`
manual e o formulário do cliente declararem o mesmo canal, o manual vence
(é tratado como uma correção deliberada por cima do que veio automático).

Cadastrar um canal em `config/taxas_canais.json` (e em `SalesChannel`, em
`dp-01/motores/motor diagnostico/financial_engine_models.py`) continua
valendo a pena quando for um canal que vários clientes usam — poupa o
cliente de ter que informar a taxa dele toda vez — mas **nunca é
obrigatório** pra um canal funcionar; é só uma conveniência.

## 📝 Documentação

Ver documentos adicionais:
- SETUP_COMPLETO.md
- COMO_FUNCIONA_TRATAMENTO_COM_CLAUDE.md
- ATUALIZACOES_CODIGO.md

## 🎉 Pronto!

Sistema 100% funcional e com Claude integrado! 🚀

## 🛠️ Correções da auditoria (04–06/09/2026)

Uma auditoria cruzada (código Python vs. planilhas Google de referência,
caso de teste "Loja Premium Test", Abril/2026) encontrou e corrigiu os
seguintes problemas neste repositório:

1. **`financial_engine.py` e `monthly_engine.py` (raiz) não funcionavam.**
   Os módulos de apoio só existiam em `dp-01/motores/...`. Corrigido com um
   bootstrap de `sys.path` no topo dos dois arquivos.
2. **`test_tratamento.py` apontava para um caminho inexistente**
   (`/home/claude/departamento`). Corrigido para resolver
   `dp-01/tratamento` de forma relativa ao próprio arquivo.
3. **Motor de Mensalidade não tinha alerta de LTV:CAC.** Calculava
   `ltv_cac` mas nunca comparava a nenhum limite. Adicionados os alertas
   M4/M5, espelhando as mesmas regras do Motor de Diagnóstico.
4. **Alertas de vendas (S1, S4) disparavam com dados vazios.** Se o
   analista não preenchia a Inteligência de Vendas, `recurring_pct` e
   `best_channel_margin_pct` ficavam em 0.0 por padrão, disparando os
   alertas como se fossem um problema real. Agora só avaliam quando há
   evidência de que os dados foram informados.
5. **Referências a `summary.summary` (código morto).** Existiam em
   `financial_engine.py` e `financial_engine_diagnostic.py`, protegidas por
   `hasattr` (nunca davam erro, mas nunca preenchiam o campo pretendido —
   o semáforo da margem de contribuição). Corrigido para usar
   `get_contribution_margin_traffic_light(...)`.
6. **Contagem de alertas incorreta na documentação.** Motor de Diagnóstico
   tinha 13 alertas (não 15); Motor de Mensalidade tinha 15 (13 + os 2
   novos de LTV:CAC). Motor de Diagnóstico agora tem 14 (13 + o novo R1 de
   retenção, item 9 abaixo).
7. **Modelo Claude desatualizado** (`claude-3-5-sonnet-20241022`) em
   `extratora.py`, `fiscal_dados.py` e `limpeza.py`, atualizado para
   `claude-sonnet-5`.
8. **Fórmula de LTV Simplificado incorreta no Python.** `ltv_simplified`
   era calculado como `avg_ticket × avg_repurchase_rate × retention_rate`,
   misturando uma contagem de recompras (`avg_repurchase_rate`, ex.: 1.5)
   com uma probabilidade de retenção (`retention_rate`, ex.: 30%) sem
   nenhum componente de tempo — o resultado não era um "valor vitalício"
   de verdade (para o caso de teste, dava R$106,88 e LTV:CAC = 1,34x,
   soando como risco quando não era). Corrigido para a fórmula padrão de
   LTV simplificado, igual à planilha de referência (CONFIG!B41/B42):
   `Ticket Médio × Frequência de Recompra/Ano × Anos de Retenção`. Os
   campos `avg_repurchase_rate`/`retention_rate` em `ConfigParameters` (e
   no dicionário de config do Motor de Mensalidade) foram renomeados para
   `repurchase_frequency_per_year`/`retention_years` (padrão 2.0/2.0, os
   mesmos valores da planilha). Para o caso de teste isso muda o resultado
   de LTV de R$106,88 para R$950,00 e de LTV:CAC de 1,34x para 11,9x —
   fazendo o alerta M4 (LTV:CAC em risco) deixar de disparar, porque o
   valor antigo era artificialmente baixo.
9. **Novidade (não é bug corrigido, é funcionalidade nova): Categoria do
   negócio (A-E) usada de verdade nos dois motores.** Antes a Categoria era
   só um campo manual em `ConfigParameters`/config, sem nenhum efeito nos
   cálculos — e o alerta de recorrência (S1, Motor de Mensalidade) usava um
   piso fixo de 30% pra qualquer cliente. Agora: (a) a Categoria é
   **derivada automaticamente nos dois motores** (Diagnóstico: uma vez por
   período analisado; Mensalidade: todo mês) a partir do ticket médio e da
   margem de contribuição do próprio cliente — sem nenhuma pergunta nova no
   formulário (`derive_business_category()`, uma versão em cada motor); (b)
   cada Categoria tem seu próprio piso mínimo de recorrência (12% a 45%,
   baseado em pesquisa de mercado de taxa de recompra por ticket
   médio/nicho — Prax Analytics, Rivo, Flawless Magazine), usado pelo novo
   alerta R1 do Motor de Diagnóstico e pelo S1 (recalibrado) do Motor de
   Mensalidade; (c) o S1 agora também distingue frequência baixa
   **sustentada** (3 meses seguidos abaixo do piso) de uma queda pontual de
   um único mês. R1 e o campo `recurring_customers_pct` são opcionais —
   sem esse dado, nenhum alerta de retenção é gerado no Motor de
   Diagnóstico, igual ao cuidado já tomado no S1 (Motor de Mensalidade)
   pra não confundir "sem dado" com "0% de recorrência".
10. **Limpeza do Departamento de Tratamento.** A IA Extratora parou de
    pedir pra Claude "chutar" uma Categoria (A-E) durante a extração do
    formulário — isso nunca mais era usado depois que a Categoria passou a
    ser derivada automaticamente (item 9). De quebra, corrigido um bug
    latente: as chaves do JSON de "cliente" no prompt (`periodo`,
    `aliquota`) não batiam com os nomes de campo reais de `DadosCliente`
    (`periodo_analisado`, `aliquota_impostos`) — a primeira chamada real à
    API quebraria em `DadosCliente(**dados['cliente'])`. Também removido o
    campo `nicho_produto` (não usado por nenhum motor; a ideia de regras
    por nicho foi descartada em favor da Categoria automática).
11. **Novidade (não é bug corrigido, é departamento novo): Departamento de
    Produção (`dp-02/producao/`).** Recebe o `export_to_dict()` de qualquer
    um dos dois motores e gera o texto do relatório PDF + roteiro de vídeo,
    seguindo os 4 guias da Gem fornecidos pelo analista (Relatório PDF e
    Roteiro de Vídeo — um par pro Diagnóstico, um pro Mensalidade), com
    revisão automática pela IA Fiscal (checklist de 7 blocos do Guia da Gem
    Fiscal) antes de considerar pronto pro cliente. Ver seção **Departamento
    de Produção** acima.
12. **Novidade (não é bug corrigido, é departamento novo): Departamento de
    Edição (`dp-03/edicao/`).** Pega o relatório + roteiro já aprovados pela
    Produção (dp-02) e monta os entregáveis finais de verdade — PDF e vídeo
    MP4 — na identidade visual do Guia de Marca, com uma IA Fiscal de
    Produção final (checagem determinística de completude/estouro de texto
    + revisão de coerência por Claude) antes de considerar pronto pro
    cliente. Ver seção **Departamento de Edição** acima.
13. **`export_to_dict()` do Motor de Mensalidade exportava só 2 dos 4
    comparativos financeiros, e um deles com a chave errada** (auditoria
    05/09/2026, encontrado ao implementar o gráfico real dos slides —
    ver item acima). `MonthlySummary` tinha `revenue_comparative`,
    `margin_comparative` (Margem de Contribuição) e `profit_comparative`
    (Lucro Líquido), mas faltava um 4º campo pro comparativo de Margem
    Líquida (%) — ele já era calculado em `monthly_engine.py` mas se
    perdia, nunca chegava a lugar nenhum. E o `profit_comparative` (Lucro
    Líquido em R$) estava sendo exportado sob a chave `'profit_margin'`,
    nome que sugeria ser a Margem Líquida (%) — quando na verdade era outro
    indicador. Corrigido em `dp-01/motores/motor mensalidade/` (e espelhado
    no `monthly_engine.py` da raiz): adicionado o campo
    `profit_margin_comparative` em `MonthlySummary`, populado corretamente,
    e `export_to_dict()` agora exporta os 4 indicadores da tabela do bloco
    COMPARATIVO FINANCEIRO (`revenue`, `contribution_margin_pct`,
    `profit_margin_pct`, `profit_net`), cada um já com `variation_pct`
    pronta pro `[▲/▼]` do roteiro.
14. **Bloco de Marketing tratava "falta o CAC" como "falta tudo"**
    (auditoria 05/09/2026 — o campo de marketing é opcional no formulário e
    o público é leigo, então é comum vir incompleto). Corrigido em
    `dp-02/producao/templates.py`: os blocos MARKETING (Diagnóstico) e
    CLIENTES E MARKETING (Mensalidade), tanto no relatório quanto no
    roteiro, agora tratam 3 estados — sem nenhum dado de ads, com ROAS/%Ads
    mas sem CAC (número de novos clientes via ads ausente), e com tudo —
    em vez de descartar o ROAS real só porque faltou o CAC.
15. **`test_tratamento.py` não tinha tratamento de falha de API, ao
    contrário de `test_producao.py`/`test_edicao.py`** (auditoria
    05/09/2026 — o próprio docstring de `test_producao.py` já dizia que
    `test_tratamento.py` capturava a falha esperada sem
    `ANTHROPIC_API_KEY`, mas isso nunca tinha sido implementado: o teste
    terminava com traceback não tratado e exit code 1). Corrigido com o
    mesmo padrão try/except dos outros dois testes.
16. **`.env.example` e `.gitignore` citados no README mas inexistentes no
    repositório.** Adicionados os dois — `.env.example` lista
    `ANTHROPIC_API_KEY` (obrigatória) e `ELEVENLABS_API_KEY`/
    `ELEVENLABS_VOICE_ID` (opcionais, cai em modo placeholder sem elas).
17. **Produto "Cohort" removido (confirmado com o analista, 05/09/2026: não
    vai existir).** Existia como um terceiro valor em `TipoProduto`
    (`dp-01/tratamento/models.py`) e um branch em `limpeza.py` que nunca
    saiu do estágio de stub (`'status_limpeza': 'TODO'`) — sem motor, sem
    templates de relatório/roteiro, sem ícones no dp-03. Removidos o valor
    do enum, o branch e o método stub. Também removida, dos dois motores
    (`financial_engine_diagnostic.py`, Diagnóstico e Mensalidade), a frase
    do insight de LTV:CAC que recomendava "utilize a planilha de Cohort" —
    seria uma recomendação real pro cliente apontando pra um produto
    inexistente.
18. **Criado `app.py` (05/09/2026) — orquestrador único ligando dp-01 →
    motor → dp-02 → dp-03.** Até então cada departamento só tinha sido
    testado isoladamente (`test_tratamento.py`/`test_producao.py`/
    `test_edicao.py` forjam à mão o dado de entrada do departamento
    seguinte) — nenhum teste tinha instanciado o motor de verdade a partir
    da saída real de `dp-01/tratamento/limpeza.py`. Construir `app.py`
    (ver `test_app.py`) expôs 4 bugs de integração até então invisíveis,
    todos corrigidos:
    - `limpeza.py::_limpar_para_diagnostico()` incluía uma chave `'year'`
      que não existe em `ConfigParameters` — `ConfigParameters(**config)`
      quebrava com `TypeError` pra **qualquer** cliente Diagnóstico.
      Removida; `analysis_period` (campo obrigatório, nunca preenchido)
      adicionado no lugar, em `config` e em `input_data`.
    - `cliente.regime_tributario` nunca chegava ao motor de Diagnóstico —
      ficava sempre no default (Simples Nacional), mesmo pra clientes
      MEI/Lucro Presumido. Corrigido (com fallback seguro se o texto não
      bater com nenhum `TaxRegime` conhecido).
    - `FinancialInput.channel_revenues` exige chaves `SalesChannel` (enum);
      a Limpeza sempre produziu chaves de texto livre (ex.: `"Mercado
      Livre"`) — na prática nunca dava erro porque `faturamento_por_canal`
      nunca foi populado pela Extratora (campo sempre vazio), mas quebraria
      no dia em que alguém preenchesse esse campo. `app.py` converte pro
      enum, ignorando com aviso (não exceção) qualquer canal não
      reconhecido.
    - **Mensalidade perdia 4 campos coletados pela Extratora** (devoluções,
      novos clientes via ads, PMR, PMP) — `limpeza.py::_limpar_para_mensalidade()`
      parava em `ads_investment`. Na prática isso zerava sempre a receita
      líquida de devoluções e sempre o CAC/LTV da Mensalidade, mesmo
      quando o cliente informava esses dados. Corrigido.
19. **Cópia órfã e desatualizada de `financial_engine*.py` dentro de
    `dp-01/motores/motor mensalidade/` (encontrada ao construir `app.py`).**
    As 4 arquivos do Motor de Diagnóstico (`financial_engine.py`,
    `financial_engine_models.py`, `financial_engine_calculator.py`,
    `financial_engine_diagnostic.py`) existiam duplicados, sem uso, dentro
    da pasta do Motor de Mensalidade — cópia pré-correção de 04/09/2026
    (sem a derivação automática de Categoria, por exemplo), citada só em
    comentários (nunca importada por `monthly_engine*.py`). Inofensiva
    enquanto nada colocava as duas pastas de motor no mesmo `sys.path` ao
    mesmo tempo — exatamente o que `app.py` precisa fazer, e nesse caso a
    pasta errada acabava na frente e o Diagnóstico rodava silenciosamente
    a versão velha. Arquivos órfãos removidos.
20. **Taxas de canal (Mercado Livre, Shopee, etc.) viraram configuráveis
    sem código (pedido do analista, 05/09/2026).** Não era bug — era um
    dicionário Python fixo (`ConfigParameters.channel_fees`, em
    `financial_engine_models.py`) — mas atualizar uma taxa exigia editar
    esse arquivo, e são números que os marketplaces reajustam de tempos em
    tempos. Movido pra `config/taxas_canais.json` (ver seção
    "Configuração" acima); o motor carrega esse arquivo sozinho, com
    fallback pros valores antigos se o arquivo sumir ou vier corrompido —
    nunca quebra. Aproveitado pra adicionar `Nuvemshop` como canal (não
    existia no `SalesChannel` antes).
21. **Canal de venda fora da lista conhecida deixou de ser descartado
    (pedido do analista, 05/09/2026).** Antes, `app.py` simplesmente
    ignorava (com aviso) qualquer canal que o cliente declarasse e que não
    batesse com nenhum `SalesChannel` — o faturamento daquele canal
    desaparecia da análise de "Canais". Agora ele entra igual, com o nome
    exato que o cliente usou, só que com taxa 0% até alguém declarar a
    real (via o novo parâmetro `taxas_canais_customizadas` de
    `PipelineSAF.processar_cliente()`, que vira `channel_fees_custom` no
    motor). Também expandido `SalesChannel` com ~17 canais novos comuns em
    e-commerce brasileiro (Magalu, Americanas, Casas Bahia, Shein,
    AliExpress, Carrefour, Dafiti, Kabum, Netshoes, Elo7, Enjoei, OLX,
    VTEX, Tray, Loja Integrada, WooCommerce, Wix) — ver seção
    "Configuração" acima.
22. **`FinancialInput.channel_fees_custom` substituía a tabela de taxas
    inteira em vez de sobrepor (encontrado ao testar a correção nº 21).**
    `valid_data.channel_fees = input_data.channel_fees_custom or
    self.config.channel_fees.copy()` — informar a taxa de UM canal
    customizado apagava as taxas de referência de TODOS os outros canais
    do cliente (Mercado Livre, Shopee, etc. viravam 0%). Corrigido pra
    merge (`{**self.config.channel_fees, **(input_data.channel_fees_custom
    or {})}`, em `financial_engine_calculator.py`) — só o(s) canal(is)
    informado(s) é(são) sobrescrito(s).
23. **Os dois shims de raiz (`financial_engine.py`, `monthly_engine.py`)
    eram cópias inteiras do orquestrador, não shims de verdade — e isso já
    tinha causado bug antes.** Cada um repetia a classe inteira do motor
    (não só um bootstrap de `sys.path` como o comentário original
    afirmava), então uma correção feita só na cópia "oficial"
    (`dp-01/motores/...`) não chegava em quem importava
    `from financial_engine import ...`/`from monthly_engine import ...` da
    raiz — exatamente como o README e o "Uso Rápido" sempre instruíram
    fazer. Isso já tinha exigido replicar manualmente, numa sessão
    anterior, a correção do comparativo de Margem Líquida da Mensalidade
    nas duas cópias; mordeu de novo ao testar a correção nº 21 (o fix de
    canal customizado só existia na cópia oficial). Os dois arquivos agora
    carregam o módulo real por caminho (`importlib.util`, sob um nome
    interno diferente pra não colidir com o próprio nome do arquivo em
    `sys.modules`) e reexportam os símbolos — só existe uma implementação
    de verdade de cada motor a partir de agora.
24. **Canal customizado exigia um parâmetro manual (`taxas_canais_customizadas`)
    por cliente — não escala num pipeline automático/assíncrono de alto
    volume (correção da correção nº 21, pedido explícito do analista,
    05/09/2026: "é q ta é td automatico e assincrono, quando tiver uma alta
    demanda como é q eu vou configurar manualmente?").** A correção nº 21
    resolvia o crash/perda de dado, mas ainda exigia um humano digitando a
    taxa na chamada de `processar_cliente()` — inviável em alto volume.
    Também descoberto no processo: o faturamento POR CANAL nunca era
    extraído de verdade (o campo existia em `DadosFinanceirosTratados` mas
    ficava sempre vazio — a Extratora nunca pedia isso a Claude). Corrigido
    de ponta a ponta, sem nenhum passo manual: `DadosFinanceirosTratados`
    (`dp-01/tratamento/models.py`) ganhou `taxas_canais_declaradas`; o
    prompt da IA Extratora (`extratora.py::_montar_prompt_extracao`) passou
    a pedir `faturamento_por_canal` (a partir de `q9_faturamento_por_canal`
    no formulário) e `taxas_canais_declaradas` (a partir de
    `q9_canais_outros`, só quando o cliente informa a taxa — nunca
    inventada); `IALimpeza._limpar_para_diagnostico()` repassa isso em
    `channel_fees_customizadas`; e `app.py::_rodar_motor_diagnostico()`
    aplica esse dicionário automaticamente, fazendo merge com o
    `taxas_canais_customizadas` manual (que passa a ser só uma correção
    pontual opcional, não o caminho principal). Ver seção "Configuração"
    acima para o contrato de chaves do formulário (`q9_canais`,
    `q9_faturamento_por_canal`, `q9_canais_outros`) e
    `test_tratamento.py` para os testes sem API deste fluxo.
25. **Bug crítico: TODA extração real via API quebraria no primeiro campo
    (encontrado ao escrever o teste sem API da correção nº 24 — nunca
    tinha sido pego porque não havia teste que reproduzisse o formato
    exato que o prompt pede).** O prompt da IA Extratora
    (`extratora.py::_montar_prompt_extracao`) instrui Claude a devolver
    `"qualidade": "EXATO"` (maiúsculas — é o texto literal do JSON de
    exemplo no prompt), mas `QualidadeDado(...)` é chamado pelo *value* do
    enum, que é uma string capitalizada em português — `"Exato"` (ver
    `models.py`). `"EXATO" != "Exato"`, então `QualidadeDado("EXATO")`
    sempre levantava `ValueError: 'EXATO' is not a valid QualidadeDado` —
    ou seja, a primeira chamada real à API sempre quebraria em
    `_montar_resultado_tratamento()`, no primeiro campo (`receita_bruta`).
    Corrigido com um parser (`parsear_qualidade()`, dentro de
    `_montar_resultado_tratamento()`) que aceita tanto o *value* do enum
    (`"Exato"`, case-insensitive) quanto o *nome* do membro (`"EXATO"`, o
    que o prompt de fato pede), caindo em `AUSENTE` só se vier algo
    irreconhecível — nunca mais quebra o tratamento inteiro por causa de
    maiúscula/minúscula.
26. **Diagnóstico Comparativo (Guia Operacional 5.1) nunca tinha sido
    implementado — só existia como texto no guia antigo (pedido explícito
    do analista, 06/09/2026: "essas perguntas sobre expectativas do
    cliente [...] vai comparar com calculo do motor que é a realidade, e
    vai explicar 'segundo a sua resposta no formulario vc fatura x mas
    naverdade é y' [...] mas isso tem q ser feito com cuidado pra n
    parecer um sermão, pq o intuito é trazer clareza").** As respostas
    subjetivas da Seção 6 do formulário de Diagnóstico (o que o cliente
    *acredita* sobre o próprio negócio — se acha que está lucrando, qual
    canal acha melhor, quanto gostaria de tirar de pró-labore, etc.) eram
    extraídas por nenhuma parte do sistema; não havia como a Produção
    cruzar "o que o cliente acredita" com "o que os dados realmente
    mostram". Implementado de ponta a ponta, com uma regra de separação
    absoluta (a mesma que já vale pro resto da Seção 6, Guia Operacional
    3.1): percepção subjetiva NUNCA entra no motor de cálculo.
    - `dp-01/tratamento/models.py`: novo dataclass `PercepcoesCliente`
      (`percepcao_faturamento`, `acha_que_esta_lucrando`,
      `pro_labore_desejado`, `canal_percebido_como_melhor`,
      `sabe_produto_mais_lucrativo`, `objetivo_com_diagnostico`,
      `maior_duvida_ou_preocupacao`, `outras_percepcoes` como catch-all) +
      `tem_alguma_percepcao()`; campo novo em `ResultadoTratamento`.
    - `dp-01/tratamento/extratora.py`: prompt de extração ganhou o bloco
      `"percepcoes_cliente"` no schema JSON (com regra explícita de nunca
      inventar — usar `null` quando o cliente não respondeu) e
      `_montar_resultado_tratamento()` parseia isso num `PercepcoesCliente`.
    - `dp-01/tratamento/limpeza.py`: `_limpar_para_diagnostico()` repassa
      `percepcoes_cliente` como chave-irmã de `input_data` (fora dele, de
      propósito — o motor de cálculo nunca a vê). `_limpar_para_mensalidade()`
      não foi alterado: a Mensalidade não tem Seção 6 (não há formulário
      novo todo mês, ver `GUIA_DO_FORMULARIO_DIAGNOSTICO_E_MENSALIDADE.md`).
    - `app.py`: repassa `dados_limpos["percepcoes_cliente"]` (só quando
      `tipo_produto == "Diagnóstico"`) pro `DepartamentoProducao.processar()`.
    - `dp-02/producao/producao.py`, `relatorio_roteiro.py`,
      `fiscal_relatorio.py`: `percepcoes_cliente` passou a ser parâmetro
      opcional em toda a cadeia (geração de relatório, geração de roteiro,
      e revisão fiscal de ambos). Quando ausente/vazio, nada muda — gera
      normalmente, sem forçar nenhuma comparação (nunca é tratado como
      erro ou dado faltando).
    - `dp-02/producao/templates.py`: novo bloco `VOICE_RULES_COMPARATIVO`
      (formato da comparação, frases proibidas vs. preferidas, "no máximo
      1-2 por entrega", "nunca inventar", tom de clareza e não de correção
      — alinhado ao guia de marca: "honesta mesmo quando o número dói" +
      "nunca faz o cliente se sentir burro por não saber"), referenciado
      na Página 2 do relatório e no Bloco 1 do roteiro (onde o gancho cabe
      naturalmente) e injetado só quando há percepção declarada. Checklist
      da Gem Fiscal (`FISCAL_BLOCO_4_VOZ_ESCRITA`) ganhou dois itens: tom
      de sermão (🟠 Ajuste) e comparação inventada/com número errado
      (🔴 Bloqueador).
    - Prompt da Gem Fiscal (`fiscal_relatorio.py::_montar_prompt`) recebeu
      uma seção nova deixando explícito que uma divergência entre a crença
      declarada do cliente e `dados_motor` NÃO é erro — é o propósito da
      seção — só citar uma crença não declarada, comparar com número
      errado ou usar tom de correção é que seria.
    - Testes sem API: `test_tratamento.py` ganhou
      `teste_percepcoes_cliente_extracao_e_limpeza_sem_api()` (extração +
      isolamento do `input_data`); `test_producao.py` ganhou
      `teste_diagnostico_comparativo_no_prompt_sem_api()` (confirma que o
      bloco de comparação aparece/desaparece do prompt conforme há ou não
      percepção declarada).
27. **Auditoria "sistema digestivo" (06/09/2026, pergunta direta do
    analista: "quando tiver o formulário de verdade, o sistema tá
    preparado pra digerir?") — dois problemas reais encontrados, ambos
    corrigidos.**
    - **Bug crítico (nunca exercitado por nenhum teste): a chamada real
      pra `IAFiscalDados.validar_extracao()` sempre quebraria.**
      `DepartamentoTratamento.processar_cliente()` (dp-01/tratamento/__init__.py)
      sempre chamou esse método passando `dados_originais_formulario=` e
      `dados_originais_arquivos=` — mas a assinatura de
      `validar_extracao()` só aceitava `resultado_extracao`. Assim que a
      IA Extratora tivesse sucesso de verdade (ANTHROPIC_API_KEY
      configurada), a Etapa 2/3 (Fiscal de Dados) quebraria na hora com
      `TypeError: unexpected keyword argument`, derrubando o pipeline
      inteiro antes da Limpeza — nunca pego porque, sem chave de API
      configurada neste ambiente, a Extratora já falha ANTES desta
      chamada ser alcançada. Corrigido em `fiscal_dados.py`: a assinatura
      agora aceita os dois parâmetros e — já que a função da IA Fiscal de
      Dados é justamente comparar extraído vs. original — eles passaram a
      ser usados de verdade no prompt (antes, o prompt só mostrava o
      resultado já extraído, nunca o formulário/arquivos originais pra
      comparar contra, o que tornava boa parte do checklist de 9 pontos
      impossível de aplicar).
    - **`conteudo_arquivos` era um parâmetro morto — o conteúdo real de um
      arquivo enviado pelo cliente nunca chegava à IA Extratora.** A
      assinatura de `extrair_dados()`/`_montar_prompt_extracao()`
      (extratora.py) sempre teve um parâmetro `conteudo_arquivos: Dict[str,
      str]`, mas ele nunca era referenciado dentro do prompt — e nem
      `DepartamentoTratamento.processar_cliente()` nem `app.py::processar_cliente()`
      sequer o repassavam. Na prática, a Regra Absoluta nº 1 do prompt
      ("Hierarquia de fontes: Arquivo oficial > Formulário") nunca existiu
      de verdade: só nome/formato/tamanho do arquivo chegavam a Claude
      (`arquivos_info`), nunca o conteúdo (o extrato/planilha em si) — um
      cliente podia anexar um CSV certinho que o sistema ia extrair os
      números só do formulário mesmo. Corrigido de ponta a ponta:
      `conteudo_arquivos` agora é repassado por todo o pipeline
      (`app.py` → `DepartamentoTratamento.processar_cliente()` →
      `IAExtratora.extrair_dados()`) e entra de verdade no prompt, um
      bloco por arquivo (`_montar_prompt_conteudo_arquivos`, com limite de
      tamanho por arquivo, pra um extrato gigante não estourar o prompt
      inteiro sozinho). Continua sem parser de binário — quem receber o
      upload no site precisa converter o arquivo pra texto antes de
      chamar o pipeline; isso só resolve o problema de o conteúdo, uma
      vez em texto, ter pra onde ir.
    - **De quebra**: os cortes cegos `[:2000]`/`[:1000]`/`[:3000]` que
      truncavam formulário/arquivos/resultado em silêncio (em
      `extratora.py` e `fiscal_dados.py`) agora usam um helper
      (`_truncar_com_aviso`) que deixa explícito, no próprio texto
      enviado a Claude, quantos caracteres foram cortados — pra ela tratar
      dado potencialmente incompleto como incerto em vez de ignorar o
      corte sem perceber (um formulário de 44 perguntas com respostas
      longas passa fácil de 2000 caracteres).
    - Testes sem API novos em `test_tratamento.py`:
      `teste_extratora_digere_conteudo_de_arquivo_sem_api()` (conteúdo
      real do arquivo aparece no prompt; ausência dele gera aviso
      explícito; truncamento vem com aviso) e
      `teste_fiscal_de_dados_aceita_e_usa_originais_sem_api()` (a
      assinatura corrigida não quebra mais com `TypeError`, e os
      originais realmente aparecem no prompt da Fiscal).

As planilhas Google de referência (Diagnóstico e Mensalidade) também
tinham bugs de fórmula no bloco de LTV/LTV:CAC (referência quebrada e
erro de fórmula, respectivamente) — corrigidos separadamente nas próprias
planilhas (não fazem parte deste repositório). A correção nº 8 acima é o
que alinhou a fórmula do Python à fórmula que a planilha sempre pretendeu
calcular.
