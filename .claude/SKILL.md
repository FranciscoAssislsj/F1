---
name: python-data-engineering-standards
description: Padrões obrigatórios para projetos Python de Engenharia de Dados (Poetry, layout src, Ruff, Pytest com cobertura mínima de 50%, MkDocs Material, pipelines idempotentes, Git e CI). Use ao criar, modificar, revisar ou manter qualquer código Python, pipeline, teste, configuração ou documentação deste repositório.
---

# Padrões de Engenharia de Dados em Python

Este documento é a fonte única de verdade para desenvolvimento neste repositório. Vale para desenvolvedores e agentes de IA.

**Convenções do documento**

- **[OBRIGATÓRIO]** — regra inegociável. Violação bloqueia a entrega.
- **[RECOMENDADO]** — boa prática; desvios exigem justificativa curta no PR.
- `projeto` é um placeholder. Substitua pelo nome real do pacote em `src/` (neste repositório: `f1`). Nunca renomeie o pacote existente.

---

## 0. Antes de qualquer mudança

1. **[OBRIGATÓRIO]** Inspecione o repositório antes de criar arquivos: `pyproject.toml`, `src/`, `tests/`, `docs/`, `mkdocs.yml`, `.github/workflows/`.
2. **[OBRIGATÓRIO]** Reaproveite módulos, convenções e decisões existentes. Não crie um segundo mecanismo para algo que já existe.
3. **[OBRIGATÓRIO]** Verifique as versões instaladas (`poetry run ruff --version`, `poetry run pytest --version`, `poetry run mkdocs --version`) antes de aplicar qualquer configuração deste documento. Se a sintaxe divergir da versão instalada, siga a documentação oficial da versão e informe a divergência.

---

## 1. Ambiente e dependências (Poetry)

### Regras

- **[OBRIGATÓRIO]** Poetry é a única ferramenta de dependências, ambiente virtual e execução.
- **[OBRIGATÓRIO]** Proibido: `pip install`, `pip uninstall`, `pip freeze`, `python -m pip`, `requirements.txt` como gestor de dependências, instalação global de ferramentas do projeto.
- **[OBRIGATÓRIO]** Dependências declaradas no `pyproject.toml`; `poetry.lock` sempre versionado e atualizado no mesmo commit que altera dependências.
- **[OBRIGATÓRIO]** Todo comando de Python/ferramenta roda via `poetry run`.
- **[OBRIGATÓRIO]** Ambiente virtual em `.venv` dentro do projeto (`.venv` no `.gitignore`).
- **[OBRIGATÓRIO]** Dependência de sistema operacional (ex.: driver ODBC, `libpq`) é documentada em `docs/development.md`, nunca instalada por script oculto.
- **[RECOMENDADO]** Se usar pyenv, ele controla apenas a versão do Python (`.python-version`); Poetry controla venv e dependências.
- **[RECOMENDADO]** Adicionar apenas dependências realmente necessárias; prefira a biblioteca padrão quando suficiente.

### Comandos

```bash
poetry config virtualenvs.in-project true --local   # gera poetry.toml (versionar)
poetry install                                      # reproduz o ambiente a partir do poetry.lock
poetry add pandas                                   # dependência de runtime
poetry add --group dev ruff pytest pytest-cov       # ferramentas de desenvolvimento
poetry add --group docs "mkdocs<2" mkdocs-material "mkdocstrings[python]"
poetry remove <pacote>
poetry lock                                         # após editar o pyproject.toml manualmente
poetry check                                        # valida o pyproject.toml
poetry run python -m projeto.pipelines.minha_pipeline
```

> Fixe `mkdocs<2`: o MkDocs 2.x não é compatível com o ecossistema atual de plugins e com o tema Material. Confirme na versão instalada antes de remover o limite.

### Incorreto × correto

```bash
# ❌ Incorreto
pip install requests
pip freeze > requirements.txt
python script.py

# ✅ Correto
poetry add requests
poetry run python script.py
```

---

## 2. Arquitetura e organização

### Layout `src` (obrigatório)

```text
projeto/
├── .github/workflows/ci.yml
├── .python-version
├── .gitignore
├── .env.example
├── README.md
├── SKILL.md
├── pyproject.toml
├── poetry.lock
├── mkdocs.yml
├── src/projeto/
│   ├── __init__.py
│   ├── config/          # leitura e validação de configuração/variáveis de ambiente
│   ├── core/            # modelos, exceções, interfaces (sem I/O)
│   ├── ingestion/       # conectores e extração
│   ├── transformation/  # funções puras de transformação
│   ├── validation/      # regras de qualidade e schema
│   ├── pipelines/       # orquestração: compõe ingestão → transformação → validação → carga
│   ├── integrations/    # clientes de serviços externos (APIs, bancos, storage)
│   └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── conftest.py
├── docs/ (index.md, architecture.md, development.md, testing.md)
└── scripts/             # wrappers finos que apenas chamam src/projeto
```

A árvore é referência. **[OBRIGATÓRIO]** Só crie diretórios e arquivos quando houver conteúdo real; não gere pastas vazias "por completude".

### Regras de design

- **[OBRIGATÓRIO]** Todo código de produção fica em `src/projeto/`. Nada de lógica em `scripts/`, notebooks ou raiz.
- **[OBRIGATÓRIO]** Separar responsabilidades: ingestão, transformação, validação, persistência e orquestração em módulos distintos.
- **[OBRIGATÓRIO]** Transformações são funções puras (entrada → saída), sem ler/escrever disco, rede ou banco.
- **[OBRIGATÓRIO]** Imports absolutos a partir do pacote (`from projeto.transformation.clean import normalize`). Sem dependências circulares.
- **[OBRIGATÓRIO]** Componentes testáveis isoladamente: dependências externas entram por parâmetro (injeção), não por import global.
- **[RECOMENDADO]** SOLID, DRY e KISS quando apropriado. Não introduza classes abstratas, factories ou padrões sem necessidade concreta e atual.
- **[RECOMENDADO]** Funções ≤ ~40 linhas e módulos ≤ ~400 linhas como sinal de alerta, não limite rígido.

### Injeção de dependências simples

```python
# ✅ Correto: dependência injetada, fácil de mockar
from typing import Protocol

import pandas as pd


class Sink(Protocol):
    def write(self, df: pd.DataFrame) -> None: ...


def run_load(df: pd.DataFrame, sink: Sink) -> None:
    sink.write(df)


# ❌ Incorreto: conexão criada dentro da regra de negócio
def run_load_bad(df: pd.DataFrame) -> None:
    import psycopg2

    conn = psycopg2.connect("host=prod user=admin password=123")
    ...
```

---

## 3. Padrões de código Python

### Regras

- **[OBRIGATÓRIO]** PEP 8 (garantido pelo Ruff) e Python na versão declarada em `requires-python`; use recursos modernos dessa versão (`X | None`, `list[str]`, `match` quando clarear).
- **[OBRIGATÓRIO]** Type hints em todas as funções, métodos e interfaces públicas.
- **[OBRIGATÓRIO]** Docstrings em módulos, classes e funções públicas relevantes (formato Google, curto, em português ou inglês — siga o já existente).
- **[OBRIGATÓRIO]** Nomes: `snake_case` (funções, variáveis, módulos), `PascalCase` (classes), `UPPER_SNAKE_CASE` (constantes). Nomes descritivos; sem abreviações obscuras.
- **[OBRIGATÓRIO]** `pathlib.Path` para caminhos; `logging` para logs operacionais (proibido `print` em `src/`).
- **[OBRIGATÓRIO]** Context managers (`with`) para arquivos, conexões, cursores e sessões.
- **[OBRIGATÓRIO]** Exceções específicas e com contexto. Proibido `except:` e `except Exception:` que silencia erro. Se precisar capturar amplo (ex.: fronteira do pipeline), registre com `logger.exception` e relance.
- **[OBRIGATÓRIO]** Sem argumentos mutáveis como padrão.
- **[OBRIGATÓRIO]** Sem credenciais, tokens, hosts de produção ou caminhos absolutos hardcoded; tudo vem de configuração/variáveis de ambiente.
- **[OBRIGATÓRIO]** Sem código morto, comentado ou imports não usados.
- **[RECOMENDADO]** Evitar efeitos colaterais em tempo de import. Preferir `dataclass(frozen=True)` ou Pydantic para modelos/configuração.
- **[RECOMENDADO]** Logging com formatação preguiçosa: `logger.info("lidas %d linhas", n)`.

### Exemplos

```python
# ❌ Incorreto
import os


def load(path, rows=[]):  # sem type hints, default mutável
    f = open("C:\\dados\\" + path)  # caminho hardcoded, sem with
    try:
        rows.append(f.read())
    except Exception:  # esconde o erro
        pass
    print("ok")  # print em vez de logging
    return rows
```

```python
# ✅ Correto
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SourceFileError(RuntimeError):
    """Falha ao ler um arquivo de origem."""


def load(path: Path, rows: list[str] | None = None) -> list[str]:
    """Lê o arquivo e acrescenta seu conteúdo à lista de linhas.

    Args:
        path: Arquivo de origem.
        rows: Lista a estender; se omitida, uma nova é criada.

    Raises:
        SourceFileError: Se o arquivo não puder ser lido.
    """
    result = [] if rows is None else rows
    try:
        with path.open(encoding="utf-8") as fh:
            result.append(fh.read())
    except OSError as exc:
        raise SourceFileError(f"Não foi possível ler {path}") from exc
    logger.info("arquivo lido: %s", path)
    return result
```

### Configuração centralizada

```python
# src/projeto/config/settings.py
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_url: str
    api_timeout_s: float = 30.0

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            return cls(
                db_url=os.environ["DB_URL"],
                api_timeout_s=float(os.getenv("API_TIMEOUT_S", "30")),
            )
        except KeyError as exc:
            raise RuntimeError(f"Variável de ambiente ausente: {exc}") from exc
```

---

## 4. Ruff — lint, formatação e imports

**[OBRIGATÓRIO]** Ruff é a única ferramenta de lint, formatação e ordenação de imports. Não adicionar black, isort, flake8 ou pylint.

### Comandos

```bash
poetry run ruff check .
poetry run ruff check . --fix
poetry run ruff format .
poetry run ruff format --check .
```

### Configuração (`pyproject.toml`)

```toml
[tool.ruff]
target-version = "py314"   # alinhar com requires-python
line-length = 88
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.ruff.lint.isort]
known-first-party = ["projeto"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["B011"]      # exemplo; só adicionar com justificativa

[tool.ruff.format]
quote-style = "double"
```

### Regras

- **[OBRIGATÓRIO]** Todo código passa em `ruff check` e `ruff format --check` antes de commit/PR.
- **[OBRIGATÓRIO]** Famílias mínimas: `E`, `F`, `I`, `B`, `UP`. Pode-se ampliar (ex.: `SIM`, `S`, `PT`); não reduzir.
- **[OBRIGATÓRIO]** Supressão (`# noqa: XXXX`) só pontual, com o código da regra e justificativa. Proibido `# noqa` genérico e `ignore` global para contornar falhas.
- **[OBRIGATÓRIO]** `target-version` compatível com `requires-python`.
- **[RECOMENDADO]** Use `--fix` e revise o diff gerado antes de commitar.

---

## 5. Pytest — testes e cobertura

### Regras

- **[OBRIGATÓRIO]** `pytest` + `pytest-cov`. Testes em `tests/unit/` (rápidos, isolados) e `tests/integration/` (dependem de infraestrutura, fora do gate padrão do CI).
- **[OBRIGATÓRIO]** Cobertura mínima de **50%** sobre `src/projeto/`, incluindo módulos que nenhum teste importa.
- **[OBRIGATÓRIO]** Arquivos `test_*.py`; funções `test_*`. Fixtures em `conftest.py` ou `tests/fixtures/`.
- **[OBRIGATÓRIO]** Testes unitários não acessam rede, banco ou serviço real — use mocks/fakes (`unittest.mock`, `monkeypatch`, `tmp_path`).
- **[OBRIGATÓRIO]** Nunca chamar APIs ou bancos de produção em testes.
- **[OBRIGATÓRIO]** Testes determinísticos: sem dependência de relógio, ordem, aleatoriedade sem seed ou estado global.
- **[OBRIGATÓRIO]** Cobrir sucesso, falha e bordas (vazio, nulos, duplicados, tipos inesperados).
- **[OBRIGATÓRIO]** Mudou comportamento → crie/atualize o teste no mesmo PR.
- **[RECOMENDADO]** Priorizar regras de negócio e transformações críticas; usar `pytest.mark.parametrize`.
- **[RECOMENDADO]** Marcar testes de integração: `@pytest.mark.integration`.
- Proibido: testes sem asserção criados só para subir cobertura; remover/enfraquecer testes válidos para esconder regressão.

### Configuração (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
markers = [
    "integration: testes que dependem de infraestrutura externa",
]

[tool.coverage.run]
source = ["src/projeto"]   # inclui arquivos nunca importados pelos testes (0%)
branch = true

[tool.coverage.report]
fail_under = 50
show_missing = true
skip_covered = false
```

### Comandos

```bash
# Gate oficial (unitários + cobertura mínima)
poetry run pytest tests/unit/ --cov=src/projeto --cov-report=term-missing --cov-fail-under=50

# Relatório HTML navegável (htmlcov/index.html)
poetry run pytest tests/unit/ --cov=src/projeto --cov-report=html

# Um teste específico / integração
poetry run pytest tests/unit/test_x.py::test_caso -x
poetry run pytest tests/integration -m integration
```

### Como ler o relatório

Colunas `Stmts` (linhas executáveis), `Miss` (não executadas), `Cover` (%) e `Missing` (números das linhas não cobertas). Com `branch = true` aparecem também `Branch`/`BrPart`. Comece pelos módulos de regra de negócio com `Missing` alto. Se um arquivo aparece com 0%, ele existe em `src/projeto/` mas nenhum teste o executa — isso é esperado e desejado no cálculo.

### Exemplo

```python
import pandas as pd
import pytest

from projeto.transformation.clean import drop_duplicates_by_key


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ([{"id": 1}, {"id": 1}], 1),
        ([], 0),
    ],
)
def test_drop_duplicates_by_key(rows: list[dict], expected: int) -> None:
    df = pd.DataFrame(rows, columns=["id"])
    assert len(drop_duplicates_by_key(df, "id")) == expected
```

---

## 6. Documentação (MkDocs Material)

- **[OBRIGATÓRIO]** Documentação técnica com MkDocs + tema Material (+ `mkdocstrings` quando houver API Python a documentar).
- **[OBRIGATÓRIO]** Conteúdo mínimo em `docs/`: visão geral e escopo; estrutura de diretórios; requisitos e instalação; ambiente com Poetry; arquitetura e responsabilidade dos módulos; execução dos pipelines; estratégia de testes; padrões de qualidade; guia de contribuição.
- **[OBRIGATÓRIO]** Atualize a documentação em toda mudança de funcionalidade relevante ou de arquitetura.
- **[OBRIGATÓRIO]** O build estrito deve passar (links quebrados e referências inválidas falham).
- **[RECOMENDADO]** Exemplos executáveis; usar docstrings + mkdocstrings em vez de duplicar texto.

### `mkdocs.yml`

```yaml
site_name: Projeto
docs_dir: docs
theme:
  name: material
plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
nav:
  - Início: index.md
  - Arquitetura: architecture.md
  - Desenvolvimento: development.md
  - Testes: testing.md
```

### Comandos

```bash
poetry run mkdocs serve            # preview local em http://127.0.0.1:8000
poetry run mkdocs build --strict   # gate de validação
```

Referência de API em uma página: `::: projeto.transformation.clean`.

---

## 7. Boas práticas de Engenharia de Dados

### Ingestão
- **[OBRIGATÓRIO]** Conectores (como acessar a fonte) separados da lógica de ingestão (o que fazer com os dados).
- **[OBRIGATÓRIO]** Validar dados na entrada (schema, colunas obrigatórias, tipos).
- **[OBRIGATÓRIO]** Definir timeout em toda chamada de rede/banco.
- **[OBRIGATÓRIO]** Retry com backoff exponencial **somente** para falhas transitórias (timeout, 429, 5xx); nunca para erros permanentes (401, 404, schema inválido).
- **[RECOMENDADO]** Processar em lotes/chunks/streaming em vez de carregar o dataset inteiro em memória.

```python
import time


def with_retry(fn, *, attempts: int = 3, base_delay_s: float = 1.0):
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except TransientError:
            if attempt == attempts:
                raise
            time.sleep(base_delay_s * 2 ** (attempt - 1))
```

### Transformação
- **[OBRIGATÓRIO]** Funções reutilizáveis, puras e testáveis, separadas de leitura/escrita.
- **[OBRIGATÓRIO]** Preservar e declarar tipos explicitamente (datas, decimais, inteiros anuláveis); não deixar a inferência decidir.
- **[OBRIGATÓRIO]** Tratar explicitamente nulos, duplicados e inconsistências; registrar quantas linhas foram afetadas.
- **[OBRIGATÓRIO]** Cada regra de negócio vive em um único lugar.

### Pipelines
- **[OBRIGATÓRIO]** Idempotência: reexecutar a mesma janela produz o mesmo resultado, sem duplicar dados (use `MERGE`/upsert por chave, ou sobrescrita de partição, ou escrita em temporário + troca atômica).
- **[OBRIGATÓRIO]** Entradas, saídas e dependências de cada etapa explícitas (parâmetros e tipos de retorno, sem estado oculto).
- **[OBRIGATÓRIO]** Registrar início, fim, duração, volume processado e erros de cada execução, com um identificador de execução (`run_id`).
- **[OBRIGATÓRIO]** Distinguir falha transitória (retentável) de permanente (falha rápida com erro claro).
- **[OBRIGATÓRIO]** Prever reprocessamento por janela/partição e recuperação a partir da última etapa concluída.
- **[RECOMENDADO]** Parametrizar a janela de processamento (`--start`, `--end`) em vez de usar "hoje" implícito.

### Segurança
- **[OBRIGATÓRIO]** Nenhum segredo no código, em testes, em workflows ou em logs.
- **[OBRIGATÓRIO]** `.env` fora do Git; `.env.example` versionado apenas com chaves e valores fictícios.
- **[OBRIGATÓRIO]** Menor privilégio: credenciais somente-leitura onde só se lê; usuário de carga restrito ao esquema de destino.
- **[OBRIGATÓRIO]** Não registrar dados pessoais/confidenciais em logs; mascarar quando inevitável.

### Observabilidade
- **[OBRIGATÓRIO]** Logs com contexto suficiente para diagnóstico (pipeline, etapa, `run_id`, janela, contagens).
- **[RECOMENDADO]** Logs estruturados (JSON ou `extra={}`) em ambientes de produção; registrar métricas de linhas lidas/rejeitadas/gravadas.

```python
logger.info(
    "etapa concluída",
    extra={"run_id": run_id, "step": "transform", "rows_in": n_in, "rows_out": n_out},
)
```

---

## 8. Git e controle de versão

- **[OBRIGATÓRIO]** Trabalhar em branches e integrar via Pull Request com revisão antes do merge; sem push direto na `main`.
- **[OBRIGATÓRIO]** Commits pequenos e objetivos, um propósito por commit.
- **[OBRIGATÓRIO]** Versionar `pyproject.toml`, `poetry.lock`, `poetry.toml`, `.python-version`, `.env.example`.
- **[OBRIGATÓRIO]** Nunca versionar `.venv/`, `.env`, caches (`__pycache__/`, `.ruff_cache/`, `.pytest_cache/`), `.coverage`, `htmlcov/`, `site/`, dados e artefatos temporários.
- **[OBRIGATÓRIO]** Sem código comentado, não utilizado ou arquivos gerados desnecessários nos commits.
- **[RECOMENDADO]** Conventional Commits:

```text
feat(ingestion): adiciona conector da API de pedidos
fix(transformation): corrige deduplicação por chave composta
docs: atualiza guia de execução dos pipelines
test(validation): cobre schema com colunas ausentes
chore(deps): atualiza ruff
```

---

## 9. CI/CD

**[OBRIGATÓRIO]** O CI executa, nesta ordem, e bloqueia o merge se qualquer etapa falhar: Python → Poetry → instalação → lint → formato → testes unitários com cobertura ≥ 50% → build estrito da documentação.

```yaml
# .github/workflows/ci.yml
name: CI
on:
  pull_request:
  push:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version-file: .python-version   # ou python-version: "3.14"
      - name: Instalar Poetry
        run: pipx install poetry
      - name: Instalar dependências
        run: poetry install --no-interaction --with dev,docs
      - name: Ruff lint
        run: poetry run ruff check .
      - name: Ruff format
        run: poetry run ruff format --check .
      - name: Testes unitários e cobertura
        run: poetry run pytest tests/unit/ --cov=src/projeto --cov-report=term-missing --cov-fail-under=50
      - name: Documentação
        run: poetry run mkdocs build --strict
```

Regras:

- **[OBRIGATÓRIO]** Configurar *branch protection* exigindo o job `quality` e revisão aprovada.
- **[OBRIGATÓRIO]** Credenciais somente via *secrets* do CI; nunca em texto no workflow. O pipeline não acessa recursos de produção.
- **[OBRIGATÓRIO]** Testes de integração que dependem de infraestrutura rodam em job separado (manual ou agendado), nunca no gate padrão.
- **[RECOMENDADO]** Cache do Poetry/venv para acelerar, mantendo `poetry.lock` como fonte de reprodutibilidade.
- Nota: se algum grupo usado no `--with` não existir no `pyproject.toml`, o `poetry install` falha — mantenha os nomes dos grupos alinhados com o arquivo.

---

## 10. Regras para agentes de IA

O agente **deve**:

1. Inspecionar a estrutura existente antes de criar arquivos e respeitar convenções e decisões já adotadas.
2. Usar Poetry em todo comando de ambiente Python. **Nunca** usar `pip`.
3. Manter código novo em `src/projeto/`; não criar dependências desnecessárias; não duplicar funcionalidade existente.
4. Preservar compatibilidade de APIs e interfaces existentes; se quebrar, declarar explicitamente.
5. Criar/atualizar testes ao modificar comportamento e atualizar a documentação em mudanças relevantes.
6. Após mudanças relevantes, executar e reportar o resultado de:
   ```bash
   poetry run ruff check .
   poetry run ruff format --check .
   poetry run pytest tests/unit/ --cov=src/projeto --cov-report=term-missing --cov-fail-under=50
   poetry run mkdocs build --strict
   ```
7. Informar claramente o que **não** foi executado e as limitações (ex.: integração sem acesso à infraestrutura).
8. Preferir soluções simples, legíveis, seguras e sustentáveis.

O agente **nunca** deve:

- Afirmar que testes, lint ou build passaram sem tê-los executado e lido a saída.
- Desabilitar regras de lint, marcar testes como `skip`/`xfail`, ou excluir arquivos da cobertura para fazer a validação passar.
- Reduzir `fail_under`/`--cov-fail-under` abaixo de 50.
- Remover ou enfraquecer testes válidos para ocultar regressão.
- Inserir credenciais, tokens ou dados reais em código, testes, docs ou logs.
- Instalar ferramentas globalmente ou alterar `poetry.lock` manualmente.

Em caso de falha nas verificações: corrija a causa raiz; se não for possível, reporte o erro e o motivo em vez de contorná-lo.

---

## 11. Checklist de conclusão

Toda entrega deve cumprir (marque apenas o que foi realmente verificado):

- [ ] Código organizado de forma modular.
- [ ] Dependências gerenciadas exclusivamente pelo Poetry (`pyproject.toml` + `poetry.lock` coerentes).
- [ ] Código-fonte localizado corretamente em `src/projeto/`.
- [ ] Type hints e docstrings aplicados quando relevantes.
- [ ] `poetry run ruff check .` aprovado.
- [ ] `poetry run ruff format --check .` aprovado.
- [ ] Imports organizados (regra `I` do Ruff).
- [ ] Testes unitários executados com sucesso.
- [ ] Cobertura mínima de 50% atingida.
- [ ] Documentação atualizada.
- [ ] `poetry run mkdocs build --strict` aprovado.
- [ ] Sem credenciais expostas.
- [ ] Sem dependências ou arquivos desnecessários.
- [ ] Mudanças compatíveis com os padrões do projeto.

---

## 12. Documentação complementar

Detalhes que extrapolam este arquivo ficam em `docs/` (`architecture.md`, `development.md`, `testing.md`). As regras fundamentais acima permanecem aqui; em caso de conflito, este `SKILL.md` prevalece.
