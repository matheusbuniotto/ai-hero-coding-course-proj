import { useState } from "react";

import { ApiError } from "./api";

export interface Action<Args extends unknown[]> {
  run: (...args: Args) => Promise<void>;
  busy: boolean;
  error: string | null;
}

/** Wraps a write call with the busy/error bookkeeping every approve/reject/end button needs. */
export function useAction<Args extends unknown[]>(
  perform: (...args: Args) => Promise<unknown>,
): Action<Args> {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(...args: Args) {
    setBusy(true);
    setError(null);
    try {
      await perform(...args);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  return { run, busy, error };
}
