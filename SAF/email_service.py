"""
Envio de email transacional via Resend — link mágico e aviso de entrega.

Requer: RESEND_API_KEY. EMAIL_REMETENTE é opcional (padrão abaixo); pra
usar seu próprio domínio (contato@finspots.com.br), precisa verificá-lo
antes no painel da Resend.
"""

import os

import resend

resend.api_key = os.environ["RESEND_API_KEY"]

REMETENTE = os.environ.get("EMAIL_REMETENTE", "Finspots <onboarding@resend.dev>")


def enviar_link_login(email_destino: str, link: str):
    resend.Emails.send({
        "from": REMETENTE,
        "to": email_destino,
        "subject": "Seu link de acesso à Finspots",
        "html": (
            f"<p>Clica no link abaixo pra entrar na sua conta. "
            f"Ele vale por 30 minutos e só funciona uma vez:</p>"
            f'<p><a href="{link}">Entrar na minha conta</a></p>'
        ),
    })


def enviar_relatorio_pronto(email_destino: str, link_login: str):
    resend.Emails.send({
        "from": REMETENTE,
        "to": email_destino,
        "subject": "Seu relatório está pronto",
        "html": (
            f"<p>Sua análise já está disponível.</p>"
            f'<p><a href="{link_login}">Ver meu relatório</a></p>'
        ),
    })


def enviar_revisao_manual(email_destino: str):
    resend.Emails.send({
        "from": REMETENTE,
        "to": email_destino,
        "subject": "Seu diagnóstico está sendo revisado",
        "html": (
            "<p>Seu relatório passou por uma checagem extra antes de ser liberado. "
            "Isso não é um problema com os seus dados — só significa que alguém da "
            "nossa equipe vai dar uma olhada antes de te enviar. Você recebe um "
            "aviso assim que estiver pronto.</p>"
        ),
    })
