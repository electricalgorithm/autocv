"""Pydantic schema for CVML documents, as specified in docs/CVML_SPEC.md."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from autocv.markup.dates import require_year_month, require_year_month_or_present


class CVModel(BaseModel):
    """Base model shared by every CVML node: closed schema, trimmed strings."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Person(CVModel):
    """Identity fields shown in the CV header."""

    name: str
    headline: str
    photo: str | None = None
    birth_date: date | None = None
    citizenships: list[str] = Field(default_factory=list)
    work_authorization: str | None = None


class Contact(CVModel):
    """Contact details shown in the CV header."""

    email: EmailStr
    phone: str
    location: str
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None
    scholar: str | None = None


class ExperienceEntry(CVModel):
    """One professional experience entry."""

    title: str
    organization: str
    organization_url: str | None = None
    location: str
    start: str
    end: str
    summary: str | None = None
    highlights: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)

    @field_validator("start")
    @classmethod
    def _check_start(cls, value: str) -> str:
        return require_year_month(value)

    @field_validator("end")
    @classmethod
    def _check_end(cls, value: str) -> str:
        return require_year_month_or_present(value)

    @model_validator(mode="after")
    def _require_summary_or_highlights(self) -> ExperienceEntry:
        if not self.summary and not self.highlights:
            raise ValueError("experience entry needs a summary or at least one highlight")
        return self


class EducationEntry(CVModel):
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


class Publication(CVModel):
    """One publication entry."""

    title: str
    venue: str
    date: str
    url: str | None = None

    @field_validator("date")
    @classmethod
    def _check_date(cls, value: str) -> str:
        return require_year_month(value)


class Project(CVModel):
    """One open-source or personal project entry."""

    title: str
    categories: list[str] = Field(default_factory=list)
    detail: str | None = None
    stack: list[str] = Field(default_factory=list)
    url: str | None = None


class Reference(CVModel):
    """One professional reference."""

    name: str
    title: str
    organization: str
    email: EmailStr


class LanguageSkill(CVModel):
    """One spoken/written language and proficiency level."""

    name: str
    level: str


class CV(CVModel):
    """Full CV document: the root of a CVML file."""

    person: Person
    contact: Contact
    summary: str
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    publications: list[Publication] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    languages: list[LanguageSkill] = Field(default_factory=list)
