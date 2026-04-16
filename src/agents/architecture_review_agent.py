"""Architecture Review Agent."""

from __future__ import annotations

import json
import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.models.schemas import ArchitectureReviewResult, RepoAnalysisResult


class ArchitectureReviewAgent:
    """Converts repository analysis findings into review recommendations."""

    def __init__(self, llm: BaseChatModel) -> None:
        self.llm = llm

    def _extract_json_object(self, text: str) -> dict | None:
        """Extract a valid JSON object from noisy model output."""
        raw = text.strip()

        # Direct parse first.
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # Parse markdown fenced JSON block.
        fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if fenced_match:
            candidate = fenced_match.group(1)
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        # Parse first object-like slice.
        first_brace = raw.find("{")
        last_brace = raw.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = raw[first_brace : last_brace + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        return None

    def _clean_lines(self, text: str) -> list[str]:
        """Filter noisy fallback lines to human-readable observations."""
        bad_tokens = {"undefined", "{", "}", "[", "]", "null"}
        cleaned: list[str] = []
        for line in text.splitlines():
            item = line.strip().strip(",")
            if not item:
                continue
            if item.lower() in bad_tokens:
                continue
            if item.startswith('"') and item.endswith('":'):
                continue
            if item.startswith('"') and item.endswith('['):
                continue
            if ":" in item and item.strip().startswith('"'):
                continue
            item = item.strip('"').strip()
            if len(item) < 4:
                continue
            cleaned.append(item)
        return cleaned

    def run(self, analysis: RepoAnalysisResult) -> ArchitectureReviewResult:
        prompt = f"""
You are Architecture Review Agent.
Create a practical architecture review for repository {analysis.repo.full_name}.

Inputs:
- Focus: {analysis.focus}
- Detected stack: {analysis.tech_stack}
- Modules: {analysis.structure.modules}
- Entry points: {analysis.structure.entry_points}
- Architectural patterns: {analysis.architectural_patterns}
- Initial risks: {analysis.risks}

Return a JSON object with keys:
project_overview (string),
architecture_observations (array of strings),
risks_and_antipatterns (array of strings),
recommendations (array of strings),
next_steps (array of strings).
Be concise and actionable.
"""
        response = self.llm.invoke(
            [
                SystemMessage(content="You are a senior software architect."),
                HumanMessage(content=prompt),
            ]
        )
        text = str(response.content).strip()

        # Resilient parse for non-strict JSON model output.
        try:
            data = self._extract_json_object(text)
            if data is None:
                raise ValueError("No valid JSON object found in model output.")
            return ArchitectureReviewResult(**data)
        except Exception:
            lines = self._clean_lines(text)
            return ArchitectureReviewResult(
                project_overview=f"{analysis.repo.full_name} appears to use {', '.join(analysis.tech_stack[:4])}.",
                architecture_observations=lines[:5] or analysis.architectural_patterns[:5],
                risks_and_antipatterns=analysis.risks[:8],
                recommendations=[
                    "Establish explicit module ownership and boundaries.",
                    "Add or strengthen CI checks for lint/test/security.",
                    "Prioritize dependency and configuration hygiene.",
                ],
                next_steps=[
                    "Review top 3 risks with the team and assign owners.",
                    "Create a follow-up architecture review after remediation.",
                ],
            )
