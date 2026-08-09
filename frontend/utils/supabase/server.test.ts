import { describe, it, expect, vi } from "vitest";

type SetAll = (
  cookies: { name: string; value: string; options?: object }[]
) => void;

const captured: { setAll?: SetAll } = {};

vi.mock("@supabase/ssr", () => ({
  createServerClient: (
    _url: string,
    _key: string,
    opts: { cookies: { setAll: SetAll } }
  ) => {
    captured.setAll = opts.cookies.setAll;
    return {};
  },
}));

// A Server Component render: cookies().set() throws ReadonlyRequestCookiesError.
// See next/dist/server/web/spec-extension/adapters/request-cookies.js —
// mutation is only permitted when requestStore.phase === "action".
vi.mock("next/headers", () => ({
  cookies: async () => ({
    getAll: () => [],
    set: () => {
      throw new Error(
        "Cookies can only be modified in a Server Action or Route Handler."
      );
    },
  }),
}));

import { createSupabaseServerClient } from "./server";

describe("createSupabaseServerClient", () => {
  it("setAll does not throw when the RSC cookie store is read-only", async () => {
    await createSupabaseServerClient();

    expect(() =>
      captured.setAll!([{ name: "sb-access-token", value: "new", options: {} }])
    ).not.toThrow();
  });
});
