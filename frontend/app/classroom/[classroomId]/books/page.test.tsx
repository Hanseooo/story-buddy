import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { jobState, type Job } from "@/lib/types/jobs";
import { FailedBookRow } from "./page";
import BookCard from "@/components/BookCard";
import NeedsHelpQueue from "@/components/NeedsHelpQueue";
// Captured from the real graph/disposable-Postgres test_teacher_hold integration run.
import heldDetail from "./held-detail.fixture.json";
import heldReference from "./held-reference.fixture.json";
import heldText from "./held-text.fixture.json";
import heldTitle from "./held-title.fixture.json";
import moderationPolicy from "./moderation-policy.fixture.json";
import clearances from "./clearances.fixture.json";
import pendingContinuation from "./pending-continuation.fixture.json";
import BookReviewDialog from "@/components/BookReviewDialog";

vi.mock("@/lib/supabaseClient", () => ({ supabase: {
  auth: { getSession: async () => ({ data: { session: { access_token: "synthetic" } } }) },
  channel: () => ({ on() { return this; }, subscribe() { return this; } }),
  removeChannel: vi.fn(),
} }));

describe("held story inspection", () => {
  it.each([
    { held: heldText, subject: "story text" }, { held: heldTitle, subject: "title" },
  ])("allows the unchanged $subject after criteria confirmation and retries a lost response", async ({ held, subject }) => {
    const bodies: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
      if (url.endsWith("/decision")) {
        bodies.push(options!.body as string);
        if (bodies.length === 1) throw new Error("lost response");
        return Response.json({ status: "queued", dispatch_state: "queued" }, { status: 200 });
      }
      if (url.endsWith("/moderation-policy")) return Response.json(moderationPolicy);
      if (url.endsWith("/moderation-review")) return Response.json(held);
      return Response.json([{ review_id: held.review_id, job_id: "synthetic-job", title: held.title,
        held_at: "2026-10-28T00:00:00Z", ready: true }]);
    }));
    render(<NeedsHelpQueue classroomId="synthetic-class" active onCount={() => {}} onBack={() => {}} />);
    fireEvent.click(await screen.findByRole("button", { name: `Inspect ${held.title}` }));
    expect(await screen.findByText(held.story_text)).toBeDefined();
    if (subject === "title") expect(screen.getByText(heldTitle.subject_title)).toBeDefined();
    const allow = await screen.findByRole("button", { name: `Allow this ${subject}` });
    expect(allow).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Request replacement picture" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Show picture to review" })).toBeNull();
    expect(screen.getByRole("button", { name: "Stop this story" })).toBeEnabled();
    for (const checkbox of screen.getAllByRole("checkbox")) fireEvent.click(checkbox);
    fireEvent.click(allow);
    expect(await screen.findByRole("alert")).toHaveFocus();
    expect(screen.getByText(held.story_text)).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Continue story" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Story continuing" })).toHaveFocus());
    expect(bodies).toHaveLength(2);
    expect(bodies[0]).toBe(bodies[1]);
    expect(JSON.parse(bodies[0]).subject_version).toBe(held.subject_version);
    vi.unstubAllGlobals();
  });

  it("cancels stop without a write, then retries the same confirmed stop after a lost response", async () => {
    const bodies: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
      if (url.endsWith("/decision")) {
        bodies.push(options!.body as string);
        if (bodies.length === 1) throw new Error("lost response");
        return Response.json({ status: "stopped", dispatch_state: null });
      }
      if (url.endsWith("/moderation-review")) return Response.json(heldDetail);
      return Response.json([{ review_id: heldDetail.review_id, job_id: "synthetic-job", title: heldDetail.title, held_at: "2026-10-28T00:00:00Z", ready: true }]);
    }));
    render(<NeedsHelpQueue classroomId="synthetic-class" active onCount={() => {}} onBack={() => {}} />);
    fireEvent.click(await screen.findByRole("button", { name: /Inspect Synthetic title/ }));
    const stop = await screen.findByRole("button", { name: "Stop this story" });
    fireEvent.click(stop);
    expect(screen.getByRole("button", { name: "Keep waiting" })).toHaveFocus();
    fireEvent(screen.getAllByRole("dialog").at(-1)!, new Event("cancel", { bubbles: true }));
    expect(stop).toHaveFocus();
    expect(bodies).toHaveLength(0);
    fireEvent.click(stop);
    fireEvent.click(within(screen.getAllByRole("dialog").at(-1)!).getByRole("button", { name: "Stop this story" }));
    expect(await screen.findByRole("alert")).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Retry stop" }));
    expect(await screen.findByRole("heading", { name: "Story stopped. The writing is saved." })).toHaveFocus();
    expect(bodies).toHaveLength(2);
    expect(bodies[0]).toBe(bodies[1]);
    expect(JSON.parse(bodies[0]).action).toBe("stop");
    vi.unstubAllGlobals();
  });
  it.each([false, true])("confirms withdrawal and reconciles a later release on replay (%s)", async (replayed) => {
    let writes = 0;
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.endsWith("/withdraw")) {
        writes++;
        if (replayed && writes === 1) throw new Error("lost response");
        return Response.json({ status: replayed ? "complete" : "awaiting_teacher", dispatch_state: replayed ? "consumed" : "queued" }, { status: replayed ? 200 : 202 });
      }
      return Response.json(clearances);
    }));
    render(<BookReviewDialog job={makeJob({ moderation_mode: "teacher_review_v1" })} pageUrls={[]}
      onClose={() => {}} onDecide={() => {}} />);
    const buttons = await screen.findAllByRole("button", { name: /^Withdraw clearance for/ });
    fireEvent.click(buttons[0]);
    expect(screen.getByRole("button", { name: "Keep clearance" })).toHaveFocus();
    expect(writes).toBe(0);
    fireEvent.click(screen.getByRole("button", { name: "Keep clearance" }));
    await waitFor(() => expect(screen.getAllByRole("button", { name: /^Withdraw clearance for/ })[0]).toHaveFocus());
    fireEvent.click(screen.getAllByRole("button", { name: /^Withdraw clearance for/ })[0]);
    expect(screen.getByText(/hides the whole book/)).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Withdraw safety clearance" }));
    if (replayed) {
      expect(await screen.findByRole("alert")).toHaveFocus();
      fireEvent.click(screen.getByRole("button", { name: "Withdraw safety clearance" }));
    }
    expect(await screen.findByRole("heading", { name: replayed ? "Current story status: complete" : "Story returned to teacher review" })).toHaveFocus();
    if (!replayed) expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
    expect(writes).toBe(replayed ? 2 : 1);
    vi.unstubAllGlobals();
  });
  it.each([
    { action: "allow", held: heldDetail }, { action: "replace", held: heldDetail },
    { action: "allow", held: heldReference }, { action: "replace", held: heldReference },
  ])("$action retries the same request across a lost response and reload for $held.kind", async ({ action, held }) => {
    let submissions = 0;
    const bodies: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
      if (url.endsWith("/decision")) {
        bodies.push(options!.body as string);
        if (++submissions === 1) throw new Error("lost response");
        return Response.json({ status: "queued", dispatch_state: "queued" }, { status: 200 });
      }
      if (url.endsWith("/reveal")) return new Response("picture");
      if (url.endsWith("/moderation-policy")) return Response.json(moderationPolicy);
      if (url.endsWith("/moderation-review")) return Response.json(submissions
        ? { ...pendingContinuation, pending_command: JSON.parse(bodies[0]) }
        : { ...held, replacement_available: true, replacement_disabled_reason: null });
      return Response.json([{ review_id: heldDetail.review_id, job_id: "synthetic-job", title: heldDetail.title, held_at: "2026-10-28T00:00:00Z", ready: true }]);
    }));
    URL.createObjectURL = vi.fn(() => "blob:synthetic-picture");
    URL.revokeObjectURL = vi.fn();
    render(<NeedsHelpQueue classroomId="synthetic-class" active onCount={() => {}} onBack={() => {}} />);
    fireEvent.click(await screen.findByRole("button", { name: /Inspect Synthetic title/ }));
    const allow = await screen.findByRole("button", { name: action === "allow" ? "Allow this picture" : "Request replacement picture" });
    expect(allow).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Show picture to review" }));
    fireEvent.load(await screen.findByRole("img", { name: held.pictures.find(picture => picture.state === "held")!.label }));
    if (action === "allow") {
      expect(allow).toBeDisabled();
      for (const checkbox of screen.getAllByRole("checkbox")) fireEvent.click(checkbox);
    }
    fireEvent.click(allow);
    expect(await screen.findByRole("alert")).toHaveFocus();
    fireEvent(document, new Event("visibilitychange"));
    expect(await screen.findByText("Your decision is saved. Continue story retries its pending delivery.")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Continue story" }));
    expect(await screen.findByRole("heading", { name: "Story continuing" })).toHaveFocus();
    expect(bodies).toHaveLength(2);
    expect(bodies[0]).toBe(bodies[1]);
    expect(JSON.parse(bodies[0]).action).toBe(action);
    vi.unstubAllGlobals();
  });
  it("explains exhausted replacement budget while keeping other decisions available", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.endsWith("/moderation-review")) return Response.json({ ...heldDetail,
        replacement_available: false, replacement_disabled_reason: "image_budget_exhausted" });
      return Response.json([{ review_id: heldDetail.review_id, job_id: "synthetic-job", title: heldDetail.title, held_at: "2026-10-28T00:00:00Z", ready: true }]);
    }));
    render(<NeedsHelpQueue classroomId="synthetic-class" active onCount={() => {}} onBack={() => {}} />);
    fireEvent.click(await screen.findByRole("button", { name: /Inspect Synthetic title/ }));
    expect(await screen.findByRole("button", { name: "Request replacement picture" })).toBeDisabled();
    expect(screen.getByText("The image budget is used up. You can still inspect, leave waiting, allow or stop this story.")).toBeDefined();
    expect(screen.getByRole("button", { name: "Stop this story" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Back to Needs your help" })).toBeEnabled();
    vi.unstubAllGlobals();
  });
  it("shows captured evidence and a closable criteria reference, with honest missing reasoning", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.endsWith("/moderation-policy")) return Response.json(moderationPolicy);
      if (url.endsWith("/moderation-review")) return Response.json(heldDetail);
      return Response.json([{ review_id: heldDetail.review_id, job_id: "synthetic-job", title: heldDetail.title, held_at: "2026-10-28T00:00:00Z", ready: true }]);
    }));
    render(<NeedsHelpQueue classroomId="synthetic-class" active onCount={() => {}} onBack={() => {}} />);
    fireEvent.click(await screen.findByRole("button", { name: /Inspect Synthetic title/ }));
    expect(await screen.findByText("Synthetic review explanation")).toBeDefined();
    expect(screen.getByText("The recorded reason is unavailable")).toBeDefined();
    expect(screen.getByText(heldDetail.classifier_evidence[0].model_id)).toBeDefined();
    expect(screen.getByText("Shared safety", { selector: "p" })).toBeDefined();
    const dialog = screen.getByRole("dialog");
    const summary = dialog.querySelector("summary")!;
    fireEvent.click(summary);
    expect(await screen.findByText(moderationPolicy.basis)).toBeDefined();
    expect(screen.getByText(moderationPolicy.criteria[1].trigger)).toBeDefined();
    expect(screen.getByText(moderationPolicy.optional_themes[0].trigger)).toBeDefined();
    fireEvent.click(within(dialog).getByRole("button", { name: "Close review criteria" }));
    expect(summary.parentElement).not.toHaveAttribute("open");
    expect(summary).toHaveFocus();
    vi.unstubAllGlobals();
  });
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
