"""Validation for de-identified Objective-4 story intake (research-corpus-operations §4.1)."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from contracts.story_memory import StoryMemory


class CorpusError(ValueError):
    """A corpus artifact that must be quarantined instead of regenerated."""


class AssetRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    storage_path: str
    local_path: str
    sha256: str
    mime_type: Literal["image/png", "image/webp"]
    width: int
    height: int
    byte_length: int
    kind: Literal["ref", "scene"]


class RunBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory: StoryMemory
    provenance: Literal["synthetic", "donated"]
    split: Literal["train", "val", "test"]
    candidate_role: Literal["primary", "backup", "not_applicable"]
    declared_characters: list[str] | None = None
    declared_non_human: list[str] | None = None
    exclusions: list[str] = Field(default_factory=list)
    run_metadata: dict[str, str | int | float]
    assets: list[AssetRecord]


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _atomic_write(path: Path, contents: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_bytes(contents)
    temporary.replace(path)


def write_bundle(root: Path, bundle: RunBundle) -> Path:
    """Persist one completed corpus run, accepting only byte-identical reruns."""
    story_id = bundle.memory.story_id
    if not story_id or Path(story_id).name != story_id:
        raise CorpusError("story_id must be one path segment")
    bundle_dir = Path(root) / "runs" / story_id
    files = {
        "memory.json": _json_bytes(bundle.memory.model_dump(mode="json")),
        "run.json": _json_bytes({
            "provenance": bundle.provenance,
            "split": bundle.split,
            "candidate_role": bundle.candidate_role,
            **(
                {
                    "declared_characters": bundle.declared_characters,
                    "declared_non_human": bundle.declared_non_human,
                }
                if bundle.declared_characters is not None
                and bundle.declared_non_human is not None
                else {}
            ),
            **({"exclusions": bundle.exclusions} if bundle.exclusions else {}),
            "run_metadata": bundle.run_metadata,
        }),
        "assets.json": _json_bytes([asset.model_dump(mode="json") for asset in bundle.assets]),
    }
    bundle_dir.mkdir(parents=True, exist_ok=True)
    for name, contents in files.items():
        path = bundle_dir / name
        if path.exists() and path.read_bytes() != contents:
            raise CorpusError(f"immutable bundle differs: {story_id}/{name}")
    for name, contents in files.items():
        path = bundle_dir / name
        if not path.exists():
            _atomic_write(path, contents)
    return bundle_dir


def reconcile_declared_roster(
    declared_characters: list[str], declared_non_human: list[str], memory: StoryMemory
) -> None:
    declared = Counter(name.casefold() for name in declared_characters)
    declared_non_human_counts = Counter(name.casefold() for name in declared_non_human)
    final = Counter(character.name.casefold() for character in memory.characters)
    final_non_human = Counter(
        character.name.casefold()
        for character in memory.characters
        if not character.description.is_humanoid
    )
    if declared != final or declared_non_human_counts != final_non_human:
        raise CorpusError(f"declared roster does not reconcile for {memory.story_id}")


def load_completed_bundles(root: Path) -> list[RunBundle]:
    """Load only complete immutable run bundles, revalidating Story Memory at the boundary."""
    runs_dir = Path(root) / "runs"
    if not runs_dir.exists():
        return []
    bundles = []
    for bundle_dir in sorted(path for path in runs_dir.iterdir() if path.is_dir()):
        paths = {name: bundle_dir / name for name in ("memory.json", "run.json", "assets.json")}
        missing = [name for name, path in paths.items() if not path.is_file()]
        if missing:
            raise CorpusError(f"incomplete bundle quarantined: {bundle_dir.name} missing {', '.join(missing)}")
        memory = StoryMemory.model_validate(json.loads(paths["memory.json"].read_text(encoding="utf-8")))
        run = json.loads(paths["run.json"].read_text(encoding="utf-8"))
        assets = json.loads(paths["assets.json"].read_text(encoding="utf-8"))
        bundle = RunBundle(memory=memory, assets=assets, **run)
        if bundle.memory.story_id != bundle_dir.name:
            raise CorpusError(f"bundle story_id differs from directory: {bundle_dir.name}")
        bundles.append(bundle)
    return bundles


class IntakeRecord(BaseModel):
    """A sanitized story record; identity and receipt data are intentionally not representable."""

    model_config = ConfigDict(extra="forbid")

    story_id: str
    text: str
    declared_characters: list[str]
    declared_non_human: list[str]
    provenance: Literal["synthetic", "donated"]
    split: Literal["train", "val", "test"]
    candidate_role: Literal["primary", "backup", "not_applicable"]
    style_preset_id: Literal["cel", "gouache", "cut_paper"]
    guardian_consent: bool | None = None
    child_assent: bool | None = None
    manual_pii_redaction: bool | None = None
    independent_redaction_review: bool | None = None
    withdrawal_state: Literal["active", "withdrawn"] | None = None
    selection_frozen_at: datetime | None = None

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

    @model_validator(mode="after")
    def validate_source_rules(self) -> Self:
        if not set(self.declared_non_human) <= set(self.declared_characters):
            raise ValueError("declared_non_human must be a subset of declared_characters")

        donated_values = (
            self.guardian_consent,
            self.child_assent,
            self.manual_pii_redaction,
            self.independent_redaction_review,
            self.withdrawal_state,
            self.selection_frozen_at,
        )
        if self.provenance == "synthetic":
            if self.split == "test":
                raise ValueError("synthetic records cannot use the test split")
            if self.candidate_role != "not_applicable":
                raise ValueError("synthetic records must use candidate_role=not_applicable")
            if any(value is not None for value in donated_values):
                raise ValueError("synthetic records cannot carry donated-only fields")
            return self

        if self.split != "test":
            raise ValueError("donated records must use the test split")
        if self.candidate_role == "not_applicable":
            raise ValueError("donated records must be primary or backup candidates")
        if not all(
            (
                self.guardian_consent,
                self.child_assent,
                self.manual_pii_redaction,
                self.independent_redaction_review,
            )
        ):
            raise ValueError("donated records require every approval")
        if self.withdrawal_state != "active":
            raise ValueError("withdrawn donated records cannot enter generation")
        if self.selection_frozen_at is None:
            raise ValueError("donated records require selection_frozen_at")
        if self.selection_frozen_at.tzinfo is None or self.selection_frozen_at > datetime.now(timezone.utc):
            raise ValueError("selection_frozen_at must be a completed timestamp")
        return self


def load_intake(path: Path) -> list[IntakeRecord]:
    """Load one strict JSON-list intake file and reject duplicate opaque story identifiers."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("intake must be a JSON list")

    records = [IntakeRecord.model_validate(item) for item in payload]
    story_ids = [record.story_id for record in records]
    if len(story_ids) != len(set(story_ids)):
        raise ValueError("duplicate story_id")
    if len({record.provenance for record in records}) > 1:
        raise ValueError("intake must contain one provenance")
    if records and all(record.provenance == "donated" for record in records):
        styles = Counter(record.style_preset_id for record in records)
        primary_styles = Counter(
            record.style_preset_id for record in records if record.candidate_role == "primary"
        )
        backup_styles = Counter(
            record.style_preset_id for record in records if record.candidate_role == "backup"
        )
        if (
            len(records) != 15
            or styles != {"gouache": 5, "cel": 5, "cut_paper": 5}
            or primary_styles != {"gouache": 4, "cel": 3, "cut_paper": 3}
            or backup_styles != {"gouache": 1, "cel": 2, "cut_paper": 2}
        ):
            raise ValueError("donated allocation must be 15 candidates in the frozen style and role slots")
    return records
