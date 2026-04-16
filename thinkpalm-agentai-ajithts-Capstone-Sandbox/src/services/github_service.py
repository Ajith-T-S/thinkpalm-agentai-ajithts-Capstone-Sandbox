"""GitHub REST API service wrappers."""

from __future__ import annotations

import base64
from typing import Dict, List, Optional

import requests

from src.models.schemas import RepoFileInfo, RepoMetadata
from src.utils.helpers import should_skip_file


class GitHubServiceError(Exception):
    """Raised for GitHub API related failures."""


class GitHubService:
    def __init__(self, token: Optional[str] = None, timeout_seconds: int = 20) -> None:
        self.base_url = "https://api.github.com"
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "User-Agent": "ai-architecture-review-assistant",
            }
        )
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _request(self, endpoint: str) -> Dict:
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, timeout=self.timeout_seconds)
        if response.status_code == 404:
            raise GitHubServiceError("Repository or resource not found.")
        if response.status_code == 401:
            raise GitHubServiceError("Unauthorized. Check GitHub token.")
        if response.status_code == 403:
            message = response.json().get("message", "Forbidden or rate-limited request.")
            raise GitHubServiceError(f"GitHub access denied: {message}")
        if response.status_code >= 400:
            raise GitHubServiceError(f"GitHub API error ({response.status_code}).")
        return response.json()

    def fetch_repo_metadata(self, owner: str, repo: str) -> RepoMetadata:
        payload = self._request(f"/repos/{owner}/{repo}")
        return RepoMetadata(
            name=payload["name"],
            full_name=payload["full_name"],
            description=payload.get("description"),
            default_branch=payload.get("default_branch", "main"),
            stars=payload.get("stargazers_count", 0),
            forks=payload.get("forks_count", 0),
            open_issues=payload.get("open_issues_count", 0),
            language=payload.get("language"),
            topics=payload.get("topics", []),
            private=payload.get("private", False),
            archived=payload.get("archived", False),
            pushed_at=payload.get("pushed_at"),
            html_url=payload["html_url"],
        )

    def list_repo_files(
        self,
        owner: str,
        repo: str,
        branch: str,
        max_files: int = 300,
        max_file_bytes: int = 120000,
    ) -> List[RepoFileInfo]:
        tree_data = self._request(f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
        entries = tree_data.get("tree", [])
        file_infos: List[RepoFileInfo] = []

        for item in entries:
            if item.get("type") != "blob":
                continue
            path = item.get("path", "")
            size = item.get("size", 0)
            if should_skip_file(path, size, max_file_bytes=max_file_bytes):
                continue
            file_infos.append(
                RepoFileInfo(
                    path=path,
                    type="blob",
                    size=size,
                    sha=item.get("sha"),
                )
            )
            if len(file_infos) >= max_files:
                break

        return file_infos

    def read_repo_file(self, owner: str, repo: str, path: str, branch: str) -> str:
        payload = self._request(f"/repos/{owner}/{repo}/contents/{path}?ref={branch}")
        content = payload.get("content")
        encoding = payload.get("encoding")
        if not content or encoding != "base64":
            return ""

        try:
            decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
        except ValueError as exc:
            raise GitHubServiceError(f"Could not decode file {path}.") from exc
        return decoded
