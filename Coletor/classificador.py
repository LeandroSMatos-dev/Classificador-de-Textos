# -*- coding: utf-8 -*-
"""
Classificador de crimes em textos de redes sociais.
Utiliza Naive Bayes (NLTK) com suporte a outros modelos via scikit-learn.

Fontes originais:
  https://www.ravikiranj.net/posts/2012/code/how-build-twitter-sentiment-analyzer/
  http://www.laurentluce.com/posts/twitter-sentiment-analysis-using-python-and-nltk/
  https://pythonprogramming.net/sklearn-scikit-learn-nltk-tutorial/
  http://www.nltk.org/book/ch06.html
"""

import re
import csv
import logging
import collections
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import nltk
from nltk.metrics import precision, recall, f_measure
from nltk.metrics import ConfusionMatrix
from nltk.classify.scikitlearn import SklearnClassifier
from sklearn.naive_bayes import BernoulliNB
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report

# -- Conexão com MongoDB comentada: resultados agora são gravados em arquivo .txt --
# import pymongo
# from pymongo import MongoClient

# ---------------------------------------------------------------------------
# Configuração de logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
STOPWORDS_FILE = DATA_DIR / "stopwords_pt-BR.txt"
TREINO_CSV = DATA_DIR / "baseTreino.csv"
TESTE_CSV = DATA_DIR / "newBaseTestes.csv"

# Arquivo de saída com os resultados da classificação
RESULTADO_TXT = DATA_DIR / "resultados_classificacao.txt"

CATEGORIAS = {
    "1": "Roubo",
    "2": "Homicídio",
    "3": "Tráfico",
    "4": "Crime não categorizado",
    "5": "Não representa um crime",
}

# ---------------------------------------------------------------------------
# Pré-processamento
# ---------------------------------------------------------------------------

def pre_processar_texto(tweet: str) -> str:
    """Normaliza o texto do tweet para extração de características."""
    tweet = tweet.lower()
    tweet = re.sub(r"(www\.[^\s]+)|(https?://[^\s]+)", "URL", tweet)
    tweet = re.sub(r"@[^\s]+", "AT_USER", tweet)
    tweet = re.sub(r"\s+", " ", tweet)
    tweet = re.sub(r"#([^\s]+)", r"\1", tweet)
    tweet = tweet.strip("'\"")
    return tweet


def remover_repeticao(palavra: str) -> str:
    """Remove sequências de letras repetidas. Ex.: 'leeeeento' → 'leento'."""
    return re.sub(r"(.)\1{1,}", r"\1\1", palavra, flags=re.DOTALL)


def carregar_stopwords() -> List[str]:
    """Carrega stopwords do NLTK + arquivo customizado."""
    stopwords = list(nltk.corpus.stopwords.words("portuguese"))
    stopwords += ["AT_USER", "URL"]

    try:
        with open(STOPWORDS_FILE, encoding="utf-8") as fp:
            stopwords += [line.strip() for line in fp if line.strip()]
    except FileNotFoundError:
        logger.warning("Arquivo de stopwords não encontrado: %s", STOPWORDS_FILE)

    return stopwords


# Cache para não recarregar stopwords a cada chamada
_STOPWORDS: List[str] = []

def get_stopwords() -> List[str]:
    global _STOPWORDS
    if not _STOPWORDS:
        _STOPWORDS = carregar_stopwords()
    return _STOPWORDS


def extrair_vetor(tweet: str) -> List[str]:
    """Retorna vetor de características de um tweet pré-processado."""
    stopwords = get_stopwords()
    vetor = []
    for palavra in tweet.split():
        palavra = remover_repeticao(palavra)
        palavra = palavra.strip("'\"?,.")
        if (
            palavra in stopwords
            or not re.match(r"^[a-zA-Z][a-zA-Z0-9]*$", palavra)
            or len(palavra) <= 2
        ):
            continue
        vetor.append(palavra.lower())
    return vetor

# ---------------------------------------------------------------------------
# Carregamento de dados
# ---------------------------------------------------------------------------

def carregar_csv(caminho: Path) -> Tuple[List[Tuple], List[str]]:
    """
    Lê CSV com colunas [sentimento, texto].
    Retorna (lista de (vetor, sentimento), vocabulário único).
    """
    registros: List[Tuple] = []
    vocabulario: List[str] = []

    with open(caminho, encoding="utf-8", newline="") as f:
        leitor = csv.reader(f, delimiter=",", quotechar="|")
        for linha in leitor:
            if len(linha) < 2:
                continue
            sentimento, texto = linha[0], linha[1]
            texto_proc = pre_processar_texto(texto)
            vetor = extrair_vetor(texto_proc)
            vocabulario.extend(vetor)
            registros.append((vetor, sentimento))

    vocabulario = list(set(vocabulario))
    return registros, vocabulario


# ---------------------------------------------------------------------------
# Classificação
# ---------------------------------------------------------------------------

def criar_extrator(vocabulario: List[str]):
    """Retorna função de extração de características baseada no vocabulário."""
    vocab_set = set(vocabulario)

    def extrator(tweet: List[str]) -> dict:
        palavras = set(tweet)
        return {f"contains({p})": (p in palavras) for p in vocab_set}

    return extrator


def classificar_e_salvar(classificador, tweets: List[Tuple], extrator) -> List[dict]:
    """
    Classifica os tweets e grava os resultados em arquivo de texto.

    -- Conexão com MongoDB removida --
    Antes o resultado era persistido com:
        client = MongoClient("localhost", 27017)
        colecao = client.classificador.crimesClassificados
        colecao.insert_one({"categoria": categoria, "texto": texto})
    Agora os resultados são retornados como lista e gravados em .txt.
    """
    resultados = []

    for vetor, _ in tweets:
        resultado = classificador.classify(extrator(vetor))
        categoria = CATEGORIAS.get(resultado, "Desconhecido")
        texto = " ".join(vetor)
        resultados.append({"categoria": categoria, "texto": texto})

    # Grava em arquivo de texto
    with open(RESULTADO_TXT, "w", encoding="utf-8") as f:
        f.write(f"RESULTADOS DA CLASSIFICAÇÃO\n")
        f.write(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total de registros: {len(resultados)}\n")
        f.write("=" * 60 + "\n\n")

        for i, item in enumerate(resultados, start=1):
            f.write(f"[{i}] Categoria : {item['categoria']}\n")
            f.write(f"     Texto     : {item['texto']}\n\n")

    logger.info("Resultados gravados em: %s", RESULTADO_TXT)
    return resultados


def avaliar_por_classe(classificador, conjunto_teste, extrator):
    """Calcula precisão, recall e F1 por classe."""
    refsets = collections.defaultdict(set)
    testsets = collections.defaultdict(set)

    for i, (feats, label) in enumerate(conjunto_teste):
        refsets[label].add(i)
        observado = classificador.classify(extrator(feats))
        testsets[observado].add(i)

    for classe, nome in CATEGORIAS.items():
        p = precision(refsets[classe], testsets[classe])
        r = recall(refsets[classe], testsets[classe])
        f = f_measure(refsets[classe], testsets[classe])
        logger.info(
            "%-30s | Precisão: %.3f | Recall: %.3f | F1: %.3f",
            nome,
            p or 0,
            r or 0,
            f or 0,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("Carregando base de treino: %s", TREINO_CSV)
    tweets_treino, vocabulario = carregar_csv(TREINO_CSV)

    logger.info("Carregando base de teste: %s", TESTE_CSV)
    tweets_teste, _ = carregar_csv(TESTE_CSV)

    extrator = criar_extrator(vocabulario)

    logger.info("Extraindo características...")
    conjunto_treino = nltk.classify.util.apply_features(extrator, tweets_treino)
    conjunto_teste_features = nltk.classify.util.apply_features(extrator, tweets_teste)

    # --- Naive Bayes (NLTK) ---
    logger.info("Treinando Naive Bayes...")
    nb = nltk.NaiveBayesClassifier.train(conjunto_treino)
    acuracia_nb = nltk.classify.util.accuracy(nb, conjunto_teste_features)
    logger.info("Acurácia Naive Bayes: %.4f", acuracia_nb)

    # --- BernoulliNB (sklearn) ---
    logger.info("Treinando BernoulliNB...")
    bnb = SklearnClassifier(BernoulliNB())
    bnb.train(conjunto_treino)
    acuracia_bnb = nltk.classify.accuracy(bnb, conjunto_teste_features)
    logger.info("Acurácia BernoulliNB: %.4f", acuracia_bnb)

    # --- LinearSVC ---
    logger.info("Treinando LinearSVC...")
    svc = SklearnClassifier(LinearSVC(class_weight='balanced'), sparse=False)
    svc.train(conjunto_treino)
    acuracia_svc = nltk.classify.accuracy(svc, conjunto_teste_features)
    logger.info("Acurácia LinearSVC: %.4f", acuracia_svc)

    # --- Métricas por classe (melhor modelo) ---
    melhor = max(
        [(nb, acuracia_nb, "Naive Bayes"), (bnb, acuracia_bnb, "BernoulliNB"), (svc, acuracia_svc, "LinearSVC")],
        key=lambda x: x[1],
    )
    logger.info("Melhor modelo: %s (%.4f) — métricas por classe:", melhor[2], melhor[1])
    avaliar_por_classe(melhor[0], tweets_teste, extrator)

    # --- Salvar resultados em arquivo de texto (MongoDB comentado) ---
    # -- Bloco MongoDB original --
    # logger.info("Salvando resultados no MongoDB...")
    # client = MongoClient("localhost", 27017)
    # colecao = client.classificador.crimesClassificados
    # classificar_e_salvar(melhor[0], tweets_teste, extrator, colecao)
    # ------------------------------------
    logger.info("Salvando resultados em arquivo de texto...")
    classificar_e_salvar(melhor[0], tweets_teste, extrator)
    logger.info("Concluído.")


if __name__ == "__main__":
    main()
