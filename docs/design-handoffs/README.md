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

## The one rule that governs all of them

The user is a non-technical parent or grandparent. `docs/INSTALL-FOR-MOM.md` is
the register: no jargon, no assumed knowledge, every unavoidable technical term
explained on the spot. Words that are **banned** from user-facing copy:

> OAuth, token, authenticate, credentials, revoke, endpoint, API, session,
> cache, config, JSON, refresh token, PKCE

"Client ID" is the single permitted exception, because Yoto's own dashboard
calls it that and the user must match what they see there. It is always
introduced with an explanation, never used bare.
