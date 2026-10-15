# OpenF1 API — Resumo da Documentação

Fonte: https://openf1.org/docs/

## 1. Visão geral

- API **não oficial** de dados de Fórmula 1 (sem afiliação com empresas da F1).
- Base URL: `https://api.openf1.org/v1/{endpoint}`
- **Dados históricos** (a partir de 2023): gratuitos, sem autenticação.
- **Dados em tempo real**: exigem assinatura paga.

## 2. Formatos de resposta

- JSON por padrão.
- Adicione `csv=true` para receber CSV (útil para Excel/planilhas):
  `sessions?year=2023&csv=true`

## 3. Filtros

- Qualquer atributo pode ser filtrado via query string (exceto arrays).
- Operadores: `=`, `>=`, `<=`, `>`, `<` (codifique se necessário, ex.: `%3E%3D` para `>=`).
- Parâmetros repetidos retornam múltiplos valores: `driver_number=4&driver_number=81`.
- `meeting_key` e `session_key` aceitam o valor `latest` (mais recente/atual).
- Filtros de data usam `date` (ou `date_start`/`date_end`) com operadores; aceita formatos do `dateutil.parser`, ex.: `2021-09-10T14:30:20+00:00`.

Exemplo:

```
laps?session_key=9222&driver_number=55&is_pit_out_lap=true&lap_duration>=120
```

## 4. Campos comuns

| Campo | Descrição |
|---|---|
| `meeting_key` | Identificador do fim de semana (GP/testes) |
| `session_key` | Identificador da sessão |
| `driver_number` | Número do carro (específico da temporada) |
| `date` | Data/hora em UTC, ISO 8601 |

## 5. Endpoints

| Endpoint | Descrição |
|---|---|
| `car_data` | Telemetria do carro (~3,7 Hz) |
| `championship_drivers` (beta) | Classificação de pilotos (só corridas) |
| `championship_teams` (beta) | Classificação de equipes (só corridas) |
| `drivers` | Dados dos pilotos por sessão |
| `intervals` | Diferenças entre pilotos e para o líder (corrida, ~4 s) |
| `laps` | Tempos e velocidades por volta |
| `location` | Posição aproximada do carro na pista (~3,7 Hz) |
| `meetings` | Fins de semana de GP/testes |
| `overtakes` | Ultrapassagens (só corrida) |
| `pit` | Passagens pelo pit lane |
| `position` | Mudanças de posição ao longo da sessão |
| `race_control` | Bandeiras, safety car, incidentes, status |
| `sessions` | Treinos, classificação, sprint, corrida |
| `session_result` | Resultado final da sessão |
| `starting_grid` | Grid de largada |
| `stints` | Períodos contínuos de pilotagem (pneus) |
| `team_radio` | Gravações de rádio piloto-equipe (seleção limitada) |
| `weather` | Clima da pista/ar (atualizado a cada minuto) |

### car_data
Telemetria a ~3,7 Hz.
Exemplo: `car_data?driver_number=55&session_key=9159&speed>=315`
Campos: `brake` (100 = pressionado, 0 = não), `date`, `driver_number`, `drs`, `meeting_key`, `n_gear` (0–8), `rpm`, `session_key`, `speed` (km/h), `throttle` (%).

### championship_drivers (beta)
Só sessões de corrida. Valores `*_current` dependem de quando a chamada é feita; `*_start` são a classificação antes da corrida.
Exemplo: `championship_drivers?session_key=9839&driver_number=4&driver_number=81`
Campos: `driver_number`, `meeting_key`, `points_current`, `points_start`, `position_current`, `position_start`, `session_key`.

### championship_teams (beta)
Exemplo: `championship_teams?session_key=9839&team_name=McLaren`
Campos: `meeting_key`, `points_current`, `points_start`, `position_current`, `position_start`, `session_key`, `team_name`.

### drivers
Exemplo: `drivers?driver_number=1&session_key=9158`
Campos: `broadcast_name`, `country_code` (deprecated), `driver_number`, `first_name`, `full_name`, `headshot_url`, `last_name`, `meeting_key`, `name_acronym` (3 letras), `session_key`, `team_colour` (hex RRGGBB), `team_name`.

### intervals
Somente corrida, atualizado a cada ~4 s.
Exemplo: `intervals?session_key=9165&interval>0&interval<0.005`
Campos: `date`, `driver_number`, `gap_to_leader` (segundos, `+N LAP` se retardatário, null para o líder), `interval` (para o carro à frente, mesmo formato), `meeting_key`, `session_key`.

### laps
Exemplo: `laps?session_key=9161&driver_number=63&lap_number=8`
Campos: `date_start` (aproximado), `driver_number`, `duration_sector_1/2/3`, `i1_speed`, `i2_speed` (km/h), `is_pit_out_lap`, `lap_duration`, `lap_number`, `meeting_key`, `segments_sector_1/2/3`, `session_key`, `st_speed` (speed trap, km/h).

### location
Posição 3D aproximada a ~3,7 Hz. Mostra progresso ao longo da pista, não a posição lateral; origem (0,0,0) não está ligada a um ponto da pista.
Exemplo: `location?session_key=9161&driver_number=81&date>2023-09-16T13:03:35.200&date<2023-09-16T13:03:35.800`
Campos: `date`, `driver_number`, `meeting_key`, `session_key`, `x`, `y`, `z`.

### meetings
Atualizado diariamente à meia-noite UTC.
Exemplo: `meetings?year=2026&country_name=Singapore`
Campos: `circuit_key`, `circuit_image`, `circuit_info_url` (JSON do MultiViewer), `circuit_short_name`, `circuit_type` (`Permanent`, `Temporary - Street`, `Temporary - Road`), `country_code`, `country_flag`, `country_key`, `country_name`, `date_end`, `date_start`, `gmt_offset`, `is_cancelled`, `location`, `meeting_key`, `meeting_name`, `meeting_official_name`, `year`.

### overtakes
Só corrida; inclui trocas por pit stop e punições pós-corrida. Dados podem estar incompletos.
Exemplo: `overtakes?session_key=9636&overtaking_driver_number=63&overtaken_driver_number=4&position=1`
Campos: `date`, `meeting_key`, `overtaken_driver_number`, `overtaking_driver_number`, `position` (do ultrapassador após a manobra), `session_key`.

### pit
Exemplo: `pit?session_key=9877&stop_duration<2.3`
Campos: `date`, `driver_number`, `lane_duration` (s no pit lane), `lap_number`, `meeting_key`, `pit_duration` (deprecated = `lane_duration`), `session_key`, `stop_duration` (tempo parado; disponível desde o GP dos EUA 2024).

### position
Exemplo: `position?meeting_key=1217&driver_number=40&position<=3`
Campos: `date`, `driver_number`, `meeting_key`, `position` (começa em 1), `session_key`.

### race_control
Exemplo: `race_control?flag=BLACK AND WHITE&driver_number=1&date>=2023-01-01&date<2023-09-01`
Campos: `category` (`SessionStatus`, `CarEvent`, `Drs`, `Flag`, `SafetyCar`…), `date`, `driver_number`, `flag` (`GREEN`, `YELLOW`, `DOUBLE YELLOW`, `CHEQUERED`…), `lap_number` (corridas), `meeting_key`, `message`, `qualifying_phase` (1–3), `scope` (`Track`, `Driver`, `Sector`…), `sector`, `session_key`.

### sessions
Atualizado diariamente à meia-noite UTC.
Exemplo: `sessions?country_name=Belgium&session_name=Sprint%20Qualifying&year=2023`
Campos: `circuit_key`, `circuit_short_name`, `country_code`, `country_key`, `country_name`, `date_end`, `date_start`, `gmt_offset`, `is_cancelled`, `location`, `meeting_key`, `session_key`, `session_name` (`Practice 1`, `Qualifying`, `Race`…), `session_type` (`Practice`, `Qualifying`, `Race`), `year`.

### session_result
Aparece alguns minutos após a publicação do resultado oficial.
Exemplo: `session_result?session_key=7782&position<=3`
Campos: `dnf`, `dns` (só quali/corrida), `dsq`, `driver_number`, `duration` (melhor volta em treino/quali; tempo total em corrida; em quali, array Q1/Q2/Q3), `gap_to_leader` (s ou `+N LAP(S)`; array em quali), `number_of_laps`, `meeting_key`, `position`, `session_key`.

### starting_grid
Exemplo: `starting_grid?session_key=7783&position<=3`
Campos: `position`, `driver_number`, `lap_duration` (volta da quali, s), `meeting_key`, `session_key`.

### stints
Exemplo: `stints?session_key=9165&tyre_age_at_start>=3`
Campos: `compound` (`SOFT`, `MEDIUM`, `HARD`…), `driver_number`, `lap_end`, `lap_start`, `meeting_key`, `session_key`, `stint_number`, `tyre_age_at_start`.

### team_radio
Seleção limitada; a F1 não libera rádio de todas as sessões.
Exemplo: `team_radio?session_key=9158&driver_number=11`
Campos: `date`, `driver_number`, `meeting_key`, `recording_url` (MP3), `session_key`.

### weather
Exemplo: `weather?meeting_key=1208&wind_direction>=130&track_temperature>=52`
Campos: `air_temperature` (°C), `date`, `humidity` (%), `meeting_key`, `pressure` (mbar), `rainfall`, `session_key`, `track_temperature` (°C), `wind_direction` (0–359°), `wind_speed` (m/s).

## 6. Tabelas de códigos

**DRS (`car_data.drs`)**

| Valor | Significado |
|---|---|
| 0, 1 | Desligado |
| 8 | Detectado, elegível ao entrar na zona de ativação |
| 10, 12, 14 | Ligado |
| 2, 3, 9 | Não documentado |

**Segmentos de setor (`laps.segments_sector_*`)**

| Valor | Significado |
|---|---|
| 0 | Indisponível |
| 2048 | Setor amarelo |
| 2049 | Setor verde |
| 2051 | Setor roxo |
| 2064 | Pit lane |
| 2050, 2052, 2068 | Não documentado |

## 7. Deprecações e ressalvas

- `drivers.country_code` e `pit.pit_duration` estão deprecated (remoção prevista após 2026).
- `team_radio`: cobertura caiu bastante em 2026; a maioria dos eventos não tem rádio.
- `overtakes` pode estar incompleto.
- Segmentos de `laps` não estão disponíveis em corridas; cores podem não bater com a TV.
- `location` não mostra posição lateral; a origem é arbitrária.
- `championship_*` estão em beta.

## 8. Fluxo típico de uso

1. `meetings?year=2024` → obter `meeting_key`.
2. `sessions?meeting_key=...&session_name=Race` → obter `session_key`.
3. `drivers?session_key=...` → pilotos e números.
4. `laps`, `stints`, `pit`, `position`, `weather`... com `session_key` (e `driver_number`).

```python
import requests

BASE = "https://api.openf1.org/v1"

session = requests.get(
    f"{BASE}/sessions",
    params={"year": 2023, "country_name": "Belgium", "session_name": "Race"},
).json()[0]
laps = requests.get(
    f"{BASE}/laps", params={"session_key": session["session_key"], "driver_number": 1}
).json()
```

Operadores de comparação com `requests`: inclua-os na chave, ex. `params={"speed>=": 315}`, ou monte a URL manualmente.

## 9. Não documentado na página

- Limites de taxa (rate limit).
- Paginação e formato de respostas de erro.
- Autenticação/formato de chave e streaming em tempo real (MQTT/WebSocket); a página só remete a um tutorial separado.
