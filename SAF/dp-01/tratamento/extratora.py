"""
IA EXTRATORA COM GEMINI - Departamento de Tratamento (COMPLETO)
Extrai dados brutos do cliente usando Gemini para interpretar e estruturar
Segue 100% o GUIA_DA_GEM_DE_TRATAMENTO_DE_DADOS
"""

from .models import *
from google import genai
import json
import re
from datetime import datetime


class IAExtratora:
    """
    IA Extratora que REALMENTE usa Gemini para:
    1. Entender o formulário e arquivos
    2. Aplicar hierarquia de fontes
    3. Marcar qualidade de dados
    4. Estruturar no formato correto
    """
    
    def __init__(self):
        self.client = genai.Client()
        # CORREÇÃO (auditoria 04/09/2026): modelo antigo (2024) atualizado.
        self.model = "gemini-3.6-flash"
    
    def extrair_dados(
        self,
        tipo_produto: TipoProduto,
        respostas_formulario: Dict[str, Any],
        arquivos_info: List[Dict[str, Any]],
        conteudo_arquivos: Dict[str, str] = None
    ) -> ResultadoTratamento:
        """
        Usa CLAUDE para extrair e estruturar dados
        """
        
        print("[IA EXTRATORA] 🔍 Iniciando extração com Gemini...")
        
        # Montar prompt para Gemini
        prompt = self._montar_prompt_extracao(
            tipo_produto,
            respostas_formulario,
            arquivos_info,
            conteudo_arquivos
        )
        
        # Chamar Gemini
        try:
            response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(max_output_tokens=4000),
        )
            
            resultado_texto = response.text
            print("[IA EXTRATORA] ✅ Gemini respondeu")
            
            # Parsear JSON da resposta
            dados_extraidos = self._parsear_resposta_claude(resultado_texto)
            
            # Montar ResultadoTratamento
            return self._montar_resultado_tratamento(
                tipo_produto,
                dados_extraidos,
                respostas_formulario,
                arquivos_info
            )
            
        except Exception as e:
            print(f"[IA EXTRATORA] ❌ Erro: {e}")
            raise
    
    def _truncar_com_aviso(self, texto: str, limite: int) -> str:
        """
        CORREÇÃO (06/09/2026, auditoria "sistema digestivo — quando o
        formulário de verdade existir, o motor consegue digerir?"): o
        prompt cortava formulário/arquivos com `[:N]` cru, sem nenhum
        aviso — se o corte caísse no meio do JSON, o texto sumia em
        silêncio e a IA não tinha como saber que faltava conteúdo (um
        formulário de 44 perguntas com respostas longas passa fácil de
        2000 caracteres). Agora o corte fica explícito no texto enviado.
        """
        if len(texto) <= limite:
            return texto
        cortados = len(texto) - limite
        return (
            texto[:limite]
            + f"\n... [TRUNCADO — {cortados} caractere(s) a mais não enviados. "
              f"Se algum dado citado depender do que foi cortado, marque qualidade "
              f"ESTIMATIVA ou AUSENTE em vez de EXATO.]"
        )

    def _montar_prompt_conteudo_arquivos(
        self, arquivos: List[Dict[str, Any]], conteudo_arquivos: Dict[str, str]
    ) -> str:
        """
        CORREÇÃO CRÍTICA (06/09/2026, auditoria "sistema digestivo"):
        `conteudo_arquivos` era um parâmetro morto — existia na assinatura
        de `extrair_dados()`/`_montar_prompt_extracao()` desde sempre, mas
        NUNCA era usado dentro do prompt (nem `DepartamentoTratamento.
        processar_cliente()` nem `app.py::processar_cliente()` sequer o
        repassavam). Na prática, isso significa que o "arquivo oficial"
        citado na Regra Absoluta nº 1 ("Hierarquia de fontes: Arquivo
        oficial > Formulário") NUNCA existiu de verdade pro sistema — só
        o NOME/formato/tamanho do arquivo chegava até Claude
        (`arquivos_info`), nunca o conteúdo real (o extrato/planilha em
        si). Ou seja: hoje, um cliente podia anexar um CSV de vendas
        certinho que o sistema extraía os números só do formulário mesmo,
        ignorando o arquivo por completo.

        Corrigido: `conteudo_arquivos` (Dict[str, str], chave = mesmo
        "nome" usado em `arquivos_info`, valor = o CONTEÚDO já em texto do
        arquivo — CSV/planilha convertida em string, texto extraído de
        PDF, etc.) agora entra no prompt de verdade, um bloco por arquivo,
        cada um com seu próprio limite (evita um extrato gigante estourar
        o prompt inteiro sozinho). IMPORTANTE: este sistema continua sem
        nenhum parser de binário (não lê .xlsx/.pdf/.csv brutos) — quem
        chama `extrair_dados()` precisa converter o arquivo pra texto
        ANTES de chamar (é essa conversão texto-pronto que entra aqui).
        Sem `conteudo_arquivos`, o comportamento é o de sempre: só
        metadados do arquivo, extração baseada no formulário.
        """
        if not conteudo_arquivos:
            return "Nenhum conteúdo de arquivo disponível — extraia usando somente o formulário."

        nomes_conhecidos = {a.get('nome') for a in (arquivos or [])}
        blocos = []
        for nome, conteudo in conteudo_arquivos.items():
            aviso_nome = "" if nome in nomes_conhecidos else " (⚠️ não está na lista de arquivos_info — trate com cautela)"
            blocos.append(
                f"--- Arquivo: {nome}{aviso_nome} ---\n{self._truncar_com_aviso(str(conteudo), 15000)}"
            )
        return "\n\n".join(blocos)

    def _montar_prompt_extracao(
        self,
        tipo_produto: TipoProduto,
        formulario: Dict[str, Any],
        arquivos: List[Dict[str, Any]],
        conteudo_arquivos: Dict[str, str]
    ) -> str:
        """
        Monta prompt estruturado para Gemini.

        LIMPEZA (04/09/2026): o prompt não pede mais pra Claude "chutar" uma
        Categoria do negócio (A-E) — isso era um resquício de quando a
        Categoria era escolhida manualmente. Hoje ela é sempre derivada
        automaticamente pelos próprios motores (ticket médio + margem de
        contribuição, ver derive_business_category() em
        financial_engine_models.py / monthly_engine_models.py), então pedir
        isso aqui era trabalho desperdiçado — o valor nunca era usado.
        De quebra, corrigidas as chaves do JSON de "cliente" (periodo ->
        periodo_analisado, aliquota -> aliquota_impostos) pra baterem com os
        nomes de campo reais de DadosCliente — antes disso, a primeira
        chamada real à API (sem a chave de API, nunca tinha rodado de
        verdade neste ambiente) quebraria em
        `DadosCliente(**dados['cliente'])` com "unexpected keyword argument".

        NOVIDADE (05/09/2026, pedido do analista): "o público que vou
        atender é só a galera do e-commerce, então tenho que ter o máximo
        de opções possível [...] se não for nenhum dos que a gente citou,
        o próprio cliente tem que declarar" — e isso tem que fluir sozinho
        pelo pipeline automático/assíncrono, sem ninguém digitando taxa de
        canal na mão pra cada cliente (alto volume não permite). Antes, o
        formulário só perguntava QUAIS canais o cliente usa (`q9_canais`)
        — quanto cada canal faturou e a taxa de comissão nunca eram
        extraídos de verdade (campos que existiam na estrutura de dados
        mas ficavam sempre vazios). Adicionadas ao prompt e ao JSON de
        saída: `faturamento_por_canal` (finalmente preenchido, a partir de
        `q9_faturamento_por_canal` no formulário) e `taxas_canais_declaradas`
        (a partir de `q9_canais_outros` — canais fora da nossa lista
        conhecida, com a taxa que o próprio cliente informou, quando ele
        souber). Ver DadosFinanceirosTratados em models.py e o
        comentário de `taxas_canais_declaradas` lá.
        """

        return f"""
Você é a IA EXTRATORA do FinSpots.

TAREFA: Extrair dados financeiros seguindo o GUIA_DA_GEM_DE_TRATAMENTO_DE_DADOS.

REGRAS ABSOLUTAS:
1. Hierarquia de fontes: Arquivo oficial > Formulário exato > Formulário estimativa > Ausente
2. Marcar qualidade: EXATO | ESTIMATIVA | CALCULADO | AUSENTE
3. Declarar fonte de CADA campo
4. Nunca inventar dados
5. Sinalizar conflitos > 5%
6. Retornar JSON estruturado

DADOS RECEBIDOS:

📋 FORMULÁRIO:
{self._truncar_com_aviso(json.dumps(formulario, ensure_ascii=False, indent=2, default=str), 6000)}

📁 ARQUIVOS ENVIADOS (metadados — nome, formato, tamanho):
{self._truncar_com_aviso(json.dumps(arquivos, ensure_ascii=False, indent=2, default=str), 2000)}

📄 CONTEÚDO DOS ARQUIVOS (fonte OFICIAL — quando um valor vier daqui, use qualidade EXATO e prevaleça sobre o formulário em caso de conflito, ver Regra Absoluta 1):
{self._montar_prompt_conteudo_arquivos(arquivos, conteudo_arquivos)}

TIPO DE PRODUTO: {tipo_produto.value}

TAREFA:
1. Processar cada campo do formulário
2. Comparar com o CONTEÚDO DOS ARQUIVOS acima (se houver) — não só com os metadados
3. Aplicar hierarquia (arquivo > formulário)
4. Marcar qualidade de cada dado
5. Sinalizar conflitos
6. Retornar JSON EXATO neste formato (PREENCHA TODOS OS CAMPOS):

{{
  "cliente": {{
    "nome_loja": "valor",
    "periodo_analisado": "valor",
    "regime_tributario": "Simples Nacional|MEI|Lucro Presumido|Lucro Real",
    "aliquota_impostos": 0.04
  }},
  "dados_financeiros": {{
    "receita_bruta": {{"valor": 0, "qualidade": "EXATO", "fonte": "..."}},
    "devolucoes": {{"valor": 0, "qualidade": "EXATO", "fonte": "..."}},
    "cmv": {{"valor": 0, "qualidade": "EXATO", "fonte": "..."}},
    "custos_variaveis": {{"valor": 0, "qualidade": "CALCULADO", "fonte": "..."}},
    "custos_fixos": {{"valor": 0, "qualidade": "EXATO", "fonte": "..."}},
    "pro_labore": {{"valor": 0, "qualidade": "EXATO", "fonte": "..."}},
    "num_pedidos": {{"valor": 0, "qualidade": "EXATO", "fonte": "..."}},
    "ads_investment": {{"valor": 0, "qualidade": "EXATO", "fonte": "..."}},
    "novos_clientes_ads": {{"valor": 0, "qualidade": "EXATO", "fonte": "..."}},
    "pmr": {{"valor": 0, "qualidade": "EXATO", "fonte": "..."}},
    "pmp": {{"valor": 0, "qualidade": "EXATO", "fonte": "..."}},
    "faturamento_por_canal": {{
      "Nome do Canal 1": {{"valor": 0, "qualidade": "EXATO", "fonte": "..."}}
    }},
    "taxas_canais_declaradas": {{
      "Nome do Canal Fora Da Lista": {{"valor": 0.0, "qualidade": "ESTIMATIVA", "fonte": "..."}}
    }}
  }},
  "percepcoes_cliente": {{
    "percepcao_faturamento": "Crescendo|Estável|Caindo|Oscilando muito ou null se não respondeu",
    "acha_que_esta_lucrando": "resposta literal do cliente ou null",
    "pro_labore_desejado": 0.0,
    "canal_percebido_como_melhor": "nome do canal ou null",
    "sabe_produto_mais_lucrativo": "resposta literal ou null",
    "objetivo_com_diagnostico": "resposta literal ou null",
    "maior_duvida_ou_preocupacao": "texto livre ou null",
    "outras_percepcoes": {{
      "Pergunta curta (ex.: Como precifica)": "Resposta literal do cliente"
    }}
  }},
  "alertas": [],
  "status_final": "COMPLETO"
}}

REGRAS ESPECÍFICAS DE PERCEPÇÕES DO CLIENTE ("percepcoes_cliente", novidade 06/09/2026):
- Isto é DIFERENTE de "dados_financeiros" — são as respostas SUBJETIVAS
  do cliente sobre o próprio negócio (típico da Seção "Sobre o negócio"
  do formulário: se acha que fatura X, se acha que está lucrando, qual
  canal acha melhor, quanto gostaria de retirar de pró-labore, etc.).
- Estas respostas NUNCA são usadas pra calcular nada — só existem pra
  Produção comparar depois "o que o cliente acredita" com "o que os
  dados realmente mostram" (Diagnóstico Comparativo).
- "pro_labore_desejado" é o valor que o cliente GOSTARIA de retirar —
  não confundir com "pro_labore" em dados_financeiros, que é o valor
  REAL já retirado (são propositalmente dois campos diferentes).
- Regra absoluta: se o cliente não respondeu uma dessas perguntas, o
  campo fica `null` — NUNCA invente uma crença que ele não declarou. É
  perfeitamente normal (e não é erro) "percepcoes_cliente" vir inteiro
  vazio quando o formulário não tinha essa seção ou o cliente pulou.
- Qualquer outra resposta subjetiva relevante que não se encaixe nos
  campos acima (ex.: como o cliente precifica, se separa as finanças)
  vai em "outras_percepcoes" como pergunta curta → resposta, dentro do
  mesmo objeto "percepcoes_cliente".

REGRAS ESPECÍFICAS DE CANAIS DE VENDA (novidade 05/09/2026):
- "q9_canais" no formulário: lista dos canais que o cliente marcou (podem
  ser canais que já conhecemos, tipo Mercado Livre/Shopee, ou não).
- "q9_faturamento_por_canal" no formulário: quanto cada canal de q9_canais
  faturou no período — preencha "faturamento_por_canal" no JSON com UMA
  entrada por canal, usando EXATAMENTE o nome do canal como chave.
- "q9_canais_outros" no formulário (se vier): lista de canais que o
  cliente usa mas não estão na nossa lista conhecida, cada um com nome,
  faturamento e (opcionalmente) a taxa de comissão que o próprio cliente
  informou. Pra cada um: some o faturamento em "faturamento_por_canal"
  (mesma chave, nome do canal); SE E SÓ SE o cliente informou uma taxa
  (não deixe em branco/estimado se ele não disse), inclua também em
  "taxas_canais_declaradas" com a MESMA chave (nome do canal) — valor em
  fração (12% = 0.12). Se o cliente não informou taxa nenhuma pra esse
  canal, NÃO invente uma entrada em "taxas_canais_declaradas" pra ele —
  deixe de fora e ele fica com taxa 0% até alguém informar.
- Nunca invente nome de canal, faturamento ou taxa que não veio do
  formulário/arquivos — se um canal foi marcado em "q9_canais" mas não tem
  faturamento nenhum associado, marque "qualidade": "AUSENTE" com "valor": 0
  em vez de estimar um número.

COMECE!
"""
    
    def _parsear_resposta_claude(self, texto: str) -> Dict[str, Any]:
        """Extrai JSON da resposta do Gemini"""
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        else:
            raise ValueError("Gemini não retornou JSON válido")
    
    def _montar_resultado_tratamento(
        self,
        tipo_produto: TipoProduto,
        dados: Dict[str, Any],
        formulario: Dict[str, Any],
        arquivos: List[Dict[str, Any]]
    ) -> ResultadoTratamento:
        """Monta ResultadoTratamento COMPLETO a partir dos dados extraídos"""

        def parsear_qualidade(valor: Any) -> QualidadeDado:
            """
            CORREÇÃO CRÍTICA (05/09/2026, descoberta ao escrever
            teste_extracao_canais_customizados_sem_api() em
            test_tratamento.py): o prompt (_montar_prompt_extracao, acima)
            instrui a IA a devolver "qualidade" em MAIÚSCULAS — "EXATO",
            "ESTIMATIVA", "CALCULADO", "AUSENTE" (é literalmente o texto
            do JSON de exemplo no prompt). Só que QualidadeDado(...) chama
            o enum PELO VALUE, e os values são strings capitalizadas em
            português — "Exato", "Estimativa", "Calculado", "Ausente" (ver
            models.py). "EXATO" != "Exato", então `QualidadeDado("EXATO")`
            sempre levantava `ValueError: 'EXATO' is not a valid
            QualidadeDado` — ou seja, TODA chamada real à API (a IA
            seguindo o prompt à risca) quebraria aqui, sempre, no primeiro
            campo. Como nenhum teste deste arquivo rodava sem
            GEMINI_API_KEY reproduzindo o formato exato do prompt, isso
            nunca foi pego antes. Corrigido aceitando os dois formatos:
            o VALUE do enum ("Exato", case-insensitive) e o NOME do membro
            ("EXATO", o que o prompt de fato pede) — cai em AUSENTE se vier
            algo irreconhecível, em vez de quebrar o tratamento inteiro.
            """
            if isinstance(valor, QualidadeDado):
                return valor
            texto = str(valor or 'AUSENTE').strip()
            for membro in QualidadeDado:
                if membro.value.lower() == texto.lower():
                    return membro
            try:
                return QualidadeDado[texto.upper()]
            except KeyError:
                return QualidadeDado.AUSENTE

        cliente = DadosCliente(**dados['cliente'])
        
        alertas = [
            Alerta(
                tipo=a.get('tipo', 'outro'),
                severidade=a.get('severidade', 'INFO'),
                descricao=a.get('descricao', ''),
                localizacao=a.get('localizacao', '')
            )
            for a in dados.get('alertas', [])
        ]
        
        # Converter dados financeiros
        df = dados.get('dados_financeiros', {})
        
        # Helper para criar CampoTratado
        def campo(nome, key):
            data = df.get(key, {})
            return CampoTratado(
                nome_campo=nome,
                valor=data.get('valor', 0),
                qualidade=parsear_qualidade(data.get('qualidade', 'AUSENTE')),
                fonte=data.get('fonte', 'Não informado')
            )
        
        # NOVIDADE (05/09/2026): "faturamento_por_canal" e
        # "taxas_canais_declaradas" são dicts CHAVEADOS POR NOME DE CANAL
        # (não um campo fixo como os outros) — cada chave vira um
        # CampoTratado próprio, preservando qualidade/fonte por canal.
        def canais(chave: str, nome_prefixo: str) -> Dict[str, CampoTratado]:
            bruto = df.get(chave, {}) or {}
            return {
                nome_canal: CampoTratado(
                    nome_campo=f"{nome_prefixo} — {nome_canal}",
                    valor=info.get('valor', 0),
                    qualidade=parsear_qualidade(info.get('qualidade', 'AUSENTE')),
                    fonte=info.get('fonte', 'Não informado'),
                )
                for nome_canal, info in bruto.items()
            }

        dados_financeiros = DadosFinanceirosTratados(
            receita_bruta=campo('Receita Bruta', 'receita_bruta'),
            devolucoes=campo('Devoluções', 'devolucoes'),
            cmv=campo('CMV', 'cmv'),
            custos_variaveis=campo('Custos Variáveis', 'custos_variaveis'),
            custos_fixos=campo('Custos Fixos', 'custos_fixos'),
            pro_labore=campo('Pró-labore', 'pro_labore'),
            num_pedidos=campo('Número de Pedidos', 'num_pedidos'),
            ads_investment=campo('Investimento Ads', 'ads_investment'),
            novos_clientes_ads=campo('Novos Clientes Ads', 'novos_clientes_ads'),
            pmr=campo('PMR', 'pmr'),
            pmp=campo('PMP', 'pmp'),
            faturamento_por_canal=canais('faturamento_por_canal', 'Faturamento'),
            taxas_canais_declaradas=canais('taxas_canais_declaradas', 'Taxa declarada'),
        )

        # NOVIDADE (06/09/2026): percepções do cliente (Seção 6 do
        # formulário) — nunca entram em dados_financeiros/no motor, só em
        # PercepcoesCliente, pra Produção usar no Diagnóstico Comparativo
        # (ver comentário completo em models.py). "outras_percepcoes" já
        # vem como dict simples (pergunta -> resposta), sem CampoTratado —
        # aqui é opinião do cliente, não dado com qualidade/fonte.
        pc = dados.get('percepcoes_cliente', {}) or {}
        percepcoes_cliente = PercepcoesCliente(
            percepcao_faturamento=pc.get('percepcao_faturamento'),
            acha_que_esta_lucrando=pc.get('acha_que_esta_lucrando'),
            pro_labore_desejado=pc.get('pro_labore_desejado'),
            canal_percebido_como_melhor=pc.get('canal_percebido_como_melhor'),
            sabe_produto_mais_lucrativo=pc.get('sabe_produto_mais_lucrativo'),
            objetivo_com_diagnostico=pc.get('objetivo_com_diagnostico'),
            maior_duvida_ou_preocupacao=pc.get('maior_duvida_ou_preocupacao'),
            outras_percepcoes=pc.get('outras_percepcoes', {}) or {},
        )

        return ResultadoTratamento(
            tipo_produto=tipo_produto,
            cliente=cliente,
            formulario_respostas=[],
            arquivos_recebidos=[
                ArquivoRecebido(
                    nome_arquivo=a['nome'],
                    formato=a.get('formato', 'unknown'),
                    tamanho_mb=a.get('tamanho', 0),
                    data_recebimento=a.get('data', ''),
                    tipo_arquivo=a.get('tipo', 'outro'),
                    status_processamento='processado',
                )
                for a in arquivos
            ],
            mapeamento_canais=MapeamentoCanais(
                canais_declarados=formulario.get('q9_canais', []),
                canais_com_arquivo={},
                canais_sem_arquivo=[]
            ),
            dados_financeiros=dados_financeiros,
            alertas=alertas,
            campos_ausentes=[],
            status_final=dados.get('status_final', 'COMPLETO'),
            mensagem_status="Extração concluída com sucesso",
            timestamp=datetime.now().isoformat(),
            percepcoes_cliente=percepcoes_cliente,
        )
