"""Pydantic schema for master profile documents, per docs/MASTER_PROFILE_SPEC.md."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from autocv.markup.dates import require_year_month, require_year_month_or_present


class ProfileModel(BaseModel):
    """Base model shared by every master profile node."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProfileExperience(ProfileModel):
    """One professional experience entry, with the raw achievements pool."""

    title: str
    organization: str
    organization_url: str | None = None
    location: str
    start: str
    end: str
    keywords: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)

    @field_validator("start")
    @classmethod
    def _check_start(cls, value: str) -> str:
        return require_year_month(value)

    @field_validator("end")
    @classmethod
    def _check_end(cls, value: str) -> str:
        return require_year_month_or_present(value)


class ProfileEducation(ProfileModel):
    """One education entry."""

    degree: str
    institution: str
    institution_url: str | None = None
    location: str
    start: str
    end: str
    detail: str | None = None

    @field_validator("start")
    @classmethod
    def _check_start(cls, value: str) -> str:
        return require_year_month(value)

    @field_validator("end")
    @classmethod
    def _check_end(cls, value: str) -> str:
        return require_year_month_or_present(value)


class ProfilePublication(ProfileModel):
    """One publication entry."""

    title: str
    venue: str
    date: str
    url: str | None = None

    @field_validator("date")
    @classmethod
    def _check_date(cls, value: str) -> str:
        return require_year_month(value)


class ProfileProject(ProfileModel):
    """One project entry, with the raw achievements pool."""

    title: str
    categories: list[str] = Field(default_factory=list)
    detail: str | None = None
    stack: list[str] = Field(default_factory=list)
    url: str | None = None
    achievements: list[str] = Field(default_factory=list)


class MasterProfile(ProfileModel):
    """The applicant's full experience pool."""

    experience: list[ProfileExperience] = Field(default_factory=list)
    education: list[ProfileEducation] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    publications: list[ProfilePublication] = Field(default_factory=list)
    projects: list[ProfileProject] = Field(default_factory=list)
