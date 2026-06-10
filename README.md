# GitHub PR Comments Export

This standalone utility exports all comments and review activity from one or many GitHub pull requests into a single CSV file.

## What It Exports

- Issue conversation comments (`/issues/{pr}/comments`)
- Inline review comments (`/pulls/{pr}/comments`)
- Review events (`/pulls/{pr}/reviews`)

## Requirements

- Python 3.9+
- A GitHub token with access to the target repository (required for private repos)

Recommended token permissions (read-only):

- Fine-grained PAT: `Pull requests (Read)`, `Issues (Read)`, `Metadata (Read)`
- Classic PAT: use minimal scopes and avoid any write/admin scopes

## Safety: Read-Only API Access

This script is designed to be read-only against PRs.

- It only calls GitHub GET endpoints for:
	- `/issues/{pr}/comments`
	- `/pulls/{pr}/comments`
	- `/pulls/{pr}/reviews`
- It does not send POST, PATCH, PUT, or DELETE requests.
- It validates that every API URL (including pagination links/redirects) stays on `https://api.github.com` and on the allowed read endpoints.

## Usage (PowerShell)

Single PR:

```powershell
$env:GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"
python .\export_github_pr_comments_csv.py --pr-url "https://github.com/OWNER/REPO/pull/123" --output-csv "PR_123_comments.csv"
```

Multiple PRs from input file:

```powershell
@'
https://github.com/OWNER/REPO/pull/123
https://github.com/OWNER/REPO/pull/124
# comments and blank lines are ignored
'@ | Set-Content -Path .\pr_list.txt

python .\export_github_pr_comments_csv.py --pr-list-file ".\pr_list.txt" --output-csv "PR_batch_comments.csv"
```

Or pass token explicitly:

```powershell
python .\export_github_pr_comments_csv.py --pr-url "https://github.com/OWNER/REPO/pull/123" --token "YOUR_GITHUB_TOKEN" --output-csv "PR_123_comments.csv"
```

Or place your token in a file named `.github_token` in the same folder as the script (first non-empty line is used):

```powershell
Set-Content -Path .\.github_token -Value "YOUR_GITHUB_TOKEN"
python .\export_github_pr_comments_csv.py --pr-url "https://github.com/OWNER/REPO/pull/123" --output-csv "PR_123_comments.csv"
```

You can also point to a different token file path:

```powershell
python .\export_github_pr_comments_csv.py --pr-url "https://github.com/OWNER/REPO/pull/123" --token-file "C:\path\to\token.txt" --output-csv "PR_123_comments.csv"
```

Token resolution order:

1. `--token`
2. `GITHUB_TOKEN` environment variable
3. `--token-file` (default `.github_token`)

## PR Input File Format

- One PR URL per line
- Blank lines are ignored
- Lines starting with `#` are treated as comments and ignored

Example `pr_list.txt`:

```text
https://github.com/OWNER/REPO/pull/123
https://github.com/OWNER/REPO/pull/456
```

## Output CSV Columns

The CSV includes PR identifiers so multiple PRs can be merged safely:

- `pr_owner`
- `pr_repo`
- `pr_number`
- `pr_url`
- (all existing comment/review fields)

## Example For Your PR

```powershell
$env:GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"
python .\export_github_pr_comments_csv.py --pr-url "https://github.com/pearson-vle-pvs/pvs-web-connexus/pull/8886" --output-csv "PR_8886_comments.csv"
```

The CSV is written to the file passed via `--output-csv`.

Output behavior details:

- If `--output-csv` has no `.csv` extension, the script appends `.csv` automatically.
- If the output folder does not exist, it is created automatically.
- The script prints the absolute path of the saved CSV so it is easy to locate/download.
