import "@testing-library/jest-dom/vitest";

// jsdom has dialog elements but no native modal API. Focus containment and
// background inertness are supplied by the browser and need browser verification.
if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
}

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
