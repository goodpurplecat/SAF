"""
Upload dos relatórios pro Cloudflare R2 e geração de URLs temporárias.

O bucket fica privado — nada é público. Toda vez que o cliente abre a área
dele, o backend gera uma URL assinada nova (válida por 1 hora, por padrão)
só pro arquivo dele. É essa URL temporária que aparece na página, nunca o
endereço fixo do arquivo.

Requer: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME
(pega tudo isso no painel do Cloudflare, em R2 > Manage API tokens).
"""

import os

import boto3
from botocore.client import Config

R2_ACCOUNT_ID = os.environ["R2_ACCOUNT_ID"]
R2_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
R2_BUCKET_NAME = os.environ["R2_BUCKET_NAME"]

_client = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)


def subir_arquivo(caminho_local: str, chave_destino: str) -> str:
    """
    Sobe um arquivo local pro R2.
    chave_destino é o 'caminho' dentro do bucket — ex: 'relatorios/<id>/relatorio.pdf'.
    Retorna a própria chave, pra salvar no banco.
    """
    _client.upload_file(caminho_local, R2_BUCKET_NAME, chave_destino)
    return chave_destino


def gerar_url_temporaria(chave: str, expira_em_segundos: int = 3600) -> str:
    """Gera uma URL assinada e temporária pra um arquivo já armazenado."""
    return _client.generate_presigned_url(
        "get_object",
        Params={"Bucket": R2_BUCKET_NAME, "Key": chave},
        ExpiresIn=expira_em_segundos,
    )
