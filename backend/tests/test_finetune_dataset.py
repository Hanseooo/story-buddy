"""§5.2 / §5.4 — pairing, annotation consensus, and the ONE polarity conversion.

`annotations.same_character` is `true` for *same*; the manuscript's positive class is
`label = not same_character` (annotation-surface §2.1). That inversion happens in
`build_dataset.py` and nowhere else, so it is asserted here and nowhere else.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from contracts.story_memory import (
    Attempt,
    Character,
    CharacterDescription,
    Input,
    RefVerdict,
    Scene,
    Style,
    StoryMemory,
)
from finetune import build_dataset as bd
from finetune import annotation_truth as at
from finetune import freeze_dataset as fd
from finetune.corpus_io import AssetRecord, CorpusError, RunBundle, write_bundle

from finetune.dataset_selection import (
    DatasetSelection,
    DatasetSelectionAudit,
    validate_hard_negative_matches,
)
from finetune.manifest import ManifestError


def memory() -> StoryMemory:
    return StoryMemory(
        schema_version=1,
        story_id="story_1",
        classroom_id="c1",
        profile_id="p1",
        input=Input(raw_text="once upon a time"),
        characters=[
            Character(
                char_id="quill_007",
                name="Quill",
                description=CharacterDescription(
                    species="hedgehog", colours=["cream chest"], body_features=["three amber eyes"],
                    clothing=["striped scarf"],
                ),
                canonical_ref_image="story_1/ref-quill.png",
            ),
            Character(char_id="noref_1", name="Ghost", canonical_ref_image=None),
        ],
        scenes=[
            Scene(
                scene_id="s1",
                text_excerpt="x",
                characters_present=["quill_007", "noref_1"],
                attempts=[Attempt(image_ref="story_1/s1-1.png"), Attempt(image_ref="story_1/s1-2.png")],
                final_image_ref="story_1/s1-2.png",
            ),
            Scene(
                scene_id="s2",
                text_excerpt="y",
                characters_present=[],
                attempts=[Attempt(image_ref="story_1/s2-1.png")],
                final_image_ref="story_1/s2-1.png",
            ),
            Scene(
                scene_id="s3",
                text_excerpt="z",
                characters_present=["quill_007"],
                attempts=[Attempt(image_ref="story_1/s3-1.png")],
                final_image_ref="story_1/s3-1.png",
            ),
        ],
    )


def freeze_bundle(
    data_dir, *, split="train", provenance="synthetic", exclusions=None, fixture=True,
    include_roster=True,
):
    ref = BytesIO()
    scene = BytesIO()
    Image.new("RGB", (2, 3), "purple").save(ref, format="PNG")
    Image.new("RGB", (2, 3), "purple").save(scene, format="WEBP", quality=82)
    ref_bytes, scene_bytes = ref.getvalue(), scene.getvalue()
    ref_path = data_dir / "ref" / "story-freeze_ref.png"
    scene_path = data_dir / "scene" / "story-freeze_scene.webp"
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_bytes(ref_bytes)
    scene_path.write_bytes(scene_bytes)
    story = StoryMemory(
        schema_version=1,
        story_id="story-freeze",
        classroom_id="c1",
        profile_id="p1",
        input=Input(raw_text="redacted fixture"),
        style=Style(style_preset_id="cel", prompt_fragment="fixture cel"),
        characters=[
            Character(char_id="char-freeze", name="Moss", canonical_ref_image="story-freeze/ref.png")
        ],
        scenes=[
            Scene(
                scene_id="s1",
                text_excerpt="Moss waved.",
                characters_present=["char-freeze"],
                attempts=[Attempt(image_ref="story-freeze/scene.webp")],
                final_image_ref="story-freeze/scene.webp",
            )
        ],
    )
    bundle = RunBundle(
        memory=story,
        provenance=provenance,
        split=split,
        candidate_role="not_applicable" if provenance == "synthetic" else "primary",
        declared_characters=["Moss"] if include_roster else None,
        declared_non_human=[] if include_roster else None,
        exclusions=exclusions or [],
        run_metadata={
            "fixture": "true" if fixture else "false",
            "schema_version": 1,
            "style_preset_id": "cel",
            "code_commit": "fixture-commit",
            "text_model": "fixture-text",
            "image_model": "fixture-image",
            "image_edit_model": "fixture-image-edit",
            "judge_model": "fixture-judge",
            "moderation_primary_model": "fixture-mod-text",
            "moderation_primary_image_model": "fixture-mod-image",
            "moderation_backstop_model": "fixture-mod-backstop",
            "moderation_backstop_image_model": "fixture-mod-image-backstop",
            "extraction_prompt_version": 1,
            "reference_judge_prompt_version": 6,
            "scene_prompt_version": 2,
            "judge_prompt_version": 4,
            "scene_constraint_prompt_version": 3,
            "segment_prompt_version": 1,
            "image_budget": 55,
            "recursion_limit": 87,
        },
        assets=[
            AssetRecord(
                storage_path="story-freeze/ref.png",
                local_path=ref_path.relative_to(data_dir).as_posix(),
                sha256=hashlib.sha256(ref_bytes).hexdigest(),
                mime_type="image/png",
                width=2,
                height=3,
                byte_length=len(ref_bytes),
                kind="ref",
            ),
            AssetRecord(
                storage_path="story-freeze/scene.webp",
                local_path=scene_path.relative_to(data_dir).as_posix(),
                sha256=hashlib.sha256(scene_bytes).hexdigest(),
                mime_type="image/webp",
                width=2,
                height=3,
                byte_length=len(scene_bytes),
                kind="scene",
            ),
        ],
    )
    write_bundle(data_dir, bundle)
    return bundle


# --- pairing -------------------------------------------------------------------------------

def test_pair_id_is_deterministic_and_opaque():
    a = bd.mint_pair_id("quill_007", "story_1/s1-1.png")
    assert a == bd.mint_pair_id("quill_007", "story_1/s1-1.png")
    assert a != bd.mint_pair_id("quill_007", "story_1/s1-2.png")
    assert "quill" not in a and ".png" not in a


def test_pairs_are_reference_first_one_per_finalized_scene_and_skip_missing_references():
    pairs = bd.pairs_from_memory(memory())
    assert [(p.char_id, p.ref_image, p.scene_image) for p in pairs] == [
        ("quill_007", "story_1/ref-quill.png", "story_1/s1-2.png"),
        ("quill_007", "story_1/ref-quill.png", "story_1/s3-1.png"),
    ]


# --- annotation consensus ------------------------------------------------------------------

def test_fetch_annotations_paginates_past_supabase_default_row_limit():
    client = MagicMock()
    query = client.table.return_value.select.return_value
    query.order.return_value = query
    first_page = MagicMock()
    first_page.execute.return_value.data = [{"pair_id": f"p{i}"} for i in range(1000)]
    second_page = MagicMock()
    second_page.execute.return_value.data = [{"pair_id": "p1000"}]
    query.range.side_effect = [first_page, second_page]

    with patch.object(at, "get_supabase_client", return_value=client):
        result = bd.fetch_annotations()

    assert len(result) == 1001
    assert query.range.call_args_list == [((0, 999),), ((1000, 1999),)]

def rows(pair_id, *specs):
    out = []
    for i, spec in enumerate(specs):
        row = {"pair_id": pair_id, "annotator_id": f"a{i}", "failure_reasons": [],
               "anatomy_intact": True, "text_free": True}
        row.update(spec)
        out.append(row)
    return out


def test_consensus_is_majority_on_same_character():
    resolved = bd.resolve_annotations(
        rows("p1", {"same_character": True}, {"same_character": True}),
        set(), set(),
    )
    assert resolved["p1"].same_character is True
    assert resolved["p1"].adjudicated is False


def test_an_unadjudicated_tie_raises_manifest_error():
    with pytest.raises(ManifestError, match="unresolved conflict"):
        bd.resolve_annotations(
            rows("p1", {"same_character": True}, {"same_character": False}),
            set(), set(),
        )


def test_disagreeing_fields_goes_to_adjudication_and_is_exclusive():
    # If they agree on same_character but disagree on fields, it's a conflict and requires an adjudicator.
    # The adjudicator's row is used exclusively.
    resolved = bd.resolve_annotations(rows(
        "p1",
        {"annotator_id": "a1", "same_character": False, "failure_reasons": ["wrong_colour"], "anatomy_intact": False},
        {"annotator_id": "a2", "same_character": False, "failure_reasons": ["wrong_clothing"], "text_free": False},
        {"annotator_id": "adj1", "same_character": False, "failure_reasons": ["wrong_colour"], "anatomy_intact": True, "text_free": True},
    ), {"adj1"}, set())
    c = resolved["p1"]
    # Should exactly match adj1, no unioning
    assert c.anatomy_intact is True and c.text_free is True
    assert c.failure_reasons == ["wrong_colour"]


def test_missing_gating_columns_default_to_the_schema_defaults():
    resolved = bd.resolve_annotations(
        rows("p1", {"same_character": True}, {"same_character": True}),
        set(), set(),
    )
    assert resolved["p1"].anatomy_intact is True and resolved["p1"].text_free is True


def test_resolve_annotations_strict_rules():
    # >2 ordinary annotations -> hard fail
    with pytest.raises(ManifestError, match=">2 ordinary annotations"):
        bd.resolve_annotations(
            rows("p1", {"same_character": True}, {"same_character": True}, {"same_character": True}),
            set(), set(),
        )

    # <2 ordinary annotations -> hard fail
    with pytest.raises(ManifestError, match="<2 ordinary annotations"):
        bd.resolve_annotations(
            rows("p1", {"same_character": True}),
            set(), set(),
        )

    # duplicate annotator_ids -> hard fail
    with pytest.raises(ManifestError, match="duplicate annotator_ids"):
        bd.resolve_annotations(
            [
                {"pair_id": "p1", "annotator_id": "a1", "same_character": True},
                {"pair_id": "p1", "annotator_id": "a1", "same_character": True},
            ],
            set(), set(),
        )

    # 2 disagreeing ordinary rows + 1 adjudicator -> adjudicator decides
    res = bd.resolve_annotations(
        rows("p1",
            {"same_character": True, "annotator_id": "a1"},
            {"same_character": False, "annotator_id": "a2"},
            {"same_character": False, "annotator_id": "adj1", "failure_reasons": ["wrong_colour"]},
        ),
        {"adj1"}, set(),
    )
    assert res["p1"].same_character is False
    assert res["p1"].adjudicated is True
    assert res["p1"].failure_reasons == ["wrong_colour"]

    # 2 disagreeing ordinary rows + >1 adjudicators -> hard fail
    with pytest.raises(ManifestError, match="multiple adjudicator rows"):
        bd.resolve_annotations(
            rows("p1",
                {"same_character": True, "annotator_id": "a1"},
                {"same_character": False, "annotator_id": "a2"},
                {"same_character": False, "annotator_id": "adj1"},
                {"same_character": True, "annotator_id": "adj2"},
            ),
            {"adj1", "adj2"}, set(),
        )

    # 2 agreeing ordinary rows + adjudicator present -> hard fail
    with pytest.raises(ManifestError, match="ordinary annotators agreed, but adjudicator row exists"):
        bd.resolve_annotations(
            rows("p1",
                {"same_character": True, "annotator_id": "a1"},
                {"same_character": True, "annotator_id": "a2"},
                {"same_character": False, "annotator_id": "adj1"},
            ),
            {"adj1"}, set(),
        )

    # Pilot pairs are silently excluded from resolution
    assert bd.resolve_annotations(
        rows("pilot_1", {"same_character": True}),
        set(), {"pilot_1"},
    ) == {}


def test_reconcile_pair_status_derives_every_state_without_trusting_cached_status():
    annotation_rows = [
        {"pair_id": "pending", "annotator_id": None, "status": "adjudicated"},
        *rows("partial", {"same_character": True, "status": "complete"}),
        *rows("complete", {"same_character": True}, {"same_character": True}),
        *rows("conflicted", {"same_character": True}, {"same_character": False}),
        *rows(
            "adjudicated",
            {"annotator_id": "a1", "same_character": True},
            {"annotator_id": "a2", "same_character": False},
            {"annotator_id": "adj", "same_character": False},
        ),
    ]

    assert bd.reconcile_pair_status(annotation_rows, {"adj"}) == {
        "pending": "pending",
        "partial": "partially_annotated",
        "complete": "complete",
        "conflicted": "conflicted",
        "adjudicated": "adjudicated",
    }


def test_reconcile_pair_status_rejects_impossible_annotation_states():
    with pytest.raises(ManifestError, match="duplicate annotator"):
        bd.reconcile_pair_status(
            rows(
                "p1",
                {"annotator_id": "a1", "same_character": True},
                {"annotator_id": "a1", "same_character": True},
            ),
            set(),
        )


def test_repair_pair_statuses_updates_only_stale_rows_and_is_idempotent():
    client = MagicMock()
    response = MagicMock(data=[])
    response.error = None
    client.table.return_value.update.return_value.in_.return_value.execute.return_value = response
    current = [
        {"id": "p1", "status": "pending"},
        {"id": "p2", "status": "partially_annotated"},
    ]
    statuses = {"p1": "complete", "p2": "partially_annotated"}

    assert bd.repair_pair_statuses(client, current, statuses) == 1
    client.table.assert_called_once_with("research_pairs")
    client.table.return_value.update.assert_called_once_with({"status": "complete"})
    client.table.return_value.update.return_value.in_.assert_called_once_with("id", ["p1"])

    client.reset_mock()
    assert bd.repair_pair_statuses(
        client,
        [{"id": "p1", "status": "complete"}, {"id": "p2", "status": "partially_annotated"}],
        statuses,
    ) == 0
    client.table.assert_not_called()


def test_reconcile_remote_status_includes_unlabelled_queue_rows_and_repairs_cache():
    client = MagicMock()
    current = [{"id": "p1", "status": "complete"}, {"id": "p2", "status": "pending"}]
    annotations = rows("p1", {"same_character": True}, {"same_character": True})
    with (
        patch.object(at, "_fetch_pair_status_rows", return_value=current),
        patch.object(at, "fetch_annotations", return_value=annotations),
        patch.object(at, "fetch_adjudicator_ids", return_value=set()),
        patch.object(at, "repair_pair_statuses", return_value=0) as repair,
    ):
        statuses, changed = bd.reconcile_remote_status(client)

    assert statuses == {"p1": "complete", "p2": "pending"}
    assert changed == 0
    repair.assert_called_once_with(client, current, statuses)


def test_cli_exposes_reconcile_and_freeze_modes(tmp_path):
    with (
        patch.object(bd, "get_supabase_client", return_value=MagicMock()),
        patch.object(bd, "reconcile_remote_status", return_value=({"p1": "complete"}, 1)),
    ):
        assert bd.main(["--reconcile-only"]) == 0

    report = bd.FreezeReport(
        dataset_sha256="a" * 64,
        counts={},
        adjudication_rate=0.0,
        exclusions=[],
        pinned_versions={},
    )
    with patch.object(bd, "freeze_dataset", return_value=report) as freeze:
        assert bd.main(
            ["--freeze", "--data", str(tmp_path / "data"), "--out", str(tmp_path / "frozen")]
        ) == 0
    freeze.assert_called_once_with(
        tmp_path / "data",
        tmp_path / "frozen",
        donated_intake_path=None,
        selection_path=None,
    )


# --- polarity ------------------------------------------------------------------------------

@pytest.mark.parametrize("same_character", [True, False])
def test_label_is_the_inverse_of_same_character_and_is_converted_only_here(same_character):
    consensus = bd.resolve_annotations(
        rows("x", {"same_character": same_character}, {"same_character": same_character}),
        set(), set(),
    )
    pairs = bd.pairs_from_memory(memory())
    keyed = {pairs[0].pair_id: consensus["x"]}
    records = bd.build_records(memory(), "train", "synthetic", keyed, {pairs[1].pair_id})

    assert len(records) == 1
    assert records[0].same_character is same_character
    assert records[0].label is (not same_character)


def test_unannotated_pairs_hard_fail_if_not_pilot():
    with pytest.raises(ManifestError, match="<2 annotations"):
        bd.build_records(memory(), "train", "synthetic", {}, set())


def test_pilot_pairs_are_dropped():
    pairs = bd.pairs_from_memory(memory())
    pilot_pairs = {p.pair_id for p in pairs}
    assert bd.build_records(memory(), "train", "synthetic", {}, pilot_pairs) == []


def test_build_records_carries_the_gating_booleans_and_the_split_metadata():
    pairs = bd.pairs_from_memory(memory())
    keyed = {
        pairs[0].pair_id: bd.Consensus(
            same_character=False, failure_reasons=["wrong_colour"], anatomy_intact=False, text_free=False,
        ),
        pairs[1].pair_id: bd.Consensus(
            same_character=True, failure_reasons=[], anatomy_intact=True, text_free=True,
        ),
    }
    rec1, rec2 = bd.build_records(memory(), "test", "donated", keyed, set())
    assert (rec1.split, rec1.provenance, rec1.pair_type) == ("test", "donated", "pipeline")
    assert rec1.char_id == "story_1:quill_007"
    assert rec1.anatomy_intact is False and rec1.text_free is False
    assert rec1.failure_reasons == ["wrong_colour"]
    # Local dataset paths, NOT the raw Storage paths — LLaMA-Factory resolves `images` against
    # the filesystem and `build_corpus` writes the flattened name (manifest.local_image_path).
    assert rec1.images == ["data/judge/corpus/ref/story_1_ref-quill.png", "data/judge/corpus/scene/story_1_s1-2.png"]
    assert rec2.same_character is True
    assert rec2.label is False


def test_manifest_lineage_ids_qualify_story_local_character_ids(tmp_path):
    first = memory().model_copy(update={"story_id": "story-a"})
    second = memory().model_copy(
        update={
            "story_id": "story-b",
            "characters": [
                memory().characters[0].model_copy(
                    update={"canonical_ref_image": "story-b/ref-quill.png"}
                )
            ],
            "scenes": [
                memory().scenes[0].model_copy(
                    update={
                        "attempts": [Attempt(image_ref="story-b/s1-1.png")],
                        "final_image_ref": "story-b/s1-1.png",
                    }
                )
            ],
        }
    )
    pairs = [*bd.pairs_from_memory(first), *bd.pairs_from_memory(second)]
    annotations = [
        row
        for pair in pairs
        for row in rows(pair.pair_id, {"same_character": True}, {"same_character": True})
    ]

    records = bd.build_dataset(
        [(first, "train", "synthetic"), (second, "val", "synthetic")],
        out_path=tmp_path / "manifest.jsonl",
        add_constructed=False,
        annotation_rows=annotations,
        adjudicator_ids=set(),
        pilot_pair_ids=set(),
    )

    assert {record.char_id for record in records} == {
        "story-a:quill_007",
        "story-b:quill_007",
    }


# --- rationale template --------------------------------------------------------------------

def test_positive_rationale_lists_the_attributes_rather_than_being_blank():
    text = bd.render_rationale(True, [], ["three amber eyes", "striped scarf"])
    assert text and "three amber eyes" in text and "striped scarf" in text


def test_negative_rationale_is_one_deterministic_sentence_per_ticked_reason():
    text = bd.render_rationale(False, ["wrong_body_feature", "wrong_clothing"], ["three amber eyes"])
    assert text == bd.render_rationale(False, ["wrong_body_feature", "wrong_clothing"], ["three amber eyes"])
    assert text.count(".") >= 2
    assert "three amber eyes" in text


def test_negative_with_no_ticked_reason_still_renders_prose():
    assert bd.render_rationale(False, [], []).strip()


def manifest_record(
    pair_id: str,
    char_id: str,
    ref_image: str,
    scene_image: str,
    *,
    split: str = "train",
    provenance: str = "synthetic",
    pair_type: str = "pipeline",
    ref_verdict_status: str = "unverified",
) -> bd.ManifestRecord:
    return bd.ManifestRecord(
        pair_id=pair_id,
        char_id=char_id,
        split=split,  # type: ignore[arg-type]
        provenance=provenance,  # type: ignore[arg-type]
        pair_type=pair_type,  # type: ignore[arg-type]
        images=[ref_image, scene_image],
        differences_observed="ok",
        same_character=True,
        label=False,
        failure_reasons=[],
        ref_verdict_status=ref_verdict_status,  # type: ignore[arg-type]
    )


# --- constructed negatives -----------------------------------------------------------------

def test_constructed_negatives_use_every_natural_target_scene():
    records = [
        manifest_record("ref", "story-a:a", "ref/a.png", "scene/a.webp"),
        manifest_record("target-1", "story-b:b", "ref/b.png", "scene/b-1.webp"),
        manifest_record("target-2", "story-b:b", "ref/b.png", "scene/b-2.webp"),
    ]
    made = bd.constructed_records(records, {"story-a:a": "story-b:b"})
    assert [row.images for row in made] == [
        ["ref/a.png", "scene/b-1.webp"],
        ["ref/a.png", "scene/b-2.webp"],
    ]
    for row in made:
        assert row.split == "train"
        assert row.pair_type == "constructed"
        assert row.same_character is False
        assert row.label is True
        assert row.char_id == "story-a:a"


def test_constructed_negatives_ignore_val_and_test_records():
    records = [
        manifest_record("ref", "story-a:a", "ref/a.png", "scene/a.webp", split="val"),
        manifest_record("target", "story-b:b", "ref/b.png", "scene/b.webp", split="test"),
    ]
    with pytest.raises(ManifestError, match="natural training records"):
        bd.constructed_records(records, {"story-a:a": "story-b:b"})


def test_constructed_negatives_rejects_missing_reference_or_target():
    records = [
        manifest_record("ref", "story-a:a", "ref/a.png", "scene/a.webp"),
    ]
    with pytest.raises(ManifestError, match="target character"):
        bd.constructed_records(records, {"story-a:a": "story-b:b"})


def test_build_dataset_requires_hard_negative_matches_when_constructed_enabled():
    with pytest.raises(ManifestError, match="hard-negative selection is required"):
        bd.build_dataset(
            [],
            out_path=Path("tmp.jsonl"),
            add_constructed=True,
            annotation_rows=[],
            adjudicator_ids=set(),
            pilot_pair_ids=set(),
            hard_negative_matches=None,
        )



# --- the supabase seam ---------------------------------------------------------------------

def test_fetch_annotations_reads_the_annotations_table_through_the_existing_client_seam():
    client = MagicMock()
    query = client.table.return_value.select.return_value
    query.order.return_value = query
    query.range.return_value.execute.return_value.data = [{"pair_id": "p1"}]
    with patch("finetune.annotation_truth.get_supabase_client", return_value=client):
        assert bd.fetch_annotations() == [{"pair_id": "p1"}]
    client.table.assert_called_once_with("annotations")


def test_fetch_adjudicator_ids_reads_profiles_table():
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": "a1"}]
    with patch("finetune.annotation_truth.get_supabase_client", return_value=client):
        assert bd.fetch_adjudicator_ids() == {"a1"}
    client.table.assert_called_with("profiles")


def test_fetch_pilot_pairs_reads_research_pairs_table():
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": "p1"}]
    with patch("finetune.annotation_truth.get_supabase_client", return_value=client):
        assert bd.fetch_pilot_pairs() == {"p1"}
    client.table.assert_called_with("research_pairs")


# --- build_dataset manifest & stats --------------------------------------------------------


def test_build_dataset_creates_manifest_and_stats(tmp_path):
    import json
    out = tmp_path / "manifest.jsonl"
    with patch("finetune.build_dataset.fetch_annotations", return_value=[]), \
         patch("finetune.build_dataset.fetch_adjudicator_ids", return_value=set()), \
         patch("finetune.build_dataset.fetch_pilot_pairs", return_value=set()):
        records = bd.build_dataset([], out_path=out, add_constructed=False)

    assert out.exists()
    assert records == []
    stats_out = tmp_path / "dataset_manifest.json"
    assert stats_out.exists()
    stats = json.loads(stats_out.read_text(encoding="utf-8"))
    assert stats["overall"]["total_pairs"] == 0
    assert stats["overall"]["characters"] == 0
    assert stats["overall"]["natural_pairs"] == 0
    assert stats["overall"]["constructed_pairs"] == 0
    assert "splits" in stats
    assert set(stats["splits"].keys()) == {"train", "val", "test"}
    assert "class_balance" in stats
    assert "failure_reasons" in stats
    assert "adjudication_rate" in stats
    assert "dataset_sha256" in stats


def test_freeze_dataset_writes_complete_immutable_artifacts_from_annotation_truth(tmp_path):
    data_dir = tmp_path / "corpus"
    run_bundle = freeze_bundle(data_dir)
    pair_id = bd.pairs_from_memory(run_bundle.memory)[0].pair_id
    annotations = rows(pair_id, {"same_character": True}, {"same_character": True})
    out_dir = tmp_path / "freeze"

    with (
        patch.object(fd, "fetch_annotations", return_value=annotations),
        patch.object(fd, "fetch_adjudicator_ids", return_value=set()),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
    ):
        first = bd.freeze_dataset(data_dir, out_dir)
        second = bd.freeze_dataset(data_dir, out_dir)

    assert first == second
    assert first.dataset_sha256 == hashlib.sha256((out_dir / "manifest.jsonl").read_bytes()).hexdigest()
    assert first.counts["story"] == {"story-freeze": 1}
    assert first.counts["split"] == {"train": 1}
    assert first.exclusions == []
    assert first.pinned_versions["code_commit"] == "fixture-commit"
    [manifest_row] = [json.loads(line) for line in (out_dir / "manifest.jsonl").read_text().splitlines()]
    assert manifest_row["images"] == [
        "assets/ref/story-freeze_ref.png",
        "assets/scene/story-freeze_scene.webp",
    ]
    assert (out_dir / manifest_row["images"][0]).read_bytes() == (
        data_dir / run_bundle.assets[0].local_path
    ).read_bytes()
    assert (out_dir / manifest_row["images"][1]).read_bytes() == (
        data_dir / run_bundle.assets[1].local_path
    ).read_bytes()
    assert {
        "manifest.jsonl",
        "dataset_manifest.json",
        "train.json",
        "val.json",
        "test.json",
        "dataset_info.json",
        "freeze_report.json",
        "manifest.train.jsonl",
        "manifest.val.jsonl",
        "manifest.test.jsonl",
        "annotation_agreement.jsonl",
        "character_slices.json",
    } <= {path.name for path in out_dir.iterdir()}
    assert json.loads((out_dir / "freeze_report.json").read_text(encoding="utf-8")) == first.model_dump(
        mode="json"
    )


def test_freeze_writes_hashed_evaluation_projections_without_identity_fields(tmp_path):
    data_dir = tmp_path / "corpus"
    bundle = freeze_bundle(data_dir)
    pair_id = bd.pairs_from_memory(bundle.memory)[0].pair_id
    annotations = rows(
        pair_id,
        {"same_character": True},
        {"same_character": False},
        {"same_character": True, "annotator_id": "adjudicator"},
    )
    out_dir = tmp_path / "freeze"

    with (
        patch.object(fd, "fetch_annotations", return_value=annotations),
        patch.object(fd, "fetch_adjudicator_ids", return_value={"adjudicator"}),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
    ):
        report = fd.freeze_dataset(data_dir, out_dir)

    combined = (out_dir / "manifest.jsonl").read_bytes()
    assert (out_dir / "manifest.train.jsonl").read_bytes() == combined
    assert (out_dir / "manifest.val.jsonl").read_bytes() == b""
    assert (out_dir / "manifest.test.jsonl").read_bytes() == b""
    agreement = [json.loads(line) for line in (out_dir / "annotation_agreement.jsonl").read_text().splitlines()]
    assert agreement == [{"pair_id": pair_id, "labels": [True, False]}]
    assert "annotator_id" not in (out_dir / "annotation_agreement.jsonl").read_text()
    assert json.loads((out_dir / "character_slices.json").read_text()) == {
        "story-freeze:char-freeze": "human"
    }
    for name in (
        "manifest.train.jsonl",
        "manifest.val.jsonl",
        "manifest.test.jsonl",
        "annotation_agreement.jsonl",
        "character_slices.json",
    ):
        assert report.artifact_sha256[name] == hashlib.sha256((out_dir / name).read_bytes()).hexdigest()



def test_freeze_dataset_rejects_bundle_without_declared_roster(tmp_path):
    data_dir = tmp_path / "corpus"
    run_bundle = freeze_bundle(data_dir, include_roster=False)
    pair_id = bd.pairs_from_memory(run_bundle.memory)[0].pair_id
    annotations = rows(pair_id, {"same_character": True}, {"same_character": True})
    with (
        patch.object(fd, "fetch_annotations", return_value=annotations),
        patch.object(fd, "fetch_adjudicator_ids", return_value=set()),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
        pytest.raises(ManifestError, match="missing declared roster"),
    ):
        bd.freeze_dataset(data_dir, tmp_path / "freeze")


def test_freeze_counts_assign_constructed_pair_to_reference_story():
    natural = bd.ManifestRecord(
        pair_id="natural",
        char_id="char-a",
        split="train",
        provenance="synthetic",
        pair_type="pipeline",
        images=["ref/a.png", "scene/a.webp"],
        differences_observed="ok",
        same_character=True,
        label=False,
    )
    constructed = natural.model_copy(
        update={"pair_id": "constructed", "pair_type": "constructed", "same_character": False}
    )

    counts = fd._freeze_counts(
        [natural, constructed], {"natural": "story-a"}, {"char-a": "story-a"}
    )

    assert counts["story"] == {"story-a": 2}


def test_freeze_dataset_ignores_pilot_annotations_outside_the_corpus(tmp_path):
    data_dir = tmp_path / "corpus"
    run_bundle = freeze_bundle(data_dir)
    pair_id = bd.pairs_from_memory(run_bundle.memory)[0].pair_id
    annotations = [
        *rows(pair_id, {"same_character": True}, {"same_character": True}),
        *rows("pilot-pair", {"same_character": False}),
    ]
    with (
        patch.object(fd, "fetch_annotations", return_value=annotations),
        patch.object(fd, "fetch_adjudicator_ids", return_value=set()),
        patch.object(fd, "fetch_pilot_pairs", return_value={"pilot-pair"}),
    ):
        report = bd.freeze_dataset(data_dir, tmp_path / "freeze")

    assert report.adjudication_rate == 0.0
    assert report.exclusions == []


def test_freeze_dataset_checks_hard_negative_timestamp_against_excluded_annotations(tmp_path):
    data_dir = tmp_path / "corpus"
    selected = freeze_bundle(data_dir)
    excluded_memory = selected.memory.model_copy(
        update={
            "story_id": "excluded-story",
            "scenes": [
                selected.memory.scenes[0].model_copy(
                    update={"final_image_ref": "excluded-story/scene.webp"}
                )
            ],
        }
    )
    excluded = selected.model_copy(update={"memory": excluded_memory})
    selected_pair = bd.pairs_from_memory(selected.memory)[0].pair_id
    excluded_pair = bd.pairs_from_memory(excluded.memory)[0].pair_id
    frozen_at = datetime.now(timezone.utc) - timedelta(hours=1)
    selection = DatasetSelection(
        hard_negatives_frozen_at=frozen_at,
        hard_negative_matches=[],
        donated_replacements=[],
    )
    selected_annotations = [
        {
            **row,
            "created_at": (frozen_at + timedelta(minutes=1)).isoformat(),
        }
        for row in rows(selected_pair, {"same_character": True}, {"same_character": True})
    ]
    annotations = [
        *selected_annotations,
        {
            **rows(excluded_pair, {"same_character": True})[0],
            "created_at": (frozen_at - timedelta(minutes=1)).isoformat(),
        },
    ]

    def validate_timestamp(_bundles, current_selection, annotation_rows, pilot_pair_ids):
        return validate_hard_negative_matches(
            [], current_selection, annotation_rows, pilot_pair_ids
        )

    with (
        patch.object(
            fd,
            "prepare_dataset_bundles",
            return_value=([selected], selection, DatasetSelectionAudit([], [], {}, "hash")),
        ),
        patch.object(fd, "load_completed_bundles", return_value=[selected, excluded]),
        patch.object(fd, "fetch_annotations", return_value=annotations),
        patch.object(fd, "fetch_adjudicator_ids", return_value=set()),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
        patch.object(fd, "validate_hard_negative_matches", side_effect=validate_timestamp),
        pytest.raises(ManifestError, match="must precede all non-pilot annotations"),
    ):
        bd.freeze_dataset(data_dir, tmp_path / "freeze")


def test_freeze_dataset_snapshots_exact_selection_artifact(tmp_path):
    data_dir = tmp_path / "corpus"
    selected = freeze_bundle(data_dir)
    pair_id = bd.pairs_from_memory(selected.memory)[0].pair_id
    selection_path = tmp_path / "dataset_selection.json"
    selection_bytes = b'{"controlled": true}\r\n'
    selection_path.write_bytes(selection_bytes)
    selection_hash = hashlib.sha256(selection_bytes).hexdigest()
    selection = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc) - timedelta(hours=1),
        hard_negative_matches=[],
        donated_replacements=[],
    )
    out_dir = tmp_path / "freeze"

    with (
        patch.object(
            fd,
            "prepare_dataset_bundles",
            return_value=(
                [selected],
                selection,
                DatasetSelectionAudit([], [], {}, selection_hash),
            ),
        ),
        patch.object(
            fd,
            "fetch_annotations",
            return_value=rows(pair_id, {"same_character": True}, {"same_character": True}),
        ),
        patch.object(fd, "fetch_adjudicator_ids", return_value=set()),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
        patch.object(fd, "validate_hard_negative_matches", return_value={}),
    ):
        report = bd.freeze_dataset(
            data_dir,
            out_dir,
            selection_path=selection_path,
        )

    assert (out_dir / "dataset_selection.json").read_bytes() == selection_bytes
    assert report.selection_sha256 == selection_hash


def test_freeze_dataset_rejects_selection_snapshot_hash_mismatch(tmp_path):
    data_dir = tmp_path / "corpus"
    selected = freeze_bundle(data_dir)
    pair_id = bd.pairs_from_memory(selected.memory)[0].pair_id
    selection_path = tmp_path / "dataset_selection.json"
    selection_path.write_bytes(b'{"changed": true}\n')
    selection = DatasetSelection(
        hard_negatives_frozen_at=datetime.now(timezone.utc) - timedelta(hours=1),
        hard_negative_matches=[],
        donated_replacements=[],
    )
    out_dir = tmp_path / "freeze"

    with (
        patch.object(
            fd,
            "prepare_dataset_bundles",
            return_value=(
                [selected],
                selection,
                DatasetSelectionAudit([], [], {}, "validated-before-change"),
            ),
        ),
        patch.object(
            fd,
            "fetch_annotations",
            return_value=rows(pair_id, {"same_character": True}, {"same_character": True}),
        ),
        patch.object(fd, "fetch_adjudicator_ids", return_value=set()),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
        patch.object(fd, "validate_hard_negative_matches", return_value={}),
        pytest.raises(ManifestError, match="selection artifact changed during freeze"),
    ):
        bd.freeze_dataset(
            data_dir,
            out_dir,
            selection_path=selection_path,
        )

    assert not out_dir.exists()


def test_freeze_dataset_rejects_changed_existing_output(tmp_path):
    data_dir = tmp_path / "corpus"
    run_bundle = freeze_bundle(data_dir)
    pair_id = bd.pairs_from_memory(run_bundle.memory)[0].pair_id
    annotations = rows(pair_id, {"same_character": True}, {"same_character": True})
    out_dir = tmp_path / "freeze"
    with (
        patch.object(fd, "fetch_annotations", return_value=annotations),
        patch.object(fd, "fetch_adjudicator_ids", return_value=set()),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
    ):
        bd.freeze_dataset(data_dir, out_dir)
        (out_dir / "train.json").write_text("changed", encoding="utf-8")
        with pytest.raises(ManifestError, match="immutable freeze differs"):
            bd.freeze_dataset(data_dir, out_dir)


def test_freeze_dataset_rejects_unknown_annotation_pair_and_asset_drift(tmp_path):
    data_dir = tmp_path / "corpus"
    run_bundle = freeze_bundle(data_dir)
    pair_id = bd.pairs_from_memory(run_bundle.memory)[0].pair_id
    annotations = [
        *rows(pair_id, {"same_character": True}, {"same_character": True}),
        *rows("not-in-bundles", {"same_character": True}, {"same_character": True}),
    ]
    with (
        patch.object(fd, "fetch_annotations", return_value=annotations),
        patch.object(fd, "fetch_adjudicator_ids", return_value=set()),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
        pytest.raises(ManifestError, match="pair/memory mismatch"),
    ):
        bd.freeze_dataset(data_dir, tmp_path / "unknown")

    (data_dir / run_bundle.assets[0].local_path).write_bytes(b"changed")
    with (
        patch.object(fd, "fetch_annotations", return_value=annotations[:2]),
        patch.object(fd, "fetch_adjudicator_ids", return_value=set()),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
        pytest.raises(CorpusError),
    ):
        bd.freeze_dataset(data_dir, tmp_path / "drift")


def test_freeze_dataset_accepts_only_bundle_declared_exclusions(tmp_path):
    data_dir = tmp_path / "corpus"
    initial = freeze_bundle(data_dir)
    pair_id = bd.pairs_from_memory(initial.memory)[0].pair_id
    # Recreate in a separate root because completed bundles are immutable.
    declared_dir = tmp_path / "declared-corpus"
    freeze_bundle(declared_dir, exclusions=[pair_id])
    with (
        patch.object(fd, "fetch_annotations", return_value=[]),
        patch.object(fd, "fetch_adjudicator_ids", return_value=set()),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
    ):
        report = bd.freeze_dataset(declared_dir, tmp_path / "declared-freeze")
    assert report.exclusions == [pair_id]

    unknown_dir = tmp_path / "unknown-corpus"
    freeze_bundle(unknown_dir, exclusions=["unknown-pair"])
    with (
        patch.object(fd, "fetch_annotations", return_value=[]),
        patch.object(fd, "fetch_adjudicator_ids", return_value=set()),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
        pytest.raises(ManifestError, match="unknown exclusions"),
    ):
        bd.freeze_dataset(unknown_dir, tmp_path / "unknown-freeze")


@pytest.mark.parametrize("drift", ["missing", "hash", "mime"])
def test_freeze_dataset_revalidates_local_asset_inventory(tmp_path, drift):
    data_dir = tmp_path / "corpus"
    run_bundle = freeze_bundle(data_dir)
    pair_id = bd.pairs_from_memory(run_bundle.memory)[0].pair_id
    annotations = rows(pair_id, {"same_character": True}, {"same_character": True})
    if drift == "missing":
        (data_dir / run_bundle.assets[0].local_path).unlink()
    else:
        inventory_path = data_dir / "runs" / run_bundle.memory.story_id / "assets.json"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory[0][drift] = "0" * 64 if drift == "hash" else "image/webp"
        if drift == "hash":
            inventory[0]["sha256"] = inventory[0].pop("hash")
        else:
            inventory[0]["mime_type"] = inventory[0].pop("mime")
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    with (
        patch.object(fd, "fetch_annotations", return_value=annotations),
        patch.object(fd, "fetch_adjudicator_ids", return_value=set()),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
        pytest.raises(CorpusError),
    ):
        bd.freeze_dataset(data_dir, tmp_path / "freeze")


def test_freeze_dataset_rejects_production_without_controlled_inputs(tmp_path):
    data_dir = tmp_path / "corpus"
    freeze_bundle(data_dir, fixture=False)
    with pytest.raises(ManifestError, match="production dataset preparation requires"):
        bd.freeze_dataset(data_dir, tmp_path / "freeze")


def test_freeze_dataset_cli_passes_controlled_inputs(tmp_path):
    report = fd.FreezeReport(
        dataset_sha256="hash123",
        counts={},
        adjudication_rate=0.0,
        exclusions=[],
        pinned_versions={},
        selected_donated_stories=["don-001"],
        excluded_donated_stories=["don-011"],
        replacement_reasons={"don-001": "withdrawal"},
        selection_sha256="sel-sha",
    )
    with patch("finetune.build_dataset.freeze_dataset", return_value=report) as mock_freeze:
        ret = bd.main([
            "--freeze",
            "--data", str(tmp_path / "corpus"),
            "--out", str(tmp_path / "freeze"),
            "--donated-intake", "donated.json",
            "--selection", "selection.json",
        ])

    assert ret == 0
    mock_freeze.assert_called_once_with(
        tmp_path / "corpus",
        tmp_path / "freeze",
        donated_intake_path=Path("donated.json"),
        selection_path=Path("selection.json"),
    )

def test_build_dataset_computes_accurate_statistics(tmp_path):
    import json
    out = tmp_path / "manifest.jsonl"
    mem = memory()
    pairs = bd.pairs_from_memory(mem)
    pair1, pair2 = pairs[0], pairs[1]

    # pair1: 2 annotators disagree (a1=True, a2=False), adj1=False (adjudicated)
    # pair2: 2 annotators agree (a1=True, a2=True)
    raw_annotations = [
        {"pair_id": pair1.pair_id, "annotator_id": "a1", "same_character": True, "failure_reasons": []},
        {"pair_id": pair1.pair_id, "annotator_id": "a2", "same_character": False, "failure_reasons": ["wrong_colour"]},
        {"pair_id": pair1.pair_id, "annotator_id": "adj1", "same_character": False, "failure_reasons": ["wrong_colour"]},
        {"pair_id": pair2.pair_id, "annotator_id": "a1", "same_character": True, "failure_reasons": []},
        {"pair_id": pair2.pair_id, "annotator_id": "a2", "same_character": True, "failure_reasons": []},
    ]
    with patch("finetune.build_dataset.fetch_annotations", return_value=raw_annotations), \
         patch("finetune.build_dataset.fetch_adjudicator_ids", return_value={"adj1"}), \
         patch("finetune.build_dataset.fetch_pilot_pairs", return_value=set()):
        records = bd.build_dataset([(mem, "train", "synthetic")], out_path=out, add_constructed=False)

    assert len(records) == 2
    stats_out = tmp_path / "dataset_manifest.json"
    stats = json.loads(stats_out.read_text(encoding="utf-8"))
    assert stats["overall"]["characters"] == 1
    assert stats["overall"]["natural_pairs"] == 2
    assert stats["overall"]["constructed_pairs"] == 0
    assert stats["overall"]["total_pairs"] == 2
    assert stats["class_balance"]["same_character"] == 1
    assert stats["class_balance"]["different_character"] == 1
    assert stats["failure_reasons"] == {"wrong_colour": 1}
    assert stats["adjudication_rate"] == 0.5
    assert len(stats["dataset_sha256"]) == 64


def test_candidate_report_cli(tmp_path, capsys):
    data_dir = tmp_path / "corpus"
    freeze_bundle(data_dir, fixture=True)
    with (
        patch("finetune.build_dataset.get_supabase_client", side_effect=RuntimeError("remote not allowed")),
        patch("finetune.build_dataset.fetch_annotations", side_effect=RuntimeError("remote not allowed")),
        patch("finetune.build_dataset.freeze_dataset", side_effect=RuntimeError("freeze not allowed")),
    ):
        ret = bd.main(["--candidate-report", "--data", str(data_dir)])

    assert ret == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert isinstance(report, list)
    assert len(report) == 1
    assert report[0]["reference_char_id"] == "story-freeze:char-freeze"


# --- reference verification status (ADR-028) -----------------------------------------------

def test_build_records_stamps_the_reference_verification_status_on_every_pair():
    """`char_bible` ships `ref_verdict=None` when the judge call itself fails. That anchor is
    what every pair built on it is measured against, so the status travels with the pair."""
    unchecked = memory()
    pairs = bd.pairs_from_memory(unchecked)
    keyed = {
        pair.pair_id: bd.Consensus(
            same_character=True, failure_reasons=[], anatomy_intact=True, text_free=True,
        )
        for pair in pairs
    }
    records = bd.build_records(unchecked, "train", "synthetic", keyed, set())
    assert [r.ref_verdict_status for r in records] == ["unverified", "unverified"]

    checked = memory()
    checked.characters[0].ref_verdict = RefVerdict(
        differences_observed="", matches_description=True, contradictions=[], text_free=True,
    )
    records = bd.build_records(checked, "train", "synthetic", keyed, set())
    assert [r.ref_verdict_status for r in records] == ["passed", "passed"]


def test_constructed_negatives_inherit_the_reference_characters_status():
    """The constructed pair's anchor is the REFERENCE character's image, so it carries the
    reference's status — not the target's, whose reference is never shown to the model."""
    records = [
        manifest_record("ref", "story-a:a", "ref/a.png", "scene/a.webp", ref_verdict_status="unverified"),
        manifest_record("target", "story-b:b", "ref/b.png", "scene/b.webp", ref_verdict_status="passed"),
    ]
    made = bd.constructed_records(records, {"story-a:a": "story-b:b"})
    assert [row.ref_verdict_status for row in made] == ["unverified"]


def test_build_dataset_statistics_count_unverified_reference_anchors(tmp_path):
    out = tmp_path / "manifest.jsonl"
    mem = memory()
    pairs = bd.pairs_from_memory(mem)
    raw_annotations = [
        {"pair_id": pair.pair_id, "annotator_id": annotator, "same_character": True, "failure_reasons": []}
        for pair in pairs
        for annotator in ("a1", "a2")
    ]
    with patch("finetune.build_dataset.fetch_annotations", return_value=raw_annotations), \
         patch("finetune.build_dataset.fetch_adjudicator_ids", return_value=set()), \
         patch("finetune.build_dataset.fetch_pilot_pairs", return_value=set()):
        bd.build_dataset([(mem, "train", "synthetic")], out_path=out, add_constructed=False)

    stats = json.loads((tmp_path / "dataset_manifest.json").read_text(encoding="utf-8"))
    assert stats["reference_verification"] == {"unverified": 2}


# --- single-rater test-retest (rounds) ------------------------------------------------------
# One human labels every pair twice, cold (annotation-surface.md §4.1, settled 2026-07-29:
# this capstone has exactly one rater, permanently). The two rounds are the two ordinary
# labels the consensus machinery already expects; a third round is the adjudication.


def solo_rows(pair_id, *specs, annotator="solo"):
    """Rows that all carry the SAME annotator_id and differ only by `round`."""
    out = []
    for i, spec in enumerate(specs):
        row = {"pair_id": pair_id, "annotator_id": annotator, "round": i + 1,
               "failure_reasons": [], "anatomy_intact": True, "text_free": True}
        row.update(spec)
        out.append(row)
    return out


def test_two_rounds_from_one_rater_are_the_two_ordinary_labels():
    resolved = bd.resolve_annotations(
        solo_rows("p1", {"same_character": True}, {"same_character": True}),
        set(), set(),
    )
    assert resolved["p1"].same_character is True
    assert resolved["p1"].adjudicated is False


def test_round_three_by_the_same_rater_adjudicates_a_test_retest_disagreement():
    with pytest.raises(ManifestError, match="unresolved conflict"):
        bd.resolve_annotations(
            solo_rows("p1", {"same_character": True}, {"same_character": False}),
            set(), set(),
        )

    resolved = bd.resolve_annotations(
        solo_rows(
            "p1",
            {"same_character": True},
            {"same_character": False, "failure_reasons": ["wrong_clothing"]},
            {"same_character": False, "failure_reasons": ["wrong_colour"]},
        ),
        set(), set(),
    )
    # The round-3 row is authoritative, exactly as a third annotator's row would be.
    assert resolved["p1"].same_character is False
    assert resolved["p1"].adjudicated is True
    assert resolved["p1"].failure_reasons == ["wrong_colour"]


def test_round_three_is_rejected_when_the_two_rounds_agreed():
    with pytest.raises(ManifestError, match="ordinary annotators agreed, but adjudicator row exists"):
        bd.resolve_annotations(
            solo_rows(
                "p1",
                {"same_character": True},
                {"same_character": True},
                {"same_character": False},
            ),
            set(), set(),
        )


def test_the_same_round_twice_from_one_rater_is_a_duplicate_not_a_second_label():
    with pytest.raises(ManifestError, match="duplicate"):
        bd.resolve_annotations(
            [
                {"pair_id": "p1", "annotator_id": "solo", "round": 1, "same_character": True},
                {"pair_id": "p1", "annotator_id": "solo", "round": 1, "same_character": True},
            ],
            set(), set(),
        )


def test_one_rater_one_round_is_still_an_incomplete_pair():
    with pytest.raises(ManifestError, match="<2 ordinary annotations"):
        bd.resolve_annotations(solo_rows("p1", {"same_character": True}), set(), set())


def test_reconcile_pair_status_derives_every_state_from_rounds_of_one_rater():
    annotation_rows = [
        {"pair_id": "pending", "annotator_id": None},
        *solo_rows("partial", {"same_character": True}),
        *solo_rows("complete", {"same_character": True}, {"same_character": True}),
        *solo_rows("conflicted", {"same_character": True}, {"same_character": False}),
        *solo_rows(
            "adjudicated",
            {"same_character": True},
            {"same_character": False},
            {"same_character": False},
        ),
    ]
    assert bd.reconcile_pair_status(annotation_rows, set()) == {
        "pending": "pending",
        "partial": "partially_annotated",
        "complete": "complete",
        "conflicted": "conflicted",
        "adjudicated": "adjudicated",
    }


def test_a_distinct_adjudicator_profile_still_overrides_round_one_and_two():
    """Two genuine annotators never materialized, but the mechanism must not be removed."""
    resolved = bd.resolve_annotations(
        [
            {"pair_id": "p1", "annotator_id": "a1", "round": 1, "same_character": True},
            {"pair_id": "p1", "annotator_id": "a2", "round": 1, "same_character": False},
            {"pair_id": "p1", "annotator_id": "adj", "round": 1, "same_character": False,
             "failure_reasons": ["wrong_species"]},
        ],
        {"adj"}, set(),
    )
    assert resolved["p1"].adjudicated is True
    assert resolved["p1"].failure_reasons == ["wrong_species"]


def test_rows_without_a_round_column_are_treated_as_round_one():
    """Pre-0018 rows carry no `round` key; they must keep resolving unchanged."""
    resolved = bd.resolve_annotations(
        rows("p1", {"same_character": True}, {"same_character": True}), set(), set()
    )
    assert resolved["p1"].same_character is True


def test_freeze_agreement_evidence_pairs_round_one_against_round_two(tmp_path):
    """annotation_agreement.jsonl is the intra-rater statistic's only evidence: exactly the
    two ordinary rounds, in round order, with the round-3 adjudication excluded."""
    data_dir = tmp_path / "corpus"
    run_bundle = freeze_bundle(data_dir)
    pair_id = bd.pairs_from_memory(run_bundle.memory)[0].pair_id
    annotations = solo_rows(
        pair_id,
        {"same_character": False, "failure_reasons": ["wrong_colour"]},
        {"same_character": True},
        {"same_character": True},
    )
    out_dir = tmp_path / "freeze"

    with (
        patch.object(fd, "fetch_annotations", return_value=annotations),
        patch.object(fd, "fetch_adjudicator_ids", return_value=set()),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
    ):
        report = bd.freeze_dataset(data_dir, out_dir)

    assert report.adjudication_rate == 1.0
    [evidence] = [
        json.loads(line)
        for line in (out_dir / "annotation_agreement.jsonl").read_text().splitlines()
    ]
    assert evidence == {"pair_id": pair_id, "labels": [False, True]}
