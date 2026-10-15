# Desenvolvimento

## Requisitos

- Python 3.13 (`.python-version`; pode ser gerenciado com pyenv).
- [Poetry](https://python-poetry.org/) — única ferramenta de dependências e execução.
- Nenhuma dependência de sistema operacional além do Python.

## Instalação

```bash
poetry config virtualenvs.in-project true --local   # cria .venv no projeto
poetry install --with dev,docs
```

Todo comando roda via `poetry run`. Não use `pip`.

!!! warning "Variável `VIRTUAL_ENV`"
    Se o shell já exportar `VIRTUAL_ENV` apontando para outro Python, o Poetry usa esse
    ambiente em vez do `.venv` do projeto. Limpe a variável (ou desative o ambiente)
    antes de `poetry install`.

## Configuração

Copie `.env.example` para `.env` (ignorado pelo Git) e exporte as variáveis, se quiser
alterar os padrões:

| Variável | Padrão | Descrição |
|---|---|---|
| `OPENF1_BASE_URL` | `https://api.openf1.org/v1` | URL base da API |
| `API_TIMEOUT_S` | `30` | timeout de cada chamada |
| `RATE_LIMIT_DELAY_S` | `2.0` | pausa antes de cada chamada |
| `DATA_DIR` | `data` | raiz dos Parquet |

## Qualidade

```bash
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest tests/unit/ --cov=src/f1 --cov-report=term-missing --cov-fail-under=50
poetry run task docs          # preview em http://127.0.0.1:8000
poetry run task docs-build    # igual ao mkdocs build --strict
```

Padrões completos: `.claude/SKILL.md`.
