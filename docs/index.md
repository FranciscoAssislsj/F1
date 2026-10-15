# F1 — Pipeline OpenF1

Pipeline de dados históricos de Fórmula 1 (gratuitos e sem autenticação, desde 2023)
obtidos da [API OpenF1](https://openf1.org/docs/). Etapas:
**ingestão → transformação → validação → carga**.

## Escopo

| Entidade | Endpoint | Granularidade |
|---|---|---|
| `meetings` | `meetings` | um fim de semana de GP |
| `sessions` | `sessions` (`Race` e `Qualifying`) | uma sessão |
| `drivers` | `drivers` | piloto por sessão |
| `laps` | `laps` | volta por piloto |
| `stints` | `stints` | períodos de pilotagem com o mesmo pneu |
| `pit` | `pit` | passagens pelo pit lane |
| `weather` | `weather` | clima, ~1 registro/min |
| `session_result` | `session_result` | resultado final |

Fora do escopo: telemetria pesada (`car_data`, `location`) e dados em tempo real.

## Destino

Arquivos Parquet locais em `DATA_DIR`:

```text
data/
├── meetings/meeting_key=1219/part.parquet
├── sessions/session_key=9606/part.parquet
└── laps/session_key=9606/part.parquet   (e demais entidades de sessão)
```

## Estrutura do repositório

```text
src/f1/
├── config/          # Settings.from_env
├── core/            # exceções, interfaces (Protocol), modelos e schemas
├── integrations/    # cliente HTTP OpenF1 e sink Parquet
├── ingestion/       # retry e extratores
├── transformation/  # funções puras de limpeza e tipagem
├── validation/      # checagem contra o schema
├── pipelines/       # orquestração e CLI
└── utils/           # logging estruturado
tests/{unit,fixtures}
docs/
```

## Ressalvas da API

- Os limites de taxa não são documentados, mas a API responde `429` quando recebe
  chamadas em rajada. `429`/`5xx` são transitórios (5 tentativas com backoff de 2 s) e há
  uma pausa entre chamadas (`RATE_LIMIT_DELAY_S`, padrão 2 s). Carregar um ano inteiro
  (Race + Qualifying) leva cerca de 20 minutos; use `--skip-existing` para retomar.
- `drivers.country_code` e `pit.pit_duration` estão *deprecated* e não são carregados.
- `pit.stop_duration` só existe desde o GP dos EUA de 2024 (nulo antes).
- `segments_*` das voltas não existem em corridas e não são carregados.
