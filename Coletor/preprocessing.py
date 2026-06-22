# -*- coding: utf-8 -*-
"""
Módulo de pré-processamento de texto para NLP em português.
Compatível com Python 3. Remove dependência de StringIO do Python 2.
"""

import re
import string
import logging

import nltk
from nltk.stem.snowball import SnowballStemmer
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import TweetTokenizer
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def extract_entity_names(tree) -> list:
    """Extrai nomes de entidades de uma árvore de chunking do NLTK."""
    entity_names = []
    if hasattr(tree, "label") and tree.label:
        if tree.label() in ("NE", "NNP"):
            entity_names.append(" ".join(child[0] for child in tree))
        else:
            for child in tree:
                entity_names.extend(extract_entity_names(child))
    return entity_names


class PreProcessing:
    """
    Pipeline de pré-processamento de texto para tweets e posts em português.

    Uso típico:
        pp = PreProcessing("Texto aqui")
        pp.initial_processing()
        pp.stopwords()
        pp.stemming()
        resultado = pp.text
    """

    # Palavras a bloquear além das stopwords padrão do NLTK
    PALAVROES = frozenset(
        ["foda", "caralho", "porra", "puta", "merda", "cu", "foder", "viado", "cacete", "kkk"]
    )

    def __init__(self, text: str = ""):
        self._text = text
        self.tokens: list = []

    # ------------------------------------------------------------------
    # Propriedade text
    # ------------------------------------------------------------------

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str):
        self._text = value

    # ------------------------------------------------------------------
    # Etapas do pipeline
    # ------------------------------------------------------------------

    def initial_processing(self):
        """Remove HTML, URLs e tokeniza."""
        soup = BeautifulSoup(self._text, "html.parser")
        plain = soup.get_text()
        # Remove URLs
        plain = re.sub(r"(http://|https://|www\.)[^\s\"']+", " ", plain)
        self._text = plain.strip()
        self.tokens = self._tokenize()

    def _tokenize(self) -> list:
        tknzr = TweetTokenizer(strip_handles=True, reduce_len=True)
        return tknzr.tokenize(self._text)

    def lexical_diversity(self) -> float:
        """Razão vocabulário / total de palavras (0 se vazio)."""
        words = self._text.split()
        if not words:
            return 0.0
        return len(set(words)) / len(words)

    def stopwords(self):
        """Remove stopwords, palavrões e pontuação dos tokens."""
        sw = set(nltk.corpus.stopwords.words("portuguese")) | self.PALAVROES
        pontuacao = set(string.punctuation)
        self.tokens = [
            w for w in self.tokens
            if w.lower() not in sw and w not in pontuacao
        ]
        self._sync_text()

    def stemming(self):
        """Aplica stemming em português (Snowball)."""
        stemmer = SnowballStemmer("portuguese")
        self.tokens = [stemmer.stem(w) for w in self.tokens]
        self._sync_text()

    def lemmatization(self):
        """Aplica lematização (WordNet — melhor para inglês; usar stemming para PT)."""
        lemmatizer = WordNetLemmatizer()
        self.tokens = [lemmatizer.lemmatize(w, pos="v") for w in self.tokens]
        self._sync_text()

    def spell_checker(self):
        """Corrige ortografia usando enchant (requer dicionário pt_BR instalado)."""
        try:
            import enchant
        except ImportError:
            logger.warning("enchant não instalado; etapa de spell_checker ignorada.")
            return

        pt_dict = enchant.Dict("pt_BR")
        corrigidas = []
        for word in self.tokens:
            if not pt_dict.check(word):
                sugestoes = pt_dict.suggest(word)
                corrigidas.append(sugestoes[0] if sugestoes else word)
            else:
                corrigidas.append(word)
        self.tokens = corrigidas
        self._sync_text()

    def get_chunks(self) -> list:
        """Extrai entidades nomeadas do texto."""
        sentences = nltk.sent_tokenize(self._text)
        tokenized = [nltk.word_tokenize(s) for s in sentences]
        tagged = [nltk.pos_tag(s) for s in tokenized]
        chunked = nltk.ne_chunk_sents(tagged, binary=True)
        entities = []
        for tree in chunked:
            entities.extend(extract_entity_names(tree))
        return entities

    def remove_chunks(self):
        """Remove entidades nomeadas dos tokens."""
        chunks = set(self.get_chunks())
        self.tokens = [w for w in self.tokens if w not in chunks]
        self._sync_text()

    def untokenize(self, words: list = None) -> str:
        """
        Reconstrói o texto a partir de uma lista de palavras,
        respeitando espaçamento de pontuação.
        """
        words = words or self.tokens
        text = " ".join(words)
        text = text.replace("`` ", '"').replace(" ''", '"').replace(". . .", "...")
        text = text.replace(" ( ", " (").replace(" ) ", ") ")
        text = re.sub(r" ([.,:;?!%]+)([ '\"`])", r"\1\2", text)
        text = re.sub(r" ([.,:;?!%]+)$", r"\1", text)
        text = text.replace(" '", "'").replace(" n't", "n't").replace("can not", "cannot")
        text = text.replace(" ` ", " '")
        return text.strip()

    # ------------------------------------------------------------------
    # Auxiliares internos
    # ------------------------------------------------------------------

    def _sync_text(self):
        """Sincroniza self._text com os tokens atuais."""
        self._text = " ".join(self.tokens)
