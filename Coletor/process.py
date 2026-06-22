# -*- coding: utf-8 -*-
"""
Processa mensagens coletadas do Facebook aplicando o pipeline de NLP
e salva o resultado em CSV.

-- Conexão com MongoDB comentada --
Antes os textos pré-processados eram lidos e gravados no MongoDB.
Agora a entrada é lida do CSV coletado e a saída é gravada em um novo CSV.
"""

import csv
import logging
from pathlib import Path

# -- Importações MongoDB comentadas --
# from pymongo import MongoClient
# import pymongo

from preprocessing import PreProcessing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# -- URI do MongoDB comentada (não utilizada) --
# MONGO_URI = "mongodb://localhost:27017"

DATA_DIR = Path(__file__).parent / "data"

# Arquivo de entrada: CSV gerado pelo coletorFacebook.py
# (ou NER_file.csv como fallback para testes sem coleta)
ENTRADA_CSV = DATA_DIR / "NER_file.csv"

# Arquivo de saída com os textos pré-processados
SAIDA_CSV = DATA_DIR / "textos_processados.csv"


def processar_status(mensagem: str) -> str:
    """Aplica o pipeline completo de pré-processamento e retorna o texto final."""
    corpus = PreProcessing(mensagem)

    logger.debug("Processamento inicial...")
    corpus.initial_processing()

    logger.debug("Tokenizando...")
    # tokenização já ocorre em initial_processing via _tokenize()

    logger.debug("Removendo stopwords...")
    corpus.stopwords()

    logger.debug("Lematizando...")
    corpus.lemmatization()

    logger.debug("Untokenizando...")
    return corpus.untokenize()


def salvar_em_csv(texto_final: str, escritor) -> None:
    """
    Grava o texto processado no CSV de saída.

    -- Função MongoDB original comentada --
    # def salvar_no_mongo(texto_final: str, db) -> None:
    #     doc = {"word_final": texto_final}
    #     try:
    #         db.textosSite.insert_one(doc)
    #     except pymongo.errors.DuplicateKeyError:
    #         logger.debug("Texto duplicado, ignorado.")
    #     except Exception as exc:
    #         logger.error("Erro ao salvar no MongoDB: %s", exc)
    """
    escritor.writerow([texto_final])


def main():
    # -- Bloco MongoDB original comentado --
    # client = MongoClient(MONGO_URI)
    # db = client["facebook"]
    # colecao = db["aracajucomoeuvejo.facebook"]
    # query = {"message": {"$exists": True}}
    # projection = {"_id": 0, "message": 1, "id": 1, "created_time": 1}
    # documentos = list(colecao.find(query, projection))
    # ----------------------------------------

    # Lê os textos do CSV de entrada
    if not ENTRADA_CSV.exists():
        logger.error("Arquivo de entrada não encontrado: %s", ENTRADA_CSV)
        return

    with open(ENTRADA_CSV, encoding="utf-8", newline="") as f_entrada:
        leitor = csv.reader(f_entrada)
        cabecalho = next(leitor, None)  # pula cabeçalho se existir
        documentos = [{"message": linha[0]} for linha in leitor if linha]

    logger.info("Total de documentos a processar: %d", len(documentos))

    with open(SAIDA_CSV, "w", encoding="utf-8", newline="") as f_saida:
        escritor = csv.writer(f_saida)
        escritor.writerow(["texto_processado"])

        for i, doc in enumerate(documentos, start=1):
            mensagem = doc.get("message", "")
            if not mensagem:
                continue

            logger.info("Processando mensagem %d/%d...", i, len(documentos))
            texto_final = processar_status(mensagem)
            salvar_em_csv(texto_final, escritor)

    logger.info("Processamento concluído. Saída: %s", SAIDA_CSV)


if __name__ == "__main__":
    main()
