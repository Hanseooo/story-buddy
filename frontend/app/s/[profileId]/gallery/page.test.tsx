import { render } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const {
  mockLimit,
  mockOrder,
  mockIs,
  mockNot,
  mockSelect,
  mockFrom,
  mockCreateSignedUrls,
  mockStorageFrom,
} = vi.hoisted(() => {
  const mockLimit = vi.fn();
  const mockOrder = vi.fn(() => ({ limit: mockLimit }));
  const mockIs = vi.fn(() => ({ order: mockOrder }));
  const mockNot = vi.fn(() => ({ is: mockIs }));
  const mockSelect = vi.fn(() => ({ not: mockNot }));
  const mockFrom = vi.fn(() => ({ select: mockSelect }));
  const mockCreateSignedUrls = vi.fn();
  const mockStorageFrom = vi.fn(() => ({ createSignedUrls: mockCreateSignedUrls }));
  return {
    mockLimit,
    mockOrder,
    mockIs,
    mockNot,
    mockSelect,
    mockFrom,
    mockCreateSignedUrls,
    mockStorageFrom,
  };
});

vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(() => ({
    from: mockFrom,
    storage: { from: mockStorageFrom },
  })),
}));

vi.mock("next/headers", () => ({
  cookies: vi.fn().mockResolvedValue({ get: vi.fn().mockReturnValue(undefined) }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
  }: {
    href: string;
    children: React.ReactNode;
  }) => <a href={href}>{children}</a>,
}));

const PROFILE_ID = "profile-abc";
const params = Promise.resolve({ profileId: PROFILE_ID });

function makeJob(overrides: Record<string, unknown> = {}) {
  return {
    id: "job-1",
    approved_at: "2026-01-01T00:00:00Z",
    pages: [
      {
        scene_id: "s1",
        caption: "Once upon a time",
        image_path: "covers/job-1.jpg",
      },
    ],
    profile_id: "author-1",
    profiles: { display_nickname: "Kai" },
    ...overrides,
  };
}

describe("GalleryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLimit.mockResolvedValue({ data: [] });
    mockCreateSignedUrls.mockResolvedValue({ data: [] });
  });

  it("renders one card per returned row with the author display_nickname", async () => {
    const jobs = [
      makeJob({ id: "job-1", profiles: { display_nickname: "Kai" } }),
      makeJob({ id: "job-2", profiles: { display_nickname: "Sam" } }),
    ];
    mockLimit.mockResolvedValue({ data: jobs });

    const { default: GalleryPage } = await import("./page");
    const jsx = await GalleryPage({ params });
    const { getByText } = render(jsx);

    getByText("by Kai");
    getByText("by Sam");
  });

  it("filters out unapproved rows with .not('approved_at', 'is', null)", async () => {
    const { default: GalleryPage } = await import("./page");
    await GalleryPage({ params });
    expect(mockNot).toHaveBeenCalledWith("approved_at", "is", null);
  });

  it("filters removed authors and uses profiles!inner embed", async () => {
    const { default: GalleryPage } = await import("./page");
    await GalleryPage({ params });
    expect(mockIs).toHaveBeenCalledWith("profiles.removed_at", null);
    const selectArg: string = mockSelect.mock.calls[0][0];
    expect(selectArg).toContain("profiles!inner");
  });

  it("orders by approved_at descending and limits to 200", async () => {
    const { default: GalleryPage } = await import("./page");
    await GalleryPage({ params });
    expect(mockOrder).toHaveBeenCalledWith("approved_at", { ascending: false });
    expect(mockLimit).toHaveBeenCalledWith(200);
  });

  it("does not select input_text", async () => {
    const { default: GalleryPage } = await import("./page");
    await GalleryPage({ params });
    const selectArg: string = mockSelect.mock.calls[0][0];
    expect(selectArg).not.toContain("input_text");
  });

  it("links each card to the book reader at the correct URL", async () => {
    mockLimit.mockResolvedValue({ data: [makeJob({ id: "job-xyz" })] });

    const { default: GalleryPage } = await import("./page");
    const jsx = await GalleryPage({ params });
    const { getAllByRole } = render(jsx);

    const links = getAllByRole("link");
    expect(links[0]).toHaveAttribute("href", `/s/${PROFILE_ID}/book/job-xyz`);
  });

  it("requests signed URLs from bucket storybook-images", async () => {
    mockLimit.mockResolvedValue({ data: [makeJob()] });

    const { default: GalleryPage } = await import("./page");
    await GalleryPage({ params });

    expect(mockStorageFrom).toHaveBeenCalledWith("storybook-images");
  });

  it("empty state renders without any approval vocabulary", async () => {
    const { default: GalleryPage } = await import("./page");
    const jsx = await GalleryPage({ params });
    const { container } = render(jsx);

    const text = container.textContent?.toLowerCase() ?? "";
    for (const forbidden of [
      "approved",
      "pending",
      "waiting",
      "rejected",
      "teacher",
    ]) {
      expect(text, `found forbidden word: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
