# AI-Powered Code Review, Security Analysis & Automated DevSecOps Pipeline

A small, runnable Python web service demonstrating how automated tests, static security tools, an optional AI reviewer, Docker, and CI/CD gates fit together. The sample is intentionally compact enough for a college DevOps IA and is not a production deployment template.

## Overview and architecture

The Flask application exposes a health check, a greeting endpoint, and a JSON addition endpoint. Pytest verifies behavior. Bandit checks the application source, Gitleaks scans the checked-out repository, and pip-audit checks the pinned runtime dependencies. An optional AI reviewer accepts an allow-listed, locally sanitized Git diff and writes an advisory Markdown report. The GitHub Actions workflow builds a container only when all mandatory checks pass. A deployment webhook runs only after the build and only when explicitly enabled for a push to `main`.

```text
Push / pull request
        |
        v
Install -> Pytest -> Bandit -> Gitleaks -> pip-audit
        |                 (all required gates must pass)
        +---- optional AI review (advisory; artifact)
                          |
                          v
                    Docker build
                          |
          main + DEPLOY_ENABLED=true + credentials
                          v
              HTTPS deployment webhook
```

AI output is deliberately kept separate from scanner results. It cannot override a failed test or scanner and never constitutes a security finding from Bandit, Gitleaks, or pip-audit.

## Technology choices

| Tool | Purpose |
| --- | --- |
| Python 3.12, Flask | Small HTTP application with a built-in test client |
| Pytest | Repeatable API and input validation tests |
| Bandit | Python static security analysis |
| Gitleaks | Detect credentials committed to the repository |
| pip-audit | Check runtime dependencies against vulnerability advisories |
| GitHub Actions | Automate checks, gated container build, and optional deployment hook |
| Docker, Gunicorn | Reproducible container running as a non-root user |
| OpenAI-compatible API | Optional advisory review of sanitized code diffs |

## Project structure

```text
.
|-- .github/
|   `-- workflows/
|       `-- devsecops.yml
|-- app/
|   |-- __init__.py
|   `-- __main__.py
|-- scripts/
|   `-- scanner_demo.py
|-- tests/
|   `-- test_app.py
|-- tools/
|   `-- ai_review.py
|-- .dockerignore
|-- .gitignore
|-- Dockerfile
|-- README.md
|-- requirements-dev.txt
`-- requirements.txt
```

## Local installation and execution

Use Python 3.12 or newer. From the project root, create and activate a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Run the server:

```powershell
python -m app
```

The server listens at `http://127.0.0.1:8000` (the Flask development server is for local demonstration only). Try these requests:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/greet/Ada
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/add `
  -ContentType 'application/json' -Body '{"left":2,"right":3}'
```

Set `PORT` to change the local port. Invalid input returns HTTP 400; booleans, non-finite values, non-JSON bodies, and excessively long names are rejected.

## Run tests and security checks locally

```powershell
python -m pytest -q
python -m bandit -q -r app -ll
python -m pip_audit -r requirements.txt
```

Install Gitleaks for the current project (Windows x64; downloads the official release and verifies its published SHA-256 checksum) with:

```powershell
.\scripts\install_gitleaks.ps1
```

This installs a local, ignored binary at `.tools\gitleaks.exe`; it does not change system `PATH`. The scanner demo automatically detects that binary. To scan the working tree directly with:

```powershell
gitleaks dir . --no-banner --redact --exit-code 1
```

The pipeline uses the Gitleaks GitHub Action. A finding produces a non-zero result; reports are redacted. Dependency audit requires access to the Python package advisory service.

### Safe scanner demonstrations

The normal application deliberately contains no vulnerable code or credential. Instead, each command below creates a short-lived fixture in the system temporary directory and statically scans it; the fixture is automatically removed. The high-entropy dummy API-key value is assembled at runtime and is never a real credential or committed to the repository.

```powershell
python scripts/scanner_demo.py bandit
python scripts/scanner_demo.py gitleaks
```

Bandit should report the `subprocess` call with `shell=True`; Gitleaks should report the synthetic API-key-shaped value. These expected detections return success from the demo script. Do not commit real credentials to reproduce a finding.

## Optional AI code review

The AI integration is off by default. It uses an OpenAI-compatible Chat Completions API, with `AI_API_URL` defaulting to `https://api.openai.com/v1/chat/completions`. The local workspace must be a Git repository with a baseline commit; only changed/tracked diffs are reviewed. Configure the endpoint, model, and API key in your local environment (never in source control):

```powershell
$env:AI_API_KEY = 'your-provider-key'
$env:AI_MODEL = 'gpt-4o-mini'
# Optional compatible endpoint; HTTPS is required.
$env:AI_API_URL = 'https://api.openai.com/v1/chat/completions'
python tools/ai_review.py --output artifacts/ai-review.md
```

For a fresh workspace, initialize Git, create a baseline commit, then modify tracked files before requesting a review. The AI step in CI receives the pull request base or previous push commit automatically.

By default, the tool reviews the working-tree and staged changes relative to `HEAD`. Use `--base <commit>` to review `<commit>...HEAD`, which is useful for pull requests. It only sends allow-listed source/documentation diff paths; environment files, key/certificate files, and paths with secret/credential names are excluded. Before sending, it redacts common secret assignments, known token formats, bearer tokens, private-key blocks, and long high-entropy quoted strings. The diff is size-limited. No API key means a `skipped` report and no network request. API errors or invalid model responses produce an `error` report but do not fail tests or security gates. Review the redaction and report before using this demonstration with sensitive code; no automatic redaction can identify every possible credential.

Example report:

```markdown
# Advisory AI Code Review
**Status:** complete

> AI-generated advice is unverified and advisory only...

## Findings
### 1. [medium] Handle missing record
- **File:** `app/routes.py` (line 42)
- **Category:** Bug
- **Recommendation:** Return a 404 response when the record is absent.
```

AI findings are model-generated examples only; actual findings depend on the diff and provider response. The pipeline runs this step only when `AI_API_KEY` is configured. It uploads `artifacts/ai-review.md` as an Actions artifact, and review errors are advisory (`continue-on-error`).

## GitHub Actions setup and gates

The workflow at `.github/workflows/devsecops.yml` runs on every push, pull request, or manual dispatch:

1. Checks out the repository and installs the development requirements.
2. Runs pytest, Bandit (`-ll`), Gitleaks, and pip-audit. A failed test or scanner fails the quality-gate job.
3. Runs AI review when configured; it is advisory and its report is uploaded as a short-lived artifact.
4. Builds a Docker image only after all mandatory quality gates pass.
5. Calls the optional deployment webhook only for a push to `main`, after a successful image build, with `DEPLOY_ENABLED` explicitly set to `true`.

To connect this local project to a GitHub repository, create an empty repository on GitHub, then set its remote and push your branch (no remote or push is configured by this project):

```powershell
git add .
git commit -m "Add DevSecOps sample project"
git remote add origin https://github.com/OWNER/REPOSITORY.git
git push -u origin main
```

Use Git Credential Manager or SSH for authentication; never put a personal access token in the remote URL. GitHub Actions starts automatically after the first push. Open the repository's **Actions** tab to follow the check and container-build jobs.

Configure these repository/environment settings only if using the optional features:

| Name | GitHub location | Required | Purpose |
| --- | --- | --- | --- |
| `AI_API_KEY` | Actions secret | No | Enables the optional AI review |
| `AI_API_URL` | Actions variable | No | HTTPS-compatible API endpoint; defaults to OpenAI |
| `AI_MODEL` | Actions variable | No | Model name; defaults to `gpt-4o-mini` |
| `GITLEAKS_LICENSE` | Actions secret | Only for organization-owned repositories | License required by Gitleaks Action for organization repositories; personal-account repositories do not require it |
| `DEPLOY_ENABLED` | Actions variable | No | Must equal `true` to enable the deployment job |
| `DEPLOY_WEBHOOK_URL` | `production` environment secret | If deployment enabled | HTTPS endpoint accepting a POST deployment notification |
| `DEPLOY_WEBHOOK_TOKEN` | `production` environment secret | If deployment enabled | Bearer credential for the webhook |

The webhook receives JSON containing the repository and commit SHA. The endpoint must validate the bearer token and implement its own deployment policy. Configure required reviewers/protection on the `production` environment for an approval gate. The workflow does not create infrastructure or publish the image to a registry. Do not enable the webhook until its behavior and credentials are configured and reviewed. No deployment credentials are needed for local use or for CI testing.

## Docker

Docker must be installed and running. Build and start the container:

```powershell
docker build -t devsecops-sample .
docker run --rm -p 8000:8000 devsecops-sample
```

Then open `http://localhost:8000/health`. The image installs only runtime dependencies, copies only the application package, runs Gunicorn as an unprivileged user, and excludes environment files, Git metadata, tests, and scanner tooling. No secret is passed into the image.

## Expected findings and troubleshooting

| Check | Demonstration | Expected result |
| --- | --- | --- |
| Tests | Run `python -m pytest -q` | All tests pass; a deliberately failing assertion blocks the quality gate |
| Bandit | `python scripts/scanner_demo.py bandit` | Finds `subprocess.call(..., shell=True)` in a temporary fixture |
| Gitleaks | `python scripts/scanner_demo.py gitleaks` | Finds a synthetic high-entropy API key in a temporary fixture |
| pip-audit | `python -m pip_audit -r requirements.txt` | Passes when installed runtime dependencies have no known advisories; an advisory fails the check |
| AI review | Set `AI_API_KEY`, make a code change, run `python tools/ai_review.py` | Writes an advisory Markdown report if the configured API is reachable |

- **Scanner command not found:** install Bandit and pip-audit from `requirements-dev.txt`; install Gitleaks using its official installation instructions.
- **AI report says `skipped`:** check that `AI_API_KEY` is set and that the selected diff contains eligible files. A missing key intentionally sends no code.
- **AI report says `error`:** verify HTTPS endpoint, model name, provider compatibility, quota, and API key. The report is advisory and does not turn a passing security gate into a failure.
- **pip-audit cannot reach its service:** check network access to the Python advisory database; do not suppress findings to make the pipeline green.
- **Gitleaks finds a secret:** revoke/rotate it immediately, remove it from the working tree, and follow repository history remediation guidance. Redaction in scan output does not undo exposure.
- **Docker is unavailable:** local application tests and security checks still work; install/start Docker to validate the image build.
- **Deployment did not run:** verify this is a push to `main`, `DEPLOY_ENABLED` is exactly `true`, and the `production` environment has the two required HTTPS webhook secrets. An enabled deployment with missing/invalid settings fails rather than silently succeeding.

## DevOps IA demonstration checklist

1. Show the application endpoints and the passing local pytest suite.
2. Show the pipeline succeeding on a valid push or pull request.
3. Temporarily introduce a failing test, push a branch, and show the quality gate fail and Docker build remain skipped; revert the test change.
4. Run the Bandit and Gitleaks demo commands to show safe, isolated findings without committing a vulnerability or credential.
5. Add a harmless source change, configure an AI key as a GitHub Secret, and show the optional advisory report artifact. Remove/unset the key to demonstrate that no-key runs skip AI cleanly.
6. Restore valid source and show the checks pass, followed by the Docker build.
7. Explain that deployment stays disabled by default; optionally demonstrate the webhook only with an approved test endpoint and explicitly configured environment secrets.

For the exact Command Prompt order, new-repository setup, failure/recovery demonstration, and speaking script, see [PRESENTATION_RUNBOOK.md](./PRESENTATION_RUNBOOK.md).

## Scope and limitations

This project is an educational baseline, not a complete production security program. AI redaction is best-effort, AI conclusions may be wrong, the sample endpoints are intentionally small, and deployment is an integration hook rather than a cloud deployment implementation. The current workspace may not have Docker, Gitleaks, or an AI credential installed/configured; those steps require the manual setup described above.
