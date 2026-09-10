import { describe, it, expect, vi, beforeEach } from "vitest";
import { classify, useJob } from "./useJob";
import type { JobRow } from "./useJob";
import { renderHook, act, waitFor } from "@testing-library/react";

const BASE: JobRow = {
  id: "j1",
  status: "running",
  current_stage: null,
  failure_reason: null,
  input_text: "x",
  title: null,
  style_preset_id: null,
  pages: [],
  reveal: null,
};

describe("classify", () => {
  it("null row → not-found", () => {
    expect(classify(null)).toBe("not-found");
  });

  it("complete + pages → terminal-success", () => {
    expect(
      classify({ ...BASE, status: "complete", pages: [{ scene_id: "s0", caption: "c", image_path: "p" }] })
    ).toBe("terminal-success");
  });

  it("complete + empty pages → terminal-failure (broken book, spec §3.4)", () => {
    expect(classify({ ...BASE, status: "complete", pages: [] })).toBe("terminal-failure");
  });

  it("awaiting_confirm → paused", () => {
    expect(classify({ ...BASE, status: "awaiting_confirm" })).toBe("paused");
  });

  it("queued → in-flight", () => {
    expect(classify({ ...BASE, status: "queued" })).toBe("in-flight");
  });

  it("running → in-flight", () => {
    expect(classify({ ...BASE, status: "running" })).toBe("in-flight");
  });

  it("failed → terminal-failure", () => {
    expect(classify({ ...BASE, status: "failed" })).toBe("terminal-failure");
  });

  it("unknown status → terminal-failure (fail-safe, spec §3.4 last line)", () => {
    expect(classify({ ...BASE, status: "swept_pause_future_value" })).toBe("terminal-failure");
  });
});

// ---- Supabase mock ----
const mockSingle = vi.fn();
const mockSelectColumns = vi.fn();
let capturedCallback: ((payload: { new: JobRow }) => void) | null = null;

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    from: () => ({
      select: (columns: string) => {
        mockSelectColumns(columns);
        return {
        eq: () => ({ single: () => mockSingle() }),
        };
      },
    }),
    channel: () => ({
      on: (_event: string, _filter: unknown, cb: (payload: { new: JobRow }) => void) => {
        capturedCallback = cb;
        return { subscribe: () => ({}) };
      },
    }),
    removeChannel: vi.fn(),
  },
}));

beforeEach(() => {
  mockSingle.mockReset();
  mockSelectColumns.mockReset();
  capturedCallback = null;
});

it("select string includes title", async () => {
  mockSingle.mockResolvedValue({ data: null, error: { code: "PGRST116" } });
  renderHook(() => useJob("j1"));
  await waitFor(() => expect(mockSelectColumns).toHaveBeenCalled());
  expect(mockSelectColumns.mock.calls[0][0]).toContain("title");
});

const RUNNING: JobRow = {
  id: "j1", status: "running", current_stage: "analyze",
  failure_reason: null, input_text: "x", title: null, style_preset_id: null, pages: [], reveal: null,
};
const COMPLETE: JobRow = {
  ...RUNNING, status: "complete",
  pages: [{ scene_id: "s0", caption: "c", image_path: "p" }],
};

describe("useJob", () => {
  it("starts with in-flight bucket before any data arrives", async () => {
    mockSingle.mockResolvedValue({ data: null });
    const { result } = renderHook(() => useJob("j1"));
    expect(result.current.bucket).toBe("in-flight");
  });

  it("seed SELECT updates row and bucket when no live UPDATE arrived first", async () => {
    mockSingle.mockResolvedValue({ data: RUNNING });
    const { result } = renderHook(() => useJob("j1"));
    await waitFor(() => expect(result.current.row?.status).toBe("running"));
    expect(result.current.bucket).toBe("in-flight");
  });

  it("a transient SELECT error is retry, not not-found (#76)", async () => {
    // Network blip / 5xx: PostgREST returns an error with no PGRST116 code. The old code
    // destructured only `data`, so this read as a missing book and the child was told their
    // story does not exist.
    mockSingle.mockResolvedValue({ data: null, error: { code: "08006", message: "network" } });
    const { result } = renderHook(() => useJob("j1"));
    await waitFor(() => expect(result.current.bucket).not.toBe("in-flight"));
    expect(result.current.bucket).toBe("terminal-failure");
  });

  it("PGRST116 (no rows) is still not-found", async () => {
    mockSingle.mockResolvedValue({ data: null, error: { code: "PGRST116", message: "no rows" } });
    const { result } = renderHook(() => useJob("j1"));
    await waitFor(() => expect(result.current.bucket).not.toBe("in-flight"));
    expect(result.current.bucket).toBe("not-found");
  });

  it("live UPDATE is applied regardless", async () => {
    mockSingle.mockResolvedValue({ data: null });
    const { result } = renderHook(() => useJob("j1"));
    await act(async () => {
      capturedCallback?.({ new: COMPLETE });
    });
    expect(result.current.bucket).toBe("terminal-success");
  });

  it("seed is discarded when a live UPDATE already arrived (overtake protection)", async () => {
    // The live UPDATE sets COMPLETE before the SELECT resolves
    let resolveSeed!: (v: { data: JobRow | null }) => void;
    mockSingle.mockReturnValue(new Promise(r => { resolveSeed = r; }));
    const { result } = renderHook(() => useJob("j1"));

    // Live UPDATE fires first
    await act(async () => {
      capturedCallback?.({ new: COMPLETE });
    });

    // Now the seed resolves with a stale row — should be discarded
    await act(async () => {
      resolveSeed({ data: RUNNING });
    });

    // Row should still be COMPLETE, not overwritten by the stale seed
    expect(result.current.bucket).toBe("terminal-success");
    expect(result.current.row?.status).toBe("complete");
  });

  it("refetch() forces a re-read and updates the row, bypassing overtake guard", async () => {
    mockSingle
      .mockResolvedValueOnce({ data: RUNNING })
      .mockResolvedValueOnce({ data: COMPLETE });

    const { result } = renderHook(() => useJob("j1"));
    await waitFor(() => expect(result.current.row?.status).toBe("running"));

    await act(async () => {
      await result.current.refetch();
    });

    expect(result.current.bucket).toBe("terminal-success");
  });

  it("refetch returns true after a successful forced row read", async () => {
    const paused = {
      ...RUNNING,
      status: "awaiting_confirm",
      current_stage: "reveal",
      reveal: {
        characters: [{ char_id: "c0", name: "Kiko", image_path: "j1/ref-c0.png", chips: ["orange sock"] }],
        taps_left: 2,
      },
    } satisfies JobRow;
    mockSingle
      .mockResolvedValueOnce({ data: RUNNING, error: null })
      .mockResolvedValueOnce({ data: paused, error: null });
    const { result } = renderHook(() => useJob("j1"));
    await waitFor(() => expect(result.current.row).toEqual(RUNNING));

    let refreshed = false;
    await act(async () => { refreshed = await result.current.refetch(); });

    expect(refreshed).toBe(true);
    expect(result.current.row).toEqual(paused);
  });

  it("a forced refetch reclassifies to not-found when the row is gone", async () => {
    // A job deleted (or unshared) while the child sat on the pause: PGRST116 is the answer,
    // not a read failure, so the forced read must still apply it rather than stranding the
    // page on a stale row behind a retry that can never succeed.
    mockSingle
      .mockResolvedValueOnce({ data: RUNNING, error: null })
      .mockResolvedValueOnce({ data: null, error: { code: "PGRST116", message: "no rows" } });
    const { result } = renderHook(() => useJob("j1"));
    await waitFor(() => expect(result.current.bucket).toBe("in-flight"));

    await act(async () => { await result.current.refetch(); });

    expect(result.current.bucket).toBe("not-found");
  });

  it("refetch returns false after a failed forced row read", async () => {
    const paused = {
      ...RUNNING,
      status: "awaiting_confirm",
      current_stage: "reveal",
      reveal: {
        characters: [{ char_id: "c0", name: "Kiko", image_path: "j1/ref-c0.png", chips: ["orange sock"] }],
        taps_left: 2,
      },
    } satisfies JobRow;
    mockSingle
      .mockResolvedValueOnce({ data: paused, error: null })
      .mockResolvedValueOnce({ data: null, error: { code: "503", message: "unavailable" } });
    const { result } = renderHook(() => useJob("j1"));
    await waitFor(() => expect(result.current.bucket).toBe("paused"));

    let refreshed = true;
    await act(async () => { refreshed = await result.current.refetch(); });

    expect(refreshed).toBe(false);
    expect(result.current.bucket).toBe("paused");
    expect(result.current.row).toEqual(paused);
  });
});
