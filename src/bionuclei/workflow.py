"""Reusable, headless BioNuclei analysis workflows."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class AnalysisWorkflow:
    """Declarative workflow definition for deterministic BioNuclei operations."""

    name: str
    analyses: tuple[str, ...] = ("nuclei", "morphology", "intensity")
    device: str = "cpu"
    keep_intermediates: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        allowed = {"nuclei", "morphology", "intensity"}
        unknown = set(self.analyses) - allowed
        if unknown:
            raise ValueError(f"Unsupported analyses: {sorted(unknown)}")
        if not self.name.strip():
            raise ValueError("Workflow name cannot be empty")
        if self.device not in {"cpu", "cuda", "auto"}:
            raise ValueError(f"Unsupported device: {self.device}")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "name": self.name,
            "analyses": list(self.analyses),
            "device": self.device,
            "keep_intermediates": self.keep_intermediates,
            "metadata": dict(self.metadata),
        }


def load_workflow(path: Path) -> AnalysisWorkflow:
    """Load a JSON workflow without importing a UI framework."""
    import json

    data = json.loads(path.read_text())
    workflow = AnalysisWorkflow(
        name=str(data["name"]),
        analyses=tuple(str(x) for x in data.get("analyses", ["nuclei", "morphology", "intensity"])),
        device=str(data.get("device", "cpu")),
        keep_intermediates=bool(data.get("keep_intermediates", False)),
        metadata=dict(data.get("metadata", {})),
    )
    workflow.validate()
    return workflow


def save_workflow(workflow: AnalysisWorkflow, path: Path) -> None:
    import json

    workflow.validate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(workflow.to_dict(), indent=2) + "\n")
