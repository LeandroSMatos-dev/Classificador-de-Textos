# O que é esse projeto

Classificador de crimes em textos de redes sociais (Facebook/Twitter),
com visualização geoespacial via Flask + Google Maps. 

Esse prejto foi feito e apresentado no meu TCC e ficou parado por muitos anos. Decidi atualizar ele para versão
mais nova do Python e deixá-lo em modo funcional e armazená-lo no Github para versionamento.

---

## Melhorias aplicadas

### 1. Migração para Python 3
- Removidos todos os `print` sem parênteses (sintaxe Python 2).
- Substituído `urllib2` por `requests`.
- `StringIO` do Python 2 trocado pela versão padrão do Python 3.
- `open()` com `encoding="utf-8"` no lugar de `codecs.open()`.
- Iteradores `.iteritems()` → `.items()`.
- `csv.reader(open(..., 'rb'))` → `csv.reader(open(..., encoding='utf-8'))`.

### 2. Segurança —
- API keys lidos via variáveis de ambiente (`FB_APP_ID`, `FB_APP_SECRET`, `GOOGLEMAPS_KEY`).
- Arquivo `.env` (não versionado) com essas variáveis.

### 3. Qualidade de código
- **classificador.py**: variáveis globais mutáveis eliminadas; lógica encapsulada
  em funções bem definidas com tipos anotados; dicionário `CATEGORIAS` substitui
  o bloco `if/elif` repetitivo; métricas por classe ativadas por padrão.
- **preprocessing.py**: classe `PreProcessing` reescrita com `__init__` recebendo
  o texto; método `_sync_text()` interno evita código duplicado; `part_of_speech_tagging`
  e `padronizacaoInternetes` marcados como `NotImplementedError` com docstring clara.
- **spellcorrect.py**: corrigido bug crítico — `self.NWORDS.get` em função standalone
  trocado por referência direta à variável do módulo `_NWORDS`.
- **coletorFacebook.py**: retry com backoff exponencial; encoding explícito no CSV;
  tratamento de exceções genérico corrigido; `insert` depreciado → `insert_one`.
- **Map.py**: `flask.ext.pymongo` (removido no Flask 1+) → `flask_pymongo`;
  chave de API via variável de ambiente; `debug=True` controlado por env var.

### 4. Logging
- `print` de status trocados por `logging` em todos os arquivos.
- Nível configurável via código ou variável `LOG_LEVEL`.

### 5. Organização
- `requirements.txt` criado listando todas as dependências com versões mínimas.
- Caminhos de arquivo usando `pathlib.Path` em vez de strings relativas brutas.

---

## Estrutura

```
TCC_Melhorado/
├── Coletor/
│   ├── classificador.py     # classificação de textos
│   ├── coletorFacebook.py   # coleta via Graph API
│   ├── preprocessing.py     # pipeline de NLP
│   ├── process.py           # orquestrador de pré-processamento
│   ├── spellcorrect.py      # corretor ortográfico
│   └── data/                # CSVs e stopwords
├── Map/
│   ├── Map.py               # servidor Flask com mapa
│   └── templates/
│       └── fullmap.html
└── requirements.txt
```

## Como executar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Definir variáveis de ambiente
export FB_APP_ID="seu_id"
export FB_APP_SECRET="seu_secret"
export GOOGLEMAPS_KEY="sua_chave"

# 3. Coletar dados
python Coletor/coletorFacebook.py

# 4. Pré-processar
python Coletor/process.py

# 5. Classificar
python Coletor/classificador.py

# 6. Visualizar no mapa
python Map/Map.py
```

## Como rodar a classe Main.py

```bash
# Modo padrão: pré-processamento + classificação + abre o mapa
python main.py

# Com coleta do Facebook (requer FB_APP_ID e FB_APP_SECRET no ambiente)
python main.py --coleta

# Só classificação, sem subir o mapa
python main.py --sem-mapa

# Só o mapa (dados já estão no MongoDB)
python main.py --apenas-mapa

# Pular etapas individualmente
python main.py --skip-processamento --skip-classificacao
```

## Mudanças futuras
- Migrar da API de mapas do Google para uma free 
- Migrar de coletor de texto do Facebook para Twitter
