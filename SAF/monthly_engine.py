"""
Monthly Diagnostic Engine - shim de raiz

Reexporta o Motor de Mensalidade de verdade, que mora em
"dp-01/motores/motor mensalidade/monthly_engine.py" — só pra
`from monthly_engine import ...` funcionar a partir da raiz do
repositório, como o README e o briefing de uso sempre instruíram.

CORREÇÃO (05/09/2026, auditoria app.py): mesmo problema do shim irmão
`financial_engine.py` (ver o comentário lá, mais detalhado) — este arquivo
era uma cópia INTEIRA do orquestrador da Mensalidade, não um shim de
verdade. Isso já exigiu replicar manualmente, numa sessão anterior, a
correção do comparativo de Margem Líquida (`profit_margin_comparative`)
nas duas cópias — o tipo exato de duplicação frágil que este arquivo
deixa de ser agora. Carrega o módulo real por CAMINHO (via
`importlib.util`, sob um nome interno diferente, pra não colidir com o
nome deste próprio módulo em sys.modules) e reexporta os símbolos que
quem usa este shim (README, testes, EXAMPLES.py) espera encontrar.
"""

import importlib.util
import os
import sys

_DIR_MOTOR_MENSALIDADE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "dp-01", "motores", "motor mensalidade",
)
if _DIR_MOTOR_MENSALIDADE not in sys.path:
    # Necessário pra que o `from monthly_engine_models import *` (etc.) de
    # dentro do módulo real encontre seus próprios módulos de apoio.
    sys.path.insert(0, _DIR_MOTOR_MENSALIDADE)

_caminho_real = os.path.join(_DIR_MOTOR_MENSALIDADE, "monthly_engine.py")
_spec = importlib.util.spec_from_file_location("_monthly_engine_impl_real", _caminho_real)
_modulo_real = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_modulo_real)

MonthlyDiagnosticEngineMain = _modulo_real.MonthlyDiagnosticEngineMain
example_usage = _modulo_real.example_usage

# Modelos/enums/funções reexportados pra manter compatível qualquer código
# que fazia `from monthly_engine import Month, MonthlyFinancialInput,
# SalesIntelligence, ...` direto.
for _nome in dir(_modulo_real):
    if not _nome.startswith("_") and _nome not in globals():
        globals()[_nome] = getattr(_modulo_real, _nome)
del _nome


if __name__ == "__main__":
    example_usage()
