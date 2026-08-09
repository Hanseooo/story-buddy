import { render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi, beforeEach, describe } from "vitest";
import BookshelfPage from "./page";

const mockSelect = vi.hoisted(() => vi.fn());
const mockChannel = vi.hoisted(() => vi.fn());
const mockRemoveChannel = vi.hoisted(() => vi.fn());
const mockCreateSignedUrls = vi.hoisted(() => vi.fn());

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    from: () => ({
      select: () => ({
        eq: () => ({
          order: mockSelect,
        }),
      }),
    }),
    storage: {
      from: () => ({ createSignedUrls: mockCreateSignedUrls }),
    },
    channel: () => ({
      on: () => ({ subscribe: mockChannel }),
    }),
    removeChannel: mockRemoveChannel,
  },
}));

const PROFILE_ID = "user-abc";

const makeJob = (overrides: Partial<{
  id: string;
  status: string;
  profile_id: string;
  input_text: string;
  pages: { scene_id: string; caption: string; image_path: string }[];
}> = {}) => ({
  id: "job-1",
  status: "complete",
  current_stage: null,
  failure_reason: null,
  input_text: "My story",
  pages: [{ scene_id: "s1", caption: "cap", image_path: "pages/img.jpg" }],
  reveal: null,
  profile_id: PROFILE_ID,
  ...overrides,
});

describe("Bookshelf — §9.11–12", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockChannel.mockReturnValue({ unsubscribe: vi.fn() });
    mockCreateSignedUrls.mockResolvedValue({ data: [] });
  });

  it("§9.11 — shows own jobs (explicit .eq filter prevents classmate leak)", async () => {
    mockSelect.mockResolvedValueOnce({ data: [makeJob({ id: "own-job" })] });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(screen.getByText("My story")).toBeDefined());
    // Three links: desktop write CTA, the book card, and mobile write CTA
    expect(screen.getAllByRole("link")).toHaveLength(3);
  });

  it("§9.12 — terminal-success card links to /book/[jobId]", async () => {
    mockSelect.mockResolvedValueOnce({ data: [makeJob({ id: "j1", status: "complete" })] });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => {
      // The book card link (not the write CTAs)
      const cardLink = screen.getAllByRole("link").find(
        (el) => el.getAttribute("href") === `/s/${PROFILE_ID}/book/j1`
      );
      expect(cardLink).toBeDefined();
      expect(cardLink).toHaveAttribute("href", `/s/${PROFILE_ID}/book/j1`);
    });
  });

  it("§9.12 — in-flight card links to /process/[jobId]", async () => {
    mockSelect.mockResolvedValueOnce({
      data: [makeJob({ id: "j2", status: "running", pages: [] })],
    });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => {
      const cardLink = screen.getAllByRole("link").find(
        (el) => el.getAttribute("href") === `/s/${PROFILE_ID}/process/j2`
      );
      expect(cardLink).toBeDefined();
      expect(screen.getByText("Still making it…")).toBeDefined();
    });
  });

  it("§9.12 — paused card links to /process/[jobId]", async () => {
    mockSelect.mockResolvedValueOnce({
      data: [makeJob({ id: "j3", status: "awaiting_confirm", pages: [] })],
    });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => {
      const cardLink = screen.getAllByRole("link").find(
        (el) => el.getAttribute("href") === `/s/${PROFILE_ID}/process/j3`
      );
      expect(cardLink).toBeDefined();
      expect(screen.getByText("Come meet your cast!")).toBeDefined();
    });
  });

  it("§9.12 — terminal-failure card links to /write", async () => {
    mockSelect.mockResolvedValueOnce({
      data: [makeJob({ id: "j4", status: "failed", pages: [] })],
    });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => {
      expect(
        screen.getByRole("link", { name: /this one didn't finish/i })
      ).toHaveAttribute("href", `/s/${PROFILE_ID}/write`);
    });
  });

  it("shows empty state when no jobs", async () => {
    mockSelect.mockResolvedValueOnce({ data: [] });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(screen.getByText(/your shelf is empty/i)).toBeDefined());
  });
});
