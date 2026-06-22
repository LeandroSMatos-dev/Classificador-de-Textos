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
from flask import Flask, render_template
import folium

# Carrega variaveis de ambiente do .env na raiz do projeto
#load_dotenv(Path(__file__).parent.parent / ".env")

# -- Importações MongoDB comentadas --
# from flask_pymongo import PyMongo
# MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/classificador")

from flask_googlemaps import GoogleMaps, Map

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates")


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
    marcadores = []
    categoria_atual = ""
    texto_atual = ""

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
                    # O folium lida bem com strings, mas limpamos aspas para garantir
                    t_limpo = texto_atual[:120].replace('"', "'").replace("\n", " ")
                    c_limpa = categoria_atual.replace('"', "'")

                    infobox = f"<b>{c_limpa}</b><br>{t_limpo}..."
                    marcadores.append({
                        "infobox": infobox,
                        "lat": LAT_CENTRO,
                        "lng": LNG_CENTRO,
                    })
                    categoria_atual = ""
                    texto_atual = ""
    return marcadores


@app.route("/", methods=["GET"])
def fullmap():
    marcadores = ler_marcadores()

    # Cria o mapa Leaflet
    mapa = folium.Map(location=[LAT_CENTRO, LNG_CENTRO], zoom_start=13)

    # Adiciona os marcadores com segurança
    for m in marcadores:
        folium.Marker(
            location=[m["lat"], m["lng"]],
            popup=folium.Popup(m["infobox"], max_width=300)
        ).add_to(mapa)

    # Retorna o mapa gerado diretamente como HTML puro
    return mapa._repr_html_()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, use_reloader=debug)
