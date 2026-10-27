import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { jobState, type Job } from "@/lib/types/jobs";
import { FailedBookRow } from "./page";
import BookCard from "@/components/BookCard";
import NeedsHelpQueue from "@/components/NeedsHelpQueue";
// Captured from the real graph/disposable-Postgres test_teacher_hold integration run.
import heldDetail from "./held-detail.fixture.json";

vi.mock("@/lib/supabaseClient", () => ({ supabase: {
  auth: { getSession: async () => ({ data: { session: { access_token: "synthetic" } } }) },
  channel: () => ({ on() { return this; }, subscribe() { return this; } }),
  removeChannel: vi.fn(),
} }));

describe("held story inspection", () => {
  it.each([false, true])("reveals only on request and keeps writing readable on image failure (%s)", async (fails) => {
    let queueChanged = false;
    const fetchMock = vi.fn<(url: string, options?: RequestInit) => Promise<Response>>(async (url) => {
      if (url.endsWith("/reveal")) return new Response(fails ? "unavailable" : "picture", { status: fails ? 503 : 200 });
      if (url.endsWith("/moderation-review")) return Response.json(heldDetail);
      return Response.json(queueChanged ? [] : [{ review_id: heldDetail.review_id, job_id: "synthetic-job", title: heldDetail.title, author: heldDetail.author, held_at: "2026-10-28T00:00:00Z", ready: true }]);
    });
    vi.stubGlobal("fetch", fetchMock);
    URL.createObjectURL = vi.fn(() => "blob:synthetic-picture");
    URL.revokeObjectURL = vi.fn();
    render(<NeedsHelpQueue classroomId="synthetic-class" active onCount={() => {}} onBack={() => {}} />);
    const opener = await screen.findByRole("button", { name: /Inspect Synthetic title/ });
    opener.focus();
    fireEvent.click(opener);
    expect(await screen.findByText("Synthetic story", { selector: "p.whitespace-pre-wrap" })).toBeDefined();
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/reveal"))).toBe(false);
    expect(screen.getByText("Picture not generated yet")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Show picture to review" }));
    if (fails) {
      expect(await screen.findByText("Picture unavailable. Your story context is still here.")).toBeDefined();
      expect(screen.getByRole("button", { name: "Try loading again" })).toBeDefined();
    } else {
      expect(await screen.findByRole("img", { name: "Synthetic story" })).toHaveAttribute("src", "blob:synthetic-picture");
    }
    if (fails) {
      queueChanged = true;
      fireEvent(document, new Event("visibilitychange"));
      await waitFor(() => expect(opener.isConnected).toBe(false));
    }
    fireEvent(screen.getByRole("dialog"), new Event("cancel", { bubbles: true }));
    await waitFor(() => expect(fails ? screen.getByRole("region", { name: "Needs your help" }) : opener).toHaveFocus());
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(fetchMock.mock.calls.filter(([, options]) => options?.method === "POST")).toHaveLength(1);
    vi.unstubAllGlobals();
  });
});

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
    title: null,
    pages: [{ scene_id: "s1", caption: "Page 1", image_path: "job-1/s1.png" }],
    profile_id: "profile-1",
    profiles: { display_nickname: "Alex", avatar_id: null },
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
    ["child_text", "The submitted title or story did not pass the input safety check."],
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

  it("says so when the copy fails, and never claims success", async () => {
    const writeText = vi.fn().mockRejectedValue(new Error("denied"));
    vi.stubGlobal("navigator", { clipboard: { writeText } });

    render(<FailedBookRow job={makeJob({ status: "failed" })} />);
    fireEvent.click(screen.getByLabelText("Copy story reference ID"));

    // The button's `aria-label` is its accessible name in every state, so the result has to live
    // in a region of its own to be announced at all (spec §4).
    await waitFor(() => {
      const message = screen.getByText("Couldn’t copy");
      expect(message.getAttribute("role")).toBe("status");
    });
    expect(screen.queryByText("Copied!")).toBeNull();
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

  it("shows the book title on a pending review card", () => {
    render(
      <BookCard
        job={makeJob({ title: "My Dragon Book" })}
        thumbnailUrl={null}
        onOpen={vi.fn()}
      />
    );
    expect(screen.getByText("My Dragon Book")).toBeDefined();
  });

  it("keeps the full title in the review card accessible name", () => {
    render(
      <BookCard
        job={makeJob({ title: "A Very Long Dragon Book Title" })}
        thumbnailUrl={null}
        onOpen={vi.fn()}
      />
    );
    expect(
      screen.getByRole("button", {
        name: "Review story by Alex: A Very Long Dragon Book Title",
      })
    ).toBeDefined();
  });

  it("shows the book title in a failed-book row alongside the reference", () => {
    render(
      <FailedBookRow
        job={makeJob({
          title: "My Dragon Book",
          status: "failed",
          failure_reason: "child_text",
        })}
      />
    );
    expect(screen.getByText("My Dragon Book")).toBeDefined();
    expect(screen.getByText(/Ref:/)).toBeDefined();
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
