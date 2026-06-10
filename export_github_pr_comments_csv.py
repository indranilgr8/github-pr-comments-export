import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple


API_VERSION = "2022-11-28"
READ_ONLY_API_PATH_PATTERN = re.compile(
    r"^/repos/[^/]+/[^/]+/(issues/\d+/comments|pulls/\d+/(comments|reviews))$"
)
READ_ONLY_API_PATH_ALT_PATTERN = re.compile(
    r"^/repositories/\d+/(issues/\d+/comments|pulls/\d+/(comments|reviews))$"
)


def read_token_file(path: str) -> Optional[str]:
    if not path or not os.path.isfile(path):
        return None

    with open(path, "r", encoding="utf-8") as token_file:
        for line in token_file:
            token = line.strip()
            if token:
                return token
    return None


def parse_pr_url(pr_url: str) -> Tuple[str, str, int]:
    pattern = re.compile(r"^https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)(?:/.*)?$")
    match = pattern.match(pr_url.strip())
    if not match:
        raise ValueError("Invalid PR URL. Expected: https://github.com/<owner>/<repo>/pull/<number>")

    owner = match.group(1)
    repo = match.group(2)
    pr_number = int(match.group(3))
    return owner, repo, pr_number


def read_pr_list_file(path: str) -> List[str]:
    urls: List[str] = []
    with open(path, "r", encoding="utf-8") as pr_file:
        for raw_line in pr_file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls


def extract_next_link(link_header: Optional[str]) -> Optional[str]:
    if not link_header:
        return None

    parts = [part.strip() for part in link_header.split(",")]
    for part in parts:
        if 'rel="next"' in part:
            start = part.find("<")
            end = part.find(">")
            if start >= 0 and end > start:
                return part[start + 1 : end]
    return None


def validate_read_only_api_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("Only HTTPS GitHub API URLs are allowed")
    if parsed.netloc.lower() != "api.github.com":
        raise ValueError("Only api.github.com URLs are allowed")
    if not READ_ONLY_API_PATH_PATTERN.match(parsed.path) and not READ_ONLY_API_PATH_ALT_PATTERN.match(parsed.path):
        raise ValueError("Only read-only PR comment/review endpoints are allowed")


def github_get(url: str, token: Optional[str]) -> Tuple[List[Dict], Optional[str]]:
    validate_read_only_api_url(url)
    request = urllib.request.Request(url, method="GET")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", API_VERSION)
    request.add_header("User-Agent", "github-pr-comments-export")
    if token:
        request.add_header("Authorization", "Bearer {0}".format(token))

    try:
        with urllib.request.urlopen(request) as response:
            final_url = response.geturl()
            validate_read_only_api_url(final_url)
            payload = json.loads(response.read().decode("utf-8"))
            next_link = extract_next_link(response.headers.get("Link"))
            if next_link:
                validate_read_only_api_url(next_link)
            if isinstance(payload, list):
                return payload, next_link
            return [payload], next_link
    except urllib.error.HTTPError as ex:
        detail = ex.read().decode("utf-8", errors="replace")
        raise RuntimeError("GitHub API error {0}: {1}".format(ex.code, detail))


def github_get_all_pages(url: str, token: Optional[str]) -> List[Dict]:
    items: List[Dict] = []
    next_url: Optional[str] = url

    while next_url:
        page_items, next_url = github_get(next_url, token)
        items.extend(page_items)

    return items


def to_iso_sort_key(value: Optional[str]) -> Tuple[int, str]:
    if not value:
        return (1, "")

    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return (0, parsed.isoformat())
    except ValueError:
        return (0, value)


def safe_get_user_login(node: Dict) -> str:
    user = node.get("user") or {}
    login = user.get("login")
    return login or ""


def normalize_issue_comment(node: Dict) -> Dict[str, str]:
    return {
        "comment_type": "issue_comment",
        "id": str(node.get("id", "")),
        "created_at": node.get("created_at", "") or "",
        "updated_at": node.get("updated_at", "") or "",
        "author": safe_get_user_login(node),
        "review_state": "",
        "body": (node.get("body") or "").replace("\r\n", "\n").replace("\r", "\n"),
        "path": "",
        "line": "",
        "start_line": "",
        "side": "",
        "commit_id": "",
        "in_reply_to_id": "",
        "url": node.get("html_url", "") or "",
    }


def normalize_review_comment(node: Dict) -> Dict[str, str]:
    return {
        "comment_type": "review_comment",
        "id": str(node.get("id", "")),
        "created_at": node.get("created_at", "") or "",
        "updated_at": node.get("updated_at", "") or "",
        "author": safe_get_user_login(node),
        "review_state": "",
        "body": (node.get("body") or "").replace("\r\n", "\n").replace("\r", "\n"),
        "path": node.get("path", "") or "",
        "line": str(node.get("line", "") or ""),
        "start_line": str(node.get("start_line", "") or ""),
        "side": node.get("side", "") or "",
        "commit_id": node.get("commit_id", "") or "",
        "in_reply_to_id": str(node.get("in_reply_to_id", "") or ""),
        "url": node.get("html_url", "") or "",
    }


def normalize_review_event(node: Dict) -> Dict[str, str]:
    return {
        "comment_type": "review_event",
        "id": str(node.get("id", "")),
        "created_at": node.get("submitted_at", "") or node.get("created_at", "") or "",
        "updated_at": node.get("submitted_at", "") or node.get("updated_at", "") or "",
        "author": safe_get_user_login(node),
        "review_state": node.get("state", "") or "",
        "body": (node.get("body") or "").replace("\r\n", "\n").replace("\r", "\n"),
        "path": "",
        "line": "",
        "start_line": "",
        "side": "",
        "commit_id": node.get("commit_id", "") or "",
        "in_reply_to_id": "",
        "url": node.get("html_url", "") or "",
    }


def fetch_all_comment_data(owner: str, repo: str, pr_number: int, token: Optional[str]) -> List[Dict[str, str]]:
    base = "https://api.github.com/repos/{0}/{1}".format(owner, repo)

    issue_comments_url = "{0}/issues/{1}/comments?per_page=100".format(base, pr_number)
    review_comments_url = "{0}/pulls/{1}/comments?per_page=100".format(base, pr_number)
    reviews_url = "{0}/pulls/{1}/reviews?per_page=100".format(base, pr_number)

    issue_comments = github_get_all_pages(issue_comments_url, token)
    review_comments = github_get_all_pages(review_comments_url, token)
    reviews = github_get_all_pages(reviews_url, token)

    rows: List[Dict[str, str]] = []
    rows.extend(normalize_issue_comment(item) for item in issue_comments)
    rows.extend(normalize_review_comment(item) for item in review_comments)
    rows.extend(normalize_review_event(item) for item in reviews)

    rows.sort(key=lambda row: to_iso_sort_key(row.get("created_at")))
    return rows


def add_pr_metadata(rows: List[Dict[str, str]], owner: str, repo: str, pr_number: int) -> List[Dict[str, str]]:
    pr_url = "https://github.com/{0}/{1}/pull/{2}".format(owner, repo, pr_number)
    for row in rows:
        row["pr_owner"] = owner
        row["pr_repo"] = repo
        row["pr_number"] = str(pr_number)
        row["pr_url"] = pr_url
    return rows


def normalize_output_csv_path(output_csv: str) -> str:
    path = (output_csv or "").strip()
    if not path:
        path = "pr_comments.csv"
    if not path.lower().endswith(".csv"):
        path = "{0}.csv".format(path)

    absolute_path = os.path.abspath(path)
    parent_dir = os.path.dirname(absolute_path)
    if parent_dir and not os.path.isdir(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    return absolute_path


def write_csv(rows: List[Dict[str, str]], output_csv: str) -> None:
    fieldnames = [
        "pr_owner",
        "pr_repo",
        "pr_number",
        "pr_url",
        "comment_type",
        "id",
        "created_at",
        "updated_at",
        "author",
        "review_state",
        "body",
        "path",
        "line",
        "start_line",
        "side",
        "commit_id",
        "in_reply_to_id",
        "url",
    ]

    with open(output_csv, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export all GitHub PR comments and reviews to one CSV file.")
    parser.add_argument("--pr-url", default=None, help="PR URL, for example https://github.com/org/repo/pull/123")
    parser.add_argument(
        "--pr-list-file",
        default=None,
        help="Path to input file containing one PR URL per line. Blank lines and lines starting with # are ignored.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="GitHub token. Optional if repo is public.",
    )
    parser.add_argument(
        "--token-file",
        default=".github_token",
        help="Optional token file path. Uses first non-empty line. Default: .github_token",
    )
    parser.add_argument(
        "--output-csv",
        default="pr_comments.csv",
        help="Output CSV path. Default: pr_comments.csv",
    )

    args = parser.parse_args()

    if not args.pr_url and not args.pr_list_file:
        print("Error: provide either --pr-url or --pr-list-file", file=sys.stderr)
        return 1
    if args.pr_url and args.pr_list_file:
        print("Error: use only one of --pr-url or --pr-list-file", file=sys.stderr)
        return 1

    token = args.token or os.getenv("GITHUB_TOKEN")
    if not token:
        token = read_token_file(args.token_file)

    output_csv_path = normalize_output_csv_path(args.output_csv)

    try:
        pr_urls: List[str]
        if args.pr_list_file:
            pr_urls = read_pr_list_file(args.pr_list_file)
            if not pr_urls:
                raise ValueError("PR list file is empty or has no valid URLs")
        else:
            pr_urls = [args.pr_url]

        rows: List[Dict[str, str]] = []
        for pr_url in pr_urls:
            owner, repo, pr_number = parse_pr_url(pr_url)
            pr_rows = fetch_all_comment_data(owner, repo, pr_number, token)
            rows.extend(add_pr_metadata(pr_rows, owner, repo, pr_number))

        rows.sort(key=lambda row: to_iso_sort_key(row.get("created_at")))
        write_csv(rows, output_csv_path)
    except Exception as ex:
        print("Error: {0}".format(ex), file=sys.stderr)
        return 1

    print("Saved CSV: {0}".format(output_csv_path))
    print("Total rows: {0}".format(len(rows)))
    print("Total PRs processed: {0}".format(len(pr_urls)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
