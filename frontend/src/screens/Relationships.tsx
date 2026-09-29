import { motion } from "framer-motion";
import { useMemo, useState } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  EdgeLabelRenderer,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  getBezierPath,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { api, type ForeignKey } from "../lib/api";
import { ease, rise, spring } from "../lib/motion";
import { useStore } from "../lib/store";
import { IconKey, IconLink, IconSpark } from "../components/Icons";
import { Banner, Button, Card, EmptyState, PageTitle, Toggle } from "../components/ui";

// Node Data Type
type TableNodeData = {
  name: string;
  rowCount: number;
  fields: { name: string; dtype: string; pk: boolean; fk: boolean }[];
};

// Custom Table Node Component
function TableNode({ data, selected }: NodeProps & { data: TableNodeData }) {
  return (
    <div
      className={`min-w-[210px] max-w-[260px] overflow-hidden rounded-xl border bg-canvas-raised shadow-card transition-all ${
        selected ? "border-navy ring-2 ring-navy/25 shadow-lift" : "border-line"
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-3 !w-3 !bg-navy !border-2 !border-white !-left-1.5"
      />
      <div className="flex h-[36px] items-center justify-between bg-navy px-3.5 text-white">
        <span className="font-serif text-[13.5px] font-semibold tracking-tight">{data.name}</span>
        <span className="tnum rounded-md bg-white/15 px-1.5 py-0.5 text-[10.5px] font-medium text-white/90">
          {data.rowCount.toLocaleString()}
        </span>
      </div>
      <div className="py-1.5">
        {data.fields.map((f) => (
          <div
            key={f.name}
            className="flex items-center justify-between gap-2 px-3 py-1 text-[11.5px] text-ink-soft hover:bg-canvas/50"
          >
            <span className="flex items-center gap-1.5 truncate">
              {f.pk && <IconKey size={11} className="shrink-0 text-navy" />}
              {f.fk && <IconLink size={11} className="shrink-0 text-teal" />}
              {!f.pk && !f.fk && <span className="w-[11px] shrink-0" />}
              <span className={`truncate ${f.pk ? "font-semibold text-ink" : ""}`}>{f.name}</span>
            </span>
            <span className="text-[10px] text-ink-mute font-mono shrink-0">{f.dtype}</span>
          </div>
        ))}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!h-3 !w-3 !bg-navy !border-2 !border-white !-right-1.5"
      />
    </div>
  );
}

// Custom Edge Component with Cardinality Label
function CardinalityEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
  selected,
}: EdgeProps & { data?: { cardinality: string; fk: ForeignKey } }) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <path
        id={id}
        style={{
          ...style,
          strokeWidth: selected ? 2.5 : 1.75,
          stroke: selected ? "#1f4e79" : "#b6c2d2",
        }}
        className="react-flow__edge-path transition-colors"
        d={edgePath}
        markerEnd={markerEnd}
      />
      {data?.cardinality && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: "all",
            }}
            className="nodrag nopan"
          >
            <span
              className={`tnum flex h-5 items-center justify-center rounded-md border px-2 text-[10.5px] font-semibold shadow-sm transition-colors cursor-pointer ${
                selected
                  ? "border-navy bg-navy text-white"
                  : "border-line bg-canvas-raised text-ink-mute hover:border-navy hover:text-navy"
              }`}
            >
              {data.cardinality}
            </span>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

const nodeTypes = { tableNode: TableNode };
const edgeTypes = { cardinalityEdge: CardinalityEdge };

export function Relationships() {
  const { schema, project, go, run } = useStore();
  const [selectedFk, setSelectedFk] = useState<ForeignKey | null>(null);
  const [proposals, setProposals] = useState<
    (ForeignKey & { confidence: number; reason: string; already_applied: boolean })[] | null
  >(null);
  const [mode, setMode] = useState("");
  const [thinking, setThinking] = useState(false);

  // Compute Layout Nodes & Edges from Schema
  const { initialNodes, initialEdges } = useMemo(() => {
    if (!schema) return { initialNodes: [], initialEdges: [] };

    // Topological depth calculation for column placement
    const depth = new Map<string, number>();
    const resolve = (name: string, seen = new Set<string>()): number => {
      if (depth.has(name)) return depth.get(name)!;
      if (seen.has(name)) return 0;
      seen.add(name);
      const parents = schema.foreign_keys.filter((f) => f.child_table === name);
      const d = parents.length
        ? Math.max(...parents.map((f) => resolve(f.parent_table, seen) + 1))
        : 0;
      depth.set(name, d);
      return d;
    };
    schema.tables.forEach((t) => resolve(t.name));

    const byDepth = new Map<number, string[]>();
    schema.tables.forEach((t) => {
      const d = depth.get(t.name) ?? 0;
      byDepth.set(d, [...(byDepth.get(d) ?? []), t.name]);
    });

    const fkSet = new Set(schema.foreign_keys.map((f) => `${f.child_table}.${f.child_column}`));

    const NODE_W = 240;
    const GAP_X = 140;
    const GAP_Y = 50;

    const nodes: Node[] = [];

    [...byDepth.keys()].sort((a, b) => a - b).forEach((d) => {
      let y = 0;
      (byDepth.get(d) ?? []).forEach((name) => {
        const table = schema.tables.find((t) => t.name === name);
        if (!table) return;
        const fields = (table.columns ?? []).slice(0, 8).map((c) => ({
          name: c.name,
          dtype: c.dtype,
          pk: c.name === table.primary_key,
          fk: fkSet.has(`${name}.${c.name}`),
        }));

        nodes.push({
          id: name,
          type: "tableNode",
          position: { x: d * (NODE_W + GAP_X) + 40, y: y + 40 },
          data: {
            name: table.name,
            rowCount: table.row_count,
            fields,
          },
        });

        y += 40 + fields.length * 28 + GAP_Y;
      });
    });

    const edges: Edge[] = schema.foreign_keys.map((fk) => {
      const edgeId = `${fk.parent_table}->${fk.child_table}:${fk.child_column}`;
      return {
        id: edgeId,
        source: fk.parent_table,
        target: fk.child_table,
        type: "cardinalityEdge",
        animated: true,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 14,
          height: 14,
          color: "#b6c2d2",
        },
        data: {
          cardinality: fk.cardinality,
          fk,
        },
      };
    });

    return { initialNodes: nodes, initialEdges: edges };
  }, [schema]);

  const infer = async () => {
    if (!project) return;
    setThinking(true);
    const res = await run(() => api.inferRelations(project.id));
    if (res) {
      setProposals(res.proposals);
      setMode(res.mode);
    }
    setThinking(false);
  };

  if (!schema || !project) {
    return (
      <EmptyState
        title="No project open"
        body="Open a project to see how its tables connect."
        action={<Button variant="primary" onClick={() => go("projects")}>Go to projects</Button>}
      />
    );
  }

  return (
    <div className="space-y-5">
      <motion.div variants={rise} className="flex flex-wrap items-end justify-between gap-4">
        <PageTitle sub={`${schema.tables.length} tables joined by ${schema.foreign_keys.length} foreign keys`}>
          Relationships
        </PageTitle>
        <div className="flex gap-2">
          <Button icon={<IconSpark size={15} />} loading={thinking} onClick={infer}>
            Infer relationships
          </Button>
          <Button variant="primary" onClick={() => go("workspace")}>
            Generate
          </Button>
        </div>
      </motion.div>

      {proposals && (
        <Banner
          tone="iris"
          icon={<IconSpark size={17} />}
          title={
            mode === "live"
              ? `AI proposed ${proposals.length} relationships, ${proposals.filter((p) => !p.already_applied).length} of them new`
              : `Heuristics found ${proposals.length} relationships from name matching and value containment`
          }
          body={proposals.map((p) => `${p.child_table}.${p.child_column} → ${p.parent_table}`).join("  ·  ")}
          actions={
            <Button size="sm" onClick={() => setProposals(null)}>
              Dismiss
            </Button>
          }
        />
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_310px]">
        <motion.div variants={rise} className="min-w-0">
          <Card className="overflow-hidden border border-line p-0 bg-canvas-raised shadow-card">
            <div className="h-[560px] w-full">
              <ReactFlow
                defaultNodes={initialNodes}
                defaultEdges={initialEdges}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                minZoom={0.2}
                maxZoom={1.5}
                onEdgeClick={(_, edge) => {
                  const fkData = (edge.data as { fk?: ForeignKey })?.fk;
                  if (fkData) setSelectedFk(fkData);
                }}
                onNodeClick={(_, node) => {
                  const fk = schema.foreign_keys.find(
                    (f) => f.parent_table === node.id || f.child_table === node.id,
                  );
                  if (fk) setSelectedFk(fk);
                }}
              >
                <Background variant={BackgroundVariant.Dots} gap={20} size={1.2} color="#d3d9e3" />
                <Controls showInteractive={false} className="!bg-canvas-raised !border !border-line !shadow-card !rounded-xl overflow-hidden" />
              </ReactFlow>
            </div>
          </Card>
        </motion.div>

        <motion.div variants={rise} className="min-w-0 space-y-3">
          <Card className="p-5">
            <div className="label mb-3 uppercase">Relationship Detail</div>
            {selectedFk ? (
              <motion.div
                key={`${selectedFk.child_table}.${selectedFk.child_column}`}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={ease}
                className="space-y-4"
              >
                <div className="rounded-xl bg-canvas px-3 py-2.5 text-[12.5px] leading-relaxed text-ink">
                  <span className="font-semibold">
                    {selectedFk.child_table}.{selectedFk.child_column}
                  </span>
                  <span className="mx-1.5 text-ink-faint">→</span>
                  <span className="font-semibold">
                    {selectedFk.parent_table}.{selectedFk.parent_column}
                  </span>
                </div>

                <div>
                  <div className="label mb-2 uppercase">Cardinality</div>
                  <div className="flex gap-1.5">
                    {["1:1", "1:N", "N:N"].map((c) => (
                      <span
                        key={c}
                        className={`rounded-lg border px-2.5 py-1 text-[11.5px] font-semibold ${
                          selectedFk.cardinality === c
                            ? "border-navy bg-navy text-white"
                            : "border-line bg-canvas-sunken text-ink-mute"
                        }`}
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </div>

                {(selectedFk.count_values?.length ?? 0) > 0 && (
                  <div>
                    <div className="label mb-2 uppercase">Children per parent</div>
                    <div className="flex h-16 items-end gap-[3px]">
                      {selectedFk.count_values.slice(0, 16).map((v, i) => {
                        const prob = selectedFk.count_probs?.[i] ?? 0;
                        const maxProb = Math.max(...(selectedFk.count_probs ?? [1]));
                        return (
                          <motion.div
                            key={`${v}-${i}`}
                            initial={{ height: 0 }}
                            animate={{
                              height: `${Math.max(4, (prob / (maxProb || 1)) * 100)}%`,
                            }}
                            transition={{ delay: i * 0.02, ...spring }}
                            className="flex-1 rounded-t-sm bg-navy/70"
                            title={`${v} children: ${(prob * 100).toFixed(1)}%`}
                          />
                        );
                      })}
                    </div>
                    <div className="tnum mt-1.5 flex justify-between text-[10.5px] text-ink-mute">
                      <span>{Math.min(...selectedFk.count_values)}</span>
                      <span>
                        avg{" "}
                        {(
                          selectedFk.count_values.reduce(
                            (n, v, i) => n + v * (selectedFk.count_probs?.[i] ?? 0),
                            0,
                          )
                        ).toFixed(1)}
                      </span>
                      <span>{Math.max(...selectedFk.count_values)}</span>
                    </div>
                  </div>
                )}
              </motion.div>
            ) : (
              <p className="text-[12.5px] leading-relaxed text-ink-mute">
                Select an edge or table on the canvas to inspect its foreign key relationship and
                the real children-per-parent distribution learned from your data.
              </p>
            )}
          </Card>

          <Card className="p-5">
            <div className="label mb-2 uppercase">Reconciliation</div>
            <Toggle
              checked
              locked
              label="Compute parent totals from children"
              hint="Always enforced. Order totals are summed from their line items after generation, never invented, which is why they reconcile exactly."
            />
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
