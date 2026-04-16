"""Persistent and in-session memory storage."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from src.models.schemas import MemoryComparison, MemoryRecord
from src.utils.helpers import load_json_file, save_json_file


class MemoryStore:
    def __init__(self, store_path: str = "data/memory_store.json") -> None:
        self.store_path = Path(store_path)
        self._session_cache: Dict[str, Any] = {}
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        default = {"analyses": {}, "preferences": {}}
        payload = load_json_file(self.store_path, default=default)
        payload.setdefault("analyses", {})
        payload.setdefault("preferences", {})
        return payload

    def _save(self) -> None:
        save_json_file(self.store_path, self._data)

    def store_analysis_memory(self, record: MemoryRecord) -> None:
        self._data["analyses"][record.repo_key] = record.model_dump()
        self._session_cache[record.repo_key] = record.model_dump()
        self._save()

    def retrieve_analysis_memory(self, repo_key: str) -> Optional[Dict[str, Any]]:
        if repo_key in self._session_cache:
            return self._session_cache[repo_key]
        return self._data["analyses"].get(repo_key)

    def save_preferences(self, user_key: str, preferences: Dict[str, Any]) -> None:
        self._data["preferences"][user_key] = preferences
        self._session_cache[f"pref::{user_key}"] = preferences
        self._save()

    def get_preferences(self, user_key: str) -> Dict[str, Any]:
        return self._session_cache.get(
            f"pref::{user_key}",
            self._data["preferences"].get(user_key, {}),
        )

    def compare_with_previous(self, record: MemoryRecord) -> MemoryComparison:
        previous = self.retrieve_analysis_memory(record.repo_key)
        if not previous:
            return MemoryComparison(repo_key=record.repo_key, previous_exists=False)

        previous_risks = set(previous.get("risks", []))
        current_risks = set(record.risks)
        new_risks = sorted(current_risks - previous_risks)
        resolved_risks = sorted(previous_risks - current_risks)

        previous_risk_count = int(previous.get("risk_count", len(previous_risks)))
        previous_module_count = int(previous.get("module_count", 0))
        previous_dependency_count = int(previous.get("dependency_count", 0))
        previous_stack_signature = previous.get(
            "stack_signature",
            "|".join(sorted([s.lower() for s in previous.get("tech_stack", [])])),
        )
        previous_patterns = set(previous.get("architecture_patterns", []))
        current_patterns = set(record.architecture_patterns)

        risk_delta = record.risk_count - previous_risk_count
        module_delta = record.module_count - previous_module_count
        dependency_delta = record.dependency_count - previous_dependency_count
        stack_changed = previous_stack_signature != record.stack_signature
        pattern_changes = {
            "added": sorted(current_patterns - previous_patterns),
            "removed": sorted(previous_patterns - current_patterns),
        }

        score = 50
        score += 10 * len(resolved_risks)
        score -= 12 * len(new_risks)
        if risk_delta < 0:
            score += 8
        elif risk_delta > 0:
            score -= 8
        if not stack_changed:
            score += 2
        if module_delta < 0:
            score -= 3
        if dependency_delta < 0:
            score -= 2
        score = max(0, min(100, score))

        if score >= 65:
            drift_status = "improved"
        elif score < 45:
            drift_status = "regressed"
        else:
            drift_status = "stable"

        return MemoryComparison(
            repo_key=record.repo_key,
            previous_exists=True,
            previous_analyzed_at=previous.get("analyzed_at"),
            new_risks=new_risks,
            resolved_risks=resolved_risks,
            focus_changed=previous.get("focus") != record.focus,
            risk_delta=risk_delta,
            module_delta=module_delta,
            dependency_delta=dependency_delta,
            stack_changed=stack_changed,
            pattern_changes=pattern_changes,
            drift_status=drift_status,  # type: ignore[arg-type]
            improvement_score=score,
        )
