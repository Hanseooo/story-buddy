import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import OfflineIndicator from "./OfflineIndicator";

describe("OfflineIndicator component", () => {
  let originalNavigatorOnline: boolean;

  beforeEach(() => {
    originalNavigatorOnline = navigator.onLine;
  });

  afterEach(() => {
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: originalNavigatorOnline,
    });
  });

  it("does not render when online", () => {
    Object.defineProperty(navigator, "onLine", { configurable: true, value: true });
    render(<OfflineIndicator />);
    expect(screen.queryByText(/you're offline right now/i)).toBeNull();
  });

  it("renders offline banner when offline event fires", () => {
    Object.defineProperty(navigator, "onLine", { configurable: true, value: true });
    render(<OfflineIndicator />);

    act(() => {
      Object.defineProperty(navigator, "onLine", { configurable: true, value: false });
      window.dispatchEvent(new Event("offline"));
    });

    expect(
      screen.getByText(/you're offline right now\. your work will sync once you reconnect/i)
    ).toBeDefined();
  });

  it("shows reconnected message when online event fires", () => {
    Object.defineProperty(navigator, "onLine", { configurable: true, value: false });
    render(<OfflineIndicator />);

    act(() => {
      window.dispatchEvent(new Event("offline"));
    });

    expect(
      screen.getByText(/you're offline right now\. your work will sync once you reconnect/i)
    ).toBeDefined();

    act(() => {
      Object.defineProperty(navigator, "onLine", { configurable: true, value: true });
      window.dispatchEvent(new Event("online"));
    });

    expect(
      screen.getByText(/back online\. your story is connected again/i)
    ).toBeDefined();
  });
});
