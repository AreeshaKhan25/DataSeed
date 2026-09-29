// Typed client for the DataSeed API.
//
// Every backend error is {code, message, remedy}. This layer turns that into a
// thrown ApiError carrying the remedy, so screens can show the user what to do
// instead of "Request failed".

export class ApiError extends Error {
  code: string;
  remedy: string;
  status: number;

  constructor(status: number, code: string, message: string, remedy: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.remedy = remedy;
  }
}

const BASE = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(BASE + path, {
      ...init,
      headers: {
        ...(init?.body && !(init.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(
      0,
      "network_error",
      "Could not reach the DataSeed API.",
      "Check that the server is running on port 8000, then try again.",
    );
  }

  if (!response.ok) {
    let detail: { code?: string; message?: string; remedy?: string } = {};
    try {
      const body = await response.json();
      detail = typeof body.detail === "object" ? body.detail : { message: String(body.detail) };
    } catch {
      /* the body was not JSON; fall through to the generic message below */
    }
    throw new ApiError(
      response.status,
      detail.code ?? "http_error",
      detail.message ?? `Request failed (${response.status}).`,
      detail.remedy ?? "Try again, or reload the demo project.",
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

// ---------------------------------------------------------------- types

export type Pii = "none" | "quasi" | "direct";
export type Privacy = "passthrough" | "mask" | "hash" | "noise" | "synthesize";

export interface Column {
  name: string;
  dtype: string;
  semantic: string;
  nullable: boolean;
  null_rate: number;
  unique: boolean;
  pii: Pii;
  privacy: Privacy;
  ai_inferred: boolean;
  sample: string | null;
  stats: { n_unique: number; minimum: number | null; maximum: number | null };
}

export interface DerivedField {
  column: string;
  child_table: string;
  agg: string;
  expr: string | null;
}

export interface Table {
  name: string;
  columns: Column[];
  primary_key: string | null;
  row_count: number;
  derived: DerivedField[];
  junction: string[];
}

export interface Rule {
  id: string;
  table: string;
  kind: string;
  column: string;
  enabled: boolean;
  description: string;
  source: "inferred" | "user" | "ai";
  params: Record<string, unknown>;
  label: string;
}

export interface RuleResult {
  id: string;
  label: string;
  kind: string;
  violations_before: number;
  repaired: number;
  dropped: number;
  violations_after: number;
  note: string;
}

export interface ForeignKey {
  child_table: string;
  child_column: string;
  parent_table: string;
  parent_column: string;
  cardinality: string;
  count_values: number[];
  count_probs: number[];
}

export interface Schema {
  name: string;
  tables: Table[];
  foreign_keys: ForeignKey[];
  seed: number;
  locale: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  tables: {
    name: string;
    columns: number;
    source_rows: number;
    generated_rows: number;
    primary_key: string | null;
  }[];
  foreign_keys: number;
  seed: number;
  has_output: boolean;
  has_report: boolean;
  scores: {
    integrity: number | null;
    fidelity: number | null;
    utility: number | null;
    privacy: number | null;
    overall: number | null;
  } | null;
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: string;
  project_id: string;
  kind: string;
  status: "queued" | "running" | "done" | "failed";
  phase: string;
  percent: number;
  message: string;
  error: { code: string; message: string; remedy: string } | null;
  result: {
    rows?: Record<string, number>;
    total_rows?: number;
    integrity?: Integrity;
    warnings?: string[];
    export_allowed?: boolean;
    seed?: number;
  };
}

export interface Integrity {
  passed: boolean;
  score: number;
  orphan_keys: Record<string, number>;
  duplicate_primary_keys: Record<string, number>;
  reconciliation_mismatches: Record<string, number>;
  total_orphans: number;
  total_duplicate_keys: number;
  total_reconciliation_mismatches: number;
}

export interface TrustReport {
  available: boolean;
  reason?: string;
  overall: number;
  conditioned_on: string | null;
  condition_strength: number;
  rows_evaluated: number;
  holdout_rows: number;
  integrity: Integrity;
  fidelity: {
    score: number;
    column_score: number;
    correlation_score: number;
    correlation_delta: number;
    columns: { column: string; metric: string; distance: number; match: number }[];
    regenerated_columns: string[];
    note: string;
  };
  utility: {
    score: number;
    available: boolean;
    reason?: string;
    task?: string;
    target?: string;
    metric?: string;
    trtr?: number;
    tstr?: number;
    ratio?: number;
    features?: number;
    explanation?: string;
    candidates?: { target: string; trtr: number; tstr: number }[];
    excluded_as_leaked?: string[];
    conditioned_on?: string | null;
    independent_check?: {
      target: string;
      trtr: number;
      tstr: number;
      score: number;
    } | null;
  };
  privacy: {
    score: number;
    exact_matches: number;
    dcr: number | null;
    dcr_baseline: number | null;
    membership_auc: number | null;
    explanation: string;
  };
  detection: { auc: number | null; available: boolean; score?: number; explanation?: string };
  gates: Record<string, boolean>;
  export_allowed: boolean;
}

export type Row = Record<string, string | number | boolean | null>;

export interface PreviewResult {
  table: string;
  seed: number;
  rows: Row[];
  columns: { name: string; dtype: string; semantic: string; pii: Pii }[];
}

export interface AiProposal {
  column: string;
  semantic: string;
  pii: Pii;
  privacy: Privacy;
  reason: string;
  source: "ai" | "heuristic";
}

export interface EdgeCase {
  name: string;
  description: string;
  column: string;
  kind: string;
  rate: number;
  source: string;
}

export interface InvoiceDoc {
  number: string;
  issued: string;
  due: string;
  bill_to_name: string;
  bill_to_address: string[];
  from_name: string;
  from_address: string[];
  currency: string;
  tax_label: string;
  tax_rate: number;
  lines: { description: string; quantity: number; unit_price: number; amount: number }[];
  subtotal: number;
  tax: number;
  total: number;
  reconciles: boolean;
}

export interface StatementDoc {
  account_number: string;
  holder: string;
  currency: string;
  period_start: string;
  period_end: string;
  opening_balance: number;
  closing_balance: number;
  total_credits: number;
  total_debits: number;
  transactions: {
    date: string;
    description: string;
    debit: number | null;
    credit: number | null;
    balance: number;
  }[];
  reconciles: boolean;
}

// ---------------------------------------------------------------- calls

export const api = {
  health: () => request<{ status: string; limits: Record<string, number> }>("/api/health"),
  aiStatus: () =>
    request<{
      available: boolean;
      provider: string;
      reasoning_model: string;
      bulk_model: string;
      mode: string;
      note: string;
      calls_ok: number;
      calls_failed: number;
      cached_responses: number;
    }>("/api/ai/status"),
  formats: () => request<{ formats: { id: string; label: string }[] }>("/api/formats"),
  regions: () =>
    request<{
      regions: { code: string; name: string; tax_label: string; tax_rate: number; currency: string }[];
    }>("/api/regions"),

  listProjects: () => request<{ projects: ProjectSummary[] }>("/api/projects"),
  createDemo: () => post<{ project: ProjectSummary; schema: Schema }>("/api/projects/demo"),
  getProject: (id: string) =>
    request<{ project: ProjectSummary; schema: Schema; warnings: string[] }>(`/api/projects/${id}`),
  deleteProject: (id: string) => request<void>(`/api/projects/${id}`, { method: "DELETE" }),

  ingest: (files: File[], name: string) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return request<{ project: ProjectSummary; schema: Schema }>(
      `/api/projects/ingest?name=${encodeURIComponent(name)}`,
      { method: "POST", body: form },
    );
  },

  getSchema: (id: string) => request<Schema>(`/api/projects/${id}/schema`),
  patchSchema: (id: string, patch: { seed?: number; columns?: Record<string, unknown>[] }) =>
    request<Schema>(`/api/projects/${id}/schema`, { method: "PATCH", body: JSON.stringify(patch) }),

  preview: (
    id: string,
    body: { table?: string; rows?: number; seed?: number; null_rate?: number; outlier_rate?: number },
  ) => post<PreviewResult>(`/api/projects/${id}/preview`, body),

  generate: (
    id: string,
    body: { rows: number; seed?: number; null_rate?: number; outlier_rate?: number },
  ) => post<{ job: Job }>(`/api/projects/${id}/generate`, body),

  job: (jobId: string) => request<Job>(`/api/jobs/${jobId}`),
  data: (id: string, table: string, limit = 50, offset = 0) =>
    request<{ table: string; total_rows: number; rows: Row[]; columns: string[] }>(
      `/api/projects/${id}/data/${table}?limit=${limit}&offset=${offset}`,
    ),
  report: (id: string) => request<TrustReport>(`/api/projects/${id}/report`),
  validate: (id: string) => post<TrustReport>(`/api/projects/${id}/validate`),

  inferTypes: (id: string, table: string) =>
    post<{ table: string; mode: string; proposals: AiProposal[]; ai_count: number; pii_flagged: number }>(
      `/api/projects/${id}/ai/infer-types?table=${encodeURIComponent(table)}`,
    ),
  inferRelations: (id: string) =>
    post<{
      mode: string;
      new_count: number;
      proposals: (ForeignKey & { confidence: number; reason: string; already_applied: boolean; source: string })[];
    }>(`/api/projects/${id}/ai/infer-relations`),
  edgeCases: (id: string) =>
    post<{ mode: string; edge_cases: EdgeCase[] }>(`/api/projects/${id}/ai/edge-cases`),
  applyProposals: (id: string, table: string, columns: Partial<AiProposal>[]) =>
    post<{ changed: number; schema: Schema }>(`/api/projects/${id}/ai/apply`, { table, columns }),

  rules: (id: string) =>
    request<{ rules: Rule[]; results: Record<string, RuleResult[]> }>(
      `/api/projects/${id}/rules`,
    ),
  addRule: (id: string, rule: Partial<Rule>) =>
    post<{ rule: Rule; total: number }>(`/api/projects/${id}/rules`, rule),
  toggleRule: (id: string, ruleId: string, enabled: boolean) =>
    request<{ rule: Rule }>(`/api/projects/${id}/rules/${ruleId}?enabled=${enabled}`, {
      method: "PATCH",
    }),
  deleteRule: (id: string, ruleId: string) =>
    request<{ deleted: string }>(`/api/projects/${id}/rules/${ruleId}`, { method: "DELETE" }),
  inferRules: (id: string) =>
    post<{ inferred: number; kept: number; rules: Rule[] }>(`/api/projects/${id}/rules/infer`),
  aiRules: (id: string) =>
    post<{ mode: string; note: string; proposals: (Partial<Rule> & { already_present: boolean })[] }>(
      `/api/projects/${id}/ai/business-rules`,
    ),

  documents: (
    id: string,
    body: { kind: "invoice" | "statement"; count: number; region: string; query?: string },
  ) =>
    post<{
      kind: string;
      region: string;
      count: number;
      reconciled: number;
      all_reconciled: boolean;
      from_generated_data: boolean;
      interpretation: string | null;
      documents: (InvoiceDoc | StatementDoc)[];
    }>(`/api/projects/${id}/documents`, body),

  // The query must ride along, or the printable document silently ignores the
  // filter the user just applied on screen.
  documentHtmlUrl: (
    id: string, index: number, kind: string, region: string, count: number, query?: string,
  ) =>
    `/api/projects/${id}/documents/${index}/html?kind=${kind}&region=${region}&count=${count}` +
    (query ? `&query=${encodeURIComponent(query)}` : ""),
  documentBundleUrl: (
    id: string, kind: string, region: string, count: number, query?: string,
  ) =>
    `/api/projects/${id}/documents/bundle?kind=${kind}&region=${region}&count=${count}` +
    (query ? `&query=${encodeURIComponent(query)}` : ""),
  exportUrl: (id: string, fmt: string) => `/api/projects/${id}/export?fmt=${fmt}`,
};

/** Poll a job to completion. Resolves on done, rejects on failed or timeout. */
export async function trackJob(
  jobId: string,
  onTick: (job: Job) => void,
  { intervalMs = 220, timeoutMs = 180_000 } = {},
): Promise<Job> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const job = await api.job(jobId);
    onTick(job);
    if (job.status === "done") return job;
    if (job.status === "failed") {
      const e = job.error;
      throw new ApiError(
        500,
        e?.code ?? "generation_failed",
        e?.message ?? "Generation failed.",
        e?.remedy ?? "Try a smaller row count.",
      );
    }
    if (Date.now() > deadline) {
      throw new ApiError(
        504,
        "job_timeout",
        "Generation is taking longer than expected.",
        "Reduce the row count, or check the server log.",
      );
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
