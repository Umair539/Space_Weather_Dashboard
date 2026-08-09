import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "./api";

export interface AsyncState<T> {
  data: T | undefined;
  error: string | undefined;
  loading: boolean;
}

/**
 * Fetch-on-mount plus optional polling, mirroring Streamlit's
 * `@st.fragment(run_every=120)`. `deps` is the dependency list that should
 * trigger a refetch - passed explicitly because `fetcher` is a fresh closure
 * on every render and can't be a dependency itself.
 *
 * Keeps the previous data visible while refetching so a poll doesn't blank
 * the chart out; only the very first load shows a loading state.
 */
export function useApi<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: unknown[],
  refreshMs?: number,
): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({
    data: undefined,
    error: undefined,
    loading: true,
  });
  // Held in a ref so the polling effect never restarts when the callback
  // identity changes - only `deps` and `refreshMs` should restart it.
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    const load = async () => {
      try {
        const data = await fetcherRef.current(controller.signal);
        if (!cancelled) setState({ data, error: undefined, loading: false });
      } catch (error) {
        if (cancelled || controller.signal.aborted) return;
        setState((prev) => ({
          ...prev,
          loading: false,
          error:
            error instanceof ApiError ? error.message : String(error),
        }));
      }
    };

    void load();
    const timer = refreshMs ? setInterval(load, refreshMs) : undefined;
    return () => {
      cancelled = true;
      controller.abort();
      if (timer) clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, refreshMs]);

  return state;
}

/**
 * "Data last updated at ..." - /health reports each table's true
 * last-changed time, which only moves on a genuine value change (the ETL
 * bumps updated_at only on IS DISTINCT FROM). metadata.last_synced was
 * rewritten every run regardless, which is why the API doesn't expose it.
 */
export function useLastUpdated(): string {
  const { data, error } = useApi((signal) => api.health(signal), [], 120_000);
  if (error) return "Error fetching last updated";
  if (!data) return "";

  const stamps = Object.values(data.tables)
    .map((t) => t.last_updated_at)
    .filter((s): s is string => Boolean(s))
    .map((s) => new Date(s).getTime());
  if (!stamps.length) return "";

  return `Data last updated at ${formatUtc(new Date(Math.max(...stamps)), {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  })} UTC`;
}

/**
 * The API serves naive timestamps that are already UTC, so they must be
 * formatted as UTC - letting the browser apply a local offset would shift
 * every label by the viewer's timezone.
 */
export function formatUtc(date: Date, options: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat("en-GB", {
    ...options,
    timeZone: "UTC",
    hour12: false,
  })
    .format(date)
    .replace(",", "");
}

/** Naive ISO string from the API -> Date, pinned to UTC. */
export function parseApiTime(iso: string): Date {
  return new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
}
