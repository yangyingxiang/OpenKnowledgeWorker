# Security Policy

## Supported versions

OpenKnowledgeWorker is pre-1.0 software. Security fixes are made on the `main` branch and
shipped in the latest `0.x` release only.

| Version         | Supported          |
| --------------- | ------------------ |
| Latest `0.x`    | :white_check_mark: |
| Older `0.x`     | :x:                |

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues, discussions,
or pull requests.**

Report them privately using GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability):
open the repository's **Security** tab and choose **Report a vulnerability**.

Please include as much of the following as you can:

- The type of issue (for example: sandbox escape, path traversal, injection, secret leakage,
  stored XSS through uploaded documents).
- The affected file(s), endpoint(s), or component, and the commit or release you tested.
- Step-by-step instructions to reproduce, including any proof-of-concept input.
- The impact you believe the issue has, and how an attacker could exploit it.

Do not include real customer data, API keys, or other secrets in a report.

## What to expect

OpenKnowledgeWorker is maintained by a small team on a best-effort basis. Our targets are:

- **Acknowledgement** of your report within 3 business days.
- **Initial assessment** (severity and whether we can reproduce it) within 10 business days.
- **Fix or mitigation** for confirmed high-severity issues as quickly as practical, typically
  within 90 days. We will keep you informed of progress.
- **Disclosure** through a GitHub Security Advisory once a fix is available. We are happy to
  credit you in the advisory unless you prefer to remain anonymous.

## Security model

Understand these properties before deploying OpenKnowledgeWorker anywhere other than your
own workstation.

### No built-in authentication or multi-tenancy

The API and UI have **no authentication, authorization, or tenant isolation**. Anyone who can
reach the backend can read and modify every process, document, PDD, and generated project,
and can trigger LLM calls billed to your API key. Run it only on a trusted network (for
example, bound to `127.0.0.1`, or behind a VPN or an authenticating reverse proxy).
Authentication (OIDC) and roles are on the [roadmap](ROADMAP.md).

### Execution of LLM-generated code

The coding agent writes Python code and runs it to verify it, and the test suite runs the
generated engine against golden test cases. All of this goes through one module,
[`backend/app/sandbox.py`](backend/app/sandbox.py), and **never** imports or `exec`s generated
code inside the API server process:

- every run is a separate Python subprocess with its working directory set to the project's
  sandbox folder;
- the subprocess gets an **allow-listed** environment (`PATH`, locale and temp-dir variables
  only), so API keys, database URLs and any other secrets in the server's environment are
  not visible to generated code;
- each run is bounded by a timeout (`SANDBOX_TIMEOUT`, default 120 seconds);
- file paths written by the agent are validated to stay inside the project directory.

**This is not a container or VM boundary.** The subprocess runs as the same OS user as the
backend, with the same filesystem and network access. A malicious or prompt-injected
document could steer the agent into generating harmful code. If you process documents you do
not fully trust, or expose the application to users you do not fully trust, run the backend
inside a container or VM with minimal privileges, no access to production networks, and no
credentials beyond the LLM API key. A container-based sandbox is on the
[roadmap](ROADMAP.md).

### Uploaded documents

Uploaded source documents (PDF, HTML, Markdown, text) are stored on the backend's local disk
(`UPLOAD_DIR`) and **served back by the API** for in-app preview. Uploaded HTML is served as
uploaded; treat document upload as a trusted operation and do not let untrusted users upload
files.

### Secrets and data

- Keep API keys and database credentials in `.env` at the repository root (see
  [`.env.example`](.env.example)). **Never commit `.env` files.**
- Document text, chat messages, and PDD content are sent to the configured LLM provider.
  Do not upload documents you are not permitted to share with that provider.
- Example and test data in this repository must be synthetic. Never commit real customer data.

### Request auditing

Mutating API requests are recorded in an audit log table (method, path, and a hash of the
request body). This is a debugging and traceability aid, not a tamper-proof audit trail.
