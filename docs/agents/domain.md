# Domain docs

## Read before exploring

- Follow `AGENTS.md` and its Documentation Map.
- Read root `GLOSSARY.md` if it exists.
- Read `docs/product/ADRs.md` and relevant decisions in `docs/product/adr/`.
- For a feature, read its spec under `docs/specs/`.

## Layout and vocabulary

StoryBuddy uses one domain context.
Create root `GLOSSARY.md` when the first term is resolved.
Keep it limited to domain terminology, using the domain-modeling skill's format.
Use its canonical terms in tickets, proposals, and tests.
Proceed silently when the glossary does not exist.

## Decisions during /grill-with-docs

Use grilling to challenge assumptions and domain-modeling to record resolved terms.
Keep ADRs in `docs/product/adr/`, following the repository's naming convention,
with an index row in `docs/product/ADRs.md`.

Existing ADRs are frozen. Surface conflicts and follow AGENTS.md's acceptance
process for proposed changes. Log architectural questions encountered during
implementation in `docs/product/DECISION_BACKLOG.md`.
