# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Initial open-source release, planned as **0.1.0**.

### Added

- **Document ingestion** — upload PDF, HTML, Markdown, and plain-text sources; text extraction,
  heading-aware chunking, and in-app preview.
- **Research agent** — a tool-using agent that reads the sources and streams a draft Process
  Definition Document (PDD), knowledge items, and prioritized open questions.
- **SME chat with tools** — context-aware chat on the PDD, code, and test pages; the agent can
  edit the PDD, record knowledge, create and resolve questions, edit generated code, and manage
  test cases.
- **Evidence and provenance** — PDD statements linked to source evidence spans, document-removal
  impact analysis, change events, and PDD versioning with version diffs.
- **Coding agent** — generates a multi-file, test-driven Python automation project from the PDD
  (plan, code, test, fix), with a code-to-PDD-step mapping, stale-code detection, and project
  download.
- **Test suite** — golden test cases with CSV/JSONL import, per-step assertions, and three
  execution modes: generated code, LLM-only execution of the PDD, or both side by side.
- **Domain packs** — `examples/<pack>/pack.json` bundles a domain's sources, golden tests,
  output contract, agent guidance, sample outputs and an optional reference engine. The core
  agent prompts are domain-neutral; domain specifics come from the pack.
- **Mortgage income verification pack** — links to the public Fannie Mae Selling Guide, a
  synthetic lender overlay, five golden test cases, sample outputs, and a reference engine
  that passes every golden test offline.
- **Load example** — one click in the UI (or `python backend/seed.py`) creates a fully
  populated example process; no API key needed to explore it or run code-mode tests.
- **Multi-provider LLM support** — Anthropic (default `claude-opus-5-5`, with server-side
  refusal fallback) and any OpenAI-compatible endpoint, including Ollama and vLLM.
- **Background jobs** — research, coding and test runs keep running when the browser
  disconnects; the UI re-attaches to the event stream automatically.
- **Sandboxed execution** — generated code (coding-agent tests and test-suite runs) always
  runs in a subprocess with an allow-listed environment (no secrets), path validation, and
  a timeout.
- **Docker Compose quick start** with automatic migrations and seeding.
- Request audit logging and security headers.
- Project documentation: architecture guide, glossary, target-architecture vision, roadmap,
  security policy, code of conduct, and contribution templates.
