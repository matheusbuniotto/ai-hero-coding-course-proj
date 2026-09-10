import { useCallback, useEffect, useState } from "react";

import { NotSignedIn } from "./api";

export interface Async<T> {
  data: T | null;
  error: string | null;
  reload: () => void;
}

/** Run `load` whenever `deps` change, ignoring results from superseded runs.
 *
 * A reload keeps the data it already has on screen, so refreshing after a write
 * never tears down the tree that asked for it.
 */
export function useAsync<T>(load: () => Promise<T>, deps: unknown[]): Async<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  const run = useCallback(load, deps);

  useEffect(() => {
    let current = true;
    setError(null);
    run().then(
      (value) => current && setData(value),
      // A 401 has already redirected to the login page; nothing to report here.
      (cause) => current && !(cause instanceof NotSignedIn) && setError(String(cause)),
    );
    return () => {
      current = false;
    };
  }, [run, attempt]);

  return { data, error, reload: useCallback(() => setAttempt((n) => n + 1), []) };
}
