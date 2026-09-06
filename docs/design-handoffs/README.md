# Design handoffs

Canonical UX specs for Yoto Maker surfaces. Each package is a directory named
after the surface, containing:

| File               | Contents                                                        |
| ------------------ | --------------------------------------------------------------- |
| `overview.md`      | What it is, who uses it, placement decision, the component spec  |
| `interactions.md`  | State machines, focus, keyboard, responsive behavior             |
| `copy.md`          | Every user-visible string, verbatim                              |
| `tokens.md`        | New CSS tokens/utilities introduced, with justification          |
| `mockups/`         | Visual references (ASCII where no rendered mockup exists)        |

Every package declares, at the top of `overview.md`, whether it **follows**,
**extends**, or **deviates from** the packages that came before it. `deviates`
requires explicit direction from Mark plus written rationale.

## Packages

| Surface                                             | Status   | Date       |
| --------------------------------------------------- | -------- | ---------- |
| [`configuration-surface/`](configuration-surface/)   | Shipped  | 2026-07-20 |
| [`export-only-mode/`](export-only-mode/)             | Proposed | 2026-09-05 |

`export-only-mode/` has **no `tokens.md`**, deliberately: it introduces no CSS
and no tokens. Per the configuration surface's own §13, that absence is the
strongest available evidence an extension fits the existing primitives rather
than straining them.

## The one rule that governs all of them

The user is a non-technical parent or grandparent. `docs/INSTALL-FOR-MOM.md` is
the register: no jargon, no assumed knowledge, every unavoidable technical term
explained on the spot. Words that are **banned** from user-facing copy:

> OAuth, token, authenticate, credentials, revoke, endpoint, API, session,
> cache, config, JSON, refresh token, PKCE, export, directory, path, file
> format, codec, transcode, MP3 encoding, metadata

The list grows as packages find more of it. `export-only-mode/` adds the last
eight — **export**, **directory**, **path**, **file format**, **codec**,
**transcode**, **MP3 encoding** and **metadata** — and adds no exception to the
list in return: there, the verb is *save*, the noun is *files*, and the
destination is *a folder*. (`MP3` on its own is permitted and used: it is the
name of a thing she can see in her own file names, not a concept she has to
understand.)

"Client ID" is the single permitted exception, because Yoto's own dashboard
calls it that and the user must match what they see there. It is always
introduced with an explanation, never used bare.
