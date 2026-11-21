# ADR-084 — The study corpus is English-only, and non-English stories are translated before use

**Status:** Accepted (2026-11-22) · the owner decided it in the SDLC grill session · narrows the
population line of `research_direction_and_goals.md` §4.1 and §6, `methodology.md` §4.1 and
`RESEARCH_PROTOCOL.md` §8 and §11 · does not edit ADR-011 · no code, route, migration or
`StoryMemory` change

## Context

The scope read "English with Taglish code-switching tolerated". Nothing in the repository measures
how well the pipeline's models handle Filipino or Taglish. Probe 4, the planned test of the text
moderation on Filipino and Taglish stories (`PHASE_05_RESULTS.md`, `ROADMAP.md`), has not run, and
no test of the story analyzer or the judge on Taglish exists.

Some donated stories were not in English, and the research team translated them into English before
they were generated into books (owner, 2026-11-22). Which stories, how many, and whether a second
person checked each translation were not recorded, and the owner judged reconstructing it not worth
the time.

## Decision

1. **The study corpus is English-only.** The population is Grade 5–6 (ages 10–12), Philippines,
   English. English is the medium of instruction from Grade 4 (DepEd), which the scope already cites.
   Filipino and Taglish join the deferred languages.
2. **A donated story not written in English is translated into English by the research team before
   use.** The translated text is the generation input and the text Objective 3's experts compare the
   book against.
3. **The translations are disclosed, not hidden.** Some donated stories were translated; the count,
   the story IDs and any second-person check are not recorded. This is reported as a limitation: a
   translated story is the child's story in the team's words, so faithfulness is measured against
   the translation, not the original.
4. **The product does not change.** StoryBuddy still sends a child's text as written and never
   translates it (magic pencil OD-06). The Filipino PII recognizers stay, because Filipino names and
   addresses appear in English stories too.
5. **Probe 4 stays open, as a gate before ethics Stage 2.** When children type into the system they
   may still write Filipino or Taglish, so the moderation risk ADR-011 names still holds for real
   use. It does not apply to the study corpus, which is English by decision 1.
6. **ADR-011 and earlier ADRs are not edited.** They record what was decided at the time.

## Consequences

- The scope no longer claims Taglish tolerance that nothing measured.
- The paper's population and limitations text must say English-only and disclose the translations.
  The paper is edited by the team, outside this change.
- An untranslated original, if kept, is not used anywhere in the study.
- Not recorded, and not reconstructed: which stories were translated, and whether the Stage-1 consent
  wording covers translation. Ask the adviser about the consent question before the defense.
