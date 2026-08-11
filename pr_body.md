This PR ships three pipeline hardening fixes along with their corresponding spec updates:

1. **Naming — analyze.py**: `analyze` now uses the name the story gives the character rather than placeholders (which are still forbidden). The comment block has been updated to clarify that we lean on `redact_pii` upstream rather than forcing relabeling at the LLM boundary.
2. **c1 draw prompt fix**: Fixed the "c1" prompt which was unconditionally asking for a full-body standing human. It now says "shown in full, facing forward", and adds an unconditional clause for non-humanoid characters ("If the character is not a person, draw it as the kind of thing it actually is — give it no human body...").
3. **Error posture — char_ref_mod**: `char_ref_mod` now mirrors `input_gate`. A primary error degrades to the backstop instead of failing the book, and a primary flag short-circuits the backstop.

Also included:
- Spec updates for all three changes (`character-bible.md`, `story-analyzer.md`, `moderation-stack.md`).
- ADR-033 clarification about `PostgresSaver` hardcoding `prepare_threshold=0`, preventing the use of connection pooling on 6543.
- Pre-existing drift fixes in documentation.
