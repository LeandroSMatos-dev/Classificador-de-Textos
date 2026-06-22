# -*- coding: utf-8 -*-
"""
Coletor de posts da API Graph do Facebook (v2.4).
Salva os dados em CSV.

ATENÇÃO: nunca coloque credenciais diretamente no código.
         Defina as variáveis de ambiente antes de executar:
             export FB_APP_ID="seu_app_id"
             export FB_APP_SECRET="seu_app_secret"

-- Conexão com MongoDB comentada --
A gravação paralela no MongoDB foi removida; todos os dados
são agora persistidos apenas no CSV de saída.
"""

import csv
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# -- Importações MongoDB comentadas --
# import pymongo
# from pymongo import MongoClient

import requests

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

APP_ID = os.environ.get("FB_APP_ID", "")
APP_SECRET = os.environ.get("FB_APP_SECRET", "")
ACCESS_TOKEN = f"{APP_ID}|{APP_SECRET}"
PAGE_ID = "AracajuAgoraNoticias"
API_BASE = "https://graph.facebook.com/v2.4"

# -- URI do MongoDB comentada (não utilizada) --
# MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")

OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Requisições
# ---------------------------------------------------------------------------

def _requisicao_com_retry(url: str, max_tentativas: int = 5) -> dict:
    """Faz GET na URL com retry exponencial. Retorna dict JSON."""
    espera = 5
    for tentativa in range(1, max_tentativas + 1):
        try:
            resposta = requests.get(url, timeout=30)
            resposta.raise_for_status()
            return resposta.json()
        except requests.RequestException as exc:
            logger.warning(
                "Tentativa %d/%d falhou para %s: %s",
                tentativa, max_tentativas, url, exc,
            )
            if tentativa == max_tentativas:
                raise
            time.sleep(espera)
            espera *= 2
    return {}


def obter_feed_pagina(page_id: str, token: str) -> dict:
    url = f"{API_BASE}/{page_id}/feed?access_token={token}"
    return _requisicao_com_retry(url)


# ---------------------------------------------------------------------------
# Processamento de status
# ---------------------------------------------------------------------------

def processar_status(status: dict) -> tuple:
    """Extrai campos relevantes de um post do Facebook."""
    status_id = status.get("id", "")
    mensagem = status.get("message", "")

    criado_em_str = status.get("created_time", "")
    if criado_em_str:
        criado_em = datetime.strptime(criado_em_str, "%Y-%m-%dT%H:%M:%S+0000")
        criado_em = criado_em.replace(tzinfo=timezone.utc) - timedelta(hours=3)  # BRT
        criado_em = criado_em.strftime("%Y-%m-%d %H:%M:%S")
    else:
        criado_em = ""

    return status_id, mensagem, criado_em


# ---------------------------------------------------------------------------
# Scraping principal
# ---------------------------------------------------------------------------

def coletar_posts(page_id: str, token: str):
    """Itera todas as páginas do feed e salva apenas no CSV."""
    if not APP_ID or not APP_SECRET:
        raise EnvironmentError(
            "Defina as variáveis de ambiente FB_APP_ID e FB_APP_SECRET antes de executar."
        )

    # -- Bloco MongoDB original comentado --
    # client = MongoClient(MONGO_URI)
    # colecao = client.facebook.coletor1
    # ----------------------------------------

    saida_csv = OUTPUT_DIR / f"{page_id}_facebook_statuses.csv"

    with open(saida_csv, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["status_id", "status_message", "status_published"])

        total = 0
        inicio = datetime.now()
        logger.info("Iniciando coleta de '%s' em %s", page_id, inicio)

        pagina = obter_feed_pagina(page_id, token)

        while True:
            for status in pagina.get("data", []):
                sid, msg, pub = processar_status(status)
                escritor.writerow([sid, msg, pub])

                # -- Inserção no MongoDB comentada --
                # try:
                #     colecao.insert_one({**status, "_page": page_id})
                # except pymongo.errors.DuplicateKeyError:
                #     pass
                # except Exception as exc:
                #     logger.error("Erro ao inserir status %s: %s", sid, exc)

                total += 1
                if total % 1000 == 0:
                    logger.info("%d posts coletados (até %s)", total, datetime.now())

            proxima = pagina.get("paging", {}).get("next")
            if not proxima:
                break
            pagina = _requisicao_com_retry(proxima)

    duracao = datetime.now() - inicio
    logger.info("Coleta concluída: %d posts em %s. CSV: %s", total, duracao, saida_csv)


if __name__ == "__main__":
    coletar_posts(PAGE_ID, ACCESS_TOKEN)
