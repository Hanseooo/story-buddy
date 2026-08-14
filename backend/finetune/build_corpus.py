"""Turn `corpus_synthetic.json` into judge training images (spec `docs/specs/judge-finetune.md` §5.3).

Runs the **existing** Phase-1 pipeline — `pipeline.graph.build_graph()`, driven exactly the way
`worker/run_job.py` drives it — over each checked-in story, then downloads the canonical
references and the finalized scene images into `data/judge/ref/` and `data/judge/scene/`.
Nothing about the pipeline is forked, reimplemented or configured differently; if the pipeline
changes, so does this corpus, which is the point.

    uv run python -m finetune.build_corpus --budget 40          # from backend/

**Every image is a paid fal.ai draw ($0.02–0.035).** `--budget` is a hard ceiling on the number
of images this script will let the pipeline draw, checked after every super-step, and it is the
most important line in the file (§6.2). It defaults deliberately low: spending real money is an
explicit act, not something you get by forgetting a flag.

Resume: a story that finished is recorded in `data/judge/build_state.json` and is never
resubmitted. That guard is NOT redundant with `generate_scene`'s CC-10 Storage-exists skip —
the skip makes a *re-executed scene* free, but `char_bible.mint_reference` has no exists-check
at all, so re-entering a finished story would redraw and re-bill every canonical reference
(up to 3 draws each). Mid-story resume comes from the LangGraph Postgres checkpointer, keyed on
`thread_id = story_id`, the same mechanism `resume_storybook_job` uses.
"""
import argparse
import json
import pathlib
import sys

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command

from app.config import RECURSION_LIMIT, STYLE_PRESETS, settings
from app.db import get_supabase_client
from app.length import word_count
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, Style, StoryMemory
from finetune.manifest import local_image_path
from pipeline.graph import build_graph

CORPUS_PATH = pathlib.Path(__file__).with_name("corpus_synthetic.json")
# `backend/finetune/build_corpus.py` -> repo root -> `data/judge/` (spec §5.3, gitignored).
DATA_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "judge"
STATE_FILE = "build_state.json"
BUCKET = "storybook-images"

# fal.ai per-image price band (§5.4). Reported as a range because the two models differ.
COST_LOW, COST_HIGH = 0.02, 0.035

# ponytail: 40 images ≈ three stories. Low enough that a mistyped command costs about a dollar,
# and the whole 30-story run is a deliberate `--budget 500`. Ceiling: it is a count, not dollars,
# so a price change needs the band above updated too.
DEFAULT_BUDGET = 40

# The reveal (ADR-029) interrupts once per book, and `route_reveal` can loop it up to
# MAX_RETRY_TAPS times. This script always confirms, so one resume is the expected case; the
# cap only exists so a pathological graph cannot spin here forever.
MAX_RESUMES = 4
CONFIRM = {"action": "confirm"}

# ponytail: one style for the whole corpus. Style diversity in the training set is a research
# decision (§3.1 shortcut learning), not a scripting one — add a per-story `style_preset_id`
# key and read it here if that decision lands.
STYLE_ID = "cel"


def load_corpus(path: pathlib.Path = CORPUS_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _image_count(values: dict | None) -> int:
    cost = (values or {}).get("cost")
    return getattr(cost, "image_count", 0) if cost is not None else 0


def _initial_state(story: dict) -> StoryMemory:
    """Byte-for-byte the shape `run_job.run_storybook_job` builds, minus the `jobs` row.

    `classroom_id` / `profile_id` are required by the contract but read by no pipeline node
    (grepped); a corpus run has no classroom, so it says so rather than borrowing a real one.
    """
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id=story["story_id"],
        classroom_id="judge-corpus",
        profile_id="judge-corpus",
        input=Input(raw_text=story["text"], word_count=word_count(story["text"]), truncated=False),
        style=Style(style_preset_id=STYLE_ID, prompt_fragment=STYLE_PRESETS[STYLE_ID]),
    )


def run_story(app_graph, story: dict, budget_left: int) -> tuple[dict, int, bool]:
    """Drive one story through the graph. Returns `(values, images_drawn, halted)`.

    THE SPEND CAP. `cost.image_count` is re-read after every `values` chunk — i.e. after every
    super-step — and the moment it reaches `budget_left` the loop **breaks**, abandoning the
    generator. Abandoning it is what makes this a stop rather than a tally: LangGraph only runs
    the next node when the consumer asks for the next chunk.
    """
    config = {"configurable": {"thread_id": story["story_id"]}, "recursion_limit": RECURSION_LIMIT}
    graph_input = _initial_state(story)
    values: dict = {}

    for _ in range(MAX_RESUMES + 1):
        interrupted = False
        for chunk in app_graph.stream(graph_input, config, stream_mode=["updates", "values"]):
            # 2-tuple (mode, payload) top-level, 3-tuple (ns, mode, payload) for subgraphs —
            # the same unpacking `run_job._run_with_progress` does.
            mode, payload = chunk[-2:]
            if mode == "values":
                values = payload
                if _image_count(values) >= budget_left:
                    return values, _image_count(values), True
            elif "__interrupt__" in payload:
                interrupted = True
        if not interrupted:
            return values, _image_count(values), False
        graph_input = Command(resume=CONFIRM)

    return values, _image_count(values), False


def download_images(values: dict, out_dir: pathlib.Path, supabase) -> tuple[int, int]:
    """Land the two image classes where §5.3 says they go. Free — Storage reads are not billed.

    The local filename is the durable Storage path with `/` replaced by `_`, so it is unique
    across stories (the path is prefixed with `story_id`) and losslessly reversible. Inventing a
    naming scheme here would be a second source of truth for something the pipeline already
    decided.
    """
    counts = {"ref": 0, "scene": 0}
    targets = [
        ("ref", c.canonical_ref_image)
        for c in values.get("characters") or []
        if c.canonical_ref_image
    ]
    targets += [
        ("scene", s.final_image_ref) for s in values.get("scenes") or [] if s.final_image_ref
    ]

    for kind, path in targets:
        local = pathlib.Path(local_image_path(path, kind, root=out_dir))
        counts[kind] += 1
        if local.exists():
            continue
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(supabase.storage.from_(BUCKET).download(path))
    return counts["ref"], counts["scene"]


def build(stories: list[dict], app_graph, budget: int, out_dir: pathlib.Path, supabase) -> dict:
    """The loop: skip what is done, run what is not, stop the moment the budget is gone."""
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = out_dir / STATE_FILE
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}

    spent = 0
    summary = {
        "stories_run": 0, "stories_skipped": 0, "characters": 0, "scenes": 0,
        "images_spent": 0, "halted": False,
    }

    for story in stories:
        story_id = story["story_id"]
        if story_id in state:
            summary["stories_skipped"] += 1
            continue

        budget_left = budget - spent
        if budget_left <= 0:
            summary["halted"] = True
            break

        values, drawn, halted = run_story(app_graph, story, budget_left)
        spent += drawn
        refs, scenes = download_images(values, out_dir, supabase)
        print(
            f"{story_id}: images={drawn} refs={refs} scenes={scenes} "
            f"total={spent}/{budget} (${spent * COST_LOW:.2f}-${spent * COST_HIGH:.2f})"
            + ("  ** BUDGET REACHED — HALTED **" if halted else ""),
            flush=True,
        )
        if halted:
            # Deliberately NOT recorded as done: the book is unfinished, and a resume must be
            # allowed to pick it back up from the checkpointer.
            summary["halted"] = True
            break

        state[story_id] = {"images": drawn, "characters": refs, "scenes": scenes}
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        summary["stories_run"] += 1
        summary["characters"] += refs
        summary["scenes"] += scenes

    summary["images_spent"] = spent
    summary["usd_low"] = round(spent * COST_LOW, 2)
    summary["usd_high"] = round(spent * COST_HIGH, 2)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET,
                        help=f"hard ceiling on paid images (default {DEFAULT_BUDGET})")
    parser.add_argument("--corpus", type=pathlib.Path, default=CORPUS_PATH)
    parser.add_argument("--out", type=pathlib.Path, default=DATA_DIR)
    parser.add_argument("--limit", type=int, default=None, help="run only the first N stories")
    args = parser.parse_args(argv)

    stories = load_corpus(args.corpus)[: args.limit]
    supabase = get_supabase_client()

    with PostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
        checkpointer.setup()
        summary = build(stories, build_graph(checkpointer=checkpointer), args.budget, args.out, supabase)

    print(
        "\n--- summary ---\n"
        f"stories run:      {summary['stories_run']}\n"
        f"stories skipped:  {summary['stories_skipped']} (already built)\n"
        f"characters minted:{summary['characters']}\n"
        f"scenes drawn:     {summary['scenes']}\n"
        f"images spent:     {summary['images_spent']} / {args.budget}\n"
        f"estimated cost:   ${summary['usd_low']:.2f}-${summary['usd_high']:.2f}\n"
        f"halted on budget: {summary['halted']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
