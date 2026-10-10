"""Prompt construction for each agent in the adaptation workflow."""

from __future__ import annotations

import json

import yaml

from autocv.adapt.models import CompanyResearch, FactCheckReport
from autocv.jobs.models import JobPosting
from autocv.markup.models import CV
from autocv.profile.models import MasterProfile

_STYLE_GUIDE = """\
Content selection:
- Every experience entry uses "highlights" (a bullet list) and no "summary". \
Give the two most recent roles 3-4 bullets, older roles 2-3, internships 2. \
Order bullets by relevance to the job, not by the profile's order.
- Do not emit "keywords" on experience entries, "stack" on projects, or \
"certifications". They read as keyword stuffing.
- Pick 3-5 projects relevant to the job. Skip any project that is the \
reference implementation of a listed publication. Each project "detail" \
is one or two sentences on what the applicant built and the measurable \
result. Do not describe team size, architecture overviews, or technology \
choices in project details.
- Keep only project categories that are plain domains (Embedded, ML, IoT, \
Web, Research, DSP). Drop abstract ones like "System Architecture".
- Publications newest first.
- "skills" is 8-12 lines. Group related items on one line (all programming \
languages on one line, e.g. "C/C++, Python, Go"). Use a parenthetical only \
when it adds a concrete tool name the job asks for; otherwise leave the \
line bare. Never repeat a skill that already appears in another line.
- Prefer the base CV's "summary" wording. Adjust it only to shift emphasis \
toward the job; keep it first person and keep the applicant's own voice.

Writing style (applies to every bullet, detail, and summary):
- Plain, readable English, the way an engineer describes their own work. \
Not job-posting language, not a keyword list.
- Start with the profile's own bullet wording. Trim, merge, or split it; \
do not re-inflate it with adjectives.
- One idea per sentence. If a bullet needs two ideas, use two sentences. \
Do not chain clauses with dashes or with "while", "by", "plus".
- No em dashes or en dashes anywhere. Use commas, parentheses, a colon, or \
a new sentence.
- Do not use these words and phrases: end-to-end, leveraged, spearheaded, \
cutting-edge, robust, seamless, state-of-the-art, "sourced", "on-device" \
as a filler adjective, "so X could Y without waiting on Z".
- Keep numbers exactly as the profile states them, including "~" where the \
profile uses it. Never round up or strengthen a claim. Do not report a \
100% accuracy figure even if the profile has one; use the more \
conservative number for that item.
- Do not name specific LLM vendors or models (write "AI workflow" or \
"LLM agent", not the model name).
- Do not use internal incident or escalation jargon (write "alarming", \
not a severity code). Do not mention how many engineers a change freed up.
- Refer to hardware at chip level (RP2040, Syntiant NPU), not by dev-kit \
product names.
- Do not include the applicant's project-management or process bullets \
(agile ceremonies, ADR processes, on-call rotations) unless the job \
explicitly asks for that.
"""

_DRAFT_INSTRUCTIONS = """\
You are tailoring a CV to a specific job posting.

Output ONLY a single YAML document (CVML) that validates against the JSON \
Schema below. Do not include markdown code fences, commentary, or any text \
before or after the YAML.

Rules:
- Reuse only facts present in the applicant's master profile below. Never \
invent an employer, title, date, metric, or credential that is not there.
- You may re-order, re-phrase, and select a subset of entries.
- The "person" and "contact" objects must be copied unchanged from the \
base identity provided below.
- Omit "references" and "languages", or leave them empty. They are not \
present in the master profile and are filled in separately.

{style_guide}
JSON Schema for the CVML document:
{schema}
"""

_RESEARCH_INSTRUCTIONS = """\
You are researching the company behind a job posting, to inform how a CV \
should be framed for it.

Use web search and fetch the company's own pages (site, careers page, \
about page) where available. Ground every claim in what you actually \
found — do not guess or rely on prior knowledge of the company. If you \
cannot find the company or any usable information, say so in the summary \
and leave "products"/"culture_notes"/"sources" empty rather than \
inventing anything.

Output ONLY a single YAML document that validates against the JSON Schema \
below. Do not include markdown code fences, commentary, or any text \
before or after the YAML.

JSON Schema:
{schema}
"""

_FACT_CHECK_INSTRUCTIONS = """\
You are fact-checking a draft CV against the applicant's master profile, \
which contains only verified facts.

Find every claim in the draft — employer, title, dates, metrics, \
credentials, technologies — that is NOT directly supported by the master \
profile. Rephrasing and reasonable synthesis of profile facts are fine and \
are not issues; a new employer, date, number, or credential that does not \
appear in the profile is an issue.

Output ONLY a single YAML document that validates against the JSON Schema \
below. Do not include markdown code fences, commentary, or any text \
before or after the YAML. If nothing is wrong, return an empty issues list.

JSON Schema:
{schema}
"""

_EDITORIAL_INSTRUCTIONS = """\
You are the final editor for a tailored CV. You are given a draft CV, a \
fact-check report, company research on the hiring company, the \
applicant's master profile, the job posting, and the applicant's base \
identity.

Rules:
- Correct or remove every issue the fact-check report raised, using only \
the master profile as the source of truth.
- Use the company research only to decide which existing, true experience \
to foreground and how to frame it, never as a new source of facts about \
the applicant. If the research is empty or unhelpful, ignore it.
- Otherwise follow the same rules as the draft: reuse only facts present \
in the master profile, no invented employer/title/date/metric/credential.
- Don't spend effort on "person", "contact", "references", or "languages". \
They are copied from the base identity regardless of what you write.
- Read every bullet once more against the writing-style rules below and \
fix any that break them. This is your main job after the fact-check.

{style_guide}
Output ONLY a single YAML document (CVML) that validates against the JSON \
Schema below. Do not include markdown code fences, commentary, or any text \
before or after the YAML.

JSON Schema for the CVML document:
{schema}
"""


def _dump_yaml(data: object) -> str:
    """Dump a JSON-compatible value as YAML for prompt embedding.

    Args:
        data: The value to dump, typically from ``model_dump(mode="json")``.

    Returns:
        The YAML text.
    """
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def _format_job(job: JobPosting) -> str:
    """Format a job posting as plain text for a prompt.

    Args:
        job: The job posting.

    Returns:
        The formatted text.
    """
    return (
        f"Title: {job.title}\n"
        f"Company: {job.company or 'unknown'}\n"
        f"Location: {job.location or 'unknown'}\n\n"
        f"{job.description}"
    )


def build_system_prompt() -> str:
    """Build the draft agent's system prompt: instructions plus the CVML schema.

    The schema is generated from ``autocv.markup.models.CV`` itself, so the
    prompt can never drift out of sync with the schema it asks for.

    Returns:
        The system prompt text.
    """
    schema = json.dumps(CV.model_json_schema(), indent=2)
    return _DRAFT_INSTRUCTIONS.format(style_guide=_STYLE_GUIDE, schema=schema)


def build_user_prompt(profile: MasterProfile, job: JobPosting, base: CV) -> str:
    """Build the draft agent's user prompt.

    Args:
        profile: The applicant's full experience pool.
        job: The job posting to tailor the CV to.
        base: The base CV; only its ``person``/``contact`` fields are used,
            as the identity to carry through unchanged.

    Returns:
        The user prompt text.
    """
    base_identity = _dump_yaml(
        {
            "person": base.person.model_dump(mode="json"),
            "contact": base.contact.model_dump(mode="json"),
        }
    )
    profile_yaml = _dump_yaml(profile.model_dump(mode="json"))
    return (
        "## Job posting\n\n"
        f"{_format_job(job)}\n\n"
        "## Base identity (copy unchanged into person/contact)\n\n"
        f"{base_identity}\n"
        "## Master profile (full experience pool to select and rephrase from)\n\n"
        f"{profile_yaml}\n"
        "Now write the tailored CVML document."
    )


def build_research_system_prompt() -> str:
    """Build the research agent's system prompt.

    Returns:
        The system prompt text.
    """
    schema = json.dumps(CompanyResearch.model_json_schema(), indent=2)
    return _RESEARCH_INSTRUCTIONS.format(schema=schema)


def build_research_user_prompt(job: JobPosting) -> str:
    """Build the research agent's user prompt.

    Args:
        job: The job posting naming the company to research.

    Returns:
        The user prompt text.
    """
    return f"## Job posting\n\n{_format_job(job)}\n\nResearch this company."


def build_fact_check_system_prompt() -> str:
    """Build the fact-check agent's system prompt.

    Returns:
        The system prompt text.
    """
    schema = json.dumps(FactCheckReport.model_json_schema(), indent=2)
    return _FACT_CHECK_INSTRUCTIONS.format(schema=schema)


def build_fact_check_user_prompt(draft: CV, profile: MasterProfile) -> str:
    """Build the fact-check agent's user prompt.

    Args:
        draft: The draft CV to check.
        profile: The applicant's full experience pool (source of truth).

    Returns:
        The user prompt text.
    """
    draft_yaml = _dump_yaml(draft.model_dump(mode="json"))
    profile_yaml = _dump_yaml(profile.model_dump(mode="json"))
    return (
        "## Draft CV\n\n"
        f"{draft_yaml}\n"
        "## Master profile (source of truth)\n\n"
        f"{profile_yaml}\n"
        "Now fact-check the draft."
    )


def build_editorial_system_prompt() -> str:
    """Build the editorial agent's system prompt.

    Returns:
        The system prompt text.
    """
    schema = json.dumps(CV.model_json_schema(), indent=2)
    return _EDITORIAL_INSTRUCTIONS.format(style_guide=_STYLE_GUIDE, schema=schema)


def build_editorial_user_prompt(  # noqa: PLR0913, PLR0917 - each is distinct input material
    draft: CV,
    research: CompanyResearch,
    fact_check: FactCheckReport,
    profile: MasterProfile,
    job: JobPosting,
    base: CV,
) -> str:
    """Build the editorial agent's user prompt.

    Args:
        draft: The draft CV produced by the drafting agent.
        research: Company research findings.
        fact_check: The fact-check report over the draft.
        profile: The applicant's full experience pool.
        job: The job posting to tailor the CV to.
        base: The base CV; only its identity fields are used.

    Returns:
        The user prompt text.
    """
    base_identity = _dump_yaml(
        {
            "person": base.person.model_dump(mode="json"),
            "contact": base.contact.model_dump(mode="json"),
        }
    )
    return (
        "## Job posting\n\n"
        f"{_format_job(job)}\n\n"
        "## Draft CV\n\n"
        f"{_dump_yaml(draft.model_dump(mode='json'))}\n"
        "## Fact-check report (fix or remove every issue)\n\n"
        f"{_dump_yaml(fact_check.model_dump(mode='json'))}\n"
        "## Company research (framing only, not a source of new facts)\n\n"
        f"{_dump_yaml(research.model_dump(mode='json'))}\n"
        "## Base identity (copied automatically, shown for context only)\n\n"
        f"{base_identity}\n"
        "## Master profile (full experience pool to select and rephrase from)\n\n"
        f"{_dump_yaml(profile.model_dump(mode='json'))}\n"
        "Now write the final, edited CVML document."
    )
