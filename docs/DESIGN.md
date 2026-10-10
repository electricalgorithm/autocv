# Design

## Problem

A job applicant has one body of experience but every application should read as if
written for that specific role. Doing this by hand does not scale. This project
splits the problem into three stages, each solved by an independent component:

1. Hold the CV as structured, editable source instead of a fixed PDF.
2. Render that source into a document that looks like the applicant's real CV.
3. Given a job posting and the applicant's full experience pool, use an LLM to
   select and phrase a new source document targeted at that job, then render it.

## Components

### `autocv.markup` — CV source and schema

The canonical CV representation: a YAML document under a fixed schema, called
CVML (`docs/CVML_SPEC.md`). Chosen over a hand-rolled grammar because YAML has a
mature, forgiving parser and LLMs reliably produce syntactically valid YAML —
the schema is enforced separately by Pydantic, not by a custom parser that would
also need to be forgiving of LLM output.

- `models.py` — Pydantic models: `Contact`, `Person`, `ExperienceEntry`,
  `EducationEntry`, `Publication`, `Project`, `Reference`, `LanguageSkill`, `CV`.
  This is the single source of truth for the schema; the spec doc and the LLM
  prompt both derive from it.
- `parser.py` — `CVSource` protocol (`load() -> CV`) with a `YAMLCVSource`
  implementation. Isolated behind a protocol so the renderer and the adapter
  never depend on YAML specifically — a future source (e.g. a form-filled
  database record) only needs to implement `load`.

Problem solved: gives every other component one validated, typed CV object
instead of ad hoc dict access, and turns malformed LLM output into a caught
`CVValidationError` instead of a silently broken render.

### `autocv.render` — CV source to document

- `renderer.py` — `CVRenderer` protocol (`render(cv, output_path) -> Path`).
- `html_renderer.py` — `PlaywrightHTMLRenderer`: fills a Jinja2 HTML/CSS
  template from the CV model, then prints it to PDF with headless Chromium
  (already available in this environment). HTML/CSS was chosen over a direct
  PDF-drawing library (e.g. ReportLab) because the source CV is a
  browser-rendered template (confirmed from the PDF's embedded fonts/colors)
  and CSS is the fastest way to match spacing, color and two-column layout
  iteratively. Templates are self-contained directories under
  `templates/<name>/` (`cv.html.jinja` + `cv.css`), selected by name
  (`--template`, default `default`); `list_templates()` discovers them by
  scanning the directory rather than a hardcoded registry, so adding a
  template is just adding a directory.

Problem solved: turns any valid CVML document — original or LLM-adapted — into
the same visual artifact, so "does this look right" only needs checking once,
per template.

### `autocv.profile` — the applicant's full experience pool

A person has far more experience than fits one CV; the adapter needs the full
pool to choose from, in a human-editable file the applicant maintains directly
(`docs/MASTER_PROFILE_SPEC.md`). Markdown, not YAML: this file is prose-heavy
and hand-edited far more often than CVML is, so it optimizes for the applicant
writing it, not for a parser.

- `models.py` — `MasterProfile`, `ProfileExperience`, `ProfileEducation`, etc.
  A superset of the CVML entry shapes plus a free-form `achievements` list per
  entry, so the LLM has more raw material than any single CV needs.
- `parser.py` — `MasterProfileSource` protocol + Markdown implementation.

Problem solved: keeps "everything I've ever done" separate from "what goes on
this CV," so adding a new project never requires touching the CVML schema.

### `autocv.jobs` — job posting intake

- `models.py` — `JobPosting` (title, company, location, description text).
- `fetcher.py` — `JobPostingFetcher` protocol + `LinkedInJobFetcher` (best
  effort `httpx` + HTML text extraction; LinkedIn serves partial markup to
  unauthenticated requests, so this degrades to "whatever text is visible"
  rather than failing the whole run — documented, not hidden).

Problem solved: isolates the one component that depends on an external,
uncontrolled website, so its failure mode (partial/empty text) is a typed
result the generator can act on, not an exception that kills the CLI.

### `autocv.adapt` — the LLM adaptation

- `backends.py` — `MarkupGenerationBackend` protocol: one method,
  `generate(system_prompt, user_prompt) -> str`. Every provider — Claude Code
  CLI subprocess, Gemini API key, local Ollama — reduces to "send these two
  strings, get text back." This is what makes the provider swap in requirement
  (a)/(b)/(c) a one-line change at the call site instead of three parallel code
  paths.
  - `ClaudeCodeCLIBackend` — shells out to the `claude` CLI (`-p` / print mode)
    already installed in this environment. Implemented first, per instructions.
  - `GeminiBackend`, `OllamaBackend` — implemented via `pydantic-ai`, the
    library that gives one `Agent`/`Model` interface across providers
    (Google, and any OpenAI-compatible endpoint, which covers Ollama).
- `parsing.py` — `strip_code_fence` and `parse_yaml_model(text, ModelType)`:
  the shared "backend text → validated Pydantic model" step every agent below
  uses, so YAML-fence stripping and schema validation are written once.
- `prompts.py` — builds the system/user prompt pair for each agent role
  (draft, research, fact-check, editorial). The draft system prompt embeds
  the CV schema (constraints: reuse only facts present in the master
  profile, never invent employers/dates/metrics); person/contact/references/
  languages are marked as copied from the base CV, not generated.
- `generator.py` (`CVAdapter`) — the draft step: prompt → backend →
  parse/validate the returned CVML through `parsing.py` → on schema
  violation, retry once with the error appended to the prompt → force
  `person`/`contact`/`references`/`languages` back to the base CV's values
  regardless of what the backend returned.
- `research.py` — `CompanyResearcher` protocol (`research(job) ->
  CompanyResearch`): gathers company/product/culture context by letting the
  backend browse the web. `ClaudeCodeCLICompanyResearcher` reuses
  `ClaudeCodeCLIBackend` with `WebSearch`/`WebFetch` explicitly allowed (off
  by default for every other role — a plain-text agent has no reason to
  reach the network). `GeminiCompanyResearcher` uses pydantic-ai's built-in
  `WebSearchTool`/`WebFetchTool` (Gemini supports server-side search
  grounding). `OllamaCompanyResearcher` has no server-side search available
  to a local model, so it gets a single client-side `fetch_url` function
  tool instead — best-effort, documented as weaker than the other two.
- `fact_check.py` — `FactChecker` protocol (`check(draft, profile) ->
  FactCheckReport`): asks the backend to compare every claim in the draft
  against the master profile and list what it can't verify. Backend-agnostic
  (`LLMFactChecker` wraps any `MarkupGenerationBackend`), because fact-
  checking is text reasoning over data already in hand — it needs no tools.
- `editorial.py` — `Editor` protocol (`edit(draft, research, fact_check,
  profile, job, base) -> CV`): produces the final CV, instructed to correct
  or remove anything the fact-checker flagged and to use the company
  research only for framing/relevance, never as a new source of CV facts.
  Also backend-agnostic (`LLMEditor`).
- `workflow.py` — `CVWorkflow`: the graph tying the above together (see
  below).

Problem solved: the one place where "hallucination" is a real risk. Keeping
generation (LLM call) and validation (schema parse) as separate steps means a
bad LLM response is a caught, retryable error, never a corrupt CV file. Fact-
checking is a second, independent pass over the same risk, informed by
nothing the drafting step didn't already have — it can only catch drift, not
introduce it.

## Adaptation workflow

`CVWorkflow.run` is a small graph, not a single LLM call:

```
GenerateDraft ──┬──▶ ResearchCompany ──┐
                └──▶ FactCheckDraft ───┴──▶ EditorialSynthesis ──▶ tailored CV
```

`ResearchCompany` and `FactCheckDraft` run concurrently (`asyncio.gather`
over both, each wrapped in `asyncio.to_thread` since the underlying backends
are synchronous — subprocess/HTTP calls, matching every other component in
this codebase); `EditorialSynthesis` starts only once both finish. This is
implemented directly with `asyncio`, not the `pydantic_graph` library that
ships transitively with `pydantic-ai`: that library's current API is a
low-level fork/join graph *builder* (nodes, edges, typed state) aimed at
long-running, resumable, potentially-distributed graphs. For a 4-step,
in-process, run-to-completion workflow, `asyncio.gather` expresses the same
fan-out/join shape directly, with far less machinery to get wrong. Revisit
`pydantic_graph` if this workflow grows branches that need to persist,
resume, or run out-of-process.

Asymmetric failure handling, because the two branches are not equally
load-bearing:
- `ResearchCompany` failing (network error, backend misconfigured, nothing
  found) is not fatal — the workflow substitutes an empty `CompanyResearch`
  and continues. Company context is enrichment; losing it should not block a
  CV from being produced.
- `FactCheckDraft` failing propagates and aborts the run. Skipping the fact
  check silently would mean shipping a CV whose claims were never verified,
  which defeats the point of having it.

### `autocv.cli` — entry point

`typer` app with two subcommands:

- `autocv render SOURCE.cvml.yaml -o OUTPUT.pdf`
- `autocv adapt --profile PROFILE.md --job-url URL --base BASE.cvml.yaml -o OUT.cvml.yaml [--backend claude-code|gemini|ollama]`

Problem solved: one installable tool covering both the "show me the CV" and
"tailor the CV" use cases, sharing the same render step at the end of `adapt`.

## Data flow

```
                      ┌─────────────────┐
                      │ johndoe.cvml.yaml │──render──▶ PDF (unmodified CV)
                      └─────────────────┘
                              ▲
                              │ base identity (person/contact/references/languages)
┌───────────────┐   ┌───────────────────┐   ┌──────────────┐
│ profile.md    │──▶│  autocv.adapt      │◀──│ LinkedIn URL │
│ (full history)│   │  .workflow         │   │ or job text  │
└───────────────┘   └───────────────────┘   └──────────────┘
                              │
                              ▼
                    tailored.cvml.yaml ──render──▶ PDF (tailored CV)
```

## Known simplifications (v1)

- Font: the original PDF embeds a subsetted Source Sans Pro (only the glyphs
  used on the CV — unusable for arbitrary tailored text). The renderer uses
  Liberation Sans (metric-compatible with Arial, full glyph coverage, already
  installed), so layout and spacing match closely but glyph shapes are not
  identical. Swapping in a full Source Sans Pro/3 font file later is a
  one-line CSS change.
- The handwritten signature on page 2 of the original is decorative and not
  reproduced; nothing in CVML represents it.
- `LinkedInJobFetcher` does not authenticate; it extracts what an
  unauthenticated request returns. The CLI also accepts raw job text directly
  so a blocked fetch is never a hard stop.
- Gemini/Ollama backends, and their `CompanyResearcher` counterparts, are
  implemented and unit-tested, but the exercised end-to-end path in this
  iteration is Claude Code CLI, per the task's explicit priority.
- `OllamaCompanyResearcher` cannot search the web (no server-side search
  exists for a local model); it can only fetch a URL it already knows or
  guesses. Treat its research as best-effort.
- The renderer supports multiple templates (`--template`); only the
  original layout has been tuned pixel-for-pixel against the source PDF.
