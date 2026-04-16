"""CLI entrypoint for AI Architecture Review Assistant."""

from __future__ import annotations

import json
import os
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from src.agents.architecture_review_agent import ArchitectureReviewAgent
from src.agents.repo_analysis_agent import RepositoryAnalysisAgent
from src.agents.report_writer_agent import ReportWriterAgent
from src.memory.memory_store import MemoryStore
from src.services.github_service import GitHubService, GitHubServiceError
from src.services.llm_service import LLMService
from src.services.report_service import ReviewPipeline
from src.utils.helpers import parse_github_input

app = typer.Typer(help="AI Architecture Review Assistant CLI")
console = Console()


@app.command()
def analyze(
    repository: str = typer.Argument(..., help="GitHub URL or owner/repo"),
    focus: str = typer.Option("general", help="general | security | scalability | maintainability"),
    report_depth: str = typer.Option("standard", help="short | standard | deep"),
    github_token: Optional[str] = typer.Option(None, help="Optional GitHub token"),
    verbose: bool = typer.Option(False, "--verbose", help="Show raw JSON details for debugging."),
) -> None:
    """Run architecture analysis for a repository."""
    load_dotenv()
    owner, repo = parse_github_input(repository)
    token = github_token or os.getenv("GITHUB_TOKEN")

    try:
        llm = LLMService().create_chat_model()
        github_service = GitHubService(token=token)
        memory_store = MemoryStore()
        pipeline = ReviewPipeline(
            repo_agent=RepositoryAnalysisAgent(github_service=github_service, llm=llm),
            review_agent=ArchitectureReviewAgent(llm=llm),
            writer_agent=ReportWriterAgent(llm=llm),
            memory_store=memory_store,
        )
        result = pipeline.run(owner=owner, repo=repo, focus=focus, report_depth=report_depth)
    except (ValueError, GitHubServiceError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    report = result["report"]
    analysis = result["analysis"]
    comparison = result["comparison"]

    console.print(Panel(report["summary"], title="Project Overview"))
    console.print("[bold]Detected stack:[/bold]")
    for stack in report.get("detected_stack", [])[:8]:
        console.print(f"- {stack}")

    console.print("\n[bold]Top recommendations:[/bold]")
    for rec in report.get("recommendations", [])[:4]:
        console.print(f"- {rec}")

    console.print("\n[bold]Priority risks:[/bold]")
    for risk in report.get("risks_and_antipatterns", [])[:4]:
        console.print(f"- {risk}")

    react_summary = analysis.get("react_summary", {})
    console.print(
        "\n[bold]ReAct summary:[/bold] "
        f"stop=[cyan]{react_summary.get('stop_condition')}[/cyan] | "
        f"iterations=[cyan]{react_summary.get('iterations_used')}/{react_summary.get('max_iterations')}[/cyan] | "
        f"fallback=[cyan]{react_summary.get('fallback_used')}[/cyan]"
    )
    trace = analysis.get("reasoning_trace", [])
    if trace:
        console.print("[bold]Recent reasoning steps:[/bold]")
        for step in trace[-3:]:
            console.print(
                f"- Step {step.get('step_index')}: action={step.get('action')}, "
                f"status={step.get('status')}, observation={step.get('observation')}"
            )

    console.print("\n[bold]Architecture drift:[/bold]")
    console.print(
        f"- Status: [cyan]{comparison.get('drift_status')}[/cyan]\n"
        f"- Improvement score: [cyan]{comparison.get('improvement_score')}[/cyan]/100\n"
        f"- Previous run: {comparison.get('previous_analyzed_at') or 'N/A'}\n"
        f"- Stack changed: {comparison.get('stack_changed')}\n"
        f"- Focus changed: {comparison.get('focus_changed')}"
    )
    new_risks = comparison.get("new_risks", [])
    resolved_risks = comparison.get("resolved_risks", [])
    if new_risks:
        console.print("- New risks since previous run:")
        for item in new_risks[:5]:
            console.print(f"  - {item}")
    if resolved_risks:
        console.print("- Resolved risks since previous run:")
        for item in resolved_risks[:5]:
            console.print(f"  - {item}")

    if verbose:
        console.print("\n[bold]Raw comparison payload (verbose):[/bold]")
        console.print(json.dumps(comparison, indent=2))

    console.print(f"\nSaved report: [green]{report.get('report_path')}[/green]")


if __name__ == "__main__":
    app()
