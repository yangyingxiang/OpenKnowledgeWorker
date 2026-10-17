# Contributing to OpenKnowledgeWorker

Thanks for your interest in improving OpenKnowledgeWorker! Bug reports, docs fixes, new
features and new **domain packs** are all welcome.

## Ways to contribute

- **Pick a starter task:** see [docs/good-first-issues.md](docs/good-first-issues.md) and
  issues labelled `good first issue`.
- **Add a domain pack:** teach OpenKnowledgeWorker a new domain (KYC onboarding,
  invoice matching, procurement approvals, ...) without touching core code. See [examples/README.md](examples/README.md).
- **Try a model:** run the agents on a local or alternative model and report what works
  (see the [roadmap](ROADMAP.md)).
- **Report a bug or propose a feature:** use the issue templates.

For larger changes, open an issue first so we can agree on the approach.

## Development setup

Prerequisites: Python 3.11+, Node.js 20+, [pnpm](https://pnpm.io/), PostgreSQL 14+
(or just Docker: `docker compose up --build`).

```bash
cp .env.example .env && createdb openknowledgeworker
make install    # backend virtualenv, frontend packages, pre-commit hooks
make db seed    # migrations + example domain packs
make backend    # API on :5003
make frontend   # app on :3000
```

You don't need an LLM API key for most work. Backend tests use a scripted fake LLM
(`backend/tests/fakes.py`) and in-memory SQLite. The seeded example and code-mode test runs
also work without a key.

How the code fits together: [docs/architecture.md](docs/architecture.md). Terms:
[docs/glossary.md](docs/glossary.md).

## Before opening a pull request

```bash
make test   # backend + example engine + frontend tests
make lint   # ruff, eslint, prettier (format with: make format)
```

The pre-commit hooks installed by `make install` run the formatters on commit.

- Keep pull requests focused: one change per PR.
- Add or update tests for behaviour changes.
- Database schema changes need an Alembic migration
  (`cd backend && alembic revision --autogenerate -m "describe change"`, then review it).
- Never commit secrets, `.env` files, uploaded documents, third-party documents, or real
  customer data. Example data must be synthetic; link to third-party sources instead of
  copying them.
- Code that runs LLM-generated code must go through `backend/app/sandbox.py`.

## Code style

- **Python:** ruff (lint + format), configured in `ruff.toml`. Line length 120, quotes preserved.
- **TypeScript:** ESLint + Prettier (`frontend/.prettierrc`).
- Agents call the LLM through `app.llm.get_llm()`, never a vendor SDK directly.
- Keep core prompts domain-neutral; put domain knowledge in a domain pack.

## License

By contributing, you agree that your contributions will be licensed under the
[Apache License 2.0](LICENSE).
