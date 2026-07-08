import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import BookPage from "./page";

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    from: () => ({
      select: () => ({
        eq: () => ({
          single: async () => ({
            data: {
              id: "abc-123",
              caption: "A dog runs through a sunny field.",
              image_path: "abc-123/scene-1.png",
            },
          }),
        }),
      }),
    }),
    storage: {
      from: () => ({
        createSignedUrl: async () => ({ data: { signedUrl: "https://example.com/signed.png" } }),
      }),
    },
  },
}));

describe("BookPage", () => {
  it("renders the signed image and caption", async () => {
    await act(async () => {
      render(<BookPage params={Promise.resolve({ jobId: "abc-123" })} />);
    });

    await waitFor(() =>
      expect(screen.getByAltText("A dog runs through a sunny field.")).toHaveAttribute(
        "src",
        "https://example.com/signed.png"
      )
    );
    expect(screen.getByText("A dog runs through a sunny field.")).toBeDefined();
  });
});
