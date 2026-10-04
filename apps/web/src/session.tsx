import { createContext, useContext, useState } from "react";
import type { Api } from "./api";
import type { Project, Provider, Profile } from "./types";
export interface Session {
  api: Api;
  project: Project;
  branch: string;
  providers: Provider[];
  profiles: Profile[];
  refresh: () => Promise<void>;
  report: (error: unknown) => void;
  notice: (message: string) => void;
  setRun: (id: string) => void;
}
export const SessionContext = createContext<Session | null>(null);
export function useSession() {
  const session = useContext(SessionContext);
  if (!session) throw new Error("未选择作品");
  return session;
}
export function useAction() {
  const [busy, setBusy] = useState(false);
  const { report } = useSession();
  const act = async <T,>(work: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    try {
      return await work();
    } catch (error) {
      report(error);
      return undefined;
    } finally {
      setBusy(false);
    }
  };
  return { busy, act };
}
export function query(
  values: Record<string, string | number | null | undefined>,
) {
  const p = new URLSearchParams();
  Object.entries(values).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== "") p.set(k, String(v));
  });
  return p.toString();
}
