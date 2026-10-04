import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
afterEach(() => {
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
});
// jsdom does not implement element measurement; Radix observes control sizes.
vi.stubGlobal(
  "ResizeObserver",
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  },
);

Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
  configurable: true,
  value: () => {},
});
