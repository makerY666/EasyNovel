import { useEffect, useRef } from "react";
import type { Api } from "./api";
import type { ImportJob } from "./types";

// Keep following durable imports after the import page is closed. Refresh only
// directory metadata: an import must never remount the active manuscript editor.
export function ImportMonitor({
  api,
  projectId,
  branch,
  signal,
  onChanged,
  onJobs,
  onError,
}: {
  api: Api;
  projectId: string;
  branch: string;
  signal: number;
  onChanged: () => Promise<void>;
  onJobs: (jobs: ImportJob[]) => void;
  onError: (error: unknown) => void;
}) {
  const callbacks = useRef({ onChanged, onJobs, onError });
  callbacks.current = { onChanged, onJobs, onError };
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let previous: string | null = null;
    const poll = async () => {
      try {
        const jobs = await api.get<ImportJob[]>(
          `/projects/${projectId}/imports?branch_id=${encodeURIComponent(branch)}`,
        );
        if (!alive) return;
        callbacks.current.onJobs(jobs);
        const snapshot = JSON.stringify(
          jobs.map((job) => [job.id, job.status, job.completed]),
        );
        if (
          snapshot !== previous &&
          (previous !== null || jobs.some((job) => job.completed > 0))
        )
          await callbacks.current.onChanged();
        previous = snapshot;
        if (
          alive &&
          jobs.some((job) => ["queued", "running"].includes(job.status))
        )
          timer = setTimeout(() => void poll(), 2000);
      } catch (error) {
        if (alive) {
          callbacks.current.onError(error);
          timer = setTimeout(() => void poll(), 5000);
        }
      }
    };
    void poll();
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
    };
  }, [api, projectId, branch, signal]);
  return null;
}
