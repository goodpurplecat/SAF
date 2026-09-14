"""
IA Extratora de Vendas - Motor de Mensalidade (upload de vendas por pedido)

NOVIDADE (auditoria 14/09/2026): extrai PEDIDOS BRUTOS (produto, cliente,
canal, valor) do arquivo que o cliente sobe no novo upload de vendas da
Mensalidade. Confirmado pelo analista: o formulário de vendas é
"praticamente igual ao do Diagnóstico, só que sem as perguntas de
identificação e expectativas (a Mensalidade já tem as metas) — só o
espaço de upload", e os dados brutos enviados são processados "que nem no
Diagnóstico", ou seja, pelo mesmo tipo de IA Extratora (Gemini) já usado
em dp-01/tratamento/extratora.py.

DIFERENÇA DELIBERADA, confirmada pelo analista ao escolher entre 3
caminhos possíveis para esta parte: a IA aqui SÓ estrutura os dados brutos
linha a linha (produto/cliente/canal/valor) — ela NUNCA calcula top
produtos, pior margem, canal líder ou recorrência. Isso continua sendo
código determinístico (sales_intelligence_calculator.py, na pasta do
Motor de Mensalidade), por fórmula fixa (MAX/MIN/soma/diferença de
conjuntos), nunca por estimativa de IA — essa divisão de trabalho é o que
reproduz em Python a mesma garantia de precisão que uma fórmula de
planilha (PROCV/SOMASE/MÁXIMO/MÍNIMO) sempre teve, mesmo lendo arquivo de
formato livre.

DIFERENÇA DE VOLUME em relação à IAExtratora original
(dp-01/tratamento/extratora.py): aquele formulário tem ~15-20 campos e
cabe inteiro num prompt só. Um export de vendas pode ter centenas ou
milhares de linhas — muito além do que um prompt único (e o limite de
max_output_tokens) suporta com segurança. Por isso este módulo divide o
conteúdo do arquivo em BLOCOS (ver _dividir_em_blocos) antes de mandar
pra Gemini, chama a IA uma vez por bloco, e concatena os pedidos
extraídos. Um bloco que falhar ao extrair levanta ErroExtracaoVendas —
NUNCA falha em silêncio, porque um pedido perdido muda o cálculo de top
produtos/margens/recorrência rio abaixo.

LIMITAÇÃO CONHECIDA (documentada, não escondida): assim como
IAExtratora, este sistema não lê binário — quem chama extrair_pedidos()
precisa converter o arquivo (xlsx/csv/pdf) pra texto ANTES de chamar
(mesma responsabilidade que app.py/dp-01/tratamento já tem hoje pro
Diagnóstico). E como a extração ainda passa por um modelo de linguagem
(não um parser de coluna fixa), ela é mais flexível pra aceitar qualquer
formato de export de canal, mas não tem 100% de garantia matemática linha
a linha como um parser de CSV com coluna fixa teria — esse é o
trade-off explícito que o analista escolheu (flexibilidade de leitura,
mantendo o CÁLCULO em si 100% determinístico).
"""

from typing import List, Dict, Any, Optional
import json
import re

from google import genai

from monthly_engine_models import OrderLine


class ErroExtracaoVendas(Exception):
    """
    Levantado quando um bloco de pedidos não pôde ser extraído/parseado.
    Nunca é engolido em silêncio — quem chama extrair_pedidos() decide o
    que fazer (ex.: marcar o relatório do mês como REVISAO_MANUAL_NECESSARIA,
    mesmo padrão já usado em dp-02/producao/producao.py pra outros erros
    de IA).
    """
    def __init__(self, bloco_numero: int, total_blocos: int, motivo: str):
        self.bloco_numero = bloco_numero
        self.total_blocos = total_blocos
        self.motivo = motivo
        super().__init__(
            f"Bloco {bloco_numero}/{total_blocos} do arquivo de vendas: {motivo}"
        )


class IAExtratoraVendas:
    """
    Extrai uma lista de OrderLine (monthly_engine_models.py) a partir do
    conteúdo (já em texto) de um arquivo de vendas enviado pelo cliente —
    planilha própria ou export baixado de canal (Mercado Livre, Shopee,
    Shopify, etc.). A saída desta classe alimenta diretamente
    sales_intelligence_calculator.calculate_sales_intelligence().
    """

    # Linhas de texto por bloco/chamada à IA. Número conservador de
    # propósito — poucas linhas por chamada custa mais chamadas, mas cada
    # chamada fica bem dentro do limite de saída (max_output_tokens),
    # evitando truncar pedidos no meio de um bloco grande. Ajustável se,
    # na prática, um formato de export específico permitir blocos maiores
    # sem estourar a saída.
    LINHAS_POR_BLOCO = 150

    def __init__(self):
        self.client = genai.Client()
        # Mesmo modelo do resto do sistema (ver extratora.py) — mantém um
        # único modelo pra toda a IA Extratora, diagnóstico e vendas.
        self.model = "gemini-3.6-flash"

    def extrair_pedidos(
        self,
        conteudo_arquivo: str,
        nome_arquivo: str,
        canal_default: Optional[str] = None,
    ) -> List[OrderLine]:
        """
        conteudo_arquivo: conteúdo do arquivo já convertido pra texto
            (CSV cru, ou texto extraído de XLSX/PDF) — mesma conversão que
            IAExtratora já exige de quem a chama (ver
            _montar_prompt_conteudo_arquivos em extratora.py).
        nome_arquivo: só pra identificar o arquivo em erros/logs — o
            cliente pode subir mais de um (ex.: um export por canal).
        canal_default: nome do canal a usar quando uma linha não tiver
            informação de canal própria (ex.: um export que já é 100%
            Mercado Livre não repete "Mercado Livre" em cada linha).
            Passe o canal do arquivo quando ele for conhecido de
            antemão (ex.: pelo nome do arquivo ou uma pergunta simples no
            upload — "de qual canal é este arquivo?").

        Levanta ErroExtracaoVendas se algum bloco não puder ser
        estruturado — nunca devolve uma lista "incompleta" sem avisar
        quem chamou.
        """
        blocos = self._dividir_em_blocos(conteudo_arquivo)
        pedidos: List[OrderLine] = []

        for i, bloco in enumerate(blocos, start=1):
            prompt = self._montar_prompt(bloco, canal_default)
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(max_output_tokens=8000),
                )
                linhas_json = self._parsear_resposta(response.text)
            except ErroExtracaoVendas:
                raise
            except Exception as e:
                raise ErroExtracaoVendas(i, len(blocos), f"Gemini falhou ou devolveu formato inválido ({e})")

            for linha in linhas_json:
                pedidos.append(OrderLine(
                    produto_id=str(linha.get('produto_id') or '').strip(),
                    produto_nome=str(linha.get('produto_nome') or '').strip(),
                    cliente_id=str(linha.get('cliente_id') or '').strip(),
                    canal=str(linha.get('canal') or canal_default or 'Não informado').strip(),
                    receita=float(linha.get('receita') or 0),
                    custo=float(linha.get('custo') or 0),
                    data=linha.get('data'),
                ))

        # Regra absoluta (mesma da IAExtratora original): nunca inventar
        # dado. Uma linha sem produto_id/cliente_id não entra na
        # agregação por produto/cliente com um ID vazio (isso juntaria
        # incorretamente todos os "sem ID" num único produto/cliente
        # fantasma) — é descartada e contada, não escondida.
        validos = [p for p in pedidos if p.produto_id and p.cliente_id]
        descartados = len(pedidos) - len(validos)
        if descartados:
            print(
                f"[IA EXTRATORA DE VENDAS] ⚠️ {descartados} linha(s) de "
                f"'{nome_arquivo}' descartada(s) por falta de produto_id/cliente_id "
                f"(nunca inventamos um ID pra encaixar a linha)."
            )

        return validos

    def _dividir_em_blocos(self, conteudo: str) -> List[str]:
        """
        Divide o conteúdo do arquivo em blocos de até LINHAS_POR_BLOCO
        linhas, preservando a primeira linha (cabeçalho, se houver) em
        todo bloco — assim cada chamada à IA continua sabendo o que cada
        coluna significa, mesmo processando só um pedaço do arquivo de
        cada vez.
        """
        linhas = [l for l in conteudo.splitlines() if l.strip() != ""]
        if not linhas:
            return []

        cabecalho = linhas[0]
        corpo = linhas[1:]

        if len(corpo) <= self.LINHAS_POR_BLOCO:
            return [conteudo]

        blocos = []
        for inicio in range(0, len(corpo), self.LINHAS_POR_BLOCO):
            pedaco = corpo[inicio:inicio + self.LINHAS_POR_BLOCO]
            blocos.append(cabecalho + "\n" + "\n".join(pedaco))
        return blocos

    def _montar_prompt(self, bloco: str, canal_default: Optional[str]) -> str:
        contexto_canal = (
            f'Se uma linha não tiver informação de canal explícita, use "{canal_default}" (é o canal deste arquivo).'
            if canal_default else
            'Se uma linha não tiver informação de canal, deixe "canal": null.'
        )
        return f"""
Você é a IA EXTRATORA DE VENDAS do FinSpots.

TAREFA: ler este trecho de um arquivo de vendas (planilha própria do
cliente ou export baixado de um canal como Mercado Livre, Shopee, Shopify
etc.) e estruturar CADA LINHA DE PEDIDO/ITEM VENDIDO em JSON. Você NÃO
calcula nada — nunca soma, nunca tira média, nunca decide "top produto"
ou "pior margem". Isso é feito depois por código, não por você. Sua única
tarefa é estruturar o que já está escrito no arquivo.

REGRAS ABSOLUTAS:
1. Uma entrada por item vendido (se um pedido tiver 2 produtos diferentes, são 2 entradas).
2. Nunca invente produto_id, cliente_id, receita ou custo que não esteja no texto.
3. Se não houver um código/SKU único de produto, use o nome exato do produto como produto_id (produtos com nome idêntico são tratados como o mesmo produto).
4. Se não houver identificador único de cliente (e-mail, ID do comprador, CPF/telefone mascarado etc.), NÃO invente um — descarte a linha em vez de gerar um ID falso.
5. {contexto_canal}
6. "custo" só entra se o arquivo trouxer isso explicitamente (custo do produto, CMV, etc.) — senão, deixe 0.0.
7. Retorne APENAS um array JSON, sem nenhum texto antes ou depois.

TRECHO DO ARQUIVO:
{bloco}

FORMATO DE SAÍDA (array JSON, um objeto por linha de pedido):
[
  {{"produto_id": "...", "produto_nome": "...", "cliente_id": "...", "canal": "..." ou null, "receita": 0.0, "custo": 0.0, "data": "AAAA-MM-DD" ou null}}
]

COMECE!
"""

    def _parsear_resposta(self, texto: str) -> List[Dict[str, Any]]:
        match = re.search(r'\[.*\]', texto, re.DOTALL)
        if not match:
            raise ValueError("Gemini não retornou um array JSON")
        return json.loads(match.group(0))
