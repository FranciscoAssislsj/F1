# Guia de contribuição

1. Crie uma branch a partir da `main` (`feat/...`, `fix/...`, `docs/...`); não há push
   direto na `main`.
2. Faça commits pequenos, um propósito por commit, em
   [Conventional Commits](https://www.conventionalcommits.org/)
   (`feat(ingestion): ...`, `fix(transformation): ...`).
3. Código novo vai em `src/f1/`, com *type hints* e docstrings. Transformações são
   funções puras; dependências externas entram por parâmetro.
4. Mudou comportamento? Crie ou atualize os testes e a documentação no mesmo PR.
5. Antes de abrir o PR, rode os quatro comandos de [Desenvolvimento](development.md).
6. Abra um Pull Request. O CI (job `quality`) precisa passar e o PR precisa de revisão.

## Branch protection (configuração manual no GitHub)

Em *Settings → Branches*, proteger a `main` exigindo: PR com revisão aprovada e o
status check `quality`.

## Segurança

Nenhum segredo no código, testes, workflows ou logs. `.env` nunca é versionado;
`.env.example` contém só chaves e valores fictícios.
