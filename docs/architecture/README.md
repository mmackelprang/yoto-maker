# Architecture

**System overview lives in [`../DESIGN.md`](../DESIGN.md).** That document is the
approved description of what Yoto Maker is, its module layout, and its data flow.
It is the thing to read first, and the thing to update when a shipped change makes
it untrue.

This directory holds the decisions that shape it.

## `decisions/` — architecture decision records

One file per decision, named `YYYY-MM-DD-<topic>.md`.

An ADR is written when a choice **spans more than one PR** or **constrains future
work**: a data model, an endpoint contract, a cross-cutting abstraction, a
service boundary, a performance or security trade-off. Single-PR feature work does
not get one — the plan under `docs/superpowers/plans/` is its record.

Each ADR carries the same sections:

| Section | What it holds |
| --- | --- |
| **Status** | `proposed` / `accepted` / `superseded by <file>` |
| **Context** | What is true today, measured where possible |
| **Options considered** | The real alternatives, including doing nothing |
| **Decision** | One recommendation, named and defended |
| **Consequences** | Good *and* bad. The bad half is the reason the file exists. |
| **Related** | Specs, plans, handoffs and other ADRs this touches |
| **Open questions** | What is still undecided, and who decides it |

An accepted ADR is not relitigated without explicit direction. If a new request
conflicts with one, surface the conflict rather than quietly overriding it.

## Index

| Date | Decision | Status |
| --- | --- | --- |
| 2026-07-21 | [Move `/api/tracks/file` onto the background job system](decisions/2026-07-21-file-upload-on-job-system.md) | proposed |
| 2026-07-21 | ["Repair my cards": fix declared track metadata on existing MYO cards](decisions/2026-07-21-repair-existing-cards.md) | proposed |
</content>
</invoke>
