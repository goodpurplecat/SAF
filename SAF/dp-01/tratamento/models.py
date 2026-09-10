"""
Tratamento de Dados - Data Models
Estruturas para armazenar dados do cliente, formulário e arquivos tratados
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class QualidadeDado(Enum):
    """Qualidade do dado conforme o guia"""
    EXATO = "Exato"              # Veio de relatório oficial
    ESTIMATIVA = "Estimativa"    # Cliente marcou como estimativa
    CALCULADO = "Calculado"      # Gem derivou de outros campos
    AUSENTE = "Ausente"          # Campo não encontrado


class TipoProduto(Enum):
    """
    Tipo de produto para análise.

    REMOÇÃO (auditoria 05/09/2026): existia um terceiro valor, COHORT, cujo
    tratamento nunca saiu do estágio de stub (ver histórico do repositório)
    e cuja "planilha de Cohort" também era citada em alguns insights dos
    motores como recomendação pro cliente. Confirmado com o analista que
    esse produto não vai existir — removido daqui e dos textos que o
    citavam (ver financial_engine_diagnostic.py nos dois motores).
    """
    DIAGNOSTICO = "Diagnóstico"
    MENSALIDADE = "Mensalidade"


@dataclass
class CampoTratado:
    """Um campo de dados com valor, fonte e qualidade"""
    nome_campo: str
    valor: Any
    qualidade: QualidadeDado
    fonte: str  # Qual arquivo/formulário forneceu o dado
    celula_destino: Optional[str] = None  # Ex: "INPUT!B5"
    observacao: str = ""


@dataclass
class RespostaFormulario:
    """Resposta de uma pergunta do formulário"""
    numero_pergunta: int  # Q1, Q2, ...
    pergunta: str
    resposta: str
    tipo: str  # "texto", "numero", "multipla_escolha", "arquivo"


@dataclass
class ArquivoRecebido:
    """Um arquivo enviado pelo cliente"""
    nome_arquivo: str
    formato: str  # csv, xlsx, pdf, png, etc
    tamanho_mb: float
    data_recebimento: str
    tipo_arquivo: str  # "relatorio_ml", "relatorio_shopee", "extrato_bancario", etc
    status_processamento: str  # "processado", "erro", "ilegivel"
    mensagem_erro: Optional[str] = None


@dataclass
class DadosCliente:
    """Dados de identificação do cliente"""
    nome_loja: str
    periodo_analisado: str
    # LIMPEZA (04/09/2026): categoria_negocio não é mais preenchido pela IA
    # Extratora (ela parou de pedir isso a Claude — ver extratora.py). Os
    # motores derivam a Categoria (A-E) sozinhos a partir do ticket médio e
    # da margem de contribuição, então este campo só serve hoje como
    # possível override manual futuro; fica None na prática.
    categoria_negocio: Optional[str] = None  # A, B, C, D, E
    regime_tributario: Optional[str] = None
    aliquota_impostos: float = 0.0
    tempo_loja: Optional[str] = None
    observacoes: str = ""


@dataclass
class MapeamentoCanais:
    """Mapeamento de canais declarados e arquivos esperados"""
    canais_declarados: List[str]  # Mercado Livre, Shopee, etc
    canais_com_arquivo: Dict[str, str] = field(default_factory=dict)  # canal -> arquivo
    canais_sem_arquivo: List[str] = field(default_factory=list)


@dataclass
class DadosFinanceirosTratados:
    """Todos os dados financeiros já tratados"""
    receita_bruta: CampoTratado
    devolucoes: CampoTratado
    cmv: CampoTratado
    custos_variaveis: CampoTratado
    custos_fixos: CampoTratado
    pro_labore: CampoTratado
    num_pedidos: CampoTratado
    ads_investment: CampoTratado
    novos_clientes_ads: CampoTratado
    pmr: CampoTratado  # Prazo Médio Recebimento
    pmp: CampoTratado  # Prazo Médio Pagamento
    faturamento_por_canal: Dict[str, CampoTratado] = field(default_factory=dict)
    # NOVIDADE (05/09/2026, pedido do analista): pipeline é automático e
    # assíncrono — alta demanda não permite ninguém digitar taxa de canal
    # na mão pra cada cliente. Preenchido pela IA Extratora a partir da
    # resposta do cliente no formulário quando ele usa um canal fora da
    # nossa lista conhecida (ver SalesChannel, financial_engine_models.py)
    # e informa a própria taxa — flui sozinho até o motor (ver
    # limpeza.py::_limpar_para_diagnostico() e app.py). Fica vazio (não é
    # erro) quando todos os canais do cliente já são conhecidos, ou quando
    # um canal customizado aparece sem o cliente saber a taxa dele (nesse
    # caso o motor usa 0% até alguém informar — ver README, seção
    # "Configuração").
    taxas_canais_declaradas: Dict[str, CampoTratado] = field(default_factory=dict)


@dataclass
class PercepcoesCliente:
    """
    NOVIDADE (06/09/2026, confirmado pelo analista): respostas SUBJETIVAS
    do cliente sobre o próprio negócio (Seção 6 do formulário de
    Diagnóstico — "Sobre o negócio": se acha que fatura X, se acha que
    está lucrando, qual canal acha melhor, etc.). Existem só pra Produção
    (dp-02, a IA de Relatório e Roteiro) cruzar "o que o cliente acredita"
    com "o que os dados realmente mostram" — o Diagnóstico Comparativo
    (Guia Operacional 5.1; ver também GUIA_DO_FORMULARIO_DIAGNOSTICO_E_
    MENSALIDADE, Seção A.7). Confirmado pelo analista: "essas perguntas
    [...] servem de gancho pra criar o roteiro do vídeo e roteiro pdf,
    fica mais personalizado" — só que "tem que ser feito com cuidado pra
    não parecer um sermão, pois o intuito é trazer clareza".

    Regra absoluta, igual ao resto da Seção 6 (Guia Operacional 3.1):
    NUNCA entram no motor de cálculo — `DadosFinanceirosTratados` acima é
    quem alimenta o motor, este dataclass é usado só por dp-02. Existe só
    pro Diagnóstico — a Mensalidade não tem formulário novo (ver Parte B
    do guia do formulário), então não há Seção 6 pra repetir todo mês.

    Todo campo é Optional/string livre e fica None quando o cliente não
    respondeu — a IA Extratora NUNCA deve inventar uma crença que o
    cliente não declarou (mesma regra de fonte/qualidade do resto do
    tratamento, só que aqui não se aplica CampoTratado porque não é um
    dado com "qualidade" no sentido financeiro — é uma opinião, existe ou
    não existe).
    """
    percepcao_faturamento: Optional[str] = None        # Q28: "Crescendo" / "Estável" / "Caindo" / "Oscilando muito"
    acha_que_esta_lucrando: Optional[str] = None        # Q33: resposta literal do cliente
    pro_labore_desejado: Optional[float] = None         # quanto o cliente GOSTARIA de retirar — distinto do real (esse é dado financeiro, ver custos_fixos/pro_labore acima). Formulário antigo não separava isso — ver guia do formulário, A.4.
    canal_percebido_como_melhor: Optional[str] = None   # nome do canal que o cliente ACHA que é o melhor (nem sempre bate com o canal real de melhor margem)
    sabe_produto_mais_lucrativo: Optional[str] = None   # Q35: resposta literal
    objetivo_com_diagnostico: Optional[str] = None      # Q37: o que o cliente espera tirar da análise
    maior_duvida_ou_preocupacao: Optional[str] = None   # Q36: texto livre
    outras_percepcoes: Dict[str, str] = field(default_factory=dict)  # qualquer outra resposta relevante da Seção 6 não coberta acima (pergunta curta -> resposta)

    def tem_alguma_percepcao(self) -> bool:
        """
        True se o cliente declarou pelo menos uma expectativa/percepção —
        usado por dp-02 pra decidir se inclui o bloco de Diagnóstico
        Comparativo no prompt ou se gera o relatório/roteiro normalmente
        (sem forçar nenhuma comparação quando não há nada declarado).
        """
        campos_simples = (
            self.percepcao_faturamento, self.acha_que_esta_lucrando,
            self.pro_labore_desejado, self.canal_percebido_como_melhor,
            self.sabe_produto_mais_lucrativo, self.objetivo_com_diagnostico,
            self.maior_duvida_ou_preocupacao,
        )
        return any(c not in (None, "") for c in campos_simples) or bool(self.outras_percepcoes)


@dataclass
class Alerta:
    """Um conflito ou alerta encontrado durante o tratamento"""
    tipo: str  # "conflito", "campo_ausente", "dado_ilegivel", "divergencia"
    severidade: str  # "CRITICO", "ATENCAO", "INFO"
    localizacao: str  # Onde foi encontrado (ex: "Arquivo ML_vendas.csv, linha 45")
    descricao: str
    valor_formulario: Optional[Any] = None
    valor_arquivo: Optional[Any] = None
    divergencia_pct: float = 0.0


@dataclass
class ResultadoTratamento:
    """Resultado final do tratamento"""
    tipo_produto: TipoProduto
    cliente: DadosCliente
    formulario_respostas: List[RespostaFormulario]
    arquivos_recebidos: List[ArquivoRecebido]
    mapeamento_canais: MapeamentoCanais
    dados_financeiros: DadosFinanceirosTratados
    alertas: List[Alerta]
    campos_ausentes: List[str]
    status_final: str  # "COMPLETO", "INCOMPLETO", "AGUARDANDO_CONFIRMACAO"
    mensagem_status: str
    timestamp: str
    # NOVIDADE (06/09/2026): ver PercepcoesCliente acima — nunca entra no
    # motor, só em dp-02 (Diagnóstico Comparativo). Fica com o default
    # (tudo None) pra Mensalidade e pra qualquer Diagnóstico sem Seção 6
    # respondida — nunca quebra a construção de ResultadoTratamento.
    percepcoes_cliente: PercepcoesCliente = field(default_factory=PercepcoesCliente)
    
    def como_json(self) -> Dict[str, Any]:
        """Exporta resultado como dicionário"""
        return {
            'tipo_produto': self.tipo_produto.value,
            'cliente': self.cliente.__dict__,
            'alertas': [a.__dict__ for a in self.alertas],
            'status_final': self.status_final,
            'campos_ausentes': self.campos_ausentes,
            'num_campos_tratados': len([f for f in self.dados_financeiros.__dict__.values() if isinstance(f, CampoTratado)]),
        }
