# Arquitetura

## Fluxo

```text
meetings?year=  →  sessions?meeting_key=&session_name=Race|Qualifying
                        │
                        ├─ drivers / laps / stints / pit / weather / session_result
                        ▼
   Extractor (retry) → transform (puro) → validate → Sink (Parquet atômico)
```

Cada etapa recebe suas dependências por parâmetro (cliente, extrator, sink), o que
permite testá-las sem rede nem disco real.

## Responsabilidades

| Módulo | Responsabilidade |
|---|---|
| `f1.config.settings` | `Settings` imutável lido do ambiente |
| `f1.core` | exceções, `Protocol`s (`ApiClient`, `Sink`), modelos e `schemas` das entidades |
| `f1.integrations.openf1_client` | HTTP com timeout; classifica erros em transitórios e permanentes |
| `f1.integrations.parquet_sink` | grava em arquivo temporário e troca atomicamente |
| `f1.ingestion.retry` | backoff exponencial **somente** para `TransientApiError` |
| `f1.ingestion.extractors` | `Extractor`: o que consultar em cada endpoint |
| `f1.transformation` | tipagem explícita, nulos, duplicados e `gap_to_leader` |
| `f1.validation.checks` | colunas, tipos, chave sem nulos e única |
| `f1.pipelines` | `race_pipeline` (orquestração) e `cli` |
| `f1.utils.logging` | logs JSON com campos de `extra` (`run_id`, contagens) |

## Regras de negócio

- **Erros**: timeout, erro de conexão, `429` e `5xx` → `TransientApiError` (retentável).
  Demais `4xx` e corpo inválido → `PermanentApiError` (falha rápida). Exceção: a
  OpenF1 responde `404 {"detail":"No results found."}` quando o filtro não casa com
  nada (ex.: fim de semana de testes sem corrida); isso vira lista vazia. Dados fora do
  schema → `SchemaValidationError`; nada é gravado para a entidade afetada.
- **Tipagem** (`core.schemas` + `transformation.clean`): inteiros anuláveis (`Int64`),
  decimais (`Float64`), datas em UTC, booleanos anuláveis. Valores com tipo inesperado
  viram nulos e são contados em `values_coerced`.
- **Chaves**: linhas com chave nula são rejeitadas; duplicados pela chave mantêm a
  última ocorrência. Ambos são contados nos logs.
- **`gap_to_leader`** (`session_result`): número vira `gap_to_leader_s`;
  `"+N LAP(S)"` vira `laps_down = N`.
- **Idempotência**: cada partição é sobrescrita por inteiro; reexecutar a mesma sessão
  gera os mesmos arquivos. `session_result` é gravado por último e marca a sessão como
  concluída (`--skip-existing`).

## Observabilidade

Cada execução tem um `run_id`. Cada entidade registra `rows_in`, `rows_rejected`,
`duplicates_dropped`, `values_coerced` e `rows_out`; cada sessão e a execução registram
a duração.
