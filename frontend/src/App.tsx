import { motion } from "framer-motion";
import { useState } from "react";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Intro } from "./components/Intro";
import {
  IconColumns,
  IconDocument,
  IconDownload,
  IconGrid,
  IconNodes,
  IconPlus,
  IconRules,
  IconSearch,
  IconSettings,
  IconShield,
  IconSpark,
  IconUpload,
} from "./components/Icons";
import { Button, Dot, ErrorNote, Spinner } from "./components/ui";
import { StoreProvider, useStore } from "./lib/store";
import { type ScreenId } from "./lib/nav";
import { Documents } from "./screens/Documents";
import { ExportScreen } from "./screens/Export";
import { Ingest } from "./screens/Ingest";
import { Landing } from "./screens/Landing";
import { Projects } from "./screens/Projects";
import { Relationships } from "./screens/Relationships";
import { Rules } from "./screens/Rules";
import { SchemaStudio } from "./screens/SchemaStudio";
import { Settings } from "./screens/Settings";
import { Trust } from "./screens/Trust";
import { Workspace } from "./screens/Workspace";

function Sidebar() {
  const { screen, go } = useStore();

  const navItems: { id: ScreenId; label: string; icon: typeof IconGrid }[] = [
    { id: "landing", label: "Landing Overview", icon: IconSpark },
    { id: "projects", label: "Dashboard", icon: IconGrid },
    { id: "ingest", label: "New Project", icon: IconUpload },
    { id: "schema", label: "Schema Studio", icon: IconColumns },
    { id: "relationships", label: "Relationships", icon: IconNodes },
    { id: "rules", label: "Business Rules", icon: IconRules },
    { id: "workspace", label: "Workspace", icon: IconSpark },
    { id: "trust", label: "Trust Report", icon: IconShield },
    { id: "documents", label: "Documents", icon: IconDocument },
    { id: "export", label: "Exports", icon: IconDownload },
    { id: "settings", label: "Settings", icon: IconSettings },
  ];

  return (
    <aside className="w-60 fixed left-0 top-0 bottom-0 bg-surface-container-lowest border-r border-outline-variant/30 flex flex-col justify-between z-30 p-4 select-none">
      <div className="flex flex-col gap-5">
        {/* Brand & Logo */}
        <div className="flex items-center gap-3 px-2 pt-1 cursor-pointer" onClick={() => go("landing")}>
          <img
            src="/dataseed-logo.png"
            alt="DataSeed"
            className="h-8 w-auto shrink-0 select-none"
            draggable={false}
          />
        </div>

        {/* Navigation Items */}
        <nav aria-label="Sidebar Navigation" className="flex flex-col gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = screen === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => go(item.id)}
                className={`flex items-center gap-3 rounded-full px-4 py-2 text-[13px] font-semibold transition-all duration-150 text-left ${
                  active
                    ? "bg-secondary-container text-primary shadow-sm shadow-primary/5"
                    : "text-secondary hover:bg-surface-container-low hover:text-on-surface"
                }`}
              >
                <Icon size={18} className={active ? "text-primary" : "text-secondary"} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* AI Assistant Card Footer */}
      <div className="flex flex-col gap-3 pt-3 border-t border-outline-variant/20">
        <div className="p-3.5 bg-gradient-to-br from-primary-fixed/50 to-secondary-container/40 rounded-2xl border border-outline-variant/30 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <IconSpark size={16} className="text-primary" />
              <span className="text-[12px] font-bold text-primary">AI Engine</span>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-[#FFD666] text-[#1B1740] text-[10px] font-extrabold uppercase">
              ✦ LIVE
            </span>
          </div>
          <p className="text-[11.5px] text-secondary leading-snug">
            Mistral synthetic engine connected & active.
          </p>
          <button
            type="button"
            onClick={() => go("settings")}
            className="w-full mt-0.5 py-1 px-3 bg-white text-primary text-[11px] font-bold rounded-full border border-outline-variant/40 hover:bg-primary-fixed transition-all text-center"
          >
            Configure AI Key
          </button>
        </div>
      </div>
    </aside>
  );
}

function TopBar() {
  const { project, schema, aiMode, aiNote, go } = useStore();
  const [search, setSearch] = useState("");

  return (
    <header className="h-16 bg-white/90 backdrop-blur-md sticky top-0 z-20 px-6 flex items-center justify-between border-b border-outline-variant/20 shadow-xs">
      {/* Left: Project title & Seed indicator */}
      <div className="flex items-center gap-3">
        <span className="font-bold text-[15px] text-on-surface tracking-tight cursor-pointer" onClick={() => go("projects")}>
          DataSeed
        </span>
        {project && (
          <>
            <span className="text-outline-variant font-light">/</span>
            <div className="flex items-center gap-2">
              <span className="text-[13px] font-semibold text-primary">{project.name}</span>
              {schema && (
                <span className="tnum rounded-full bg-surface-container-low px-2.5 py-0.5 text-[11px] font-medium text-secondary border border-outline-variant/30">
                  seed {schema.seed}
                </span>
              )}
            </div>
          </>
        )}
      </div>

      {/* Center: Global Search Input */}
      <div className="relative w-80 hidden lg:block">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-secondary">
          <IconSearch size={16} />
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search tables, schemas, or rules..."
          className="w-full pl-9 pr-4 py-1.5 bg-surface-container-low border border-outline-variant/30 rounded-full text-[13px] placeholder:text-secondary/50 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary-fixed-dim/50 transition-all text-on-surface"
        />
      </div>

      {/* Right: Engine Status & Quick Actions */}
      <div className="flex items-center gap-3">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider ${
            aiMode === "live"
              ? "bg-[#FFD666] text-[#1B1740]"
              : aiMode === "degraded"
              ? "bg-amber-wash text-amber border border-amber/20"
              : "bg-surface-container-low text-secondary border border-outline-variant/30"
          }`}
          title={aiNote}
        >
          <IconSpark size={13} />
          {aiMode === "live"
            ? "✦ AI Live"
            : aiMode === "degraded"
            ? "✦ AI Degraded"
            : "✦ Heuristics"}
        </span>

        <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-grass-wash border border-grass/20 px-2.5 py-1 text-[11px] font-semibold text-grass">
          <Dot tone="grass" />
          Engine ready
        </span>

        <Button
          size="sm"
          variant="secondary"
          icon={<IconPlus size={14} />}
          onClick={() => go("ingest")}
        >
          New project
        </Button>

        <Button
          size="sm"
          variant="primary"
          icon={<IconDownload size={14} />}
          onClick={() => go("export")}
        >
          Export dataset
        </Button>
      </div>
    </header>
  );
}

const SCREENS = {
  landing: Landing,
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
  const { screen, booting, error, setError } = useStore();
  const Current = SCREENS[screen] ?? Projects;

  if (booting) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-6 text-secondary bg-background">
        <motion.img
          src="/dataseed-logo.png"
          alt="DataSeed"
          className="w-[280px] max-w-[70vw] select-none"
          draggable={false}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        />
        <div className="flex items-center gap-2 text-[13px] font-medium">
          <Spinner />
          Booting Synthetic Intelligence Engine...
        </div>
      </div>
    );
  }

  // Full-bleed rendering for the Landing Page
  if (screen === "landing") {
    return (
      <div className="min-h-screen bg-background antialiased">
        <Current />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background antialiased flex flex-col">
      <Sidebar />
      <div className="ml-60 flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 px-4 sm:px-6 py-6 pb-12 max-w-[1400px] w-full mx-auto">
          <div className="mb-4">
            <ErrorNote error={error} onDismiss={() => setError(null)} />
          </div>
          <motion.div
            key={screen}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
          >
            <ErrorBoundary key={screen}>
              <Current />
            </ErrorBoundary>
          </motion.div>
        </main>
      </div>
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
