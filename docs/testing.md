# Testes

## Estratégia

- `tests/unit/`: rápidos e isolados. HTTP é simulado com `responses`; o pipeline usa um
  `FakeClient` em memória e `tmp_path` para o Parquet. Nenhum acesso à rede.
- `tests/fixtures/`: amostras JSON pequenas e sintéticas, no formato da OpenF1
  (inclui duplicados, voltas sem tempo, `+1 LAP` e campos *deprecated*).
- Teste de integração contra a API real, marcado com `@pytest.mark.integration`, fica
  fora do gate padrão.

## Comandos

```bash
# gate oficial
poetry run pytest tests/unit/ --cov=src/f1 --cov-report=term-missing --cov-fail-under=50

# relatório HTML (htmlcov/index.html)
poetry run pytest tests/unit/ --cov=src/f1 --cov-report=html

# integração (usa a API real; respeite os limites de uso)
poetry run pytest tests/integration -m integration
```

## O que é coberto

Sucesso, falha e bordas: entrada vazia, nulos, duplicados, tipos inesperados, `429`/`5xx`
(com retry), `404` (sem retry), timeout, idempotência do pipeline, `--skip-existing` e
códigos de saída da CLI.
