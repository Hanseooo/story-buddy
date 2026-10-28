import { fireEvent, render, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import StoppedWritingCleanup from "./stoppedWriting";
import stoppedState from "./stopped-state.fixture.json";

vi.mock("@/lib/supabaseClient", () => ({ supabase: { auth: {
  getSession: async () => ({ data: { session: { user: { id: "synthetic-author" }, access_token: "synthetic" } } }),
  onAuthStateChange: () => ({ data: { subscription: { unsubscribe() {} } } }),
} } }));

it("clears a handoff retained across reload on sign-out and on revoked access", async () => {
  const key = `sb.stopped.synthetic-author.${stoppedState.job_id}`;
  sessionStorage.setItem(key, JSON.stringify(stoppedState.saved_writing));
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(stoppedState)));
  const view = render(<><StoppedWritingCleanup /><form action="/auth/signout" method="post" aria-label="Sign out" /></>);
  fireEvent.submit(view.getByRole("form", { name: "Sign out" }));
  expect(sessionStorage.getItem(key)).toBeNull();
  sessionStorage.setItem(key, JSON.stringify(stoppedState.saved_writing));
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 404 })));
  fireEvent(document, new Event("visibilitychange"));
  await waitFor(() => expect(sessionStorage.getItem(key)).toBeNull());
  vi.unstubAllGlobals();
});
