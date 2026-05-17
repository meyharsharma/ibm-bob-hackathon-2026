"""Flask web server for The Time Machine — GitHub profile mode only."""

import hashlib
import math
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "time-machine-hackathon",
}
if GITHUB_TOKEN:
    GITHUB_HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

PROFILE_CACHE: Dict[str, Dict[str, Any]] = {}

LANG_COLORS = {
    "Python": [0.31, 0.55, 0.85],
    "JavaScript": [0.94, 0.86, 0.30],
    "TypeScript": [0.18, 0.46, 0.84],
    "Go": [0.0, 0.68, 0.85],
    "Rust": [0.85, 0.35, 0.20],
    "Java": [0.72, 0.35, 0.13],
    "C": [0.34, 0.40, 0.55],
    "C++": [0.93, 0.27, 0.42],
    "C#": [0.30, 0.55, 0.30],
    "Ruby": [0.85, 0.20, 0.20],
    "PHP": [0.30, 0.36, 0.62],
    "Swift": [0.96, 0.51, 0.20],
    "Kotlin": [0.69, 0.41, 0.86],
    "Shell": [0.55, 0.85, 0.42],
    "HTML": [0.91, 0.39, 0.23],
    "CSS": [0.36, 0.50, 0.86],
    "Vue": [0.25, 0.72, 0.51],
    "Dart": [0.0, 0.70, 0.84],
    "Scala": [0.79, 0.16, 0.16],
    "Lua": [0.0, 0.0, 0.50],
    "Haskell": [0.36, 0.36, 0.65],
    "Elixir": [0.42, 0.30, 0.55],
    "Solidity": [0.30, 0.30, 0.30],
}
DEFAULT_LANG_COLOR = [0.65, 0.65, 0.72]


def _gh_get(url: str, params: dict = None, token: str = None) -> requests.Response:
    headers = dict(GITHUB_HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.get(url, headers=headers, params=params, timeout=20)


def _rate_remaining(token: str = None) -> Dict[str, Any]:
    try:
        r = _gh_get("https://api.github.com/rate_limit", token=token)
        if r.status_code == 200:
            return r.json().get("rate", {})
    except Exception:
        pass
    return {}


def _commits_head(owner: str, repo: str, default_branch: str, token: str = None):
    """Single call returns last commit details + count (via Link header)."""
    r = _gh_get(
        f"https://api.github.com/repos/{owner}/{repo}/commits",
        params={"per_page": 1, "sha": default_branch} if default_branch else {"per_page": 1},
        token=token,
    )
    if r.status_code != 200:
        return 0, {}
    link = r.headers.get("Link", "")
    m = re.search(r'page=(\d+)>;\s*rel="last"', link)
    count = int(m.group(1)) if m else (1 if r.json() else 0)
    last = {}
    try:
        arr = r.json()
        if arr:
            c = arr[0]
            last = {
                "sha": c["sha"][:10],
                "message": (c["commit"]["message"] or "").split("\n")[0][:160],
                "author": c["commit"]["author"]["name"],
                "date": c["commit"]["author"]["date"],
            }
    except Exception:
        pass
    return count, last


def _commit_activity(owner: str, repo: str, token: str = None) -> List[Dict[str, Any]]:
    """GitHub /stats/commit_activity returns 52 weeks. Retry with backoff on 202."""
    url = f"https://api.github.com/repos/{owner}/{repo}/stats/commit_activity"
    delays = [0.5, 1.5, 3.0]
    for d in delays:
        r = _gh_get(url, token=token)
        if r.status_code == 200:
            try:
                data = r.json()
                if isinstance(data, list):
                    return data
                return []
            except Exception:
                return []
        if r.status_code == 202:
            time.sleep(d)
            continue
        return []
    return []


def _months_window(n: int = 12) -> List[str]:
    """Return last n months as 'YYYY-MM' inclusive of current month."""
    today = datetime.now(timezone.utc).replace(day=1)
    months = []
    y, m = today.year, today.month
    for _ in range(n):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


def _aggregate_monthly(activity: List[Dict[str, Any]], months: List[str]) -> Dict[str, int]:
    """Bucket weekly activity into months. activity entry: {week: ts, total: int, days: [..]}."""
    by_month = defaultdict(int)
    for w in activity:
        ts = w.get("week")
        total = w.get("total", 0)
        if ts is None:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        key = f"{dt.year:04d}-{dt.month:02d}"
        by_month[key] += int(total)
    return {m: by_month.get(m, 0) for m in months}


def _summarize(repo: dict, last_commit: dict) -> List[str]:
    lines = []
    desc = (repo.get("description") or "").strip()
    if desc:
        lines.append(desc)
    else:
        lines.append(f"{repo['name']} — {repo.get('language') or 'unknown stack'} project.")
    lang = repo.get("language") or "mixed sources"
    lines.append(f"Primary language: {lang}. Default branch: {repo.get('default_branch', 'main')}.")
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    issues = repo.get("open_issues_count", 0)
    lines.append(f"{stars}★ · {forks} forks · {issues} open issues.")
    if last_commit.get("date"):
        lines.append(f"Last commit {last_commit['date'][:10]} by {last_commit.get('author','unknown')}: \"{last_commit.get('message','')[:80]}\"")
    if repo.get("archived"):
        lines.append("Archived — read-only.")
    elif repo.get("fork"):
        lines.append("Fork of upstream repository.")
    else:
        created = (repo.get("created_at") or "")[:10]
        if created:
            lines.append(f"Active since {created}.")
    return lines[:5]


def _layout_grid(n: int, spacing: float = 18.0):
    cols = max(1, int(math.ceil(math.sqrt(n))))
    positions = []
    for i in range(n):
        r = i // cols
        c = i % cols
        x = (c - (cols - 1) / 2.0) * spacing
        z = (r - (cols - 1) / 2.0) * spacing
        positions.append((x, z))
    return positions, cols


def _build_profile_city(username: str, token: str = None, max_repos: int = 50) -> Dict[str, Any]:
    r = _gh_get(
        f"https://api.github.com/users/{username}/repos",
        params={"per_page": 100, "sort": "updated", "type": "owner"},
        token=token,
    )
    if r.status_code == 404:
        raise RuntimeError(f"GitHub user not found: {username}")
    if r.status_code == 403:
        raise RuntimeError("GitHub rate limit exceeded. Set GITHUB_TOKEN.")
    if r.status_code != 200:
        raise RuntimeError(f"GitHub API error {r.status_code}: {r.text[:200]}")
    repos = r.json()
    if not repos:
        raise RuntimeError(f"User {username} has no public repos")

    # cap to keep within rate limit (each repo costs 2 API calls)
    repos = repos[:max_repos]

    user_r = _gh_get(f"https://api.github.com/users/{username}", token=token)
    user_info = user_r.json() if user_r.status_code == 200 else {}

    months = _months_window(12)
    positions, _ = _layout_grid(len(repos))

    # per-month totals across whole profile
    profile_monthly = {m: 0 for m in months}

    enriched = []
    for repo in repos:
        owner = repo["owner"]["login"]
        name = repo["name"]
        branch = repo.get("default_branch") or "main"
        commits, last = _commits_head(owner, name, branch, token=token)
        activity = _commit_activity(owner, name, token=token)
        monthly = _aggregate_monthly(activity, months)
        for m, v in monthly.items():
            profile_monthly[m] += v
        # cumulative within window
        running = 0
        cumulative = {}
        for m in months:
            running += monthly[m]
            cumulative[m] = running
        enriched.append({
            "repo": repo, "commits": commits, "last": last,
            "monthly": monthly, "cumulative": cumulative,
        })

    buildings = []
    for i, item in enumerate(enriched):
        repo = item["repo"]
        commits = item["commits"]
        last = item["last"]
        x, z = positions[i]
        if commits <= 0:
            final_h = 2.0
        else:
            final_h = 2.0 + math.log(commits + 1) * 5.0
            final_h = min(final_h, 50.0)
        stars = repo.get("stargazers_count", 0)
        base = 4.0 + math.log(stars + 1) * 0.6
        base = min(base, 8.0)
        lang = repo.get("language") or ""
        color = LANG_COLORS.get(lang, DEFAULT_LANG_COLOR)
        if repo.get("archived"):
            color = [0.55, 0.55, 0.60]
        roof = "antenna" if final_h > 18 else ("pitched" if final_h < 5 else "flat")
        summary = _summarize(repo, last)

        # per-month height series (log-scaled cumulative within window)
        height_by_month = {}
        max_cum_window = max(item["cumulative"].values()) if item["cumulative"] else 0
        for m in months:
            cum = item["cumulative"][m]
            if cum <= 0:
                hm = 0.6
            else:
                hm = 0.6 + math.log(cum + 1) * 4.5
                hm = min(hm, 50.0)
            height_by_month[m] = hm

        buildings.append({
            "id": repo["full_name"],
            "name": repo["name"],
            "full_name": repo["full_name"],
            "neighborhood": lang or "other",
            "x": float(x),
            "z": float(z),
            "y": final_h / 2.0,
            "width": float(base),
            "depth": float(base),
            "height": float(final_h),
            "color": color,
            "roof": roof,
            "lines_of_code": 0,
            "modifications": commits,
            "windows_seed": int(hashlib.md5(repo["full_name"].encode()).hexdigest()[:8], 16) % 100000,
            "monthly_commits": item["monthly"],
            "height_by_month": height_by_month,
            "repo": {
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description") or "",
                "language": lang,
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "open_issues": repo.get("open_issues_count", 0),
                "default_branch": repo.get("default_branch"),
                "url": repo.get("html_url"),
                "created_at": repo.get("created_at"),
                "updated_at": repo.get("updated_at"),
                "pushed_at": repo.get("pushed_at"),
                "topics": repo.get("topics", []),
                "archived": repo.get("archived", False),
                "fork": repo.get("fork", False),
                "commit_count": commits,
                "last_commit": last,
                "summary": summary,
            },
        })

    roads = []
    if buildings:
        xs = sorted({round(b["x"], 1) for b in buildings})
        zs = sorted({round(b["z"], 1) for b in buildings})
        span = max(20.0, (max(xs) - min(xs)) + 24.0)
        spanz = max(20.0, (max(zs) - min(zs)) + 24.0)
        for i in range(len(xs) - 1):
            roads.append({"x": (xs[i] + xs[i + 1]) / 2.0, "z": 0, "width": 4.0, "depth": spanz})
        for i in range(len(zs) - 1):
            roads.append({"x": 0, "z": (zs[i] + zs[i + 1]) / 2.0, "width": span, "depth": 4.0})
        roads.append({"x": min(xs) - 9, "z": 0, "width": 4.0, "depth": spanz})
        roads.append({"x": max(xs) + 9, "z": 0, "width": 4.0, "depth": spanz})
        roads.append({"x": 0, "z": min(zs) - 9, "width": span, "depth": 4.0})
        roads.append({"x": 0, "z": max(zs) + 9, "width": span, "depth": 4.0})

    return {
        "name": f"{username} · GitHub",
        "mode": "profile",
        "user": {
            "login": username,
            "name": user_info.get("name") or username,
            "bio": user_info.get("bio") or "",
            "avatar_url": user_info.get("avatar_url"),
            "html_url": user_info.get("html_url"),
            "public_repos": user_info.get("public_repos"),
            "followers": user_info.get("followers"),
            "following": user_info.get("following"),
        },
        "months": months,
        "profile_monthly": profile_monthly,
        "buildings": buildings,
        "roads": roads,
        "stats": {
            "total_repos": len(buildings),
            "total_neighborhoods": len({b["neighborhood"] for b in buildings}),
            "total_commits": sum(b["modifications"] for b in buildings),
            "window_commits": sum(profile_monthly.values()),
            "source": "profile",
        },
    }


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "time-machine"})

    @app.get("/api/city")
    def city():
        user = (request.args.get("user") or "").strip().lstrip("@")
        if not user:
            return jsonify({"error": "missing user param"}), 400
        if user not in PROFILE_CACHE:
            return jsonify({"error": f"profile not loaded — POST /api/profile first"}), 404
        return jsonify(PROFILE_CACHE[user])

    @app.post("/api/profile")
    def profile():
        data = request.get_json(force=True, silent=True) or {}
        username = (data.get("user") or "").strip().lstrip("@")
        token = (data.get("token") or GITHUB_TOKEN or "").strip() or None
        if not username:
            return jsonify({"error": "missing user"}), 400
        # rate-limit pre-check
        rate = _rate_remaining(token)
        if rate and rate.get("remaining", 0) < 5:
            reset = rate.get("reset", 0)
            return jsonify({"error": f"GitHub rate limit nearly exhausted ({rate['remaining']}/{rate['limit']}). Resets in {max(0, reset - int(time.time()))}s. Provide a token to bypass."}), 429
        try:
            city = _build_profile_city(username, token=token)
            PROFILE_CACHE[username] = city
            return jsonify({
                "ok": True,
                "user": username,
                "repos": len(city["buildings"]),
                "total_commits": city["stats"]["total_commits"],
                "window_commits": city["stats"]["window_commits"],
                "months": city["months"],
                "rate_limit": _rate_remaining(token),
            })
        except Exception as e:
            return jsonify({"error": str(e), "rate_limit": _rate_remaining(token)}), 500

    @app.get("/api/rate-limit")
    def rate_limit():
        token = request.args.get("token", "").strip() or GITHUB_TOKEN
        return jsonify(_rate_remaining(token))

    @app.get("/api/profiles")
    def profiles():
        return jsonify(sorted(PROFILE_CACHE.keys()))

    return app


def main():
    app = create_app()
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)


if __name__ == "__main__":
    main()
