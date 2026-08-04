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
let capturedCallback: ((payload: { new: JobRow }) => void) | null = null;

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    from: () => ({
      select: () => ({
        eq: () => ({ single: () => mockSingle() }),
      }),
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
  capturedCallback = null;
});

const RUNNING: JobRow = {
  id: "j1", status: "running", current_stage: "analyze",
  failure_reason: null, input_text: "x", pages: [], reveal: null,
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
});
