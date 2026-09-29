export type ScreenId =
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
