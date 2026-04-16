"""GitHub related LangChain tools."""

from __future__ import annotations

from typing import Dict, List

from langchain_core.tools import tool

from src.services.github_service import GitHubService


def fetch_repo_metadata(github_service: GitHubService, owner: str, repo: str) -> Dict:
    return github_service.fetch_repo_metadata(owner=owner, repo=repo).model_dump()


def list_repo_files(
    github_service: GitHubService,
    owner: str,
    repo: str,
    branch: str,
    max_files: int = 300,
    max_file_bytes: int = 120000,
) -> List[Dict]:
    files = github_service.list_repo_files(
        owner=owner,
        repo=repo,
        branch=branch,
        max_files=max_files,
        max_file_bytes=max_file_bytes,
    )
    return [item.model_dump() for item in files]


def read_repo_file(github_service: GitHubService, owner: str, repo: str, path: str, branch: str) -> str:
    return github_service.read_repo_file(owner=owner, repo=repo, path=path, branch=branch)


def build_github_tools(github_service: GitHubService):
    @tool
    def fetch_repo_metadata_tool(owner: str, repo: str) -> Dict:
        """Fetch high-level metadata about a GitHub repository."""
        return fetch_repo_metadata(github_service, owner=owner, repo=repo)

    @tool
    def list_repo_files_tool(
        owner: str,
        repo: str,
        branch: str,
        max_files: int = 300,
        max_file_bytes: int = 120000,
    ) -> List[Dict]:
        """List repository files with optional filtering limits."""
        return list_repo_files(
            github_service=github_service,
            owner=owner,
            repo=repo,
            branch=branch,
            max_files=max_files,
            max_file_bytes=max_file_bytes,
        )

    @tool
    def read_repo_file_tool(owner: str, repo: str, path: str, branch: str) -> str:
        """Read a text file from a GitHub repository."""
        return read_repo_file(github_service=github_service, owner=owner, repo=repo, path=path, branch=branch)

    return [fetch_repo_metadata_tool, list_repo_files_tool, read_repo_file_tool]
