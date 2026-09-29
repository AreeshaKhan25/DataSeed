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

const ICON = 44;
const MAX_ICON = 68;
const RANGE = 140;

export interface DockItem {
  id: ScreenId;
  label: string;
  color: string;
  icon: (p: { size?: number; className?: string }) => JSX.Element;
}

export const DOCK_ITEMS: DockItem[] = [
  { id: "projects", label: "Projects", color: "#5B3FD0", icon: IconGrid },
  { id: "ingest", label: "New project", color: "#0E7490", icon: IconUpload },
  { id: "schema", label: "Schema", color: "#6D28D9", icon: IconColumns },
  { id: "relationships", label: "Relationships", color: "#B06000", icon: IconNodes },
  { id: "rules", label: "Business rules", color: "#0F766E", icon: IconRules },
  { id: "workspace", label: "Workspace", color: "#431FB8", icon: IconSpark },
  { id: "trust", label: "Trust report", color: "#22A06B", icon: IconShield },
  { id: "documents", label: "Documents", color: "#474457", icon: IconDocument },
  { id: "export", label: "Export", color: "#0E7490", icon: IconDownload },
  { id: "settings", label: "Settings", color: "#5F5C70", icon: IconSettings },
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
  const size = useSpring(rawSize, { stiffness: 380, damping: 28, mass: 0.4 });
  const rawLift = useTransform(distance, [0, RANGE], [-12, 0], { clamp: true });
  const lift = useSpring(rawLift, { stiffness: 380, damping: 28, mass: 0.4 });
  const glyph = useTransform(size, (s) => Math.round(s * 0.48));

  const Glyph = item.icon;

  return (
    <motion.button
      ref={ref}
      type="button"
      onClick={() => onSelect(item.id)}
      aria-label={item.label}
      aria-current={active ? "page" : undefined}
      className="group relative flex h-[44px] shrink-0 items-center justify-center outline-none z-10 hover:z-40 focus-visible:z-40 overflow-visible"
      style={{ width: size }}
      whileTap={{ scale: 0.88 }}
      transition={{ type: "spring", stiffness: 500, damping: 24 }}
    >
      <motion.span
        className="absolute bottom-0 flex items-center justify-center rounded-[22%] text-white overflow-visible transition-shadow"
        style={{
          width: size,
          height: size,
          y: lift,
          background: item.color,
          boxShadow: active
            ? "0 8px 24px -2px rgba(91, 63, 208, 0.45), inset 0 1px 0 rgba(255,255,255,0.4)"
            : "0 4px 14px -2px rgba(27, 23, 64, 0.3), inset 0 1px 0 rgba(255,255,255,0.25)",
        }}
      >
        <motion.span style={{ width: glyph, height: glyph }} className="flex items-center justify-center">
          <Glyph size={undefined} className="h-full w-full" />
        </motion.span>

        {/* Floating Tooltip Pill sitting tightly 6px above icon */}
        <span
          className="pointer-events-none absolute bottom-full mb-1.5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-[#1B1740] border border-white/20 px-2.5 py-0.5 text-[11px] font-semibold text-white shadow-2xl opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100 transition-all duration-150 z-50 pointer-events-none"
        >
          {item.label}
        </span>
      </motion.span>

      {active && (
        <motion.span
          layoutId="dock-active-dot"
          className="absolute -bottom-[5px] h-[4px] w-[4px] rounded-full bg-white z-20 shadow-sm shadow-white"
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
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-center pb-3 px-3">
      <motion.nav
        aria-label="Primary Navigation"
        onMouseMove={(e) => mouseX.set(e.clientX)}
        onMouseLeave={() => mouseX.set(Infinity)}
        initial={{ y: 80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: "spring", stiffness: 260, damping: 26, delay: 0.1 }}
        className="pointer-events-auto relative flex h-[62px] items-center gap-1.5 rounded-full px-4 border border-white/20 backdrop-blur-2xl shadow-[0_16px_36px_-4px_rgba(27,23,64,0.2),0_4px_16px_rgba(91,63,208,0.12)] overflow-visible"
        style={{
          background: "rgba(26, 27, 32, 0.88)",
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
            {/* Soft vertical divider between main workflow and tools */}
            {i === 6 && <span className="mx-0.5 h-7 w-px self-center bg-white/20 shrink-0" />}
          </Fragment>
        ))}
      </motion.nav>
    </div>
  );
}
