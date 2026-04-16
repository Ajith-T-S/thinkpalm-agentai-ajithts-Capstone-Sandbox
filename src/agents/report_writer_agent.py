"""Report Writer Agent."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.models.schemas import ArchitectureReviewResult, RepoAnalysisResult


class ReportWriterAgent:
    """Formats final architecture findings into polished markdown."""

    def __init__(self, llm: BaseChatModel) -> None:
        self.llm = llm

    def run(self, analysis: RepoAnalysisResult, review: ArchitectureReviewResult) -> str:
        prompt = f"""
Write a markdown architecture report for {analysis.repo.full_name}.
Sections required:
1. Project Overview
2. Detected Stack
3. Module Breakdown
4. Architecture Observations
5. Risks / Anti-patterns
6. Recommendations
7. Suggested Next Steps
8. Raw Evidence (top evidence items only)

Use concise bullets and clear section headings.

Data:
- Overview: {review.project_overview}
- Stack: {analysis.tech_stack}
- Modules: {analysis.structure.modules}
- Observations: {review.architecture_observations}
- Risks: {review.risks_and_antipatterns}
- Recommendations: {review.recommendations}
- Next steps: {review.next_steps}
- Raw evidence: {analysis.evidence}
"""
        response = self.llm.invoke(
            [
                SystemMessage(content="You are a technical report writer."),
                HumanMessage(content=prompt),
            ]
        )
        return str(response.content).strip()
