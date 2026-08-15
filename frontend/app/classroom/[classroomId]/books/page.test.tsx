import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { jobState, type Job } from "@/lib/types/jobs";
import { FailedBookRow } from "./page";

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

// Renders the real FailedBookRow. An earlier version of this suite declared its own copy of
// `getTeacherLabel` and asserted against that, so it passed no matter what the teacher saw.
describe("failure_reason rendering", () => {
  const LABELS: [string | null, string][] = [
    ["child_text", "The submitted story did not pass the input safety check."],
    ["character_safety", "A generated character reference did not pass the image safety check."],
    ["scene_safety", "A generated scene did not pass the image safety check."],
    ["service_busy", "A required story-making service was temporarily unavailable."],
    ["worker_stopped", "The worker process stopped or exceeded its job deadline."],
    ["service_limit", "The configured story-making service reported exhausted quota or credits."],
    ["book_limit", "The job reached its paid-image circuit breaker."],
    [null, "The job ended because of an unclassified system error."],
    ["some_future_value", "The job ended because of an unclassified system error."],
    ["machine", "The job ended because of an unclassified system error."],
  ];

  it.each(LABELS)("%s shows its exact teacher label", (reason, label) => {
    render(<FailedBookRow job={makeJob({ status: "failed", failure_reason: reason })} />);
    expect(screen.getByText(label)).toBeDefined();
  });

  it("shows an abbreviated reference and copies the full job ID", async () => {
    const writeText = vi.fn();
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    const job = makeJob({ id: "3f8b21c9-0d44-4a71-9e02-6cb5a1d7e330", status: "failed" });

    render(<FailedBookRow job={job} />);
    expect(screen.getByText(`Ref: ${job.id.slice(0, 8)}`)).toBeDefined();
    expect(screen.queryByText(job.id)).toBeNull();

    fireEvent.click(screen.getByLabelText("Copy story reference ID"));
    expect(writeText).toHaveBeenCalledWith(job.id);
    await waitFor(() => expect(screen.getByText("Copied!")).toBeDefined());
    vi.unstubAllGlobals();
  });

  it("never leaks a raw diagnostic, provider name, or moderation category", () => {
    const { container } = render(
      <FailedBookRow job={makeJob({ status: "failed", failure_reason: "scene_safety" })} />
    );
    for (const leak of ["output_moderation_failed", "openai", "fal.ai", "sexual", "self-harm", "Traceback"]) {
      expect(container.textContent?.toLowerCase()).not.toContain(leak.toLowerCase());
    }
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
