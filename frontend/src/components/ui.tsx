import { AnimatePresence, motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect, type ReactNode } from "react";
import { ease, popIn, pressable, quick, softSpring, spring } from "../lib/motion";
import { IconAlert, IconCheck, IconClose } from "./Icons";

// ---------------------------------------------------------------- text

export function PageTitle({ children, sub }: { children: ReactNode; sub?: ReactNode }) {
  return (
    <div>
      <h1 className="font-sans text-[28px] sm:text-[32px] font-bold leading-tight tracking-tight text-on-surface">
        {children}
      </h1>
      {sub && <p className="mt-1 text-[13.5px] text-secondary font-sans">{sub}</p>}
    </div>
  );
}

export function SectionTitle({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="mb-3 flex items-baseline justify-between gap-3">
      <h2 className="font-sans text-[18px] font-semibold text-on-surface">{children}</h2>
      {hint && <span className="text-[12.5px] text-secondary">{hint}</span>}
    </div>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return <div className="label mb-1.5 uppercase text-secondary font-semibold text-[11px] tracking-wider">{children}</div>;
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
      className={`rounded-2xl border border-outline-variant/30 bg-white bento-shadow p-6 transition-all ${
        interactive ? "cursor-pointer bento-shadow-hover hover:-translate-y-0.5" : ""
      } ${className}`}
      {...(interactive
        ? { whileTap: { scale: 0.995 }, transition: softSpring }
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
  size?: "sm" | "md" | "lg";
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
    primary: "bg-primary text-on-primary hover:bg-primary-container shadow-sm shadow-primary/20",
    secondary: "bg-surface-container-low text-primary hover:bg-secondary-container border border-outline-variant/40",
    ghost: "bg-transparent text-secondary hover:bg-surface-container-low hover:text-on-surface",
    danger: "bg-error-container/60 text-error hover:bg-error-container border border-error/20",
  };
  const sizing =
    size === "sm"
      ? "h-8 px-3 text.xs gap-1.5"
      : size === "lg"
      ? "h-11 px-5 text-sm gap-2.5"
      : "h-9.5 px-4 text-[13px] gap-2";

  return (
    <motion.button
      type="button"
      title={title}
      onClick={onClick}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center rounded-full font-semibold transition-all duration-150
                  disabled:cursor-not-allowed disabled:opacity-45 ${styles[variant]} ${sizing} ${className}`}
      whileHover={disabled || loading ? undefined : { scale: 1.01 }}
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
                  border-t-transparent opacity-75 ${className}`}
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
  tone?: "neutral" | "grass" | "amber" | "rose" | "navy" | "iris" | "teal" | "ai";
  active?: boolean;
  onClick?: () => void;
}) {
  const tones: Record<string, string> = {
    neutral: "bg-surface-container-low text-secondary border-outline-variant/30",
    grass: "bg-grass-wash text-grass border-grass/20",
    amber: "bg-amber-wash text-amber border-amber/20",
    rose: "bg-rose-wash text-rose border-rose/20",
    navy: "bg-primary-fixed text-primary border-primary/20",
    iris: "bg-secondary-container text-primary border-primary/20",
    teal: "bg-teal-wash text-teal border-teal/20",
    ai: "bg-[#FFD666] text-[#1B1740] font-bold border-[#CCA73C]/30",
  };
  const Tag = onClick ? motion.button : motion.span;
  return (
    <Tag
      {...(onClick ? { type: "button", onClick, ...pressable } : {})}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11.5px] font-semibold
                  ${active ? "bg-primary text-on-primary border-primary" : tones[tone]}`}
    >
      {children}
    </Tag>
  );
}

export function Dot({ tone = "grass" }: { tone?: "grass" | "amber" | "rose" | "navy" }) {
  const map = { grass: "bg-grass", amber: "bg-amber", rose: "bg-rose", navy: "bg-primary" };
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
      <div className="flex items-center gap-2 rounded-xl border border-outline-variant/40 bg-white px-3.5 transition-colors focus-within:border-primary focus-within:ring-2 focus-within:ring-primary-fixed-dim/50">
        <input
          type={type}
          value={value}
          min={min}
          max={max}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          className="tnum h-10 w-full bg-transparent text-[13.5px] font-medium text-on-surface outline-none placeholder:text-secondary/50 font-sans"
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
        <span className="label uppercase text-secondary font-semibold text-[11px]">{label}</span>
        <span className="tnum text-[12.5px] font-semibold text-primary">
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
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-surface-container-high accent-primary
                   [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4
                   [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full
                   [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white
                   [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:shadow-card"
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
    <div className="flex items-start justify-between gap-3 py-2">
      <div className="min-w-0">
        <div className="flex items-center gap-1.5 text-[13px] font-medium text-on-surface">
          {label}
          {locked && <IconAlert size={12} className="text-secondary/60" />}
        </div>
        {hint && <div className="mt-0.5 text-[12px] leading-snug text-secondary">{hint}</div>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={locked}
        onClick={() => onChange?.(!checked)}
        className={`relative mt-0.5 h-[22px] w-[38px] shrink-0 rounded-full transition-colors
                    ${checked ? "bg-primary" : "bg-outline-variant"} ${locked ? "opacity-50" : ""}`}
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
  size = 64,
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
  const colors = { grass: "#22A06B", amber: "#F5A524", rose: "#E5484D", navy: "#5B3FD0" };

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" role="img" aria-label={label}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#ECE8F7" strokeWidth={stroke} />
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
          className="font-sans text-[19px] font-bold text-on-surface"
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
  const colors = { grass: "bg-grass", amber: "bg-amber", rose: "bg-rose", navy: "bg-primary" };
  return (
    <div className="w-full overflow-hidden rounded-full bg-surface-container-low" style={{ height }}>
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
      className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-outline-variant/50
                 bg-white/70 px-8 py-14 text-center bento-shadow"
    >
      <h3 className="font-sans text-[18px] font-bold text-on-surface">{title}</h3>
      <p className="mt-1.5 max-w-sm text-[13.5px] leading-relaxed text-secondary">{body}</p>
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
    navy: "bg-primary-fixed/60 border-primary/20 text-primary",
    grass: "bg-grass-wash border-grass/20 text-grass",
    amber: "bg-amber-wash border-amber/20 text-amber",
    rose: "bg-rose-wash border-rose/20 text-rose",
    iris: "bg-secondary-container border-primary/20 text-primary",
  };
  return (
    <motion.div
      variants={popIn}
      initial="hidden"
      animate="show"
      className={`flex items-center gap-3.5 rounded-2xl border px-4.5 py-3.5 ${tones[tone]}`}
    >
      {icon ?? <IconCheck size={18} />}
      <div className="min-w-0 flex-1">
        <div className="text-[13.5px] font-semibold">{title}</div>
        {body && <div className="mt-0.5 text-[12.5px] leading-snug opacity-85">{body}</div>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </motion.div>
  );
}

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
          <div className="flex items-start gap-3 rounded-2xl border border-error/20 bg-error-container/60 px-4 py-3">
            <IconAlert size={18} className="mt-0.5 shrink-0 text-error" />
            <div className="min-w-0 flex-1">
              <div className="text-[13.5px] font-semibold text-error">{error.message}</div>
              {error.remedy && (
                <div className="mt-0.5 text-[12.5px] leading-snug text-error/85">{error.remedy}</div>
              )}
            </div>
            {onDismiss && (
              <button
                type="button"
                onClick={onDismiss}
                aria-label="Dismiss"
                className="shrink-0 rounded-full p-1 text-error/70 transition-colors hover:bg-error-container"
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
      className={`rounded-xl bg-surface-container-low ${className}`}
      animate={{ opacity: [0.5, 1, 0.5] }}
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
            className="absolute inset-0 bg-[#1A1B20]/40 backdrop-blur-md"
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
            className="relative max-h-[86vh] overflow-auto rounded-3xl border border-outline-variant/40 bg-white p-6 bento-shadow shadow-2xl"
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h2 className="font-sans text-[20px] font-bold text-on-surface">{title}</h2>
                {sub && <div className="mt-1 text-[13px] text-secondary">{sub}</div>}
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="rounded-full p-1.5 text-secondary transition-colors hover:bg-surface-container-low"
              >
                <IconClose size={18} />
              </button>
            </div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
