"""Repository Analysis Agent."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.models.schemas import (
    ReActStep,
    ReActSummary,
    RepoAnalysisResult,
    RepoFileInfo,
    RepoMetadata,
    RepoReference,
)
from src.tools.analysis_tools import (
    analyze_project_structure,
    detect_architecture_patterns,
    detect_risks,
    detect_tech_stack,
    parse_dependencies,
)
from src.tools.github_tools import build_github_tools
from src.utils.helpers import prioritize_paths


class RepositoryAnalysisAgent:
    """Collects evidence and creates a structured repository analysis."""

    def __init__(self, github_service, llm: BaseChatModel) -> None:
        self.github_tools = build_github_tools(github_service)
        self.llm = llm
        self.max_files_to_analyze = int(os.getenv("MAX_FILES_TO_ANALYZE", "120"))
        self.max_file_bytes = int(os.getenv("MAX_FILE_BYTES", "120000"))
        self.max_react_iterations = int(os.getenv("MAX_REACT_ITERATIONS", "8"))
        self.target_file_reads = int(os.getenv("TARGET_FILE_READS", "12"))

    def _llm_observations(self, metadata: RepoMetadata, files: List[str], focus: str) -> List[str]:
        top_files = "\n".join(f"- {f}" for f in files[:40])
        prompt = (
            "Given repository metadata and sampled file paths, provide concise architecture observations.\n"
            "Return 4-8 bullet points only, each prefixed with '- '.\n\n"
            f"Repository: {metadata.full_name}\n"
            f"Description: {metadata.description}\n"
            f"Primary language: {metadata.language}\n"
            f"Focus area: {focus}\n"
            f"Sampled file paths:\n{top_files}"
        )
        response = self.llm.invoke(
            [
                SystemMessage(content="You are an architecture analyst focused on practical codebase review."),
                HumanMessage(content=prompt),
            ]
        )
        lines = [line.strip("- ").strip() for line in response.content.splitlines() if line.strip().startswith("-")]
        return lines[:8]

    def _short_observation(self, value: Any, max_chars: int = 240) -> str:
        text = str(value).replace("\n", " ").strip()
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."

    def _stop_from_exception(self, exc: Exception) -> str:
        message = str(exc).lower()
        if "rate" in message and "limit" in message:
            return "rate_limit"
        if "403" in message and "github" in message:
            return "rate_limit"
        return "api_error"

    def _run_react_loop(
        self,
        owner: str,
        repo: str,
    ) -> Tuple[RepoMetadata, str, List[Dict[str, Any]], List[str], Dict[str, str], List[ReActStep], ReActSummary]:
        fetch_tool = self.github_tools[0]
        list_tool = self.github_tools[1]
        read_tool = self.github_tools[2]

        metadata: RepoMetadata | None = None
        branch = "main"
        files_payload: List[Dict[str, Any]] = []
        prioritized_paths: List[str] = []
        file_contents: Dict[str, str] = {}
        trace: List[ReActStep] = []
        stop_condition = "max_iterations"

        for step_index in range(1, self.max_react_iterations + 1):
            thought = ""
            action = ""
            action_input: Dict[str, Any] = {}
            observation = ""
            status = "success"
            stop_reason = None

            try:
                if metadata is None:
                    thought = "Need repository metadata before choosing evidence strategy."
                    action = "fetch_repo_metadata_tool"
                    action_input = {"owner": owner, "repo": repo}
                    metadata_payload = fetch_tool.invoke(action_input)
                    metadata = RepoMetadata(**metadata_payload)
                    branch = metadata.default_branch
                    observation = f"Fetched metadata. default_branch={branch}, language={metadata.language}, stars={metadata.stars}"
                elif not files_payload:
                    thought = "Need repository file inventory to locate architecture signals."
                    action = "list_repo_files_tool"
                    action_input = {
                        "owner": owner,
                        "repo": repo,
                        "branch": branch,
                        "max_files": self.max_files_to_analyze,
                        "max_file_bytes": self.max_file_bytes,
                    }
                    files_payload = list_tool.invoke(action_input)
                    paths = [item["path"] for item in files_payload]
                    prioritized_paths = prioritize_paths(paths, limit=self.max_files_to_analyze)
                    observation = f"Collected {len(files_payload)} files; prioritized {len(prioritized_paths)} paths."
                elif len(file_contents) < min(self.target_file_reads, max(1, len(prioritized_paths))):
                    unread_paths = [p for p in prioritized_paths if p not in file_contents]
                    if not unread_paths:
                        stop_condition = "enough_evidence"
                        thought = "No additional high-priority files remain to read."
                        action = "stop"
                        action_input = {}
                        observation = "Stopped after reading all prioritized candidate files."
                        status = "stopped"
                        stop_reason = stop_condition
                        trace.append(
                            ReActStep(
                                step_index=step_index,
                                thought=thought,
                                action=action,
                                action_input=action_input,
                                observation=observation,
                                status=status,  # type: ignore[arg-type]
                                stop_reason=stop_reason,
                            )
                        )
                        break

                    next_path = unread_paths[0]
                    thought = "Need file-level evidence from high-priority configuration or entrypoint files."
                    action = "read_repo_file_tool"
                    action_input = {"owner": owner, "repo": repo, "path": next_path, "branch": branch}
                    content = read_tool.invoke(action_input)
                    if content:
                        file_contents[next_path] = content[:20000]
                        observation = f"Read {next_path} ({len(content)} chars)."
                    else:
                        observation = f"File {next_path} was empty/unreadable; moving to next."
                else:
                    stop_condition = "enough_evidence"
                    thought = "Evidence is sufficient for architecture analysis and risk scoring."
                    action = "stop"
                    action_input = {}
                    observation = (
                        f"Stopping with metadata + {len(prioritized_paths)} files listed + "
                        f"{len(file_contents)} files read."
                    )
                    status = "stopped"
                    stop_reason = stop_condition
                    trace.append(
                        ReActStep(
                            step_index=step_index,
                            thought=thought,
                            action=action,
                            action_input=action_input,
                            observation=observation,
                            status=status,  # type: ignore[arg-type]
                            stop_reason=stop_reason,
                        )
                    )
                    break
            except Exception as exc:
                stop_condition = self._stop_from_exception(exc)
                status = "error"
                thought = thought or "Tool call failed while collecting evidence."
                action = action or "unknown"
                observation = f"Tool failure: {self._short_observation(exc)}"
                stop_reason = stop_condition
                trace.append(
                    ReActStep(
                        step_index=step_index,
                        thought=thought,
                        action=action,
                        action_input=action_input,
                        observation=observation,
                        status=status,  # type: ignore[arg-type]
                        stop_reason=stop_reason,
                    )
                )
                break

            trace.append(
                ReActStep(
                    step_index=step_index,
                    thought=thought,
                    action=action,
                    action_input=action_input,
                    observation=self._short_observation(observation),
                    status=status,  # type: ignore[arg-type]
                    stop_reason=stop_reason,
                )
            )

        if metadata is None:
            raise ValueError("Could not fetch repository metadata during ReAct loop.")

        react_summary = ReActSummary(
            max_iterations=self.max_react_iterations,
            iterations_used=len(trace),
            stop_condition=stop_condition,  # type: ignore[arg-type]
            fallback_used=stop_condition != "enough_evidence",
        )
        return metadata, branch, files_payload, prioritized_paths, file_contents, trace, react_summary

    def run(
        self,
        owner: str,
        repo: str,
        focus: str = "general",
        report_depth: str = "standard",
    ) -> RepoAnalysisResult:
        metadata, branch, files_payload, prioritized_paths, file_contents, trace, react_summary = self._run_react_loop(
            owner=owner,
            repo=repo,
        )

        structure = analyze_project_structure(prioritized_paths)
        tech_stack = detect_tech_stack(prioritized_paths, metadata_language=metadata.language)
        dependencies = parse_dependencies(file_contents)
        patterns = detect_architecture_patterns(prioritized_paths, file_contents)
        risks = detect_risks(prioritized_paths, dependencies, focus=focus)
        llm_findings = self._llm_observations(metadata, prioritized_paths, focus=focus)

        evidence = {
            "sampled_files": prioritized_paths[:120],
            "read_files": list(file_contents.keys()),
            "metadata": metadata.model_dump(),
            "analysis_warnings": [],
        }
        if react_summary.fallback_used:
            evidence["analysis_warnings"].append(
                f"ReAct loop stopped by {react_summary.stop_condition}; report may be based on partial evidence."
            )

        sampled_files = [RepoFileInfo(**item) for item in files_payload[:120]]

        return RepoAnalysisResult(
            repo=RepoReference(
                owner=owner,
                repo=repo,
                full_name=f"{owner}/{repo}",
                branch=branch,
                html_url=metadata.html_url,
            ),
            metadata=metadata,
            files_sampled=sampled_files,
            tech_stack=tech_stack,
            dependencies=dependencies,
            structure=structure,
            architectural_patterns=sorted(set(patterns + llm_findings)),
            risks=risks,
            evidence=evidence,
            reasoning_trace=trace,
            react_summary=react_summary,
            focus=focus,  # type: ignore[arg-type]
            report_depth=report_depth,  # type: ignore[arg-type]
        )
