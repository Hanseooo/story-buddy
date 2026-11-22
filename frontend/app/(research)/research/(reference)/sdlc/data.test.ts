import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import * as data from "./data";

const REPO_ROOT = path.resolve(__dirname, "../../../../../..");
const raw = (file: string) => readFileSync(path.join(REPO_ROOT, file), "utf8");
// One line of text: wrapped lines joined, and the bold and italic marks of the source dropped.
const read = (file: string) => raw(file).replace(/\*+/g, "").replace(/\s+/g, " ");
const states = (text: string, sentence: string) => expect(text.includes(sentence), sentence).toBe(true);

const record = raw(data.SOURCES.record);
const cells = (line: string) => line.split("|").slice(1, -1).map((c) => c.trim());

// §5 of the record: | #N | `hash` | date | title | loop |
const PR_ROWS = [...record.matchAll(/^\| #(\d+) \| `([0-9a-f]+)` \| (\d{4}-\d{2}-\d{2}) \| (.+) \| (\d) \|$/gm)].map((m) => ({
  pr: Number(m[1]),
  hash: m[2],
  date: m[3],
  title: m[4],
  loop: Number(m[5]),
}));
// §2 of the record: | loop | phase | risk | PRs | first | last | gate | result |
const LOOP_ROWS = record
  .split("\n")
  .filter((l) => /^\| [1-6] \| /.test(l))
  .map(cells);

function git(...args: string[]): string | null {
  try {
    const shallow = execFileSync("git", ["rev-parse", "--is-shallow-repository"], { cwd: REPO_ROOT }).toString().trim();
    if (shallow === "true") return null;
    return execFileSync("git", args, { cwd: REPO_ROOT, maxBuffer: 1 << 24 }).toString();
  } catch {
    return null;
  }
}

describe("SDLC record against git", () => {
  it("lists 68 merged PRs, from #1 to #134", () => {
    expect(PR_ROWS).toHaveLength(68);
    expect(PR_ROWS[0].pr).toBe(1);
    expect(PR_ROWS.at(-1)?.pr).toBe(134);
  });

  // Skips its checks where history is missing (a shallow clone); CI fetches full history (ci.yml).
  it("matches each row's merge commit: PR number, date and title", () => {
    const noBody: number[] = [];
    for (const row of PR_ROWS) {
      const out = git("log", "-1", "--format=%s%n%cs%n%b", row.hash);
      if (out === null) return;
      const [subject, date, body] = out.split("\n");
      expect(subject, `#${row.pr}`).toMatch(new RegExp(`^Merge pull request #${row.pr} from `));
      expect(date, `#${row.pr}`).toBe(row.date);
      if (body.trim() === "") noBody.push(row.pr);
      else expect(body.trim(), `#${row.pr}`).toBe(row.title);
    }
    // The record names these three as copied from GitHub.
    expect(noBody).toEqual([79, 128, 129]);
    // One git call per row: 68 of them can pass 5 s while the full suite runs.
  }, 60_000);

  it("leaves out no PR merged up to #134", () => {
    const out = git("log", "--merges", "--format=%s");
    if (out === null) return;
    const merged = [...out.matchAll(/^Merge pull request #(\d+) from /gm)].map((m) => Number(m[1])).filter((n) => n <= 134);
    expect([...new Set(merged)].sort((a, b) => a - b)).toEqual(PR_ROWS.map((r) => r.pr));
  });
});

describe("SDLC loop table", () => {
  it("has six loops whose counts and dates agree with the PR rows", () => {
    expect(LOOP_ROWS.map((r) => r[0])).toEqual(["1", "2", "3", "4", "5", "6"]);
    for (const [loop, , , count, first, last] of LOOP_ROWS) {
      const dates = PR_ROWS.filter((r) => r.loop === Number(loop)).map((r) => r.date).sort();
      expect(String(dates.length), `loop ${loop}`).toBe(count);
      expect(dates[0] ?? "—", `loop ${loop}`).toBe(first);
      expect(dates.at(-1) ?? "—", `loop ${loop}`).toBe(last);
    }
  });

  // Hand-counted from the generated rows on 2026-11-22.
  it("puts 0, 21, 20, 17, 5 and 5 PRs in loops 1 to 6", () => {
    expect(data.LOOPS.map((l) => l.prs)).toEqual([0, 21, 20, 17, 5, 5]);
  });
});

describe("SDLC page data", () => {
  it("copies each loop from the record's loop table", () => {
    expect(data.LOOPS).toHaveLength(6);
    for (const l of data.LOOPS) {
      const row = LOOP_ROWS.find((r) => r[0] === String(l.loop))!;
      expect(row.slice(1, 8), `loop ${l.loop}`).toEqual([l.phase, l.risk, String(l.prs), l.first ?? "—", l.last ?? "—", l.gate, l.result]);
    }
  });

  // The label must say what the sentence says: each outcome's opening words, written by hand.
  it("marks each gate result with the outcome its sentence states", () => {
    const opens: Record<data.Outcome, string> = {
      split: "Split.",
      "not run": "Not run.",
      partial: "Partial.",
      relaxed: "Shipped off by default, then turned on",
      open: "Open.",
    };
    for (const l of data.LOOPS) expect(l.result.startsWith(opens[l.outcome]), `loop ${l.loop}: ${l.outcome}`).toBe(true);
    // Loop 2 is partial since 2026-11-22: its judge passed 29 of 77 defective pages.
    expect(data.LOOPS.map((l) => l.outcome)).toEqual(["split", "partial", "not run", "partial", "relaxed", "open"]);
  });

  it("takes each deviation from the record", () => {
    const flat = read(data.SOURCES.record);
    for (const d of data.DEVIATIONS) states(flat, `${d.title} ${d.detail}`);
  });

  it("keeps methodology.md §1.3 in step with the record", () => {
    const methodology = raw(data.SOURCES.methodology);
    for (const l of data.LOOPS) {
      states(methodology, `| ${l.loop} | ${l.phase} | ${l.risk} | ${l.gate} | ${l.result} |`);
    }
  });

  // Hand-written ranges, checked against the record's rows: a run of three or more numbers is a range.
  it("lists each loop's PRs as the record assigns them", () => {
    for (const l of data.LOOPS) {
      const listed = l.prList === "" ? [] : l.prList.split(", ").flatMap((part) => {
        const [a, b] = part.split("–").map((x) => Number(x.slice(1)));
        if (b === undefined) return [a];
        expect(b - a, part).toBeGreaterThanOrEqual(2);
        return Array.from({ length: b - a + 1 }, (_, i) => a + i);
      });
      expect(listed, `loop ${l.loop}`).toEqual(PR_ROWS.filter((r) => r.loop === l.loop).map((r) => r.pr));
    }
  });

  it("records the Phase 0.5 gate result as both documents state it", () => {
    states(read(data.SOURCES.phase05), data.PHASE_05.recorded);
    states(read(data.SOURCES.methodology), data.PHASE_05.methodology);
  });

  // The loop 2 counts the script printed, against the audit they come from.
  it("takes loop 2's judge miss count from the October audit", () => {
    states(read("docs/capstone/pipeline-stage-audit-2026-10.md"), "Of the 77 defective shipped pages, 29 passed the stored gate");
    expect(data.LOOPS[1].result).toContain("passed 29 of 77 defective pages");
  });

  it("names the model as methodology.md does", () => {
    states(read(data.SOURCES.methodology), data.MODEL);
  });
});
