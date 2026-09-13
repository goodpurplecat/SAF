"""Departamento de Edição - Data Models"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class StatusEdicao(Enum):
    SUCESSO = "SUCESSO"
    REVISAO_MANUAL_NECESSARIA = "REVISAO_MANUAL_NECESSARIA"
    ERRO = "ERRO"


@dataclass
class SlideRenderizado:
    """Um slide de vídeo já renderizado (imagem) + o áudio narrado correspondente."""
    bloco_nome: str
    imagem_path: str
    audio_path: Optional[str] = None
    duracao_segundos: Optional[float] = None


@dataclass
class ItemRevisaoFinal:
    localizacao: str
    problema: str
    sugestao: str = ""


@dataclass
class RevisaoFiscalFinal:
    """
    Resultado da IA Fiscal de Produção — compara o PDF/vídeo MONTADOS
    (arquivo final) com os textos aprovados pela Produção, pra pegar
    problemas que só aparecem na montagem: texto cortado no slide, página
    fora de ordem, áudio fora de sincronia, etc. Não repete a revisão de
    voz/dados já feita pela IA Fiscal do Relatório e Roteiro (dp-02).
    """
    bloqueadores: List[ItemRevisaoFinal] = field(default_factory=list)
    ajustes: List[ItemRevisaoFinal] = field(default_factory=list)
    observacoes: List[ItemRevisaoFinal] = field(default_factory=list)
    aprovado: bool = False
    texto_completo: str = ""

    @property
    def precisa_correcao(self) -> bool:
        return len(self.bloqueadores) > 0 or len(self.ajustes) > 0


@dataclass
class ResultadoEdicao:
    status: StatusEdicao
    tipo_produto: str
    cliente_nome: str
    pdf_path: Optional[str] = None
    video_path: Optional[str] = None
    slides: List[SlideRenderizado] = field(default_factory=list)
    revisao_fiscal_final: Optional[RevisaoFiscalFinal] = None
    tentativas: int = 0
    timestamp: str = ""
    # CORREÇÃO (auditoria 12/09/2026): sinaliza quando o vídeo foi montado
    # com narração placeholder (áudio silencioso — ver audio_generator.py,
    # IAAudio.modo_real) em vez de narração real do ElevenLabs. Ver
    # DepartamentoEdicao.processar(): quando True, o status NUNCA fecha como
    # SUCESSO, mesmo que a IA Fiscal aprove — silêncio no lugar da narração
    # jamais deveria chegar a um cliente pagante.
    audio_placeholder: bool = False

    def como_json(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "tipo_produto": self.tipo_produto,
            "cliente_nome": self.cliente_nome,
            "pdf_path": self.pdf_path,
            "video_path": self.video_path,
            "num_slides": len(self.slides),
            "aprovado_fiscal_final": self.revisao_fiscal_final.aprovado if self.revisao_fiscal_final else None,
            "audio_placeholder": self.audio_placeholder,
            "tentativas": self.tentativas,
            "timestamp": self.timestamp,
        }
