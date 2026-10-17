## Summary

<!-- What does this PR change, and why? Link the issue it addresses. -->

Closes #

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Domain pack / example
- [ ] Documentation
- [ ] Refactor / chore

## How was this tested?

<!-- Describe manual testing (e.g. ran research on the mortgage example) and automated tests. -->

## Checklist

- [ ] **Tests** — added or updated tests for behavior changes; `cd backend && pytest` passes.
- [ ] **Reference engine** — `cd examples/mortgage-income-verification/reference_engine && pytest` passes (if touched).
- [ ] **Lint and build** — `cd frontend && pnpm lint && pnpm build` passes (if the frontend changed).
- [ ] **Migrations** — schema changes include an Alembic migration (`alembic revision --autogenerate -m "..."`), reviewed by hand, and `alembic upgrade head` works on a fresh database.
- [ ] **No secrets or real data** — no API keys, `.env` files, uploaded documents, or real customer data; example data is synthetic.
- [ ] **Docs** — updated `README.md`, `docs/`, or `CHANGELOG.md` (under *Unreleased*) where relevant.
- [ ] The PR is focused on one change.

## Screenshots

<!-- For UI changes, include before/after screenshots. -->
