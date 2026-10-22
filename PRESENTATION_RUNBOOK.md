# DevSecOps IA Presentation Runbook

This guide follows the same order we used to get the project working: run the API, verify tests and scanners, install Gitleaks from Command Prompt, connect the existing local project to a new empty GitHub repository, then demonstrate a failed test and recovery in a pull request.

## Important: your terminal is Command Prompt

The examples below use **Command Prompt (cmd.exe)**, identified by a prompt such as:

```text
(.venv) D:\STUDY\Devops LabCA>
```

In Command Prompt, use `cd /d` to change folders. `Set-Location` is a PowerShell command and is not recognized by Command Prompt. Run each command separately and press Enter after each one; do not join commands together.

## What to have open

Before presenting, have these ready:

1. This project open in VS Code.
2. One terminal for the running app.
3. A second terminal for tests, scanners, and Git.
4. A browser tab for the local API and another tab for the GitHub repository.

Do not show or commit real API keys, passwords, tokens, or `.env` files.

## Step 1 — Start the application and show its response

In Command Prompt, go to the project folder:

```cmd
cd /d "D:\STUDY\Devops LabCA"
```

If the prompt does not already show `(.venv)`, activate the existing virtual environment:

```cmd
.\.venv\Scripts\activate.bat
```

If `.venv` does not exist yet, create it and install the project dependencies first:

```cmd
py -3.12 -m venv .venv
.\.venv\Scripts\activate.bat
python -m pip install -r requirements-dev.txt
```

Start the application in this terminal:

```cmd
python -m app
```

Keep this terminal open. In the browser, visit:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Show the other endpoints too:

```text
http://127.0.0.1:8000/api/greet/Ada
```

In a **second Command Prompt** opened in the project folder, run the addition request:

```cmd
curl.exe -X POST -H "Content-Type: application/json" -d "{\"left\":2,\"right\":3}" http://127.0.0.1:8000/api/add
```

Expected response:

```json
{"result":5}
```

Explain that this project is an API with JSON responses; it does not have a graphical website or dashboard.

## Step 2 — Run unit tests

In the second terminal, make sure you are on the clean `main` branch before running the passing test suite:

```cmd
git switch main
python -m pytest -q
```

Expected result on the clean main branch:

```text
18 passed
```

The deliberate failing test belongs on `demo/failing-test`, not `main`. Check the branch and file status before continuing:

```cmd
git status --short --branch
if exist tests\test_pipeline_demo.py echo WARNING: demo failure test is present
if not exist tests\test_pipeline_demo.py echo Clean main branch: demo failure test is absent
```

If the warning appears on `main`, do not push it as your clean starting version. Remove it, commit that cleanup, and then continue:

```cmd
del tests\test_pipeline_demo.py
git add -u
git commit -m "Keep main branch tests passing"
```

Only run `del` if the file exists on `main`.

## Step 3 — Run security checks and explain the demos

Run the scanners against the real project:

```cmd
python -m bandit -q -r app -ll
python -m pip_audit -r requirements.txt
.\.tools\gitleaks.exe dir . --no-banner --redact --exit-code 1
```

Expected for the validated project: Bandit reports no app findings, pip-audit reports no known runtime dependency vulnerabilities, and Gitleaks reports no leaks.

Run the safe demonstration fixtures separately:

```cmd
python scripts/scanner_demo.py bandit
python scripts/scanner_demo.py gitleaks
```

Each demo creates a temporary synthetic finding, scans it, then removes it. Bandit will print its intentional `shell=True` finding. Gitleaks will say it found a leak in the temporary dummy fixture. The final `PASS` means the scanner correctly detected its demo example; it does **not** mean that the actual project contains that issue.

### If Gitleaks is missing

The binary is installed locally under `.tools`, not on the system PATH. From Command Prompt, run:

```cmd
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\install_gitleaks.ps1"
```

Then verify and run the demo:

```cmd
.\.tools\gitleaks.exe version
python scripts/scanner_demo.py gitleaks
```

The expected installed version is `8.30.1`. The installer verifies the official release checksum. If download fails, check your network or proxy access to GitHub release downloads, then retry. Do not download Gitleaks from unofficial sources.

## Step 4 — Create a new, empty GitHub repository

1. Sign in to GitHub and choose **New repository**.
2. Give it a name for the presentation, for example `devsecops-ia-demo`.
3. Choose **Private** if you want the work hidden from public view.
4. Do not initialize it with a README, `.gitignore`, or license. The local project already has files and Git history.
5. Create the repository and copy its HTTPS URL. It should look like:

   ```text
   https://github.com/YOUR-USERNAME/devsecops-ia-demo.git
   ```

Replace `YOUR-USERNAME` and the repository name with the exact values from GitHub. Never use the literal placeholder URL.

## Step 5 — Point this project at the new repository and push clean main

This workspace already has a Git remote named `origin`. The presentation guide and its README link are currently uncommitted on the demo branch. Switch to `main`; Git should carry these non-conflicting documentation changes with you:

```cmd
git switch main
git status --short --branch
```

Save the guide on `main` so it is included in the new repository:

```cmd
git add README.md PRESENTATION_RUNBOOK.md
git commit -m "Add DevSecOps presentation guide"
```

If Git says there is nothing to commit, the guide is already committed; continue. If Git refuses to switch branches or reports a conflict, stop and do not discard changes.

Change the existing `origin` URL to your new repository; do **not** run `git remote add origin` again:

```cmd
git status --short --branch
git remote set-url origin https://github.com/YOUR-USERNAME/devsecops-ia-demo.git
git remote -v
```

Confirm the fetch and push URLs both show the new repository. Then push the clean main branch:

```cmd
git push -u origin main
```

GitHub may ask you to authenticate. Use the browser/Git Credential Manager sign-in flow. Do not put a password or token into the URL or a command.

If `git push` says the remote contains work you do not have locally, the new repository was probably initialized with files. For the simplest college demonstration, create another empty GitHub repository and use its URL. Do not force-push.

## Step 6 — Show the successful GitHub Actions run

1. Open the new repository page on GitHub.
2. Select **Actions**.
3. Open the latest **DevSecOps pipeline** run.
4. Wait for the run to finish, then open **Tests and security gates**.
5. Show the test, Bandit, Gitleaks, and dependency-audit step results.
6. If the required checks pass, show **Build container after quality gates**.

The AI report is optional/advisory and may say it was skipped when no `AI_API_KEY` is configured. Deployment is disabled unless separately configured. The GitHub workflow builds an image on the GitHub runner; it does not publish that image to a registry.

## Step 7 — Demonstrate a failing test without breaking main

The current workspace already has a `demo/failing-test` branch whose committed version contains the intentional test file [tests/test_pipeline_demo.py](./tests/test_pipeline_demo.py). Start from main and then switch to that demonstration branch:

```cmd
git switch main
git switch demo/failing-test
git status --short --branch
```

If the status shows `D tests/test_pipeline_demo.py` or the file is missing, there is a local, uncommitted deletion. To repeat the failing-test demonstration, first inspect that status. Only if you want to bring back the intentional failing test, restore that one demo file from the branch commit:

```cmd
git restore --source=HEAD -- tests\test_pipeline_demo.py
```

This command discards the local deletion of that specific demo test. Do not run it if you meant to keep the deletion. Confirm the test file is present, then push the demonstration branch to the **new** repository:

```cmd
type tests\test_pipeline_demo.py
git push -u origin demo/failing-test
```

The file should show this intentional failing test:

```python
def test_demo_failure_blocks_pipeline():
    assert False, "intentional demonstration failure"
```

The push starts a workflow run. For a clear pull-request demonstration:

1. On GitHub, choose **Compare & pull request** for `demo/failing-test`, or open **Pull requests → New pull request**.
2. Set the base to `main` and compare branch to `demo/failing-test`.
3. Create the pull request.
4. Open its **Checks** or the linked Actions run.
5. Show that **Run unit tests** fails and **Build container after quality gates** does not run because its required job failed.

This intentionally demonstrates the quality gate. Do not merge a pull request while its required checks are failing.

## Step 8 — Fix the test and show recovery

On the `demo/failing-test` branch, remove only the temporary failing test:

```cmd
git switch demo/failing-test
if exist tests\test_pipeline_demo.py del tests\test_pipeline_demo.py
git add -u
git commit -m "Remove failing pipeline demonstration test"
git push
```

The pull request should update automatically and start a new workflow run. Refresh its checks and show the tests and mandatory scanners passing, followed by the Docker build. You may close the demonstration pull request without merging it; this keeps the exercise isolated.

Return to the clean main branch when finished:

```cmd
git switch main
git status --short --branch
```

## What to say while presenting

### Opening

> “My project is a small Python API used to demonstrate DevSecOps. I have automated tests and security scans in a GitHub Actions pipeline so code is checked before the Docker image build.”

### While showing the API

> “This response is from the health endpoint. The application also has a greeting endpoint and an addition endpoint. It returns JSON and does not have a graphical user interface.”

### While showing tests and scanners

> “Pytest checks application behavior. Bandit checks Python security patterns, Gitleaks looks for exposed secrets, and pip-audit checks runtime dependencies for known advisories. The temporary scanner demos intentionally produce findings so I can show that each tool detects its example.”

### While showing GitHub Actions

> “A push or pull request starts the workflow. The tests and security scans are required gates. Docker build depends on those checks passing, so a failed test prevents the build job from running.”

### While explaining the failing-test scenario

> “I added a deliberately failing test on a separate demonstration branch. The Actions run failed at the test gate, and the dependent Docker build was skipped. I removed the demo test and pushed again; the new run passed.”

### Closing

> “The main result is an automated quality and security gate before container build. AI review is optional advice, not a replacement for scanners. Deployment is disabled by default.”

## What is actually built—and what is not

**Built and locally verified:**

- Flask API with health, greeting, and addition endpoints.
- Automated pytest suite and separate AI-review input validation tests.
- Bandit, Gitleaks, and pip-audit checks, with safe temporary scanner demonstrations.
- GitHub Actions workflow for tests/scans, gated Docker build, optional advisory AI report, and an opt-in deployment webhook.
- Dockerfile configured for a non-root runtime user.
- Gitleaks Windows x64 installer that verifies the published checksum.

**Do not claim these have been completed unless you configure and demonstrate them:**

- There is no graphical user interface; the API responds with JSON.
- AI review requires a real API key and provider configuration. Without them, no AI review request is sent.
- The deployment webhook is only an integration hook; no cloud deployment service, infrastructure, or registry publishing is configured.
- Docker was not installed in the local workspace during development. GitHub Actions builds the image on its hosted runner after gates pass; that is distinct from a local Docker build.
- GitHub Actions is visible only after pushing to a GitHub repository with Actions enabled. A push runs CI but does not make the API publicly accessible.

## Troubleshooting during the presentation

- **`Set-Location` is not recognized:** you are in Command Prompt. Use `cd /d "D:\STUDY\Devops LabCA"` instead.
- **`remote origin already exists`:** use `git remote set-url origin <your-new-repository-url>` instead of adding `origin` again.
- **`Repository not found`:** verify the repository exists, the URL exactly matches GitHub, and you are signed in with access.
- **Gitleaks is not on PATH:** run it as `.\.tools\gitleaks.exe`; the installer keeps it local to the project.
- **The tests fail on main:** check whether the intentional `tests\test_pipeline_demo.py` is present. Keep that file only on the demo branch.
- **No Actions run appears:** confirm the push succeeded, Actions are enabled, and you are looking at the correct repository.
- **The application is already running:** leave its terminal open and use a second terminal for commands. If port 8000 is occupied, stop the other server with Ctrl+C or choose another port before starting.
