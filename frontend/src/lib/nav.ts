export type ScreenId =
  | "landing"
  | "projects"
  | "ingest"
  | "schema"
  | "relationships"
  | "rules"
  | "workspace"
  | "trust"
  | "documents"
  | "export"
  | "settings";

export const SCREEN_TITLES: Record<ScreenId, string> = {
  landing: "Landing Page",
  projects: "Projects",
  ingest: "New project",
  schema: "Schema",
  relationships: "Relationships",
  rules: "Business rules",
  workspace: "Workspace",
  trust: "Trust report",
  documents: "Documents",
  export: "Export",
  settings: "Settings",
};
