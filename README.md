# autocv

A CV kept as structured source (CVML), a renderer that turns it into a PDF,
and a CLI that uses an LLM to tailor that source to a specific job posting.

See `docs/DESIGN.md` for the system design, `docs/CVML_SPEC.md` for the CV
schema, and `docs/MASTER_PROFILE_SPEC.md` for the master profile format.

## Setup

```sh
uv sync
```

Rendering uses headless Chromium; if Playwright's bundled browser isn't
already on the machine, install it once:

```sh
uv run playwright install chromium
```

## Render a CV

```sh
uv run autocv render examples/johndoe.cvml.yaml -o cv.pdf
```

Add `--template compact` for a plain single-column, ATS-friendly layout
instead of the default two-column one (see
`src/autocv/render/templates/`).

## Tailor a CV to a job posting

Requires a master profile (`docs/MASTER_PROFILE_SPEC.md`) with the
applicant's full experience pool, and a base CVML file for identity
(name, contact, references, languages).

```sh
uv run autocv adapt \
  --profile examples/johndoe.profile.md \
  --base examples/johndoe.cvml.yaml \
  --job-url https://www.linkedin.com/jobs/view/... \
  --output tailored.cvml.yaml \
  --backend claude-code

uv run autocv render tailored.cvml.yaml -o tailored.pdf
```

`adapt` runs a small agentic workflow, not a single LLM call: it drafts a
CV, then researches the hiring company and fact-checks the draft against
the master profile in parallel, then an editorial pass reconciles both
before writing the final CVML. See "Adaptation workflow" in
`docs/DESIGN.md` for the shape of that pipeline.

If a LinkedIn job page can't be fetched without logging in, pass the
posting as text instead: `--job-text-file job.txt`.

`--backend` selects the LLM: `claude-code` (default, runs the local `claude`
CLI — no API key needed, just a working Claude Code login), `gemini`
(`--gemini-api-key`, or `GEMINI_API_KEY`), or `ollama` (`--ollama-base-url`,
default `http://localhost:11434/v1`).

## Development

```sh
uv run pytest
uv run mypy src
uv run ruff check src tests
```
