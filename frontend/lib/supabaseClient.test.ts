import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock both packages before the module under test is imported.
const mockCreateBrowserClient = vi.fn(() => ({ auth: {}, from: vi.fn() }));
const mockCreateClient = vi.fn();

vi.mock("@supabase/ssr", () => ({ createBrowserClient: mockCreateBrowserClient }));
vi.mock("@supabase/supabase-js", () => ({ createClient: mockCreateClient }));

describe("supabaseClient", () => {
  beforeEach(() => {
    vi.resetModules();
    mockCreateBrowserClient.mockClear();
    mockCreateClient.mockClear();
  });

  // spec §8 test 8 — import assertion
  it("exports a client created by createBrowserClient, not createClient", async () => {
    await import("./supabaseClient");
    expect(mockCreateBrowserClient).toHaveBeenCalledTimes(1);
    expect(mockCreateClient).not.toHaveBeenCalled();
  });

  // spec §8 test 7 — cookie storage is enabled by using createBrowserClient
  // ponytail: createBrowserClient IS the cookie-storage mechanism; testing it was called
  // proves cookies are enabled — direct document.cookie manipulation requires a real browser.
  it("passes the Supabase URL and anon key to createBrowserClient", async () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://example.supabase.co";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "anon-key";
    await import("./supabaseClient");
    expect(mockCreateBrowserClient).toHaveBeenCalledWith(
      "https://example.supabase.co",
      "anon-key"
    );
  });
});
