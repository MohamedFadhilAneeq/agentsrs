# AgentSRS — How to Run

> **Audit date:** 2026-09-27. All commands and file paths in this document are verified against `eval.bat` and project source. Where something is uncertain or unverified, it is explicitly marked.

---

## 1. Prerequisites

- A `.conda` Python environment in the project root (see Section 2)
- Groq API key(s) configured in your environment or `.env` file (the LLM client uses Groq as the active provider)
- PowerShell (commands below are written for PowerShell)

> [!NOTE]
> An Ollama code path exists in `backend/llm/client.py` but it is **not the active configuration**. Whether Ollama can be substituted without code changes is unverified.

---

## 2. Environment

The `.conda` environment already exists in the project root. No re-creation is needed for normal use.

If you need a **fresh install** (e.g., on a new machine), install from `requirements.txt`:

```powershell
# From the project root
.conda\python.exe -m pip install -r requirements.txt
```

Packages pinned in `requirements.txt`:

| Package | Minimum version |
|---|---|
| `requests` | 2.31 |
| `python-dotenv` | 1.0 |
| `fastapi` | 0.110 |
| `uvicorn` | 0.29 |
| `python-multipart` | 0.0.9 |

---

## 3. Starting the Web Frontend

Run this command from the project root:

```powershell
$env:PYTHONUTF8=1; .conda\python.exe -m uvicorn backend.api:app --reload --port 8000
```

- Serves on **http://localhost:8000**
- `--reload` enables hot-reload on source changes

Once the server is running, open `http://localhost:8000` in a browser. The frontend (`frontend/index.html`) is a single-file UI.

> [!NOTE]
> The exact tab names/labels in `frontend/index.html` are not listed in the verified audit. The tabs referenced below (Tab 1, Tab 2) reflect what is known from the run commands and API routes. Verify tab labels in the browser on first launch.

---

## 4. Evaluation Commands

| Command | What it does | Hits live Groq API? | Approx. time |
|---|---|---|---|
| `.\eval.bat --show` | Display saved evaluation results (Studies 1 & 2) | No | Instant |
| `.\eval.bat --show --pure` | Display saved evaluation results including Study 3 (pure) | No | Instant |
| `.\eval.bat groq` | Re-run Studies 1 & 2 fresh | **Yes** | ~25–35 min |
| `.\eval.bat groq --force` | Re-run Studies 1 & 2 (force, ignores cache) | **Yes** | ~25–35 min |
| `.\eval.bat --pure groq` | Re-run Study 3 fresh | **Yes** | ~45 min |
| `$env:PYTHONUTF8=1; .conda\python.exe judge_check.py` | Interactive judge spot-check | No | Interactive |
| `$env:PYTHONUTF8=1; .conda\python.exe -m backend.main backend/data/sample_srs_with_description.txt groq` | Run CLI pipeline on a sample file | **Yes** | Varies |

> [!IMPORTANT]
> Commands marked **Yes** under "Hits live Groq API?" consume Groq API quota and rate-limited tokens. Do not run these unless you intend to use credits.

---

## 5. Demo Inputs for Tab 1 (Single Requirement Analysis)

Tab 1 corresponds to the `/analyze-single` API route. Use this verified input (sourced from `backend/data/demo_srs_showcase.txt`):

**Description field:**
```
The THEMAS system shall check if reported temperatures exceed set limits. Exceedances will be reported, while temperatures within limits will be output for further processing. If the temperature is below the lower limit a separate alert should be raised. Normal readings should be silently logged.
```

**Requirement field:**
```
When the temperature exceeds the set limit, the system shall trigger an alarm.
```

Expected output: completeness gaps (missing lower-limit alert, silent logging, exceedance reporting detail) + ambiguity flag ("set limit" — no numeric value defined). Output varies slightly between runs due to LLM non-determinism.

> [!NOTE]
> The ambiguity agent occasionally returns "Unambiguous" for this input due to temperature=0.2 non-determinism. This is normal LLM behaviour, not a bug. See LIMITATIONS_AND_OPEN_ITEMS.md.

---

## 6. File Upload for Tab 2

Tab 2 accepts a `.txt` file upload (one requirement per line; optional `description || spec` format).

**Verified demo file (5 requirements, mixed issues):**
```
backend/data/demo_srs_showcase.txt
```

**Alternative (3 requirements, paired format):**
```
backend/data/sample_srs_with_description.txt
```

---

## 7. Troubleshooting

### 1. Unicode / encoding errors on Windows
**Symptom:** Garbled text or `UnicodeDecodeError` in the terminal.  
**Fix:** Ensure `$env:PYTHONUTF8=1` is set before every command, exactly as shown in Section 4. This forces Python to use UTF-8 on Windows.

### 2. Server not starting — port already in use
**Symptom:** `[ERROR] Address already in use` on port 8000.  
**Fix:** Find and kill the process using port 8000:
```powershell
netstat -ano | findstr :8000
# Note the PID from the last column, then:
taskkill /PID <PID> /F
```
Then re-run the server command.

### 3. Groq API errors / rate limits during evaluation
**Symptom:** Errors or timeouts during `.\eval.bat groq` runs.  
**Fix:** The LLM client (`backend/llm/client.py`) supports multi-key round-robin via `_rotate_key`. Ensure multiple Groq API keys are configured if hitting rate limits. Exact environment variable names for key configuration are **not listed in the verified audit** — check `.env.example` or `backend/llm/client.py` directly.

### 4. `ModuleNotFoundError` when running commands
**Symptom:** Python cannot find `backend` or other modules.  
**Fix:** All commands must be run from the **project root** (`c:\Users\fadhi\OneDrive\Documents\agentsrs\`). Do not `cd` into subdirectories before running. The `-m` flag requires the project root to be the working directory.
