"""
Banco de dados — clientes, relatórios entregues, e controle de links mágicos.

Requer a variável de ambiente DATABASE_URL. No Railway, adicionar um
PostgreSQL ao projeto cria essa variável automaticamente.
"""

import os
import uuid
from datetime import datetime

from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def _novo_id() -> str:
    return str(uuid.uuid4())


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(String, primary_key=True, default=_novo_id)
    email = Column(String, unique=True, nullable=False, index=True)
    nome = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    relatorios = relationship("Relatorio", back_populates="cliente")


class Relatorio(Base):
    """
    Uma linha por entrega — o Diagnóstico gera uma, e cada mês de
    Mensalidade gera outra pro mesmo cliente. dados_motor_json guarda o
    export_to_dict() do motor pra alimentar a comparação do mês seguinte.
    """
    __tablename__ = "relatorios"

    id = Column(String, primary_key=True, default=_novo_id)
    cliente_id = Column(String, ForeignKey("clientes.id"), nullable=False, index=True)
    tipo_produto = Column(String, nullable=False)  # "Diagnóstico" ou "Mensalidade"
    mes_referencia = Column(String, nullable=True)  # ex: "2026-09" — None no Diagnóstico
    status = Column(String, default="processando")  # processando | pronto | revisao_manual | erro
    pdf_chave_r2 = Column(String, nullable=True)
    video_chave_r2 = Column(String, nullable=True)
    dados_motor_json = Column(Text, nullable=True)
    # NOVIDADE (auditoria 15/09/2026, handoff Pendência 3): lista JSON de
    # cliente_id (ResultadoPipeline.clientes_ids_mes, app.py) vistos nos
    # pedidos deste mês — só preenchido em Mensalidade, quando o cliente
    # subiu arquivo de vendas por pedido. dados_motor_json (acima) só guarda
    # o AGREGADO por produto (product_breakdown) — nenhum ID de cliente
    # individual aparece lá — então sem esta coluna não haveria como
    # reconstruir known_customer_ids (novo x recorrente) nos meses
    # seguintes. None em qualquer relatório anterior a esta migração, ou em
    # meses processados sem upload de vendas por pedido.
    clientes_ids_json = Column(Text, nullable=True)
    mensagem_erro = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    cliente = relationship("Cliente", back_populates="relatorios")


class MagicLinkUsado(Base):
    """Um registro por link já clicado, pra impedir que o mesmo link funcione duas vezes."""
    __tablename__ = "magic_links_usados"

    token = Column(String, primary_key=True)
    usado_em = Column(DateTime, default=datetime.utcnow)


def criar_tabelas():
    Base.metadata.create_all(engine)


def get_db():
    """Dependency do FastAPI — abre uma sessão por requisição e sempre fecha."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
