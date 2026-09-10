"""
Departamento de Produção - Data Models
Estruturas para o Relatório PDF, o Roteiro de Vídeo e a Revisão Fiscal.

Este departamento entra DEPOIS do Motor (Diagnóstico ou Mensalidade) já ter
rodado. Ele não recalcula nada — pega o `export_to_dict()` do motor (que
faz o papel da planilha preenchida nos guias originais da Gem) e transforma
isso em texto pronto pro relatório PDF e pro roteiro de vídeo, depois manda
tudo pra revisão fiscal antes de considerar pronto pro cliente.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class TipoProduto(Enum):
    """Qual motor gerou os dados que a Produção vai transformar em texto."""
    DIAGNOSTICO = "Diagnóstico"
    MENSALIDADE = "Mensalidade"


class TipoDocumento(Enum):
    """Qual dos dois entregáveis está sendo gerado/revisado."""
    RELATORIO = "Relatório PDF"
    ROTEIRO = "Roteiro de Vídeo"


class StatusRevisao(Enum):
    """Espelha o 'STATUS FINAL' do Guia da Gem Fiscal."""
    APROVADO = "APROVADO"
    APROVADO_COM_OBSERVACOES = "APROVADO_COM_OBSERVACOES"
    NAO_APROVADO = "NAO_APROVADO"


class StatusProducao(Enum):
    """Status final do pipeline do Departamento de Produção."""
    SUCESSO = "SUCESSO"
    REVISAO_MANUAL_NECESSARIA = "REVISAO_MANUAL_NECESSARIA"
    ERRO = "ERRO"


@dataclass
class ItemRevisao:
    """Um item apontado pela Gem Fiscal (bloqueador, ajuste ou observação)."""
    localizacao: str
    problema: str
    sugestao: str = ""

    def como_dict(self) -> Dict[str, str]:
        return {
            "localizacao": self.localizacao,
            "problema": self.problema,
            "sugestao": self.sugestao,
        }


@dataclass
class RevisaoFiscal:
    """
    Resultado da IA Fiscal do Relatório e Roteiro sobre UM documento
    (o relatório OU o roteiro — cada um recebe sua própria revisão).
    """
    tipo_documento: TipoDocumento
    bloqueadores: List[ItemRevisao] = field(default_factory=list)
    ajustes: List[ItemRevisao] = field(default_factory=list)
    observacoes: List[ItemRevisao] = field(default_factory=list)
    status: StatusRevisao = StatusRevisao.NAO_APROVADO
    texto_completo: str = ""  # relatório de revisão formatado (para log/humano)

    @property
    def tem_bloqueadores(self) -> bool:
        return len(self.bloqueadores) > 0

    @property
    def precisa_correcao(self) -> bool:
        """Bloqueadores E ajustes impedem o envio ao cliente (ver Guia da Gem Fiscal)."""
        return len(self.bloqueadores) > 0 or len(self.ajustes) > 0

    def como_feedback_para_geradora(self) -> str:
        """
        Formata os problemas encontrados como instrução de correção pra
        IA de Relatório e Roteiro reprocessar — é o loop pontilhado do
        fluxograma (Fiscal → volta pra geradora).
        """
        linhas = []
        if self.bloqueadores:
            linhas.append("BLOQUEADORES (corrigir obrigatoriamente):")
            for item in self.bloqueadores:
                linhas.append(f"- [{item.localizacao}] {item.problema} → {item.sugestao}")
        if self.ajustes:
            linhas.append("AJUSTES (corrigir obrigatoriamente):")
            for item in self.ajustes:
                linhas.append(f"- [{item.localizacao}] {item.problema} → {item.sugestao}")
        return "\n".join(linhas)


@dataclass
class RelatorioTexto:
    """Texto de cada página do relatório PDF, pronto para colar no Canva."""
    tipo_produto: TipoProduto
    paginas: Dict[int, str] = field(default_factory=dict)  # número da página -> texto

    def como_texto_unico(self) -> str:
        partes = []
        for numero in sorted(self.paginas.keys()):
            partes.append(f"=== PÁGINA {numero} ===\n{self.paginas[numero]}")
        return "\n\n".join(partes)


@dataclass
class RoteiroTexto:
    """
    Texto de cada bloco do vídeo, na ordem de gravação — em DOIS textos por
    bloco (decisão do analista, 05/09/2026, pra manter o card do slide curto
    e visualmente limpo em vez de repetir a fala inteira na tela):

    - `blocos`: a FALA completa, narrada de verdade (vai pro ElevenLabs/IA
      de Áudio, dp-03).
    - `blocos_card`: o texto CURTO que aparece escrito no card do slide
      (dado principal + 1 frase, ver templates.VOICE_RULES_CARD) — nunca é
      a fala transcrita, é um recorte dela.

    Cards de transição (sem narração própria) usam o mesmo texto curto nos
    dois campos — não têm versão longa separada.
    """
    tipo_produto: TipoProduto
    blocos: Dict[str, str] = field(default_factory=dict)  # nome do bloco -> fala narrada completa
    blocos_card: Dict[str, str] = field(default_factory=dict)  # nome do bloco -> texto curto do card
    ordem_blocos: List[str] = field(default_factory=list)  # ordem de gravação

    def como_texto_unico(self) -> str:
        """Formata fala + card lado a lado — usado pela Fiscal, que revisa os dois juntos."""
        partes = []
        ordem = self.ordem_blocos or list(self.blocos.keys())
        for nome in ordem:
            if nome not in self.blocos:
                continue
            texto = f"▶ {nome}\nFALA (narração completa): {self.blocos[nome]}"
            if nome in self.blocos_card:
                texto += f"\nCARD (texto curto na tela): {self.blocos_card[nome]}"
            partes.append(texto)
        return "\n\n".join(partes)


@dataclass
class ResultadoProducao:
    """Resultado final do pipeline do Departamento de Produção para 1 cliente."""
    status: StatusProducao
    tipo_produto: TipoProduto
    cliente_nome: str
    relatorio: Optional[RelatorioTexto] = None
    roteiro: Optional[RoteiroTexto] = None
    revisao_relatorio: Optional[RevisaoFiscal] = None
    revisao_roteiro: Optional[RevisaoFiscal] = None
    tentativas: int = 0
    timestamp: str = ""

    def como_json(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "tipo_produto": self.tipo_produto.value,
            "cliente_nome": self.cliente_nome,
            "tentativas": self.tentativas,
            "relatorio": self.relatorio.paginas if self.relatorio else None,
            "roteiro": self.roteiro.blocos if self.roteiro else None,
            "roteiro_card": self.roteiro.blocos_card if self.roteiro else None,
            "revisao_relatorio_status": self.revisao_relatorio.status.value if self.revisao_relatorio else None,
            "revisao_roteiro_status": self.revisao_roteiro.status.value if self.revisao_roteiro else None,
            "timestamp": self.timestamp,
        }
