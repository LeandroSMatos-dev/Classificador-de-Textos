# -*- coding: utf-8 -*-
"""
Corretor ortográfico simples baseado em distância de edição,
treinado com o corpus Floresta do NLTK.

Baseado no algoritmo de Peter Norvig (https://norvig.com/spell-correct.html).
"""

import collections
from string import ascii_lowercase as ALPHABET

import nltk

# Treina o modelo de frequência com o corpus Floresta (PT)
_NWORDS: collections.Counter = collections.Counter(nltk.corpus.floresta.words())


def _edits1(word: str):
    """Gera todas as edições a 1 distância de 'word'."""
    for i, letra in enumerate(word):
        inicio, fim = word[:i], word[i + 1:]
        yield inicio + fim                          # deleção
        if fim:
            yield inicio + fim[0] + letra + fim[1:]  # transposição
        else:
            for outro in ALPHABET:
                yield inicio + letra + outro        # inserção no final
        for outro in ALPHABET:
            yield inicio + outro + fim              # substituição
            yield inicio + outro + letra + fim      # inserção antes


def _edits2(word: str):
    """Gera todas as edições a 2 distâncias de 'word'."""
    for e1 in _edits1(word):
        yield from _edits1(e1)


def _known(words) -> set:
    """Filtra apenas palavras presentes no vocabulário."""
    return {w for w in words if w in _NWORDS}


def correct(word: str) -> str:
    """
    Retorna a correção mais provável para 'word'.
    Prioridade: palavra original > edição 1 > edição 2 > palavra original.
    """
    candidatos = (
        _known([word])
        or _known(_edits1(word))
        or _known(_edits2(word))
        or {word}
    )
    return max(candidatos, key=_NWORDS.get)
