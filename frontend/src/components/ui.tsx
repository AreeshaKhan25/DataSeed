import { AnimatePresence, motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect, type ReactNode } from "react";
import { ease, popIn, pressable, quick, softSpring, spring } from "../lib/motion";
import { IconAlert, IconCheck, IconClose } from "./Icons";

// ---------------------------------------------------------------- text

export function PageTitle({ children, sub }: { children: ReactNode; sub?: ReactNode }) {
  return (
    <div>
      <h1 className="font-serif text-[30px] font-semibold leading-tight tracking-[-0.015em] text-ink">
        {children}
      </h1>
      {sub && <p className="mt-1 text-[13.5px] text-ink-mute">{sub}</p>}
    </div>
  );
}

export function SectionTitle({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="mb-3 flex items-baseline justify-between gap-3">
      <h2 className="font-serif text-[17px] font-semibold text-ink">{children}</h2>
      {hint && <span className="text-[12px] text-ink-mute">{hint}</span>}
    </div>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return <div className="label mb-1.5 uppercase">{children}</div>;
}

// ---------------------------------------------------------------- surfaces

export function Card({
  children,
  className = "",
  interactive = false,
  ...rest
}: { children: ReactNode; className?: string; interactive?: boolean } & Record<string, unknown>) {
  return (
    <motion.div
      className={`card ${interactive ? "cursor-pointer" : ""} ${className}`}
      {...(interactive
        ? { whileHover: { y: -3 }, whileTap: { scale: 0.995 }, transition: softSpring }
        : {})}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

// ---------------------------------------------------------------- controls

type ButtonProps = {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
  disabled?: boolean;
  loading?: boolean;
  icon?: ReactNode;
  className?: string;
  title?: string;
};

export function Button({
  children,
  onClick,
  variant = "secondary",
  size = "md",
  disabled,
  loading,
  icon,
  className = "",
  title,
}: ButtonProps) {
  const styles: Record<string, string> = {
    primary: "bg-navy text-white hover:bg-navy-deep shadow-card",
    secondary: "bg-canvas-raised text-ink border border-line hover:border-line-strong",
    ghost: "bg-transparent text-ink-soft hover:bg-canvas-sunken",
    danger: "bg-rose-wash text-rose border border-rose/25 hover:bg-rose/12",
  };
  const sizing = size === "sm" ? "h-8 px-3 text-[12.5px] gap-1.5" : "h-10 px-4 text-[13.5px] gap-2";

  return (
    <motion.button
      type="button"
      title={title}
      onClick={onClick}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center rounded-xl font-semibold transition-colors
                  disabled:cursor-not-allowed disabled:opacity-45 ${styles[variant]} ${sizing} ${className}`}
      whileHover={disabled || loading ? undefined : { y: -1 }}
      whileTap={disabled || loading ? undefined : { scale: 0.97 }}
      transition={spring}
    >
      {loading ? <Spinner /> : icon}
      {children}
    </motion.button>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-current
                  border-t-transparent opacity-70 ${className}`}
    />
  );
}

export function Pill({
  children,
  tone = "neutral",
  active = false,
  onClick,
}: {
  children: ReactNode;
  tone?: "neutral" | "grass" | "amber" | "rose" | "navy" | "iris" | "teal";
  active?: boolean;
  onClick?: () => void;
}) {
  const tones: Record<string, string> = {
    neutral: "bg-canvas-sunken text-ink-soft border-line",
    grass: "bg-grass-wash text-grass border-grass/20",
    amber: "bg-amber-wash text-amber border-amber/20",
    rose: "bg-rose-wash text-rose border-rose/20",
    navy: "bg-navy-wash text-navy border-navy/20",
    iris: "bg-iris-wash text-iris border-iris/20",
    teal: "bg-teal-wash text-teal border-teal/20",
  };
  const Tag = onClick ? motion.button : motion.span;
  return (
    <Tag
      {...(onClick ? { type: "button", onClick, ...pressable } : {})}
      className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11.5px] font-semibold
                  ${active ? "bg-navy text-white border-navy" : tones[tone]}`}
    >
      {children}
    </Tag>
  );
}

export function Dot({ tone = "grass" }: { tone?: "grass" | "amber" | "rose" | "navy" }) {
  const map = { grass: "bg-grass", amber: "bg-amber", rose: "bg-rose", navy: "bg-navy" };
  return <span className={`inline-block h-[7px] w-[7px] shrink-0 rounded-full ${map[tone]}`} />;
}

export function Field({
  label,
  value,
  onChange,
  type = "text",
  suffix,
  placeholder,
  min,
  max,
}: {
  label: string;
  value: string | number;
  onChange: (v: string) => void;
  type?: string;
  suffix?: ReactNode;
  placeholder?: string;
  min?: number;
  max?: number;
}) {
  return (
    <label className="block">
      <Label>{label}</Label>
      <div className="flex items-center gap-1.5 rounded-xl border border-line bg-canvas-raised px-3 transition-colors focus-within:border-navy-light">
        <input
          type={type}
          value={value}
          min={min}
          max={max}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          className="tnum h-10 w-full bg-transparent text-[13.5px] font-medium text-ink outline-none placeholder:text-ink-faint"
        />
        {suffix}
      </div>
    </label>
  );
}

export function Slider({
  label,
  value,
  onChange,
  max = 0.2,
  step = 0.005,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  max?: number;
  step?: number;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="label uppercase">{label}</span>
        <span className="tnum text-[12.5px] font-semibold text-ink">
          {(value * 100).toFixed(1)}%
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-line-strong accent-navy
                   [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4
                   [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full
                   [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white
                   [&::-webkit-slider-thumb]:bg-navy [&::-webkit-slider-thumb]:shadow-card"
      />
    </div>
  );
}

export function Toggle({
  checked,
  onChange,
  label,
  hint,
  locked,
}: {
  checked: boolean;
  onChange?: (v: boolean) => void;
  label: string;
  hint?: string;
  locked?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-3 py-1.5">
      <div className="min-w-0">
        <div className="flex items-center gap-1.5 text-[13px] font-medium text-ink">
          {label}
          {locked && <IconAlert size={12} className="text-ink-faint" />}
        </div>
        {hint && <div className="mt-0.5 text-[11.5px] leading-snug text-ink-mute">{hint}</div>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={locked}
        onClick={() => onChange?.(!checked)}
        className={`relative mt-0.5 h-[22px] w-[38px] shrink-0 rounded-full transition-colors
                    ${checked ? "bg-navy" : "bg-line-strong"} ${locked ? "opacity-50" : ""}`}
      >
        <motion.span
          layout
          transition={spring}
          className="absolute top-[3px] h-4 w-4 rounded-full bg-white shadow-card"
          style={{ left: checked ? 19 : 3 }}
        />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------- data display

/** Counts up to `value`. Purely decorative, so it snaps under reduced motion. */
export function AnimatedNumber({
  value,
  decimals = 0,
  className = "",
}: {
  value: number;
  decimals?: number;
  className?: string;
}) {
  const raw = useMotionValue(0);
  const smooth = useSpring(raw, { stiffness: 90, damping: 20, mass: 0.6 });
  const text = useTransform(smooth, (v) => v.toFixed(decimals));
  useEffect(() => {
    raw.set(value);
  }, [value, raw]);
  return <motion.span className={`tnum ${className}`}>{text}</motion.span>;
}

export function ScoreRing({
  value,
  tone = "navy",
  size = 62,
  label,
}: {
  value: number;
  tone?: "grass" | "amber" | "rose" | "navy";
  size?: number;
  label?: string;
}) {
  const stroke = 5.5;
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const colors = { grass: "#1e8e3e", amber: "#b06000", rose: "#c5221f", navy: "#1f4e79" };

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" role="img" aria-label={label}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#eef1f6" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={colors[tone]}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference * (1 - Math.max(0, Math.min(100, value)) / 100) }}
          transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <AnimatedNumber
          value={value}
          className="font-serif text-[19px] font-semibold text-ink"
        />
      </div>
    </div>
  );
}

export function Meter({
  value,
  tone = "grass",
  height = 6,
}: {
  value: number;
  tone?: "grass" | "amber" | "rose" | "navy";
  height?: number;
}) {
  const colors = { grass: "bg-grass", amber: "bg-amber", rose: "bg-rose", navy: "bg-navy" };
  return (
    <div className="w-full overflow-hidden rounded-full bg-canvas-sunken" style={{ height }}>
      <motion.div
        className={`h-full rounded-full ${colors[tone]}`}
        initial={{ width: 0 }}
        animate={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      />
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <motion.div
      variants={popIn}
      initial="hidden"
      animate="show"
      className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-line-strong
                 bg-canvas-raised/60 px-8 py-14 text-center"
    >
      <h3 className="font-serif text-[17px] font-semibold text-ink">{title}</h3>
      <p className="mt-1.5 max-w-sm text-[13px] leading-relaxed text-ink-mute">{body}</p>
      {action && <div className="mt-5">{action}</div>}
    </motion.div>
  );
}

export function Banner({
  tone = "navy",
  title,
  body,
  actions,
  icon,
}: {
  tone?: "navy" | "grass" | "amber" | "rose" | "iris";
  title: ReactNode;
  body?: ReactNode;
  actions?: ReactNode;
  icon?: ReactNode;
}) {
  const tones: Record<string, string> = {
    navy: "bg-navy-wash border-navy/15 text-navy",
    grass: "bg-grass-wash border-grass/18 text-grass",
    amber: "bg-amber-wash border-amber/18 text-amber",
    rose: "bg-rose-wash border-rose/18 text-rose",
    iris: "bg-iris-wash border-iris/18 text-iris",
  };
  return (
    <motion.div
      variants={popIn}
      initial="hidden"
      animate="show"
      className={`flex items-center gap-3 rounded-2xl border px-4 py-3 ${tones[tone]}`}
    >
      {icon ?? <IconCheck size={17} />}
      <div className="min-w-0 flex-1">
        <div className="text-[13.5px] font-semibold">{title}</div>
        {body && <div className="mt-0.5 text-[12.5px] leading-snug opacity-85">{body}</div>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </motion.div>
  );
}

/** Error surface. Always shows the remedy — the backend guarantees one. */
export function ErrorNote({
  error,
  onDismiss,
}: {
  error: { message: string; remedy?: string } | null;
  onDismiss?: () => void;
}) {
  return (
    <AnimatePresence>
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -8, height: 0 }}
          animate={{ opacity: 1, y: 0, height: "auto" }}
          exit={{ opacity: 0, y: -8, height: 0 }}
          transition={ease}
          className="overflow-hidden"
        >
          <div className="flex items-start gap-3 rounded-2xl border border-rose/20 bg-rose-wash px-4 py-3">
            <IconAlert size={17} className="mt-0.5 shrink-0 text-rose" />
            <div className="min-w-0 flex-1">
              <div className="text-[13.5px] font-semibold text-rose">{error.message}</div>
              {error.remedy && (
                <div className="mt-0.5 text-[12.5px] leading-snug text-rose/85">{error.remedy}</div>
              )}
            </div>
            {onDismiss && (
              <button
                type="button"
                onClick={onDismiss}
                aria-label="Dismiss"
                className="shrink-0 rounded-lg p-1 text-rose/70 transition-colors hover:bg-rose/10"
              >
                <IconClose size={14} />
              </button>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <motion.div
      className={`rounded-lg bg-canvas-sunken ${className}`}
      animate={{ opacity: [0.55, 1, 0.55] }}
      transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
    />
  );
}

export function Modal({
  open,
  onClose,
  title,
  sub,
  children,
  width = 640,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  sub?: ReactNode;
  children: ReactNode;
  width?: number;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={quick}
        >
          <div
            className="absolute inset-0 bg-ink/35 backdrop-blur-[2px]"
            onClick={onClose}
            aria-hidden
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={title}
            initial={{ opacity: 0, scale: 0.97, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, y: 6 }}
            transition={spring}
            style={{ width }}
            className="relative max-h-[86vh] overflow-auto rounded-3xl border border-line bg-canvas-raised p-6 shadow-lift"
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h2 className="font-serif text-[20px] font-semibold text-ink">{title}</h2>
                {sub && <div className="mt-1 text-[12.5px] text-ink-mute">{sub}</div>}
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="rounded-lg p-1.5 text-ink-mute transition-colors hover:bg-canvas-sunken"
              >
                <IconClose size={16} />
              </button>
            </div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
