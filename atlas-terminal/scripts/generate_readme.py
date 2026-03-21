#!/usr/bin/env python3
"""Generate README.md for ATLAS Terminal from project metadata.

Scans the project structure and produces a fresh README with:
- Feature list derived from router files
- Tech stack from requirements.txt and package.json
- Changelog from recent git commits

Run manually or via the GitHub Actions workflow (.github/workflows/update-readme.yml).
"""

import json
import subprocess
import textwrap
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_requirements() -> list[str]:
    """Return top-level package names from requirements.txt."""
    req_path = PROJECT_ROOT / "requirements.txt"
    if not req_path.exists():
        return []
    lines = req_path.read_text().splitlines()
    packages = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            name = line.split(">=")[0].split("==")[0].split("[")[0].strip()
            packages.append(name)
    return packages


def _read_package_json_deps() -> list[str]:
    """Return dependency names from apps/web/package.json."""
    pkg_path = PROJECT_ROOT / "apps" / "web" / "package.json"
    if not pkg_path.exists():
        return []
    try:
        data = json.loads(pkg_path.read_text())
        deps = list(data.get("dependencies", {}).keys())
        deps += list(data.get("devDependencies", {}).keys())
        return deps
    except (json.JSONDecodeError, OSError):
        return []


def _detect_routers() -> list[str]:
    """Return router module names from server/routers/."""
    router_dir = PROJECT_ROOT / "server" / "routers"
    if not router_dir.exists():
        return []
    return sorted(
        f.stem
        for f in router_dir.glob("*.py")
        if f.stem != "__init__"
    )


def _recent_commits(n: int = 10) -> list[str]:
    """Return the last *n* one-line commit messages."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--pretty=format:%s"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            return [line for line in result.stdout.splitlines() if line.strip()]
    except FileNotFoundError:
        pass
    return []


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

def generate() -> str:
    routers = _detect_routers()
    py_deps = _read_requirements()
    js_deps = _read_package_json_deps()
    commits = _recent_commits(10)

    feature_bullets = "\n".join(f"- **{r.replace('_', ' ').title()}**" for r in routers)
    py_stack = ", ".join(py_deps[:8]) + (" ..." if len(py_deps) > 8 else "")
    js_stack = ", ".join(js_deps[:8]) + (" ..." if len(js_deps) > 8 else "")
    changelog = "\n".join(f"- {c}" for c in commits) if commits else "- (no commits yet)"
    today = datetime.now().strftime("%Y-%m-%d")

    readme = textwrap.dedent(f"""\
    # ATLAS Terminal

    > Personal Bloomberg-style financial terminal -- real-time market data,
    > AI-powered analysis, DCF valuation, and portfolio management.

    ## Features

    {feature_bullets}

    ## Tech Stack

    **Backend (Python):** {py_stack}

    **Frontend (Next.js):** {js_stack}

    ## Quick Start

    ```bash
    # Backend
    cd atlas-terminal
    pip install -r requirements.txt
    uvicorn server.main:app --reload --port 8000

    # Frontend
    cd apps/web
    npm install && npm run dev
    ```

    ## Recent Changes

    {changelog}

    ---
    *Auto-generated on {today}*
    """)
    return readme


def main():
    readme_path = PROJECT_ROOT / "README.md"
    content = generate()
    readme_path.write_text(content)
    print(f"README.md written ({len(content)} bytes)")


if __name__ == "__main__":
    main()
