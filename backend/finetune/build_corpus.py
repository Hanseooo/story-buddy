"""Turn `corpus_synthetic.json` into immutable judge-training corpus bundles.

Runs the existing Phase-1 graph over each sanitized intake record. Completed results are persisted
under `data/judge/runs/<story_id>/` with their validated Story Memory and hashed local assets;
the legacy count-only state file is never trusted as completion. `--fixture` exercises that same
bundle path using generated local image bytes, without a graph, provider, database, or Storage call.
"""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from typing import Literal

from langgraph.types import Command
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError

from app.config import IMAGE_BUDGET, RECURSION_LIMIT, STYLE_PRESETS, settings
from app.length import word_count
from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Character,
    CharacterDescription,
    Cost,
    Input,
    Scene,
    Style,
    StoryMemory,
)
from finetune.corpus_io import (
    AssetRecord,
    CorpusError,
    IntakeRecord,
    RunBundle,
    intake_sha256,
    load_completed_bundles,
    load_intake,
    reconcile_declared_roster,
    write_bundle,
)
from finetune.manifest import local_image_path
from pipeline.analyze import EXTRACTION_PROMPT_VERSION
from pipeline.char_bible import JUDGE_PROMPT_VERSION as REFERENCE_JUDGE_PROMPT_VERSION
from pipeline.consistency_check import (
    JUDGE_PROMPT_VERSION,
    SCENE_CONSTRAINT_PROMPT_VERSION,
)
from pipeline.prompt_optimizer import SCENE_PROMPT_VERSION
from providers import _fal_event_sink

CORPUS_PATH = pathlib.Path(__file__).with_name("corpus_synthetic.json")
# `backend/finetune/build_corpus.py` -> repo root -> `data/judge/` (gitignored).
DATA_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "judge"
STATE_FILE = "build_state.json"
BUCKET = "storybook-images"
# The reveal can interrupt once per book and retry taps are cap-bounded; this is production's
# existing resume ceiling, unchanged by fixture mode.
MAX_RESUMES = 4
CONFIRM = {"action": "confirm"}
TELEMETRY_KEYS = ("attempted", "completed", "failed", "uncertain")


def _code_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=pathlib.Path(__file__).resolve().parents[2],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@dataclass(frozen=True)
class SpendPolicy:
    max_usd: Decimal = Decimal("25.00")
    hard_usd: Decimal = Decimal("30.00")
    smoke_usd: Decimal = Decimal("1.50")
    conservative_call_usd: Decimal = Decimal("0.035")

    def __post_init__(self) -> None:
        if self.max_usd < 0 or self.hard_usd <= 0 or self.smoke_usd < 0:
            raise ValueError("spend limits must be non-negative and hard_usd must be positive")
        if self.conservative_call_usd <= 0:
            raise ValueError("conservative_call_usd must be positive")

    @property
    def authorized_usd(self) -> Decimal:
        return min(self.max_usd, self.hard_usd)

    def story_draw_limit(self, story_count: int) -> int:
        if story_count <= 0:
            return 0
        if self.authorized_usd <= self.smoke_usd:
            return int(self.authorized_usd / self.conservative_call_usd) // story_count
        return IMAGE_BUDGET


def load_corpus(path: pathlib.Path = CORPUS_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _record(story: IntakeRecord | dict) -> IntakeRecord:
    return story if isinstance(story, IntakeRecord) else IntakeRecord.model_validate(story)


def _image_count(values: dict | None) -> int:
    cost = (values or {}).get("cost")
    return getattr(cost, "image_count", 0) if cost is not None else 0


def _initial_state(story: IntakeRecord) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id=story.story_id,
        classroom_id="judge-corpus",
        profile_id="judge-corpus",
        input=Input(raw_text=story.text, word_count=word_count(story.text), truncated=False),
        style=Style(
            style_preset_id=story.style_preset_id,
            prompt_fragment=STYLE_PRESETS[story.style_preset_id],
        ),
    )


class StoryBudgetStopped(Exception):
    pass


@dataclass(frozen=True)
class StoryRun:
    values: dict
    image_count: int
    outcome: Literal["completed", "budget_stopped", "quarantined"]
    reason: str | None = None


def run_story(app_graph, story: IntakeRecord) -> StoryRun:
    config = {"configurable": {"thread_id": story.story_id}, "recursion_limit": RECURSION_LIMIT}
    graph_input = _initial_state(story)
    values: dict = {}
    for _ in range(MAX_RESUMES + 1):
        interrupted = False
        try:
            for chunk in app_graph.stream(graph_input, config, stream_mode=["updates", "values"]):
                mode, payload = chunk[-2:]
                if mode == "values":
                    values = payload
                elif "__interrupt__" in payload:
                    interrupted = True
        except StoryBudgetStopped:
            return StoryRun(values, _image_count(values), "budget_stopped", "budget_stopped")
        if not interrupted:
            return StoryRun(values, _image_count(values), "completed")
        graph_input = Command(resume=CONFIRM)
    return StoryRun(values, _image_count(values), "quarantined", "resume_exhausted")


def _image_details(contents: bytes, expected_mime: str | None = None) -> tuple[str, int, int]:
    if contents.startswith(b"\x89PNG\r\n\x1a\n"):
        mime_type = "image/png"
    elif contents.startswith(b"RIFF") and contents[8:12] == b"WEBP":
        mime_type = "image/webp"
    else:
        raise CorpusError("invalid image magic bytes")
    if expected_mime is not None and mime_type != expected_mime:
        raise CorpusError(f"invalid image MIME: expected {expected_mime}, got {mime_type}")
    try:
        with Image.open(BytesIO(contents)) as image:
            image.load()
            return mime_type, image.width, image.height
    except (OSError, UnidentifiedImageError) as error:
        raise CorpusError("invalid image payload") from error


def _webp_bytes(contents: bytes) -> bytes:
    try:
        with Image.open(BytesIO(contents)) as image:
            image.load()
            output = BytesIO()
            image.save(output, format="WEBP", quality=82)
            return output.getvalue()
    except (OSError, UnidentifiedImageError) as error:
        raise CorpusError("invalid image payload") from error


def _value_attr(value, key):
    return getattr(value, key) if hasattr(value, key) else value.get(key)


def download_images(values: dict | StoryMemory, out_dir: pathlib.Path, supabase) -> tuple[int, int]:
    """Download references as PNG and encode each scene exactly once as WebP quality 82."""
    counts = {"ref": 0, "scene": 0}
    targets = [
        ("ref", _value_attr(character, "canonical_ref_image"))
        for character in _value_attr(values, "characters") or []
        if _value_attr(character, "canonical_ref_image")
    ]
    targets += [
        ("scene", _value_attr(scene, "final_image_ref"))
        for scene in _value_attr(values, "scenes") or []
        if _value_attr(scene, "final_image_ref")
    ]
    for kind, storage_path in targets:
        local = pathlib.Path(local_image_path(storage_path, kind, root=out_dir))
        counts[kind] += 1
        expected_mime = "image/png" if kind == "ref" else "image/webp"
        if local.exists():
            _image_details(local.read_bytes(), expected_mime)
            continue
        contents = supabase.storage.from_(BUCKET).download(storage_path)
        if kind == "scene":
            contents = _webp_bytes(contents)
        _image_details(contents, expected_mime)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(contents)
    return counts["ref"], counts["scene"]


def _asset(storage_path: str, kind: str, out_dir: pathlib.Path) -> AssetRecord:
    local = pathlib.Path(local_image_path(storage_path, kind, root=out_dir))
    if not local.is_file():
        raise CorpusError(f"missing completed asset: {local}")
    contents = local.read_bytes()
    mime_type, width, height = _image_details(contents, "image/png" if kind == "ref" else "image/webp")
    return AssetRecord(
        storage_path=storage_path,
        local_path=local.relative_to(out_dir).as_posix(),
        sha256=hashlib.sha256(contents).hexdigest(),
        mime_type=mime_type,
        width=width,
        height=height,
        byte_length=len(contents),
        kind=kind,
    )


def _assets(memory: StoryMemory, out_dir: pathlib.Path) -> list[AssetRecord]:
    paths = [("ref", character.canonical_ref_image) for character in memory.characters]
    paths += [("scene", scene.final_image_ref) for scene in memory.scenes]
    assets = [_asset(path, kind, out_dir) for kind, path in paths if path]
    if len({asset.storage_path for asset in assets}) != len(assets):
        raise CorpusError("completed assets contain duplicate storage paths")
    return assets


def _verify_bundle_assets(bundle: RunBundle, out_dir: pathlib.Path) -> None:
    for asset in bundle.assets:
        try:
            actual = _asset(asset.storage_path, asset.kind, out_dir)
        except CorpusError as error:
            raise CorpusError(f"immutable bundle asset differs: {bundle.memory.story_id}") from error
        if actual != asset:
            raise CorpusError(f"immutable bundle asset differs: {bundle.memory.story_id}")


def _reconcile_roster(story: IntakeRecord, memory: StoryMemory) -> None:
    reconcile_declared_roster(story.declared_characters, story.declared_non_human, memory)


def _fixture_memory(story: IntakeRecord) -> StoryMemory:
    characters = [
        Character(
            char_id=f"c{index}",
            name=name,
            description=CharacterDescription(is_humanoid=name not in story.declared_non_human),
            canonical_ref_image=f"{story.story_id}/ref-c{index}.png",
        )
        for index, name in enumerate(story.declared_characters, start=1)
    ]
    return _initial_state(story).model_copy(
        update={
            "characters": characters,
            "scenes": [
                Scene(
                    scene_id="fixture-scene-1",
                    text_excerpt=story.text,
                    characters_present=[character.char_id for character in characters],
                    final_image_ref=f"{story.story_id}/fixture-scene-1.png",
                )
            ],
            "cost": Cost(),
        }
    )


def _write_fixture_images(memory: StoryMemory, out_dir: pathlib.Path) -> None:
    for character in memory.characters:
        local = pathlib.Path(local_image_path(character.canonical_ref_image, "ref", root=out_dir))
        if not local.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (2, 2), "purple").save(local, format="PNG")
    for scene in memory.scenes:
        local = pathlib.Path(local_image_path(scene.final_image_ref, "scene", root=out_dir))
        if not local.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (2, 2), "purple").save(local, format="WEBP", quality=82)


def _bundle(
    story: IntakeRecord,
    memory: StoryMemory,
    out_dir: pathlib.Path,
    fixture: bool,
    telemetry: Counter | None = None,
    price_per_call: Decimal = Decimal("0.035"),
    billing_acknowledged_at: str | None = None,
) -> RunBundle:
    if memory.story_id != story.story_id:
        raise CorpusError(f"completed story_id differs from intake: {story.story_id}")
    if memory.style.style_preset_id != story.style_preset_id:
        raise CorpusError(f"completed style differs from intake: {story.story_id}")
    _reconcile_roster(story, memory)
    return RunBundle(
        memory=memory,
        provenance=story.provenance,
        split=story.split,
        candidate_role=story.candidate_role,
        declared_characters=story.declared_characters,
        declared_non_human=story.declared_non_human,
        run_metadata={
            "code_commit": _code_commit(),
            "schema_version": memory.schema_version,
            "intake_sha256": intake_sha256(story),
            "style_preset_id": story.style_preset_id,
            "text_model": settings.text_model,
            "image_model": settings.fal_image_model,
            "image_edit_model": settings.fal_image_edit_model,
            "judge_model": settings.vlm_judge_model,
            "moderation_primary_model": settings.moderation_primary_model,
            "moderation_primary_image_model": settings.moderation_primary_image_model,
            "moderation_backstop_model": settings.moderation_backstop_model,
            "moderation_backstop_image_model": settings.moderation_backstop_image_model,
            "extraction_prompt_version": EXTRACTION_PROMPT_VERSION,
            "reference_judge_prompt_version": REFERENCE_JUDGE_PROMPT_VERSION,
            "scene_prompt_version": SCENE_PROMPT_VERSION,
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
            "scene_constraint_prompt_version": SCENE_CONSTRAINT_PROMPT_VERSION,
            "image_budget": IMAGE_BUDGET,
            "recursion_limit": RECURSION_LIMIT,
            "fixture": "true" if fixture else "false",
            "conservative_call_usd": str(price_per_call),
            "attempted_calls": (telemetry or {}).get("attempted", 0),
            "completed_calls": (telemetry or {}).get("completed", 0),
            "failed_calls": (telemetry or {}).get("failed", 0),
            "uncertain_calls": (telemetry or {}).get("uncertain", 0),
            **(
                {"billing_acknowledged_at": billing_acknowledged_at}
                if billing_acknowledged_at is not None
                else {}
            ),
        },
        assets=_assets(memory, out_dir),
    )


def _write_state(path: pathlib.Path, state: dict) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _persisted_telemetry(values: dict, policy: SpendPolicy, source: str) -> Counter:
    try:
        price = Decimal(str(values["conservative_call_usd"]))
        stored = values.get("telemetry")
        telemetry = Counter(
            {
                key: stored[key] if stored is not None else values[f"{key}_calls"]
                for key in TELEMETRY_KEYS
            }
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise CorpusError(f"invalid persisted billing telemetry: {source}") from error
    if price != policy.conservative_call_usd or any(
        type(telemetry[key]) is not int or telemetry[key] < 0 for key in TELEMETRY_KEYS
    ):
        raise CorpusError(f"invalid persisted billing telemetry: {source}")
    terminal_calls = sum(telemetry[key] for key in ("completed", "failed", "uncertain"))
    if terminal_calls > telemetry["attempted"]:
        raise CorpusError(f"invalid persisted billing telemetry: {source}")
    return telemetry


RECOVERABLE_REASONS = {"budget_stopped", "resume_exhausted", "billing_uncertain"}


def _validated_checkpoint(app_graph, story: IntakeRecord) -> StoryMemory:
    snapshot = app_graph.get_state({"configurable": {"thread_id": story.story_id}})
    try:
        checkpoint = StoryMemory.model_validate(snapshot.values)
    except (AttributeError, ValidationError) as error:
        raise CorpusError(f"checkpoint is not resumable: {story.story_id}") from error
    if (
        checkpoint.story_id != story.story_id
        or checkpoint.input.raw_text != story.text
        or checkpoint.style.style_preset_id != story.style_preset_id
    ):
        raise CorpusError(f"checkpoint does not match intake: {story.story_id}")
    return checkpoint


def _validate_recovery(
    app_graph,
    story: IntakeRecord,
    state_entry: dict,
    resume_quarantined: str | None,
    acknowledge_uncertain_billing: str | None,
) -> str | None:
    reason = state_entry.get("reason_code")
    if resume_quarantined != story.story_id or reason not in RECOVERABLE_REASONS:
        raise CorpusError(f"{state_entry['quarantined']} for {story.story_id}")
    if state_entry.get("intake_sha256") != intake_sha256(story):
        raise CorpusError(f"intake digest differs for quarantined story: {story.story_id}")
    if reason == "billing_uncertain" and acknowledge_uncertain_billing != story.story_id:
        raise CorpusError(f"acknowledge uncertain billing before retry: {story.story_id}")
    _validated_checkpoint(app_graph, story)
    return (
        datetime.now(timezone.utc).isoformat()
        if reason == "billing_uncertain"
        else state_entry.get("billing_acknowledged_at")
    )


def _quarantine(
    state: dict,
    state_path: pathlib.Path,
    story: IntakeRecord,
    reason_code: str,
    message: str,
    telemetry: Counter,
    policy: SpendPolicy,
) -> None:
    previous = state.get(story.story_id, {})
    state[story.story_id] = {
        "quarantined": message,
        "reason_code": reason_code,
        "intake_sha256": intake_sha256(story),
        "conservative_call_usd": str(policy.conservative_call_usd),
        "telemetry": dict(telemetry),
        **(
            {"billing_acknowledged_at": previous["billing_acknowledged_at"]}
            if isinstance(previous, dict) and "billing_acknowledged_at" in previous
            else {}
        ),
    }
    _write_state(state_path, state)


def build(
    stories: list[IntakeRecord | dict],
    app_graph,
    out_dir: pathlib.Path,
    supabase,
    fixture: bool = False,
    policy: SpendPolicy = SpendPolicy(),
    resume_quarantined: str | None = None,
    acknowledge_uncertain_billing: str | None = None,
) -> dict:
    """Run only incomplete stories; a completed run is the immutable bundle, never a count."""
    records = [_record(story) for story in stories]
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = out_dir / STATE_FILE
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    bundles = {bundle.memory.story_id: bundle for bundle in load_completed_bundles(out_dir)}
    campaign_spent = sum(bundle.memory.cost.image_count for bundle in bundles.values())
    invocation_spent = 0
    telemetry = Counter(attempted=0, completed=0, failed=0, uncertain=0)
    if not fixture:
        for story_id, bundle in bundles.items():
            telemetry.update(_persisted_telemetry(bundle.run_metadata, policy, story_id))
        for story_id, entry in state.items():
            if story_id not in bundles and isinstance(entry, dict) and "telemetry" in entry:
                telemetry.update(_persisted_telemetry(entry, policy, story_id))
    story_draw_limit = policy.story_draw_limit(len(records))
    summary = {
        "stories_run": 0,
        "stories_skipped": 0,
        "characters": 0,
        "scenes": 0,
        "images_spent": 0,
        "halted": False,
    }
    for story in records:
        story_id = story.story_id
        state_entry = state.get(story_id)
        expected_reference = {"bundle": f"runs/{story_id}"}
        billing_acknowledged_at = None
        if state_entry is not None and state_entry != expected_reference:
            if not isinstance(state_entry, dict) or "telemetry" not in state_entry:
                state[story_id] = {"quarantined": "legacy count-only state; completed bundle required"}
                _write_state(state_path, state)
                raise CorpusError(
                    f"legacy build state quarantined for {story_id}; completed bundle required"
                )
            if "quarantined" in state_entry:
                if fixture:
                    raise CorpusError(f"{state_entry['quarantined']} for {story_id}")
                billing_acknowledged_at = _validate_recovery(
                    app_graph,
                    story,
                    state_entry,
                    resume_quarantined,
                    acknowledge_uncertain_billing,
                )
                if billing_acknowledged_at is not None:
                    state_entry["billing_acknowledged_at"] = billing_acknowledged_at
                    _write_state(state_path, state)
            else:
                state_telemetry = _persisted_telemetry(state_entry, policy, story_id)
                if state_entry.get("intake_sha256") != intake_sha256(story):
                    _quarantine(
                        state,
                        state_path,
                        story,
                        "intake_mismatch",
                        "intake digest differs from in-progress state",
                        state_telemetry,
                        policy,
                    )
                    raise CorpusError(f"intake digest differs for in-progress story: {story_id}")
                try:
                    _validated_checkpoint(app_graph, story)
                except CorpusError as error:
                    _quarantine(
                        state,
                        state_path,
                        story,
                        "invalid_terminal",
                        str(error),
                        state_telemetry,
                        policy,
                    )
                    raise
                terminal_calls = sum(state_telemetry[key] for key in ("completed", "failed", "uncertain"))
                if terminal_calls < state_telemetry["attempted"]:
                    _quarantine(
                        state,
                        state_path,
                        story,
                        "billing_uncertain",
                        "billing uncertain; reconcile before retry",
                        state_telemetry,
                        policy,
                    )
                    raise CorpusError(f"billing uncertain for {story_id}; reconcile before retry")
        if story_id in bundles:
            if bundles[story_id].run_metadata.get("intake_sha256") != intake_sha256(story):
                bundle_telemetry = _persisted_telemetry(
                    bundles[story_id].run_metadata, policy, story_id
                )
                _quarantine(
                    state,
                    state_path,
                    story,
                    "intake_mismatch",
                    "intake digest differs from completed bundle",
                    bundle_telemetry,
                    policy,
                )
                raise CorpusError(f"intake digest differs for completed bundle: {story_id}")
            _verify_bundle_assets(bundles[story_id], out_dir)
            if state_entry != expected_reference:
                state[story_id] = expected_reference
                _write_state(state_path, state)
            summary["stories_skipped"] += 1
            continue
        if fixture:
            memory = _fixture_memory(story)
            _write_fixture_images(memory, out_dir)
            refs = len(memory.characters)
            scenes = len(memory.scenes)
            story_telemetry = Counter(attempted=0, completed=0, failed=0, uncertain=0)
            bundle = _bundle(
                story,
                memory,
                out_dir,
                fixture,
                story_telemetry,
                policy.conservative_call_usd,
            )
        else:
            billable_calls = max(campaign_spent, telemetry["attempted"])
            remaining_usd = policy.authorized_usd - billable_calls * policy.conservative_call_usd
            reserve_usd = story_draw_limit * policy.conservative_call_usd
            if story_draw_limit <= 0 or reserve_usd > remaining_usd:
                summary["halted"] = True
                break
            story_telemetry = (
                _persisted_telemetry(state_entry, policy, story_id)
                if state_entry is not None
                else Counter(attempted=0, completed=0, failed=0, uncertain=0)
            )

            def record_fal_event(event: str) -> None:
                if event == "attempted" and story_telemetry["attempted"] >= story_draw_limit:
                    raise StoryBudgetStopped
                if event == "failed_uncertain":
                    key = "uncertain"
                else:
                    key = event
                story_telemetry[key] += 1
                telemetry[key] += 1
                state[story_id] = {
                    "in_progress": True,
                    "intake_sha256": intake_sha256(story),
                    "conservative_call_usd": str(policy.conservative_call_usd),
                    "telemetry": dict(story_telemetry),
                    **(
                        {"billing_acknowledged_at": billing_acknowledged_at}
                        if billing_acknowledged_at is not None
                        else {}
                    ),
                }
                _write_state(state_path, state)

            token = _fal_event_sink.set(record_fal_event)
            try:
                run = run_story(app_graph, story)
            except Exception as error:
                if story_telemetry["uncertain"]:
                    _quarantine(
                        state,
                        state_path,
                        story,
                        "billing_uncertain",
                        "billing uncertain; reconcile before retry",
                        story_telemetry,
                        policy,
                    )
                    raise CorpusError(f"billing uncertain for {story_id}; reconcile before retry") from error
                raise
            finally:
                _fal_event_sink.reset(token)

            campaign_spent += run.image_count
            invocation_spent += run.image_count
            if run.outcome != "completed":
                reason = run.reason or "invalid_terminal"
                _quarantine(
                    state,
                    state_path,
                    story,
                    reason,
                    reason.replace("_", " "),
                    story_telemetry,
                    policy,
                )
                summary["halted"] = True
                break

            try:
                memory = StoryMemory.model_validate(run.values)
                refs, scenes = download_images(memory, out_dir, supabase)
                bundle = _bundle(
                    story,
                    memory,
                    out_dir,
                    fixture,
                    story_telemetry,
                    policy.conservative_call_usd,
                    billing_acknowledged_at=billing_acknowledged_at,
                )
            except (CorpusError, ValidationError) as error:
                _quarantine(
                    state,
                    state_path,
                    story,
                    "invalid_terminal",
                    f"invalid terminal state: {error}",
                    story_telemetry,
                    policy,
                )
                raise CorpusError(f"invalid terminal state for {story_id}: {error}") from error

        write_bundle(out_dir, bundle)
        state[story_id] = expected_reference
        _write_state(state_path, state)
        summary["stories_run"] += 1
        summary["characters"] += refs
        summary["scenes"] += scenes
    summary["images_spent"] = invocation_spent
    summary["usd_high"] = str(
        max(campaign_spent, telemetry["attempted"]) * policy.conservative_call_usd
    )
    summary["telemetry"] = dict(telemetry)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    paid_or_fixture = parser.add_mutually_exclusive_group()
    paid_or_fixture.add_argument("--max-usd", type=Decimal)
    paid_or_fixture.add_argument("--fixture", action="store_true")
    parser.add_argument("--price-per-call", type=Decimal)
    parser.add_argument("--corpus", type=pathlib.Path, default=CORPUS_PATH)
    parser.add_argument("--out", type=pathlib.Path, default=DATA_DIR)
    parser.add_argument("--limit", type=int, default=None, help="run only the first N stories")
    parser.add_argument("--resume-quarantined", metavar="STORY_ID")
    parser.add_argument("--acknowledge-uncertain-billing", metavar="STORY_ID")
    args = parser.parse_args(argv)
    if args.fixture and args.price_per_call is not None:
        parser.error("--fixture cannot be combined with --price-per-call")
    if args.fixture and (
        args.resume_quarantined is not None or args.acknowledge_uncertain_billing is not None
    ):
        parser.error("--fixture cannot be combined with quarantine recovery options")
    if (
        args.acknowledge_uncertain_billing is not None
        and args.acknowledge_uncertain_billing != args.resume_quarantined
    ):
        parser.error("--acknowledge-uncertain-billing requires matching --resume-quarantined")
    stories = load_intake(args.corpus)[: args.limit]
    try:
        if args.fixture:
            summary = build(stories, None, args.out, None, fixture=True)
        else:
            from app.config import settings
            from app.db import get_supabase_client
            from langgraph.checkpoint.postgres import PostgresSaver
            from pipeline.graph import build_graph

            with PostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
                checkpointer.setup()
                defaults = SpendPolicy()
                policy = SpendPolicy(
                    max_usd=args.max_usd if args.max_usd is not None else defaults.max_usd,
                    conservative_call_usd=(
                        args.price_per_call
                        if args.price_per_call is not None
                        else defaults.conservative_call_usd
                    ),
                )
                summary = build(
                    stories,
                    build_graph(checkpointer=checkpointer),
                    args.out,
                    get_supabase_client(),
                    policy=policy,
                    resume_quarantined=args.resume_quarantined,
                    acknowledge_uncertain_billing=args.acknowledge_uncertain_billing,
                )
    except CorpusError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
