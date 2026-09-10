"""
Login sem senha: link mágico por email + sessão depois.

O link em si nunca é armazenado — é um token assinado (itsdangerous), que
carrega o próprio email e expira sozinho. A tabela magic_links_usados só
serve pra barrar reuso do MESMO link depois que ele já funcionou uma vez.

Requer a variável de ambiente SECRET_KEY — gere uma string aleatória longa
(ex.: `python -c "import secrets; print(secrets.token_hex(32))"`) e guarde
só nas variáveis de ambiente do Railway, nunca no código.
"""

import os

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy.orm import Session

from database import MagicLinkUsado

SECRET_KEY = os.environ["SECRET_KEY"]
_serializer = URLSafeTimedSerializer(SECRET_KEY)

LOGIN_TOKEN_MAX_AGE_SEGUNDOS = 30 * 60          # link de entrada: 30 minutos
SESSAO_MAX_AGE_SEGUNDOS = 30 * 24 * 60 * 60     # sessão depois de logada: 30 dias


def gerar_link_login(email: str) -> str:
    return _serializer.dumps(email, salt="login")


def validar_link_login(token: str, db: Session) -> str:
    """Retorna o email se o token for válido e ainda não usado. Lança ValueError caso contrário."""
    if db.query(MagicLinkUsado).filter_by(token=token).first():
        raise ValueError("Esse link já foi usado. Peça um novo pra entrar.")

    try:
        email = _serializer.loads(token, salt="login", max_age=LOGIN_TOKEN_MAX_AGE_SEGUNDOS)
    except SignatureExpired:
        raise ValueError("Esse link expirou. Peça um novo pra entrar.")
    except BadSignature:
        raise ValueError("Link inválido.")

    db.add(MagicLinkUsado(token=token))
    db.commit()
    return email


def gerar_sessao(cliente_id: str) -> str:
    return _serializer.dumps(cliente_id, salt="sessao")


def validar_sessao(valor_cookie: str) -> str:
    """Retorna o cliente_id se a sessão for válida. Lança ValueError caso contrário."""
    try:
        return _serializer.loads(valor_cookie, salt="sessao", max_age=SESSAO_MAX_AGE_SEGUNDOS)
    except (SignatureExpired, BadSignature):
        raise ValueError("Sessão expirada. Faça login de novo.")
