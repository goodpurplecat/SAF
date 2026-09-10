"""
Financial Diagnostic Engine - shim de raiz

Reexporta o Motor de Diagnóstico de verdade, que mora em
"dp-01/motores/motor diagnostico/financial_engine.py" — só pra
`from financial_engine import ...` funcionar a partir da raiz do
repositório, como o README e o briefing de uso sempre instruíram.

CORREÇÃO (05/09/2026, auditoria app.py): até aqui este arquivo não era um
shim de verdade — era uma cópia INTEIRA do orquestrador, colada por baixo
de um bootstrap de `sys.path` (mesma ideia, execução ruim). Isso já tinha
mordido o projeto uma vez (o comparativo de Margem Líquida da Mensalidade
foi corrigido na cópia "oficial" e alguém — no caso, eu mesmo, numa sessão
anterior — teve que lembrar de replicar manualmente aqui). Mordeu de novo
agora: corrigi `nome_canal()` (canal de venda customizado, ver
financial_engine_models.py) só na cópia oficial, e um teste rodando através
deste shim quebrou porque a cópia daqui não tinha o fix. Daqui pra frente só
existe UMA implementação de verdade — este arquivo só a carrega e reexporta.

Carrega o arquivo real por CAMINHO (não por `import financial_engine`, que
colidiria com o nome deste próprio módulo em sys.modules — o mesmo motivo
pelo qual isso nunca foi um `from ... import *` simples) via
`importlib.util`, sob um nome interno diferente, e reexpõe só os símbolos
que quem usa este shim (README, app.py, testes, EXAMPLES.py) espera
encontrar em `from financial_engine import ...`.
"""

import importlib.util
import os
import sys

_DIR_MOTOR_DIAGNOSTICO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "dp-01", "motores", "motor diagnostico",
)
if _DIR_MOTOR_DIAGNOSTICO not in sys.path:
    # Necessário pra que o `from financial_engine_models import *` (etc.)
    # de dentro do módulo real encontre seus próprios módulos de apoio.
    sys.path.insert(0, _DIR_MOTOR_DIAGNOSTICO)

_caminho_real = os.path.join(_DIR_MOTOR_DIAGNOSTICO, "financial_engine.py")
_spec = importlib.util.spec_from_file_location("_financial_engine_impl_real", _caminho_real)
_modulo_real = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_modulo_real)

# Reexporta tudo que este shim precisa oferecer — mesma superfície pública
# que `from financial_engine_models import *` já trazia antes (a classe do
# motor + os modelos/enums usados em exemplos e testes), mais a própria
# classe do orquestrador e a função de demonstração.
FinancialDiagnosticEngine = _modulo_real.FinancialDiagnosticEngine
example_usage = _modulo_real.example_usage

# Modelos/enums/funções reexportados pra manter compatível qualquer código
# que fazia `from financial_engine import ConfigParameters, FinancialInput,
# BusinessCategory, TaxRegime, SalesChannel, ...` direto (padrão usado no
# README e em vários exemplos deste repositório).
for _nome in dir(_modulo_real):
    if not _nome.startswith("_") and _nome not in globals():
        globals()[_nome] = getattr(_modulo_real, _nome)
del _nome


if __name__ == "__main__":
    example_usage()
