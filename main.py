# -*- coding: utf-8 -*-
"""
main.py — Ponto de entrada do Projeto TCC
==========================================
Executa o pipeline completo em sequência:

    Etapa 1 — Coleta de posts do Facebook (opcional, requer credenciais)
    Etapa 2 — Pré-processamento NLP dos textos coletados
    Etapa 3 — Classificação de crimes com Naive Bayes / SVM
    Etapa 4 — Servidor Flask com mapa de calor dos crimes

Uso básico (apenas classificação + mapa, sem coleta):
    python main.py

Uso completo (com coleta do Facebook):
    python main.py --coleta

Pular etapas individualmente:
    python main.py --skip-coleta --skip-processamento

Subir apenas o mapa:
    python main.py --apenas-mapa

Variáveis de ambiente necessárias para coleta:
    FB_APP_ID       — ID do app do Facebook
    FB_APP_SECRET   — Segredo do app do Facebook

Variável para o mapa:
    GOOGLEMAPS_KEY  — Chave da API do Google Maps
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import nltk
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env na raiz do projeto
load_dotenv(Path(__file__).parent / ".env")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("tcc_pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
COLETOR_DIR = BASE_DIR / "Coletor"
MAP_DIR = BASE_DIR / "Map"

SCRIPTS = {
    "coleta":         COLETOR_DIR / "coletorFacebook.py",
    "processamento":  COLETOR_DIR / "process.py",
    "classificacao":  COLETOR_DIR / "classificador.py",
    "mapa":           MAP_DIR / "Map.py",
}


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def _separador(titulo: str):
    linha = "=" * 60
    logger.info(linha)
    logger.info("  %s", titulo)
    logger.info(linha)


def _executar_script(nome: str, caminho: Path) -> bool:
    """
    Executa um script Python como subprocesso.
    Retorna True se bem-sucedido, False em caso de erro.
    """
    if not caminho.exists():
        logger.error("Script não encontrado: %s", caminho)
        return False

    logger.info("Iniciando: %s", caminho.name)
    inicio = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(caminho)],
            cwd=str(caminho.parent),
            check=True,
            text=True,
            encoding="utf-8",
        )
        duracao = time.time() - inicio
        logger.info("✓ '%s' concluído em %.1f s.", nome, duracao)
        return True

    except subprocess.CalledProcessError as exc:
        logger.error("✗ '%s' falhou (código %d).", nome, exc.returncode)
        return False

    except FileNotFoundError:
        logger.error("Python não encontrado: %s", sys.executable)
        return False


def _verificar_env_vars(variaveis: list) -> bool:
    """Verifica se as variáveis de ambiente necessárias estão definidas."""
    ausentes = [v for v in variaveis if not os.environ.get(v)]
    if ausentes:
        logger.warning(
            "Variáveis de ambiente não definidas: %s",
            ", ".join(ausentes),
        )
        logger.warning(
            "Defina-as antes de executar ou use --skip-coleta para pular a coleta."
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Etapas do pipeline
# ---------------------------------------------------------------------------

def etapa_coleta() -> bool:
    _separador("ETAPA 1 — Coleta de posts (Facebook Graph API)")

    if not _verificar_env_vars(["FB_APP_ID", "FB_APP_SECRET"]):
        logger.warning("Pulando coleta por falta de credenciais.")
        return False

    return _executar_script("coleta", SCRIPTS["coleta"])


def etapa_processamento() -> bool:
    _separador("ETAPA 2 — Pré-processamento NLP")
    return _executar_script("processamento", SCRIPTS["processamento"])


def etapa_classificacao() -> bool:
    _separador("ETAPA 3 — Classificação de crimes")
    return _executar_script("classificacao", SCRIPTS["classificacao"])


def etapa_mapa():
    _separador("ETAPA 4 — Servidor Flask (Mapa de crimes)")

    if not os.environ.get("GOOGLEMAPS_KEY"):
        logger.warning(
            "GOOGLEMAPS_KEY não definida. "
            "O mapa será exibido sem tiles do Google Maps."
        )
    script_mapa = Path(__file__).parent / "Map" / "Map.py"
    if not script_mapa.exists():
        logger.error("Script do mapa não encontrado em: %s", script_mapa)
        return False

    logger.info("Iniciando servidor Flask em http://127.0.0.1:5000")
    logger.info("Pressione Ctrl+C para encerrar.")

    try:
        subprocess.run(
            [sys.executable, str(SCRIPTS["mapa"])],
            cwd=str(script_mapa.parent),
            check=True,
            text=True,
            encoding="utf-8",
        )
    except KeyboardInterrupt:
        logger.info("Servidor encerrado pelo usuário.")
    except subprocess.CalledProcessError as exc:
        logger.error("Servidor Flask falhou (código %d).", exc.returncode)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pipeline completo do Projeto TCC — Classificador de Crimes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--coleta",
        action="store_true",
        help="Executa a coleta de posts do Facebook (requer credenciais).",
    )
    parser.add_argument(
        "--skip-processamento",
        action="store_true",
        help="Pula a etapa de pré-processamento.",
    )
    parser.add_argument(
        "--skip-classificacao",
        action="store_true",
        help="Pula a etapa de classificação.",
    )
    parser.add_argument(
        "--apenas-mapa",
        action="store_true",
        help="Pula todas as etapas e inicia apenas o servidor do mapa.",
    )
    parser.add_argument(
        "--sem-mapa",
        action="store_true",
        help="Executa o pipeline mas não sobe o servidor Flask.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# NLTK
# ---------------------------------------------------------------------------

def baixar_recursos_nltk():
    """Baixa os recursos do NLTK necessários para o pipeline."""
    _separador("NLTK — Download de recursos")
    recursos = [
        ("stopwords",                  "Stopwords em português"),
        ("wordnet",                    "WordNet para lematização"),
        ("averaged_perceptron_tagger", "POS Tagger"),
        ("maxent_ne_chunker",          "Chunker para NER"),
        ("words",                      "Corpus de palavras"),
        ("floresta",                   "Corpus Floresta (PT) para spell check"),
        ("punkt",                      "Tokenizador de sentenças"),
        ("punkt_tab",                  "Tokenizador de sentenças (tabular)"),
    ]
    for recurso, descricao in recursos:
        logger.info("Baixando: %s (%s)...", recurso, descricao)
        nltk.download(recurso, quiet=True)
    logger.info("✓ Recursos do NLTK prontos.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = _parse_args()

    logger.info("=" * 60)
    logger.info("  PROJETO TCC — Pipeline de Classificação de Crimes")
    logger.info("=" * 60)
    logger.info("Log salvo em: tcc_pipeline.log")

    resultados = {}

    if args.apenas_mapa:
        etapa_mapa()
        return

    # Etapa 1 — Coleta (opcional, ativada via flag)
    if args.coleta:
        resultados["coleta"] = etapa_coleta()
    else:
        logger.info("Coleta ignorada. Use --coleta para ativá-la.")

    # Etapa 2 — Pré-processamento
    if not args.skip_processamento:
        resultados["processamento"] = etapa_processamento()
        if not resultados["processamento"]:
            logger.warning("Pré-processamento falhou; continuando mesmo assim...")
    else:
        logger.info("Pré-processamento ignorado (--skip-processamento).")

    # Etapa 3 — Classificação
    if not args.skip_classificacao:
        resultados["classificacao"] = etapa_classificacao()
        if not resultados["classificacao"]:
            logger.error(
                "Classificação falhou. Verifique os CSVs em Coletor/data/ e os logs acima."
            )
    else:
        logger.info("Classificação ignorada (--skip-classificacao).")

    # Resumo
    _separador("RESUMO DO PIPELINE")
    for etapa, ok in resultados.items():
        status = "✓ OK" if ok else "✗ FALHOU"
        logger.info("  %-20s %s", etapa, status)

    # Etapa 4 — Mapa (bloqueante, por último)
    if not args.sem_mapa:
        etapa_mapa()
    else:
        logger.info("Servidor do mapa ignorado (--sem-mapa).")
        logger.info("Para iniciar o mapa manualmente: python Map/Map.py")


if __name__ == "__main__":
    main()
