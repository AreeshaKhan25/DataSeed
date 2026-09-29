// A small hand-rolled icon set. Stroke 1.75 throughout, 24x24 grid, round caps.
// Inline SVG rather than an icon font so stroke weight stays consistent and
// nothing depends on a webfont loading before the UI reads correctly.

type P = { className?: string; size?: number; strokeWidth?: number };

const base = (size: number, strokeWidth: number, className?: string) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  className,
});

export const IconGrid = ({ size = 20, strokeWidth = 1.75, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <rect x="3" y="3" width="7" height="7" rx="2" />
    <rect x="14" y="3" width="7" height="7" rx="2" />
    <rect x="3" y="14" width="7" height="7" rx="2" />
    <rect x="14" y="14" width="7" height="7" rx="2" />
  </svg>
);

export const IconUpload = ({ size = 20, strokeWidth = 1.75, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <path d="M12 16V4" />
    <path d="m7 9 5-5 5 5" />
    <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
  </svg>
);

export const IconColumns = ({ size = 20, strokeWidth = 1.75, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M9 4v16M15 4v16M3 9h18" />
  </svg>
);

export const IconNodes = ({ size = 20, strokeWidth = 1.75, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <circle cx="6" cy="6" r="2.5" />
    <circle cx="18" cy="12" r="2.5" />
    <circle cx="6" cy="18" r="2.5" />
    <path d="M8.2 7.3 15.6 11M15.6 13 8.2 16.7" />
  </svg>
);

export const IconSpark = ({ size = 20, strokeWidth = 1.75, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <path d="M12 3.5 13.7 9l5.5 1.7-5.5 1.7L12 18l-1.7-5.6L4.8 10.7 10.3 9z" />
    <path d="M18.5 3.5v3M20 5h-3" />
  </svg>
);

export const IconShield = ({ size = 20, strokeWidth = 1.75, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <path d="M12 3.2 5 6v5.4c0 4.3 2.9 8.3 7 9.4 4.1-1.1 7-5.1 7-9.4V6z" />
    <path d="m9 12 2.2 2.2L15.5 10" />
  </svg>
);

export const IconDocument = ({ size = 20, strokeWidth = 1.75, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
    <path d="M14 3v5h5M9 13h6M9 17h4" />
  </svg>
);

export const IconDownload = ({ size = 20, strokeWidth = 1.75, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <path d="M12 4v12" />
    <path d="m7 11 5 5 5-5" />
    <path d="M4 20h16" />
  </svg>
);

export const IconSettings = ({ size = 20, strokeWidth = 1.75, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 14.5a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-2.9 1.2v.2a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-3-1.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0-1.2-2.9H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.3-3l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 2.9-1.2V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 3 1.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0 1.2 2.9h.2a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.6 1z" />
  </svg>
);

export const IconCheck = ({ size = 16, strokeWidth = 2.2, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <path d="m4.5 12.5 4.5 4.5L19.5 6.5" />
  </svg>
);

export const IconAlert = ({ size = 16, strokeWidth = 1.9, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7.5v5M12 16.2v.3" />
  </svg>
);

export const IconLock = ({ size = 16, strokeWidth = 1.8, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <rect x="4.5" y="10.5" width="15" height="10" rx="2.5" />
    <path d="M8 10.5V7.8a4 4 0 0 1 8 0v2.7" />
  </svg>
);

export const IconArrow = ({ size = 16, strokeWidth = 1.9, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
);

export const IconDice = ({ size = 16, strokeWidth = 1.8, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <rect x="4" y="4" width="16" height="16" rx="3.5" />
    <circle cx="9" cy="9" r="1.1" fill="currentColor" stroke="none" />
    <circle cx="15" cy="15" r="1.1" fill="currentColor" stroke="none" />
    <circle cx="12" cy="12" r="1.1" fill="currentColor" stroke="none" />
  </svg>
);

export const IconKey = ({ size = 14, strokeWidth = 1.8, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <circle cx="8" cy="12" r="3.5" />
    <path d="M11.5 12H20M17 12v3M20 12v2.5" />
  </svg>
);

export const IconLink = ({ size = 14, strokeWidth = 1.8, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <path d="M10 13.5a3.5 3.5 0 0 0 5 0l3-3a3.5 3.5 0 0 0-5-5l-1.2 1.2" />
    <path d="M14 10.5a3.5 3.5 0 0 0-5 0l-3 3a3.5 3.5 0 0 0 5 5l1.2-1.2" />
  </svg>
);

export const IconSearch = ({ size = 16, strokeWidth = 1.9, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="m16 16 4 4" />
  </svg>
);

export const IconClose = ({ size = 16, strokeWidth = 2, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <path d="m6 6 12 12M18 6 6 18" />
  </svg>
);

export const IconRules = ({ size = 20, strokeWidth = 1.75, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <path d="M5 4.5h14M5 9.5h9M5 14.5h6" />
    <path d="m13.5 18 2.2 2.2L20.5 15.5" />
  </svg>
);

export const IconPlus = ({ size = 16, strokeWidth = 1.9, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);

export const IconTrash = ({ size = 16, strokeWidth = 1.9, className }: P) => (
  <svg {...base(size, strokeWidth, className)}>
    <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
  </svg>
);

export const IconLogo = ({ size = 22, className }: { size?: number; className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className}>
    <rect width="32" height="32" rx="8" fill="currentColor" />
    <circle cx="11" cy="12" r="3.2" fill="#fff" />
    <circle cx="21" cy="12" r="3.2" fill="#fff" fillOpacity="0.55" />
    <circle cx="11" cy="21" r="3.2" fill="#fff" fillOpacity="0.55" />
    <circle cx="21" cy="21" r="3.2" fill="#fff" />
  </svg>
);
