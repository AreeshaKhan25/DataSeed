import { motion, useMotionValue, useSpring, useTransform, type MotionValue } from "framer-motion";
import { Fragment, useRef } from "react";
import {
  IconColumns,
  IconDocument,
  IconDownload,
  IconGrid,
  IconNodes,
  IconRules,
  IconSettings,
  IconShield,
  IconSpark,
  IconUpload,
} from "./Icons";
import type { ScreenId } from "../lib/nav";

const ICON = 46;
const MAX_ICON = 72;
const RANGE = 130;

export interface DockItem {
  id: ScreenId;
  label: string;
  color: string;
  icon: (p: { size?: number; className?: string }) => JSX.Element;
}

export const DOCK_ITEMS: DockItem[] = [
  { id: "projects", label: "Projects", color: "#1f4e79", icon: IconGrid },
  { id: "ingest", label: "New project", color: "#0e7490", icon: IconUpload },
  { id: "schema", label: "Schema", color: "#6d28d9", icon: IconColumns },
  { id: "relationships", label: "Relationships", color: "#b06000", icon: IconNodes },
  { id: "rules", label: "Business rules", color: "#0f766e", icon: IconRules },
  { id: "workspace", label: "Workspace", color: "#c5221f", icon: IconSpark },
  { id: "trust", label: "Trust report", color: "#1e8e3e", icon: IconShield },
  { id: "documents", label: "Documents", color: "#334155", icon: IconDocument },
  { id: "export", label: "Export", color: "#0f766e", icon: IconDownload },
  { id: "settings", label: "Settings", color: "#5f6368", icon: IconSettings },
];

function DockIcon({
  item,
  active,
  mouseX,
  onSelect,
}: {
  item: DockItem;
  active: boolean;
  mouseX: MotionValue<number>;
  onSelect: (id: ScreenId) => void;
}) {
  const ref = useRef<HTMLButtonElement>(null);

  const distance = useTransform(mouseX, (x) => {
    const box = ref.current?.getBoundingClientRect();
    if (!box || x === Infinity) return RANGE;
    return Math.abs(x - (box.left + box.width / 2));
  });

  const rawSize = useTransform(distance, [0, RANGE], [MAX_ICON, ICON], { clamp: true });
  const size = useSpring(rawSize, { stiffness: 360, damping: 28, mass: 0.5 });
  const rawLift = useTransform(distance, [0, RANGE], [-10, 0], { clamp: true });
  const lift = useSpring(rawLift, { stiffness: 360, damping: 28, mass: 0.5 });
  const glyph = useTransform(size, (s) => Math.round(s * 0.46));

  const Glyph = item.icon;

  return (
    <motion.button
      ref={ref}
      type="button"
      onClick={() => onSelect(item.id)}
      aria-label={item.label}
      aria-current={active ? "page" : undefined}
      className="group relative flex h-[44px] shrink-0 items-center justify-center outline-none z-10 hover:z-30 focus-visible:z-30"
      style={{ width: size }}
      whileTap={{ scale: 0.88 }}
      transition={{ type: "spring", stiffness: 500, damping: 24 }}
    >
      <motion.span
        className="absolute bottom-0 flex items-center justify-center rounded-[24%] text-white shadow-card"
        style={{
          width: size,
          height: size,
          y: lift,
          background: item.color,
          boxShadow:
            "0 2px 6px rgba(8,14,22,.38), inset 0 1px 0 rgba(255,255,255,.26), inset 0 -1px 0 rgba(0,0,0,.18)",
        }}
      >
        <motion.span style={{ width: glyph, height: glyph }} className="flex items-center justify-center">
          <Glyph size={undefined} className="h-full w-full" />
        </motion.span>

        {/* Tooltip text pill sitting tightly 6px directly above the icon */}
        <span
          className="pointer-events-none absolute bottom-full mb-1.5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md bg-ink/95 border border-white/10 px-2 py-0.5 text-[11px]
                     font-semibold text-white opacity-0 shadow-lift transition-all duration-150
                     group-hover:opacity-100 group-focus-visible:opacity-100 z-50"
        >
          {item.label}
        </span>
      </motion.span>

      {active && (
        <motion.span
          layoutId="dock-active-dot"
          className="absolute -bottom-[6px] h-[3.5px] w-[3.5px] rounded-full bg-white/90 z-20"
          transition={{ type: "spring", stiffness: 420, damping: 30 }}
        />
      )}
    </motion.button>
  );
}

export function Dock({
  current,
  onSelect,
}: {
  current: ScreenId;
  onSelect: (id: ScreenId) => void;
}) {
  const mouseX = useMotionValue(Infinity);

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-center pb-3 sm:pb-5 px-3">
      <motion.nav
        aria-label="Primary"
        onMouseMove={(e) => mouseX.set(e.clientX)}
        onMouseLeave={() => mouseX.set(Infinity)}
        initial={{ y: 80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: "spring", stiffness: 260, damping: 26, delay: 0.15 }}
        className="pointer-events-auto relative flex h-[62px] items-center gap-1 sm:gap-2 rounded-[24px] px-3.5 shadow-2xl backdrop-blur-2xl"
        style={{
          background: "rgba(20, 28, 40, 0.88)",
          border: "1px solid rgba(255, 255, 255, 0.14)",
          boxShadow:
            "0 12px 32px rgba(15, 23, 35, 0.38), 0 2px 6px rgba(15, 23, 35, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.18)",
        }}
      >
        {DOCK_ITEMS.map((item, i) => (
          <Fragment key={item.id}>
            <DockIcon
              item={item}
              active={current === item.id}
              mouseX={mouseX}
              onSelect={onSelect}
            />
            {/* Divider between workflow and tools */}
            {i === 6 && <span className="mx-0.5 h-8 w-px self-center bg-white/15 shrink-0" />}
          </Fragment>
        ))}
      </motion.nav>
    </div>
  );
}
