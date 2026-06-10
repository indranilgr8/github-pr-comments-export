# GitHub PR Comments Export

> A lightweight Python CLI utility to extract all pull request comments, inline review feedback, and review events from one or many GitHub PRs — exported as a single, analysis-ready CSV file.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![GitHub API](https://img.shields.io/badge/GitHub%20API-REST%20v3-181717?logo=github)
![License](https://img.shields.io/badge/License-MIT-green)
![Read Only](https://img.shields.io/badge/API%20Access-Read--Only-brightgreen)

---

## Why This Tool Exists

When managing large engineering teams, analyzing PR review patterns across dozens of pull requests manually is slow and error-prone. This utility was built to automate the extraction of review comments at scale — enabling data-driven insights into code review quality, reviewer engagement, and feedback trends across entire sprints or release cycles.

---

## What It Exports

For each PR, the tool captures three comment sources via the GitHub REST API:

| Source | API Endpoint |
|---|---|
| Conversation comments | `/issues/{pr}/comments` |
| Inline review comments | `/pulls/{pr}/comments` |
| Review events (approved, changes requested, etc.) | `/pulls/{pr}/reviews` |

All output is merged into a single CSV with PR identifiers, making it safe to combine data across multiple repositories or time periods.

---

## Output CSV Columns

```
pr_owner | pr_repo | pr_number | pr_url | comment_id | comment_type |
author | body | created_at | updated_at | path | line | state
```

---

## Requirements

- Python 3.9+
- A GitHub Personal Access Token (PAT) with the following **read-only** permissions:
  - Fine-grained PAT: `Pull Requests (Read)`, `Issues (Read)`, `Metadata (Read)`
  - Classic PAT: `repo` (read) — use minimal scopes only

No third-party libraries required — uses Python standard library + `requests`.

---

## Installation

```bash
git clone https://github.com/indranilgr8/github-pr-comments-export.git
cd github-pr-comments-export
pip install requests
```

---

## Usage

### Single PR (PowerShell)

```powershell
$env:GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"
python .\export_github_pr_comments_csv.py `
  --pr-url "https://github.com/OWNER/REPO/pull/123" `
  --output-csv "PR_123_comments.csv"
```

### Single PR (Bash / macOS / Linux)

```bash
export GITHUB_TOKEN="YOUR_GITHUB_TOKEN"
python export_github_pr_comments_csv.py \
  --pr-url "https://github.com/OWNER/REPO/pull/123" \
  --output-csv "PR_123_comments.csv"
```

### Batch Export from File

Create a `pr_list.txt` file with one PR URL per line:

```
https://github.com/OWNER/REPO/pull/101
https://github.com/OWNER/REPO/pull/102
https://github.com/OWNER/REPO/pull/103
# Lines starting with # are ignored
```

Then run:

```bash
python export_github_pr_comments_csv.py \
  --pr-list-file "./pr_list.txt" \
  --output-csv "sprint_review_comments.csv"
```

### Token Resolution Order

The script resolves your GitHub token in this priority order:

1. `--token` flag (explicit)
2. `GITHUB_TOKEN` environment variable
3. `--token-file` flag (path to a file containing your token)
4. Default `.github_token` file in the same directory

---

## CLI Reference

| Flag | Description |
|---|---|
| `--pr-url` | Single PR URL to export |
| `--pr-list-file` | Path to a text file containing multiple PR URLs |
| `--output-csv` | Output file path (`.csv` extension auto-appended if missing) |
| `--token` | GitHub PAT (overrides environment variable) |
| `--token-file` | Path to a file containing your token |

---

## Security & Safety

This tool is **strictly read-only**:

- Only calls `GET` endpoints — no `POST`, `PATCH`, `PUT`, or `DELETE`
- Validates all API URLs to ensure they stay on `https://api.github.com`
- Validates all pagination links before following them
- Never writes back to GitHub in any form

**Token hygiene tip:** Store your token in a `.github_token` file and add it to `.gitignore` — never commit tokens to source control.

---

## Use Cases

- **Sprint retrospectives** — analyze review comment volume and patterns across a sprint
- **Engineering metrics** — measure reviewer engagement, feedback density, and response time
- **Code review audits** — export historical review data for compliance or quality reports
- **Team insights** — identify top reviewers and common feedback themes across a codebase

---

## Contributing

Issues and PRs are welcome. If you extend this tool to support additional output formats (JSON, Excel, Markdown tables), feel free to open a pull request.

---

## License

MIT License — free to use, modify, and distribute.
