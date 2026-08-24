# CVML — CV Markup Language

A CVML document is a YAML file validated against the schema in
`autocv.markup.models`. That module is the source of truth; this document is
a human-readable summary of it, plus the conventions the LLM adapter must
follow.

File extension: `.cvml.yaml`.

## Top-level shape

```yaml
person:
  name: Full Name
  headline: Software Engineer          # role/title shown under the name
  photo: assets/photo.jpg              # optional, path relative to the CVML file
  birth_date: 2001-11-02               # optional, ISO date
  citizenships: [Bulgarian, Turkish]   # optional
  work_authorization: full working permission in Germany   # optional, free text

contact:
  email: hello@example.com
  phone: "+49 162 3348183"
  location: Dresden, Germany
  linkedin: gokhankocmarli              # username only, no URL
  github: electricalgorithm             # username only, no URL
  website: example.com                  # optional
  scholar: https://scholar.google.com/citations?user=... # optional, full URL

summary: >
  One paragraph, first person, no line breaks required in the source —
  YAML folds a `>` block into a single paragraph.

experience:
  - title: Software Engineer
    organization: Example Corp
    organization_url: https://example.com     # optional
    location: Berlin, Germany
    start: "2023-07"                    # YYYY-MM
    end: present                        # YYYY-MM, or the literal "present"
    summary: What the role covered, one paragraph.   # optional if highlights given
    highlights:                         # optional bullet list, rendered under summary
      - Shipped X, cutting Y by 30%.
    keywords: [Python, Kubernetes]      # shown as an italic tag line

education:
  - degree: BEng. Computer Engineering
    institution: Example University
    institution_url: https://example.edu       # optional
    location: City, Country
    start: "2020-09"
    end: "2024-07"
    detail: High-honours degree, 3.8/4.0 GPA.   # optional

skills:
  - Client/Customer Relations
  - AWS Serverless (EC2, S3, Lambda, IAM, CF)

certifications:
  - AWS Certified Solutions Architect

publications:
  - title: Paper Title
    venue: Conference or Journal Name
    date: "2026-03"                     # YYYY-MM
    url: https://example.com/paper      # optional

projects:
  - title: Project Name
    categories: [Embedded, Web]         # shown as a left-column tag list
    detail: 31+ stars on GitHub         # optional
    stack: [Zig, MQTT]
    url: https://github.com/example     # optional

references:
  - name: Reference Name
    title: Their Job Title
    organization: Their Company
    email: reference@example.com

languages:
  - name: English
    level: Professional
```

## Rules

- Every field not marked optional above is required.
- `experience[].start`, `experience[].end` (unless `present`), `education[].start`,
  `education[].end`, `publications[].date` all match `YYYY-MM`.
- `person.birth_date` is a full ISO date (`YYYY-MM-DD`).
- Unknown top-level or nested fields are rejected — the schema is closed, so a
  malformed LLM response fails validation immediately instead of silently
  dropping data at render time.
- List fields (`experience`, `education`, `skills`, `certifications`,
  `publications`, `projects`, `references`, `languages`) default to empty if
  omitted.

## Rule for LLM-generated CVML

The adapter must only restate facts present in the applicant's master profile
(`docs/MASTER_PROFILE_SPEC.md`). It may re-order, re-phrase, select a subset
of entries, and choose which `keywords`/`skills`/`stack` to surface — it must
never invent an employer, title, date, metric, or credential that is not in
the master profile.
