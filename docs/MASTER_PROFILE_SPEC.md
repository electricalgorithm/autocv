# Master Profile

The master profile is the applicant's full experience pool — every role,
project, and publication they could put on a CV, with more detail than any
single CV needs. The adapter (`autocv adapt`) selects and rephrases from this
file when tailoring a CV to a job posting; it never invents facts beyond it.

File extension: `.profile.md`. Markdown, not YAML: this file is prose-heavy
and hand-maintained, so it optimizes for the applicant editing it directly.

Person and contact details are not part of the master profile — they live in
a base CVML file (`--base` on the CLI) and are carried through unchanged.

## Grammar

```markdown
## Experience

### Software Engineer
- Organization: Example Corp
- Organization URL: https://example.com        (optional)
- Location: Berlin, Germany
- Start: 2023-01
- End: present
- Keywords: Python, Kubernetes                  (optional, comma-separated)

Achievements:
- Cut deploy time from 40 minutes to 6 by moving CI to buildkite.
- Led the migration of the billing service to Kubernetes.

## Education

### BEng. Computer Engineering
- Institution: Example University
- Institution URL: https://example.edu          (optional)
- Location: Berlin, Germany
- Start: 2018-09
- End: 2022-07
- Detail: First-class honours.                  (optional)

## Skills

- Python
- Kubernetes
- Team leadership

## Certifications

- Certified Kubernetes Administrator

## Publications

### Paper Title
- Venue: Conference or Journal Name
- Date: 2024-01
- URL: https://example.com/paper                (optional)

## Projects

### Project Name
- Categories: Web, Embedded                     (optional, comma-separated)
- Stack: Python, MQTT                            (optional, comma-separated)
- URL: https://github.com/example                (optional)
- Detail: 100+ stars on GitHub                   (optional)

Achievements:
- Built a broker-enforced schema layer for MQTT topics.
```

## Rules

- Top-level sections are `## Experience`, `## Education`, `## Skills`,
  `## Certifications`, `## Publications`, `## Projects`. All are optional;
  omit a section that doesn't apply.
- `Experience` and `Publications` and `Projects` entries are `### `
  headings followed by `- Key: value` metadata lines, optionally followed
  by an `Achievements:` line and a bullet list. `Education` entries have no
  achievements list.
- `Skills` and `Certifications` are flat bullet lists, no entry headings.
- Metadata keys are case-insensitive and map to the field of the same name
  (spaces become underscores): `Organization URL` → `organization_url`.
- `Start`/`End`/`Date` are `YYYY-MM`; `End` also accepts `present`.
- Achievements are the raw material the adapter draws on to write each CVML
  `experience[].highlights` bullet and to choose project `categories`. Write
  them as finished CV bullets: as many, as specific, and as quantified as
  possible. The adapter trims and merges them rather than rewriting, so
  wording here is what ends up on the page. More detail here means a
  better-targeted CV later, not a longer one.
