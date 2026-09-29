import { AnimatePresence, motion } from "framer-motion";
import { Dock } from "./components/Dock";
import { Intro } from "./components/Intro";
import { IconSpark } from "./components/Icons";
import { Dot, ErrorNote, Spinner } from "./components/ui";
import { page } from "./lib/motion";
import { StoreProvider, useStore } from "./lib/store";
import { Documents } from "./screens/Documents";
import { ExportScreen } from "./screens/Export";
import { Ingest } from "./screens/Ingest";
import { Projects } from "./screens/Projects";
import { Relationships } from "./screens/Relationships";
import { Rules } from "./screens/Rules";
import { SchemaStudio } from "./screens/SchemaStudio";
import { Settings } from "./screens/Settings";
import { Trust } from "./screens/Trust";
import { Workspace } from "./screens/Workspace";

function TopBar() {
  const { project, schema, aiMode, aiNote } = useStore();
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-canvas/85 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-4 px-6">
        {/* The full lockup — emblem, wordmark and tagline as one image. Height
            is fixed and width follows the aspect ratio, so it never distorts. */}
        <img
          src="/dataseed-logo.png"
          alt="DataSeed"
          className="h-9 w-auto shrink-0 select-none"
          draggable={false}
        />

        {project && (
          <>
            <span className="h-4 w-px bg-line-strong" />
            <div className="flex min-w-0 items-center gap-2">
              <span className="truncate text-[13px] font-medium text-ink-soft">{project.name}</span>
              {schema && (
                <span className="tnum shrink-0 rounded-md bg-canvas-sunken px-2 py-0.5 text-[11.5px] text-ink-mute">
                  seed {schema.seed}
                </span>
              )}
            </div>
          </>
        )}

        <div className="ml-auto flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11.5px] font-semibold
                        ${
                          aiMode === "live"
                            ? "border-iris/20 bg-iris-wash text-iris"
                            : aiMode === "degraded"
                              ? "border-amber/25 bg-amber-wash text-amber"
                              : "border-line bg-canvas-sunken text-ink-mute"
                        }`}
            title={aiNote}
          >
            <IconSpark size={13} />
            {aiMode === "live"
              ? "AI live"
              : aiMode === "degraded"
                ? "AI unreachable"
                : aiMode === "configured"
                  ? "AI ready"
                  : "Heuristics"}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-grass/20 bg-grass-wash px-2.5 py-1 text-[11.5px] font-semibold text-grass">
            <Dot tone="grass" />
            Engine ready
          </span>
        </div>
      </div>
    </header>
  );
}

const SCREENS = {
  projects: Projects,
  ingest: Ingest,
  schema: SchemaStudio,
  relationships: Relationships,
  rules: Rules,
  workspace: Workspace,
  trust: Trust,
  documents: Documents,
  export: ExportScreen,
  settings: Settings,
} as const;

function Shell() {
  const { screen, go, booting, error, setError } = useStore();
  const Current = SCREENS[screen];

  if (booting) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-6 text-ink-mute">
        {/* The splash has room for the full lockup, so this is where it reads
            properly rather than being shrunk into the header. */}
        <motion.img
          src="/dataseed-logo.png"
          alt="DataSeed"
          className="w-[280px] max-w-[70vw] select-none"
          draggable={false}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        />
        <div className="flex items-center gap-2 text-[13px]">
          <Spinner />
          Starting the engine
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <TopBar />
      <main className="mx-auto max-w-[1440px] px-6 pb-36 pt-7">
        <div className="mb-5">
          <ErrorNote error={error} onDismiss={() => setError(null)} />
        </div>
        <AnimatePresence mode="wait">
          <motion.div key={screen} variants={page} initial="hidden" animate="show" exit="exit">
            <Current />
          </motion.div>
        </AnimatePresence>
      </main>
      <Dock current={screen} onSelect={go} />
    </div>
  );
}

export default function App() {
  return (
    <StoreProvider>
      <Intro />
      <Shell />
    </StoreProvider>
  );
}
