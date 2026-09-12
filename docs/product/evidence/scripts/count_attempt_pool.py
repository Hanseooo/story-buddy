"""Count the harvestable rejected-attempt pool in the existing corpus bundles.

Evidence for ADR-060. Costs USD 0: reads committed `memory.json` files only, makes no
provider call and no database write. Re-runnable from its committed location:

    uv run python docs/product/evidence/scripts/count_attempt_pool.py

A "reject" is an attempt on a finalized scene whose `image_ref` is not the scene's
`final_image_ref`. That is the definition `pairs_from_memory` would harvest under ADR-060,
and it is NOT the same as `len(attempts) - 1` read off the filename suffix: the pipeline
finalizes on the best-ranked attempt once ADR-037's cap is reached, so the final is
frequently not the last attempt and sometimes never passed at all.
"""

import collections
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[4]
BUNDLES = sorted((ROOT / "data" / "judge").glob("corpus-*"))


def main() -> None:
    scenes = rejects = finals = 0
    unfinalized_scenes = unfinalized_attempts = 0
    final_never_passed = 0
    reason_counts: collections.Counter[str] = collections.Counter()
    attempts_total = 0
    passed_with_reasons = 0

    for bundle in BUNDLES:
        for memory_path in sorted(bundle.glob("runs/*/memory.json")):
            memory = json.loads(memory_path.read_text(encoding="utf-8"))
            for scene in memory.get("scenes") or []:
                attempts = scene.get("attempts") or []
                final_ref = scene.get("final_image_ref")

                if not final_ref:
                    unfinalized_scenes += 1
                    unfinalized_attempts += len(attempts)
                    continue

                scenes += 1
                finals += 1
                final_attempt = next(
                    (a for a in attempts if a.get("image_ref") == final_ref), None
                )
                if final_attempt is not None and not final_attempt.get("passed"):
                    final_never_passed += 1

                for attempt in attempts:
                    attempts_total += 1
                    if attempt.get("passed") and (attempt.get("failure_reasons") or []):
                        passed_with_reasons += 1
                    if attempt.get("image_ref") == final_ref:
                        continue
                    rejects += 1
                    for reason in attempt.get("failure_reasons") or []:
                        reason_counts[reason] += 1

    print(f"bundles read                 : {len(BUNDLES)}")
    print(f"finalized scenes             : {scenes}")
    print(f"final images (in bundle now) : {finals}")
    print(f"harvestable rejects          : {rejects}")
    print(f"rejects per finalized scene  : {rejects / scenes:.2f}" if scenes else "")
    print(f"scene-image pool multiplier  : {(finals + rejects) / finals:.2f}x" if finals else "")
    print()
    print(f"unfinalized scenes (skipped) : {unfinalized_scenes} "
          f"holding {unfinalized_attempts} attempts")
    print(f"finals that never passed     : {final_never_passed} / {finals}")
    print(f"attempts passed=True but carrying failure_reasons: "
          f"{passed_with_reasons} / {attempts_total}")
    print()
    print("failure_reasons across harvestable rejects (an attempt may carry several):")
    for reason, count in reason_counts.most_common():
        print(f"  {reason:<20} {count:>4}  ({count / rejects:.0%} of rejects)")


if __name__ == "__main__":
    main()
