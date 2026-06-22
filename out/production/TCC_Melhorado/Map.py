# -*- coding: utf-8 -*-
"""
Servidor Flask que exibe um mapa Google com crimes classificados.

Os marcadores são lidos do arquivo de resultados gerado pelo classificador
(Coletor/data/resultados_classificacao.txt) em vez do MongoDB.

Variável de ambiente necessária:
    GOOGLEMAPS_KEY  — chave da API do Google Maps

-- Conexão com MongoDB comentada --
Antes os dados vinham de:
    mongo.db.nerClassificados.find(...)
Agora são lidos do arquivo de texto de saída do classificador.
"""

import csv
import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template

# Carrega variaveis de ambiente do .env na raiz do projeto
load_dotenv(Path(__file__).parent.parent / ".env")

# -- Importações MongoDB comentadas --
# from flask_pymongo import PyMongo
# MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/classificador")

from flask_googlemaps import GoogleMaps, Map

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates")

GOOGLEMAPS_KEY = os.environ.get("GOOGLEMAPS_KEY", "")
app.config["GOOGLEMAPS_KEY"] = GOOGLEMAPS_KEY
GoogleMaps(app, key=GOOGLEMAPS_KEY)

if not GOOGLEMAPS_KEY:
    logger.warning(
        "GOOGLEMAPS_KEY não definida. "
        "Defina a variável de ambiente antes de iniciar o servidor."
    )

# -- Configuração MongoDB comentada --
# app.config["MONGO_DBNAME"] = "classificador"
# app.config["MONGO_URI"] = MONGO_URI


# -- Instância PyMongo comentada --
# mongo = PyMongo(app)

# Arquivo gerado pelo classificador
RESULTADO_TXT = (
        Path(__file__).parent.parent / "Coletor" / "data" / "resultados_classificacao.txt"
)

# Coordenadas fixas de Aracaju (centro do mapa)
LAT_CENTRO = -10.9680346
LNG_CENTRO = -37.0580638


def ler_marcadores() -> list:
    """
    Lê os resultados do arquivo .txt gerado pelo classificador e
    retorna marcadores para o mapa.

    -- Lógica MongoDB original comentada --
    # crimes = mongo.db.nerClassificados.find({}, {"_id": 0, "infobox": 1, "lat": 1, "lng": 1})
    # marcadores = [
    #     {"infobox": doc["infobox"], "lat": doc["lat"], "lng": doc["lng"]}
    #     for doc in crimes
    #     if "lat" in doc and "lng" in doc
    # ]
    # ----------------------------------------
    Como o arquivo .txt não possui coordenadas individuais por post
    (o NER/geocoding era feito em outro módulo), os registros são
    exibidos agrupados no centro de Aracaju com o texto como infobox.
    Para coordenadas reais, integre o módulo NER.py com geocoding.
    """
    if not RESULTADO_TXT.exists():
        logger.warning("Arquivo de resultados não encontrado: %s", RESULTADO_TXT)
        return []

    marcadores = []
    categoria_atual = ""
    texto_atual = ""

    # Define o caminho dinamicamente subindo uma pasta a partir de Map.py
    BASE_DIR = Path(__file__).parent.parent
    caminho_resultados = BASE_DIR / "Coletor" / "data" / "resultados_classificacao.txt"

    if not caminho_resultados.exists():
        logger.error(f"Arquivo não encontrado em: {caminho_resultados}")
        return marcadores

    with open(caminho_resultados, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha.startswith("[") and "Categoria" in linha:
                categoria_atual = linha.split(":", 1)[-1].strip()
            elif "Texto     :" in linha:
                texto_atual = linha.split(":", 1)[-1].strip()
                if categoria_atual and texto_atual:
                    # Remove quebras de linha físicas que destroem o JS
                    texto_limpo = texto_atual[:120].replace("\n", " ").replace("\r", " ")
                    # Escapa aspas duplas para não fechar a string do JS antes da hora
                    texto_limpo = texto_limpo.replace('"', '\\"')
                    infobox = f"<b>{categoria_atual}</b><br>{texto_limpo}..."
                    marcadores.append({
                        "infobox": infobox,
                        "lat": LAT_CENTRO,
                        "lng": LNG_CENTRO,
                    })
                    categoria_atual = ""
                    texto_atual = ""

    logger.info("%d marcadores carregados do arquivo de resultados.", len(marcadores))
    return marcadores


@app.route("/", methods=["GET"])
def fullmap():
    """Renderiza o mapa com todos os crimes classificados."""
    marcadores = ler_marcadores()

    mapa = Map(
        identifier="fullmap",
        varname="fullmap",
        style=(
            "height:100%;"
            "width:100%;"
            "top:0;"
            "left:0;"
            "position:absolute;"
            "z-index:200;"
        ),
        lat=LAT_CENTRO,
        lng=LNG_CENTRO,
        markers=marcadores,
    )

    return render_template("fullmap.html", fullmap=mapa)


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, use_reloader=debug)
