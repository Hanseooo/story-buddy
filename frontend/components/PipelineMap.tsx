import { ArrowsClockwise, ShieldCheck, PaintBrush, CheckCircle, Database, Robot, Warning, Eye, UserCheck, Swap, Palette } from "@phosphor-icons/react/dist/ssr";
import { ReactNode } from "react";

type Mode = "both" | "teacher-review";

// One entry per `add_node` in backend/pipeline/graph.py, in flow order. components/PipelineMap.test.tsx
// compares these ids with that file, so a node added there fails the test until it is added here.
const NODES: { id: string; title: string; desc: string; mode: Mode; icon: ReactNode; edges?: string }[] = [
  {
    id: "input_gate", title: "Input Gate", mode: "both", icon: <ShieldCheck weight="duotone" className="size-6" />,
    desc: "meta-llama/llama-guard-4-12b text check (gpt-oss-safeguard backstop) + Presidio identifier redaction.",
    edges: "Flagged text stops the job. In teacher-review mode it goes to Teacher Review instead.",
  },
  {
    id: "optional_themes", title: "Optional Themes", mode: "teacher-review", icon: <Palette weight="duotone" className="size-6" />,
    desc: "Checks the themes the teacher chose for the class before the story is analyzed.",
    edges: "Runs only when themes are chosen. A flagged theme goes to Teacher Review.",
  },
  { id: "analyze", title: "Analyze", mode: "both", icon: <Robot weight="duotone" className="size-6" />, desc: "Mistral Small 3.2 lists the characters, objects and places." },
  { id: "segment", title: "Segment", mode: "both", icon: <Robot weight="duotone" className="size-6" />, desc: "Mistral Small 3.2 splits the story into pages and writes each drawing direction." },
  { id: "char_bible", title: "Character Bible", mode: "both", icon: <PaintBrush weight="duotone" className="size-6" />, desc: "fal.ai Qwen-Image draws one canonical reference per main character." },
  {
    id: "char_ref_mod", title: "Char Ref Mod", mode: "both", icon: <Warning weight="duotone" className="size-6" />,
    desc: "Mistral Small 3.2 image safety check + Gemma-3-27B rubric backstop.",
    edges: "A flagged reference is redrawn once. After that the job stops, or in teacher-review mode goes to Teacher Review.",
  },
  {
    id: "reveal", title: "Reveal", mode: "both", icon: <Eye weight="duotone" className="size-6" />,
    desc: "Pauses until the references are accepted; up to 3 “try again” taps redraw them. The magic pencil and “other versions” also act here.",
    edges: "Try again loops back to Character Bible. A held pencil text goes to Teacher Review.",
  },
  { id: "generate_scene", title: "Generate Scene", mode: "both", icon: <PaintBrush weight="duotone" className="size-6" />, desc: "fal.ai Qwen-Image-Edit draws each page from the references." },
  {
    id: "consistency_check", title: "Consistency Check", mode: "both", icon: <CheckCircle weight="duotone" className="size-6" />,
    desc: "Gemma-3-27B judge compares each page with the references.",
    edges: "A failed page goes to Regenerate. A passed page goes on to Output Mod.",
  },
  {
    id: "regenerate", title: "Regenerate", mode: "both", icon: <ArrowsClockwise weight="bold" className="size-5" />,
    desc: "Up to two retries with the judge’s reasons; the best attempt is kept.",
    edges: "Goes back to Consistency Check.",
  },
  {
    id: "output_mod", title: "Output Mod", mode: "both", icon: <ShieldCheck weight="duotone" className="size-6" />,
    desc: "Safety pass on each finished page, inside the scene loop.",
    edges: "Next page loops back to Generate Scene. A flagged page stops the job, or in teacher-review mode goes to Teacher Review.",
  },
  {
    id: "moderation_review", title: "Teacher Review", mode: "teacher-review", icon: <UserCheck weight="duotone" className="size-6" />,
    desc: "The job is held until the teacher allows, replaces or stops what was flagged.",
    edges: "Allow resumes where the job stopped. Replace goes to Replace. Stop on a pencil text returns to Reveal.",
  },
  {
    id: "moderation_replace", title: "Replace", mode: "teacher-review", icon: <Swap weight="duotone" className="size-6" />,
    desc: "Swaps in a new drawing for a flagged reference or page.",
    edges: "A reference goes back to Char Ref Mod. A page goes back to Consistency Check.",
  },
  { id: "compose", title: "Compose", mode: "both", icon: <Database weight="duotone" className="size-6" />, desc: "Assembles the book and writes it to Supabase." },
];

const LOOP = ["generate_scene", "consistency_check", "regenerate", "output_mod"];
const TEACHER_BRANCH =["moderation_review", "moderation_replace"];

const MODE_LABEL: Record<Mode, string> = { both: "Both modes", "teacher-review": "Teacher review only" };

const FlowNode = ({ node }: { node: (typeof NODES)[number] }) => {
  const teacher = node.mode === "teacher-review";
  return (
    <li
      data-node={node.id}
      data-mode={node.mode}
      className={`relative z-10 flex w-full max-w-[420px] flex-col gap-2 rounded-2xl p-4 neo-shadow-sm sm:p-5 ${
        teacher ? "border-2 border-secondary/30 bg-secondary/10 text-secondary-deep" : "neo-border bg-surface text-foreground"
      }`}
    >
      <div className="flex items-center gap-3">
        <div className={`rounded-xl p-2 ${teacher ? "bg-secondary/20" : "bg-primary/10 text-primary"}`}>{node.icon}</div>
        <h3 className="font-mono text-sm font-bold tracking-tight md:text-base">{node.title}</h3>
      </div>
      <p className="text-xs font-medium leading-relaxed sm:text-sm">{node.desc}</p>
      {node.edges && <p className="text-xs font-medium leading-relaxed text-foreground/70">{node.edges}</p>}
      <p className={`w-fit rounded-full px-2 py-0.5 text-[11px] font-bold ${teacher ? "bg-secondary/20" : "bg-primary/10 text-primary"}`}>
        {MODE_LABEL[node.mode]}
      </p>
    </li>
  );
};

const Arrow = () => (
  <li aria-hidden className="relative my-1 h-8 w-[2px] bg-primary/30">
    <span className="absolute -bottom-[5px] left-1/2 size-0 -translate-x-1/2 border-x-[5px] border-t-[6px] border-x-transparent border-t-primary/80" />
  </li>
);

function Chain({ ids }: { ids: string[] }) {
  return ids.map((id, i) => (
    <FlowNodeWithArrow key={id} id={id} last={i === ids.length - 1} />
  ));
}

function FlowNodeWithArrow({ id, last }: { id: string; last: boolean }) {
  const node = NODES.find((n) => n.id === id)!;
  return (
    <>
      <FlowNode node={node} />
      {!last && <Arrow />}
    </>
  );
}

export default function PipelineMap() {
  const before = NODES.map((n) => n.id).slice(0, NODES.findIndex((n) => n.id === LOOP[0]));  return (
    <div className="relative mx-auto w-full max-w-4xl px-4 py-10">
      <div className="pointer-events-none absolute left-1/2 top-1/2 -z-20 aspect-square w-full max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/5 blur-3xl" />

      <p className="mx-auto mb-6 max-w-[420px] text-sm font-medium text-foreground/80">
        14 nodes in total. 11 run in baseline mode, the mode the study corpus was made in. All 14 run in
        teacher-review mode, the default since 2026-11-21. Nodes marked “Teacher review only” are skipped in baseline mode.
      </p>

      <ol aria-label="Pipeline nodes" className="relative z-0 flex flex-col items-center">
        <Chain ids={before} />
        <Arrow />
        <li className="w-full max-w-[460px] list-none rounded-3xl border-2 border-dashed border-secondary/60 p-3 sm:p-4">
          <p className="mb-3 text-center text-xs font-bold text-secondary-deep">Scene loop: repeats for every page</p>
          <ol aria-label="Scene loop" className="flex flex-col items-center">
            <Chain ids={LOOP} />
          </ol>
        </li>
        <Arrow />
        <FlowNodeWithArrow id="compose" last />
      </ol>

      <section aria-labelledby="teacher-branch" className="mx-auto mt-8 flex w-full max-w-[460px] flex-col items-center gap-3">
        <h3 id="teacher-branch" className="text-center text-sm font-bold text-secondary-deep">
          Teacher-review branch: entered from Input Gate, Optional Themes, Char Ref Mod, Reveal or Output Mod
        </h3>
        <ol aria-label="Teacher-review branch" className="flex flex-col items-center">
          <Chain ids={TEACHER_BRANCH} />
        </ol>
      </section>
    </div>
  );
}
