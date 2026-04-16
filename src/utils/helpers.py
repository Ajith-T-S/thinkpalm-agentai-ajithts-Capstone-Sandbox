"""General helper utilities."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


TEXT_FILE_EXTENSIONS: Set[str] = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".kt",
    ".go",
    ".rb",
    ".php",
    ".cs",
    ".rs",
    ".scala",
    ".swift",
    ".m",
    ".mm",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".md",
    ".txt",
    ".xml",
    ".gradle",
    ".sh",
    ".ps1",
    ".sql",
    ".dockerfile",
}


BINARY_FILE_EXTENSIONS: Set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".7z",
    ".jar",
    ".war",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".mp4",
    ".mp3",
    ".wav",
    ".ttf",
    ".woff",
    ".woff2",
    ".class",
}


PRIORITY_FILES = (
    "README.md",
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    "tsconfig.json",
    "angular.json",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".github/workflows",
)


def parse_github_input(value: str) -> Tuple[str, str]:
    """Parse owner/repo from URL or shorthand."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("GitHub repository input cannot be empty.")

    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        match = re.search(r"github\.com/([^/\s]+)/([^/\s#]+)", cleaned)
        if not match:
            raise ValueError("Could not parse owner/repo from GitHub URL.")
        owner = match.group(1)
        repo = match.group(2).replace(".git", "")
        return owner, repo

    if "/" not in cleaned:
        raise ValueError("Use owner/repo format, e.g. langchain-ai/langchain.")

    owner, repo = cleaned.split("/", 1)
    repo = repo.replace(".git", "")
    return owner.strip(), repo.strip()


def should_skip_file(path: str, size: int, max_file_bytes: int) -> bool:
    lower_path = path.lower()
    suffix = Path(path).suffix.lower()

    if size > max_file_bytes:
        return True
    if any(part in {"node_modules", ".git", "dist", "build", "target", "bin"} for part in Path(path).parts):
        return True
    if suffix in BINARY_FILE_EXTENSIONS:
        return True
    if suffix and suffix not in TEXT_FILE_EXTENSIONS and "/" in lower_path and size > 80000:
        return True
    return False


def prioritize_paths(paths: Iterable[str], limit: int) -> List[str]:
    path_list = list(paths)
    prioritized: List[str] = []

    for key in PRIORITY_FILES:
        for path in path_list:
            if path.endswith(key) or key in path:
                prioritized.append(path)

    leftovers = [p for p in path_list if p not in prioritized]
    ordered = prioritized + sorted(leftovers)
    return ordered[:limit]


def load_json_file(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return default
    except (json.JSONDecodeError, OSError):
        return default


def save_json_file(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=True)


def list_top_level_modules(file_paths: Iterable[str], max_items: int = 20) -> List[str]:
    top = {p.split("/", 1)[0] for p in file_paths if "/" in p}
    if not top:
        top = {p for p in file_paths}
    return sorted(top)[:max_items]
