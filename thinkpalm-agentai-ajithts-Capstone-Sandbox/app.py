"""Streamlit UI for AI Architecture Review Assistant."""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from src.agents.architecture_review_agent import ArchitectureReviewAgent
from src.agents.repo_analysis_agent import RepositoryAnalysisAgent
from src.agents.report_writer_agent import ReportWriterAgent
from src.memory.memory_store import MemoryStore
from src.services.github_service import GitHubService, GitHubServiceError
from src.services.llm_service import LLMService
from src.services.report_service import ReviewPipeline
from src.utils.helpers import parse_github_input


def render_bullets(title: str, items: list, empty_text: str = "No data available.") -> None:
    st.markdown(f"**{title}**")
    if not items:
        st.caption(empty_text)
        return
    for item in items:
        st.markdown(f"- {item}")


def to_yes_no(value: bool) -> str:
    return "Yes" if value else "No"


st.set_page_config(page_title="AI Architecture Review Assistant", layout="wide")
st.title("AI Architecture Review Assistant")
st.caption("Agentic repository architecture analysis with memory, tool-calling, and report export.")

load_dotenv()
memory_store = MemoryStore()

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

with st.sidebar:
    st.subheader("Inputs")
    repo_input = st.text_input("GitHub repo URL or owner/repo", value="langchain-ai/langchain")
    github_token = st.text_input("GitHub token (optional)", type="password")
    focus = st.selectbox("Report focus", options=["general", "security", "scalability", "maintainability"])
    report_depth = st.selectbox("Report depth", options=["short", "standard", "deep"], index=1)
    analyze_clicked = st.button("Analyze repository", type="primary")

if analyze_clicked:
    try:
        owner, repo = parse_github_input(repo_input)
        token = github_token or os.getenv("GITHUB_TOKEN")
        llm = LLMService().create_chat_model()
        pipeline = ReviewPipeline(
            repo_agent=RepositoryAnalysisAgent(github_service=GitHubService(token=token), llm=llm),
            review_agent=ArchitectureReviewAgent(llm=llm),
            writer_agent=ReportWriterAgent(llm=llm),
            memory_store=memory_store,
        )
        with st.spinner("Analyzing repository..."):
            result = pipeline.run(owner=owner, repo=repo, focus=focus, report_depth=report_depth)
        st.session_state["last_result"] = result
    except (ValueError, GitHubServiceError, Exception) as exc:
        st.error(f"Analysis failed: {exc}")

result = st.session_state.get("last_result")
if result:
    report = result["report"]
    analysis = result["analysis"]
    comparison = result["comparison"]

    st.success(f"Analysis complete for `{report['repo_full_name']}`")
    st.markdown(f"**Saved report:** `{report.get('report_path')}`")

    tabs = st.tabs(
        [
            "Summary",
            "Repo Structure",
            "Findings",
            "Recommendations",
            "Raw Evidence",
            "Reasoning Trace",
            "Architecture Drift",
            "Reports",
        ]
    )
    with tabs[0]:
        st.subheader("Project Overview")
        st.write(report["summary"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Detected technologies", len(report.get("detected_stack", [])))
        c2.metric("Modules identified", len(report.get("module_breakdown", [])))
        c3.metric("Risks flagged", len(report.get("risks_and_antipatterns", [])))
        render_bullets("Detected Stack", report.get("detected_stack", []), "No clear stack markers found.")
    with tabs[1]:
        st.subheader("Structure")
        structure = analysis.get("structure", {})
        render_bullets("Modules", report.get("module_breakdown", []), "No module boundaries inferred.")
        render_bullets("Entry Points", structure.get("entry_points", []), "No entry points detected.")
        render_bullets("Configuration Files", structure.get("config_files", []), "No config files identified.")
    with tabs[2]:
        st.subheader("Architecture Observations")
        render_bullets(
            "Observations",
            report.get("architecture_observations", []),
            "No architecture observations were generated.",
        )
        st.subheader("Risks / Anti-patterns")
        render_bullets("Risk Findings", report.get("risks_and_antipatterns", []), "No significant risks detected.")
    with tabs[3]:
        st.subheader("Recommendations")
        render_bullets("Recommended Actions", report.get("recommendations", []), "No recommendations available.")
        st.subheader("Suggested Next Steps")
        render_bullets("Execution Plan", report.get("next_steps", []), "No next steps available.")
    with tabs[4]:
        st.subheader("Raw Evidence")
        evidence = report.get("raw_evidence", {})
        warnings = analysis.get("evidence", {}).get("analysis_warnings", [])
        sampled = evidence.get("sampled_files", [])
        read_files = evidence.get("read_files", [])
        st.markdown(
            f"- Sampled files: **{len(sampled)}**\n"
            f"- Files read in detail: **{len(read_files)}**\n"
            f"- Metadata captured: **{to_yes_no(bool(evidence.get('metadata')))}**"
        )
        render_bullets("Analysis Warnings", warnings, "No warnings reported.")
        with st.expander("Show raw evidence payload (JSON)"):
            st.json(evidence)
    with tabs[5]:
        st.subheader("Reasoning Trace (ReAct)")
        react_summary = analysis.get("react_summary", {})
        st.markdown(
            f"**Stop condition:** `{react_summary.get('stop_condition', 'n/a')}` | "
            f"**Iterations:** `{react_summary.get('iterations_used', 0)}/"
            f"{react_summary.get('max_iterations', 0)}` | "
            f"**Fallback used:** `{react_summary.get('fallback_used', False)}`"
        )
        trace_rows = analysis.get("reasoning_trace", [])
        if trace_rows:
            for step in trace_rows:
                st.markdown(
                    f"**Step {step.get('step_index')}** - {step.get('status', 'unknown').upper()}  \n"
                    f"- Thought: {step.get('thought', 'n/a')}  \n"
                    f"- Action: `{step.get('action', 'n/a')}`  \n"
                    f"- Observation: {step.get('observation', 'n/a')}"
                )
        else:
            st.info("No reasoning trace captured.")
    with tabs[6]:
        st.subheader("Architecture Drift Detection")
        st.markdown(f"- Drift status: **{comparison.get('drift_status', 'n/a')}**")
        st.markdown(f"- Improvement score: **{comparison.get('improvement_score', 'n/a')} / 100**")
        st.markdown(f"- Previous run timestamp: `{comparison.get('previous_analyzed_at', 'n/a')}`")
        st.markdown(f"- Focus changed from previous run: **{to_yes_no(comparison.get('focus_changed', False))}**")
        st.markdown(f"- Stack changed: **{to_yes_no(comparison.get('stack_changed', False))}**")
        st.markdown(
            f"- Risk delta: **{comparison.get('risk_delta', 0)}**, "
            f"Module delta: **{comparison.get('module_delta', 0)}**, "
            f"Dependency delta: **{comparison.get('dependency_delta', 0)}**"
        )
        render_bullets("New Risks Since Last Run", comparison.get("new_risks", []), "No new risks identified.")
        render_bullets(
            "Resolved Risks Since Last Run",
            comparison.get("resolved_risks", []),
            "No previously known risks were resolved.",
        )
        pattern_changes = comparison.get("pattern_changes", {"added": [], "removed": []})
        render_bullets("Pattern Additions", pattern_changes.get("added", []), "No new patterns added.")
        render_bullets("Pattern Removals", pattern_changes.get("removed", []), "No patterns removed.")
    with tabs[7]:
        st.subheader("Reports")
        st.markdown(f"**Saved report path:** `{report.get('report_path')}`")
        st.download_button(
            label="Download markdown report",
            data=report["markdown_report"],
            file_name=f"{report['repo_full_name'].replace('/', '_')}_architecture_report.md",
            mime="text/markdown",
        )

        with st.expander("Preview full markdown report"):
            st.markdown(report["markdown_report"])
else:
    st.info("Enter a repository and click Analyze repository to generate a report.")
