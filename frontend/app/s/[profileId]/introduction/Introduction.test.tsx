import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import Introduction from "./Introduction";

const { rpc, replace, refresh } = vi.hoisted(() => ({ rpc: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));
vi.mock("@/lib/supabaseClient", () => ({ supabase: { rpc } }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace, refresh }) }));
beforeEach(() => vi.clearAllMocks());

it("explains navigation and saves caller-owned dismissal before entering the bookshelf", async () => {
  rpc.mockResolvedValue({ error: null });
  render(<Introduction profileId="student-1" />);
  expect(screen.getByText(/your stories live here/i)).toBeDefined();
  expect(screen.getByText(/your teacher has shared/i)).toBeDefined();
  expect(screen.getByText(/change your password or log out/i)).toBeDefined();
  fireEvent.click(screen.getByRole("button", { name: /skip for now/i }));
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/s/student-1"));
  expect(rpc).toHaveBeenCalledWith("dismiss_student_introduction");
});

it("announces save failure and provides an explicit way to continue", async () => {
  rpc.mockRejectedValue(new TypeError("network"));
  render(<Introduction profileId="student-1" />);
  fireEvent.click(screen.getByRole("button", { name: /go to my bookshelf/i }));
  await screen.findByText(/couldn.t save that you.ve seen this/i);
  expect(replace).not.toHaveBeenCalled();
  expect(screen.getByRole("link", { name: /continue to my bookshelf/i })).toHaveAttribute("href", "/s/student-1");
});
