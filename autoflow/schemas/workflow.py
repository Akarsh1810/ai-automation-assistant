from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowOutput(BaseModel):
    summary: str = Field(description="Human-readable summary of the result")
    output_path: str | None = Field(None, description="Path to output file if applicable")
    data: Any = Field(None, description="Structured data output")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
