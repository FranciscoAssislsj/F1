# 🏎️ F1 — Dashboard de Fórmula 1 com Streamlit

Projeto de dados de Fórmula 1 que consome a [API OpenF1](https://openf1.org/docs/),
processa os dados em um pipeline **ingestão → transformação → validação → carga**,
grava arquivos Parquet particionados e os apresenta em um **dashboard Streamlit**
com as voltas mais rápidas de cada Grande Prêmio.

## Visão geral

```
API OpenF1 ──► Ingestão ──► Transformação ──► Validação ──► Parquet (data/) ──► Dashboard Streamlit
```

- **Pipeline (CLI):** baixa sessões de corrida desde 2023 e grava Parquet em
  `data/<entidade>/<partição>/part.parquet`. Reexecutar a mesma sessão sobrescreve
  a partição (idempotente).
- **Dashboard (Streamlit):** lê os Parquet e mostra as 5 voltas mais rápidas por
  circuito, com filtros de **ano** e **tipo de sessão**.

Entidades coletadas: `meetings`, `sessions`, `drivers`, `laps`, `stints`, `pit`,
`weather`, `session_result`. Telemetria pesada e tempo real ficam fora do escopo.

## API OpenF1

[OpenF1](https://openf1.org/) é uma API aberta e gratuita com dados históricos e em
tempo real de F1 (sessões, pilotos, voltas, pit stops, clima, resultados etc.).

- Base URL: `https://api.openf1.org/v1`
- Documentação: <https://openf1.org/docs/>
- O cliente HTTP do projeto aplica **retry** e **rate limit** (`RATE_LIMIT_DELAY_S`)
  para respeitar os limites da API.

## Tecnologias

| Tecnologia | Uso |
|---|---|
| Python 3.13 | Linguagem |
| [Streamlit](https://streamlit.io/) | Dashboard web |
| pandas | Transformação e análise |
| PyArrow | Leitura/escrita de Parquet |
| requests | Cliente HTTP da API OpenF1 |
| [Poetry](https://python-poetry.org/) | Dependências e ambiente virtual |
| pytest, pytest-cov, responses | Testes e cobertura |
| Ruff | Lint e formatação |
| MkDocs Material + mkdocstrings | Documentação |
| taskipy | Atalhos de tarefas |

## Instalação

Requisitos: Python 3.13 e Poetry.

```bash
poetry config virtualenvs.in-project true --local
poetry install --with dev,docs
cp .env.example .env            # opcional; os padrões já funcionam
```

### Configuração (`.env`)

| Variável | Padrão | Descrição |
|---|---|---|
| `OPENF1_BASE_URL` | `https://api.openf1.org/v1` | URL base da API |
| `API_TIMEOUT_S` | `30` | Timeout das requisições (s) |
| `RATE_LIMIT_DELAY_S` | `2.0` | Intervalo entre requisições (s) |
| `DATA_DIR` | `data` | Diretório de saída dos Parquet |

## Executar

### 1. Carregar os dados (pipeline)

```bash
poetry run python -m f1.pipelines.cli --year 2024
poetry run python -m f1.pipelines.cli --session-key 9158
```

### 2. Abrir o dashboard

```bash
poetry run streamlit run src/f1/dashboard.py
# ou
poetry run task dashboard
```

## Estrutura do projeto

```
src/f1/
  dashboard.py        # Aplicação Streamlit (entry point)
  config/             # Settings carregadas do ambiente (.env)
  core/               # Modelos, schemas, interfaces e exceções
  ingestion/          # Extratores e retry
  integrations/       # Cliente OpenF1, escrita e leitura de Parquet
  transformation/     # Limpeza, entidades e métricas (voltas mais rápidas)
  validation/         # Checagens de qualidade dos dados
  pipelines/          # Pipeline de corrida e CLI
  utils/              # Logger
tests/
  unit/               # Testes unitários (cobertura >= 50%)
  integration/        # Testes contra a API real (marcados como integration)
  fixtures/           # Respostas JSON de exemplo
docs/                 # Documentação com MkDocs Material
data/                 # Parquet gerados pelo pipeline
```

## Testes

```bash
poetry run pytest tests/unit/ --cov=src/f1 --cov-report=term-missing --cov-fail-under=50
# ou
poetry run task test
```

Os testes unitários usam fixtures e `responses` para simular a API, sem acesso à rede.
Os testes de `tests/integration/` dependem da API real e são marcados com
`@pytest.mark.integration`.

## Lint

```bash
poetry run ruff check .
poetry run ruff format --check .
```

Para formatar automaticamente: `poetry run task format`.

## Documentação

```bash
poetry run task docs          # servidor local com live reload
poetry run task docs-build    # build estrito (mkdocs build --strict)
```

Conteúdo em `docs/`: arquitetura, pipelines, desenvolvimento, testes, contribuição e
referência da API. Os padrões de desenvolvimento estão em `.claude/SKILL.md`.

## Atalhos (taskipy)

| Comando | Ação |
|---|---|
| `poetry run task test` | Testes com cobertura |
| `poetry run task lint` | Lint com Ruff |
| `poetry run task format` | Formata o código |
| `poetry run task dashboard` | Abre o dashboard Streamlit |
| `poetry run task docs` | Serve a documentação |
| `poetry run task docs-build` | Build da documentação |

## Autor

Francisco de Assis — <franciscofut25@gmail.com>
