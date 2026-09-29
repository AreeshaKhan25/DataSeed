import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ApiError, api, type Job, type ProjectSummary, type Schema, type TrustReport } from "./api";
import type { ScreenId } from "./nav";

interface Store {
  screen: ScreenId;
  go: (s: ScreenId) => void;

  introActive: boolean;
  triggerIntro: (target?: ScreenId) => void;
  finishIntro: () => void;

  projects: ProjectSummary[];
  project: ProjectSummary | null;
  schema: Schema | null;
  report: TrustReport | null;
  job: Job | null;
  aiMode: string;
  aiNote: string;

  booting: boolean;
  error: { message: string; remedy?: string } | null;
  setError: (e: { message: string; remedy?: string } | null) => void;

  refreshProjects: () => Promise<void>;
  openProject: (id: string) => Promise<void>;
  loadDemo: () => Promise<void>;
  setSchema: (s: Schema) => void;
  setReport: (r: TrustReport | null) => void;
  setJob: (j: Job | null) => void;
  run: <T>(fn: () => Promise<T>) => Promise<T | undefined>;
}

const Ctx = createContext<Store | null>(null);

export function useStore(): Store {
  const store = useContext(Ctx);
  if (!store) throw new Error("useStore must be used inside <StoreProvider>");
  return store;
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [screen, setScreen] = useState<ScreenId>("landing");
  const [introActive, setIntroActive] = useState(false);
  const [introTarget, setIntroTarget] = useState<ScreenId | null>(null);

  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [schema, setSchema] = useState<Schema | null>(null);
  const [report, setReport] = useState<TrustReport | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [aiMode, setAiMode] = useState("heuristic");
  const [aiNote, setAiNote] = useState("");
  const [booting, setBooting] = useState(true);
  const [error, setError] = useState<{ message: string; remedy?: string } | null>(null);

  const triggerIntro = useCallback((target: ScreenId = "workspace") => {
    setIntroTarget(target);
    setIntroActive(true);
  }, []);

  const finishIntro = useCallback(() => {
    setIntroActive(false);
    if (introTarget) {
      setScreen(introTarget);
      setIntroTarget(null);
    }
  }, [introTarget]);

  /** Wrap any API call so a thrown ApiError becomes a visible remedy. */
  const run = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    try {
      setError(null);
      return await fn();
    } catch (e) {
      if (e instanceof ApiError) setError({ message: e.message, remedy: e.remedy });
      else setError({ message: String(e), remedy: "Reload the page and try again." });
      return undefined;
    }
  }, []);

  const refreshProjects = useCallback(async () => {
    const res = await run(() => api.listProjects());
    if (res) setProjects(res.projects);
  }, [run]);

  const openProject = useCallback(
    async (id: string) => {
      const res = await run(() => api.getProject(id));
      if (!res) return;
      setProject(res.project);
      setSchema(res.schema);
      if (res.project.has_report) {
        try {
          setReport(await api.report(id));
        } catch {
          setReport(null);
        }
      } else {
        setReport(null);
      }
    },
    [run],
  );

  const loadDemo = useCallback(async () => {
    const res = await run(() => api.createDemo());
    if (!res) return;
    setProject(res.project);
    setSchema(res.schema);
    setReport(null);
    setProjects((p) => [res.project, ...p.filter((x) => x.id !== res.project.id)]);
  }, [run]);

  useEffect(() => {
    (async () => {
      try {
        const status = await api.aiStatus();
        setAiMode(status.mode);
        setAiNote(status.note ?? "");
      } catch {
        /* the status endpoint is informational only */
      }
      try {
        const list = await api.listProjects();
        setProjects(list.projects);
        if (list.projects.length === 0) {
          const demo = await api.createDemo();
          setProjects([demo.project]);
          setProject(demo.project);
          setSchema(demo.schema);
        } else {
          const first = list.projects[0];
          const full = await api.getProject(first.id);
          setProject(full.project);
          setSchema(full.schema);
          if (full.project.has_report) {
            try {
              setReport(await api.report(first.id));
            } catch {
              /* ignore */
            }
          }
        }
      } catch (e) {
        if (e instanceof ApiError) setError({ message: e.message, remedy: e.remedy });
      } finally {
        setBooting(false);
      }
    })();
  }, []);

  const value = useMemo<Store>(
    () => ({
      screen,
      go: setScreen,
      introActive,
      triggerIntro,
      finishIntro,
      projects,
      project,
      schema,
      report,
      job,
      aiMode,
      aiNote,
      booting,
      error,
      setError,
      refreshProjects,
      openProject,
      loadDemo,
      setSchema,
      setReport,
      setJob,
      run,
    }),
    [
      screen, introActive, triggerIntro, finishIntro, projects, project, schema, report, job,
      aiMode, aiNote, booting, error, refreshProjects, openProject, loadDemo, run,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
