"""Shared data models for architecture review pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ReportFocus = Literal["general", "security", "scalability", "maintainability"]
ReActStepStatus = Literal["success", "error", "stopped"]
ReActStopCondition = Literal["enough_evidence", "api_error", "rate_limit", "max_iterations"]


class RepoReference(BaseModel):
    owner: str
    repo: str
    branch: Optional[str] = None
    full_name: str
    html_url: Optional[str] = None


class RepoMetadata(BaseModel):
    name: str
    full_name: str
    description: Optional[str] = None
    default_branch: str
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    language: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    private: bool = False
    archived: bool = False
    pushed_at: Optional[str] = None
    html_url: str


class RepoFileInfo(BaseModel):
    path: str
    type: Literal["blob", "tree"]
    size: int = 0
    sha: Optional[str] = None


class DependencyInfo(BaseModel):
    ecosystem: str
    dependencies: List[str] = Field(default_factory=list)
    evidence_file: str


class ProjectStructureFinding(BaseModel):
    modules: List[str] = Field(default_factory=list)
    entry_points: List[str] = Field(default_factory=list)
    config_files: List[str] = Field(default_factory=list)
    ci_files: List[str] = Field(default_factory=list)
    container_files: List[str] = Field(default_factory=list)
    key_directories: List[str] = Field(default_factory=list)


class ReActStep(BaseModel):
    step_index: int
    thought: str
    action: str
    action_input: Dict[str, Any] = Field(default_factory=dict)
    observation: str
    status: ReActStepStatus = "success"
    stop_reason: Optional[str] = None


class ReActSummary(BaseModel):
    max_iterations: int = 8
    iterations_used: int = 0
    stop_condition: ReActStopCondition = "max_iterations"
    fallback_used: bool = False


class RepoAnalysisResult(BaseModel):
    repo: RepoReference
    metadata: RepoMetadata
    files_sampled: List[RepoFileInfo] = Field(default_factory=list)
    tech_stack: List[str] = Field(default_factory=list)
    dependencies: List[DependencyInfo] = Field(default_factory=list)
    structure: ProjectStructureFinding
    architectural_patterns: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    reasoning_trace: List[ReActStep] = Field(default_factory=list)
    react_summary: ReActSummary = Field(default_factory=ReActSummary)
    focus: ReportFocus = "general"
    report_depth: Literal["short", "standard", "deep"] = "standard"


class ArchitectureReviewResult(BaseModel):
    project_overview: str
    architecture_observations: List[str] = Field(default_factory=list)
    risks_and_antipatterns: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)


class ArchitectureReport(BaseModel):
    title: str
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    repo_full_name: str
    focus: ReportFocus = "general"
    summary: str
    detected_stack: List[str] = Field(default_factory=list)
    module_breakdown: List[str] = Field(default_factory=list)
    architecture_observations: List[str] = Field(default_factory=list)
    risks_and_antipatterns: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    raw_evidence: Dict[str, Any] = Field(default_factory=dict)
    markdown_report: str
    report_path: Optional[str] = None


class MemoryRecord(BaseModel):
    repo_key: str
    analyzed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    focus: ReportFocus = "general"
    report_depth: Literal["short", "standard", "deep"] = "standard"
    summary: str
    tech_stack: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    risk_count: int = 0
    module_count: int = 0
    dependency_count: int = 0
    stack_signature: str = ""
    architecture_patterns: List[str] = Field(default_factory=list)
    entry_points_count: int = 0
    config_files_count: int = 0


class MemoryComparison(BaseModel):
    repo_key: str
    previous_exists: bool
    previous_analyzed_at: Optional[str] = None
    new_risks: List[str] = Field(default_factory=list)
    resolved_risks: List[str] = Field(default_factory=list)
    focus_changed: bool = False
    risk_delta: int = 0
    module_delta: int = 0
    dependency_delta: int = 0
    stack_changed: bool = False
    pattern_changes: Dict[str, List[str]] = Field(default_factory=lambda: {"added": [], "removed": []})
    drift_status: Literal["improved", "stable", "regressed"] = "stable"
    improvement_score: int = 50
