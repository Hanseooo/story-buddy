# Objective-4 research runbook

> **Stop gate:** This runbook does not authorize donor contact, donated-story intake, generation, annotation
> or training. The consent/assent draft remains **DRAFT — DO NOT ADMINISTER** until its remaining blanks,
> retention schedule and Filipino/Tagalog translation are institutionally approved.

## Governance record before any donated intake

- [ ] Adviser approves the final study wording and operational process.
- [ ] HCDC/ethics approval covers consent, assent, retention, withdrawal and third-party processing.
- [ ] The participating school approves recruitment, contact and administration.
- [ ] The final consent/assent version, approval dates and approvers are recorded outside the dataset.
- [ ] The identity-to-receipt ledger is stored only in the ethics-approved restricted location outside
      StoryBuddy, its repository, Supabase research storage, logs, checkpoints and model artifacts.

## Sanitized intake and selection freeze

- [ ] Receive the source material through the approved process; do not place the raw submission, names,
      contacts or receipt code in the controlled JSON intake.
- [ ] Manually redact PII, then obtain an independent second-person redaction review before creating the
      donated `story_id` record.
- [ ] Record affirmative guardian consent, child assent, manual-redaction and independent-review approvals.
- [ ] Freeze 10 primary and 5 backup held-out candidates before generation or judge outcomes: five candidates
      per style; primaries are 4 Gouache, 3 Cel and 3 Cut-paper; backups are 1 Gouache, 2 Cel and 2 Cut-paper.
- [ ] Keep each candidate's frozen style and role outcome-blind. A replacement may fill only the same-style
      slot after withdrawal, unusable/de-identification failure, terminal pipeline failure or inadequate
      character yield under the recorded rule.
- [ ] After selection freeze, restrict changes to the controlled intake file and record every approved
      same-style replacement in the restricted study record. The loader validates the completed freeze timestamp
      and exact batch allocation, but the approved record shape cannot reconstruct whether a role or style was
      edited after that timestamp.

## Withdrawal and stop rules

- [ ] Locate a withdrawal only through the restricted receipt ledger; mark the sanitized record withdrawn and
      exclude its story, assets, labels and dataset records before freeze under the approved retention process.
- [ ] After freeze, exclude a withdrawal from future training and evaluation and disclose that an already
      trained model cannot selectively unlearn one example.
- [ ] Stop before spending or advancing if an approval is missing, redaction is uncertain, a candidate is
      withdrawn, the selection is not frozen, or the approved retention/translation wording is incomplete.

## Evidence to retain outside intake data

Record approval references, finalized consent/assent version, selection-freeze timestamp, withdrawal actions
and deviations in the restricted study record. The JSON intake contains only the validated de-identified
research fields accepted by `finetune.corpus_io`.
