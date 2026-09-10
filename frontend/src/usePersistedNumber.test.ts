import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { usePersistedNumber } from "./usePersistedNumber";

// jsdom in this environment doesn't provide window.localStorage, so stub a minimal one.
function fakeLocalStorage(): Storage {
  const store = new Map<string, string>();
  return {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => void store.set(key, value),
    removeItem: (key) => void store.delete(key),
    clear: () => store.clear(),
    key: (index) => Array.from(store.keys())[index] ?? null,
    get length() {
      return store.size;
    },
  };
}

beforeEach(() => {
  Object.defineProperty(window, "localStorage", { value: fakeLocalStorage(), configurable: true });
});

afterEach(() => {
  window.localStorage.clear();
});

describe("usePersistedNumber", () => {
  it("starts at the initial value when nothing is stored", () => {
    const { result } = renderHook(() => usePersistedNumber("test.key", 420));
    expect(result.current[0]).toBe(420);
  });

  it("reads a previously stored value", () => {
    window.localStorage.setItem("test.key", "600");
    const { result } = renderHook(() => usePersistedNumber("test.key", 420));
    expect(result.current[0]).toBe(600);
  });

  it("falls back to the initial value when the stored value is not a number", () => {
    window.localStorage.setItem("test.key", "not-a-number");
    const { result } = renderHook(() => usePersistedNumber("test.key", 420));
    expect(result.current[0]).toBe(420);
  });

  it("updates state and persists on set", () => {
    const { result } = renderHook(() => usePersistedNumber("test.key", 420));
    act(() => result.current[1](700));
    expect(result.current[0]).toBe(700);
    expect(window.localStorage.getItem("test.key")).toBe("700");
  });
});
