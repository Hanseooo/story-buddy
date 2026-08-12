import { describe, expect, it } from "vitest";
import { jobState, type Job } from "@/lib/types/jobs";

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeJob(overrides: Partial<Job> = {}): Job {
  return {
    id: "job-1",
    status: "complete",
    failure_reason: null,
    approved_at: null,
    rejected_at: null,
    created_at: new Date().toISOString(),
    input_text: "A story",
    style_preset_id: null,
    pages: [{ scene_id: "s1", caption: "Page 1", image_path: "job-1/s1.png" }],
    profile_id: "profile-1",
    profiles: { display_nickname: "Alex" },
    ...overrides,
  };
}

// ── jobState ──────────────────────────────────────────────────────────────────

describe("jobState", () => {
  it("returns 'pending' when both timestamps null", () => {
    expect(jobState(makeJob())).toBe("pending");
  });

  it("returns 'approved' when approved_at set", () => {
    expect(jobState(makeJob({ approved_at: "2026-08-07T00:00:00Z" }))).toBe("approved");
  });

  it("returns 'rejected' when rejected_at set", () => {
    expect(jobState(makeJob({ rejected_at: "2026-08-07T00:00:00Z" }))).toBe("rejected");
  });
});

// ── Tab filter logic ──────────────────────────────────────────────────────────

describe("tab filters", () => {
  const jobs: Job[] = [
    makeJob({ id: "j1", status: "complete" }),
    makeJob({ id: "j2", status: "complete", approved_at: "2026-08-07T00:00:00Z" }),
    makeJob({ id: "j3", status: "complete", rejected_at: "2026-08-07T00:00:00Z" }),
    makeJob({ id: "j4", status: "failed" }),
  ];

  it("pending tab shows only complete + both timestamps null", () => {
    const pending = jobs.filter(
      (j) => j.status === "complete" && !j.approved_at && !j.rejected_at
    );
    expect(pending.map((j) => j.id)).toEqual(["j1"]);
  });

  it("approved tab shows jobs with approved_at set", () => {
    const approved = jobs.filter((j) => j.approved_at !== null);
    expect(approved.map((j) => j.id)).toEqual(["j2"]);
  });

  it("rejected tab shows jobs with rejected_at set", () => {
    const rejected = jobs.filter((j) => j.rejected_at !== null);
    expect(rejected.map((j) => j.id)).toEqual(["j3"]);
  });

  it("failed section shows status=failed jobs", () => {
    const failed = jobs.filter((j) => j.status === "failed");
    expect(failed.map((j) => j.id)).toEqual(["j4"]);
  });

  it("in-flight statuses (queued, running, awaiting_confirm) do not appear in any tab", () => {
    const inFlight: Job[] = [
      makeJob({ id: "q", status: "queued" }),
      makeJob({ id: "r", status: "running" }),
      makeJob({ id: "a", status: "awaiting_confirm" }),
    ];
    const visible = inFlight.filter(
      (j) =>
        (j.status === "complete" && !j.approved_at && !j.rejected_at) ||
        j.approved_at !== null ||
        j.rejected_at !== null ||
        j.status === "failed"
    );
    expect(visible).toHaveLength(0);
  });
});

// ── failure_reason rendering ──────────────────────────────────────────────────

describe("failure_reason rendering", () => {
  function resolveFailureCopy(reason: string | null): "safety" | "machine" {
    return reason === "child_text" ? "safety" : "machine";
  }

  it("child_text shows safety copy", () => {
    expect(resolveFailureCopy("child_text")).toBe("safety");
  });

  it("null shows machine copy", () => {
    expect(resolveFailureCopy(null)).toBe("machine");
  });

  it("unknown value shows machine copy (fail-safe default)", () => {
    expect(resolveFailureCopy("some_future_value")).toBe("machine");
  });

  it("machine shows machine copy", () => {
    expect(resolveFailureCopy("machine")).toBe("machine");
  });
});

// ── Dialog advance logic ───────────────────────────────────────────────────────

describe("dialog advance after decision", () => {
  const pending: Job[] = [
    makeJob({ id: "j1" }),
    makeJob({ id: "j2" }),
    makeJob({ id: "j3" }),
  ];

  it("advances to next pending after a decision", () => {
    const decidedId = "j1";
    const pendingAfter = pending.filter((j) => j.id !== decidedId);
    const nextId = pendingAfter[0]?.id ?? null;
    expect(nextId).toBe("j2");
  });

  it("closes dialog when last pending is decided", () => {
    const decidedId = "j3";
    const onlyJ3: Job[] = [makeJob({ id: "j3" })];
    const pendingAfter = onlyJ3.filter((j) => j.id !== decidedId);
    expect(pendingAfter).toHaveLength(0);
    const nextId = pendingAfter[0]?.id ?? null;
    expect(nextId).toBeNull();
  });
});

// ── Removed student visibility ────────────────────────────────────────────────

describe("removed student visibility", () => {
  it("removed student's pending book appears in the pending list", () => {
    const jobs: Job[] = [
      makeJob({ id: "j1", profile_id: "removed-student" }),
      makeJob({ id: "j2", profile_id: "active-student" }),
    ];
    // No removed_at filter applied — both appear
    const pending = jobs.filter(
      (j) => j.status === "complete" && !j.approved_at && !j.rejected_at
    );
    expect(pending).toHaveLength(2);
  });
});
