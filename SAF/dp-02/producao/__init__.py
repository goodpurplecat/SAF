"""
Departamento de Produção
Transforma o output do Motor (Diagnóstico ou Mensalidade) em texto de
relatório PDF e roteiro de vídeo, revisados pela IA Fiscal antes de ir pro cliente.
"""

from .models import (
    TipoProduto,
    TipoDocumento,
    StatusRevisao,
    StatusProducao,
    ItemRevisao,
    RevisaoFiscal,
    RelatorioTexto,
    RoteiroTexto,
    ResultadoProducao,
)
from .relatorio_roteiro import IARelatorioRoteiro
from .fiscal_relatorio import IAFiscalRelatorioRoteiro
from .producao import DepartamentoProducao

__all__ = [
    "TipoProduto",
    "TipoDocumento",
    "StatusRevisao",
    "StatusProducao",
    "ItemRevisao",
    "RevisaoFiscal",
    "RelatorioTexto",
    "RoteiroTexto",
    "ResultadoProducao",
    "IARelatorioRoteiro",
    "IAFiscalRelatorioRoteiro",
    "DepartamentoProducao",
]
