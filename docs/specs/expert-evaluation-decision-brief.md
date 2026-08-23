# Artifact Design — Expert Evaluation Decision Brief

**Status:** approved · **Date:** 2026-08-24 · **Output:** `/expert_evaluation_decision_brief.html`
**Derived from:** ADR-004, ADR-008, `docs/capstone/methodology.md`,
`docs/capstone/research_instruments.md`, and the implemented pipeline

## 1. Purpose

Create one standalone, researcher-facing HTML brief that explains StoryBuddy's evaluation design,
assesses whether an exact questionnaire from prior research can validly be reused, documents the evidence
and limitations behind the recommendation, and includes a printable draft of Tool B. The draft instrument is
clearly marked **pending adviser and ethics approval** and does not change a frozen ADR.

Success means a researcher can answer five questions after reading it:

1. What does StoryBuddy's pipeline actually do?
2. What do Objectives 3, 4, and 5 measure, and why are they separate?
3. Why does copying an existing questionnaire exactly not automatically transfer validity?
4. Which prior sources can be reused, adapted, or only cited?
5. What should the research team approve and do next?

## 2. Binding methodological position

The artifact recommends **keeping Objective 3 as a written, open-ended expert-validation interview analysed
by directed content analysis**. CANVAS/ContinuityEval contributes continuity constructs and probe wording,
not the headline outcome metric. StoryBuddy must not use its runtime judge to score the pages that judge helped
select or regenerate.

The argument about an exact prior questionnaire is explicit:

- Validity belongs to the interpretation and intended use of evidence, not to a questionnaire title in the
  abstract. Exact copying is defensible only when the construct, evaluated object, respondent population,
  age/context, administration procedure, and score interpretation match.
- If those conditions do not match, unchanged wording can reduce validity. A content-valid adaptation with a
  documented source map is stronger than an exact but construct-invalid copy.
- A source may still provide authoritative criteria without being a validated questionnaire.
- Reuse permission and measurement validity are separate questions. A permissive license does not establish
  construct validity, and a valid instrument may still require copyright permission.

This position is anchored to the *Standards for Educational and Psychological Testing* and explained in plain
language. It is not presented as legal advice.

## 3. Evidence ledger and transfer-validity comparison

The HTML includes a source-status ledger with direct links and four labels: **exact-use candidate**,
**adaptable construct source**, **context-only source**, and **rejected for this purpose**.

### CANVAS / ContinuityEval

- **Verified source:** Mondal et al. (2026), *CANVAS: Continuity-Aware Narratives via Visual Agentic
  Storyboarding*, arXiv:2604.13452v1; OpenReview manuscript supplied by the owner.
- **What it is:** a VLM autorating framework for storyboard-frame transitions: face, clothing, hair/body,
  background, and prop continuity.
- **Evidence:** three visual-evaluation experts used the same rubrics; reported average Fleiss' kappa 0.74;
  reported human–VLM Pearson correlations 0.61–0.71.
- **Disclosure:** Appendix A.7 says 100 sampled transitions while Table 14 says 50. The brief presents this as
  an internal reporting inconsistency, not a resolved sample size.
- **Reuse:** the arXiv page declares CC BY 4.0. Prompt concepts may be attributed and adapted with a change
  notice; the artifact does not reproduce long copyrighted passages.
- **Decision:** adaptable construct source, not an exact Tool B questionnaire.

### Picture-book rating-scale study

- **Verified source:** Harrison and Neira-Piñeiro (2018), *Designing a picture-book rating scale for
  preschool education*, DOI 10.17398/1988-8430.27.81.
- **What the indexed abstract establishes:** action research with 46 Spanish preservice preschool teachers;
  participants collaboratively developed and applied a picture-book scale to improve their literary-mediator
  training.
- **What is not established by the accessible abstract:** psychometric validation for rating AI-generated
  books, Grade 5–6 outputs, character continuity, story faithfulness, or classroom deployment in the
  Philippines.
- **Access limitation:** the full item set could not be retrieved from the publisher/repository during the
  design review. The HTML must not claim item content or reproduce the scale until the primary full text and
  its reuse terms are inspected.
- **Decision:** relevant related research, but not a verified exact-use instrument.

### ALSC Caldecott criteria

- **Verified source:** official Association for Library Service to Children terms and criteria.
- **What it contributes:** authoritative picture-book artistic criteria and child-audience framing.
- **Limitation:** an award-selection framework, not a questionnaire with transferred psychometric validity.
- **Decision:** adaptable criteria source for visual presentation; do not call it a validated scale.

### LORI

- **Verified source:** Vargo et al. (2003), *Learning Object Evaluation: Computer-Mediated Collaboration and
  Inter-Rater Reliability*, DOI 10.1080/1206212X.2003.11441703.
- **What it contributes:** an example of a structured expert-review instrument with inter-rater evidence.
- **Limitation:** evaluates digital learning objects, not generated picture books or visual continuity.
- **Decision:** context-only; exact adoption would measure the wrong object.

### DreamBench++, ViStoryBench, and TIFA

- DreamBench++ supports subject-preservation and human-aligned identity-evaluation reasoning.
- ViStoryBench supports multi-frame story-visualization evaluation.
- TIFA supports decomposing prompt/image faithfulness into observable questions.
- None is represented as a complete, validated expert questionnaire for AI-generated children's picture
  books.

### ISO/IEC 25010

- This remains the exact standard family for Objective 5 software-quality evaluation.
- It is deliberately excluded from Objective 3 because software quality is not generated-book acceptability.

## 4. Information architecture

The page follows a decision-first sequence:

1. **Hero / decision:** Keep, Adapt, Do Not Adopt.
2. **The question researchers are really asking:** exact reuse versus valid use.
3. **Three evaluation legs:** Objective 3, 4, and 5 with non-circularity.
4. **Implemented pipeline:** request/worker context plus the eleven-node graph and per-scene loop.
5. **Evidence ledger:** source-by-source findings, verification status, and links.
6. **Transfer-validity test:** construct, object, respondents, context, administration, scoring, and license.
7. **CANVAS deep dive:** useful concepts, invalid transfers, formula and evidence limitations.
8. **Use / Adapt / Reject matrix.**
9. **Edge-case laboratory:** difficult cases and instrument handling rules.
10. **Recommended evaluation procedure.**
11. **Printable Tool B draft.**
12. **Researcher coding guide.**
13. **Approval gates and next actions.**
14. **References and evidence notes.**

## 5. Visual direction

The artifact is an editorial research field guide aligned with StoryBuddy's Cobalt Playroom palette but
visually quieter than the child-facing product:

- ivory paper ground, cobalt structure, navy ink;
- restrained amber for caution and crimson only for invalid claims or stop gates;
- large decision banner and numbered evidence path;
- CSS/HTML pipeline flow and evidence-to-decision map;
- comparison cards, annotated formulas, edge-case cards, and approval-gate timeline;
- sticky desktop contents, compact mobile navigation, and visible section anchors;
- print stylesheet for clean A4 output, with navigation and interaction controls removed;
- no gradients, external frameworks, remote fonts, images, or required network access.

Minimal JavaScript is permitted only for reading progress, table-of-contents highlighting, and optional
details expansion. The content remains available when JavaScript is disabled.

## 6. Pipeline representation

The diagram distinguishes manuscript modules from implementation:

`POST /storybooks → Supabase job → RQ worker → checkpointed LangGraph`

`input_gate → analyze → segment → char_bible → char_ref_mod → reveal → generate_scene →
consistency_check ↔ regenerate → output_mod → next scene / compose`

It states that:

- `StoryMemory` is the shared contract, not a graph node;
- style and prompt optimization are inputs, not standalone nodes;
- the current cap is ten scenes and three attempts per scene;
- output moderation occurs inside the scene loop;
- `compose` currently validates finalized pages but the graph has no export node;
- the runtime judge compares each page with canonical references and structured scene constraints, not with
  adjacent pages using PropCons.

## 7. Tool B draft

The printable appendix contains:

- **status banner:** Draft — do not administer before adviser and ethics approval;
- anonymous validator ID, role, book ID, date, and review duration;
- neutral instructions and definitions;
- five open-ended questions matching the accepted criteria exactly;
- optional non-scored prompts for recurring character, prop, setting, and style continuity;
- page/evidence fields so criticism can be traced;
- an overall improvement question;
- researcher-only coding sheet.

It contains no Likert scale, aggregate score, pass threshold, acceptance percentage, or PropCons formula.
The draft asks validators to describe evidence rather than agree with positive claims.

### Proposed questions

1. **Narrative coherence:** Which page transitions, if any, made the sequence of events difficult to follow?
   Identify the pages and explain why.
2. **Story faithfulness:** Which characters, actions, settings, or important objects, if any, contradict or
   omit details essential to the anonymized source story?
3. **Visual presentation:** Which aspects of illustration, composition, layout, caption legibility, or page
   balance help or hinder the book's presentation?
4. **Visual style consistency:** Across pages, what unexpected changes, if any, occur in recurring characters,
   props, settings, or drawing style? Ignore differences reasonably explained by pose, viewpoint, occlusion,
   lighting, or story-supported events.
5. **Classroom suitability:** What, if anything, makes the book unsuitable or difficult to use with Grade 5–6
   learners, and what should be improved?

Question 4's non-scored cue list uses StoryBuddy's inclusive axes: body plan/silhouette, face/interface,
colours/markings, distinctive body features, clothing/accessories, recurring props, and recurring locations.
Hair is an optional visible feature, never a required axis.

## 8. Coding and reporting rules

- The coding unit is a meaning unit, not the whole response.
- One passage may receive several criterion and orientation codes.
- Orientation is positive, negative, or suggestion; blank/unclear is recorded separately and is not negative.
- Every page-specific finding carries book/page identifiers.
- Counts are descriptive. Three validators do not justify population percentages or inferential claims.
- Representative excerpts remain anonymous and are selected to show both agreement and disagreement.
- A second researcher double-codes a predeclared subset, records disagreements, and resolves them using the
  codebook. The artifact recommends this transparency without inventing a reliability threshold.
- Arts-sector and Education-sector judgments remain attributable to their intended expertise; comments outside
  that scope are retained but labelled contextual.

## 9. Edge cases

Each edge-case card contains the risk, decision rule, and rationale:

- hairless, robotic, animal, vehicle, and personified-object characters;
- multiple characters and mistaken identity assignment;
- rear/profile/foreshortened/occluded views;
- intentional costume, body, or age changes supported by the story;
- props transferred, broken, transformed, consumed, or intentionally absent;
- zero visible props and PropCons division-by-zero;
- one-of-many surviving props yielding 100% under the smaller-set denominator;
- permanent setting drift versus legitimate weather, time, damage, or lighting changes;
- key story objects versus incidental decoration;
- source-story access for faithfulness without exposing PII;
- shuffled order, reviewer fatigue, missing responses, and page-versus-book scope;
- all-positive feedback, disagreement between disciplines, and no consensus.

## 10. Safety and research-integrity boundaries

- Validators receive only anonymized, redacted source stories and finished books.
- They do not see runtime judge scores, retry history, provider/model details, or internal provenance.
- The artifact never labels an unapproved Tool B as validated.
- It distinguishes factual verification, inference, recommendation, and unresolved question.
- Exact questionnaire reuse remains blocked until the complete primary instrument, validation population,
  scoring instructions, and reuse terms are verified.
- Numeric scoring, a new criterion, or a cross-frame runtime evaluator requires a separate ADR/design session.

## 11. Implementation boundaries

- Create one new root file: `expert_evaluation_decision_brief.html`.
- Update `tasks/todo.md` only for project tracking.
- Do not modify `research_strategy.html`, application code, contracts, ADRs, capstone methodology, or pipeline.
- Do not add dependencies, generated assets, or network-loaded resources.

## 12. Verification

The finished artifact must pass:

1. HTML parse and balanced-tag checks.
2. Unique IDs and valid internal navigation targets.
3. Link inventory with every external source labelled by verification status.
4. Text scans for prohibited claims: Tool B “validated,” CANVAS “questionnaire,” PropCons as the outcome,
   population percentages from three validators, and implemented export.
5. Responsive browser inspection at desktop and mobile widths.
6. Keyboard navigation, visible focus, reduced-motion, contrast, and JavaScript-disabled content checks.
7. Print preview inspection for A4 pagination and complete Tool B fields.
8. Repository diff and whitespace checks.

No application test suite is required because the artifact is standalone documentation, but browser and parser
verification are required before completion.

## 13. Sources to cite in the artifact

- Mondal et al. (2026), CANVAS: https://arxiv.org/abs/2604.13452
- CC BY 4.0: https://creativecommons.org/licenses/by/4.0/
- Harrison & Neira-Piñeiro (2018): https://doi.org/10.17398/1988-8430.27.81
- ALSC Caldecott terms and criteria: https://www.ala.org/alsc/awardsgrants/bookmedia/caldecott
- Vargo et al. (2003), LORI reliability study: https://doi.org/10.1080/1206212X.2003.11441703
- Standards for Educational and Psychological Testing: https://www.testingstandards.net/uploads/7/6/6/4/76643089/standards_2014edition.pdf
- Elo & Kyngäs (2008), qualitative content analysis: https://doi.org/10.1111/j.1365-2648.2007.04569.x
- DreamBench++: https://arxiv.org/abs/2406.16855
- ViStoryBench: https://arxiv.org/abs/2505.24862
- TIFA: https://arxiv.org/abs/2303.11897
