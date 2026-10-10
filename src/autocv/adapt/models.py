"""Structured outputs produced by the adaptation workflow's agents."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AdaptModel(BaseModel):
    """Base model shared by every adaptation-workflow output."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CompanyResearch(AdaptModel):
    """Findings about the hiring company, gathered by the research agent."""

    summary: str
    products: list[str] = Field(default_factory=list)
    culture_notes: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class FactCheckIssue(AdaptModel):
    """One claim in a draft CV that the fact-checker could not verify."""

    claim: str
    explanation: str


class FactCheckReport(AdaptModel):
    """Result of fact-checking a draft CV against the master profile."""

    issues: list[FactCheckIssue] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Whether the draft raised no fact-check issues."""
        return not self.issues
