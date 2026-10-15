# Execução dos pipelines

```bash
# corridas e classificações de um ano
poetry run python -m f1.pipelines.cli --year 2024

# janela de datas (exige --year)
poetry run python -m f1.pipelines.cli --year 2024 --start 2024-03-01 --end 2024-06-30

# só um tipo de sessão (repetível)
poetry run python -m f1.pipelines.cli --year 2024 --session-name Race

# uma sessão específica
poetry run python -m f1.pipelines.cli --session-key 9158

# retomar: pula sessões cujo session_result já foi gravado
poetry run python -m f1.pipelines.cli --year 2024 --skip-existing
```

| Argumento | Descrição |
|---|---|
| `--year` | ano a processar; repetível, ex.: `--year 2023 --year 2024` (exclusivo com `--session-key`) |
| `--all-years` | todos os anos, de 2023 até o atual (exclusivo com `--year`/`--session-key`) |
| `--session-key` | uma sessão pelo `session_key` |
| `--session-name` | tipo de sessão com `--year` (`Race`, `Qualifying`, ...); padrão: `Race` e `Qualifying` |
| `--start`, `--end` | janela `AAAA-MM-DD` sobre `date_start`/`date_end` dos fins de semana |
| `--skip-existing` | não reprocessa sessões já concluídas |

## Códigos de saída

- `0` — tudo processado.
- `1` — alguma sessão falhou (as demais continuam) ou a execução foi abortada.

## Reprocessamento

Reexecutar uma sessão sobrescreve suas partições, sem duplicar dados. Para refazer só
as sessões que falharam, rode de novo com `--skip-existing`.

## Logs

Saem em JSON no stderr, sempre com `run_id`:

```json
{"level": "INFO", "message": "etapa concluída", "run_id": "3f2a9c1b7d40",
 "entity": "laps", "rows_in": 1250, "rows_rejected": 0, "duplicates_dropped": 2,
 "values_coerced": 0, "rows_out": 1248}
```

## Dashboard

Depois de carregar dados com o pipeline, o Streamlit mostra as 5 voltas mais rápidas
de cada GP, com filtros de ano e tipo de sessão (Race/Qualifying):

```bash
poetry run streamlit run src/f1/dashboard.py
# ou: poetry run task dashboard
```

Pela barra lateral (**⬇️ Carregar dados da OpenF1**) dá para escolher os anos e rodar o
pipeline com uma barra de progresso; no terminal, a CLI mostra a mesma barra.

Ele lê os Parquet de `DATA_DIR` (padrão `data/`); sem dados, mostra como gerá-los.

O dashboard detecta quando o pipeline grava novos Parquet e recarrega os dados
sozinho; basta atualizar a página (F5), sem limpar o cache.
