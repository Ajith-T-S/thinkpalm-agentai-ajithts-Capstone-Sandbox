#Author
AJITH T S
Tech Lead
Capstone Sandbox — Full Agent Pipeline

What it does :

AI assistant that can ingest a GitHub repository, analyze architecture signals, and generate a structured architecture review that is demo-friendly and easy to run

# AI Architecture Review Assistant

AI Architecture Review Assistant is an end-to-end, agentic mini project that ingests a GitHub repository and generates a structured architecture review report with practical recommendations.

## Project overview
The app analyzes repository metadata, file structure, dependency manifests, and key config signals. It then uses multiple agents to produce a review report covering architecture observations, risks, and next steps.

## Features
- End-to-end architecture analysis from GitHub URL or `owner/repo`
- Multi-agent pipeline:
  - Repository Analysis Agent
  - Architecture Review Agent
  - Report Writer Agent
- LangChain tool-calling for GitHub + analysis + memory operations
- Memory with JSON persistence:
  - stores previous analysis by repo
  - remembers focus/depth preferences
  - compares current vs previous run for architecture drift
- Explicit ReAct-style evidence loop:
  - Thought -> Action -> Observation steps
  - max-iteration guardrails and stop conditions
  - per-step reasoning trace shown in UI and CLI
- Streamlit UI with report sections and markdown download
- CLI mode for terminal workflows

## Architecture flow
User -> Streamlit UI / CLI -> Orchestrator -> Repo Analysis Agent + Tools + Memory -> Architecture Review Agent -> Report Writer Agent -> Markdown Report + UI output

## ReAct loop and drift detection

### ReAct evidence collection loop
The Repository Analysis Agent executes a bounded loop with visible steps:
1. **Thought**: decide the next information gap
2. **Action**: call one tool (`fetch_repo_metadata`, `list_repo_files`, `read_repo_file`)
3. **Observation**: capture what was learned
4. repeat until enough evidence or guardrail stop

Guardrails:
- `MAX_REACT_ITERATIONS` (default `8`)
- stop conditions: `enough_evidence`, `api_error`, `rate_limit`, `max_iterations`
- fallback mode when the loop exits early (partial evidence warning is attached)

Where visible:
- Streamlit tab: **Reasoning Trace**
- CLI output: ReAct summary + recent reasoning steps
- Markdown report: `Reasoning Trace (ReAct)` section

### Architecture drift detection between runs
Each run stores summary metrics in `data/memory_store.json` keyed by `owner/repo`, then compares the new run with the previous one.

Drift output includes:
- `new_risks` and `resolved_risks`
- `risk_delta`, `module_delta`, `dependency_delta`
- `stack_changed`
- `pattern_changes` (`added`/`removed`)
- `drift_status` (`improved`, `stable`, `regressed`)
- `improvement_score` (0-100)

Where visible:
- Streamlit tab: **Architecture Drift**
- CLI output: drift status and score

### Observability and evaluation visibility
To make evaluation straightforward:
- ReAct step traces are stored in each analysis result (`reasoning_trace`, `react_summary`)
- Streamlit exposes **Reasoning Trace**, **Architecture Drift**, and **Reports** tabs
- CLI prints ReAct stop condition, iteration usage, and recent tool steps
- Markdown report includes a `Reasoning Trace (ReAct)` section

## Folder structure
```text
ai-architecture-review-assistant/
├── app.py
├── main.py
├── requirements.txt
├── .env.example
├── README.md
├── docs/
│   ├── architecture_decision_doc.md
│   └── demo_script_outline.md
├── src/
│   ├── agents/
│   │   ├── repo_analysis_agent.py
│   │   ├── architecture_review_agent.py
│   │   └── report_writer_agent.py
│   ├── tools/
│   │   ├── github_tools.py
│   │   ├── analysis_tools.py
│   │   └── memory_tools.py
│   ├── services/
│   │   ├── github_service.py
│   │   ├── llm_service.py
│   │   └── report_service.py
│   ├── memory/
│   │   └── memory_store.py
│   ├── models/
│   │   └── schemas.py
│   └── utils/
│       └── helpers.py
├── data/
│   └── memory_store.json
└── reports/
```

## Setup

### 1) Clone and create virtual environment
```bash
python -m venv .venv
```

Activate:

- Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```

- macOS/Linux:
```bash
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Configure environment
```bash
copy .env.example .env
```
Update `.env` values:
- `OPENAI_API_KEY` (required)
- `OPENAI_MODEL` (default `gpt-4o-mini`)
- `GITHUB_TOKEN` (optional but recommended for higher limits/private repos)
- `MAX_FILES_TO_ANALYZE`
- `MAX_FILE_BYTES`
- `MAX_REACT_ITERATIONS` (default `8`)
- `TARGET_FILE_READS` (default `12`)
- `DEFAULT_REPORT_FOCUS`

## Run Streamlit app (preferred)
```bash
streamlit run app.py
```

UI supports:
- repo URL/owner-repo input
- optional GitHub token
- focus dropdown
- report depth
- section tabs for summary, structure, findings, recommendations, raw evidence, reasoning trace, architecture drift, reports
- markdown report download

## Run CLI
```bash
python main.py analyze langchain-ai/langchain --focus maintainability --report-depth standard
```

Optional token override:
```bash
python main.py analyze microsoft/vscode --github-token <token>
```

## Sample input and output

### Sample input
- Repo: `https://github.com/streamlit/streamlit`
- Focus: `scalability`
- Depth: `standard`

### Sample output sections
- Project overview
- Detected stack
- Module breakdown
- Architecture observations
- Risks / anti-patterns
- Recommendations
- Suggested next steps
- Raw evidence

Generated markdown report is saved under `reports/`.

## 8-minute demo flow
See [`docs/demo_script_outline.md`](docs/demo_script_outline.md). Quick suggested flow:
1. Intro and problem (0:00-0:45)
2. Architecture and agents/tools/memory overview (0:45-2:00)
3. Streamlit run + analysis demo (2:00-5:00)
4. Memory comparison rerun (5:00-6:30)
5. CLI run and repo export location (6:30-7:30)
6. Limitations and future enhancements (7:30-8:00)

## Safeguards included
- Limits files analyzed and file size to control token cost
- Skips likely binary/large generated files
- Handles missing/invalid token cases
- Handles GitHub API errors and rate-limit style failures
- Supports private repos when token permissions allow

## Limitations
- Static repository scan cannot fully validate runtime behavior
- Dependency parsing is heuristic for common manifest formats
- Very large monorepos may need higher limits or scoped analysis
- LLM output can vary by model and prompt behavior
- Drift scoring is heuristic and should be treated as directional guidance
- JSON memory is lightweight and practical, but less scalable than DB/vector-backed memory

## Future improvements
- Add richer diff-based comparisons across commits
- Add pluggable analyzers for security/performance metrics
- Add async retrieval and caching
- Add Claude provider integration path in `llm_service`
- Add unit/integration tests and evaluation suite
