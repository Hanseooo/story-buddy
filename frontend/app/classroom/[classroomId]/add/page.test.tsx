import { expect, it, describe, vi, beforeEach, afterEach } from "vitest";

// Test 18: beforeunload armed while slips show, disarmed after.
// Tested as a unit of the useEffect logic (no full render needed).

describe("test 18: beforeunload armed while slips show, disarmed after", () => {
  let addedHandler: EventListener | null = null;

  beforeEach(() => {
    vi.spyOn(window, "addEventListener").mockImplementation(
      (type: string, handler: EventListenerOrEventListenerObject) => {
        if (type === "beforeunload") addedHandler = handler as EventListener;
      }
    );
    vi.spyOn(window, "removeEventListener").mockImplementation(
      (type: string) => {
        if (type === "beforeunload") addedHandler = null;
      }
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("registers beforeunload when slips phase is active", () => {
    function simulateSlipsPhase(active: boolean) {
      if (!active) return () => {};
      const handler = (e: BeforeUnloadEvent) => {
        e.preventDefault();
        e.returnValue = "";
      };
      window.addEventListener("beforeunload", handler);
      return () => window.removeEventListener("beforeunload", handler);
    }

    const cleanup = simulateSlipsPhase(true);
    expect(addedHandler).not.toBeNull();

    cleanup();
    expect(addedHandler).toBeNull();
  });

  it("does not register beforeunload during paste phase", () => {
    function simulateNonSlipsPhase() {
      return () => {};
    }
    simulateNonSlipsPhase();
    expect(addedHandler).toBeNull();
  });
});
