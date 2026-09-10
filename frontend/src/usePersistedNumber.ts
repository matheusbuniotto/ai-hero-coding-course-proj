import { useState } from "react";

/** A number that survives reload, scoped to a single localStorage key. */
export function usePersistedNumber(key: string, initial: number): [number, (value: number) => void] {
  const [value, setValue] = useState(() => {
    const stored = readStorage(key);
    const parsed = stored === null ? NaN : Number(stored);
    return Number.isFinite(parsed) ? parsed : initial;
  });

  function set(next: number) {
    setValue(next);
    writeStorage(key, String(next));
  }

  return [value, set];
}

// window.localStorage can throw or be unavailable (private browsing, test environments); best-effort only.
function readStorage(key: string): string | null {
  try {
    return window.localStorage?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string): void {
  try {
    window.localStorage?.setItem(key, value);
  } catch {
    // ignore
  }
}
