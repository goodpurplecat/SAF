"""
API do site — autenticação por link mágico, pagamento (Mercado Pago) e a
rota que aciona o PipelineSAF já existente.

`from app import PipelineSAF` já resolve sozinho o sys.path de dp-01/02/03
— essa parte não precisa ser repetida aqui, app.py já faz isso.

Variáveis de ambiente necessárias (ver .env.example):
  DATABASE_URL, SECRET_KEY, RESEND_API_KEY,
  R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME,
  MERCADOPAGO_ACCESS_TOKEN, MERCADOPAGO_WEBHOOK_SECRET, FRONTEND_URL, API_URL
"""

import os
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import mercadopago
from mercadopago.webhook.validator import WebhookSignatureValidator, InvalidWebhookSignatureError
from fastapi import FastAPI, Request, HTTPException, Depends, Cookie, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import PipelineSAF  # seu pipeline já existente — sys.path já resolvido por ele mesmo

from database import get_db, criar_tabelas, Cliente, Relatorio
from auth_magic_link import gerar_link_login, validar_link_login, gerar_sessao, validar_sessao
from email_service import enviar_link_login, enviar_relatorio_pronto, enviar_revisao_manual
from storage_r2 import subir_arquivo, gerar_url_temporaria


@asynccontextmanager
async def lifespan(app: FastAPI):
    criar_tabelas()
    yield


app = FastAPI(title="Finspots API", lifespan=lifespan)

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://finspots.com.br")

# CORREÇÃO (auditoria 10/09/2026): CORS estava totalmente ausente — o
# frontend (FRONTEND_URL, outro domínio) não conseguia chamar esta API do
# navegador. allow_credentials=True é necessário porque a autenticação usa
# cookie de sessão (ver /auth/confirmar). Se o frontend rodar em mais de um
# domínio (ex.: staging + produção), ajuste allow_origins para uma lista.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CORREÇÃO (auditoria 10/09/2026, achado "música de fundo"): a Edição já
# sabe fazer loop + fade de uma música por baixo da narração
# (dp-03/edicao/video_assembler.py), mas o pipeline era instanciado sem
# musica_path — nenhum vídeo saía com música, mesmo o recurso pronto.
#
# ATUALIZAÇÃO (13/09/2026): pra não depender de configurar variável de
# ambiente no Railway, agora existe um caminho padrão dentro do próprio
# repositório: dp-03/edicao/assets/musica_fundo.mp3. Basta subir o
# arquivo de música (mp3, sem letra/vocal, tipo lofi/corporativo baixo)
# nesse caminho exato pelo GitHub e fazer o deploy — o pipeline usa esse
# arquivo automaticamente, sem precisar mexer em nada no Railway.
# MUSICA_BACKGROUND_PATH continua funcionando como opção manual (tem
# prioridade sobre o arquivo padrão, útil pra trocar a música sem commit
# ou apontar pra um caminho fora do repo). Volume/fade ficam em
# AUDIO_CONFIG, dp-03/edicao/design_config.py (hoje: 17% de volume,
# fade-in de 2s, fade-out de 3s).
_MUSICA_PADRAO = os.path.join(
    os.path.dirname(__file__), "dp-03", "edicao", "assets", "musica_fundo.mp3"
)
MUSICA_BACKGROUND_PATH = os.environ.get("MUSICA_BACKGROUND_PATH") or (
    _MUSICA_PADRAO if os.path.isfile(_MUSICA_PADRAO) else None
)

pipeline = PipelineSAF(musica_path=MUSICA_BACKGROUND_PATH)
sdk_mp = mercadopago.SDK(os.environ["MERCADOPAGO_ACCESS_TOKEN"])

# Chave secreta do webhook (Mercado Pago > Suas integrações > [sua aplicação]
# > Webhooks > Configurar notificações). É DIFERENTE do MERCADOPAGO_ACCESS_TOKEN
# — usada só pra validar a assinatura de quem está chamando o webhook.
MERCADOPAGO_WEBHOOK_SECRET = os.environ["MERCADOPAGO_WEBHOOK_SECRET"]

# ATUALIZAÇÃO (13/09/2026): preço de lançamento/beta — R$800 (Diagnóstico) e
# R$1.200 (Mensalidade). Manter sincronizado com contrato.html, mensal.html,
# termos.html e termos-mensal.html no repo do site.
PRECOS = {
    "Diagnóstico": 800.00,
    "Mensalidade": 1200.00,
}


def cliente_atual(sessao: str = Cookie(default=None), db: Session = Depends(get_db)) -> Cliente:
    if not sessao:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    try:
        cliente_id = validar_sessao(sessao)
    except ValueError as erro:
        raise HTTPException(status_code=401, detail=str(erro))
    cliente = db.query(Cliente).filter_by(id=cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=401, detail="Cliente não encontrado.")
    return cliente


# ------------------------------------------------------------------
# Pagamento
# ------------------------------------------------------------------

@app.post("/pagamento/criar-preferencia")
def criar_preferencia(email: str, tipo_produto: str):
    """
    Chamado quando a pessoa clica em 'comprar' no site. Devolve a URL de
    checkout do Mercado Pago pra redirecionar. external_reference e
    metadata carregam email/tipo_produto pra virem de volta no webhook,
    já que o Mercado Pago não devolve isso sozinho.

    TODO: testar contra sua conta real do Mercado Pago — a forma do
    preference_data abaixo segue a doc oficial do SDK, mas nunca rodei
    isso de fato.
    """
    if tipo_produto not in PRECOS:
        raise HTTPException(status_code=400, detail="tipo_produto inválido.")

    preference_data = {
        "items": [{
            "title": f"Finspots — {tipo_produto}",
            "quantity": 1,
            "unit_price": PRECOS[tipo_produto],
            "currency_id": "BRL",
        }],
        "payer": {"email": email},
        "metadata": {"email": email, "tipo_produto": tipo_produto},
        "external_reference": f"{email}|{tipo_produto}",
        "back_urls": {
            "success": f"{FRONTEND_URL}/obrigado",
            "failure": f"{FRONTEND_URL}/pagamento-recusado",
        },
        "auto_return": "approved",
        "notification_url": f"{os.environ['API_URL']}/webhook/pagamento",
    }
    resultado = sdk_mp.preference().create(preference_data)
    preferencia = resultado["response"]
    return {"checkout_url": preferencia["init_point"]}


@app.post("/webhook/pagamento")
async def webhook_pagamento(request: Request, db: Session = Depends(get_db)):
    """
    O Mercado Pago manda só um ID aqui — o valor e o status de verdade
    precisam ser buscados na API deles antes de confiar em qualquer coisa.

    Antes de mais nada, valida a assinatura (cabeçalho x-signature) —
    sem isso, qualquer um poderia chamar essa URL e fingir um pagamento
    aprovado. O "id" usado na validação vem da query string
    (?data.id=...), não do corpo, e precisa estar em minúsculas — é assim
    que o Mercado Pago manda no cabeçalho.
    """
    data_id_url = request.query_params.get("data.id") or request.query_params.get("id")
    if data_id_url:
        data_id_url = data_id_url.lower()

    try:
        WebhookSignatureValidator.validate(
            x_signature=request.headers.get("x-signature"),
            x_request_id=request.headers.get("x-request-id"),
            data_id=data_id_url,
            secret=MERCADOPAGO_WEBHOOK_SECRET,
        )
    except InvalidWebhookSignatureError:
        raise HTTPException(status_code=401, detail="Assinatura do webhook inválida.")

    corpo = await request.json()

    if corpo.get("type") != "payment":
        return {"status": "ignorado"}

    payment_id = corpo["data"]["id"]
    pagamento = sdk_mp.payment().get(payment_id)["response"]

    if pagamento.get("status") != "approved":
        return {"status": "aguardando"}

    metadata = pagamento.get("metadata", {})
    email = metadata.get("email")
    tipo_produto = metadata.get("tipo_produto")

    if not email or not tipo_produto:
        return {"status": "erro", "detalhe": "metadata ausente no pagamento"}

    cliente = db.query(Cliente).filter_by(email=email).first()
    if not cliente:
        cliente = Cliente(email=email)
        db.add(cliente)
        db.commit()
        db.refresh(cliente)

    # CORREÇÃO (auditoria 12/09/2026): o link apontava pro FRONTEND
    # (finspots.com.br/entrar/confirmar), uma página que não existe no site
    # estático — quem clicasse caía num 404, nunca conseguindo entrar.
    # O endpoint que de fato valida o token e cria a sessão é
    # GET /auth/confirmar, que só existe nesta API — o link precisa apontar
    # pra cá (API_URL), não pro site. Este endpoint já redireciona pro
    # FRONTEND_URL/minha-area sozinho depois de validar (ver /auth/confirmar).
    link = f"{os.environ['API_URL']}/auth/confirmar?token={gerar_link_login(email)}"
    enviar_link_login(email, link)

    return {"status": "processado"}


# ------------------------------------------------------------------
# Autenticação por link mágico
# ------------------------------------------------------------------

@app.post("/auth/solicitar-link")
def solicitar_link(email: str, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter_by(email=email).first()
    if cliente:
        # CORREÇÃO (auditoria 12/09/2026): mesmo bug do webhook — link tem
        # que apontar pro endpoint que valida o token (API_URL/auth/confirmar),
        # não pro FRONTEND_URL (onde essa rota não existe).
        link = f"{os.environ['API_URL']}/auth/confirmar?token={gerar_link_login(email)}"
        enviar_link_login(email, link)
    # Mesma resposta se o email existir ou não — evita confirmar pra
    # quem tá tentando adivinhar emails de clientes cadastrados.
    return {"mensagem": "Se esse email tiver uma conta, o link chegou na caixa de entrada."}


@app.get("/auth/confirmar")
def confirmar_link(token: str, db: Session = Depends(get_db)):
    try:
        email = validar_link_login(token, db)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))

    cliente = db.query(Cliente).filter_by(email=email).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    resposta = RedirectResponse(url=f"{FRONTEND_URL}/minha-area")
    resposta.set_cookie(
        "sessao",
        gerar_sessao(cliente.id),
        httponly=True,
        secure=True,
        # CORREÇÃO (auditoria 12/09/2026): com samesite="lax", o navegador
        # não manda este cookie em chamadas fetch()/XHR entre sites — e é
        # exatamente assim que o frontend (finspots.com.br) chama esta API
        # (domínio separado, Railway). Resultado: o cliente "entra" (recebe
        # o cookie aqui), mas toda chamada seguinte da área dele
        # (/minha-area/relatorios, /processar) volta 401, como se nunca
        # tivesse logado. samesite="none" exige secure=True, que já estava
        # presente.
        samesite="none",
        max_age=30 * 24 * 60 * 60,
    )
    return resposta


# ------------------------------------------------------------------
# Área do cliente
# ------------------------------------------------------------------

@app.get("/minha-area/relatorios")
def listar_relatorios(cliente: Cliente = Depends(cliente_atual), db: Session = Depends(get_db)):
    relatorios = (
        db.query(Relatorio)
        .filter_by(cliente_id=cliente.id)
        .order_by(Relatorio.criado_em.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "tipo_produto": r.tipo_produto,
            "mes_referencia": r.mes_referencia,
            "status": r.status,
            "pdf_url": gerar_url_temporaria(r.pdf_chave_r2) if r.pdf_chave_r2 else None,
            "video_url": gerar_url_temporaria(r.video_chave_r2) if r.video_chave_r2 else None,
            "criado_em": r.criado_em.isoformat(),
        }
        for r in relatorios
    ]


# ------------------------------------------------------------------
# Processamento — chamado depois que o cliente envia o formulário
# ------------------------------------------------------------------

def _processar_em_segundo_plano(
    cliente_id: str,
    email: str,
    tipo_produto: str,
    respostas_formulario: dict,
    arquivos_info: list,
    conteudo_arquivos: dict,
):
    """
    Roda numa BackgroundTask — a geração de PDF/vídeo demora (é
    renderização real + narração + montagem de vídeo), então a requisição
    HTTP não pode ficar esperando isso terminar.
    """
    db = next(get_db())
    try:
        dados_motor_anterior = None
        if tipo_produto == "Mensalidade":
            ultimo = (
                db.query(Relatorio)
                .filter_by(cliente_id=cliente_id, status="pronto")
                .order_by(Relatorio.criado_em.desc())
                .first()
            )
            if ultimo and ultimo.dados_motor_json:
                dados_motor_anterior = json.loads(ultimo.dados_motor_json)

        out_dir = f"/tmp/saidas/{cliente_id}_{datetime.now().timestamp()}"

        resultado = pipeline.processar_cliente(
            tipo_produto=tipo_produto,
            respostas_formulario=respostas_formulario,
            arquivos_info=arquivos_info,
            conteudo_arquivos=conteudo_arquivos,
            out_dir=out_dir,
            dados_motor_periodo_anterior=dados_motor_anterior,
        )

        # CORREÇÃO (auditoria 12/09/2026): `relatorio.id` era lido AQUI, antes
        # de db.add()/db.commit() — o default (SQLAlchemy Column(default=...))
        # só é aplicado no flush/commit, então `relatorio.id` valia `None`
        # neste ponto, sempre. Toda chave R2 saía como "relatorios/None/...",
        # e cada novo relatório (de QUALQUER cliente) sobrescrevia o PDF/vídeo
        # do relatório anterior no mesmo caminho fixo — risco real de um
        # cliente ver o relatório de outro. Gerando o id explicitamente antes
        # de montar as chaves, cada relatório fica isolado de verdade.
        relatorio_id = str(uuid.uuid4())
        relatorio = Relatorio(id=relatorio_id, cliente_id=cliente_id, tipo_produto=tipo_produto)

        if resultado.status == "SUCESSO":
            chave_pdf = f"relatorios/{relatorio_id}/relatorio.pdf"
            chave_video = f"relatorios/{relatorio_id}/video.mp4"
            subir_arquivo(resultado.resultado_edicao.pdf_path, chave_pdf)
            subir_arquivo(resultado.resultado_edicao.video_path, chave_video)
            relatorio.pdf_chave_r2 = chave_pdf
            relatorio.video_chave_r2 = chave_video
            relatorio.dados_motor_json = json.dumps(resultado.dados_motor)
            relatorio.status = "pronto"
            db.add(relatorio)
            db.commit()

            link = f"{os.environ['API_URL']}/auth/confirmar?token={gerar_link_login(email)}"
            enviar_relatorio_pronto(email, link)

        elif resultado.status == "REVISAO_MANUAL_NECESSARIA":
            relatorio.status = "revisao_manual"
            relatorio.mensagem_erro = resultado.mensagem
            db.add(relatorio)
            db.commit()
            enviar_revisao_manual(email)

        else:  # ERRO
            relatorio.status = "erro"
            relatorio.mensagem_erro = resultado.mensagem
            db.add(relatorio)
            db.commit()
            # TODO: decidir se um erro de pipeline também deve gerar um
            # aviso pro cliente ou só uma notificação interna sua.
    finally:
        db.close()


@app.post("/processar")
def processar(
    background_tasks: BackgroundTasks,
    tipo_produto: str,
    respostas_formulario: Dict[str, Any],
    arquivos_info: List[Any],
    cliente: Cliente = Depends(cliente_atual),
    conteudo_arquivos: Optional[Dict[str, Any]] = None,
):
    background_tasks.add_task(
        _processar_em_segundo_plano,
        cliente.id, cliente.email, tipo_produto,
        respostas_formulario, arquivos_info, conteudo_arquivos,
    )
    return {"status": "processando", "mensagem": "Você recebe um email assim que estiver pronto."}
