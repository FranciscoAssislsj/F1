# Plano — Pipeline de dados F1 (OpenF1)

## Context

O repositório `F1` tem apenas o esqueleto do Poetry (`pyproject.toml` com pacote `f1`, `src/f1/__init__.py`, `tests/__init__.py`, `.python-version` = 3.13.13) e dois documentos: `doc_api.md` (resumo da API OpenF1) e `SKILL.md` (padrões obrigatórios de Engenharia de Dados em Python). Este plano define como construir o projeto: um pipeline de **ingestão → transformação → validação → carga** de dados históricos de F1 (gratuitos, sem autenticação, desde 2023) da API OpenF1, seguindo integralmente o `SKILL.md`.

**Premissas (ajustar se discordar):**
- Escopo inicial: dados históricos de **sessões de corrida** (`meetings`, `sessions`, `drivers`, `laps`, `stints`, `pit`, `session_result`, `weather`). Telemetria pesada (`car_data`, `location`) e tempo real ficam fora do MVP.
- Destino: arquivos **Parquet** locais particionados por `session_key` (sem infraestrutura externa).
- Python `>=3.13` (já no `pyproject.toml`); `ruff target-version = "py313"` (o `py314` do SKILL.md é só exemplo).
- Pacote: `f1` (não renomear). Onde o SKILL.md diz `projeto`, ler `f1`.

## Restrições do SKILL.md que guiam tudo

Poetry é a única ferramenta (nunca `pip`); layout `src/f1/`; Ruff; pytest + cobertura ≥ 50% sobre `src/f1`; MkDocs Material com `mkdocs<2` e build `--strict`; transformações puras; timeout em toda chamada de rede; retry com backoff só para 429/5xx/timeout; pipelines idempotentes com `run_id`; sem segredos; branches + PR; CI. Só criar pastas com conteúdo real.

## Arquitetura (`src/f1/`)

| Módulo | Responsabilidade |
|---|---|
| `config/settings.py` | `Settings` (dataclass frozen, `from_env`): `OPENF1_BASE_URL`, `API_TIMEOUT_S`, `DATA_DIR`, `RATE_LIMIT_DELAY_S` |
| `core/` | `exceptions.py` (`TransientApiError`, `PermanentApiError`, `SchemaValidationError`), `models.py` (dataclasses), `interfaces.py` (`Protocol` `ApiClient`, `Sink`) |
| `integrations/openf1_client.py` | Cliente HTTP (`requests`, com `Session`), timeout, mapeia status → exceções transitórias/permanentes; suporta filtros com operadores (`date>=`, repetidos) |
| `ingestion/` | `retry.py` (`with_retry` com backoff exponencial, só `TransientApiError`); `extractors.py` (uma função por endpoint, cliente injetado) |
| `transformation/` | Funções puras por entidade: tipagem explícita (datas UTC, inteiros anuláveis), tratamento de nulos/duplicados, normaliza `gap_to_leader` (`+N LAP`), registra linhas afetadas |
| `validation/` | Schemas e regras (colunas obrigatórias, tipos, chaves únicas); falha rápida com `SchemaValidationError` |
| `pipelines/` | `race_pipeline.py` (compõe etapas para um `session_key`), `cli.py` (`--year`, `--session-key`, `--start`, `--end`) |
| `integrations/parquet_sink.py` | `Sink` que grava Parquet em temporário e troca atomicamente (sobrescrita de partição ⇒ idempotência) |
| `utils/logging.py` | Config de logging com `run_id` e `extra={}` |

Dependências (via `poetry add`): runtime `requests`, `pandas`, `pyarrow`; grupo `dev` `ruff pytest pytest-cov responses` (ou `requests-mock`); grupo `docs` `"mkdocs<2" mkdocs-material "mkdocstrings[python]"`.

Fluxo (de `doc_api.md` §8): `meetings?year=` → `sessions?meeting_key=&session_name=Race` → `drivers?session_key=` → `laps/stints/pit/weather/session_result?session_key=`. `meeting_key`/`session_key` aceitam `latest`.

Ressalvas da API incorporadas ao design: campos `drivers.country_code` e `pit.pit_duration` deprecated (não usar); `stop_duration` só desde GP dos EUA 2024 (nulo permitido); `segments_*` indisponível em corridas; limites de taxa e formato de erro **não documentados** ⇒ tratar 429/5xx como transitórios, com delay configurável e teste de integração para descobrir o comportamento real.

## Fases (cada uma = 1 branch + PR, commits Conventional)

**Fase 0 — Fundação** (`chore/setup`)
- `poetry config virtualenvs.in-project true --local`; completar `pyproject.toml` (Ruff, pytest, coverage conforme SKILL.md §4–5; `known-first-party = ["f1"]`, `source = ["src/f1"]`, `fail_under = 50`).
- `.gitignore`, `.env.example`, `README.md` (já existe; completar), `poetry.lock`.
- `poetry run ruff --version`, `pytest --version`, `mkdocs --version` antes de aplicar configs (SKILL.md §0.3).

**Fase 1 — Núcleo e cliente** (`feat/api-client`)
- `config`, `core`, `integrations/openf1_client.py`, `ingestion/retry.py`.
- Testes unitários com HTTP mockado: sucesso, 404 (permanente, sem retry), 429/503 (retry), timeout, operadores de filtro.

**Fase 2 — Ingestão + transformação + validação** (`feat/etl-core`)
- Extractors por endpoint; transformações puras; schemas de validação.
- Fixtures JSON pequenas em `tests/fixtures/` (amostras reais reduzidas, sem dados sensíveis).
- Testes parametrizados: vazio, nulos, duplicados, tipos inesperados, `+1 LAP`.

**Fase 3 — Carga e pipeline** (`feat/race-pipeline`)
- `parquet_sink.py`, `race_pipeline.py`, `cli.py` (`poetry run python -m f1.pipelines.cli --year 2024`).
- Idempotência: rodar duas vezes a mesma sessão ⇒ mesmo resultado, sem duplicar (teste com `tmp_path`).
- Logs com `run_id`, duração, linhas lidas/rejeitadas/gravadas; reprocessamento por sessão/janela.

**Fase 4 — Documentação** (`docs/pipeline-docs`)
- `mkdocs.yml` e `docs/` (`index`, `architecture`, `development`, `testing`, execução dos pipelines, guia de contribuição) + referência via mkdocstrings.

**Fase 5 — CI** (`ci/github-actions`)
- `.github/workflows/ci.yml` exatamente como SKILL.md §9 (lint → format → pytest cobertura ≥ 50 → `mkdocs build --strict`); integração em job separado manual/agendado (`@pytest.mark.integration`).
- Branch protection na `main` (configuração manual no GitHub, a documentar).

## Arquivos críticos

- Editar: `pyproject.toml`, `README.md`
- Criar: `src/f1/{config,core,ingestion,transformation,validation,pipelines,integrations,utils}/…`, `tests/{unit,integration,fixtures}/…`, `docs/*`, `mkdocs.yml`, `.github/workflows/ci.yml`, `.gitignore`, `.env.example`, `poetry.toml`
- Reaproveitar do SKILL.md: padrão `Settings.from_env`, `with_retry`, `Protocol Sink`, exemplos de teste parametrizado.

## Verificação (end-to-end)

Após cada fase, executar e ler a saída:
```bash
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest tests/unit/ --cov=src/f1 --cov-report=term-missing --cov-fail-under=50
poetry run mkdocs build --strict
```
Teste manual da Fase 3: `poetry run python -m f1.pipelines.cli --year 2024` duas vezes e comparar contagens dos Parquet em `DATA_DIR`. Teste de integração opcional (`pytest -m integration`) contra a API real, fora do gate. Relatar claramente o que não foi executado.

## Ponto de entrega do arquivo

Após a aprovação, este conteúdo é salvo como `plan.md` na raiz do repositório (não versionar nada sem pedido explícito de commit).
