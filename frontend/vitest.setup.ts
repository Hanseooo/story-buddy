import "@testing-library/jest-dom/vitest";

// jsdom doesn't implement IntersectionObserver; framer-motion's whileInView uses it.
// Provide a no-op stub so tests don't throw "IntersectionObserver is not defined".
if (typeof IntersectionObserver === "undefined") {
  class IntersectionObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (global as any).IntersectionObserver = IntersectionObserverStub;
}
