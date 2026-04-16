"""Memory tool wrappers."""

from __future__ import annotations

from typing import Dict

from langchain_core.tools import tool

from src.memory.memory_store import MemoryStore
from src.models.schemas import MemoryRecord


def build_memory_tools(memory_store: MemoryStore):
    @tool
    def store_analysis_memory(
        repo_key: str,
        summary: str,
        tech_stack: list[str],
        risks: list[str],
        recommendations: list[str],
        focus: str = "general",
        report_depth: str = "standard",
        risk_count: int = 0,
        module_count: int = 0,
        dependency_count: int = 0,
        stack_signature: str = "",
        architecture_patterns: list[str] | None = None,
        entry_points_count: int = 0,
        config_files_count: int = 0,
    ) -> str:
        """Store analysis output in persistent memory."""
        record = MemoryRecord(
            repo_key=repo_key,
            summary=summary,
            tech_stack=tech_stack,
            risks=risks,
            recommendations=recommendations,
            focus=focus,  # type: ignore[arg-type]
            report_depth=report_depth,  # type: ignore[arg-type]
            risk_count=risk_count,
            module_count=module_count,
            dependency_count=dependency_count,
            stack_signature=stack_signature,
            architecture_patterns=architecture_patterns or [],
            entry_points_count=entry_points_count,
            config_files_count=config_files_count,
        )
        memory_store.store_analysis_memory(record)
        return f"Stored memory for {repo_key}"

    @tool
    def retrieve_analysis_memory(repo_key: str) -> Dict:
        """Retrieve the latest stored analysis for a repository."""
        return memory_store.retrieve_analysis_memory(repo_key) or {}

    return [store_analysis_memory, retrieve_analysis_memory]


def save_user_preferences(memory_store: MemoryStore, user_key: str, preferences: Dict) -> None:
    memory_store.save_preferences(user_key=user_key, preferences=preferences)


def load_user_preferences(memory_store: MemoryStore, user_key: str) -> Dict:
    return memory_store.get_preferences(user_key=user_key)


def compare_with_previous(
    memory_store: MemoryStore,
    repo_key: str,
    summary: str,
    tech_stack: list[str],
    risks: list[str],
    recommendations: list[str],
    focus: str,
    report_depth: str,
    risk_count: int = 0,
    module_count: int = 0,
    dependency_count: int = 0,
    stack_signature: str = "",
    architecture_patterns: list[str] | None = None,
    entry_points_count: int = 0,
    config_files_count: int = 0,
) -> Dict:
    record = MemoryRecord(
        repo_key=repo_key,
        summary=summary,
        tech_stack=tech_stack,
        risks=risks,
        recommendations=recommendations,
        focus=focus,  # type: ignore[arg-type]
        report_depth=report_depth,  # type: ignore[arg-type]
        risk_count=risk_count,
        module_count=module_count,
        dependency_count=dependency_count,
        stack_signature=stack_signature,
        architecture_patterns=architecture_patterns or [],
        entry_points_count=entry_points_count,
        config_files_count=config_files_count,
    )
    return memory_store.compare_with_previous(record).model_dump()
